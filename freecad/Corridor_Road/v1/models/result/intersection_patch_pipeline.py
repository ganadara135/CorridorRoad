"""Typed non-roundabout Intersection patch pipeline result."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINSurface


@dataclass(frozen=True)
class IntersectionPatchPipelineResult:
    status: str
    surface_id: str
    intersection_id: str
    tin_surface: TINSurface | None = None
    boundary_selection: object | None = None
    center_vertex: object | None = None
    drainage_review: object | None = None
    triangulation: object | None = None
    constraint_build: object | None = None
    shape_quality: object | None = None
    assembly: object | None = None
    completed_stages: tuple[str, ...] = ()
    failed_stage: str = ""
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
