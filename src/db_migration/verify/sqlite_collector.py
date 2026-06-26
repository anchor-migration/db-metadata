"""SQLite source verification via SQLAlchemy inspector (no portable catalog SQL)."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from db_migration.verify.entities import EntityRecord
from db_migration.verify.from_export import _apply_schema_filter
from db_migration.verify.keys import (
    column_key,
    foreign_key_key,
    index_key,
    primary_key_key,
    table_key,
    unique_constraint_key,
)


def collect_sqlite_entities(
    engine: Engine,
    schema_filter: list[str] | None = None,
) -> set[EntityRecord]:
    """Collect entities from SQLite using inspector (matches export key format)."""
    inspector = inspect(engine)
    entities: set[EntityRecord] = set()

    schemas = inspector.get_schema_names() or ["main"]
    for schema in schemas:
        for table_name in inspector.get_table_names(schema=schema):
            entities.add(EntityRecord("table", table_key(schema, table_name)))
            _collect_table_entities(inspector, entities, schema, table_name, "TABLE")

        for view_name in inspector.get_view_names(schema=schema):
            if view_name not in inspector.get_table_names(schema=schema):
                entities.add(EntityRecord("view", table_key(schema, view_name)))
                _collect_table_entities(inspector, entities, schema, view_name, "VIEW")

    return _apply_schema_filter(entities, schema_filter)


def _collect_table_entities(
    inspector,
    entities: set[EntityRecord],
    schema: str,
    table_name: str,
    table_type: str,
) -> None:
    for ordinal, col in enumerate(inspector.get_columns(table_name, schema=schema), start=1):
        entities.add(EntityRecord("column", column_key(schema, table_name, col["name"])))

    pk = inspector.get_pk_constraint(table_name, schema=schema) or {}
    for i, col_name in enumerate(pk.get("constrained_columns") or [], start=1):
        entities.add(EntityRecord("primary_key", primary_key_key(schema, table_name, col_name, i)))

    for fk in inspector.get_foreign_keys(table_name, schema=schema) or []:
        constrained = fk.get("constrained_columns") or []
        referred_schema = fk.get("referred_schema") or schema
        referred_table = fk.get("referred_table")
        referred_columns = fk.get("referred_columns") or []
        if not referred_table:
            continue
        for src_col, tgt_col in zip(constrained, referred_columns, strict=False):
            entities.add(
                EntityRecord(
                    "foreign_key",
                    foreign_key_key(
                        schema, table_name, src_col,
                        referred_schema, referred_table, tgt_col,
                    ),
                )
            )

    if table_type == "TABLE":
        seen_indexes: set[str] = set()
        for idx in inspector.get_indexes(table_name, schema=schema) or []:
            idx_name = idx.get("name")
            if idx_name and idx_name not in seen_indexes:
                seen_indexes.add(idx_name)
                entities.add(EntityRecord("index", index_key(schema, table_name, idx_name)))

        for uc in inspector.get_unique_constraints(table_name, schema=schema) or []:
            name = uc.get("name")
            for ordinal, col_name in enumerate(uc.get("column_names") or [], start=1):
                entities.add(
                    EntityRecord(
                        "unique_constraint",
                        unique_constraint_key(schema, table_name, name, col_name, ordinal),
                    )
                )
