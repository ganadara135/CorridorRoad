"""Intersection source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class IntersectionLegRow:
    """Minimal participating-leg row for one junction."""

    leg_id: str
    leg_role: str
    alignment_ref: str
    profile_ref: str = ""
    region_ref: str = ""
    approach_station_start: float = 0.0
    approach_station_end: float = 0.0
    priority: int = 0


@dataclass(frozen=True)
class IntersectionControlArea:
    """Minimal control-area row for one intersection."""

    control_area_id: str
    intersection_id: str
    station_ranges: list[tuple[float, float]] = field(default_factory=list)
    influence_ranges: list[tuple[float, float]] = field(default_factory=list)
    turn_lane_policy_ref: str = ""
    curb_return_policy_ref: str = ""
    drainage_policy_ref: str = ""


@dataclass(frozen=True)
class IntersectionRow:
    """Minimal at-grade intersection definition row."""

    intersection_id: str
    intersection_kind: str
    leg_rows: list[IntersectionLegRow] = field(default_factory=list)
    control_area_ref: str = ""
    grading_policy_ref: str = ""
    drainage_ref: str = ""
    design_criteria_ref: str = ""


@dataclass
class IntersectionModel(SourceModelBase):
    """Durable at-grade junction source contract."""

    intersection_model_id: str = ""
    intersection_rows: list[IntersectionRow] = field(default_factory=list)
    control_area_rows: list[IntersectionControlArea] = field(default_factory=list)
