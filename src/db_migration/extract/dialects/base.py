"""Base dialect adapter and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sqlalchemy import inspect
from sqlalchemy.engine import Engine, Inspector

from db_migration.models.metadata import (
    ColumnMeta,
    ForeignKeyMeta,
    IndexColumnMeta,
    IndexMeta,
    PrimaryKeyMeta,
    SchemaMeta,
    TableMeta,
    UniqueConstraintMeta,
)

if TYPE_CHECKING:
    pass

# System schemas to exclude when no explicit filter is provided
SYSTEM_SCHEMAS: dict[str, frozenset[str]] = {
    "oracle": frozenset(
        {
            "SYS",
            "SYSTEM",
            "OUTLN",
            "DBSNMP",
            "APPQOSSYS",
            "WMSYS",
            "XDB",
            "CTXSYS",
            "MDSYS",
            "ORDSYS",
            "ORDDATA",
            "LBACSYS",
            "DVSYS",
            "OJVMSYS",
            "OLAPSYS",
            "SI_INFORMTN_SCHEMA",
        }
    ),
    "postgresql": frozenset(
        {
            "pg_catalog",
            "information_schema",
            "pg_toast",
        }
    ),
    "mysql": frozenset({"information_schema", "performance_schema", "mysql", "sys"}),
    "mssql": frozenset({"sys", "INFORMATION_SCHEMA", "guest"}),
}


class DialectAdapter(ABC):
    """Normalize SQLAlchemy inspector output per dialect."""

    dialect_name: str = "generic"

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.inspector: Inspector = inspect(engine)

    def list_schemas(self, schema_filter: list[str] | None) -> list[str]:
        """Return schemas to introspect."""
        if schema_filter is not None:
            return schema_filter

        if self.inspector.has_schema():
            schemas = self.inspector.get_schema_names()
        else:
            schemas = [self.default_schema()]

        excluded = SYSTEM_SCHEMAS.get(self.dialect_name, frozenset())
        return [s for s in schemas if s not in excluded and not self._is_system_schema(s)]

    @abstractmethod
    def default_schema(self) -> str:
        """Default schema when dialect has no multi-schema support."""

    def _is_system_schema(self, schema: str) -> bool:
        return schema.startswith("pg_") if self.dialect_name == "postgresql" else False

    def extract_schema(self, schema: str) -> SchemaMeta:
        """Extract all tables and views for a schema."""
        tables: list[TableMeta] = []

        table_names = sorted(self.inspector.get_table_names(schema=schema))
        for name in table_names:
            tables.append(self.extract_table(schema, name, "TABLE"))

        if hasattr(self.inspector, "get_view_names"):
            view_names = sorted(self.inspector.get_view_names(schema=schema))
            for name in view_names:
                if name not in table_names:
                    tables.append(self.extract_table(schema, name, "VIEW"))

        return SchemaMeta(name=schema, tables=tables)

    def extract_table(self, schema: str, name: str, table_type: str) -> TableMeta:
        """Extract metadata for a single table or view."""
        raw_columns = self.inspector.get_columns(name, schema=schema)
        pk_constraint = self.inspector.get_pk_constraint(name, schema=schema) or {}
        pk_columns = pk_constraint.get("constrained_columns") or []
        pk_set = set(pk_columns)

        columns: list[ColumnMeta] = []
        for ordinal, col in enumerate(raw_columns, start=1):
            col_name = col["name"]
            full_type = self.format_full_type(col)
            data_type = self.format_data_type(col)
            columns.append(
                ColumnMeta(
                    name=col_name,
                    ordinal=ordinal,
                    data_type=data_type,
                    full_type=full_type,
                    nullable=col.get("nullable", True),
                    default_value=self.format_default(col.get("default")),
                    comment=self.get_column_comment(schema, name, col_name, col),
                    is_pk=col_name in pk_set,
                )
            )

        primary_keys = [
            PrimaryKeyMeta(column_name=col_name, ordinal=i)
            for i, col_name in enumerate(pk_columns, start=1)
        ]

        foreign_keys = self.extract_foreign_keys(schema, name)
        indexes = self.extract_indexes(schema, name)
        unique_constraints = self.extract_unique_constraints(schema, name)

        return TableMeta(
            name=name,
            table_type=table_type,
            comment=self.get_table_comment(schema, name),
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            unique_constraints=unique_constraints,
        )

    def extract_foreign_keys(self, schema: str, table: str) -> list[ForeignKeyMeta]:
        result: list[ForeignKeyMeta] = []
        for fk in self.inspector.get_foreign_keys(table, schema=schema) or []:
            constrained = fk.get("constrained_columns") or []
            referred_schema = fk.get("referred_schema") or schema
            referred_table = fk.get("referred_table")
            referred_columns = fk.get("referred_columns") or []
            if not referred_table or not constrained:
                continue
            for src_col, tgt_col in zip(constrained, referred_columns, strict=False):
                result.append(
                    ForeignKeyMeta(
                        name=fk.get("name"),
                        source_column=src_col,
                        target_schema=referred_schema,
                        target_table=referred_table,
                        target_column=tgt_col,
                        on_delete=fk.get("options", {}).get("ondelete"),
                        on_update=fk.get("options", {}).get("onupdate"),
                    )
                )
        return result

    def extract_indexes(self, schema: str, table: str) -> list[IndexMeta]:
        result: list[IndexMeta] = []
        seen: set[str] = set()
        for idx in self.inspector.get_indexes(table, schema=schema) or []:
            idx_name = idx.get("name") or ""
            if not idx_name or idx_name in seen:
                continue
            seen.add(idx_name)
            column_names = idx.get("column_names") or []
            columns = [
                IndexColumnMeta(column_name=col, ordinal=i)
                for i, col in enumerate(column_names, start=1)
                if col
            ]
            result.append(
                IndexMeta(
                    name=idx_name,
                    unique=bool(idx.get("unique")),
                    columns=columns,
                )
            )
        return result

    def extract_unique_constraints(self, schema: str, table: str) -> list[UniqueConstraintMeta]:
        result: list[UniqueConstraintMeta] = []
        for uc in self.inspector.get_unique_constraints(table, schema=schema) or []:
            columns = uc.get("column_names") or []
            if columns:
                result.append(UniqueConstraintMeta(name=uc.get("name"), columns=list(columns)))
        return result

    def format_data_type(self, col: dict) -> str:
        col_type = col.get("type")
        if col_type is None:
            return "UNKNOWN"
        return col_type.__class__.__name__.upper()

    def format_full_type(self, col: dict) -> str:
        col_type = col.get("type")
        if col_type is None:
            return "UNKNOWN"
        return str(col_type)

    def format_default(self, default) -> str | None:
        if default is None:
            return None
        return str(default)

    def get_table_comment(self, schema: str, table: str) -> str | None:
        return None

    def get_column_comment(
        self, schema: str, table: str, column: str, col_info: dict
    ) -> str | None:
        comment = col_info.get("comment")
        return str(comment) if comment else None


class GenericAdapter(DialectAdapter):
    """Fallback adapter for unsupported dialects."""

    dialect_name = "generic"

    def default_schema(self) -> str:
        return ""


def get_adapter(engine: Engine) -> DialectAdapter:
    """Return dialect adapter for the given engine."""
    from db_migration.extract.dialects.mysql import MySQLAdapter
    from db_migration.extract.dialects.oracle import OracleAdapter
    from db_migration.extract.dialects.postgresql import PostgreSQLAdapter
    from db_migration.extract.dialects.sqlserver import SQLServerAdapter

    dialect_name = engine.dialect.name
    registry: dict[str, type[DialectAdapter]] = {
        "oracle": OracleAdapter,
        "mysql": MySQLAdapter,
        "mariadb": MySQLAdapter,
        "postgresql": PostgreSQLAdapter,
        "mssql": SQLServerAdapter,
    }
    adapter_cls = registry.get(dialect_name, GenericAdapter)
    return adapter_cls(engine)
