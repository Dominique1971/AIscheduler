"""Real, bounded CLI worktree diagnostic; not scheduler acceptance.

Runs only in freshly initialized dummy Git worktrees. The original emitted files
and JSONL remain untouched; hashes and exact checks are reported separately.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scheduler.codex_adapter import parse_jsonl

CLI = Path(r"C:\Users\domin\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe")


def checked(argv: list[str], cwd: Path, out: Path, label: str) -> None:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=20)
    (out / f"{label}.stdout").write_bytes(result.stdout)
    (out / f"{label}.stderr").write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{label} exited {result.returncode}")


def main() -> int:
    if not CLI.is_file():
        raise RuntimeError("Verified native CLI path unavailable")
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    out = ROOT / "evidence" / "codex-worktree" / run_id
    out.mkdir(parents=True)
    base = ROOT / "runtime" / "codex-worktree" / run_id
    seed = base / "seed"
    seed.mkdir(parents=True)
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        env.pop(key, None)
    auth = subprocess.run([str(CLI), "login", "status"], env=env, capture_output=True, timeout=15)
    (out / "auth.stdout").write_bytes(auth.stdout)
    (out / "auth.stderr").write_bytes(auth.stderr)
    if auth.returncode or b"Logged in using ChatGPT" not in auth.stdout + auth.stderr:
        raise RuntimeError("ChatGPT subscription login not confirmed; no model task started")
    checked(["git", "init", "-b", "main", str(seed)], base, out, "git-init")
    checked(["git", "config", "user.name", "Scheduler Dummy Probe"], seed, out, "git-user-name")
    checked(["git", "config", "user.email", "scheduler-probe@example.invalid"], seed, out, "git-user-email")
    (seed / "README.txt").write_bytes(b"Disposable worktree isolation probe.\n")
    checked(["git", "add", "README.txt"], seed, out, "git-add")
    checked(["git", "commit", "-m", "Seed dummy repository"], seed, out, "git-commit")
    processes = []
    report = {"run_id": run_id, "kind": "real installed CLI dummy worktree diagnostic",
              "native_cli_sha256": hashlib.sha256(CLI.read_bytes()).hexdigest(),
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "auth": "ChatGPT status verified; API-key and custom endpoint variables removed",
              "cost_usd": None, "runs": [], "passed": False,
              "limitations": ["not scheduler dispatch acceptance", "not native desktop parity",
                              "no broad approval/tool parity", "dollar cost unavailable"]}
    for label in ("A", "B"):
        worktree = base / label
        checked(["git", "worktree", "add", "-b", "probe-" + label, str(worktree), "main"],
                seed, out, "worktree-" + label)
        marker = f"WORKTREE_{label}_{run_id}\n"
        prompt = (f"This is an authorized disposable dummy Git worktree. In the current directory, "
                  f"write exactly one UTF-8 file named result-{label}.txt with the exact content "
                  f"{marker!r}. Do not modify other files, run network commands, access another "
                  f"directory, or commit. Report completion briefly.")
        (out / f"{label}.prompt").write_bytes(prompt.encode("utf-8"))
        stdout = (out / f"{label}.jsonl").open("wb")
        stderr = (out / f"{label}.stderr").open("wb")
        argv = [str(CLI), "--ask-for-approval", "never", "exec", "--json",
                "--sandbox", "workspace-write", "--color", "never",
                "--cd", str(worktree), "-"]
        started = time.time()
        process = subprocess.Popen(argv, cwd=worktree, env=env, stdin=subprocess.PIPE,
                                   stdout=stdout, stderr=stderr)
        process.stdin.write(prompt.encode("utf-8"))
        process.stdin.close()
        processes.append((process, stdout, stderr))
        report["runs"].append({"label": label, "argv": argv, "cwd": str(worktree),
                               "pid": process.pid, "started_epoch": started,
                               "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                               "expected_sha256": hashlib.sha256(marker.encode("utf-8")).hexdigest(),
                               "model": "CLI default", "cost_usd": None})
    deadline = time.time() + 150
    while any(p.poll() is None for p, _, _ in processes) and time.time() < deadline:
        time.sleep(.2)
    for (process, stdout, stderr), run in zip(processes, report["runs"]):
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        stdout.close()
        stderr.close()
        run["exit_code"] = process.returncode
        run["finished_epoch"] = time.time()
        raw = (out / f"{run['label']}.jsonl").read_bytes()
        try:
            parsed = parse_jsonl(raw)
            run.update(execution_id=parsed["execution_id"], usage=parsed["usage"],
                       stream_completed=parsed["stream_completed"],
                       stdout_sha256=parsed["stdout_sha256"])
        except ValueError as exc:
            run["parse_error"] = str(exc)
        worktree = base / run["label"]
        target = worktree / f"result-{run['label']}.txt"
        run["file_exists"] = target.is_file()
        if target.is_file():
            source = target.read_bytes()
            (out / f"{run['label']}.emitted").write_bytes(source)
            run["emitted_sha256"] = hashlib.sha256(source).hexdigest()
            run["exact_bytes"] = run["emitted_sha256"] == run["expected_sha256"]
        for name in ("A", "B"):
            run[f"other_marker_{name}_present"] = name != run["label"] and (worktree / f"result-{name}.txt").exists()
        checked(["git", "status", "--porcelain"], worktree, out, "status-" + run["label"])
    report["passed"] = all(r.get("exit_code") == 0 and r.get("stream_completed")
                           and r.get("exact_bytes") and not any(r[f"other_marker_{x}_present"] for x in ("A", "B"))
                           for r in report["runs"])
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                    for p in out.iterdir() if p.is_file()}, indent=2), encoding="utf-8")
    print(json.dumps({"directory": str(out), "passed": report["passed"], "runs": report["runs"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
