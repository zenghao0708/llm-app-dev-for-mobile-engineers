from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manuscript" / "book-manifest.json"
DEFAULT_OUTPUT = ROOT / "build" / "ebooks" / "llm-app-dev-for-mobile-engineers.epub"

BLOCK_START_RE = re.compile(r"^(#{1,6})\s+|^```|^\s*$|^\s*[-*]\s+|^\s*\d+\.\s+|^\|")
INLINE_LINK_RE = re.compile(r"(!?\[([^\]\n]*)]\(([^)\n]+)\))")
AUTO_LINK_RE = re.compile(r"&lt;(https?://[^&\s]+)&gt;")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
STRONG_RE = re.compile(r"\*\*([^*\n]+)\*\*")
EM_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
FOOTNOTE_USE_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)]")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([A-Za-z0-9_-]+)]:\s*(.*)$")


@dataclass
class SourceItem:
    item_id: str
    title: str
    item_type: str
    source_path: Path
    href: str


@dataclass
class Heading:
    level: int
    title: str
    href: str
    anchor: str


@dataclass
class Asset:
    source: Path
    href: str
    media_type: str


class EpubBuilder:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path.resolve()
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.items = self._load_items()
        self.assets: dict[Path, Asset] = {}
        self.source_to_href = {item.source_path.resolve(): item.href for item in self.items}
        self.headings_by_item: dict[str, list[Heading]] = {}
        self.book_uuid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, self.manifest['title'])}"

    def build(self) -> dict[str, int | str]:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            stage = Path(temp_dir)
            self._write_static_files(stage)
            for item in self.items:
                self._write_xhtml_item(stage, item)
            self._copy_assets(stage)
            self._write_nav(stage)
            self._write_ncx(stage)
            self._write_opf(stage)
            self._zip_epub(stage)
        return {
            "output": str(self.output_path),
            "sources": len(self.items),
            "assets": len(self.assets),
        }

    def _load_items(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        for index, raw_item in enumerate(self.manifest["source_order"], start=1):
            relative_path = raw_item["path"]
            source_path = (ROOT / relative_path).resolve()
            try:
                source_path.relative_to(ROOT)
            except ValueError as exc:
                raise ValueError(f"Manifest path escapes repository: {relative_path}") from exc
            if not source_path.is_file():
                raise FileNotFoundError(f"Missing source file: {relative_path}")

            item_id = raw_item.get("id") or f"section-{index:03d}"
            href = f"text/{safe_id(item_id)}.xhtml"
            items.append(
                SourceItem(
                    item_id=safe_id(item_id),
                    title=str(raw_item.get("title") or item_id),
                    item_type=str(raw_item.get("type") or "section"),
                    source_path=source_path,
                    href=href,
                )
            )
        return items

    def _write_static_files(self, stage: Path) -> None:
        (stage / "META-INF").mkdir(parents=True, exist_ok=True)
        (stage / "EPUB" / "text").mkdir(parents=True, exist_ok=True)
        (stage / "EPUB" / "styles").mkdir(parents=True, exist_ok=True)
        (stage / "mimetype").write_text("application/epub+zip", encoding="utf-8")
        (stage / "META-INF" / "container.xml").write_text(CONTAINER_XML, encoding="utf-8")
        (stage / "EPUB" / "styles" / "book.css").write_text(CSS, encoding="utf-8")

    def _write_xhtml_item(self, stage: Path, item: SourceItem) -> None:
        source_text = item.source_path.read_text(encoding="utf-8")
        body, headings = markdown_to_xhtml(
            source_text,
            item,
            lambda target: self._resolve_href(target, item),
            lambda target: self._resolve_image(target, item),
        )
        self.headings_by_item[item.item_id] = headings
        title = html.escape(item.title)
        xhtml = XHTML_TEMPLATE.format(title=title, body=body)
        output = stage / "EPUB" / item.href
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(xhtml, encoding="utf-8")

    def _resolve_href(self, target: str, item: SourceItem) -> str:
        clean_target, fragment = split_target(target)
        if is_external_or_anchor(clean_target):
            return target
        if not clean_target:
            return f"#{fragment}" if fragment else target

        source_target = (item.source_path.parent / clean_target).resolve()
        if source_target.suffix.lower() == ".md" and source_target in self.source_to_href:
            href = os.path.relpath(
                (Path("EPUB") / self.source_to_href[source_target]),
                (Path("EPUB") / item.href).parent,
            ).replace(os.sep, "/")
            return f"{href}#{fragment}" if fragment else href
        if source_target.exists():
            asset = self._register_asset(source_target)
            href = os.path.relpath(
                (Path("EPUB") / asset.href),
                (Path("EPUB") / item.href).parent,
            ).replace(os.sep, "/")
            return f"{href}#{fragment}" if fragment else href
        return target

    def _resolve_image(self, target: str, item: SourceItem) -> str:
        clean_target, fragment = split_target(target)
        if is_external_or_anchor(clean_target):
            return target
        source_target = (item.source_path.parent / clean_target).resolve()
        if not source_target.is_file():
            raise FileNotFoundError(f"Broken image link in {item.source_path}: {target}")
        asset = self._register_asset(source_target)
        href = os.path.relpath(
            (Path("EPUB") / asset.href),
            (Path("EPUB") / item.href).parent,
        ).replace(os.sep, "/")
        return f"{href}#{fragment}" if fragment else href

    def _register_asset(self, source_path: Path) -> Asset:
        source_path = source_path.resolve()
        if source_path in self.assets:
            return self.assets[source_path]
        relative = source_path.relative_to(ROOT).as_posix()
        href = f"assets/{relative}"
        media_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
        if source_path.suffix.lower() == ".svg":
            media_type = "image/svg+xml"
        asset = Asset(source=source_path, href=href, media_type=media_type)
        self.assets[source_path] = asset
        return asset

    def _copy_assets(self, stage: Path) -> None:
        for asset in self.assets.values():
            output = stage / "EPUB" / asset.href
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(asset.source, output)

    def _write_nav(self, stage: Path) -> None:
        nav_items = []
        for item in self.items:
            headings = self.headings_by_item.get(item.item_id, [])
            title = headings[0].title if headings else item.title
            nav_items.append(render_nav_item(title, item.href, headings[1:]))
        content = NAV_TEMPLATE.format(
            title=html.escape(self.manifest["title"]),
            nav_items="\n".join(nav_items),
        )
        (stage / "EPUB" / "nav.xhtml").write_text(content, encoding="utf-8")

    def _write_ncx(self, stage: Path) -> None:
        nav_points: list[str] = []
        play_order = 1
        for item in self.items:
            headings = self.headings_by_item.get(item.item_id, [])
            title = headings[0].title if headings else item.title
            nav_points.append(render_ncx_point(f"nav-{play_order}", play_order, title, item.href))
            play_order += 1
        content = NCX_TEMPLATE.format(
            uuid=html.escape(self.book_uuid),
            title=html.escape(self.manifest["title"]),
            nav_points="\n".join(nav_points),
        )
        (stage / "EPUB" / "toc.ncx").write_text(content, encoding="utf-8")

    def _write_opf(self, stage: Path) -> None:
        manifest_entries = [
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
            '<item id="style" href="styles/book.css" media-type="text/css"/>',
        ]
        spine_entries = []
        for item in self.items:
            manifest_entries.append(
                f'<item id="{item.item_id}" href="{html.escape(item.href)}" media-type="application/xhtml+xml"/>'
            )
            spine_entries.append(f'<itemref idref="{item.item_id}"/>')
        for index, asset in enumerate(self.assets.values(), start=1):
            manifest_entries.append(
                f'<item id="asset-{index}" href="{html.escape(asset.href)}" media-type="{asset.media_type}"/>'
            )

        content = OPF_TEMPLATE.format(
            uuid=html.escape(self.book_uuid),
            title=html.escape(self.manifest["title"]),
            subtitle=html.escape(self.manifest.get("subtitle", "")),
            manifest="\n    ".join(manifest_entries),
            spine="\n    ".join(spine_entries),
        )
        (stage / "EPUB" / "content.opf").write_text(content, encoding="utf-8")

    def _zip_epub(self, stage: Path) -> None:
        if self.output_path.exists():
            self.output_path.unlink()
        with zipfile.ZipFile(self.output_path, "w") as archive:
            archive.write(stage / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
            for path in sorted(stage.rglob("*")):
                if path.is_dir() or path.name == "mimetype":
                    continue
                archive.write(path, path.relative_to(stage).as_posix(), compress_type=zipfile.ZIP_DEFLATED)


def markdown_to_xhtml(
    text: str,
    item: SourceItem,
    resolve_href: Callable[[str], str],
    resolve_image: Callable[[str], str],
) -> tuple[str, list[Heading]]:
    lines = text.splitlines()
    output: list[str] = []
    headings: list[Heading] = []
    heading_ids: dict[str, int] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        if line.startswith("```"):
            code_lines: list[str] = []
            language = line.strip().strip("`").strip()
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            class_name = f' class="language-{html.escape(language)}"' if language else ""
            code = html.escape("\n".join(code_lines))
            output.append(f"<pre><code{class_name}>{code}</code></pre>")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            anchor = unique_heading_id(item.item_id, title, heading_ids)
            headings.append(Heading(level=level, title=strip_inline_markup(title), href=item.href, anchor=anchor))
            output.append(
                f'<h{level} id="{html.escape(anchor)}">{inline_html(title, resolve_href, resolve_image)}</h{level}>'
            )
            index += 1
            continue

        if is_table_start(lines, index):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            output.append(render_table(table_lines, resolve_href, resolve_image))
            continue

        if re.match(r"^\s*[-*]\s+", line):
            list_lines: list[str] = []
            while index < len(lines) and re.match(r"^\s*[-*]\s+", lines[index]):
                list_lines.append(re.sub(r"^\s*[-*]\s+", "", lines[index]).strip())
                index += 1
            output.append(render_list("ul", list_lines, resolve_href, resolve_image))
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            list_lines = []
            while index < len(lines) and re.match(r"^\s*\d+\.\s+", lines[index]):
                list_lines.append(re.sub(r"^\s*\d+\.\s+", "", lines[index]).strip())
                index += 1
            output.append(render_list("ol", list_lines, resolve_href, resolve_image))
            continue

        footnote_match = FOOTNOTE_DEF_RE.match(line)
        if footnote_match:
            note_id = safe_id(footnote_match.group(1))
            note = inline_html(footnote_match.group(2), resolve_href, resolve_image)
            output.append(f'<aside epub:type="footnote" id="fn-{note_id}"><p>{note}</p></aside>')
            index += 1
            continue

        paragraph_lines = [line.rstrip()]
        index += 1
        while index < len(lines) and not BLOCK_START_RE.match(lines[index]):
            paragraph_lines.append(lines[index].rstrip())
            index += 1
        paragraph = join_paragraph_lines(paragraph_lines)
        output.append(f"<p>{inline_html(paragraph, resolve_href, resolve_image)}</p>")

    if not headings:
        anchor = unique_heading_id(item.item_id, item.title, {})
        headings.append(Heading(level=1, title=item.title, href=item.href, anchor=anchor))
    return "\n".join(output), headings


def inline_html(
    text: str,
    resolve_href: Callable[[str], str],
    resolve_image: Callable[[str], str],
) -> str:
    parts: list[str] = []
    position = 0
    for match in INLINE_LINK_RE.finditer(text):
        parts.append(inline_text(text[position:match.start()]))
        full, label, target = match.groups()
        if full.startswith("!"):
            src = html.escape(resolve_image(clean_markdown_target(target)))
            alt = html.escape(strip_inline_markup(label))
            parts.append(f'<img src="{src}" alt="{alt}"/>')
        else:
            href = html.escape(resolve_href(clean_markdown_target(target)))
            parts.append(f'<a href="{href}">{inline_text(label)}</a>')
        position = match.end()
    parts.append(inline_text(text[position:]))
    return "".join(parts)


def inline_text(text: str) -> str:
    placeholders: list[str] = []

    def hold_code(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"@@CODE{len(placeholders) - 1}@@"

    escaped = html.escape(CODE_SPAN_RE.sub(hold_code, text))
    escaped = AUTO_LINK_RE.sub(r'<a href="\1">\1</a>', escaped)
    escaped = FOOTNOTE_USE_RE.sub(lambda match: render_footnote_ref(match), escaped)
    escaped = STRONG_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = EM_RE.sub(r"<em>\1</em>", escaped)
    escaped = escaped.replace("&lt;br/&gt;", "<br/>")
    for index, value in enumerate(placeholders):
        escaped = escaped.replace(f"@@CODE{index}@@", value)
    return escaped


def render_footnote_ref(match: re.Match[str]) -> str:
    note_id = safe_id(match.group(1))
    return f'<a epub:type="noteref" href="#fn-{note_id}" id="fnref-{note_id}">[{html.escape(match.group(1))}]</a>'


def render_list(tag: str, items: list[str], resolve_href: Callable[[str], str], resolve_image: Callable[[str], str]) -> str:
    body = "\n".join(f"<li>{inline_html(item, resolve_href, resolve_image)}</li>" for item in items)
    return f"<{tag}>\n{body}\n</{tag}>"


def is_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and lines[index].lstrip().startswith("|")
        and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]) is not None
    )


