"""Intersection slope-face cell result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionSlopeFaceCellRow:
    """One source-owned slope-face cell around an intersection."""

    cell_id: str
    intersection_id: str
    cell_role: str
    alignment_ref: str = ""
    leg_ref: str = ""
    side: str = ""
    inner_breakline_ref: str = ""
    outer_breakline_ref: str = ""
    left_breakline_ref: str = ""
    right_breakline_ref: str = ""
    arc_breakline_ref: str = ""
    boundary_breakline_refs: tuple[str, ...] = ()
    loop_points_xyz: tuple[tuple[float, float, float], ...] = ()
    source_applied_section_refs: tuple[str, ...] = ()
    source_intersection_refs: tuple[str, ...] = ()
    source_shared_breakline_refs: tuple[str, ...] = ()
    consumer_surface_ref: str = "intersection_slope_face_surface"
    closed_xy: bool = False
    self_crossing: bool = False
    overlaps_intersection_surface: bool = False
    overlaps_curb_return_interior: bool = False
    point_count: int = 0
    surface_generation_status: str = "not_ready"
    status: str = "candidate"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSlopeFaceCellResult(ResultModelBase):
    """Cell-first handoff for dedicated intersection Slope Face Surface generation."""

    cell_result_id: str = "intersection-slope-face-cells:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    cell_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    open_cell_count: int = 0
    missing_edge_count: int = 0
    shared_breakline_mismatch_count: int = 0
    generated_triangle_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    cell_rows: list[IntersectionSlopeFaceCellRow] = field(default_factory=list)
