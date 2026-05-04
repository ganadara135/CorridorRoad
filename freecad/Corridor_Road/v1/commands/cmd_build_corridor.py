"""Build Corridor command helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.qt_compat import QtWidgets

from ...objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree, find_project
from ..exchange import export_exchange_package_to_ifc, export_exchange_package_to_json
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_corridor import create_or_update_v1_corridor_model_object, find_v1_corridor_model
from ..objects.obj_exchange_package import create_or_update_v1_exchange_package_object, find_v1_exchange_package
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..objects.obj_surface import create_or_update_v1_surface_model_object, find_v1_surface_model
from ..objects.obj_surface_transition import (
    create_or_update_v1_surface_transition_model_object,
    find_v1_surface_transition_model,
    to_surface_transition_model,
)
from ..models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ..services.builders import (
    CorridorDesignSurfaceGeometryRequest,
    CorridorModelBuildRequest,
    CorridorModelService,
    CorridorSurfaceBuildRequest,
    CorridorSurfaceGeometryService,
    CorridorSurfaceService,
    QuantityBuildRequest,
    QuantityBuildService,
    StructureSolidBuildRequest,
    StructureSolidOutputService,
    transition_augmented_applied_section_set,
)
from ..services.evaluation.surface_transition_validation_service import SurfaceTransitionValidationService
from ..services.mapping import ExchangeOutputMapper, ExchangePackageRequest, QuantityOutputMapper, SectionOutputMapper
from ..services.mapping.tin_mesh_preview_mapper import TINMeshPreviewMapper


@dataclass(frozen=True)
class StructureOutputPackageBuildResult:
    """Build Corridor handoff result for structure solids, quantities, and exchange payloads."""

    corridor_model: object
    structure_solid_output: object
    quantity_model: object
    quantity_output: object
    exchange_output: object
    section_outputs: list[object] = field(default_factory=list)


CORRIDOR_BUILD_REVIEW_OBJECTS = (
    ("centerline", "3D Centerline", "V1CorridorCenterline3DPreview"),
    ("design", "Design Surface", "V1CorridorDesignSurfacePreview"),
    ("subgrade", "Subgrade Surface", "V1CorridorSubgradeSurfacePreview"),
    ("daylight", "Slope Face Surface", "V1CorridorDaylightSurfacePreview"),
    ("drainage", "Drainage Surface", "V1CorridorDrainageSurfacePreview"),
)
CORRIDOR_BUILD_GUIDED_REVIEW_STEPS = (
    ("centerline", "1. Centerline", ("centerline",), "Check 3D centerline continuity and station ordering."),
    ("design", "2. Design Surface", ("centerline", "design"), "Check finished-grade surface continuity."),
    ("slope_issues", "3. Slope Face Issues", ("daylight",), "Check daylight tie-in fallbacks and EG hits."),
    ("drainage", "4. Drainage", ("centerline", "drainage"), "Check ditch/drainage surface handoff where available."),
)
BUILD_CORRIDOR_PANEL_MIN_WIDTH = 420
BUILD_CORRIDOR_PANEL_MAX_WIDTH = 560
REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD = 1.0
REGION_BOUNDARY_SUBGRADE_JUMP_THRESHOLD = 0.15
REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD = 1.0
REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD = 0.05
SURFACE_TRANSITION_DEFAULT_HALF_LENGTH = 5.0
REGION_SURFACE_DISPLAY_Z_OFFSET = 0.25
SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL = 2.5
SURFACE_TRANSITION_SPACING_PRESETS = (
    ("Dense 1.000 m", 1.0),
    ("Normal 2.500 m", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL),
    ("Sparse 5.000 m", 5.0),
    ("Custom", None),
)

CORRIDOR_BUILD_REVIEW_ROW_COLORS = {
    "ready": (220, 245, 224),
    "missing": (238, 238, 238),
    "empty": (255, 241, 205),
}
CORRIDOR_BUILD_REVIEW_TEXT_COLOR = (20, 20, 20)
CORRIDOR_CENTERLINE_PREVIEW_STYLE = {
    "shape_color": (0.00, 0.85, 1.00),
    "line_color": (0.00, 0.85, 1.00),
    "point_color": (0.00, 0.85, 1.00),
    "line_width": 5.0,
    "point_size": 6.0,
}


def document_has_v1_applied_sections(document=None) -> bool:
    """Return True when a document has a v1 AppliedSectionSet result."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    return find_v1_applied_section_set(doc) is not None


def build_document_corridor_model(document=None, *, project=None, corridor_id: str = "corridor:main"):
    """Build a CorridorModel result from the document's v1 AppliedSectionSet."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        raise RuntimeError("A v1 AppliedSectionSet is required before Build Corridor.")
    region_obj = find_v1_region_model(doc)
    return CorridorModelService().build(
        CorridorModelBuildRequest(
            project_id=_project_id(project or find_project(doc)),
            corridor_id=corridor_id,
            applied_section_set=applied_section_set,
            region_model_ref=str(getattr(region_obj, "RegionModelId", "") or ""),
        )
    )


def build_document_corridor_surface_model(
    document=None,
    *,
    project=None,
    corridor_model=None,
    surface_model_id: str = "surface:main",
):
    """Build the first corridor-derived SurfaceModel result from Applied Sections."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        raise RuntimeError("A v1 AppliedSectionSet is required before corridor surfaces.")
    corridor = corridor_model or build_document_corridor_model(doc, project=project)
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    return CorridorSurfaceService().build(
        CorridorSurfaceBuildRequest(
            project_id=_project_id(project or find_project(doc)),
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_model_id=surface_model_id,
            surface_transition_model=transition_model,
        )
    )


def build_document_structure_output_package(
    document=None,
    *,
    project=None,
    corridor_model=None,
    structure_solid_output_id: str = "structure-solids:main",
    quantity_model_id: str = "quantities:structures",
    exchange_output_id: str = "exchange:structure-solids",
    exchange_format: str = "ifc",
    package_kind: str = "structure_geometry",
) -> StructureOutputPackageBuildResult:
    """Build structure solids, derived quantities, and one normalized exchange package."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        raise RuntimeError("A v1 AppliedSectionSet is required before structure outputs.")
    structure_model = to_structure_model(find_v1_structure_model(doc))
    if structure_model is None:
        raise RuntimeError("A v1 StructureModel is required before structure outputs.")

    prj = project or find_project(doc)
    project_id = _project_id(prj)
    corridor = corridor_model or build_document_corridor_model(doc, project=prj)
    structure_solid_output = StructureSolidOutputService().build(
        StructureSolidBuildRequest(
            project_id=project_id,
            corridor=corridor,
            structure_model=structure_model,
            applied_section_set=applied_section_set,
            structure_solid_output_id=structure_solid_output_id,
        )
    )
    quantity_model = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id=project_id,
            corridor=corridor,
            quantity_model_id=quantity_model_id,
            applied_section_set=applied_section_set,
            structure_solid_output=structure_solid_output,
            structure_model=structure_model,
        )
    )
    quantity_output = QuantityOutputMapper().map_quantity_model(quantity_model)
    section_outputs = [
        SectionOutputMapper().map_applied_section(section)
        for section in list(getattr(applied_section_set, "sections", []) or [])
    ]
    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id=project_id,
            exchange_output_id=exchange_output_id,
            format=exchange_format,
            package_kind=package_kind,
            outputs=[structure_solid_output, quantity_output, *section_outputs],
        )
    )
    return StructureOutputPackageBuildResult(
        corridor_model=corridor,
        structure_solid_output=structure_solid_output,
        quantity_model=quantity_model,
        quantity_output=quantity_output,
        exchange_output=exchange_output,
        section_outputs=section_outputs,
    )


def structure_output_package_summary(result: StructureOutputPackageBuildResult) -> dict[str, object]:
    """Return display-ready counts and ids for a built structure output package."""

    solid_rows = list(getattr(result.structure_solid_output, "solid_rows", []) or [])
    solid_segment_rows = list(getattr(result.structure_solid_output, "solid_segment_rows", []) or [])
    export_diagnostics = list(getattr(result.structure_solid_output, "diagnostic_rows", []) or [])
    quantity_fragments = list(getattr(result.quantity_model, "fragment_rows", []) or [])
    exchange_refs = list(getattr(result.exchange_output, "output_refs", []) or [])
    payload_metadata = getattr(result.exchange_output, "payload_metadata", {}) or {}
    active_structure_refs = sorted(
        {
            str(getattr(row, "structure_id", "") or "")
            for row in solid_rows
            if str(getattr(row, "structure_id", "") or "")
        }
    )
    return {
        "corridor_id": str(getattr(result.corridor_model, "corridor_id", "") or ""),
        "structure_solid_output_id": str(getattr(result.structure_solid_output, "structure_solid_output_id", "") or ""),
        "solid_count": len(solid_rows),
        "active_structure_refs": active_structure_refs,
        "active_structure_count": len(active_structure_refs),
        "solid_segment_count": len(solid_segment_rows),
        "export_readiness_status": _export_readiness_status(export_diagnostics),
        "export_diagnostic_count": len(export_diagnostics),
        "quantity_model_id": str(getattr(result.quantity_model, "quantity_model_id", "") or ""),
        "quantity_fragment_count": len(quantity_fragments),
        "section_output_count": len(list(getattr(result, "section_outputs", []) or [])),
        "source_context_count": int(payload_metadata.get("source_context_count", 0) or 0),
        "side_slope_source_context_count": int(payload_metadata.get("side_slope_source_context_count", 0) or 0),
        "bench_source_context_count": int(payload_metadata.get("bench_source_context_count", 0) or 0),
        "exchange_output_id": str(getattr(result.exchange_output, "exchange_output_id", "") or ""),
        "exchange_format": str(getattr(result.exchange_output, "format", "") or ""),
        "exchange_output_count": len(exchange_refs),
    }


def _export_readiness_status(diagnostics: list[object]) -> str:
    severities = {str(getattr(row, "severity", "") or "").strip().lower() for row in list(diagnostics or [])}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warning"
    return "ready"


def _notify_progress(progress_callback, value: int, text: str) -> None:
    if not callable(progress_callback):
        return
    try:
        progress_callback(value, text)
    except TypeError:
        try:
            progress_callback(value)
        except Exception:
            pass
    except Exception:
        pass


def apply_v1_structure_output_package(*, document=None, project=None, package_result=None):
    """Persist a built structure output package as a v1 ExchangePackage object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    if package_result is None:
        package_result = build_document_structure_output_package(doc, project=prj)
    obj = create_or_update_v1_exchange_package_object(
        document=doc,
        project=prj,
        package_result=package_result,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def export_document_structure_output_package_json(
    path: str,
    *,
    document=None,
    project=None,
    exchange_package=None,
) -> dict[str, object]:
    """Export the current persisted structure exchange package to JSON."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    package_obj = find_v1_exchange_package(doc, preferred_exchange_package=exchange_package)
    if package_obj is None:
        package_obj = apply_v1_structure_output_package(document=doc, project=project)
    return export_exchange_package_to_json(path, package_obj)


def export_document_structure_output_package_ifc(
    path: str,
    *,
    document=None,
    project=None,
    exchange_package=None,
) -> dict[str, object]:
    """Export the current persisted structure exchange package to IFC4 STEP."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    package_obj = find_v1_exchange_package(doc, preferred_exchange_package=exchange_package)
    if package_obj is None:
        package_obj = apply_v1_structure_output_package(document=doc, project=project)
    return export_exchange_package_to_ifc(path, package_obj)


def apply_v1_corridor_model(
    *,
    document=None,
    project=None,
    corridor_model=None,
    build_surfaces: bool = True,
    show_daylight_contact_markers: bool = True,
    supplemental_sampling_enabled: bool = True,
    progress_callback=None,
):
    """Persist a v1 CorridorModel result object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    _notify_progress(progress_callback, 40, "Preparing project tree...")
    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"
    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    if corridor_model is None:
        _notify_progress(progress_callback, 45, "Building CorridorModel...")
        corridor_model = build_document_corridor_model(doc, project=prj)
    surface_model = None
    if build_surfaces:
        _notify_progress(progress_callback, 50, "Building corridor surfaces...")
        surface_model = build_document_corridor_surface_model(doc, project=prj, corridor_model=corridor_model)
        corridor_model.surface_build_refs = [str(getattr(surface_model, "surface_model_id", "") or "surface:main")]
    _notify_progress(progress_callback, 65, "Writing CorridorModel object...")
    obj = create_or_update_v1_corridor_model_object(document=doc, project=prj, corridor_model=corridor_model)
    if surface_model is not None:
        _notify_progress(progress_callback, 70, "Writing SurfaceModel object...")
        create_or_update_v1_surface_model_object(document=doc, project=prj, surface_model=surface_model)
        _notify_progress(progress_callback, 74, "Creating centerline preview...")
        create_corridor_centerline_3d_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            applied_section_set_ref=str(getattr(corridor_model, "applied_section_set_ref", "") or ""),
        )
        _notify_progress(progress_callback, 78, "Creating design surface preview...")
        create_corridor_design_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        _notify_progress(progress_callback, 80, "Creating Region surface objects...")
        create_corridor_region_surface_previews(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        _notify_progress(progress_callback, 82, "Creating subgrade surface preview...")
        create_corridor_subgrade_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        _notify_progress(progress_callback, 86, "Creating slope face preview...")
        create_corridor_daylight_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            show_daylight_contact_markers=show_daylight_contact_markers,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        _notify_progress(progress_callback, 90, "Creating drainage preview...")
        create_corridor_drainage_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        _notify_progress(progress_callback, 92, "Creating transition span markers...")
        create_corridor_surface_transition_span_markers(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
    try:
        _notify_progress(progress_callback, 94, "Recomputing document...")
        doc.recompute()
    except Exception:
        pass
    return obj


def corridor_build_review_rows(document=None) -> list[dict[str, object]]:
    """Return display-ready Build Corridor result rows from document preview objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied_summary = corridor_applied_sections_review_summary(doc)
    rows: list[dict[str, object]] = []
    for role, title, object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        obj = doc.getObject(object_name) if doc is not None else None
        rows.append(
            _with_applied_section_review_summary(
                _corridor_build_review_row(role, title, object_name, obj),
                applied_summary,
            )
        )
    return rows


def corridor_slope_face_issue_rows(document=None) -> list[dict[str, str]]:
    """Return station-side slope-face issue rows from the corridor daylight preview."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    obj = doc.getObject("V1CorridorDaylightSurfacePreview") if doc is not None else None
    if obj is None:
        return []
    rows: list[dict[str, str]] = []
    for text in list(getattr(obj, "SlopeFaceIssueRows", []) or []):
        row = _parse_slope_face_issue_row_text(str(text or ""))
        if row:
            rows.append(row)
    if not rows:
        rows = _parse_slope_face_issue_summary_text(str(getattr(obj, "SlopeFaceIssueStations", "") or ""))
    return rows


def corridor_build_guided_review_steps(document=None) -> list[dict[str, object]]:
    """Return ordered guided-review rows for the Build Corridor panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    review_by_role = {str(row.get("role", "") or ""): row for row in corridor_build_review_rows(doc)}
    issue_count = len(corridor_slope_face_issue_rows(doc))
    rows: list[dict[str, object]] = []
    for step_id, title, roles, default_notes in CORRIDOR_BUILD_GUIDED_REVIEW_STEPS:
        if step_id == "slope_issues":
            daylight = review_by_role.get("daylight", {})
            base_status = str(daylight.get("status", "missing") or "missing")
            status = "warn" if base_status == "ready" and issue_count else base_status
            notes = f"{issue_count} slope-face issue(s) to review." if issue_count else "No slope-face issue rows."
            focus = "First issue marker" if issue_count else "Slope Face Surface"
        else:
            primary_role = str(list(roles)[-1] if roles else "")
            source = review_by_role.get(primary_role, {})
            status = str(source.get("status", "missing") or "missing")
            notes = default_notes if status == "ready" else str(source.get("notes", "") or "Not built yet.")
            focus = str(source.get("result", title) or title)
            if step_id == "drainage":
                drainage = corridor_drainage_review_summary(doc)
                status = str(drainage.get("status", status) or status)
                notes = str(drainage.get("notes", notes) or notes)
                focus = "Drainage Surface" if source.get("status") == "ready" else "Drainage Diagnostics"
        rows.append(
            {
                "step_id": step_id,
                "title": title,
                "roles": list(roles),
                "status": status,
                "focus": focus,
                "notes": notes,
            }
        )
    return rows


def corridor_drainage_review_rows(document=None) -> list[dict[str, object]]:
    """Return station-level drainage source diagnostics from Applied Sections."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return [
            {
                "station": "",
                "section_id": "",
                "status": "missing",
                "ditch_point_count": 0,
                "left_count": 0,
                "right_count": 0,
                "notes": "Applied Sections are required before drainage review.",
            }
        ]
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied, "sections", []) or [])
    }
    output: list[dict[str, object]] = []
    for row in sorted(list(getattr(applied, "station_rows", []) or []), key=lambda item: float(getattr(item, "station", 0.0) or 0.0)):
        section_id = str(getattr(row, "applied_section_id", "") or "")
        section = sections.get(section_id)
        station = float(getattr(row, "station", 0.0) or 0.0)
        if section is None:
            output.append(
                {
                    "station": station,
                    "section_id": section_id,
                    "status": "missing",
                    "ditch_point_count": 0,
                    "left_count": 0,
                    "right_count": 0,
                    "marker_object": _drainage_review_marker_name(len(output)),
                    "x": "",
                    "y": "",
                    "z": "",
                    "notes": "Applied section row is missing.",
                }
            )
            continue
        ditch_points = [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "") == "ditch_surface"
        ]
        left_count = sum(1 for point in ditch_points if _drainage_point_side(point) == "L")
        right_count = sum(1 for point in ditch_points if _drainage_point_side(point) == "R")
        if not ditch_points:
            status = "missing"
            notes = "No ditch_surface point rows from Assembly/Applied Sections."
        elif left_count and right_count:
            status = "ready"
            notes = "Left and right ditch surface points available."
        else:
            status = "warn"
            notes = "Only one side has ditch surface points."
        marker_point = _drainage_review_marker_point(section, ditch_points)
        output.append(
            {
                "station": station,
                "section_id": section_id,
                "status": status,
                "ditch_point_count": len(ditch_points),
                "left_count": left_count,
                "right_count": right_count,
                "marker_object": _drainage_review_marker_name(len(output)),
                "x": f"{marker_point[0]:.6f}",
                "y": f"{marker_point[1]:.6f}",
                "z": f"{marker_point[2]:.6f}",
                "notes": notes,
            }
        )
    if not output:
        return [
            {
                "station": "",
                "section_id": "",
                "status": "missing",
                "ditch_point_count": 0,
                "left_count": 0,
                "right_count": 0,
                "notes": "No Applied Section station rows.",
            }
        ]
    return output


def corridor_drainage_review_summary(document=None) -> dict[str, object]:
    """Return a compact drainage readiness summary for Build Corridor review."""

    rows = corridor_drainage_review_rows(document)
    real_rows = [row for row in rows if row.get("station") != ""]
    ready = sum(1 for row in real_rows if row.get("status") == "ready")
    warn = sum(1 for row in real_rows if row.get("status") == "warn")
    missing = sum(1 for row in real_rows if row.get("status") == "missing")
    point_count = sum(int(row.get("ditch_point_count", 0) or 0) for row in real_rows)
    if not real_rows:
        status = "missing"
        notes = str(rows[0].get("notes", "No drainage rows.") if rows else "No drainage rows.")
    elif missing:
        status = "missing"
        notes = f"{missing} station(s) without ditch_surface points."
    elif warn:
        status = "warn"
        notes = f"{warn} station(s) have one-sided ditch points."
    else:
        status = "ready"
        notes = "Drainage source points available at all reviewed stations."
    return {
        "status": status,
        "station_count": len(real_rows),
        "ready_count": ready,
        "warn_count": warn,
        "missing_count": missing,
        "ditch_point_count": point_count,
        "notes": notes,
    }


def corridor_region_boundary_rows(document=None) -> list[dict[str, object]]:
    """Return Build Corridor Region rows with boundary continuity diagnostics."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return [
            {
                "region_id": "",
                "station_start": "",
                "station_end": "",
                "assembly": "",
                "structure": "",
                "drainage": "",
                "surface_status": "missing",
                "boundary_status": "missing",
                "diagnostics": "Applied Sections are required before Region boundary review.",
            }
        ]
    sections = _station_ordered_applied_sections(applied)
    if not sections:
        return [
            {
                "region_id": "",
                "station_start": "",
                "station_end": "",
                "assembly": "",
                "structure": "",
                "drainage": "",
                "surface_status": "missing",
                "boundary_status": "missing",
                "diagnostics": "No Applied Section station rows are available.",
            }
        ]
    region_model = to_region_model(find_v1_region_model(doc))
    source_rows = _region_source_rows(region_model)
    if source_rows:
        return _region_boundary_rows_from_source_regions(source_rows, sections)
    groups = _contiguous_region_groups(sections)
    rows: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        group_sections = list(group.get("sections", []) or [])
        first = group_sections[0]
        last = group_sections[-1]
        diagnostics: list[dict[str, str]] = []
        if index > 0:
            diagnostics.extend(_region_boundary_diagnostics(groups[index - 1]["sections"][-1], first, boundary_side="start"))
        if index < len(groups) - 1:
            diagnostics.extend(_region_boundary_diagnostics(last, groups[index + 1]["sections"][0], boundary_side="end"))
        boundary_status = _region_boundary_status(diagnostics)
        rows.append(
            {
                "region_id": str(group.get("region_id", "") or ""),
                "station_start": float(group.get("station_start", 0.0) or 0.0),
                "station_end": float(group.get("station_end", 0.0) or 0.0),
                "assembly": _unique_join(_section_text_values(group_sections, "assembly_id")),
                "structure": _unique_join(_section_structure_values(group_sections)) or "-",
                "drainage": _region_group_drainage_summary(group_sections),
                "surface_status": _region_group_surface_status(group_sections),
                "boundary_status": boundary_status,
                "diagnostics": _region_boundary_diagnostic_summary(diagnostics),
                "diagnostic_count": len(diagnostics),
            }
        )
    return rows