def render_table(
    lines: list[str],
    resolve_href: Callable[[str], str],
    resolve_image: Callable[[str], str],
) -> str:
    header = split_table_row(lines[0])
    body_rows = [split_table_row(line) for line in lines[2:]]
    header_html = "".join(f"<th>{inline_html(cell, resolve_href, resolve_image)}</th>" for cell in header)
    rows_html = []
    for row in body_rows:
        rows_html.append("".join(f"<td>{inline_html(cell, resolve_href, resolve_image)}</td>" for cell in row))
    body_html = "\n".join(f"<tr>{row}</tr>" for row in rows_html)
    return f"<table>\n<thead><tr>{header_html}</tr></thead>\n<tbody>\n{body_html}\n</tbody>\n</table>"


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def join_paragraph_lines(lines: list[str]) -> str:
    result = ""
    for line in lines:
        if line.endswith("  "):
            result += line.rstrip() + "<br/>"
        else:
            result += (" " if result and not result.endswith("<br/>") else "") + line.strip()
    return result


def clean_markdown_target(target: str) -> str:
    target = target.strip()
    if (target.startswith("<") and ">" in target) or " " in target:
        if target.startswith("<"):
            return target[1 : target.find(">")]
        return target.split(maxsplit=1)[0]
    return target


def split_target(target: str) -> tuple[str, str]:
    target = target.strip()
    if "#" not in target:
        return target, ""
    path, fragment = target.split("#", 1)
    return path, fragment


