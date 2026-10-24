# Implementation plan

Updated 2026-10-24. Effort means engineering effort, not delivery promises. Stage
gates remain blocking even when structural unit tests pass.

The full requirement-to-delivery audit is in `docs/REQUIREMENT_GAPS.md`.
The immediate sequence is project intake/review, disposable scheduled Codex
execution, artifact validation and recovery, then device and endurance gates.
IDs below identify deliverables, not permission to attach real repositories.

| ID | Task | Depends | Estimate | Acceptance | State |
|---|---|---|---|---|---|
| D1 | Inventory and capability evidence | — | 1–2h | Raw CLI evidence, verified/advertised distinction | Real CLI/app-server probes partly verified |
| D2 | Architecture and requirement gaps | D1 | 1h | Recorded decisions and full-stage ledger | Initial ADR done |
| I1 | Versioned project intake description | C1 | 2–4h | Authored tasks/estimates/dependencies -> canonical draft with defaults, hashes and critical path; no auto-import | Fresh dummy CLI-to-simulation intake run passed; real-project authoring unrun |
| I2 | Assisted goal-to-task authoring | I1 | 3–6h | Skill drafts tasks from an incomplete goal, marks unknowns, validates DAG, preserves the authored brief | Plan Builder skill updated; interactive authoring acceptance unrun |
| I3 | Project review and approval surface | I1,A1,U1 | 5–9h | Local UI/API shows inbound description, task details, dependency graph, estimates, defaults, diff and explicit apply | Local review graph, diff and guarded dummy import implemented; browser interaction and phone Site parity pending |
| C1 | Strict portable plan contract and builder | D2 | 2–4h | Valid/invalid YAML, line errors, DAG/schema | Implemented, diagnostic tests |
| C2 | Durable tasks, revisions, receipts | C1 | 3–5h | Untouched output, immutable history, integrity rejection | Implemented simulation slice |
| C3 | Dispatcher, backfill, leases/restart | C2 | 3–5h | Normal daemon/API two-project forced restart | Fresh simulation passed; real lifecycle unrun |
| C4 | Full min/target/reserved fairness and resources | C3 | 3–5h | Reservations, aging, resource exhaustion cases | Allocations/slots implemented; memory/skills pending |
| C5 | Revisions, splits, rollback workflow | C2 | 2–4h | Active split preserves attempts/completions | Append splits implemented; rollback UX pending |
| C6 | Admission of resource/skill/budget policy | C4,E2 | 5–9h | Memory, skill requirements, project concurrency caps and task token budgets enforced or clearly rejected | Slots only; other fields declarative |
| C7 | Complete plan revision controls | C5,I3 | 4–7h | Edge/estimate/allocation diff, rollback as new revision, safe active replacement, approval audit | Basic diff and append split only |
| E1 | Real Codex capability spike | D1 | 2–5h | Actual launch/IDs/status/resume/cancel/usage with receipts | Parallel CLI, resume, own-thread app-server controls/usage verified; artifact/worktree/parity pending |
| E2 | Worker worktrees and Codex lifecycle | E1,C3 | 5–10h | Disposable real tasks, crash reconciliation, no duplicates | Parser and root-gated write invocation prepared; launch/reconciliation unimplemented |
| E3 | Validation/tests/Git checkpoints and batch review | E2 | 5–8h | Source-faithful actual artifacts and narrow/full test policy | Unimplemented |
| E4 | Live process reconciliation and control | E2 | 5–9h | After daemon/host restart, recover IDs/status/logs without duplicate side effects; cancel/steer only where proven | Direct CLI/app-server probes only |
| R1 | Watchdog/bounded recovery/alerts | C3,E2 | 3–6h | Stalls, network/rate limits, partial side effects | Simulation timeout/retry/warnings only |
| R2 | Host service and reboot recovery | E4,R1 | 4–8h | Supervised user service, restart after reboot, alert on orphaned work, no silent relaunch | Unimplemented |
| R3 | Rate-limit/resource pressure handling | E4,C6 | 4–8h | Bounded backoff, pause/resume, RAM pressure and cost/usage ceilings with truthful unknowns | Unimplemented |
| A1 | Versioned local API and CLI | C3 | 3–5h | Auth/RBAC/idempotency and normal API pipeline | Initial subset implemented |
| A2 | Complete documented local API | A1,C7,E4,P2 | 5–9h | Operations, pagination, executions, logs, metrics, alerts, structured errors | Partial API |
| A3 | Optional MCP/Dot adapter | A2 | 3–6h | Same permissioned operations and actual Dot handshake; native Dot workflow remains independent | Unrun |
| U1 | Dashboard overview and controls | A1 | 4–7h | Live desktop/mobile screenshots and controls | Local viewport/controls passed; private phone read-only view and one dummy Pause observed |
| U2 | Attempt phases/dependency graph/revisions/forecasts | U1,R1 | 4–7h | Actual history/trends, estimates and uncertainty | Partial current timestamps only |
| U3 | Full compact and accessible device UX | U2,I3 | 4–8h | 1h/8h/24h/7d pan/zoom, graph, source plans, retry phases, labels, no overflow on physical phone | Partial local timeline and viewport emulation |
| S1 | HTTPS remote interface, MFA and controls | A1,U1 | 3–6h | Outside-LAN Android MFA/CSRF/RBAC audit | Private Site, owner TOTP, dummy bridge and phone Pause verified; cellular control and alternate-owner denial pending |
| S2 | Remote security and cellular completion | S1,U3 | 4–8h | Fresh mobile-data login/control, wrong-owner denial, expiry/refresh/replay/rate tests, recovery and audit integrity | Dummy phone Pause and read-only cellular reachability only |
| P1 | History/retention/backup/restore/monitoring | C2 | 3–6h | Restore and retention preserve durable project state | Backup/restore passed; configurable cleanup/aggregation pending |
| P2 | Forecasts, usage and cost provenance | C2,E2,U2 | 4–8h | UTC/local time, elapsed/active duration, rolling estimates/confidence, per-task model/tokens where exposed; no invented spend | Simulation metrics only |
| P3 | Durable retention and observability | P1,E4 | 4–8h | >=90d execution/audit history, 7d high-resolution samples, size controls, backups and restore verification | Backup/restore only |
| V1 | Fresh simulation acceptance | C3,C5,A1 | 2–4h | A1–A5/A9–A10 evidence through normal CLI/API | Fresh finite suite passed; dedicated latency stress pending |
| V2 | Real Codex and native parity | E2,E3 | 3–6h | Disposable tasks, parity report, A11/A14 | Unrun |
| V3 | Device UX/cellular gate | S1,U2 | 2–4h | A6–A8 phone evidence | User-observed cellular read-only view and one dummy phone Pause; fresh cellular login/control and 8h endurance unrun |
| V4 | 24h dummy soak and reboot | R1,P1,V1 | 24h elapsed + 2–4h | A12, no human prompts, retained faults | 24h burst/idle soak running; reboot unrun |
| V5 | Quantitative performance and negative gates | C6,E4,S2 | 4–8h | <=15s backfill, no duplicate external launch, bad identity/plan/receipt/command cases, resource stress | Diagnostic subset only |
| V6 | Long-duration device and production-like reliability | S2,R2,P3 | 8h device elapsed + 3–6h | Physical phone view/refresh/staleness, session renewal, outages and recovery with complete receipts | Unrun |
| O1 | Real-project onboarding checklist | V2,V3,V4 | 1–2h | Explicit project authorization and all required gates | Blocked by acceptance gates |
| O2 | Safe per-project enrollment | O1,I3,E3 | 3–6h | Explicit repository scope and permission review, dry run, rollback path, no alteration of native Codex/Dot settings | Unimplemented |

The earlier 35–55h placeholder and 60–110h revision omitted several explicit
requirements above. The table supplies bounded estimates per deliverable;
overlap, experimental Codex behavior and the running soak make a precise total
misleading. Re-estimate after E2/E4 and S2 evidence. No estimate is approval to
spend, deploy or connect a real project.
