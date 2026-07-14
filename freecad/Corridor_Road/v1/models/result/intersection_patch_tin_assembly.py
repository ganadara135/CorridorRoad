"""Typed final non-roundabout Intersection patch TIN assembly result."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINSurface


@dataclass(frozen=True)
class IntersectionPatchTinAssemblyResult:
    status: str
    surface_id: str
    intersection_id: str
    tin_surface: TINSurface | None = None
    quality_row_count: int = 0
    provenance_row_count: int = 0
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