def show_corridor_build_review_object(document=None, row_index: int = 0):
    """Select and fit one Build Corridor review object by review-table row index."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_build_review_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Build Corridor review row index is out of range.")
    row = rows[row_index]
    object_name = str(row.get("object_name", "") or "")
    obj = doc.getObject(object_name) if doc is not None and object_name else None
    if obj is None:
        raise RuntimeError(f"{row.get('result', 'Result')} has not been built yet.")
    _select_and_fit_object(obj)
    return obj


def focus_corridor_region_boundary_row(document=None, row_index: int = 0):
    """Select the built 3D Region surface object for one Region row in Build Corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_region_boundary_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Region boundary row index is out of range.")
    row = rows[row_index]
    region_id = str(row.get("region_id", "") or "")
    if not region_id:
        raise RuntimeError("No Region row is available to display.")
    _remove_legacy_region_display_objects(doc)
    objects = _corridor_region_preview_objects(doc, region_id)
    if not objects:
        raise RuntimeError("Region object set has not been built yet. Rebuild Corridor first.")
    set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
    if set_corridor_build_preview_visibility(doc, "design", True) is None:
        set_corridor_build_preview_visibility(doc, "centerline", True)
    for obj in objects:
        _set_object_visibility(obj, True)
        _style_region_preview_object(obj, selected=True)
    try:
        doc.recompute()
    except Exception:
        pass
    _select_and_fit_objects(objects)
    return objects[0]


def corridor_surface_transition_rows(document=None) -> list[dict[str, object]]:
    """Return Build Corridor rows for user-selected Surface Transition ranges."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    if transition_model is None:
        return []
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    region_surface_contexts = _surface_transition_region_surface_contexts(applied)
    region_rows = corridor_region_boundary_rows(doc)
    validation = SurfaceTransitionValidationService().validate(
        transition_model,
        known_region_refs=_surface_transition_known_region_refs(region_rows),
        boundary_stations=_surface_transition_boundary_stations(region_rows),
    )
    diagnostics_by_source: dict[str, list[object]] = {}
    for diagnostic in list(validation.diagnostic_rows or []):
        diagnostics_by_source.setdefault(str(getattr(diagnostic, "source_ref", "") or ""), []).append(diagnostic)

    rows: list[dict[str, object]] = []
    for transition in list(getattr(transition_model, "transition_ranges", []) or []):
        transition_id = str(getattr(transition, "transition_id", "") or "")
        diagnostics = diagnostics_by_source.get(transition_id, [])
        generation_diagnostics = _surface_transition_generation_diagnostics(
            applied,
            transition_model,
            transition_id=transition_id,
            target_surface_kinds=list(getattr(transition, "target_surface_kinds", []) or []),
        )
        row_status = _surface_transition_row_status(transition, diagnostics)
        if generation_diagnostics and row_status in {"active", "approved", "draft"}:
            row_status = "warn"
        station_start = float(getattr(transition, "station_start", 0.0) or 0.0)
        station_end = float(getattr(transition, "station_end", 0.0) or 0.0)
        sample_interval = float(getattr(transition, "sample_interval", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL) or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)
        rows.append(
            {
                "transition_id": transition_id,
                "enabled": bool(getattr(transition, "enabled", True)),
                "station_start": station_start,
                "station_end": station_end,
                "boundary_station": (station_start + station_end) * 0.5,
                "sample_interval": sample_interval,
                "sample_count": _surface_transition_sample_count(station_start, station_end, sample_interval),
                "from_region_ref": str(getattr(transition, "from_region_ref", "") or ""),
                "to_region_ref": str(getattr(transition, "to_region_ref", "") or ""),
                "from_surface": region_surface_contexts.get(str(getattr(transition, "from_region_ref", "") or ""), ""),
                "to_surface": region_surface_contexts.get(str(getattr(transition, "to_region_ref", "") or ""), ""),
                "target_surfaces": _unique_join(list(getattr(transition, "target_surface_kinds", []) or [])),
                "transition_mode": str(getattr(transition, "transition_mode", "") or ""),
                "approval_status": str(getattr(transition, "approval_status", "") or ""),
                "status": row_status,
                "diagnostics": _surface_transition_review_diagnostic_summary(diagnostics, generation_diagnostics),
                "generation_diagnostic_count": len(generation_diagnostics),
            }
        )
    return rows


def corridor_surface_transition_boundary_options(document=None, region_id: str = "") -> list[dict[str, object]]:
    """Return station combo options for the selected Region's Surface Transition editing."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return []
    region_rows = corridor_region_boundary_rows(doc)
    sections = _station_ordered_applied_sections(applied)
    selected_region = str(region_id or "").strip()
    if selected_region:
        sections = [section for section in sections if _section_region_id(section) == selected_region]
    station_candidates = [
        (_section_station(section), _section_region_id(section))
        for section in sections
    ]
    station_candidates.extend(_region_boundary_station_candidates(region_rows, selected_region))
    if not station_candidates:
        return []
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    transitions_by_id = {
        str(getattr(row, "transition_id", "") or ""): row
        for row in list(getattr(transition_model, "transition_ranges", []) or []) if transition_model is not None
    }
    options: list[dict[str, object]] = []
    seen_keys: set[tuple[str, float, str, str]] = set()
    for station, section_region in sorted(station_candidates, key=lambda row: (float(row[0]), str(row[1]))):
        boundary = _surface_transition_context_for_region_station(region_rows, section_region, station)
        from_region = str(boundary["from_region_ref"])
        to_region = str(boundary["to_region_ref"])
        key = (section_region, round(float(station), 6), from_region, to_region)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        transition_id = _surface_transition_id(from_region, to_region, station)
        transition = transitions_by_id.get(transition_id)
        interval = (
            float(getattr(transition, "sample_interval", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL) or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)
            if transition is not None
            else SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL
        )
        label_context = f"{from_region} -> {to_region}" if from_region != to_region else section_region
        options.append(
            {
                "boundary_index": len(options),
                "boundary_station": float(station),
                "station": float(station),
                "region_ref": section_region,
                "from_region_ref": from_region,
                "to_region_ref": to_region,
                "transition_id": transition_id,
                "sample_interval": interval,
                "transition_exists": transition is not None,
                "label": f"STA {float(station):.3f} | {label_context}",
            }
        )
    return options


def create_corridor_surface_transition_from_region_boundary(
    document=None,
    row_index: int = 0,
    *,
    half_length: float = SURFACE_TRANSITION_DEFAULT_HALF_LENGTH,
    sample_interval: float = SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL,
):
    """Create or replace a SurfaceTransitionRange around a selected Region boundary."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    region_rows = corridor_region_boundary_rows(doc)
    boundary = _surface_transition_boundary_from_region_row(region_rows, int(row_index))
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    project = find_project(doc)
    existing = to_surface_transition_model(find_v1_surface_transition_model(doc))
    if existing is None:
        existing = SurfaceTransitionModel(
            schema_version=1,
            project_id=_project_id(project),
            transition_model_id="surface-transitions:main",
            corridor_ref=str(getattr(applied, "corridor_id", "") or "corridor:main"),
        )
    transition_id = _surface_transition_id(
        boundary["from_region_ref"],
        boundary["to_region_ref"],
        float(boundary["boundary_station"]),
    )
    station_start = float(boundary["boundary_station"]) - max(0.001, float(half_length))
    station_end = float(boundary["boundary_station"]) + max(0.001, float(half_length))
    new_range = SurfaceTransitionRange(
        transition_id=transition_id,
        station_start=station_start,
        station_end=station_end,
        from_region_ref=str(boundary["from_region_ref"]),
        to_region_ref=str(boundary["to_region_ref"]),
        transition_mode="interpolate_matching_roles",
        sample_interval=max(0.1, float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)),
        enabled=True,
        approval_status="active",
        source_ref="build-corridor:region-boundary",
        notes="Created from Build Corridor Region boundary review.",
    )
    rows = [
        row
        for row in list(getattr(existing, "transition_ranges", []) or [])
        if str(getattr(row, "transition_id", "") or "") != transition_id
    ]
    rows.append(new_range)
    updated = SurfaceTransitionModel(
        schema_version=int(getattr(existing, "schema_version", 1) or 1),
        project_id=str(getattr(existing, "project_id", "") or _project_id(project)),
        transition_model_id=str(getattr(existing, "transition_model_id", "") or "surface-transitions:main"),
        corridor_ref=str(getattr(existing, "corridor_ref", "") or getattr(applied, "corridor_id", "") or "corridor:main"),
        label=str(getattr(existing, "label", "") or "Surface Transitions"),
        transition_ranges=sorted(rows, key=lambda row: (float(row.station_start), float(row.station_end), str(row.transition_id))),
    )
    return create_or_update_v1_surface_transition_model_object(
        document=doc,
        project=project,
        transition_model=updated,
    )


def create_or_update_corridor_surface_transition_for_boundary(
    document=None,
    boundary_index: int = 0,
    *,
    sample_interval: float = SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL,
    region_id: str = "",
):
    """Create or update one station-owned Surface Transition with a station-specific interval."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    options = corridor_surface_transition_boundary_options(doc, region_id=region_id)
    index = int(boundary_index)
    if index < 0 or index >= len(options):
        raise IndexError("Surface Transition station index is out of range.")
    return _create_or_update_corridor_surface_transition_from_station_option(
        doc,
        options[index],
        sample_interval=float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL),
    )


def _create_or_update_corridor_surface_transition_from_station_option(
    document,
    option: dict[str, object],
    *,
    half_length: float = SURFACE_TRANSITION_DEFAULT_HALF_LENGTH,
    sample_interval: float = SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL,
):
    """Persist one SurfaceTransitionRange from a Region station combo option."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    project = find_project(doc)
    existing = to_surface_transition_model(find_v1_surface_transition_model(doc))
    if existing is None:
        existing = SurfaceTransitionModel(
            schema_version=1,
            project_id=_project_id(project),
            transition_model_id="surface-transitions:main",
            corridor_ref=str(getattr(applied, "corridor_id", "") or "corridor:main"),
        )
    station = float(option.get("station", option.get("boundary_station", 0.0)) or 0.0)
    from_region = str(option.get("from_region_ref", "") or "")
    to_region = str(option.get("to_region_ref", "") or "")
    if not from_region or not to_region:
        region_ref = str(option.get("region_ref", "") or "")
        from_region = from_region or region_ref
        to_region = to_region or region_ref
    transition_id = _surface_transition_id(from_region, to_region, station)
    station_start = station - max(0.001, float(half_length))
    station_end = station + max(0.001, float(half_length))
    source_ref = "build-corridor:region-boundary" if from_region != to_region else "build-corridor:region-station"
    new_range = SurfaceTransitionRange(
        transition_id=transition_id,
        station_start=station_start,
        station_end=station_end,
        from_region_ref=from_region,
        to_region_ref=to_region,
        transition_mode="interpolate_matching_roles",
        sample_interval=max(0.1, float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)),
        enabled=True,
        approval_status="active",
        source_ref=source_ref,
        notes="Created from Build Corridor Region station review.",
    )
    rows = [
        row
        for row in list(getattr(existing, "transition_ranges", []) or [])
        if str(getattr(row, "transition_id", "") or "") != transition_id
    ]
    rows.append(new_range)
    updated = SurfaceTransitionModel(
        schema_version=int(getattr(existing, "schema_version", 1) or 1),
        project_id=str(getattr(existing, "project_id", "") or _project_id(project)),
        transition_model_id=str(getattr(existing, "transition_model_id", "") or "surface-transitions:main"),
        corridor_ref=str(getattr(existing, "corridor_ref", "") or getattr(applied, "corridor_id", "") or "corridor:main"),
        label=str(getattr(existing, "label", "") or "Surface Transitions"),
        transition_ranges=sorted(rows, key=lambda row: (float(row.station_start), float(row.station_end), str(row.transition_id))),
    )
    return create_or_update_v1_surface_transition_model_object(
        document=doc,
        project=project,
        transition_model=updated,
    )


def toggle_corridor_surface_transition_enabled(document=None, row_index: int = 0):
    """Toggle a Surface Transition range enabled flag by transition-table row index."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    transition_obj = find_v1_surface_transition_model(doc)
    transition_model = to_surface_transition_model(transition_obj)
    if transition_model is None:
        raise RuntimeError("No Surface Transition ranges are available.")
    rows = list(getattr(transition_model, "transition_ranges", []) or [])
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Surface Transition row index is out of range.")
    updated_rows: list[SurfaceTransitionRange] = []
    for index, row in enumerate(rows):
        updated_rows.append(
            SurfaceTransitionRange(
                transition_id=row.transition_id,
                station_start=row.station_start,
                station_end=row.station_end,
                from_region_ref=row.from_region_ref,
                to_region_ref=row.to_region_ref,
                target_surface_kinds=list(row.target_surface_kinds or []),
                transition_mode=row.transition_mode,
                sample_interval=row.sample_interval,
                enabled=(not bool(row.enabled)) if index == row_index else bool(row.enabled),
                approval_status=row.approval_status,
                source_ref=row.source_ref,
                notes=row.notes,
            )
        )
    updated = SurfaceTransitionModel(
        schema_version=int(getattr(transition_model, "schema_version", 1) or 1),
        project_id=str(getattr(transition_model, "project_id", "") or _project_id(find_project(doc))),
        transition_model_id=str(getattr(transition_model, "transition_model_id", "") or "surface-transitions:main"),
        corridor_ref=str(getattr(transition_model, "corridor_ref", "") or "corridor:main"),
        label=str(getattr(transition_model, "label", "") or "Surface Transitions"),
        transition_ranges=updated_rows,
    )
    return create_or_update_v1_surface_transition_model_object(
        document=doc,
        project=find_project(doc),
        transition_model=updated,
    )


def update_corridor_surface_transition_station_range(
    document=None,
    row_index: int = 0,
    *,
    station_start: float,
    station_end: float,
):
    """Update one Surface Transition station range by transition-table row index."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    if transition_model is None:
        raise RuntimeError("No Surface Transition ranges are available.")
    rows = list(getattr(transition_model, "transition_ranges", []) or [])
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Surface Transition row index is out of range.")
    start = float(station_start)
    end = float(station_end)
    updated_rows: list[SurfaceTransitionRange] = []
    for index, row in enumerate(rows):
        updated_rows.append(
            SurfaceTransitionRange(
                transition_id=row.transition_id,
                station_start=start if index == row_index else row.station_start,
                station_end=end if index == row_index else row.station_end,
                from_region_ref=row.from_region_ref,
                to_region_ref=row.to_region_ref,
                target_surface_kinds=list(row.target_surface_kinds or []),
                transition_mode=row.transition_mode,
                sample_interval=row.sample_interval,
                enabled=bool(row.enabled),
                approval_status=row.approval_status,
                source_ref=row.source_ref or "build-corridor:station-range",
                notes=row.notes,
            )
        )
    updated = SurfaceTransitionModel(
        schema_version=int(getattr(transition_model, "schema_version", 1) or 1),
        project_id=str(getattr(transition_model, "project_id", "") or _project_id(find_project(doc))),
        transition_model_id=str(getattr(transition_model, "transition_model_id", "") or "surface-transitions:main"),
        corridor_ref=str(getattr(transition_model, "corridor_ref", "") or "corridor:main"),
        label=str(getattr(transition_model, "label", "") or "Surface Transitions"),
        transition_ranges=updated_rows,
    )
    return create_or_update_v1_surface_transition_model_object(
        document=doc,
        project=find_project(doc),
        transition_model=updated,
    )


def focus_corridor_build_guided_review_step(document=None, step_id: str = "centerline"):
    """Focus one guided review step and isolate its relevant preview layers."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    step = _corridor_build_guided_review_step(step_id)
    if doc is None or step is None:
        raise RuntimeError(f"Guided review step was not found: {step_id}")
    set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
    for role in list(step[2] or []):
        set_corridor_build_preview_visibility(doc, role, True)
    if step[0] == "slope_issues":
        issue_markers = _corridor_build_issue_marker_objects(doc)
        for marker in issue_markers:
            _set_object_visibility(marker, True)
        issues = corridor_slope_face_issue_rows(doc)
        if issues:
            return show_corridor_slope_face_issue_marker(doc, 0)
        daylight = _corridor_build_preview_object(doc, "daylight")
        if daylight is not None:
            _select_and_fit_object(daylight)
            return daylight
    focus_role = str(list(step[2])[-1] if step[2] else "")
    obj = _corridor_build_preview_object(doc, focus_role)
    if obj is None:
        raise RuntimeError(f"Guided review target has not been built: {step[1]}")
    _select_and_fit_object(obj)
    return obj


def show_corridor_slope_face_issue_marker(document=None, row_index: int = 0):
    """Select and fit the 3D marker object related to one slope-face issue row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_slope_face_issue_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Slope Face issue row index is out of range.")
    row = rows[row_index]
    object_name = str(row.get("marker_object", "") or "ReviewIssueSlopeFaceFallbackMarkers")
    obj = doc.getObject(object_name) if doc is not None and object_name else None
    if obj is None:
        raise RuntimeError(f"Slope Face marker object was not found: {object_name}")
    _select_and_fit_object(obj)
    return obj


def focus_corridor_slope_face_issue(document=None, row_index: int = 0):
    """Focus one slope-face issue with the daylight surface and issue markers visible."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_slope_face_issue_rows(doc)
    if not rows:
        raise RuntimeError("No Slope Face issue rows are available.")
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Slope Face issue row index is out of range.")
    set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
    set_corridor_build_preview_visibility(doc, "daylight", True)
    for marker in _corridor_build_issue_marker_objects(doc):
        _set_object_visibility(marker, True)
    return show_corridor_slope_face_issue_marker(doc, row_index)


def focus_adjacent_corridor_slope_face_issue(document=None, current_index: int = -1, direction: int = 1):
    """Focus the previous or next slope-face issue and return its index and marker object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_slope_face_issue_rows(doc)
    if not rows:
        raise RuntimeError("No Slope Face issue rows are available.")
    step = 1 if int(direction or 0) >= 0 else -1
    if current_index < 0 or current_index >= len(rows):
        target_index = 0 if step > 0 else len(rows) - 1
    else:
        target_index = (int(current_index) + step) % len(rows)
    return target_index, focus_corridor_slope_face_issue(doc, target_index)


def focus_corridor_drainage_review_row(document=None, row_index: int = 0):
    """Create/select a marker for one drainage diagnostic row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_drainage_review_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Drainage diagnostic row index is out of range.")
    row = rows[row_index]
    marker_name = str(row.get("marker_object", "") or _drainage_review_marker_name(row_index))
    obj = _create_drainage_review_marker(document=doc, row=row, object_name=marker_name)
    if obj is None:
        raise RuntimeError("Drainage diagnostic marker was not created.")
    set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
    set_corridor_build_preview_visibility(doc, "drainage", True)
    _set_object_visibility(obj, True)
    _select_and_fit_object(obj)
    return obj


