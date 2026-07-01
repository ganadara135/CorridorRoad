"""Intersection boundary-loop result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionBoundarySegmentRow:
    """One source-derived segment on an authoritative intersection boundary loop."""

    segment_id: str
    intersection_id: str
    loop_ref: str
    segment_role: str
    from_point_ref: str
    to_point_ref: str
    from_xyz: tuple[float, float, float]
    to_xyz: tuple[float, float, float]
    source_refs: tuple[str, ...] = ()
    expected_consumers: tuple[str, ...] = ()
    shared_breakline_ref: str = ""
    graph_edge_ref: str = ""
    source_status: str = "accepted"
    diagnostics: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class IntersectionBoundaryLoopRow:
    """One closed outer intersection boundary before surface generation."""

    loop_id: str
    intersection_id: str
    loop_role: str
    status: str = "candidate"
    closed: bool = False
    source_status: str = "accepted"
    point_count: int = 0
    segment_count: int = 0
    area_xy: float = 0.0
    bbox_xy: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    source_refs: tuple[str, ...] = ()
    segment_refs: tuple[str, ...] = ()
    consumer_roles: tuple[str, ...] = ()
    loop_points_xyz: tuple[tuple[float, float, float], ...] = ()
    diagnostics: tuple[str, ...] = ()
    recommended_action: str = ""
    notes: str = ""


@dataclass
class IntersectionBoundaryLoopResult(ResultModelBase):
    """Authoritative outer intersection boundary loop for shared surface ownership."""

    boundary_loop_result_id: str = "intersection-boundary-loops:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    loop_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    segment_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    loop_rows: list[IntersectionBoundaryLoopRow] = field(default_factory=list)
    segment_rows: list[IntersectionBoundarySegmentRow] = field(default_factory=list)
