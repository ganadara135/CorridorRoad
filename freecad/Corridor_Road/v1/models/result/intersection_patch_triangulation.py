"""Typed non-roundabout Intersection patch triangulation selection result."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINTriangle, TINVertex


@dataclass(frozen=True)
class IntersectionPatchTriangulationResult:
    """Normalized result of selecting and running one patch triangulation path."""

    status: str
    selection_path: str
    vertex_rows: tuple[TINVertex, ...] = ()
    triangle_rows: tuple[TINTriangle, ...] = ()
    degenerate_count: int = 0
    max_edge_length: float = 0.0
    long_edge_count: int = 0
    long_edge_factor: float = 2.5
    long_edge_limit: float = 0.0
    max_boundary_edge_length_policy: float = 0.0
    boundary_strategy: str = "ordered_polygon"
    structured_strip_count: int = 0
    curb_return_surface_edge_count: int = 0
    curb_return_arc_count: int = 0
    curb_return_arc_sample_count: int = 0
    curb_return_arc_segment_count: int = 0
    edge_blend_face_count: int = 0
    boundary_role_summary: str = ""
    pavement_tie_in_edge_count: int = 0
    stem_tie_in_edge_count: int = 0
    overlap_cut_edge_count: int = 0
    curb_return_edge_count: int = 0
    fallback_used: bool = False
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