def set_corridor_build_preview_visibility(document=None, role: str = "", visible: bool = True):
    """Set visibility for one Build Corridor preview object by result role."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    obj = _corridor_build_preview_object(doc, role)
    if obj is None:
        return None
    _set_object_visibility(obj, bool(visible))
    return obj


def set_all_corridor_build_preview_visibility(document=None, visible: bool = True, *, include_issue_markers: bool = True) -> int:
    """Set visibility for all Build Corridor preview objects and optional issue markers."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return 0
    changed = 0
    for role, _title, _object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        if set_corridor_build_preview_visibility(doc, role, visible) is not None:
            changed += 1
    if include_issue_markers:
        for obj in _corridor_build_issue_marker_objects(doc):
            _set_object_visibility(obj, bool(visible))
            changed += 1
    return changed


def set_corridor_build_daylight_contact_marker_visibility(document=None, visible: bool = True):
    """Set visibility for daylight marker objects created by Build Corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    objects = _corridor_build_daylight_marker_objects(doc)
    if not objects:
        return None
    for obj in objects:
        _set_object_visibility(obj, bool(visible))
    return _corridor_build_daylight_contact_marker_object(doc) or objects[0]


def preferred_corridor_build_review_row_index(
    rows: list[dict[str, object]],
    *,
    preferred_role: str = "design",
) -> int | None:
    """Return the best review row index to focus after a corridor build."""

    ready_rows = [
        (index, row)
        for index, row in enumerate(list(rows or []))
        if str(row.get("status", "") or "") == "ready"
    ]
    if not ready_rows:
        return None
    preferred = str(preferred_role or "").strip()
    for index, row in ready_rows:
        if str(row.get("role", "") or "") == preferred:
            return index
    return ready_rows[0][0]


def corridor_centerline_preview_style() -> dict[str, object]:
    """Return the visual style policy for the v1 corridor 3D centerline."""

    return dict(CORRIDOR_CENTERLINE_PREVIEW_STYLE)


def create_corridor_centerline_3d_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    applied_section_set_ref: str = "",
):
    """Create or update a spline-based 3D centerline preview from AppliedSection frames."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None

    points, stations = _centerline_points_from_applied_sections(applied_section_set, AppModule)
    if len(points) < 2:
        return None
    shape, curve_kind = _make_centerline_shape(points, Part)
    obj = doc.getObject("V1CorridorCenterline3DPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1CorridorCenterline3DPreview")
    try:
        obj.Shape = shape
        obj.Label = "Corridor 3D Centerline"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_centerline_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorCenterlinePreview")
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_property(
        obj,
        "AppliedSectionSetId",
        str(applied_section_set_ref or getattr(applied_section_set, "applied_section_set_id", "") or ""),
    )
    _set_preview_property(obj, "DisplayCurveKind", curve_kind)
    _set_preview_integer_property(obj, "PointCount", len(points))
    if stations:
        _set_preview_float_property(obj, "StationStart", min(stations))
        _set_preview_float_property(obj, "StationEnd", max(stations))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            style = corridor_centerline_preview_style()
            vobj.Visibility = True
            vobj.LineColor = style["line_color"]
            vobj.PointColor = style["point_color"]
            vobj.ShapeColor = style["shape_color"]
            vobj.LineWidth = float(style["line_width"])
            vobj.PointSize = float(style["point_size"])
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(doc), obj)
    except Exception:
        pass
    return obj


def create_corridor_design_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
):
    """Create or update the first design-surface mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    surface_id = _surface_id(surface_model, "design_surface") or f"{corridor_model.corridor_id}:design"
    try:
        tin_surface = CorridorSurfaceGeometryService().build_design_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
                supplemental_sampling_enabled=supplemental_sampling_enabled,
                surface_transition_model=transition_model,
            )
        )
    except Exception:
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDesignSurfacePreview",
        label_prefix="Corridor Design Surface",
        surface_role="design",
        recompute=False,
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def create_corridor_region_surface_previews(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
) -> list[object]:
    """Create/update built Region surface objects used by Region Boundary review selection."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None:
        return []
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return []
    _remove_legacy_region_display_objects(doc)
    rows = corridor_region_boundary_rows(doc)
    created: list[object] = []
    keep_names: set[str] = set()
    for row in rows:
        region_id = str(row.get("region_id", "") or "")
        if not region_id:
            continue
        objects = _create_or_update_region_preview_objects(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=applied,
            row=row,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        if objects:
            created.extend(objects)
            keep_names.update(str(getattr(obj, "Name", "") or "") for obj in objects)
        for object_name in _region_preview_object_names(region_id):
            if object_name not in keep_names and doc.getObject(object_name) is not None:
                _remove_preview_object(doc, object_name)
    _remove_stale_region_surface_preview_objects(doc, keep_names=keep_names)
    return created


def create_corridor_subgrade_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
):
    """Create or update the first subgrade-surface mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    surface_id = _surface_id(surface_model, "subgrade_surface") or f"{corridor_model.corridor_id}:subgrade"
    try:
        tin_surface = CorridorSurfaceGeometryService().build_subgrade_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
                supplemental_sampling_enabled=supplemental_sampling_enabled,
                surface_transition_model=transition_model,
            )
        )
    except Exception:
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorSubgradeSurfacePreview",
        label_prefix="Corridor Subgrade Surface",
        surface_role="subgrade",
        recompute=False,
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def create_corridor_daylight_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    show_daylight_contact_markers: bool = True,
    supplemental_sampling_enabled: bool = False,
):
    """Create or update the first slope-face mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    surface_id = _surface_id(surface_model, "daylight_surface") or f"{corridor_model.corridor_id}:daylight"
    try:
        tin_surface = CorridorSurfaceGeometryService().build_daylight_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
                existing_ground_surface=_resolve_corridor_existing_ground_tin_surface(doc),
                supplemental_sampling_enabled=supplemental_sampling_enabled,
                surface_transition_model=transition_model,
            )
        )
    except Exception:
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDaylightSurfacePreview",
        label_prefix="Corridor Slope Face Surface",
        surface_role="daylight",
        recompute=False,
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        _attach_surface_quality_properties(preview_obj, tin_surface, applied_section_set=applied_section_set)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
        _create_slope_face_diagnostic_markers(
            document=doc,
            project=project or find_project(doc),
            surface=tin_surface,
            corridor_model=corridor_model,
            applied_section_set=applied_section_set,
            show_daylight_contact_markers=show_daylight_contact_markers,
        )
    return preview_obj


def create_corridor_drainage_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
):
    """Create or update the first ditch/drainage mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    surface_id = _surface_id(surface_model, "drainage_surface")
    if not surface_id:
        _remove_preview_object(doc, "V1CorridorDrainageSurfacePreview")
        return None
    try:
        tin_surface = CorridorSurfaceGeometryService().build_drainage_surface(
            CorridorDesignSurfaceGeometryRequest(
                project_id=_project_id(project or find_project(doc)),
                corridor=corridor_model,
                applied_section_set=applied_section_set,
                surface_id=surface_id,
                supplemental_sampling_enabled=supplemental_sampling_enabled,
                surface_transition_model=transition_model,
            )
        )
    except Exception:
        _remove_preview_object(doc, "V1CorridorDrainageSurfacePreview")
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDrainageSurfacePreview",
        label_prefix="Corridor Drainage Surface",
        surface_role="drainage",
        recompute=False,
    )
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _set_preview_property(preview_obj, "CRRecordKind", "v1_corridor_surface_preview")
        _set_preview_property(preview_obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
        _set_preview_property(preview_obj, "SurfaceId", surface_id)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def create_corridor_surface_transition_span_markers(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update 3D markers for surface spans with Transition Surface intent."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or surface_model is None:
        return None
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    points, refs = _surface_transition_span_marker_points(applied, surface_model)
    obj = _create_marker_compound(
        document=doc,
        object_name="V1SurfaceTransitionSpanMarkers",
        label="Surface Transition Spans",
        points=points,
        radius=_marker_radius(points),
        color=(0.72, 0.10, 0.88),
        surface=surface_model,
        corridor_model=corridor_model,
    )
    if obj is None:
        return None
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "surface_transition_span")
    _set_preview_property(obj, "CRRecordKind", "v1_surface_transition_span_marker")
    _set_preview_property(obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
    _set_preview_string_list_property(obj, "TransitionRefs", refs)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(doc), obj)
    except Exception:
        pass
    return obj


def run_v1_build_corridor_command():
    """Open the v1 Build Corridor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1BuildCorridorTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_corridor_model(App.ActiveDocument)


