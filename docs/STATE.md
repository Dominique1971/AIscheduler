# State

Updated 2026-10-23. Initial delivery in progress; **not production ready**.

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

Gates: real Codex inference authorization/authentication path, actual execution
capabilities, optional Dot handshake, remote tunnel provider/MFA, Android cellular
testing, 24h soak and host reboot. No real projects connected; no external API
spend, remote publication, installs of persistent service or global settings edits.

Decisions: simulation-only execution until capabilities proven; every plan
revision requires explicit approval; incompatible active/completed contracts are
rejected, split by append; loopback API requires bearer tokens. A background
daemon command exists, but this alone does not prove auto-start or continuous
weeks-long operation. Source-faithful receipts cannot establish task semantics.

Next: inspect soak outcome when available, then advance E1/E2 and remote gates.
Two user decisions are pending: subscription-only Codex execution authorization
and remote access provider. Full remaining scope is
tracked in IMPLEMENTATION_PLAN.md and ARCHITECTURE.md; nothing is silently waived.
