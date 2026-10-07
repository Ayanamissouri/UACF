-- Explicit compatible batch2 migration, applied only after verified recovery.
CREATE TABLE IF NOT EXISTS ingest_runs(key TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES objects(id), parser TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, receipt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS budget_accounts(id TEXT PRIMARY KEY, currency TEXT NOT NULL, limit_micro INTEGER NOT NULL CHECK(limit_micro>=0), spent_micro INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS budget_reservations(id TEXT PRIMARY KEY, account TEXT NOT NULL REFERENCES budget_accounts(id), amount_micro INTEGER NOT NULL CHECK(amount_micro>0), state TEXT NOT NULL CHECK(state IN('reserved','settled','unknown','released')), actual_micro INTEGER, receipt TEXT NOT NULL);
PRAGMA user_version=2;
