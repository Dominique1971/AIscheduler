"""Disposable Git worktree preparation for a future Codex runner.

This module never launches a model task or removes a checkout. The caller must
provide a marked disposable root; every Git command is recorded as raw bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess


MARKER = b"scheduler-disposable-v1\n"
ATTEMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


@dataclass(frozen=True)
class Worktree:
    path: Path
    source_commit: str
    receipt_dir: Path
    receipts: tuple[dict, ...]


def prepare_disposable_worktree(permitted_root: str | Path, seed_repository: str | Path,
                                attempt_id: str) -> Worktree:
    """Create one isolated checkout, refusing missing markers or existing paths.

    Partial Git failures are preserved in place for investigation. A retry must
    use a new attempt ID after explicit reconciliation, never overwrite one.
    """
    if not isinstance(attempt_id, str) or not ATTEMPT_ID.fullmatch(attempt_id):
        raise ValueError("attempt ID must be a simple filesystem-safe identifier")
    root = Path(permitted_root).resolve(strict=True)
    marker = root / ".scheduler-disposable"
    if not root.is_dir() or not marker.is_file() or marker.is_symlink() or marker.read_bytes() != MARKER:
        raise ValueError("an explicitly marked disposable root is required")
    seed = Path(seed_repository).resolve(strict=True)
    if not seed.is_dir() or not seed.is_relative_to(root) or not (seed / ".git").exists():
        raise ValueError("seed must be a Git checkout within the disposable root")
    destination = root / "worktrees" / attempt_id
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"worktree destination already exists: {destination}")
    if destination.parent.is_symlink() or destination.parent.exists() and destination.parent.resolve(strict=True) != root / "worktrees":
        raise ValueError("worktree parent must not redirect through a symlink")
    receipt_parent = root / "receipts"
    if receipt_parent.is_symlink():
        raise ValueError("receipt parent must not redirect through a symlink")
    receipt_dir = receipt_parent / attempt_id
    if receipt_dir.exists() or receipt_dir.is_symlink():
        raise FileExistsError(f"receipt directory already exists: {receipt_dir}")
    receipt_parent.mkdir(exist_ok=True)
    receipt_dir.mkdir()
    receipts = []

    def git(*args: str, cwd: Path = seed) -> bytes:
        argv = ["git", *args]
        run = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=30, check=False)
        index = len(receipts) + 1
        prefix = f"{index:04d}"
        (receipt_dir / f"{prefix}.stdout.raw").write_bytes(run.stdout)
        (receipt_dir / f"{prefix}.stderr.raw").write_bytes(run.stderr)
        receipt = {"argv": argv, "cwd": str(cwd), "exit_code": run.returncode,
                         "stdout": run.stdout, "stderr": run.stderr,
                         "stdout_sha256": hashlib.sha256(run.stdout).hexdigest(),
                         "stderr_sha256": hashlib.sha256(run.stderr).hexdigest()}
        (receipt_dir / f"{prefix}.json").write_text(json.dumps({k: v for k, v in receipt.items()
                                                                   if k not in {"stdout", "stderr"}}, indent=2) + "\n",
                                                       encoding="utf-8")
        receipts.append(receipt)
        if run.returncode:
            raise RuntimeError(f"Git command failed: {' '.join(args[:2])}")
        return run.stdout

    if git("rev-parse", "--is-inside-work-tree").strip() != b"true":
        raise ValueError("seed is not a Git worktree")
    source_commit = git("rev-parse", "HEAD").decode("ascii").strip()
    if not re.fullmatch(r"[a-f0-9]{40,64}", source_commit):
        raise ValueError("seed HEAD is not a full commit hash")
    destination.parent.mkdir(exist_ok=True)
    git("worktree", "add", "--detach", str(destination), source_commit)
    actual = Path(git("rev-parse", "--show-toplevel", cwd=destination).decode().strip()).resolve(strict=True)
    if actual != destination.resolve(strict=True):
        raise RuntimeError("Git reported an unexpected worktree root")
    if git("rev-parse", "HEAD", cwd=destination).decode("ascii").strip() != source_commit:
        raise RuntimeError("worktree HEAD differs from the seed commit")
    return Worktree(destination, source_commit, receipt_dir, tuple(receipts))
