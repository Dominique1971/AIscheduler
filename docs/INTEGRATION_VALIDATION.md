# Codex and Dot integration evidence

Discovery date: 23 October 2026, America/New_York. Probe timestamps are UTC.
Installed CLI: **codex-cli 0.159.0**, resolved by PowerShell `Get-Command codex`
to `C:\Users\domin\AppData\Roaming\npm\codex.ps1`.

The current gate is **real disposable CLI and app-server capabilities partly
verified; scheduler executor acceptance unrun**. Initial discovery used help only.
After explicit user authorization, bounded real probes used ChatGPT login and
removed API-key environment variables. No credentials or unrelated sessions were
inspected, and no global configuration or existing real project was modified.
The scheduler remains simulation-only pending its own executor acceptance gate.

## Evidence matrix

| Capability | Observed evidence | Runtime conclusion / fallback |
|---|---|---|
| Installed CLI | `version.txt`, exit 0, 0.159.0 | Confirmed local executable and version |
| Start independent jobs | Real CLI run `20261024T001621Z-05ccade5` | Two concurrent disposable read-only jobs completed exact responses |
| Persistent identity | CLI resume and app-server read/resume of exact dummy IDs | ID persisted across CLI subprocesses and app-server processes |
| Live status by ID | `thread/read` plus `thread/status/changed` / `turn/started` / `turn/completed` notifications | Owned dummy states read; unloaded thread status is `notLoaded`, not proof of global inactivity |
| Transcripts/artifacts | Original CLI JSONL and `thread/read includeTurns=true` | Owned stored transcripts retrieved; generated file artifact pipeline unrun |
| Resume/retry | CLI resume A and app-server resume B with exact followup | Resume confirmed; automatic retry/recovery semantics remain unverified |
| Redirect instructions | App-server `turn/steer` returns same active turn ID | Acceptance confirmed; semantic adoption unrun because turn was interrupted immediately; CLI queue still unrun |
| Stop/cancel | Final app-server probe `turn/interrupt` then completed/interrupted notification and stored status | Confirmed for owned active no-tool turn; implemented scheduler adapter does not yet expose it |
| Model override | `model/list` yielded seven entries; explicit `gpt-6.1-sol` followup completed | Requested model accepted; broad model compatibility and independent backend attestation unrun |
| Reasoning effort | Explicit `effort: low` on same app-server followup | Accepted with requested available model; CLI config-key route remains unverified |
| Token counts | Real CLI JSONL and app-server `thread/tokenUsage/updated` | Raw usage confirmed; app-server distinguishes `total` and `last`; do not sum cumulative CLI-resume counters |
| Rate limits/costs | App-server emitted `account/rateLimits/updated` | Account window status available; real rate-limit failure/recovery unrun; dollar cost unavailable |
| Approvals/sandbox | Explicit never/readOnly settings; own-repository write denied; same-path workspaceWrite positive control succeeded | Narrow write-policy distinction verified; broad tool/network/approval parity unrun |
| Worktrees | Real CLI diagnostic `20261024T130534Z-f438b82a` | Two separately created disposable Git worktrees accepted exact file writes in parallel with distinct thread IDs; scheduler-created worktree lifecycle remains unrun |
| Desktop interoperability | CLI thread read/resume through independent app-server works | CLI/app-server storage interoperability confirmed; desktop UI parity remains unrun |
| Dot/Pam | No Dot-side endpoint handshake performed | Unsupported/unverified; HTTP contract is only a prospective integration surface |
| Tool/context parity | No matched direct/scheduled task | Acceptance A11 unrun |

## Commands and integrity

`evidence/capabilities/manifest.json` records executable, exact intended argv,
exit status, start/end UTC timestamps, output path and SHA-256 per successful
probe. The seven probes are `--version`, `--help`, `exec --help`,
`exec resume --help`, `app-server --help`, `agents --help`, `queue --help`.
All final probes exited 0. They request help only: no daemon was launched and no
sessions were listed. Capture transport was PowerShell 7 native output as lines,
merged stdout/stderr, serialized once with `Out-File -Encoding utf8`; these files
remain untouched. The capture is text transport, not a byte-for-byte native pipe
capture or a real model execution receipt.

