# Remote dashboard candidate

This implements the hosting pattern reviewed in Oppo and Compass: Cloudflare
hosting, Supabase-verified single-owner login, authenticated operations, and an
outbound-only local connection. It is **prepared and tested locally, not deployed**.
No existing Oppo/Compass resources, users, secrets or settings are reused/changed.

The main scheduler continues to own SQLite, dispatch and execution. A Worker owns
only a bounded status projection, short sessions and expiring typed control
requests. The Python bridge initiates every network connection. No inbound
router port, local API publication, arbitrary URL proxy or remote shell exists.

## Authentication

The Worker sends bounded email/password input to the exact configured Supabase
project, verifies the returned access token via `/auth/v1/user`, checks immutable
owner ID, confirmed email and non-anonymous status, then challenges/verifies an
already enrolled TOTP factor. It independently verifies the resulting token and
requires `aal2` before issuing an opaque HttpOnly/Secure/SameSite cookie.

Only a SHA-256 session-token hash, CSRF token, owner/role and expiry are stored in
D1. Provider credentials, access tokens, refresh tokens and passwords never reach
browser JavaScript, persistence or logs. Sessions expire within 15 minutes;
there is no remembered-device/refresh implementation in this initial candidate.
Signout deletes the application session immediately. The provider's access JWT
may remain valid until provider expiry; short application sessions are not a claim
of immediate global provider revocation. Enrollment/recovery are private setup
steps, not unauthenticated application routes.

Anonymous API access fails. Cookie mutations require exact Origin and CSRF token.
Read-only mode is the default; it must be explicitly enabled for controller
sessions. Agent credentials are separate from website and local API credentials.
Login/API rate budgets and audit events are persisted. HTML/assets carry CSP,
no-store, no-referrer, frame denial and content-type protection.

## Outbound control protocol

The bridge polls every five seconds and exports only allowlisted state fields,
never task descriptions/prompts, repositories, stdout, error text or credentials.
Raw source snapshots, projections and control response bytes remain in local
content-addressed receipts with a journal recording transformation version/hashes.
The cloud keeps the latest projection with both source and receive timestamps.
Agent heartbeat freshness gates enqueue; browser state always identifies its age.

Commands permit only project pause/resume/cap, task hold/unhold/retry, global
start and explicitly confirmed emergency stop. Commands expire after 60 seconds,
leases last 30 seconds and acknowledgements carry a fencing number. The bridge
validates every payload again and calls only normal loopback API routes with a
durable `remote:COMMAND_ID` idempotency key. Reclaim after bridge failure reuses
that same identity. Expired leased work becomes **uncertain**, not silently retried
or presented as unapplied. Acknowledged HTTP success remains separate from task
completion. This is not exactly-once external execution.

## Local checks

```powershell
cd C:\dev-codex\scheduler\remote
npm ci --ignore-scripts
npm test
npm run types
npm run build
cd ..
python -m pytest tests/test_remote_bridge.py -q
python remote/tests/local_pipeline.py
```

`build` is a Wrangler dry-run, not deployment. The local pipeline creates isolated
dummy projects, real loopback API/daemon/bridge and local Worker/D1, with an
**explicitly mocked Auth provider**. Its `DEV_MODE=local-only` and HTTP fixture
provider are allowed only on loopback and must never become production settings.
These tests do not establish real Supabase MFA, hosted Worker CPU, phone cellular
reachability or production authorization. Failed runs must remain separate.

Wrangler is pinned with a lockfile. Its transitive Undici dependency is narrowly
overridden to 7.30.1 to address advisories in the default dependency tree. Audit
reports before/after are retained; no force downgrade or runtime auth weakening.

## Concrete publication prerequisites

Use a **new, dedicated scheduler** Worker, D1 database and Supabase Auth project.
Do not substitute an existing app's database, owner UUID, keys or secrets.
`wrangler.jsonc` intentionally contains invalid destination placeholders,
`workers_dev: false`, no preview URLs, and control disabled. Before publication:

1. Approve the dedicated destination/resources and verify available free quota;
   no paid subscription, billing change or shared-resource alteration is authorized.
2. Privately provision a confirmed owner, disable public/anonymous signup, enroll
   TOTP, and retain recovery procedures. Do not enter passwords/TOTP seeds in chat.
3. Set the exact HTTPS `APP_ORIGIN`, official `SUPABASE_URL`, immutable `OWNER_ID`,
   publishable key, and a new random agent token. Store secret values through the
   platform secret mechanism. There are no service-role keys or database passwords.
4. Bind the dedicated D1 database and apply `schema.sql`; configure provider limits,
   backups and authentication recovery before calling the setup complete.
5. Publish initially read-only. Verify real owner MFA, anonymous/wrong-owner denial,
   session expiry, CSRF, no-cache and endpoint isolation. Measure actual hosted CPU
   and quotas. Only then enable audited controls against dummy projects.
6. Verify Android over cellular and recovery with the local bridge offline/restarted.
   Test queued/leased uncertain actions; no stale control may execute after expiry.

Run the bridge in a separate supervised terminal/service:

```powershell
# Set distinct SCHEDULER_REMOTE_AGENT_TOKEN and SCHEDULER_CONTROL_TOKEN privately.
python remote/bridge.py --origin https://APPROVED-SCHEDULER-HOST
```

The local API must already be running on `http://127.0.0.1:8765`. The bridge does
not start the scheduler or access Codex credentials. No API-key inference or paid
LLM route is added; Codex tests remain existing-ChatGPT-subscription-only.

No remote resources have been created. Source/config/tests are reviewable before
the separately controlled publication step in SPEC section 11.
