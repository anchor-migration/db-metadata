# Verification SQL Scripts

Dialect-specific SQL scripts used by `db-migration verify` to collect ground-truth
metadata entities from the live source database.

Scripts live in [`src/db_migration/verify/queries/`](../src/db_migration/verify/queries/).

## Entity key format

Both the source collector and the export collector produce rows with:

| Column | Description |
|--------|-------------|
| `entity_type` | `table`, `view`, `column`, `primary_key`, `foreign_key`, `index`, `unique_constraint` |
| `entity_key` | Stable string matching the export snapshot format |

Examples:

```
table           main.customers
column          main.customers.id
primary_key     main.customers|id|1
foreign_key     main.orders|customer_id|main.customers|id
index           main.orders|idx_orders_customer
unique_constraint main.customers|uq_name|name|1
```

## Dialect coverage

| Dialect | Script | Notes |
|---------|--------|-------|
| PostgreSQL | `postgresql.sql` | `information_schema` + `pg_indexes` |
| MySQL | `mysql.sql` | `information_schema` |
| Oracle | `oracle.sql` | `ALL_*` catalog views |
| SQL Server | `sqlserver.sql` | `sys` catalog views |
| SQLite | programmatic | No portable catalog SQL; uses inspector collector |

## Usage

```bash
# 1. Export metadata
db-migration export --url "postgresql+psycopg://..." --out metadata.db

# 2. Verify export against source
db-migration verify metadata.db --url "postgresql+psycopg://..."
```

Exit code `0` = match, `1` = mismatch.

## Extending

When adding a new dialect:

1. Add `your_dialect.sql` under `src/db_migration/verify/queries/`
2. Register it in `from_source.py` `_DIALECT_SQL_MAP`
3. Ensure `entity_key` values match keys produced by `from_export.py`
