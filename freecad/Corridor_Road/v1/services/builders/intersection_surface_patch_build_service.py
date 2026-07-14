"""Typed orchestration boundary for Intersection surface patch builds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ...models.result.intersection_surface_patch_build import (
    IntersectionSurfacePatchBuildResult,
)


IntersectionSurfaceTinBuilder = Callable[..., object]


@dataclass(frozen=True)
class IntersectionSurfacePatchBuildRequest:
    """Source/result inputs required by one Intersection surface patch build."""

    project_id: str
    corridor_model: object
    applied_section_set: object
    prerequisite: object
    intersection_model: object | None
    surface_id: str


class IntersectionSurfacePatchBuildService:
    """Normalize Intersection patch build success, fallback, and failure results."""

    def __init__(self, tin_builder: IntersectionSurfaceTinBuilder | None = None) -> None:
        self.tin_builder = tin_builder

    def build(
        self,
        request: IntersectionSurfacePatchBuildRequest,
    ) -> IntersectionSurfacePatchBuildResult:
        intersection_id = str(
            getattr(request.prerequisite, "intersection_id", "") or ""
        )
        if self.tin_builder is None:
            message = "Intersection surface patch TIN builder is not configured."
            return IntersectionSurfacePatchBuildResult(
                status="unsupported",
                surface_id=request.surface_id,
                intersection_id=intersection_id,
                diagnostic_rows=("intersection_surface_patch_builder_missing",),
                error_message=message,
            )
        try:
            surface = self.tin_builder(
                project_id=request.project_id,
                corridor_model=request.corridor_model,
                applied_section_set=request.applied_section_set,
                prerequisite=request.prerequisite,
                intersection_model=request.intersection_model,
                surface_id=request.surface_id,
            )
        except Exception as exc:
            return IntersectionSurfacePatchBuildResult(
                status="error",
                surface_id=request.surface_id,
                intersection_id=intersection_id,
                diagnostic_rows=(
                    "intersection_surface_patch_build_failed:"
                    f"{type(exc).__name__}:{exc}",
                ),
                error_message=str(exc),
            )
        boundary_source = _quality_text(surface, "patch_boundary_source")
        triangulation_mode = _quality_text(surface, "patch_triangulation_mode")
        fallback_used = boundary_source == "convex_hull_fallback"
        diagnostics = (
            ("intersection_patch_boundary_fallback:convex_hull_fallback",)
            if fallback_used
            else ()
        )
        return IntersectionSurfacePatchBuildResult(
            status="ready",
            surface_id=request.surface_id,
            intersection_id=intersection_id,
            tin_surface=surface,
            boundary_source=boundary_source,
            triangulation_mode=triangulation_mode,
            vertex_count=len(list(getattr(surface, "vertex_rows", []) or [])),
            triangle_count=len(list(getattr(surface, "triangle_rows", []) or [])),
            quality_row_count=len(list(getattr(surface, "quality_rows", []) or [])),
            fallback_used=fallback_used,
            diagnostic_rows=diagnostics,
        )


def _quality_text(surface: object, kind: str) -> str:
    for row in list(getattr(surface, "quality_rows", []) or []):
        if str(getattr(row, "kind", "") or "") == kind:
            return str(getattr(row, "value", "") or "")
    return ""
