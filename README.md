# db-metadata

Part of **[Anchor Migration](https://github.com/anchor-migration/migration-hub)** — schema metadata export for legacy modernization.

Export database metadata (tables, columns, keys, indexes) from live databases into a local SQLite file. The source database is treated as the **single source of truth (SSoT)**. Downstream tools—such as Java migration (EJB → Spring) and data lineage analysis—read from SQLite instead of connecting to production.

**Supported source databases:** Oracle, MySQL, PostgreSQL, SQL Server

## Features

- Read-only introspection (no DDL/DML on the source database)
- Portable SQLite snapshot with versioned schema
- Stable identifiers: `schema.table.column`
- Foreign keys stored as lineage edges
- Multiple export runs preserved for schema drift comparison
- Dialect adapters for comments and schema naming differences

## Requirements

- Python 3.11+
- Database driver for your source DB (see optional extras below)

## Installation

```bash
git clone https://github.com/anchor-migration/db-metadata.git
cd db-metadata
pip install -e ".[all]"
```

Install only the drivers you need:

```bash
pip install -e ".[postgresql]"   # PostgreSQL
pip install -e ".[oracle]"       # Oracle
pip install -e ".[mysql]"        # MySQL
pip install -e ".[sqlserver]"    # SQL Server
```

## Quick start

### Export metadata

```bash
db-migration export \
  --url "postgresql+psycopg://user:pass@localhost:5432/mydb" \
  --schemas public,sales \
  --out ./metadata/mydb.db
```

You can also set the URL via environment variable:

```bash
export DB_MIGRATION_URL="postgresql+psycopg://user:pass@localhost:5432/mydb"
db-migration export --out ./metadata/mydb.db
```

### Connection URL examples

| Database   | URL example |
|------------|-------------|
| PostgreSQL | `postgresql+psycopg://user:pass@host:5432/dbname` |
| MySQL      | `mysql+pymysql://user:pass@host:3306/dbname` |
| Oracle     | `oracle+oracledb://user:pass@host:1521/?service_name=ORCL` |
| SQL Server | `mssql+pyodbc://user:pass@host/dbname?driver=ODBC+Driver+18+for+SQL+Server` |

### Initialize an empty SQLite file (DDL only)

```bash
db-migration init-db --out ./metadata/empty.db
```

### Show export summary

```bash
db-migration info ./metadata/mydb.db
```

## SQLite metadata model

Each `export` creates a new `export_run` snapshot:

| Table | Description |
|-------|-------------|
| `export_run` | Export provenance (dialect, masked URL, timestamp) |
| `db_schema` | Logical schema / catalog |
| `db_table` | Tables and views |
| `db_column` | Columns (type, nullable, default, comment) |
| `db_primary_key` | Primary key columns |
| `db_foreign_key` | Foreign keys (lineage edges) |
| `db_index` / `db_index_column` | Indexes |
| `db_unique_constraint` | Unique constraints |

DDL definition: [`src/db_migration/store/schema/v1.sql`](src/db_migration/store/schema/v1.sql)

## Downstream query examples

### Foreign key lineage (downstream: tables this table references)

```sql
SELECT fk.name, st.name AS source_table, fk.source_column,
       tt.name AS target_table, fk.target_column
FROM db_foreign_key fk
JOIN db_table st ON st.id = fk.source_table_id
JOIN db_table tt ON tt.id = fk.target_table_id
WHERE st.name = 'orders';
```

### Foreign key lineage (upstream: tables that reference this table)

```sql
SELECT fk.name, st.name AS source_table, fk.source_column,
       tt.name AS target_table, fk.target_column
FROM db_foreign_key fk
JOIN db_table st ON st.id = fk.source_table_id
JOIN db_table tt ON tt.id = fk.target_table_id
WHERE tt.name = 'customers';
```

More examples: [`examples/queries/`](examples/queries/)

## Testing

### Unit tests

No live database required:

```bash
pip install -e ".[dev]"
pytest -v
```

### End-to-end smoke test (SQLite → SQLite)

Use a local SQLite file as the source database. No extra drivers are needed beyond the base install.

**1. Create a sample source database**

```bash
mkdir -p metadata

python -c "
import sqlite3
conn = sqlite3.connect('metadata/source.db')
conn.executescript('''
CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id)
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
''')
conn.commit()
conn.close()
print('source.db created')
"
```

**2. Export metadata**

```bash
db-migration export \
  --url "sqlite:///metadata/source.db" \
  --out metadata/exported.db
```

Expected output:

```
Connecting to database...
Extracted 1 schema(s), 2 table(s)/view(s)
Written to metadata/exported.db (export_run_id=1)
```

**3. Verify the export**

```bash
db-migration info metadata/exported.db
```

Expected summary:

```
Export run:     1
Source dialect: sqlite
Schemas:        1
Tables/views:   2
Columns:        4
Foreign keys:   1
Indexes:        1
```

**4. (Optional) Inspect exported columns**

```bash
python -c "
import sqlite3
for row in sqlite3.connect('metadata/exported.db').execute(
    'SELECT stable_id, data_type, is_pk FROM db_column ORDER BY stable_id'
):
    print(row)
"
```

`metadata/*.db` files are listed in `.gitignore` and are not committed.

### Verify export against source

After exporting, reconcile the SQLite snapshot against the live database:

```bash
# 1. Export
db-migration export \
  --url "sqlite:///metadata/source.db" \
  --out metadata/exported.db

# 2. Verify (exit 0 = match, 1 = mismatch)
db-migration verify metadata/exported.db \
  --url "sqlite:///metadata/source.db"
```

Verification compares normalized entity sets:

- tables, views, columns
- primary keys, foreign keys
- indexes, unique constraints

Dialect-specific ground-truth SQL scripts:
[`src/db_migration/verify/queries/`](src/db_migration/verify/queries/)
and [`examples/verify/`](examples/verify/).

SQLite uses a programmatic collector (no portable catalog SQL). PostgreSQL, MySQL,
Oracle, and SQL Server each have a dedicated `.sql` script.

## Development

```bash
pip install -e ".[all,dev]"
pytest
```

## Out of scope (v1)

- Java migration or lineage UI
- Stored procedures, triggers, view SQL bodies
- Bidirectional sync with source databases

## License

MIT — see [LICENSE](LICENSE).
