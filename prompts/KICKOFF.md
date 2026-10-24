# Kickoff — autonomous scheduler

Implement a standalone, reusable multi-project scheduler based on `docs/SPEC.md`.

## First phase: feasibility and inventory

1. Read the full specification and enumerate requirements, open questions, and contradictions.
2. Test, rather than assume, Codex execution launch, persistent task/session identifiers, retrieval by ID, status inspection, cancellation, resume, model override, and usage reporting. Distinguish CLI, desktop, and Dot capabilities.
3. Document verified capabilities and gaps in `docs/INTEGRATION_VALIDATION.md`, with commands, observed results, and dates. Do not fabricate support.
4. Propose architecture and an incremental implementation plan with dependencies and acceptance criteria. Keep native Codex usage possible without the scheduler.

## Implementation constraints

- Build the scheduler as a separate repository and service, independent of Koboo, Oppo, and Compass.
- Use dummy projects with real but harmless tasks, fake dependencies, injected failures, plan revisions, and multiple workers for acceptance tests.
- Prioritize durable state, dependency-safe dispatch, automatic backfill, crash recovery, clear escalation, and remote security.
- Keep the dashboard compact, mobile-friendly, and readable without vertical scrolling in its overview. Default to the last eight hours; refresh every five minutes with manual refresh.
- Build the remote phone dashboard as an owner-private OpenAI Site. Keep Python scheduling and Codex execution local; use an outbound-only bridge. Prove Site visitor identity, independent MFA, and unattended machine access before publishing remote controls. Do not use or alter the Supabase connection serving Oppo and Compass.
- Do not expose a remotely controllable executor without authentication, authorization, and audit logging.
- Do not launch tasks against existing projects or incur external costs without authorization.

## Delivery

Produce a phased plan, implement and test the smallest safe vertical slice, report verified results and blockers, then proceed through the documented gates. If the spec is ambiguous or requires a material architectural change, surface a specific decision rather than guessing.
