"""Typed ordinary-road corridor surface geometry orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.tin_surface import TINSurface
from .corridor_surface_geometry_service import (
    CorridorDesignSurfaceGeometryRequest,
    CorridorSurfaceGeometryService,
)


@dataclass(frozen=True)
class CorridorSurfaceGeometryBuildRequest:
    """Select one ordinary-road surface role for a normalized geometry request."""

    surface_role: str
    geometry_request: CorridorDesignSurfaceGeometryRequest


@dataclass(frozen=True)
class CorridorSurfaceGeometryBuildResult:
    """Typed result for one ordinary-road surface geometry build decision."""

    surface_role: str
    surface_kind: str
    surface_id: str
    status: str
    tin_surface: TINSurface | None = None
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""


class CorridorSurfaceOrchestrationService:
    """Route normalized ordinary-road surface requests without UI or documents."""

    def __init__(
        self,
        geometry_service: CorridorSurfaceGeometryService | None = None,
    ) -> None:
        self.geometry_service = geometry_service or CorridorSurfaceGeometryService()

    def build(
        self,
        request: CorridorSurfaceGeometryBuildRequest,
    ) -> CorridorSurfaceGeometryBuildResult:
        """Build one surface role and normalize success or failure diagnostics."""

        role = _normalized_surface_role(request.surface_role)
        surface_kind = _surface_kind_for_role(role)
        surface_id = str(getattr(request.geometry_request, "surface_id", "") or "")
        builder = self._builder_for_role(role)
        if builder is None:
            raw_role = str(request.surface_role or "").strip() or "(empty)"
            return CorridorSurfaceGeometryBuildResult(
                surface_role=role,
                surface_kind=surface_kind,
                surface_id=surface_id,
                status="unsupported",
                diagnostic_rows=(f"unsupported_surface_role:{raw_role}",),
                error_message=f"Unsupported corridor surface role: {raw_role}",
            )
        try:
            surface = builder(request.geometry_request)
        except Exception as exc:
            return CorridorSurfaceGeometryBuildResult(
                surface_role=role,
                surface_kind=surface_kind,
                surface_id=surface_id,
                status="error",
                diagnostic_rows=(
                    f"surface_build_failed:{role}:{type(exc).__name__}:{exc}",
                ),
                error_message=str(exc),
            )
        return CorridorSurfaceGeometryBuildResult(
            surface_role=role,
            surface_kind=surface_kind,
            surface_id=surface_id,
            status="ready",
            tin_surface=surface,
        )

    def _builder_for_role(self, role: str):
        return {
            "design": self.geometry_service.build_design_surface,
            "subgrade": self.geometry_service.build_subgrade_surface,
            "daylight": self.geometry_service.build_daylight_surface,
            "drainage": self.geometry_service.build_drainage_surface,
        }.get(role)


def _normalized_surface_role(value: object) -> str:
    role = str(value or "").strip().lower()
    aliases = {
        "design_surface": "design",
        "fg_surface": "design",
        "subgrade_surface": "subgrade",
        "daylight_surface": "daylight",
        "slope_face_surface": "daylight",
        "drainage_surface": "drainage",
    }
    return aliases.get(role, role)


def _surface_kind_for_role(role: str) -> str:
    return {
        "design": "design_surface",
        "subgrade": "subgrade_surface",
        "daylight": "daylight_surface",
        "drainage": "drainage_surface",
    }.get(role, "")
