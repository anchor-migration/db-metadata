"""SQL Server-specific metadata extraction."""

from __future__ import annotations

from sqlalchemy import text

from db_migration.extract.dialects.base import DialectAdapter, SYSTEM_SCHEMAS


class SQLServerAdapter(DialectAdapter):
    dialect_name = "mssql"

    def default_schema(self) -> str:
        return "dbo"

    def list_schemas(self, schema_filter: list[str] | None) -> list[str]:
        if schema_filter is not None:
            return schema_filter
        try:
            schemas = list(self.inspector.get_schema_names())
        except NotImplementedError:
            schemas = []
        if not schemas:
            schemas = [self.default_schema()]
        excluded = SYSTEM_SCHEMAS["mssql"]
        return [s for s in schemas if s not in excluded and not s.startswith("db_")]

    def get_table_comment(self, schema: str, table: str) -> str | None:
        query = text(
            """
            SELECT CAST(ep.value AS NVARCHAR(MAX))
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = t.object_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
            WHERE s.name = :schema AND t.name = :table_name
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"schema": schema, "table_name": table}).scalar()
            if result:
                return str(result)

        view_query = text(
            """
            SELECT CAST(ep.value AS NVARCHAR(MAX))
            FROM sys.views v
            INNER JOIN sys.schemas s ON v.schema_id = s.schema_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = v.object_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
            WHERE s.name = :schema AND v.name = :table_name
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                view_query, {"schema": schema, "table_name": table}
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
            SELECT CAST(ep.value AS NVARCHAR(MAX))
            FROM sys.columns c
            INNER JOIN sys.objects o ON c.object_id = o.object_id
            INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = c.object_id AND ep.minor_id = c.column_id
                AND ep.name = 'MS_Description'
            WHERE s.name = :schema AND o.name = :table_name AND c.name = :column_name
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"schema": schema, "table_name": table, "column_name": column}
            ).scalar()
            return str(result) if result else None

    def format_data_type(self, col: dict) -> str:
        col_type = col.get("type")
        if col_type is None:
            return "UNKNOWN"
        name = col_type.__class__.__name__.upper()
        if name == "NVARCHAR" or name == "VARCHAR":
            return name
        return name
