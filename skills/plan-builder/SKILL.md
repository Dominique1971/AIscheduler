---
name: plan-builder
description: Create strict canonical scheduler plans from goals, using dummy projects until real-project authorization is explicit.
---

Use an explicitly selected scheduler checkout. Paths below are relative to that checkout, not the skill's install location. Read `docs/SPEC.md` section 4 and `schemas/plan-1.0.schema.json` before drafting. The schema, not the abbreviated prose example in section 5, defines all required fields. Start from `examples/demo-weather.yaml` or `examples/demo-inventory.yaml`.

1. Translate the authorized goal into independently verifiable tasks. Preserve source facts and acceptance criteria; surface missing requirements rather than inventing them.
2. Assign stable, unique task IDs and resolvable dependencies. Include forks and joins where tasks can proceed independently. Never repurpose an ID for unrelated work across revisions.
3. Include every required task field: description, acceptance criteria, estimate, priority, executor, model, resources, risk, allowed operations, validation profile, artifact outputs, timeout policy, escalation conditions. Use the smallest necessary operations and bounded retries.
4. Use `executor: simulation` for dummy validation; label simulation outputs honestly. `codex-cli` can describe a proposed execution contract but execution remains capability-gated. Only `model: {preference: default}` is currently verified at the contract layer; explicit model and reasoning overrides are rejected until a verified adapter supports them.
5. Validate with the normal CLI (`python -m scheduler validate PATH`) before proposing import. Preserve original input and validation errors. Fix authoring input, never generated execution output.
6. Explain scope, DAG, estimated effort, risks, and plan diff. A valid plan does not authorize execution or real-project access. Use the normal authenticated preview/apply workflow with explicit approval for material scope changes.

Timeouts use seconds; estimates use minutes. Priorities range 0–100. Dates must be quoted strings. YAML aliases and duplicate mapping fields are rejected. Repository locators remain declarative in simulation; validation does not resolve, create or modify repositories.
