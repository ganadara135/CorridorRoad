"""Intersection tie-slope result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionTieSlopeRow:
    """One source-owned side-slope tie between road Applied Sections and an intersection."""

    tie_slope_id: str
    intersection_id: str
    alignment_ref: str
    road_role: str
    side: str
    gap_role: str = ""
    leg_ref: str = ""
    control_area_ref: str = ""
    region_start_sta: float = 0.0
    region_end_sta: float = 0.0
    intersection_start_sta: float = 0.0
    intersection_end_sta: float = 0.0
    transition_outer_sta: float = 0.0
    transition_inner_sta: float = 0.0
    transition_window_start_sta: float = 0.0
    transition_window_end_sta: float = 0.0
    transition_span_length: float = 0.0
    transition_span_role: str = ""
    transition_window_kind: str = ""
    road_outer_edge_xyz: tuple[tuple[float, float, float], ...] = ()
    intersection_outer_edge_xyz: tuple[tuple[float, float, float], ...] = ()
    inner_boundary_points_xyz: tuple[tuple[float, float, float], ...] = ()
    outer_applied_section_points_xyz: tuple[tuple[float, float, float], ...] = ()
    inner_intersection_edge_xyz: tuple[tuple[float, float, float], ...] = ()
    outer_applied_section_edge_xyz: tuple[tuple[float, float, float], ...] = ()
    start_cap_edge_xyz: tuple[tuple[float, float, float], ...] = ()
    end_cap_edge_xyz: tuple[tuple[float, float, float], ...] = ()
    loop_points_xyz: tuple[tuple[float, float, float], ...] = ()
    loop_area_xy: float = 0.0
    source_applied_section_refs: tuple[str, ...] = ()
    last_applied_section_refs: tuple[str, ...] = ()
    source_intersection_boundary_ref: str = ""
    source_control_area_cap_refs: tuple[str, ...] = ()
    source_slope_face_boundary_ref: str = ""
    matched_intersection_contact_refs: tuple[str, ...] = ()
    intersection_contact_status: str = "not_evaluated"
    shared_breakline_refs: tuple[str, ...] = ()
    inner_breakline_ref: str = ""
    outer_breakline_ref: str = ""
    start_cap_breakline_ref: str = ""
    end_cap_breakline_ref: str = ""
    consumer_surface_ref: str = "intersection_tie_slope"
    closed_xy: bool = False
    point_count: int = 0
    surface_generation_status: str = "not_ready"
    status: str = "candidate"
    diagnostics: tuple[str, ...] = ()
    recommended_action: str = ""
    notes: str = ""


@dataclass
class IntersectionTieSlopeResult(ResultModelBase):
    """Dedicated contract for connection slopes around an intersection."""

    tie_slope_result_id: str = "intersection-tie-slope:main"
    intersection_id: str = ""
    status: str = "not_evaluated"
    tie_slope_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    tie_slope_rows: list[IntersectionTieSlopeRow] = field(default_factory=list)
