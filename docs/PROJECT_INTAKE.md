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

The package includes two disposable catalog examples, `demo-weather` and
`demo-inventory`, each with six synthetic tasks, a fork/join dependency graph,
authored estimates, descriptions and acceptance criteria. Their declared
repositories sit below `./runtime/examples/`; simulation emits receipts and
does not create the described business artifacts. The catalog is available at
`GET /api/v1/examples` and in the local dashboard's **Import plan** dialog.
Reviewing an example uses the same server preview path as a manually authored
intake, and never imports it automatically.

The authenticated **local** dashboard is an import and visualization surface;
it has no project drafting editor. Its **Import plan** dialog accepts a `.md`
file authored elsewhere using the exact
[`Markdown intake v1` format](../scheduler/static/intake-format.md). A
[downloadable template](../scheduler/static/intake-template.md) and in-dialog
format guide list every required field. The upload calls
`POST /api/v1/intake/file/preview` and `POST /api/v1/plans/preview`, then shows
the authored description, estimates, directed dependency arrows, criteria, defaults,
source/plan hashes and plan diff. An explicit review checkbox is required
before `POST /api/v1/intake/file/import` can store the plan. The server
reparses the exact Markdown text, verifies its raw UTF-8 SHA-256 and the plan
preview, and records the untouched Markdown source, parser/transform versions
and defaults with the plan revision. Programmatic JSON intake preview/import
and the YAML CLI remain available, but are not authoring fields in the UI.

The dashboard can import only a **new** `demo-` or `dummy-` simulation plan
with a declared path below `./runtime/`. A control token is required. The
separate source, canonical plan and provenance downloads support review.
`GET /api/v1/projects/{project}/plan` checks stored hashes and returns the
current goal, task details and a DAG computed from task IDs and dependencies;
the project card's
**View plan** button renders these on demand. Import
queues synthetic tasks for a running daemon. Browser interaction is still
unverified. The private phone Site displays a bounded read-only projection
of the goal, task descriptions, criteria, estimates and dependency layers
for projects reported by its outbound bridge; importing remains local. The path
check applies to this UI workflow only; a future real executor must validate
the resolved repository path independently before any launch.

The total is the sum of task estimates; the critical path is the longest chain
of dependent task estimates. Neither includes review, retries, queue time or
resource contention, so neither is a delivery forecast. For a new goal that
does not yet contain task boundaries, an author or Plan Builder skill must draft
them and surface unknowns. The deterministic converter will not guess.

Simulation is the intake default and produces synthetic scheduler receipts,
not the described artifacts. Proposed `codex-cli` tasks are admitted by the
canonical contract but remain blocked by the current simulation-only daemon.
No existing real project is connected by this workflow.
