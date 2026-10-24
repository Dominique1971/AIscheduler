# Autonomous Multi-Project Scheduler

An independent, dummy-first Python scheduler. This is the first local vertical
slice, **not a production-ready autonomous coding service**. Only simulation
execution is enabled. Native Codex and Dot remain independent.

Requires Python 3.12+. From this directory:

```powershell
python -m pip install -e ".[test]"
python -m scheduler validate examples/demo-weather.yaml
python -m scheduler import examples/demo-weather.yaml
python -m scheduler import examples/demo-inventory.yaml
python -m scheduler daemon --workers 6
```

The daemon owns dispatch; keep it in a terminal or a supervised user service. It
does not need an API/dashboard/chat session. A second daemon is fenced by a
renewing lease; restart takeover takes approximately three seconds. This release
does not install automatic host-start or wake a sleeping computer.

In another PowerShell terminal, generate separate local tokens:

```powershell
$env:SCHEDULER_CONTROL_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:SCHEDULER_READ_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:SCHEDULER_TOKEN_EXPIRES_AT = [DateTimeOffset]::UtcNow.AddHours(8).ToUnixTimeSeconds().ToString()
python -m scheduler serve
```

Open [the local dashboard](http://127.0.0.1:8765), click Connect, and paste the
appropriate token from your terminal environment. Read tokens inspect; control
tokens change state. Do not publish this local bearer-token service directly.
HTTPS tunnel + MFA and Android cellular testing are still gated. No inbound router
ports are required or configured. No credentials belong in plans or Git.

```powershell
python -m scheduler preview path/to/revision.yaml
python -m scheduler import path/to/revision.yaml --approve
python -m scheduler control pause --project demo-weather
python -m scheduler control allocate --project demo-weather --value 2
python -m scheduler control workers --value 4
python -m scheduler control emergency-stop --confirmed
python -m scheduler control start
python -m scheduler trace demo-weather source
python -m scheduler verify
python -m scheduler backup runtime/backups/snapshot.db
python -m scheduler --db runtime/restored.db restore runtime/backups/snapshot.db
```

Pause stops new dispatch and lets active simulation work finish. Emergency stop
cancels active simulation attempts and stops new dispatch globally. Failed tasks
enter review after their bounded retry budget; other eligible work continues.
Changes to active/completed contracts are rejected. Split by appending new IDs
dependent on the original task; retain original results and history.

Tests and evidence:

```powershell
python -m pytest -q
python tests/acceptance_simulation.py
python tests/verify_acceptance_evidence.py evidence/acceptance/RUN_ID --current-source
python tests/soak_simulation.py --hours 24
```

Unit/API fixtures are diagnostic tests. The fresh acceptance runner invokes the
normal CLI, real API and actual daemon processes; it writes raw request/response
receipts, logs, authored input plans, database and SHA-256 manifest in a new
evidence directory. The soak runner invokes the normal CLI and independent daemon,
with hourly synthetic batches and forced daemon restarts. A short soak does not
satisfy 24h acceptance. No test alters emitted output or touches a real project.

See [state](docs/STATE.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md),
[architecture](docs/ARCHITECTURE.md), [capabilities](docs/INTEGRATION_VALIDATION.md),
[API](docs/API.md), and [acceptance gates](docs/ACCEPTANCE.md). Plans use the packaged
JSON Schema 2020-12 contract; the reusable skill lives under `skills/plan-builder`.

The optional [remote dashboard candidate](remote/README.md) follows the reviewed
Oppo/Compass Cloudflare + Supabase owner-login pattern. It adds mandatory TOTP MFA
and an outbound-only bridge to the existing local API. It is locally tested and
not deployed; no existing app resources or real projects are connected. See the
[setup decision](docs/REMOTE_SETUP.md) for evidence and publication gates.
