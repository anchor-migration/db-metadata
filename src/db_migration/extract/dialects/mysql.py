"""MySQL-specific metadata extraction."""

from __future__ import annotations

from sqlalchemy import text

from db_migration.extract.dialects.base import DialectAdapter


class MySQLAdapter(DialectAdapter):
    dialect_name = "mysql"

    def default_schema(self) -> str:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT DATABASE()")).scalar()
            return str(result) if result else ""

    def list_schemas(self, schema_filter: list[str] | None) -> list[str]:
        if schema_filter is not None:
            return schema_filter
        with self.engine.connect() as conn:
            rows = conn.execute(text("SHOW DATABASES")).fetchall()
        schemas = [row[0] for row in rows]
        excluded = self._system_schemas()
        return [s for s in schemas if s not in excluded]

    def _system_schemas(self) -> frozenset[str]:
        from db_migration.extract.dialects.base import SYSTEM_SCHEMAS

        return SYSTEM_SCHEMAS["mysql"]

    def get_table_comment(self, schema: str, table: str) -> str | None:
        query = text(
            """
            SELECT table_comment FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table_name
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"schema": schema, "table_name": table}).scalar()
            if result and str(result) not in ("", "VIEW"):
                return str(result)
        return None

    def get_column_comment(
        self, schema: str, table: str, column: str, col_info: dict
    ) -> str | None:
        base = super().get_column_comment(schema, table, column, col_info)
        if base:
            return base
        query = text(
            """
            SELECT column_comment FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table_name AND column_name = :column
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"schema": schema, "table_name": table, "column": column}
            ).scalar()
            return str(result) if result else None
