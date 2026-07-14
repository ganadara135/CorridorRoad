"""Typed Intersection patch shape-quality evaluation result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntersectionPatchShapeQualityResult:
    status: str
    triangulation_mode: str
    bbox_x: float = 0.0
    bbox_y: float = 0.0
    bbox_aspect_ratio: float = 0.0
    triangle_min_quality: float = 0.0
    skinny_triangle_count: int = 0
    evaluated_triangle_count: int = 0
    missing_vertex_triangle_count: int = 0
    skinny_threshold: float = 0.08
    diagnostic_rows: tuple[str, ...] = ()
