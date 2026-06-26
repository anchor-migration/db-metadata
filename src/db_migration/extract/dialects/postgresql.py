"""PostgreSQL-specific metadata extraction."""

from __future__ import annotations

from sqlalchemy import text

from db_migration.extract.dialects.base import DialectAdapter


class PostgreSQLAdapter(DialectAdapter):
    dialect_name = "postgresql"

    def default_schema(self) -> str:
        return "public"

    def _is_system_schema(self, schema: str) -> bool:
        return schema.startswith("pg_") or schema == "information_schema"

    def get_table_comment(self, schema: str, table: str) -> str | None:
        query = text(
            """
            SELECT obj_description(c.oid)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :schema AND c.relname = :table_name
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"schema": schema, "table_name": table}).scalar()
            return str(result) if result else None

    def get_column_comment(
        self, schema: str, table: str, column: str, col_info: dict
    ) -> str | None:
        base = super().get_column_comment(schema, table, column, col_info)
        if base:
            return base
        query = text(
            """
            SELECT col_description(c.oid, a.attnum)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid
            WHERE n.nspname = :schema AND c.relname = :table_name AND a.attname = :column
              AND a.attnum > 0 AND NOT a.attisdropped
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"schema": schema, "table_name": table, "column": column}
            ).scalar()
            return str(result) if result else None

    def format_full_type(self, col: dict) -> str:
        col_type = col.get("type")
        if col_type is None:
            return "UNKNOWN"
        type_str = str(col_type)
        if col.get("autoincrement"):
            return f"{type_str} AUTO_INCREMENT"
        return type_str
