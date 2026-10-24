"""Git worktree diagnostics; no model task or scheduler dispatch is run."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

from scheduler.worktrees import MARKER, prepare_disposable_worktree


def git(*args, cwd: Path):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True, timeout=20)


def test_marked_dummy_root_creates_independent_exact_commit_worktrees(tmp_path):
    root = tmp_path / "disposable"
    root.mkdir()
    seed = root / "seed"
    git("init", "-b", "main", str(seed), cwd=root)
    (seed / "seed.txt").write_bytes(b"untouched seed\n")
    git("add", "seed.txt", cwd=seed)
    git("-c", "user.name=Scheduler Test", "-c", "user.email=test@example.invalid",
        "commit", "-m", "seed", cwd=seed)
    with pytest.raises(ValueError, match="marked disposable root"):
        prepare_disposable_worktree(root, seed, "one")
    (root / ".scheduler-disposable").write_bytes(MARKER)
    first = prepare_disposable_worktree(root, seed, "one")
    second = prepare_disposable_worktree(root, seed, "two")
    assert first.source_commit == second.source_commit == git("rev-parse", "HEAD", cwd=seed).stdout.decode().strip()
    assert first.path != second.path
    (first.path / "result.txt").write_bytes(b"first only\n")
    assert not (second.path / "result.txt").exists()
    assert not (seed / "result.txt").exists()
    assert all(hashlib.sha256(step["stdout"]).hexdigest() == step["stdout_sha256"] and
               hashlib.sha256(step["stderr"]).hexdigest() == step["stderr_sha256"]
               for step in first.receipts + second.receipts)
    for checkout in (first, second):
        for index, step in enumerate(checkout.receipts, 1):
            assert hashlib.sha256((checkout.receipt_dir / f"{index:04d}.stdout.raw").read_bytes()).hexdigest() == step["stdout_sha256"]
            assert hashlib.sha256((checkout.receipt_dir / f"{index:04d}.stderr.raw").read_bytes()).hexdigest() == step["stderr_sha256"]
    with pytest.raises(FileExistsError):
        prepare_disposable_worktree(root, seed, "one")


def test_outside_checkout_and_unsafe_identity_are_refused(tmp_path):
    root = tmp_path / "disposable"
    root.mkdir()
    (root / ".scheduler-disposable").write_bytes(MARKER)
    outside = tmp_path / "outside"
    git("init", "-b", "main", str(outside), cwd=tmp_path)
    with pytest.raises(ValueError, match="seed must"):
        prepare_disposable_worktree(root, outside, "one")
    with pytest.raises(ValueError, match="attempt ID"):
        prepare_disposable_worktree(root, outside, "../escape")
    assert not (root / "worktrees").exists()