class V1BuildCorridorTaskPanel:
    """Small Apply-gated panel for v1 CorridorModel creation."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.form = self._build_ui()
        self._refresh_summary()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Build Corridor")
        try:
            widget.setMinimumWidth(BUILD_CORRIDOR_PANEL_MIN_WIDTH)
            widget.setMaximumWidth(BUILD_CORRIDOR_PANEL_MAX_WIDTH)
        except Exception:
            pass
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QtWidgets.QLabel("Build Corridor")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        note = QtWidgets.QLabel(
            "Build the v1 CorridorModel from Applied Sections, review corridor surfaces, and package structure outputs when StructureModel source rows are available."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setFixedHeight(150)
        layout.addWidget(self._summary)
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Ready")
        layout.addWidget(self._progress)
        tabs = QtWidgets.QTabWidget()
        guided_tab = QtWidgets.QWidget()
        guided_layout = QtWidgets.QVBoxLayout(guided_tab)
        guided_layout.setContentsMargins(8, 8, 8, 8)
        results_tab = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(results_tab)
        results_layout.setContentsMargins(8, 8, 8, 8)
        issues_tab = QtWidgets.QWidget()
        issues_layout = QtWidgets.QVBoxLayout(issues_tab)
        issues_layout.setContentsMargins(8, 8, 8, 8)
        regions_tab = QtWidgets.QWidget()
        regions_layout = QtWidgets.QVBoxLayout(regions_tab)
        regions_layout.setContentsMargins(8, 8, 8, 8)
        drainage_tab = QtWidgets.QWidget()
        drainage_layout = QtWidgets.QVBoxLayout(drainage_tab)
        drainage_layout.setContentsMargins(8, 8, 8, 8)
        options_tab = QtWidgets.QWidget()
        options_layout = QtWidgets.QVBoxLayout(options_tab)
        options_layout.setContentsMargins(8, 8, 8, 8)
        visibility_tab = QtWidgets.QWidget()
        visibility_layout = QtWidgets.QVBoxLayout(visibility_tab)
        visibility_layout.setContentsMargins(8, 8, 8, 8)
        tabs.addTab(guided_tab, "Guided Review")
        tabs.addTab(results_tab, "Results")
        tabs.addTab(issues_tab, "Slope Issues")
        tabs.addTab(regions_tab, "Regions")
        tabs.addTab(drainage_tab, "Drainage")
        tabs.addTab(options_tab, "Options")
        tabs.addTab(visibility_tab, "Visibility")
        layout.addWidget(tabs, 1)
        guided_label = QtWidgets.QLabel("Guided Review")
        guided_label.setToolTip("Follow the practical corridor check order and focus the related 3D preview layer.")
        guided_layout.addWidget(guided_label)
        self._guided_table = QtWidgets.QTableWidget(0, 4)
        self._guided_table.setHorizontalHeaderLabels(["Step", "Status", "Focus", "Notes"])
        _compact_build_corridor_table(self._guided_table, [145, 76, 120, 220])
        self._guided_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._guided_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._guided_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._guided_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._guided_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._guided_table.cellDoubleClicked.connect(lambda row_index, _col: self._focus_guided_review_row(row_index))
        guided_layout.addWidget(self._guided_table, 1)
        self._review_table = QtWidgets.QTableWidget(0, 9)
        self._review_table.setHorizontalHeaderLabels(
            [
                "Result",
                "Status",
                "Object",
                "Vertices",
                "Triangles/Points",
                "Role",
                "Applied Sections",
                "Applied Diagnostics",
                "Notes",
            ]
        )
        _compact_build_corridor_table(self._review_table, [110, 72, 150, 70, 105, 90, 150, 150, 220])
        self._review_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._review_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._review_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._review_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._review_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._review_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_review_row(row_index))
        results_layout.addWidget(self._review_table, 1)
        issue_label = QtWidgets.QLabel("Slope Face Issues")
        issue_label.setToolTip("Double-click an issue row to select and fit the related 3D review marker.")
        issues_layout.addWidget(issue_label)
        self._slope_issue_table = QtWidgets.QTableWidget(0, 5)
        self._slope_issue_table.setHorizontalHeaderLabels(["Station", "Side", "Reason", "Status", "Marker"])
        _compact_build_corridor_table(self._slope_issue_table, [90, 60, 150, 80, 130])
        self._slope_issue_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._slope_issue_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._slope_issue_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._slope_issue_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._slope_issue_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._slope_issue_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_slope_face_issue_row(row_index))
        issues_layout.addWidget(self._slope_issue_table, 1)
        issue_nav_row = QtWidgets.QHBoxLayout()
        previous_issue_button = QtWidgets.QPushButton("Previous Issue")
        previous_issue_button.clicked.connect(lambda: self._focus_adjacent_slope_face_issue(-1))
        issue_nav_row.addWidget(previous_issue_button)
        next_issue_button = QtWidgets.QPushButton("Next Issue")
        next_issue_button.clicked.connect(lambda: self._focus_adjacent_slope_face_issue(1))
        issue_nav_row.addWidget(next_issue_button)
        issue_nav_row.addStretch(1)
        issues_layout.addLayout(issue_nav_row)
        regions_label = QtWidgets.QLabel("Region Boundaries")
        regions_label.setToolTip("Double-click a Region row to select its built 3D Region surface object.")
        regions_layout.addWidget(regions_label)
        self._region_table = QtWidgets.QTableWidget(0, 9)
        self._region_table.setHorizontalHeaderLabels(
            ["Region", "Start STA", "End STA", "Assembly", "Structure", "Drainage", "Surface", "Boundary", "Diagnostics"]
        )
        _compact_build_corridor_table(self._region_table, [120, 80, 80, 105, 105, 90, 80, 90, 240])
        self._region_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._region_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._region_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._region_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._region_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._region_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_region_boundary_row(row_index))
        self._region_table.itemSelectionChanged.connect(self._sync_surface_transition_station_options_from_selected_region)
        regions_layout.addWidget(self._region_table, 1)
        region_button_row = QtWidgets.QHBoxLayout()
        highlight_region_button = QtWidgets.QPushButton("Highlight Region")
        highlight_region_button.clicked.connect(self._show_selected_region_boundary_row)
        region_button_row.addWidget(highlight_region_button)
        refresh_regions_button = QtWidgets.QPushButton("Refresh Boundaries")
        refresh_regions_button.clicked.connect(self._refresh_region_boundary_rows)
        region_button_row.addWidget(refresh_regions_button)
        region_button_row.addStretch(1)
        regions_layout.addLayout(region_button_row)
        transitions_label = QtWidgets.QLabel("Surface Transitions")
        transitions_label.setToolTip("User-selected station ranges where Transition Surface treatment should be applied.")
        regions_layout.addWidget(transitions_label)
        self._surface_transition_table = QtWidgets.QTableWidget(0, 13)
        self._surface_transition_table.setHorizontalHeaderLabels(
            [
                "Transition",
                "Enabled",
                "STA",
                "Spacing",
                "Sample Count",
                "From",
                "To",
                "From Surface",
                "To Surface",
                "Targets",
                "Mode",
                "Status",
                "Diagnostics",
            ]
        )
        _compact_build_corridor_table(self._surface_transition_table, [135, 58, 90, 75, 65, 90, 90, 150, 150, 95, 135, 75, 190])
        self._surface_transition_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._surface_transition_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._surface_transition_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._surface_transition_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._surface_transition_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._surface_transition_table.itemSelectionChanged.connect(self._sync_selected_surface_transition_row_controls)
        regions_layout.addWidget(self._surface_transition_table, 1)
        transition_range_row = QtWidgets.QHBoxLayout()
        transition_range_row.addWidget(QtWidgets.QLabel("Region STA"))
        self._surface_transition_boundary_combo = QtWidgets.QComboBox()
        self._surface_transition_boundary_combo.currentIndexChanged.connect(lambda _index: self._sync_selected_surface_transition_boundary_spacing())
        transition_range_row.addWidget(self._surface_transition_boundary_combo, 2)
        transition_range_row.addWidget(QtWidgets.QLabel("Spacing"))
        self._surface_transition_spacing_combo = QtWidgets.QComboBox()
        for label, value in SURFACE_TRANSITION_SPACING_PRESETS:
            self._surface_transition_spacing_combo.addItem(label, value)
        self._surface_transition_spacing_combo.currentIndexChanged.connect(lambda _index: self._sync_surface_transition_custom_spacing_state())
        transition_range_row.addWidget(self._surface_transition_spacing_combo)
        self._surface_transition_spacing_spin = QtWidgets.QDoubleSpinBox()
        self._surface_transition_spacing_spin.setRange(0.1, 10000.0)
        self._surface_transition_spacing_spin.setDecimals(3)
        self._surface_transition_spacing_spin.setSingleStep(0.5)
        self._surface_transition_spacing_spin.setSuffix(" m")
        self._surface_transition_spacing_spin.setValue(SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)
        transition_range_row.addWidget(self._surface_transition_spacing_spin)
        create_update_transition_button = QtWidgets.QPushButton("Update")
        create_update_transition_button.clicked.connect(self._create_transition_from_selected_boundary_option)
        transition_range_row.addWidget(create_update_transition_button)
        transition_range_row.addStretch(1)
        regions_layout.addLayout(transition_range_row)
        transition_button_row = QtWidgets.QHBoxLayout()
        toggle_transition_button = QtWidgets.QPushButton("Toggle Enabled")
        toggle_transition_button.clicked.connect(self._toggle_selected_surface_transition)
        transition_button_row.addWidget(toggle_transition_button)
        refresh_transitions_button = QtWidgets.QPushButton("Refresh Transitions")
        refresh_transitions_button.clicked.connect(lambda: self._set_surface_transition_rows(corridor_surface_transition_rows(self.document)))
        transition_button_row.addWidget(refresh_transitions_button)
        transition_button_row.addStretch(1)
        regions_layout.addLayout(transition_button_row)
        drainage_label = QtWidgets.QLabel("Drainage Diagnostics")
        drainage_label.setToolTip("Station-level ditch_surface point diagnostics from Applied Sections.")
        drainage_layout.addWidget(drainage_label)
        self._drainage_table = QtWidgets.QTableWidget(0, 6)
        self._drainage_table.setHorizontalHeaderLabels(["Station", "Status", "Points", "Left", "Right", "Notes"])
        _compact_build_corridor_table(self._drainage_table, [90, 80, 65, 55, 55, 220])
        self._drainage_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._drainage_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._drainage_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._drainage_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._drainage_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._drainage_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_drainage_review_row(row_index))
        drainage_layout.addWidget(self._drainage_table, 1)
        sampling_label = QtWidgets.QLabel("Surface Sampling")
        sampling_label.setToolTip("Control generated Build Corridor mesh rows between source Applied Section stations.")
        options_layout.addWidget(sampling_label)
        self._supplemental_sampling_check = QtWidgets.QCheckBox("Supplemental Sampling")
        self._supplemental_sampling_check.setToolTip(
            "Automatically add generated mesh rows inside triggered station spans for cleaner corridor surfaces."
        )
        self._supplemental_sampling_check.setChecked(True)
        options_layout.addWidget(self._supplemental_sampling_check)
        options_layout.addStretch(1)
        visibility_label = QtWidgets.QLabel("Preview Visibility")
        visibility_label.setToolTip("Toggle corridor review objects in the 3D View without rebuilding the corridor.")
        visibility_layout.addWidget(visibility_label)
        visibility_grid = QtWidgets.QGridLayout()
        self._visibility_checks = {}
        for index, (role, title, _object_name) in enumerate(CORRIDOR_BUILD_REVIEW_OBJECTS):
            check = QtWidgets.QCheckBox(title)
            check.setChecked(True)
            check.toggled.connect(lambda checked, role=role: self._set_preview_visibility(role, checked))
            self._visibility_checks[role] = check
            visibility_grid.addWidget(check, index // 2, index % 2)
        visibility_layout.addLayout(visibility_grid)
        marker_row = QtWidgets.QHBoxLayout()
        self._daylight_contact_marker_check = QtWidgets.QCheckBox("Daylight Contact Markers")
        self._daylight_contact_marker_check.setToolTip("Show or hide the large daylight/EG contact markers.")
        self._daylight_contact_marker_check.setChecked(False)
        self._daylight_contact_marker_check.toggled.connect(self._set_daylight_contact_marker_visibility)
        marker_row.addWidget(self._daylight_contact_marker_check)
        marker_row.addStretch(1)
        visibility_layout.addLayout(marker_row)
        visibility_layout.addStretch(1)
        row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_summary)
        row.addWidget(refresh_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        row.addWidget(apply_button)
        focus_button = QtWidgets.QPushButton("Focus")
        focus_button.clicked.connect(self._show_selected_row)
        row.addWidget(focus_button)
        structure_output_button = QtWidgets.QPushButton("Structure Output")
        structure_output_button.clicked.connect(self._open_structure_output_panel)
        row.addWidget(structure_output_button)
        row.addStretch(1)
        layout.addLayout(row)

        export_row = QtWidgets.QHBoxLayout()
        show_all_button = QtWidgets.QPushButton("Show All")
        show_all_button.clicked.connect(lambda: self._set_all_preview_visibility(True))
        export_row.addWidget(show_all_button)
        hide_all_button = QtWidgets.QPushButton("Hide All")
        hide_all_button.clicked.connect(lambda: self._set_all_preview_visibility(False))
        export_row.addWidget(hide_all_button)
        export_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        export_row.addWidget(close_button)
        layout.addLayout(export_row)
        return widget

    def _refresh_summary(self):
        applied_obj = find_v1_applied_section_set(self.document)
        applied = to_applied_section_set(applied_obj)
        if applied is None:
            self._summary.setPlainText("Applied Sections: missing\nRun Applied Sections before Build Corridor.")
            self._set_guided_review_rows(corridor_build_guided_review_steps(self.document))
            self._set_review_rows(corridor_build_review_rows(self.document))
            self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
            self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._set_drainage_review_rows(corridor_drainage_review_rows(self.document))
            return
        applied_summary = corridor_applied_sections_review_summary(self.document)
        self._summary.setPlainText(
            "\n".join(
                [
                    f"Applied Sections: {applied.applied_section_set_id}",
                    f"Stations: {len(applied.station_rows)}",
                    f"Alignment: {applied.alignment_id}",
                    f"Source Review: {applied_summary.get('summary', '')}",
                    f"Source Structure: {_format_structure_review_summary(applied_summary)}",
                    f"Source Diagnostics: {applied_summary.get('diagnostics', '')}",
                    "",
                    "Click Apply to create or update the v1 CorridorModel.",
                ]
            )
        )
        self._set_guided_review_rows(corridor_build_guided_review_steps(self.document))
        self._set_review_rows(corridor_build_review_rows(self.document))
        self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
        self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
        self._sync_surface_transition_station_options_from_selected_region()
        self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
        self._set_drainage_review_rows(corridor_drainage_review_rows(self.document))

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            self._set_progress(0, "Preparing Corridor Build...")
            self._set_progress(15, "Reading Applied Sections...")
            result = build_document_corridor_model(self.document)
            self._set_progress(35, "Building CorridorModel...")
            obj = apply_v1_corridor_model(
                document=self.document,
                corridor_model=result,
                show_daylight_contact_markers=self._show_daylight_contact_markers(),
                supplemental_sampling_enabled=self._use_supplemental_sampling(),
                progress_callback=self._set_progress,
            )
            self._set_progress(96, "Reading surface summary...")
            surface_obj = find_v1_surface_model(self.document)
            surface_count = int(getattr(surface_obj, "SurfaceCount", 0) or 0) if surface_obj is not None else 0
            message = f"CorridorModel has been built.\nStations: {len(result.station_rows)}\nSurface rows: {surface_count}"
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            self._set_progress(97, "Refreshing review rows...")
            _hide_applied_section_set_review_shape(self.document)
            review_rows = corridor_build_review_rows(self.document)
            self._set_guided_review_rows(corridor_build_guided_review_steps(self.document))
            self._set_review_rows(review_rows)
            self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
            self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._set_drainage_review_rows(corridor_drainage_review_rows(self.document))
            self._set_progress(99, "Focusing review preview...")
            focused = self._show_preferred_review_row(review_rows)
            if focused:
                self._summary.setPlainText(
                    message + f"\nObject: {obj.Label}\nFocused: {getattr(focused, 'Label', getattr(focused, 'Name', ''))}"
                )
            self._set_progress(100, "Corridor Build complete")
            _show_message(self.form, "Build Corridor", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_progress(0, "Corridor Build failed")
            self._summary.setPlainText(f"CorridorModel was not built:\n{exc}")
            _show_message(self.form, "Build Corridor", f"CorridorModel was not built.\n{exc}")
            return False

    def _set_progress(self, value: int, text: str = "") -> None:
        progress = getattr(self, "_progress", None)
        if progress is None:
            return
        try:
            progress.setValue(max(0, min(100, int(value))))
            if text:
                progress.setFormat(text)
        except Exception:
            return
        _process_panel_events()

    def _use_supplemental_sampling(self) -> bool:
        check = getattr(self, "_supplemental_sampling_check", None)
        if check is None:
            return True
        try:
            return bool(check.isChecked())
        except Exception:
            return True

    def _open_structure_output_panel(self) -> bool:
        try:
            from .cmd_structure_output import run_v1_structure_output_command

            run_v1_structure_output_command(document=self.document)
            self._summary.setPlainText("Structure Output panel opened.")
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Structure Output panel was not opened:\n{exc}")
            _show_message(self.form, "Build Corridor", f"Structure Output panel was not opened.\n{exc}")
            return False

    def _set_guided_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_guided_table"):
            return
        self._guided_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._guided_table.rowCount()
            self._guided_table.insertRow(row_index)
            values = [
                str(row.get("title", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("focus", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("step_id", "") or ""))
                self._guided_table.setItem(row_index, col, item)
            self._apply_guided_row_style(row_index, str(row.get("status", "") or ""))
        if self._guided_table.rowCount() > 0:
            try:
                self._guided_table.selectRow(0)
            except Exception:
                pass

    def _set_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_review_table"):
            return
        self._review_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._review_table.rowCount()
            self._review_table.insertRow(row_index)
            values = [
                str(row.get("result", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("object_label", "") or row.get("object_name", "") or ""),
                str(row.get("vertex_count", "") or ""),
                str(row.get("triangle_or_point_count", "") or ""),
                str(row.get("role", "") or ""),
                str(row.get("applied_section_summary", "") or ""),
                str(row.get("applied_section_diagnostics", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._review_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
            self._apply_review_row_style(row_index, str(row.get("status", "") or ""))
        preferred_index = preferred_corridor_build_review_row_index(list(rows or []))
        if preferred_index is not None:
            try:
                self._review_table.selectRow(int(preferred_index))
            except Exception:
                pass
        self._sync_visibility_checks()

    def _set_slope_face_issue_rows(self, rows: list[dict[str, str]]) -> None:
        if not hasattr(self, "_slope_issue_table"):
            return
        self._slope_issue_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._slope_issue_table.rowCount()
            self._slope_issue_table.insertRow(row_index)
            values = [
                str(row.get("station_label", "") or ""),
                str(row.get("side", "") or ""),
                str(row.get("reason", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("marker_object", "") or ""),
            ]
            for col, value in enumerate(values):
                self._slope_issue_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
            self._apply_slope_issue_row_style(row_index)
        if self._slope_issue_table.rowCount() > 0:
            try:
                self._slope_issue_table.selectRow(0)
            except Exception:
                pass

    def _set_drainage_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_drainage_table"):
            return
        self._drainage_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._drainage_table.rowCount()
            self._drainage_table.insertRow(row_index)
            station = row.get("station", "")
            station_text = "" if station == "" else f"{float(station):.3f}"
            values = [
                station_text,
                str(row.get("status", "") or ""),
                str(row.get("ditch_point_count", "") or "0"),
                str(row.get("left_count", "") or "0"),
                str(row.get("right_count", "") or "0"),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("marker_object", "") or ""))
                self._drainage_table.setItem(row_index, col, item)
            self._apply_drainage_row_style(row_index, str(row.get("status", "") or ""))

    def _set_region_boundary_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_region_table"):
            return
        self._region_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._region_table.rowCount()
            self._region_table.insertRow(row_index)
            start = row.get("station_start", "")
            end = row.get("station_end", "")
            values = [
                str(row.get("region_id", "") or ""),
                "" if start == "" else f"{float(start):.3f}",
                "" if end == "" else f"{float(end):.3f}",
                str(row.get("assembly", "") or ""),
                str(row.get("structure", "") or ""),
                str(row.get("drainage", "") or ""),
                str(row.get("surface_status", "") or ""),
                str(row.get("boundary_status", "") or ""),
                str(row.get("diagnostics", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("region_id", "") or ""))
                self._region_table.setItem(row_index, col, item)
            self._apply_region_boundary_row_style(row_index, str(row.get("boundary_status", "") or ""))
        if self._region_table.rowCount() > 0:
            try:
                self._region_table.selectRow(0)
            except Exception:
                pass
        self._sync_surface_transition_station_options_from_selected_region()

    def _refresh_region_boundary_rows(self) -> None:
        self._set_region_boundary_rows(corridor_region_boundary_rows(self.document))
        self._sync_surface_transition_station_options_from_selected_region()

    def _selected_region_id(self) -> str:
        table = getattr(self, "_region_table", None)
        if table is None:
            return ""
        row_index = -1
        try:
            rows = table.selectionModel().selectedRows()
            if rows:
                row_index = int(rows[0].row())
        except Exception:
            row_index = -1
        if row_index < 0:
            try:
                row_index = int(table.currentRow())
            except Exception:
                row_index = -1
        if row_index < 0:
            return ""
        item = table.item(row_index, 0)
        if item is None:
            return ""
        try:
            value = item.data(32)
            if value:
                return str(value)
        except Exception:
            pass
        return str(item.text() or "")

    def _sync_surface_transition_station_options_from_selected_region(self) -> None:
        self._set_surface_transition_boundary_options(
            corridor_surface_transition_boundary_options(self.document, region_id=self._selected_region_id())
        )

    def _set_surface_transition_boundary_options(self, options: list[dict[str, object]]) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None:
            return
        current_transition_id = ""
        try:
            current_transition_id = str(combo.itemData(combo.currentIndex()) or "")
        except Exception:
            current_transition_id = ""
        try:
            combo.blockSignals(True)
            combo.clear()
            for option in list(options or []):
                label = str(option.get("label", "") or "")
                transition_id = str(option.get("transition_id", "") or "")
                combo.addItem(label, transition_id)
            if combo.count() > 0:
                selected_index = 0
                if current_transition_id:
                    for index in range(combo.count()):
                        if str(combo.itemData(index) or "") == current_transition_id:
                            selected_index = index
                            break
                combo.setCurrentIndex(selected_index)
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass
        self._sync_selected_surface_transition_boundary_spacing()

    def _set_surface_transition_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_surface_transition_table"):
            return
        self._surface_transition_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._surface_transition_table.rowCount()
            self._surface_transition_table.insertRow(row_index)
            boundary = row.get("boundary_station", "")
            spacing = row.get("sample_interval", "")
            values = [
                str(row.get("transition_id", "") or ""),
                "yes" if bool(row.get("enabled", True)) else "no",
                "" if boundary == "" else f"{float(boundary):.3f}",
                "" if spacing == "" else f"{float(spacing):.3f}",
                str(row.get("sample_count", "") or ""),
                str(row.get("from_region_ref", "") or ""),
                str(row.get("to_region_ref", "") or ""),
                str(row.get("from_surface", "") or ""),
                str(row.get("to_surface", "") or ""),
                str(row.get("target_surfaces", "") or ""),
                str(row.get("transition_mode", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("diagnostics", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 0:
                    item.setData(32, str(row.get("transition_id", "") or ""))
                self._surface_transition_table.setItem(row_index, col, item)
            self._apply_surface_transition_row_style(row_index, str(row.get("status", "") or ""))
        if self._surface_transition_table.rowCount() > 0:
            try:
                self._surface_transition_table.selectRow(0)
            except Exception:
                pass
            self._sync_selected_surface_transition_row_controls()

    def _sync_selected_surface_transition_row_controls(self) -> None:
        if not hasattr(self, "_surface_transition_table"):
            return
        rows = self._surface_transition_table.selectionModel().selectedRows()
        if not rows:
            return
        row_index = int(rows[0].row())
        transition_item = self._surface_transition_table.item(row_index, 0)
        spacing_item = self._surface_transition_table.item(row_index, 3)
        transition_id = str(transition_item.text() if transition_item is not None else "")
        if transition_id:
            self._set_surface_transition_boundary_combo_transition(transition_id)
        try:
            spacing = float(spacing_item.text()) if spacing_item is not None and spacing_item.text() else SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL
            self._set_surface_transition_spacing_controls(spacing)
        except Exception:
            pass

    def _set_surface_transition_boundary_combo_transition(self, transition_id: str) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None:
            return
        target = str(transition_id or "")
        if not target:
            return
        for index in range(combo.count()):
            if str(combo.itemData(index) or "") == target:
                try:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(index)
                finally:
                    try:
                        combo.blockSignals(False)
                    except Exception:
                        pass
                return

    def _sync_selected_surface_transition_boundary_spacing(self) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None or combo.count() <= 0:
            return
        transition_id = str(combo.itemData(combo.currentIndex()) or "")
        for option in corridor_surface_transition_boundary_options(self.document, region_id=self._selected_region_id()):
            if str(option.get("transition_id", "") or "") == transition_id:
                self._set_surface_transition_spacing_controls(float(option.get("sample_interval", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL) or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL))
                return

    def _set_surface_transition_spacing_controls(self, sample_interval: float) -> None:
        combo = getattr(self, "_surface_transition_spacing_combo", None)
        spin = getattr(self, "_surface_transition_spacing_spin", None)
        value = max(0.1, float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL))
        if spin is not None:
            try:
                spin.blockSignals(True)
                spin.setValue(value)
            finally:
                try:
                    spin.blockSignals(False)
                except Exception:
                    pass
        if combo is not None:
            selected_index = combo.count() - 1
            for index in range(combo.count()):
                data = combo.itemData(index)
                if data is not None and abs(float(data) - value) <= 1.0e-9:
                    selected_index = index
                    break
            try:
                combo.blockSignals(True)
                combo.setCurrentIndex(max(0, selected_index))
            finally:
                try:
                    combo.blockSignals(False)
                except Exception:
                    pass
        self._sync_surface_transition_custom_spacing_state()

    def _sync_surface_transition_custom_spacing_state(self) -> None:
        combo = getattr(self, "_surface_transition_spacing_combo", None)
        spin = getattr(self, "_surface_transition_spacing_spin", None)
        if combo is None or spin is None:
            return
        try:
            spin.setEnabled(combo.itemData(combo.currentIndex()) is None)
        except Exception:
            pass

    def _surface_transition_spacing_value(self) -> float:
        combo = getattr(self, "_surface_transition_spacing_combo", None)
        spin = getattr(self, "_surface_transition_spacing_spin", None)
        if combo is not None:
            try:
                data = combo.itemData(combo.currentIndex())
                if data is not None:
                    return max(0.1, float(data))
            except Exception:
                pass
        if spin is not None:
            return max(0.1, float(spin.value()))
        return SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL

    def _show_selected_region_boundary_row(self) -> None:
        rows = self._region_table.selectionModel().selectedRows() if hasattr(self, "_region_table") else []
        if not rows:
            _show_message(self.form, "Build Corridor", "Select one Region row first.")
            return
        self._show_region_boundary_row(int(rows[0].row()))

    def _show_region_boundary_row(self, row_index: int) -> None:
        try:
            rows = corridor_region_boundary_rows(self.document)
            row = rows[int(row_index)]
            obj = focus_corridor_region_boundary_row(self.document, int(row_index))
            self._sync_visibility_checks()
            try:
                self._region_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Region surface object selected.",
                        f"Region: {row.get('region_id', '')}",
                        f"Station: {float(row.get('station_start', 0.0) or 0.0):.3f} -> {float(row.get('station_end', 0.0) or 0.0):.3f}",
                        f"Boundary: {row.get('boundary_status', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Region surface object was not selected.\n{exc}")

    def _create_transition_from_selected_region_boundary(self) -> None:
        rows = self._region_table.selectionModel().selectedRows() if hasattr(self, "_region_table") else []
        if not rows:
            _show_message(self.form, "Build Corridor", "Select one Region row first.")
            return
        try:
            row_index = int(rows[0].row())
            obj = create_corridor_surface_transition_from_region_boundary(
                self.document,
                row_index,
                sample_interval=self._surface_transition_spacing_value(),
            )
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            transition_rows = corridor_surface_transition_rows(self.document)
            if transition_rows:
                self._surface_transition_table.selectRow(max(0, len(transition_rows) - 1))
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Surface Transition range stored.",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                        "Source: Build Corridor Region boundary review.",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Surface Transition range was not created.\n{exc}")

    def _create_transition_from_selected_boundary_option(self) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None or combo.count() <= 0:
            _show_message(self.form, "Build Corridor", "No Region boundary station is available.")
            return
        try:
            boundary_index = int(combo.currentIndex())
            spacing = self._surface_transition_spacing_value()
            obj = create_or_update_corridor_surface_transition_for_boundary(
                self.document,
                boundary_index,
                sample_interval=spacing,
                region_id=self._selected_region_id(),
            )
            self._sync_surface_transition_station_options_from_selected_region()
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            transition_id = str(combo.itemData(combo.currentIndex()) or "")
            self._set_surface_transition_boundary_combo_transition(transition_id)
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Surface Transition spacing stored.",
                        f"Boundary: {combo.currentText()}",
                        f"Spacing: {spacing:.3f} m",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Surface Transition spacing was not stored.\n{exc}")

    def _toggle_selected_surface_transition(self) -> None:
        rows = self._surface_transition_table.selectionModel().selectedRows() if hasattr(self, "_surface_transition_table") else []
        if not rows:
            _show_message(self.form, "Build Corridor", "Select one Surface Transition row first.")
            return
        try:
            obj = toggle_corridor_surface_transition_enabled(self.document, int(rows[0].row()))
            self._set_surface_transition_rows(corridor_surface_transition_rows(self.document))
            self._sync_surface_transition_station_options_from_selected_region()
            self._surface_transition_table.selectRow(int(rows[0].row()))
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Surface Transition enabled state updated.",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Surface Transition range was not updated.\n{exc}")

    def _show_drainage_review_row(self, row_index: int) -> None:
        try:
            rows = corridor_drainage_review_rows(self.document)
            row = rows[int(row_index)]
            obj = focus_corridor_drainage_review_row(self.document, int(row_index))
            self._sync_visibility_checks()
            try:
                self._drainage_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Drainage diagnostic marker shown.",
                        f"Station: {float(row.get('station', 0.0) or 0.0):.3f}" if row.get("station", "") != "" else "Station: n/a",
                        f"Status: {row.get('status', '')}",
                        f"Points: {row.get('ditch_point_count', 0)}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Drainage diagnostic marker was not shown.\n{exc}")

    def _show_slope_face_issue_row(self, row_index: int) -> None:
        try:
            issue_rows = corridor_slope_face_issue_rows(self.document)
            issue = issue_rows[int(row_index)]
            obj = focus_corridor_slope_face_issue(self.document, int(row_index))
            self._sync_visibility_checks()
            try:
                self._slope_issue_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Slope Face issue marker shown.",
                        f"Station: {issue.get('station_label', '')}",
                        f"Side: {issue.get('side', '')}",
                        f"Reason: {issue.get('reason', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Slope Face issue was not shown.\n{exc}")

    def _focus_adjacent_slope_face_issue(self, direction: int) -> None:
        try:
            current_index = self._selected_slope_face_issue_row_index()
            target_index, obj = focus_adjacent_corridor_slope_face_issue(
                self.document,
                current_index=current_index,
                direction=direction,
            )
            issue = corridor_slope_face_issue_rows(self.document)[target_index]
            self._sync_visibility_checks()
            try:
                self._slope_issue_table.selectRow(int(target_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Slope Face issue marker shown.",
                        f"Issue: {target_index + 1} / {len(corridor_slope_face_issue_rows(self.document))}",
                        f"Station: {issue.get('station_label', '')}",
                        f"Side: {issue.get('side', '')}",
                        f"Reason: {issue.get('reason', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Slope Face issue was not shown.\n{exc}")

    def _selected_slope_face_issue_row_index(self) -> int:
        rows = self._slope_issue_table.selectionModel().selectedRows() if hasattr(self, "_slope_issue_table") else []
        if not rows:
            return -1
        return int(rows[0].row())

    def _show_selected_row(self) -> None:
        rows = self._review_table.selectionModel().selectedRows() if hasattr(self, "_review_table") else []
        if not rows:
            _show_message(self.form, "Build Corridor", "Select one review row first.")
            return
        self._show_review_row(int(rows[0].row()))

    def _show_review_row(self, row_index: int) -> None:
        try:
            obj = show_corridor_build_review_object(self.document, int(row_index))
            self._summary.setPlainText(f"Review object shown.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Review object was not shown.\n{exc}")

    def _focus_guided_review_row(self, row_index: int) -> None:
        try:
            item = self._guided_table.item(int(row_index), 0)
            step_id = str(item.data(32) if item is not None else "")
            obj = focus_corridor_build_guided_review_step(self.document, step_id)
            self._sync_visibility_checks()
            self._summary.setPlainText(
                f"Guided review step focused.\nStep: {step_id}\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}"
            )
        except Exception as exc:
            _show_message(self.form, "Build Corridor", f"Guided review step was not focused.\n{exc}")

    def _set_preview_visibility(self, role: str, visible: bool) -> None:
        obj = set_corridor_build_preview_visibility(self.document, role, visible)
        if obj is None:
            return
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Preview {state}.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")

    def _set_daylight_contact_marker_visibility(self, visible: bool) -> None:
        obj = set_corridor_build_daylight_contact_marker_visibility(self.document, visible)
        if obj is None:
            return
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Daylight contact markers {state}.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")

    def _set_all_preview_visibility(self, visible: bool) -> None:
        count = set_all_corridor_build_preview_visibility(self.document, visible, include_issue_markers=True)
        self._sync_visibility_checks()
        state = "shown" if visible else "hidden"
        self._summary.setPlainText(f"Corridor previews {state}.\nObjects updated: {count}")

    def _sync_visibility_checks(self) -> None:
        if not hasattr(self, "_visibility_checks"):
            return
        for role, check in dict(self._visibility_checks).items():
            obj = _corridor_build_preview_object(self.document, role)
            enabled = obj is not None
            visible = _object_visibility(obj) if obj is not None else False
            try:
                check.blockSignals(True)
                check.setEnabled(enabled)
                check.setChecked(bool(visible))
            finally:
                try:
                    check.blockSignals(False)
                except Exception:
                    pass
        self._sync_daylight_contact_marker_check()

    def _sync_daylight_contact_marker_check(self) -> None:
        check = getattr(self, "_daylight_contact_marker_check", None)
        if check is None:
            return
        obj = _corridor_build_daylight_contact_marker_object(self.document)
        if obj is None:
            return
        try:
            check.blockSignals(True)
            check.setChecked(_object_visibility(obj))
        finally:
            try:
                check.blockSignals(False)
            except Exception:
                pass

    def _show_daylight_contact_markers(self) -> bool:
        check = getattr(self, "_daylight_contact_marker_check", None)
        if check is None:
            return True
        try:
            return bool(check.isChecked())
        except Exception:
            return True

    def _show_preferred_review_row(self, rows: list[dict[str, object]]):
        row_index = preferred_corridor_build_review_row_index(rows)
        if row_index is None:
            return None
        try:
            return show_corridor_build_review_object(self.document, int(row_index))
        except Exception:
            return None

    def _apply_review_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color(status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._review_table.columnCount())):
                item = self._review_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_guided_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") == "warn" else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._guided_table.columnCount())):
                item = self._guided_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_slope_issue_row_style(self, row_index: int) -> None:
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_ROW_COLORS["empty"]))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._slope_issue_table.columnCount())):
                item = self._slope_issue_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_drainage_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") == "warn" else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._drainage_table.columnCount())):
                item = self._drainage_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_region_boundary_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") == "warn" else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._region_table.columnCount())):
                item = self._region_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass

    def _apply_surface_transition_row_style(self, row_index: int, status: str) -> None:
        color_key = "missing" if str(status or "") == "disabled" else "empty" if str(status or "") in {"warn", "draft"} else "ready"
        if str(status or "") == "error":
            color_key = "empty"
        color = corridor_build_review_row_color(color_key)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._surface_transition_table.columnCount())):
                item = self._surface_transition_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass


def _compact_build_corridor_table(table, column_widths: list[int]) -> None:
    """Keep Build Corridor tables from forcing a very wide task panel."""

    if table is None:
        return
    try:
        table.setMinimumWidth(0)
        table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        table.setWordWrap(False)
    except Exception:
        pass
    try:
        header = table.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setDefaultSectionSize(90)
        for index, width in enumerate(list(column_widths or [])):
            table.setColumnWidth(index, int(width))
    except Exception:
        pass


def _hide_applied_section_set_review_shape(document) -> bool:
    """Hide source AppliedSectionSet review wires while Build Corridor output is being reviewed."""

    obj = find_v1_applied_section_set(document)
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return False
    try:
        vobj.Visibility = False
        return True
    except Exception:
        return False


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def corridor_build_review_row_color(status: object) -> tuple[int, int, int] | None:
    """Return the dark-theme-readable review-row background color for a status."""

    return CORRIDOR_BUILD_REVIEW_ROW_COLORS.get(str(status or "").strip())


def corridor_applied_sections_review_summary(document=None) -> dict[str, object]:
    """Summarize Applied Sections as the source context for Build Corridor rows."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return {
            "status": "missing",
            "summary": "Applied Sections: missing",
            "diagnostics": "Run Applied Sections before Build Corridor.",
            "station_count": 0,
            "diagnostic_count": 0,
        }
    station_rows = list(getattr(applied, "station_rows", []) or [])
    sections = list(getattr(applied, "sections", []) or [])
    stations = []
    for row in station_rows:
        try:
            stations.append(float(getattr(row, "station", 0.0) or 0.0))
        except Exception:
            pass
    diagnostic_count = sum(len(list(getattr(section, "diagnostic_rows", []) or [])) for section in sections)
    ditch_point_count = sum(
        1
        for section in sections
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    )
    slope_face_count = sum(
        1
        for section in sections
        if float(getattr(section, "daylight_left_width", 0.0) or 0.0) > 0.0
        or float(getattr(section, "daylight_right_width", 0.0) or 0.0) > 0.0
    )
    region_count = len({str(getattr(section, "region_id", "") or "") for section in sections if str(getattr(section, "region_id", "") or "")})
    assembly_count = len({str(getattr(section, "assembly_id", "") or "") for section in sections if str(getattr(section, "assembly_id", "") or "")})
    structure_refs = {
        ref
        for section in sections
        for ref in [_first_active_structure_ref(section)]
        if ref
    }
    structure_count = len(structure_refs)
    station_range = f"{min(stations):.3f}->{max(stations):.3f}" if stations else "no stations"
    summary = (
        f"{len(station_rows)} STA | {station_range} | "
        f"regions:{region_count} | assemblies:{assembly_count} | structures:{structure_count} | "
        f"ditch_pts:{ditch_point_count} | slope_rows:{slope_face_count}"
    )
    diagnostics = f"{diagnostic_count} diagnostic(s)" if diagnostic_count else "ok"
    return {
        "status": "warn" if diagnostic_count else "ok",
        "summary": summary,
        "diagnostics": diagnostics,
        "station_count": len(station_rows),
        "station_range": station_range,
        "diagnostic_count": diagnostic_count,
        "ditch_point_count": ditch_point_count,
        "slope_face_count": slope_face_count,
        "region_count": region_count,
        "assembly_count": assembly_count,
        "structure_count": structure_count,
        "structure_refs": sorted(structure_refs),
    }


