"""Intersection slope-face loop result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionSlopeFaceLoopRow:
    """One closed intersection Slope Face responsibility loop before triangulation."""

    loop_id: str
    intersection_id: str
    loop_family: str
    alignment_ref: str = ""
    leg_ref: str = ""
    side: str = ""
    inner_edge_refs: tuple[str, ...] = ()
    outer_edge_refs: tuple[str, ...] = ()
    tie_edge_refs: tuple[str, ...] = ()
    boundary_edge_refs: tuple[str, ...] = ()
    loop_points_xyz: tuple[tuple[float, float, float], ...] = ()
    source_applied_section_refs: tuple[str, ...] = ()
    source_edge_network_refs: tuple[str, ...] = ()
    source_edge_network_status: str = ""
    source_surface_zone_refs: tuple[str, ...] = ()
    source_surface_zone_status: str = ""
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    source_lineage_status: str = "accepted"
    closed_xy: bool = False
    self_crossing: bool = False
    overlaps_intersection_surface: bool = False
    point_count: int = 0
    status: str = "candidate"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSlopeFaceLoopResult(ResultModelBase):
    """Topology-first handoff for intersection-owned Slope Face loop generation."""

    loop_result_id: str = "intersection-slope-face-loops:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    loop_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    primary_outside_loop_count: int = 0
    secondary_outside_loop_count: int = 0
    curb_return_loop_count: int = 0
    corner_gap_loop_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    loop_rows: list[IntersectionSlopeFaceLoopRow] = field(default_factory=list)
