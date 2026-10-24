# Remote setup decision — 24 October 2026

User direction: review Oppo/Compass and implement a similar setup. Review was
read-only; no project, auth, database, network or hosting settings changed there.

| Reference | Observed current pattern | Scheduler application |
|---|---|---|
| Oppo `web/README.md`, `web/public-config.js`, `deploy/README.md` | Cloudflare Pages static app, owner UUID checked through Supabase Auth/RPC, narrow outbound worker jobs; older local prototype remains separate | Cloud-hosted view/control plane, local scheduler remains authoritative, narrow outbound bridge |
| Compass `docs/15-compass-hosted-mvp-setup.md`, ADR 0005, `web/wrangler.jsonc` | Cloudflare Worker + Supabase single-owner Auth; authoritative user check; protected HttpOnly sessions | Worker with independent owner verification and short opaque HttpOnly sessions |
| Compass ADR 0001 / ADR 0002 | Tailscale private VPS was the older alternative; later hosted decision addressed phone access | Do not mistake the older Tailscale baseline for the current hosted setup |
| Scheduler SPEC 13 | MFA, HTTPS, role separation, audit and no inbound router ports | Require owner TOTP/AAL2, default read-only, allowlisted expiring commands and outbound polling |

The chosen candidate is `remote/`: a small Cloudflare Worker plus D1 status/queue
store and dedicated Supabase Auth. SQLite/daemon/Codex stay local and independent
of cloud outages. This is a separate optional interface, not migration of scheduler
state to a hosted database. No app's credentials/configuration are copied.

Scope: initial remote overview and controls. The existing local dashboard retains
its timeline; remote full timeline/history parity remains future work. Mandatory
MFA is stricter than the password-only portions observed in the reference apps;
their existing live MFA posture was not tested or changed.

Local diagnostics: real local Worker/D1/bridge/API/daemon pipeline with mocked
Auth passed under `evidence/remote-local/20261024T124234Z-21f59291`. Original inputs,
HTTP results, process logs, receipts and hashes preserved. Real provider MFA and
cellular acceptance remain **UNRUN**. See [candidate runbook](../remote/README.md).

The original 24h soak remains on untouched scheduler source; the candidate lives
outside `scheduler/` and uses only separate dummy databases. Its recorded source
hashes remain authoritative for that run, not for the new remote module.

Publication requires a dedicated approved destination and free-quota check,
private owner/TOTP setup, real auth isolation verification, then dummy control
and Android cellular checks. Production deployment is separately controlled by
SPEC section 11. No cloud resource, billing change or public endpoint was created.

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

The user chose a different Supabase account with free capacity. The current
connector still exposes only `Dominique1971's Org` under the original account;
there is no alternate organization available through this connection. Supabase's
documented free-project limit applies across organizations where a member is an
Owner or Administrator, so another organization owned by the same account would
not resolve this refusal. Continue only after the connector is authenticated to
the separate account or a separate existing project is explicitly identified;
then inspect that account's organization, quote its cost and provision a dedicated
Auth project. Do not infer the new account or reuse a reference app's Auth project.

Supabase policy source, checked October 24: https://supabase.com/docs/guides/platform/billing-on-supabase
