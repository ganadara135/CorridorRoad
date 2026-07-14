"""Typed non-roundabout Intersection patch preparation pipeline result."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINSurface


@dataclass(frozen=True)
class IntersectionPatchPreparationPipelineResult:
    status: str
    surface_id: str
    intersection_id: str
    tin_surface: TINSurface | None = None
    prepared_input: object | None = None
    grading_result: object | None = None
    boundary_context: object | None = None
    patch_pipeline: object | None = None
    completed_stages: tuple[str, ...] = ()
    failed_stage: str = ""
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
