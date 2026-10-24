# Architecture decision 001 — gated local vertical slices

Recorded 2026-10-23. Requirements: SPEC.md and prompts/KICKOFF.md.

Use Python 3.12, SQLite WAL, a deterministic dispatcher, separate API process and
browser client. `python -m scheduler daemon` performs all dispatch without a chat,
dashboard or API process. Each transaction obtains the SQLite write lock. A
renewable three-second leader lease and monotonically increasing fencing number
serialize dispatch across daemon processes. Attempt identity and `(project,task,
number)` uniqueness are durable. Simulation attempts represent deterministic
wall-clock state; a new daemon reconciles the same persisted attempt after lease
expiry without relaunch. This property does **not** establish exactly-once Codex
side effects or external-process recovery.

The v0.1 enabled executor is deliberately simulation only. Its output is a
synthetic receipt, not generated source code, CSV or independently validated task
semantics. Only the `simulation-receipt` validation profile is enabled. Codex CLI
command construction and JSONL parsing are preparatory; runtime execution must
pass capability and authorization gates first. The invocation builder has an
explicit disposable-root gate for workspace-write mode, uses the existing
ChatGPT user configuration needed by the verified CLI write probe, and never
starts a process itself. It is not scheduled Codex execution or artifact
acceptance. Desktop and Dot are optional
peers. Nothing changes their configuration or intercepts native tasks.

Each plan revision stores the canonical input and hash. Active/completed task
contracts cannot change or disappear. A split appends new tasks dependent on the
original task; incompatible replacement requires a different identity. Removed
pending tasks become superseded and cannot have their identity reused. Rollback
must be expressed as a new reviewed revision, never overwrite history. Whole-plan
approval is conservative: every revision requires explicit approval after preview.

Each attempt preserves canonical input/hash and untouched receipt/hash. Trace
checks integrity and rejects changed bytes. Events describe transitions, attempt
identity, lease acquisition, controls and provenance. This is a local audit
journal, not tamper-proof storage. The host user can alter the database. No model
tokens or subscription percentages are fabricated.

The API binds loopback only, requires separate controller/optional read bearer
tokens, uses request idempotency for mutations, rejects foreign origins and
untrusted hosts, bounds request size and rate, and emits restrictive browser
headers. Tokens may expire through configuration. It is not an MFA gateway and
must not be published directly. Remote HTTPS/MFA, identity-specific roles and
Android cellular verification remain a separate gate. No tunnel is installed.

## Unresolved requirements and scope boundaries

The complete specification remains authoritative. This vertical slice is not a
complete scheduler delivery. Memory declarations, task skill requirements,
concurrency caps, token budgets, due dates and merge/regression policies are plan
metadata in v0.1; they are not real worker enforcement. Min/target allocations are
dispatch preferences; reserved slots hold idle capacity even when a project is
paused. Runtime allocations preserve canonical plans. Online backup/restore into
new destinations preserve verified receipts. Process/worktree isolation, artifact
validation, independent reviews, real code execution, rate-limit recovery, configurable retention,
long-term monitoring/forecasting, full API/MCP surface and remote MFA remain
implementation work. See IMPLEMENTATION_PLAN.md and ACCEPTANCE.md.

The short illustrative YAML in SPEC section 5 omits fields required by section 4
and has damaged indentation. The normative schema follows section 4; complete
examples are supplied. Initial 35–55 hours is provisional and insufficient evidence
for secure unattended production operation. A single run cannot prove weeks-long
resilience or cellular access.
