import json
import subprocess
import sys
import tempfile
import unittest
from argparse import ArgumentTypeError
from pathlib import Path

from mobile_llm.retriever import DocumentChunk


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tfidf_vector_search import (
    TfidfVectorIndex,
    _dot,
    _normalize,
    _term_counts,
    _weighted_terms,
    positive_int,
    search_payload,
)


class TfidfVectorSearchTest(unittest.TestCase):
    def test_search_finds_api_key_guidance(self):
        index = TfidfVectorIndex.from_directory(ROOT / "data" / "documents")

        results = index.search("移动端为什么不能直接保存模型 API Key？", top_k=2)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].section, "API Key 管理")
        self.assertGreater(results[0].score, 0)

    def test_payload_exposes_dimension_and_results(self):
        payload = search_payload("移动端隐私权限怎么处理？", ROOT / "data" / "documents", top_k=1)

        self.assertEqual(payload["index_size"], 9)
        self.assertGreater(payload["vector_dimension"], 0)
        self.assertEqual(len(payload["results"]), 1)

    def test_empty_query_returns_no_results(self):
        index = TfidfVectorIndex.from_directory(ROOT / "data" / "documents")

        self.assertEqual(index.search("   "), [])

    def test_repeated_terms_increase_tf_weight(self):
        terms = _term_counts("api api key")
        weighted = _weighted_terms(terms, {"api": 1.0, "key": 1.0})

        self.assertEqual(terms["api"], 2)
        self.assertGreater(weighted["api"], weighted["key"])

    def test_chinese_repeated_bigrams_keep_frequency(self):
        terms = _term_counts("权限权限")

        self.assertEqual(terms["权"], 2)
        self.assertEqual(terms["限"], 2)
        self.assertEqual(terms["权限"], 2)

    def test_normalize_returns_unit_length_vector(self):
        vector = _normalize({"x": 3.0, "y": 4.0})

        norm = sum(value * value for value in vector.values()) ** 0.5
        self.assertAlmostEqual(norm, 1.0)

    def test_dot_uses_sparse_overlap(self):
        self.assertAlmostEqual(_dot({"a": 0.6, "b": 0.8}, {"a": 0.5}), 0.3)

    def test_search_sorts_by_raw_score_before_rounding(self):
        index = TfidfVectorIndex.__new__(TfidfVectorIndex)
        index._chunks = [
            DocumentChunk("lower.md", "Lower", "S", "lower"),
            DocumentChunk("higher.md", "Higher", "S", "higher"),
        ]
        index._idf = {"query": 1.0}
        index.dimension = 1
        index._vectors = [{"query": 0.123441}, {"query": 0.123449}]

        results = index.search("query", top_k=2)

        self.assertEqual(results[0].source, "higher.md")
        self.assertEqual(results[0].score, results[1].score)

    def test_top_k_must_be_positive(self):
        index = TfidfVectorIndex.from_directory(ROOT / "data" / "documents")

        with self.assertRaises(ValueError):
            index.search("hello", top_k=0)
        with self.assertRaises(ArgumentTypeError):
            positive_int("0")

    def test_rejects_empty_docs_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                TfidfVectorIndex.from_directory(Path(temp_dir))

    def test_cli_outputs_json_results(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "tfidf_vector_search.py"),
                "--question",
                "移动端为什么不能直接保存模型 API Key？",
                "--top-k",
                "1",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["results"][0]["section"], "API Key 管理")

    def test_cli_reports_missing_docs_dir(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "tfidf_vector_search.py"),
                "--question",
                "hello",
                "--docs-dir",
                str(ROOT / "missing-docs"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docs_dir not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
