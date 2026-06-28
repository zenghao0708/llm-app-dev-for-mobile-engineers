import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_epub import SourceItem, markdown_to_xhtml


class MarkdownToXhtmlTest(unittest.TestCase):
    def test_renders_blockquote_callout(self):
        item = SourceItem(
            item_id="chapter",
            title="Chapter",
            item_type="chapter",
            source_path=ROOT / "manuscript" / "chapter.md",
            href="text/chapter.xhtml",
        )

        body, _ = markdown_to_xhtml(
            "> **重点提示**：移动端不能保存模型 Key。",
            item,
            lambda target: target,
            lambda target: target,
        )

        self.assertIn("<blockquote>", body)
        self.assertIn("<strong>重点提示</strong>", body)
        self.assertIn("移动端不能保存模型 Key。", body)


if __name__ == "__main__":
    unittest.main()
