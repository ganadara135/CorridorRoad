"""Intersection ordered patch boundary result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionPatchBoundaryPointRow:
    """One ordered point on a refined intersection patch boundary polygon."""

    boundary_point_id: str
    intersection_id: str
    order_index: int
    x: float
    y: float
    z: float
    source_segment_ref: str = ""
    source_kind: str = ""
    ring_id: str = "outer"
    ring_role: str = "outer"
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionPatchBoundaryResult(ResultModelBase):
    """Ordered boundary polygon candidate for an intersection surface patch."""

    patch_boundary_result_id: str = "intersection-patch-boundary:build-parametric"
    intersection_id: str = ""
    boundary_mode: str = "ordered_boundary"
    status: str = "not_evaluated"
    boundary_point_count: int = 0
    source_segment_count: int = 0
    ring_count: int = 1
    outer_ring_count: int = 1
    hole_ring_count: int = 0
    island_ring_count: int = 0
    closed: bool = False
    polygon_area: float = 0.0
    self_crossing: bool = False
    diagnostic_rows: list[str] = field(default_factory=list)
    point_rows: list[IntersectionPatchBoundaryPointRow] = field(default_factory=list)
