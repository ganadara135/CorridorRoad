"""Intersection slope-face boundary result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionSlopeFaceBoundaryRow:
    """One boundary strip candidate between an intersection surface and Applied Sections."""

    boundary_id: str
    intersection_id: str
    alignment_ref: str
    side: str
    inner_points_xyz: tuple[tuple[float, float, float], ...] = ()
    outer_points_xyz: tuple[tuple[float, float, float], ...] = ()
    start_tie_edge_xyz: tuple[tuple[float, float, float], tuple[float, float, float]] | tuple = ()
    end_tie_edge_xyz: tuple[tuple[float, float, float], tuple[float, float, float]] | tuple = ()
    source_applied_section_refs: tuple[str, ...] = ()
    source_intersection_surface_ref: str = ""
    status: str = "candidate"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSlopeFaceBoundaryResult(ResultModelBase):
    """Boundary-first handoff for intersection-owned Slope Face Surface strips."""

    boundary_result_id: str = "intersection-slope-face-boundary:main"
    intersection_id: str = ""
    status: str = "not_evaluated"
    boundary_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    boundary_rows: list[IntersectionSlopeFaceBoundaryRow] = field(default_factory=list)
