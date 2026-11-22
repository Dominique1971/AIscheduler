# Claude <-> Codex mailbox for the Site (same pattern as Koboo)

Claude writes one task per file into `inbox/` (names sort in order: T001-*.md).
Codex takes the lowest-numbered task, does it, moves the task file to `done/`,
and writes `results/<task>.result.md`. Claude reads results and writes the next task.
Write files under a temp name, then rename, so a half-written file is never read.

Result file must contain: status (done/failed), Site version, deployment ID,
the commands run with exit codes, and EVIDENCE: for each tab (#overall, #project,
#harness, #loops, #models, #cost, #new) the visible page text and a screenshot saved
to `handoff/results/evidence/<task>/`. No secrets, TOTP codes, tokens or env values.

Rules: REMOTE_CONTROL_ENABLED stays false; owner-only audience and read-only bypass
unchanged; Codex checks `inbox/` every 15 minutes while a session is open.
