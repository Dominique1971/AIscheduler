"""Markdown intake parser and HTTP diagnostics; not browser acceptance."""
import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from scheduler.api import create_app
from scheduler.core import Store
from scheduler.intake import build_intake, parse_markdown_intake

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "scheduler/static/intake-template.md").read_text(encoding="utf-8")
TOKEN = "markdown-diagnostic-" + "m" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN, "Idempotency-Key": "markdown-diagnostic"}


def test_markdown_template_has_valid_fork_join_and_preserves_authored_facts():
    intake = parse_markdown_intake(TEMPLATE)
    draft = build_intake(intake, hashlib.sha256(TEMPLATE.encode()).hexdigest(), source_kind="markdown-intake/1")
    assert draft["summary"]["task_count"] == 4
    assert draft["summary"]["total_estimate_minutes"] == 12
    assert draft["summary"]["critical_path_estimate_minutes"] == 10
    assert draft["summary"]["tasks"][-1]["depends_on"] == ["check", "summarize"]


@pytest.mark.parametrize("changed", [
    TEMPLATE.replace("Maximum workers: 2", "Maximum workers: maybe"),
    TEMPLATE.replace("Estimate minutes: 4", "Estimate minutes: later"),
    TEMPLATE.replace("Depends on: check, summarize", "Depends on: missing"),
    TEMPLATE.replace("Depends on: none", "Depends on: review"),
    TEMPLATE.replace("Acceptance criteria:\n- The outline references both preceding specifications.", "Acceptance criteria:"),
    TEMPLATE + "\n## Unrecognized work\nSomething important\n",
    "\ufeff" + TEMPLATE,
])
def test_invalid_or_unmapped_markdown_is_rejected(changed):
    with pytest.raises(ValueError):
        intake = parse_markdown_intake(changed)
        build_intake(intake, "0" * 64)


def test_exact_markdown_file_preview_and_import_records_raw_source(tmp_path):
    store = Store(tmp_path / "markdown.sqlite")
    client = TestClient(create_app(store, control_token=TOKEN))
    body = {"filename": "sample.md", "source_text": TEMPLATE}
    assert client.post("/api/v1/intake/file/preview", json=body).status_code == 401
    draft_response = client.post("/api/v1/intake/file/preview", headers=HEADERS, json=body)
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()
    assert draft["source_text"] == TEMPLATE
    assert draft["source_sha256"] == hashlib.sha256(TEMPLATE.encode()).hexdigest()
    preview = client.post("/api/v1/plans/preview", headers=HEADERS, json={"plan": draft["plan"]}).json()
    import_body = {**body, "expected_source_sha256": draft["source_sha256"],
                   "expected_preview": preview, "approved": True}
    assert client.post("/api/v1/intake/file/import", headers=HEADERS,
                       json={**import_body, "source_text": TEMPLATE + "\n"}).status_code == 409
    imported = client.post("/api/v1/intake/file/import", headers=HEADERS, json=import_body)
    assert imported.status_code == 200, imported.text
    stored = client.get("/api/v1/projects/dummy-sample-project/plan", headers=HEADERS)
    assert stored.status_code == 200
    assert stored.json()["source"]["source_sha256"] == draft["source_sha256"]
    with store.connect() as db:
        source = db.execute("SELECT source FROM intake_sources WHERE project=?", ("dummy-sample-project",)).fetchone()[0]
    assert source == TEMPLATE