def _first_active_structure_ref(section) -> str:
    for value in list(getattr(section, "active_structure_ids", []) or []):
        text = str(value or "").strip()
        if text:
            return text
    for component in list(getattr(section, "component_rows", []) or []):
        for value in list(getattr(component, "structure_ids", []) or []):
            text = str(value or "").strip()
            if text:
                return text
    return ""


def _format_structure_review_summary(applied_summary: dict[str, object]) -> str:
    refs = list(applied_summary.get("structure_refs", []) or [])
    if refs:
        return f"{len(refs)} active ({', '.join(str(value) for value in refs[:3])})"
    return "none"


def _station_ordered_applied_sections(applied_section_set) -> list[object]:
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    output: list[object] = []
    for row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda item: float(getattr(item, "station", 0.0) or 0.0),
    ):
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None:
            output.append(section)
    if output:
        return output
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=lambda section: _section_station(section))


def _contiguous_region_groups(sections: list[object]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for section in list(sections or []):
        region_id = _section_region_id(section)
        if not groups or str(groups[-1].get("region_id", "") or "") != region_id:
            groups.append({"region_id": region_id, "sections": [section]})
        else:
            groups[-1]["sections"].append(section)
    for group in groups:
        group_sections = list(group.get("sections", []) or [])
        stations = [_section_station(section) for section in group_sections]
        group["station_start"] = min(stations) if stations else 0.0
        group["station_end"] = max(stations) if stations else 0.0
    return groups


def _region_source_rows(region_model) -> list[object]:
    if region_model is None:
        return []
    rows = [
        row
        for row in list(getattr(region_model, "region_rows", []) or [])
        if str(getattr(row, "region_id", "") or "").strip()
    ]
    return sorted(
        rows,
        key=lambda row: (
            float(getattr(row, "station_start", 0.0) or 0.0),
            float(getattr(row, "station_end", 0.0) or 0.0),
            int(getattr(row, "region_index", 0) or 0),
            str(getattr(row, "region_id", "") or ""),
        ),
    )


def _region_boundary_rows_from_source_regions(source_rows: list[object], sections: list[object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    section_groups = [
        _sections_for_source_region_row(sections, row)
        for row in list(source_rows or [])
    ]
    for index, source_row in enumerate(list(source_rows or [])):
        group_sections = section_groups[index]
        first = group_sections[0] if group_sections else None
        last = group_sections[-1] if group_sections else None
        diagnostics: list[dict[str, str]] = []
        diagnostics.extend(_region_source_range_diagnostics(source_rows, index))
        diagnostics.extend(_region_sample_coverage_diagnostics(source_row, group_sections))
        if index > 0:
            previous_last = section_groups[index - 1][-1] if section_groups[index - 1] else None
            diagnostics.extend(_region_boundary_diagnostics(previous_last, first, boundary_side="start"))
        if index < len(source_rows) - 1:
            next_first = section_groups[index + 1][0] if section_groups[index + 1] else None
            diagnostics.extend(_region_boundary_diagnostics(last, next_first, boundary_side="end"))
        boundary_status = _region_boundary_status(diagnostics)
        rows.append(
            {
                "region_id": str(getattr(source_row, "region_id", "") or ""),
                "station_start": float(getattr(source_row, "station_start", 0.0) or 0.0),
                "station_end": float(getattr(source_row, "station_end", 0.0) or 0.0),
                "assembly": str(getattr(source_row, "assembly_ref", "") or "") or _unique_join(_section_text_values(group_sections, "assembly_id")),
                "structure": _unique_join(list(getattr(source_row, "structure_refs", []) or [])) or _unique_join(_section_structure_values(group_sections)) or "-",
                "drainage": _unique_join(list(getattr(source_row, "drainage_refs", []) or [])) or _region_group_drainage_summary(group_sections),
                "surface_status": _region_group_surface_status(group_sections),
                "boundary_status": boundary_status,
                "diagnostics": _region_boundary_diagnostic_summary(diagnostics),
                "diagnostic_count": len(diagnostics),
            }
        )
    return rows


def _sections_for_source_region_row(sections: list[object], source_row) -> list[object]:
    region_id = str(getattr(source_row, "region_id", "") or "")
    try:
        start = float(getattr(source_row, "station_start", 0.0) or 0.0)
        end = float(getattr(source_row, "station_end", start) or start)
    except Exception:
        start = 0.0
        end = 0.0
    low = min(start, end)
    high = max(start, end)
    tolerance = 1.0e-6
    rows = [
        section
        for section in list(sections or [])
        if _section_region_id(section) == region_id
        and low - tolerance <= _section_station(section) <= high + tolerance
    ]
    return sorted(rows, key=lambda section: _section_station(section))


def _region_source_range_diagnostics(source_rows: list[object], row_index: int) -> list[dict[str, str]]:
    rows = list(source_rows or [])
    if row_index < 0 or row_index >= len(rows):
        return []
    diagnostics: list[dict[str, str]] = []
    current = rows[row_index]
    start = float(getattr(current, "station_start", 0.0) or 0.0)
    end = float(getattr(current, "station_end", 0.0) or 0.0)
    tolerance = 1.0e-6
    if row_index > 0:
        previous = rows[row_index - 1]
        previous_end = float(getattr(previous, "station_end", 0.0) or 0.0)
        if previous_end < start - tolerance:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "region_source_gap_before",
                    f"STA {previous_end:.3f}->{start:.3f}: source Region gap before this row.",
                    "start",
                )
            )
        elif previous_end > start + tolerance:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "region_source_overlap_before",
                    f"STA {start:.3f}->{previous_end:.3f}: source Region rows overlap before this row.",
                    "start",
                )
            )
    if row_index < len(rows) - 1:
        next_row = rows[row_index + 1]
        next_start = float(getattr(next_row, "station_start", 0.0) or 0.0)
        if end < next_start - tolerance:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "region_source_gap_after",
                    f"STA {end:.3f}->{next_start:.3f}: source Region gap after this row.",
                    "end",
                )
            )
        elif end > next_start + tolerance:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "region_source_overlap_after",
                    f"STA {next_start:.3f}->{end:.3f}: source Region rows overlap after this row.",
                    "end",
                )
            )
    return diagnostics


def _region_sample_coverage_diagnostics(source_row, sections: list[object]) -> list[dict[str, str]]:
    start = float(getattr(source_row, "station_start", 0.0) or 0.0)
    end = float(getattr(source_row, "station_end", 0.0) or 0.0)
    low = min(start, end)
    high = max(start, end)
    ordered = sorted(list(sections or []), key=lambda section: _section_station(section))
    if not ordered:
        return [
            _region_boundary_diagnostic(
                "warning",
                "region_sample_missing",
                f"STA {low:.3f}->{high:.3f}: no Applied Section samples exist inside this Region.",
                "range",
            )
        ]
    diagnostics: list[dict[str, str]] = []
    first_station = _section_station(ordered[0])
    last_station = _section_station(ordered[-1])
    tolerance = 1.0e-6
    if first_station > low + tolerance:
        diagnostics.append(
            _region_boundary_diagnostic(
                "warning",
                "region_sample_start_gap",
                f"STA {low:.3f}->{first_station:.3f}: Applied Section samples are missing at the Region start.",
                "start",
            )
        )
    if last_station < high - tolerance:
        diagnostics.append(
            _region_boundary_diagnostic(
                "warning",
                "region_sample_end_gap",
                f"STA {last_station:.3f}->{high:.3f}: Applied Section samples are missing at the Region end.",
                "end",
            )
        )
    return diagnostics


def _section_region_id(section) -> str:
    return str(getattr(section, "region_id", "") or "(unassigned)")


def _section_station(section) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
    except Exception:
        try:
            return float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            return 0.0


def _section_text_values(sections: list[object], attr: str) -> list[str]:
    values: list[str] = []
    for section in list(sections or []):
        text = str(getattr(section, attr, "") or "").strip()
        if text:
            values.append(text)
    return values


def _section_structure_values(sections: list[object]) -> list[str]:
    values: list[str] = []
    for section in list(sections or []):
        values.extend(
            str(value or "").strip()
            for value in list(getattr(section, "active_structure_ids", []) or [])
            if str(value or "").strip()
        )
    return values


def _unique_join(values: list[str], *, max_items: int = 3) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    if not output:
        return ""
    clipped = output[: max(1, int(max_items))]
    if len(output) > len(clipped):
        clipped.append(f"+{len(output) - len(clipped)}")
    return ", ".join(clipped)


def _unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _surface_transition_region_surface_contexts(applied_section_set) -> dict[str, str]:
    if applied_section_set is None:
        return {}
    groups: dict[str, list[object]] = {}
    for section in _station_ordered_applied_sections(applied_section_set):
        region_id = _section_region_id(section)
        if not region_id:
            continue
        groups.setdefault(region_id, []).append(section)
    return {region_id: _region_surface_context_summary(sections) for region_id, sections in groups.items()}


def _region_surface_context_summary(sections: list[object]) -> str:
    if not sections:
        return "surface:missing"
    left_values = [_float_attr(section, "surface_left_width") for section in sections]
    right_values = [_float_attr(section, "surface_right_width") for section in sections]
    subgrade_values = [_float_attr(section, "subgrade_depth") for section in sections]
    daylight_values = [
        max(_float_attr(section, "daylight_left_width"), _float_attr(section, "daylight_right_width"))
        for section in sections
    ]
    role_names = sorted(
        {
            role
            for section in sections
            for role, count in _surface_point_role_counts(section).items()
            if count
        }
    )
    return (
        f"FG L {_range_summary(left_values)} / R {_range_summary(right_values)}; "
        f"SG {_range_summary(subgrade_values)}; DL {_range_summary(daylight_values)}; "
        f"roles {_unique_join(role_names, max_items=2) or '-'}"
    )


def _range_summary(values: list[float]) -> str:
    clean = [float(value) for value in list(values or [])]
    if not clean:
        return "-"
    low = min(clean)
    high = max(clean)
    if abs(high - low) <= 1.0e-9:
        return f"{low:.2f}"
    return f"{low:.2f}-{high:.2f}"


def _surface_transition_known_region_refs(region_rows: list[dict[str, object]]) -> list[str]:
    return [
        str(row.get("region_id", "") or "")
        for row in list(region_rows or [])
        if str(row.get("region_id", "") or "")
    ]


def _surface_transition_boundary_stations(region_rows: list[dict[str, object]]) -> list[float]:
    stations: list[float] = []
    rows = list(region_rows or [])
    for index in range(len(rows) - 1):
        try:
            stations.append(float(rows[index].get("station_end", 0.0) or 0.0))
        except Exception:
            continue
    return stations


def _surface_transition_boundary_from_region_row(region_rows: list[dict[str, object]], row_index: int) -> dict[str, object]:
    rows = [row for row in list(region_rows or []) if str(row.get("region_id", "") or "")]
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Region boundary row index is out of range.")
    if len(rows) < 2:
        raise RuntimeError("At least two Region rows are required to create a Surface Transition.")
    current = rows[row_index]
    if row_index < len(rows) - 1:
        next_row = rows[row_index + 1]
        return {
            "from_region_ref": str(current.get("region_id", "") or ""),
            "to_region_ref": str(next_row.get("region_id", "") or ""),
            "boundary_station": float(current.get("station_end", 0.0) or 0.0),
        }
    previous = rows[row_index - 1]
    return {
        "from_region_ref": str(previous.get("region_id", "") or ""),
        "to_region_ref": str(current.get("region_id", "") or ""),
        "boundary_station": float(current.get("station_start", 0.0) or 0.0),
    }


def _region_boundary_station_candidates(region_rows: list[dict[str, object]], region_id: str = "") -> list[tuple[float, str]]:
    selected = str(region_id or "").strip()
    candidates: list[tuple[float, str]] = []
    for row in list(region_rows or []):
        row_region = str(row.get("region_id", "") or "")
        if not row_region or (selected and row_region != selected):
            continue
        for key in ("station_start", "station_end"):
            try:
                candidates.append((float(row.get(key, 0.0) or 0.0), row_region))
            except Exception:
                continue
    return candidates


def _surface_transition_context_for_region_station(
    region_rows: list[dict[str, object]],
    region_ref: str,
    station: float,
) -> dict[str, object]:
    """Resolve whether a Region station is local or hands off to an adjacent Region."""

    region = str(region_ref or "")
    rows = [row for row in list(region_rows or []) if str(row.get("region_id", "") or "")]
    fallback = {"from_region_ref": region, "to_region_ref": region, "boundary_station": float(station)}
    if not region:
        return fallback
    value = float(station)
    tolerance = 1.0e-6
    for index, row in enumerate(rows):
        row_region = str(row.get("region_id", "") or "")
        if row_region != region:
            continue
        try:
            start = float(row.get("station_start", 0.0) or 0.0)
            end = float(row.get("station_end", 0.0) or 0.0)
        except Exception:
            continue
        if value < min(start, end) - tolerance or value > max(start, end) + tolerance:
            continue
        if abs(value - end) <= tolerance and index < len(rows) - 1:
            next_region = str(rows[index + 1].get("region_id", "") or "")
            if next_region:
                return {"from_region_ref": region, "to_region_ref": next_region, "boundary_station": value}
        if abs(value - start) <= tolerance and index > 0:
            previous_region = str(rows[index - 1].get("region_id", "") or "")
            if previous_region:
                return {"from_region_ref": previous_region, "to_region_ref": region, "boundary_station": value}
        return fallback
    return fallback


