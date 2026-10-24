# Acceptance ledger — 24 October 2026

The full specification is not accepted yet. A fresh simulation run is useful
evidence for the simulation product; it is not real generator acceptance.

## Recorded runs

- Latest project intake run `evidence/intake/20261024T162250Z-d3975619/` passed
  through the normal intake CLI, canonical validation, preview, import,
  simulation daemon and snapshot on a disposable brief. Three tasks retained
  their authored descriptions, estimates and dependencies; total effort was
  9 minutes and dependency critical path 7 minutes, both estimates only.
  Dependency precedence held and all 16 post-exit file hashes, source hash
  and five code hashes verified. This accepts the intake transformation and
  synthetic scheduling path only; no CSV, chart or real Codex artifact was made.
- Earlier intact intake run `20261024T161849Z-69e7805b` passed against the
  preceding source revision. The fresh run above covers the current intake
  transform after its source-kind provenance update.
- Intake UI source passed JavaScript syntax check and its preview API passed
  authenticated TestClient diagnostics. Browser automation did not initialize,
  so form interaction and visual layout are **unrun**, not accepted.
- The preceding intake run `20261024T161835Z-95724fdc` reported green during
  execution but its manifest captured transient SQLite sidecars that vanished
  after exit. **Rejected as consumable acceptance evidence**, not patched.
  The reusable harness now closes the checkpoint connection before manifest
  creation. The original raw outputs and inaccurate manifest remain retained.

- Latest fresh pass: `evidence/acceptance/20261024T001345Z-dd456acd/` (UTC run ID;
  October 23, 8:13pm New York). Normal CLI -> actual loopback API + independent
  daemon -> untouched receipts/database. Twenty authored dummy tasks: 18 completed,
  one exhausted synthetic retries and entered review, one dependency-blocked.
  Four active workers observed; six capacity configured. Forced kill/restart,
  active split, immutable contract, receipt preservation, RBAC, idempotency,
  emergency confirmation and online backup/restore exercised. Original inputs,
  outputs, database, hashes and code provenance retained. Synthetic receipts
  do not prove arbitrary task criteria.
- Integrity gate passed for all 239 latest run/source files in
  `evidence/diagnostics/integrity-final-02.json`. Use
  `python tests/verify_acceptance_evidence.py RUN_DIRECTORY --current-source`.
- Earlier raw reports `20261024T000349Z-982059dd`, `20261024T000907Z-e640f133`,
  `20261024T001035Z-45924344` said passed, but their manifests captured ephemeral
  SQLite sidecars that disappeared at process exit. **Rejected as consumable
  acceptance evidence**, never patched. The harness now closes the native SQLite
  checkpoint connection before manifest creation; latest fresh run verifies after
  process exit. Rejection details retained in `integrity-rejected-history.json`.
- First run `20261024T000338Z-5b18470d` remains **red**. The fixture expected a
  queued task to be immutable as though running. Normal authored input priorities
  and the precondition were corrected in the reusable harness, then a new run
  performed. No old output was patched or adopted.
- Diagnostics: **52 passing** unit/API/fixture tests in
  `evidence/diagnostics/final-suite-02.txt`. Earlier red diagnostics retained.
  Includes concurrent fencing, corruption rejection, reservations, schema
  negatives, expiry and malformed HTTP. Not fresh Codex acceptance. A TestClient
  dependency emits a non-failing deprecation warning.
- Packaging: isolated wheel build and installed schema/API smoke passed. Final
  wheel SHA-256 `db13fce8ac5deb939ad1bd101120ea35d6d61bcdaccec871e2a44e94d7accc5a`.
  Build/install/smoke transcripts retained; runtime wheel ignored by Git.
- UI: authenticated normal browser controls, final source/screenshots/bounds in
  `evidence/dashboard/ui-verification-receipt.json`. Overview has no vertical
  overflow at 1280×720 and 390×844. Project focus opens detailed timeline.
  Browser viewport emulation is not physical Android/cellular testing.
