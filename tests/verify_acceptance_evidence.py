"""Read-only integrity gate. Never rewrites manifests or blesses missing bytes."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(directory, current_source=False):
    folder = Path(directory).resolve()
    failures = []
    checked = 0
    manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder):
            failures.append({"path": name, "error": "outside run directory"})
        elif not path.is_file():
            failures.append({"path": name, "error": "missing; evidence rejected"})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append({"path": name, "error": "hash mismatch; evidence rejected"})
        checked += 1
    if current_source:
        report = json.loads((folder/"report.json").read_text())
        for name, expected in report["source_sha256"].items():
            path = (ROOT/name).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                failures.append({"path": name, "error": "current source differs from recorded source"})
            checked += 1
    return {"directory": str(folder), "integrity_passed": not failures, "checked_files": checked, "failures": failures}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--current-source", action="store_true")
    args = parser.parse_args()
    result = verify(args.directory, args.current_source)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["integrity_passed"] else 1)
