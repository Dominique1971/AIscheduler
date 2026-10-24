# State

Updated 2026-10-24. Initial delivery in progress; **not production ready**.

Remote setup: reviewed Oppo/Compass locally, read-only. Their current hosted
pattern is Cloudflare + Supabase owner authentication, not the older Compass
Tailscale-only baseline. The separate Supabase scheduler Auth project was
refused at the free-project limit; no paid plan or alteration of either app was
authorized. The user then chose a private OpenAI Site instead. Its Cloudflare
Worker/D1 dashboard lives under `sites/scheduler-dashboard/`, while the
Python/SQLite scheduler and outbound-only bridge remain local and independent.
The earlier `remote/` Supabase candidate is retained as diagnostic history.

The owner-private Site is deployed with exact owner Site ID, separate TOTP,
15-minute opaque HttpOnly sessions, CSRF, read-only role, typed controls,
idempotent command queue, audit and bounded status projection. Temporary
identity and TOTP enrollment routes are off; remote controls remain off.
The owner completed TOTP login on PC and phone over Wi-Fi, then reported that
the read-only dashboard opened on the phone over mobile data. D1 corroborates
reader sessions, but does not prove a fresh cellular login. A fresh dummy CLI →
local API → outbound Python bridge → hosted Site run had three successful polls;
hosted forged identity headers were denied. One normal phone Pause of disposable
Demo Weather succeeded through the Site, D1 queue, outbound bridge and local API;
Demo Inventory remained unpaused. Controls were then disabled again. Raw evidence
and limitations are in `docs/INTEGRATION_VALIDATION.md`. Alternate signed-in
user denial, fresh cellular control, endurance and real Codex scheduling remain
unrun.

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
No host-start, host reboot, eight-hour phone endurance or continuous inference claim.

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
tool/approval parity, optional Dot handshake, fresh cellular control and
session renewal, alternate signed-in user denial, 24h soak and host reboot. No
real projects connected; no persistent service or global settings edits. The
private read-only Site is published; Sites reported no dollar cost.

Decisions: simulation-only execution until capabilities proven; every plan
revision requires explicit approval; incompatible active/completed contracts are
rejected, split by append; loopback API requires bearer tokens. A background
daemon command exists, but this alone does not prove auto-start or continuous
weeks-long operation. Source-faithful receipts cannot establish task semantics.

Next: inspect soak outcome when available, then advance E1/E2 and remote gates.
The subscription-route question was resolved from actual CLI login status under
the original authorization for real dummy tests. Remote access uses a separate
private OpenAI Site without changing Oppo or Compass. Full remaining scope is
tracked in IMPLEMENTATION_PLAN.md and ARCHITECTURE.md; nothing is silently waived.