An initial probe harness used expression splatting instead of a named argv array.
Multiword probes accidentally reached the TUI entry path and immediately refused
because TERM was dumb. All initial outputs and their manifest are retained under
`diagnostic-argument-splat/`; these are invalid syntax-probe evidence and must not
be used as execution acceptance. The corrected probes use `$probeArguments` and
`& $executable @probeArguments`. Nothing was repaired in generated output.

Verify file hashes before citing or replaying evidence. `verify_hash()` rejects
changes instead of updating receipts. Preserve future stdout/stderr as original
bytes separately, plus prompt, full arguments, code revision, timing, exit code,
model and configuration provenance. Store costs as unavailable unless actually
reported. Protect logs because tasks can emit sensitive content.

## Preparatory adapter boundary

`scheduler/codex_adapter.py` deliberately has no process launch function and is
disabled by default. An explicit opt-in can construct argv for a disposable Git
repository, read-only sandbox, noninteractive approval failures, JSONL and stdin
prompt. User config is excluded per invocation without changing global settings.
Rules are preserved. This reduced config means parity cannot yet be claimed.

On Windows the resolved `.ps1` shim requires a suitable explicit launcher prefix
(for example PowerShell `-NoProfile -File`); a shell string is never constructed.
The preparatory boundary can accept that prefix but does not resolve, execute or
attest it. Full process launch, worktree management, cancellation, durable status,
recovery, approval review, billing guardrails and runtime gating remain required.

The JSONL parser uses the documented `thread.started` and `turn.completed`
structure, retains unknown events and rejects malformed events, conflicting IDs
and negative/noninteger usage. A completed stream is not artifact acceptance.
Raw hashes, process status and task acceptance remain independent checks. Runtime
probe harnesses are deliberately outside scheduler dispatch and do not enable it.

## Real runtime receipts and retained failures

All paths below are relative to `evidence/`; manifests hash the untouched raw
streams. Runtime probes ran around 00:16–00:20 UTC on 24 October, corresponding to
20:16–20:20 America/New_York on 23 October 2026.

- `codex-runtime/20261024T001621Z-05ccade5`: original concurrent CLI A/B,
  subprocess identity, arguments, prompts and raw JSONL.
- `codex-runtime/20261024T001744Z-resume-da8d279c`: independent CLI resume A.
- `codex-appserver/20261024T001726Z-cc469b01`: installed JSON schemas; raw
  initialize, catalog, read A/B, resume B, and completed exact followup.
  Aggregate report remains **failed** because immediate interrupt raced a turn
  that was acknowledged but had not emitted `turn/started` yet. Steer acceptance
  alone did not establish active execution.
- `codex-appserver/20261024T001909Z-2f17466a`: own-directory write denied by
  sandbox with PermissionError, canary absent. Aggregate report remains **failed**
  after a harness refactor mistakenly returned before waiting for completion.
- `codex-appserver/20261024T001942Z-d985a303`: corrected **control-only passed**
  run; waits for actual start, steers then interrupts a new owned dummy turn,
  observes interrupted completion and re-reads stored interrupted status. Repeated
  canary was denied. Completed followup was deliberately skipped; its evidence
  belongs to the first run, not this run.
- `codex-appserver/20261024T002117Z-positive-50db9a29`: **positive diagnostic
  control passed**, no model invocation. With workspaceWrite restricted to the
  same owned dummy directory, the same previously denied canary path was written
  successfully; command output confirmed its resolved absolute path. The emitted
  diagnostic canary remains untouched in that dummy directory and its bytes/hash
  are preserved in the evidence. It is never a delivery or continuation candidate.

