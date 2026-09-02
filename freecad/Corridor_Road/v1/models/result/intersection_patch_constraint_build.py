"""Typed Intersection patch shared-breakline constraint build result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntersectionPatchConstraintBuildResult:
    status: str
    surface_id: str
    vertex_rows: tuple[object, ...] = ()
    triangle_rows: tuple[object, ...] = ()
    mode: str = "none"
    segment_count: int = 0
    edge_count: int = 0
    inserted_vertex_count: int = 0
    boundary_loop_segment_count: int = 0
    boundary_loop_edge_count: int = 0
    boundary_loop_refs: tuple[str, ...] = ()
    boundary_loop_role_counts: tuple[tuple[str, int], ...] = ()
    boundary_loop_role_summary: str = ""
    snap_count: int = 0
    snap_max_distance: float = 0.0
    snap_diagnostic_rows: tuple[str, ...] = ()
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
