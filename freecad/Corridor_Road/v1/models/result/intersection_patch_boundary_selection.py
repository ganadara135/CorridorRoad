"""Typed Intersection patch boundary selection result."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINVertex


@dataclass(frozen=True)
class IntersectionPatchBoundarySelectionResult:
    status: str
    boundary_source: str
    vertex_rows: tuple[TINVertex, ...] = ()
    patch_boundary_point_count: int = 0
    patch_boundary_source_segment_count: int = 0
    patch_boundary_closed: bool = False
    patch_boundary_diagnostic_count: int = 0
    patch_boundary_polygon_area: float = 0.0
    patch_boundary_self_crossing: bool = False
    patch_boundary_ring_count: int = 0
    patch_boundary_hole_ring_count: int = 0
    patch_boundary_island_ring_count: int = 0
    boundary_loop_point_count: int = 0
    boundary_loop_segment_count: int = 0
    boundary_loop_source: str = ""
    fallback_used: bool = False
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
