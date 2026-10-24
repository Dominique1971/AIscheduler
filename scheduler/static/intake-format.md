# Scheduler Markdown intake format v1

Create this `.md` file outside the dashboard. The dashboard reads the file, validates it, previews the resulting plan, and imports only after you approve the exact preview. It does not generate tasks or fill missing facts.

Start from [the template](intake-template.md). Keep the labels and section headings exactly as shown. The order is required:

```text
# Scheduler project intake v1
Project ID: dummy-unique-id
Project name: A readable name
Repository path: ./runtime/examples/dummy-unique-id
Base branch: main
Maximum workers: 2

## Description
Why the project exists and what result is intended.

## Tasks
### first: First task title
Description: What this task does.
Estimate minutes: 3
Depends on: none
Acceptance criteria:
- An observable criterion for this task.

### second: Second task title
Description: What this task does.
Estimate minutes: 4
Depends on: first
Acceptance criteria:
- An observable criterion for this task.
```

- The file must be UTF-8 without a byte-order mark, have a simple `.md` filename, and be at most 512 KiB through the dashboard.
- `Project ID` and task IDs use letters, digits, `_`, `-`, or `.`, starting with a letter or digit. IDs must be unique. The dashboard currently imports only new IDs beginning `demo-` or `dummy-`.
- `Repository path` must be under `./runtime/` for dashboard import. It is declarative; importing a simulation project does not create a repository.
- `Maximum workers` is an integer from 1 to 128.
- `## Description` contains one or more lines of authored project goal text. It ends at `## Tasks`. A task's `Description:` is one nonempty line.
- `Estimate minutes` is a positive number. The dashboard shows the sum of task estimates and the longest dependency chain; neither is a delivery forecast.
- `Depends on` is `none` or a comma-separated list of task IDs in the same file. Dependencies may point to tasks listed later. Unknown IDs, duplicates, and cycles fail validation.
- Every task needs at least one nonempty `- ` item under `Acceptance criteria:`. The criteria are authored requirements; simulation completion does not prove them.
- Blank lines are allowed. Extra headings, fields, or prose outside the defined project description are rejected rather than silently ignored.

This v1 Markdown format maps to `scheduler/schemas/intake-1.0.schema.json` in the repository. The parser applies and reports operational defaults, including the simulation executor. More detailed canonical YAML plans remain available through the CLI. The local dashboard intentionally has no drafting editor. It can import only new disposable simulation projects until real execution and onboarding gates are complete.
