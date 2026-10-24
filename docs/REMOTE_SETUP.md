# Remote setup decision — 24 October 2026

User direction: review Oppo/Compass and implement a similar setup. Review was
read-only; no project, auth, database, network or hosting settings changed there.

| Reference | Observed current pattern | Scheduler application |
|---|---|---|
| Oppo `web/README.md`, `web/public-config.js`, `deploy/README.md` | Cloudflare Pages static app, owner UUID checked through Supabase Auth/RPC, narrow outbound worker jobs; older local prototype remains separate | Cloud-hosted view/control plane, local scheduler remains authoritative, narrow outbound bridge |
| Compass `docs/15-compass-hosted-mvp-setup.md`, ADR 0005, `web/wrangler.jsonc` | Cloudflare Worker + Supabase single-owner Auth; authoritative user check; protected HttpOnly sessions | Worker with independent owner verification and short opaque HttpOnly sessions |
| Compass ADR 0001 / ADR 0002 | Tailscale private VPS was the older alternative; later hosted decision addressed phone access | Do not mistake the older Tailscale baseline for the current hosted setup |
| Scheduler SPEC 13 | MFA, HTTPS, role separation, audit and no inbound router ports | Require owner TOTP/AAL2, default read-only, allowlisted expiring commands and outbound polling |

The current chosen implementation is the owner-private OpenAI Site in
`sites/scheduler-dashboard/`, with an outbound-only Python bridge in
`remote/bridge.py`. It has a Cloudflare Worker and D1 under Sites, with Sites
owner sign-in plus separate TOTP; it does not require Supabase. SQLite/daemon/
Codex stay local and independent of Site outages. The earlier separate
Cloudflare Worker + Supabase Auth candidate under `remote/` is retained for
diagnostic history. No reference app credentials/configuration were copied.

Scope: initial remote overview and controls. The existing local dashboard retains
its timeline; remote full timeline/history parity remains future work. Mandatory
MFA is stricter than the password-only portions observed in the reference apps;
their existing live MFA posture was not tested or changed.

The earlier local candidate diagnostic with mocked Auth passed under
`evidence/remote-local/20261024T124234Z-21f59291`. The private Site now has
observed owner TOTP, dummy status polling, a successful dummy phone Pause, and
user-reported read-only cellular reachability. Fresh cellular sign-in/control
remains unrun.
See `docs/INTEGRATION_VALIDATION.md` and the Site's own README for precise
evidence and limitations.

The original 24h soak remains on untouched scheduler source; the candidate lives
outside `scheduler/` and uses only separate dummy databases. Its recorded source
hashes remain authoritative for that run, not for the new remote module.

The Site is privately deployed with one allowed owner and no external visitors;
the identity and enrollment probes are off, and remote controls remain off.
No Supabase project or paid plan was created. Sites reported no dollar cost.
The bounded dummy control trial is complete; only disposable projects may be
attached for further testing.

The user selected the existing Oppo/Compass Supabase organization for the new,
separate Auth project. The connector's project-creation quote on October 24 is
`{"type":"project","recurrence":"monthly","amount":0}` ($0/month).
The user confirmed that quoted cost. Creation was attempted for a separate
`AI Scheduler Auth` project in `us-east-1`, but Supabase refused it because the
organization's owner has reached the two-active-free-project limit. The exact
request and response are preserved in
`evidence/remote-setup/20261024-prepublication/supabase-create-refused.json`.
No project was created. Do not upgrade billing, pause another project or reuse
an existing app's Auth configuration without a specific new decision.

The user considered a different Supabase account, then chose OpenAI Sites
instead. The free-project refusal and alternate-account exploration remain
historical evidence, not an active provisioning step. Do not resume Supabase
provisioning without a new user decision.

Supabase policy source, checked October 24: https://supabase.com/docs/guides/platform/billing-on-supabase
