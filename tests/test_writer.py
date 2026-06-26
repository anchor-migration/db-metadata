"""Tests for SQLite metadata writer."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db_migration.models.metadata import (
    ColumnMeta,
    DatabaseSnapshot,
    ForeignKeyMeta,
    IndexColumnMeta,
    IndexMeta,
    PrimaryKeyMeta,
    SchemaMeta,
    TableMeta,
    UniqueConstraintMeta,
)
from db_migration.store.writer import MetadataWriter, init_db, read_info


def _sample_snapshot() -> DatabaseSnapshot:
    customers = TableMeta(
        name="customers",
        table_type="TABLE",
        comment="Customer master",
        columns=[
            ColumnMeta(
                name="id",
                ordinal=1,
                data_type="INTEGER",
                full_type="INTEGER",
                nullable=False,
                is_pk=True,
            ),
            ColumnMeta(
                name="name",
                ordinal=2,
                data_type="VARCHAR",
                full_type="VARCHAR(100)",
                nullable=False,
            ),
        ],
        primary_keys=[PrimaryKeyMeta(column_name="id", ordinal=1)],
        indexes=[
            IndexMeta(
                name="idx_customers_name",
                unique=False,
                columns=[IndexColumnMeta(column_name="name", ordinal=1)],
            )
        ],
        unique_constraints=[
            UniqueConstraintMeta(name="uq_customers_name", columns=["name"]),
        ],
    )
    orders = TableMeta(
        name="orders",
        table_type="TABLE",
        columns=[
            ColumnMeta(
                name="id",
                ordinal=1,
                data_type="INTEGER",
                full_type="INTEGER",
                nullable=False,
                is_pk=True,
            ),
            ColumnMeta(
                name="customer_id",
                ordinal=2,
                data_type="INTEGER",
                full_type="INTEGER",
                nullable=False,
            ),
        ],
        primary_keys=[PrimaryKeyMeta(column_name="id", ordinal=1)],
        foreign_keys=[
            ForeignKeyMeta(
                name="fk_orders_customer",
                source_column="customer_id",
                target_schema="public",
                target_table="customers",
                target_column="id",
                on_delete="CASCADE",
            )
        ],
    )
    return DatabaseSnapshot(
        source_dialect="postgresql",
        source_url_masked="postgresql://user:***@localhost:5432/testdb",
        schema_filter="public",
        schemas=[SchemaMeta(name="public", tables=[customers, orders])],
    )


def test_init_db_creates_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "meta.db"
    init_db(db_path)
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        version = conn.execute(
            "SELECT version FROM meta_schema_version"
        ).fetchone()
        assert version is not None
        assert version[0] == 1

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "meta_schema_version",
            "export_run",
            "db_schema",
            "db_table",
            "db_column",
            "db_primary_key",
            "db_foreign_key",
            "db_index",
            "db_index_column",
            "db_unique_constraint",
        }
        assert expected.issubset(tables)
    finally:
        conn.close()


def test_writer_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "meta.db"
    snapshot = _sample_snapshot()

    writer = MetadataWriter(db_path)
    export_run_id = writer.write(snapshot)
    assert export_run_id == 1

    info = read_info(db_path)
    assert info.export_run_id == 1
    assert info.source_dialect == "postgresql"
    assert info.schema_count == 1
    assert info.table_count == 2
    assert info.column_count == 4
    assert info.foreign_key_count == 1
    assert info.index_count == 1

    conn = sqlite3.connect(db_path)
    try:
        stable_ids = [
            row[0]
            for row in conn.execute(
                "SELECT stable_id FROM db_column WHERE export_run_id = ? ORDER BY stable_id",
                (export_run_id,),
            ).fetchall()
        ]
        assert stable_ids == [
            "public.customers.id",
            "public.customers.name",
            "public.orders.customer_id",
            "public.orders.id",
        ]

        fk = conn.execute(
            """
            SELECT fk.name, st.name, tt.name
            FROM db_foreign_key fk
            JOIN db_table st ON st.id = fk.source_table_id
            JOIN db_table tt ON tt.id = fk.target_table_id
            WHERE fk.export_run_id = ?
            """,
            (export_run_id,),
        ).fetchone()
        assert fk == ("fk_orders_customer", "orders", "customers")
    finally:
        conn.close()


def test_writer_preserves_export_history(tmp_path: Path) -> None:
    db_path = tmp_path / "meta.db"
    writer = MetadataWriter(db_path)

    first_id = writer.write(_sample_snapshot())
    second_id = writer.write(_sample_snapshot())

    assert first_id == 1
    assert second_id == 2

    conn = sqlite3.connect(db_path)
    try:
        run_count = conn.execute("SELECT COUNT(*) FROM export_run").fetchone()[0]
        assert run_count == 2
    finally:
        conn.close()


def test_read_info_requires_export_run(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    init_db(db_path)
    with pytest.raises(ValueError, match="No export runs"):
        read_info(db_path)
