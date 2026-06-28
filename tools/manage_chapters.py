from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "books" / "01-llm-app-dev-for-mobile-engineers" / "book-manifest.json"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(manifest: dict[str, Any], path: Path = MANIFEST_PATH) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chapter_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in manifest["source_order"] if item.get("type") == "chapter"]


def find_chapter(manifest: dict[str, Any], identifier: str) -> dict[str, Any]:
    chapters = chapter_items(manifest)
    for item in chapters:
        if item.get("id") == identifier or str(item.get("number")) == identifier:
            return item
    raise ValueError(f"Chapter not found: {identifier}")


def chapter_path(manifest_path: Path, number: int, slug: str) -> str:
    book_dir = manifest_path.resolve().parent
    try:
        relative_book_dir = book_dir.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"Manifest must be inside repository: {manifest_path}") from exc
    return f"{relative_book_dir.as_posix()}/chapters/ch{number:02d}-{slug}.md"


def validate_slug(slug: str) -> None:
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("Slug must use lowercase letters, digits, and hyphens, for example: on-device-llm")


def command_list(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    for item in chapter_items(manifest):
        print(f"{item['number']:02d}\t{item['id']}\t{item['title']}\t{item['path']}")
    return 0


def command_show(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    item = find_chapter(manifest, args.identifier)
    print(json.dumps(item, ensure_ascii=False, indent=2))
    return 0


def command_add(args: argparse.Namespace) -> int:
    validate_slug(args.slug)
    manifest = load_manifest(args.manifest)
    number = args.number
    if any(item.get("number") == number for item in chapter_items(manifest)):
        raise ValueError(f"Chapter number already exists: {number}")

    relative_path = chapter_path(args.manifest, number, args.slug)
    absolute_path = ROOT / relative_path
    if absolute_path.exists():
        raise FileExistsError(f"Chapter file already exists: {relative_path}")

    item = {
        "id": f"ch{number:02d}-{args.slug}",
        "type": "chapter",
        "number": number,
        "part": args.part,
        "title": args.title,
        "path": relative_path,
    }
    source_order = manifest["source_order"]
    insert_at = next(
        (
            index
            for index, existing in enumerate(source_order)
            if existing.get("type") == "chapter" and int(existing.get("number", 0)) > number
        ),
        None,
    )
    if insert_at is None:
        insert_at = next(
            (index for index, existing in enumerate(source_order) if existing.get("type") == "back-matter"),
            len(source_order),
        )
    source_order.insert(insert_at, item)

    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(chapter_template(number, args.title), encoding="utf-8")
    save_manifest(manifest, args.manifest)
    print(f"added {relative_path}")
    return 0


def command_rename(args: argparse.Namespace) -> int:
    if args.slug:
        validate_slug(args.slug)
    manifest = load_manifest(args.manifest)
    item = find_chapter(manifest, args.identifier)
    number = int(item["number"])
    old_path = ROOT / item["path"]

    if args.title:
        item["title"] = args.title
    if args.slug:
        new_relative_path = chapter_path(args.manifest, number, args.slug)
        new_path = ROOT / new_relative_path
        if new_path.exists() and new_path != old_path:
            raise FileExistsError(f"Chapter file already exists: {new_relative_path}")
        if old_path.exists() and new_path != old_path:
            old_path.rename(new_path)
        item["id"] = f"ch{number:02d}-{args.slug}"
        item["path"] = new_relative_path

    final_path = ROOT / item["path"]
    if final_path.exists():
        replace_heading(final_path, number, str(item["title"]))
    save_manifest(manifest, args.manifest)
    print(f"renamed chapter {number:02d}")
    return 0


def command_remove(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    item = find_chapter(manifest, args.identifier)
    manifest["source_order"].remove(item)
    path = ROOT / item["path"]
    if args.delete_file and path.exists():
        path.unlink()
    save_manifest(manifest, args.manifest)
    print(f"removed {item['id']} from manifest")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"manifest ok: {len(manifest['source_order'])} source files, {len(chapter_items(manifest))} chapters")
    return 0


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_order = manifest.get("source_order")
    if not isinstance(source_order, list) or not source_order:
        return ["source_order must be a non-empty list"]

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_numbers: set[int] = set()
    for index, item in enumerate(source_order, start=1):
        if not isinstance(item, dict):
            errors.append(f"item #{index} must be an object")
            continue
        item_id = item.get("id")
        item_type = item.get("type")
        item_path = item.get("path")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"item #{index} has an invalid id")
        elif item_id in seen_ids:
            errors.append(f"duplicate id: {item_id}")
        else:
            seen_ids.add(item_id)

        if item_type not in {"front-matter", "contents", "chapter", "back-matter"}:
            errors.append(f"item #{index} has an invalid type: {item_type}")

        if not isinstance(item_path, str) or not item_path:
            errors.append(f"item #{index} has an invalid path")
            continue
        if item_path in seen_paths:
            errors.append(f"duplicate path: {item_path}")
        seen_paths.add(item_path)

        resolved_path = (ROOT / item_path).resolve()
        try:
            resolved_path.relative_to(ROOT)
        except ValueError:
            errors.append(f"path escapes repository: {item_path}")
            continue
        if not resolved_path.is_file():
            errors.append(f"missing source file: {item_path}")

        if item_type == "chapter":
            number = item.get("number")
            title = item.get("title")
            if not isinstance(number, int) or number <= 0:
                errors.append(f"chapter {item_id} has an invalid number")
            elif number in seen_numbers:
                errors.append(f"duplicate chapter number: {number}")
            else:
                seen_numbers.add(number)
            if not isinstance(title, str) or not title:
                errors.append(f"chapter {item_id} has an invalid title")
    return errors


def chapter_template(number: int, title: str) -> str:
    return (
        f"# 第 {number} 章 {title}\n\n"
        "## 本章目标\n\n"
        "- 说明本章要解决的移动端工程问题。\n"
        "- 给出可运行示例对应的脚本或模块路径。\n"
        "- 总结上线前需要验证的边界。\n\n"
        "## 移动端场景\n\n"
        "说明这个主题在 iOS、Android、Flutter 或 React Native 应用中的典型入口。\n\n"
        "## 核心概念\n\n"
        "先解释工程问题，再引入大模型相关概念。\n\n"
        "## 可运行示例\n\n"
        "补充配套工程中的命令、输入、输出和关键注释。\n\n"
        "## 小结\n\n"
        "用工程检查清单收束本章内容。\n"
    )


def replace_heading(path: Path, number: int, title: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            lines[index] = f"# 第 {number} 章 {title}"
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage book chapters through books/01-llm-app-dev-for-mobile-engineers/book-manifest.json.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List chapters in manifest order.")
    list_parser.set_defaults(func=command_list)

    show_parser = subparsers.add_parser("show", help="Show one chapter entry.")
    show_parser.add_argument("identifier", help="Chapter id or number.")
    show_parser.set_defaults(func=command_show)

    add_parser = subparsers.add_parser("add", help="Add a chapter file and manifest entry.")
    add_parser.add_argument("--number", type=int, required=True)
    add_parser.add_argument("--slug", required=True)
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--part", default="")
    add_parser.set_defaults(func=command_add)

    rename_parser = subparsers.add_parser("rename", help="Rename a chapter title and optionally its slug.")
    rename_parser.add_argument("identifier", help="Chapter id or number.")
    rename_parser.add_argument("--title")
    rename_parser.add_argument("--slug")
    rename_parser.set_defaults(func=command_rename)

    remove_parser = subparsers.add_parser("remove", help="Remove a chapter from manifest.")
    remove_parser.add_argument("identifier", help="Chapter id or number.")
    remove_parser.add_argument("--delete-file", action="store_true", help="Also delete the Markdown file.")
    remove_parser.set_defaults(func=command_remove)

    validate_parser = subparsers.add_parser("validate", help="Validate manifest paths and chapter metadata.")
    validate_parser.set_defaults(func=command_validate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
