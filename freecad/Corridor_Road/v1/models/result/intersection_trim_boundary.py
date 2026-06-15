"""Intersection trim-boundary result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionTrimBoundaryPair:
    """Candidate patch/road edge pair for future intersection clip/trim."""

    boundary_pair_id: str
    patch_output_ref: str
    road_output_ref: str
    distance_xy: float = 0.0
    patch_segment_xyz: tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    road_segment_xyz: tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionTrimBoundaryResult(ResultModelBase):
    """Rebuildable result contract for intersection patch/road trim candidates."""

    trim_boundary_result_id: str = "intersection-trim-boundaries:watertight"
    tolerance: float = 0.05
    application_status: str = "not_evaluated"
    ready_pair_count: int = 0
    blocked_pair_count: int = 0
    boundary_pair_rows: list[IntersectionTrimBoundaryPair] = field(default_factory=list)
