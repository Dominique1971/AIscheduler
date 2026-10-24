"""Disabled, preparatory Codex CLI boundary. This module never starts a process.

Help evidence establishes syntax only. Runtime launch and sandbox behavior must be
verified in disposable repositories before wiring this boundary to dispatch.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CodexUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Invocation:
    argv: tuple[str, ...]
    stdin: bytes
    cwd: str


class CodexAdapter:
    """Build explicit argv, with no shell, config mutation or inferred model."""

    def __init__(self, executable: tuple[str, ...] = ("codex",), *, enabled: bool = False):
        if not executable or any(not isinstance(x, str) or not x for x in executable):
            raise ValueError("Executable must be a nonempty argument vector")
        self.executable = executable
        self.enabled = enabled

    def prepare(self, repository: str | Path, prompt: str, *, model: str | None = None,
                reasoning_effort: str | None = None) -> Invocation:
        if not self.enabled:
            raise CodexUnavailable("Codex execution is disabled; runtime acceptance is unrun")
        root = Path(repository).resolve(strict=True)
        if not root.is_dir() or not (root / ".git").exists():
            raise ValueError("A disposable Git repository or worktree is required")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be nonempty")
        argv = [*self.executable, "--ask-for-approval", "never", "exec", "--json",
                "--ignore-user-config", "--sandbox", "read-only", "--color", "never",
                "--cd", str(root)]
        if model is not None:
            if not model or model.startswith("-") or any(c.isspace() for c in model):
                raise ValueError("Invalid model identifier")
            argv.extend(["--model", model])
        if reasoning_effort is not None:
            if reasoning_effort not in {"minimal", "low", "medium", "high", "xhigh"}:
                raise ValueError("Reasoning effort is not in the preparatory allowlist")
            argv.extend(["--config", "model_reasoning_effort=" + json.dumps(reasoning_effort)])
        argv.append("-")
        return Invocation(tuple(argv), prompt.encode("utf-8"), str(root))


def parse_jsonl(raw: bytes) -> dict[str, Any]:
    """Parse a saved stream strictly; retain unknown events, never repair input.

    The expected event shape is from official documentation, not a captured real
    execution. Successful process exit and independent artifact acceptance remain
    separate gates even when this stream reports a completed turn.
    """
    events: list[dict[str, Any]] = []
    execution_id = None
    usage = None
    completed = False
    errors = []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {number}: {exc.msg}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError(f"Invalid event at line {number}")
        events.append(event)
        if event["type"] == "thread.started":
            identity = event.get("thread_id")
            if not isinstance(identity, str) or not identity:
                raise ValueError(f"Missing thread ID at line {number}")
            if execution_id is not None and identity != execution_id:
                raise ValueError("Stream contains conflicting thread IDs")
            execution_id = identity
        elif event["type"] == "turn.started":
            completed = False
            usage = None
        elif event["type"] == "turn.completed":
            completed = True
            candidate = event.get("usage")
            if candidate is not None:
                if not isinstance(candidate, dict) or any(
                    type(value) is not int or value < 0 for value in candidate.values()
                ):
                    raise ValueError(f"Invalid token usage at line {number}")
                usage = candidate
        elif event["type"] in {"error", "turn.failed"}:
            errors.append(event)
    return {"execution_id": execution_id, "usage": usage, "events": events,
            "errors": errors, "stream_completed": bool(execution_id and completed and not errors),
            "stdout_sha256": hashlib.sha256(raw).hexdigest()}


def make_receipt(invocation: Invocation, stdout: bytes, stderr: bytes, *, exit_code: int,
                 started_at: str, finished_at: str, code_revision: str) -> dict[str, Any]:
    """Provenance for untouched bytes; does not certify semantic acceptance/cost."""
    return {"argv": list(invocation.argv), "cwd": invocation.cwd,
            "prompt_sha256": hashlib.sha256(invocation.stdin).hexdigest(),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "exit_code": exit_code, "started_at": started_at, "finished_at": finished_at,
            "code_revision": code_revision, "cost": None, "acceptance": "unrun"}


def verify_hash(path: str | Path, expected_sha256: str) -> None:
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_sha256:
        raise ValueError(f"Evidence integrity mismatch: {path}")
