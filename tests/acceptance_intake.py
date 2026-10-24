"""Fresh black-box project-intake CLI trial with disposable simulation only."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "intake-demo-weather.yaml"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "evidence" / "intake" / run_id
    folder.mkdir(parents=True)
    source = folder / SOURCE.name
    shutil.copy2(SOURCE, source)
    plan = folder / "proposed-plan.json"
    db = folder / "scheduler.sqlite"
    commands = [
        ("intake", [sys.executable, "-m", "scheduler", "intake", str(source), "--output", str(plan)]),
        ("validate", [sys.executable, "-m", "scheduler", "validate", str(plan)]),
        ("preview", [sys.executable, "-m", "scheduler", "--db", str(db), "preview", str(plan)]),
        ("import", [sys.executable, "-m", "scheduler", "--db", str(db), "import", str(plan)]),
        ("daemon", [sys.executable, "-m", "scheduler", "--db", str(db), "daemon", "--workers", "2",
                    "--interval", "0.05", "--run-seconds", "1.5"]),
        ("snapshot", [sys.executable, "-m", "scheduler", "--db", str(db), "snapshot"]),
    ]
    receipts = []
    result = "red_or_unrun"
    try:
        for label, argv in commands:
            run = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=20)
            (folder / f"{label}.stdout.raw").write_bytes(run.stdout)
            (folder / f"{label}.stderr.raw").write_bytes(run.stderr)
            receipts.append({"entry_point": " ".join(argv[:4]), "label": label, "exit_code": run.returncode})
            if run.returncode:
                raise RuntimeError(f"{label} exited {run.returncode}")
        intake = json.loads((folder / "intake.stdout.raw").read_bytes())
        provenance = json.loads((folder / "proposed-plan.json.provenance.json").read_bytes())
        proposed = json.loads(plan.read_bytes())
        snapshot = json.loads((folder / "snapshot.stdout.raw").read_bytes())
        projects = snapshot["projects"]
        if len(projects) != 1 or projects[0]["project_id"] != "intake-demo-weather":
            raise RuntimeError("unexpected project snapshot")
        tasks = {task["task_id"]: task for task in projects[0]["tasks"]}
        if set(tasks) != {"observations", "averages", "chart"}:
            raise RuntimeError("task identity mismatch")
        if any(task["state"] != "completed" for task in tasks.values()):
            raise RuntimeError("not all synthetic tasks completed")
        if tasks["averages"]["depends_on"] != ["observations"] or tasks["chart"]["depends_on"] != ["observations"]:
            raise RuntimeError("dependency mismatch")
        if intake["summary"]["total_estimate_minutes"] != 9 or intake["summary"]["critical_path_estimate_minutes"] != 7:
            raise RuntimeError("estimate mismatch")
        if provenance["source_sha256"] != digest(source):
            raise RuntimeError("source integrity mismatch")
        canonical = json.dumps(proposed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        if provenance["plan_sha256"] != hashlib.sha256(canonical).hexdigest():
            raise RuntimeError("provenance mismatch")
        connection = sqlite3.connect(db)
        try:
            attempts = connection.execute("SELECT task,started,ended FROM attempts WHERE project=?",
                                          ("intake-demo-weather",)).fetchall()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()
        times = {task: (started, ended) for task, started, ended in attempts}
        if len(times) != 3 or any(times[child][0] < times["observations"][1]
                                  for child in ("averages", "chart")):
            raise RuntimeError("dependency precedence mismatch")
        result = "green_intake_and_simulation_only"
    except Exception as exc:
        result = "red: " + type(exc).__name__ + ": " + str(exc)
    files = [path for path in folder.iterdir() if path.is_file()]
    manifest = {
        "run_id": run_id, "entry_point": "python tests/acceptance_intake.py",
        "test_class": "fresh project intake CLI -> draft -> validate -> preview -> import -> simulation daemon -> snapshot; real generator unrun",
        "commands": receipts,
        "source_sha256": digest(SOURCE),
        "code_sha256": {str(path.relative_to(ROOT)): digest(path) for path in
                        [ROOT / "scheduler/intake.py", ROOT / "scheduler/__main__.py",
                         ROOT / "scheduler/schemas/intake-1.0.schema.json", ROOT / "scheduler/core.py",
                         ROOT / "tests/acceptance_intake.py"]},
        "file_sha256": {path.name: digest(path) for path in files},
        "cost": "no model call; local simulation only", "result": result,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "result": result, "evidence": str(folder)}))
    return 0 if result == "green_intake_and_simulation_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