`tests/codex_appserver_probe.py` records raw inbound/outbound JSONL and stderr,
native executable and harness hashes, source CLI evidence integrity, process and
run identity, times, requested model/effort and unavailable dollar cost. The final
run also contains the exact harness source. Timeout is bounded to 120 seconds;
only owned dummy thread IDs are read, and no enumeration method is used. The
stdio process is closed after each probe without modifying the shared daemon.

The canary is a diagnostic fault injection, never a generated delivery candidate.
Negative RPC wrappers report an execution error, while underlying Python ran and
reported permission denial; no canary existed at those negative checks. Their
raw reports conservatively retain the original generic classification about an
unconfirmed setup error. The later independent positive control establishes that
the same Python/path can write when granted workspaceWrite. This narrow result
does not establish every shell/tool/network operation is constrained correctly.

App-server usage exposes both cumulative `total` and `last`. The first completed
followup emitted last input 25,379/output 9 and total input 47,685/output 20.
CLI resume counters appeared cumulative as well. Preserve original counters and
scope rather than silently treating each event as incremental task consumption.

## Remaining scheduler-runtime gate

### Disposable worktree write diagnostic (24 October)

`tests/codex_worktree_probe.py` initialized one new dummy Git repository, created
two branches/worktrees through normal Git commands, then launched two concurrent
installed `codex exec --json --sandbox workspace-write` turns using the existing
ChatGPT login. API-key and custom endpoint variables were removed from each child
environment. Prompts, original JSONL/stderr, emitted file bytes, Git status,
CLI/harness hashes and manifest are retained under `evidence/codex-worktree/`.
Both run manifests independently verify after completion.

- `20261024T130451Z-e44b58e2` is **red**. With `--ignore-user-config`, both
  turns exited 0 and reported completion, but shell writes were rejected by the
  runtime's read-only policy. No marker file existed. This illustrates why CLI
  exit and `turn.completed` alone cannot count as artifact acceptance.
- `20261024T130534Z-f438b82a` is a **green diagnostic**. The only intended
  command-line difference was removal of `--ignore-user-config`; each turn wrote
  its own exact expected UTF-8 bytes, neither wrote in the other worktree, and
  the two thread IDs differ. The original red output was not repaired or reused.

This difference implicates per-invocation configuration loading, but does not
prove which policy setting controlled the result. The green diagnostic runs
direct CLI commands, not the scheduler's dispatch pipeline. The preparatory
adapter still uses `--ignore-user-config` and remains disabled. A real adapter
must make its selected policy explicit, verify effective behavior in its own
normal task path, and preserve native config/tool access expectations without
silently relaxing controls. Dollar cost and broad desktop/tool parity remain
unavailable.

1. Implement an explicitly enabled adapter with owned IDs, bounded lifecycle and
   authentication/billing guardrails. Current harness evidence does not wire it.
2. Use a new disposable repository through the normal scheduler entry point and
   a bounded, harmless task. Record
   untouched stdout/stderr, model/config/code provenance and receipts.
3. Verify scheduled ID, JSONL usage scope, output and sandbox enforcement. Independently evaluate
   output through the normal pipeline; no out-of-band repairs.
4. Run two independent jobs, then dependent jobs; query owned IDs and capture
   actual completion and rate-limit behavior. Exercise interruption/resume,
   failures and restart reconciliation before enabling automatic retries.
5. Compare direct and scheduled tasks for model, context, tools, approvals,
   debugging and Git behavior. Test Dot reachability in its actual environment.

These scheduled runtime tests are unrun. Real standalone capability probes,
helper unit tests and CLI help do not satisfy them. Sustained concurrency,
broader sandbox/approval behavior, costs, semantic correctness and desktop UI
parity remain uncertain.

## Official documentation consulted

[Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
fetched 23 October 2026, documents `exec --json`, stream identity/usage fields,
saved authentication reuse and per-invocation configuration controls. This is
documentation evidence, not installed-runtime verification.

[Codex App Server](https://learn.chatgpt.com/docs/app-server), fetched the same
date, supplied protocol guidance. Installed generated schemas were checked before
sending methods. Lifecycle conclusions above come from preserved real responses
and notifications, with limitations stated separately.