def is_external_or_anchor(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "#"))


def unique_heading_id(item_id: str, title: str, used: dict[str, int]) -> str:
    base = f"{item_id}-{slugify(title)}"
    count = used.get(base, 0)
    used[base] = count + 1
    return base if count == 0 else f"{base}-{count + 1}"


def slugify(text: str) -> str:
    text = strip_inline_markup(text).casefold()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    text = text.strip("-_")
    return text or "section"


def safe_id(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")
    return value or "item"


def strip_inline_markup(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text


def render_nav_item(title: str, href: str, headings: list[Heading]) -> str:
    child_items = []
    for heading in headings:
        if heading.level <= 3:
            child_items.append(
                f'<li><a href="{html.escape(heading.href)}#{html.escape(heading.anchor)}">{html.escape(heading.title)}</a></li>'
            )
    children = f"\n<ol>{''.join(child_items)}</ol>" if child_items else ""
    return f'<li><a href="{html.escape(href)}">{html.escape(title)}</a>{children}</li>'


def render_ncx_point(point_id: str, play_order: int, title: str, href: str) -> str:
    return (
        f'<navPoint id="{point_id}" playOrder="{play_order}">'
        f"<navLabel><text>{html.escape(title)}</text></navLabel>"
        f'<content src="{html.escape(href)}"/>'
        "</navPoint>"
    )


CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

XHTML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="../styles/book.css"/>
</head>
<body>
{body}
</body>
</html>
"""

NAV_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="styles/book.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>目录</h1>
    <ol>
{nav_items}
    </ol>
  </nav>
</body>
</html>
"""

NCX_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uuid}"/>
    <meta name="dtb:depth" content="2"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
{nav_points}
  </navMap>
</ncx>
"""

OPF_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{uuid}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:description>{subtitle}</dc:description>
    <dc:language>zh-CN</dc:language>
    <dc:creator>zenghao0708</dc:creator>
    <dc:publisher>GitHub</dc:publisher>
    <meta property="dcterms:modified">2026-06-22T00:00:00Z</meta>
  </metadata>
  <manifest>
    {manifest}
  </manifest>
  <spine toc="toc">
    {spine}
  </spine>
</package>
"""

CSS = """
body {
  color: #172033;
  font-family: serif;
  line-height: 1.72;
}
h1, h2, h3, h4, h5, h6 {
  color: #111827;
  font-family: sans-serif;
  line-height: 1.32;
  margin: 1.4em 0 0.65em;
}
p {
  margin: 0.75em 0;
}
a {
  color: #0f6ca8;
}
pre {
  background: #f4f7fb;
  border: 1px solid #d7e0ea;
  border-radius: 6px;
  font-size: 0.86em;
  line-height: 1.5;
  overflow-wrap: break-word;
  padding: 0.85em;
  white-space: pre-wrap;
}
code {
  font-family: monospace;
}
p code, li code, td code {
  background: #f4f7fb;
  border-radius: 4px;
  padding: 0.05em 0.25em;
}
table {
  border-collapse: collapse;
  font-size: 0.9em;
  margin: 1em 0;
  width: 100%;
}
th, td {
  border: 1px solid #cfd8e3;
  padding: 0.45em 0.55em;
  vertical-align: top;
}
th {
  background: #eef4f9;
}
img {
  display: block;
  height: auto;
  margin: 1em auto;
  max-width: 100%;
}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an EPUB 3 ebook from manuscript/book-manifest.json.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = EpubBuilder(args.output).build()
    print(f"built {result['output']}")
    print(f"sources {result['sources']}")
    print(f"assets {result['assets']}")


if __name__ == "__main__":
    main()
