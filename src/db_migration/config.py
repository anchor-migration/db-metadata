"""Configuration helpers for database connections and schema filtering."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse, urlunparse


def resolve_url(url: str | None = None) -> str:
    """Resolve database URL from CLI arg or DB_MIGRATION_URL env var."""
    resolved = url or os.environ.get("DB_MIGRATION_URL")
    if not resolved:
        raise ValueError(
            "Database URL required: pass --url or set DB_MIGRATION_URL environment variable"
        )
    return resolved


def parse_schemas(schemas: str | None) -> list[str] | None:
    """Parse comma-separated schema list. None means all user schemas."""
    if not schemas or not schemas.strip():
        return None
    return [s.strip() for s in schemas.split(",") if s.strip()]


def mask_url(url: str) -> str:
    """Mask password in connection URL for storage in export_run."""
    parsed = urlparse(url)
    if parsed.password:
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        if parsed.username:
            netloc = f"{parsed.username}:***@{netloc}"
        else:
            netloc = f"***@{netloc}"
        return urlunparse(parsed._replace(netloc=netloc))
    return url


def normalize_schema_filter(schemas: list[str] | None) -> str | None:
    """Serialize schema filter for export_run record."""
    if schemas is None:
        return None
    return ",".join(schemas)


def stable_column_id(schema: str, table: str, column: str) -> str:
    """Build stable column identifier: schema.table.column."""
    return f"{schema}.{table}.{column}"


def stable_table_id(schema: str, table: str) -> str:
    """Build stable table identifier: schema.table."""
    return f"{schema}.{table}"


_CREDENTIAL_PATTERN = re.compile(r":([^:@/]+)@")


def redact_credentials(text: str) -> str:
    """Redact credentials in log output."""
    return _CREDENTIAL_PATTERN.sub(":****@", text)
