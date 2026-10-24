# Autonomous Multi-Project Scheduler

An independent, dummy-first Python scheduler. This is the first local vertical
slice, **not a production-ready autonomous coding service**. Only simulation
execution is enabled. Native Codex and Dot remain independent.

Requires Python 3.12+. From this directory:

```powershell
python -m pip install -e ".[test]"
python -m scheduler validate examples/demo-weather.yaml
python -m scheduler intake examples/intake-demo-weather.yaml --output runtime/proposed-weather.json
python -m scheduler validate runtime/proposed-weather.json
python -m scheduler preview runtime/proposed-weather.json
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
The local **Import plan** dialog uses a control token to preview an external
Markdown intake file without importing it. Download the
[format specification](scheduler/static/intake-format.md) and
[template](scheduler/static/intake-template.md) to prepare the file elsewhere.
The dialog also lists two packaged six-task examples and shows the goal,
estimate critical path, dependencies and task details before and after import.
For the isolated example showcase already set up on this machine:

```powershell
pwsh -NoProfile -File scripts/start_example_showcase.ps1
pwsh -NoProfile -File scripts/copy_example_showcase_token.ps1
```

Open [the example dashboard](http://127.0.0.1:8877/), click **Connect**, and
paste the copied token. **Import plan** accepts a versioned `.md` file or a
packaged example for review and guarded import; each project has **View plan**. The
script keeps this showcase in `runtime/example-showcase/`, separate from the
default scheduler database. It starts the local daemon and, where provisioned,
the owner-private outbound Site bridge. These hidden processes do not restart
after a host reboot; run the start script again. The separate private Site has
owner sign-in and an outbound bridge; its temporary read-only TOTP bypass is
active, so remote controls remain disabled. Fresh cellular control testing is
still open. No inbound router ports are
required or configured. No credentials belong in plans or Git.

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

The project intake command turns an authored description, task explanations,
minute estimates and dependency IDs into a **draft** canonical plan. It reports
all operational defaults and a source-hash provenance sidecar. Total effort and
critical path are estimates, not delivery forecasts. Review the draft before a
separate import; intake itself does not create a project or run a task. See
[project intake](docs/PROJECT_INTAKE.md).

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

The owner-private [OpenAI Site dashboard](sites/scheduler-dashboard/README.md)
uses TOTP and an outbound-only bridge to the local API. A dummy phone Pause
trial passed; remote controls are disabled again, and real projects remain
unconnected. The older Supabase candidate under `remote/` is retained as
diagnostic history. See the [setup decision](docs/REMOTE_SETUP.md) and
[acceptance gates](docs/ACCEPTANCE.md).
