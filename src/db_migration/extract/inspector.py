"""Orchestrate metadata extraction from source databases."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from db_migration.config import mask_url, normalize_schema_filter
from db_migration.extract.dialects import get_adapter
from db_migration.models.metadata import DatabaseSnapshot, SchemaMeta


def create_readonly_engine(url: str) -> Engine:
    """Create a read-only SQLAlchemy engine (no DDL on source)."""
    return create_engine(
        url,
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )


def extract_metadata(
    url: str,
    schema_filter: list[str] | None = None,
) -> DatabaseSnapshot:
    """
    Extract database metadata from a live source database.

    Performs read-only introspection via SQLAlchemy Inspector and dialect adapters.
    """
    engine = create_readonly_engine(url)
    try:
        adapter = get_adapter(engine)
        schemas_to_extract = adapter.list_schemas(schema_filter)
        schema_metas: list[SchemaMeta] = []

        for schema_name in schemas_to_extract:
            schema_metas.append(adapter.extract_schema(schema_name))

        return DatabaseSnapshot(
            source_dialect=engine.dialect.name,
            source_url_masked=mask_url(url),
            schema_filter=normalize_schema_filter(schema_filter),
            schemas=schema_metas,
        )
    finally:
        engine.dispose()
