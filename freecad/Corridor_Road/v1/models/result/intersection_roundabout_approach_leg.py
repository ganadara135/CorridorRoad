"""Roundabout approach-leg result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionRoundaboutApproachLegRow:
    """One physical approach leg resolved from roundabout source/topology intent."""

    approach_leg_id: str
    intersection_id: str
    approach_role: str
    approach_index: int = 0
    source_leg_ref: str = ""
    source_leg_role: str = ""
    alignment_ref: str = ""
    control_area_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    handoff_station: float = 0.0
    inner_station: float = 0.0
    outer_station: float = 0.0
    direction_sign: int = 1
    direction_angle_deg: float = 0.0
    direction_vector_xy: tuple[float, float] = (0.0, 0.0)
    approach_center_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    roundabout_center_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    connector_boundary_role: str = "roundabout_entry_exit_connector_boundary"
    corridor_clip_boundary_role: str = "roundabout_approach_clip_boundary"
    subgrade_handoff_boundary_role: str = "roundabout_subgrade_clip_boundary"
    slope_handoff_boundary_role: str = "roundabout_slope_handoff_boundary"
    shared_breakline_roles: tuple[str, ...] = ()
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionRoundaboutApproachLegResult(ResultModelBase):
    """Directional approach-leg contract for roundabout output builders."""

    approach_leg_result_id: str = "intersection-roundabout-approach-legs:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    source_leg_count: int = 0
    approach_leg_count: int = 0
    accepted_approach_leg_count: int = 0
    alignment_count: int = 0
    approach_leg_rows: list[IntersectionRoundaboutApproachLegRow] = field(default_factory=list)
