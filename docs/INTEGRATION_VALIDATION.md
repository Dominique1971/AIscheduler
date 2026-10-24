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

## Private OpenAI Sites remote diagnostic (24 October)

The migration source is committed on GitHub `master` at `130c21f`, pushed to the
separate Sites source repository at `ba4b1643cc25a21c2fc906ebf32967f694659f13`,
and saved as Site version 1. The owner-private diagnostic deployment
`appgdep_6adcbbd1dd008191a851a9f3872f2a70` succeeded at
`https://autonomous-scheduler.jetpack71.chatgpt.site`. Environment revision 1
sets only `APP_ORIGIN`, `IDENTITY_PROBE_ENABLED=true`, and
`REMOTE_CONTROL_ENABLED=false`. There is no bridge connection, TOTP enrollment,
owner identity configuration, or live scheduler control. The Site access policy
reported one owner and no external visitors; its account user ID has **not** been
assumed to equal the per-Site authenticated-user header.

The normal local Worker bundle validated and four direct Worker/SQLite diagnostic
tests passed. The Python bridge's seven targeted tests passed. These tests inject
the Sites identity header and therefore cannot establish hosted identity or MFA.
The deployed `/setup/identity` probe was then requested without credentials and
with the `siwc_bypass_bearer_token` returned by the Sites `get_site` tool. Raw
responses and hashes are in `evidence/remote-sites/20261024T140824Z-private-probe/`.
The anonymous request returned Cloudflare HTTP 403 (`error code: 1010`); the
service-token request returned a Sites HTML **401 Sign in required** rather than
the Worker's JSON 401. Thus the service request did not reach the Worker, and
unattended bridge access is **red/unverified** despite the token being listed.
The token value was neither logged nor stored. Sites reported no dollar cost.

The in-app browser and Node REPL diagnostic tools failed to initialize with
`failed to write kernel assets`, so an owner-signed-in browser request and Android
cellular test were not run. Do not enable controls or connect a bridge until the
actual Sites visitor ID, private audience denial, separate TOTP, D1 migration,
and an unattended authenticated bridge request are observed through the normal
hosted path. The failed service request is not evidence that Sites cannot support
service access generally; its cause remains unresolved.

The hosted Worker log for an authenticated browser rendering request reached
the deployed Worker with `oai-authenticated-user-email` and optional name
headers, but no `oai-authenticated-user-id` header in the recorded request.
The root route returned 503 because the full owner/TOTP/agent configuration is
intentionally absent. This is a real hosted observation, not proof that every
visitor request omits the ID. Source after version 1 now supports exact
platform-authenticated owner email as a fallback; that new source needs its own
normal build and deployment before it can count as hosted evidence.

The email-fallback source was pushed to the Sites source repository at
`b25a40742c7fcbf214d57948ee6b81b4dab4f4b9`, saved as version 2, and
privately deployed as `appgdep_6adcbd1b74a081918f622125908f8910` with the
same environment revision and controls disabled. This version adds a harmless
diagnostic landing page so an authenticated owner does not encounter the
unconfigured dashboard's 503. A fresh anonymous `GET /` returned HTTP 401.
No owner-signed-in response or successful service-token request has yet been
captured on version 2; hosted identity and bridge acceptance remain unrun/red.

### Version 2 follow-up: identity and rotated service token

The owner opened `/setup/identity` while signed in and reported JSON containing
both `site_user_id` and `site_user_email`. This is a user-observed live result,
not an independently captured raw browser response. The ID is available for
`OWNER_SITE_USER_ID` configuration; its personal value is omitted from the
repository. The earlier absence of the ID in one Worker log is therefore not a
general property of the hosted runtime. The owner also explicitly authorized
generating and testing a new Sites bypass token.

