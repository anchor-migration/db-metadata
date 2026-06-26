-- SQLite metadata schema v1
-- SSoT snapshot store for database structure metadata

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta_schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO meta_schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS export_run (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_dialect      TEXT NOT NULL,
    source_url_masked   TEXT NOT NULL,
    exported_at         TEXT NOT NULL DEFAULT (datetime('now')),
    schema_filter       TEXT,
    tool_version        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS db_schema (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    name            TEXT NOT NULL,
    UNIQUE (export_run_id, name)
);

CREATE TABLE IF NOT EXISTS db_table (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_id       INTEGER NOT NULL REFERENCES db_schema(id),
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    name            TEXT NOT NULL,
    table_type      TEXT NOT NULL CHECK (table_type IN ('TABLE', 'VIEW')),
    comment         TEXT,
    stable_id       TEXT NOT NULL,
    UNIQUE (export_run_id, stable_id)
);

CREATE INDEX IF NOT EXISTS idx_db_table_schema_id ON db_table (schema_id);
CREATE INDEX IF NOT EXISTS idx_db_table_export_run_id ON db_table (export_run_id);

CREATE TABLE IF NOT EXISTS db_column (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id        INTEGER NOT NULL REFERENCES db_table(id),
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    name            TEXT NOT NULL,
    ordinal         INTEGER NOT NULL,
    data_type       TEXT NOT NULL,
    full_type       TEXT NOT NULL,
    nullable        INTEGER NOT NULL CHECK (nullable IN (0, 1)),
    default_value   TEXT,
    comment         TEXT,
    is_pk           INTEGER NOT NULL DEFAULT 0 CHECK (is_pk IN (0, 1)),
    stable_id       TEXT NOT NULL,
    UNIQUE (export_run_id, stable_id)
);

CREATE INDEX IF NOT EXISTS idx_db_column_table_id ON db_column (table_id);

CREATE TABLE IF NOT EXISTS db_primary_key (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id        INTEGER NOT NULL REFERENCES db_table(id),
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    column_name     TEXT NOT NULL,
    ordinal         INTEGER NOT NULL,
    UNIQUE (table_id, column_name)
);

CREATE TABLE IF NOT EXISTS db_foreign_key (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    export_run_id       INTEGER NOT NULL REFERENCES export_run(id),
    name                TEXT,
    source_table_id     INTEGER NOT NULL REFERENCES db_table(id),
    source_column       TEXT NOT NULL,
    target_table_id     INTEGER NOT NULL REFERENCES db_table(id),
    target_column       TEXT NOT NULL,
    on_delete           TEXT,
    on_update           TEXT
);

CREATE INDEX IF NOT EXISTS idx_db_foreign_key_source ON db_foreign_key (source_table_id);
CREATE INDEX IF NOT EXISTS idx_db_foreign_key_target ON db_foreign_key (target_table_id);
CREATE INDEX IF NOT EXISTS idx_db_foreign_key_export_run ON db_foreign_key (export_run_id);

CREATE TABLE IF NOT EXISTS db_index (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id        INTEGER NOT NULL REFERENCES db_table(id),
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    name            TEXT NOT NULL,
    is_unique       INTEGER NOT NULL CHECK (is_unique IN (0, 1)),
    UNIQUE (table_id, name)
);

CREATE TABLE IF NOT EXISTS db_index_column (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_id        INTEGER NOT NULL REFERENCES db_index(id),
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    column_name     TEXT NOT NULL,
    ordinal         INTEGER NOT NULL,
    sort_order      TEXT,
    UNIQUE (index_id, ordinal)
);

CREATE TABLE IF NOT EXISTS db_unique_constraint (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id        INTEGER NOT NULL REFERENCES db_table(id),
    export_run_id   INTEGER NOT NULL REFERENCES export_run(id),
    name            TEXT,
    column_name     TEXT NOT NULL,
    ordinal         INTEGER NOT NULL,
    UNIQUE (table_id, name, column_name)
);
