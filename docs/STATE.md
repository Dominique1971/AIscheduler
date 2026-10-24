# State

Updated 2026-10-24. Initial delivery in progress; **not production ready**.

Remote setup: reviewed Oppo/Compass locally, read-only. Their current hosted
pattern is Cloudflare + Supabase owner authentication, not the older Compass
Tailscale-only baseline. Added a separate optional Worker/D1 dashboard and
outbound-only local bridge under `remote/`; scheduler source remains untouched.
Owner TOTP/AAL2, 15-minute opaque HttpOnly sessions, CSRF, default read-only role,
bounded typed controls, leases/fencing, idempotency, expiry/uncertainty, audit and
status projection are implemented. No cloud resource or public endpoint created.

Remote validation: 14 Worker diagnostics, six new bridge diagnostics, full Python
suite 58 pass, dry-run build passes, npm audit zero findings. Real local
Worker/D1/bridge/API/daemon pipeline passed with explicitly mocked Auth at
`evidence/remote-local/20261024T124234Z-21f59291`; 88 artifact hashes verify. Hosted
Supabase MFA, cellular access and deployment remain unrun. See REMOTE_SETUP.md.

User selected the same Supabase organization as Oppo/Compass for a dedicated
scheduler Auth project and confirmed the connector's $0/month quote. Creation
was refused: the organization owner has reached its two-active-free-project
limit. Raw refusal is preserved in `evidence/remote-setup/20261024-prepublication/`.
No paid upgrade or alteration/reuse of either existing application's resources
is authorized. Cloudflare account read-only inventory confirmed the expected
account, an existing `compass` Worker and no D1 databases; no new resource was
created there.

Completed: repository discovery, independent Git initialization, capability help
probes with raw hashes, ADR, schema/validator and builder, two 6-task dummy plans,
SQLite simulation dispatcher and immutable attempts/revisions, bounded synthetic
retries, pause/hold/allocation/emergency controls, loopback authenticated API/CLI,
initial compact dashboard. Direct native Codex/Dot workflows are unchanged.

Verified: fresh simulation acceptance `20261024T001345Z-dd456acd` passed; all 239
manifest/source files verified after exit; 52
diagnostic tests passed; final wheel build/import passed. Live browser pause,
resume, allocation and read-only denial passed. Overview fits 1280x720 and 390x844
browser viewports. Original failing runs and receipts remain preserved. Earlier
raw-green manifests with missing SQLite sidecars are rejected; see ACCEPTANCE.md.

Runtime min/target/reserved allocations and slot accounting are implemented.
Reservations hold idle capacity even when a project is paused. Online backup,
read-only integrity verification and restore into a new destination are implemented
and tested through normal CLI. Existing state is never overwritten by restore.

Current: full 24h simulation soak **running, not passed**, supervisor PID 43032,
run `20261024T001115Z-4cbca9a7`. Started October 23 at 8:11:15pm New York; deadline
October 24 at 8:11:15pm. Independent process and child daemon; hourly 12-task bursts
plus synthetic failures/restarts. First batch completed. Inspect actual final
report/hashes after deadline. Short 10.85s compressed trial passed separately.
No host-start, host reboot, physical Android or continuous inference claim.

Additional real probes: ChatGPT login confirmed; API-key variables removed from
child environments. Two concurrent harmless CLI executions completed with distinct
IDs/usage. CLI resume retained identity/context. Own-thread app-server read/resume,
explicit model/low effort, steer/interrupt and stored interrupted status were
observed. CLI resume usage may be cumulative; app-server exposes total/last. See
INTEGRATION_VALIDATION.md for exact scopes, original red probes and limitations.

Further disposable Git-worktree diagnostic: two concurrent installed CLI tasks
created exact expected files in separate branches/worktrees with ordinary user
configuration and explicit workspace-write, while the same diagnostic using
`--ignore-user-config` had both writes refused by read-only policy. Raw red and
green streams, emitted bytes and hashes are under `evidence/codex-worktree/`.
This establishes only direct CLI isolation in dummy repositories; scheduled
Codex dispatch and artifact acceptance remain unrun.

Gates: scheduled Codex execution/worktree isolation and artifact acceptance,
tool/approval parity, optional Dot handshake, remote tunnel provider/MFA, Android cellular
testing, 24h soak and host reboot. No real projects connected; no external API
spend, remote publication, installs of persistent service or global settings edits.

Decisions: simulation-only execution until capabilities proven; every plan
revision requires explicit approval; incompatible active/completed contracts are
rejected, split by append; loopback API requires bearer tokens. A background
daemon command exists, but this alone does not prove auto-start or continuous
weeks-long operation. Source-faithful receipts cannot establish task semantics.

Next: inspect soak outcome when available, then advance E1/E2 and remote gates.
The subscription-route question was resolved from actual CLI login status under
the original authorization for real dummy tests. Remote access provider remains
resolved user choice: follow the hosted Cloudflare/Supabase pattern; dedicated
resource provisioning and publication still require their gates. Full remaining scope is
tracked in IMPLEMENTATION_PLAN.md and ARCHITECTURE.md; nothing is silently waived.
