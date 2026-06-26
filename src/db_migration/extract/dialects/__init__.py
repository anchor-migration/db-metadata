"""Dialect-specific metadata adapters."""

from db_migration.extract.dialects.base import DialectAdapter, get_adapter

__all__ = ["DialectAdapter", "get_adapter"]
