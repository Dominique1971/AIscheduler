"""HTTP TestClient diagnostics; no deployed service, phone or MFA acceptance."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from fastapi.testclient import TestClient
import pytest

from scheduler.api import create_app
from scheduler.contracts import load_plan
from scheduler.core import Store
from scheduler.intake import load_intake

ROOT = Path(__file__).resolve().parents[1]
READ = "diagnostic-reader-" + "r" * 40
CONTROL = "diagnostic-controller-" + "c" * 40


@pytest.fixture
def plan():
    return load_plan(ROOT / "examples/demo-weather.yaml")


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "api-diagnostic.sqlite3")


@pytest.fixture
def client(store, monkeypatch):
    monkeypatch.delenv("SCHEDULER_TOKEN_EXPIRES_AT", raising=False)
    return TestClient(create_app(store, read_token=READ, control_token=CONTROL))


def headers(token=CONTROL, key="diagnostic-request"):
    return {"Authorization": "Bearer " + token, "Idempotency-Key": key}


@pytest.mark.parametrize("path,body", [("/plans/validate", []), ("/system/start", []), ("/projects/demo-weather/allocate", {"max_worker": 3})])
def test_invalid_body_shape_and_unknown_fields_are_client_errors(client, path, body):
    response = client.post("/api/v1"+path, headers=headers(), json=body)
    assert response.status_code == 422


def test_anonymous_rejected_reader_sees_state_but_cannot_control(client, store, plan):
    store.apply(plan)
    assert client.get("/api/v1/snapshot").status_code == 401
    reader = client.get("/api/v1/snapshot", headers=headers(READ))
    assert reader.status_code == 200 and reader.json()["role"] == "reader"
    assert client.post("/api/v1/projects/demo-weather/pause", headers=headers(READ), json={}).status_code == 403
    assert store.snapshot()["projects"][0]["paused"] is False


def test_controls_require_idempotency_and_replay_exact_response(client, store, plan):
    store.apply(plan)
    url = "/api/v1/projects/demo-weather/pause"
    assert client.post(url, headers={"Authorization": "Bearer " + CONTROL}, json={}).status_code == 400
    first = client.post(url, headers=headers(), json={})
    second = client.post(url, headers=headers(), json={})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert client.post("/api/v1/projects/demo-weather/resume", headers=headers(), json={}).status_code == 409


def test_plan_apply_replay_and_key_mismatch(client, store, plan):
    body = {"plan": plan}
    first = client.post("/api/v1/plans/apply", headers=headers(), json=body)
    second = client.post("/api/v1/plans/apply", headers=headers(), json=body)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    body["plan"]["display_name"] = "Changed"
    assert client.post("/api/v1/plans/apply", headers=headers(), json=body).status_code == 409


def test_intake_preview_is_authenticated_draft_without_project_mutation(client, store):
    intake, _ = load_intake(ROOT / "examples/intake-demo-weather.yaml")
    url = "/api/v1/intake/preview"
    assert client.post(url, headers=headers(READ), json={"intake": intake}).status_code == 403
    response = client.post(url, headers=headers(), json={"intake": intake})
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["critical_path_estimate_minutes"] == 7
    assert response.json()["status"].startswith("draft_only")
    assert hashlib.sha256(response.json()["source_text"].encode()).hexdigest() == response.json()["source_sha256"]
    assert response.json()["source_kind"] == "canonical-json-intake/1"
    assert store.snapshot()["projects"] == []
    intake["tasks"][1]["depends_on"] = ["unknown"]
    assert client.post(url, headers=headers(), json={"intake": intake}).status_code == 422


def test_cross_origin_and_dns_rebinding_rejected(client):
    for origin in ["https://evil.invalid", "null", "http://localhost"]:
        assert client.get("/api/v1/snapshot", headers={**headers(), "Origin": origin}).status_code == 403
    assert client.get("/api/v1/snapshot", headers={**headers(), "Host": "evil.invalid"}).status_code == 400
    assert client.get("/api/v1/snapshot", headers={**headers(), "Origin": "http://testserver"}).status_code == 200


def test_security_headers_and_pagination(client):
    response = client.get("/api/v1/snapshot", headers=headers())
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/api/v1/projects?limit=101", headers=headers()).status_code == 422
    assert client.get("/api/v1/projects?offset=-1", headers=headers()).status_code == 422


def test_emergency_stop_requires_explicit_confirmation(client, store, plan):
    store.apply(plan)
    assert client.post("/api/v1/system/emergency-stop", headers=headers(), json={}).status_code == 400
    assert store.snapshot()["stopped"] is False
    response = client.post("/api/v1/system/emergency-stop", headers=headers(), json={"confirmed": True})
    assert response.status_code == 200 and store.snapshot()["stopped"] is True


def test_expired_tokens_rejected(store, monkeypatch):
    monkeypatch.setenv("SCHEDULER_TOKEN_EXPIRES_AT", "1")
    client = TestClient(create_app(store, read_token=READ, control_token=CONTROL))
    assert client.get("/api/v1/snapshot", headers=headers()).status_code == 401


def test_invalid_configuration_fails_closed(store):
    with pytest.raises(ValueError):
        create_app(store, control_token="short")
    with pytest.raises(ValueError):
        create_app(store, read_token=CONTROL, control_token=CONTROL)


def test_malformed_content_length_is_client_error(store):
    client = TestClient(create_app(store, read_token=READ, control_token=CONTROL), raise_server_exceptions=False)
    response = client.get("/api/v1/snapshot", headers={**headers(), "Content-Length": "invalid"})
    assert 400 <= response.status_code < 500


def test_concurrent_identical_plan_requests_replay_once(client, store, plan, monkeypatch):
    """Synchronize first-import requests after replay checks to expose atomicity."""
    original = store.apply
    rendezvous = Barrier(2)

    def synchronized_apply(*args, **kwargs):
        rendezvous.wait(timeout=10)
        return original(*args, **kwargs)

    monkeypatch.setattr(store, "apply", synchronized_apply)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post("/api/v1/plans/apply", headers=headers(), json={"plan": plan}), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM revisions").fetchone()[0] == 1
