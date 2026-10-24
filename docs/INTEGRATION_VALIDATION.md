# Codex and Dot integration evidence

Discovery date: 23 October 2026, America/New_York. Probe timestamps are UTC.
Installed CLI: **codex-cli 0.159.0**, resolved by PowerShell `Get-Command codex`
to `C:\Users\domin\AppData\Roaming\npm\codex.ps1`.

The current gate is **syntax discovery passed; real execution acceptance unrun**.
No inference was requested, no credentials or unrelated sessions were inspected,
and no user configuration, native workflow, or other project was modified.
The scheduler must remain simulation-only until the runtime gate below passes.

## Evidence matrix

| Capability | Observed evidence | Runtime conclusion / fallback |
|---|---|---|
| Installed CLI | `version.txt`, exit 0, 0.159.0 | Confirmed local executable and version |
| Start independent jobs | `exec-help.txt` advertises noninteractive execution | Advertised only; concurrent launches unrun |
| Persistent identity | `resume-help.txt` accepts session UUID/name | Advertised only; identity durability unrun |
| Live status by ID | `agents-help.txt` advertises browsing daemon sessions; experimental app-server exists | No machine-readable query verified; scheduler-owned process status must not impersonate Codex authoritative state |
| Transcripts/artifacts | `exec-help.txt` advertises JSONL and final-message output | No real stream/artifact retrieval verified |
| Resume/retry | `resume-help.txt` accepts ID and follow-up prompt | Advertised only; no existing thread touched |
| Redirect instructions | `queue-help.txt` advertises thread ID plus message | Advertised only; delivery timing/control unverified |
| Stop/cancel | No tested CLI cancellation operation | Unsupported by implemented adapter; killing a local process cannot yet establish remote/daemon cancellation |
| Model override | `exec-help.txt` advertises `--model` | Syntax confirmed, account/model compatibility and actual selection unrun |
| Reasoning effort | Generic `--config key=value` exists | Proposed setting unverified against installed runtime/model; never promise compatibility |
| Token counts | Official documentation describes usage fields in completed JSONL turns | Documentation only; fixture parser diagnostic passed, real usage unavailable |
| Rate limits/costs | No real request issued | Reporting unverified; no token-to-subscription or dollar conversion |
| Approvals/sandbox | Help advertises approval policy and read-only/workspace-write modes | Enforcement and noninteractive approval behavior unrun |
| Worktrees | Help advertises `--worktree` | Isolation and lifecycle unrun; no application-created worktree |
| Desktop interoperability | Shared daemon and CLI agents are advertised | Not tested against desktop; native app remains independent |
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
Raw hashes, process status and task acceptance remain independent checks.

## Next disposable-runtime gate

1. Confirm permitted authentication/billing route without printing credentials;
   do not assume an existing login proves a no-charge execution route.
2. Use a new disposable repository and a bounded, harmless read-only task. Record
   untouched stdout/stderr, model/config/code provenance and receipts.
3. Verify ID, JSONL usage, output and sandbox enforcement. Independently evaluate
   output through the normal pipeline; no out-of-band repairs.
4. Run two independent jobs, then dependent jobs; query owned IDs and capture
   actual completion and rate-limit behavior. Exercise interruption/resume,
   failures and restart reconciliation before enabling automatic retries.
5. Compare direct and scheduled tasks for model, context, tools, approvals,
   debugging and Git behavior. Test Dot reachability in its actual environment.

These runtime tests are unrun, and neither helper unit tests nor CLI help satisfy
them. Account access, concurrency, sandbox behavior, costs, semantic correctness
and desktop/CLI lifecycle relationships remain uncertain.

## Official documentation consulted

[Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
fetched 23 October 2026, documents `exec --json`, stream identity/usage fields,
saved authentication reuse and per-invocation configuration controls. This is
documentation evidence, not installed-runtime verification.
