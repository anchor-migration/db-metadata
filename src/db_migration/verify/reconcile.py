"""Compare source and export entity sets."""

from __future__ import annotations

from dataclasses import dataclass, field

from db_migration.verify.entities import EntityRecord


@dataclass
class ReconcileReport:
    """Result of reconciling source database entities against an export."""

    matched: int
    missing_in_export: list[EntityRecord] = field(default_factory=list)
    extra_in_export: list[EntityRecord] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_in_export and not self.extra_in_export

    def summary_by_type(self) -> dict[str, dict[str, int]]:
        """Group mismatch counts by entity_type."""
        result: dict[str, dict[str, int]] = {}
        for entity in self.missing_in_export:
            bucket = result.setdefault(entity.entity_type, {"missing": 0, "extra": 0})
            bucket["missing"] += 1
        for entity in self.extra_in_export:
            bucket = result.setdefault(entity.entity_type, {"missing": 0, "extra": 0})
            bucket["extra"] += 1
        return result


def reconcile(
    source_entities: set[EntityRecord],
    export_entities: set[EntityRecord],
) -> ReconcileReport:
    """Diff two entity sets. Source is ground truth."""
    source_keys = {(e.entity_type, e.entity_key) for e in source_entities}
    export_keys = {(e.entity_type, e.entity_key) for e in export_entities}

    missing_keys = source_keys - export_keys
    extra_keys = export_keys - source_keys
    matched = len(source_keys & export_keys)

    missing = sorted(
        (EntityRecord(t, k) for t, k in missing_keys),
        key=lambda e: (e.entity_type, e.entity_key),
    )
    extra = sorted(
        (EntityRecord(t, k) for t, k in extra_keys),
        key=lambda e: (e.entity_type, e.entity_key),
    )

    return ReconcileReport(
        matched=matched,
        missing_in_export=missing,
        extra_in_export=extra,
    )
