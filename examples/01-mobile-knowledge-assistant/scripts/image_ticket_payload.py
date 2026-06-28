from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = PROJECT_ROOT / "data" / "multimodal" / "login_error.svg"
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_SIDE = 4096

SUPPORTED_MIME = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    mime_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    warnings: tuple[str, ...] = ()


def inspect_image(path: Path, max_bytes: int = DEFAULT_MAX_BYTES, max_side: int = DEFAULT_MAX_SIDE) -> ImageInfo:
    """Validate a local screenshot and extract metadata without third-party libraries."""

    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if max_side <= 0:
        raise ValueError("max_side must be positive")

    image_path = Path(path)
    if not image_path.is_file():
        raise FileNotFoundError(f"image not found: {image_path}")

    data = image_path.read_bytes()
    if not data:
        raise ValueError("image file must not be empty")
    if len(data) > max_bytes:
        raise ValueError(f"image is too large: {len(data)} bytes, max {max_bytes} bytes")

    suffix = image_path.suffix.lower()
    mime_type = SUPPORTED_MIME.get(suffix)
    if mime_type is None:
        raise ValueError(f"unsupported image type: {suffix or '<no extension>'}")

    width, height = _read_dimensions(data, suffix)
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    if max(width, height) > max_side:
        raise ValueError(f"image side is too large: {width}x{height}, max side {max_side}")

    warnings = []
    if mime_type == "image/jpeg":
        warnings.append("jpeg_may_contain_exif; strip metadata before production upload")
    if mime_type == "image/svg+xml":
        warnings.append("svg_fixture; use PNG or JPEG for real device screenshots")

    return ImageInfo(
        path=image_path,
        mime_type=mime_type,
        size_bytes=len(data),
        width=width,
        height=height,
        sha256=hashlib.sha256(data).hexdigest(),
        warnings=tuple(warnings),
    )


def build_ticket_payload(
    image_path: Path,
    user_note: str,
    ticket_id: str,
    include_image_data: bool = True,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_side: int = DEFAULT_MAX_SIDE,
) -> dict:
    """Build a model-gateway payload for mobile screenshot triage."""

    if not ticket_id.strip():
        raise ValueError("ticket_id must not be empty")

    info = inspect_image(image_path, max_bytes=max_bytes, max_side=max_side)
    image_data = info.path.read_bytes()
    image_url = _data_url(info.mime_type, image_data) if include_image_data else "<omitted; remove --omit-image-data to include>"

    return {
        "ticket_id": ticket_id.strip(),
        "image": {
            "file_name": info.path.name,
            "mime_type": info.mime_type,
            "size_bytes": info.size_bytes,
            "width": info.width,
            "height": info.height,
            "sha256": info.sha256,
            "warnings": list(info.warnings),
        },
        "mobile_upload_checks": [
            "client uploads to app server, not directly to the model provider",
            "server validates file type, size, and dimensions before model call",
            "production service strips metadata and masks visible personal data before model upload",
            "model output is a draft; creating a ticket still requires user confirmation",
        ],
        "model_request": {
            "model": "multimodal-gateway-placeholder",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You analyze mobile app screenshots for engineering triage. "
                        "Return JSON only and do not infer private user identity."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "请分析这张移动端截图，提取可见错误、影响页面、可能原因和下一步排查动作。"
                                f"用户补充说明：{user_note.strip() or '无'}"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "mobile_screenshot_triage",
                    "schema": expected_output_schema(),
                },
            },
        },
        "expected_output_schema": expected_output_schema(),
    }


def expected_output_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "summary",
            "visible_error",
            "affected_screen",
            "severity",
            "possible_causes",
            "next_steps",
            "needs_human_review",
            "redaction_notes",
        ],
        "properties": {
            "summary": {"type": "string"},
            "visible_error": {"type": "string"},
            "affected_screen": {"type": "string"},
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            "possible_causes": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}},
            "needs_human_review": {"type": "boolean"},
            "redaction_notes": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }


def _read_dimensions(data: bytes, suffix: str) -> tuple[int, int]:
    if suffix == ".png":
        return _png_dimensions(data)
    if suffix in (".jpg", ".jpeg"):
        return _jpeg_dimensions(data)
    if suffix == ".gif":
        if len(data) < 10 or data[:6] not in (b"GIF87a", b"GIF89a"):
            raise ValueError("invalid GIF image")
        return struct.unpack("<HH", data[6:10])
    if suffix == ".svg":
        return _svg_dimensions(data)
    raise ValueError(f"unsupported image type: {suffix}")


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 33 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG image")
    first_chunk_length = struct.unpack(">I", data[8:12])[0]
    first_chunk_type = data[12:16]
    if first_chunk_length != 13 or first_chunk_type != b"IHDR":
        raise ValueError("invalid PNG image: missing IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    expected_crc = struct.unpack(">I", data[29:33])[0]
    actual_crc = zlib.crc32(data[12:29]) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise ValueError("invalid PNG image: IHDR checksum mismatch")
    return width, height


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("invalid JPEG image")

    offset = 2
    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if segment_length < 2:
            raise ValueError("invalid JPEG segment length")
        if marker in start_of_frame_markers:
            if offset + 7 > len(data):
                raise ValueError("invalid JPEG start-of-frame segment")
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        offset += segment_length
    raise ValueError("JPEG dimensions not found")


def _svg_dimensions(data: bytes) -> tuple[int, int]:
    try:
        root = ElementTree.fromstring(data.decode("utf-8"))
    except (UnicodeDecodeError, ElementTree.ParseError) as exc:
        raise ValueError("invalid SVG image") from exc
    if _xml_local_name(root.tag) != "svg":
        raise ValueError("invalid SVG root element")

    width = _svg_length(root.attrib.get("width"))
    height = _svg_length(root.attrib.get("height"))
    if width and height:
        return width, height

    view_box = root.attrib.get("viewBox")
    if view_box:
        try:
            parts = [float(part) for part in re.split(r"[\s,]+", view_box.strip()) if part]
        except ValueError as exc:
            raise ValueError("invalid SVG viewBox") from exc
        if len(parts) == 4:
            return round(parts[2]), round(parts[3])
        raise ValueError("invalid SVG viewBox")
    raise ValueError("SVG dimensions not found")


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _svg_length(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", value)
    return round(float(match.group(1))) if match else None


def _data_url(mime_type: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a multimodal screenshot triage payload.")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE, help="Path to a PNG, JPEG, GIF, or SVG screenshot.")
    parser.add_argument("--note", default="用户反馈登录页一直失败，点击重试无效。", help="User supplied context.")
    parser.add_argument("--ticket-id", default="ticket_demo_001")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-side", type=int, default=DEFAULT_MAX_SIDE)
    parser.add_argument(
        "--omit-image-data",
        action="store_true",
        help="Print the payload shape without embedding the full base64 image data.",
    )
    args = parser.parse_args()

    try:
        payload = build_ticket_payload(
            args.image,
            user_note=args.note,
            ticket_id=args.ticket_id,
            include_image_data=not args.omit_image_data,
            max_bytes=args.max_bytes,
            max_side=args.max_side,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
