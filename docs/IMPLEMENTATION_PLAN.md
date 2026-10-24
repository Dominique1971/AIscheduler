# Implementation plan

Updated 2026-10-24. Effort means engineering effort, not delivery promises. Stage
gates remain blocking even when structural unit tests pass.

| ID | Task | Depends | Estimate | Acceptance | State |
|---|---|---|---|---|---|
| D1 | Inventory and capability evidence | — | 1–2h | Raw CLI evidence, verified/advertised distinction | Real CLI/app-server probes partly verified |
| D2 | Architecture and requirement gaps | D1 | 1h | Recorded decisions and full-stage ledger | Initial ADR done |
| C1 | Strict portable plan contract and builder | D2 | 2–4h | Valid/invalid YAML, line errors, DAG/schema | Implemented, diagnostic tests |
| C2 | Durable tasks, revisions, receipts | C1 | 3–5h | Untouched output, immutable history, integrity rejection | Implemented simulation slice |
| C3 | Dispatcher, backfill, leases/restart | C2 | 3–5h | Normal daemon/API two-project forced restart | Fresh simulation passed; real lifecycle unrun |
| C4 | Full min/target/reserved fairness and resources | C3 | 3–5h | Reservations, aging, resource exhaustion cases | Allocations/slots implemented; memory/skills pending |
| C5 | Revisions, splits, rollback workflow | C2 | 2–4h | Active split preserves attempts/completions | Append splits implemented; rollback UX pending |
| E1 | Real Codex capability spike | D1 | 2–5h | Actual launch/IDs/status/resume/cancel/usage with receipts | Parallel CLI, resume, own-thread app-server controls/usage verified; artifact/worktree/parity pending |
| E2 | Worker worktrees and Codex lifecycle | E1,C3 | 5–10h | Disposable real tasks, crash reconciliation, no duplicates | Preparatory parser only |
| E3 | Validation/tests/Git checkpoints and batch review | E2 | 5–8h | Source-faithful actual artifacts and narrow/full test policy | Unimplemented |
| R1 | Watchdog/bounded recovery/alerts | C3,E2 | 3–6h | Stalls, network/rate limits, partial side effects | Simulation timeout/retry/warnings only |
| A1 | Versioned local API and CLI | C3 | 3–5h | Auth/RBAC/idempotency and normal API pipeline | Initial subset implemented |
| A2 | Remaining documented API and optional MCP | A1 | 3–5h | Pagination, operations, tools handshake in Dot | Partial API; MCP/Dot unrun |
| U1 | Dashboard overview and controls | A1 | 4–7h | Live desktop/mobile screenshots and controls | Local viewport/controls passed; private phone read-only view and one dummy Pause observed |
| U2 | Attempt phases/dependency graph/revisions/forecasts | U1,R1 | 4–7h | Actual history/trends, estimates and uncertainty | Partial current timestamps only |
| S1 | HTTPS remote interface, MFA and controls | A1,U1 | 3–6h | Outside-LAN Android MFA/CSRF/RBAC audit | Private Site, owner TOTP, dummy bridge and phone Pause verified; cellular control and alternate-owner denial pending |
| P1 | History/retention/backup/restore/monitoring | C2 | 3–6h | Restore and retention preserve durable project state | Backup/restore passed; configurable cleanup/aggregation pending |
| V1 | Fresh simulation acceptance | C3,C5,A1 | 2–4h | A1–A5/A9–A10 evidence through normal CLI/API | Fresh finite suite passed; dedicated latency stress pending |
| V2 | Real Codex and native parity | E2,E3 | 3–6h | Disposable tasks, parity report, A11/A14 | Unrun |
| V3 | Device UX/cellular gate | S1,U2 | 2–4h | A6–A8 phone evidence | User-observed cellular read-only view and one dummy phone Pause; fresh cellular login/control and 8h endurance unrun |
| V4 | 24h dummy soak and reboot | R1,P1,V1 | 24h elapsed + 2–4h | A12, no human prompts, retained faults | 24h burst/idle soak running; reboot unrun |
| O1 | Real-project onboarding checklist | V2,V3,V4 | 1–2h | Explicit project authorization and all required gates | Blocked by acceptance gates |

Bottom-up full remaining effort is materially larger than the earlier 35–55h
placeholder (roughly 60–110h across the complete scope, plus soak elapsed time),
with substantial uncertainty in Codex control and remote identity integration.
This is a staged estimate, not approval to spend or deploy.
