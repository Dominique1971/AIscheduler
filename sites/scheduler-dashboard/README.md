# Private Scheduler Site candidate

The Site hosts only the phone dashboard, bounded status projection, command queue, and audit records. The Python scheduler, SQLite authority, Codex CLI, and loopback API remain on the owner's computer. `remote/bridge.py --site` makes outbound HTTPS requests. This source is registered as a **private, unpublished** Site; no hosted version or database migration has been deployed.

The private Sites audience currently includes only the owner. A visitor request must carry either a Sites-authenticated user ID matching `OWNER_SITE_USER_ID` or, where the hosted runtime supplies no ID, the exact Sites-authenticated email matching `OWNER_SITE_EMAIL`. The latter is supported by observed hosted request headers and official Sites documentation; keep the private audience restricted to the owner. The visitor must then pass a separate TOTP challenge before an application session exists. The access-policy account ID is not assumed to equal the Site-local identity ID. A read-only `/setup/identity` route can reveal the actual supplied identity only while `IDENTITY_PROBE_ENABLED=true` and remote control is disabled; turn it off after setup. This diagnostic is not MFA or authorization acceptance. ChatGPT sign-in alone is not treated as MFA. Site service access for the bridge is separate from a human session and must be accompanied by the distinct `AGENT_TOKEN` credential. Never put Sites or agent tokens, TOTP seeds, Codex credentials, or local API credentials in source, prompts, or command lines.

The Site environment needs `APP_ORIGIN`, exactly one of `OWNER_SITE_USER_ID` or `OWNER_SITE_EMAIL`, `OWNER_TOTP_SECRET` (base32, enrolled privately in an authenticator), `AGENT_TOKEN`, and `REMOTE_CONTROL_ENABLED=false` initially. The local bridge additionally needs `SCHEDULER_SITE_ACCESS_TOKEN`, `SCHEDULER_REMOTE_AGENT_TOKEN`, and `SCHEDULER_CONTROL_TOKEN` in its environment. The `OAI-Sites-Authorization` header is sent only to the configured Site origin. The first D1 migration is `drizzle/0000_scheduler.sql`; later migrations must be append-only. The source bundler in `scripts/build.mjs` embeds the HTML, browser script, CSS, contract and Worker into the supported `dist/server/index.js` artifact.

Local diagnostics:

```powershell
cd C:\dev-codex\scheduler\sites\scheduler-dashboard
npm ci --ignore-scripts
npm run build
npm run validate
npm test
```

The tests inject identity headers and a SQLite adapter directly into the Worker. They do **not** verify Sites dispatch, real ChatGPT sign-in, hosted D1 migrations, actual MFA enrollment, service access, cellular reachability, or safe hosted CPU/quota behavior. Keep control disabled and do not deploy until those gaps are tested with dummy projects. Publication is a separately controlled step under `docs/SPEC.md` section 11.
