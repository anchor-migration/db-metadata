"""Entity records used for metadata reconciliation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRecord:
    """Normalized metadata entity for set comparison."""

    entity_type: str
    entity_key: str

    @property
    def schema_name(self) -> str:
        """Extract schema name from entity_key for filtering."""
        if self.entity_type in ("table", "view", "column"):
            return self.entity_key.split(".")[0]
        if self.entity_type in ("primary_key", "index", "unique_constraint"):
            return self.entity_key.split(".")[0]
        if self.entity_type == "foreign_key":
            return self.entity_key.split(".")[0]
        return ""
