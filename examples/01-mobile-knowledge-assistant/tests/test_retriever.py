from pathlib import Path
import unittest

from mobile_llm.retriever import LocalRetriever


ROOT = Path(__file__).resolve().parents[1]


class LocalRetrieverTest(unittest.TestCase):
    def test_search_finds_api_key_guidance(self):
        retriever = LocalRetriever.from_directory(ROOT / "data" / "documents")

        results = retriever.search("移动端为什么不能直接保存模型 API Key？")

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].chunk.section, "API Key 管理")

    def test_empty_query_returns_no_results(self):
        retriever = LocalRetriever.from_directory(ROOT / "data" / "documents")

        self.assertEqual(retriever.search("   "), [])


if __name__ == "__main__":
    unittest.main()

