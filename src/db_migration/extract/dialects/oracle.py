"""Oracle-specific metadata extraction."""

from __future__ import annotations

from sqlalchemy import text

from db_migration.extract.dialects.base import DialectAdapter, SYSTEM_SCHEMAS


class OracleAdapter(DialectAdapter):
    dialect_name = "oracle"

    def default_schema(self) -> str:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT USER FROM DUAL")).scalar()
            return str(result) if result else ""

    def list_schemas(self, schema_filter: list[str] | None) -> list[str]:
        if schema_filter is not None:
            return [s.upper() for s in schema_filter]
        schemas = super().list_schemas(None)
        excluded = SYSTEM_SCHEMAS["oracle"]
        return [s.upper() for s in schemas if s.upper() not in excluded]

    def get_table_comment(self, schema: str, table: str) -> str | None:
        query = text(
            """
            SELECT comments FROM all_tab_comments
            WHERE owner = :owner AND table_name = :table_name AND table_type IN ('TABLE', 'VIEW')
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"owner": schema.upper(), "table_name": table.upper()}
            ).scalar()
            return str(result) if result else None

    def get_column_comment(
        self, schema: str, table: str, column: str, col_info: dict
    ) -> str | None:
        base = super().get_column_comment(schema, table, column, col_info)
        if base:
            return base
        query = text(
            """
            SELECT comments FROM all_col_comments
            WHERE owner = :owner AND table_name = :table_name AND column_name = :column_name
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {
                    "owner": schema.upper(),
                    "table_name": table.upper(),
                    "column_name": column.upper(),
                },
            ).scalar()
            return str(result) if result else None

    def format_full_type(self, col: dict) -> str:
        col_type = col.get("type")
        if col_type is None:
            return "UNKNOWN"
        type_str = str(col_type)
        precision = col.get("precision") or getattr(col_type, "precision", None)
        scale = col.get("scale") or getattr(col_type, "scale", None)
        if precision is not None and scale is not None:
            return f"{type_str}({precision},{scale})"
        if precision is not None:
            return f"{type_str}({precision})"
        return type_str
