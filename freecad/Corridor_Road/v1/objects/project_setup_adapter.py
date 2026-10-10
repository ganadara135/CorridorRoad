"""Project Setup persistence for CorridorRoad v1.

Reads and writes the Project Setup properties of the CorridorRoadProject object. The property
names belong to `objects/obj_project.ensure_project_properties`, which creates any that an older
document lacks; this adapter adds none.
"""

from __future__ import annotations

from ...objects.obj_project import ensure_project_properties
from ...objects.unit_policy import resolve_project_unit_settings
from ..services.editing.project_setup_service import (
    COORDINATE_WORKFLOWS,
    DEFAULT_TIN_MAX_TRIANGLES,
    MIN_TIN_MAX_TRIANGLES,
    ProjectSetupDraft,
    recommended_coordinate_workflow,
)

# Draft field -> Project property. Units come from the unit policy resolver instead, so a stored
# value the policy does not know reads back as its default.
_PROPERTY_BY_FIELD = {
    "design_standard": "DesignStandard",
    "linear_unit_display": "LinearUnitDisplay",
    "linear_unit_import": "LinearUnitImportDefault",
    "linear_unit_export": "LinearUnitExportDefault",
    "custom_linear_unit_scale": "CustomLinearUnitScale",
    "tin_max_triangles": "TINConversionMaxTriangles",
    "crs_epsg": "CRSEPSG",
    "coordinate_workflow": "CoordinateWorkflow",
    "auto_apply_coordinate_recommendations": "AutoApplyCoordinateRecommendations",
    "horizontal_datum": "HorizontalDatum",
    "vertical_datum": "VerticalDatum",
    "project_origin_e": "ProjectOriginE",
    "project_origin_n": "ProjectOriginN",
    "project_origin_z": "ProjectOriginZ",
    "local_origin_x": "LocalOriginX",
    "local_origin_y": "LocalOriginY",
    "local_origin_z": "LocalOriginZ",
    "north_rotation_deg": "NorthRotationDeg",
    "coord_setup_locked": "CoordSetupLocked",
    "coord_setup_status": "CoordSetupStatus",
}


def project_setup_draft_from_project(project) -> ProjectSetupDraft:
    """Read the stored Project Setup of one CorridorRoadProject.

    Read only: a property an older document lacks reads as its default. (ensure_project_properties
    re-assigns the unit properties on every call, which would mark the project touched.)
    """

    units = resolve_project_unit_settings(project)
    crs_epsg = str(getattr(project, "CRSEPSG", "") or "")
    workflow = str(getattr(project, "CoordinateWorkflow", "") or "").strip()
    if workflow not in COORDINATE_WORKFLOWS:
        workflow = recommended_coordinate_workflow(crs_epsg)
    return ProjectSetupDraft(
        design_standard=str(getattr(project, "DesignStandard", "") or ""),
        linear_unit_display=str(units.get("display", "m")),
        linear_unit_import=str(units.get("import", "m")),
        linear_unit_export=str(units.get("export", "m")),
        custom_linear_unit_scale=float(units.get("custom_scale", 1.0)),
        tin_max_triangles=max(
            MIN_TIN_MAX_TRIANGLES,
            int(getattr(project, "TINConversionMaxTriangles", DEFAULT_TIN_MAX_TRIANGLES) or DEFAULT_TIN_MAX_TRIANGLES),
        ),
        crs_epsg=crs_epsg,
        coordinate_workflow=workflow,
        auto_apply_coordinate_recommendations=bool(getattr(project, "AutoApplyCoordinateRecommendations", True)),
        horizontal_datum=str(getattr(project, "HorizontalDatum", "") or ""),
        vertical_datum=str(getattr(project, "VerticalDatum", "") or ""),
        project_origin_e=float(getattr(project, "ProjectOriginE", 0.0)),
        project_origin_n=float(getattr(project, "ProjectOriginN", 0.0)),
        project_origin_z=float(getattr(project, "ProjectOriginZ", 0.0)),
        local_origin_x=float(getattr(project, "LocalOriginX", 0.0)),
        local_origin_y=float(getattr(project, "LocalOriginY", 0.0)),
        local_origin_z=float(getattr(project, "LocalOriginZ", 0.0)),
        north_rotation_deg=float(getattr(project, "NorthRotationDeg", 0.0)),
        coord_setup_locked=bool(getattr(project, "CoordSetupLocked", False)),
        coord_setup_status=str(getattr(project, "CoordSetupStatus", "Uninitialized") or "Uninitialized"),
    )


def write_project_setup(project, draft: ProjectSetupDraft) -> None:
    """Store a normalized draft on the Project object and mark the Project touched.

    No recompute: the readers of these properties (import/export unit and coordinate policy, TIN
    preview limits, Alignment criteria) read them when they run, and no FreeCAD object computes
    geometry from them.
    """

    ensure_project_properties(project)
    for field_name, property_name in _PROPERTY_BY_FIELD.items():
        setattr(project, property_name, getattr(draft, field_name))
    project.touch()


__all__ = ["project_setup_draft_from_project", "write_project_setup"]
