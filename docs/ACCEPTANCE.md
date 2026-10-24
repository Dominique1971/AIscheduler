# Acceptance ledger — 23 October 2026

The full specification is not accepted yet. A fresh simulation run is useful
evidence for the simulation product; it is not real generator acceptance.

## Recorded runs

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
- Short controller trial `evidence/soak/20261024T000554Z-4bc38639` passed 10.85s /
  three compressed batches. **Not 24-hour acceptance.**
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
| A6 Cellular MFA | Unrun, no tunnel/publication |
| A7 Refresh/manual/stale | 300s source timer + live manual controls; elapsed timer/staleness test unrun |
| A8 Compact 8h overview | Browser viewport checks passed; physical phone unrun |
| A9 Preserve completed | Fresh revision/split/receipt preservation passed; rollback UX pending |
| A10 Recovery states | Synthetic retries/review/blocking passed; real recovery unrun |
| A11 Native parity | Unrun |
| A12 24h soak | Running, not passed |
| A13 Test scope | Targeted diagnostics then broad suite at slice boundary; worker validation profiles pending |
| A14 Token reporting | Simulation labels unavailable; parser diagnostic only; real counters unrun |

Manifests hash original files. Never regenerate one to bless changed artifacts.
`python -m scheduler --db PATH verify` checks SQLite, immutable revisions and
attempt hashes; trace rejects changed receipts. This establishes consistency,
not semantic correctness, tamper-proof logs or subscription allowance.

Real Codex, tool parity, reboot, remote identity/cellular, forecasting, resource
pressure and long-term reliability remain uncertain. No real-project onboarding
until gates pass and explicit project authorization is recorded.
