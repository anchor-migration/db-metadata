"""Tests for metadata reconciliation."""

from __future__ import annotations

from db_migration.verify.entities import EntityRecord
from db_migration.verify.reconcile import reconcile


def test_reconcile_ok() -> None:
    source = {
        EntityRecord("table", "main.customers"),
        EntityRecord("column", "main.customers.id"),
        EntityRecord("foreign_key", "main.orders|customer_id|main.customers|id"),
    }
    export = set(source)
    report = reconcile(source, export)
    assert report.ok
    assert report.matched == 3
    assert report.missing_in_export == []
    assert report.extra_in_export == []


def test_reconcile_missing_in_export() -> None:
    source = {
        EntityRecord("table", "main.customers"),
        EntityRecord("column", "main.customers.id"),
    }
    export = {EntityRecord("table", "main.customers")}
    report = reconcile(source, export)
    assert not report.ok
    assert len(report.missing_in_export) == 1
    assert report.missing_in_export[0].entity_type == "column"


def test_reconcile_extra_in_export() -> None:
    source = {EntityRecord("table", "main.customers")}
    export = {
        EntityRecord("table", "main.customers"),
        EntityRecord("index", "main.customers|idx_name"),
    }
    report = reconcile(source, export)
    assert not report.ok
    assert len(report.extra_in_export) == 1
    assert report.extra_in_export[0].entity_type == "index"


def test_reconcile_summary_by_type() -> None:
    source = {
        EntityRecord("table", "main.a"),
        EntityRecord("column", "main.a.id"),
    }
    export = {EntityRecord("table", "main.a")}
    report = reconcile(source, export)
    summary = report.summary_by_type()
    assert summary["column"]["missing"] == 1
    assert summary["column"]["extra"] == 0
