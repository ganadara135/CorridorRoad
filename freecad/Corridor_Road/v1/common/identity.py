"""Shared identity helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class EntityIdentity:
    """Minimal stable identity container for v1 models."""

    entity_id: str
    entity_kind: str


@dataclass(frozen=True)
class EntityRef:
    """Lightweight reference to another v1 entity."""

    entity_id: str
    entity_kind: str
    label: str = ""


def new_entity_id(entity_kind: str) -> str:
    """Create a simple opaque id for a v1 entity kind."""

    return f"{entity_kind}:{uuid4().hex}"
