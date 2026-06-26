"""Collect normalized entity records from a live source database."""

from __future__ import annotations

from importlib import resources

from sqlalchemy import text
from sqlalchemy.engine import Engine

from db_migration.config import parse_schemas
from db_migration.verify.entities import EntityRecord
from db_migration.verify.from_export import _apply_schema_filter
from db_migration.verify.sqlite_collector import collect_sqlite_entities


_DIALECT_SQL_MAP = {
    "postgresql": "postgresql.sql",
    "mysql": "mysql.sql",
    "mariadb": "mysql.sql",
    "oracle": "oracle.sql",
    "mssql": "sqlserver.sql",
}


def _load_sql(dialect_name: str) -> str:
    filename = _DIALECT_SQL_MAP.get(dialect_name)
    if filename is None:
        raise ValueError(
            f"No verification SQL for dialect '{dialect_name}'. "
            f"Supported: {', '.join(sorted(set(_DIALECT_SQL_MAP)))}"
        )
    ref = resources.files("db_migration.verify.queries") / filename
    return ref.read_text(encoding="utf-8")


def collect_from_source(
    engine: Engine,
    schema_filter: list[str] | None = None,
) -> set[EntityRecord]:
    """Run dialect-specific verification SQL against the source database."""
    dialect_name = engine.dialect.name

    if dialect_name == "sqlite":
        return collect_sqlite_entities(engine, schema_filter)

    sql = _load_sql(dialect_name)

    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()

    entities = {EntityRecord(entity_type=row[0], entity_key=row[1]) for row in rows}
    return _apply_schema_filter(entities, schema_filter)


def read_export_schema_filter(metadata_db: str, export_run_id: int | None) -> list[str] | None:
    """Read schema_filter from export_run record."""
    import sqlite3

    from db_migration.verify.from_export import resolve_export_run_id

    conn = sqlite3.connect(metadata_db)
    try:
        run_id = resolve_export_run_id(conn, export_run_id)
        row = conn.execute(
            "SELECT schema_filter FROM export_run WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return parse_schemas(row[0])
    finally:
        conn.close()
