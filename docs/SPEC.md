Standalone product requirements, technical architecture, integration validation and acceptance test plan \| Version 1.1 \| 24 October 2026

# 1. Product objective

Build an independent, reusable local-first orchestration service for continuous, weeks-long AI development across multiple projects. The scheduler directly manages execution; Pam (OpenAI Dot), Codex desktop/CLI, and the human dashboard are optional peer interfaces, never required intermediary links. Optimize verified completed work and low human intervention, not token consumption. Initial target: six configurable workers, e.g. 4 Koboo + 1 Oppo + 1 Compass. No hardcoded project names or fixed worker count.

# 2. Non-negotiable principles

Additive integration: preserve direct Codex use, native tools, context, models, interactive debugging, approvals, Git actions, and normal Pam workflows. Never route all operations through the scheduler. Deterministic scheduler core; AI may propose plans, troubleshoot and review, but cannot silently redefine objectives. Durable task identity, auditable transitions, bounded autonomous recovery, least privilege, clear human escalation. Projects and plans are portable and versioned. The scheduler must work without Pam or a dashboard session.

# 3. System architecture

Independent repository/service, ideally Python orchestration daemon, SQLite in WAL mode for initial single-host operation, versioned REST API and optional MCP adapter, local executor adapter for Codex, simulation executor, responsive browser dashboard, and CLI. Separate planner/importer, dependency graph engine, admission controller, dispatcher, worker lifecycle manager, watchdog, event journal, reconciliation service, estimator, metrics aggregator and authentication gateway. All business logic behind stable interfaces. Do not assume desktop-app session APIs or session IDs exist; prove them first. If unsupported, run Codex CLI workers and store CLI execution identifiers while keeping desktop access independent. The remote phone dashboard target is a private OpenAI Site with supported hosted HTTP code and D1 storage; Python scheduling, SQLite authority, and Codex execution stay local. An outbound-only local bridge exchanges bounded projections and typed control requests with the Site. Site hosting must not be treated as a Python process host or a direct connection to the local scheduler.

# 4. Canonical project input contract

Provide JSON Schema 2020-12 as normative machine-readable contract and YAML as preferred human/AI authoring format. Required project fields: schema_version, project_id, display_name, revision, goal, repository locator, root branch, policy, task list. Each task: immutable task_id, title, description, acceptance_criteria, dependency task IDs, estimate_minutes, priority, executor type, model preference/override, reasoning effort if supported, resource needs, risk class, allowed operations, validation profile, artifact outputs, timeout policy and escalation conditions. Optional task groups/milestones, due dates, concurrency caps, skill requirements and token budget. Strict validation: unique IDs, resolvable dependencies, DAG/no cycles, valid model/executor compatibility, schema errors with line numbers. Provide a reusable Plan Builder skill and templates to create compliant plans from project goals. Import must not silently create unapproved work.

# 5. Example canonical YAML

schema_version: "1.0"  
project_id: "demo-weather"  
revision: 1  
display_name: "Weather Data Demonstration"  
goal: "Generate and analyze reproducible sample weather observations"  
repository: {path: "./demo-weather", base_branch: "main"}  
policy: {max_workers: 4, merge: "feature-batch", full_regression: "daily"}  
tasks:  
- task_id: A  
title: Generate synthetic observations  
description: Create deterministic sample NJ temperatures, not live weather  
depends_on: \[\]  
estimate_minutes: 4  
priority: 80  
executor: simulation  
model: {preference: default}  
acceptance_criteria: \["CSV produced", "100 rows"\]  
- task_id: B  
title: Calculate daily averages  
depends_on: \[A\]  
estimate_minutes: 3  
priority: 60  
executor: simulation  
model: {preference: default}  
acceptance_criteria: \["Averages match fixture"\]

# 6. Plan revisions and live reload

Support create_project, validate_plan, preview_plan_diff, apply_plan_revision, list_revisions and rollback_plan_revision. Immutable revision history; immutable task IDs across revisions. Diff added/removed/modified tasks, changed edges, changed estimates and resource allocations. Preserve completed results, provenance, logs and active work whenever compatible. Do not mutate a running task’s execution contract in place: queue replacement, let safe work finish, or request controlled cancellation. Reject cycles and dependencies on deleted/unavailable outputs. Re-evaluate ready queue transactionally. Dry-run preview and risk classification before applying; require human approval for material scope or architectural changes. A plan update must not accidentally launch duplicates or discard task history.

# 7. Scheduling and worker allocation

Maintain global max workers and per-project min/max/target allocations. Dynamically reallocate spare capacity to eligible ready tasks while honoring explicit reserved slots, priority, fairness and resource limits. Dispatch only tasks whose dependencies have succeeded and outputs passed acceptance checks. Backfill promptly when workers finish; do not wait for dashboard refresh or Pam prompts. Support project pause/resume, task hold/unhold, worker target changes, priority updates and global emergency stop. Define pause as stop-new-dispatch by default; optionally request graceful cancellation of active tasks. Display allocated, busy, ready, blocked and idle slots separately. Prevent starvation with aging/fair scheduling; deterministic tie breaks.

