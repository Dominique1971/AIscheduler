"""Fresh dummy HTTP intake -> review -> guarded import -> simulation trial."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scheduler.intake import load_intake


SOURCE = ROOT / "examples" / "intake-demo-weather.yaml"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "evidence" / "intake-http" / run_id
    folder.mkdir(parents=True)
    source = folder / SOURCE.name
    shutil.copy2(SOURCE, source)
    intake, source_hash = load_intake(source)
    (folder / "intake-input.json").write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
    db = folder / "scheduler.sqlite"
    with socket.socket() as bound:
        bound.bind(("127.0.0.1", 0))
        port = bound.getsockname()[1]
    control = secrets.token_urlsafe(48)
    environment = {**os.environ, "SCHEDULER_CONTROL_TOKEN": control}
    server_out = (folder / "server.stdout.raw").open("wb")
    server_err = (folder / "server.stderr.raw").open("wb")
    server = subprocess.Popen([sys.executable, "-m", "scheduler", "--db", str(db),
                               "serve", "--port", str(port)], cwd=ROOT, env=environment,
                              stdout=server_out, stderr=server_err)
    receipts = []
    result = "red_or_unrun"

    def post(label: str, route: str, value: dict, *, authorized=True):
        raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
        (folder / f"{label}.request.json").write_bytes(raw)
        headers = {"Content-Type": "application/json", "Idempotency-Key": label}
        if authorized:
            headers["Authorization"] = "Bearer " + control
        request = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1{route}", raw, headers,
                                         method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        (folder / f"{label}.response.raw").write_bytes(body)
        receipts.append({"label": label, "route": route, "status": status,
                         "request_sha256": hashlib.sha256(raw).hexdigest(),
                         "response_sha256": hashlib.sha256(body).hexdigest()})
        return status, json.loads(body)

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError("local API exited before readiness")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5).close()
                break
            except urllib.error.HTTPError:
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("local API readiness timed out")
        status, _ = post("anonymous-intake", "/intake/preview", {"intake": intake}, authorized=False)
        if status != 401:
            raise RuntimeError("anonymous intake was not denied")
        status, draft = post("intake-preview", "/intake/preview", {"intake": intake})
        if status != 200 or draft["summary"]["critical_path_estimate_minutes"] != 7:
            raise RuntimeError("intake preview failed")
        if hashlib.sha256(draft["source_text"].encode()).hexdigest() != draft["source_sha256"]:
            raise RuntimeError("intake source provenance mismatch")
        status, preview = post("plan-preview", "/plans/preview", {"plan": draft["plan"]})
        if status != 200 or preview["from_revision"] is not None:
            raise RuntimeError("initial plan preview failed")
        stale = {**preview, "added": []}
        status, _ = post("stale-rejected", "/plans/apply",
                         {"plan": draft["plan"], "approved": True, "expected_preview": stale})
        if status != 409:
            raise RuntimeError("stale preview was accepted")
        status, applied = post("reviewed-import", "/plans/apply",
                               {"plan": draft["plan"], "approved": True, "expected_preview": preview})
        if status != 200 or applied != preview:
            raise RuntimeError("reviewed import failed")
        status, _ = post("reused-preview-rejected", "/plans/apply",
                         {"plan": draft["plan"], "approved": True, "expected_preview": preview})
        if status != 409:
            raise RuntimeError("reused preview was accepted")
        result = "green_dummy_http_review_import_only"
    except Exception as error:
        result = "red: " + type(error).__name__ + ": " + str(error)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        server_out.close()
        server_err.close()
    if db.exists():
        connection = sqlite3.connect(db)
        try:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            if result.startswith("green") and count != 1:
                result = "red: imported project count mismatch"
        finally:
            connection.close()
    manifest = {
        "run_id": run_id, "entry_point": "python tests/acceptance_intake_http.py",
        "test_class": "fresh local HTTP intake -> plan preview -> guarded import; browser interaction and real Codex unrun",
        "source_sha256": source_hash,
        "code_sha256": {str(path.relative_to(ROOT)): digest(path) for path in
                        [ROOT / "scheduler/api.py", ROOT / "scheduler/core.py", ROOT / "scheduler/intake.py",
                         ROOT / "scheduler/static/dashboard.js", ROOT / "tests/acceptance_intake_http.py"]},
        "http_receipts": receipts,
        "file_sha256": {path.name: digest(path) for path in folder.iterdir() if path.is_file()},
        "cost": "no model call; local simulation intake only", "result": result,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "result": result, "evidence": str(folder)}))
    return 0 if result == "green_dummy_http_review_import_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
