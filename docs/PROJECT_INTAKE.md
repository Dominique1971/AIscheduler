# Project intake and plan review

The scheduler accepts a short, authored project description before the full
canonical execution contract. The intake records the project goal, a repository
locator, each task's description and acceptance criteria, estimate in minutes,
and explicit dependency IDs. It is a **draft**: intake does not inspect a
repository, invent tasks, contact a model, import a project or start work.

The versioned source shape is `scheduler/schemas/intake-1.0.schema.json`; see
`examples/intake-demo-weather.yaml`. Unknown fields, duplicate keys, aliases,
missing dependencies and cycles are rejected. The `description` maps unchanged
to the canonical plan's `goal`, and task descriptions, estimates, criteria and
dependencies are preserved. The converter records every added operational
default in a separate provenance sidecar. The canonical plan remains governed
by `scheduler/schemas/plan-1.0.schema.json` and its DAG validator.

```powershell
python -m scheduler intake examples/intake-demo-weather.yaml --output runtime/proposed-weather.json
python -m scheduler validate runtime/proposed-weather.json
python -m scheduler preview runtime/proposed-weather.json
```

The intake command refuses to overwrite an existing draft or provenance file.
It produces `runtime/proposed-weather.json` and
`runtime/proposed-weather.json.provenance.json`, containing the raw source hash,
transform version, canonical plan hash, defaults, per-task explanations, total
authored effort and dependency critical-path estimate. Without `--output`, it
prints the same draft envelope as JSON. Generated draft corrections go through
the authored intake and a new output path. The reviewer must compare the draft,
defaults, risks, accepted outputs and dependencies with the actual goal before
using the separate `import` command. Plan revisions continue to require explicit
approval and immutable task identity.

The authenticated **local** dashboard also has a Draft project form. It collects
the same description and task fields, calls `POST /api/v1/intake/preview`, and
shows each task's estimate, dependencies and criteria before offering separate
downloads of the source intake, canonical plan and provenance. The downloaded
intake is exact canonical JSON whose SHA-256 matches the preview response;
the API also reports the raw HTTP request hash. A control token is required.
This form does not yet provide the richer plan-diff or approval/import workflow,
and it is not deployed in the private phone Site.

The total is the sum of task estimates; the critical path is the longest chain
of dependent task estimates. Neither includes review, retries, queue time or
resource contention, so neither is a delivery forecast. For a new goal that
does not yet contain task boundaries, an author or Plan Builder skill must draft
them and surface unknowns. The deterministic converter will not guess.

Simulation is the intake default and produces synthetic scheduler receipts,
not the described artifacts. Proposed `codex-cli` tasks are admitted by the
canonical contract but remain blocked by the current simulation-only daemon.
No existing real project is connected by this workflow.
