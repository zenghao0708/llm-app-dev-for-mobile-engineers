import sys
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sse_client import build_stream_url, parse_sse_events


class SseClientTest(unittest.TestCase):
    def test_build_stream_url_encodes_chinese_question(self):
        url = build_stream_url("http://127.0.0.1:8000", "如何处理移动端流式输出", "req_001")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/ask/stream")
        self.assertEqual(query["question"], ["如何处理移动端流式输出"])
        self.assertEqual(query["request_id"], ["req_001"])

    def test_parse_sse_events_reads_event_and_data_fields(self):
        lines = [
            b"event: token\n",
            b'data: {"type":"token","content":"hello"}\n',
            b"\n",
            b"event: done\n",
            b'data: {"citations":[]}\n',
            b"\n",
        ]

        events = list(parse_sse_events(lines))

        self.assertEqual(events[0], {"type": "token", "content": "hello"})
        self.assertEqual(events[1], {"citations": [], "type": "done"})


if __name__ == "__main__":
    unittest.main()
