"""Intake diagnostics; generated plans are drafts, not generator acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scheduler.intake import build_intake, load_intake


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "intake-demo-weather.yaml"


class IntakeTests(unittest.TestCase):
    def test_normal_cli_draft_and_canonical_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "proposed-plan.json"
            command = [sys.executable, "-m", "scheduler", "intake", str(EXAMPLE), "--output", str(output)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report["summary"]["total_estimate_minutes"], 9)
            self.assertEqual(report["summary"]["critical_path_estimate_minutes"], 7)
            self.assertEqual(report["status"], "draft_only; explicit preview and import required")
            self.assertEqual(report["summary"]["tasks"][2]["depends_on"], ["observations"])
            provenance = json.loads((Path(str(output) + ".provenance.json")).read_text())
            self.assertEqual(provenance["source_sha256"], hashlib.sha256(EXAMPLE.read_bytes()).hexdigest())
            self.assertIn("tasks[0].executor", provenance["defaults_applied"])
            validated = subprocess.run([sys.executable, "-m", "scheduler", "validate", str(output)],
                                       cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(validated.returncode, 0, validated.stderr)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already exists", second.stderr)

    def test_invalid_dependencies_and_unknown_fields_are_rejected(self):
        value, source_hash = load_intake(EXAMPLE)
        value["tasks"][1]["depends_on"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "unresolved dependency"):
            build_intake(value, source_hash)
        value["tasks"][1]["depends_on"] = ["chart"]
        value["tasks"][2]["depends_on"] = ["averages"]
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            build_intake(value, source_hash)
        value["tasks"][2]["unexpected"] = "silently ignored?"
        with self.assertRaisesRegex(ValueError, "unknown field"):
            build_intake(value, source_hash)

    def test_authored_estimate_and_description_preserved(self):
        value, source_hash = load_intake(EXAMPLE)
        value["tasks"][0]["estimate_minutes"] = 13
        value["tasks"][0]["description"] = "exact authored wording"
        built = build_intake(value, source_hash)
        self.assertEqual(built["plan"]["tasks"][0]["estimate_minutes"], 13)
        self.assertEqual(built["plan"]["tasks"][0]["description"], "exact authored wording")
        self.assertEqual(built["summary"]["critical_path_estimate_minutes"], 16)

    def test_duplicate_keys_and_aliases_rejected_in_authored_source(self):
        original = EXAMPLE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad-intake.yaml"
            source.write_text(original.replace('project_id: intake-demo-weather',
                                               'project_id: intake-demo-weather\nproject_id: another-id'), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate field"):
                load_intake(source)
            source.write_text(original.replace('depends_on: []', 'depends_on: *missing', 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "YAML aliases are unsupported"):
                load_intake(source)


if __name__ == "__main__":
    unittest.main()
