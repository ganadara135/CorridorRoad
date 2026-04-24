"""Schema version helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass


def schema_version(version: int) -> int:
    """Return a normalized schema version integer."""

    return int(version)


@dataclass(frozen=True)
class SchemaInfo:
    """Minimal schema metadata container for v1 models."""

    schema_name: str
    schema_version: int