def _surface_transition_id(from_region_ref: object, to_region_ref: object, boundary_station: float) -> str:
    return f"surface-transition:{from_region_ref}->{to_region_ref}@{float(boundary_station):.3f}"


def _surface_transition_row_status(transition, diagnostics: list[object]) -> str:
    if not bool(getattr(transition, "enabled", True)):
        return "disabled"
    if any(str(getattr(row, "severity", "") or "") == "error" for row in list(diagnostics or [])):
        return "error"
    if diagnostics:
        return "warn"
    return str(getattr(transition, "approval_status", "") or "draft")


def _surface_transition_sample_count(station_start: float, station_end: float, sample_interval: float) -> int:
    length = abs(float(station_end) - float(station_start))
    interval = max(0.1, float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL))
    return int(length / interval) + 1


def _surface_transition_diagnostic_summary(diagnostics: list[object], *, max_items: int = 2) -> str:
    rows = list(diagnostics or [])
    if not rows:
        return "ok"
    labels = []
    for row in rows[: max(1, int(max_items))]:
        kind = str(getattr(row, "kind", "") or "diagnostic")
        severity = str(getattr(row, "severity", "") or "info")
        labels.append(f"{severity}:{kind}")
    if len(rows) > len(labels):
        labels.append(f"+{len(rows) - len(labels)}")
    return "; ".join(labels)


def _surface_transition_review_diagnostic_summary(validation_diagnostics: list[object], generation_diagnostics: list[str]) -> str:
    parts: list[str] = []
    validation_summary = _surface_transition_diagnostic_summary(validation_diagnostics)
    if validation_summary and validation_summary != "ok":
        parts.append(validation_summary)
    generation_rows = list(generation_diagnostics or [])
    if generation_rows:
        labels = []
        for row in generation_rows[:2]:
            labels.append(_surface_transition_generation_diagnostic_label(row))
        if len(generation_rows) > len(labels):
            labels.append(f"+{len(generation_rows) - len(labels)}")
        parts.append("; ".join(labels))
    return "ok" if not parts else " | ".join(parts)


def _surface_transition_generation_diagnostic_label(row: str) -> str:
    parts = str(row or "").split("|", 3)
    if len(parts) >= 4:
        return f"{parts[0]}:{parts[1]}"
    return str(row or "")


def _surface_transition_generation_diagnostics(
    applied_section_set,
    transition_model,
    *,
    transition_id: str,
    target_surface_kinds: list[str],
) -> list[str]:
    if applied_section_set is None or transition_model is None:
        return []
    diagnostics: list[str] = []
    for surface_kind in list(target_surface_kinds or []):
        try:
            augmented = transition_augmented_applied_section_set(
                applied_section_set,
                surface_transition_model=transition_model,
                surface_kind=str(surface_kind or ""),
            )
        except Exception:
            continue
        for section in list(getattr(augmented, "sections", []) or []):
            section_id = str(getattr(section, "applied_section_id", "") or "")
            if str(transition_id or "") not in section_id:
                continue
            for diagnostic in list(getattr(section, "structure_diagnostic_rows", []) or []):
                text = str(diagnostic or "")
                if "surface_transition_role_skipped" in text and text not in diagnostics:
                    diagnostics.append(text)
    return diagnostics


def _surface_transition_span_marker_points(applied_section_set, surface_model) -> tuple[list[tuple[float, float, float]], list[str]]:
    if applied_section_set is None or surface_model is None:
        return [], []
    sections = _station_ordered_applied_sections(applied_section_set)
    if len(sections) < 2:
        return [], []
    points: list[tuple[float, float, float]] = []
    refs: list[str] = []
    seen: set[tuple[str, float, float]] = set()
    for span in list(getattr(surface_model, "span_rows", []) or []):
        transition_ref = str(getattr(span, "transition_ref", "") or "")
        if not transition_ref:
            continue
        try:
            station_start = float(getattr(span, "station_start", 0.0) or 0.0)
            station_end = float(getattr(span, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        key = (transition_ref, round(station_start, 6), round(station_end, 6))
        if key in seen:
            continue
        seen.add(key)
        point = _surface_transition_span_marker_point(sections, (station_start + station_end) * 0.5)
        if point is None:
            continue
        points.append(point)
        refs.append(transition_ref)
    return points, refs


def _surface_transition_span_marker_point(sections: list[object], station: float) -> tuple[float, float, float] | None:
    if not sections:
        return None
    ordered = sorted(list(sections or []), key=lambda section: _section_station(section))
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = _section_station(first)
        second_station = _section_station(second)
        if min(first_station, second_station) - 1.0e-9 <= float(station) <= max(first_station, second_station) + 1.0e-9:
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (float(station) - first_station) / (second_station - first_station)
            return _interpolate_section_frame_point(getattr(first, "frame", None), getattr(second, "frame", None), ratio, z_offset=0.75)
    nearest = min(ordered, key=lambda section: abs(_section_station(section) - float(station)))
    frame = getattr(nearest, "frame", None)
    if frame is None:
        return None
    return (
        float(getattr(frame, "x", 0.0) or 0.0),
        float(getattr(frame, "y", 0.0) or 0.0),
        float(getattr(frame, "z", 0.0) or 0.0) + 0.75,
    )


def _interpolate_section_frame_point(first_frame, second_frame, ratio: float, *, z_offset: float = 0.0) -> tuple[float, float, float] | None:
    if first_frame is None and second_frame is None:
        return None
    if first_frame is None:
        first_frame = second_frame
    if second_frame is None:
        second_frame = first_frame
    t = max(0.0, min(1.0, float(ratio)))
    return (
        _lerp_value(getattr(first_frame, "x", 0.0), getattr(second_frame, "x", 0.0), t),
        _lerp_value(getattr(first_frame, "y", 0.0), getattr(second_frame, "y", 0.0), t),
        _lerp_value(getattr(first_frame, "z", 0.0), getattr(second_frame, "z", 0.0), t) + float(z_offset or 0.0),
    )


def _lerp_value(first, second, ratio: float) -> float:
    return float(first or 0.0) + (float(second or 0.0) - float(first or 0.0)) * float(ratio)


def _region_group_drainage_summary(sections: list[object]) -> str:
    ditch_count = sum(
        1
        for section in list(sections or [])
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    )
    if ditch_count:
        return f"ditch points: {ditch_count}"
    return "-"


def _region_group_surface_status(sections: list[object]) -> str:
    if not sections:
        return "missing"
    return "ready" if all(getattr(section, "frame", None) is not None for section in sections) else "warn"


def _region_boundary_diagnostics(left, right, *, boundary_side: str) -> list[dict[str, str]]:
    if left is None or right is None:
        return []
    diagnostics: list[dict[str, str]] = []
    left_station = _section_station(left)
    right_station = _section_station(right)
    station_text = f"STA {left_station:.3f}->{right_station:.3f}"
    left_region = _section_region_id(left)
    right_region = _section_region_id(right)
    if left_region != right_region:
        diagnostics.append(
            _region_boundary_diagnostic(
                "info",
                "region_context_change",
                f"{station_text}: {left_region} -> {right_region}.",
                boundary_side,
            )
        )
    for attr, label, threshold, kind in (
        ("surface_left_width", "left design width", REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD, "region_boundary_width_jump"),
        ("surface_right_width", "right design width", REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD, "region_boundary_width_jump"),
        ("subgrade_depth", "subgrade depth", REGION_BOUNDARY_SUBGRADE_JUMP_THRESHOLD, "region_boundary_subgrade_jump"),
        ("daylight_left_width", "left daylight width", REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD, "region_boundary_daylight_width_jump"),
        ("daylight_right_width", "right daylight width", REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD, "region_boundary_daylight_width_jump"),
        ("daylight_left_slope", "left daylight slope", REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD, "region_boundary_daylight_slope_jump"),
        ("daylight_right_slope", "right daylight slope", REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD, "region_boundary_daylight_slope_jump"),
    ):
        delta = abs(_float_attr(right, attr) - _float_attr(left, attr))
        if delta > threshold + 1.0e-9:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    kind,
                    f"{station_text}: {label} changes by {delta:.3f}.",
                    boundary_side,
                )
            )
    left_roles = _surface_point_role_counts(left)
    right_roles = _surface_point_role_counts(right)
    if left_roles != right_roles:
        diagnostics.append(
            _region_boundary_diagnostic(
                "warning",
                "region_boundary_point_role_mismatch",
                f"{station_text}: surface point roles differ ({_role_count_summary(left_roles)} -> {_role_count_summary(right_roles)}).",
                boundary_side,
            )
        )
    for role, kind, label in (
        ("ditch_surface", "region_boundary_ditch_mismatch", "ditch"),
        ("bench_surface", "region_boundary_bench_mismatch", "bench"),
    ):
        left_count = left_roles.get(role, 0)
        right_count = right_roles.get(role, 0)
        if bool(left_count) != bool(right_count):
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    kind,
                    f"{station_text}: {label} rows exist on one side only ({left_count} -> {right_count}).",
                    boundary_side,
                )
            )
    left_structures = set(_section_structure_values([left]))
    right_structures = set(_section_structure_values([right]))
    if left_structures != right_structures:
        diagnostics.append(
            _region_boundary_diagnostic(
                "info",
                "region_boundary_structure_context_change",
                f"{station_text}: structure context changes ({_unique_join(sorted(left_structures)) or '-'} -> {_unique_join(sorted(right_structures)) or '-'}).",
                boundary_side,
            )
        )
    return diagnostics


def _region_boundary_diagnostic(severity: str, kind: str, message: str, boundary_side: str) -> dict[str, str]:
    return {
        "severity": str(severity or ""),
        "kind": str(kind or ""),
        "message": str(message or ""),
        "boundary_side": str(boundary_side or ""),
    }


def _float_attr(obj, attr: str) -> float:
    try:
        return float(getattr(obj, attr, 0.0) or 0.0)
    except Exception:
        return 0.0


def _surface_point_role_counts(section) -> dict[str, int]:
    roles = {"fg_surface", "subgrade_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"}
    counts = {role: 0 for role in roles}
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role in counts:
            counts[role] += 1
    return {role: count for role, count in counts.items() if count}


def _role_count_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{role}:{count}" for role, count in sorted(counts.items()))


def _region_boundary_status(diagnostics: list[dict[str, str]]) -> str:
    severities = {str(row.get("severity", "") or "") for row in list(diagnostics or [])}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warn"
    return "ready"


def _region_boundary_diagnostic_summary(diagnostics: list[dict[str, str]], *, max_items: int = 2) -> str:
    if not diagnostics:
        return "ok"
    warning_count = sum(1 for row in diagnostics if str(row.get("severity", "") or "") == "warning")
    info_count = sum(1 for row in diagnostics if str(row.get("severity", "") or "") == "info")
    messages = [str(row.get("message", "") or "") for row in diagnostics if str(row.get("severity", "") or "") != "info"]
    if not messages:
        messages = [str(row.get("message", "") or "") for row in diagnostics]
    clipped = [message for message in messages if message][: max(1, int(max_items))]
    suffix = ""
    if len(messages) > len(clipped):
        suffix = f"; +{len(messages) - len(clipped)} more"
    prefix = f"{warning_count} warning(s), {info_count} info"
    return f"{prefix}: {'; '.join(clipped)}{suffix}"


def _create_or_update_region_preview_objects(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    applied_section_set=None,
    row: dict[str, object],
    supplemental_sampling_enabled: bool = False,
):
    if document is None or corridor_model is None or applied_section_set is None:
        return []
    region_id = str(row.get("region_id", "") or "")
    start = float(row.get("station_start", 0.0) or 0.0)
    end = float(row.get("station_end", start) or start)
    all_sections = [
        section
        for section in _station_ordered_applied_sections(applied_section_set)
        if getattr(section, "frame", None) is not None
    ]
    region_sections = [
        section
        for section in all_sections
        if _section_region_id(section) == region_id
        and start - 1.0e-6 <= _section_station(section) <= end + 1.0e-6
    ]
    build_sections = _region_surface_build_sections(
        region_sections,
        station_start=start,
        station_end=end,
        all_sections=all_sections,
        region_id=region_id,
    )
    if len(build_sections) < 2:
        return []
    subset = _region_applied_section_subset(applied_section_set, region_id=region_id, sections=build_sections)
    objects: list[object] = []
    keep_names: set[str] = set()
    for spec in _region_surface_role_specs(region_id):
        obj = _create_or_update_region_surface_preview_object(
            document=document,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=subset,
            row=row,
            region_sections=build_sections,
            surface_role_spec=spec,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
        )
        if obj is not None:
            objects.append(obj)
            keep_names.add(str(getattr(obj, "Name", "") or ""))
        elif document.getObject(spec["object_name"]) is not None:
            _remove_preview_object(document, spec["object_name"])
    structure_obj = _create_or_update_region_structure_preview_object(
        document=document,
        project=project,
        corridor_model=corridor_model,
        row=row,
        region_sections=build_sections,
    )
    structure_name = _region_structure_preview_object_name(region_id)
    if structure_obj is not None:
        objects.append(structure_obj)
        keep_names.add(str(getattr(structure_obj, "Name", "") or ""))
    elif document.getObject(structure_name) is not None:
        _remove_preview_object(document, structure_name)
    return objects


def _create_or_update_region_surface_preview_object(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    applied_section_set=None,
    row: dict[str, object],
    region_sections: list[object],
    surface_role_spec: dict[str, object],
    supplemental_sampling_enabled: bool = False,
):
    if document is None or corridor_model is None or applied_section_set is None:
        return None
    region_id = str(row.get("region_id", "") or "")
    start = float(row.get("station_start", 0.0) or 0.0)
    end = float(row.get("station_end", start) or start)
    role = str(surface_role_spec.get("role", "") or "")
    object_name = str(surface_role_spec.get("object_name", "") or "")
    surface_id = f"{str(getattr(corridor_model, 'corridor_id', '') or 'corridor:main')}:region:{_safe_region_token(region_id)}:{role}"
    builder_name = str(surface_role_spec.get("builder", "") or "")
    builder = getattr(CorridorSurfaceGeometryService(), builder_name, None)
    if builder is None:
        return None
    try:
        request = CorridorDesignSurfaceGeometryRequest(
            project_id=_project_id(project or find_project(document)),
            corridor=corridor_model,
            applied_section_set=applied_section_set,
            surface_id=surface_id,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
            surface_transition_model=None,
        )
        if role == "daylight":
            request = replace(request, existing_ground_surface=_resolve_corridor_existing_ground_tin_surface(document))
        tin_surface = builder(
            request
        )
    except Exception:
        return None
    tin_surface = _offset_tin_surface_z(tin_surface, float(surface_role_spec.get("z_offset", REGION_SURFACE_DISPLAY_Z_OFFSET) or 0.0))
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        document,
        tin_surface,
        object_name=object_name,
        label_prefix=str(surface_role_spec.get("label_prefix", "Corridor Region Surface") or "Corridor Region Surface"),
        surface_role=str(surface_role_spec.get("style_role", "edited") or "edited"),
        recompute=False,
    )
    obj = document.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if obj is None:
        return None
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_region_surface_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorRegionSurface")
    _set_preview_property(obj, "RegionRef", region_id)
    _set_preview_property(obj, "RegionObjectRole", role)
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_property(obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
    _set_preview_float_property(obj, "StationStart", start)
    _set_preview_float_property(obj, "StationEnd", end)
    _set_preview_integer_property(obj, "SectionCount", len(region_sections))
    _set_preview_integer_property(obj, "SurfaceFaceCount", int(getattr(obj, "TriangleCount", 0) or 0))
    _set_preview_float_property(obj, "DisplayZOffset", float(surface_role_spec.get("z_offset", REGION_SURFACE_DISPLAY_Z_OFFSET) or 0.0))
    _set_preview_property(obj, "BoundaryStatus", str(row.get("boundary_status", "") or ""))
    _set_preview_property(obj, "BoundaryDiagnostics", str(row.get("diagnostics", "") or ""))
    try:
        obj.Label = f"Corridor Region {str(surface_role_spec.get('label_role', role) or role).title()} - {region_id}"
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    _style_region_preview_object(obj, selected=False)
    return obj


def _create_or_update_region_structure_preview_object(
    *,
    document=None,
    project=None,
    corridor_model=None,
    row: dict[str, object],
    region_sections: list[object],
):
    if document is None or not region_sections:
        return None
    structure_refs = _unique_refs(_section_structure_values(region_sections))
    if not structure_refs:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    region_id = str(row.get("region_id", "") or "")
    object_name = _region_structure_preview_object_name(region_id)
    shapes = []
    for index, section in enumerate(region_sections):
        frame = getattr(section, "frame", None)
        if frame is None:
            continue
        width = max(float(getattr(section, "surface_left_width", 0.0) or 0.0) + float(getattr(section, "surface_right_width", 0.0) or 0.0), 2.0)
        try:
            x = float(getattr(frame, "x", 0.0) or 0.0) - 0.6
            y = float(getattr(frame, "y", 0.0) or 0.0) - width * 0.5
            z = float(getattr(frame, "z", 0.0) or 0.0) + REGION_SURFACE_DISPLAY_Z_OFFSET + 0.25
            shapes.append(Part.makeBox(1.2, width, 0.6, AppModule.Vector(x, y, z)))
        except Exception:
            pass
    if not shapes:
        return None
    obj = document.getObject(object_name)
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = f"Corridor Region Structure - {region_id}"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_region_structure_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorRegionStructure")
    _set_preview_property(obj, "RegionRef", region_id)
    _set_preview_property(obj, "RegionObjectRole", "structure")
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_string_list_property(obj, "StructureRefs", structure_refs)
    _set_preview_float_property(obj, "StationStart", float(row.get("station_start", 0.0) or 0.0))
    _set_preview_float_property(obj, "StationEnd", float(row.get("station_end", 0.0) or 0.0))
    _set_preview_integer_property(obj, "SectionCount", len(region_sections))
    _set_preview_integer_property(obj, "StructureCount", len(structure_refs))
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    _style_region_preview_object(obj, selected=False)
    return obj


def _region_surface_build_sections(
    sections: list[object],
    *,
    station_start: float,
    station_end: float,
    all_sections: list[object] | None = None,
    region_id: str = "",
) -> list[object]:
    ordered = sorted(list(sections or []), key=_section_station)
    all_ordered = sorted(list(all_sections or ordered), key=_section_station)
    augmented = list(ordered)
    for boundary_role, station in (("start", float(station_start)), ("end", float(station_end))):
        if not _has_section_at_station(augmented, station):
            boundary_section = _region_boundary_virtual_section(
                all_ordered,
                station,
                region_id=str(region_id or ""),
                boundary_role=boundary_role,
            )
            if boundary_section is not None:
                augmented.append(boundary_section)
    ordered = _unique_sections_by_station(augmented)
    if len(ordered) != 1:
        return ordered
    section = ordered[0]
    frame = getattr(section, "frame", None)
    if frame is None:
        return ordered
    length = abs(float(station_end) - float(station_start))
    if length <= 1.0e-6:
        length = 1.0
    try:
        import math as _math

        angle_rad = _math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        station = float(getattr(frame, "station", _section_station(section)) or _section_station(section)) + length
        new_frame = replace(
            frame,
            station=station,
            x=float(getattr(frame, "x", 0.0) or 0.0) + _math.cos(angle_rad) * length,
            y=float(getattr(frame, "y", 0.0) or 0.0) + _math.sin(angle_rad) * length,
        )
        return [
            section,
            replace(
                section,
                applied_section_id=f"{str(getattr(section, 'applied_section_id', '') or 'region-section')}:display-end",
                station=station,
                frame=new_frame,
            ),
        ]
    except Exception:
        return ordered


def _has_section_at_station(sections: list[object], station: float, *, tolerance: float = 1.0e-6) -> bool:
    return any(abs(_section_station(section) - float(station)) <= float(tolerance) for section in list(sections or []))


def _unique_sections_by_station(sections: list[object]) -> list[object]:
    rows: dict[float, object] = {}
    for section in sorted(list(sections or []), key=lambda item: (_section_station(item), str(getattr(item, "applied_section_id", "") or ""))):
        rows[round(_section_station(section), 6)] = section
    return [rows[key] for key in sorted(rows)]


def _region_boundary_virtual_section(
    sections: list[object],
    station: float,
    *,
    region_id: str,
    boundary_role: str,
):
    ordered = sorted([section for section in list(sections or []) if getattr(section, "frame", None) is not None], key=_section_station)
    if not ordered:
        return None
    value = float(station)
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = _section_station(first)
        second_station = _section_station(second)
        low = min(first_station, second_station)
        high = max(first_station, second_station)
        if low - 1.0e-6 <= value <= high + 1.0e-6:
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (value - first_station) / (second_station - first_station)
            return _interpolate_region_boundary_section(first, second, ratio, station=value, region_id=region_id, boundary_role=boundary_role)
    nearest = min(ordered, key=lambda section: abs(_section_station(section) - value))
    return _project_region_boundary_section(nearest, station=value, region_id=region_id, boundary_role=boundary_role)


def _interpolate_region_boundary_section(first, second, ratio: float, *, station: float, region_id: str, boundary_role: str):
    t = max(0.0, min(1.0, float(ratio)))
    source = _region_boundary_context_source(first, second, station=station, region_id=region_id)
    frame = _interpolate_region_boundary_frame(getattr(first, "frame", None), getattr(second, "frame", None), t, station=station, source_frame=getattr(source, "frame", None))
    point_rows = _interpolate_region_boundary_points(first, second, t)
    if not point_rows:
        point_rows = list(getattr(source, "point_rows", []) or [])
    return _replace_region_boundary_section(
        source,
        station=station,
        frame=frame,
        region_id=region_id,
        boundary_role=boundary_role,
        point_rows=point_rows,
        first=first,
        second=second,
        ratio=t,
    )


def _project_region_boundary_section(section, *, station: float, region_id: str, boundary_role: str):
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    try:
        import math as _math

        delta = float(station) - _section_station(section)
        angle_rad = _math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        projected_frame = replace(
            frame,
            station=float(station),
            x=float(getattr(frame, "x", 0.0) or 0.0) + _math.cos(angle_rad) * delta,
            y=float(getattr(frame, "y", 0.0) or 0.0) + _math.sin(angle_rad) * delta,
            notes=_append_frame_note(frame, "region_boundary_virtual"),
        )
    except Exception:
        projected_frame = replace(frame, station=float(station), notes=_append_frame_note(frame, "region_boundary_virtual"))
    return _replace_region_boundary_section(
        section,
        station=station,
        frame=projected_frame,
        region_id=region_id,
        boundary_role=boundary_role,
        point_rows=list(getattr(section, "point_rows", []) or []),
    )


def _region_boundary_context_source(first, second, *, station: float, region_id: str):
    target = str(region_id or "")
    for section in (first, second):
        if str(getattr(section, "region_id", "") or "") == target:
            return section
    return first if abs(_section_station(first) - float(station)) <= abs(_section_station(second) - float(station)) else second


def _interpolate_region_boundary_frame(first_frame, second_frame, ratio: float, *, station: float, source_frame=None):
    source = source_frame or first_frame or second_frame
    if source is None:
        return None
    if first_frame is None:
        first_frame = source
    if second_frame is None:
        second_frame = source
    t = max(0.0, min(1.0, float(ratio)))
    return replace(
        source,
        station=float(station),
        x=_lerp_value(getattr(first_frame, "x", 0.0), getattr(second_frame, "x", 0.0), t),
        y=_lerp_value(getattr(first_frame, "y", 0.0), getattr(second_frame, "y", 0.0), t),
        z=_lerp_value(getattr(first_frame, "z", 0.0), getattr(second_frame, "z", 0.0), t),
        tangent_direction_deg=_lerp_angle_degrees(
            float(getattr(first_frame, "tangent_direction_deg", 0.0) or 0.0),
            float(getattr(second_frame, "tangent_direction_deg", 0.0) or 0.0),
            t,
        ),
        profile_grade=_lerp_value(getattr(first_frame, "profile_grade", 0.0), getattr(second_frame, "profile_grade", 0.0), t),
        notes=_append_frame_note(source, "region_boundary_virtual"),
    )


def _replace_region_boundary_section(
    source,
    *,
    station: float,
    frame,
    region_id: str,
    boundary_role: str,
    point_rows: list[object],
    first=None,
    second=None,
    ratio: float = 0.0,
):
    try:
        return replace(
            source,
            applied_section_id=f"{str(getattr(source, 'applied_section_id', '') or 'section')}:region-boundary:{boundary_role}:{float(station):.3f}",
            station=float(station),
            frame=frame,
            region_id=str(region_id or getattr(source, "region_id", "") or ""),
            surface_left_width=_interpolate_attr(first, second, "surface_left_width", ratio, source),
            surface_right_width=_interpolate_attr(first, second, "surface_right_width", ratio, source),
            subgrade_depth=_interpolate_attr(first, second, "subgrade_depth", ratio, source),
            daylight_left_width=_interpolate_attr(first, second, "daylight_left_width", ratio, source),
            daylight_right_width=_interpolate_attr(first, second, "daylight_right_width", ratio, source),
            daylight_left_slope=_interpolate_attr(first, second, "daylight_left_slope", ratio, source),
            daylight_right_slope=_interpolate_attr(first, second, "daylight_right_slope", ratio, source),
            point_rows=point_rows,
            structure_diagnostic_rows=list(getattr(source, "structure_diagnostic_rows", []) or [])
            + [f"info|region_boundary_virtual|{region_id}|{boundary_role}:{float(station):.3f}"],
        )
    except Exception:
        return source


def _interpolate_attr(first, second, attr: str, ratio: float, fallback) -> float:
    if first is None or second is None:
        return float(getattr(fallback, attr, 0.0) or 0.0)
    return _lerp_value(getattr(first, attr, 0.0), getattr(second, attr, 0.0), max(0.0, min(1.0, float(ratio))))


def _interpolate_region_boundary_points(first, second, ratio: float) -> list[object]:
    first_points = list(getattr(first, "point_rows", []) or [])
    second_points = list(getattr(second, "point_rows", []) or [])
    t = max(0.0, min(1.0, float(ratio)))
    if len(first_points) == len(second_points):
        output = []
        for index, first_point in enumerate(first_points):
            second_point = second_points[index]
            first_role = str(getattr(first_point, "point_role", "") or "")
            if first_role != str(getattr(second_point, "point_role", "") or ""):
                output = []
                break
            output.append(_interpolate_region_boundary_point(first_point, second_point, t, point_role=first_role, index=index))
        if output:
            return output
    output: list[object] = []
    for role in ("fg_surface", "subgrade_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"):
        left = _role_points_for_region_boundary(first, role)
        right = _role_points_for_region_boundary(second, role)
        if not left or len(left) != len(right):
            continue
        for index, first_point in enumerate(left):
            output.append(_interpolate_region_boundary_point(first_point, right[index], t, point_role=role, index=index))
    return output


def _role_points_for_region_boundary(section, role: str) -> list[object]:
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == str(role or "")
    ]
    return sorted(rows, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))


