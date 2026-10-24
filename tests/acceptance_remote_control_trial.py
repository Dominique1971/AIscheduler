"""Bounded real Site control trial against disposable simulation projects only.

Run while the owner uses the normal phone dashboard to pause Demo Weather.
All secrets stay in process environments or the ignored DPAPI credential file.
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


def events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    # Ignore only an in-progress final line; preserve the raw journal unchanged.
    lines = path.read_bytes().splitlines(keepends=True)
    return [json.loads(line) for line in lines if line.endswith(b"\n")]


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("This trial uses the owner's Windows DPAPI credentials")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            raise SystemExit(f"127.0.0.1:{PORT} is already in use")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "evidence/remote-sites" / (run_id + "-control")
    folder.mkdir(parents=True)
    for plan in PLANS:
        shutil.copy2(plan, folder / plan.name)
    db = folder / "scheduler.sqlite"
    journal = folder / "bridge-journal.jsonl"
    env = os.environ.copy()
    env["SCHEDULER_CONTROL_TOKEN"] = secrets.token_hex(32)
    env["SCHEDULER_TOKEN_EXPIRES_AT"] = str(int(time.time()) + 3600)
    started_at = datetime.now(timezone.utc).isoformat()
    processes = []
    api = bridge = None
    streams = []
    result = "unrun"
    try:
        for plan in PLANS:
            command = [sys.executable, "-m", "scheduler", "--db", str(db), "import", str(plan), "--approve"]
            run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=20)
            label = "import-" + plan.stem
            (folder / (label + ".stdout.raw")).write_bytes(run.stdout)
            (folder / (label + ".stderr.raw")).write_bytes(run.stderr)
            processes.append({"entry_point": "scheduler import " + plan.name, "exit_code": run.returncode})
            if run.returncode:
                raise RuntimeError("dummy import failed")
        for label in ("api", "bridge"):
            streams.extend([(folder / (label + ".stdout.raw")).open("wb"), (folder / (label + ".stderr.raw")).open("wb")])
        api = subprocess.Popen([sys.executable, "-m", "scheduler", "--db", str(db), "serve", "--port", str(PORT)],
                               cwd=ROOT, env=env, stdout=streams[0], stderr=streams[1], creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(100):
            if api.poll() is not None:
                raise RuntimeError("local API exited before listening")
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", PORT)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("local API did not listen within 10 seconds")
        bridge = subprocess.Popen(["pwsh", "-NoProfile", "-File", "remote/site_bridge.ps1", "-Action", "run",
                                   "-RunSeconds", "300", "-LocalApi", f"http://127.0.0.1:{PORT}", "-Journal", str(journal)],
                                  cwd=ROOT, env=env, stdout=streams[2], stderr=streams[3], creationflags=subprocess.CREATE_NO_WINDOW)
        ready = observed_ack = False
        deadline = time.monotonic() + 310
        while time.monotonic() < deadline:
            if api.poll() is not None:
                raise RuntimeError("local API exited early")
            if bridge.poll() is not None:
                if bridge.returncode != 0:
                    raise RuntimeError("bridge exited with error")
                break
            current = events(journal)
            polls = [event for event in current if event.get("kind") == "site.poll" and event.get("http_status") == 200]
            if polls and not ready:
                ready = True
                print(json.dumps({"run_id": run_id, "state": "ready", "action": "Pause Demo Weather in the owner phone dashboard"}), flush=True)
            acks = [event for event in current if event.get("kind") == "control.ack"]
            if acks and not observed_ack:
                observed_ack = True
                print(json.dumps({"run_id": run_id, "state": "ack_observed", "status": acks[-1].get("status")}), flush=True)
            time.sleep(1)
        else:
            raise RuntimeError("bridge exceeded trial duration")
        if not ready:
            raise RuntimeError("hosted bridge did not poll successfully")
        snapshot = subprocess.run([sys.executable, "-m", "scheduler", "--db", str(db), "snapshot"],
                                  cwd=ROOT, env=env, capture_output=True, timeout=10)
        (folder / "final-snapshot.stdout.raw").write_bytes(snapshot.stdout)
        (folder / "final-snapshot.stderr.raw").write_bytes(snapshot.stderr)
        if snapshot.returncode:
            raise RuntimeError("final local snapshot failed")
        body = json.loads(snapshot.stdout)
        weather = next(p for p in body["projects"] if p["project_id"] == "demo-weather")
        acks = [event for event in events(journal) if event.get("kind") == "control.ack"]
        if weather["paused"] and any(event.get("status") == "succeeded" and event.get("http_status") == 200 for event in acks):
            result = "green_dummy_phone_control_observed"
        else:
            result = "red_or_unrun_dummy_control"
    except Exception as exc:
        result = "red: " + type(exc).__name__ + ": " + str(exc)
    finally:
        if bridge is not None and bridge.poll() is None:
            stopped = subprocess.run(["taskkill", "/PID", str(bridge.pid), "/T", "/F"], capture_output=True, timeout=10)
            (folder / "bridge-cleanup.stdout.raw").write_bytes(stopped.stdout)
            (folder / "bridge-cleanup.stderr.raw").write_bytes(stopped.stderr)
            bridge.wait(timeout=5)
        if api is not None and api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait(timeout=5)
        for stream in streams:
            stream.close()
        manifest = {
            "run_id": run_id, "started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
            "entry_point": "python tests/acceptance_remote_control_trial.py",
            "test_class": "fresh dummy-project CLI/API/bridge/Site/owner-phone control trial; real Codex unrun",
            "site_source_sha": "77349ba15def44aec241a8dce79dc5dc5fc63624",
            "site_version_id": "appgprj_6adcbab3ab1c81919496cad194193625~appgver_c94929c3e4f08191b5ccb24ff1107efe",
            "plans": {p.name: digest(folder / p.name) for p in PLANS},
            "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [ROOT / "remote/bridge.py", ROOT / "remote/site_bridge.ps1", ROOT / "tests/acceptance_remote_control_trial.py"]},
            "config": {"port": PORT, "max_duration_seconds": 300, "credential_storage": "Windows CurrentUser DPAPI, values omitted",
                       "local_control_token": "fresh random 32 bytes, value omitted", "expected_action": "pause demo-weather"},
            "processes": processes,
            "raw_hashes": {p.name: digest(p) for p in folder.glob("*.raw")},
            "journal_sha256": digest(journal) if journal.exists() else None,
            "cost": "unreported by Sites and local API", "result": result,
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "result": result}), flush=True)
    return 0 if result == "green_dummy_phone_control_observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
