-- Additive E7 extension of schema3. Same database/authority, no object head changes.
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS archive_plans(id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES objects(id), contract TEXT NOT NULL, plan TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS archive_progress(plan_id TEXT NOT NULL REFERENCES archive_plans(id), member TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL, receipt TEXT NOT NULL, PRIMARY KEY(plan_id,member));
CREATE TABLE IF NOT EXISTS archive_conversations(plan_id TEXT NOT NULL REFERENCES archive_plans(id), member TEXT NOT NULL, ordinal INTEGER NOT NULL, native_id TEXT, title TEXT, raw_hash TEXT NOT NULL, stats TEXT NOT NULL, PRIMARY KEY(plan_id,member,ordinal));
CREATE TABLE IF NOT EXISTS archive_messages(plan_id TEXT NOT NULL REFERENCES archive_plans(id), member TEXT NOT NULL, ordinal INTEGER NOT NULL, node TEXT NOT NULL, raw_hash TEXT NOT NULL, record TEXT NOT NULL, detail TEXT NOT NULL, PRIMARY KEY(plan_id,member,ordinal,node));
CREATE TABLE IF NOT EXISTS archive_assets(plan_id TEXT NOT NULL REFERENCES archive_plans(id), member TEXT NOT NULL, detail TEXT NOT NULL, PRIMARY KEY(plan_id,member));
CREATE TABLE IF NOT EXISTS archive_refs(plan_id TEXT NOT NULL REFERENCES archive_plans(id), member TEXT NOT NULL, ordinal INTEGER NOT NULL, node TEXT NOT NULL, ref_index INTEGER NOT NULL, pointer TEXT NOT NULL, resolution TEXT NOT NULL, PRIMARY KEY(plan_id,member,ordinal,node,ref_index));
CREATE TABLE IF NOT EXISTS archive_reads(plan_id TEXT NOT NULL REFERENCES archive_plans(id), member TEXT NOT NULL, sha256 TEXT NOT NULL, detail TEXT NOT NULL, PRIMARY KEY(plan_id,member));
CREATE INDEX IF NOT EXISTS archive_ref_pointer ON archive_refs(plan_id,pointer);
INSERT OR IGNORE INTO budget_accounts VALUES('batch4','CNY',45000000,0,1);
INSERT OR REPLACE INTO metadata VALUES('archive_contract','batch4-1');
COMMIT;
