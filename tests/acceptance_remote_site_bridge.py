"""Fresh dummy-project acceptance of the normal API -> bridge -> private Site path.

Requires previously provisioned Windows DPAPI Site credentials. No real project,
Codex execution, Site control command, or MFA login is involved.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
PORT = 8876
PLANS = [ROOT / "examples/demo-weather.yaml", ROOT / "examples/demo-inventory.yaml"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("This hosted diagnostic uses Windows DPAPI credentials")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            raise SystemExit(f"127.0.0.1:{PORT} is already in use")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "evidence/remote-sites" / (run_id + "-bridge")
    folder.mkdir(parents=True)
    for plan in PLANS:
        shutil.copy2(plan, folder / plan.name)
    db = folder / "scheduler.sqlite"
    env = os.environ.copy()
    env["SCHEDULER_CONTROL_TOKEN"] = secrets.token_hex(32)
    env["SCHEDULER_TOKEN_EXPIRES_AT"] = str(int(time.time()) + 3600)
    records = []
    api = None
    started_at = datetime.now(timezone.utc).isoformat()
    result = "unrun"
    try:
        for plan in PLANS:
            args = [sys.executable, "-m", "scheduler", "--db", str(db), "import", str(plan), "--approve"]
            completed = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=20)
            prefix = "import-" + plan.stem
            (folder / (prefix + ".stdout.raw")).write_bytes(completed.stdout)
            (folder / (prefix + ".stderr.raw")).write_bytes(completed.stderr)
            records.append({"entry_point": " ".join(args[:4]) + " import " + plan.name + " --approve", "exit_code": completed.returncode,
                            "stdout_sha256": digest(folder / (prefix + ".stdout.raw")), "stderr_sha256": digest(folder / (prefix + ".stderr.raw"))})
            if completed.returncode:
                raise RuntimeError("dummy plan import failed")
        stdout = (folder / "api.stdout.raw").open("wb")
        stderr = (folder / "api.stderr.raw").open("wb")
        try:
            api = subprocess.Popen([sys.executable, "-m", "scheduler", "--db", str(db), "serve", "--port", str(PORT)],
                                   cwd=ROOT, env=env, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(100):
                if api.poll() is not None:
                    raise RuntimeError("local API exited before listening")
                with socket.socket() as probe:
                    if probe.connect_ex(("127.0.0.1", PORT)) == 0:
                        break
                time.sleep(0.1)
            else:
                raise RuntimeError("local API did not listen within 10 seconds")
            journal = folder / "bridge-journal.jsonl"
            args = ["pwsh", "-NoProfile", "-File", "remote/site_bridge.ps1", "-Action", "run",
                    "-RunSeconds", "12", "-LocalApi", f"http://127.0.0.1:{PORT}", "-Journal", str(journal)]
            completed = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=30)
            (folder / "bridge.stdout.raw").write_bytes(completed.stdout)
            (folder / "bridge.stderr.raw").write_bytes(completed.stderr)
            records.append({"entry_point": "remote/site_bridge.ps1 -Action run -> remote/bridge.py --site",
                            "exit_code": completed.returncode, "stdout_sha256": digest(folder / "bridge.stdout.raw"),
                            "stderr_sha256": digest(folder / "bridge.stderr.raw")})
            if completed.returncode:
                raise RuntimeError("bridge process failed")
            events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
            polls = [event for event in events if event.get("kind") == "site.poll"]
            failures = [event for event in events if event.get("kind") == "bridge.unavailable"]
            for event in polls:
                receipt = folder / "receipts" / (event["raw_sha256"] + ".json")
                if digest(receipt) != event["raw_sha256"]:
                    raise RuntimeError("site poll receipt integrity failure")
            if len(polls) < 2 or any(event["http_status"] != 200 for event in polls) or failures:
                raise RuntimeError("expected successful repeated hosted polling")
            result = "green_bridge_diagnostic"
        finally:
            if api is not None and api.poll() is None:
                api.terminate()
                try:
                    api.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait(timeout=5)
            stdout.close()
            stderr.close()
    except Exception as exc:
        result = "red: " + type(exc).__name__ + ": " + str(exc)
    finally:
        manifest = {
            "run_id": run_id, "started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
            "entry_point": "python tests/acceptance_remote_site_bridge.py",
            "test_class": "fresh dummy-project normal API and Python bridge to hosted Site; no visitor MFA or control acceptance",
            "site_source_sha": "77349ba15def44aec241a8dce79dc5dc5fc63624",
            "site_deployment_id": "appgdep_6adcce77c2f481919ee2d29b02ce9eb5",
            "site_environment_revision": 3, "remote_control_enabled": False,
            "plans": {p.name: digest(folder / p.name) for p in PLANS},
            "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [ROOT / "remote/bridge.py", ROOT / "remote/site_bridge.ps1", ROOT / "tests/acceptance_remote_site_bridge.py"]},
            "config": {"port": PORT, "bridge_run_seconds": 12, "credential_storage": "Windows CurrentUser DPAPI, values omitted",
                       "local_control_token": "fresh random 32 bytes, value omitted"},
            "processes": records,
            "raw_hashes": {p.name: digest(p) for p in folder.glob("*.raw")},
            "journal_sha256": digest(folder / "bridge-journal.jsonl") if (folder / "bridge-journal.jsonl").exists() else None,
            "cost": "unreported by Sites and local API",
            "result": result,
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "result": result}))
    return 0 if result == "green_bridge_diagnostic" else 1


if __name__ == "__main__":
    raise SystemExit(main())