- Real capability probes (separate from generator acceptance): two concurrent
  ChatGPT-authenticated CLI runs and same-ID CLI resume passed under
  `evidence/codex-runtime`. Own-thread app-server retrieval/resume, explicit
  model/effort and active-turn steer/interrupt were exercised under
  `evidence/codex-appserver`. Original red timing/harness probes retained.
  Protocol IDs and raw token counters are confirmed; real scheduled artifacts,
  worktree isolation, tool parity and rate-limit recovery are still unrun.
- Short controller trial `evidence/soak/20261024T000554Z-4bc38639` passed 10.85s /
  three compressed batches. **Not 24-hour acceptance.**
- Dummy phone control trial `evidence/remote-sites/20261024T155802Z-f92958ea-control/`
  passed through the normal owner-private Site → D1 command → outbound bridge →
  loopback API path. After a fresh TOTP controller login, the owner reported
  tapping Pause for Demo Weather on the phone. The hosted command and audit
  recorded one successful pause; the raw bridge journal recorded HTTP 200
  acknowledgment, and the untouched local snapshot shows Weather paused while
  Inventory remains unpaused. All 10 raw-output hashes, journal hash, two input
  hashes and 170 receipt filename hashes verified. The bounded five-minute run
  used disposable projects only; no scheduled Codex task or fresh cellular
  control was exercised. Site controls were disabled again after the trial.
- Full soak **RUNNING, not passed**: `evidence/soak/20261024T001115Z-4cbca9a7`,
  supervisor PID 43032. Started October 23 at 8:11:15pm New York; deadline
  October 24 at 8:11:15pm. Independent hidden Python process and child daemon;
  hourly 12-task simulation bursts, bounded failures, periodic daemon kills and
  idle monitoring. First batch completed. This is not sustained inference load.
  Source changes, host sleep, process termination or reboot may invalidate it.
  Require the actual final report and hash verification before claiming pass.

## Requirement gates

| Criterion | Status / evidence |
|---|---|
| A1 No duplicates | Fresh simulation restart passed; race diagnostic; external effects unrun |
| A2 DAG precedence | Passed within finite fresh simulation fixtures; Codex unrun |
| A3 Backfill <=15s | Automatic continuation exercised; dedicated quantitative stress gate pending |
| A4 Recovery | Forced daemon restart passed; host reboot / real-process reconciliation unrun |
| A5 4/1/1 ->2/2/2 | Three-project diagnostic passed; fresh two-project allocation controls passed |
| A6 Cellular MFA | Owner TOTP and dummy phone Pause verified; read-only cellular reachability user-observed; fresh login/control over cellular unrun |
| A7 Refresh/manual/stale | 300s source timer + live manual controls; elapsed timer/staleness test unrun |
| A8 Compact 8h overview | Browser viewport checks passed; physical phone read-only view and one dummy Pause observed; 8h endurance unrun |
| A9 Preserve completed | Fresh revision/split/receipt preservation passed; rollback UX pending |
| A10 Recovery states | Synthetic retries/review/blocking passed; real recovery unrun |
| A11 Native parity | Unrun |
| A12 24h soak | Running, not passed |
| A13 Test scope | Targeted diagnostics then broad suite at slice boundary; worker validation profiles pending |
| A14 Token reporting | Simulation labels unavailable; real CLI/app-server counters captured, scheduler accounting not integrated |

Manifests hash original files. Never regenerate one to bless changed artifacts.
`python -m scheduler --db PATH verify` checks SQLite, immutable revisions and
attempt hashes; trace rejects changed receipts. This establishes consistency,
not semantic correctness, tamper-proof logs or subscription allowance.

Real Codex, tool parity, reboot, fresh cellular control, forecasting, resource
pressure and long-term reliability remain uncertain. No real-project onboarding
until gates pass and explicit project authorization is recorded.
