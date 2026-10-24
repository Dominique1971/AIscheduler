"""Synthetic diagnostic tests, not real Codex generator acceptance."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scheduler.codex_adapter import CodexAdapter, CodexUnavailable, make_receipt, parse_jsonl, verify_hash


class CodexBoundaryTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with self.assertRaises(CodexUnavailable):
            CodexAdapter().prepare(".", "hello")

    def test_stdin_and_argv_preserve_literal_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".git").mkdir()
            invocation = CodexAdapter(enabled=True).prepare(
                directory, 'literal $(whoami) `stuff` --model anything', model="test-model",
                reasoning_effort="high")
            self.assertEqual(invocation.stdin, b'literal $(whoami) `stuff` --model anything')
            self.assertIn("read-only", invocation.argv)
            self.assertIn("--ignore-user-config", invocation.argv)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", invocation.argv)
            self.assertEqual(invocation.argv[-1], "-")
            receipt = make_receipt(invocation, b"out", b"err", exit_code=0,
                                   started_at="start", finished_at="end", code_revision="test")
            self.assertEqual(receipt["stdout_sha256"], hashlib.sha256(b"out").hexdigest())
            self.assertEqual(receipt["acceptance"], "unrun")

    def test_write_invocation_requires_explicit_disposable_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inside = root / "dummy"
            outside = root / "outside"
            for repo in (inside, outside):
                (repo / ".git").mkdir(parents=True)
            adapter = CodexAdapter(enabled=True, permitted_root=inside)
            with self.assertRaises(ValueError):
                adapter.prepare(outside, "write a file", write=True)
            with self.assertRaises(ValueError):
                CodexAdapter(enabled=True).prepare(inside, "write a file", write=True)
            invocation = adapter.prepare(inside, "write a file", write=True)
            self.assertIn("workspace-write", invocation.argv)
            self.assertNotIn("--ignore-user-config", invocation.argv)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", invocation.argv)

    def test_documented_synthetic_events(self):
        raw = b'\n'.join(json.dumps(x).encode() for x in [
            {"type": "thread.started", "thread_id": "fixture-id"},
            {"type": "future.event", "data": "retained"},
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 3}}])
        result = parse_jsonl(raw)
        self.assertTrue(result["stream_completed"])
        self.assertEqual(result["usage"]["input_tokens"], 10)
        self.assertEqual(len(result["events"]), 3)

    def test_incomplete_and_error_streams_are_not_success(self):
        for raw in [b'', b'{"type":"turn.completed"}',
                    b'{"type":"thread.started","thread_id":"x"}\n{"type":"turn.failed"}']:
            self.assertFalse(parse_jsonl(raw)["stream_completed"])

    def test_second_turn_must_also_complete(self):
        raw = (b'{"type":"thread.started","thread_id":"x"}\n'
               b'{"type":"turn.completed","usage":{"input_tokens":1}}\n'
               b'{"type":"turn.started"}')
        result = parse_jsonl(raw)
        self.assertFalse(result["stream_completed"])
        self.assertIsNone(result["usage"])

    def test_malformed_and_conflicting_events_rejected(self):
        for raw in [b'{broken', b'[]', b'{"type":"thread.started"}',
                    b'{"type":"turn.completed","usage":{"input_tokens":true}}',
                    b'{"type":"thread.started","thread_id":"a"}\n'
                    b'{"type":"thread.started","thread_id":"b"}']:
            with self.assertRaises(ValueError):
                parse_jsonl(raw)

    def test_changed_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw"
            path.write_bytes(b"original")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            verify_hash(path, expected)
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_hash(path, expected)


if __name__ == "__main__":
    unittest.main()
