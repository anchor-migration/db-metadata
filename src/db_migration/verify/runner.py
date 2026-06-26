"""Orchestrate metadata export verification."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from db_migration.extract.inspector import create_readonly_engine
from db_migration.verify.from_export import collect_from_export, resolve_export_run_id
from db_migration.verify.from_source import collect_from_source, read_export_schema_filter
from db_migration.verify.reconcile import ReconcileReport, reconcile


def run_verify(
    source_url: str,
    metadata_db: str | Path,
    export_run_id: int | None = None,
    schema_filter: list[str] | None = None,
    engine: Engine | None = None,
) -> tuple[ReconcileReport, int]:
    """
    Reconcile exported metadata against live source database.

    Returns (report, export_run_id used).
    """
    metadata_path = str(metadata_db)
    import sqlite3

    conn = sqlite3.connect(metadata_path)
    try:
        run_id = resolve_export_run_id(conn, export_run_id)
    finally:
        conn.close()

    if schema_filter is None:
        schema_filter = read_export_schema_filter(metadata_path, run_id)

    owns_engine = engine is None
    if engine is None:
        engine = create_readonly_engine(source_url)

    try:
        source_entities = collect_from_source(engine, schema_filter)
        export_entities = collect_from_export(metadata_path, run_id, schema_filter)
        report = reconcile(source_entities, export_entities)
        return report, run_id
    finally:
        if owns_engine:
            engine.dispose()
