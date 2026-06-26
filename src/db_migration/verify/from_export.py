"""Collect normalized entity records from exported SQLite metadata."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from db_migration.verify.entities import EntityRecord


def resolve_export_run_id(conn: sqlite3.Connection, export_run_id: int | None) -> int:
    if export_run_id is not None:
        row = conn.execute(
            "SELECT id FROM export_run WHERE id = ?", (export_run_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Export run {export_run_id} not found")
        return export_run_id

    row = conn.execute("SELECT id FROM export_run ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        raise ValueError("No export runs found in metadata database")
    return row[0]


def collect_from_export(
    metadata_db: str | Path,
    export_run_id: int | None = None,
    schema_filter: list[str] | None = None,
) -> set[EntityRecord]:
    """Build entity set from an export snapshot in SQLite."""
    conn = sqlite3.connect(metadata_db)
    try:
        run_id = resolve_export_run_id(conn, export_run_id)
        entities: set[EntityRecord] = set()

        for row in conn.execute(
            """
            SELECT CASE table_type WHEN 'VIEW' THEN 'view' ELSE 'table' END,
                   stable_id
            FROM db_table
            WHERE export_run_id = ?
            """,
            (run_id,),
        ):
            entities.add(EntityRecord(entity_type=row[0], entity_key=row[1]))

        for row in conn.execute(
            "SELECT stable_id FROM db_column WHERE export_run_id = ?",
            (run_id,),
        ):
            entities.add(EntityRecord(entity_type="column", entity_key=row[0]))

        for row in conn.execute(
            """
            SELECT ds.name || '.' || dt.name || '|' || pk.column_name || '|' || pk.ordinal
            FROM db_primary_key pk
            JOIN db_table dt ON dt.id = pk.table_id
            JOIN db_schema ds ON ds.id = dt.schema_id
            WHERE pk.export_run_id = ?
            """,
            (run_id,),
        ):
            entities.add(EntityRecord(entity_type="primary_key", entity_key=row[0]))

        for row in conn.execute(
            """
            SELECT
                sds.name || '.' || st.name || '|' || fk.source_column || '|' ||
                tds.name || '.' || tt.name || '|' || fk.target_column
            FROM db_foreign_key fk
            JOIN db_table st ON st.id = fk.source_table_id
            JOIN db_schema sds ON sds.id = st.schema_id
            JOIN db_table tt ON tt.id = fk.target_table_id
            JOIN db_schema tds ON tds.id = tt.schema_id
            WHERE fk.export_run_id = ?
            """,
            (run_id,),
        ):
            entities.add(EntityRecord(entity_type="foreign_key", entity_key=row[0]))

        for row in conn.execute(
            """
            SELECT ds.name || '.' || dt.name || '|' || idx.name
            FROM db_index idx
            JOIN db_table dt ON dt.id = idx.table_id
            JOIN db_schema ds ON ds.id = dt.schema_id
            WHERE idx.export_run_id = ?
            """,
            (run_id,),
        ):
            entities.add(EntityRecord(entity_type="index", entity_key=row[0]))

        for row in conn.execute(
            """
            SELECT
                ds.name || '.' || dt.name || '|' ||
                COALESCE(uc.name, '') || '|' ||
                uc.column_name || '|' || uc.ordinal
            FROM db_unique_constraint uc
            JOIN db_table dt ON dt.id = uc.table_id
            JOIN db_schema ds ON ds.id = dt.schema_id
            WHERE uc.export_run_id = ?
            """,
            (run_id,),
        ):
            entities.add(EntityRecord(entity_type="unique_constraint", entity_key=row[0]))

        return _apply_schema_filter(entities, schema_filter)
    finally:
        conn.close()


def _apply_schema_filter(
    entities: set[EntityRecord],
    schema_filter: list[str] | None,
) -> set[EntityRecord]:
    if not schema_filter:
        return entities
    allowed = {s.lower() for s in schema_filter}
    return {e for e in entities if e.schema_name.lower() in allowed}
