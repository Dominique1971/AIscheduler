"""Preserve fresh CLI traces and integrity metadata for the dummy showcase."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "runtime/example-showcase/scheduler.sqlite"
EVIDENCE = ROOT / "evidence/example-showcase/20261024T190729Z-3725e490"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    snapshot = json.loads((EVIDENCE / "final-snapshot.json").read_bytes())
    projects = {p["project_id"]: p for p in snapshot["projects"]}
    if set(projects) != {"demo-weather", "demo-inventory"}:
        raise ValueError("unexpected project in isolated evidence")
    attempt_times = {}
    for project in projects.values():
        if len(project["tasks"]) != 6:
            raise ValueError("expected six tasks per project")
        for task in project["tasks"]:
            if task["state"] != "completed" or task["executor"] != "simulation":
                raise ValueError("simulation task did not complete")
            name = f"trace-{project['project_id']}-{task['task_id']}"
            process = subprocess.run([sys.executable, "-m", "scheduler", "--db", str(DB),
                                      "trace", project["project_id"], task["task_id"]],
                                     cwd=ROOT, capture_output=True, check=False)
            (EVIDENCE / (name + ".stdout.json")).write_bytes(process.stdout)
            (EVIDENCE / (name + ".stderr.txt")).write_bytes(process.stderr)
            if process.returncode:
                raise ValueError(name + " CLI trace failed")
            attempts = json.loads(process.stdout)["attempts"]
            if len(attempts) != 1 or attempts[0]["state"] != "completed":
                raise ValueError(name + " has unexpected attempt history")
            attempt = attempts[0]
            if sha(attempt["input"].encode()) != attempt["input_hash"] or sha(attempt["output"].encode()) != attempt["output_hash"]:
                raise ValueError(name + " input/output hash mismatch")
            attempt_times[(project["project_id"], task["task_id"])] = (attempt["started"], attempt["ended"])
    for project in projects.values():
        for task in project["tasks"]:
            start = attempt_times[(project["project_id"], task["task_id"])][0]
            for dependency in task["depends_on"]:
                end = attempt_times[(project["project_id"], dependency)][1]
                if start < end:
                    raise ValueError("dependency precedence failure")
    bridge = [json.loads(line) for line in (EVIDENCE / "bridge.jsonl").read_text().splitlines()]
    if not any(row["kind"] == "site.poll" and row.get("http_status") == 200 for row in bridge):
        raise ValueError("no successful hosted bridge poll")
    sources = ["scheduler/core.py", "scheduler/api.py", "scheduler/intake.py",
               "scheduler/examples/demo-weather.yaml", "scheduler/examples/demo-inventory.yaml",
               "remote/bridge.py", "sites/scheduler-dashboard/worker/contract.mjs",
               "sites/scheduler-dashboard/worker/app.txt"]
    manifest = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "entry_points": ["loopback HTTP /api/v1/examples → intake/preview → plans/preview → intake/import → projects/{id}/plan",
                         "python -m scheduler daemon", "python -m scheduler trace", "remote/bridge.py → private Site /agent/poll"],
        "scope": "Two isolated dummy simulation projects; no real repositories, Codex execution or artifact generation.",
        "project_ids": sorted(projects), "completed_attempts": len(attempt_times),
        "dependency_precedence": "12 task traces checked against all declared edges",
        "integrity": "Raw CLI attempt input/output hashes verified; standalone CLI database verify in verify.json.",
        "model": "none (simulation)", "cost": "not measured; no model call in simulation",
        "hosted_site": {"project_id": "appgprj_6adcbab3ab1c81919496cad194193625",
                        "version": 7, "remote_control_enabled": False,
                        "read_only_totp_bypass": True,
                        "verification": "bridge HTTP 200 and Sites D1 row; signed-in browser rendering unverified"},
        "source_sha256": {name: sha((ROOT / name).read_bytes()) for name in sources},
        "file_sha256": {file.name: sha(file.read_bytes()) for file in sorted(EVIDENCE.iterdir()) if file.is_file() and file.name != "manifest.json"},
    }
    (EVIDENCE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(attempt_times)} untouched attempts and {len(manifest['file_sha256'])} evidence files: {EVIDENCE}")


if __name__ == "__main__":
    main()
