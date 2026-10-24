"""Import packaged disposable examples through the normal loopback API.

Preserves exact request/response bytes and hashes. Never touches real projects.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid

ORIGIN = "http://127.0.0.1:8877"
EVIDENCE = Path("runtime/example-showcase/evidence")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    token = os.environ.get("SCHEDULER_CONTROL_TOKEN", "")
    if len(token) < 32:
        raise ValueError("SCHEDULER_CONTROL_TOKEN required")
    run = EVIDENCE / (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    ledger = []

    def call(label: str, path: str, body=None):
        request_raw = None if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
        if request_raw is not None:
            headers.update({"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())})
        request = urllib.request.Request(ORIGIN + path, data=request_raw, headers=headers,
                                         method="GET" if body is None else "POST")
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status, raw = response.status, response.read(1048577)
        if len(raw) > 1048576:
            raise ValueError("oversized response")
        if request_raw is not None:
            (run / (label + ".request.json")).write_bytes(request_raw)
        (run / (label + ".response.json")).write_bytes(raw)
        ledger.append({"step": label, "path": path, "status": status,
                       "request_sha256": sha(request_raw) if request_raw is not None else None,
                       "response_sha256": sha(raw)})
        if status != 200:
            raise ValueError(f"{label}: HTTP {status}; see {run}")
        return json.loads(raw)

    try:
        catalog = call("catalog", "/api/v1/examples")
        for example in catalog["items"]:
            name, intake = example["id"], example["intake"]
            if name not in {"demo-weather", "demo-inventory"}:
                raise ValueError("unexpected example identity")
            draft = call(name + ".draft", "/api/v1/intake/preview", {"intake": intake})
            preview = call(name + ".preview", "/api/v1/plans/preview", {"plan": draft["plan"]})
            if preview["from_revision"] is None:
                call(name + ".import", "/api/v1/intake/import",
                     {"intake": intake, "expected_source_sha256": draft["source_sha256"],
                      "expected_preview": preview, "approved": True})
            plan = call(name + ".stored", "/api/v1/projects/" + name + "/plan")
            if plan["plan_sha256"] != draft["plan_sha256"] or plan["source"]["source_sha256"] != draft["source_sha256"]:
                raise ValueError(name + ": stored plan or source hash mismatch")
            print(f"{name}: {plan['summary']['task_count']} tasks, {plan['summary']['total_estimate_minutes']} minutes effort, {plan['summary']['critical_path_estimate_minutes']} minutes critical path")
        snapshot = call("snapshot", "/api/v1/snapshot")
        if {p["project_id"] for p in snapshot["projects"]} != {"demo-weather", "demo-inventory"}:
            raise ValueError("showcase database contains unexpected projects")
    finally:
        (run / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(f"Raw API evidence: {run}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
