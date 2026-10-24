"""Fresh black-box CLI/API simulation acceptance, never edits generated output.

Run: python tests/acceptance_simulation.py
All plans are normal authored inputs. Failure/stall injection is simulation-only.
No direct domain calls, mocks, patched receipts or database mutations.
"""
from __future__ import annotations

import copy
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

import yaml

ROOT = Path(__file__).resolve().parents[1]


def run():
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())+"-"+uuid.uuid4().hex[:8]
    out = ROOT / "evidence" / "acceptance" / run_id
    out.mkdir(parents=True)
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for folder in ["scheduler", "schemas", "examples"] for p in (ROOT/folder).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts}
    source_hashes["tests/acceptance_simulation.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    db_path = out / "scheduler.db"
    env = os.environ.copy()
    token, read = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    env["SCHEDULER_CONTROL_TOKEN"], env["SCHEDULER_READ_TOKEN"] = token, read
    # These are disposable test credentials; do not inherit host expiry configuration.
    env.pop("SCHEDULER_TOKEN_EXPIRES_AT", None)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    processes, logs, checks = [], [], {}
    serial = 0

    def cli(*args):
        nonlocal serial
        serial += 1
        cmd = [sys.executable, "-m", "scheduler", "--db", str(db_path), *args]
        result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, timeout=15)
        (out/f"{serial:03}-cli-stdout.txt").write_bytes(result.stdout)
        (out/f"{serial:03}-cli-stderr.txt").write_bytes(result.stderr)
        (out/f"{serial:03}-cli-receipt.json").write_text(json.dumps({"argv": cmd, "exit_code": result.returncode}), encoding="utf-8")
        assert result.returncode == 0, result.stderr.decode()
        return json.loads(result.stdout)

    def launch(name, *args):
        a, b = (out/f"{name}-stdout.txt").open("wb"), (out/f"{name}-stderr.txt").open("wb")
        logs.extend([a,b])
        cmd = [sys.executable, "-m", "scheduler", "--db", str(db_path), *args]
        process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=a, stderr=b)
        processes.append(process)
        (out/f"{name}-launch.json").write_text(json.dumps({"argv": cmd, "pid": process.pid, "at": time.time()}), encoding="utf-8")
        return process

    def api(path, body=None, auth=token, status=200, idem=None):
        nonlocal serial
        serial += 1
        data = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": "Bearer "+auth, "Content-Type": "application/json"}
        if body is not None:
            headers["Idempotency-Key"] = idem or str(uuid.uuid4())
        req = urllib.request.Request(url+"/api/v1"+path, data=data, headers=headers)
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        raw = response.read()
        (out/f"{serial:03}-http-response.json").write_bytes(raw)
        (out/f"{serial:03}-http-receipt.json").write_text(json.dumps({"path": path, "body": body, "status": response.status,
            "role": "reader" if auth == read else "controller" if auth == token else "unauthenticated",
            "idempotency_key": headers.get("Idempotency-Key"), "response_sha256": hashlib.sha256(raw).hexdigest(), "at": time.time()}), encoding="utf-8")
        assert response.status == status, (path, response.status, raw)
        return json.loads(raw)

    def wait_for(predicate, timeout=20):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            snapshot = api("/snapshot")
            if predicate(snapshot):
                return snapshot
            time.sleep(.12)
        raise AssertionError("condition timeout")

    try:
        plans = []
        for filename in ["demo-weather.yaml", "demo-inventory.yaml"]:
            plan = yaml.safe_load((ROOT/"examples"/filename).read_text())
            for task in plan["tasks"]:
                task["simulation"]["duration_seconds"] = 2 if not task["depends_on"] else .2
            plan["tasks"][0]["priority"] = 95
            for suffix in ["alpha", "beta"]:
                task = copy.deepcopy(plan["tasks"][0])
                task.update(task_id="independent-"+suffix, title="Independent "+suffix)
                task["priority"] = 80
                task["simulation"].update(duration_seconds=3, output="independent simulation receipt "+suffix)
                plan["tasks"].append(task)
            plan["policy"].update(max_workers=4, min_workers=0, target_workers=3)
            if not plans:
                stalled = copy.deepcopy(plan["tasks"][0])
                stalled.update(task_id="stalled", title="Synthetic stalled task", depends_on=["source"])
                stalled["simulation"].update(duration_seconds=2, stall_seconds=2)
                stalled["timeout_policy"].update(execution_seconds=.3, max_retries=1)
                plan["tasks"].append(stalled)
                blocked = copy.deepcopy(stalled)
                blocked.update(task_id="blocked-by-stall", title="Blocked by reviewed failure", depends_on=["stalled"])
                plan["tasks"].append(blocked)
            path = out/filename
            path.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
            cli("validate", str(path))
            cli("import", str(path))
            plans.append(plan)
        service = launch("api", "serve", "--port", str(port))
        for _ in range(100):
            try:
                with urllib.request.urlopen(urllib.request.Request(url+"/api/v1/system/health", headers={"Authorization": "Bearer "+token}), timeout=.2) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        else:
            raise AssertionError("API did not start")
        api("/snapshot", auth="", status=401)
        api("/projects/demo-weather/pause", {}, auth=read, status=403)
        checks["RBAC"] = True
        for plan in plans:
            api(f"/projects/{plan['project_id']}/pause", {})
        daemon = launch("daemon-before-restart", "daemon", "--workers", "4", "--interval", ".05")
        wait_for(lambda s: s["daemon"]["healthy"] and s["workers"] == 0 and s["max_workers"] == 4)
        for plan in plans:
            api(f"/projects/{plan['project_id']}/resume", {})
        active = wait_for(lambda s: s["workers"] == 4)
        assert next(t for p in active["projects"] if p["project_id"] == "demo-weather" for t in p["tasks"] if t["task_id"] == "source")["state"] == "running"
        checks["four_workers"] = True
        api("/projects/demo-weather/pause", {})
        revision = copy.deepcopy(plans[0])
        revision["revision"] = 2
        for suffix in ["left", "right"]:
            task = copy.deepcopy(revision["tasks"][1])
            task.update(task_id="split-"+suffix, title="Split continuation "+suffix, depends_on=["source"])
            task["simulation"].update(fail_attempts=0, duration_seconds=.2)
            revision["tasks"].append(task)
        (out/"revision-2.yaml").write_text(yaml.safe_dump(revision, sort_keys=False), encoding="utf-8")
        preview = api("/plans/preview", {"plan": revision})
        assert preview["added"] == ["split-left", "split-right"]
        api("/plans/apply", {"plan": revision}, status=409)
        api("/plans/apply", {"plan": revision, "approved": True})
        checks["active_split_revision"] = True
        bad = copy.deepcopy(revision)
        bad["revision"] = 3
        bad["tasks"][0]["description"] += " incompatible change"
        api("/plans/apply", {"plan": bad, "approved": True}, status=409)
        checks["active_contract_rejected"] = True
        idem = str(uuid.uuid4())
        first = api("/projects/demo-weather/allocate", {"max_workers": 2}, idem=idem)
        second = api("/projects/demo-weather/allocate", {"max_workers": 2}, idem=idem)
        assert first == second
        api("/projects/demo-inventory/allocate", {"max_workers": 2})
        checks["allocation_and_idempotency"] = True
        before = api("/snapshot")
        daemon.kill()
        daemon.wait(timeout=5)
        (out/"forced-restart.json").write_text(json.dumps({"pid": daemon.pid, "exit_code": daemon.returncode,
            "method": "Popen.kill", "at": time.time(), "running_attempts": before["workers"]}), encoding="utf-8")
        time.sleep(3.2)
        assert not api("/snapshot")["daemon"]["healthy"]
        launch("daemon-after-restart", "daemon", "--interval", ".05")
        wait_for(lambda s: s["daemon"]["healthy"])
        # Paused project retains active work, but no new attempt may start while paused.
        after_restart = api("/snapshot")
        assert next(p for p in after_restart["projects"] if p["project_id"] == "demo-weather")["paused"]
        api("/system/workers", {"max_workers": 6})
        for plan in plans:
            api(f"/projects/{plan['project_id']}/allocate", {"max_workers": 4})
        api("/projects/demo-weather/resume", {})
        wait_for(lambda s: s["max_workers"] == 6)
        checks["six_worker_capacity_and_restart"] = True
        final = wait_for(lambda s: all(t["state"] in {"completed", "waiting-review", "dependency-blocked"} for p in s["projects"] for t in p["tasks"])
                            and sum(t["state"] == "completed" for p in s["projects"] for t in p["tasks"]) == 18, timeout=30)
        attempts = {}
        states = {}
        for project in final["projects"]:
            for task in project["tasks"]:
                states[(project["project_id"], task["task_id"])] = task["state"]
                trace = api(f"/projects/{project['project_id']}/tasks/{task['task_id']}/trace")
                attempts[(project["project_id"], task["task_id"])] = trace["attempts"]
        ids = [a["id"] for value in attempts.values() for a in value]
        assert len(ids) == len(set(ids))
        for key, value in attempts.items():
            assert len({a["number"] for a in value}) == len(value)
            for a in value:
                assert hashlib.sha256(a["input"].encode()).hexdigest() == a["input_hash"]
                assert hashlib.sha256(a["output"].encode()).hexdigest() == a["output_hash"]
        for project in final["projects"]:
            for task in project["tasks"]:
                value = attempts[(project["project_id"], task["task_id"])]
                for dep in task["depends_on"]:
                    if value:
                        dependency = attempts[(project["project_id"], dep)]
                        finish = next(a["ended"] for a in dependency if a["state"] == "completed")
                        assert min(a["started"] for a in value) >= finish
        assert states[("demo-weather", "stalled")] == "waiting-review"
        assert states[("demo-weather", "blocked-by-stall")] == "dependency-blocked"
        assert len(attempts[("demo-weather", "stalled")]) == 2
        checks.update(no_duplicate_attempts=True, dag_precedence=True, bounded_failure_and_blocking=True, receipt_integrity=True)
        # Existing completed receipts survive a subsequent normal plan revision.
        retained = {key: [a["output_hash"] for a in value] for key,value in attempts.items()}
        revision["revision"] = 3
        revision["display_name"] += " revised"
        api("/plans/apply", {"plan": revision, "approved": True})
        for tid in [t["task_id"] for t in revision["tasks"]]:
            trace = api(f"/projects/demo-weather/tasks/{tid}/trace")
            assert [a["output_hash"] for a in trace["attempts"]] == retained[("demo-weather",tid)]
        checks["completed_receipts_preserved"] = True
        verified = cli("verify")
        assert verified["valid"]
        backup_path = out/"online-backup.db"
        backup_receipt = cli("backup", str(backup_path))
        assert backup_receipt["valid"]
        restored_path = out/"restored.db"
        assert cli("--db", str(restored_path), "restore", str(backup_path))["valid"]
        assert cli("--db", str(restored_path), "verify")["valid"]
        restored_trace = cli("--db", str(restored_path), "trace", "demo-weather", "source")
        assert [a["output_hash"] for a in restored_trace["attempts"]] == retained[("demo-weather", "source")]
        checks["online_backup_restore_preserves_receipts"] = True
        api("/system/emergency-stop", {}, status=400)
        api("/system/emergency-stop", {"confirmed": True})
        assert api("/snapshot")["stopped"]
        checks["emergency_confirmation"] = True
        cli("snapshot")
        passed, error = True, None
    except BaseException as exc:
        passed, error = False, repr(exc)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for handle in logs:
            handle.close()
        # Checkpoint only merges SQLite's own WAL; never changes application rows.
        if db_path.exists():
            with closing(sqlite3.connect(db_path)) as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        report = {"run_id": run_id, "entry_point": "python -m scheduler CLI + loopback REST + independent daemon processes",
            "kind": "fresh black-box simulation acceptance", "passed": passed, "checks": checks, "error": error,
            "source_sha256": source_hashes, "python": platform.python_version(), "platform": platform.platform(),
            "model": None, "cost": 0, "tokens": None, "real_generator_acceptance": "UNRUN", "remote_cellular": "UNRUN", "soak_24h": "UNRUN",
            "limitations": ["synthetic receipts only", "four workers observed; six capacity verified, six concurrent workers not required by this fixture", "host reboot unrun", "no real side effects or model execution"]}
        (out/"report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        manifest = {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*") if p.is_file()}
        (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "passed": passed, "error": error, "directory": str(out)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
