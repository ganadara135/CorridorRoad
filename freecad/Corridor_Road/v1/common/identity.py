"""Shared identity helpers for CorridorRoad v1."""

from __future__ import annotations

from uuid import uuid4


def new_entity_id(entity_kind: str) -> str:
    """Create a simple opaque id for a v1 entity kind."""

    return f"{entity_kind}:{uuid4().hex}"
