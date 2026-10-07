BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS exchange_imports (package_hash TEXT PRIMARY KEY, source_authority TEXT NOT NULL, cursor INTEGER NOT NULL, total INTEGER NOT NULL, state TEXT NOT NULL, manifest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS exchange_records (package_hash TEXT NOT NULL REFERENCES exchange_imports(package_hash), object_id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(package_hash,object_id,revision));
CREATE TABLE IF NOT EXISTS executor_leases (scope TEXT PRIMARY KEY, holder TEXT NOT NULL, fence INTEGER NOT NULL, expires REAL NOT NULL, task_id TEXT NOT NULL REFERENCES objects(id), task_revision INTEGER NOT NULL);
INSERT OR IGNORE INTO budget_accounts VALUES('batch3','CNY',30000000,0,1);
PRAGMA user_version=3;
COMMIT;
