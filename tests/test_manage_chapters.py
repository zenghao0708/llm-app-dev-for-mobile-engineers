import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from manage_chapters import chapter_path


class ManageChaptersTest(unittest.TestCase):
    def test_chapter_path_uses_manifest_book_directory(self):
        manifest = ROOT / "books" / "02-ai-coding-mobile-engineers" / "book-manifest.json"

        path = chapter_path(manifest, 15, "release-automation")

        self.assertEqual(
            path,
            "books/02-ai-coding-mobile-engineers/chapters/ch15-release-automation.md",
        )


if __name__ == "__main__":
    unittest.main()
