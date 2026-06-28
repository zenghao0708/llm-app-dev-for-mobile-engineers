from pathlib import Path
import unittest

from mobile_llm.providers import MockLLMProvider
from mobile_llm.retriever import LocalRetriever
from mobile_llm.service import KnowledgeAssistant


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeAssistantTest(unittest.TestCase):
    def test_answer_contains_citations(self):
        retriever = LocalRetriever.from_directory(ROOT / "data" / "documents")
        service = KnowledgeAssistant(retriever, MockLLMProvider())

        result = service.answer("如何处理移动端流式输出？")

        self.assertIn("answer", result)
        self.assertGreater(len(result["citations"]), 0)
        self.assertIn("source", result["citations"][0])

    def test_stream_emits_done_event(self):
        retriever = LocalRetriever.from_directory(ROOT / "data" / "documents")
        service = KnowledgeAssistant(retriever, MockLLMProvider())

        events = list(service.stream_answer("如何处理移动端流式输出？"))

        self.assertEqual(events[-1]["type"], "done")
        self.assertIn("citations", events[-1])
        self.assertTrue(any(event["type"] == "token" for event in events))

    def test_stream_can_emit_cancelled_event(self):
        retriever = LocalRetriever.from_directory(ROOT / "data" / "documents")
        service = KnowledgeAssistant(retriever, MockLLMProvider())

        events = list(
            service.stream_answer(
                "如何处理移动端流式输出？",
                request_id="req_cancel_demo",
                is_cancelled=lambda: True,
            )
        )

        self.assertEqual(events, [{"type": "cancelled", "request_id": "req_cancel_demo"}])


if __name__ == "__main__":
    unittest.main()