# 8. Execution identity and Codex capability validation

Before implementation commitments, experimentally verify: launch Codex tasks programmatically; stable execution IDs; query live status by ID; retrieve transcript/artifacts; stop/cancel; resume/retry; redirect instructions; model and reasoning override; CLI vs desktop session interoperability; approval handling; rate-limit reporting; token counters; repository/worktree isolation; tool access parity. Record evidence, API versions and fallbacks. Unsupported features must be visibly marked unsupported, never simulated as if real. Pam must be able to locate scheduler task ID -\> Codex execution ID -\> evidence if tools permit. Direct Codex sessions not launched by scheduler may be manually linked or imported read-only, without claiming full control.

# 9. Worker lifecycle, resilience and recovery

State machine: draft, queued, dependency-blocked, ready, starting, running, validating, completed, retrying, recovering, waiting-review, paused, failed, canceled, superseded. Persist every transition and heartbeat. Monitor process liveness and meaningful progress (output, checkpoints, test artifacts, tool activity); distinguish legitimate long-running tasks from hung ones. Use adaptive thresholds based on estimates and phase, with warning at 2x estimate and escalation at 4x as configurable defaults, not automatic cancellation. Bound retries and recovery time; attach recovery attempts as linked phases preserving original start/end and cost. Handle process crashes, host reboot, lost connectivity, stale locks, partial commits, rate limits, resource pressure and scheduler restart. Use idempotency keys, leases, fencing tokens and reconciliation to avoid duplicate dispatch. Exactly-once external side effects cannot be guaranteed; design safe idempotent operations and explicit reconciliation.

# 10. Judgment and escalation policy

Autonomously fix narrow test failures, transient tooling issues and reversible defects within preauthorized time/budget limits. Escalate when assumptions change materially, architecture or scope shifts, data destruction or sensitive operations are proposed, repeated recovery fails, task estimates are grossly exceeded without progress, or unexpected dependencies emerge. Other projects/workers continue when one task awaits review. Each escalation includes concise context, evidence, attempted remedies, impact, alternatives and requested decision. Prevent overengineering by bounding exploratory branches and measuring accepted deliverables rather than generated code.

# 11. Git, integration and tests

Use isolated Git worktrees/branches per worker and commit checkpoints. Merge by meaningful feature/milestone batches, not every micro-task. Before merge: relevant unit tests and targeted integration tests, independent review when feasible, conflict checks, artifact validation. Broader tests after batches; full regression on daily schedule and after major architecture changes, not every narrow fix. Inventory existing test suites and measure timings before selecting thresholds. Quarantine failing branches, investigate targeted failures, and avoid rolling back unrelated changes. Production deploys and destructive actions remain separately controlled.

# 12. Dashboard UX

Mobile-first, externally accessible, one-screen compact overview with no vertical scrolling at target device viewports. Default horizontal time axis last 8 hours, anchored to now; pan horizontally and zoom to 1h/24h/7d. Per-project expandable timeline with worker lanes, parallel task bars, actual start/end, estimated finish, retry phases, dependencies and blocked markers. Overall top strip: active/target workers, ready queue, completed/total, percent complete, progress trend, utilization, warning count and last successful update. Small trend plots for completion, worker utilization, estimated vs actual throughput. Status conveyed by accessible color PLUS icons/labels. Tap task for details; tap project for original and current plans, graph of dependencies, revisions and task history. On phone show concise overview with project-specific focus modes, never microscopic unreadable text. Provide explicit refresh now and auto-refresh every 5 minutes; show data age/stale indicator. Scheduler worker monitoring remains independent and much faster.

# 13. Remote access and security

Expose the remote dashboard through an owner-private OpenAI Site over HTTPS, with no router port forwarding. Keep the scheduler's Python API on loopback; its outbound-only bridge uses supported machine-to-Site access, distinct from visitor identity. Verify private audience enforcement, stable owner identity, service access availability and recovery, and the Site runtime's suitability experimentally before deployment. Strong auth with an independently verified MFA requirement, session expiration, CSRF protection, server-side role controls, rate limiting, input validation, audit logs, secrets management and encrypted transport remain mandatory. ChatGPT sign-in by itself is not evidence of MFA. If Sites cannot satisfy both MFA and unattended bridge access, keep remote control unpublished and escalate the specific gap; do not weaken this section or silently substitute another provider. Never expose Codex credentials or arbitrary shell access through a public unauthenticated API. Read-only access separated from control actions; dangerous commands require confirmation. Android phone can inspect tasks, change worker allocations, pause/resume and invoke emergency stop. Test on cellular network, not only home Wi-Fi. Do not create a Supabase scheduler project or disturb the existing Oppo/Compass Supabase connection.

# 14. Persistence, history and forecasting

Persist projects, immutable plan versions, tasks, dependency graph, execution attempts, worker leases, transitions, timestamps, estimates, logs pointers, approvals and audit events across restart. Keep durable project state indefinitely until explicitly deleted. Default execution/audit history \>=90 days, high-resolution monitoring samples 7 days, aggregate older samples for long-term trend. All configurable, with size-based cleanup and backup/restore. Start/end times in UTC with NY-local display. Record estimated and actual elapsed/active time separately; update estimates with cheap rolling median/weighted statistics from comparable task types, no mandatory model call. Show forecast confidence and avoid false precision. Record input/output token counts and model when executor exposes them; label unavailable otherwise, and never equate API tokens with ChatGPT subscription allowance.

