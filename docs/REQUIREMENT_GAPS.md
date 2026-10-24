# Specification coverage audit — 24 October 2026

`docs/SPEC.md` remains authoritative. "Implemented" here refers to a concrete
slice, never automatic acceptance of a whole section. `docs/ACCEPTANCE.md`
separates fresh black-box runs from diagnostics and open gates. All real-project
access still requires explicit authorization after the relevant gates pass.

| SPEC area | Current evidence or gap | Delivery IDs |
|---|---|---|
| 1–3 independent architecture and native parity | Separate Python/SQLite service, optional dashboard/Site; direct Codex/Dot unaffected. Real Codex scheduler not wired. | E2–E4, V2 |
| 4 project description and plan builder | Canonical schema, validator and skill exist. Versioned intake-to-draft CLI and local preview form capture authored task explanations, estimates and dependencies. Goal-only assisted breakdown, graph/diff review and explicit UI apply remain open. | I1–I3, C1 |
| 4 portable policy fields | Slots/priority implemented. Memory, skills, concurrency caps, token budgets and due-date scheduling are declarative or absent. | C6, R3 |
| 5 illustrative YAML | Abbreviated prose example is not valid canonical input; full examples and intake example are provided. | C1, I1 |
| 6 plan revisions | Immutable versions, basic preview, append split. Rich edge/estimate/allocation diff, rollback-as-new-revision and active replacement workflow open. | C5, C7, I3 |
| 7 allocations/backfill | Global/project slots, min/target/reserved, pause/hold and fairness implemented in simulation. Dedicated <=15s stress and real worker enforcement open. | C4, C6, V5 |
| 8 Codex capability | Real CLI/app-server probes for launch, IDs, resume, usage and some controls; worktree probe passed. Scheduled adapter, parity, tool/approval coverage and rate recovery open. | E1–E4, V2 |
| 9 lifecycle/reconciliation | Durable simulation attempts, lease/fence and forced daemon restart verified. External-process recovery, liveness, cancellation and reboot open. | E4, R1–R3 |
| 10 judgment/escalation | Synthetic retries/review and warning events only. Bounded real repairs, alerts and human decision packets open. | R1, A2, E3 |
| 11 Git/integration/tests | Disposable direct CLI worktrees proven; scheduler-managed worktrees, checkpoints, merge review and regression policy open. | E2, E3, V2 |
| 12 dashboard | Local compact viewport, timeline and controls partly verified; phone read-only and one dummy Pause observed. Graph, forecasts, historical trends, physical-device long use open. | U1–U3, I3, V6 |
| 13 remote security | Owner-private Site, TOTP, sessions, D1 command/audit and outbound bridge; dummy phone Pause passed. Fresh cellular control, wrong signed-in owner and renewal/recovery open. | S1, S2, V3, V6 |
| 14 persistence/history | Revisions/attempts/events and verified backup/restore. Retention/aggregation, elapsed-active timing, forecasts and real token attribution open. | P1–P3 |
| 15 API/MCP/Dot | Versioned authenticated subset with idempotent controls. Operations/logs/alerts/metrics and Dot MCP handshake open. | A1–A3 |
| 16 dummy-first verification | Simulation fresh run, real CLI capability probes, private Site trial. Scheduled disposable Codex DAG, device negative cases and native parity open. | V1–V6 |
| 17 quantitative A1–A14 | Ledger in `docs/ACCEPTANCE.md`; A12 soak running. Do not infer all gates from simulation or one device action. | V1–V6 |
| 18 stages and gate ordering | Plan is incremental; discovery/core partly done, real adapter and robustness remain substantial. | `docs/IMPLEMENTATION_PLAN.md` |
| 19 risk/exclusions | Unknown native automation, subscription limits, sleep/reboot, resource contention and remote abuse remain tracked; no custom LLM runtime. | E4, R2–R3, S2, V5 |
| 20 handoff | Separate Git repository and raw evidence; no Oppo/Compass modification. Real-project onboarding is still blocked. | O1–O2 |

Immediate exit criteria for intake: a normal CLI run on an authored dummy brief
creates a canonical draft and provenance, reports every task and dependency,
validates both positive and negative DAGs, and leaves the scheduler database
untouched until a distinct import. The authored effort and critical path must
be clearly labeled estimates. This is separate from generator acceptance.

For a fully unstructured goal, an authoring agent may propose task boundaries,
but every proposal must be reviewable with assumptions and unknowns visible.
There is no deterministic way to infer missing work, timing or repository facts
from a short description alone. The new intake command deliberately rejects
incomplete task records instead of fabricating a plausible-looking plan.