A new token was generated through Sites, held only in the tool session, and sent
to the version 2 private deployment via `OAI-Sites-Authorization: Bearer ...`.
The normal HTTP request to `/setup/identity` returned HTTP 401 with
`application/json` and the Worker's `site_sign_in_required` error. This is the
expected result for a service request without visitor identity and proves that
the rotated token reached the Worker. The unauthenticated request received HTTP
403 at the edge. Raw bodies, request metadata, SHA-256 hashes and the receipt
are in `evidence/remote-sites/20261024T152000Z-rotated-token/`; the token
value is not present. All four raw response hashes across the two attempts
were checked against their receipts.

An initial probe attempt inadvertently received EOF on stdin and sent an empty
bearer value. Its untouched raw results and receipt remain in
`evidence/remote-sites/20261024T151703Z-rotated-token/`, with a separate note
correcting the receipt's inaccurate credential description. That attempt is
**not** evidence for the new token. The valid probe establishes Site dispatch
reachability only. Agent authentication, owner TOTP, bridge polling,
private audience denial for a different signed-in user, mobile cellular access,
and scheduler control are still unrun. Remote controls remain disabled.

A subsequent read-only Sites database overview reported the
`SCHEDULER_REMOTE` binding with all six tables from the initial migration:
`audit`, `commands`, `mfa_counters`, `rate_limits`, `sessions`, and `snapshots`.
This corrects the earlier claim in this section that the D1 migration was
pending. Table presence is a hosted schema observation, not an end-to-end data
flow or TOTP acceptance test.

### Version 3: owner enrollment and agent boundary

The first-time TOTP enrollment requirement was added to `docs/SPEC.md` before
implementation. Site source commit `bd55f969e1ee7fddfd412091aaef7fd0bd592faa`
builds an owner-only `/setup/totp` page. It shows the seed only while controls
are disabled and no TOTP verification counter exists for the owner; successful
verification closes the page. Six direct Worker/SQLite diagnostic tests passed,
including wrong-owner denial, first verification, and enrollment closure. The
Site source package was built, tested, validated, pushed, and deployed privately
as version 3, deployment `appgdep_6adccd5f3884819197191c6839f953b6`
(`succeeded`). Environment revision 3 has the exact Site user ID and separate
TOTP and agent secrets, all hidden as Site secrets. The identity probe is off,
temporary enrollment is on, and `REMOTE_CONTROL_ENABLED=false`.

A hosted service probe used the rotated Sites bypass token and the distinct
agent token. Without a visitor identity, `/setup/totp` returned Worker's JSON
403 `owner_required`. The disabled `/setup/identity` returned Worker's JSON 404.
An agent-authenticated `/agent/poll` request with an intentionally invalid
snapshot returned Worker's JSON 422 `invalid_snapshot`, showing that the
request passed the two service credential checks and reached contract validation.
The untouched bodies, SHA-256 hashes, and request receipt are in
`evidence/remote-sites/20261024T152354Z-v3-access/`; all three body hashes were
verified. This is an access diagnostic, not a successful poll or bridge test.
Sites did not report dollar costs.

The Site access and agent tokens are stored locally in an ignored Windows
CurrentUser DPAPI file for `remote/site_bridge.ps1`; a decryption round trip
confirmed their lengths without revealing either token. The local API control
token has not been provisioned to that launcher, and the normal Python bridge
has not been run against the hosted Site. The owner has been asked to enroll an
authenticator through the signed-in private Site and report the resulting
read-only dashboard. Until that user-observed step, hosted TOTP acceptance is
unrun. Wrong-owner signed-in access, cellular access, persistent bridge polling,
command execution, and real-project access remain unrun; controls stay off.

### Version 4 and a fresh dummy-project bridge run

The owner reported that the authenticator app link on the enrollment page was
not clickable. The page now makes manual key entry the primary path, with
explicit account name and time-based setting. Site source commit
`77349ba15def44aec241a8dce79dc5dc5fc63624` passed build, six direct
Worker tests and validation, then deployed privately as version 4,
`appgdep_6adcce77c2f481919ee2d29b02ce9eb5` (`succeeded`), under the same
environment revision 3. The owner was asked to refresh the setup page and try
manual enrollment. The live signed-in result is pending.

