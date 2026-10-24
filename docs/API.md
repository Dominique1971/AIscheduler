# API v1 — local slice

Base `http://127.0.0.1:8765/api/v1`. Version 0.1.0. Every API operation requires
`Authorization: Bearer TOKEN`. POST requires `Idempotency-Key` (1–128 chars).
Identical mutations replay the same result; reuse with a different payload is
409. Tokens stay in environment, never URLs. Controllers and readers are distinct
shared local roles; per-person identity/MFA is not implemented.

| Method / path | Purpose / body | Role |
|---|---|---|
| GET /snapshot | Projects/tasks/events/current metrics + source time, role, daemon lease | read/control |
| GET /system/health | Dispatcher lease freshness and enabled executor | read/control |
| GET /projects?offset=0&limit=50 | Project listing (limit 1..100) | read/control |
| GET /projects/{id}/tasks/{task}/trace | Original attempts and verified input/output hashes | read/control |
| GET /projects/{id}/plans/history?offset=0&limit=50 | Immutable plans, hashes and timestamps | read/control |
| GET /projects/{id}/plan | Hash-checked current plan summary, task DAG and intake receipt | read/control |
| GET /examples | Two packaged disposable intake plans with summaries and file hashes | read/control |
| POST /intake/preview | `{intake: authoredIntake}`; returns draft plan, per-task explanation, estimates, defaults and source provenance; no import | control |
| POST /intake/file/preview | `{filename: "plan.md", source_text: exactMarkdown}`; strict Markdown v1 parse, source hash and canonical draft; no import | control |
| POST /intake/file/import | `{filename, source_text, expected_source_sha256, expected_preview, approved: true}`; reparse and hash-check exact Markdown before guarded dummy import | control |
| POST /intake/import | `{intake, expected_source_sha256, expected_preview, approved: true}`; hash-bound guarded import for `demo-`/`dummy-` simulation plans under `./runtime/` | control |
| POST /plans/validate | `{plan: canonicalPlan}` | control |
| POST /plans/preview | `{plan: canonicalPlan}` | control |
| POST /plans/apply | `{plan: canonicalPlan, approved: true, expected_preview?: previewResponse}`; an exact expected preview rejects a changed plan state; approval required on revisions | control |
| POST /projects/{id}/pause | `{}`; stop-new-dispatch | control |
| POST /projects/{id}/resume | `{}` | control |
| POST /projects/{id}/allocate | `{max_workers: 2}` or partial object with `min_workers`, `target_workers`, `reserved_slots`; active work drains safely | control |
| POST /projects/{id}/tasks/{task}/hold | `{}`; stop future dispatch | control |
| POST /projects/{id}/tasks/{task}/unhold | `{}` | control |
| POST /projects/{id}/tasks/{task}/retry | `{}`; failed/review only; adds linked attempt | control |
| POST /system/workers | `{max_workers: 6}` | control |
| POST /system/emergency-stop | `{confirmed: true}` | control |
| POST /system/start | `{}`; explicitly re-enable dispatch | control |

Errors use JSON with `error/message` or FastAPI `detail`: 400 malformed boundary,
401 expired/missing token, 403 wrong role/origin, 404 missing operation/entity,
409 revision/idempotency/integrity conflict, 413 size, 422 invalid plan/parameters,
429 rate (Retry-After). Rate limit is local per client, 240 API requests/minute.
The rate limiter resets with the API process; it is not a public abuse gateway.

Safety headers apply to HTML/assets and API. API is loopback-only and rejects
foreign origins and unrecognized Host. There is no CORS credential grant or
cookie auth. Dashboard controls use explicit bearer headers. MFA/CSRF controls
for a future identity gateway must be tested before remote exposure. Token expiry
is optional in local development; configure `SCHEDULER_TOKEN_EXPIRES_AT` for bounded
sessions and rotate credentials by restarting API. Do not log Authorization.

Snapshot events are currently capped at the last 200; detailed events remain in
SQLite. Full task/execution/worker/metrics/alert pagination, alert acknowledgement,
plan rollback helper, independent OpenAPI publication, MCP wrapping and Dot
handshake remain pending. This document describes only implemented routes.

The intake API hashes a canonical JSON rendering of the inbound `intake`
object and returns those exact source bytes as `source_text` for download;
`request_sha256` separately identifies the raw HTTP envelope. The local
programmatic JSON route remains available. The dashboard's **Import plan**
dialog uses the file routes above and has no drafting form. Neither preview nor download
creates a project. Import recomputes the canonical source and exact reviewed
preview, then stores the source, transform version and defaults with the plan
revision. The standalone CLI hashes the original intake file bytes.
