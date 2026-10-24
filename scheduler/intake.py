"""Versioned, deterministic description-to-plan draft transformation.

No model call, repository access, database mutation, or execution occurs here.
Authored task facts are preserved; every operational default is reported.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import yaml

from .contracts import _StrictLoader, _check, _locations, validate_plan
from .core import digest


SCHEMA_PATH = Path(__file__).parent / "schemas" / "intake-1.0.schema.json"
TRANSFORM_VERSION = "intake-to-plan/1"
POLICY_DEFAULTS = {"max_workers": 1, "min_workers": 0, "target_workers": 1,
                   "reserved_slots": 0, "merge": "manual", "full_regression": "manual"}


def plan_summary(plan: dict) -> dict:
    """Summarize an authored canonical DAG without claiming a delivery forecast."""
    plan = validate_plan(plan)
    by_id = {task["task_id"]: task for task in plan["tasks"]}
    successors = {task_id: [] for task_id in by_id}
    remaining = {task_id: len(task["depends_on"]) for task_id, task in by_id.items()}
    for task_id, task in by_id.items():
        for dependency in task["depends_on"]:
            successors[dependency].append(task_id)
    longest, layers = {}, {}
    ready = [task_id for task_id, count in remaining.items() if count == 0]
    while ready:
        task_id = ready.pop()
        task = by_id[task_id]
        longest[task_id] = task["estimate_minutes"] + max((longest[dep] for dep in task["depends_on"]), default=0)
        layers[task_id] = 1 + max((layers[dep] for dep in task["depends_on"]), default=0)
        for successor in successors[task_id]:
            remaining[successor] -= 1
            if remaining[successor] == 0:
                ready.append(successor)
    return {"project_id": plan["project_id"], "description": plan["goal"],
            "task_count": len(by_id),
            "total_estimate_minutes": sum(task["estimate_minutes"] for task in plan["tasks"]),
            "critical_path_estimate_minutes": max(longest.values()),
            "estimate_note": "Authored estimates only; excludes review, retries and overhead. Not a forecast.",
            "tasks": [{"task_id": task["task_id"], "title": task["title"],
                       "description": task["description"], "estimate_minutes": task["estimate_minutes"],
                       "depends_on": task["depends_on"], "dependency_layer": layers[task["task_id"]],
                       "executor": task["executor"], "acceptance_criteria": task["acceptance_criteria"]}
                      for task in plan["tasks"]]}


def load_intake(path: str | Path) -> tuple[dict, str]:
    source = Path(path)
    raw = source.read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError(f"{source}: intake exceeds 2 MiB")
    source_hash = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
        depth = 0
        for event in yaml.parse(text):
            if isinstance(event, yaml.AliasEvent):
                raise ValueError(f"line {event.start_mark.line + 1}: YAML aliases are unsupported")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 32:
                    raise ValueError(f"line {event.start_mark.line + 1}: nesting exceeds 32 levels")
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        node = yaml.compose(text, Loader=_StrictLoader)
        locations = _locations(node) if node else {"$": 1}
        value = yaml.load(text, Loader=_StrictLoader)
        _check(value, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
        return value, source_hash
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source}: invalid UTF-8") from exc
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark else 1
        raise ValueError(f"{source}:line {line}: invalid YAML: {exc}") from exc
    except ValueError as exc:
        match = re.match(r"(\$[^:]*):", str(exc))
        location = match.group(1) if match else "$"
        locations = locals().get("locations", {"$": 1})
        while location not in locations and location != "$":
            location = re.sub(r"(\.[^.\[]+|\[\d+\])$", "", location) or "$"
        raise ValueError(f"{source}:line {locations.get(location, 1)}: {exc}") from exc


def build_intake(value: dict, source_sha256: str, *, source_kind: str = "raw-utf8-intake-file") -> dict:
    """Return a canonical plan and honest review; never import the result."""
    _check(value, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    defaults = []

    def choose(mapping, key, fallback, path):
        if key in mapping:
            return mapping[key]
        defaults.append(path)
        return fallback

    policy = {key: choose(value.get("policy", {}), key, fallback, f"policy.{key}")
              for key, fallback in POLICY_DEFAULTS.items()}
    # An explicit cap without target implies the cap, rather than hidden throttling.
    if "target_workers" not in value.get("policy", {}):
        policy["target_workers"] = policy["max_workers"]
    tasks = []
    for index, item in enumerate(value["tasks"]):
        prefix = f"tasks[{index}]"
        executor = choose(item, "executor", "simulation", prefix + ".executor")
        if executor == "codex-cli" and "simulation" in item:
            raise ValueError(f"$.{prefix}.simulation: incompatible with codex-cli")
        profile = choose(item, "validation_profile",
                         "simulation-receipt" if executor == "simulation" else "manual-review",
                         prefix + ".validation_profile")
        task = {
            "task_id": item["task_id"], "title": item["title"], "description": item["description"],
            "acceptance_criteria": item["acceptance_criteria"], "estimate_minutes": item["estimate_minutes"],
            "depends_on": item["depends_on"],
            "priority": choose(item, "priority", 50, prefix + ".priority"),
            "executor": executor, "model": {"preference": "default"},
            "resources": {"slots": choose(item, "slots", 1, prefix + ".slots")},
            "risk_class": choose(item, "risk_class", "low", prefix + ".risk_class"),
            "allowed_operations": choose(item, "allowed_operations", [], prefix + ".allowed_operations"),
            "validation_profile": profile,
            "artifact_outputs": choose(item, "artifact_outputs", [], prefix + ".artifact_outputs"),
            "timeout_policy": {
                "execution_seconds": choose(item, "execution_seconds", 300, prefix + ".execution_seconds"),
                "max_retries": choose(item, "max_retries", 0, prefix + ".max_retries"),
                "warning_multiplier": 2, "escalation_multiplier": 4},
            "escalation_conditions": ["Human review if acceptance is unverified or retry budget is exhausted"],
        }
        if "simulation" in item:
            task["simulation"] = item["simulation"]
        tasks.append(task)
    plan = validate_plan({"schema_version": "1.0", "project_id": value["project_id"],
                          "display_name": value["display_name"],
                          "revision": choose(value, "revision", 1, "revision"),
                          "goal": value["description"], "repository": value["repository"],
                          "policy": policy, "tasks": tasks})
    estimate = {task["task_id"]: task["estimate_minutes"] for task in tasks}
    by_id = {task["task_id"]: task for task in tasks}
    longest = {}
    layers = {}
    successors = {task_id: [] for task_id in by_id}
    remaining = {task_id: len(task["depends_on"]) for task_id, task in by_id.items()}
    for task_id, task in by_id.items():
        for dependency in task["depends_on"]:
            successors[dependency].append(task_id)
    ready = [task_id for task_id, count in remaining.items() if count == 0]
    while ready:
        task_id = ready.pop()
        dependencies = by_id[task_id]["depends_on"]
        longest[task_id] = estimate[task_id] + max((longest[dep] for dep in dependencies), default=0)
        layers[task_id] = 1 + max((layers[dep] for dep in dependencies), default=0)
        for successor in successors[task_id]:
            remaining[successor] -= 1
            if remaining[successor] == 0:
                ready.append(successor)
    summary = {"project_id": plan["project_id"], "description": plan["goal"],
               "task_count": len(tasks), "total_estimate_minutes": sum(estimate.values()),
               "critical_path_estimate_minutes": max(longest.values()),
               "estimate_note": "Authored estimates only; excludes review, retries and overhead. Not a forecast.",
               "execution_note": "Simulation is synthetic; Codex execution remains disabled by the scheduler.",
               "tasks": [{"task_id": task["task_id"], "title": task["title"],
                          "description": task["description"], "estimate_minutes": task["estimate_minutes"],
                          "depends_on": task["depends_on"], "dependency_layer": layers[task["task_id"]],
                          "executor": task["executor"], "acceptance_criteria": task["acceptance_criteria"]}
                         for task in tasks]}
    return {"transform_version": TRANSFORM_VERSION, "source_sha256": source_sha256,
            "source_kind": source_kind,
            "plan_sha256": digest(plan), "defaults_applied": defaults,
            "summary": summary, "plan": plan,
            "status": "draft_only; explicit preview and import required"}
