"""Core fixture diagnostics. These are not fresh CLI or real-generator acceptance."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import time

import pytest

from scheduler.contracts import load_plan
from scheduler.core import Conflict, Store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plan():
    return load_plan(ROOT / "examples/demo-weather.yaml")


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "diagnostic.sqlite3", max_workers=4)


def task_states(store):
    return {t["task_id"]: t["state"] for t in store.snapshot()["projects"][0]["tasks"]}


def test_two_projects_complete_with_precedence_and_bounded_retries(store, plan):
    store.apply(plan)
    store.apply(load_plan(ROOT / "examples/demo-inventory.yaml"))
    start = time.time()
    for step in range(40):
        store.tick("diagnostic", now=start + step * .1)
        assert store.snapshot()["workers"] <= 4
    snap = store.snapshot()
    assert snap["metrics"]["completed"] == 12
    for project in snap["projects"]:
        for task in project["tasks"]:
            trace = store.trace(project["project_id"], task["task_id"])["attempts"]
            assert len(trace) == (2 if task["task_id"] == "transform" else 1)
            for dep in task["depends_on"]:
                predecessor = store.trace(project["project_id"], dep)["attempts"][-1]
                assert predecessor["state"] == "completed"
                assert predecessor["ended"] <= trace[0]["started"]


def test_restart_retains_attempt_and_fences_competing_owner(store, plan):
    store.apply(plan)
    start = time.time()
    assert store.tick("first", now=start)
    original = store.trace(plan["project_id"], "source")["attempts"][0]["id"]
    reopened = Store(store.path)
    assert not reopened.tick("second", now=start + .05)
    assert reopened.trace(plan["project_id"], "source")["attempts"][0]["id"] == original
    assert reopened.tick("second", now=start + 3.1)
    assert not store.tick("first", now=start + 3.2)
    trace = reopened.trace(plan["project_id"], "source")["attempts"]
    assert len(trace) == 1 and trace[0]["id"] == original and trace[0]["state"] == "completed"


def test_concurrent_dispatch_has_one_leader_and_attempt(store, plan):
    store.apply(plan)
    now = time.time()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda n: Store(store.path).tick(f"owner-{n}", now=now), range(8)))
    assert sum(results) == 1
    assert len(store.trace(plan["project_id"], "source")["attempts"]) == 1


def test_pause_keeps_active_work_and_prevents_backfill(store, plan):
    store.apply(plan)
    now = time.time()
    store.tick("owner", now=now)
    store.control("pause", plan["project_id"])
    store.tick("owner", now=now + .2)
    states = task_states(store)
    assert states["source"] == "completed"
    assert all(value == "paused" for key, value in states.items() if key != "source")
    store.control("resume", plan["project_id"])
    store.tick("owner", now=now + .21)
    assert task_states(store)["transform"] == "running"


def test_completed_revision_survives_split_and_active_edits_are_rejected(store, plan):
    store.apply(plan)
    now = time.time()
    store.tick("owner", now=now)
    store.tick("owner", now=now + .13)
    before = store.trace(plan["project_id"], "source")
    revised = deepcopy(plan)
    revised["revision"] = 2
    original_tail = revised["tasks"].pop()
    first = deepcopy(original_tail)
    first.update(task_id="publish-part-a")
    second = deepcopy(original_tail)
    second.update(task_id="publish-part-b", depends_on=["publish-part-a"])
    revised["tasks"].extend([first, second])
    preview = store.preview(revised)
    assert preview["added"] == ["publish-part-a", "publish-part-b"]
    assert preview["removed"] == ["publish"]
    with pytest.raises(Conflict, match="approve"):
        store.apply(revised)
    store.apply(revised, approved=True)
    assert task_states(store)["publish"] == "superseded"
    assert store.trace(plan["project_id"], "source")["attempts"] == before["attempts"]
    assert task_states(store)["source"] == "completed"
    unsafe = deepcopy(revised)
    unsafe["revision"] = 3
    unsafe["tasks"][1]["description"] = "rewrite an active contract"
    with pytest.raises(Conflict, match="immutable"):
        store.apply(unsafe, approved=True)


def test_cannot_remove_or_rewrite_completed_task(store, plan):
    store.apply(plan)
    now = time.time()
    store.tick("owner", now=now)
    store.control("pause", plan["project_id"])
    store.tick("owner", now=now + .13)
    revised = deepcopy(plan)
    revised["revision"] = 2
    revised["tasks"][0]["description"] = "changed result contract"
    with pytest.raises(Conflict, match="immutable"):
        store.apply(revised, approved=True)
    revised["tasks"] = [t for t in revised["tasks"] if t["task_id"] != "source"]
    for task in revised["tasks"]:
        task["depends_on"] = [dep for dep in task["depends_on"] if dep != "source"]
    with pytest.raises(Conflict, match="preserve"):
        store.apply(revised, approved=True)


@pytest.mark.parametrize("location", ["contract", "attempt-input", "attempt-output"])
def test_fault_injection_integrity_rejects_corruption(store, plan, location):
    """Tampering is confined to a disposable DB and never adopted as real output."""
    store.apply(plan)
    now = time.time()
    store.tick("owner", now=now)
    with store.transaction() as db:
        if location == "contract":
            db.execute("UPDATE tasks SET contract=replace(contract,'Transform','Corrupted') WHERE id='transform'")
        elif location == "attempt-input":
            db.execute("UPDATE attempts SET input=replace(input,'Source','Corrupted')")
    if location == "attempt-output":
        store.tick("owner", now=now + .13)
        with store.transaction() as db:
            db.execute("UPDATE attempts SET output='corrupted' WHERE task='source'")
        with pytest.raises(Conflict, match="integrity"):
            store.trace(plan["project_id"], "source")
    else:
        with pytest.raises(Conflict, match="integrity"):
            store.tick("owner", now=now + .13)


def test_corrupted_predecessor_cannot_admit_dependents(store, plan):
    """Negative diagnostic: intact completion labels alone cannot certify output."""
    store.apply(plan)
    now = time.time()
    store.tick("owner", now=now)
    store.control("pause", plan["project_id"])
    store.tick("owner", now=now + .13)
    with store.transaction() as db:
        db.execute("UPDATE attempts SET output='changed' WHERE task='source'")
    store.control("resume", plan["project_id"])
    with pytest.raises(Conflict, match="integrity"):
        store.tick("owner", now=now + .14)


def test_timeout_retry_budget_escalates_and_emergency_stop_is_durable(store, plan):
    plan["tasks"][0]["simulation"].update(stall_seconds=100)
    plan["tasks"][0]["timeout_policy"].update(execution_seconds=1, max_retries=1)
    store.apply(plan)
    now = time.time()
    for step in range(4):
        store.tick("owner", now=now + step * 1.1)
    assert task_states(store)["source"] == "waiting-review"
    assert len(store.trace(plan["project_id"], "source")["attempts"]) == 2
    store.control("emergency-stop")
    assert Store(store.path).snapshot()["stopped"] is True


def test_control_idempotency_replays_without_duplicate_audit(store, plan):
    store.apply(plan)
    first = store.control("pause", plan["project_id"], key="one")
    assert store.control("pause", plan["project_id"], key="one") == first
    events = [e for e in store.snapshot()["events"] if e["kind"] == "control.pause"]
    assert len(events) == 1
    with pytest.raises(Conflict, match="different request"):
        store.control("resume", plan["project_id"], key="one")


def test_codex_contract_is_held_at_unverified_dispatch_gate(store, plan):
    plan["tasks"][0]["executor"] = "codex-cli"
    del plan["tasks"][0]["simulation"]
    store.apply(plan)
    store.tick("owner")
    assert task_states(store)["source"] == "waiting-review"
    assert store.trace(plan["project_id"], "source")["attempts"] == []


def test_emergency_stop_cancels_active_simulation_without_restart_dispatch(store, plan):
    store.apply(plan)
    now = time.time()
    store.tick("owner", now=now)
    assert store.snapshot()["workers"] == 1
    store.control("emergency-stop")
    assert task_states(store)["source"] == "canceled"
    restarted = Store(store.path)
    restarted.tick("replacement", now=now + 5)
    assert restarted.snapshot()["workers"] == 0
    assert restarted.trace(plan["project_id"], "source")["attempts"][0]["state"] == "canceled"