def _interpolate_region_boundary_point(first_point, second_point, ratio: float, *, point_role: str, index: int):
    t = max(0.0, min(1.0, float(ratio)))
    try:
        return replace(
            first_point,
            point_id=f"region-boundary:{point_role}:{index}:{float(t):.6g}",
            x=_lerp_value(getattr(first_point, "x", 0.0), getattr(second_point, "x", 0.0), t),
            y=_lerp_value(getattr(first_point, "y", 0.0), getattr(second_point, "y", 0.0), t),
            z=_lerp_value(getattr(first_point, "z", 0.0), getattr(second_point, "z", 0.0), t),
            point_role=point_role,
            lateral_offset=_lerp_value(getattr(first_point, "lateral_offset", 0.0), getattr(second_point, "lateral_offset", 0.0), t),
        )
    except Exception:
        return first_point


def _append_frame_note(frame, note: str) -> str:
    existing = str(getattr(frame, "notes", "") or "")
    token = str(note or "")
    if not existing:
        return token
    if token in existing:
        return existing
    return f"{existing};{token}"


def _lerp_angle_degrees(first: float, second: float, ratio: float) -> float:
    delta = (float(second) - float(first) + 180.0) % 360.0 - 180.0
    return float(first) + delta * float(ratio)


def _offset_tin_surface_z(surface, z_offset: float):
    offset = float(z_offset or 0.0)
    if surface is None or abs(offset) <= 1.0e-9:
        return surface
    try:
        return replace(
            surface,
            vertex_rows=[
                replace(vertex, z=float(getattr(vertex, "z", 0.0) or 0.0) + offset)
                for vertex in list(getattr(surface, "vertex_rows", []) or [])
            ],
        )
    except Exception:
        return surface


def _style_region_preview_object(obj, *, selected: bool = False) -> None:
    if obj is None:
        return
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        vobj.Visibility = True
        if hasattr(vobj, "Selectable"):
            vobj.Selectable = True
        try:
            vobj.DisplayMode = "Flat Lines"
        except Exception:
            pass
        role = str(getattr(obj, "RegionObjectRole", "") or "").strip().lower()
        shape_color, line_color = {
            "design": ((0.05, 0.95, 0.25), (0.0, 0.35, 0.05)),
            "subgrade": ((0.62, 0.66, 0.76), (0.22, 0.24, 0.30)),
            "daylight": ((0.55, 0.95, 0.18), (0.20, 0.50, 0.08)),
            "drainage": ((0.00, 0.82, 1.00), (0.00, 0.35, 0.65)),
            "structure": ((0.95, 0.30, 0.90), (0.50, 0.08, 0.48)),
        }.get(role, ((0.05, 0.95, 0.25), (0.0, 0.35, 0.05)))
        vobj.ShapeColor = shape_color
        vobj.LineColor = line_color
        vobj.PointColor = line_color
        vobj.LineWidth = 3.5 if bool(selected) else 2.4
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0 if bool(selected) else (12 if role != "structure" else 20)
    except Exception:
        pass


def _region_applied_section_subset(applied_section_set, *, region_id: str, sections: list[object]) -> AppliedSectionSet:
    applied_id = str(getattr(applied_section_set, "applied_section_set_id", "") or "sections:main")
    safe = _safe_region_token(region_id)
    ordered = sorted(list(sections or []), key=_section_station)
    return AppliedSectionSet(
        schema_version=int(getattr(applied_section_set, "schema_version", 1) or 1),
        project_id=str(getattr(applied_section_set, "project_id", "") or "corridorroad-v1"),
        applied_section_set_id=f"{applied_id}:region:{safe}",
        corridor_id=str(getattr(applied_section_set, "corridor_id", "") or "corridor:main"),
        alignment_id=str(getattr(applied_section_set, "alignment_id", "") or ""),
        station_rows=[
            AppliedSectionStationRow(
                station_row_id=f"{applied_id}:region:{safe}:station:{index + 1}",
                station=_section_station(section),
                applied_section_id=str(getattr(section, "applied_section_id", "") or f"region-section:{index + 1}"),
                kind="region_surface_sample",
            )
            for index, section in enumerate(ordered)
        ],
        sections=ordered,
    )


def _corridor_region_preview_objects(document, region_id: str) -> list[object]:
    if document is None:
        return []
    objects: list[object] = []
    for object_name in _region_preview_object_names(region_id):
        try:
            obj = document.getObject(object_name)
        except Exception:
            obj = None
        if obj is not None:
            objects.append(obj)
    return objects


def _corridor_region_surface_preview_object(document, region_id: str):
    if document is None:
        return None
    try:
        return document.getObject(_region_surface_preview_object_name(region_id))
    except Exception:
        return None


def _region_surface_role_specs(region_id: str) -> list[dict[str, object]]:
    return [
        {
            "role": "design",
            "builder": "build_design_surface",
            "object_name": _region_surface_preview_object_name(region_id, "design"),
            "label_prefix": "Corridor Region Design Surface",
            "label_role": "design surface",
            "style_role": "edited",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET,
        },
        {
            "role": "subgrade",
            "builder": "build_subgrade_surface",
            "object_name": _region_surface_preview_object_name(region_id, "subgrade"),
            "label_prefix": "Corridor Region Subgrade Surface",
            "label_role": "subgrade surface",
            "style_role": "subgrade",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET + 0.08,
        },
        {
            "role": "daylight",
            "builder": "build_daylight_surface",
            "object_name": _region_surface_preview_object_name(region_id, "daylight"),
            "label_prefix": "Corridor Region Slope Surface",
            "label_role": "slope surface",
            "style_role": "daylight",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET + 0.16,
        },
        {
            "role": "drainage",
            "builder": "build_drainage_surface",
            "object_name": _region_surface_preview_object_name(region_id, "drainage"),
            "label_prefix": "Corridor Region Drainage Surface",
            "label_role": "drainage surface",
            "style_role": "drainage",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET + 0.24,
        },
    ]


def _region_preview_object_names(region_id: str) -> list[str]:
    return [
        *[_region_surface_preview_object_name(region_id, str(spec.get("role", "") or "")) for spec in _region_surface_role_specs(region_id)],
        _region_structure_preview_object_name(region_id),
    ]


def _region_surface_preview_object_name(region_id: str, role: str = "design") -> str:
    token = _safe_region_token(region_id) or "unknown"
    role_text = str(role or "design").strip().lower()
    if role_text in {"", "design"}:
        return f"V1CorridorRegionSurface_{token}"
    return f"V1CorridorRegionSurface_{token}_{_safe_region_token(role_text)}"


def _region_structure_preview_object_name(region_id: str) -> str:
    return f"V1CorridorRegionStructure_{_safe_region_token(region_id) or 'unknown'}"


def _safe_region_token(region_id: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(region_id or "").strip())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe or "unknown"


def _drainage_point_side(point) -> str:
    point_id = str(getattr(point, "point_id", "") or "").lower()
    lateral = float(getattr(point, "lateral_offset", 0.0) or 0.0)
    if "left" in point_id:
        return "L"
    if "right" in point_id:
        return "R"
    if lateral > 0.0:
        return "L"
    if lateral < 0.0:
        return "R"
    return ""


def _drainage_review_marker_point(section, ditch_points: list[object]) -> tuple[float, float, float]:
    points = list(ditch_points or [])
    if points:
        return (
            sum(float(getattr(point, "x", 0.0) or 0.0) for point in points) / len(points),
            sum(float(getattr(point, "y", 0.0) or 0.0) for point in points) / len(points),
            sum(float(getattr(point, "z", 0.0) or 0.0) for point in points) / len(points),
        )
    frame = getattr(section, "frame", None)
    if frame is not None:
        return (
            float(getattr(frame, "x", 0.0) or 0.0),
            float(getattr(frame, "y", 0.0) or 0.0),
            float(getattr(frame, "z", 0.0) or 0.0),
        )
    return (0.0, 0.0, 0.0)


def _drainage_review_marker_name(row_index: int) -> str:
    return f"ReviewIssueDrainageStation{max(0, int(row_index)) + 1:03d}"


def _create_drainage_review_marker(*, document=None, row: dict[str, object] | None = None, object_name: str = ""):
    if document is None or row is None:
        return None
    try:
        point = (
            float(row.get("x", 0.0) or 0.0),
            float(row.get("y", 0.0) or 0.0),
            float(row.get("z", 0.0) or 0.0),
        )
    except Exception:
        point = (0.0, 0.0, 0.0)
    name = object_name or str(row.get("marker_object", "") or "ReviewIssueDrainageStation001")
    status = str(row.get("status", "") or "")
    color = {
        "ready": (0.05, 0.65, 1.00),
        "warn": (1.00, 0.72, 0.10),
        "missing": (1.00, 0.16, 0.12),
    }.get(status, (0.05, 0.65, 1.00))
    obj = _create_marker_compound(
        document=document,
        object_name=name,
        label=f"Drainage Diagnostic - STA {float(row.get('station', 0.0) or 0.0):.3f}" if row.get("station", "") != "" else "Drainage Diagnostic",
        points=[point],
        radius=0.8,
        color=color,
        surface=None,
        corridor_model=None,
    )
    if obj is None:
        return None
    _set_preview_property(obj, "IssueKind", "drainage_diagnostic")
    _set_preview_property(obj, "IssueStation", "" if row.get("station", "") == "" else f"{float(row.get('station', 0.0) or 0.0):.3f}")
    _set_preview_property(obj, "IssueStatus", status)
    _set_preview_property(obj, "IssueReason", str(row.get("notes", "") or ""))
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(document), obj)
    except Exception:
        pass
    return obj


def _with_applied_section_review_summary(row: dict[str, object], summary: dict[str, object]) -> dict[str, object]:
    output = dict(row or {})
    output["applied_section_summary"] = str(summary.get("summary", "") or "")
    output["applied_section_diagnostics"] = str(summary.get("diagnostics", "") or "")
    output["applied_section_status"] = str(summary.get("status", "") or "")
    return output


def _surface_id(surface_model, surface_kind: str) -> str:
    for row in list(getattr(surface_model, "surface_rows", []) or []):
        if str(getattr(row, "surface_kind", "") or "") == surface_kind:
            return str(getattr(row, "surface_id", "") or "")
    return ""


def _corridor_build_review_row(role: str, title: str, object_name: str, obj) -> dict[str, object]:
    if obj is None:
        return {
            "role": role,
            "result": title,
            "object_name": object_name,
            "object_label": "",
            "status": "missing",
            "vertex_count": "",
            "triangle_or_point_count": "",
            "notes": "Not built yet.",
        }
    if role == "centerline":
        point_count = int(getattr(obj, "PointCount", 0) or 0)
        curve_kind = str(getattr(obj, "DisplayCurveKind", "") or "")
        return {
            "role": role,
            "result": title,
            "object_name": str(getattr(obj, "Name", "") or object_name),
            "object_label": str(getattr(obj, "Label", "") or object_name),
            "status": "ready",
            "vertex_count": "",
            "triangle_or_point_count": point_count,
            "notes": f"Curve: {curve_kind or 'unknown'}",
        }
    vertex_count = int(getattr(obj, "VertexCount", 0) or 0)
    triangle_count = int(getattr(obj, "TriangleCount", 0) or 0)
    notes = str(getattr(obj, "SlopeFaceDiagnosticSummary", "") or "")
    issue_stations = str(getattr(obj, "SlopeFaceIssueStations", "") or "")
    if notes and issue_stations:
        notes = f"{notes} | issues: {issue_stations}"
    if not notes:
        surface_kind = str(getattr(obj, "SurfaceKind", "") or "")
        notes = f"Surface kind: {surface_kind or 'unknown'}"
    return {
        "role": role,
        "result": title,
        "object_name": str(getattr(obj, "Name", "") or object_name),
        "object_label": str(getattr(obj, "Label", "") or object_name),
        "status": "ready" if vertex_count > 0 and triangle_count > 0 else "empty",
        "vertex_count": vertex_count,
        "triangle_or_point_count": triangle_count,
        "notes": notes,
    }


def _set_preview_property(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _set_preview_string_list_property(obj, name: str, values: list[str]) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyStringList", name, "CorridorRoad", name)
        setattr(obj, name, [str(value or "") for value in list(values or [])])
    except Exception:
        pass


def _set_preview_float_property(obj, name: str, value: float) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyFloat", name, "CorridorRoad", name)
        setattr(obj, name, float(value or 0.0))
    except Exception:
        pass


def _remove_preview_object(document, object_name: str) -> None:
    try:
        obj = document.getObject(object_name)
        if obj is not None:
            document.removeObject(obj.Name)
    except Exception:
        pass


def _centerline_points_from_applied_sections(applied_section_set, app_module):
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    rows = sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda row: float(getattr(row, "station", 0.0) or 0.0),
    )
    points = []
    stations = []
    for row in rows:
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        frame = getattr(section, "frame", None) if section is not None else None
        if frame is None:
            continue
        try:
            point = app_module.Vector(float(frame.x), float(frame.y), float(frame.z))
            station = float(getattr(frame, "station", getattr(row, "station", 0.0)) or 0.0)
        except Exception:
            continue
        if points and _same_centerline_point(points[-1], point):
            continue
        points.append(point)
        stations.append(station)
    return points, stations


def _same_centerline_point(left, right, tolerance: float = 1.0e-7) -> bool:
    try:
        return (
            abs(float(left.x) - float(right.x)) <= tolerance
            and abs(float(left.y) - float(right.y)) <= tolerance
            and abs(float(left.z) - float(right.z)) <= tolerance
        )
    except Exception:
        return False


def _select_and_fit_object(obj) -> None:
    if Gui is None or obj is None:
        return
    try:
        if hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass
    try:
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
    except Exception:
        pass
    try:
        view = Gui.ActiveDocument.ActiveView
        if hasattr(view, "fitSelection"):
            view.fitSelection()
        else:
            Gui.SendMsgToActiveView("ViewSelection")
    except Exception:
        try:
            Gui.SendMsgToActiveView("ViewSelection")
        except Exception:
            try:
                Gui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass


