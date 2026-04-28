"""Corridor surface builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.surface_model import (
    SurfaceBuildRelation,
    SurfaceModel,
    SurfaceRow,
)


@dataclass(frozen=True)
class CorridorSurfaceBuildRequest:
    """Input bundle used to build minimal corridor-derived surfaces."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    surface_model_id: str


class CorridorSurfaceService:
    """Build minimal corridor-derived surface families from corridor results."""

    def build(self, request: CorridorSurfaceBuildRequest) -> SurfaceModel:
        """Build a minimal grouped surface result family for a corridor."""

        if request.applied_section_set.station_rows:
            status = "ready"
        else:
            status = "empty"

        design_surface_id = f"{request.corridor.corridor_id}:design"
        subgrade_surface_id = f"{request.corridor.corridor_id}:subgrade"
        daylight_surface_id = f"{request.corridor.corridor_id}:daylight"
        drainage_surface_id = f"{request.corridor.corridor_id}:drainage"

        surface_rows = [
            SurfaceRow(
                surface_id=design_surface_id,
                surface_kind="design_surface",
                tin_ref=f"{design_surface_id}:tin",
                status=status,
            ),
            SurfaceRow(
                surface_id=subgrade_surface_id,
                surface_kind="subgrade_surface",
                tin_ref=f"{subgrade_surface_id}:tin",
                status=status,
                parent_surface_ref=design_surface_id,
            ),
            SurfaceRow(
                surface_id=daylight_surface_id,
                surface_kind="daylight_surface",
                tin_ref=f"{daylight_surface_id}:tin",
                status=status,
                parent_surface_ref=design_surface_id,
            ),
        ]
        if _has_point_role(request.applied_section_set, "ditch_surface"):
            surface_rows.append(
                SurfaceRow(
                    surface_id=drainage_surface_id,
                    surface_kind="drainage_surface",
                    tin_ref=f"{drainage_surface_id}:tin",
                    status=status,
                    parent_surface_ref=design_surface_id,
                )
            )

        build_relation_rows = [
            SurfaceBuildRelation(
                build_relation_id=f"{request.surface_model_id}:design-build",
                surface_ref=design_surface_id,
                relation_kind="corridor_build",
                input_refs=[
                    request.corridor.corridor_id,
                    request.applied_section_set.applied_section_set_id,
                ],
                operation_summary="Built from applied section set skeleton.",
            ),
            SurfaceBuildRelation(
                build_relation_id=f"{request.surface_model_id}:subgrade-build",
                surface_ref=subgrade_surface_id,
                relation_kind="corridor_build",
                input_refs=[design_surface_id],
                operation_summary="Derived as child surface of design surface skeleton.",
            ),
            SurfaceBuildRelation(
                build_relation_id=f"{request.surface_model_id}:daylight-build",
                surface_ref=daylight_surface_id,
                relation_kind="corridor_build",
                input_refs=[design_surface_id],
                operation_summary="Derived as child surface of design surface skeleton.",
            ),
        ]
        if _has_point_role(request.applied_section_set, "ditch_surface"):
            build_relation_rows.append(
                SurfaceBuildRelation(
                    build_relation_id=f"{request.surface_model_id}:drainage-build",
                    surface_ref=drainage_surface_id,
                    relation_kind="corridor_build",
                    input_refs=[
                        request.corridor.corridor_id,
                        request.applied_section_set.applied_section_set_id,
                    ],
                    operation_summary="Built from AppliedSection ditch_surface point rows.",
                )
            )

        return SurfaceModel(
            schema_version=1,
            project_id=request.project_id,
            surface_model_id=request.surface_model_id,
            corridor_id=request.corridor.corridor_id,
            label=f"Surfaces for {request.corridor.corridor_id}",
            source_refs=[
                request.corridor.corridor_id,
                request.applied_section_set.applied_section_set_id,
            ],
            surface_rows=surface_rows,
            build_relation_rows=build_relation_rows,
            comparison_rows=[],
        )


def _has_point_role(applied_section_set: AppliedSectionSet, point_role: str) -> bool:
    for section in list(getattr(applied_section_set, "sections", []) or []):
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") == point_role:
                return True
    return False
