"""One explicit positive write control; no model call; emitted file is diagnostic."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from codex_appserver_probe import ROOT, StdioClient


def main():
    denied_dir = ROOT / "evidence/codex-appserver/20261024T001942Z-d985a303"
    denied = json.loads((denied_dir / "report.json").read_text())
    for relative, expected in json.loads((denied_dir / "manifest.json").read_text()).items():
        if hashlib.sha256((denied_dir / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Negative control integrity mismatch")
    exe = Path(denied["argv"][0])
    if hashlib.sha256(exe.read_bytes()).hexdigest() != denied["native_cli_sha256"]:
        raise RuntimeError("Native CLI changed")
    cwd = Path(denied["cwd"]).resolve(strict=True)
    canary = Path(denied["checks"]["sandbox_canary"]["path"])
    if canary.exists() or canary.parent.resolve() != cwd:
        raise RuntimeError("Canary must be absent inside the exact owned dummy directory")
    out = ROOT / "evidence/codex-appserver" / (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-positive-" + uuid.uuid4().hex[:8])
    out.mkdir(parents=True)
    (out / "harness.py").write_bytes(Path(__file__).read_bytes())
    (out / "transport-harness.py").write_bytes((ROOT / "tests/codex_appserver_probe.py").read_bytes())
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        env.pop(key, None)
    auth = subprocess.run([str(exe), "login", "status"], env=env, capture_output=True, timeout=15)
    (out / "login-stdout.txt").write_bytes(auth.stdout)
    (out / "login-stderr.txt").write_bytes(auth.stderr)
    if auth.returncode or b"Logged in using ChatGPT" not in auth.stdout + auth.stderr:
        raise RuntimeError("ChatGPT status not confirmed")
    argv = [str(exe), "app-server", "--listen", "stdio://"]
    report = {"kind": "diagnostic positive sandbox control; no model invocation", "argv": argv,
        "cwd": str(cwd), "canary": str(canary), "negative_evidence": str(denied_dir),
        "started_epoch": time.time(), "cost": None, "passed": False}
    client = StdioClient(argv, env, cwd, out, time.monotonic() + 30)
    try:
        client.request("initialize", {"clientInfo": {"name": "scheduler_canary_control", "version": "0.1.0"}})
        client.send({"method": "initialized", "params": {}})
        code = ("from pathlib import Path; p=Path(" + repr(str(canary)) + "); "
                "p.write_text('diagnostic-positive-control; never adopt as generated result'); "
                "print(str(p.resolve())); print(p.read_text())")
        result = client.request("command/exec", {"command": [sys.executable, "-c", code], "cwd": str(cwd),
            "timeoutMs": 10000, "sandboxPolicy": {"type": "workspaceWrite", "writableRoots": [str(cwd)], "networkAccess": False}})
        report["response"] = result
        report["canary_exists"] = canary.exists()
        report["passed"] = result.get("exitCode") == 0 and canary.exists()
        if canary.exists():
            report["canary_sha256"] = hashlib.sha256(canary.read_bytes()).hexdigest()
            (out / "canary-original.txt").write_bytes(canary.read_bytes())
    except Exception as error:
        report["error"] = repr(error)
    finally:
        client.close()
        report["finished_epoch"] = time.time()
        report["process_exit_code"] = client.process.returncode
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        manifest = {str(path.relative_to(out)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in out.iterdir() if path.is_file()}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(out), **report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
