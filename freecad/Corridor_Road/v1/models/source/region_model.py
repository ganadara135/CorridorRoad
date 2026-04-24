"""Region source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class RegionPolicyRow:
    """Minimal region policy row."""

    policy_id: str
    component_scope: str
    parameter: str
    value: float | str
    unit: str = ""
    policy_kind: str = "parameter_override"


@dataclass(frozen=True)
class RegionTransition:
    """Minimal region transition row."""

    transition_id: str
    from_region_id: str
    to_region_id: str
    station_start: float
    station_end: float
    transition_kind: str = "linear_blend"


@dataclass(frozen=True)
class RegionRow:
    """Minimal region row."""

    region_id: str
    region_kind: str
    station_start: float
    station_end: float
    template_ref: str = ""
    superelevation_ref: str = ""
    priority: int = 0
    policy_rows: list[RegionPolicyRow] = field(default_factory=list)


@dataclass
class RegionModel(SourceModelBase):
    """Durable region source contract."""

    region_model_id: str = ""
    alignment_id: str = ""
    region_rows: list[RegionRow] = field(default_factory=list)
    transition_rows: list[RegionTransition] = field(default_factory=list)
