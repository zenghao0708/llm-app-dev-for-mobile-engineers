import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_book import _load_book_files, _rewrite_relative_links


class BuildBookLinkTest(unittest.TestCase):
    def test_load_book_files_reads_manifest_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                '{"source_order":[{"path":"books/01-llm-app-dev-for-mobile-engineers/a.md"},{"path":"books/01-llm-app-dev-for-mobile-engineers/b.md"}]}',
                encoding="utf-8",
            )

            book_files = _load_book_files(manifest_path=manifest_path, root=root)

        self.assertEqual(book_files, ["books/01-llm-app-dev-for-mobile-engineers/a.md", "books/01-llm-app-dev-for-mobile-engineers/b.md"])

    def test_manifest_path_escaping_root_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                '{"source_order":[{"path":"../outside.md"}]}',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                _load_book_files(manifest_path=manifest_path, root=root)

    def test_rewrites_inline_link_with_title(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "books/01-llm-app-dev-for-mobile-engineers" / "chapter.md"
            target = root / "books/01-llm-app-dev-for-mobile-engineers" / "assets" / "diagram.svg"
            output = root / "build" / "book.md"
            target.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<svg/>", encoding="utf-8")
            source.write_text("", encoding="utf-8")

            rewritten = _rewrite_relative_links(
                '[图](assets/diagram.svg "架构图")',
                source,
                output,
                root=root,
            )

        self.assertEqual(rewritten, '[图](../books/01-llm-app-dev-for-mobile-engineers/assets/diagram.svg "架构图")')

    def test_missing_inline_link_with_title_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output = _source_and_output(Path(temp_dir))
            with self.assertRaises(FileNotFoundError):
                _rewrite_relative_links(
                    '[坏链接](missing.md "title")',
                    source,
                    output,
                    root=Path(temp_dir),
                )

    def test_missing_angle_link_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output = _source_and_output(Path(temp_dir))
            with self.assertRaises(FileNotFoundError):
                _rewrite_relative_links(
                    '[坏链接](<missing file.md>)',
                    source,
                    output,
                    root=Path(temp_dir),
                )

    def test_missing_reference_definition_target_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output = _source_and_output(Path(temp_dir))
            with self.assertRaises(FileNotFoundError):
                _rewrite_relative_links(
                    '[资料][ref]\n\n[ref]: missing.md "title"',
                    source,
                    output,
                    root=Path(temp_dir),
                )

    def test_undefined_reference_use_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output = _source_and_output(Path(temp_dir))
            with self.assertRaises(ValueError):
                _rewrite_relative_links(
                    '[资料][ref]',
                    source,
                    output,
                    root=Path(temp_dir),
                )

    def test_absolute_local_path_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output = _source_and_output(Path(temp_dir))
            with self.assertRaises(ValueError):
                _rewrite_relative_links(
                    '[本地文件](/tmp/secret.png)',
                    source,
                    output,
                    root=Path(temp_dir),
                )

    def test_relative_link_escaping_root_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            outside = Path(temp_dir) / "outside.md"
            source, output = _source_and_output(root)
            outside.write_text("outside", encoding="utf-8")
            with self.assertRaises(ValueError):
                _rewrite_relative_links(
                    '[越界](../../../outside.md)',
                    source,
                    output,
                    root=root,
                )

    def test_reference_definition_is_rewritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "books/01-llm-app-dev-for-mobile-engineers" / "chapter.md"
            target = root / "books/01-llm-app-dev-for-mobile-engineers" / "assets" / "diagram.svg"
            output = root / "build" / "book.md"
            target.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<svg/>", encoding="utf-8")

            rewritten = _rewrite_relative_links(
                '[资料][ref]\n\n[ref]: <assets/diagram.svg> "架构图"',
                source,
                output,
                root=root,
            )

        self.assertIn('[ref]: <../books/01-llm-app-dev-for-mobile-engineers/assets/diagram.svg> "架构图"', rewritten)


def _source_and_output(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "books/01-llm-app-dev-for-mobile-engineers" / "chapter.md"
    output = root / "build" / "book.md"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    return source, output


if __name__ == "__main__":
    unittest.main()
