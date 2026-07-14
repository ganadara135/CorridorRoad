"""Typed Intersection surface patch build result for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINSurface


@dataclass(frozen=True)
class IntersectionSurfacePatchBuildResult:
    """Normalized result of one Intersection surface patch build attempt."""

    status: str
    surface_id: str
    intersection_id: str
    tin_surface: TINSurface | None = None
    boundary_source: str = ""
    triangulation_mode: str = ""
    vertex_count: int = 0
    triangle_count: int = 0
    quality_row_count: int = 0
    fallback_used: bool = False
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
