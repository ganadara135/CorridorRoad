"""Project source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass
class ProjectModel(SourceModelBase):
    """Top-level project source contract for v1."""

    project_name: str = ""
    project_metadata: dict[str, object] = field(default_factory=dict)
