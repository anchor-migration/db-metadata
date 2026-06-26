"""Domain models for extracted database metadata."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ColumnMeta:
    name: str
    ordinal: int
    data_type: str
    full_type: str
    nullable: bool
    default_value: str | None = None
    comment: str | None = None
    is_pk: bool = False


@dataclass
class PrimaryKeyMeta:
    column_name: str
    ordinal: int


@dataclass
class ForeignKeyMeta:
    name: str | None
    source_column: str
    target_schema: str
    target_table: str
    target_column: str
    on_delete: str | None = None
    on_update: str | None = None


@dataclass
class IndexColumnMeta:
    column_name: str
    ordinal: int
    sort_order: str | None = None


@dataclass
class IndexMeta:
    name: str
    unique: bool
    columns: list[IndexColumnMeta] = field(default_factory=list)


@dataclass
class UniqueConstraintMeta:
    name: str | None
    columns: list[str] = field(default_factory=list)


@dataclass
class TableMeta:
    name: str
    table_type: str  # TABLE or VIEW
    comment: str | None = None
    columns: list[ColumnMeta] = field(default_factory=list)
    primary_keys: list[PrimaryKeyMeta] = field(default_factory=list)
    foreign_keys: list[ForeignKeyMeta] = field(default_factory=list)
    indexes: list[IndexMeta] = field(default_factory=list)
    unique_constraints: list[UniqueConstraintMeta] = field(default_factory=list)


@dataclass
class SchemaMeta:
    name: str
    tables: list[TableMeta] = field(default_factory=list)


@dataclass
class DatabaseSnapshot:
    source_dialect: str
    source_url_masked: str
    schema_filter: str | None
    schemas: list[SchemaMeta] = field(default_factory=list)
