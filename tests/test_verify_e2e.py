"""End-to-end verification test using SQLite source and export."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db_migration.extract.inspector import extract_metadata
from db_migration.store.writer import MetadataWriter
from db_migration.verify.runner import run_verify


@pytest.fixture
def sqlite_source(tmp_path: Path) -> Path:
    db_path = tmp_path / "source.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE customers (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL
        );
        CREATE TABLE orders (
          id INTEGER PRIMARY KEY,
          customer_id INTEGER NOT NULL REFERENCES customers(id)
        );
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        """
    )
    conn.commit()
    conn.close()
    return db_path


def test_verify_sqlite_export_matches_source(sqlite_source: Path, tmp_path: Path) -> None:
    source_url = f"sqlite:///{sqlite_source.as_posix()}"
    metadata_db = tmp_path / "exported.db"

    snapshot = extract_metadata(source_url)
    writer = MetadataWriter(metadata_db)
    writer.write(snapshot)

    report, run_id = run_verify(
        source_url=source_url,
        metadata_db=metadata_db,
        export_run_id=1,
    )
    assert run_id == 1
    assert report.ok, (
        f"missing={report.missing_in_export[:5]}, extra={report.extra_in_export[:5]}"
    )