# 15. API, MCP and Pam interaction

Expose stable documented operations: projects.list/get/create, plans.validate/preview/apply/history, tasks.list/get/trace, executions.get/status/logs, workers.list/allocate, projects.pause/resume, tasks.retry/hold, metrics.summary/timeseries, alerts.list/ack, system.emergency_stop and system.health. Use API versioning, pagination, idempotency keys, request authorization and structured errors. Optional MCP server wraps same domain API so Pam or other compatible assistants can query and control with permissions; capability must be tested in Pam's environment. Pam may still perform native research, Codex delegation and normal conversations. Status answers must come from authoritative scheduler state, with freshness timestamps, not memory alone.

# 16. Dummy-first verification program

Phase 0: capability spike against real installed Codex interfaces; document verified vs unsupported operations. Phase 1: deterministic simulation with \>=12 tasks, two dummy projects, DAG forks/joins, varied estimates, 4 then 6 workers, artificial latency, failure, recovery, pauses and plan revision mid-run. Phase 2: real low-risk Codex tasks in disposable repositories (generate CSV, compute summary, write tests, compare results); independent tasks run in parallel and dependent tasks wait. Phase 3: private Site capability spike and remote Android control from cellular, including actual owner MFA, anonymous/wrong-owner denial, machine-to-Site bridge authentication, auth/refresh, audit integrity, and recovery after service/host restart. Local mocks and a deployed read-only Site are intermediate diagnostics, not cellular control acceptance. Phase 4: parity tests comparing same task direct Codex versus scheduled Codex for model, context, tools, approvals, debugging, outputs and Git. Only after passing gates attach real projects. Include test that one running task splits into two new dependent tasks without losing unrelated progress.

# 17. Quantitative acceptance criteria

A1: no duplicate dispatch of the same attempt under restart/race tests. A2: 100% DAG precedence respected in deterministic suite. A3: refill a free worker within 15 seconds of eligible task becoming ready under healthy local conditions (configurable target). A4: recover consistent persisted state after forced restart, with no silent task loss. A5: user can change 4/1/1 to 2/2/2 allocations without restarting service. A6: remote phone control over cellular with MFA and complete audit events. A7: dashboard auto-refresh \<=5 min plus manual refresh and visible staleness. A8: default last-8-hour view, compact one-screen no vertical scroll on agreed phone/desktop viewport sizes. A9: preserve every completed task across plan revision; explain each diff. A10: fail/blocked/recovering clearly distinct and logged. A11: Codex parity test report and documented exceptions. A12: unattended 24-hour dummy soak test with synthetic failures and backfill; no user prompt required. A13: full regression not run on narrow fix unless explicitly requested. A14: task token accounting shown only where supported. These are proposed engineering targets, not verified platform guarantees.

# 18. Delivery stages and gates

Stage I (discovery): verify local OS, Codex app/CLI version, CLI/API interfaces, Pam custom-tool reachability, test tools, security and resource constraints; produce evidence matrix and revised estimates. Stage II (core MVP): schema, SQLite, DAG, simulator, dispatcher, leases, restart recovery, CLI/API. Stage III (Codex adapter): real task launch, worktrees, progress, tests, retries, model overrides where verified. Stage IV (dashboard + remote): timeline, metrics, phone actions, tunnel/auth. Stage V (robustness): watchdog, replanning, forecasting, token reporting, parity, soak tests. Stage VI (optional): advanced MCP/Pam features and multi-host support. Earlier 35–55 engineering-hour estimate is provisional and may be low given security, compatibility and 24/7 resilience; require a bottom-up estimate after Stage I, and avoid a big-bang build.

# 19. Risks, exclusions and decisions

Risks: undocumented Codex desktop automation, unknown Pam tool support, subscription rate limits, machine sleep/reboots, multiple workers exhausting RAM/GPU, long test suites, remote attack surface, Sites runtime/service-access limits and Git conflicts. Initial release is single-host, not distributed exactly-once execution; no claim of unlimited concurrency or subscription-token visibility. Do not build a custom LLM runtime, replace Codex UI, or require Pam for execution. Pending decisions after discovery: supported Codex adapter, verified private Site MFA and bridge access, precise phone viewport, allowed autonomous shell permissions, token/compute budget controls and actual task throughput targets.

# 20. Handoff instructions for Codex

Create a NEW independent repository; do not modify Koboo/Oppo/Compass during discovery or dummy testing. Begin with capability tests and architecture decision record, then commit versioned schema, example plans, API contract, simulation fixtures, acceptance tests and implementation roadmap. Report unsupported Codex/Pam capabilities before designing dependent features. Implement vertical slices with reproducible test results and screenshots of mobile/desktop dashboard. Avoid overengineering; prioritize continuously useful autonomous execution and measurable outcomes. Preserve native Codex workflows and explicitly document what the scheduler cannot control.