def _select_and_fit_objects(objects: list[object]) -> None:
    clean = [obj for obj in list(objects or []) if obj is not None]
    if not clean:
        return
    if Gui is None:
        return
    try:
        if hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass
    try:
        Gui.Selection.clearSelection()
        for obj in clean:
            Gui.Selection.addSelection(obj)
    except Exception:
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(clean[0])
        except Exception:
            pass
    try:
        view = Gui.ActiveDocument.ActiveView
        if hasattr(view, "fitSelection"):
            view.fitSelection()
        else:
            Gui.SendMsgToActiveView("ViewSelection")
    except Exception:
        try:
            Gui.SendMsgToActiveView("ViewSelection")
        except Exception:
            try:
                Gui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass


def _corridor_build_preview_object(document, role: str):
    if document is None:
        return None
    role_text = str(role or "").strip()
    for candidate_role, _title, object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        if candidate_role != role_text:
            continue
        try:
            return document.getObject(object_name)
        except Exception:
            return None
    return None


def _corridor_build_guided_review_step(step_id: str):
    step_text = str(step_id or "").strip()
    for step in CORRIDOR_BUILD_GUIDED_REVIEW_STEPS:
        if step[0] == step_text:
            return step
    return None


def _corridor_build_issue_marker_objects(document) -> list[object]:
    if document is None:
        return []
    markers = []
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if name.startswith((
            "ReviewIssueSlopeFace",
            "ReviewIssueDrainage",
            "V1CorridorRegionSurface_",
            "V1CorridorRegionStructure_",
            "V1RegionBoundaryRangeHighlight",
            "V1SurfaceTransitionSpanMarkers",
        )):
            markers.append(obj)
    return markers


def _remove_legacy_region_display_objects(document) -> None:
    if document is None:
        return
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if name.startswith(("V1RegionDisplay_", "V1RegionBoundaryRangeHighlight")):
            try:
                document.removeObject(name)
            except Exception:
                pass


def _remove_stale_region_surface_preview_objects(document, *, keep_names: set[str]) -> None:
    if document is None:
        return
    keep = {str(name or "") for name in set(keep_names or set())}
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if name.startswith(("V1CorridorRegionSurface_", "V1CorridorRegionStructure_")) and name not in keep:
            try:
                document.removeObject(name)
            except Exception:
                pass


def _corridor_build_daylight_contact_marker_object(document):
    if document is None:
        return None
    try:
        return document.getObject("ReviewIssueSlopeFaceIntersectionMarkers")
    except Exception:
        return None


def _corridor_build_daylight_marker_objects(document) -> list[object]:
    if document is None:
        return []
    names = (
        "ReviewIssueSlopeFaceIntersectionMarkers",
        "ReviewIssueSlopeFaceSampledEdgeMarkers",
        "ReviewIssueSlopeFaceFallbackMarkers",
    )
    objects = []
    for name in names:
        try:
            obj = document.getObject(name)
        except Exception:
            obj = None
        if obj is not None:
            objects.append(obj)
    for obj in _corridor_build_issue_marker_objects(document):
        name = str(getattr(obj, "Name", "") or "")
        if name.startswith("ReviewIssueSlopeFaceIssue"):
            objects.append(obj)
    return objects


def _set_object_visibility(obj, visible: bool) -> None:
    if obj is None:
        return
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = bool(visible)
    except Exception:
        pass


def _object_visibility(obj) -> bool:
    if obj is None:
        return False
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            return bool(getattr(vobj, "Visibility", False))
    except Exception:
        pass
    return False


def _make_centerline_shape(points, part_module):
    if len(points) < 2:
        return part_module.Shape(), "empty"
    if len(points) == 2:
        return part_module.makeLine(points[0], points[1]), "line"
    try:
        curve = part_module.BSplineCurve()
        curve.interpolate(points)
        return curve.toShape(), "spline"
    except Exception:
        edges = []
        for idx in range(len(points) - 1):
            try:
                edges.append(part_module.makeLine(points[idx], points[idx + 1]))
            except Exception:
                pass
        if not edges:
            return part_module.Shape(), "empty"
        return part_module.makeCompound(edges), "polyline_fallback"


def _attach_surface_quality_properties(obj, surface, *, applied_section_set=None) -> None:
    quality = {str(getattr(row, "kind", "") or ""): getattr(row, "value", 0) for row in list(getattr(surface, "quality_rows", []) or [])}
    _set_preview_integer_property(obj, "EGTieInHitCount", int(float(quality.get("eg_tie_in_hit_count", 0) or 0)))
    _set_preview_integer_property(obj, "EGTieInMissCount", int(float(quality.get("eg_tie_in_miss_count", 0) or 0)))
    _set_preview_integer_property(obj, "EGIntersectionCount", int(float(quality.get("eg_intersection_count", 0) or 0)))
    _set_preview_integer_property(obj, "EGOuterEdgeSampleCount", int(float(quality.get("eg_outer_edge_sample_count", 0) or 0)))
    _set_preview_integer_property(obj, "SlopeFaceFallbackCount", int(float(quality.get("slope_face_fallback_count", 0) or 0)))
    _set_preview_integer_property(obj, "SlopeFaceNoExistingGroundCount", int(float(quality.get("slope_face_no_existing_ground_count", 0) or 0)))
    _set_preview_integer_property(obj, "SlopeFaceNoEGHitCount", int(float(quality.get("slope_face_no_eg_hit_count", 0) or 0)))
    summary = (
        f"EG intersections: {int(float(quality.get('eg_intersection_count', 0) or 0))}, "
        f"outer-edge samples: {int(float(quality.get('eg_outer_edge_sample_count', 0) or 0))}, "
        f"fallbacks: {int(float(quality.get('slope_face_fallback_count', 0) or 0))}, "
        f"no EG TIN: {int(float(quality.get('slope_face_no_existing_ground_count', 0) or 0))}, "
        f"no EG hit: {int(float(quality.get('slope_face_no_eg_hit_count', 0) or 0))}, "
        f"hits: {int(float(quality.get('eg_tie_in_hit_count', 0) or 0))}, "
        f"misses: {int(float(quality.get('eg_tie_in_miss_count', 0) or 0))}"
    )
    _set_preview_property(obj, "SlopeFaceDiagnosticSummary", summary)
    issue_rows = _slope_face_issue_station_rows(surface, applied_section_set)
    _set_preview_property(obj, "SlopeFaceIssueStations", _slope_face_issue_station_summary_from_rows(issue_rows))
    _set_preview_string_list_property(
        obj,
        "SlopeFaceIssueRows",
        [_serialize_slope_face_issue_row(row) for row in issue_rows],
    )


def _create_slope_face_diagnostic_markers(
    *,
    document=None,
    project=None,
    surface=None,
    corridor_model=None,
    applied_section_set=None,
    show_daylight_contact_markers: bool = True,
):
    """Create visible 3D markers for slope-face EG tie-in states."""

    if document is None or surface is None:
        return []
    if not bool(show_daylight_contact_markers):
        _remove_slope_face_diagnostic_markers(document)
        return []
    status_points = _slope_face_status_points(surface)
    if not status_points:
        _remove_slope_face_diagnostic_markers(document)
        return []
    daylight_marker_color = (0.10, 0.85, 0.25)
    marker_specs = [
        ("intersection", "ReviewIssueSlopeFaceIntersectionMarkers", "Slope Face Daylight / EG Intersections", daylight_marker_color, 1.8),
        ("sampled_outer_edge", "ReviewIssueSlopeFaceSampledEdgeMarkers", "Slope Face Outer Edge Samples", daylight_marker_color),
        ("fallback", "ReviewIssueSlopeFaceFallbackMarkers", "Slope Face Fallback / No Hit", daylight_marker_color),
    ]
    radius = _marker_radius([point for points in status_points.values() for point in points])
    created = []
    for spec in marker_specs:
        status_key, object_name, label, color = spec[:4]
        radius_scale = float(spec[4]) if len(spec) > 4 else 1.0
        points = status_points.get(status_key, [])
        obj = _create_marker_compound(
            document=document,
            object_name=object_name,
            label=label,
            points=points,
            radius=radius * radius_scale,
            color=color,
            surface=surface,
            corridor_model=corridor_model,
        )
        if obj is not None:
            _set_object_visibility(obj, bool(show_daylight_contact_markers))
            created.append(obj)
            try:
                from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

                route_to_v1_tree(project or find_project(document), obj)
            except Exception:
                pass
    created.extend(
        _create_slope_face_individual_issue_markers(
            document=document,
            project=project,
            surface=surface,
            corridor_model=corridor_model,
            applied_section_set=applied_section_set,
            radius=radius,
            visible=show_daylight_contact_markers,
        )
    )
    return created


def _remove_slope_face_diagnostic_markers(document) -> None:
    for name in (
        "ReviewIssueSlopeFaceIntersectionMarkers",
        "ReviewIssueSlopeFaceSampledEdgeMarkers",
        "ReviewIssueSlopeFaceFallbackMarkers",
    ):
        try:
            obj = document.getObject(name)
            if obj is not None:
                document.removeObject(obj.Name)
        except Exception:
            pass
    _remove_slope_face_individual_issue_markers(document)


def _remove_slope_face_individual_issue_markers(document) -> None:
    if document is None:
        return
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if not name.startswith("ReviewIssueSlopeFaceIssue"):
            continue
        try:
            document.removeObject(obj.Name)
        except Exception:
            pass


def _create_slope_face_individual_issue_markers(
    *,
    document=None,
    project=None,
    surface=None,
    corridor_model=None,
    applied_section_set=None,
    radius: float = 0.5,
    visible: bool = True,
):
    """Create one small marker object for each station-side slope-face issue."""

    if document is None or surface is None:
        return []
    _remove_slope_face_individual_issue_markers(document)
    rows = _slope_face_issue_station_rows(surface, applied_section_set)
    created = []
    for row in rows:
        try:
            point = (float(row.get("x", 0.0) or 0.0), float(row.get("y", 0.0) or 0.0), float(row.get("z", 0.0) or 0.0))
        except Exception:
            continue
        object_name = str(row.get("marker_object", "") or "")
        if not object_name:
            continue
        obj = _create_marker_compound(
            document=document,
            object_name=object_name,
            label=f"Slope Face Issue - {row.get('station_label', '')} {row.get('side', '')}",
            points=[point],
            radius=max(float(radius or 0.5) * 1.6, 0.3),
            color=(0.10, 0.85, 0.25),
            surface=surface,
            corridor_model=corridor_model,
        )
        if obj is None:
            continue
        _set_preview_property(obj, "IssueStation", str(row.get("station_label", "") or ""))
        _set_preview_property(obj, "IssueSide", str(row.get("side", "") or ""))
        _set_preview_property(obj, "IssueReason", str(row.get("reason", "") or ""))
        _set_object_visibility(obj, bool(visible))
        created.append(obj)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(document), obj)
        except Exception:
            pass
    return created


def _slope_face_status_points(surface) -> dict[str, list[tuple[float, float, float]]]:
    points: dict[str, list[tuple[float, float, float]]] = {
        "intersection": [],
        "sampled_outer_edge": [],
        "fallback": [],
    }
    for vertex in list(getattr(surface, "vertex_rows", []) or []):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        status = str(getattr(vertex, "notes", "") or "")
        if status == "daylight_marker":
            points["intersection"].append((float(vertex.x), float(vertex.y), float(vertex.z)))
            continue
        if not vertex_id.endswith(":outer"):
            continue
        if status == "intersection":
            key = "intersection"
        elif status == "sampled_outer_edge":
            key = "sampled_outer_edge"
        else:
            key = "fallback"
        points[key].append((float(vertex.x), float(vertex.y), float(vertex.z)))
    return points


def _slope_face_issue_station_summary(surface, applied_section_set=None, *, max_items: int = 8) -> str:
    """Return compact station/side list for slope-face fallback conditions."""

    return _slope_face_issue_station_summary_from_rows(
        _slope_face_issue_station_rows(surface, applied_section_set),
        max_items=max_items,
    )


def _slope_face_issue_station_rows(surface, applied_section_set=None) -> list[dict[str, str]]:
    """Return row-level slope-face fallback issues tied to station and side."""

    station_labels = _slope_face_station_labels(applied_section_set)
    rows: list[dict[str, str]] = []
    for vertex in list(getattr(surface, "vertex_rows", []) or []):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        if not vertex_id.endswith(":outer"):
            continue
        status = str(getattr(vertex, "notes", "") or "").strip()
        if not status.startswith("fallback"):
            continue
        parsed = _parse_slope_face_vertex_id(vertex_id)
        if parsed is None:
            continue
        index, side = parsed
        station_label = station_labels[index] if 0 <= index < len(station_labels) else f"row {index + 1}"
        reason = {
            "fallback:no_existing_ground_tin": "no EG TIN",
            "fallback:no_eg_hit_in_search_width": "no EG hit",
        }.get(status, status.replace("fallback:", ""))
        marker_object = _slope_face_issue_marker_name(index, side)
        rows.append(
            {
                "station_label": station_label,
                "station_index": str(index),
                "side": side.upper(),
                "reason": reason,
                "status": status,
                "marker_object": marker_object,
                "x": f"{float(getattr(vertex, 'x', 0.0) or 0.0):.6f}",
                "y": f"{float(getattr(vertex, 'y', 0.0) or 0.0):.6f}",
                "z": f"{float(getattr(vertex, 'z', 0.0) or 0.0):.6f}",
            }
        )
    return rows


def _slope_face_issue_station_summary_from_rows(rows: list[dict[str, str]], *, max_items: int = 8) -> str:
    items = [
        f"{row.get('station_label', '')} {row.get('side', '')} {row.get('reason', '')}".strip()
        for row in list(rows or [])
    ]
    if not items:
        return ""
    clipped = items[: max(1, int(max_items))]
    if len(items) > len(clipped):
        clipped.append(f"+{len(items) - len(clipped)} more")
    return "; ".join(clipped)


def _serialize_slope_face_issue_row(row: dict[str, str]) -> str:
    keys = ("station_label", "station_index", "side", "reason", "status", "marker_object", "x", "y", "z")
    return ";".join(f"{key}={_escape_issue_row_value(row.get(key, ''))}" for key in keys)


def _parse_slope_face_issue_row_text(text: str) -> dict[str, str]:
    row: dict[str, str] = {}
    for part in str(text or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = str(key or "").strip()
        if not key:
            continue
        row[key] = _unescape_issue_row_value(value)
    return row


def _parse_slope_face_issue_summary_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for part in str(text or "").split(";"):
        tokens = str(part or "").strip().split()
        if len(tokens) < 5 or tokens[0] != "STA":
            continue
        station_label = " ".join(tokens[0:2])
        side = tokens[2].upper()
        if side not in {"L", "R"}:
            continue
        rows.append(
            {
                "station_label": station_label,
                "station_index": "",
                "side": side,
                "reason": " ".join(tokens[3:]),
                "status": "fallback",
                "marker_object": "ReviewIssueSlopeFaceFallbackMarkers",
            }
        )
    return rows


def _slope_face_issue_marker_name(station_index: int, side: str) -> str:
    side_text = str(side or "").strip().upper()
    if side_text not in {"L", "R"}:
        side_text = "X"
    return f"ReviewIssueSlopeFaceIssue{max(0, int(station_index)) + 1:03d}{side_text}"


def _escape_issue_row_value(value: object) -> str:
    return str(value or "").replace("%", "%25").replace(";", "%3B").replace("=", "%3D")


def _unescape_issue_row_value(value: object) -> str:
    return str(value or "").replace("%3D", "=").replace("%3B", ";").replace("%25", "%")


def _slope_face_station_labels(applied_section_set=None) -> list[str]:
    if applied_section_set is None:
        return []
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    labels: list[str] = []
    for row in list(getattr(applied_section_set, "station_rows", []) or []):
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is None or getattr(section, "frame", None) is None:
            continue
        try:
            station = float(getattr(row, "station", getattr(section, "station", 0.0)) or 0.0)
        except Exception:
            continue
        labels.append(f"STA {station:.3f}")
    return labels


def _parse_slope_face_vertex_id(vertex_id: str) -> tuple[int, str] | None:
    parts = str(vertex_id or "").split(":")
    if len(parts) < 3:
        return None
    if not parts[0].startswith("v"):
        return None
    try:
        index = int(parts[0][1:])
    except Exception:
        return None
    side = str(parts[1] or "").strip().lower()
    if side not in {"left", "right"}:
        return None
    return index, "L" if side == "left" else "R"


def _create_marker_compound(
    *,
    document,
    object_name: str,
    label: str,
    points: list[tuple[float, float, float]],
    radius: float,
    color: tuple[float, float, float],
    surface,
    corridor_model,
):
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    obj = document.getObject(object_name)
    if not points:
        if obj is not None:
            try:
                document.removeObject(obj.Name)
            except Exception:
                pass
        return None
    shapes = []
    for x, y, z in points:
        try:
            shapes.append(Part.makeSphere(float(radius), AppModule.Vector(float(x), float(y), float(z))))
        except Exception:
            pass
    if not shapes:
        return None
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes)
        obj.Label = label
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_review_issue")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "slope_face_tie_in")
    _set_preview_property(obj, "SurfaceId", str(getattr(surface, "surface_id", "") or ""))
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_integer_property(obj, "MarkerCount", len(points))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = color
            vobj.PointColor = color
            vobj.LineColor = color
            vobj.Transparency = 0
    except Exception:
        pass
    return obj


def _marker_radius(points: list[tuple[float, float, float]]) -> float:
    if not points:
        return 0.5
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    return max(0.15, min(2.0, float(span or 1.0) * 0.015))


def _resolve_corridor_existing_ground_tin_surface(document):
    """Resolve an EG TIN for corridor slope-face tie-in without selecting corridor previews."""

    if document is None:
        return None
    try:
        from .cmd_review_tin import (
            _tin_surface_candidate_sort_key,
            _tin_surface_from_object,
            resolve_document_tin_max_triangles,
        )
        from ..models.result.tin_surface import TINSurface
    except Exception:
        return None

    candidates = []
    if Gui is not None:
        try:
            candidates.extend(list(Gui.Selection.getSelection() or []))
        except Exception:
            pass
    project = find_project(document)
    if project is not None:
        try:
            terrain = getattr(project, "Terrain", None)
            if terrain is not None:
                candidates.append(terrain)
        except Exception:
            pass
    candidates.extend(list(getattr(document, "Objects", []) or []))

    seen = set()
    for obj in sorted(candidates, key=_tin_surface_candidate_sort_key):
        name = str(getattr(obj, "Name", "") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        if _skip_corridor_existing_ground_candidate(obj):
            continue
        try:
            surface = _tin_surface_from_object(
                obj,
                max_triangles=resolve_document_tin_max_triangles(document, surface_obj=obj),
            )
        except Exception:
            surface = None
        if isinstance(surface, TINSurface):
            return surface
    return None


def _skip_corridor_existing_ground_candidate(obj) -> bool:
    if obj is None:
        return True
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    if record_kind == "v1_corridor_surface_preview":
        return True
    if record_kind == "v1_review_issue":
        return True
    if record_kind.startswith("profile_show_preview"):
        return True
    surface_role = str(getattr(obj, "SurfaceRole", "") or "").lower()
    if surface_role in {"design", "subgrade", "daylight", "drainage"}:
        return True
    surface_kind = str(getattr(obj, "SurfaceKind", "") or "").lower()
    if surface_kind in {"design_surface", "subgrade_surface", "daylight_surface", "drainage_surface"}:
        return True
    v1_type = str(getattr(obj, "V1ObjectType", "") or "")
    if v1_type in {"V1Alignment", "V1Profile", "V1Stationing", "V1CorridorModel", "V1SurfaceModel", "ReviewIssue"}:
        return True
    preview_role = str(getattr(obj, "PreviewRole", "") or "").lower()
    if preview_role in {"boundary", "void"}:
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if name.startswith("ReviewIssue"):
        return True
    if name.startswith(("CRV1_TIN_Boundary_Rectangle_Preview", "CRV1_TIN_Void_Rectangle_Preview")):
        return True
    if label.startswith(("TIN Boundary Rectangle Preview", "TIN Void Rectangle Preview")):
        return True
    return False


def _process_panel_events() -> None:
    try:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.processEvents()
    except Exception:
        pass
    try:
        if Gui is not None and hasattr(Gui, "updateGui"):
            Gui.updateGui()
    except Exception:
        pass


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass
