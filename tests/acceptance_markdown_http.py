"""Fresh loopback Markdown upload -> reviewed import -> daemon simulation evidence.

Requires the isolated example showcase and its control token in the environment.
This is an HTTP/daemon test, not a signed-in browser or real Codex test.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scheduler/static/intake-template.md"
ORIGIN = "http://127.0.0.1:8877"
PROJECT = "dummy-sample-project"


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    token = os.environ.get("SCHEDULER_CONTROL_TOKEN", "")
    if len(token) < 32:
        raise ValueError("showcase control token required")
    source = Path(os.environ.get("SCHEDULER_MARKDOWN_ACCEPTANCE_SOURCE", str(SOURCE)))
    project_id = os.environ.get("SCHEDULER_MARKDOWN_ACCEPTANCE_PROJECT", PROJECT)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "evidence/markdown-import" / run_id
    folder.mkdir(parents=True)
    steps = []
    result = "red"

    def call(name: str, path: str, body=None, *, authorized=True):
        raw_input = None if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        headers = {"Accept": "application/json"}
        if authorized:
            headers["Authorization"] = "Bearer " + token
        if raw_input is not None:
            headers.update({"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())})
            (folder / (name + ".request.raw")).write_bytes(raw_input)
        request = urllib.request.Request(ORIGIN + path, data=raw_input, headers=headers,
                                         method="POST" if raw_input is not None else "GET")
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status, raw_output = response.status, response.read(1048577)
        (folder / (name + ".response.raw")).write_bytes(raw_output)
        steps.append({"name": name, "path": path, "status": status,
                      "input_sha256": sha(raw_input) if raw_input is not None else None,
                      "output_sha256": sha(raw_output)})
        return status, json.loads(raw_output) if raw_output and path.startswith("/api/") else raw_output

    try:
        authored = source.read_bytes()
        (folder / "authored-intake.md").write_bytes(authored)
        status, html = call("dashboard", "/", authorized=False)
        if status != 200 or b'id="intake-file"' not in html or b'id="intake-form"' in html or b'/static/dag-layout.js' not in html:
            raise ValueError("local dashboard did not serve import-only UI")
        status, dag_script = call("dag-layout-script", "/static/dag-layout.js", authorized=False)
        if status != 200 or dag_script != (ROOT / "scheduler/static/dag-layout.js").read_bytes():
            raise ValueError("served dependency layout script differs from source")
        status, served = call("served-template", "/intake-template.md", authorized=False)
        if status != 200 or served != SOURCE.read_bytes():
            raise ValueError("served template differs from packaged bytes")
        status, _ = call("anonymous-preview", "/api/v1/intake/file/preview",
                         {"filename": "intake-template.md", "source_text": authored.decode()}, authorized=False)
        if status != 401:
            raise ValueError("anonymous preview was not denied")
        body = {"filename": "intake-template.md", "source_text": authored.decode()}
        status, draft = call("preview", "/api/v1/intake/file/preview", body)
        if status != 200 or draft["source_sha256"] != sha(authored) or draft["source_text"].encode() != authored:
            raise ValueError("Markdown source was not preserved")
        status, diff = call("plan-preview", "/api/v1/plans/preview", {"plan": draft["plan"]})
        if status != 200 or diff["from_revision"] is not None:
            raise ValueError("expected a new project preview")
        import_body = {**body, "expected_source_sha256": draft["source_sha256"],
                       "expected_preview": diff, "approved": True}
        status, _ = call("changed-source-rejected", "/api/v1/intake/file/import",
                         {**import_body, "source_text": body["source_text"] + "\n"})
        if status != 409:
            raise ValueError("changed Markdown source was not rejected")
        status, imported = call("import", "/api/v1/intake/file/import", import_body)
        if status != 200 or imported["project_id"] != project_id:
            raise ValueError("reviewed Markdown was not imported")
        status, stored = call("stored-plan", "/api/v1/projects/" + project_id + "/plan")
        if status != 200 or stored["plan_sha256"] != draft["plan_sha256"] or stored["source"]["source_sha256"] != draft["source_sha256"]:
            raise ValueError("stored provenance mismatch")
        deadline = time.monotonic() + 20
        while True:
            status, snapshot = call("snapshot-" + str(len(steps)), "/api/v1/snapshot")
            project = next((p for p in snapshot["projects"] if p["project_id"] == project_id), None)
            if status == 200 and project and all(t["state"] == "completed" for t in project["tasks"]):
                break
            if time.monotonic() >= deadline:
                raise ValueError("simulation did not complete before deadline")
            time.sleep(.5)
        attempts = {}
        for task in project["tasks"]:
            status, trace = call("trace-" + task["task_id"], "/api/v1/projects/" + project_id + "/tasks/" + task["task_id"] + "/trace")
            if status != 200 or len(trace["attempts"]) != 1:
                raise ValueError("unexpected task attempts")
            attempt = trace["attempts"][0]
            if attempt["state"] != "completed" or sha(attempt["input"].encode()) != attempt["input_hash"] or sha(attempt["output"].encode()) != attempt["output_hash"]:
                raise ValueError("raw attempt failed integrity check")
            attempts[task["task_id"]] = attempt
        for task in project["tasks"]:
            for dependency in task["depends_on"]:
                if attempts[task["task_id"]]["started"] < attempts[dependency]["ended"]:
                    raise ValueError("dependency precedence failed")
        result = "green_markdown_http_and_simulation_only"
    finally:
        manifest = {"run_id": run_id, "entry_point": "python tests/acceptance_markdown_http.py",
                    "test_class": "fresh local HTTP Markdown upload -> preview -> guarded import -> daemon simulation; browser and real Codex unrun",
                    "result": result, "project_id": project_id, "source_path": str(source), "source_sha256": sha(source.read_bytes()),
                    "code_sha256": {name: sha((ROOT / name).read_bytes()) for name in
                                    ["scheduler/intake.py", "scheduler/api.py", "scheduler/core.py",
                                     "scheduler/static/dashboard.js", "scheduler/static/index.html",
                                     "scheduler/static/dag-layout.js", "scheduler/static/style.css",
                                     "tests/acceptance_markdown_http.py"]},
                    "steps": steps, "model": "none (simulation)", "cost": "not measured; no model call",
                    "files": {p.name: sha(p.read_bytes()) for p in sorted(folder.iterdir()) if p.is_file()}}
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": result, "evidence": str(folder)}))
    return 0 if result.startswith("green_") else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
