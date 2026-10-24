"""Transactional scheduler domain. No network, shell, model, or dashboard dependency."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

TERMINAL = {"completed", "failed", "canceled", "superseded"}
ACTIVE = {"running", "starting", "validating", "recovering"}


class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def stamp(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value, timezone.utc).isoformat()


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path, max_workers=6):
        if not 1 <= max_workers <= 128:
            raise ValueError("max_workers must be between 1 and 128")
        self.path = str(path)
        source = Path(__file__).parent
        self.code_hash = digest({str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in source.rglob("*") if p.is_file() and p.suffix in {".py", ".json"}})
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,
              revision INTEGER NOT NULL,paused INTEGER NOT NULL DEFAULT 0,max_workers INTEGER NOT NULL,
              plan TEXT NOT NULL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS allocations(project TEXT PRIMARY KEY,
              min_workers INTEGER NOT NULL,target_workers INTEGER NOT NULL,reserved_slots INTEGER NOT NULL,
              FOREIGN KEY(project) REFERENCES projects(id));
            CREATE TABLE IF NOT EXISTS revisions(project TEXT NOT NULL,revision INTEGER NOT NULL,
              plan TEXT NOT NULL,hash TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(project,revision));
            CREATE TABLE IF NOT EXISTS tasks(project TEXT NOT NULL,id TEXT NOT NULL,contract TEXT NOT NULL,
              hash TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,started REAL,ended REAL,
              attempt_count INTEGER NOT NULL DEFAULT 0,error TEXT,hold INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY(project,id),FOREIGN KEY(project) REFERENCES projects(id));
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,project TEXT NOT NULL,task TEXT NOT NULL,
              number INTEGER NOT NULL,input TEXT NOT NULL,input_hash TEXT NOT NULL,state TEXT NOT NULL,
              started REAL NOT NULL,due REAL NOT NULL,ended REAL,output TEXT,output_hash TEXT,error TEXT,
              heartbeat REAL NOT NULL,UNIQUE(project,task,number));
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,at REAL NOT NULL,
              kind TEXT NOT NULL,project TEXT,task TEXT,detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests(key TEXT PRIMARY KEY,hash TEXT NOT NULL,response TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS leader(id INTEGER PRIMARY KEY CHECK(id=1),owner TEXT NOT NULL,
              expires REAL NOT NULL,fence INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS attempt_state ON attempts(state);
            ''')
            db.execute("INSERT OR IGNORE INTO settings VALUES('max_workers',?)", (str(max_workers),))
            db.execute("INSERT OR IGNORE INTO settings VALUES('stopped','false')")
            # Add runtime allocations without rewriting canonical plan/revision history.
            for row in db.execute("SELECT id,max_workers,plan FROM projects").fetchall():
                policy = json.loads(row["plan"])["policy"]
                maximum = row["max_workers"]
                db.execute("INSERT OR IGNORE INTO allocations VALUES(?,?,?,?)",
                           (row["id"], min(policy.get("min_workers", 0), maximum),
                            min(policy.get("target_workers", maximum), maximum),
                            min(policy.get("reserved_slots", 0), maximum)))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None, factory=Connection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _allocations(self, db):
        return {r["id"]: dict(r) for r in db.execute(
            "SELECT p.id,p.max_workers,a.min_workers,a.target_workers,a.reserved_slots "
            "FROM projects p JOIN allocations a ON a.project=p.id")}

    def _validate_allocations(self, db, allocations, maximum=None):
        maximum = maximum if maximum is not None else int(db.execute(
            "SELECT value FROM settings WHERE key='max_workers'").fetchone()[0])
        for allocation in allocations.values():
            values = [allocation[k] for k in ("max_workers", "min_workers", "target_workers", "reserved_slots")]
            if any(type(v) is not int or not 0 <= v <= 128 for v in values):
                raise ValueError("allocations must be integers 0..128")
            if not 0 <= values[1] <= values[2] <= values[0] or values[3] > values[0]:
                raise ValueError("require min_workers <= target_workers <= max_workers and reserved_slots <= max_workers")
        if sum(a["reserved_slots"] for a in allocations.values()) > maximum:
            raise Conflict("reserved slots exceed global workers")
        busy = {}
        for row in db.execute("SELECT project,contract FROM tasks WHERE state='running'"):
            busy[row["project"]] = busy.get(row["project"], 0) + json.loads(row["contract"])["resources"]["slots"]
        if sum(max(busy.get(pid, 0), a["reserved_slots"]) for pid, a in allocations.items()) > maximum:
            raise Conflict("active work and reserved slots exceed global workers; wait for work to drain")

    def event(self, db, kind, project=None, task=None, **detail):
        db.execute("INSERT INTO events(at,kind,project,task,detail) VALUES(?,?,?,?,?)",
                   (time.time(), kind, project, task, encoded(detail)))

    def transition(self, db, project, task, state, **values):
        before = db.execute("SELECT state FROM tasks WHERE project=? AND id=?", (project, task)).fetchone()[0]
        fields = {"state": state, **values}
        db.execute("UPDATE tasks SET " + ",".join(f"{key}=?" for key in fields) + " WHERE project=? AND id=?",
                   (*fields.values(), project, task))
        if before != state:
            self.event(db, "transition", project, task, previous=before, state=state)

    def _preview(self, db, plan):
        row = db.execute("SELECT * FROM projects WHERE id=?", (plan["project_id"],)).fetchone()
        old = {t["task_id"]: t for t in json.loads(row["plan"])["tasks"]} if row else {}
        new = {t["task_id"]: t for t in plan["tasks"]}
        return {"project_id": plan["project_id"], "from_revision": row["revision"] if row else None,
                "to_revision": plan["revision"], "added": sorted(new.keys()-old.keys()),
                "removed": sorted(old.keys()-new.keys()),
                "modified": sorted(k for k in old.keys() & new.keys() if digest(old[k]) != digest(new[k])),
                "requires_approval": bool(row), "risk": "material-plan-revision" if row else "initial-dummy-import"}

    def preview(self, plan):
        from .contracts import validate_plan
        plan = validate_plan(plan)
        with self.connect() as db:
            return self._preview(db, plan)

    def apply(self, plan, approved=False, key=None, expected_preview=None):
        from .contracts import validate_plan
        plan = validate_plan(plan)
        with self.transaction() as db:
            request = {"plan": plan, "approved": approved}
            if expected_preview is not None:
                request["expected_preview"] = expected_preview
            if key:
                prior = db.execute("SELECT * FROM requests WHERE key=?", (key,)).fetchone()
                if prior:
                    if prior["hash"] != digest(request):
                        raise Conflict("idempotency key reused")
                    return json.loads(prior["response"])
            diff = self._preview(db, plan)
            if expected_preview is not None and diff != expected_preview:
                raise Conflict("plan preview changed; review again before applying")
            pid, rev = plan["project_id"], plan["revision"]
            current = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
            if current and rev <= current["revision"]:
                raise Conflict("revision must increase; rollback requires a new revision")
            if current and not approved:
                raise Conflict("review preview and explicitly approve this plan revision")
            previous = {r["id"]: r for r in db.execute("SELECT * FROM tasks WHERE project=?", (pid,))}
            new = {t["task_id"]: t for t in plan["tasks"]}
            for tid, task in new.items():
                if tid in previous and previous[tid]["state"] in ACTIVE | {"completed"} and previous[tid]["hash"] != digest(task):
                    raise Conflict(f"{tid}: active/completed contract is immutable; create new task IDs for replacement/split")
                if tid in previous and previous[tid]["state"] == "superseded":
                    raise Conflict(f"{tid}: removed task ID cannot be reused")
            for tid in diff["removed"]:
                if previous[tid]["state"] in ACTIVE | {"completed"}:
                    raise Conflict(f"{tid}: preserve active/completed task in revision")
            allocation = {"max_workers": plan["policy"]["max_workers"],
                          "min_workers": plan["policy"].get("min_workers", 0),
                          "target_workers": plan["policy"].get("target_workers", plan["policy"]["max_workers"]),
                          "reserved_slots": plan["policy"].get("reserved_slots", 0)}
            allocations = self._allocations(db)
            allocations[pid] = allocation
            self._validate_allocations(db, allocations)
            now = time.time()
            if current:
                db.execute("UPDATE projects SET name=?,revision=?,max_workers=?,plan=? WHERE id=?",
                           (plan["display_name"], rev, plan["policy"]["max_workers"], encoded(plan), pid))
            else:
                db.execute("INSERT INTO projects(id,name,revision,max_workers,plan,created) VALUES(?,?,?,?,?,?)",
                           (pid, plan["display_name"], rev, plan["policy"]["max_workers"], encoded(plan), now))
            db.execute("INSERT OR REPLACE INTO allocations VALUES(?,?,?,?)",
                       (pid, allocation["min_workers"], allocation["target_workers"], allocation["reserved_slots"]))
            db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)", (pid, rev, encoded(plan), digest(plan), now))
            for tid, task in new.items():
                if tid not in previous:
                    db.execute("INSERT INTO tasks(project,id,contract,hash,state,created) VALUES(?,?,?,?,?,?)",
                               (pid, tid, encoded(task), digest(task), "queued", now))
                elif previous[tid]["hash"] != digest(task):
                    db.execute("UPDATE tasks SET contract=?,hash=?,state='queued',error=NULL WHERE project=? AND id=?",
                               (encoded(task), digest(task), pid, tid))
            for tid in diff["removed"]:
                self.transition(db, pid, tid, "superseded", ended=now)
            self.event(db, "plan.applied", pid, revision=rev, hash=digest(plan), diff=diff, approved=approved)
            if key:
                db.execute("INSERT INTO requests VALUES(?,?,?)", (key, digest(request), encoded(diff)))
            return diff

    def control(self, action, project=None, task=None, value=None, key=None, actor="local-cli"):
        """Audit runtime controls independently of immutable canonical revisions.

        Min/target workers are dispatch preferences, never idle reservations.
        Reserved slots are hard capacity held even while a project is paused.
        Lower project caps let active work finish; infeasible global reductions
        or reservations are rejected rather than silently canceling that work.
        Integer allocation retains compatibility and clamps min/target to its cap.
        """
        request = {"action": action, "project": project, "task": task, "value": value, "actor": actor}
        with self.transaction() as db:
            if key:
                previous = db.execute("SELECT * FROM requests WHERE key=?", (key,)).fetchone()
                if previous:
                    if previous["hash"] != digest(request):
                        raise Conflict("idempotency key was used for a different request")
                    return json.loads(previous["response"])
            if action in {"pause", "resume", "allocate"}:
                if not db.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                    raise KeyError("unknown project")
                if action == "allocate":
                    allocations = self._allocations(db)
                    allocation = allocations[project]
                    if type(value) is int:
                        allocation.update(max_workers=value,
                                          min_workers=min(allocation["min_workers"], value),
                                          target_workers=min(allocation["target_workers"], value))
                    elif isinstance(value, dict) and value and not (value.keys() - {"max_workers", "min_workers", "target_workers", "reserved_slots"}):
                        allocation.update(value)
                    else:
                        raise ValueError("allocation requires integer max_workers or allocation field object")
                    self._validate_allocations(db, allocations)
                    db.execute("UPDATE projects SET max_workers=? WHERE id=?", (allocation["max_workers"], project))
                    db.execute("UPDATE allocations SET min_workers=?,target_workers=?,reserved_slots=? WHERE project=?",
                               (allocation["min_workers"], allocation["target_workers"], allocation["reserved_slots"], project))
                else:
                    db.execute("UPDATE projects SET paused=? WHERE id=?", (int(action == "pause"), project))
            elif action in {"hold", "unhold", "retry"}:
                row = db.execute("SELECT * FROM tasks WHERE project=? AND id=?", (project, task)).fetchone()
                if not row:
                    raise KeyError("unknown task")
                if action == "retry":
                    if row["state"] not in {"failed", "waiting-review"}:
                        raise Conflict("only failed/review tasks can be retried")
                    self.transition(db, project, task, "queued", error=None, ended=None)
                else:
                    db.execute("UPDATE tasks SET hold=? WHERE project=? AND id=?", (int(action == "hold"), project, task))
            elif action in {"emergency-stop", "start"}:
                db.execute("UPDATE settings SET value=? WHERE key='stopped'", (encoded(action == "emergency-stop"),))
                # Simulation has no external side effects; cancel all active attempts atomically.
                if action == "emergency-stop":
                    for row in db.execute("SELECT * FROM tasks WHERE state='running'").fetchall():
                        self.transition(db, row["project"], row["id"], "canceled", ended=time.time(), error="emergency stop")
                    db.execute("UPDATE attempts SET state='canceled',ended=?,error='emergency stop' WHERE state='running'", (time.time(),))
            elif action == "workers":
                if type(value) is not int or not 1 <= value <= 128:
                    raise ValueError("global workers must be integer 1..128")
                self._validate_allocations(db, self._allocations(db), maximum=value)
                db.execute("UPDATE settings SET value=? WHERE key='max_workers'", (str(value),))
            else:
                raise ValueError("unknown action")
            result = {"ok": True, **request, "updated_at": stamp()}
            self.event(db, "control." + action, project, task, actor=actor, value=value, idempotency_key=key)
            if key:
                db.execute("INSERT INTO requests VALUES(?,?,?)", (key, digest(request), encoded(result)))
            return result

    def tick(self, owner, now=None):
        now = time.time() if now is None else now
        with self.transaction() as db:
            leader = db.execute("SELECT * FROM leader WHERE id=1").fetchone()
            if leader and leader["owner"] != owner and leader["expires"] > now:
                return False
            fence = (leader["fence"] + int(leader["owner"] != owner)) if leader else 1
            if not leader or leader["owner"] != owner:
                self.event(db, "daemon.acquired", owner=owner, fence=fence, simulation_reconciliation="retained persisted attempts")
            db.execute("INSERT OR REPLACE INTO leader VALUES(1,?,?,?)", (owner, now+3, fence))
            for attempt in db.execute("SELECT * FROM attempts WHERE state='running'").fetchall():
                contract = json.loads(attempt["input"])
                if digest(contract) != attempt["input_hash"]:
                    raise Conflict("attempt integrity check failed")
                sim = contract.get("simulation", {})
                timeout = contract.get("timeout_policy", {}).get("execution_seconds", 300)
                elapsed = now-attempt["started"]
                stalled = sim.get("stall_seconds", 0) > elapsed
                warning = contract["estimate_minutes"]*60*contract["timeout_policy"]["warning_multiplier"]
                escalation = contract["estimate_minutes"]*60*contract["timeout_policy"]["escalation_multiplier"]
                for threshold, kind in [(warning, "watchdog.warning"), (escalation, "watchdog.escalation")]:
                    if elapsed >= threshold and now < attempt["due"]:
                        marker = attempt["id"]+":"+kind
                        if not db.execute("SELECT 1 FROM settings WHERE key=?", (marker,)).fetchone():
                            db.execute("INSERT INTO settings VALUES(?, 'true')", (marker,))
                            self.event(db, kind, attempt["project"], attempt["task"], attempt_id=attempt["id"], elapsed_seconds=elapsed,
                                       meaningful_progress=not stalled, action="review warning; no automatic cancellation")
                if stalled and elapsed < timeout:
                    continue
                if now < attempt["due"] and elapsed < timeout:
                    db.execute("UPDATE attempts SET heartbeat=? WHERE id=?", (now, attempt["id"]))
                    continue
                timed_out = attempt["due"]-attempt["started"] >= timeout and elapsed >= timeout
                failed = timed_out or attempt["number"] <= sim.get("fail_attempts", 0)
                error = "execution timeout (synthetic stall)" if timed_out else "injected simulation failure" if failed else None
                output = encoded({"executor": "simulation", "synthetic": True, "attempt_id": attempt["id"],
                                  "result": sim.get("output", "simulation completed"), "error": error})
                state = "failed" if failed else "completed"
                db.execute("UPDATE attempts SET state=?,ended=?,output=?,output_hash=?,error=? WHERE id=?",
                           (state, now, output, hashlib.sha256(output.encode()).hexdigest(), error, attempt["id"]))
                retries = contract.get("timeout_policy", {}).get("max_retries", 0)
                task_state = "retrying" if failed and attempt["number"] <= retries else "waiting-review" if failed else "completed"
                self.transition(db, attempt["project"], attempt["task"], "validating")
                self.transition(db, attempt["project"], attempt["task"], task_state, ended=now if task_state != "retrying" else None, error=error)
                self.event(db, "attempt.finished", attempt["project"], attempt["task"], attempt_id=attempt["id"], state=state,
                           output_hash=hashlib.sha256(output.encode()).hexdigest(), validation="simulation-envelope-only", tokens=None, cost=0)
                if task_state == "retrying":
                    db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", ("retry:"+attempt["project"]+":"+attempt["task"], str(now+min(30, 0.5*2**min(attempt["number"]-1, 6)))))
            stopped = json.loads(db.execute("SELECT value FROM settings WHERE key='stopped'").fetchone()[0])
            projects = {r["id"]: r for r in db.execute("SELECT * FROM projects")}
            tasks = db.execute("SELECT * FROM tasks ORDER BY created,project,id").fetchall()
            for row in tasks:
                if digest(json.loads(row["contract"])) != row["hash"]:
                    raise Conflict("task integrity check failed")
                if row["state"] == "completed":
                    evidence = db.execute("SELECT * FROM attempts WHERE project=? AND task=? AND state='completed' ORDER BY number DESC LIMIT 1", (row["project"], row["id"])).fetchone()
                    if not evidence or evidence["output"] is None or hashlib.sha256(evidence["output"].encode()).hexdigest() != evidence["output_hash"]:
                        raise Conflict("completed output integrity check failed; dependent dispatch refused")
            states = {(r["project"], r["id"]): r["state"] for r in tasks}
            ready = []
            for row in tasks:
                if row["state"] in TERMINAL | ACTIVE | {"waiting-review"}:
                    continue
                contract = json.loads(row["contract"])
                if digest(contract) != row["hash"]:
                    raise Conflict("task integrity check failed")
                if row["hold"] or projects[row["project"]]["paused"] or stopped:
                    self.transition(db, row["project"], row["id"], "paused")
                    continue
                if not all(states.get((row["project"], dep)) == "completed" for dep in contract["depends_on"]):
                    self.transition(db, row["project"], row["id"], "dependency-blocked")
                    continue
                retry = db.execute("SELECT value FROM settings WHERE key=?", ("retry:"+row["project"]+":"+row["id"],)).fetchone()
                if retry and float(retry[0]) > now:
                    self.transition(db, row["project"], row["id"], "retrying")
                    continue
                if contract["executor"] != "simulation":
                    self.transition(db, row["project"], row["id"], "waiting-review", error="Codex execution capability gate is unverified; real dispatch disabled")
                    continue
                if contract["validation_profile"] != "simulation-receipt":
                    self.transition(db, row["project"], row["id"], "waiting-review", error="unsupported validation profile; simulation cannot attest arbitrary acceptance criteria")
                    continue
                self.transition(db, row["project"], row["id"], "ready")
                ready.append((row, contract))
            maximum = int(db.execute("SELECT value FROM settings WHERE key='max_workers'").fetchone()[0])
            busy = {}
            for row in db.execute("SELECT project,contract FROM tasks WHERE state='running'"):
                busy[row["project"]] = busy.get(row["project"], 0) + json.loads(row["contract"]).get("resources", {}).get("slots", 1)
            allocations = self._allocations(db)
            # Min/target are preferences; only explicit reservations hold idle slots,
            # including for paused projects. Spare unreserved capacity is backfilled.
            def rank(pair):
                pid = pair[0]["project"]
                allocation = allocations[pid]
                used = busy.get(pid, 0)
                tier = 0 if used < allocation["min_workers"] else 1 if used < allocation["target_workers"] else 2
                return (tier, used/max(1, allocation["max_workers"]),
                        -(pair[1]["priority"] + (now-pair[0]["created"])/60), pid, pair[0]["id"])

            def fits(row, contract):
                pid = row["project"]
                slots = contract["resources"]["slots"]
                if busy.get(pid, 0)+slots > allocations[pid]["max_workers"]:
                    return False
                committed = sum(max(busy.get(other, 0) + (slots if other == pid else 0), a["reserved_slots"])
                                for other, a in allocations.items())
                return committed <= maximum

            # Fair by current utilization inside preference tier; stable IDs break ties.
            while ready and sum(busy.values()) < maximum:
                ready.sort(key=rank)
                chosen = next(((r,c) for r,c in ready if fits(r,c)), None)
                if not chosen:
                    break
                ready.remove(chosen)
                row, contract = chosen
                number = row["attempt_count"]+1
                aid = str(uuid.uuid4())
                duration = max(contract.get("simulation", {}).get("duration_seconds", 1), contract.get("simulation", {}).get("stall_seconds", 0))
                db.execute("INSERT INTO attempts(id,project,task,number,input,input_hash,state,started,due,heartbeat) VALUES(?,?,?,?,?,?,'running',?,?,?)",
                           (aid, row["project"], row["id"], number, row["contract"], row["hash"], now, now+duration, now))
                self.transition(db, row["project"], row["id"], "starting")
                self.transition(db, row["project"], row["id"], "running", started=row["started"] or now, ended=None, attempt_count=number)
                self.event(db, "attempt.started", row["project"], row["id"], attempt_id=aid, number=number, input_hash=row["hash"], fence=fence,
                           code_sha256=self.code_hash, python=sys.version, model=contract["model"], executor="simulation", owner=owner,
                           schema_version="1.0", cost=0, tokens=None)
                busy[row["project"]] = busy.get(row["project"], 0)+contract.get("resources", {}).get("slots", 1)
            return True

    def release(self, owner):
        with self.transaction() as db:
            db.execute("UPDATE leader SET expires=0 WHERE owner=?", (owner,))
            self.event(db, "daemon.released", owner=owner)

    def snapshot(self):
        with self.transaction() as db:
            projects = []
            allocations = self._allocations(db)
            for p in db.execute("SELECT * FROM projects ORDER BY id").fetchall():
                tasks = []
                for row in db.execute("SELECT * FROM tasks WHERE project=? ORDER BY created,id", (p["id"],)):
                    contract = json.loads(row["contract"])
                    tasks.append({**contract, "state": row["state"], "started_at": stamp(row["started"]) if row["started"] else None,
                                  "ended_at": stamp(row["ended"]) if row["ended"] else None, "attempt_count": row["attempt_count"],
                                  "error": row["error"], "tokens": None, "held": bool(row["hold"])})
                allocation = allocations[p["id"]]
                busy_slots = sum(t["resources"]["slots"] for t in tasks if t["state"] == "running")
                allocated = max(busy_slots, allocation["reserved_slots"])
                counts = {"allocated": allocated, "busy": busy_slots,
                          "ready": sum(t["resources"]["slots"] for t in tasks if t["state"] == "ready"),
                          "blocked": sum(t["resources"]["slots"] for t in tasks if t["state"] in {"dependency-blocked", "waiting-review", "paused"}),
                          "idle": max(0, allocated-busy_slots)}
                projects.append({"project_id": p["id"], "display_name": p["name"], "revision": p["revision"],
                                 "paused": bool(p["paused"]), "max_workers": p["max_workers"], "tasks": tasks,
                                 "min_workers": allocation["min_workers"], "target_workers": allocation["target_workers"],
                                 "reserved_slots": allocation["reserved_slots"], **counts})
            events = [{**dict(r), "at": stamp(r["at"]), "detail": json.loads(r["detail"])} for r in db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT 200")]
            tasks = [t for p in projects for t in p["tasks"]]
            busy = sum(t.get("resources", {}).get("slots", 1) for t in tasks if t["state"] == "running")
            maximum = int(db.execute("SELECT value FROM settings WHERE key='max_workers'").fetchone()[0])
            leader = db.execute("SELECT * FROM leader WHERE id=1").fetchone()
            return {"updated_at": stamp(), "max_workers": maximum, "workers": busy, "projects": projects,
                    "events": events, "stopped": json.loads(db.execute("SELECT value FROM settings WHERE key='stopped'").fetchone()[0]),
                    "daemon": {"healthy": bool(leader and leader["expires"] > time.time()), "lease_expires_at": stamp(leader["expires"]) if leader else None},
                    "metrics": {"allocated": sum(p["allocated"] for p in projects),
                                "reserved_slots": sum(p["reserved_slots"] for p in projects),
                                "unallocated": max(0, maximum-sum(p["allocated"] for p in projects)),
                                "blocked": sum(p["blocked"] for p in projects), "busy": busy, "idle": max(0, maximum-busy), "total": len(tasks),
                                "completed": sum(t["state"] == "completed" for t in tasks),
                                "ready": sum(t["state"] == "ready" for t in tasks),
                                "warnings": sum(t["state"] in {"failed", "waiting-review", "recovering"} for t in tasks),
                                "utilization": busy/maximum, "token_accounting": "unavailable", "forecast_confidence": "simulation-only"}}

    def trace(self, project, task):
        with self.connect() as db:
            attempts = [dict(r) for r in db.execute("SELECT * FROM attempts WHERE project=? AND task=? ORDER BY number", (project, task))]
            for a in attempts:
                if hashlib.sha256(a["input"].encode()).hexdigest() != a["input_hash"]:
                    raise Conflict("input integrity failure")
                if a["output"] is not None and hashlib.sha256(a["output"].encode()).hexdigest() != a["output_hash"]:
                    raise Conflict("output integrity failure")
            return {"project_id": project, "task_id": task, "attempts": attempts, "updated_at": stamp()}
