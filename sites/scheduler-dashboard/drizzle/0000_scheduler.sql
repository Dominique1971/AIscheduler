CREATE TABLE IF NOT EXISTS sessions (
  hash TEXT PRIMARY KEY, owner TEXT NOT NULL, csrf TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('reader','controller')), expires INTEGER NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS mfa_counters (
  owner TEXT PRIMARY KEY, last_counter INTEGER NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL,
  source_updated_at TEXT NOT NULL, received INTEGER NOT NULL, input_sha256 TEXT NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS commands (
  id TEXT PRIMARY KEY, hash TEXT NOT NULL, payload TEXT NOT NULL, owner TEXT NOT NULL,
  created INTEGER NOT NULL, expires INTEGER NOT NULL, state TEXT NOT NULL,
  fence INTEGER NOT NULL DEFAULT 0, lease_until INTEGER NOT NULL DEFAULT 0,
  result TEXT, finished INTEGER
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS claimable ON commands(state,expires,lease_until,created);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS audit (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL,
  actor TEXT NOT NULL, kind TEXT NOT NULL, command_id TEXT, detail TEXT NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS rate_limits (
  key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL
);
