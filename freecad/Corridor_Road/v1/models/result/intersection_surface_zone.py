"""Intersection surface-zone result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionSurfaceZoneRow:
    """One surface-zone contract row before triangulation."""

    zone_id: str
    intersection_id: str
    zone_role: str
    zone_family: str
    design_zone_role: str = ""
    surface_role: str = "design"
    source_edge_refs: tuple[str, ...] = ()
    boundary_edge_refs: tuple[str, ...] = ()
    inner_edge_refs: tuple[str, ...] = ()
    outer_edge_refs: tuple[str, ...] = ()
    tie_edge_refs: tuple[str, ...] = ()
    leg_refs: tuple[str, ...] = ()
    alignment_refs: tuple[str, ...] = ()
    control_area_refs: tuple[str, ...] = ()
    vertical_policy_ref: str = ""
    triangulation_method: str = "not_assigned"
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSurfaceZoneResult(ResultModelBase):
    """Source-driven surface-zone handoff before intersection triangulation."""

    surface_zone_result_id: str = "intersection-surface-zones:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    zone_count: int = 0
    design_zone_count: int = 0
    pavement_zone_count: int = 0
    main_pavement_zone_count: int = 0
    side_pavement_zone_count: int = 0
    central_pavement_zone_count: int = 0
    curb_return_zone_count: int = 0
    slope_zone_count: int = 0
    slope_zone_ready_count: int = 0
    slope_zone_warning_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    zone_rows: list[IntersectionSurfaceZoneRow] = field(default_factory=list)