Run `20261024T152829Z-8e037522` invoked
`tests/acceptance_remote_site_bridge.py` with fresh dummy Weather and Inventory
plans. It imported both through the normal CLI into a new SQLite database,
started the normal loopback API, and ran `remote/site_bridge.ps1` →
`remote/bridge.py --site` for 12 seconds using the stored Site and agent
credentials and a fresh local control token. The bridge wrote three `site.poll`
events with HTTP 200 and no `bridge.unavailable` events. Its journal contains
source and projection hashes; all three hosted response receipts and top-level
raw process output hashes were verified. Untouched inputs, raw outputs, database,
bridge journal/receipts, code hashes, configuration, and manifest are in
`evidence/remote-sites/20261024T152829Z-8e037522-bridge/`.

A read-only D1 query found one hosted snapshot row with the run's recent
`source_updated_at`. The Sites row-view tool truncated its JSON value, so this
query does not independently verify every projected field. The normal bridge
path demonstrated repeated status delivery for dummy projects, but the runner
had no scheduler daemon or control command. It is a **green hosted bridge
diagnostic**, not phone, MFA, command-control, or real Codex acceptance. Site
cost was not reported; controls are still disabled.

### Owner authenticator follow-up

The owner reported that manual authenticator setup worked. A read-only Sites
D1 check then found one owner verification counter, two `reader` sessions and
two `auth.login` audit events. These hosted records support successful separate
TOTP verification, but the browser response itself was reported by the owner
rather than captured by this runner. The Site access policy remains owner-only.
Temporary `TOTP_ENROLLMENT_ENABLED` was set to `false`, and the saved version 4
was privately redeployed as `appgdep_6adcd37756908191930bac68fb71b8f4`
(`succeeded`) with environment revision 4. The identity probe and remote
controls are also `false`.

The owner has been asked to verify the read-only dashboard on Android over
mobile data with Wi-Fi off. Until that result is observed, cellular access is
unrun. No command-control or real-project access has been enabled or tested.

The owner subsequently reported that the dashboard also worked on the phone,
then clarified that Wi-Fi was **on**. A read-only D1 inspection found a third
`reader` session and a third `auth.login` event. These records corroborate
another successful TOTP login, but they do not identify the device or network;
the phone result is user-observed. This is a phone-on-Wi-Fi check, **not** a
cellular-network test. The owner has been asked to lock the phone session and
sign in again with Wi-Fi off and mobile data on. Remote control is still
disabled.

The owner subsequently confirmed that the read-only dashboard opened on the
phone with Wi-Fi off and mobile data on. This is user-observed evidence of
cellular reachability. D1 still showed three `reader` sessions and three
`auth.login` events after that report, with no `auth.logout` event. Therefore
the available hosted records do **not** establish a fresh TOTP login over
cellular; the existing phone session may have been reused. Control actions and
session renewal over cellular remain unrun.

A separate hosted identity-boundary diagnostic sent a forged owner identity
header with no Site credential, then forged other and owner identity headers
with the Site bypass credential. The unauthenticated request was denied at the
edge with HTTP 403. Both service requests reached the Worker and returned JSON
403 `owner_required`, including the one with the real owner ID. This shows that
Sites dispatch did not pass through these caller-supplied identity headers on
the tested path. Untouched responses and SHA-256 receipts are in
`evidence/remote-sites/20261024T155411Z-identity-boundary/`; all three hashes
were verified. This is strong spoofing-denial evidence but does not replace a
different signed-in account test. Controls remain disabled.

## Official documentation consulted

[Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
fetched 23 October 2026, documents `exec --json`, stream identity/usage fields,
saved authentication reuse and per-invocation configuration controls. This is
documentation evidence, not installed-runtime verification.

[Codex App Server](https://learn.chatgpt.com/docs/app-server), fetched the same
date, supplied protocol guidance. Installed generated schemas were checked before
sending methods. Lifecycle conclusions above come from preserved real responses
and notifications, with limitations stated separately.
