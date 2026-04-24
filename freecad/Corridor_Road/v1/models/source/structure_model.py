"""Structure source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class StructurePlacement:
    """Minimal station-aware structure placement."""

    placement_id: str
    alignment_id: str
    station_start: float
    station_end: float
    offset: float = 0.0
    elevation_reference: str = ""
    orientation_mode: str = "alignment"


@dataclass(frozen=True)
class StructureInteractionRule:
    """Minimal structure interaction rule."""

    interaction_rule_id: str
    structure_ref: str
    rule_kind: str
    target_scope: str
    parameter: str = ""
    value: float | str = ""
    unit: str = ""
    priority: int = 0


@dataclass(frozen=True)
class StructureInfluenceZone:
    """Minimal structure influence zone."""

    influence_zone_id: str
    structure_ref: str
    zone_kind: str
    station_start: float
    station_end: float
    offset_min: float | None = None
    offset_max: float | None = None


@dataclass(frozen=True)
class StructureRow:
    """Minimal corridor-related structure row."""

    structure_id: str
    structure_kind: str
    structure_role: str
    placement: StructurePlacement
    geometry_ref: str = ""
    reference_mode: str = "native"


@dataclass
class StructureModel(SourceModelBase):
    """Durable structure source contract."""

    structure_model_id: str = ""
    alignment_id: str = ""
    structure_rows: list[StructureRow] = field(default_factory=list)
    interaction_rule_rows: list[StructureInteractionRule] = field(default_factory=list)
    influence_zone_rows: list[StructureInfluenceZone] = field(default_factory=list)
