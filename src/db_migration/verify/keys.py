"""Stable entity key builders shared by collectors."""

from __future__ import annotations


def table_key(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def column_key(schema: str, table: str, column: str) -> str:
    return f"{schema}.{table}.{column}"


def primary_key_key(schema: str, table: str, column: str, ordinal: int) -> str:
    return f"{schema}.{table}|{column}|{ordinal}"


def foreign_key_key(
    source_schema: str,
    source_table: str,
    source_column: str,
    target_schema: str,
    target_table: str,
    target_column: str,
) -> str:
    return (
        f"{source_schema}.{source_table}|{source_column}|"
        f"{target_schema}.{target_table}|{target_column}"
    )


def index_key(schema: str, table: str, index_name: str) -> str:
    return f"{schema}.{table}|{index_name}"


def unique_constraint_key(
    schema: str,
    table: str,
    name: str | None,
    column: str,
    ordinal: int,
) -> str:
    return f"{schema}.{table}|{name or ''}|{column}|{ordinal}"
