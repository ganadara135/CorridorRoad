"""Intersection boundary segment result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionBoundarySegmentRow:
    """One ordered boundary candidate segment for a refined intersection patch."""

    boundary_segment_id: str
    intersection_id: str
    segment_kind: str
    segment_role: str = ""
    source_ref: str = ""
    alignment_ref: str = ""
    side: str = ""
    start_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    center_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 0.0
    chord_points_xyz: tuple[tuple[float, float, float], ...] = ()
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionBoundarySegmentResult(ResultModelBase):
    """Rebuildable result contract for refined intersection patch boundary candidates."""

    boundary_segment_result_id: str = "intersection-boundary-segments:build-parametric"
    intersection_id: str = ""
    boundary_mode: str = "curb_return_boundary"
    status: str = "not_evaluated"
    segment_count: int = 0
    tie_in_segment_count: int = 0
    arc_segment_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    segment_rows: list[IntersectionBoundarySegmentRow] = field(default_factory=list)
