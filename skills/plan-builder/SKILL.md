---
name: plan-builder
description: Draft and review scheduler project intake and canonical plans from a stated goal, task descriptions, estimates and dependencies.
---

Use an explicitly selected scheduler checkout. Read `docs/SPEC.md` section 4 and `docs/PROJECT_INTAKE.md`. The canonical schema is `scheduler/schemas/plan-1.0.schema.json`; the intake schema is `scheduler/schemas/intake-1.0.schema.json`. The abbreviated example in SPEC section 5 omits required fields.

1. For an inbound project description, draft `examples/intake-demo-weather.yaml`-shaped intake. State the goal in `description`, then list each task's purpose, acceptance criteria, estimate in minutes and dependency IDs. Preserve source facts; mark unknown scope or estimates as open questions instead of inventing them. Start with dummy projects until real-project authorization is explicit.
2. Assign stable, unique task IDs and resolvable dependencies. Include forks and joins where tasks can proceed independently. Never repurpose an ID for unrelated work across revisions.
3. Run `python -m scheduler intake INTAKE.yaml --output PROPOSED.json`. Review the reported total task effort, dependency critical path, per-task explanation and all defaults. The command creates a draft canonical plan and provenance sidecar; it never imports or executes it. Preserve original input and validation errors. Revise authored intake and regenerate to a new path when corrections are needed; do not patch generated output.
4. Validate the draft with `python -m scheduler validate PROPOSED.json`, then use the normal preview and explicit import flow. A valid plan does not authorize execution or real-project access. For material revisions, compare the diff and obtain the required approval. Direct canonical authoring is still possible when full operational fields are needed.
5. Use `executor: simulation` for dummy verification and label synthetic outputs honestly. `codex-cli` may describe a proposed contract but scheduler execution remains gated. The transform uses `model: {preference: default}`; explicit model and effort overrides remain rejected by the canonical contract.

Estimates use minutes; timeouts use seconds. YAML aliases and duplicate mapping fields are rejected. Repository locators are declarative here; intake neither resolves nor modifies them.
