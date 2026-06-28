import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from image_ticket_payload import build_ticket_payload, expected_output_schema, inspect_image


class ImageTicketPayloadTest(unittest.TestCase):
    def test_inspect_default_svg_fixture(self):
        info = inspect_image(ROOT / "data" / "multimodal" / "login_error.svg")

        self.assertEqual(info.mime_type, "image/svg+xml")
        self.assertEqual(info.width, 390)
        self.assertEqual(info.height, 844)
        self.assertTrue(info.sha256)
        self.assertIn("svg_fixture", info.warnings[0])

    def test_inspect_png_dimensions_without_third_party_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.png"
            image_path.write_bytes(_png_image(width=320, height=640))

            info = inspect_image(image_path)

        self.assertEqual(info.mime_type, "image/png")
        self.assertEqual((info.width, info.height), (320, 640))

    def test_inspect_jpeg_dimensions_and_metadata_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.jpg"
            image_path.write_bytes(_jpeg_image(width=120, height=240))

            info = inspect_image(image_path)

        self.assertEqual(info.mime_type, "image/jpeg")
        self.assertEqual((info.width, info.height), (120, 240))
        self.assertIn("jpeg_may_contain_exif", info.warnings[0])

    def test_inspect_gif_dimensions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.gif"
            image_path.write_bytes(b"GIF89a" + struct.pack("<HH", 88, 99) + b"\x00\x00\x00")

            info = inspect_image(image_path)

        self.assertEqual(info.mime_type, "image/gif")
        self.assertEqual((info.width, info.height), (88, 99))

    def test_inspect_svg_viewbox_dimensions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.svg"
            image_path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 500"></svg>', encoding="utf-8")

            info = inspect_image(image_path)

        self.assertEqual((info.width, info.height), (300, 500))

    def test_rejects_unsupported_file_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.txt"
            image_path.write_text("not an image", encoding="utf-8")

            with self.assertRaises(ValueError):
                inspect_image(image_path)

    def test_rejects_oversized_upload_before_payload_build(self):
        with self.assertRaises(ValueError):
            inspect_image(ROOT / "data" / "multimodal" / "login_error.svg", max_bytes=10)

    def test_rejects_empty_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "empty.png"
            image_path.write_bytes(b"")

            with self.assertRaises(ValueError):
                inspect_image(image_path)

    def test_rejects_non_positive_limits(self):
        image_path = ROOT / "data" / "multimodal" / "login_error.svg"

        with self.assertRaises(ValueError):
            inspect_image(image_path, max_bytes=0)
        with self.assertRaises(ValueError):
            inspect_image(image_path, max_side=0)

    def test_rejects_image_side_above_limit(self):
        with self.assertRaises(ValueError):
            inspect_image(ROOT / "data" / "multimodal" / "login_error.svg", max_side=100)

    def test_rejects_malformed_png_missing_ihdr(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "bad.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + _png_chunk(b"tEXt", b"bad"))

            with self.assertRaises(ValueError):
                inspect_image(image_path)

    def test_rejects_png_with_bad_ihdr_checksum(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "bad.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 10, 20) + b"\x08\x02\x00\x00\x00" + b"\x00\x00\x00\x00")

            with self.assertRaises(ValueError):
                inspect_image(image_path)

    def test_rejects_non_svg_xml_with_svg_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "bad.svg"
            image_path.write_text("<notsvg width=\"10\" height=\"10\"></notsvg>", encoding="utf-8")

            with self.assertRaises(ValueError):
                inspect_image(image_path)

    def test_rejects_invalid_svg_viewbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "bad.svg"
            image_path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 nope 10"></svg>', encoding="utf-8")

            with self.assertRaises(ValueError):
                inspect_image(image_path)

    def test_build_payload_rejects_empty_ticket_id(self):
        with self.assertRaises(ValueError):
            build_ticket_payload(
                ROOT / "data" / "multimodal" / "login_error.svg",
                user_note="登录页点击重试无效",
                ticket_id=" ",
            )

    def test_build_payload_contains_model_request_and_schema(self):
        payload = build_ticket_payload(
            ROOT / "data" / "multimodal" / "login_error.svg",
            user_note="登录页点击重试无效",
            ticket_id="ticket_001",
        )

        image_url = payload["model_request"]["messages"][1]["content"][1]["image_url"]["url"]
        self.assertEqual(payload["ticket_id"], "ticket_001")
        self.assertTrue(image_url.startswith("data:image/svg+xml;base64,"))
        self.assertIn("mobile_screenshot_triage", payload["model_request"]["response_format"]["json_schema"]["name"])
        self.assertEqual(payload["expected_output_schema"], expected_output_schema())

    def test_cli_outputs_payload_shape_without_image_data(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "image_ticket_payload.py"),
                "--omit-image-data",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        image_url = payload["model_request"]["messages"][1]["content"][1]["image_url"]["url"]
        self.assertEqual(image_url, "<omitted; remove --omit-image-data to include>")
        self.assertEqual(payload["image"]["width"], 390)

    def test_cli_reports_invalid_image_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "bad.png"
            image_path.write_bytes(b"not a real png")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "image_ticket_payload.py"),
                    "--image",
                    str(image_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid PNG image", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_reports_missing_file_without_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "image_ticket_payload.py"),
                "--image",
                str(ROOT / "missing.png"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("image not found", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


def _png_image(width: int, height: int) -> bytes:
    raw_rows = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00")
        + _png_chunk(b"IDAT", zlib.compress(raw_rows))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _jpeg_image(width: int, height: int) -> bytes:
    sof_payload = b"\x08" + struct.pack(">HH", height, width) + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    return b"\xff\xd8" + b"\xff\xc0" + struct.pack(">H", len(sof_payload) + 2) + sof_payload + b"\xff\xd9"


if __name__ == "__main__":
    unittest.main()
