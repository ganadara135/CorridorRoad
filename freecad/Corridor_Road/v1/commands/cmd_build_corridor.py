"""Build Corridor command helpers for CorridorRoad v1."""

from __future__ import annotations

import math
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
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_exchange_package import create_or_update_v1_exchange_package_object, find_v1_exchange_package
from ..objects.obj_intersection import find_v1_intersection_model, to_intersection_model
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
from ..models.result.intersection_boundary_segment import IntersectionBoundarySegmentResult, IntersectionBoundarySegmentRow
from ..models.result.intersection_patch_boundary import IntersectionPatchBoundaryPointRow, IntersectionPatchBoundaryResult
from ..models.result.intersection_slope_face_boundary import (
    IntersectionSlopeFaceBoundaryResult,
    IntersectionSlopeFaceBoundaryRow,
)
from ..models.result.intersection_tie_in_edge import IntersectionTieInEdgeResult, IntersectionTieInEdgeRow
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
from ..services.evaluation.intersection_evaluation_service import IntersectionEvaluationService, IntersectionPatchPrerequisiteResult
from ..services.evaluation.station_context_resolver import StationContextResolver
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
    ("intersection", "Intersection Surface", "V1CorridorIntersectionSurfacePreview"),
    ("subgrade", "Subgrade Surface", "V1CorridorSubgradeSurfacePreview"),
    ("daylight", "Slope Face Surface", "V1CorridorDaylightSurfacePreview"),
    ("drainage", "Drainage Surface", "V1CorridorDrainageSurfacePreview"),
)
CORRIDOR_BUILD_PREVIEW_DIAGNOSTIC_OBJECTS = {
    "design": "V1CorridorDesignSurfacePreviewDiagnostic",
    "intersection": "V1CorridorIntersectionSurfacePreviewDiagnostic",
    "subgrade": "V1CorridorSubgradeSurfacePreviewDiagnostic",
    "daylight": "V1CorridorDaylightSurfacePreviewDiagnostic",
    "drainage": "V1CorridorDrainageSurfacePreviewDiagnostic",
}
CORRIDOR_BUILD_GUIDED_REVIEW_STEPS = (
    ("centerline", "1. Centerline", ("centerline",), "Check 3D centerline continuity and station ordering."),
    ("design", "2. Design Surface", ("centerline", "design"), "Check finished-grade surface continuity."),
    ("intersections", "3. Intersections", ("intersection",), "Check intersection-controlled Region context and Applied Sections handoff."),
    ("slope_issues", "4. Slope Face Issues", ("daylight",), "Check daylight tie-in fallbacks and EG hits."),
    ("drainage", "5. Drainage Surface", ("centerline", "drainage"), "Check roadside ditch surfaces and intersection low-point drainage coverage."),
    ("drainage_flow", "6. Drainage Flow", ("centerline", "drainage"), "Check Flow Route connections and linked drainage structures."),
)
BUILD_CORRIDOR_PANEL_MIN_WIDTH = 420
BUILD_CORRIDOR_PANEL_MAX_WIDTH = 16777215
REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD = 1.0
REGION_BOUNDARY_SUBGRADE_JUMP_THRESHOLD = 0.15
REGION_BOUNDARY_DAYLIGHT_WIDTH_JUMP_THRESHOLD = 1.0
REGION_BOUNDARY_DAYLIGHT_SLOPE_JUMP_THRESHOLD = 0.05
SURFACE_TRANSITION_DEFAULT_HALF_LENGTH = 5.0
REGION_SURFACE_DISPLAY_Z_OFFSET = 0.25
SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL = 2.5
INTERSECTION_SLOPE_FACE_HEIGHT_CLIP_TOLERANCE = 0.05
INTERSECTION_CONTRACT_HIGHLIGHT_Z_OFFSET = 0.12
INTERSECTION_SLOPE_FACE_BOUNDARY_EXTENSION_LENGTH = 5.0
SURFACE_TRANSITION_SPACING_PRESETS = (
    ("Dense 1.000 m", 1.0),
    ("Normal 2.500 m", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL),
    ("Sparse 5.000 m", 5.0),
    ("Custom", None),
)

CORRIDOR_BUILD_REVIEW_ROW_COLORS = {
    "ready": (220, 245, 224),
    "warning": (255, 241, 205),
    "missing": (238, 238, 238),
    "empty": (255, 241, 205),
    "error": (255, 210, 210),
}
CORRIDOR_BUILD_REVIEW_STATUS_VALUES = ("ready", "warning", "missing", "empty", "error")
CORRIDOR_BUILD_REVIEW_OUTCOME_MATRIX = (
    ("ready", "Preview object exists and has usable geometry."),
    ("warning", "Preview object or diagnostic exists, but the output needs review before downstream use."),
    ("missing", "Preview object is not available because source/result context is missing or not built."),
    ("empty", "Preview object exists, but has no usable geometry rows."),
    ("error", "Preview generation failed and a diagnostic object records the failure."),
)
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
        prj.Label = "Parametric Road Project"
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
        _notify_progress(progress_callback, 81, "Creating intersection surface preview...")
        create_corridor_intersection_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
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
        diagnostic = _corridor_build_preview_diagnostic_object(doc, role)
        rows.append(
            _with_applied_section_review_summary(
                _corridor_build_review_row(role, title, object_name, obj, diagnostic=diagnostic),
                applied_summary,
            )
        )
    return rows


def corridor_build_review_outcome_matrix() -> list[dict[str, str]]:
    """Return the deterministic Build Parametric review status meanings."""

    return [
        {"status": str(status), "meaning": str(meaning)}
        for status, meaning in CORRIDOR_BUILD_REVIEW_OUTCOME_MATRIX
    ]


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
    drainage_flow_summary = corridor_drainage_flow_review_summary(doc)
    intersection_summary = corridor_intersection_review_summary(doc)
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
            elif step_id == "drainage_flow":
                status = str(drainage_flow_summary.get("status", status) or status)
                notes = str(drainage_flow_summary.get("notes", default_notes) or default_notes)
                focus = str(drainage_flow_summary.get("focus", "Drainage Flow") or "Drainage Flow")
            elif step_id == "intersections":
                status = str(intersection_summary.get("status", status) or status)
                notes = str(intersection_summary.get("notes", default_notes) or default_notes)
                focus = str(intersection_summary.get("focus", "Intersections") or "Intersections")
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


def corridor_intersection_review_summary(document=None) -> dict[str, object]:
    """Return a compact Build Parametric intersection readiness summary."""

    patch_summary = corridor_intersection_patch_prerequisite_summary(document)
    rows = [
        row
        for row in corridor_region_boundary_rows(document)
        if str(row.get("intersection", "") or "").strip() not in {"", "-"}
    ]
    if not rows:
        return {
            "status": "missing",
            "notes": str(patch_summary.get("notes", "") or "No intersection-controlled Region rows are available."),
            "focus": "Intersections",
        }
    diagnostic_count = sum(int(row.get("intersection_diagnostic_count", 0) or 0) for row in rows)
    patch_status = str(patch_summary.get("status", "") or "")
    patch_notes = str(patch_summary.get("notes", "") or "").strip()
    if diagnostic_count:
        return {
            "status": "warning",
            "notes": f"{len(rows)} intersection Region row(s); {diagnostic_count} intersection diagnostic(s). {patch_notes}".strip(),
            "focus": "Intersection Region diagnostics",
        }
    if patch_status in {"missing", "warning", "empty"}:
        return {
            "status": "warning" if patch_status != "missing" else "missing",
            "notes": patch_notes or f"{len(rows)} intersection-controlled Region row(s); patch prerequisites need review.",
            "focus": "Intersection Patch prerequisites",
        }
    boundary_review = _intersection_patch_boundary_review_notes(document)
    exclusion_notes = _intersection_exclusion_review_notes(document)
    grading_notes = _intersection_grading_review_notes(document)
    surface_quality_review = _intersection_surface_quality_review_notes(document)
    if int(boundary_review.get("diagnostic_count", 0) or 0) or int(surface_quality_review.get("diagnostic_count", 0) or 0):
        return {
            "status": "warning",
            "notes": _join_review_notes(
                patch_notes or f"{len(rows)} intersection-controlled Region row(s) reflected in Applied Sections.",
                grading_notes,
                str(surface_quality_review.get("notes", "") or ""),
                str(boundary_review.get("notes", "") or ""),
                exclusion_notes,
            ),
            "focus": "Intersection Surface diagnostics",
        }
    return {
        "status": "ready",
        "notes": _join_review_notes(
            patch_notes or f"{len(rows)} intersection-controlled Region row(s) reflected in Applied Sections.",
            grading_notes,
            str(surface_quality_review.get("notes", "") or ""),
            str(boundary_review.get("notes", "") or ""),
            exclusion_notes,
        ),
        "focus": "Intersection Regions",
    }


def corridor_intersection_patch_prerequisite_summary(document=None) -> dict[str, object]:
    """Return display-ready readiness information for future intersection surface patches."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    result = corridor_intersection_patch_prerequisite_result(document)
    diagnostic_count = len(list(result.diagnostic_rows or ()))
    supplemental_summary = _intersection_supplemental_applied_section_summary(
        to_applied_section_set(find_v1_applied_section_set(doc)),
        intersection_id=str(getattr(result, "intersection_id", "") or ""),
        control_region_refs=tuple(getattr(result, "control_region_refs", ()) or ()),
    )
    supplemental_notes = str(supplemental_summary.get("notes", "") or "")
    if result.status == "ready":
        notes = (
            f"Intersection patch prerequisites ready for {result.intersection_id}; "
            f"alignments={result.participating_alignment_count}, "
            f"control regions={result.control_region_count}, "
            f"sections={result.applied_section_count}, "
            f"tie-in edges={result.tie_in_edge_count}, "
            f"boundary points={result.boundary_point_count}."
        )
    elif result.status == "warning":
        notes = (
            f"Intersection patch prerequisites partial for {result.intersection_id or 'intersection'}; "
            f"diagnostics={diagnostic_count}, alignments={result.participating_alignment_count}, "
            f"control regions={result.control_region_count}, sections={result.applied_section_count}, "
            f"tie-in edges={result.tie_in_edge_count}."
        )
    else:
        notes = "Intersection Surface Patch prerequisites are missing."
        if diagnostic_count:
            notes = f"{notes} Diagnostics: {', '.join(result.diagnostic_rows[:3])}."
    if supplemental_notes and result.intersection_id:
        notes = f"{notes} {supplemental_notes}."
    return {
        "status": result.status,
        "intersection_id": result.intersection_id,
        "intersection_kind": result.intersection_kind,
        "participating_alignment_count": result.participating_alignment_count,
        "control_region_count": result.control_region_count,
        "applied_section_count": result.applied_section_count,
        "tie_in_edge_count": result.tie_in_edge_count,
        "boundary_point_count": result.boundary_point_count,
        "diagnostic_count": diagnostic_count,
        "diagnostics": list(result.diagnostic_rows or ()),
        "notes": notes,
        "focus": "Intersection Surface Patch prerequisites",
    }


def _intersection_exclusion_review_notes(document=None) -> str:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return ""
    items: list[str] = []
    for role, label in (("design", "Design"), ("daylight", "Slope")):
        obj = _corridor_build_preview_object(doc, role)
        if obj is None:
            continue
        status = str(getattr(obj, "IntersectionExclusionClipStatus", "") or "")
        if not status:
            continue
        clipped = int(getattr(obj, "IntersectionExclusionClippedTriangleCount", 0) or 0)
        kept = int(getattr(obj, "IntersectionExclusionKeptTriangleCount", 0) or 0)
        exact_cut_candidates = int(getattr(obj, "IntersectionExclusionExactCutCandidateCount", 0) or 0)
        boundary_strategy = str(getattr(obj, "IntersectionExclusionBoundaryStrategy", "") or "")
        aligned = int(getattr(obj, "IntersectionExclusionPracticalBoundaryAligned", 0) or 0)
        suffix_parts = []
        if exact_cut_candidates:
            suffix_parts.append(f"exact-cut candidates={exact_cut_candidates}")
        if boundary_strategy:
            suffix_parts.append(f"boundary={boundary_strategy}")
        if aligned:
            suffix_parts.append("aligned=practical")
        suffix = f", {', '.join(suffix_parts)}" if suffix_parts else ""
        items.append(f"{label} exclusion {status}: clipped={clipped}, kept={kept}{suffix}")
    return "; ".join(items)


def _intersection_patch_boundary_review_notes(document=None) -> dict[str, object]:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    obj = _corridor_build_preview_object(doc, "intersection") if doc is not None else None
    if obj is None:
        return {"diagnostic_count": 0, "notes": ""}
    diagnostic_count = int(getattr(obj, "IntersectionPatchBoundaryDiagnosticCount", 0) or 0)
    hole_count = int(getattr(obj, "IntersectionPatchBoundaryHoleRingCount", 0) or 0)
    island_count = int(getattr(obj, "IntersectionPatchBoundaryIslandRingCount", 0) or 0)
    diagnostics = [str(value or "") for value in list(getattr(obj, "IntersectionPatchBoundaryDiagnostics", []) or []) if str(value or "")]
    parts: list[str] = []
    if hole_count or island_count:
        parts.append(f"patch boundary rings: holes={hole_count}, islands={island_count}")
    if diagnostic_count:
        shown = "; ".join(diagnostics[:2]) if diagnostics else f"{diagnostic_count} diagnostic(s)"
        suffix = f"; +{diagnostic_count - 2} more" if diagnostic_count > 2 else ""
        parts.append(f"patch boundary diagnostics: {shown}{suffix}")
    return {"diagnostic_count": diagnostic_count, "notes": "; ".join(parts)}


def _intersection_grading_review_notes(document=None) -> str:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    obj = _corridor_build_preview_object(doc, "intersection") if doc is not None else None
    if obj is None:
        return ""
    policy_ref = _display_source_id(str(getattr(obj, "IntersectionGradingPolicyRef", "") or ""), "grading:")
    mode = str(getattr(obj, "IntersectionGradingMode", "") or "")
    z_delta = float(getattr(obj, "IntersectionGradingZDeltaMax", 0.0) or 0.0)
    superelevation_sources = int(getattr(obj, "IntersectionSuperelevationSourceCount", 0) or 0)
    superelevation_transitions = int(getattr(obj, "IntersectionSuperelevationTransitionCount", 0) or 0)
    parts: list[str] = []
    if policy_ref or mode:
        label = policy_ref or "default"
        parts.append(f"grading policy={label}, mode={mode or 'use_normal_superelevation'}")
    if z_delta:
        parts.append(f"max z adjustment={z_delta:.3f}m")
    if superelevation_sources or superelevation_transitions:
        parts.append(f"superelevation sources={superelevation_sources}, transitions={superelevation_transitions}")
    return "; ".join(parts)


def _intersection_surface_quality_review_notes(document=None) -> dict[str, object]:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    obj = _corridor_build_preview_object(doc, "intersection") if doc is not None else None
    if obj is None:
        return {"diagnostic_count": 0, "notes": ""}
    triangulation_mode = str(getattr(obj, "PatchTriangulationMode", "") or "")
    boundary_strategy = str(getattr(obj, "PatchSurfaceBoundaryStrategy", "") or "")
    structured_strip_count = int(getattr(obj, "PatchStructuredStripCount", 0) or 0)
    curb_return_surface_edge_count = int(getattr(obj, "PatchCurbReturnSurfaceEdgeCount", 0) or 0)
    curb_return_arc_count = int(getattr(obj, "PatchCurbReturnArcCount", 0) or 0)
    curb_return_arc_sample_count = int(getattr(obj, "PatchCurbReturnArcSampleCount", 0) or 0)
    curb_return_arc_segment_count = int(getattr(obj, "PatchCurbReturnArcSegmentCount", 0) or 0)
    edge_blend_face_count = int(getattr(obj, "PatchEdgeBlendFaceCount", 0) or 0)
    bbox_ratio = float(getattr(obj, "PatchBoundaryBBoxAspectRatio", 0.0) or 0.0)
    min_quality = float(getattr(obj, "PatchTriangleMinQuality", 0.0) or 0.0)
    skinny_count = int(getattr(obj, "PatchTriangleSkinnyCount", 0) or 0)
    long_edge_count = int(getattr(obj, "PatchBoundaryLongEdgeCount", 0) or 0)
    parts: list[str] = []
    diagnostics = 0
    if triangulation_mode:
        if triangulation_mode == "fan_fallback":
            diagnostics += 1
            parts.append(f"warning:patch triangulation={triangulation_mode}; ear clipping failed and fan fallback was used")
        else:
            parts.append(f"patch triangulation={triangulation_mode}")
    if boundary_strategy:
        parts.append(f"surface boundary={boundary_strategy}")
    if structured_strip_count:
        parts.append(f"structured strips={structured_strip_count}")
    if curb_return_surface_edge_count:
        parts.append(f"curb-return surface edges={curb_return_surface_edge_count}")
    if curb_return_arc_count:
        parts.append(f"curb-return arcs={curb_return_arc_count}")
    if curb_return_arc_sample_count:
        parts.append(f"arc samples={curb_return_arc_sample_count}")
    if curb_return_arc_segment_count:
        parts.append(f"arc segments={curb_return_arc_segment_count}")
    if edge_blend_face_count:
        parts.append(f"edge blend faces={edge_blend_face_count}")
    if bbox_ratio:
        if bbox_ratio >= 8.0:
            diagnostics += 1
            parts.append(f"warning:patch bbox ratio={bbox_ratio:.3f}; boundary is elongated")
        else:
            parts.append(f"patch bbox ratio={bbox_ratio:.3f}")
    if min_quality:
        if min_quality < 0.08:
            diagnostics += 1
            parts.append(f"warning:patch min triangle quality={min_quality:.3f}; skinny triangle risk")
        else:
            parts.append(f"patch min triangle quality={min_quality:.3f}")
    if skinny_count:
        diagnostics += skinny_count
        parts.append(f"warning:skinny triangles={skinny_count}; improve intersection boundary/tie-in shape")
    if long_edge_count:
        parts.append(f"warning:long boundary edges={long_edge_count}; patch boundary needs more local control points")
    return {"diagnostic_count": diagnostics, "notes": "; ".join(parts)}


def _join_review_notes(*parts: str) -> str:
    return "; ".join(str(part or "").strip() for part in parts if str(part or "").strip())


def corridor_intersection_patch_prerequisite_result(document=None) -> IntersectionPatchPrerequisiteResult:
    """Evaluate whether source/result contracts are ready for an intersection surface patch."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    if intersection_model is None or not list(getattr(intersection_model, "intersection_rows", []) or []):
        return IntersectionPatchPrerequisiteResult(
            status="missing",
            diagnostic_rows=("intersection_patch_prerequisites_missing: IntersectionModel is required.",),
        )
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        first_row = list(getattr(intersection_model, "intersection_rows", []) or [None])[0]
        return IntersectionPatchPrerequisiteResult(
            status="missing",
            intersection_id=str(getattr(first_row, "intersection_id", "") or ""),
            intersection_kind=str(getattr(first_row, "intersection_kind", "") or ""),
            diagnostic_rows=("intersection_patch_prerequisites_missing: Applied Sections are required.",),
        )

    sections = _station_ordered_applied_sections(applied)
    region_rows = [
        row for row in corridor_region_boundary_rows(doc)
        if str(row.get("intersection", "") or "").strip() not in {"", "-"}
    ]
    if not region_rows:
        first_row = list(getattr(intersection_model, "intersection_rows", []) or [None])[0]
        return IntersectionPatchPrerequisiteResult(
            status="missing",
            intersection_id=str(getattr(first_row, "intersection_id", "") or ""),
            intersection_kind=str(getattr(first_row, "intersection_kind", "") or ""),
            applied_section_count=len(sections),
            diagnostic_rows=("intersection_patch_prerequisites_missing: intersection-controlled Region rows are required.",),
        )

    source_row = list(getattr(intersection_model, "intersection_rows", []) or [None])[0]
    intersection_id = str(getattr(source_row, "intersection_id", "") or str(region_rows[0].get("intersection", "") or ""))
    intersection_kind = str(getattr(source_row, "intersection_kind", "") or "")
    alignment_refs = _unique_text_values([
        str(row.get("alignment_id", "") or "")
        for row in region_rows
        if str(row.get("alignment_id", "") or "").strip()
    ])
    control_region_refs = _unique_text_values([
        str(row.get("region_id", "") or "")
        for row in region_rows
        if str(row.get("region_id", "") or "").strip()
    ])
    control_area_refs = _unique_text_values([
        str(getattr(row, "control_area_id", "") or "")
        for row in list(getattr(intersection_model, "control_area_rows", []) or [])
        if str(getattr(row, "intersection_id", "") or "") == intersection_id
    ])
    section_count = len([
        section for section in sections
        if str(getattr(section, "active_intersection_id", "") or "") == intersection_id
        or str(getattr(section, "region_id", "") or "") in set(control_region_refs)
    ])
    diagnostics: list[str] = []
    if len(alignment_refs) < 2:
        diagnostics.append("intersection_patch_prerequisites_missing: at least two participating alignments are required.")
    if len(control_region_refs) < 2:
        diagnostics.append("intersection_patch_prerequisites_missing: at least two control Regions are required.")
    if section_count < 2:
        diagnostics.append("intersection_patch_tie_in_edge_missing: Applied Sections are not available for enough control Regions.")
    boundary_point_count = max(0, len(control_region_refs) * 2)
    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=IntersectionPatchPrerequisiteResult(
            status="ready",
            intersection_id=intersection_id,
            intersection_kind=intersection_kind,
            alignment_refs=tuple(alignment_refs),
            control_region_refs=tuple(control_region_refs),
            control_area_refs=tuple(control_area_refs),
        ),
        intersection_model=intersection_model,
    )
    tie_in_edge_count = int(getattr(tie_in_result, "edge_count", 0) or 0)
    for diagnostic in list(getattr(tie_in_result, "diagnostic_rows", []) or []):
        diagnostics.append(str(diagnostic or ""))
    supplemental_summary = _intersection_supplemental_applied_section_summary(
        applied,
        intersection_id=intersection_id,
        control_region_refs=tuple(control_region_refs),
    )
    supplemental_alignments = set(supplemental_summary.get("alignment_refs", []) or [])
    missing_supplemental_alignments = [ref for ref in alignment_refs if ref not in supplemental_alignments]
    if alignment_refs and missing_supplemental_alignments:
        diagnostics.append(
            "warning:intersection_supplemental_applied_sections_missing: "
            "Build Sections should add intersection_supplemental rows for "
            + ", ".join(missing_supplemental_alignments)
            + "."
        )
    if boundary_point_count < 4:
        diagnostics.append("intersection_patch_boundary_too_few_points: control Region boundary is not sufficient for a patch.")
    status = "ready" if not _diagnostics_include_error(diagnostics) else "warning"
    return IntersectionPatchPrerequisiteResult(
        status=status,
        intersection_id=intersection_id,
        intersection_kind=intersection_kind,
        alignment_refs=tuple(alignment_refs),
        control_region_refs=tuple(control_region_refs),
        control_area_refs=tuple(control_area_refs),
        participating_alignment_count=len(alignment_refs),
        control_region_count=len(control_region_refs),
        applied_section_count=section_count,
        tie_in_edge_count=tie_in_edge_count,
        boundary_point_count=boundary_point_count,
        diagnostic_rows=tuple(diagnostics),
    )


def _intersection_supplemental_applied_section_summary(
    applied_section_set,
    *,
    intersection_id: str = "",
    control_region_refs: tuple[str, ...] = (),
) -> dict[str, object]:
    if applied_section_set is None:
        return {"count": 0, "alignment_refs": [], "notes": "intersection supplemental sections=0"}
    section_by_id = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    target_intersection = str(intersection_id or "").strip()
    target_regions = {str(value or "").strip() for value in list(control_region_refs or ()) if str(value or "").strip()}
    counts: dict[str, int] = {}
    total = 0
    for row in list(getattr(applied_section_set, "station_rows", []) or []):
        if str(getattr(row, "kind", "") or "") != "intersection_supplemental":
            continue
        section = section_by_id.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is None:
            continue
        section_intersection = str(getattr(section, "active_intersection_id", "") or "").strip()
        section_region = str(getattr(section, "region_id", "") or "").strip()
        if target_intersection and section_intersection and section_intersection != target_intersection:
            continue
        if target_regions and not section_intersection and section_region not in target_regions:
            continue
        alignment_ref = str(getattr(section, "alignment_id", "") or "").strip() or "-"
        counts[alignment_ref] = int(counts.get(alignment_ref, 0) or 0) + 1
        total += 1
    alignment_refs = sorted(ref for ref in counts if ref != "-")
    if counts:
        distribution = ", ".join(f"{ref}={count}" for ref, count in sorted(counts.items()))
        notes = f"intersection supplemental sections={total} ({distribution})"
    else:
        notes = "intersection supplemental sections=0"
    return {"count": total, "alignment_refs": alignment_refs, "notes": notes}


def corridor_intersection_contract_review_rows(document=None) -> list[dict[str, object]]:
    """Return edge-network-first intersection contract rows for Build Parametric review."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    if intersection_model is None or not list(getattr(intersection_model, "intersection_rows", []) or []):
        return [
            {
                "contract_family": "intersection",
                "status": "missing",
                "row_id": "",
                "role": "",
                "source_refs": "",
                "boundary_refs": "",
                "focus_object": "",
                "notes": "IntersectionModel is required before edge-network-first review.",
            }
        ]
    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(intersection_model)
    edge_network = service.evaluate_edge_network(intersection_model, topology)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network)
    corridor_clips = service.evaluate_corridor_clipping(intersection_model, topology, surface_zones)
    drainage_hints = service.evaluate_drainage_hints(intersection_model, surface_zones)
    rows: list[dict[str, object]] = []
    rows.append(
        {
            "contract_family": "topology",
            "status": topology.status,
            "row_id": topology.topology_result_id,
            "role": "control_area",
            "source_refs": ", ".join(list(getattr(topology, "source_refs", []) or [])),
            "boundary_refs": ", ".join(row.control_area_id for row in list(topology.control_area_rows or [])),
            "focus_object": "V1CorridorIntersectionSurfacePreview",
            "notes": (
                f"legs={topology.leg_span_count}; control areas={topology.control_area_count}; "
                f"alignments={topology.participating_alignment_count}; diagnostics={len(topology.diagnostic_rows)}"
            ),
        }
    )
    for row in list(edge_network.edge_rows or []):
        rows.append(
            {
                "contract_family": "edge_network",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or edge_network.status)),
                "row_id": str(getattr(row, "edge_id", "") or ""),
                "role": str(getattr(row, "edge_role", "") or ""),
                "source_refs": str(getattr(row, "source_policy_ref", "") or ""),
                "boundary_refs": _join_review_notes(
                    str(getattr(row, "leg_ref", "") or ""),
                    str(getattr(row, "control_area_ref", "") or ""),
                    str(getattr(row, "alignment_ref", "") or ""),
                ),
                "focus_object": "V1IntersectionEdgeNetworkPreview",
                "notes": _join_review_notes(
                    f"family={getattr(row, 'edge_family', '')}",
                    f"side={getattr(row, 'side', '')}",
                    f"STA {float(getattr(row, 'station_start', 0.0) or 0.0):.3f}-{float(getattr(row, 'station_end', 0.0) or 0.0):.3f}",
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    for row in list(surface_zones.zone_rows or []):
        rows.append(
            {
                "contract_family": "surface_zone",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or surface_zones.status)),
                "row_id": str(getattr(row, "zone_id", "") or ""),
                "role": str(getattr(row, "design_zone_role", "") or getattr(row, "zone_role", "") or ""),
                "source_refs": ", ".join(list(getattr(row, "source_edge_refs", ()) or ())),
                "boundary_refs": ", ".join(list(getattr(row, "boundary_edge_refs", ()) or ())),
                "focus_object": "V1CorridorIntersectionSurfacePreview",
                "notes": _join_review_notes(
                    f"zone={getattr(row, 'zone_role', '')}",
                    f"surface={getattr(row, 'surface_role', '')}",
                    f"triangulation={getattr(row, 'triangulation_method', '')}",
                    "; ".join(list(getattr(row, "diagnostic_rows", ()) or ())),
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    for row in list(corridor_clips.clip_rows or []):
        rows.append(
            {
                "contract_family": "corridor_clip",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or corridor_clips.status)),
                "row_id": str(getattr(row, "clip_id", "") or ""),
                "role": str(getattr(row, "surface_role", "") or ""),
                "source_refs": str(getattr(row, "control_area_ref", "") or ""),
                "boundary_refs": ", ".join(list(getattr(row, "protected_zone_refs", ()) or ())),
                "focus_object": "V1CorridorIntersectionExclusionZonePreview",
                "notes": _join_review_notes(
                    f"alignment={getattr(row, 'alignment_ref', '')}",
                    f"method={getattr(row, 'clip_method', '')}",
                    f"timing={getattr(row, 'clip_timing', '')}",
                    "; ".join(list(getattr(row, "diagnostic_rows", ()) or ())),
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    for row in list(drainage_hints.hint_rows or []):
        rows.append(
            {
                "contract_family": "drainage_hint",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or drainage_hints.status)),
                "row_id": str(getattr(row, "hint_id", "") or ""),
                "role": str(getattr(row, "hint_kind", "") or ""),
                "source_refs": _join_review_notes(
                    str(getattr(row, "drainage_policy_ref", "") or ""),
                    ", ".join(list(getattr(row, "source_edge_refs", ()) or ())),
                ),
                "boundary_refs": _join_review_notes(
                    str(getattr(row, "zone_ref", "") or ""),
                    ", ".join(list(getattr(row, "control_area_refs", ()) or ())),
                ),
                "focus_object": "V1CorridorIntersectionSurfacePreview",
                "notes": _join_review_notes(
                    f"zone={getattr(row, 'zone_role', '')}",
                    f"surface={getattr(row, 'surface_role', '')}",
                    f"recommend={getattr(row, 'recommended_element_kind', '')}",
                    "; ".join(list(getattr(row, "diagnostic_rows", ()) or ())),
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    return rows


def corridor_intersection_contract_review_summary(document=None) -> dict[str, object]:
    """Return a compact edge-network-first contract summary for Build Parametric."""

    rows = corridor_intersection_contract_review_rows(document)
    real_rows = [row for row in rows if row.get("row_id")]
    if not real_rows:
        return {
            "status": "missing",
            "row_count": 0,
            "notes": str(rows[0].get("notes", "No intersection contract rows.") if rows else "No intersection contract rows."),
        }
    error_count = sum(1 for row in real_rows if str(row.get("status", "") or "") == "error")
    warning_count = sum(1 for row in real_rows if str(row.get("status", "") or "") in {"warning", "warn"})
    family_counts: dict[str, int] = {}
    for row in real_rows:
        family = str(row.get("contract_family", "") or "contract")
        family_counts[family] = family_counts.get(family, 0) + 1
    status = "error" if error_count else ("warning" if warning_count else "ready")
    counts = ", ".join(f"{family}={count}" for family, count in sorted(family_counts.items()))
    return {
        "status": status,
        "row_count": len(real_rows),
        "warning_count": warning_count,
        "error_count": error_count,
        "notes": f"Intersection contracts: {counts}; warnings={warning_count}; errors={error_count}.",
    }


def _intersection_contract_display_status(status: str) -> str:
    text = str(status or "").strip().lower()
    if text == "candidate":
        return "ready"
    if text == "warn":
        return "warning"
    return text or "missing"


def focus_corridor_intersection_contract_review_row(document=None, row_index: int = 0):
    """Create/select a clear 3D highlight for one intersection contract review row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_intersection_contract_review_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Intersection contract review row index is out of range.")
    row = rows[row_index]
    highlight = _create_intersection_contract_review_highlight(
        document=doc,
        row=row,
        row_index=row_index,
    )
    if highlight is not None:
        _set_object_visibility(highlight, True)
        _select_and_fit_object(highlight)
        return highlight
    candidates = [
        str(row.get("focus_object", "") or ""),
        "V1IntersectionEdgeNetworkPreview",
        "V1CorridorIntersectionSurfacePreview",
        "V1CorridorIntersectionExclusionZonePreview",
    ]
    for name in candidates:
        obj = doc.getObject(name) if doc is not None and name else None
        if obj is not None:
            _select_and_fit_object(obj)
            return obj
    raise RuntimeError("No 3D review object is available for the selected intersection contract row.")


def _create_intersection_contract_review_highlight(*, document=None, row: dict[str, object], row_index: int = 0):
    """Create a bright linework overlay for a selected Build Parametric intersection contract row."""

    if document is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    family = str(row.get("contract_family", "") or "").strip()
    row_id = str(row.get("row_id", "") or "").strip()
    context = _intersection_contract_highlight_context(document)
    shapes: list[object] = []
    refs: list[str] = []
    if family == "edge_network" and row_id:
        edge = _intersection_contract_edge_by_id(context.get("edge_rows", []), row_id)
        shape = _intersection_contract_edge_highlight_shape(Part, AppModule, edge)
        if shape is not None:
            shapes.append(shape)
            refs.append(row_id)
    elif family == "surface_zone" and row_id:
        zone = _intersection_contract_zone_by_id(context.get("zone_rows", []), row_id)
        edge_refs = _intersection_contract_zone_edge_refs(zone)
        for edge_ref in edge_refs:
            edge = _intersection_contract_edge_by_id(context.get("edge_rows", []), edge_ref)
            shape = _intersection_contract_edge_highlight_shape(Part, AppModule, edge)
            if shape is not None:
                shapes.append(shape)
                refs.append(edge_ref)
        if not shapes:
            shapes.extend(_intersection_contract_boundary_segment_shapes(Part, AppModule, context.get("boundary_result"), refs))
    elif family == "corridor_clip" and row_id:
        shapes.extend(_intersection_contract_patch_boundary_shapes(Part, AppModule, context.get("patch_boundary_result"), refs))
    elif family == "drainage_hint":
        zone_refs = {
            value.strip()
            for value in str(row.get("boundary_refs", "") or "").replace(";", ",").split(",")
            if value.strip()
        }
        for zone in list(context.get("zone_rows", []) or []):
            zone_id = str(getattr(zone, "zone_id", "") or "")
            if zone_id not in zone_refs:
                continue
            for edge_ref in _intersection_contract_zone_edge_refs(zone):
                edge = _intersection_contract_edge_by_id(context.get("edge_rows", []), edge_ref)
                shape = _intersection_contract_edge_highlight_shape(Part, AppModule, edge)
                if shape is not None:
                    shapes.append(shape)
                    refs.append(edge_ref)
        if not shapes:
            shapes.extend(_intersection_contract_boundary_segment_shapes(Part, AppModule, context.get("boundary_result"), refs))
    else:
        shapes.extend(_intersection_contract_boundary_segment_shapes(Part, AppModule, context.get("boundary_result"), refs))
        if not shapes:
            for edge in list(context.get("edge_rows", []) or []):
                shape = _intersection_contract_edge_highlight_shape(Part, AppModule, edge)
                if shape is not None:
                    shapes.append(shape)
                    refs.append(str(getattr(edge, "edge_id", "") or ""))
    if not shapes:
        focus_shape = _intersection_contract_focus_object_shape(document, row)
        if focus_shape is not None:
            shapes.append(focus_shape)
            refs.append(str(row.get("focus_object", "") or ""))
    if not shapes:
        return None
    object_name = "ReviewIntersectionContractHighlight"
    obj = document.getObject(object_name)
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = "Intersection Contract Highlight"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_intersection_contract_review_highlight")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "intersection_contract")
    _set_preview_property(obj, "ContractFamily", family)
    _set_preview_property(obj, "ContractRowId", row_id)
    _set_preview_integer_property(obj, "ContractRowIndex", int(row_index))
    _set_preview_property(obj, "IntersectionId", str(context.get("intersection_id", "") or ""))
    _set_preview_string_list_property(obj, "HighlightedRefs", _unique_text_values(refs))
    _set_preview_integer_property(obj, "HighlightedShapeCount", len(shapes))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = (1.00, 0.95, 0.00)
            vobj.LineColor = (1.00, 0.95, 0.00)
            vobj.PointColor = (1.00, 0.95, 0.00)
            vobj.LineWidth = 9.0
            vobj.PointSize = 10.0
            vobj.Transparency = 0
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(document), obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def _intersection_contract_highlight_context(document) -> dict[str, object]:
    intersection_model = to_intersection_model(find_v1_intersection_model(document))
    context: dict[str, object] = {
        "intersection_model": intersection_model,
        "intersection_id": "",
        "edge_rows": [],
        "zone_rows": [],
        "boundary_result": None,
        "patch_boundary_result": None,
    }
    if intersection_model is None:
        return context
    service = IntersectionEvaluationService()
    try:
        topology = service.evaluate_topology(intersection_model)
        edge_network = service.evaluate_edge_network(intersection_model, topology)
        surface_zones = service.evaluate_surface_zones(intersection_model, edge_network)
        context["intersection_id"] = str(getattr(edge_network, "intersection_id", "") or getattr(topology, "intersection_id", "") or "")
        context["edge_rows"] = list(getattr(edge_network, "edge_rows", []) or [])
        context["zone_rows"] = list(getattr(surface_zones, "zone_rows", []) or [])
    except Exception:
        pass
    try:
        applied = to_applied_section_set(find_v1_applied_section_set(document))
        applied = _applied_section_set_with_intersection_tie_in_sections(applied, document=document)
        prerequisite = corridor_intersection_patch_prerequisite_result(document)
        if applied is not None and str(getattr(prerequisite, "status", "") or "") != "missing":
            tie_in_result = corridor_intersection_tie_in_edge_result(
                applied,
                prerequisite=prerequisite,
                intersection_model=intersection_model,
            )
            boundary_result = corridor_intersection_boundary_segment_result(
                tie_in_result,
                intersection_model=intersection_model,
            )
            context["boundary_result"] = boundary_result
            context["patch_boundary_result"] = corridor_intersection_patch_boundary_result(boundary_result)
            if not str(context.get("intersection_id", "") or ""):
                context["intersection_id"] = str(getattr(boundary_result, "intersection_id", "") or "")
    except Exception:
        pass
    return context


def _intersection_contract_edge_by_id(edge_rows: list[object], edge_id: str):
    target = str(edge_id or "").strip()
    for edge in list(edge_rows or []):
        if str(getattr(edge, "edge_id", "") or "") == target:
            return edge
    return None


def _intersection_contract_zone_by_id(zone_rows: list[object], zone_id: str):
    target = str(zone_id or "").strip()
    for zone in list(zone_rows or []):
        if str(getattr(zone, "zone_id", "") or "") == target:
            return zone
    return None


def _intersection_contract_zone_edge_refs(zone) -> list[str]:
    if zone is None:
        return []
    refs: list[str] = []
    for attr in ("boundary_edge_refs", "source_edge_refs", "inner_edge_refs", "outer_edge_refs", "tie_edge_refs"):
        refs.extend(str(value or "") for value in list(getattr(zone, attr, ()) or ()))
    return _unique_text_values(refs)


def _intersection_contract_edge_highlight_shape(part_module, app_module, edge):
    if edge is None:
        return None
    start = tuple(getattr(edge, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
    end = tuple(getattr(edge, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
    return _intersection_contract_polyline_shape(part_module, app_module, [start, end])


def _intersection_contract_boundary_segment_shapes(part_module, app_module, boundary_result, refs: list[str]) -> list[object]:
    shapes: list[object] = []
    if boundary_result is None:
        return shapes
    for segment in list(getattr(boundary_result, "segment_rows", []) or []):
        points = list(getattr(segment, "chord_points_xyz", ()) or ())
        if len(points) < 2:
            points = [
                tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
                tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
            ]
        shape = _intersection_contract_polyline_shape(part_module, app_module, points)
        if shape is not None:
            shapes.append(shape)
            refs.append(str(getattr(segment, "boundary_segment_id", "") or ""))
    return shapes


def _intersection_contract_patch_boundary_shapes(part_module, app_module, patch_boundary_result, refs: list[str]) -> list[object]:
    if patch_boundary_result is None:
        return []
    grouped: dict[str, list[object]] = {}
    for point in list(getattr(patch_boundary_result, "point_rows", []) or []):
        ring_id = str(getattr(point, "ring_id", "") or "outer")
        grouped.setdefault(ring_id, []).append(point)
    shapes: list[object] = []
    for ring_id, points in sorted(grouped.items()):
        ordered = sorted(points, key=lambda item: int(getattr(item, "order_index", 0) or 0))
        xyz = [
            (
                float(getattr(point, "x", 0.0) or 0.0),
                float(getattr(point, "y", 0.0) or 0.0),
                float(getattr(point, "z", 0.0) or 0.0),
            )
            for point in ordered
        ]
        if len(xyz) >= 3:
            xyz.append(xyz[0])
        shape = _intersection_contract_polyline_shape(part_module, app_module, xyz)
        if shape is not None:
            shapes.append(shape)
            refs.append(ring_id)
    return shapes


def _intersection_contract_focus_object_shape(document, row: dict[str, object]):
    if document is None:
        return None
    focus_name = str(row.get("focus_object", "") or "").strip()
    if not focus_name:
        return None
    try:
        obj = document.getObject(focus_name)
    except Exception:
        obj = None
    if obj is None:
        return None
    shape = getattr(obj, "Shape", None)
    if shape is None:
        return None
    try:
        if bool(getattr(shape, "isNull", lambda: False)()):
            return None
    except Exception:
        pass
    try:
        return shape.copy()
    except Exception:
        return shape


def _intersection_contract_polyline_shape(part_module, app_module, points_xyz: list[tuple[float, float, float]]):
    vectors = []
    for point in list(points_xyz or []):
        if len(point) < 3:
            continue
        try:
            vectors.append(
                app_module.Vector(
                    float(point[0]),
                    float(point[1]),
                    float(point[2]) + INTERSECTION_CONTRACT_HIGHLIGHT_Z_OFFSET,
                )
            )
        except Exception:
            continue
    if len(vectors) < 2:
        return None
    try:
        if len(vectors) == 2:
            if vectors[0].distanceToPoint(vectors[1]) <= 1.0e-9:
                return None
            return part_module.makeLine(vectors[0], vectors[1])
        return part_module.makePolygon(vectors)
    except Exception:
        return None


def corridor_drainage_flow_review_rows(document=None) -> list[dict[str, object]]:
    """Return Flow Route review rows for Build Corridor Guided Review."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    if drainage_model is None:
        return [
            {
                "flow_route_id": "",
                "status": "missing",
                "from_element": "",
                "to_element": "",
                "outlet": "",
                "structure_refs": "",
                "station_start": "",
                "station_end": "",
                "notes": "DrainageModel is required before Drainage Flow review.",
            }
        ]
    element_by_id = {
        str(getattr(row, "drainage_element_id", "") or ""): row
        for row in list(getattr(drainage_model, "element_rows", []) or [])
    }
    structure_model = to_structure_model(find_v1_structure_model(doc))
    structure_by_id = {
        str(getattr(row, "structure_id", "") or ""): row
        for row in list(getattr(structure_model, "structure_rows", []) or [])
    } if structure_model is not None else {}
    rows: list[dict[str, object]] = []
    for flow_row in list(getattr(drainage_model, "flow_route_rows", []) or []):
        connected_elements = _drainage_flow_connected_elements(flow_row, element_by_id)
        structure_refs = _drainage_flow_structure_refs(flow_row, connected_elements)
        station_range = _drainage_flow_station_range(flow_row, connected_elements, structure_by_id)
        route_id = str(getattr(flow_row, "flow_route_id", "") or "")
        from_ref = str(getattr(flow_row, "from_element_ref", "") or "")
        to_ref = str(getattr(flow_row, "to_element_ref", "") or "")
        outlet_ref = str(getattr(flow_row, "outlet_ref", "") or "")
        chain_values = [value for value in (from_ref, to_ref, outlet_ref) if value]
        missing_refs = [
            ref
            for ref in (from_ref, to_ref)
            if ref and ref.startswith("drainage:") and ref not in element_by_id
        ]
        if missing_refs:
            status = "missing"
            notes = "Broken Flow Route element refs: " + ", ".join(_display_source_ref(ref) for ref in missing_refs)
        elif not chain_values:
            status = "missing"
            notes = "Flow Route has no From, To, or Outlet refs."
        elif not structure_refs:
            status = "warn"
            notes = f"Route {' -> '.join(_display_source_ref(value) for value in chain_values)} has no linked Structure ref."
        else:
            status = "ready"
            notes = (
                f"Route {' -> '.join(_display_source_ref(value) for value in chain_values)}; "
                f"structures={', '.join(_display_source_ref(ref) for ref in structure_refs)}"
            )
        rows.append(
            {
                "flow_route_id": route_id,
                "status": status,
                "from_element": from_ref,
                "to_element": to_ref,
                "outlet": outlet_ref,
                "structure_refs": ", ".join(structure_refs),
                "station_start": "" if station_range is None else station_range[0],
                "station_end": "" if station_range is None else station_range[1],
                "highlight_mode": _drainage_flow_row_highlight_mode(doc, route_id),
                "notes": notes,
            }
        )
    if not rows:
        return [
            {
                "flow_route_id": "",
                "status": "missing",
                "from_element": "",
                "to_element": "",
                "outlet": "",
                "structure_refs": "",
                "station_start": "",
                "station_end": "",
                "notes": "No Drainage Flow Route rows.",
            }
        ]
    return rows


def corridor_drainage_flow_review_summary(document=None) -> dict[str, object]:
    """Return a compact Flow Route readiness summary for Guided Review."""

    rows = corridor_drainage_flow_review_rows(document)
    real_rows = [row for row in rows if row.get("flow_route_id")]
    if not real_rows:
        return {
            "status": "missing",
            "route_count": 0,
            "structure_count": 0,
            "focus": "Drainage Flow",
            "notes": str(rows[0].get("notes", "No Drainage Flow Route rows.") if rows else "No Drainage Flow Route rows."),
        }
    ready = sum(1 for row in real_rows if row.get("status") == "ready")
    warn = sum(1 for row in real_rows if row.get("status") == "warn")
    missing = sum(1 for row in real_rows if row.get("status") == "missing")
    structure_refs = sorted(
        {
            ref.strip()
            for row in real_rows
            for ref in str(row.get("structure_refs", "") or "").split(",")
            if ref.strip()
        }
    )
    route_labels = [_display_source_ref(row.get("flow_route_id", "")) for row in real_rows]
    if missing:
        status = "missing"
        notes = f"{missing} Flow Route row(s) have broken or empty route refs."
    elif warn:
        status = "warn"
        notes = f"{warn} Flow Route row(s) have no linked Structure ref."
    else:
        status = "ready"
        notes = f"Flow Routes: {len(real_rows)}; structures: {', '.join(_display_source_ref(ref) for ref in structure_refs) or '-'}."
    return {
        "status": status,
        "route_count": len(real_rows),
        "ready_count": ready,
        "warn_count": warn,
        "missing_count": missing,
        "structure_count": len(structure_refs),
        "focus": ", ".join(route_labels[:3]) + ("..." if len(route_labels) > 3 else ""),
        "notes": notes,
    }


def corridor_drainage_review_rows(document=None) -> list[dict[str, object]]:
    """Return station-level drainage source diagnostics from Applied Sections."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return [
            {
                "station": "",
                    "section_id": "",
                    "context": "roadside_drainage",
                    "context_label": "Roadside Drainage",
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
    region_model = to_region_model(find_v1_region_model(doc))
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    output: list[dict[str, object]] = []
    for row in sorted(list(getattr(applied, "station_rows", []) or []), key=lambda item: float(getattr(item, "station", 0.0) or 0.0)):
        section_id = str(getattr(row, "applied_section_id", "") or "")
        section = sections.get(section_id)
        station = float(getattr(row, "station", 0.0) or 0.0)
        active_ditch_rows = _active_ditch_drainage_rows(
            drainage_model,
            region_model=region_model,
            station=station,
        )
        if section is None:
            output.append(
                {
                    "station": station,
                    "section_id": section_id,
                    "context": "roadside_drainage",
                    "context_label": "Roadside Drainage",
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
        mismatch_notes = _drainage_source_surface_mismatch_notes(active_ditch_rows, ditch_points)
        if active_ditch_rows and any(note.startswith("missing_side=") for note in mismatch_notes):
            status = "missing"
            notes = "Active Drainage ditch row has no matching ditch_surface side. " + " ".join(mismatch_notes)
        elif not ditch_points:
            status = "missing"
            notes = "No ditch_surface point rows from Assembly/Applied Sections."
            if active_ditch_rows:
                notes += " " + " ".join(mismatch_notes)
        elif mismatch_notes:
            status = "warn"
            notes = "Drainage source/result mismatch. " + " ".join(mismatch_notes)
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
                "context": "roadside_drainage",
                "context_label": "Roadside Drainage",
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
        output = [
            {
                "station": "",
                "section_id": "",
                "context": "roadside_drainage",
                "context_label": "Roadside Drainage",
                "status": "missing",
                "ditch_point_count": 0,
                "left_count": 0,
                "right_count": 0,
                "notes": "No Applied Section station rows.",
            }
        ]
    if output and output[0].get("station", "") == "":
        return output
    output.extend(corridor_intersection_drainage_review_rows(doc, marker_start_index=len(output)))
    return output


def corridor_intersection_drainage_review_rows(document=None, *, marker_start_index: int = 0) -> list[dict[str, object]]:
    """Return intersection low-point and Drainage Element coverage diagnostics."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return []
    applied = _applied_section_set_with_intersection_tie_in_sections(
        applied,
        document=doc,
    )
    prerequisite = corridor_intersection_patch_prerequisite_result(doc)
    if str(getattr(prerequisite, "status", "") or "") != "ready":
        return []
    patch_points = _intersection_patch_fg_points(applied, prerequisite)
    if not patch_points:
        return []
    low_point = min(patch_points, key=lambda item: float(item.get("z", 0.0) or 0.0))
    low_z = float(low_point.get("z", 0.0) or 0.0)
    low_points = [point for point in patch_points if abs(float(point.get("z", 0.0) or 0.0) - low_z) <= 0.001]
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    control_refs = list(getattr(prerequisite, "control_region_refs", ()) or ())
    coverage = _intersection_drainage_coverage(
        drainage_model,
        prerequisite,
        low_point_station=float(low_point.get("station", 0.0) or 0.0),
    )
    coverage_rows = list(coverage.get("ready_rows", []) or [])
    candidate_rows = list(coverage.get("candidate_rows", []) or [])
    coverage_diagnostics = list(coverage.get("diagnostics", []) or [])
    coverage_refs = [
        str(getattr(row, "drainage_element_id", "") or "")
        for row in coverage_rows
        if str(getattr(row, "drainage_element_id", "") or "").strip()
    ]
    if coverage_rows:
        status = "ready"
        notes = (
            f"Intersection drainage handoff ready. low_point_z={low_z:.3f}; "
            f"Drainage Elements={', '.join(_display_source_ref(ref) for ref in coverage_refs[:4])}."
        )
    elif candidate_rows:
        status = "warn"
        candidate_refs = [
            str(getattr(row, "drainage_element_id", "") or "")
            for row in candidate_rows
            if str(getattr(row, "drainage_element_id", "") or "").strip()
        ]
        notes = (
            f"Intersection Drainage Elements are linked, but none cover the low-point station. "
            f"low_point_station={float(low_point.get('station', 0.0) or 0.0):.3f}; "
            f"candidates={', '.join(_display_source_ref(ref) for ref in candidate_refs[:4]) or '-'}."
        )
    else:
        status = "missing"
        notes = (
            f"Intersection low-point candidate has no Drainage Element coverage. low_point_z={low_z:.3f}; "
            f"control_regions={', '.join(_display_source_ref(ref) for ref in control_refs) or '-'}."
        )
    return [
        {
            "review_kind": "intersection_drainage",
            "context": "intersection_drainage",
            "context_label": "Intersection Drainage",
            "intersection_id": intersection_id,
            "station": float(low_point.get("station", 0.0) or 0.0),
            "section_id": "",
            "status": status,
            "ditch_point_count": len(patch_points),
            "left_count": "-",
            "right_count": "-",
            "marker_object": _drainage_review_marker_name(int(marker_start_index or 0)),
            "marker_label": f"Suggested Inlet - {intersection_id or 'intersection'}",
            "marker_kind": "suggested_inlet",
            "x": f"{float(low_point.get('x', 0.0) or 0.0):.6f}",
            "y": f"{float(low_point.get('y', 0.0) or 0.0):.6f}",
            "z": f"{low_z:.6f}",
            "low_point_count": len(low_points),
            "drainage_element_refs": ",".join(coverage_refs),
            "drainage_candidate_refs": ",".join(
                str(getattr(row, "drainage_element_id", "") or "")
                for row in candidate_rows
                if str(getattr(row, "drainage_element_id", "") or "").strip()
            ),
            "control_region_refs": ",".join(control_refs),
            "diagnostics": "; ".join(coverage_diagnostics),
            "notes": notes,
        }
    ]


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
        intersection_missing = sum(
            1 for row in real_rows
            if row.get("status") == "missing" and row.get("review_kind") == "intersection_drainage"
        )
        if intersection_missing:
            notes = f"{intersection_missing} intersection(s) without Drainage Element coverage."
        else:
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
                "alignment_id": "",
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
                "alignment_id": "",
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
    region_models = _document_region_models(doc)
    region_model = region_models[0] if region_models else None
    structure_model = to_structure_model(find_v1_structure_model(doc))
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    source_region_groups = [
        (model, _region_source_rows(model))
        for model in region_models
        if _region_source_rows(model)
    ]
    if source_region_groups:
        rows: list[dict[str, object]] = []
        for model, source_rows in source_region_groups:
            alignment_sections = _sections_for_region_model(sections, model)
            rows.extend(
                _region_boundary_rows_from_source_regions(
                    source_rows,
                    alignment_sections,
                    document=doc,
                    region_model=model,
                    structure_model=structure_model,
                    drainage_model=drainage_model,
                    intersection_model=intersection_model,
                )
            )
        return rows
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
        row = {
            "alignment_id": _unique_join(_section_text_values(group_sections, "alignment_id")),
            "region_id": str(group.get("region_id", "") or ""),
            "station_start": float(group.get("station_start", 0.0) or 0.0),
            "station_end": float(group.get("station_end", 0.0) or 0.0),
            "assembly": _unique_join(_section_text_values(group_sections, "assembly_id")),
            "structure": _region_group_structure_summary(
                group_sections,
                region_model=region_model,
                structure_model=structure_model,
            ),
            "drainage": _region_group_drainage_summary(
                group_sections,
                region_model=region_model,
                drainage_model=drainage_model,
            ),
            "intersection": _region_group_intersection_summary(None, group_sections, intersection_model=intersection_model),
            "surface_status": _region_group_surface_status(group_sections),
            "boundary_status": boundary_status,
            "diagnostics": _region_boundary_diagnostic_summary(diagnostics),
            "diagnostic_count": len(diagnostics),
        }
        row.update(_region_generated_object_summary(doc, row))
        rows.append(row)
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
    objects = _corridor_region_preview_objects(doc, region_id, row=row)
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
    if step[0] == "drainage_flow":
        return focus_corridor_drainage_flow_review(doc)
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
        fallback = _corridor_build_preview_object(doc, "daylight")
        if fallback is None:
            raise RuntimeError(f"Slope Face marker object was not found: {object_name}")
        _select_and_fit_object(fallback)
        return fallback
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


def focus_corridor_drainage_flow_review(document=None):
    """Create/select a 3D highlight for Drainage Flow Route structure context."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = [row for row in corridor_drainage_flow_review_rows(doc) if row.get("flow_route_id")]
    if not rows:
        raise RuntimeError("No Drainage Flow Route rows are available.")
    obj = _create_drainage_flow_review_highlight(document=doc, rows=rows)
    if obj is None:
        raise RuntimeError("Drainage Flow highlight was not created.")
    set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
    set_corridor_build_preview_visibility(doc, "centerline", True)
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
    for obj in _corridor_build_auxiliary_preview_objects(doc):
        _set_object_visibility(obj, bool(visible))
        changed += 1
    for obj in _corridor_build_region_preview_objects(doc):
        _set_object_visibility(obj, False)
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
    """Create or update a 3D centerline preview from the shared Centerline3DResult."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    applied_section_set = _applied_section_set_with_intersection_tie_in_sections(
        applied_section_set,
        document=doc,
    )
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None

    points, stations, source_mode, centerline_result_id = _corridor_centerline_preview_points(
        doc,
        AppModule,
    )
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
    _set_preview_property(obj, "PreviewSource", source_mode)
    _set_preview_property(obj, "Centerline3DResultId", centerline_result_id)
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
    applied_section_set = _applied_section_set_with_intersection_tie_in_sections(
        applied_section_set,
        document=doc,
    )
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
        tin_surface = _clip_tin_surface_by_intersection_exclusion(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
            surface_role="design",
        )
    except Exception as exc:
        _record_corridor_build_preview_diagnostic(
            doc,
            role="design",
            surface_kind="design_surface",
            status="error",
            notes=f"Design Surface preview was not created: {exc}",
            project=project or find_project(doc),
        )
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDesignSurfacePreview",
        label_prefix="Corridor Design Surface",
        surface_role="design",
        recompute=False,
    )
    if str(getattr(result, "status", "") or "") == "error":
        _record_corridor_build_preview_diagnostic(
            doc,
            role="design",
            surface_kind="design_surface",
            status="error",
            notes=str(getattr(result, "notes", "") or "Design Surface preview mapper failed."),
            project=project or find_project(doc),
        )
        return None
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _remove_corridor_build_preview_diagnostic(doc, "design")
        _attach_corridor_surface_preview_contract(
            preview_obj,
            role="design",
            surface_kind="design_surface",
            surface_id=surface_id,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=applied_section_set,
            preview_result=result,
        )
        _attach_intersection_exclusion_zone_metadata(preview_obj, doc)
        _attach_intersection_exclusion_clip_quality(preview_obj, tin_surface)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def create_corridor_intersection_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update the first explicit intersection surface patch preview."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_section_set = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied_section_set is None:
        _remove_preview_object(doc, "V1CorridorIntersectionSurfacePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionCurbReturnSlopePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionTieInEdgePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionBoundarySegmentPreview")
        _remove_preview_object(doc, "V1CorridorIntersectionExclusionZonePreview")
        _record_corridor_build_preview_diagnostic(
            doc,
            role="intersection",
            surface_kind="intersection_surface",
            status="missing",
            notes="Intersection Surface preview was not created because Applied Sections are required.",
            project=project or find_project(doc),
        )
        return None
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    prerequisite = corridor_intersection_patch_prerequisite_result(doc)
    if str(getattr(prerequisite, "status", "") or "") == "missing":
        _remove_preview_object(doc, "V1CorridorIntersectionSurfacePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionCurbReturnSlopePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionTieInEdgePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionBoundarySegmentPreview")
        _remove_preview_object(doc, "V1CorridorIntersectionExclusionZonePreview")
        _record_corridor_build_preview_diagnostic(
            doc,
            role="intersection",
            surface_kind="intersection_surface",
            status="missing",
            notes=_intersection_patch_diagnostic_notes(prerequisite),
            project=project or find_project(doc),
        )
        return None
    surface_id = _surface_id(surface_model, "intersection_surface") or f"{corridor_model.corridor_id}:intersection-surface"
    intersection_applied_section_set = _applied_section_set_with_intersection_tie_in_sections(
        applied_section_set,
        document=doc,
    )
    try:
        tin_surface = _build_intersection_surface_patch_tin(
            project_id=_project_id(project or find_project(doc)),
            corridor_model=corridor_model,
            applied_section_set=intersection_applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
            surface_id=surface_id,
        )
    except Exception as exc:
        _remove_preview_object(doc, "V1CorridorIntersectionSurfacePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionCurbReturnSlopePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionTieInEdgePreview")
        _remove_preview_object(doc, "V1CorridorIntersectionBoundarySegmentPreview")
        _remove_preview_object(doc, "V1CorridorIntersectionExclusionZonePreview")
        _record_corridor_build_preview_diagnostic(
            doc,
            role="intersection",
            surface_kind="intersection_surface",
            status="error",
            notes=f"Intersection Surface preview was not created: {exc}",
            project=project or find_project(doc),
        )
        return None
    _remove_preview_object(doc, "V1CorridorIntersectionCurbReturnSlopePreview")
    display_tin_surface = tin_surface
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        display_tin_surface,
        object_name="V1CorridorIntersectionSurfacePreview",
        label_prefix="Intersection Surface",
        surface_role="intersection",
        recompute=False,
    )
    if str(getattr(result, "status", "") or "") == "error":
        _record_corridor_build_preview_diagnostic(
            doc,
            role="intersection",
            surface_kind="intersection_surface",
            status="error",
            notes=str(getattr(result, "notes", "") or "Intersection Surface preview mapper failed."),
            project=project or find_project(doc),
        )
        return None
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _remove_corridor_build_preview_diagnostic(doc, "intersection")
        _attach_corridor_surface_preview_contract(
            preview_obj,
            role="intersection",
            surface_kind="intersection_surface",
            surface_id=surface_id,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=intersection_applied_section_set,
            preview_result=result,
        )
        _set_preview_property(preview_obj, "IntersectionId", str(getattr(prerequisite, "intersection_id", "") or ""))
        _set_preview_property(preview_obj, "IntersectionKind", str(getattr(prerequisite, "intersection_kind", "") or ""))
        grading_policy = _intersection_grading_policy_for(intersection_model, str(getattr(prerequisite, "intersection_id", "") or ""))
        _set_preview_property(preview_obj, "IntersectionGradingPolicyRef", str(getattr(grading_policy, "policy_id", "") or ""))
        _set_preview_property(preview_obj, "IntersectionGradingMode", str(getattr(grading_policy, "mode", "") or "use_normal_superelevation"))
        _set_preview_property(preview_obj, "IntersectionTargetCrossfallPercent", f"{float(getattr(grading_policy, 'target_crossfall_percent', 0.0) or 0.0):.3f}")
        _set_preview_float_property(preview_obj, "IntersectionGradingZDeltaMax", _tin_quality_float(tin_surface, "intersection_grading_z_delta_max"))
        _set_preview_integer_property(preview_obj, "IntersectionSuperelevationSourceCount", int(_tin_quality_float(tin_surface, "intersection_superelevation_source_count") or 0))
        _set_preview_integer_property(preview_obj, "IntersectionSuperelevationTransitionCount", int(_tin_quality_float(tin_surface, "intersection_superelevation_transition_count") or 0))
        _set_preview_float_property(preview_obj, "IntersectionSuperelevationLeftMin", _tin_quality_float(tin_surface, "intersection_superelevation_left_min"))
        _set_preview_float_property(preview_obj, "IntersectionSuperelevationLeftMax", _tin_quality_float(tin_surface, "intersection_superelevation_left_max"))
        _set_preview_float_property(preview_obj, "IntersectionSuperelevationRightMin", _tin_quality_float(tin_surface, "intersection_superelevation_right_min"))
        _set_preview_float_property(preview_obj, "IntersectionSuperelevationRightMax", _tin_quality_float(tin_surface, "intersection_superelevation_right_max"))
        _set_preview_property(preview_obj, "IntersectionSuperelevationContext", _tin_quality_text(tin_surface, "intersection_superelevation_context"))
        _set_preview_integer_property(preview_obj, "IntersectionTINLowPointCandidateCount", int(_tin_quality_float(tin_surface, "intersection_low_point_candidate_count") or 0))
        _set_preview_float_property(preview_obj, "IntersectionTINLowPointX", _tin_quality_float(tin_surface, "intersection_low_point_x"))
        _set_preview_float_property(preview_obj, "IntersectionTINLowPointY", _tin_quality_float(tin_surface, "intersection_low_point_y"))
        _set_preview_float_property(preview_obj, "IntersectionTINLowPointZ", _tin_quality_float(tin_surface, "intersection_low_point_z"))
        _set_preview_property(preview_obj, "IntersectionTINLowPointSourceRef", _tin_quality_text(tin_surface, "intersection_low_point_source_ref"))
        _set_preview_integer_property(preview_obj, "IntersectionBoundaryToLowFlowHintCount", int(_tin_quality_float(tin_surface, "intersection_boundary_to_low_flow_hint_count") or 0))
        _set_preview_property(preview_obj, "IntersectionBoundaryToLowFlowHintSummary", _tin_quality_text(tin_surface, "intersection_boundary_to_low_flow_hint_summary"))
        _set_preview_integer_property(preview_obj, "ParticipatingAlignmentCount", int(getattr(prerequisite, "participating_alignment_count", 0) or 0))
        _set_preview_integer_property(preview_obj, "ControlRegionCount", int(getattr(prerequisite, "control_region_count", 0) or 0))
        _set_preview_integer_property(preview_obj, "TieInEdgeCount", int(getattr(prerequisite, "tie_in_edge_count", 0) or 0))
        _set_preview_integer_property(preview_obj, "PatchBoundaryPointCount", int(_tin_quality_float(tin_surface, "patch_boundary_point_count") or 0))
        _set_preview_property(preview_obj, "PatchBoundarySource", _tin_quality_text(tin_surface, "patch_boundary_source"))
        _set_preview_integer_property(preview_obj, "PatchDegenerateTriangleCount", int(_tin_quality_float(tin_surface, "patch_degenerate_triangle_count") or 0))
        _set_preview_float_property(preview_obj, "PatchBoundaryEdgeMaxLength", _tin_quality_float(tin_surface, "patch_boundary_edge_max_length"))
        _set_preview_integer_property(preview_obj, "PatchBoundaryLongEdgeCount", int(_tin_quality_float(tin_surface, "patch_boundary_edge_long_count") or 0))
        _set_preview_float_property(preview_obj, "PatchBoundaryLongEdgeFactor", _tin_quality_float(tin_surface, "patch_boundary_edge_long_factor"))
        _set_preview_float_property(preview_obj, "PatchBoundaryLongEdgeLimit", _tin_quality_float(tin_surface, "patch_boundary_edge_long_limit"))
        _set_preview_float_property(preview_obj, "PatchBoundaryMaxEdgeLengthPolicy", _tin_quality_float(tin_surface, "patch_boundary_edge_max_length_policy"))
        _set_preview_property(preview_obj, "PatchTriangulationMode", _tin_quality_text(tin_surface, "patch_triangulation_mode"))
        _set_preview_property(preview_obj, "PatchSurfaceBoundaryStrategy", _tin_quality_text(tin_surface, "patch_surface_boundary_strategy"))
        _set_preview_integer_property(preview_obj, "PatchStructuredStripCount", int(_tin_quality_float(tin_surface, "patch_structured_strip_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchCurbReturnSurfaceEdgeCount", int(_tin_quality_float(tin_surface, "patch_curb_return_surface_edge_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchCurbReturnArcCount", int(_tin_quality_float(tin_surface, "patch_curb_return_arc_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchCurbReturnArcSampleCount", int(_tin_quality_float(tin_surface, "patch_curb_return_arc_sample_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchCurbReturnArcSegmentCount", int(_tin_quality_float(tin_surface, "patch_curb_return_arc_segment_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchEdgeBlendFaceCount", int(_tin_quality_float(tin_surface, "patch_edge_blend_face_count") or 0))
        _set_preview_property(preview_obj, "PatchBoundaryRoleSummary", _tin_quality_text(tin_surface, "patch_boundary_role_summary"))
        _set_preview_integer_property(preview_obj, "PatchPavementTieInEdgeCount", int(_tin_quality_float(tin_surface, "patch_boundary_pavement_tie_in_edge_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchStemTieInEdgeCount", int(_tin_quality_float(tin_surface, "patch_boundary_stem_tie_in_edge_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchOverlapCutEdgeCount", int(_tin_quality_float(tin_surface, "patch_boundary_overlap_cut_edge_count") or 0))
        _set_preview_integer_property(preview_obj, "PatchCurbReturnEdgeCount", int(_tin_quality_float(tin_surface, "patch_boundary_curb_return_edge_count") or 0))
        _set_preview_float_property(preview_obj, "PatchBoundaryBBoxX", _tin_quality_float(tin_surface, "patch_boundary_bbox_x"))
        _set_preview_float_property(preview_obj, "PatchBoundaryBBoxY", _tin_quality_float(tin_surface, "patch_boundary_bbox_y"))
        _set_preview_float_property(preview_obj, "PatchBoundaryBBoxAspectRatio", _tin_quality_float(tin_surface, "patch_boundary_bbox_aspect_ratio"))
        _set_preview_float_property(preview_obj, "PatchTriangleMinQuality", _tin_quality_float(tin_surface, "patch_triangle_min_quality"))
        _set_preview_integer_property(preview_obj, "PatchTriangleSkinnyCount", int(_tin_quality_float(tin_surface, "patch_triangle_skinny_count") or 0))
        _set_preview_float_property(preview_obj, "IntersectionPatchBoundaryPolygonArea", _tin_quality_float(tin_surface, "ordered_patch_boundary_polygon_area"))
        _set_preview_property(
            preview_obj,
            "IntersectionPatchBoundarySelfCrossing",
            "Yes" if int(_tin_quality_float(tin_surface, "ordered_patch_boundary_self_crossing") or 0) else "No",
        )
        _set_preview_integer_property(preview_obj, "IntersectionPatchBoundaryRingCount", int(_tin_quality_float(tin_surface, "ordered_patch_boundary_ring_count") or 0))
        _set_preview_integer_property(preview_obj, "IntersectionPatchBoundaryHoleRingCount", int(_tin_quality_float(tin_surface, "ordered_patch_boundary_hole_ring_count") or 0))
        _set_preview_integer_property(preview_obj, "IntersectionPatchBoundaryIslandRingCount", int(_tin_quality_float(tin_surface, "ordered_patch_boundary_island_ring_count") or 0))
        _set_preview_string_list_property(preview_obj, "ControlRegionRefs", list(getattr(prerequisite, "control_region_refs", ()) or ()))
        _set_preview_integer_property(preview_obj, "IntersectionDiagnosticCount", len(list(getattr(prerequisite, "diagnostic_rows", ()) or ())))
        _set_preview_string_list_property(preview_obj, "IntersectionDiagnostics", list(getattr(prerequisite, "diagnostic_rows", ()) or ()))
        tie_in_result = corridor_intersection_tie_in_edge_result(
            intersection_applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
        _set_preview_property(preview_obj, "TieInEdgePreviewStatus", str(getattr(tie_in_result, "status", "") or ""))
        _set_preview_integer_property(
            preview_obj,
            "TieInEdgeDiagnosticCount",
            len(list(getattr(tie_in_result, "diagnostic_rows", []) or [])),
        )
        tie_in_preview = _create_corridor_intersection_tie_in_edge_preview(
            doc,
            tie_in_result,
            project=project or find_project(doc),
        )
        if tie_in_preview is not None:
            _set_preview_property(preview_obj, "TieInEdgePreviewRef", str(getattr(tie_in_preview, "Name", "") or ""))
        boundary_result = corridor_intersection_boundary_segment_result(
            tie_in_result,
            intersection_model=intersection_model,
        )
        _set_preview_property(preview_obj, "IntersectionBoundaryMode", str(getattr(boundary_result, "boundary_mode", "") or ""))
        _set_preview_property(preview_obj, "IntersectionBoundaryStatus", str(getattr(boundary_result, "status", "") or ""))
        _set_preview_integer_property(preview_obj, "IntersectionBoundarySegmentCount", int(getattr(boundary_result, "segment_count", 0) or 0))
        _set_preview_integer_property(preview_obj, "IntersectionBoundaryTieInSegmentCount", int(getattr(boundary_result, "tie_in_segment_count", 0) or 0))
        _set_preview_integer_property(preview_obj, "IntersectionBoundaryArcSegmentCount", int(getattr(boundary_result, "arc_segment_count", 0) or 0))
        _set_preview_string_list_property(preview_obj, "IntersectionBoundaryDiagnostics", list(getattr(boundary_result, "diagnostic_rows", []) or []))
        _set_preview_integer_property(
            preview_obj,
            "IntersectionBoundaryDiagnosticCount",
            len(list(getattr(boundary_result, "diagnostic_rows", []) or [])),
        )
        boundary_preview = _create_corridor_intersection_boundary_segment_preview(
            doc,
            boundary_result,
            project=project or find_project(doc),
        )
        if boundary_preview is not None:
            _set_preview_property(preview_obj, "IntersectionBoundaryPreviewRef", str(getattr(boundary_preview, "Name", "") or ""))
        patch_boundary_result = corridor_intersection_patch_boundary_result(boundary_result)
        _set_preview_property(preview_obj, "IntersectionPatchBoundaryMode", str(getattr(patch_boundary_result, "boundary_mode", "") or ""))
        _set_preview_property(preview_obj, "IntersectionPatchBoundaryStatus", str(getattr(patch_boundary_result, "status", "") or ""))
        _set_preview_integer_property(preview_obj, "IntersectionPatchBoundaryOrderedPointCount", int(getattr(patch_boundary_result, "boundary_point_count", 0) or 0))
        _set_preview_integer_property(preview_obj, "IntersectionPatchBoundarySourceSegmentCount", int(getattr(patch_boundary_result, "source_segment_count", 0) or 0))
        _set_preview_property(preview_obj, "IntersectionPatchBoundaryClosed", "Yes" if bool(getattr(patch_boundary_result, "closed", False)) else "No")
        _set_preview_integer_property(preview_obj, "IntersectionPatchBoundaryDiagnosticCount", len(list(getattr(patch_boundary_result, "diagnostic_rows", []) or [])))
        _set_preview_string_list_property(preview_obj, "IntersectionPatchBoundaryDiagnostics", list(getattr(patch_boundary_result, "diagnostic_rows", []) or []))
        exclusion_preview = _create_corridor_intersection_exclusion_zone_preview(
            doc,
            patch_boundary_result,
            project=project or find_project(doc),
        )
        if exclusion_preview is not None:
            _set_preview_property(preview_obj, "IntersectionExclusionZoneRef", str(getattr(exclusion_preview, "Name", "") or ""))
            _set_preview_property(preview_obj, "IntersectionExclusionZoneStatus", str(getattr(exclusion_preview, "ExclusionStatus", "") or ""))
            _set_preview_integer_property(preview_obj, "IntersectionExclusionZonePointCount", int(getattr(exclusion_preview, "BoundaryPointCount", 0) or 0))
            for role in ("design", "daylight"):
                target = _corridor_build_preview_object(doc, role)
                if target is not None:
                    _attach_intersection_exclusion_zone_metadata(target, doc, exclusion_preview=exclusion_preview)
        drainage_rows = corridor_intersection_drainage_review_rows(doc)
        drainage_row = next(
            (
                row for row in drainage_rows
                if str(row.get("intersection_id", "") or "") == str(getattr(prerequisite, "intersection_id", "") or "")
            ),
            None,
        )
        if drainage_row is not None:
            _set_preview_property(preview_obj, "IntersectionDrainageCoverageStatus", str(drainage_row.get("status", "") or ""))
            _set_preview_property(preview_obj, "IntersectionLowPointStation", f"{float(drainage_row.get('station', 0.0) or 0.0):.3f}")
            _set_preview_float_property(preview_obj, "IntersectionLowPointZ", float(drainage_row.get("z", 0.0) or 0.0))
            _set_preview_integer_property(preview_obj, "IntersectionLowPointCandidateCount", int(drainage_row.get("low_point_count", 0) or 0))
            _set_preview_string_list_property(
                preview_obj,
                "IntersectionDrainageElementRefs",
                [ref for ref in str(drainage_row.get("drainage_element_refs", "") or "").split(",") if ref],
            )
            _set_preview_string_list_property(
                preview_obj,
                "IntersectionDrainageCandidateRefs",
                [ref for ref in str(drainage_row.get("drainage_candidate_refs", "") or "").split(",") if ref],
            )
            _set_preview_string_list_property(
                preview_obj,
                "IntersectionDrainageDiagnostics",
                [value.strip() for value in str(drainage_row.get("diagnostics", "") or "").split(";") if value.strip()],
            )
        _set_preview_property(preview_obj, "IntersectionImplementationMode", "legacy_patch_frozen")
        _set_preview_property(preview_obj, "IntersectionRedesignPath", "edge_network_first")
        _set_preview_property(
            preview_obj,
            "IntersectionImplementationStatus",
            "Frozen first-slice patch path; next redesign work must use Intersection Edge Network.",
        )
        _set_preview_property(preview_obj, "IntersectionReviewSummary", _intersection_surface_review_notes(preview_obj))
        _set_preview_property(
            preview_obj,
            "IntersectionPatchQualitySummary",
            (
                f"triangulation={str(getattr(preview_obj, 'PatchTriangulationMode', '') or '')}; "
                f"boundary={str(getattr(preview_obj, 'PatchSurfaceBoundaryStrategy', '') or '')}; "
                f"edge_blend_faces={int(getattr(preview_obj, 'PatchEdgeBlendFaceCount', 0) or 0)}; "
                f"roles={str(getattr(preview_obj, 'PatchBoundaryRoleSummary', '') or '')}; "
                f"min_quality={float(getattr(preview_obj, 'PatchTriangleMinQuality', 0.0) or 0.0):.3f}"
            ),
        )
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
    return preview_obj


def _tin_surface_without_quality_refs(surface, quality_refs: set[str]):
    if surface is None:
        return surface
    refs = set(str(value or "") for value in set(quality_refs or set()))
    triangles = [
        triangle for triangle in list(getattr(surface, "triangle_rows", []) or [])
        if str(getattr(triangle, "quality_ref", "") or "") not in refs
    ]
    return _tin_surface_with_triangles(surface, triangles)


def _tin_surface_with_triangles(surface, triangles: list[object]):
    used_vertex_ids: set[str] = set()
    for triangle in list(triangles or []):
        used_vertex_ids.update(str(ref or "") for ref in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", "")) if str(ref or ""))
    vertices = [
        vertex for vertex in list(getattr(surface, "vertex_rows", []) or [])
        if str(getattr(vertex, "vertex_id", "") or "") in used_vertex_ids
    ]
    return replace(surface, vertex_rows=vertices, triangle_rows=list(triangles or []))


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
    applied_section_set = _applied_section_set_with_intersection_tie_in_sections(
        applied_section_set,
        document=doc,
    )
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
    except Exception as exc:
        _record_corridor_build_preview_diagnostic(
            doc,
            role="subgrade",
            surface_kind="subgrade_surface",
            status="error",
            notes=f"Subgrade Surface preview was not created: {exc}",
            project=project or find_project(doc),
        )
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorSubgradeSurfacePreview",
        label_prefix="Corridor Subgrade Surface",
        surface_role="subgrade",
        recompute=False,
    )
    if str(getattr(result, "status", "") or "") == "error":
        _record_corridor_build_preview_diagnostic(
            doc,
            role="subgrade",
            surface_kind="subgrade_surface",
            status="error",
            notes=str(getattr(result, "notes", "") or "Subgrade Surface preview mapper failed."),
            project=project or find_project(doc),
        )
        return None
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _remove_corridor_build_preview_diagnostic(doc, "subgrade")
        _attach_corridor_surface_preview_contract(
            preview_obj,
            role="subgrade",
            surface_kind="subgrade_surface",
            surface_id=surface_id,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=applied_section_set,
            preview_result=result,
        )
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
    applied_section_set = _applied_section_set_with_intersection_tie_in_sections(
        applied_section_set,
        document=doc,
    )
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
        tin_surface = _clip_tin_surface_by_intersection_exclusion(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
            surface_role="daylight",
        )
        tin_surface = _augment_daylight_surface_with_intersection_curb_return_bands(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
        )
        intersection_tin_surface = _build_intersection_surface_tin_for_slope_face_height_clip(
            doc,
            project=project or find_project(doc),
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=applied_section_set,
        )
        tin_surface = _suppress_daylight_triangles_inside_intersection_surface_footprint(
            tin_surface,
            intersection_tin_surface,
        )
        tin_surface = _suppress_daylight_triangles_above_intersection_surface(
            tin_surface,
            intersection_tin_surface,
            tolerance=INTERSECTION_SLOPE_FACE_HEIGHT_CLIP_TOLERANCE,
        )
        intersection_slope_trim_display_segments, intersection_slope_trim_triangle_count = _intersection_slope_face_overlap_edge_segments(
            tin_surface,
            intersection_tin_surface,
            z_offset=0.08,
        )
        tin_surface = _trim_daylight_triangles_above_intersection_surface_by_intersection_lines(
            tin_surface,
            intersection_tin_surface,
            tolerance=INTERSECTION_SLOPE_FACE_HEIGHT_CLIP_TOLERANCE,
        )
        tin_surface = _augment_daylight_surface_with_intersection_slope_face_boundary_strips(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
        )
    except Exception as exc:
        _record_corridor_build_preview_diagnostic(
            doc,
            role="daylight",
            surface_kind="daylight_surface",
            status="error",
            notes=f"Slope Face Surface preview was not created: {exc}",
            project=project or find_project(doc),
        )
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDaylightSurfacePreview",
        label_prefix="Corridor Slope Face Surface",
        surface_role="daylight",
        recompute=False,
    )
    if str(getattr(result, "status", "") or "") == "error":
        _record_corridor_build_preview_diagnostic(
            doc,
            role="daylight",
            surface_kind="daylight_surface",
            status="error",
            notes=str(getattr(result, "notes", "") or "Slope Face Surface preview mapper failed."),
            project=project or find_project(doc),
        )
        return None
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _remove_corridor_build_preview_diagnostic(doc, "daylight")
        _attach_corridor_surface_preview_contract(
            preview_obj,
            role="daylight",
            surface_kind="daylight_surface",
            surface_id=surface_id,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=applied_section_set,
            preview_result=result,
        )
        _attach_surface_quality_properties(preview_obj, tin_surface, applied_section_set=applied_section_set)
        _attach_intersection_exclusion_zone_metadata(preview_obj, doc)
        _attach_intersection_exclusion_clip_quality(preview_obj, tin_surface)
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
        _create_intersection_slope_face_overlap_preview(
            document=doc,
            project=project or find_project(doc),
            daylight_surface=tin_surface,
            intersection_surface=intersection_tin_surface,
            overlap_segments=intersection_slope_trim_display_segments,
            overlap_triangle_count=intersection_slope_trim_triangle_count,
        )
        _create_slope_face_generation_boundary_preview(
            document=doc,
            project=project or find_project(doc),
            daylight_surface=tin_surface,
        )
        _create_intersection_slope_face_boundary_preview(
            document=doc,
            project=project or find_project(doc),
            applied_section_set=applied_section_set,
        )
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
        _record_corridor_build_preview_diagnostic(
            doc,
            role="drainage",
            surface_kind="drainage_surface",
            status="missing",
            notes="Drainage Surface preview was not created because no drainage_surface row exists. Add Drainage ditch_surface points through Applied Sections before Build Parametric.",
            project=project or find_project(doc),
        )
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
    except Exception as exc:
        _remove_preview_object(doc, "V1CorridorDrainageSurfacePreview")
        _record_corridor_build_preview_diagnostic(
            doc,
            role="drainage",
            surface_kind="drainage_surface",
            status="error",
            notes=f"Drainage Surface preview was not created: {exc}",
            project=project or find_project(doc),
        )
        return None
    result = TINMeshPreviewMapper().create_or_update_preview_object(
        doc,
        tin_surface,
        object_name="V1CorridorDrainageSurfacePreview",
        label_prefix="Corridor Drainage Surface",
        surface_role="drainage",
        recompute=False,
    )
    if str(getattr(result, "status", "") or "") == "error":
        _remove_preview_object(doc, "V1CorridorDrainageSurfacePreview")
        _record_corridor_build_preview_diagnostic(
            doc,
            role="drainage",
            surface_kind="drainage_surface",
            status="error",
            notes=str(getattr(result, "notes", "") or "Drainage Surface preview mapper failed."),
            project=project or find_project(doc),
        )
        return None
    preview_obj = doc.getObject(result.object_name) if str(getattr(result, "object_name", "") or "") else None
    if preview_obj is not None:
        _remove_corridor_build_preview_diagnostic(doc, "drainage")
        _attach_corridor_surface_preview_contract(
            preview_obj,
            role="drainage",
            surface_kind="drainage_surface",
            surface_id=surface_id,
            corridor_model=corridor_model,
            surface_model=surface_model,
            applied_section_set=applied_section_set,
            preview_result=result,
        )
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
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    metadata = _surface_transition_span_marker_metadata(surface_model, transition_model)
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
    _set_preview_string_list_property(obj, "TransitionStations", metadata["stations"])
    _set_preview_string_list_property(obj, "TransitionSampleIntervals", metadata["sample_intervals"])
    _set_preview_string_list_property(obj, "TransitionSampleCounts", metadata["sample_counts"])
    _set_preview_integer_property(obj, "TransitionSpanCount", len(refs))
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(doc), obj)
    except Exception:
        pass
    return obj


def _attach_corridor_surface_preview_contract(
    obj,
    *,
    role: str,
    surface_kind: str,
    surface_id: str,
    corridor_model,
    surface_model,
    applied_section_set=None,
    preview_result=None,
) -> None:
    """Attach common Build Parametric surface-preview provenance properties."""

    if obj is None:
        return
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_surface_preview")
    _set_preview_property(obj, "SurfaceRole", str(role or ""))
    _set_preview_property(obj, "SurfaceKind", str(surface_kind or ""))
    _set_preview_property(obj, "CorridorId", str(getattr(corridor_model, "corridor_id", "") or ""))
    _set_preview_property(obj, "SurfaceModelId", str(getattr(surface_model, "surface_model_id", "") or ""))
    _set_preview_property(obj, "SurfaceId", str(surface_id or ""))
    _set_preview_property(obj, "AppliedSectionSetRef", str(getattr(applied_section_set, "applied_section_set_id", "") or ""))
    _set_preview_property(obj, "PreviewStatus", "ready")
    _set_preview_property(obj, "PreviewDiagnostic", str(getattr(preview_result, "notes", "") or "Preview object created from Build Parametric surface output."))
    _set_preview_integer_property(obj, "PreviewFacetCount", int(getattr(preview_result, "facet_count", 0) or 0))
    _set_preview_string_list_property(
        obj,
        "SourceRefs",
        _corridor_surface_preview_source_refs(corridor_model, surface_model, applied_section_set),
    )


def _corridor_surface_preview_source_refs(corridor_model, surface_model, applied_section_set=None) -> list[str]:
    refs = [
        str(getattr(corridor_model, "corridor_id", "") or ""),
        str(getattr(surface_model, "surface_model_id", "") or ""),
        str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
    ]
    refs.extend(str(ref) for ref in list(getattr(surface_model, "source_refs", []) or []) if str(ref))
    refs.extend(str(ref) for ref in list(getattr(corridor_model, "source_refs", []) or []) if str(ref))
    output: list[str] = []
    for ref in refs:
        text = str(ref or "").strip()
        if text and text not in output:
            output.append(text)
    return output


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
        widget.setWindowTitle("CorridorRoad v1 - Build Parametric")
        try:
            widget.setMinimumWidth(BUILD_CORRIDOR_PANEL_MIN_WIDTH)
            widget.setMaximumWidth(BUILD_CORRIDOR_PANEL_MAX_WIDTH)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        except Exception:
            pass
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QtWidgets.QLabel("Build Parametric")
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
        try:
            self._summary.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
        layout.addWidget(self._summary)
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Ready")
        layout.addWidget(self._progress)
        tabs = QtWidgets.QTabWidget()
        try:
            tabs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        except Exception:
            pass
        guided_tab = QtWidgets.QWidget()
        guided_layout = QtWidgets.QVBoxLayout(guided_tab)
        guided_layout.setContentsMargins(8, 8, 8, 8)
        results_tab = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(results_tab)
        results_layout.setContentsMargins(8, 8, 8, 8)
        issues_tab = QtWidgets.QWidget()
        issues_layout = QtWidgets.QVBoxLayout(issues_tab)
        issues_layout.setContentsMargins(8, 8, 8, 8)
        intersections_tab = QtWidgets.QWidget()
        intersections_layout = QtWidgets.QVBoxLayout(intersections_tab)
        intersections_layout.setContentsMargins(8, 8, 8, 8)
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
        tabs.addTab(intersections_tab, "Intersections")
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
        intersections_label = QtWidgets.QLabel("Intersection Contracts")
        intersections_label.setToolTip("Edge-network-first contracts for topology, edges, surface zones, and ordinary corridor clipping.")
        intersections_layout.addWidget(intersections_label)
        self._intersection_contract_table = QtWidgets.QTableWidget(0, 7)
        self._intersection_contract_table.setHorizontalHeaderLabels(["Contract", "Status", "ID", "Role", "Source", "Boundary", "Notes"])
        _compact_build_corridor_table(self._intersection_contract_table, [105, 72, 180, 120, 180, 220, 260])
        self._intersection_contract_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._intersection_contract_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._intersection_contract_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._intersection_contract_table.setStyleSheet(
            "QTableWidget::item { color: #141414; } "
            "QTableWidget::item:selected { color: #ffffff; background: #2f6fab; }"
        )
        try:
            self._intersection_contract_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass
        self._intersection_contract_table.cellDoubleClicked.connect(lambda row_index, _col: self._show_intersection_contract_review_row(row_index))
        intersections_layout.addWidget(self._intersection_contract_table, 1)
        regions_label = QtWidgets.QLabel("Region Boundaries")
        regions_label.setToolTip("Double-click a Region row to select its built 3D Region surface object.")
        regions_layout.addWidget(regions_label)
        self._region_table = QtWidgets.QTableWidget(0, 11)
        self._region_table.setHorizontalHeaderLabels(
            ["Alignment", "Region", "Start STA", "End STA", "Assembly", "Structure", "Drainage", "Intersection", "Surface", "Boundary", "Diagnostics"]
        )
        _compact_build_corridor_table(self._region_table, [125, 140, 80, 80, 105, 105, 90, 120, 80, 90, 240])
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
        drainage_label.setToolTip("Roadside Drainage reviews station-range ditch surfaces; Intersection Drainage reviews low-point coverage inside intersection control Regions.")
        drainage_layout.addWidget(drainage_label)
        self._drainage_table = QtWidgets.QTableWidget(0, 7)
        self._drainage_table.setHorizontalHeaderLabels(["Context", "Station", "Status", "Points", "Left", "Right", "Notes"])
        _compact_build_corridor_table(self._drainage_table, [150, 90, 80, 65, 55, 55, 220])
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
        focus_button = QtWidgets.QPushButton("Focus")
        focus_button.clicked.connect(self._show_selected_row)
        row.addWidget(focus_button)
        structure_output_button = QtWidgets.QPushButton("Structure Output")
        structure_output_button.clicked.connect(self._open_structure_output_panel)
        row.addWidget(structure_output_button)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        row.addWidget(apply_button)
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
            self._summary.setPlainText("Applied Sections: missing\nRun Applied Sections before Build Parametric.")
            self._set_guided_review_rows(corridor_build_guided_review_steps(self.document))
            self._set_review_rows(corridor_build_review_rows(self.document))
            self._set_slope_face_issue_rows(corridor_slope_face_issue_rows(self.document))
            self._set_intersection_contract_review_rows(corridor_intersection_contract_review_rows(self.document))
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
        self._set_intersection_contract_review_rows(corridor_intersection_contract_review_rows(self.document))
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
            self._set_intersection_contract_review_rows(corridor_intersection_contract_review_rows(self.document))
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
            _show_message(self.form, "Build Parametric", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_progress(0, "Corridor Build failed")
            self._summary.setPlainText(f"CorridorModel was not built:\n{exc}")
            _show_message(self.form, "Build Parametric", f"CorridorModel was not built.\n{exc}")
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
            _show_message(self.form, "Build Parametric", f"Structure Output panel was not opened.\n{exc}")
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

    def _set_intersection_contract_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_intersection_contract_table"):
            return
        self._intersection_contract_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._intersection_contract_table.rowCount()
            self._intersection_contract_table.insertRow(row_index)
            values = [
                str(row.get("contract_family", "") or ""),
                str(row.get("status", "") or ""),
                str(row.get("row_id", "") or ""),
                str(row.get("role", "") or ""),
                str(row.get("source_refs", "") or ""),
                str(row.get("boundary_refs", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._intersection_contract_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
            self._apply_intersection_contract_row_style(row_index, str(row.get("status", "") or ""))
        if self._intersection_contract_table.rowCount() > 0:
            try:
                self._intersection_contract_table.selectRow(0)
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
                str(row.get("context_label", "") or _drainage_review_context_label(row)),
                station_text,
                str(row.get("status", "") or ""),
                str(row.get("ditch_point_count", "") or "0"),
                str(row.get("left_count", "") or "0"),
                str(row.get("right_count", "") or "0"),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 1:
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
                _display_source_id(str(row.get("alignment_id", "") or ""), "alignment:"),
                str(row.get("region_id", "") or ""),
                "" if start == "" else f"{float(start):.3f}",
                "" if end == "" else f"{float(end):.3f}",
                str(row.get("assembly", "") or ""),
                str(row.get("structure", "") or ""),
                str(row.get("drainage", "") or ""),
                str(row.get("intersection", "") or ""),
                str(row.get("surface_status", "") or ""),
                str(row.get("boundary_status", "") or ""),
                _region_boundary_display_diagnostics(row),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 1:
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
            _show_message(self.form, "Build Parametric", "Select one Region row first.")
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
            _show_message(self.form, "Build Parametric", f"Region surface object was not selected.\n{exc}")

    def _create_transition_from_selected_region_boundary(self) -> None:
        rows = self._region_table.selectionModel().selectedRows() if hasattr(self, "_region_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one Region row first.")
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
            _show_message(self.form, "Build Parametric", f"Surface Transition range was not created.\n{exc}")

    def _create_transition_from_selected_boundary_option(self) -> None:
        combo = getattr(self, "_surface_transition_boundary_combo", None)
        if combo is None or combo.count() <= 0:
            _show_message(self.form, "Build Parametric", "No Region boundary station is available.")
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
            _show_message(self.form, "Build Parametric", f"Surface Transition spacing was not stored.\n{exc}")

    def _toggle_selected_surface_transition(self) -> None:
        rows = self._surface_transition_table.selectionModel().selectedRows() if hasattr(self, "_surface_transition_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one Surface Transition row first.")
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
            _show_message(self.form, "Build Parametric", f"Surface Transition range was not updated.\n{exc}")

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
                        "Drainage station highlight shown.",
                        f"Station: {float(row.get('station', 0.0) or 0.0):.3f}" if row.get("station", "") != "" else "Station: n/a",
                        f"Status: {row.get('status', '')}",
                        f"Points: {row.get('ditch_point_count', 0)}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Drainage station highlight was not shown.\n{exc}")

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
            _show_message(self.form, "Build Parametric", f"Slope Face issue was not shown.\n{exc}")

    def _show_intersection_contract_review_row(self, row_index: int) -> None:
        try:
            rows = corridor_intersection_contract_review_rows(self.document)
            row = rows[int(row_index)]
            obj = focus_corridor_intersection_contract_review_row(self.document, int(row_index))
            try:
                self._intersection_contract_table.selectRow(int(row_index))
            except Exception:
                pass
            self._summary.setPlainText(
                "\n".join(
                    [
                        "Intersection contract review object focused.",
                        f"Contract: {row.get('contract_family', '')}",
                        f"ID: {row.get('row_id', '')}",
                        f"Status: {row.get('status', '')}",
                        f"Role: {row.get('role', '')}",
                        f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                    ]
                )
            )
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Intersection contract row was not focused.\n{exc}")

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
            _show_message(self.form, "Build Parametric", f"Slope Face issue was not shown.\n{exc}")

    def _selected_slope_face_issue_row_index(self) -> int:
        rows = self._slope_issue_table.selectionModel().selectedRows() if hasattr(self, "_slope_issue_table") else []
        if not rows:
            return -1
        return int(rows[0].row())

    def _show_selected_row(self) -> None:
        rows = self._review_table.selectionModel().selectedRows() if hasattr(self, "_review_table") else []
        if not rows:
            _show_message(self.form, "Build Parametric", "Select one review row first.")
            return
        self._show_review_row(int(rows[0].row()))

    def _show_review_row(self, row_index: int) -> None:
        try:
            obj = show_corridor_build_review_object(self.document, int(row_index))
            self._summary.setPlainText(f"Review object shown.\nObject: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}")
        except Exception as exc:
            _show_message(self.form, "Build Parametric", f"Review object was not shown.\n{exc}")

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
            _show_message(self.form, "Build Parametric", f"Guided review step was not focused.\n{exc}")

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

    def _apply_intersection_contract_row_style(self, row_index: int, status: str) -> None:
        color = corridor_build_review_row_color("empty" if str(status or "") in {"warn", "warning"} else status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*CORRIDOR_BUILD_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._intersection_contract_table.columnCount())):
                item = self._intersection_contract_table.item(int(row_index), column_index)
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
    """Keep Build Parametric tables compact by default while allowing panel resize."""

    if table is None:
        return
    try:
        table.setMinimumWidth(0)
        table.setMaximumWidth(BUILD_CORRIDOR_PANEL_MAX_WIDTH)
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
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


def _display_source_id(value: object, prefix: str) -> str:
    text = str(value or "")
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text


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
            "diagnostics": "Run Applied Sections before Build Parametric.",
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


def _document_region_models(document) -> list[object]:
    models: list[object] = []
    seen_ids: set[str] = set()
    for obj in list(getattr(document, "Objects", []) or []):
        model = to_region_model(obj)
        if model is None:
            continue
        model_id = str(getattr(model, "region_model_id", "") or getattr(obj, "Name", "") or id(obj))
        if model_id in seen_ids:
            continue
        seen_ids.add(model_id)
        models.append(model)
    preferred = to_region_model(find_v1_region_model(document))
    if preferred is not None:
        preferred_id = str(getattr(preferred, "region_model_id", "") or "")
        models = [model for model in models if str(getattr(model, "region_model_id", "") or "") != preferred_id]
        models.insert(0, preferred)
    return models


def _sections_for_region_model(sections: list[object], region_model) -> list[object]:
    alignment_id = str(getattr(region_model, "alignment_id", "") or "").strip()
    if not alignment_id:
        return list(sections or [])
    return [
        section
        for section in list(sections or [])
        if str(getattr(section, "alignment_id", "") or "").strip() == alignment_id
    ]


def _region_boundary_rows_from_source_regions(
    source_rows: list[object],
    sections: list[object],
    *,
    document=None,
    region_model=None,
    structure_model=None,
    drainage_model=None,
    intersection_model=None,
) -> list[dict[str, object]]:
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
        intersection_diagnostics = _region_intersection_context_diagnostics(
            source_row,
            group_sections,
            intersection_model=intersection_model,
        )
        diagnostics.extend(intersection_diagnostics)
        if index > 0:
            previous_last = section_groups[index - 1][-1] if section_groups[index - 1] else None
            diagnostics.extend(_region_boundary_diagnostics(previous_last, first, boundary_side="start"))
        if index < len(source_rows) - 1:
            next_first = section_groups[index + 1][0] if section_groups[index + 1] else None
            diagnostics.extend(_region_boundary_diagnostics(last, next_first, boundary_side="end"))
        boundary_status = _region_boundary_status(diagnostics)
        row = {
            "alignment_id": str(getattr(region_model, "alignment_id", "") or ""),
            "region_id": str(getattr(source_row, "region_id", "") or ""),
            "station_start": float(getattr(source_row, "station_start", 0.0) or 0.0),
            "station_end": float(getattr(source_row, "station_end", 0.0) or 0.0),
            "assembly": str(getattr(source_row, "assembly_ref", "") or "") or _unique_join(_section_text_values(group_sections, "assembly_id")),
            "structure": _region_group_structure_summary(
                group_sections,
                region_model=region_model,
                structure_model=structure_model,
            ),
            "drainage": _region_group_drainage_summary(
                group_sections,
                region_model=region_model,
                drainage_model=drainage_model,
            ),
            "intersection": _region_group_intersection_summary(
                source_row,
                group_sections,
                intersection_model=intersection_model,
            ),
            "surface_status": _region_group_surface_status(group_sections),
            "boundary_status": boundary_status,
            "diagnostics": _region_boundary_diagnostic_summary(diagnostics),
            "diagnostic_count": len(diagnostics),
            "intersection_diagnostic_count": len(intersection_diagnostics),
        }
        row.update(_region_generated_object_summary(document, row))
        rows.append(row)
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


def _region_group_structure_summary(sections: list[object], *, region_model=None, structure_model=None) -> str:
    values = list(_section_structure_values(sections))
    if region_model is not None and structure_model is not None:
        for context in _region_group_station_contexts(
            sections,
            region_model=region_model,
            structure_model=structure_model,
        ):
            result = getattr(context, "structure_result", None)
            values.extend(
                str(value or "").strip()
                for value in list(getattr(result, "active_structure_ids", []) or [])
                if str(value or "").strip()
            )
    return _unique_join(values) or "-"


def _region_group_station_contexts(
    sections: list[object],
    *,
    region_model=None,
    structure_model=None,
    drainage_model=None,
) -> list[object]:
    if region_model is None or not sections:
        return []
    resolver = StationContextResolver()
    contexts: list[object] = []
    for section in list(sections or []):
        try:
            context = resolver.resolve(
                region_model=region_model,
                structure_model=structure_model,
                drainage_model=drainage_model,
                station=_section_station(section),
            )
        except Exception:
            continue
        section_region = _section_region_id(section)
        context_region = str(getattr(getattr(context, "region_context", None), "region_id", "") or "")
        if section_region and context_region and section_region != context_region:
            continue
        contexts.append(context)
    return contexts


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
    import math

    length = abs(float(station_end) - float(station_start))
    interval = max(0.1, float(sample_interval or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL))
    return int(math.ceil(length / interval)) + 1


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


def _surface_transition_span_marker_metadata(surface_model, transition_model) -> dict[str, list[str]]:
    transitions = {
        str(getattr(row, "transition_id", "") or ""): row
        for row in list(getattr(transition_model, "transition_ranges", []) or []) if transition_model is not None
    }
    stations: list[str] = []
    sample_intervals: list[str] = []
    sample_counts: list[str] = []
    seen_refs: set[str] = set()
    for span in list(getattr(surface_model, "span_rows", []) or []) if surface_model is not None else []:
        transition_ref = str(getattr(span, "transition_ref", "") or "")
        if not transition_ref:
            continue
        try:
            station_start = float(getattr(span, "station_start", 0.0) or 0.0)
            station_end = float(getattr(span, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        if transition_ref in seen_refs:
            continue
        seen_refs.add(transition_ref)
        transition = transitions.get(transition_ref)
        if transition is not None:
            station_start = float(getattr(transition, "station_start", station_start) or station_start)
            station_end = float(getattr(transition, "station_end", station_end) or station_end)
        interval = float(getattr(transition, "sample_interval", SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL) or SURFACE_TRANSITION_DEFAULT_SAMPLE_INTERVAL)
        stations.append(f"{transition_ref}|{station_start:.3f}-{station_end:.3f}")
        sample_intervals.append(f"{transition_ref}|{interval:.3f}")
        sample_counts.append(f"{transition_ref}|{_surface_transition_sample_count(station_start, station_end, interval)}")
    return {
        "stations": stations,
        "sample_intervals": sample_intervals,
        "sample_counts": sample_counts,
    }


def _surface_transition_span_marker_point(sections: list[object], station: float, *, z_offset: float = 0.75) -> tuple[float, float, float] | None:
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
            return _interpolate_section_frame_point(getattr(first, "frame", None), getattr(second, "frame", None), ratio, z_offset=z_offset)
    nearest = min(ordered, key=lambda section: abs(_section_station(section) - float(station)))
    frame = getattr(nearest, "frame", None)
    if frame is None:
        return None
    return (
        float(getattr(frame, "x", 0.0) or 0.0),
        float(getattr(frame, "y", 0.0) or 0.0),
        float(getattr(frame, "z", 0.0) or 0.0) + float(z_offset or 0.0),
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


def _region_group_drainage_summary(sections: list[object], *, region_model=None, drainage_model=None) -> str:
    drainage_refs: list[str] = []
    flow_route_refs: list[str] = []
    if region_model is not None and drainage_model is not None:
        for context in _region_group_station_contexts(
            sections,
            region_model=region_model,
            drainage_model=drainage_model,
        ):
            drainage_refs.extend(
                str(value or "").strip()
                for value in list(getattr(context, "active_drainage_refs", []) or [])
                if str(value or "").strip()
            )
            flow_route_refs.extend(
                str(value or "").strip()
                for value in list(getattr(context, "active_flow_route_refs", []) or [])
                if str(value or "").strip()
            )
    ditch_count = sum(
        1
        for section in list(sections or [])
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    )
    summary_parts: list[str] = []
    drainage_summary = _unique_join(drainage_refs)
    route_summary = _unique_join(flow_route_refs)
    if drainage_summary:
        summary_parts.append(drainage_summary)
    if route_summary:
        summary_parts.append(f"routes: {route_summary}")
    if ditch_count:
        summary_parts.append(f"ditch points: {ditch_count}")
    return "; ".join(summary_parts) if summary_parts else "-"


def _region_group_intersection_summary(source_row, sections: list[object], *, intersection_model=None) -> str:
    source_ref = str(getattr(source_row, "intersection_ref", "") or "").strip() if source_row is not None else ""
    active_refs = _unique_refs(
        [
            str(getattr(section, "active_intersection_id", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_id", "") or "").strip()
        ]
    )
    leg_roles = _unique_refs(
        [
            str(getattr(section, "active_intersection_leg_role", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_leg_role", "") or "").strip()
        ]
    )
    parts: list[str] = []
    if source_ref:
        parts.append(_display_source_id(source_ref, "intersection:"))
    elif active_refs:
        parts.extend(_display_source_id(ref, "intersection:") for ref in active_refs)
    if leg_roles:
        parts.append("/".join(leg_roles))
    if source_ref and intersection_model is not None and _intersection_row_by_id(intersection_model, source_ref) is None:
        parts.append("unlinked")
    return " | ".join(part for part in parts if part) or "-"


def _region_intersection_context_diagnostics(source_row, sections: list[object], *, intersection_model=None) -> list[dict[str, str]]:
    source_ref = str(getattr(source_row, "intersection_ref", "") or "").strip()
    region_id = str(getattr(source_row, "region_id", "") or "").strip()
    active_refs = _unique_refs(
        [
            str(getattr(section, "active_intersection_id", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_id", "") or "").strip()
        ]
    )
    diagnostics: list[dict[str, str]] = []
    if source_ref:
        if intersection_model is None:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "intersection_model_missing",
                    f"{source_ref}: Region is tagged as intersection-controlled but no IntersectionModel is available.",
                    "range",
                )
            )
        elif _intersection_row_by_id(intersection_model, source_ref) is None:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "intersection_ref_missing_in_model",
                    f"{source_ref}: Region intersection_ref is not present in IntersectionModel.",
                    "range",
                )
            )
        if sections and source_ref not in active_refs:
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "intersection_context_not_reflected_in_applied_sections",
                    f"{source_ref}: Applied Sections inside this Region do not carry the expected active intersection.",
                    "range",
                )
            )
        if intersection_model is not None and not _intersection_model_mentions_region(intersection_model, source_ref, region_id):
            diagnostics.append(
                _region_boundary_diagnostic(
                    "warning",
                    "intersection_control_region_missing",
                    f"{source_ref}: IntersectionModel does not list this Region as a control Region.",
                    "range",
                )
            )
    elif active_refs:
        diagnostics.append(
            _region_boundary_diagnostic(
                "warning",
                "intersection_context_without_region_source_ref",
                f"{', '.join(active_refs)}: Applied Sections carry intersection context, but Region source has no intersection_ref.",
                "range",
            )
        )
    if len(active_refs) > 1:
        diagnostics.append(
            _region_boundary_diagnostic(
                "warning",
                "intersection_context_overlap",
                f"Multiple active intersections are present in this Region: {', '.join(active_refs)}.",
                "range",
            )
        )
    return diagnostics


def _intersection_row_by_id(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "").strip() == target:
            return row
    return None


def _intersection_model_mentions_region(intersection_model, intersection_id: str, region_id: str) -> bool:
    target_region = str(region_id or "").strip()
    if not target_region:
        return True
    refs: list[str] = []
    row = _intersection_row_by_id(intersection_model, intersection_id)
    if row is not None:
        refs.extend(str(value or "") for value in list(getattr(row, "control_region_refs", []) or []))
        refs.extend(str(getattr(leg, "region_ref", "") or "") for leg in list(getattr(row, "leg_rows", []) or []))
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "").strip() == str(intersection_id or "").strip():
            refs.extend(str(value or "") for value in list(getattr(area, "control_region_refs", []) or []))
    return any(ref == target_region or ref.endswith(f"/{target_region}") for ref in refs if ref)


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


def _region_boundary_display_diagnostics(row: dict[str, object]) -> str:
    base = str(row.get("diagnostics", "") or "").strip()
    object_diagnostics = str(row.get("region_object_diagnostics", "") or "").strip()
    if not object_diagnostics or object_diagnostics == "Region object families are available.":
        return base
    if not base or base == "ok":
        return object_diagnostics
    return f"{base}; {object_diagnostics}"


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
    alignment_id = str(row.get("alignment_id", "") or "").strip()
    start = float(row.get("station_start", 0.0) or 0.0)
    end = float(row.get("station_end", start) or start)
    all_sections = [
        section
        for section in _station_ordered_applied_sections(applied_section_set)
        if getattr(section, "frame", None) is not None
        and (not alignment_id or str(getattr(section, "alignment_id", "") or "").strip() == alignment_id)
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
            full_applied_section_set=applied_section_set,
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
    structure_name = _region_structure_preview_object_name(region_id)
    if document.getObject(structure_name) is not None:
        _remove_preview_object(document, structure_name)
    return objects


def _create_or_update_region_surface_preview_object(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    full_applied_section_set=None,
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
    if _region_surface_role_uses_intersection_exclusion(role):
        tin_surface = _clip_tin_surface_by_intersection_exclusion(
            tin_surface,
            document,
            applied_section_set=full_applied_section_set or applied_section_set,
            source_applied_section_set=applied_section_set,
            surface_role=role,
        )
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
    if _region_surface_role_uses_intersection_exclusion(role):
        _attach_intersection_exclusion_clip_quality(obj, tin_surface)
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


def _region_surface_role_uses_intersection_exclusion(role: str) -> bool:
    return str(role or "").strip().lower() in {"design", "subgrade", "daylight"}


def _applied_section_set_with_intersection_tie_in_sections(applied_section_set, *, document=None):
    """Return a build-time section set with generated intersection tie-in stations."""

    if applied_section_set is None:
        return applied_section_set
    sections = list(getattr(applied_section_set, "sections", []) or [])
    if len(sections) < 2:
        return applied_section_set
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    prerequisite = corridor_intersection_patch_prerequisite_result(doc)
    if str(getattr(prerequisite, "status", "") or "") == "missing":
        return applied_section_set
    try:
        boundary_result = corridor_intersection_boundary_segment_result(
            corridor_intersection_tie_in_edge_result(
                applied_section_set,
                prerequisite=prerequisite,
                intersection_model=intersection_model,
            ),
            intersection_model=intersection_model,
        )
    except Exception:
        return applied_section_set
    generated: list[object] = []
    seen = {
        (str(getattr(section, "alignment_id", "") or ""), round(_section_station(section), 6))
        for section in sections
    }
    arc_points: list[tuple[float, float, float]] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        chord_points = [_xyz_tuple(point) for point in list(getattr(row, "chord_points_xyz", []) or [])]
        if len(chord_points) >= 2:
            arc_points.extend([chord_points[0], chord_points[-1]])
    if not arc_points:
        return applied_section_set
    grouped: dict[str, list[object]] = {}
    for section in sections:
        alignment_id = str(getattr(section, "alignment_id", "") or "")
        if alignment_id:
            grouped.setdefault(alignment_id, []).append(section)
    for point_index, point in enumerate(arc_points, start=1):
        candidate = _intersection_tie_in_generated_section_for_point(
            point,
            grouped,
            intersection_id=str(getattr(boundary_result, "intersection_id", "") or ""),
            source_index=point_index,
        )
        if candidate is None:
            continue
        key = (str(getattr(candidate, "alignment_id", "") or ""), round(_section_station(candidate), 6))
        if key in seen:
            continue
        seen.add(key)
        generated.append(candidate)
    if not generated:
        return applied_section_set
    combined = _unique_sections_by_alignment_station([*sections, *generated])
    station_rows = [
        AppliedSectionStationRow(
            f"{str(getattr(section, 'applied_section_id', '') or 'section')}:{index}:station-row",
            _section_station(section),
            str(getattr(section, "applied_section_id", "") or ""),
            "intersection_tie_in_generated" if str(getattr(section, "applied_section_id", "") or "").startswith("section:intersection-tie-in:") else "regular_sample",
        )
        for index, section in enumerate(combined, start=1)
    ]
    return replace(
        applied_section_set,
        applied_section_set_id=f"{str(getattr(applied_section_set, 'applied_section_set_id', '') or 'sections')}:intersection-tie-in",
        sections=combined,
        station_rows=station_rows,
    )


def _intersection_tie_in_generated_section_for_point(
    point: tuple[float, float, float],
    grouped_sections: dict[str, list[object]],
    *,
    intersection_id: str,
    source_index: int,
):
    best: tuple[float, object, object, float, str] | None = None
    for alignment_id, rows in grouped_sections.items():
        ordered = sorted([section for section in list(rows or []) if getattr(section, "frame", None) is not None], key=_section_station)
        for index in range(len(ordered) - 1):
            first = ordered[index]
            second = ordered[index + 1]
            first_frame = getattr(first, "frame", None)
            second_frame = getattr(second, "frame", None)
            if first_frame is None or second_frame is None:
                continue
            distance, ratio = _point_segment_distance_with_ratio(
                float(point[0]),
                float(point[1]),
                float(getattr(first_frame, "x", 0.0) or 0.0),
                float(getattr(first_frame, "y", 0.0) or 0.0),
                float(getattr(second_frame, "x", 0.0) or 0.0),
                float(getattr(second_frame, "y", 0.0) or 0.0),
            )
            ratio = min(max(float(ratio), 0.0), 1.0)
            if best is None or distance < best[0]:
                best = (distance, first, second, ratio, alignment_id)
    if best is None:
        return None
    _distance, first, second, ratio, alignment_id = best
    station = _section_station(first) + (_section_station(second) - _section_station(first)) * ratio
    section = _interpolate_region_boundary_section(
        first,
        second,
        ratio,
        station=station,
        region_id=str(getattr(first, "region_id", "") or getattr(second, "region_id", "") or ""),
        boundary_role="intersection_tie_in",
    )
    frame = getattr(section, "frame", None)
    if frame is not None:
        section = replace(
            section,
            frame=replace(
                frame,
                station=station,
                notes=_join_review_notes(str(getattr(frame, "notes", "") or ""), f"generated_reason=intersection_tie_in; source_point={source_index}"),
            ),
        )
    diagnostics = list(getattr(section, "intersection_diagnostic_rows", []) or [])
    diagnostics.append(f"generated_intersection_tie_in_section: source_point={source_index}; station={station:.3f}")
    return replace(
        section,
        applied_section_id=f"section:intersection-tie-in:{_safe_region_token(intersection_id) or 'intersection'}:{_safe_region_token(alignment_id)}:{source_index}",
        alignment_id=alignment_id,
        station=station,
        active_intersection_id=str(intersection_id or getattr(section, "active_intersection_id", "") or ""),
        active_intersection_control_area_id=str(getattr(section, "active_intersection_control_area_id", "") or intersection_id or ""),
        active_intersection_leg_role=str(getattr(section, "active_intersection_leg_role", "") or "tie_in_generated"),
        intersection_diagnostic_rows=diagnostics,
    )


def _unique_sections_by_alignment_station(sections: list[object]) -> list[object]:
    rows: dict[tuple[str, float], object] = {}
    for section in sorted(list(sections or []), key=lambda item: (str(getattr(item, "alignment_id", "") or ""), _section_station(item), str(getattr(item, "applied_section_id", "") or ""))):
        key = (str(getattr(section, "alignment_id", "") or ""), round(_section_station(section), 6))
        existing = rows.get(key)
        if existing is None or str(getattr(section, "applied_section_id", "") or "").startswith("section:intersection-tie-in:"):
            rows[key] = section
    return [rows[key] for key in sorted(rows, key=lambda item: (item[0], item[1]))]


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
        vobj.Visibility = bool(selected)
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


def _corridor_region_preview_objects(document, region_id: str, *, row: dict[str, object] | None = None) -> list[object]:
    if document is None:
        return []
    objects: list[object] = []
    for object_name in _region_preview_object_names(region_id) + _region_context_preview_object_names(row or {}, document=document):
        try:
            obj = document.getObject(object_name)
        except Exception:
            obj = None
        if obj is not None and obj not in objects:
            objects.append(obj)
    return objects


def _region_generated_object_summary(document, row: dict[str, object]) -> dict[str, object]:
    expected = _region_expected_preview_object_names(row, document=document)
    present = _existing_document_object_names(document, expected)
    missing = [name for name in expected if name not in present]
    if not expected:
        status = "not_required"
        diagnostics = "No Region-generated object families are required."
    elif missing:
        status = "missing"
        diagnostics = "Missing Region object families: " + ", ".join(_region_object_family_labels(missing))
    else:
        status = "ready"
        diagnostics = "Region object families are available."
    return {
        "region_object_status": status,
        "region_object_diagnostics": diagnostics,
        "region_object_count": len(present),
        "region_object_names": present,
        "missing_region_object_names": missing,
    }


def _region_expected_preview_object_names(row: dict[str, object], *, document=None) -> list[str]:
    region_id = str(row.get("region_id", "") or "")
    names = _region_expected_surface_preview_object_names(region_id, row)
    names.extend(_region_context_preview_object_names(row, document=document))
    return _unique_text_values(names)


def _region_expected_surface_preview_object_names(region_id: str, row: dict[str, object]) -> list[str]:
    if not region_id:
        return []
    roles = ["design", "subgrade", "daylight"]
    if _region_has_drainage_context(row):
        roles.append("drainage")
    return [_region_surface_preview_object_name(region_id, role) for role in roles]


def _region_has_drainage_context(row: dict[str, object]) -> bool:
    drainage = str(row.get("drainage", "") or "").strip()
    return bool(drainage and drainage != "-")


def _region_context_preview_object_names(row: dict[str, object], *, document=None) -> list[str]:
    names: list[str] = []
    for ref in _region_summary_refs(row.get("structure", "")):
        names.extend(_structure_preview_object_names_for_ref(document, ref))
    for ref in _region_summary_refs(row.get("drainage", ""), prefixes=("flow-route:",)):
        names.append("V1DrainagePipelineSegment_" + _safe_output_object_suffix(f"pipeline-segment:{ref}"))
    return names


def _structure_preview_object_names_for_ref(document, structure_ref: str) -> list[str]:
    ref = str(structure_ref or "").strip()
    if not ref:
        return []
    names: list[str] = []
    if document is not None:
        for obj in list(getattr(document, "Objects", []) or []):
            try:
                if str(getattr(obj, "CRRecordKind", "") or "") != "v1_structure_row_preview":
                    continue
                if str(getattr(obj, "StructureRef", "") or "").strip() != ref:
                    continue
                name = str(getattr(obj, "Name", "") or "")
                if name:
                    names.append(name)
            except Exception:
                continue
    if not names:
        names.append("V1StructurePreview_" + _safe_output_object_suffix(ref))
    return _unique_text_values(names)


def _existing_document_object_names(document, names: list[str]) -> list[str]:
    if document is None:
        return []
    existing: list[str] = []
    for name in _unique_text_values(names):
        try:
            if document.getObject(name) is not None:
                existing.append(name)
        except Exception:
            continue
    return existing


def _region_summary_refs(value: object, *, prefixes: tuple[str, ...] = ()) -> list[str]:
    text = str(value or "").strip()
    if not text or text == "-":
        return []
    refs: list[str] = []
    for chunk in text.replace("routes:", "").split(","):
        ref = chunk.strip()
        if not ref or ref.startswith("+") or ref.startswith("ditch points"):
            continue
        if prefixes and not any(ref.startswith(prefix) for prefix in prefixes):
            continue
        refs.append(ref)
    return _unique_text_values(refs)


def _region_object_family_labels(names: list[str]) -> list[str]:
    labels: list[str] = []
    for name in list(names or []):
        text = str(name or "")
        if text.startswith("V1CorridorRegionSurface_"):
            if text.endswith("_subgrade"):
                labels.append("subgrade surface")
            elif text.endswith("_daylight"):
                labels.append("slope surface")
            elif text.endswith("_drainage"):
                labels.append("drainage surface")
            else:
                labels.append("design surface")
        elif text.startswith("V1StructurePreview_"):
            labels.append("structure")
        elif text.startswith("V1DrainagePipelineSegment_"):
            labels.append("drainage pipeline")
        else:
            labels.append(text)
    return _unique_text_values(labels)


def _safe_output_object_suffix(value: object) -> str:
    text = str(value or "").strip()
    output = []
    for char in text:
        output.append(char if char.isalnum() else "_")
    return "".join(output).strip("_") or "unknown"


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
    side = str(getattr(point, "side", "") or "").strip().lower()
    if side == "left":
        return "L"
    if side == "right":
        return "R"
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


def _drainage_review_context_label(row: dict[str, object]) -> str:
    context = str(row.get("context", "") or row.get("review_kind", "") or "").strip().lower()
    if context == "intersection_drainage":
        return "Intersection Drainage"
    return "Roadside Drainage"


def _intersection_patch_fg_points(applied_section_set, prerequisite: IntersectionPatchPrerequisiteResult) -> list[dict[str, object]]:
    control_refs = set(str(value or "") for value in list(getattr(prerequisite, "control_region_refs", ()) or ()) if str(value or ""))
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    points: list[dict[str, object]] = []
    for section in _intersection_patch_sections(applied_section_set, prerequisite):
        section_id = str(getattr(section, "applied_section_id", "") or "")
        region_id = str(getattr(section, "region_id", "") or "")
        alignment_id = str(getattr(section, "alignment_id", "") or "")
        station = float(getattr(section, "station", 0.0) or 0.0)
        if intersection_id and str(getattr(section, "active_intersection_id", "") or "") != intersection_id and region_id not in control_refs:
            continue
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") != "fg_surface":
                continue
            points.append(
                {
                    "section_id": section_id,
                    "alignment_id": alignment_id,
                    "region_id": region_id,
                    "station": station,
                    "x": float(getattr(point, "x", 0.0) or 0.0),
                    "y": float(getattr(point, "y", 0.0) or 0.0),
                    "z": float(getattr(point, "z", 0.0) or 0.0),
                }
            )
    return points


def corridor_intersection_tie_in_edge_result(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> IntersectionTieInEdgeResult:
    """Extract first-slice intersection patch tie-in edge candidates from Applied Sections."""

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    sections = _intersection_patch_sections(applied_section_set, prerequisite)
    target_stations = _intersection_patch_target_stations_by_alignment(intersection_model, prerequisite)
    grouped: dict[str, list[object]] = {}
    for section in sections:
        alignment_id = str(getattr(section, "alignment_id", "") or "").strip()
        if not alignment_id:
            continue
        grouped.setdefault(alignment_id, []).append(section)

    edge_rows: list[IntersectionTieInEdgeRow] = []
    diagnostics: list[str] = []
    expected_alignments = [
        str(value or "")
        for value in list(getattr(prerequisite, "alignment_refs", ()) or ())
        if str(value or "").strip()
    ]
    for alignment_id in expected_alignments:
        alignment_sections = _station_ordered_applied_sections(
            AppliedSectionSet(
                schema_version=1,
                project_id="",
                applied_section_set_id="intersection-tie-in:sections",
                corridor_id="",
                sections=grouped.get(alignment_id, []),
            )
        )
        if not alignment_sections:
            diagnostics.append(f"intersection_tie_in_edge_missing: no Applied Sections for {alignment_id}.")
            continue
        target_station = target_stations.get(alignment_id)
        if target_station is None:
            stations = [float(getattr(row, "station", 0.0) or 0.0) for row in alignment_sections]
            target_station = sum(stations) / len(stations)
        start_section, end_section = _intersection_tie_in_section_pair(alignment_sections, float(target_station))
        for side in ("left", "right"):
            start_point = _intersection_tie_in_point(start_section, side)
            end_point = _intersection_tie_in_point(end_section, side)
            if start_point is None or end_point is None:
                diagnostics.append(f"intersection_tie_in_edge_missing: {alignment_id} {side} fg_surface edge is missing.")
                continue
            start_station = float(getattr(start_section, "station", 0.0) or 0.0)
            end_station = float(getattr(end_section, "station", start_station) or start_station)
            same_section = str(getattr(start_section, "applied_section_id", "") or "") == str(getattr(end_section, "applied_section_id", "") or "")
            start_xyz = _point_xyz_tuple(start_point)
            end_xyz = _point_xyz_tuple(end_point)
            if same_section:
                synthetic_edge = _intersection_single_section_tie_in_edge_xyz(start_section, start_xyz)
                if synthetic_edge is not None:
                    start_xyz, end_xyz, synthetic_station_start, synthetic_station_end = synthetic_edge
                    start_station = synthetic_station_start
                    end_station = synthetic_station_end
            edge_id = f"tie-in:{intersection_id}:{_safe_id_fragment(alignment_id)}:{side}"
            if same_section:
                diagnostics.append(
                    f"warning:intersection_tie_in_edge_single_section_candidate: {edge_id} uses one Applied Section; add adjacent section rows for a stronger tie-in edge."
                )
            edge_rows.append(
                IntersectionTieInEdgeRow(
                    tie_in_edge_id=edge_id,
                    intersection_id=intersection_id,
                    alignment_ref=alignment_id,
                    region_ref=str(getattr(start_section, "region_id", "") or getattr(end_section, "region_id", "") or ""),
                    side=side,
                    edge_role="pavement_edge",
                    station_start=min(start_station, end_station),
                    station_end=max(start_station, end_station),
                    section_start_ref=str(getattr(start_section, "applied_section_id", "") or ""),
                    section_end_ref=str(getattr(end_section, "applied_section_id", "") or ""),
                    start_xyz=start_xyz,
                    end_xyz=end_xyz,
                    status="single_section_candidate" if same_section else "candidate",
                    notes=f"target_station={float(target_station):.3f}",
                )
            )

    expected_edge_count = len(expected_alignments) * 2
    if expected_edge_count and len(edge_rows) < expected_edge_count:
        diagnostics.append(
            f"intersection_tie_in_edge_incomplete: expected {expected_edge_count} left/right edge candidate(s), found {len(edge_rows)}."
        )
    status = "ready" if edge_rows and not _diagnostics_include_error(diagnostics) else ("warning" if edge_rows else "missing")
    return IntersectionTieInEdgeResult(
        schema_version=1,
        project_id=str(getattr(applied_section_set, "project_id", "") or ""),
        label=f"Intersection Tie-in Edges - {intersection_id}",
        tie_in_edge_result_id=f"intersection-tie-in-edges:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        status=status,
        edge_count=len(edge_rows),
        diagnostic_rows=diagnostics,
        edge_rows=edge_rows,
    )


def _intersection_single_section_tie_in_edge_xyz(section, point_xyz: tuple[float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float], float, float] | None:
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    angle = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    direction = (math.cos(angle), math.sin(angle), 0.0)
    if _xyz_length(direction) <= 1.0e-9:
        return None
    width = abs(float(getattr(section, "surface_left_width", 0.0) or 0.0)) + abs(float(getattr(section, "surface_right_width", 0.0) or 0.0))
    span = max(width * 1.5, 8.0)
    half = span * 0.5
    station = float(getattr(section, "station", 0.0) or 0.0)
    start_xyz = (
        float(point_xyz[0]) - direction[0] * half,
        float(point_xyz[1]) - direction[1] * half,
        float(point_xyz[2]),
    )
    end_xyz = (
        float(point_xyz[0]) + direction[0] * half,
        float(point_xyz[1]) + direction[1] * half,
        float(point_xyz[2]),
    )
    return start_xyz, end_xyz, station - half, station + half


def corridor_intersection_boundary_segment_result(
    tie_in_result: IntersectionTieInEdgeResult,
    *,
    intersection_model=None,
) -> IntersectionBoundarySegmentResult:
    """Build first-slice boundary segment candidates from tie-in edges and curb-return policy."""

    intersection_id = str(getattr(tie_in_result, "intersection_id", "") or "").strip()
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    intersection_kind = str(getattr(source_row, "intersection_kind", "") or "t_intersection")
    policy = _intersection_curb_return_policy_for(intersection_model, intersection_id)
    raw_radius = float(getattr(policy, "radius", 0.0) or 0.0)
    radius = raw_radius
    diagnostics: list[str] = []
    if policy is not None and raw_radius <= 0.0:
        diagnostics.append(f"warning:intersection_curb_return_radius_invalid: radius {raw_radius:.3f} is not positive; default radius used.")
    elif 0.0 < raw_radius < 1.0:
        diagnostics.append(f"warning:intersection_curb_return_radius_small: radius {raw_radius:.3f} may be too small for a stable curb return.")
    if radius <= 0.0:
        radius = 12.0
        if intersection_kind == "cross_intersection":
            radius = 10.0
        elif intersection_kind == "y_intersection":
            radius = 15.0

    rows: list[IntersectionBoundarySegmentRow] = []
    for edge in list(getattr(tie_in_result, "edge_rows", []) or []):
        rows.append(
            IntersectionBoundarySegmentRow(
                boundary_segment_id=f"boundary:{str(getattr(edge, 'tie_in_edge_id', '') or len(rows) + 1)}",
                intersection_id=intersection_id,
                segment_kind="tie_in",
                segment_role="pavement_edge",
                source_ref=str(getattr(edge, "tie_in_edge_id", "") or ""),
                alignment_ref=str(getattr(edge, "alignment_ref", "") or ""),
                side=str(getattr(edge, "side", "") or ""),
                start_xyz=tuple(getattr(edge, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
                end_xyz=tuple(getattr(edge, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
                status=str(getattr(edge, "status", "") or "candidate"),
                notes=str(getattr(edge, "notes", "") or ""),
            )
        )

    tie_in_rows = [row for row in rows if row.segment_kind == "tie_in"]
    center = _intersection_boundary_center(source_row, rows)
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "") if source_row is not None else ""
    secondary_refs = list(getattr(source_row, "secondary_alignment_refs", []) or []) if source_row is not None else []
    secondary_ref = str(secondary_refs[0] if secondary_refs else "")
    primary_dir_candidate = _tie_in_alignment_direction(tie_in_result, primary_ref)
    secondary_dir_candidate = _tie_in_alignment_direction(tie_in_result, secondary_ref)
    if primary_dir_candidate is None:
        diagnostics.append(f"warning:intersection_boundary_direction_fallback: primary tie-in direction fallback used for {primary_ref or 'primary'}.")
    if secondary_dir_candidate is None:
        diagnostics.append(f"warning:intersection_boundary_direction_fallback: secondary tie-in direction fallback used for {secondary_ref or 'secondary'}.")
    primary_dir = primary_dir_candidate or (1.0, 0.0, 0.0)
    secondary_dir = secondary_dir_candidate or (0.0, 1.0, 0.0)
    primary_dir = _unit_xyz(primary_dir) or (1.0, 0.0, 0.0)
    secondary_dir = _unit_xyz(secondary_dir) or (0.0, 1.0, 0.0)
    quadrants = {
        "cross_intersection": ((1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)),
        "t_intersection": ((1.0, -1.0), (-1.0, -1.0)),
        "y_intersection": ((1.0, 1.0), (-1.0, 1.0)),
    }.get(intersection_kind, ((1.0, 1.0), (-1.0, 1.0)))
    if len(rows) < 4:
        diagnostics.append(f"intersection_boundary_tie_in_edges_incomplete: expected at least 4 tie-in segments, found {len(rows)}.")
    tie_in_span = _intersection_tie_in_boundary_span(tie_in_rows)
    if tie_in_span > 1.0e-9 and radius > tie_in_span * 0.75:
        diagnostics.append(
            f"warning:intersection_curb_return_radius_large: radius {radius:.3f} exceeds 75% of tie-in span {tie_in_span:.3f}."
        )
    arc_sample_count = _intersection_curb_return_arc_sample_count(radius, policy)
    for index, (primary_sign, secondary_sign) in enumerate(quadrants, start=1):
        chord_points = _intersection_curb_return_chord_points(
            center,
            primary_dir,
            secondary_dir,
            radius=radius,
            primary_sign=primary_sign,
            secondary_sign=secondary_sign,
            sample_count=arc_sample_count,
        )
        if len(chord_points) < 2:
            diagnostics.append(f"intersection_curb_return_radius_invalid: boundary arc {index} could not be sampled.")
            continue
        endpoint_gap = _intersection_boundary_arc_endpoint_gap(chord_points, tie_in_rows)
        endpoint_limit = max(15.0, radius * 1.5)
        if endpoint_gap is not None and endpoint_gap > endpoint_limit:
            diagnostics.append(
                "warning:intersection_curb_return_arc_endpoint_gap: "
                f"boundary arc {index} endpoint gap {endpoint_gap:.3f} exceeds limit {endpoint_limit:.3f}."
            )
        rows.append(
            IntersectionBoundarySegmentRow(
                boundary_segment_id=f"boundary:{intersection_id}:curb-return:{index}",
                intersection_id=intersection_id,
                segment_kind="arc",
                segment_role="curb_return",
                source_ref=str(getattr(policy, "policy_id", "") or ""),
                start_xyz=chord_points[0],
                end_xyz=chord_points[-1],
                center_xyz=center,
                radius=radius,
                chord_points_xyz=tuple(chord_points),
                status="candidate",
                notes=(
                    f"kind={intersection_kind}; quadrant={primary_sign:+.0f},{secondary_sign:+.0f}; "
                    f"arc_samples={len(chord_points)}; arc_segments={max(len(chord_points) - 1, 0)}"
                ),
            )
        )

    arc_count = len([row for row in rows if row.segment_kind == "arc"])
    tie_in_count = len([row for row in rows if row.segment_kind == "tie_in"])
    status = "ready" if rows and not _diagnostics_include_error(diagnostics) else ("warning" if rows else "missing")
    return IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id=str(getattr(tie_in_result, "project_id", "") or ""),
        label=f"Intersection Boundary Segments - {intersection_id}",
        boundary_segment_result_id=f"intersection-boundary-segments:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        status=status,
        segment_count=len(rows),
        tie_in_segment_count=tie_in_count,
        arc_segment_count=arc_count,
        diagnostic_rows=diagnostics,
        segment_rows=rows,
    )


def corridor_intersection_patch_boundary_result(
    boundary_result: IntersectionBoundarySegmentResult,
) -> IntersectionPatchBoundaryResult:
    """Create an ordered patch-boundary polygon candidate from boundary segment rows."""

    intersection_id = str(getattr(boundary_result, "intersection_id", "") or "").strip()
    diagnostics: list[str] = [str(value or "") for value in list(getattr(boundary_result, "diagnostic_rows", []) or []) if str(value or "")]
    union_result = _intersection_patch_boundary_from_tie_in_union(boundary_result, diagnostics)
    if union_result is not None:
        return union_result
    ring_raw_points: dict[str, list[tuple[tuple[float, float, float], str, str, str, str]]] = {}
    role_segment_counts = {"outer": 0, "hole": 0, "island": 0}
    for segment in list(getattr(boundary_result, "segment_rows", []) or []):
        segment_id = str(getattr(segment, "boundary_segment_id", "") or "")
        segment_kind = str(getattr(segment, "segment_kind", "") or "")
        segment_role = _intersection_patch_boundary_ring_role(segment)
        role_segment_counts.setdefault(segment_role, 0)
        role_segment_counts[segment_role] += 1
        ring_id = _intersection_patch_boundary_ring_id(segment, segment_role)
        ring_points = ring_raw_points.setdefault(ring_id, [])
        chord_points = list(getattr(segment, "chord_points_xyz", ()) or ())
        if chord_points:
            for point in chord_points:
                ring_points.append((_xyz_tuple(point), segment_id, segment_kind, segment_role, ring_id))
            continue
        ring_points.append((_xyz_tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0))), segment_id, segment_kind, segment_role, ring_id))
        ring_points.append((_xyz_tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0))), segment_id, segment_kind, segment_role, ring_id))

    ordered_rings: list[tuple[str, str, list[tuple[float, float, float, str, str, str, str]]]] = []
    for ring_id, raw_points in ring_raw_points.items():
        ordered = _ordered_intersection_patch_ring_points(raw_points)
        if ordered:
            ring_role = str(ordered[0][5] or "outer")
            ordered_rings.append((ring_id, ring_role, ordered))
    ordered_rings.sort(key=lambda item: (0 if item[1] == "outer" else 1 if item[1] == "hole" else 2, item[0]))
    outer_ordered = [point for _ring_id, ring_role, points in ordered_rings if ring_role == "outer" for point in points]

    if len(outer_ordered) < 3:
        diagnostics.append(
            f"intersection_patch_boundary_too_few_points: ordered outer boundary requires at least 3 unique points, found {len(outer_ordered)}."
        )
    point_rows: list[IntersectionPatchBoundaryPointRow] = []
    order_index = 1
    for ring_id, ring_role, ordered in ordered_rings:
        for point in ordered:
            point_rows.append(
                IntersectionPatchBoundaryPointRow(
                    boundary_point_id=f"patch-boundary:{intersection_id or 'unknown'}:{ring_id}:{order_index}",
                    intersection_id=intersection_id,
                    order_index=order_index,
                    x=float(point[0]),
                    y=float(point[1]),
                    z=float(point[2]),
                    source_segment_ref=str(point[3] or ""),
                    source_kind=str(point[4] or ""),
                    ring_id=str(point[6] or ring_id),
                    ring_role=str(point[5] or ring_role),
                    status="candidate",
                )
            )
            order_index += 1
    outer_point_rows = [row for row in point_rows if str(getattr(row, "ring_role", "") or "outer") == "outer"]
    polygon_area = _intersection_patch_boundary_multiring_area(point_rows)
    outer_area = abs(_intersection_patch_boundary_signed_area(outer_point_rows))
    self_crossing = _intersection_patch_boundary_has_self_crossing(outer_point_rows)
    diagnostics.extend(_intersection_patch_boundary_multiring_diagnostics(point_rows))
    if outer_area <= 1.0e-6 and len(outer_point_rows) >= 3:
        diagnostics.append("intersection_patch_boundary_zero_area: ordered boundary polygon area is too small.")
    if self_crossing:
        diagnostics.append("intersection_patch_boundary_self_crossing: ordered boundary candidate has crossing XY edges.")
    closed = len(outer_point_rows) >= 3 and not _diagnostics_include_error(diagnostics)
    status = "ready" if closed else ("warning" if outer_point_rows else "missing")
    hole_ring_count = len({str(getattr(row, "ring_id", "") or "") for row in point_rows if str(getattr(row, "ring_role", "") or "") == "hole"})
    island_ring_count = len({str(getattr(row, "ring_id", "") or "") for row in point_rows if str(getattr(row, "ring_role", "") or "") == "island"})
    outer_ring_count = len({str(getattr(row, "ring_id", "") or "") for row in point_rows if str(getattr(row, "ring_role", "") or "") == "outer"})
    return IntersectionPatchBoundaryResult(
        schema_version=1,
        project_id=str(getattr(boundary_result, "project_id", "") or ""),
        label=f"Intersection Patch Boundary - {intersection_id}",
        patch_boundary_result_id=f"intersection-patch-boundary:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        status=status,
        boundary_point_count=len(point_rows),
        source_segment_count=int(getattr(boundary_result, "segment_count", 0) or 0),
        ring_count=outer_ring_count + hole_ring_count + island_ring_count,
        outer_ring_count=outer_ring_count,
        hole_ring_count=hole_ring_count,
        island_ring_count=island_ring_count,
        closed=closed,
        polygon_area=polygon_area,
        self_crossing=self_crossing,
        diagnostic_rows=diagnostics,
        point_rows=point_rows,
    )


def corridor_intersection_slope_face_boundary_result(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> IntersectionSlopeFaceBoundaryResult:
    """Build reviewable slope-face boundary candidates around an intersection."""

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    diagnostics: list[str] = []
    if applied_section_set is None:
        diagnostics.append("intersection_slope_face_boundary_missing: Applied Sections are required.")
        return IntersectionSlopeFaceBoundaryResult(
            schema_version=1,
            project_id="",
            label=f"Intersection Slope Face Boundary - {intersection_id or 'unknown'}",
            intersection_id=intersection_id,
            status="missing",
            diagnostic_rows=diagnostics,
        )

    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    boundary_result = corridor_intersection_boundary_segment_result(
        tie_in_result,
        intersection_model=intersection_model,
    )
    tie_in_edges_by_id = {
        str(getattr(edge, "tie_in_edge_id", "") or ""): edge
        for edge in list(getattr(tie_in_result, "edge_rows", []) or [])
        if str(getattr(edge, "tie_in_edge_id", "") or "")
    }
    diagnostics.extend(str(value or "") for value in list(getattr(tie_in_result, "diagnostic_rows", []) or []) if str(value or ""))
    diagnostics.extend(str(value or "") for value in list(getattr(boundary_result, "diagnostic_rows", []) or []) if str(value or ""))

    grouped_sections: dict[str, list[object]] = {}
    for section in list(getattr(applied_section_set, "sections", []) or []):
        alignment_id = str(getattr(section, "alignment_id", "") or "").strip()
        if not alignment_id:
            continue
        active_intersection = str(getattr(section, "active_intersection_id", "") or "").strip()
        if intersection_id and active_intersection and active_intersection != intersection_id:
            continue
        grouped_sections.setdefault(alignment_id, []).append(section)
    for alignment_id in list(grouped_sections):
        grouped_sections[alignment_id] = sorted(
            grouped_sections[alignment_id],
            key=lambda section: float(getattr(section, "station", 0.0) or 0.0),
        )

    slope_boundary_segments = _intersection_slope_face_boundary_target_segments(
        boundary_result,
        intersection_model=intersection_model,
        intersection_id=intersection_id,
    )
    rows: list[IntersectionSlopeFaceBoundaryRow] = []
    for segment in slope_boundary_segments:
        if str(getattr(segment, "segment_kind", "") or "") != "tie_in":
            continue
        alignment_ref = str(getattr(segment, "alignment_ref", "") or "").strip()
        side = str(getattr(segment, "side", "") or "").strip()
        if not alignment_ref or side not in {"left", "right"}:
            continue
        inner_points = (
            _xyz_tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0))),
            _xyz_tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0))),
        )
        source_tie_in_edge = tie_in_edges_by_id.get(str(getattr(segment, "source_ref", "") or ""))
        source_section_refs = {
            str(getattr(source_tie_in_edge, "section_start_ref", "") or ""),
            str(getattr(source_tie_in_edge, "section_end_ref", "") or ""),
        }
        source_section_refs = {value for value in source_section_refs if value}
        candidate_sections = list(grouped_sections.get(alignment_ref, []) or [])
        if source_section_refs:
            candidate_sections = [
                section for section in candidate_sections
                if str(getattr(section, "applied_section_id", "") or "") in source_section_refs
            ]
        if not candidate_sections:
            candidate_sections = _nearest_applied_sections_to_xy_segment(
                grouped_sections.get(alignment_ref, []) or [],
                inner_points[0],
                inner_points[1],
                max_count=2,
            )
        candidate_sections = _intersection_slope_face_boundary_extended_sections(
            grouped_sections.get(alignment_ref, []) or [],
            candidate_sections,
            source_tie_in_edge=source_tie_in_edge,
            intersection_id=intersection_id,
            side=side,
            extension_length=INTERSECTION_SLOPE_FACE_BOUNDARY_EXTENSION_LENGTH,
        )
        applied_inner_points: list[tuple[float, float, float]] = []
        outer_points: list[tuple[float, float, float]] = []
        source_refs: list[str] = []
        projected_outer_rows: list[tuple[float, tuple[float, float, float], str, tuple[float, float, float]]] = []
        for section in candidate_sections:
            edge = _applied_section_slope_face_edge_points(
                section,
                side_label=side,
                fallback_band_width=6.0,
                fallback_band_slope=0.33,
            )
            if edge is None:
                continue
            section_inner, outer = edge
            outer_xyz = _xyz_tuple(outer)
            projection = _xy_segment_projection_ratio(
                outer_xyz,
                inner_points[0],
                inner_points[1],
            )
            projected_outer_rows.append((projection, outer_xyz, str(getattr(section, "applied_section_id", "") or ""), _xyz_tuple(section_inner)))
        for _projection, outer_xyz, source_ref, section_inner in sorted(projected_outer_rows, key=lambda item: item[0]):
            if applied_inner_points and _xy_distance((applied_inner_points[-1][0], applied_inner_points[-1][1]), (section_inner[0], section_inner[1])) <= 1.0e-6:
                continue
            if outer_points and _xy_distance((outer_points[-1][0], outer_points[-1][1]), (outer_xyz[0], outer_xyz[1])) <= 1.0e-6:
                continue
            applied_inner_points.append(section_inner)
            outer_points.append(outer_xyz)
            source_refs.append(source_ref)
        if len(outer_points) == 1 and projected_outer_rows:
            _projection, outer_xyz, source_ref, section_inner = sorted(projected_outer_rows, key=lambda item: abs(item[0] - 0.5))[0]
            vector = (
                float(outer_xyz[0]) - float(section_inner[0]),
                float(outer_xyz[1]) - float(section_inner[1]),
                float(outer_xyz[2]) - float(section_inner[2]),
            )
            outer_points = [
                (
                    float(inner_points[0][0]) + vector[0],
                    float(inner_points[0][1]) + vector[1],
                    float(inner_points[0][2]) + vector[2],
                ),
                (
                    float(inner_points[1][0]) + vector[0],
                    float(inner_points[1][1]) + vector[1],
                    float(inner_points[1][2]) + vector[2],
                ),
            ]
            source_refs = [source_ref, source_ref]
            applied_inner_points = list(inner_points)
        if len(applied_inner_points) >= 2:
            inner_points = tuple(applied_inner_points)
        row_diagnostics: list[str] = []
        if len(outer_points) < 2:
            row_diagnostics.append(
                f"warning:intersection_slope_face_boundary_outer_points_missing: {alignment_ref} {side} requires at least two Applied Section slope-face outer points."
            )
        if len(inner_points) < 2:
            row_diagnostics.append(
                f"warning:intersection_slope_face_boundary_inner_points_missing: {alignment_ref} {side} requires an Intersection Surface boundary edge."
            )
        status = "ready" if len(outer_points) >= 2 and len(inner_points) >= 2 else "warning"
        diagnostics.extend(row_diagnostics)
        rows.append(
            IntersectionSlopeFaceBoundaryRow(
                boundary_id=f"slope-face-boundary:{intersection_id or 'unknown'}:{_safe_id_fragment(alignment_ref)}:{side}",
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                side=side,
                inner_points_xyz=tuple(inner_points),
                outer_points_xyz=tuple(outer_points),
                start_tie_edge_xyz=(inner_points[0], outer_points[0]) if outer_points else (),
                end_tie_edge_xyz=(inner_points[-1], outer_points[-1]) if outer_points else (),
                source_applied_section_refs=tuple(source_refs),
                source_intersection_surface_ref=str(getattr(segment, "boundary_segment_id", "") or ""),
                status=status,
                diagnostics=tuple(row_diagnostics),
                notes=f"inner=intersection_surface_boundary; outer=applied_sections:{len(source_refs)}",
            )
        )

    ready_count = len([row for row in rows if str(getattr(row, "status", "") or "") == "ready"])
    warning_count = len([row for row in rows if str(getattr(row, "status", "") or "") == "warning"])
    status = "ready" if rows and warning_count == 0 and not _diagnostics_include_error(diagnostics) else ("warning" if rows else "missing")
    return IntersectionSlopeFaceBoundaryResult(
        schema_version=1,
        project_id=str(getattr(applied_section_set, "project_id", "") or ""),
        label=f"Intersection Slope Face Boundary - {intersection_id or 'unknown'}",
        boundary_result_id=f"intersection-slope-face-boundary:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        status=status,
        boundary_count=len(rows),
        ready_count=ready_count,
        warning_count=warning_count,
        diagnostic_rows=diagnostics,
        boundary_rows=rows,
    )


def _intersection_patch_boundary_ring_role(segment) -> str:
    text = " ".join(
        [
            str(getattr(segment, "segment_role", "") or ""),
            str(getattr(segment, "segment_kind", "") or ""),
            str(getattr(segment, "notes", "") or ""),
        ]
    ).strip().lower()
    if any(token in text for token in ("hole", "void", "opening")):
        return "hole"
    if "island" in text:
        return "island"
    return "outer"


def _intersection_patch_boundary_from_tie_in_union(
    boundary_result: IntersectionBoundarySegmentResult,
    diagnostics: list[str],
) -> IntersectionPatchBoundaryResult | None:
    """Build the patch boundary from the union outline of participating pavement strips."""

    tie_in_rows = [
        row for row in list(getattr(boundary_result, "segment_rows", []) or [])
        if str(getattr(row, "segment_kind", "") or "") == "tie_in"
    ]
    grouped: dict[str, list[IntersectionBoundarySegmentRow]] = {}
    for row in tie_in_rows:
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        if alignment_ref:
            grouped.setdefault(alignment_ref, []).append(row)
    polygons: list[list[tuple[float, float, float]]] = []
    for alignment_ref, rows in grouped.items():
        polygon = _intersection_tie_in_strip_polygon(rows)
        if polygon is None:
            diagnostics.append(f"warning:intersection_tie_in_strip_incomplete: {alignment_ref} cannot form a pavement strip boundary.")
            continue
        polygons.append(polygon)
    if len(polygons) < 2:
        return None
    union_points = _xy_polygon_union_outer_boundary(polygons)
    if len(union_points) < 3:
        diagnostics.append("warning:intersection_patch_boundary_union_failed: tie-in strip union could not produce an outer boundary.")
        return None
    point_rows: list[IntersectionPatchBoundaryPointRow] = []
    intersection_id = str(getattr(boundary_result, "intersection_id", "") or "").strip()
    for index, point in enumerate(union_points, start=1):
        point_rows.append(
            IntersectionPatchBoundaryPointRow(
                boundary_point_id=f"patch-boundary:{intersection_id or 'unknown'}:tie-in-union:{index}",
                intersection_id=intersection_id,
                order_index=index,
                x=float(point[0]),
                y=float(point[1]),
                z=float(point[2]),
                source_segment_ref="tie-in-strip-union",
                source_kind="tie_in_union",
                ring_id="outer",
                ring_role="outer",
                status="candidate",
                notes="intersection patch boundary from pavement strip union",
            )
        )
    polygon_area = abs(_intersection_patch_boundary_signed_area(point_rows))
    self_crossing = _intersection_patch_boundary_has_self_crossing(point_rows)
    output_diagnostics = list(diagnostics or [])
    output_diagnostics.extend(_intersection_patch_boundary_multiring_diagnostics(point_rows))
    if polygon_area <= 1.0e-6:
        output_diagnostics.append("intersection_patch_boundary_zero_area: tie-in union boundary polygon area is too small.")
    if self_crossing:
        output_diagnostics.append("intersection_patch_boundary_self_crossing: tie-in union boundary has crossing XY edges.")
    closed = len(point_rows) >= 3 and not _diagnostics_include_error(output_diagnostics)
    return IntersectionPatchBoundaryResult(
        schema_version=1,
        project_id=str(getattr(boundary_result, "project_id", "") or ""),
        label=f"Intersection Patch Boundary - {intersection_id}",
        patch_boundary_result_id=f"intersection-patch-boundary:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        boundary_mode="tie_in_strip_union",
        status="ready" if closed else "warning",
        boundary_point_count=len(point_rows),
        source_segment_count=len(tie_in_rows),
        ring_count=1,
        outer_ring_count=1,
        hole_ring_count=0,
        island_ring_count=0,
        closed=closed,
        polygon_area=polygon_area,
        self_crossing=self_crossing,
        diagnostic_rows=output_diagnostics,
        point_rows=point_rows,
    )


def _intersection_tie_in_strip_polygon(rows: list[IntersectionBoundarySegmentRow]) -> list[tuple[float, float, float]] | None:
    if len(rows) < 2:
        return None
    ordered_rows = sorted(
        rows,
        key=lambda row: float(getattr(row, "station_start", 0.0) or 0.0),
    )
    first = ordered_rows[0]
    second = ordered_rows[1]
    first_start = _xyz_tuple(getattr(first, "start_xyz", (0.0, 0.0, 0.0)))
    first_end = _xyz_tuple(getattr(first, "end_xyz", (0.0, 0.0, 0.0)))
    second_start = _xyz_tuple(getattr(second, "start_xyz", (0.0, 0.0, 0.0)))
    second_end = _xyz_tuple(getattr(second, "end_xyz", (0.0, 0.0, 0.0)))
    candidates = [
        [first_start, first_end, second_end, second_start],
        [first_start, second_start, second_end, first_end],
    ]
    valid = [
        polygon for polygon in candidates
        if abs(_xy_area_from_xyz_points(polygon)) > 1.0e-6
        and not _xy_xyz_polygon_self_crossing(polygon)
    ]
    if valid:
        return max(valid, key=lambda polygon: abs(_xy_area_from_xyz_points(polygon)))
    best = max(candidates, key=lambda polygon: abs(_xy_area_from_xyz_points(polygon)))
    return best if abs(_xy_area_from_xyz_points(best)) > 1.0e-6 else None


def _xy_polygon_union_outer_boundary(
    polygons: list[list[tuple[float, float, float]]],
) -> list[tuple[float, float, float]]:
    kept_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for polygon_index, polygon in enumerate(polygons):
        other_polygons = [other for index, other in enumerate(polygons) if index != polygon_index]
        for start, end in _xyz_closed_edges(polygon):
            split_points = [start, end]
            for other in other_polygons:
                for other_start, other_end in _xyz_closed_edges(other):
                    intersection = _xy_segment_intersection_point(start, end, other_start, other_end)
                    if intersection is not None:
                        split_points.append(intersection)
            split_points = _sort_points_along_segment(start, end, _unique_xyz_points(split_points))
            for first, second in zip(split_points, split_points[1:]):
                if _xy_distance((first[0], first[1]), (second[0], second[1])) <= 1.0e-6:
                    continue
                midpoint = (
                    (first[0] + second[0]) * 0.5,
                    (first[1] + second[1]) * 0.5,
                    (first[2] + second[2]) * 0.5,
                )
                if any(_xy_point_in_polygon_strict((midpoint[0], midpoint[1]), [(p[0], p[1]) for p in other]) for other in other_polygons):
                    continue
                kept_segments.append((first, second))
    return _ordered_outer_boundary_from_segments(kept_segments)


def _ordered_outer_boundary_from_segments(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
) -> list[tuple[float, float, float]]:
    normalized_segments = []
    for start, end in segments:
        if _xy_distance((start[0], start[1]), (end[0], end[1])) <= 1.0e-6:
            continue
        normalized_segments.append((start, end))
    if len(normalized_segments) < 3:
        return []
    point_by_key: dict[tuple[float, float], tuple[float, float, float]] = {}
    adjacency: dict[tuple[float, float], list[tuple[float, float]]] = {}
    edge_set: set[frozenset[tuple[float, float]]] = set()
    for start, end in normalized_segments:
        start_key = _xy_key(start)
        end_key = _xy_key(end)
        if start_key == end_key:
            continue
        point_by_key.setdefault(start_key, start)
        point_by_key.setdefault(end_key, end)
        edge_key = frozenset((start_key, end_key))
        if edge_key in edge_set:
            continue
        edge_set.add(edge_key)
        adjacency.setdefault(start_key, []).append(end_key)
        adjacency.setdefault(end_key, []).append(start_key)
    rings = _closed_boundary_rings_from_adjacency(adjacency, point_by_key)
    if not rings:
        return []
    return max(rings, key=lambda ring: abs(_xy_area_from_xyz_points(ring)))


def _closed_boundary_rings_from_adjacency(
    adjacency: dict[tuple[float, float], list[tuple[float, float]]],
    point_by_key: dict[tuple[float, float], tuple[float, float, float]],
) -> list[list[tuple[float, float, float]]]:
    unused_edges: set[frozenset[tuple[float, float]]] = set()
    for key, neighbors in adjacency.items():
        for neighbor in neighbors:
            unused_edges.add(frozenset((key, neighbor)))
    rings: list[list[tuple[float, float, float]]] = []
    while unused_edges:
        edge = next(iter(unused_edges))
        start_key, next_key = tuple(edge)
        ring_keys = [start_key]
        previous_key = start_key
        current_key = next_key
        guard = 0
        while guard < max(8, len(unused_edges) + len(adjacency) * 4):
            guard += 1
            unused_edges.discard(frozenset((previous_key, current_key)))
            ring_keys.append(current_key)
            if current_key == start_key:
                break
            candidates = [
                key for key in list(adjacency.get(current_key, []) or [])
                if key != previous_key and frozenset((current_key, key)) in unused_edges
            ]
            if not candidates:
                break
            current_point = point_by_key.get(current_key, (0.0, 0.0, 0.0))
            previous_point = point_by_key.get(previous_key, current_point)
            current_angle = math.atan2(current_point[1] - previous_point[1], current_point[0] - previous_point[0])
            next_key = min(
                candidates,
                key=lambda key: _positive_angle_delta(
                    current_angle,
                    math.atan2(
                        point_by_key.get(key, current_point)[1] - current_point[1],
                        point_by_key.get(key, current_point)[0] - current_point[0],
                    ),
                ),
            )
            previous_key, current_key = current_key, next_key
        if len(ring_keys) >= 4 and ring_keys[-1] == start_key:
            unique_keys = ring_keys[:-1]
            ring = [point_by_key[key] for key in unique_keys if key in point_by_key]
            if len(ring) >= 3 and not _xy_xyz_polygon_self_crossing(ring):
                if _xy_area_from_xyz_points(ring) < 0.0:
                    ring.reverse()
                rings.append(ring)
    return rings


def _positive_angle_delta(current_angle: float, next_angle: float) -> float:
    delta = float(next_angle) - float(current_angle)
    while delta <= 0.0:
        delta += math.tau
    return delta


def _xy_key(point: tuple[float, float, float]) -> tuple[float, float]:
    return (round(float(point[0]), 6), round(float(point[1]), 6))


def _xy_segment_intersection_point(
    a1: tuple[float, float, float],
    a2: tuple[float, float, float],
    b1: tuple[float, float, float],
    b2: tuple[float, float, float],
) -> tuple[float, float, float] | None:
    x1, y1 = float(a1[0]), float(a1[1])
    x2, y2 = float(a2[0]), float(a2[1])
    x3, y3 = float(b1[0]), float(b1[1])
    x4, y4 = float(b2[0]), float(b2[1])
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) <= 1.0e-9:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
    if not _xy_point_on_segment((px, py), (x1, y1), (x2, y2)):
        return None
    if not _xy_point_on_segment((px, py), (x3, y3), (x4, y4)):
        return None
    ta = _xy_segment_parameter((px, py), (x1, y1), (x2, y2))
    tb = _xy_segment_parameter((px, py), (x3, y3), (x4, y4))
    za = float(a1[2]) + (float(a2[2]) - float(a1[2])) * ta
    zb = float(b1[2]) + (float(b2[2]) - float(b1[2])) * tb
    return (px, py, (za + zb) * 0.5)


def _xy_point_on_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> bool:
    cross = (point[1] - start[1]) * (end[0] - start[0]) - (point[0] - start[0]) * (end[1] - start[1])
    if abs(cross) > 1.0e-6:
        return False
    return (
        min(start[0], end[0]) - 1.0e-6 <= point[0] <= max(start[0], end[0]) + 1.0e-6
        and min(start[1], end[1]) - 1.0e-6 <= point[1] <= max(start[1], end[1]) + 1.0e-6
    )


def _xy_segment_parameter(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= 1.0e-12:
        return 0.0
    return max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator))


def _xy_point_in_polygon_strict(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    for start, end in _xy_closed_edges(polygon):
        if _xy_point_on_segment(point, start, end):
            return False
    return _xy_point_in_polygon(point, polygon)


def _xyz_closed_edges(points: list[tuple[float, float, float]]) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    return [(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]


def _unique_xyz_points(points: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    seen: set[tuple[float, float]] = set()
    for point in points:
        key = (round(float(point[0]), 6), round(float(point[1]), 6))
        if key in seen:
            continue
        seen.add(key)
        output.append(point)
    return output


def _sort_points_along_segment(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    points: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    return sorted(points, key=lambda point: _xy_segment_parameter((point[0], point[1]), (start[0], start[1]), (end[0], end[1])))


def _xy_area_from_xyz_points(points: list[tuple[float, float, float]]) -> float:
    area = 0.0
    for index in range(len(points)):
        current = points[index]
        nxt = points[(index + 1) % len(points)]
        area += float(current[0]) * float(nxt[1])
        area -= float(nxt[0]) * float(current[1])
    return area * 0.5


def _xy_xyz_polygon_self_crossing(points: list[tuple[float, float, float]]) -> bool:
    xy_points = [(float(point[0]), float(point[1])) for point in points]
    edge_count = len(xy_points)
    for index in range(edge_count):
        a1 = xy_points[index]
        a2 = xy_points[(index + 1) % edge_count]
        for other_index in range(index + 1, edge_count):
            if abs(index - other_index) <= 1:
                continue
            if index == 0 and other_index == edge_count - 1:
                continue
            b1 = xy_points[other_index]
            b2 = xy_points[(other_index + 1) % edge_count]
            if _xy_segments_intersect(a1, a2, b1, b2):
                return True
    return False


def _intersection_patch_boundary_ring_id(segment, ring_role: str) -> str:
    text = str(getattr(segment, "segment_role", "") or "").strip()
    if ":" in text:
        return text
    role = str(ring_role or "outer").strip() or "outer"
    if role == "outer":
        return "outer"
    source_ref = str(getattr(segment, "source_ref", "") or "").strip()
    if source_ref:
        return f"{role}:{_safe_id_fragment(source_ref)}"
    segment_id = str(getattr(segment, "boundary_segment_id", "") or "").strip()
    if segment_id:
        prefix = f"boundary:{role}-"
        if segment_id.startswith(prefix):
            return f"{role}:{segment_id[len(prefix):].split(':')[0]}"
        return f"{role}:{_safe_id_fragment(segment_id)}"
    return role


def _ordered_intersection_patch_ring_points(
    raw_points: list[tuple[tuple[float, float, float], str, str, str, str]]
) -> list[tuple[float, float, float, str, str, str, str]]:
    unique_points: dict[tuple[float, float], tuple[float, float, float, str, str, str, str]] = {}
    for point, segment_id, segment_kind, segment_role, ring_id in raw_points:
        key = (round(float(point[0]), 6), round(float(point[1]), 6))
        unique_points.setdefault(key, (point[0], point[1], point[2], segment_id, segment_kind, segment_role, ring_id))
    if len(unique_points) < 3:
        return list(unique_points.values())
    center_x = sum(point[0] for point in unique_points.values()) / max(1, len(unique_points))
    center_y = sum(point[1] for point in unique_points.values()) / max(1, len(unique_points))
    return sorted(
        unique_points.values(),
        key=lambda point: math.atan2(float(point[1]) - center_y, float(point[0]) - center_x),
    )


def _xyz_tuple(point) -> tuple[float, float, float]:
    values = tuple(point or (0.0, 0.0, 0.0))
    return (
        float(values[0]) if len(values) > 0 else 0.0,
        float(values[1]) if len(values) > 1 else 0.0,
        float(values[2]) if len(values) > 2 else 0.0,
    )


def _resample_xyz_polyline(points, target_count: int) -> list[tuple[float, float, float]]:
    ordered = [_xyz_tuple(point) for point in list(points or [])]
    if not ordered:
        return []
    if len(ordered) == 1 or int(target_count or 0) <= 1:
        return [ordered[0]]
    target_count = max(2, int(target_count))
    cumulative_lengths = [0.0]
    total = 0.0
    for first, second in zip(ordered, ordered[1:]):
        total += math.sqrt(
            (float(second[0]) - float(first[0])) ** 2
            + (float(second[1]) - float(first[1])) ** 2
            + (float(second[2]) - float(first[2])) ** 2
        )
        cumulative_lengths.append(total)
    if total <= 1.0e-9:
        return [ordered[0] for _index in range(target_count)]
    output: list[tuple[float, float, float]] = []
    for index in range(target_count):
        distance = total * (float(index) / float(target_count - 1))
        output.append(_interpolate_xyz_polyline_at_distance(ordered, cumulative_lengths, distance))
    return output


def _interpolate_xyz_polyline_at_distance(
    points: list[tuple[float, float, float]],
    cumulative_lengths: list[float],
    distance: float,
) -> tuple[float, float, float]:
    if not points:
        return (0.0, 0.0, 0.0)
    if distance <= 0.0:
        return points[0]
    if distance >= float(cumulative_lengths[-1] if cumulative_lengths else 0.0):
        return points[-1]
    for index in range(1, len(points)):
        start_distance = float(cumulative_lengths[index - 1])
        end_distance = float(cumulative_lengths[index])
        if distance > end_distance:
            continue
        span = end_distance - start_distance
        ratio = 0.0 if span <= 1.0e-9 else (float(distance) - start_distance) / span
        first = points[index - 1]
        second = points[index]
        return (
            float(first[0]) + (float(second[0]) - float(first[0])) * ratio,
            float(first[1]) + (float(second[1]) - float(first[1])) * ratio,
            float(first[2]) + (float(second[2]) - float(first[2])) * ratio,
        )
    return points[-1]


def _intersection_patch_boundary_has_self_crossing(point_rows: list[IntersectionPatchBoundaryPointRow]) -> bool:
    if len(point_rows) < 4:
        return False
    points = [(float(row.x), float(row.y)) for row in point_rows]
    edge_count = len(points)
    for index in range(edge_count):
        a1 = points[index]
        a2 = points[(index + 1) % edge_count]
        for other_index in range(index + 1, edge_count):
            if abs(index - other_index) <= 1:
                continue
            if index == 0 and other_index == edge_count - 1:
                continue
            b1 = points[other_index]
            b2 = points[(other_index + 1) % edge_count]
            if _xy_segments_intersect(a1, a2, b1, b2):
                return True
    return False


def _intersection_patch_boundary_signed_area(point_rows: list[IntersectionPatchBoundaryPointRow]) -> float:
    area = 0.0
    for index in range(len(point_rows)):
        current = point_rows[index]
        nxt = point_rows[(index + 1) % len(point_rows)]
        area += float(getattr(current, "x", 0.0) or 0.0) * float(getattr(nxt, "y", 0.0) or 0.0)
        area -= float(getattr(nxt, "x", 0.0) or 0.0) * float(getattr(current, "y", 0.0) or 0.0)
    return area * 0.5


def _intersection_patch_boundary_multiring_area(point_rows: list[IntersectionPatchBoundaryPointRow]) -> float:
    grouped: dict[str, list[IntersectionPatchBoundaryPointRow]] = {}
    roles: dict[str, str] = {}
    for row in list(point_rows or []):
        ring_id = str(getattr(row, "ring_id", "") or "outer")
        grouped.setdefault(ring_id, []).append(row)
        roles[ring_id] = str(getattr(row, "ring_role", "") or "outer")
    area = 0.0
    for ring_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: int(getattr(row, "order_index", 0) or 0))
        ring_area = abs(_intersection_patch_boundary_signed_area(ordered))
        role = roles.get(ring_id, "outer")
        if role == "hole":
            area -= ring_area
        else:
            area += ring_area
    return max(area, 0.0)


def _intersection_patch_boundary_multiring_diagnostics(point_rows: list[IntersectionPatchBoundaryPointRow]) -> list[str]:
    grouped: dict[str, list[IntersectionPatchBoundaryPointRow]] = {}
    roles: dict[str, str] = {}
    for row in list(point_rows or []):
        ring_id = str(getattr(row, "ring_id", "") or "outer")
        grouped.setdefault(ring_id, []).append(row)
        roles[ring_id] = str(getattr(row, "ring_role", "") or "outer")
    diagnostics: list[str] = []
    outer_rows = _intersection_patch_boundary_primary_outer_ring(grouped, roles)
    outer_polygon = [(float(row.x), float(row.y)) for row in outer_rows]
    for ring_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: int(getattr(row, "order_index", 0) or 0))
        role = roles.get(ring_id, "outer")
        if len(ordered) < 3:
            diagnostics.append(f"intersection_patch_boundary_ring_too_few_points: {ring_id} has fewer than 3 point(s).")
            continue
        ring_area = abs(_intersection_patch_boundary_signed_area(ordered))
        if ring_area <= 1.0e-6:
            diagnostics.append(f"intersection_patch_boundary_ring_zero_area: {ring_id} area is too small.")
        if _intersection_patch_boundary_has_self_crossing(ordered):
            diagnostics.append(f"intersection_patch_boundary_ring_self_crossing: {ring_id} has crossing XY edges.")
        if role == "outer":
            continue
        if len(outer_polygon) >= 3:
            centroid = _intersection_patch_boundary_ring_centroid(ordered)
            if not _xy_point_in_polygon(centroid, outer_polygon):
                diagnostics.append(f"intersection_patch_boundary_inner_ring_outside_outer: {ring_id} is outside the outer ring.")
            elif _intersection_patch_boundary_rings_intersect(ordered, outer_rows):
                diagnostics.append(f"intersection_patch_boundary_inner_ring_intersects_outer: {ring_id} intersects the outer ring.")
    inner_ring_ids = [ring_id for ring_id, role in roles.items() if role in {"hole", "island"}]
    for index, ring_id in enumerate(inner_ring_ids):
        first = sorted(grouped.get(ring_id, []), key=lambda row: int(getattr(row, "order_index", 0) or 0))
        for other_id in inner_ring_ids[index + 1:]:
            second = sorted(grouped.get(other_id, []), key=lambda row: int(getattr(row, "order_index", 0) or 0))
            if _intersection_patch_boundary_rings_intersect(first, second):
                diagnostics.append(f"intersection_patch_boundary_inner_rings_intersect: {ring_id} intersects {other_id}.")
    return diagnostics


def _intersection_patch_boundary_primary_outer_ring(
    grouped: dict[str, list[IntersectionPatchBoundaryPointRow]],
    roles: dict[str, str],
) -> list[IntersectionPatchBoundaryPointRow]:
    outer_candidates = [
        sorted(rows, key=lambda row: int(getattr(row, "order_index", 0) or 0))
        for ring_id, rows in grouped.items()
        if roles.get(ring_id, "outer") == "outer"
    ]
    if not outer_candidates:
        return []
    return max(outer_candidates, key=lambda rows: abs(_intersection_patch_boundary_signed_area(rows)))


def _intersection_patch_boundary_ring_centroid(point_rows: list[IntersectionPatchBoundaryPointRow]) -> tuple[float, float]:
    if not point_rows:
        return (0.0, 0.0)
    return (
        sum(float(getattr(row, "x", 0.0) or 0.0) for row in point_rows) / len(point_rows),
        sum(float(getattr(row, "y", 0.0) or 0.0) for row in point_rows) / len(point_rows),
    )


def _intersection_patch_boundary_rings_intersect(
    first: list[IntersectionPatchBoundaryPointRow],
    second: list[IntersectionPatchBoundaryPointRow],
) -> bool:
    first_points = [(float(row.x), float(row.y)) for row in first]
    second_points = [(float(row.x), float(row.y)) for row in second]
    if len(first_points) < 2 or len(second_points) < 2:
        return False
    for first_start, first_end in _xy_closed_edges(first_points):
        for second_start, second_end in _xy_closed_edges(second_points):
            if _xy_segments_intersect(first_start, first_end, second_start, second_end):
                return True
    return False


def _xy_segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def orientation(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        return (
            min(p[0], r[0]) - 1.0e-9 <= q[0] <= max(p[0], r[0]) + 1.0e-9
            and min(p[1], r[1]) - 1.0e-9 <= q[1] <= max(p[1], r[1]) + 1.0e-9
        )

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)
    if o1 * o2 < 0.0 and o3 * o4 < 0.0:
        return True
    if abs(o1) <= 1.0e-9 and on_segment(a1, b1, a2):
        return True
    if abs(o2) <= 1.0e-9 and on_segment(a1, b2, a2):
        return True
    if abs(o3) <= 1.0e-9 and on_segment(b1, a1, b2):
        return True
    if abs(o4) <= 1.0e-9 and on_segment(b1, a2, b2):
        return True
    return False


def _intersection_curb_return_policy_for(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    rows = list(getattr(intersection_model, "curb_return_policy_rows", []) or []) if intersection_model is not None else []
    for row in rows:
        if str(getattr(row, "intersection_id", "") or "") == target and str(getattr(row, "status", "") or "active") != "disabled":
            return row
    return None


def _intersection_curb_return_arc_sample_count(radius: float, policy=None) -> int:
    """Return chord point count for a 90-degree curb-return arc."""

    explicit = int(float(getattr(policy, "arc_sample_count", 0) or getattr(policy, "sample_count", 0) or 0))
    if explicit > 0:
        return max(5, min(explicit, 49))
    spacing = float(
        getattr(policy, "arc_sample_spacing", 0.0)
        or getattr(policy, "sample_spacing", 0.0)
        or 2.0
    )
    spacing = max(spacing, 0.5)
    arc_length = max(float(radius), 0.0) * (math.pi / 2.0)
    segment_count = int(math.ceil(arc_length / spacing)) if arc_length > 0.0 else 4
    segment_count = max(4, min(segment_count, 48))
    return segment_count + 1


def _intersection_boundary_center(source_row, segment_rows: list[IntersectionBoundarySegmentRow]) -> tuple[float, float, float]:
    if source_row is not None:
        x = float(getattr(source_row, "intersection_point_x", 0.0) or 0.0)
        y = float(getattr(source_row, "intersection_point_y", 0.0) or 0.0)
        z = float(getattr(source_row, "intersection_point_z", 0.0) or 0.0)
        if abs(x) > 1.0e-9 or abs(y) > 1.0e-9 or abs(z) > 1.0e-9:
            return (x, y, z)
    points: list[tuple[float, float, float]] = []
    for row in segment_rows:
        points.append(tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)))
        points.append(tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)))
    if not points:
        return (0.0, 0.0, 0.0)
    return (
        sum(float(point[0]) for point in points) / len(points),
        sum(float(point[1]) for point in points) / len(points),
        sum(float(point[2]) for point in points) / len(points),
    )


def _tie_in_alignment_direction(tie_in_result: IntersectionTieInEdgeResult, alignment_ref: str) -> tuple[float, float, float] | None:
    target = str(alignment_ref or "").strip()
    for row in list(getattr(tie_in_result, "edge_rows", []) or []):
        if target and str(getattr(row, "alignment_ref", "") or "") != target:
            continue
        start = tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        end = tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        vector = (float(end[0]) - float(start[0]), float(end[1]) - float(start[1]), float(end[2]) - float(start[2]))
        if _xyz_length(vector) > 1.0e-9:
            return vector
    return None


def _intersection_curb_return_chord_points(
    center: tuple[float, float, float],
    primary_dir: tuple[float, float, float],
    secondary_dir: tuple[float, float, float],
    *,
    radius: float,
    primary_sign: float,
    secondary_sign: float,
    sample_count: int,
) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    count = max(int(sample_count), 2)
    denominator = max(count - 1, 1)
    for step in range(count):
        theta = (math.pi / 2.0) * (step / denominator)
        primary_scale = float(primary_sign) * float(radius) * math.cos(theta)
        secondary_scale = float(secondary_sign) * float(radius) * math.sin(theta)
        output.append(
            (
                center[0] + primary_dir[0] * primary_scale + secondary_dir[0] * secondary_scale,
                center[1] + primary_dir[1] * primary_scale + secondary_dir[1] * secondary_scale,
                center[2] + primary_dir[2] * primary_scale + secondary_dir[2] * secondary_scale,
            )
        )
    return output


def _intersection_tie_in_boundary_span(tie_in_rows: list[IntersectionBoundarySegmentRow]) -> float:
    points: list[tuple[float, float, float]] = []
    for row in tie_in_rows:
        points.append(tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)))
        points.append(tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)))
    if not points:
        return 0.0
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def _intersection_boundary_arc_endpoint_gap(
    chord_points: list[tuple[float, float, float]],
    tie_in_rows: list[IntersectionBoundarySegmentRow],
) -> float | None:
    endpoints: list[tuple[float, float, float]] = []
    for row in tie_in_rows:
        endpoints.append(tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)))
        endpoints.append(tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)))
    if len(chord_points) < 2 or not endpoints:
        return None
    gaps: list[float] = []
    for arc_point in (chord_points[0], chord_points[-1]):
        gaps.append(
            min(
                math.hypot(float(arc_point[0]) - float(endpoint[0]), float(arc_point[1]) - float(endpoint[1]))
                for endpoint in endpoints
            )
        )
    return max(gaps)


def _unit_xyz(vector: tuple[float, float, float]) -> tuple[float, float, float] | None:
    length = _xyz_length(vector)
    if length <= 1.0e-9:
        return None
    return (float(vector[0]) / length, float(vector[1]) / length, float(vector[2]) / length)


def _xyz_length(vector: tuple[float, float, float]) -> float:
    return math.sqrt(float(vector[0]) ** 2 + float(vector[1]) ** 2 + float(vector[2]) ** 2)


def _intersection_tie_in_section_pair(sections: list[object], target_station: float) -> tuple[object, object]:
    ordered = sorted(sections, key=lambda row: float(getattr(row, "station", 0.0) or 0.0))
    if not ordered:
        raise ValueError("sections are required")
    tolerance = 1.0e-6
    before = [row for row in ordered if float(getattr(row, "station", 0.0) or 0.0) < target_station - tolerance]
    after = [row for row in ordered if float(getattr(row, "station", 0.0) or 0.0) > target_station + tolerance]
    exact = [row for row in ordered if abs(float(getattr(row, "station", 0.0) or 0.0) - target_station) <= tolerance]
    if before and after:
        start = before[-1]
        end = after[0]
    elif before and exact:
        start = before[-1]
        end = exact[-1]
    elif exact and after:
        start = exact[0]
        end = after[0]
    else:
        start = before[-1] if before else ordered[0]
        end = after[0] if after else ordered[-1]
    if start is end and len(ordered) > 1:
        nearest = sorted(
            [row for row in ordered if row is not start],
            key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - target_station),
        )[0]
        if float(getattr(nearest, "station", 0.0) or 0.0) < float(getattr(start, "station", 0.0) or 0.0):
            start = nearest
        else:
            end = nearest
    return start, end


def _intersection_tie_in_point(section, side: str):
    points = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "fg_surface"
    ]
    if not points:
        return None
    side_matches = [
        point for point in points
        if str(getattr(point, "side", "") or "").strip().lower() == str(side or "").strip().lower()
        or str(getattr(point, "point_id", "") or "").strip().lower().endswith(f":{str(side or '').strip().lower()}")
    ]
    if side_matches:
        return side_matches[0]
    if side == "left":
        return max(points, key=_intersection_point_lateral_offset)
    return min(points, key=_intersection_point_lateral_offset)


def _intersection_point_lateral_offset(point) -> float:
    return float(
        getattr(point, "lateral_offset", getattr(point, "offset", 0.0)) or 0.0
    )


def _point_xyz_tuple(point) -> tuple[float, float, float]:
    return (
        float(getattr(point, "x", 0.0) or 0.0),
        float(getattr(point, "y", 0.0) or 0.0),
        float(getattr(point, "z", 0.0) or 0.0),
    )


def _diagnostics_include_error(diagnostics: list[str] | tuple[str, ...]) -> bool:
    for value in list(diagnostics or []):
        text = str(value or "").strip().lower()
        if text and not text.startswith("warning:"):
            return True
    return False


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"


def _intersection_patch_sections(applied_section_set, prerequisite: IntersectionPatchPrerequisiteResult) -> list[object]:
    control_refs = set(str(value or "") for value in list(getattr(prerequisite, "control_region_refs", ()) or ()) if str(value or ""))
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    return [
        section for section in _station_ordered_applied_sections(applied_section_set)
        if (
            (intersection_id and str(getattr(section, "active_intersection_id", "") or "") == intersection_id)
            or (str(getattr(section, "region_id", "") or "") in control_refs)
        )
    ]


def _intersection_drainage_element_rows(drainage_model, prerequisite: IntersectionPatchPrerequisiteResult) -> list[object]:
    return list(_intersection_drainage_coverage(drainage_model, prerequisite).get("candidate_rows", []) or [])


def _intersection_drainage_coverage(
    drainage_model,
    prerequisite: IntersectionPatchPrerequisiteResult,
    *,
    low_point_station: float | None = None,
) -> dict[str, object]:
    if drainage_model is None:
        return {"candidate_rows": [], "ready_rows": [], "diagnostics": ["drainage_model_missing"]}
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    control_refs = set(str(value or "") for value in list(getattr(prerequisite, "control_region_refs", ()) or ()) if str(value or ""))
    candidate_rows: list[object] = []
    ready_rows: list[object] = []
    diagnostics: list[str] = []
    for row in list(getattr(drainage_model, "element_rows", []) or []):
        row_intersection = str(getattr(row, "intersection_ref", "") or "").strip()
        row_region = str(getattr(row, "region_ref", "") or "").strip()
        owns_intersection = bool(intersection_id and row_intersection == intersection_id)
        owns_control_region = bool(row_region and row_region in control_refs)
        if not (owns_intersection or owns_control_region):
            continue
        candidate_rows.append(row)
        if low_point_station is None or _drainage_element_covers_station(row, float(low_point_station)):
            ready_rows.append(row)
        else:
            diagnostics.append(
                "drainage_element_outside_low_point_station_range:"
                f"{str(getattr(row, 'drainage_element_id', '') or '')}:"
                f"{float(getattr(row, 'station_start', 0.0) or 0.0):.3f}-"
                f"{float(getattr(row, 'station_end', 0.0) or 0.0):.3f}"
            )
    if candidate_rows and not ready_rows and low_point_station is not None:
        diagnostics.append(f"intersection_low_point_station_uncovered:{float(low_point_station):.3f}")
    if not candidate_rows:
        diagnostics.append("intersection_drainage_element_missing")
    return {"candidate_rows": candidate_rows, "ready_rows": ready_rows, "diagnostics": diagnostics}


def _drainage_element_covers_station(row, station: float, *, tolerance: float = 1.0e-6) -> bool:
    start = float(getattr(row, "station_start", 0.0) or 0.0)
    end = float(getattr(row, "station_end", 0.0) or 0.0)
    return min(start, end) - tolerance <= float(station) <= max(start, end) + tolerance


def _active_ditch_drainage_rows(drainage_model, *, region_model, station: float) -> list[object]:
    if drainage_model is None:
        return []
    if region_model is not None:
        try:
            context = StationContextResolver().resolve(
                region_model=region_model,
                drainage_model=drainage_model,
                station=float(station),
            )
            rows = list(getattr(context, "active_drainage_elements", []) or [])
            return [row for row in rows if _is_ditch_drainage_element(row)]
        except Exception:
            pass
    output: list[object] = []
    for row in list(getattr(drainage_model, "element_rows", []) or []):
        if not _is_ditch_drainage_element(row):
            continue
        try:
            start = float(getattr(row, "station_start", 0.0) or 0.0)
            end = float(getattr(row, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        if min(start, end) <= float(station) <= max(start, end):
            output.append(row)
    return output


def _is_ditch_drainage_element(row) -> bool:
    kind = str(getattr(row, "element_kind", "") or "").strip().lower()
    return kind in {"ditch", "lined_ditch", "lined-ditch", "gutter", "swale", "channel"}


def _drainage_source_surface_mismatch_notes(active_ditch_rows: list[object], ditch_points: list[object]) -> list[str]:
    if not active_ditch_rows:
        return []
    point_data = _ditch_point_context_by_side(ditch_points)
    notes: list[str] = []
    for row in active_ditch_rows:
        drainage_ref = str(getattr(row, "drainage_element_id", "") or "").strip()
        component_ref = str(getattr(row, "assembly_component_ref", "") or "").strip()
        for side in _drainage_row_sides(row):
            data = point_data.get(side, {})
            point_count = int(data.get("point_count", 0) or 0)
            drainage_refs = set(data.get("drainage_refs", []) or [])
            component_refs = set(data.get("component_refs", []) or [])
            if point_count <= 0:
                notes.append(f"missing_side={side};drainage_ref={drainage_ref or '-'}")
                continue
            if drainage_ref and drainage_ref not in drainage_refs:
                notes.append(f"missing_drainage_ref={drainage_ref};side={side}")
            if component_ref and component_ref not in component_refs:
                notes.append(f"component_mismatch={component_ref};side={side}")
    return _unique_refs(notes)


def _ditch_point_context_by_side(ditch_points: list[object]) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for point in list(ditch_points or []):
        side = _long_drainage_side(_drainage_point_side(point))
        if side not in {"left", "right"}:
            continue
        data = output.setdefault(side, {"point_count": 0, "drainage_refs": [], "component_refs": []})
        data["point_count"] = int(data.get("point_count", 0) or 0) + 1
        drainage_ref = str(getattr(point, "drainage_ref", "") or "").strip()
        component_ref = str(getattr(point, "component_ref", "") or "").strip()
        if drainage_ref:
            data.setdefault("drainage_refs", []).append(drainage_ref)
        if component_ref:
            data.setdefault("component_refs", []).append(component_ref)
    for data in output.values():
        data["drainage_refs"] = _unique_refs(list(data.get("drainage_refs", []) or []))
        data["component_refs"] = _unique_refs(list(data.get("component_refs", []) or []))
    return output


def _drainage_row_sides(row) -> list[str]:
    side = str(getattr(row, "side", "") or "").strip().lower()
    if side == "both":
        return ["left", "right"]
    if side in {"left", "right"}:
        return [side]
    ref_text = " ".join(
        [
            str(getattr(row, "drainage_element_id", "") or ""),
            str(getattr(row, "assembly_component_ref", "") or ""),
        ]
    ).lower()
    if "left" in ref_text or ":l" in ref_text or "-l" in ref_text:
        return ["left"]
    if "right" in ref_text or ":r" in ref_text or "-r" in ref_text:
        return ["right"]
    return []


def _long_drainage_side(side: str) -> str:
    text = str(side or "").strip().lower()
    if text in {"l", "left"}:
        return "left"
    if text in {"r", "right"}:
        return "right"
    return text


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


def _drainage_flow_connected_elements(flow_row, element_by_id: dict[str, object]) -> list[object]:
    elements: list[object] = []
    seen: set[str] = set()
    for ref in (
        str(getattr(flow_row, "from_element_ref", "") or ""),
        str(getattr(flow_row, "to_element_ref", "") or ""),
        str(getattr(flow_row, "outlet_ref", "") or ""),
    ):
        if not ref or ref in seen:
            continue
        seen.add(ref)
        element = element_by_id.get(ref)
        if element is not None:
            elements.append(element)
    return elements


def _drainage_flow_structure_refs(flow_row, connected_elements: list[object]) -> list[str]:
    refs: list[str] = []
    for element in list(connected_elements or []):
        ref = str(getattr(element, "structure_ref", "") or "").strip()
        if ref:
            refs.append(ref)
    outlet_ref = str(getattr(flow_row, "outlet_ref", "") or "").strip()
    if outlet_ref.startswith("structure:"):
        refs.append(outlet_ref)
    return _unique_text_values(refs)


def _drainage_flow_station_range(
    flow_row,
    connected_elements: list[object],
    structure_by_id: dict[str, object],
) -> tuple[float, float] | None:
    stations: list[float] = []
    for element in list(connected_elements or []):
        stations.extend(
            [
                float(getattr(element, "station_start", 0.0) or 0.0),
                float(getattr(element, "station_end", 0.0) or 0.0),
            ]
        )
    for ref in _drainage_flow_structure_refs(flow_row, connected_elements):
        structure = structure_by_id.get(ref)
        placement = getattr(structure, "placement", None)
        if placement is None:
            continue
        stations.extend(
            [
                float(getattr(placement, "station_start", 0.0) or 0.0),
                float(getattr(placement, "station_end", 0.0) or 0.0),
            ]
        )
    if not stations:
        return None
    return min(stations), max(stations)


def _drainage_flow_row_highlight_mode(document, route_ref: str) -> str:
    if document is None or not str(route_ref or ""):
        return "missing"
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    sections = _station_ordered_applied_sections(applied)
    segments = _drainage_flow_connection_point_segments(
        document,
        sections,
        {"flow_route_id": str(route_ref or "")},
    )
    return "connection_point_pipe" if segments else "station_span"


def _unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _display_source_ref(value: object) -> str:
    text = str(value or "").strip()
    if ":" not in text:
        return text
    return text.split(":", 1)[1]


def _create_drainage_flow_review_highlight(*, document=None, rows: list[dict[str, object]] | None = None):
    if document is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    sections = sorted(list(getattr(applied, "sections", []) or []), key=lambda section: _section_station(section)) if applied is not None else []
    shapes: list[object] = []
    route_refs: list[str] = []
    structure_refs: list[str] = []
    connection_point_refs: list[str] = []
    pipe_segment_count = 0
    station_span_count = 0
    for row in list(rows or []):
        route_ref = str(row.get("flow_route_id", "") or "")
        if route_ref:
            route_refs.append(route_ref)
        for ref in str(row.get("structure_refs", "") or "").split(","):
            if ref.strip():
                structure_refs.append(ref.strip())
        point_segments = _drainage_flow_connection_point_segments(document, sections, row)
        if point_segments:
            for segment in point_segments:
                first, second, first_ref, second_ref, radius = segment
                connection_point_refs.extend([first_ref, second_ref])
                try:
                    shapes.append(_make_drainage_pipe_segment_shape(Part, AppModule, first, second, radius))
                    pipe_segment_count += 1
                except Exception:
                    try:
                        shapes.append(Part.makeLine(AppModule.Vector(*first), AppModule.Vector(*second)))
                        pipe_segment_count += 1
                    except Exception:
                        pass
            continue
        start, end = _drainage_flow_row_station_range(row)
        if start is None or end is None:
            continue
        points = _drainage_flow_highlight_points(sections, start, end)
        for first, second in zip(points[:-1], points[1:]):
            try:
                shapes.append(Part.makeLine(AppModule.Vector(*first), AppModule.Vector(*second)))
                station_span_count += 1
            except Exception:
                pass
    if not shapes:
        return None
    obj = document.getObject("ReviewIssueDrainageFlowRoutes")
    if obj is None:
        obj = document.addObject("Part::Feature", "ReviewIssueDrainageFlowRoutes")
    try:
        obj.Shape = Part.makeCompound(shapes)
        obj.Label = "Drainage Flow Highlight"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_review_issue")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "drainage_flow")
    display_mode = "drainage_flow_pipe_segments" if pipe_segment_count else "drainage_flow_station_span"
    _set_preview_property(obj, "DisplayMode", display_mode)
    _set_preview_string_list_property(obj, "FlowRouteRefs", _unique_text_values(route_refs))
    _set_preview_string_list_property(obj, "StructureRefs", _unique_text_values(structure_refs))
    _set_preview_string_list_property(obj, "ConnectionPointRefs", _unique_text_values(connection_point_refs))
    _set_preview_integer_property(obj, "MarkerCount", len(shapes))
    _set_preview_integer_property(obj, "PipeSegmentCount", pipe_segment_count)
    _set_preview_integer_property(obj, "StationSpanCount", station_span_count)
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = (1.00, 0.68, 0.10)
            vobj.PointColor = (1.00, 0.68, 0.10)
            vobj.LineColor = (1.00, 0.68, 0.10)
            vobj.LineWidth = 7.0
            vobj.PointSize = 9.0
            vobj.Transparency = 0
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(document), obj)
    except Exception:
        pass
    return obj


def _drainage_flow_row_station_range(row: dict[str, object]) -> tuple[float | None, float | None]:
    try:
        start = float(row.get("station_start", "") if row.get("station_start", "") != "" else "")
        end = float(row.get("station_end", "") if row.get("station_end", "") != "" else "")
        return min(start, end), max(start, end)
    except Exception:
        return None, None


def _drainage_flow_connection_point_segments(
    document,
    sections: list[object],
    row: dict[str, object],
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, float]]:
    drainage_model = to_drainage_model(find_v1_drainage_model(document))
    structure_model = to_structure_model(find_v1_structure_model(document))
    if drainage_model is None or structure_model is None:
        return []
    route_ref = str(row.get("flow_route_id", "") or "")
    flow_row = next(
        (
            candidate
            for candidate in list(getattr(drainage_model, "flow_route_rows", []) or [])
            if str(getattr(candidate, "flow_route_id", "") or "") == route_ref
        ),
        None,
    )
    if flow_row is None:
        return []
    element_by_id = {
        str(getattr(element, "drainage_element_id", "") or ""): element
        for element in list(getattr(drainage_model, "element_rows", []) or [])
    }
    point_by_id = {
        str(getattr(point, "connection_point_id", "") or ""): point
        for point in list(getattr(structure_model, "connection_point_rows", []) or [])
    }
    points_by_structure: dict[str, list[object]] = {}
    for point in list(getattr(structure_model, "connection_point_rows", []) or []):
        structure_ref = str(getattr(point, "structure_ref", "") or "")
        if structure_ref:
            points_by_structure.setdefault(structure_ref, []).append(point)
    chain_refs = [
        str(getattr(flow_row, "from_element_ref", "") or ""),
        str(getattr(flow_row, "to_element_ref", "") or ""),
        str(getattr(flow_row, "outlet_ref", "") or ""),
    ]
    chain_refs = [ref for ref in chain_refs if ref]
    if len(chain_refs) < 2:
        return []
    resolved: list[tuple[object, str]] = []
    for index, ref in enumerate(chain_refs):
        direction = "out" if index == 0 else "in"
        point = _drainage_flow_chain_connection_point(
            ref,
            element_by_id=element_by_id,
            point_by_id=point_by_id,
            points_by_structure=points_by_structure,
            direction=direction,
        )
        if point is None:
            return []
        resolved.append((point, str(getattr(point, "connection_point_id", "") or "")))
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float], str, str, float]] = []
    for (first_point, first_ref), (second_point, second_ref) in zip(resolved[:-1], resolved[1:]):
        first_xyz = _drainage_connection_point_xyz(sections, first_point)
        second_xyz = _drainage_connection_point_xyz(sections, second_point)
        if first_xyz is None or second_xyz is None:
            continue
        radius = _drainage_pipe_segment_radius(first_point, second_point)
        segments.append((first_xyz, second_xyz, first_ref, second_ref, radius))
    return segments


def _drainage_flow_chain_connection_point(
    ref: str,
    *,
    element_by_id: dict[str, object],
    point_by_id: dict[str, object],
    points_by_structure: dict[str, list[object]],
    direction: str,
):
    text = str(ref or "").strip()
    if not text:
        return None
    if text.startswith("connection:"):
        return point_by_id.get(text)
    if text.startswith("structure:"):
        return _preferred_structure_connection_point(text, points_by_structure, direction=direction)
    element = element_by_id.get(text)
    if element is None:
        return None
    point_ref = str(getattr(element, "connection_point_ref", "") or "").strip()
    if point_ref:
        point = point_by_id.get(point_ref)
        if point is not None:
            return point
    structure_ref = str(getattr(element, "structure_ref", "") or "").strip()
    if structure_ref:
        return _preferred_structure_connection_point(structure_ref, points_by_structure, direction=direction)
    return None


def _preferred_structure_connection_point(
    structure_ref: str,
    points_by_structure: dict[str, list[object]],
    *,
    direction: str,
):
    points = list(points_by_structure.get(str(structure_ref or ""), []) or [])
    if not points:
        return None
    role_priority = (
        ["pipe_out", "downstream", "discharge", "outlet", "inlet", "pipe_in", "upstream"]
        if direction == "out"
        else ["pipe_in", "upstream", "inlet", "pipe_out", "downstream", "discharge", "outlet"]
    )
    by_role = {str(getattr(point, "point_role", "") or "").strip().lower(): point for point in points}
    for role in role_priority:
        if role in by_role:
            return by_role[role]
    return sorted(points, key=lambda point: int(getattr(point, "connection_order", 0) or 0))[0]


def _drainage_connection_point_xyz(
    sections: list[object],
    point,
    *,
    z_offset: float = 1.15,
) -> tuple[float, float, float] | None:
    station = float(getattr(point, "station", 0.0) or 0.0)
    frame = _drainage_flow_station_frame(sections, station)
    if frame is None:
        return None
    try:
        import math as _math

        offset = float(getattr(point, "offset", 0.0) or 0.0)
        angle_rad = _math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        x = float(getattr(frame, "x", 0.0) or 0.0) - _math.sin(angle_rad) * offset
        y = float(getattr(frame, "y", 0.0) or 0.0) + _math.cos(angle_rad) * offset
        z = float(getattr(frame, "z", 0.0) or 0.0) + float(z_offset or 0.0)
        return x, y, z
    except Exception:
        return (
            float(getattr(frame, "x", 0.0) or 0.0),
            float(getattr(frame, "y", 0.0) or 0.0),
            float(getattr(frame, "z", 0.0) or 0.0) + float(z_offset or 0.0),
        )


def _drainage_flow_station_frame(sections: list[object], station: float):
    if not sections:
        return None
    ordered = sorted(list(sections or []), key=lambda section: _section_station(section))
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = _section_station(first)
        second_station = _section_station(second)
        if min(first_station, second_station) - 1.0e-9 <= float(station) <= max(first_station, second_station) + 1.0e-9:
            first_frame = getattr(first, "frame", None)
            second_frame = getattr(second, "frame", None)
            if first_frame is None:
                return second_frame
            if second_frame is None:
                return first_frame
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (float(station) - first_station) / (second_station - first_station)
            return replace(
                first_frame,
                station=float(station),
                x=_lerp_value(getattr(first_frame, "x", 0.0), getattr(second_frame, "x", 0.0), ratio),
                y=_lerp_value(getattr(first_frame, "y", 0.0), getattr(second_frame, "y", 0.0), ratio),
                z=_lerp_value(getattr(first_frame, "z", 0.0), getattr(second_frame, "z", 0.0), ratio),
                tangent_direction_deg=_lerp_value(
                    getattr(first_frame, "tangent_direction_deg", 0.0),
                    getattr(second_frame, "tangent_direction_deg", 0.0),
                    ratio,
                ),
            )
    nearest = min(ordered, key=lambda section: abs(_section_station(section) - float(station)))
    return getattr(nearest, "frame", None)


def _drainage_pipe_segment_radius(first_point, second_point) -> float:
    diameters = [
        float(getattr(point, "diameter", 0.0) or 0.0)
        for point in (first_point, second_point)
        if float(getattr(point, "diameter", 0.0) or 0.0) > 0.0
    ]
    if diameters:
        return max(0.08, min(sum(diameters) / len(diameters) * 0.5, 1.5))
    sizes = [
        max(float(getattr(point, "width", 0.0) or 0.0), float(getattr(point, "height", 0.0) or 0.0))
        for point in (first_point, second_point)
    ]
    size = max(sizes or [0.0])
    return max(0.12, min(float(size or 0.6) * 0.18, 1.0))


def _make_drainage_pipe_segment_shape(part_module, app_module, first: tuple[float, float, float], second: tuple[float, float, float], radius: float):
    start = app_module.Vector(*first)
    end = app_module.Vector(*second)
    vector = end.sub(start)
    length = float(getattr(vector, "Length", 0.0) or 0.0)
    if length <= 1.0e-6:
        return part_module.makeSphere(float(radius or 0.2), start)
    return part_module.makeCylinder(float(radius or 0.2), length, start, vector)


def _drainage_flow_highlight_points(sections: list[object], station_start: float, station_end: float) -> list[tuple[float, float, float]]:
    stations = [float(station_start)]
    for section in list(sections or []):
        station = _section_station(section)
        if min(station_start, station_end) < station < max(station_start, station_end):
            stations.append(station)
    stations.append(float(station_end))
    points = [
        point
        for point in (_drainage_flow_station_point(sections, station) for station in stations)
        if point is not None
    ]
    output: list[tuple[float, float, float]] = []
    for point in points:
        if not output or point != output[-1]:
            output.append(point)
    return output


def _drainage_flow_station_point(sections: list[object], station: float, *, z_offset: float = 1.05) -> tuple[float, float, float] | None:
    return _surface_transition_span_marker_point(sections, float(station), z_offset=z_offset)


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
    ditch_points = _drainage_review_row_ditch_points(document, row)
    if ditch_points:
        obj = _create_drainage_review_highlight_compound(
            document=document,
            object_name=name,
            label=f"Drainage Highlight - STA {float(row.get('station', 0.0) or 0.0):.3f}" if row.get("station", "") != "" else "Drainage Highlight",
            ditch_points=ditch_points,
            color=color,
        )
    else:
        is_suggested_inlet = str(row.get("marker_kind", "") or "") == "suggested_inlet"
        marker_label = str(row.get("marker_label", "") or "").strip()
        obj = _create_drainage_review_point_marker(
            document=document,
            object_name=name,
            label=marker_label or (f"Drainage Diagnostic - STA {float(row.get('station', 0.0) or 0.0):.3f}" if row.get("station", "") != "" else "Drainage Diagnostic"),
            point=point,
            color=color,
            suggested_inlet=is_suggested_inlet,
        )
    if obj is None:
        return None
    issue_kind = "intersection_suggested_inlet" if str(row.get("marker_kind", "") or "") == "suggested_inlet" else "drainage_diagnostic"
    _set_preview_property(obj, "IssueKind", issue_kind)
    _set_preview_property(obj, "IssueStation", "" if row.get("station", "") == "" else f"{float(row.get('station', 0.0) or 0.0):.3f}")
    _set_preview_property(obj, "IssueStatus", status)
    _set_preview_property(obj, "IssueReason", str(row.get("notes", "") or ""))
    if issue_kind == "intersection_suggested_inlet":
        _set_preview_property(obj, "SuggestedInletReviewOnly", "Yes")
        _set_preview_property(obj, "IntersectionId", str(row.get("intersection_id", "") or ""))
        _set_preview_property(obj, "ControlRegionRefs", str(row.get("control_region_refs", "") or ""))
        _set_preview_float_property(obj, "SuggestedInletX", point[0])
        _set_preview_float_property(obj, "SuggestedInletY", point[1])
        _set_preview_float_property(obj, "SuggestedInletZ", point[2])
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(find_project(document), obj)
    except Exception:
        pass
    return obj


def _drainage_review_row_ditch_points(document, row: dict[str, object]) -> list[object]:
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    if applied is None:
        return []
    section_id = str(row.get("section_id", "") or "")
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied, "sections", []) or [])
    }
    section = sections.get(section_id)
    if section is None:
        return []
    return [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    ]


def _create_drainage_review_highlight_compound(
    *,
    document,
    object_name: str,
    label: str,
    ditch_points: list[object],
    color: tuple[float, float, float],
):
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    obj = document.getObject(object_name)
    shapes = []
    for side in ("L", "R", ""):
        points = [
            point
            for point in list(ditch_points or [])
            if _drainage_point_side(point) == side
        ]
        points.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
        if len(points) >= 2:
            vectors = [
                AppModule.Vector(
                    float(getattr(point, "x", 0.0) or 0.0),
                    float(getattr(point, "y", 0.0) or 0.0),
                    float(getattr(point, "z", 0.0) or 0.0),
                )
                for point in points
            ]
            for start, end in zip(vectors[:-1], vectors[1:]):
                shapes.append(Part.makeLine(start, end))
        elif len(points) == 1:
            shapes.extend(_drainage_point_cross_shapes(Part, AppModule, points[0], radius=0.25))
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
    _set_preview_property(obj, "IssueKind", "drainage_diagnostic")
    _set_preview_property(obj, "DisplayMode", "drainage_highlight")
    _set_preview_integer_property(obj, "MarkerCount", len(list(ditch_points or [])))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = color
            vobj.PointColor = color
            vobj.LineColor = color
            vobj.LineWidth = 8.0
            vobj.PointSize = 8.0
            vobj.Transparency = 0
    except Exception:
        pass
    return obj


def _create_drainage_review_point_marker(
    *,
    document,
    object_name: str,
    label: str,
    point: tuple[float, float, float],
    color: tuple[float, float, float],
    suggested_inlet: bool = False,
):
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    obj = document.getObject(object_name)
    if suggested_inlet:
        shapes = _point_sphere_marker_shapes(Part, AppModule, point, radius=0.45)
    else:
        shapes = _point_cross_shapes(Part, AppModule, point, radius=0.35)
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
    _set_preview_property(obj, "IssueKind", "intersection_suggested_inlet" if suggested_inlet else "drainage_diagnostic")
    _set_preview_property(obj, "DisplayMode", "suggested_inlet_marker" if suggested_inlet else "drainage_point_marker")
    _set_preview_integer_property(obj, "MarkerCount", 1)
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = color
            vobj.PointColor = color
            vobj.LineColor = color
            vobj.LineWidth = 5.0
            vobj.PointSize = 7.0
            vobj.Transparency = 5 if suggested_inlet else 0
    except Exception:
        pass
    return obj


def _point_sphere_marker_shapes(Part, AppModule, point: tuple[float, float, float], *, radius: float) -> list[object]:
    x, y, z = point
    r = max(float(radius or 0.0), 0.05)
    center = AppModule.Vector(float(x), float(y), float(z) + r)
    shapes = []
    try:
        shapes.append(Part.makeSphere(r, center))
    except Exception:
        pass
    try:
        base = AppModule.Vector(float(x), float(y), float(z))
        top = AppModule.Vector(float(x), float(y), float(z) + (r * 1.8))
        shapes.append(Part.makeLine(base, top))
    except Exception:
        pass
    if not shapes:
        return _point_cross_shapes(Part, AppModule, point, radius=r)
    return shapes


def _drainage_point_cross_shapes(Part, AppModule, point, *, radius: float) -> list[object]:
    return _point_cross_shapes(
        Part,
        AppModule,
        (
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0),
        ),
        radius=radius,
    )


def _point_cross_shapes(Part, AppModule, point: tuple[float, float, float], *, radius: float) -> list[object]:
    x, y, z = point
    r = max(float(radius or 0.0), 0.05)
    center = AppModule.Vector(float(x), float(y), float(z))
    vectors = [
        (AppModule.Vector(float(x) - r, float(y), float(z)), AppModule.Vector(float(x) + r, float(y), float(z))),
        (AppModule.Vector(float(x), float(y) - r, float(z)), AppModule.Vector(float(x), float(y) + r, float(z))),
        (AppModule.Vector(float(x), float(y), float(z) - r), AppModule.Vector(float(x), float(y), float(z) + r)),
    ]
    shapes = []
    for start, end in vectors:
        try:
            shapes.append(Part.makeLine(start, end))
        except Exception:
            pass
    if not shapes:
        try:
            shapes.append(Part.Vertex(center))
        except Exception:
            pass
    return shapes


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


def _intersection_patch_diagnostic_notes(prerequisite: IntersectionPatchPrerequisiteResult) -> str:
    diagnostics = list(getattr(prerequisite, "diagnostic_rows", ()) or ())
    if diagnostics:
        return "; ".join(str(value or "") for value in diagnostics[:4] if str(value or "").strip())
    return "Intersection Surface Patch prerequisites are not available."


def _create_corridor_intersection_tie_in_edge_preview(document, tie_in_result: IntersectionTieInEdgeResult, *, project=None):
    """Create visible linework for intersection tie-in edge candidates."""

    if document is None:
        return None
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    object_name = "V1CorridorIntersectionTieInEdgePreview"
    obj = document.getObject(object_name)
    edge_rows = list(getattr(tie_in_result, "edge_rows", []) or [])
    shapes = []
    refs: list[str] = []
    statuses: list[str] = []
    for row in edge_rows:
        start = tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        end = tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0))
        if len(start) < 3 or len(end) < 3:
            continue
        try:
            start_vec = AppModule.Vector(float(start[0]), float(start[1]), float(start[2]))
            end_vec = AppModule.Vector(float(end[0]), float(end[1]), float(end[2]))
            if start_vec.distanceToPoint(end_vec) <= 1.0e-9:
                continue
            shapes.append(Part.makeLine(start_vec, end_vec))
            refs.append(str(getattr(row, "tie_in_edge_id", "") or ""))
            statuses.append(str(getattr(row, "status", "") or ""))
        except Exception:
            continue
    if not shapes:
        if obj is not None:
            try:
                document.removeObject(obj.Name)
            except Exception:
                pass
        return None
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = "Intersection Tie-in Edges"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_intersection_tie_in_edge_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorIntersectionTieInEdgePreview")
    _set_preview_property(obj, "IntersectionId", str(getattr(tie_in_result, "intersection_id", "") or ""))
    _set_preview_property(obj, "PreviewStatus", str(getattr(tie_in_result, "status", "") or ""))
    _set_preview_property(obj, "BoundaryMode", str(getattr(tie_in_result, "boundary_mode", "") or "tie_in_edges"))
    _set_preview_integer_property(obj, "TieInEdgeCount", int(getattr(tie_in_result, "edge_count", 0) or 0))
    _set_preview_integer_property(obj, "DisplayedEdgeCount", len(shapes))
    _set_preview_string_list_property(obj, "TieInEdgeRefs", refs)
    _set_preview_string_list_property(obj, "TieInEdgeStatuses", statuses)
    _set_preview_string_list_property(obj, "TieInEdgeDiagnostics", [str(value or "") for value in list(getattr(tie_in_result, "diagnostic_rows", []) or [])])
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = (0.0, 0.85, 1.0)
            vobj.LineColor = (0.0, 0.85, 1.0)
            vobj.PointColor = (0.0, 0.85, 1.0)
            vobj.LineWidth = 5.0
            vobj.Transparency = 0
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    return obj


def _create_corridor_intersection_boundary_segment_preview(
    document,
    boundary_result: IntersectionBoundarySegmentResult,
    *,
    project=None,
):
    """Create visible linework for refined intersection boundary segment candidates."""

    if document is None:
        return None
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    object_name = "V1CorridorIntersectionBoundarySegmentPreview"
    obj = document.getObject(object_name)
    shapes = []
    refs: list[str] = []
    kinds: list[str] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        segment_kind = str(getattr(row, "segment_kind", "") or "")
        points_xyz = list(getattr(row, "chord_points_xyz", ()) or ())
        if segment_kind != "arc" or len(points_xyz) < 2:
            points_xyz = [
                tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
                tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
            ]
        vectors = []
        for point in points_xyz:
            if len(point) < 3:
                continue
            try:
                vectors.append(AppModule.Vector(float(point[0]), float(point[1]), float(point[2])))
            except Exception:
                continue
        if len(vectors) < 2:
            continue
        try:
            if segment_kind == "arc":
                shapes.append(Part.makePolygon(vectors))
            else:
                shapes.append(Part.makeLine(vectors[0], vectors[-1]))
            refs.append(str(getattr(row, "boundary_segment_id", "") or ""))
            kinds.append(segment_kind)
        except Exception:
            continue
    if not shapes:
        if obj is not None:
            try:
                document.removeObject(obj.Name)
            except Exception:
                pass
        return None
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = "Intersection Boundary Segments"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_intersection_boundary_segment_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorIntersectionBoundarySegmentPreview")
    _set_preview_property(obj, "IntersectionId", str(getattr(boundary_result, "intersection_id", "") or ""))
    _set_preview_property(obj, "PreviewStatus", str(getattr(boundary_result, "status", "") or ""))
    _set_preview_property(obj, "BoundaryMode", str(getattr(boundary_result, "boundary_mode", "") or ""))
    _set_preview_integer_property(obj, "BoundarySegmentCount", int(getattr(boundary_result, "segment_count", 0) or 0))
    _set_preview_integer_property(obj, "DisplayedSegmentCount", len(shapes))
    _set_preview_integer_property(obj, "TieInSegmentCount", int(getattr(boundary_result, "tie_in_segment_count", 0) or 0))
    _set_preview_integer_property(obj, "ArcSegmentCount", int(getattr(boundary_result, "arc_segment_count", 0) or 0))
    _set_preview_string_list_property(obj, "BoundarySegmentRefs", refs)
    _set_preview_string_list_property(obj, "BoundarySegmentKinds", kinds)
    _set_preview_string_list_property(obj, "BoundaryDiagnostics", [str(value or "") for value in list(getattr(boundary_result, "diagnostic_rows", []) or [])])
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = (1.0, 0.72, 0.05)
            vobj.LineColor = (1.0, 0.72, 0.05)
            vobj.PointColor = (1.0, 0.72, 0.05)
            vobj.LineWidth = 6.0
            vobj.Transparency = 0
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    return obj


def _create_corridor_intersection_exclusion_zone_preview(
    document,
    patch_boundary_result: IntersectionPatchBoundaryResult,
    *,
    project=None,
):
    """Create visible linework for the Build Parametric intersection exclusion zone."""

    if document is None:
        return None
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    object_name = "V1CorridorIntersectionExclusionZonePreview"
    obj = document.getObject(object_name)
    points = [
        row for row in list(getattr(patch_boundary_result, "point_rows", []) or [])
        if str(getattr(row, "ring_role", "") or "outer") == "outer"
    ]
    if len(points) < 3:
        if obj is not None:
            try:
                document.removeObject(obj.Name)
            except Exception:
                pass
        return None
    vectors = [
        AppModule.Vector(float(getattr(row, "x", 0.0) or 0.0), float(getattr(row, "y", 0.0) or 0.0), float(getattr(row, "z", 0.0) or 0.0))
        for row in points
    ]
    vectors.append(vectors[0])
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makePolygon(vectors)
        obj.Label = "Intersection Exclusion Zone"
    except Exception:
        return obj
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_intersection_exclusion_zone_preview")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorIntersectionExclusionZonePreview")
    _set_preview_property(obj, "IntersectionId", str(getattr(patch_boundary_result, "intersection_id", "") or ""))
    _set_preview_property(obj, "ExclusionStatus", str(getattr(patch_boundary_result, "status", "") or ""))
    _set_preview_integer_property(obj, "BoundaryPointCount", len(points))
    _set_preview_float_property(obj, "PolygonArea", float(getattr(patch_boundary_result, "polygon_area", 0.0) or 0.0))
    _set_preview_integer_property(obj, "RingCount", int(getattr(patch_boundary_result, "ring_count", 0) or 0))
    _set_preview_integer_property(obj, "HoleRingCount", int(getattr(patch_boundary_result, "hole_ring_count", 0) or 0))
    _set_preview_integer_property(obj, "IslandRingCount", int(getattr(patch_boundary_result, "island_ring_count", 0) or 0))
    _set_preview_string_list_property(obj, "ExclusionDiagnostics", [str(value or "") for value in list(getattr(patch_boundary_result, "diagnostic_rows", []) or [])])
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = (1.0, 0.25, 0.08)
            vobj.LineColor = (1.0, 0.25, 0.08)
            vobj.PointColor = (1.0, 0.25, 0.08)
            vobj.LineWidth = 5.0
            vobj.Transparency = 0
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project or find_project(document), obj)
    except Exception:
        pass
    return obj


def _attach_intersection_exclusion_zone_metadata(obj, document, *, exclusion_preview=None) -> None:
    if obj is None or document is None:
        return
    exclusion = exclusion_preview or document.getObject("V1CorridorIntersectionExclusionZonePreview")
    if exclusion is None:
        return
    _set_preview_property(obj, "IntersectionExclusionZoneRef", str(getattr(exclusion, "Name", "") or ""))
    _set_preview_property(obj, "IntersectionExclusionZoneStatus", str(getattr(exclusion, "ExclusionStatus", "") or ""))
    _set_preview_integer_property(obj, "IntersectionExclusionZonePointCount", int(getattr(exclusion, "BoundaryPointCount", 0) or 0))
    _set_preview_float_property(obj, "IntersectionExclusionZoneArea", float(getattr(exclusion, "PolygonArea", 0.0) or 0.0))
    _set_preview_integer_property(obj, "IntersectionExclusionZoneHoleRingCount", int(getattr(exclusion, "HoleRingCount", 0) or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionZoneIslandRingCount", int(getattr(exclusion, "IslandRingCount", 0) or 0))


def _attach_intersection_exclusion_clip_quality(obj, surface) -> None:
    if obj is None or surface is None:
        return
    status = _tin_quality_text(surface, "intersection_exclusion_status")
    if status:
        _set_preview_property(obj, "IntersectionExclusionClipStatus", status)
    method = _tin_quality_text(surface, "intersection_exclusion_clip_method")
    if method:
        _set_preview_property(obj, "IntersectionExclusionClipMethod", method)
    boundary_source = _tin_quality_text(surface, "intersection_exclusion_boundary_source")
    if boundary_source:
        _set_preview_property(obj, "IntersectionExclusionBoundarySource", boundary_source)
    boundary_strategy = _tin_quality_text(surface, "intersection_exclusion_boundary_strategy")
    if boundary_strategy:
        _set_preview_property(obj, "IntersectionExclusionBoundaryStrategy", boundary_strategy)
    _set_preview_integer_property(obj, "IntersectionExclusionPracticalBoundaryAligned", int(_tin_quality_float(surface, "intersection_exclusion_practical_boundary_aligned") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionClippedTriangleCount", int(_tin_quality_float(surface, "intersection_exclusion_clipped_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionKeptTriangleCount", int(_tin_quality_float(surface, "intersection_exclusion_kept_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionBoundaryCrossingTriangleCount", int(_tin_quality_float(surface, "intersection_exclusion_boundary_crossing_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionExactCutCandidateCount", int(_tin_quality_float(surface, "intersection_exclusion_exact_cut_candidate_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionExactCutRecommended", int(_tin_quality_float(surface, "intersection_exclusion_exact_cut_recommended") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionExactCutGeneratedTriangleCount", int(_tin_quality_float(surface, "intersection_exclusion_exact_cut_generated_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionExactCutPartCount", int(_tin_quality_float(surface, "intersection_exclusion_exact_cut_part_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionHoleRingCount", int(_tin_quality_float(surface, "intersection_exclusion_hole_ring_count") or 0))
    _set_preview_integer_property(obj, "IntersectionExclusionIslandRingCount", int(_tin_quality_float(surface, "intersection_exclusion_island_ring_count") or 0))
    _set_preview_float_property(obj, "IntersectionExclusionDaylightProtectionOffset", _tin_quality_float(surface, "intersection_exclusion_daylight_protection_offset"))
    _set_preview_integer_property(obj, "IntersectionExclusionControlSectionClippedTriangleCount", int(_tin_quality_float(surface, "intersection_exclusion_control_section_clipped_triangle_count") or 0))
    footprint_status = _tin_quality_text(surface, "intersection_footprint_suppress_status")
    if footprint_status:
        _set_preview_property(obj, "IntersectionFootprintSuppressStatus", footprint_status)
    footprint_method = _tin_quality_text(surface, "intersection_footprint_suppress_method")
    if footprint_method:
        _set_preview_property(obj, "IntersectionFootprintSuppressMethod", footprint_method)
    _set_preview_integer_property(obj, "IntersectionFootprintSuppressTestedTriangleCount", int(_tin_quality_float(surface, "intersection_footprint_suppress_tested_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionFootprintSuppressSuppressedTriangleCount", int(_tin_quality_float(surface, "intersection_footprint_suppress_suppressed_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionFootprintSuppressKeptTriangleCount", int(_tin_quality_float(surface, "intersection_footprint_suppress_kept_triangle_count") or 0))
    height_status = _tin_quality_text(surface, "intersection_height_clip_status")
    if height_status:
        _set_preview_property(obj, "IntersectionHeightClipStatus", height_status)
    _set_preview_float_property(obj, "IntersectionHeightClipTolerance", _tin_quality_float(surface, "intersection_height_clip_tolerance"))
    _set_preview_integer_property(obj, "IntersectionHeightClipTestedTriangleCount", int(_tin_quality_float(surface, "intersection_height_clip_tested_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionHeightClipSuppressedTriangleCount", int(_tin_quality_float(surface, "intersection_height_clip_suppressed_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionHeightClipKeptTriangleCount", int(_tin_quality_float(surface, "intersection_height_clip_kept_triangle_count") or 0))
    trim_status = _tin_quality_text(surface, "intersection_slope_trim_status")
    if trim_status:
        _set_preview_property(obj, "IntersectionSlopeTrimStatus", trim_status)
    trim_method = _tin_quality_text(surface, "intersection_slope_trim_method")
    if trim_method:
        _set_preview_property(obj, "IntersectionSlopeTrimMethod", trim_method)
    _set_preview_float_property(obj, "IntersectionSlopeTrimTolerance", _tin_quality_float(surface, "intersection_slope_trim_tolerance"))
    _set_preview_integer_property(obj, "IntersectionSlopeTrimIntersectingTriangleCount", int(_tin_quality_float(surface, "intersection_slope_trim_intersecting_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionSlopeTrimRemovedTriangleCount", int(_tin_quality_float(surface, "intersection_slope_trim_removed_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionSlopeTrimKeptTriangleCount", int(_tin_quality_float(surface, "intersection_slope_trim_kept_triangle_count") or 0))
    _set_preview_integer_property(obj, "IntersectionSlopeTrimIntersectionLineCount", int(_tin_quality_float(surface, "intersection_slope_trim_intersection_line_count") or 0))


def _build_intersection_surface_tin_for_slope_face_height_clip(
    document,
    *,
    project=None,
    corridor_model=None,
    surface_model=None,
    applied_section_set=None,
):
    if document is None or corridor_model is None or surface_model is None or applied_section_set is None:
        return None
    try:
        intersection_model = to_intersection_model(find_v1_intersection_model(document))
        prerequisite = corridor_intersection_patch_prerequisite_result(document)
        status = str(getattr(prerequisite, "status", "") or "")
        if status in {"", "missing", "error"}:
            return None
        surface_id = _surface_id(surface_model, "intersection_surface") or f"{corridor_model.corridor_id}:intersection-surface"
        return _build_intersection_surface_patch_tin(
            project_id=_project_id(project or find_project(document)),
            corridor_model=corridor_model,
            applied_section_set=applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
            surface_id=surface_id,
        )
    except Exception:
        return None


def _suppress_daylight_triangles_inside_intersection_surface_footprint(surface, intersection_surface):
    if surface is None or intersection_surface is None:
        return surface
    from ..models.result.tin_surface import TINQualityRow

    surface_triangles = list(getattr(surface, "triangle_rows", []) or [])
    if not surface_triangles:
        return surface
    reference_triangles = _tin_surface_reference_triangles(intersection_surface)
    if not reference_triangles:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    tested_count = 0
    suppressed_count = 0
    for triangle in surface_triangles:
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        tested_count += 1
        if _tin_triangle_has_sample_inside_reference_footprint(vertices, reference_triangles):
            suppressed_count += 1
            continue
        kept_triangles.append(triangle)
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_footprint_suppress_status",
            "intersection_footprint_suppress_method",
            "intersection_footprint_suppress_tested_triangle_count",
            "intersection_footprint_suppress_suppressed_triangle_count",
            "intersection_footprint_suppress_kept_triangle_count",
            "intersection_footprint_suppress_reference_surface_id",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    reference_surface_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_status", "intersection_footprint_suppress_status", "ready"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_method", "intersection_footprint_suppress_method", "sample_xy_footprint"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_tested_triangle_count", "intersection_footprint_suppress_tested_triangle_count", int(tested_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_suppressed_triangle_count", "intersection_footprint_suppress_suppressed_triangle_count", int(suppressed_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_kept_triangle_count", "intersection_footprint_suppress_kept_triangle_count", len(kept_triangles), "count"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_reference_surface_id", "intersection_footprint_suppress_reference_surface_id", reference_surface_id),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    if reference_surface_id and reference_surface_id not in void_refs:
        void_refs.append(reference_surface_id)
    return replace(surface, triangle_rows=kept_triangles, quality_rows=quality_rows, void_refs=void_refs)


def _tin_triangle_has_sample_inside_reference_footprint(vertices, reference_triangles) -> bool:
    for sample_x, sample_y, _sample_z in _tin_triangle_height_sample_points(vertices):
        if _tin_surface_z_at_xy_from_reference_triangles(reference_triangles, sample_x, sample_y) is not None:
            return True
    return False


def _suppress_daylight_triangles_above_intersection_surface(surface, intersection_surface, *, tolerance: float = 0.05):
    if surface is None or intersection_surface is None:
        return surface
    from ..models.result.tin_surface import TINQualityRow

    surface_triangles = list(getattr(surface, "triangle_rows", []) or [])
    if not surface_triangles:
        return surface
    reference_triangles = _tin_surface_reference_triangles(intersection_surface)
    if not reference_triangles:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    suppressed_count = 0
    tested_count = 0
    for triangle in surface_triangles:
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        centroid_x = sum(float(getattr(vertex, "x", 0.0) or 0.0) for vertex in vertices) / 3.0
        centroid_y = sum(float(getattr(vertex, "y", 0.0) or 0.0) for vertex in vertices) / 3.0
        centroid_z = sum(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices) / 3.0
        reference_z = _tin_surface_z_at_xy_from_reference_triangles(reference_triangles, centroid_x, centroid_y)
        if reference_z is None:
            kept_triangles.append(triangle)
            continue
        tested_count += 1
        if centroid_z >= float(reference_z) - float(tolerance or 0.0):
            suppressed_count += 1
            continue
        kept_triangles.append(triangle)
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_height_clip_status",
            "intersection_height_clip_tolerance",
            "intersection_height_clip_tested_triangle_count",
            "intersection_height_clip_suppressed_triangle_count",
            "intersection_height_clip_kept_triangle_count",
            "intersection_height_clip_reference_surface_id",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    reference_surface_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_height_clip_status", "intersection_height_clip_status", "ready"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_tolerance", "intersection_height_clip_tolerance", float(tolerance or 0.0), "m"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_tested_triangle_count", "intersection_height_clip_tested_triangle_count", int(tested_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_suppressed_triangle_count", "intersection_height_clip_suppressed_triangle_count", int(suppressed_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_kept_triangle_count", "intersection_height_clip_kept_triangle_count", len(kept_triangles), "count"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_reference_surface_id", "intersection_height_clip_reference_surface_id", reference_surface_id),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    if reference_surface_id and reference_surface_id not in void_refs:
        void_refs.append(reference_surface_id)
    if suppressed_count <= 0 and tested_count <= 0:
        return replace(surface, quality_rows=quality_rows, void_refs=void_refs)
    return replace(surface, triangle_rows=kept_triangles, quality_rows=quality_rows, void_refs=void_refs)


def _trim_daylight_triangles_above_intersection_surface_by_intersection_lines(surface, intersection_surface, *, tolerance: float = 0.05):
    if surface is None or intersection_surface is None:
        return surface
    from ..models.result.tin_surface import TINQualityRow

    surface_triangles = list(getattr(surface, "triangle_rows", []) or [])
    if not surface_triangles:
        return surface
    intersection_triangles = _tin_surface_reference_triangles(intersection_surface)
    if not intersection_triangles:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    removed_count = 0
    intersecting_count = 0
    line_count = 0
    for triangle in surface_triangles:
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        if not _daylight_triangle_has_intersection_line_with_surface(vertices, intersection_triangles):
            kept_triangles.append(triangle)
            continue
        intersecting_count += 1
        line_count += 1
        if _tin_triangle_has_sample_above_reference_surface(vertices, intersection_triangles, tolerance=tolerance):
            removed_count += 1
            continue
        kept_triangles.append(triangle)
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_slope_trim_status",
            "intersection_slope_trim_method",
            "intersection_slope_trim_tolerance",
            "intersection_slope_trim_intersecting_triangle_count",
            "intersection_slope_trim_removed_triangle_count",
            "intersection_slope_trim_kept_triangle_count",
            "intersection_slope_trim_intersection_line_count",
            "intersection_slope_trim_reference_surface_id",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    reference_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_slope_trim_status", "intersection_slope_trim_status", "ready"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_method", "intersection_slope_trim_method", "coarse_remove_intersecting_above_triangles"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_tolerance", "intersection_slope_trim_tolerance", float(tolerance or 0.0), "m"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_intersecting_triangle_count", "intersection_slope_trim_intersecting_triangle_count", int(intersecting_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_removed_triangle_count", "intersection_slope_trim_removed_triangle_count", int(removed_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_kept_triangle_count", "intersection_slope_trim_kept_triangle_count", len(kept_triangles), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_intersection_line_count", "intersection_slope_trim_intersection_line_count", int(line_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_reference_surface_id", "intersection_slope_trim_reference_surface_id", reference_id),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    if reference_id and reference_id not in void_refs:
        void_refs.append(reference_id)
    return replace(surface, triangle_rows=kept_triangles, quality_rows=quality_rows, void_refs=void_refs)


def _daylight_triangle_has_intersection_line_with_surface(daylight_vertices, intersection_triangles) -> bool:
    daylight_box = _triangle_xyz_bbox(daylight_vertices)
    for intersection_triangle in list(intersection_triangles or []):
        if not _bbox3d_overlaps(daylight_box, _triangle_xyz_bbox(intersection_triangle), tolerance=0.25):
            continue
        segment = _triangle_triangle_intersection_segment(daylight_vertices, intersection_triangle)
        if segment is None:
            continue
        if _xyz_distance(segment[0], segment[1]) > 1.0e-7:
            return True
    return False


def _tin_triangle_has_sample_above_reference_surface(vertices, reference_triangles, *, tolerance: float = 0.05) -> bool:
    for sample_x, sample_y, sample_z in _tin_triangle_height_sample_points(vertices):
        reference_z = _tin_surface_z_at_xy_from_reference_triangles(reference_triangles, sample_x, sample_y)
        if reference_z is None:
            continue
        if float(sample_z) > float(reference_z) + float(tolerance or 0.0):
            return True
    return False


def _tin_triangle_height_sample_points(vertices) -> list[tuple[float, float, float]]:
    points = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
            float(getattr(vertex, "z", 0.0) or 0.0),
        )
        for vertex in list(vertices or [])
    ]
    if len(points) != 3:
        return points
    centroid = (
        sum(point[0] for point in points) / 3.0,
        sum(point[1] for point in points) / 3.0,
        sum(point[2] for point in points) / 3.0,
    )
    midpoints = [
        (
            (points[index][0] + points[(index + 1) % 3][0]) / 2.0,
            (points[index][1] + points[(index + 1) % 3][1]) / 2.0,
            (points[index][2] + points[(index + 1) % 3][2]) / 2.0,
        )
        for index in range(3)
    ]
    return [centroid] + points + midpoints


def _create_intersection_slope_face_overlap_preview(
    *,
    document,
    project=None,
    daylight_surface=None,
    intersection_surface=None,
    overlap_segments=None,
    overlap_triangle_count=None,
):
    if document is None:
        return None
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    if overlap_segments is None:
        overlap_segments, overlap_triangle_count = _intersection_slope_face_overlap_edge_segments(
            daylight_surface,
            intersection_surface,
        )
    object_name = "V1CorridorIntersectionSlopeFaceOverlapPreview"
    obj = document.getObject(object_name)
    if not overlap_segments:
        _remove_preview_object(document, "V1CorridorIntersectionSlopeFaceOverlapPreview")
        return None
    shapes = []
    for start, end in overlap_segments:
        try:
            start_vec = AppModule.Vector(float(start[0]), float(start[1]), float(start[2]))
            end_vec = AppModule.Vector(float(end[0]), float(end[1]), float(end[2]))
            if start_vec.distanceToPoint(end_vec) <= 1.0e-9:
                continue
            shapes.append(Part.makeLine(start_vec, end_vec))
        except Exception:
            continue
    if not shapes:
        _remove_preview_object(document, object_name)
        return None
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    if obj is not None:
        try:
            obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
            obj.Label = "Intersection / Slope Face Overlap Lines"
        except Exception:
            return obj
        _set_preview_property(obj, "CRRecordKind", "v1_corridor_intersection_slope_face_overlap_line_preview")
        _set_preview_property(obj, "V1ObjectType", "V1CorridorIntersectionSlopeFaceOverlapPreview")
        _set_preview_property(obj, "OverlapKind", "intersection_surface_vs_corridor_slope_face")
        _set_preview_property(obj, "SourceSurfaceRef", str(getattr(daylight_surface, "surface_id", "") or ""))
        _set_preview_property(obj, "ReferenceSurfaceRef", str(getattr(intersection_surface, "surface_id", "") or ""))
        _set_preview_integer_property(obj, "OverlapTriangleCount", int(overlap_triangle_count))
        _set_preview_integer_property(obj, "OverlapLineCount", len(shapes))
        try:
            vobj = getattr(obj, "ViewObject", None)
            if vobj is not None:
                vobj.Visibility = True
                vobj.ShapeColor = (1.0, 0.88, 0.0)
                vobj.LineColor = (1.0, 0.88, 0.0)
                vobj.PointColor = (1.0, 0.88, 0.0)
                vobj.LineWidth = 6.0
                vobj.Transparency = 0
        except Exception:
            pass
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(document), obj)
        except Exception:
            pass
    return obj


def _create_slope_face_generation_boundary_preview(
    *,
    document,
    project=None,
    daylight_surface=None,
    boundary_segments=None,
):
    if document is None:
        return None
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    if boundary_segments is None:
        boundary_segments = _slope_face_generation_boundary_segments(daylight_surface, z_offset=0.10)
    object_name = "V1CorridorSlopeFaceGenerationBoundaryPreview"
    if not boundary_segments:
        _remove_preview_object(document, object_name)
        return None
    shapes = []
    for start, end in boundary_segments:
        try:
            start_vec = AppModule.Vector(float(start[0]), float(start[1]), float(start[2]))
            end_vec = AppModule.Vector(float(end[0]), float(end[1]), float(end[2]))
            if start_vec.distanceToPoint(end_vec) <= 1.0e-9:
                continue
            shapes.append(Part.makeLine(start_vec, end_vec))
        except Exception:
            continue
    if not shapes:
        _remove_preview_object(document, object_name)
        return None
    obj = document.getObject(object_name)
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    if obj is not None:
        try:
            obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
            obj.Label = "Slope Face Generation Boundary"
        except Exception:
            return obj
        _set_preview_property(obj, "CRRecordKind", "v1_corridor_slope_face_generation_boundary_preview")
        _set_preview_property(obj, "V1ObjectType", "V1CorridorSlopeFaceGenerationBoundaryPreview")
        _set_preview_property(obj, "BoundaryKind", "slope_face_generation_open_boundary")
        _set_preview_property(obj, "SourceSurfaceRef", str(getattr(daylight_surface, "surface_id", "") or ""))
        _set_preview_integer_property(obj, "BoundaryLineCount", len(shapes))
        try:
            vobj = getattr(obj, "ViewObject", None)
            if vobj is not None:
                vobj.Visibility = True
                vobj.ShapeColor = (1.0, 0.0, 0.75)
                vobj.LineColor = (1.0, 0.0, 0.75)
                vobj.PointColor = (1.0, 0.0, 0.75)
                vobj.LineWidth = 4.0
                vobj.Transparency = 0
        except Exception:
            pass
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(document), obj)
        except Exception:
            pass
    return obj


def _create_intersection_slope_face_boundary_preview(
    *,
    document,
    project=None,
    applied_section_set=None,
):
    if document is None:
        return None
    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    intersection_model = to_intersection_model(find_v1_intersection_model(document))
    prerequisite = corridor_intersection_patch_prerequisite_result(document)
    if (
        applied_section_set is None
        or prerequisite is None
        or str(getattr(prerequisite, "status", "") or "") == "missing"
    ):
        _remove_preview_object(document, "V1CorridorIntersectionSlopeFaceBoundaryPreview")
        return None
    boundary_result = corridor_intersection_slope_face_boundary_result(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    shapes = []

    def add_polyline(points) -> None:
        ordered = [_xyz_tuple(point) for point in list(points or [])]
        for start, end in zip(ordered, ordered[1:]):
            try:
                start_vec = AppModule.Vector(float(start[0]), float(start[1]), float(start[2]) + 0.16)
                end_vec = AppModule.Vector(float(end[0]), float(end[1]), float(end[2]) + 0.16)
                if start_vec.distanceToPoint(end_vec) <= 1.0e-9:
                    continue
                shapes.append(Part.makeLine(start_vec, end_vec))
            except Exception:
                continue

    for row in list(getattr(boundary_result, "boundary_rows", []) or []):
        add_polyline(getattr(row, "inner_points_xyz", ()) or ())
        add_polyline(getattr(row, "outer_points_xyz", ()) or ())
        add_polyline(getattr(row, "start_tie_edge_xyz", ()) or ())
        add_polyline(getattr(row, "end_tie_edge_xyz", ()) or ())

    object_name = "V1CorridorIntersectionSlopeFaceBoundaryPreview"
    if not shapes:
        _remove_preview_object(document, object_name)
        return None
    obj = document.getObject(object_name)
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    if obj is not None:
        try:
            obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
            obj.Label = "Intersection Slope Face Boundary"
        except Exception:
            return obj
        _set_preview_property(obj, "CRRecordKind", "v1_corridor_intersection_slope_face_boundary_preview")
        _set_preview_property(obj, "V1ObjectType", "V1CorridorIntersectionSlopeFaceBoundaryPreview")
        _set_preview_property(obj, "BoundaryKind", "intersection_slope_face_boundary")
        _set_preview_property(obj, "IntersectionId", str(getattr(boundary_result, "intersection_id", "") or ""))
        _set_preview_property(obj, "Status", str(getattr(boundary_result, "status", "") or ""))
        _set_preview_property(obj, "Diagnostics", "; ".join(list(getattr(boundary_result, "diagnostic_rows", []) or []))[:4000])
        _set_preview_integer_property(obj, "BoundaryCount", int(getattr(boundary_result, "boundary_count", 0) or 0))
        _set_preview_integer_property(obj, "ReadyCount", int(getattr(boundary_result, "ready_count", 0) or 0))
        _set_preview_integer_property(obj, "WarningCount", int(getattr(boundary_result, "warning_count", 0) or 0))
        _set_preview_integer_property(obj, "BoundaryLineCount", len(shapes))
        try:
            vobj = getattr(obj, "ViewObject", None)
            if vobj is not None:
                vobj.Visibility = True
                vobj.ShapeColor = (1.0, 1.0, 1.0)
                vobj.LineColor = (1.0, 1.0, 1.0)
                vobj.PointColor = (1.0, 1.0, 1.0)
                vobj.LineWidth = 5.0
                vobj.Transparency = 0
        except Exception:
            pass
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(document), obj)
        except Exception:
            pass
    return obj


def _slope_face_generation_boundary_segments(daylight_surface, *, z_offset: float = 0.10) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(daylight_surface, "vertex_rows", []) or [])
    }
    if len(vertex_map) < 2:
        return []
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    seen: set[tuple[tuple[float, float, float], tuple[float, float, float]]] = set()
    for first_id, second_id in _tin_surface_boundary_edges(daylight_surface):
        first = vertex_map.get(str(first_id or ""))
        second = vertex_map.get(str(second_id or ""))
        if first is None or second is None:
            continue
        start = (
            float(getattr(first, "x", 0.0) or 0.0),
            float(getattr(first, "y", 0.0) or 0.0),
            float(getattr(first, "z", 0.0) or 0.0) + float(z_offset or 0.0),
        )
        end = (
            float(getattr(second, "x", 0.0) or 0.0),
            float(getattr(second, "y", 0.0) or 0.0),
            float(getattr(second, "z", 0.0) or 0.0) + float(z_offset or 0.0),
        )
        if _xyz_distance(start, end) <= 1.0e-9:
            continue
        key = _normalized_segment_key(start, end)
        if key in seen:
            continue
        seen.add(key)
        segments.append((start, end))
    return segments


def _intersection_slope_face_overlap_edge_segments(daylight_surface, intersection_surface, *, z_offset: float = 0.08) -> tuple[list[tuple[tuple[float, float, float], tuple[float, float, float]]], int]:
    daylight_triangles = _tin_surface_reference_triangles(daylight_surface)
    intersection_triangles = _tin_surface_reference_triangles(intersection_surface)
    if not daylight_triangles or not intersection_triangles:
        return [], 0
    segments = []
    seen: set[tuple[tuple[float, float, float], tuple[float, float, float]]] = set()
    tested_triangle_count = 0
    for daylight_triangle in daylight_triangles:
        daylight_box = _triangle_xyz_bbox(daylight_triangle)
        triangle_has_segment = False
        for intersection_triangle in intersection_triangles:
            if not _bbox3d_overlaps(daylight_box, _triangle_xyz_bbox(intersection_triangle), tolerance=0.25):
                continue
            segment = _triangle_triangle_intersection_segment(daylight_triangle, intersection_triangle)
            if segment is None:
                continue
            start, end = segment
            if _xyz_distance(start, end) <= 1.0e-7:
                continue
            start = (start[0], start[1], start[2] + float(z_offset or 0.0))
            end = (end[0], end[1], end[2] + float(z_offset or 0.0))
            key = _normalized_segment_key(start, end)
            if key in seen:
                continue
            seen.add(key)
            segments.append((start, end))
            triangle_has_segment = True
        if triangle_has_segment:
            tested_triangle_count += 1
    return segments, tested_triangle_count


def _intersection_slope_face_overlap_surface(daylight_surface, intersection_surface, *, z_offset: float = 0.08):
    if daylight_surface is None or intersection_surface is None:
        return None
    from ..models.result.tin_surface import TINQualityRow, TINSurface, TINTriangle, TINVertex

    reference_triangles = _tin_surface_reference_triangles(intersection_surface)
    if not reference_triangles:
        return None
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(daylight_surface, "vertex_rows", []) or [])
    }
    overlap_triangles = []
    overlap_vertex_ids: set[str] = set()
    for triangle in list(getattr(daylight_surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            continue
        if not _tin_triangle_xy_overlaps_reference_triangles(vertices, reference_triangles):
            continue
        overlap_triangles.append(
            TINTriangle(
                str(getattr(triangle, "triangle_id", "") or f"overlap:{len(overlap_triangles) + 1}"),
                str(getattr(triangle, "v1", "") or ""),
                str(getattr(triangle, "v2", "") or ""),
                str(getattr(triangle, "v3", "") or ""),
                "intersection_slope_face_overlap",
                "intersection_slope_face_overlap",
                str(getattr(triangle, "notes", "") or ""),
            )
        )
        overlap_vertex_ids.update([str(getattr(triangle, "v1", "") or ""), str(getattr(triangle, "v2", "") or ""), str(getattr(triangle, "v3", "") or "")])
    if not overlap_triangles:
        return None
    overlap_vertices = []
    for vertex in list(getattr(daylight_surface, "vertex_rows", []) or []):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        if vertex_id not in overlap_vertex_ids:
            continue
        overlap_vertices.append(
            TINVertex(
                vertex_id,
                float(getattr(vertex, "x", 0.0) or 0.0),
                float(getattr(vertex, "y", 0.0) or 0.0),
                float(getattr(vertex, "z", 0.0) or 0.0) + float(z_offset or 0.0),
                str(getattr(vertex, "source_point_ref", "") or ""),
                str(getattr(vertex, "notes", "") or ""),
            )
        )
    source_id = str(getattr(daylight_surface, "surface_id", "") or "daylight_surface")
    reference_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    surface_id = f"{source_id}:intersection-slope-overlap"
    return TINSurface(
        schema_version=int(getattr(daylight_surface, "schema_version", 1) or 1),
        project_id=str(getattr(daylight_surface, "project_id", "") or getattr(intersection_surface, "project_id", "") or ""),
        surface_id=surface_id,
        surface_kind="intersection_slope_face_overlap",
        vertex_rows=overlap_vertices,
        triangle_rows=overlap_triangles,
        boundary_refs=[source_id, reference_id],
        quality_rows=[
            TINQualityRow(f"{surface_id}:overlap_triangle_count", "overlap_triangle_count", len(overlap_triangles), "count"),
            TINQualityRow(f"{surface_id}:overlap_source_surface_id", "overlap_source_surface_id", source_id),
            TINQualityRow(f"{surface_id}:overlap_reference_surface_id", "overlap_reference_surface_id", reference_id),
            TINQualityRow(f"{surface_id}:overlap_z_offset", "overlap_z_offset", float(z_offset or 0.0), "m"),
        ],
    )


def _tin_triangle_xy_overlaps_reference_triangles(vertices: list[object], reference_triangles: list[tuple[object, object, object]]) -> bool:
    for sample_x, sample_y in _tin_triangle_overlap_sample_points_xy(vertices):
        if _tin_surface_z_at_xy_from_reference_triangles(reference_triangles, sample_x, sample_y) is not None:
            return True
    return False


def _tin_triangle_overlap_sample_points_xy(vertices: list[object]) -> list[tuple[float, float]]:
    points = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
        )
        for vertex in list(vertices or [])
    ]
    if len(points) != 3:
        return points
    centroid = (
        sum(point[0] for point in points) / 3.0,
        sum(point[1] for point in points) / 3.0,
    )
    midpoints = [
        (
            (points[index][0] + points[(index + 1) % 3][0]) / 2.0,
            (points[index][1] + points[(index + 1) % 3][1]) / 2.0,
        )
        for index in range(3)
    ]
    return [centroid] + points + midpoints


def _triangle_triangle_intersection_segment(triangle_a, triangle_b):
    points: list[tuple[float, float, float]] = []
    points.extend(_triangle_edges_intersect_other_triangle_plane(triangle_a, triangle_b))
    points.extend(_triangle_edges_intersect_other_triangle_plane(triangle_b, triangle_a))
    unique = _unique_xyz_points(points, tolerance=1.0e-6)
    if len(unique) < 2:
        return None
    best_pair = None
    best_distance = 0.0
    for index, first in enumerate(unique):
        for second in unique[index + 1:]:
            distance = _xyz_distance(first, second)
            if distance > best_distance:
                best_distance = distance
                best_pair = (first, second)
    if best_pair is None or best_distance <= 1.0e-7:
        return None
    return best_pair


def _triangle_edges_intersect_other_triangle_plane(source_triangle, target_triangle) -> list[tuple[float, float, float]]:
    plane = _triangle_plane(target_triangle)
    if plane is None:
        return []
    normal, plane_d = plane
    source_points = [_vertex_xyz(vertex) for vertex in source_triangle]
    target_points = [_vertex_xyz(vertex) for vertex in target_triangle]
    output: list[tuple[float, float, float]] = []
    for first, second in ((source_points[0], source_points[1]), (source_points[1], source_points[2]), (source_points[2], source_points[0])):
        first_distance = _dot3(normal, first) + plane_d
        second_distance = _dot3(normal, second) + plane_d
        if abs(first_distance) <= 1.0e-7 and _point_in_triangle_3d(first, target_points):
            output.append(first)
        if abs(second_distance) <= 1.0e-7 and _point_in_triangle_3d(second, target_points):
            output.append(second)
        if first_distance * second_distance > 0.0:
            continue
        denominator = first_distance - second_distance
        if abs(denominator) <= 1.0e-12:
            continue
        ratio = first_distance / denominator
        if ratio < -1.0e-7 or ratio > 1.0 + 1.0e-7:
            continue
        point = (
            first[0] + (second[0] - first[0]) * ratio,
            first[1] + (second[1] - first[1]) * ratio,
            first[2] + (second[2] - first[2]) * ratio,
        )
        if _point_in_triangle_3d(point, target_points):
            output.append(point)
    return output


def _triangle_plane(triangle):
    points = [_vertex_xyz(vertex) for vertex in triangle]
    ab = _sub3(points[1], points[0])
    ac = _sub3(points[2], points[0])
    normal = _cross3(ab, ac)
    length = _length3(normal)
    if length <= 1.0e-12:
        return None
    normal = (normal[0] / length, normal[1] / length, normal[2] / length)
    return normal, -_dot3(normal, points[0])


def _point_in_triangle_3d(point: tuple[float, float, float], triangle_points: list[tuple[float, float, float]]) -> bool:
    a, b, c = triangle_points
    v0 = _sub3(c, a)
    v1 = _sub3(b, a)
    v2 = _sub3(point, a)
    dot00 = _dot3(v0, v0)
    dot01 = _dot3(v0, v1)
    dot02 = _dot3(v0, v2)
    dot11 = _dot3(v1, v1)
    dot12 = _dot3(v1, v2)
    denominator = dot00 * dot11 - dot01 * dot01
    if abs(denominator) <= 1.0e-12:
        return False
    inv = 1.0 / denominator
    u = (dot11 * dot02 - dot01 * dot12) * inv
    v = (dot00 * dot12 - dot01 * dot02) * inv
    tolerance = 1.0e-6
    return u >= -tolerance and v >= -tolerance and (u + v) <= 1.0 + tolerance


def _triangle_xyz_bbox(triangle) -> tuple[float, float, float, float, float, float]:
    points = [_vertex_xyz(vertex) for vertex in triangle]
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        min(point[2] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
        max(point[2] for point in points),
    )


def _bbox3d_overlaps(first, second, *, tolerance: float = 0.0) -> bool:
    return not (
        first[3] < second[0] - tolerance
        or second[3] < first[0] - tolerance
        or first[4] < second[1] - tolerance
        or second[4] < first[1] - tolerance
        or first[5] < second[2] - tolerance
        or second[5] < first[2] - tolerance
    )


def _unique_xyz_points(points: list[tuple[float, float, float]], *, tolerance: float = 1.0e-6) -> list[tuple[float, float, float]]:
    output = []
    for point in list(points or []):
        if any(_xyz_distance(point, existing) <= tolerance for existing in output):
            continue
        output.append(point)
    return output


def _normalized_segment_key(start, end) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    first = (round(float(start[0]), 5), round(float(start[1]), 5), round(float(start[2]), 5))
    second = (round(float(end[0]), 5), round(float(end[1]), 5), round(float(end[2]), 5))
    return (first, second) if first <= second else (second, first)


def _vertex_xyz(vertex) -> tuple[float, float, float]:
    return (
        float(getattr(vertex, "x", 0.0) or 0.0),
        float(getattr(vertex, "y", 0.0) or 0.0),
        float(getattr(vertex, "z", 0.0) or 0.0),
    )


def _sub3(first, second) -> tuple[float, float, float]:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def _dot3(first, second) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def _cross3(first, second) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _length3(value) -> float:
    return math.sqrt(_dot3(value, value))


def _xyz_distance(first, second) -> float:
    return math.sqrt(
        (float(first[0]) - float(second[0])) ** 2
        + (float(first[1]) - float(second[1])) ** 2
        + (float(first[2]) - float(second[2])) ** 2
    )


def _tin_surface_reference_triangles(surface) -> list[tuple[object, object, object]]:
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    output = []
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            continue
        output.append((vertices[0], vertices[1], vertices[2]))
    return output


def _tin_surface_z_at_xy_from_reference_triangles(reference_triangles, x: float, y: float):
    for a, b, c in list(reference_triangles or []):
        z_value = _triangle_z_at_xy(a, b, c, x, y)
        if z_value is not None:
            return z_value
    return None


def _triangle_z_at_xy(a, b, c, x: float, y: float):
    ax = float(getattr(a, "x", 0.0) or 0.0)
    ay = float(getattr(a, "y", 0.0) or 0.0)
    az = float(getattr(a, "z", 0.0) or 0.0)
    bx = float(getattr(b, "x", 0.0) or 0.0)
    by = float(getattr(b, "y", 0.0) or 0.0)
    bz = float(getattr(b, "z", 0.0) or 0.0)
    cx = float(getattr(c, "x", 0.0) or 0.0)
    cy = float(getattr(c, "y", 0.0) or 0.0)
    cz = float(getattr(c, "z", 0.0) or 0.0)
    denominator = ((by - cy) * (ax - cx)) + ((cx - bx) * (ay - cy))
    if abs(denominator) <= 1.0e-12:
        return None
    first = (((by - cy) * (float(x) - cx)) + ((cx - bx) * (float(y) - cy))) / denominator
    second = (((cy - ay) * (float(x) - cx)) + ((ax - cx) * (float(y) - cy))) / denominator
    third = 1.0 - first - second
    tolerance = 1.0e-8
    if first < -tolerance or second < -tolerance or third < -tolerance:
        return None
    return (first * az) + (second * bz) + (third * cz)


def _clip_tin_surface_by_intersection_exclusion(
    surface,
    document,
    *,
    applied_section_set=None,
    source_applied_section_set=None,
    surface_role: str,
):
    """Return a preview TIN with triangles inside the intersection exclusion polygon suppressed."""

    from ..models.result.tin_surface import TINTriangle, TINVertex

    exclusion = _intersection_exclusion_polygon_from_sources(document, applied_section_set=applied_section_set)
    if exclusion is None:
        return surface
    polygon = list(exclusion.get("points", []) or [])
    if len(polygon) < 3:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    output_vertices = list(getattr(surface, "vertex_rows", []) or [])
    generated_vertex_index = 1
    generated_triangle_index = 1
    kept = []
    clipped_count = 0
    exact_cut_candidate_count = 0
    boundary_crossing_count = 0
    exact_cut_generated_triangle_count = 0
    exact_cut_parts = _xy_exact_cut_exclusion_parts(polygon)
    exact_cut_island_parts = [
        part
        for island in list(exclusion.get("islands", []) or [])
        for part in _xy_exact_cut_exclusion_parts(list(island or []))
    ]
    exact_cut_hole_parts = [
        part
        for hole in list(exclusion.get("holes", []) or [])
        for part in _xy_exact_cut_exclusion_parts(list(hole or []))
    ]
    exact_cut_polygon_supported = bool(exact_cut_parts) and all(len(part) >= 3 for part in exact_cut_hole_parts + exact_cut_island_parts)
    exact_cut_part_count = len(exact_cut_parts) + len(exact_cut_island_parts) + len(exact_cut_hole_parts)
    exact_cut_method = "exact_convex_polygon" if exact_cut_part_count == 1 else "exact_multiring_polygon" if exact_cut_hole_parts or exact_cut_island_parts else "exact_triangulated_polygon"
    hard_suppress = str(surface_role or "").strip().lower() == "daylight"
    test_polygon = polygon
    daylight_protection_offset = 0.0
    control_section_indices: set[int] = set()
    if hard_suppress:
        daylight_protection_offset = 0.0
        test_polygon = polygon
        control_section_indices = _intersection_control_section_indices(
            source_applied_section_set or applied_section_set,
            intersection_id=str(exclusion.get("intersection_id", "") or ""),
        )
        exact_cut_polygon_supported = False
        exact_cut_method = "hard_suppress_intersection"
    control_section_clipped_count = 0
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", ""))]
        if any(vertex is None for vertex in vertices):
            kept.append(triangle)
            continue
        triangle_points = [
            (float(getattr(vertex, "x", 0.0) or 0.0), float(getattr(vertex, "y", 0.0) or 0.0))
            for vertex in vertices
        ]
        geometry_intersection_kind = _xy_triangle_polygon_intersection_kind(triangle_points, test_polygon)
        source_intersection_control = bool(
            hard_suppress
            and geometry_intersection_kind
            and _slope_face_triangle_uses_intersection_control_section(
                triangle,
                control_section_indices=control_section_indices,
            )
        )
        curb_return_daylight_protection = False
        pavement_strip_protection = False
        intersection_kind = (
            "intersection_control_section"
            if source_intersection_control
            else "curb_return_daylight_protection"
            if curb_return_daylight_protection
            else "intersection_pavement_strip_protection"
            if pavement_strip_protection
            else geometry_intersection_kind
        )
        if intersection_kind:
            clipped_count += 1
            if intersection_kind == "edge_crossing":
                boundary_crossing_count += 1
            if intersection_kind in {"intersection_control_section", "curb_return_daylight_protection", "intersection_pavement_strip_protection"}:
                control_section_clipped_count += 1
            exact_cut_candidate = (
                intersection_kind not in {"intersection_control_section", "curb_return_daylight_protection", "intersection_pavement_strip_protection"}
                and not all(_xy_point_in_polygon(point, test_polygon) for point in triangle_points[:3])
            )
            if exact_cut_candidate:
                exact_cut_candidate_count += 1
            if exact_cut_candidate and exact_cut_polygon_supported and not hard_suppress:
                triangle_polygon = [
                    {
                        "x": float(getattr(vertex, "x", 0.0) or 0.0),
                        "y": float(getattr(vertex, "y", 0.0) or 0.0),
                        "z": float(getattr(vertex, "z", 0.0) or 0.0),
                        "source": str(getattr(vertex, "vertex_id", "") or ""),
                    }
                    for vertex in vertices
                ]
                fragments = _xy_subtract_exclusion_area_from_polygon(
                    triangle_polygon,
                    exclusion_parts=exact_cut_parts + exact_cut_island_parts,
                    hole_parts=exact_cut_hole_parts,
                )
                for fragment in fragments:
                    if len(fragment) < 3 or abs(_xy_polygon_area([(point["x"], point["y"]) for point in fragment])) <= 1.0e-9:
                        continue
                    fragment_vertex_ids = []
                    for point in fragment:
                        vertex_id = f"{str(getattr(surface, 'surface_id', '') or surface_role)}:intersection-exact:v{generated_vertex_index}"
                        generated_vertex_index += 1
                        output_vertices.append(
                            TINVertex(
                                vertex_id=vertex_id,
                                x=float(point["x"]),
                                y=float(point["y"]),
                                z=float(point["z"]),
                                source_point_ref=str(point.get("source", "") or ""),
                                notes=f"exact intersection exclusion fragment from {getattr(triangle, 'triangle_id', '')}",
                            )
                        )
                        fragment_vertex_ids.append(vertex_id)
                    for index in range(1, len(fragment_vertex_ids) - 1):
                        kept.append(
                            TINTriangle(
                                triangle_id=f"{getattr(triangle, 'triangle_id', 'triangle')}:intersection-exact:{generated_triangle_index}",
                                v1=fragment_vertex_ids[0],
                                v2=fragment_vertex_ids[index],
                                v3=fragment_vertex_ids[index + 1],
                                triangle_kind=str(getattr(triangle, "triangle_kind", "") or "primary_triangle"),
                                quality_ref="intersection_exclusion_exact_cut",
                                notes=f"generated outside exclusion fragment from {getattr(triangle, 'triangle_id', '')}",
                            )
                        )
                        generated_triangle_index += 1
                        exact_cut_generated_triangle_count += 1
            continue
        kept.append(triangle)
    if clipped_count <= 0:
        return _surface_with_intersection_exclusion_quality(
            surface,
            surface_role=surface_role,
            exclusion=exclusion,
            clipped_count=0,
            kept_count=len(kept),
            exact_cut_candidate_count=0,
            boundary_crossing_count=0,
            exact_cut_generated_triangle_count=0,
            exact_cut_supported=exact_cut_polygon_supported,
            exact_cut_method=exact_cut_method,
            exact_cut_part_count=exact_cut_part_count,
            daylight_protection_offset=daylight_protection_offset,
            control_section_clipped_count=control_section_clipped_count,
        )
    return _surface_with_intersection_exclusion_quality(
        replace(surface, vertex_rows=output_vertices, triangle_rows=kept),
        surface_role=surface_role,
        exclusion=exclusion,
        clipped_count=clipped_count,
        kept_count=len(kept),
        exact_cut_candidate_count=exact_cut_candidate_count,
        boundary_crossing_count=boundary_crossing_count,
        exact_cut_generated_triangle_count=exact_cut_generated_triangle_count,
        exact_cut_supported=exact_cut_polygon_supported,
        exact_cut_method=exact_cut_method,
        exact_cut_part_count=exact_cut_part_count,
        daylight_protection_offset=daylight_protection_offset,
        control_section_clipped_count=control_section_clipped_count,
    )


def _surface_with_intersection_exclusion_quality(
    surface,
    *,
    surface_role: str,
    exclusion: dict[str, object],
    clipped_count: int,
    kept_count: int,
    exact_cut_candidate_count: int = 0,
    boundary_crossing_count: int = 0,
    exact_cut_generated_triangle_count: int = 0,
    exact_cut_supported: bool = False,
    exact_cut_method: str = "exact_convex_polygon",
    exact_cut_part_count: int = 0,
    daylight_protection_offset: float = 0.0,
    control_section_clipped_count: int = 0,
):
    from ..models.result.tin_surface import TINQualityRow

    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_exclusion_status",
            "intersection_exclusion_boundary_source",
            "intersection_exclusion_boundary_strategy",
            "intersection_exclusion_practical_boundary_aligned",
            "intersection_exclusion_point_count",
            "intersection_exclusion_area",
            "intersection_exclusion_clip_method",
            "intersection_exclusion_clipped_triangle_count",
            "intersection_exclusion_kept_triangle_count",
            "intersection_exclusion_boundary_crossing_triangle_count",
            "intersection_exclusion_exact_cut_candidate_count",
            "intersection_exclusion_exact_cut_recommended",
            "intersection_exclusion_exact_cut_generated_triangle_count",
            "intersection_exclusion_exact_cut_supported",
            "intersection_exclusion_exact_cut_part_count",
            "intersection_exclusion_hole_ring_count",
            "intersection_exclusion_island_ring_count",
            "intersection_exclusion_daylight_protection_offset",
            "intersection_exclusion_control_section_clipped_triangle_count",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or f"{surface_role}:surface")
    hard_suppressed = str(exact_cut_method or "") == "hard_suppress_intersection"
    exact_cut_recommended = 0 if hard_suppressed else 1 if int(exact_cut_candidate_count or 0) > int(exact_cut_generated_triangle_count or 0) else 0
    clip_method = (
        "hard_suppress_intersection"
        if hard_suppressed
        else str(exact_cut_method or "exact_convex_polygon") if int(exact_cut_generated_triangle_count or 0) > 0
        else "centroid_or_intersection"
    )
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_exclusion_status", "intersection_exclusion_status", str(exclusion.get("status", "") or "ready")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_source", "intersection_exclusion_boundary_source", str(exclusion.get("boundary_source", "") or "patch_boundary")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_strategy", "intersection_exclusion_boundary_strategy", str(exclusion.get("boundary_strategy", "") or "ordered_patch_boundary")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_practical_boundary_aligned", "intersection_exclusion_practical_boundary_aligned", 1 if bool(exclusion.get("practical_boundary_aligned", False)) else 0, "bool"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_point_count", "intersection_exclusion_point_count", len(list(exclusion.get("points", []) or [])), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_area", "intersection_exclusion_area", float(exclusion.get("area", 0.0) or 0.0), "m2"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_clip_method", "intersection_exclusion_clip_method", clip_method),
            TINQualityRow(f"{surface_id}:intersection_exclusion_clipped_triangle_count", "intersection_exclusion_clipped_triangle_count", int(clipped_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_kept_triangle_count", "intersection_exclusion_kept_triangle_count", int(kept_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_crossing_triangle_count", "intersection_exclusion_boundary_crossing_triangle_count", int(boundary_crossing_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_candidate_count", "intersection_exclusion_exact_cut_candidate_count", int(exact_cut_candidate_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_recommended", "intersection_exclusion_exact_cut_recommended", exact_cut_recommended, "bool"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_generated_triangle_count", "intersection_exclusion_exact_cut_generated_triangle_count", int(exact_cut_generated_triangle_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_supported", "intersection_exclusion_exact_cut_supported", 1 if exact_cut_supported else 0, "bool"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_part_count", "intersection_exclusion_exact_cut_part_count", int(exact_cut_part_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_hole_ring_count", "intersection_exclusion_hole_ring_count", len(list(exclusion.get("holes", []) or [])), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_island_ring_count", "intersection_exclusion_island_ring_count", len(list(exclusion.get("islands", []) or [])), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_daylight_protection_offset", "intersection_exclusion_daylight_protection_offset", float(daylight_protection_offset or 0.0), "m"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_control_section_clipped_triangle_count", "intersection_exclusion_control_section_clipped_triangle_count", int(control_section_clipped_count), "count"),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    exclusion_ref = str(exclusion.get("intersection_id", "") or "intersection")
    if exclusion_ref not in void_refs:
        void_refs.append(exclusion_ref)
    return replace(surface, quality_rows=quality_rows, void_refs=void_refs)


def _point_segment_distance_with_ratio(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[float, float]:
    dx = float(x2) - float(x1)
    dy = float(y2) - float(y1)
    length_sq = dx * dx + dy * dy
    if length_sq <= 1.0e-18:
        return math.hypot(float(px) - float(x1), float(py) - float(y1)), 0.0
    ratio = ((float(px) - float(x1)) * dx + (float(py) - float(y1)) * dy) / length_sq
    clamped = min(max(ratio, 0.0), 1.0)
    closest_x = float(x1) + dx * clamped
    closest_y = float(y1) + dy * clamped
    return math.hypot(float(px) - closest_x, float(py) - closest_y), ratio


def _xy_segment_projection_ratio(
    point_xyz,
    start_xyz,
    end_xyz,
) -> float:
    point = _xyz_tuple(point_xyz)
    start = _xyz_tuple(start_xyz)
    end = _xyz_tuple(end_xyz)
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length_sq = dx * dx + dy * dy
    if length_sq <= 1.0e-18:
        return 0.0
    return ((float(point[0]) - float(start[0])) * dx + (float(point[1]) - float(start[1])) * dy) / length_sq


def _nearest_applied_sections_to_xy_segment(
    sections,
    start_xyz,
    end_xyz,
    *,
    max_count: int = 2,
) -> list[object]:
    ranked: list[tuple[float, float, object]] = []
    start = _xyz_tuple(start_xyz)
    end = _xyz_tuple(end_xyz)
    for section in list(sections or []):
        frame = getattr(section, "frame", None)
        if frame is None:
            continue
        x = float(getattr(frame, "x", 0.0) or 0.0)
        y = float(getattr(frame, "y", 0.0) or 0.0)
        distance, ratio = _point_segment_distance_with_ratio(x, y, start[0], start[1], end[0], end[1])
        ranked.append((float(distance), abs(float(ratio) - 0.5), section))
    ranked.sort(key=lambda item: (item[0], item[1], float(getattr(item[2], "station", 0.0) or 0.0)))
    return [section for _distance, _center_bias, section in ranked[: max(1, int(max_count or 1))]]


def _intersection_slope_face_boundary_target_segments(
    boundary_result,
    *,
    intersection_model=None,
    intersection_id: str = "",
) -> list[object]:
    tie_in_segments = [
        segment
        for segment in list(getattr(boundary_result, "segment_rows", []) or [])
        if str(getattr(segment, "segment_kind", "") or "") == "tie_in"
        and str(getattr(segment, "segment_role", "") or "") == "pavement_edge"
    ]
    if not tie_in_segments:
        return []
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip() if source_row is not None else ""
    primary_segments = [
        segment for segment in tie_in_segments
        if not primary_ref or str(getattr(segment, "alignment_ref", "") or "").strip() == primary_ref
    ]
    candidates = primary_segments or tie_in_segments
    center = _intersection_boundary_result_center_xyz(boundary_result)

    def score(segment) -> tuple[float, float]:
        start = _xyz_tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0)))
        end = _xyz_tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0)))
        midpoint = _midpoint_xyz(start, end)
        distance = _xy_distance((midpoint[0], midpoint[1]), (center[0], center[1]))
        length = _xy_distance((start[0], start[1]), (end[0], end[1]))
        return (float(distance), float(length))

    selected = max(candidates, key=score)
    return [selected]


def _intersection_slope_face_boundary_extended_sections(
    alignment_sections,
    candidate_sections,
    *,
    source_tie_in_edge=None,
    intersection_id: str = "",
    side: str = "",
    extension_length: float = INTERSECTION_SLOPE_FACE_BOUNDARY_EXTENSION_LENGTH,
) -> list[object]:
    ordered = _station_ordered_applied_sections(
        AppliedSectionSet(
            schema_version=1,
            project_id="",
            applied_section_set_id="intersection-slope-face-boundary:alignment-sections",
            corridor_id="",
            sections=list(alignment_sections or []),
        )
    )
    candidates = list(candidate_sections or [])
    if not ordered:
        return candidates
    if source_tie_in_edge is not None:
        start_station = float(getattr(source_tie_in_edge, "station_start", 0.0) or 0.0)
        end_station = float(getattr(source_tie_in_edge, "station_end", start_station) or start_station)
    else:
        stations = [float(getattr(section, "station", 0.0) or 0.0) for section in candidates]
        if not stations:
            stations = [float(getattr(section, "station", 0.0) or 0.0) for section in ordered]
        start_station = min(stations)
        end_station = max(stations)
    low_station = min(start_station, end_station) - max(0.0, float(extension_length or 0.0))
    high_station = max(start_station, end_station) + max(0.0, float(extension_length or 0.0))
    region_id = str(getattr(candidates[0], "region_id", "") or getattr(ordered[0], "region_id", "") or "")
    start_section = _section_at_station_for_intersection_slope_boundary(
        ordered,
        station=low_station,
        region_id=region_id,
        boundary_role=f"intersection-slope-face-start:{intersection_id}:{side}",
    )
    end_section = _section_at_station_for_intersection_slope_boundary(
        ordered,
        station=high_station,
        region_id=region_id,
        boundary_role=f"intersection-slope-face-end:{intersection_id}:{side}",
    )
    output = []
    for section in [start_section, *candidates, end_section]:
        if section is None:
            continue
        station_key = round(float(getattr(section, "station", 0.0) or 0.0), 6)
        if any(round(float(getattr(existing, "station", 0.0) or 0.0), 6) == station_key for existing in output):
            continue
        output.append(section)
    return sorted(output, key=lambda section: float(getattr(section, "station", 0.0) or 0.0))


def _section_at_station_for_intersection_slope_boundary(
    ordered_sections,
    *,
    station: float,
    region_id: str,
    boundary_role: str,
):
    ordered = list(ordered_sections or [])
    if not ordered:
        return None
    value = float(station)
    for section in ordered:
        if abs(float(getattr(section, "station", 0.0) or 0.0) - value) <= 1.0e-6:
            return section
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = float(getattr(first, "station", 0.0) or 0.0)
        second_station = float(getattr(second, "station", 0.0) or 0.0)
        low = min(first_station, second_station)
        high = max(first_station, second_station)
        if low - 1.0e-6 <= value <= high + 1.0e-6:
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (value - first_station) / (second_station - first_station)
            return _interpolate_region_boundary_section(
                first,
                second,
                ratio,
                station=value,
                region_id=region_id,
                boundary_role=boundary_role,
            )
    nearest = min(ordered, key=lambda section: abs(float(getattr(section, "station", 0.0) or 0.0) - value))
    return _project_region_boundary_section(
        nearest,
        station=value,
        region_id=region_id,
        boundary_role=boundary_role,
    )


def _augment_daylight_surface_with_intersection_curb_return_bands(
    surface,
    document,
    *,
    applied_section_set=None,
):
    """Append curb-return arc slope bands without endpoint caps or bridge fillers."""

    if surface is None:
        return surface
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or applied_section_set is None:
        return surface
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    prerequisite = corridor_intersection_patch_prerequisite_result(doc)
    if str(getattr(prerequisite, "status", "") or "") == "missing":
        return surface
    try:
        tie_in_result = corridor_intersection_tie_in_edge_result(
            applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
        boundary_result = corridor_intersection_boundary_segment_result(
            tie_in_result,
            intersection_model=intersection_model,
        )
    except Exception:
        return surface
    return _augment_daylight_surface_with_curb_return_boundary_bands(
        surface,
        boundary_result,
        applied_section_set=applied_section_set,
    )


def _augment_daylight_surface_with_intersection_slope_face_boundary_strips(
    surface,
    document,
    *,
    applied_section_set=None,
):
    """Append first-slice slope-face strips from explicit intersection boundary rows."""

    if surface is None:
        return surface
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or applied_section_set is None:
        return surface
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    prerequisite = corridor_intersection_patch_prerequisite_result(doc)
    if str(getattr(prerequisite, "status", "") or "") == "missing":
        return surface
    try:
        boundary_result = corridor_intersection_slope_face_boundary_result(
            applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
    except Exception:
        return surface
    return _augment_daylight_surface_with_slope_face_boundary_strips(surface, boundary_result)


def _augment_daylight_surface_with_slope_face_boundary_strips(surface, boundary_result):
    """Append triangulated strips between Intersection Surface boundary and Applied Section slope edges."""

    if surface is None or boundary_result is None:
        return surface
    from ..models.result.tin_surface import TINQualityRow, TINTriangle, TINVertex

    vertices = list(getattr(surface, "vertex_rows", []) or [])
    triangles = list(getattr(surface, "triangle_rows", []) or [])
    surface_id = str(getattr(surface, "surface_id", "") or "surface:daylight")
    strip_count = 0
    triangle_count = 0
    sample_count = 0

    def append_triangle(first: TINVertex, second: TINVertex, third: TINVertex, *, notes: str) -> None:
        nonlocal triangle_count
        v1, v2, v3 = first, second, third
        if _xy_triangle_area(v1, v2, v3) < 0.0:
            v2, v3 = v3, v2
        area = abs(_xy_triangle_area(v1, v2, v3))
        if area <= 1.0e-8:
            return
        triangle_count += 1
        triangles.append(
            TINTriangle(
                triangle_id=f"{surface_id}:intersection-slope-face-boundary-strip:t{triangle_count}",
                v1=str(getattr(v1, "vertex_id", "") or ""),
                v2=str(getattr(v2, "vertex_id", "") or ""),
                v3=str(getattr(v3, "vertex_id", "") or ""),
                triangle_kind="daylight_surface",
                quality_ref="intersection_slope_face_boundary_strip",
                notes=notes,
            )
        )

    for row_index, row in enumerate(list(getattr(boundary_result, "boundary_rows", []) or []), start=1):
        if str(getattr(row, "status", "") or "") != "ready":
            continue
        inner_source = [_xyz_tuple(point) for point in list(getattr(row, "inner_points_xyz", ()) or ())]
        outer_source = [_xyz_tuple(point) for point in list(getattr(row, "outer_points_xyz", ()) or ())]
        if len(inner_source) < 2 or len(outer_source) < 2:
            continue
        target_count = max(len(inner_source), len(outer_source), 4)
        inner_points = _resample_xyz_polyline(inner_source, target_count)
        outer_points = _resample_xyz_polyline(outer_source, target_count)
        if len(inner_points) != len(outer_points) or len(inner_points) < 2:
            continue
        pair_vertices: list[tuple[TINVertex, TINVertex]] = []
        for point_index, (inner_xyz, outer_xyz) in enumerate(zip(inner_points, outer_points), start=1):
            inner = TINVertex(
                vertex_id=f"{surface_id}:intersection-slope-face-boundary-strip:r{row_index}:p{point_index}:inner",
                x=float(inner_xyz[0]),
                y=float(inner_xyz[1]),
                z=float(inner_xyz[2]),
                source_point_ref=str(getattr(row, "source_intersection_surface_ref", "") or ""),
                notes=(
                    "intersection_slope_face_boundary_inner; "
                    f"alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}"
                ),
            )
            outer = TINVertex(
                vertex_id=f"{surface_id}:intersection-slope-face-boundary-strip:r{row_index}:p{point_index}:outer",
                x=float(outer_xyz[0]),
                y=float(outer_xyz[1]),
                z=float(outer_xyz[2]),
                source_point_ref=",".join(list(getattr(row, "source_applied_section_refs", ()) or ())),
                notes=(
                    "intersection_slope_face_boundary_outer; "
                    f"alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}"
                ),
            )
            vertices.extend([inner, outer])
            pair_vertices.append((inner, outer))
            sample_count += 1
        for index in range(len(pair_vertices) - 1):
            first_inner, first_outer = pair_vertices[index]
            second_inner, second_outer = pair_vertices[index + 1]
            append_triangle(
                first_inner,
                second_inner,
                first_outer,
                notes=f"intersection slope-face boundary strip; boundary={getattr(row, 'boundary_id', '')}",
            )
            append_triangle(
                first_outer,
                second_inner,
                second_outer,
                notes=f"intersection slope-face boundary strip; boundary={getattr(row, 'boundary_id', '')}",
            )
        strip_count += 1

    if triangle_count <= 0:
        return surface
    filtered_quality = [
        quality
        for quality in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(quality, "kind", "") or "") not in {
            "intersection_slope_face_boundary_strip_count",
            "intersection_slope_face_boundary_strip_sample_count",
            "intersection_slope_face_boundary_strip_triangle_count",
        }
    ]
    filtered_quality.extend(
        [
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_count",
                "intersection_slope_face_boundary_strip_count",
                strip_count,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_sample_count",
                "intersection_slope_face_boundary_strip_sample_count",
                sample_count,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_triangle_count",
                "intersection_slope_face_boundary_strip_triangle_count",
                triangle_count,
                "count",
            ),
        ]
    )
    return replace(surface, vertex_rows=vertices, triangle_rows=triangles, quality_rows=filtered_quality)


def _augment_daylight_surface_with_curb_return_boundary_bands(
    surface,
    boundary_result,
    *,
    applied_section_set=None,
):
    """Append only the arc-following curb-return Slope Face band."""

    if surface is None or boundary_result is None:
        return surface
    from ..models.result.tin_surface import TINQualityRow, TINTriangle, TINVertex

    width, slope = _intersection_curb_return_slope_band_policy(applied_section_set)
    if width <= 0.0:
        return surface
    vertices = list(getattr(surface, "vertex_rows", []) or [])
    triangles = list(getattr(surface, "triangle_rows", []) or [])
    surface_id = str(getattr(surface, "surface_id", "") or "surface:daylight")
    added_edge_count = 0
    added_triangle_count = 0
    added_tie_in_edge_count = 0
    added_tie_in_triangle_count = 0
    added_side_extension_edge_count = 0
    added_side_extension_triangle_count = 0
    added_pavement_tie_in_band_edge_count = 0
    added_gap_closure_edge_pair_count = 0
    added_gap_closure_triangle_count = 0
    added_corner_closure_triangle_count = 0
    max_gap_closure_distance = 0.0
    radial_edges: list[tuple[TINVertex, TINVertex]] = []
    pavement_strip_polygons = _intersection_pavement_strip_polygons_xy_from_boundary_result(boundary_result)

    def append_triangle(first: TINVertex, second: TINVertex, third: TINVertex, *, quality_ref: str, notes: str) -> None:
        nonlocal added_triangle_count, added_tie_in_triangle_count, added_side_extension_triangle_count
        v1, v2, v3 = first, second, third
        if _xy_triangle_area(v1, v2, v3) < 0.0:
            v2, v3 = v3, v2
        if quality_ref == "intersection_slope_tie_in":
            triangle_index = added_tie_in_triangle_count + 1
            added_tie_in_triangle_count += 1
        elif quality_ref == "intersection_side_slope_extension":
            triangle_index = added_side_extension_triangle_count + 1
            added_side_extension_triangle_count += 1
        else:
            triangle_index = added_triangle_count + 1
            added_triangle_count += 1
        triangles.append(
            TINTriangle(
                triangle_id=f"{surface_id}:{quality_ref}:t{triangle_index}",
                v1=str(getattr(v1, "vertex_id", "") or ""),
                v2=str(getattr(v2, "vertex_id", "") or ""),
                v3=str(getattr(v3, "vertex_id", "") or ""),
                triangle_kind="daylight_surface",
                quality_ref=quality_ref,
                notes=notes,
            )
        )

    for arc_index, row in enumerate(list(getattr(boundary_result, "segment_rows", []) or []), start=1):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        chord_points = [_xyz_tuple(point) for point in list(getattr(row, "chord_points_xyz", []) or [])]
        center = _xyz_tuple(getattr(row, "center_xyz", (0.0, 0.0, 0.0)))
        if len(chord_points) < 2:
            continue
        strip_vertices: list[tuple[TINVertex, TINVertex]] = []
        for point_index, point in enumerate(chord_points, start=1):
            radial_x = float(point[0]) - float(center[0])
            radial_y = float(point[1]) - float(center[1])
            radial_len = math.hypot(radial_x, radial_y)
            if radial_len <= 1.0e-9:
                continue
            unit_x = radial_x / radial_len
            unit_y = radial_y / radial_len
            inner = TINVertex(
                vertex_id=f"{surface_id}:intersection-curb-return-slope-band:a{arc_index}:p{point_index}:inner",
                x=float(point[0]),
                y=float(point[1]),
                z=float(point[2]),
                source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                notes="curb_return_slope_band_inner",
            )
            outer = TINVertex(
                vertex_id=f"{surface_id}:intersection-curb-return-slope-band:a{arc_index}:p{point_index}:outer",
                x=float(point[0]) + unit_x * width,
                y=float(point[1]) + unit_y * width,
                z=float(point[2]) - abs(float(slope)) * width,
                source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                notes="curb_return_slope_band_outer",
            )
            vertices.extend([inner, outer])
            strip_vertices.append((inner, outer))
            radial_edges.append((inner, outer))
        for index in range(len(strip_vertices) - 1):
            first_inner, first_outer = strip_vertices[index]
            second_inner, second_outer = strip_vertices[index + 1]
            append_triangle(
                first_inner,
                second_inner,
                first_outer,
                quality_ref="intersection_curb_return_slope_band",
                notes="curb-return arc slope face band",
            )
            append_triangle(
                first_outer,
                second_inner,
                second_outer,
                quality_ref="intersection_curb_return_slope_band",
                notes="curb-return arc slope face band",
            )
            added_edge_count += 1

    boundary_center = _intersection_boundary_result_center_xyz(boundary_result)
    for tie_in_index, row in enumerate(list(getattr(boundary_result, "segment_rows", []) or []), start=1):
        if str(getattr(row, "segment_kind", "") or "") != "tie_in":
            continue
        if str(getattr(row, "segment_role", "") or "") != "pavement_edge":
            continue
        start = _xyz_tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0)))
        end = _xyz_tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0)))
        mid = _midpoint_xyz(start, end)
        outward_x = float(mid[0]) - float(boundary_center[0])
        outward_y = float(mid[1]) - float(boundary_center[1])
        outward_len = math.hypot(outward_x, outward_y)
        if outward_len <= 1.0e-9:
            segment_x = float(end[0]) - float(start[0])
            segment_y = float(end[1]) - float(start[1])
            outward_x, outward_y = -segment_y, segment_x
            outward_len = math.hypot(outward_x, outward_y)
        if outward_len <= 1.0e-9:
            continue
        unit_x = outward_x / outward_len
        unit_y = outward_y / outward_len
        start_inner = TINVertex(
            vertex_id=f"{surface_id}:intersection-pavement-tie-in-slope-band:e{tie_in_index}:start:inner",
            x=float(start[0]),
            y=float(start[1]),
            z=float(start[2]),
            source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
            notes="pavement_tie_in_slope_band_inner",
        )
        end_inner = TINVertex(
            vertex_id=f"{surface_id}:intersection-pavement-tie-in-slope-band:e{tie_in_index}:end:inner",
            x=float(end[0]),
            y=float(end[1]),
            z=float(end[2]),
            source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
            notes="pavement_tie_in_slope_band_inner",
        )
        start_outer = TINVertex(
            vertex_id=f"{surface_id}:intersection-pavement-tie-in-slope-band:e{tie_in_index}:start:outer",
            x=float(start[0]) + unit_x * width,
            y=float(start[1]) + unit_y * width,
            z=float(start[2]) - abs(float(slope)) * width,
            source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
            notes="pavement_tie_in_slope_band_outer",
        )
        end_outer = TINVertex(
            vertex_id=f"{surface_id}:intersection-pavement-tie-in-slope-band:e{tie_in_index}:end:outer",
            x=float(end[0]) + unit_x * width,
            y=float(end[1]) + unit_y * width,
            z=float(end[2]) - abs(float(slope)) * width,
            source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
            notes="pavement_tie_in_slope_band_outer",
        )
        vertices.extend([start_inner, end_inner, start_outer, end_outer])
        append_triangle(
            start_inner,
            end_inner,
            start_outer,
            quality_ref="intersection_pavement_tie_in_slope_band",
            notes=f"pavement tie-in edge slope face band; alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}",
        )
        append_triangle(
            start_outer,
            end_inner,
            end_outer,
            quality_ref="intersection_pavement_tie_in_slope_band",
            notes=f"pavement tie-in edge slope face band; alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}",
        )
        added_pavement_tie_in_band_edge_count += 1
        existing_edges = _near_existing_daylight_boundary_edges_to_side_edge(
            surface,
            start_outer,
            end_outer,
            max_distance=max(float(width or 0.0) * 6.0, 18.0),
            max_edges=4,
        )
        for extension_index, existing_edge in enumerate(existing_edges, start=1):
            existing_first, existing_second = existing_edge
            append_triangle(
                existing_first,
                start_outer,
                existing_second,
                quality_ref="intersection_side_slope_extension",
                notes=(
                    "existing Primary Slope Face boundary to pavement tie-in slope band; "
                    f"extension={extension_index}; alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}"
                ),
            )
            append_triangle(
                existing_second,
                start_outer,
                end_outer,
                quality_ref="intersection_side_slope_extension",
                notes=(
                    "existing Primary Slope Face boundary to pavement tie-in slope band; "
                    f"extension={extension_index}; alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}"
                ),
            )
            added_side_extension_edge_count += 1
        for cap_index, (cap_inner, cap_outer, cap_label) in enumerate(
            ((start_inner, start_outer, "start"), (end_inner, end_outer, "end")),
            start=1,
        ):
            cap_edges = _near_existing_daylight_boundary_edges_to_side_edge(
                surface,
                cap_inner,
                cap_outer,
                max_distance=max(float(width or 0.0) * 4.0, 12.0),
                max_edges=2,
            )
            for cap_edge_index, existing_edge in enumerate(cap_edges, start=1):
                existing_first, existing_second = existing_edge
                append_triangle(
                    existing_first,
                    cap_inner,
                    cap_outer,
                    quality_ref="intersection_side_slope_extension",
                    notes=(
                        "pavement tie-in slope band endpoint cap to existing Slope Face; "
                        f"cap={cap_label}; edge={cap_edge_index}; alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}"
                    ),
                )
                append_triangle(
                    existing_first,
                    cap_outer,
                    existing_second,
                    quality_ref="intersection_side_slope_extension",
                    notes=(
                        "pavement tie-in slope band endpoint cap to existing Slope Face; "
                        f"cap={cap_label}; edge={cap_edge_index}; alignment={getattr(row, 'alignment_ref', '')}; side={getattr(row, 'side', '')}"
                    ),
                )
                added_side_extension_edge_count += 1

    tie_in_edges = _intersection_side_applied_section_slope_tie_in_edges(
        applied_section_set,
        boundary_result=boundary_result,
        band_radial_edges=radial_edges,
        band_width=width,
        band_slope=slope,
    )
    for edge_index, edge in enumerate(tie_in_edges, start=1):
        side_inner = TINVertex(
            vertex_id=f"{surface_id}:intersection-slope-tie-in:e{edge_index}:side:inner",
            x=float(edge["side_inner"][0]),
            y=float(edge["side_inner"][1]),
            z=float(edge["side_inner"][2]),
            source_point_ref=str(edge.get("source_ref", "") or ""),
            notes="intersection_slope_tie_in_side_inner",
        )
        side_outer = TINVertex(
            vertex_id=f"{surface_id}:intersection-slope-tie-in:e{edge_index}:side:outer",
            x=float(edge["side_outer"][0]),
            y=float(edge["side_outer"][1]),
            z=float(edge["side_outer"][2]),
            source_point_ref=str(edge.get("source_ref", "") or ""),
            notes="intersection_slope_tie_in_side_outer",
        )
        band_inner, band_outer = edge["band_edge"]
        vertices.extend([side_inner, side_outer])
        existing_edges = _near_existing_daylight_boundary_edges_to_side_edge(
            surface,
            side_inner,
            side_outer,
            max_distance=max(float(width or 0.0) * 6.0, 18.0),
            max_edges=4,
        )
        for extension_index, existing_edge in enumerate(existing_edges, start=1):
            existing_first, existing_second = existing_edge
            append_triangle(
                existing_first,
                side_inner,
                existing_second,
                quality_ref="intersection_side_slope_extension",
                notes=f"existing side Slope Face boundary to side Applied Section; extension={extension_index}; {edge.get('notes', '')}",
            )
            append_triangle(
                existing_second,
                side_inner,
                side_outer,
                quality_ref="intersection_side_slope_extension",
                notes=f"existing side Slope Face boundary to side Applied Section; extension={extension_index}; {edge.get('notes', '')}",
            )
            added_side_extension_edge_count += 1
        append_triangle(
            side_inner,
            band_inner,
            side_outer,
            quality_ref="intersection_slope_tie_in",
            notes=f"side Applied Section to curb-return slope band; {edge.get('notes', '')}",
        )
        append_triangle(
            side_outer,
            band_inner,
            band_outer,
            quality_ref="intersection_slope_tie_in",
            notes=f"side Applied Section to curb-return slope band; {edge.get('notes', '')}",
        )
        added_tie_in_edge_count += 1

    if added_triangle_count <= 0:
        return surface
    current_surface = replace(surface, vertex_rows=vertices, triangle_rows=triangles)
    gap_closure_result = _intersection_slope_gap_closure_triangles(
        current_surface,
        boundary_result=boundary_result,
        band_width=width,
    )
    if gap_closure_result["triangles"]:
        triangles.extend(gap_closure_result["triangles"])
        added_gap_closure_edge_pair_count = int(gap_closure_result["edge_pair_count"])
        added_gap_closure_triangle_count = int(gap_closure_result["triangle_count"])
        added_corner_closure_triangle_count = int(gap_closure_result.get("corner_triangle_count", 0) or 0)
        max_gap_closure_distance = float(gap_closure_result["max_gap_distance"])
    filtered_quality = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_curb_return_slope_band_edge_count",
            "intersection_curb_return_slope_band_triangle_count",
            "intersection_curb_return_slope_band_width",
            "intersection_curb_return_slope_band_slope",
            "intersection_slope_tie_in_edge_count",
            "intersection_slope_tie_in_triangle_count",
            "intersection_side_slope_extension_edge_count",
            "intersection_side_slope_extension_triangle_count",
            "intersection_pavement_tie_in_slope_band_edge_count",
            "intersection_pavement_tie_in_slope_band_triangle_count",
            "intersection_slope_gap_closure_edge_pair_count",
            "intersection_slope_gap_closure_triangle_count",
            "intersection_slope_corner_closure_triangle_count",
            "intersection_slope_gap_closure_max_gap_distance",
        }
    ]
    filtered_quality.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_curb_return_slope_band_edge_count", "intersection_curb_return_slope_band_edge_count", added_edge_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_curb_return_slope_band_triangle_count", "intersection_curb_return_slope_band_triangle_count", added_triangle_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_curb_return_slope_band_width", "intersection_curb_return_slope_band_width", float(width), "m"),
            TINQualityRow(f"{surface_id}:intersection_curb_return_slope_band_slope", "intersection_curb_return_slope_band_slope", float(slope), "ratio"),
            TINQualityRow(f"{surface_id}:intersection_slope_tie_in_edge_count", "intersection_slope_tie_in_edge_count", added_tie_in_edge_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_tie_in_triangle_count", "intersection_slope_tie_in_triangle_count", added_tie_in_triangle_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_side_slope_extension_edge_count", "intersection_side_slope_extension_edge_count", added_side_extension_edge_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_side_slope_extension_triangle_count", "intersection_side_slope_extension_triangle_count", added_side_extension_triangle_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_pavement_tie_in_slope_band_edge_count", "intersection_pavement_tie_in_slope_band_edge_count", added_pavement_tie_in_band_edge_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_pavement_tie_in_slope_band_triangle_count", "intersection_pavement_tie_in_slope_band_triangle_count", added_pavement_tie_in_band_edge_count * 2, "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_gap_closure_edge_pair_count", "intersection_slope_gap_closure_edge_pair_count", added_gap_closure_edge_pair_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_gap_closure_triangle_count", "intersection_slope_gap_closure_triangle_count", added_gap_closure_triangle_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_corner_closure_triangle_count", "intersection_slope_corner_closure_triangle_count", added_corner_closure_triangle_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_gap_closure_max_gap_distance", "intersection_slope_gap_closure_max_gap_distance", max_gap_closure_distance, "m"),
        ]
    )
    return replace(surface, vertex_rows=vertices, triangle_rows=triangles, quality_rows=filtered_quality)


def _intersection_slope_gap_closure_triangles(
    surface,
    *,
    boundary_result=None,
    band_width: float = 0.0,
) -> dict[str, object]:
    """Create small Slope Face closure triangles between nearby open intersection edges."""

    from ..models.result.tin_surface import TINTriangle

    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    if len(vertex_map) < 3:
        return {"triangles": [], "edge_pair_count": 0, "triangle_count": 0, "corner_triangle_count": 0, "max_gap_distance": 0.0}
    edge_rows = _tin_surface_boundary_edge_rows(surface)
    if len(edge_rows) < 2:
        return {"triangles": [], "edge_pair_count": 0, "triangle_count": 0, "corner_triangle_count": 0, "max_gap_distance": 0.0}

    center = _intersection_boundary_result_center_xyz(boundary_result)
    search_radius = max(float(band_width or 0.0) * 10.0, 24.0)
    max_gap = max(float(band_width or 0.0) * 2.0, 6.0)
    max_quad_area = max(float(band_width or 0.0) * float(band_width or 0.0) * 16.0, 96.0)
    generated_refs = {
        "intersection_slope_tie_in",
        "intersection_side_slope_extension",
        "intersection_pavement_tie_in_slope_band",
    }
    closure_edges = [
        row for row in edge_rows
        if str(row.get("quality_ref", "") or "") in generated_refs
        and _xy_distance(_edge_midpoint_xy(row, vertex_map), (float(center[0]), float(center[1]))) <= search_radius
    ]
    nearby_edges = [
        row for row in edge_rows
        if _xy_distance(_edge_midpoint_xy(row, vertex_map), (float(center[0]), float(center[1]))) <= search_radius
    ]
    if len(nearby_edges) < 2:
        return {"triangles": [], "edge_pair_count": 0, "triangle_count": 0, "corner_triangle_count": 0, "max_gap_distance": 0.0}

    surface_id = str(getattr(surface, "surface_id", "") or "surface:daylight")
    added: list[TINTriangle] = []
    used_pair_keys: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    used_triangle_keys: set[tuple[str, str, str]] = set()
    used_gap_vertex_ids: set[str] = set()
    max_used_gap = 0.0

    def add_triangle(first_id: str, second_id: str, third_id: str, *, pair_index: int = 0, closure_kind: str = "gap") -> bool:
        ids = [str(first_id or ""), str(second_id or ""), str(third_id or "")]
        if len(set(ids)) < 3:
            return False
        first = vertex_map.get(ids[0])
        second = vertex_map.get(ids[1])
        third = vertex_map.get(ids[2])
        if first is None or second is None or third is None:
            return False
        area = _xy_triangle_area(first, second, third)
        if abs(area) <= 1.0e-6:
            return False
        if area < 0.0:
            ids[1], ids[2] = ids[2], ids[1]
        key = tuple(sorted(ids))
        if key in used_triangle_keys:
            return False
        used_triangle_keys.add(key)
        quality_ref = "intersection_slope_corner_closure" if closure_kind == "corner" else "intersection_slope_gap_closure"
        added.append(
            TINTriangle(
                triangle_id=f"{surface_id}:{quality_ref}:t{len(added) + 1}",
                v1=ids[0],
                v2=ids[1],
                v3=ids[2],
                triangle_kind="daylight_surface",
                quality_ref=quality_ref,
                notes=(
                    f"intersection Slope Face corner closure; anchor={pair_index}"
                    if closure_kind == "corner"
                    else f"intersection Slope Face gap closure; edge_pair={pair_index}"
                ),
            )
        )
        return True

    for first_edge in closure_edges:
        if len(added) >= 64:
            break
        for second_edge in nearby_edges:
            if first_edge is second_edge:
                continue
            first_key = tuple(sorted((str(first_edge["first_id"]), str(first_edge["second_id"]))))
            second_key = tuple(sorted((str(second_edge["first_id"]), str(second_edge["second_id"]))))
            if first_key == second_key:
                continue
            if set(first_key).intersection(second_key):
                continue
            pair_key = tuple(sorted((first_key, second_key)))
            if pair_key in used_pair_keys:
                continue
            pairing = _near_parallel_boundary_edge_pairing(first_edge, second_edge, vertex_map, max_gap=max_gap)
            if pairing is None:
                continue
            a_id, b_id, c_id, d_id, gap_distance = pairing
            a = vertex_map[a_id]
            b = vertex_map[b_id]
            c = vertex_map[c_id]
            d = vertex_map[d_id]
            quad_area = abs(_xy_triangle_area(a, b, d)) + abs(_xy_triangle_area(a, d, c))
            if quad_area <= 1.0e-6 or quad_area > max_quad_area:
                continue
            if _edge_pair_crosses_existing_triangle_interior(a, b, c, d, surface):
                continue
            used_pair_keys.add(pair_key)
            used_gap_vertex_ids.update({a_id, b_id, c_id, d_id})
            pair_index = len(used_pair_keys)
            add_triangle(a_id, b_id, d_id, pair_index=pair_index)
            add_triangle(a_id, d_id, c_id, pair_index=pair_index)
            max_used_gap = max(max_used_gap, float(gap_distance))
            if len(added) >= 64:
                break

    corner_triangle_count = _append_intersection_slope_corner_closure_triangles(
        add_triangle,
        edge_rows=edge_rows,
        vertex_map=vertex_map,
        boundary_result=boundary_result,
        band_width=band_width,
        existing_triangle_count=len(added),
        excluded_anchor_ids=used_gap_vertex_ids,
    )

    return {
        "triangles": added,
        "edge_pair_count": len(used_pair_keys),
        "triangle_count": len(added) - corner_triangle_count,
        "corner_triangle_count": corner_triangle_count,
        "max_gap_distance": max_used_gap,
    }


def _append_intersection_slope_corner_closure_triangles(
    add_triangle,
    *,
    edge_rows: list[dict[str, object]],
    vertex_map: dict[str, object],
    boundary_result=None,
    band_width: float = 0.0,
    existing_triangle_count: int = 0,
    excluded_anchor_ids: set[str] | None = None,
) -> int:
    arc_endpoints = _intersection_curb_return_arc_endpoint_points(boundary_result)
    if not arc_endpoints:
        return 0
    generated_refs = {
        "intersection_curb_return_slope_band",
        "intersection_slope_tie_in",
        "intersection_side_slope_extension",
        "intersection_pavement_tie_in_slope_band",
    }
    boundary_vertex_ids = _boundary_vertex_ids_from_edge_rows(edge_rows)
    edge_adjacency = _boundary_edge_adjacency_from_edge_rows(edge_rows)
    candidate_radius = max(float(band_width or 0.0) * 1.75, 5.0)
    max_area = max(float(band_width or 0.0) * float(band_width or 0.0) * 3.0, 24.0)
    added_count = 0
    used_anchor_ids: set[str] = set()
    excluded_anchors = {str(value or "") for value in set(excluded_anchor_ids or set())}
    for endpoint_index, endpoint in enumerate(arc_endpoints, start=1):
        anchor_id = _nearest_boundary_vertex_id_to_point(
            boundary_vertex_ids,
            vertex_map,
            endpoint,
            required_quality_refs=generated_refs,
            edge_rows=edge_rows,
            max_distance=max(candidate_radius, 0.5),
        )
        if not anchor_id or anchor_id in used_anchor_ids or anchor_id in excluded_anchors:
            continue
        anchor = vertex_map.get(anchor_id)
        if anchor is None:
            continue
        candidates = []
        anchor_xy = _xy_point_tuple(anchor)
        for vertex_id in boundary_vertex_ids:
            if vertex_id == anchor_id:
                continue
            vertex = vertex_map.get(vertex_id)
            if vertex is None:
                continue
            distance = _xy_distance(anchor_xy, _xy_point_tuple(vertex))
            if distance <= 1.0e-9 or distance > candidate_radius:
                continue
            candidates.append((distance, vertex_id))
        candidates.sort(key=lambda row: row[0])
        best_pair: tuple[float, str, str] | None = None
        for first_index, first_candidate in enumerate(candidates[:10]):
            first_id = first_candidate[1]
            for second_candidate in candidates[first_index + 1:10]:
                second_id = second_candidate[1]
                if second_id in edge_adjacency.get(first_id, set()):
                    continue
                first = vertex_map.get(first_id)
                second = vertex_map.get(second_id)
                if first is None or second is None:
                    continue
                area = abs(_xy_triangle_area(anchor, first, second))
                if area <= 1.0e-6 or area > max_area:
                    continue
                spread = _corner_candidate_angle_spread(anchor, first, second)
                if spread < 0.20:
                    continue
                score = area + first_candidate[0] + second_candidate[0]
                if best_pair is None or score < best_pair[0]:
                    best_pair = (score, first_id, second_id)
        if best_pair is None:
            continue
        if add_triangle(anchor_id, best_pair[1], best_pair[2], pair_index=endpoint_index, closure_kind="corner"):
            added_count += 1
            used_anchor_ids.add(anchor_id)
    return added_count


def _intersection_curb_return_arc_endpoint_points(boundary_result) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        chord_points = [_xyz_tuple(point) for point in list(getattr(row, "chord_points_xyz", []) or [])]
        if not chord_points:
            continue
        points.append(chord_points[0])
        if _xyz_distance(chord_points[0], chord_points[-1]) > 1.0e-7:
            points.append(chord_points[-1])
    return points


def _boundary_vertex_ids_from_edge_rows(edge_rows: list[dict[str, object]]) -> set[str]:
    output: set[str] = set()
    for row in list(edge_rows or []):
        first_id = str(row.get("first_id", "") or "")
        second_id = str(row.get("second_id", "") or "")
        if first_id:
            output.add(first_id)
        if second_id:
            output.add(second_id)
    return output


def _boundary_edge_adjacency_from_edge_rows(edge_rows: list[dict[str, object]]) -> dict[str, set[str]]:
    output: dict[str, set[str]] = {}
    for row in list(edge_rows or []):
        first_id = str(row.get("first_id", "") or "")
        second_id = str(row.get("second_id", "") or "")
        if not first_id or not second_id:
            continue
        output.setdefault(first_id, set()).add(second_id)
        output.setdefault(second_id, set()).add(first_id)
    return output


def _nearest_boundary_vertex_id_to_point(
    boundary_vertex_ids: set[str],
    vertex_map: dict[str, object],
    point: tuple[float, float, float],
    *,
    required_quality_refs: set[str],
    edge_rows: list[dict[str, object]],
    max_distance: float,
) -> str:
    candidate_ids = _boundary_vertex_ids_with_quality_refs(edge_rows, required_quality_refs)
    best_id = ""
    best_distance = None
    point_xy = (float(point[0]), float(point[1]))
    for vertex_id in set(boundary_vertex_ids or set()).intersection(candidate_ids):
        vertex = vertex_map.get(vertex_id)
        if vertex is None:
            continue
        distance = _xy_distance(point_xy, _xy_point_tuple(vertex))
        if distance > float(max_distance):
            continue
        if best_distance is None or distance < best_distance:
            best_id = vertex_id
            best_distance = distance
    return best_id


def _boundary_vertex_ids_with_quality_refs(edge_rows: list[dict[str, object]], quality_refs: set[str]) -> set[str]:
    refs = {str(value or "") for value in set(quality_refs or set())}
    output: set[str] = set()
    for row in list(edge_rows or []):
        if str(row.get("quality_ref", "") or "") not in refs:
            continue
        first_id = str(row.get("first_id", "") or "")
        second_id = str(row.get("second_id", "") or "")
        if first_id:
            output.add(first_id)
        if second_id:
            output.add(second_id)
    return output


def _corner_candidate_angle_spread(anchor, first, second) -> float:
    ax, ay = _xy_point_tuple(anchor)
    fx, fy = _xy_point_tuple(first)
    sx, sy = _xy_point_tuple(second)
    first_dx = fx - ax
    first_dy = fy - ay
    second_dx = sx - ax
    second_dy = sy - ay
    first_len = math.hypot(first_dx, first_dy)
    second_len = math.hypot(second_dx, second_dy)
    if first_len <= 1.0e-9 or second_len <= 1.0e-9:
        return 0.0
    return abs((first_dx * second_dy) - (first_dy * second_dx)) / (first_len * second_len)


def _tin_surface_boundary_edge_rows(surface) -> list[dict[str, object]]:
    edge_counts: dict[tuple[str, str], int] = {}
    edge_values: dict[tuple[str, str], dict[str, object]] = {}
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        ids = [
            str(getattr(triangle, "v1", "") or ""),
            str(getattr(triangle, "v2", "") or ""),
            str(getattr(triangle, "v3", "") or ""),
        ]
        for first_id, second_id in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            edge_values.setdefault(
                key,
                {
                    "first_id": first_id,
                    "second_id": second_id,
                    "quality_ref": str(getattr(triangle, "quality_ref", "") or ""),
                    "triangle_id": str(getattr(triangle, "triangle_id", "") or ""),
                },
            )
    return [edge_values[key] for key, count in edge_counts.items() if count == 1]


def _edge_midpoint_xy(edge_row: dict[str, object], vertex_map: dict[str, object]) -> tuple[float, float]:
    first = vertex_map.get(str(edge_row.get("first_id", "") or ""))
    second = vertex_map.get(str(edge_row.get("second_id", "") or ""))
    if first is None or second is None:
        return (0.0, 0.0)
    return (
        (float(getattr(first, "x", 0.0) or 0.0) + float(getattr(second, "x", 0.0) or 0.0)) * 0.5,
        (float(getattr(first, "y", 0.0) or 0.0) + float(getattr(second, "y", 0.0) or 0.0)) * 0.5,
    )


def _xy_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(float(first[0]) - float(second[0]), float(first[1]) - float(second[1]))


def _near_parallel_boundary_edge_pairing(
    first_edge: dict[str, object],
    second_edge: dict[str, object],
    vertex_map: dict[str, object],
    *,
    max_gap: float,
) -> tuple[str, str, str, str, float] | None:
    a_id = str(first_edge.get("first_id", "") or "")
    b_id = str(first_edge.get("second_id", "") or "")
    c_id = str(second_edge.get("first_id", "") or "")
    d_id = str(second_edge.get("second_id", "") or "")
    a = vertex_map.get(a_id)
    b = vertex_map.get(b_id)
    c = vertex_map.get(c_id)
    d = vertex_map.get(d_id)
    if a is None or b is None or c is None or d is None:
        return None
    first_dx = float(getattr(b, "x", 0.0) or 0.0) - float(getattr(a, "x", 0.0) or 0.0)
    first_dy = float(getattr(b, "y", 0.0) or 0.0) - float(getattr(a, "y", 0.0) or 0.0)
    second_dx = float(getattr(d, "x", 0.0) or 0.0) - float(getattr(c, "x", 0.0) or 0.0)
    second_dy = float(getattr(d, "y", 0.0) or 0.0) - float(getattr(c, "y", 0.0) or 0.0)
    first_len = math.hypot(first_dx, first_dy)
    second_len = math.hypot(second_dx, second_dy)
    if first_len <= 1.0e-9 or second_len <= 1.0e-9:
        return None
    if min(first_len, second_len) / max(first_len, second_len) < 0.35:
        return None
    parallel_score = abs((first_dx * second_dx + first_dy * second_dy) / (first_len * second_len))
    if parallel_score < 0.75:
        return None
    local_max_gap = min(float(max_gap), max(min(first_len, second_len) * 0.75, float(max_gap) * 0.35, 2.0))
    direct = (
        math.hypot(float(getattr(a, "x", 0.0)) - float(getattr(c, "x", 0.0)), float(getattr(a, "y", 0.0)) - float(getattr(c, "y", 0.0))),
        math.hypot(float(getattr(b, "x", 0.0)) - float(getattr(d, "x", 0.0)), float(getattr(b, "y", 0.0)) - float(getattr(d, "y", 0.0))),
    )
    reversed_pair = (
        math.hypot(float(getattr(a, "x", 0.0)) - float(getattr(d, "x", 0.0)), float(getattr(a, "y", 0.0)) - float(getattr(d, "y", 0.0))),
        math.hypot(float(getattr(b, "x", 0.0)) - float(getattr(c, "x", 0.0)), float(getattr(b, "y", 0.0)) - float(getattr(c, "y", 0.0))),
    )
    direct_gap = max(direct)
    reversed_gap = max(reversed_pair)
    if direct_gap <= reversed_gap:
        if direct_gap > local_max_gap:
            return None
        return a_id, b_id, c_id, d_id, direct_gap
    if reversed_gap > local_max_gap:
        return None
    return a_id, b_id, d_id, c_id, reversed_gap


def _edge_pair_crosses_existing_triangle_interior(a, b, c, d, surface) -> bool:
    # This closure is intentionally conservative.  If its diagonals would be
    # long and likely cross unrelated mesh, area/length guards above reject it;
    # exact planar boolean clipping is left to the later topology-first pass.
    return False


def _intersection_boundary_result_center_xyz(boundary_result) -> tuple[float, float, float]:
    centers: list[tuple[float, float, float]] = []
    points: list[tuple[float, float, float]] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") == "arc":
            centers.append(_xyz_tuple(getattr(row, "center_xyz", (0.0, 0.0, 0.0))))
        points.append(_xyz_tuple(getattr(row, "start_xyz", (0.0, 0.0, 0.0))))
        points.append(_xyz_tuple(getattr(row, "end_xyz", (0.0, 0.0, 0.0))))
    source = centers or points
    if not source:
        return (0.0, 0.0, 0.0)
    return (
        sum(float(point[0]) for point in source) / len(source),
        sum(float(point[1]) for point in source) / len(source),
        sum(float(point[2]) for point in source) / len(source),
    )


def _intersection_curb_return_slope_band_policy(applied_section_set) -> tuple[float, float]:
    widths: list[float] = []
    slopes: list[float] = []
    for section in list(getattr(applied_section_set, "sections", []) or []):
        for attr in ("daylight_left_width", "daylight_right_width"):
            value = max(float(getattr(section, attr, 0.0) or 0.0), 0.0)
            if value > 0.0:
                widths.append(value)
        for attr in ("daylight_left_slope", "daylight_right_slope"):
            value = abs(float(getattr(section, attr, 0.0) or 0.0))
            if value > 0.0:
                slopes.append(value)
    width_source = (sum(widths) / len(widths)) if widths else 3.0
    width = max(1.5, min(width_source, 4.0))
    slope = max(0.05, min((sum(slopes) / len(slopes)) if slopes else 0.25, 1.0))
    return width, slope


def _intersection_side_applied_section_slope_tie_in_edges(
    applied_section_set,
    *,
    boundary_result=None,
    band_radial_edges: list[tuple[object, object]],
    band_width: float,
    band_slope: float,
) -> list[dict[str, object]]:
    if applied_section_set is None or not band_radial_edges:
        return []
    intersection_id = str(getattr(boundary_result, "intersection_id", "") or "").strip()
    candidate_edges: list[dict[str, object]] = []
    for section in list(getattr(applied_section_set, "sections", []) or []):
        alignment_id = str(getattr(section, "alignment_id", "") or "").strip()
        active_intersection = str(getattr(section, "active_intersection_id", "") or "").strip()
        if intersection_id and active_intersection and active_intersection != intersection_id:
            continue
        leg_role = str(getattr(section, "active_intersection_leg_role", "") or "").strip()
        is_primary_through = leg_role == "primary_through"
        for side_label in ("left", "right"):
            edge = _applied_section_slope_face_edge_points(
                section,
                side_label=side_label,
                fallback_band_width=band_width,
                fallback_band_slope=band_slope,
            )
            if edge is None:
                continue
            side_inner, side_outer = edge
            side_mid = _midpoint_xyz(side_inner, side_outer)
            band_candidates: list[tuple[float, object, object]] = []
            for band_inner, band_outer in band_radial_edges:
                band_mid = _midpoint_xyz(
                    _vertex_xyz_tuple(band_inner),
                    _vertex_xyz_tuple(band_outer),
                )
                distance = _xy_distance((side_mid[0], side_mid[1]), (band_mid[0], band_mid[1]))
                band_candidates.append((float(distance), band_inner, band_outer))
            max_distance = max(float(band_width or 0.0) * (8.0 if is_primary_through else 4.0), 24.0 if is_primary_through else 12.0)
            candidate_limit = 10 if is_primary_through else 6
            for nearest_distance, band_inner, band_outer in sorted(band_candidates, key=lambda row: row[0])[:candidate_limit]:
                if float(nearest_distance) > max_distance:
                    continue
                candidate_edges.append(
                    {
                        "section_id": str(getattr(section, "applied_section_id", "") or ""),
                        "alignment_id": alignment_id,
                        "leg_role": leg_role,
                        "side_label": side_label,
                        "side_inner": side_inner,
                        "side_outer": side_outer,
                        "band_edge": (band_inner, band_outer),
                        "distance": float(nearest_distance),
                        "source_ref": f"{str(getattr(section, 'applied_section_id', '') or '')}:{side_label}",
                        "notes": f"alignment={alignment_id}; section={str(getattr(section, 'applied_section_id', '') or '')}; role={leg_role or '-'}; side={side_label}; distance={float(nearest_distance):.3f}",
                    }
                )
    output: list[dict[str, object]] = []
    used_key_counts: dict[tuple[str, str], int] = {}
    used_band_edge_counts: dict[tuple[str, str], int] = {}
    for candidate in sorted(candidate_edges, key=lambda row: float(row.get("distance", 0.0) or 0.0)):
        key = (str(candidate.get("section_id", "") or ""), str(candidate.get("side_label", "") or ""))
        is_primary_candidate = str(candidate.get("leg_role", "") or "") == "primary_through"
        if used_key_counts.get(key, 0) >= (4 if is_primary_candidate else 3):
            continue
        band_inner, band_outer = candidate["band_edge"]
        band_key = (
            str(getattr(band_inner, "vertex_id", "") or ""),
            str(getattr(band_outer, "vertex_id", "") or ""),
        )
        if used_band_edge_counts.get(band_key, 0) >= (3 if is_primary_candidate else 2):
            continue
        output.append(candidate)
        used_key_counts[key] = used_key_counts.get(key, 0) + 1
        used_band_edge_counts[band_key] = used_band_edge_counts.get(band_key, 0) + 1
        if len(output) >= 20:
            break
    return output


def _near_existing_daylight_boundary_edges_to_side_edge(
    surface,
    side_inner,
    side_outer,
    *,
    max_distance: float,
    max_edges: int = 4,
) -> list[tuple[object, object]]:
    if surface is None:
        return []
    vertex_map = surface.vertex_map()
    target_mid = _midpoint_xyz(_vertex_xyz_tuple(side_inner), _vertex_xyz_tuple(side_outer))
    side_inner_xy = (
        float(getattr(side_inner, "x", 0.0) or 0.0),
        float(getattr(side_inner, "y", 0.0) or 0.0),
    )
    side_outer_xy = (
        float(getattr(side_outer, "x", 0.0) or 0.0),
        float(getattr(side_outer, "y", 0.0) or 0.0),
    )
    candidates: list[tuple[float, int, float, object, object]] = []

    def add_candidate(first_id: str, second_id: str, *, priority: int) -> None:
        first = vertex_map.get(str(first_id or ""))
        second = vertex_map.get(str(second_id or ""))
        if first is None or second is None:
            return
        if _daylight_boundary_edge_is_generated_intersection_edge(first, second):
            return
        edge_mid = _midpoint_xyz(_vertex_xyz_tuple(first), _vertex_xyz_tuple(second))
        midpoint_distance = _xy_distance((target_mid[0], target_mid[1]), (edge_mid[0], edge_mid[1]))
        endpoint_distance = min(
            _xy_distance(side_inner_xy, (float(getattr(first, "x", 0.0) or 0.0), float(getattr(first, "y", 0.0) or 0.0))),
            _xy_distance(side_inner_xy, (float(getattr(second, "x", 0.0) or 0.0), float(getattr(second, "y", 0.0) or 0.0))),
            _xy_distance(side_outer_xy, (float(getattr(first, "x", 0.0) or 0.0), float(getattr(first, "y", 0.0) or 0.0))),
            _xy_distance(side_outer_xy, (float(getattr(second, "x", 0.0) or 0.0), float(getattr(second, "y", 0.0) or 0.0))),
        )
        segment_distance = _point_segment_distance_with_ratio(
            float(edge_mid[0]),
            float(edge_mid[1]),
            side_inner_xy[0],
            side_inner_xy[1],
            side_outer_xy[0],
            side_outer_xy[1],
        )[0]
        score = min(midpoint_distance, endpoint_distance, segment_distance)
        if score <= float(max_distance):
            candidates.append((score, int(priority), midpoint_distance, first, second))

    for first_id, second_id in _tin_surface_boundary_edges(surface):
        add_candidate(first_id, second_id, priority=0)
    for first_id, second_id in _tin_surface_triangle_edges(surface):
        add_candidate(first_id, second_id, priority=1)

    output: list[tuple[object, object]] = []
    seen_edges: set[tuple[str, str]] = set()
    for _score, _priority, _midpoint_distance, first, second in sorted(candidates, key=lambda row: (row[0], row[1], row[2])):
        edge_key = tuple(
            sorted(
                (
                    str(getattr(first, "vertex_id", "") or ""),
                    str(getattr(second, "vertex_id", "") or ""),
                )
            )
        )
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        output.append((first, second))
        if len(output) >= max(1, int(max_edges)):
            break
    return output


def _daylight_boundary_edge_is_generated_intersection_edge(first, second) -> bool:
    text = " ".join(
        [
            str(getattr(first, "vertex_id", "") or ""),
            str(getattr(second, "vertex_id", "") or ""),
            str(getattr(first, "notes", "") or ""),
            str(getattr(second, "notes", "") or ""),
        ]
    )
    return "intersection-curb-return-slope-band" in text or "intersection-slope-tie-in" in text


def _intersection_secondary_alignment_refs_from_sections(applied_section_set, *, intersection_id: str) -> set[str]:
    primary_refs = {
        str(getattr(section, "alignment_id", "") or "").strip()
        for section in list(getattr(applied_section_set, "sections", []) or [])
        if str(getattr(section, "active_intersection_leg_role", "") or "").strip() == "primary_through"
    }
    secondary_refs = {
        str(getattr(section, "alignment_id", "") or "").strip()
        for section in list(getattr(applied_section_set, "sections", []) or [])
        if str(getattr(section, "alignment_id", "") or "").strip()
        and str(getattr(section, "alignment_id", "") or "").strip() not in primary_refs
        and (
            not intersection_id
            or not str(getattr(section, "active_intersection_id", "") or "").strip()
            or str(getattr(section, "active_intersection_id", "") or "").strip() == intersection_id
        )
    }
    return secondary_refs


def _applied_section_slope_face_edge_points(
    section,
    *,
    side_label: str,
    fallback_band_width: float,
    fallback_band_slope: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    inner_offset, inner_z = _applied_section_terminal_edge(section, side_label=side_label, fallback_half_width=6.0)
    inner = _applied_section_xyz_at_offset(frame, inner_offset, inner_z)
    explicit_outer = _applied_section_explicit_slope_outer_point(section, side_label=side_label, inner_offset=inner_offset)
    if explicit_outer is not None:
        return inner, explicit_outer
    width_attr = "daylight_left_width" if side_label == "left" else "daylight_right_width"
    slope_attr = "daylight_left_slope" if side_label == "left" else "daylight_right_slope"
    width = max(float(getattr(section, width_attr, 0.0) or 0.0), 0.0)
    if width <= 1.0e-9:
        return None
    slope = abs(float(getattr(section, slope_attr, 0.0) or 0.0))
    if slope <= 1.0e-9:
        slope = abs(float(fallback_band_slope or 0.0))
    normal_x, normal_y = _applied_section_outward_normal(frame, side_label=side_label)
    return inner, (
        float(inner[0]) + normal_x * width,
        float(inner[1]) + normal_y * width,
        float(inner[2]) - abs(float(slope)) * width,
    )


def _applied_section_terminal_edge(section, *, side_label: str, fallback_half_width: float) -> tuple[float, float]:
    frame = getattr(section, "frame", None)
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    left_width = float(getattr(section, "surface_left_width", 0.0) or 0.0)
    right_width = float(getattr(section, "surface_right_width", 0.0) or 0.0)
    if left_width <= 0.0 and right_width <= 0.0:
        left_width = right_width = float(fallback_half_width)
    elif left_width <= 0.0:
        left_width = right_width
    elif right_width <= 0.0:
        right_width = left_width
    edge = (max(left_width, 0.1), frame_z) if side_label == "left" else (-max(right_width, 0.1), frame_z)
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"fg_surface", "ditch_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        z = float(getattr(point, "z", frame_z) or frame_z)
        if side_label == "left":
            if offset > edge[0] or (abs(offset - edge[0]) <= 1.0e-9 and z > edge[1]):
                edge = (offset, z)
        elif offset < edge[0] or (abs(offset - edge[0]) <= 1.0e-9 and z > edge[1]):
            edge = (offset, z)
    return edge


def _applied_section_explicit_slope_outer_point(section, *, side_label: str, inner_offset: float) -> tuple[float, float, float] | None:
    direction = 1.0 if side_label == "left" else -1.0
    candidates: list[object] = []
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"daylight_marker", "side_slope_surface", "bench_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if (offset - float(inner_offset)) * direction < -1.0e-9:
            continue
        candidates.append(point)
    if not candidates:
        return None
    chosen = max(
        candidates,
        key=lambda point: abs(float(getattr(point, "lateral_offset", 0.0) or 0.0) - float(inner_offset)),
    )
    return (
        float(getattr(chosen, "x", 0.0) or 0.0),
        float(getattr(chosen, "y", 0.0) or 0.0),
        float(getattr(chosen, "z", 0.0) or 0.0),
    )


def _applied_section_xyz_at_offset(frame, offset: float, z: float) -> tuple[float, float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    return (
        float(getattr(frame, "x", 0.0) or 0.0) + normal_x * float(offset),
        float(getattr(frame, "y", 0.0) or 0.0) + normal_y * float(offset),
        float(z),
    )


def _applied_section_outward_normal(frame, *, side_label: str) -> tuple[float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    if side_label == "right":
        return -normal_x, -normal_y
    return normal_x, normal_y


def _vertex_xyz_tuple(vertex) -> tuple[float, float, float]:
    return (
        float(getattr(vertex, "x", 0.0) or 0.0),
        float(getattr(vertex, "y", 0.0) or 0.0),
        float(getattr(vertex, "z", 0.0) or 0.0),
    )


def _midpoint_xyz(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        (float(first[0]) + float(second[0])) * 0.5,
        (float(first[1]) + float(second[1])) * 0.5,
        (float(first[2]) + float(second[2])) * 0.5,
    )


def _tin_surface_boundary_edges(surface) -> list[tuple[str, str]]:
    edge_counts: dict[tuple[str, str], int] = {}
    edge_values: dict[tuple[str, str], tuple[str, str]] = {}
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        ids = [
            str(getattr(triangle, "v1", "") or ""),
            str(getattr(triangle, "v2", "") or ""),
            str(getattr(triangle, "v3", "") or ""),
        ]
        for first_id, second_id in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            edge_values.setdefault(key, (first_id, second_id))
    return [edge_values[key] for key, count in edge_counts.items() if count == 1]


def _tin_surface_triangle_edges(surface) -> list[tuple[str, str]]:
    edge_values: dict[tuple[str, str], tuple[str, str]] = {}
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        ids = [
            str(getattr(triangle, "v1", "") or ""),
            str(getattr(triangle, "v2", "") or ""),
            str(getattr(triangle, "v3", "") or ""),
        ]
        for first_id, second_id in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            edge_values.setdefault(key, (first_id, second_id))
    return list(edge_values.values())


def _intersection_exclusion_polygon_from_sources(document, *, applied_section_set=None) -> dict[str, object] | None:
    applied = applied_section_set or to_applied_section_set(find_v1_applied_section_set(document))
    if applied is None:
        return None
    intersection_model = to_intersection_model(find_v1_intersection_model(document))
    prerequisite = corridor_intersection_patch_prerequisite_result(document)
    if str(getattr(prerequisite, "status", "") or "") == "missing":
        return None
    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    boundary_result = corridor_intersection_boundary_segment_result(
        tie_in_result,
        intersection_model=intersection_model,
    )
    patch_boundary_result = corridor_intersection_patch_boundary_result(boundary_result)
    practical = _intersection_practical_exclusion_polygon_from_boundary_segments(boundary_result, intersection_model=intersection_model)
    if practical is not None:
        return practical
    if not bool(getattr(patch_boundary_result, "closed", False)):
        return None
    points = [
        (float(getattr(row, "x", 0.0) or 0.0), float(getattr(row, "y", 0.0) or 0.0))
        for row in list(getattr(patch_boundary_result, "point_rows", []) or [])
        if str(getattr(row, "ring_role", "") or "outer") == "outer"
    ]
    if len(points) < 3:
        return None
    return {
        "intersection_id": str(getattr(patch_boundary_result, "intersection_id", "") or ""),
        "status": str(getattr(patch_boundary_result, "status", "") or ""),
        "points": points,
        "holes": _intersection_exclusion_rings_from_points(patch_boundary_result, "hole"),
        "islands": _intersection_exclusion_rings_from_points(patch_boundary_result, "island"),
        "area": float(getattr(patch_boundary_result, "polygon_area", 0.0) or 0.0),
        "boundary_source": "ordered_patch_boundary",
        "boundary_strategy": str(getattr(patch_boundary_result, "boundary_mode", "") or "ordered_patch_boundary"),
        "practical_boundary_aligned": False,
    }


def _intersection_practical_exclusion_polygon_from_boundary_segments(
    boundary_result: IntersectionBoundarySegmentResult,
    *,
    intersection_model=None,
) -> dict[str, object] | None:
    intersection_id = str(getattr(boundary_result, "intersection_id", "") or "").strip()
    grouped: dict[str, list[IntersectionBoundarySegmentRow]] = {}
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "tie_in":
            continue
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        if alignment_ref:
            grouped.setdefault(alignment_ref, []).append(row)
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip()
    if not primary_ref or primary_ref not in grouped:
        primary_ref = next(iter(grouped.keys()), "")
    primary_polygon = _intersection_tie_in_strip_polygon(grouped.get(primary_ref, []))
    if primary_polygon is None:
        return None
    pavement_strip_polygons: list[list[tuple[float, float, float]]] = [primary_polygon]
    polygons: list[list[tuple[float, float, float]]] = [primary_polygon]
    for alignment_ref, rows in grouped.items():
        if alignment_ref == primary_ref:
            continue
        polygon = _intersection_tie_in_strip_polygon(rows)
        if polygon is None:
            continue
        pavement_strip_polygons.append(polygon)
        outside = _xy_polygon_outer_difference_candidate(polygon, primary_polygon)
        polygons.append(outside or polygon)
    for polygon, _role in _intersection_curb_return_surface_parts(boundary_result):
        polygons.append(polygon)
    union_points = _xy_polygon_union_outer_boundary(polygons)
    if len(union_points) < 3:
        return None
    points = [(float(point[0]), float(point[1])) for point in union_points]
    area = abs(_xy_polygon_area(points))
    if area <= 1.0e-6:
        return None
    arc_stats = _intersection_curb_return_surface_arc_stats(boundary_result)
    edge_blend_face_count = len([
        role for _polygon, role in _intersection_curb_return_surface_parts(boundary_result)
        if str(role) == "curb_return_blend"
    ])
    if edge_blend_face_count:
        strategy = "structured_strip_curb_return_blend"
    elif int(arc_stats["arc_count"]):
        strategy = "structured_strip_curb_return"
    else:
        strategy = "structured_strip_union"
    return {
        "intersection_id": intersection_id,
        "status": str(getattr(boundary_result, "status", "") or "ready"),
        "points": points,
        "holes": [],
        "islands": [],
        "area": area,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": strategy,
        "practical_boundary_aligned": True,
        "edge_blend_face_count": edge_blend_face_count,
        "curb_return_arc_count": int(arc_stats["arc_count"]),
        "curb_return_arc_polylines": _intersection_curb_return_arc_polylines_xy(boundary_result),
        "pavement_strip_polygons": _intersection_xyz_polygons_to_xy(pavement_strip_polygons),
    }


def _intersection_xyz_polygons_to_xy(polygons: list[list[tuple[float, float, float]]]) -> list[list[tuple[float, float]]]:
    output: list[list[tuple[float, float]]] = []
    for polygon in list(polygons or []):
        points = [(float(point[0]), float(point[1])) for point in list(polygon or [])]
        if len(points) >= 3 and abs(_xy_polygon_area(points)) > 1.0e-6:
            output.append(points)
    return output


def _intersection_pavement_strip_polygons_xy_from_boundary_result(boundary_result) -> list[list[tuple[float, float]]]:
    grouped: dict[str, list[IntersectionBoundarySegmentRow]] = {}
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "tie_in":
            continue
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        if alignment_ref:
            grouped.setdefault(alignment_ref, []).append(row)
    polygons: list[list[tuple[float, float, float]]] = []
    for rows in grouped.values():
        polygon = _intersection_tie_in_strip_polygon(rows)
        if polygon is not None:
            polygons.append(polygon)
    return _intersection_xyz_polygons_to_xy(polygons)


def _intersection_curb_return_arc_polylines_xy(boundary_result) -> list[list[tuple[float, float]]]:
    if boundary_result is None:
        return []
    output: list[list[tuple[float, float]]] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        points = [
            (float(point[0]), float(point[1]))
            for point in list(getattr(row, "chord_points_xyz", []) or [])
            if len(tuple(point or ())) >= 2
        ]
        if len(points) >= 2:
            output.append(points)
    return output


def _intersection_exclusion_rings_from_points(patch_boundary_result, ring_role: str) -> list[list[tuple[float, float]]]:
    grouped: dict[str, list[object]] = {}
    target_role = str(ring_role or "").strip()
    for row in list(getattr(patch_boundary_result, "point_rows", []) or []):
        if str(getattr(row, "ring_role", "") or "outer").strip() != target_role:
            continue
        ring_id = str(getattr(row, "ring_id", "") or target_role)
        grouped.setdefault(ring_id, []).append(row)
    output: list[list[tuple[float, float]]] = []
    for rows in grouped.values():
        ordered = sorted(rows, key=lambda row: int(getattr(row, "order_index", 0) or 0))
        points = [
            (float(getattr(row, "x", 0.0) or 0.0), float(getattr(row, "y", 0.0) or 0.0))
            for row in ordered
        ]
        if len(points) >= 3:
            output.append(points)
    return output


def _intersection_daylight_protection_offset(exclusion: dict[str, object], polygon: list[tuple[float, float]]) -> float:
    points = list(polygon or [])
    if len(points) < 3:
        return 0.0
    area = abs(float(exclusion.get("area", 0.0) or _xy_polygon_area(points)))
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    bbox_axis = max((max(xs) - min(xs)) if xs else 0.0, (max(ys) - min(ys)) if ys else 0.0)
    area_scale = area ** 0.5 if area > 0.0 else 0.0
    return max(4.0, min(max(area_scale * 0.18, bbox_axis * 0.08), 8.0))


def _xy_expand_polygon_from_centroid(points: list[tuple[float, float]], offset: float) -> list[tuple[float, float]]:
    if len(points) < 3 or float(offset or 0.0) <= 0.0:
        return list(points or [])
    centroid = (
        sum(float(point[0]) for point in points) / len(points),
        sum(float(point[1]) for point in points) / len(points),
    )
    expanded: list[tuple[float, float]] = []
    for point in points:
        dx = float(point[0]) - centroid[0]
        dy = float(point[1]) - centroid[1]
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= 1.0e-9:
            expanded.append((float(point[0]), float(point[1])))
            continue
        scale = (distance + float(offset or 0.0)) / distance
        expanded.append((centroid[0] + dx * scale, centroid[1] + dy * scale))
    return expanded


def _intersection_control_section_indices(applied_section_set, *, intersection_id: str = "") -> set[int]:
    if applied_section_set is None:
        return set()
    target_intersection = str(intersection_id or "").strip()
    indices: set[int] = set()
    for index, section in enumerate(list(getattr(applied_section_set, "sections", []) or [])):
        active_intersection = str(getattr(section, "active_intersection_id", "") or "").strip()
        if active_intersection and (not target_intersection or active_intersection == target_intersection):
            indices.add(index)
            continue
        if target_intersection:
            continue
        control_area = str(getattr(section, "active_intersection_control_area_id", "") or "").strip()
        control_refs = [str(ref or "").strip() for ref in list(getattr(section, "active_intersection_control_region_refs", []) or [])]
        region_id = str(getattr(section, "region_id", "") or "").strip()
        if control_area or (region_id and region_id in control_refs):
            indices.add(index)
    return indices


def _slope_face_triangle_uses_intersection_control_section(triangle, *, control_section_indices: set[int]) -> bool:
    if not control_section_indices:
        return False
    candidate_indices: set[int] = set()
    for value in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", "")):
        parsed = _parse_slope_face_vertex_id(str(value or ""))
        if parsed is not None:
            candidate_indices.add(int(parsed[0]))
    candidate_indices.update(_parse_slope_face_triangle_span_section_indices(str(getattr(triangle, "triangle_id", "") or "")))
    return bool(candidate_indices.intersection(control_section_indices))


def _parse_slope_face_triangle_span_section_indices(triangle_id: str) -> set[int]:
    parts = str(triangle_id or "").split(":")
    indices: set[int] = set()
    for index, token in enumerate(parts[:-1]):
        if token != "span":
            continue
        try:
            span_index = int(parts[index + 1])
        except Exception:
            continue
        indices.add(span_index)
        indices.add(span_index + 1)
    return indices


def _xy_point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = float(point[0]), float(point[1])
    inside = False
    count = len(polygon)
    if count < 3:
        return False
    previous = polygon[-1]
    for current in polygon:
        xi, yi = float(current[0]), float(current[1])
        xj, yj = float(previous[0]), float(previous[1])
        if ((yi > y) != (yj > y)) and x < ((xj - xi) * (y - yi) / ((yj - yi) or 1.0e-12) + xi):
            inside = not inside
        previous = current
    return inside


def _xy_triangle_intersects_polygon(triangle: list[tuple[float, float]], polygon: list[tuple[float, float]]) -> bool:
    return bool(_xy_triangle_polygon_intersection_kind(triangle, polygon))


def _xy_triangle_polygon_intersection_kind(triangle: list[tuple[float, float]], polygon: list[tuple[float, float]]) -> str:
    if len(triangle) < 3 or len(polygon) < 3:
        return ""
    triangle_edges = _xy_closed_edges(triangle[:3])
    polygon_edges = _xy_closed_edges(polygon)
    for first_start, first_end in triangle_edges:
        for second_start, second_end in polygon_edges:
            if _xy_segments_intersect(first_start, first_end, second_start, second_end):
                return "edge_crossing"
    centroid = (
        sum(float(point[0]) for point in triangle[:3]) / 3.0,
        sum(float(point[1]) for point in triangle[:3]) / 3.0,
    )
    if _xy_point_in_polygon(centroid, polygon):
        return "centroid_inside"
    if any(_xy_point_in_polygon(point, polygon) for point in triangle[:3]):
        return "triangle_vertex_inside"
    if any(_xy_point_in_triangle(point, (triangle[0], triangle[1], triangle[2])) for point in polygon):
        return "polygon_vertex_inside_triangle"
    return ""


def _xy_triangle_near_curb_return_arc_protection(
    triangle: list[tuple[float, float]],
    arc_polylines: list[list[tuple[float, float]]],
    *,
    max_distance: float,
) -> bool:
    if len(triangle) < 3 or float(max_distance or 0.0) <= 0.0:
        return False
    centroid = (
        sum(float(point[0]) for point in triangle[:3]) / 3.0,
        sum(float(point[1]) for point in triangle[:3]) / 3.0,
    )
    triangle_edges = _xy_closed_edges(triangle[:3])
    limit = float(max_distance)
    for polyline in list(arc_polylines or []):
        points = list(polyline or [])
        if len(points) < 2:
            continue
        for index in range(len(points) - 1):
            arc_start = points[index]
            arc_end = points[index + 1]
            if _point_segment_distance_with_ratio(centroid[0], centroid[1], arc_start[0], arc_start[1], arc_end[0], arc_end[1])[0] <= limit:
                return True
            for point in triangle[:3]:
                if _point_segment_distance_with_ratio(point[0], point[1], arc_start[0], arc_start[1], arc_end[0], arc_end[1])[0] <= limit:
                    return True
            for tri_start, tri_end in triangle_edges:
                if _xy_segment_distance(tri_start, tri_end, arc_start, arc_end) <= limit:
                    return True
    return False


def _xy_triangle_intrudes_pavement_strip_protection(
    triangle: list[tuple[float, float]],
    pavement_strip_polygons: list[list[tuple[float, float]]],
) -> bool:
    if len(triangle) < 3:
        return False
    centroid = (
        sum(float(point[0]) for point in triangle[:3]) / 3.0,
        sum(float(point[1]) for point in triangle[:3]) / 3.0,
    )
    triangle_edges = _xy_closed_edges(triangle[:3])
    for polygon in list(pavement_strip_polygons or []):
        strip = list(polygon or [])
        if len(strip) < 3:
            continue
        if _xy_point_in_polygon(centroid, strip):
            return True
        if any(_xy_point_in_polygon(point, strip) for point in triangle[:3]):
            return True
        for first_start, first_end in triangle_edges:
            for second_start, second_end in _xy_closed_edges(strip):
                if _xy_segments_cross_strict(first_start, first_end, second_start, second_end):
                    return True
    return False


def _xy_segments_cross_strict(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def orientation(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)
    return o1 * o2 < -1.0e-12 and o3 * o4 < -1.0e-12


def _xy_segment_distance(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> float:
    if _xy_segments_intersect(first_start, first_end, second_start, second_end):
        return 0.0
    return min(
        _point_segment_distance_with_ratio(first_start[0], first_start[1], second_start[0], second_start[1], second_end[0], second_end[1])[0],
        _point_segment_distance_with_ratio(first_end[0], first_end[1], second_start[0], second_start[1], second_end[0], second_end[1])[0],
        _point_segment_distance_with_ratio(second_start[0], second_start[1], first_start[0], first_start[1], first_end[0], first_end[1])[0],
        _point_segment_distance_with_ratio(second_end[0], second_end[1], first_start[0], first_start[1], first_end[0], first_end[1])[0],
    )


def _xy_closed_edges(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    if len(points) < 2:
        return []
    return [(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]


def _xy_polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index in range(len(points)):
        current = points[index]
        nxt = points[(index + 1) % len(points)]
        area += float(current[0]) * float(nxt[1])
        area -= float(nxt[0]) * float(current[1])
    return area * 0.5


def _xy_polygon_is_convex(points: list[tuple[float, float]]) -> bool:
    if len(points) < 3:
        return False
    sign = 0
    for index in range(len(points)):
        a = points[index]
        b = points[(index + 1) % len(points)]
        c = points[(index + 2) % len(points)]
        cross = ((b[0] - a[0]) * (c[1] - b[1])) - ((b[1] - a[1]) * (c[0] - b[0]))
        if abs(cross) <= 1.0e-9:
            continue
        current_sign = 1 if cross > 0.0 else -1
        if sign and current_sign != sign:
            return False
        sign = current_sign
    return bool(sign)


def _xy_subtract_convex_polygon_from_polygon(
    source_polygon: list[dict[str, object]],
    exclusion_polygon: list[tuple[float, float]],
) -> list[list[dict[str, object]]]:
    """Return source polygon fragments outside a convex exclusion polygon."""

    if len(source_polygon) < 3 or len(exclusion_polygon) < 3 or not _xy_polygon_is_convex(exclusion_polygon):
        return []
    orientation = 1.0 if _xy_polygon_area(exclusion_polygon) >= 0.0 else -1.0
    remaining_inside = _dedupe_xy_points(source_polygon)
    outside_fragments: list[list[dict[str, object]]] = []
    for edge_start, edge_end in _xy_closed_edges(exclusion_polygon):
        inside_fragment, outside_fragment = _split_polygon_by_oriented_halfplane(
            remaining_inside,
            edge_start,
            edge_end,
            orientation=orientation,
        )
        outside_fragment = _dedupe_xy_points(outside_fragment)
        if len(outside_fragment) >= 3 and abs(_xy_polygon_area([(point["x"], point["y"]) for point in outside_fragment])) > 1.0e-9:
            outside_fragments.append(outside_fragment)
        remaining_inside = _dedupe_xy_points(inside_fragment)
        if len(remaining_inside) < 3:
            break
    return outside_fragments


def _xy_exact_cut_exclusion_parts(polygon: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    if len(polygon) < 3:
        return []
    if _xy_polygon_is_convex(polygon):
        return [polygon]
    triangles = _xy_triangulate_simple_polygon_points(polygon)
    return [triangle for triangle in triangles if len(triangle) == 3 and abs(_xy_polygon_area(triangle)) > 1.0e-9]


def _xy_subtract_convex_polygon_parts_from_polygon(
    source_polygon: list[dict[str, object]],
    exclusion_parts: list[list[tuple[float, float]]],
) -> list[list[dict[str, object]]]:
    fragments = [_dedupe_xy_points(source_polygon)]
    for exclusion_part in list(exclusion_parts or []):
        next_fragments: list[list[dict[str, object]]] = []
        for fragment in fragments:
            next_fragments.extend(_xy_subtract_convex_polygon_from_polygon(fragment, exclusion_part))
        fragments = [
            fragment for fragment in next_fragments
            if len(fragment) >= 3 and abs(_xy_polygon_area([(point["x"], point["y"]) for point in fragment])) > 1.0e-9
        ]
        if not fragments:
            break
    return fragments


def _xy_subtract_exclusion_area_from_polygon(
    source_polygon: list[dict[str, object]],
    *,
    exclusion_parts: list[list[tuple[float, float]]],
    hole_parts: list[list[tuple[float, float]]] | None = None,
) -> list[list[dict[str, object]]]:
    outside_fragments = _xy_subtract_convex_polygon_parts_from_polygon(source_polygon, exclusion_parts)
    hole_fragments: list[list[dict[str, object]]] = []
    for hole_part in list(hole_parts or []):
        clipped = _xy_intersect_polygon_with_convex_polygon(source_polygon, hole_part)
        if len(clipped) >= 3 and abs(_xy_polygon_area([(point["x"], point["y"]) for point in clipped])) > 1.0e-9:
            hole_fragments.append(clipped)
    return outside_fragments + hole_fragments


def _xy_intersect_polygon_with_convex_polygon(
    source_polygon: list[dict[str, object]],
    clip_polygon: list[tuple[float, float]],
) -> list[dict[str, object]]:
    if len(source_polygon) < 3 or len(clip_polygon) < 3 or not _xy_polygon_is_convex(clip_polygon):
        return []
    orientation = 1.0 if _xy_polygon_area(clip_polygon) >= 0.0 else -1.0
    output = _dedupe_xy_points(source_polygon)
    for edge_start, edge_end in _xy_closed_edges(clip_polygon):
        inside, _outside = _split_polygon_by_oriented_halfplane(
            output,
            edge_start,
            edge_end,
            orientation=orientation,
        )
        output = _dedupe_xy_points(inside)
        if len(output) < 3:
            return []
    return output


def _xy_triangulate_simple_polygon_points(points: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    if len(points) < 3:
        return []
    polygon_area = _xy_polygon_area(points)
    if abs(polygon_area) <= 1.0e-9:
        return []
    remaining = list(range(len(points)))
    if polygon_area < 0.0:
        remaining.reverse()
    triangles: list[list[tuple[float, float]]] = []
    guard = 0
    while len(remaining) > 3 and guard < len(points) * len(points):
        guard += 1
        ear_index = None
        for index in range(len(remaining)):
            prev_index = remaining[(index - 1) % len(remaining)]
            current_index = remaining[index]
            next_index = remaining[(index + 1) % len(remaining)]
            if not _xy_points_form_ear(points, remaining, prev_index, current_index, next_index):
                continue
            ear_index = index
            triangles.append([points[prev_index], points[current_index], points[next_index]])
            break
        if ear_index is None:
            if triangles and abs(_xy_polygon_area([points[index] for index in remaining])) <= 1.0e-6:
                break
            return []
        remaining.pop(ear_index)
    if len(remaining) == 3:
        triangle = [points[remaining[0]], points[remaining[1]], points[remaining[2]]]
        if abs(_xy_polygon_area(triangle)) > 1.0e-9:
            triangles.append(triangle)
    return triangles


def _xy_points_form_ear(
    points: list[tuple[float, float]],
    remaining: list[int],
    prev_index: int,
    current_index: int,
    next_index: int,
) -> bool:
    prev_point = points[prev_index]
    current_point = points[current_index]
    next_point = points[next_index]
    if _xy_triangle_area_from_points(prev_point, current_point, next_point) <= 1.0e-9:
        return False
    triangle = (prev_point, current_point, next_point)
    for candidate_index in remaining:
        if candidate_index in {prev_index, current_index, next_index}:
            continue
        if _xy_point_in_triangle(points[candidate_index], triangle):
            return False
    return True


def _xy_triangle_area_from_points(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    return 0.5 * ((float(b[0]) - float(a[0])) * (float(c[1]) - float(a[1])) - (float(b[1]) - float(a[1])) * (float(c[0]) - float(a[0])))


def _split_polygon_by_oriented_halfplane(
    polygon: list[dict[str, object]],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
    *,
    orientation: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if len(polygon) < 3:
        return [], []
    inside: list[dict[str, object]] = []
    outside: list[dict[str, object]] = []
    for index, current in enumerate(polygon):
        previous = polygon[index - 1]
        previous_inside = _point_in_oriented_halfplane(previous, edge_start, edge_end, orientation=orientation)
        current_inside = _point_in_oriented_halfplane(current, edge_start, edge_end, orientation=orientation)
        if current_inside:
            if not previous_inside:
                intersection = _halfplane_segment_intersection(previous, current, edge_start, edge_end)
                if intersection:
                    inside.append(intersection)
                    outside.append(intersection)
            inside.append(current)
        else:
            if previous_inside:
                intersection = _halfplane_segment_intersection(previous, current, edge_start, edge_end)
                if intersection:
                    inside.append(intersection)
                    outside.append(intersection)
            outside.append(current)
    return _dedupe_xy_points(inside), _dedupe_xy_points(outside)


def _point_in_oriented_halfplane(
    point: dict[str, object],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
    *,
    orientation: float,
) -> bool:
    cross = (
        (float(edge_end[0]) - float(edge_start[0])) * (float(point["y"]) - float(edge_start[1]))
        - (float(edge_end[1]) - float(edge_start[1])) * (float(point["x"]) - float(edge_start[0]))
    )
    return cross * float(orientation or 1.0) >= -1.0e-9


def _halfplane_segment_intersection(
    first: dict[str, object],
    second: dict[str, object],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
) -> dict[str, object] | None:
    x1 = float(first["x"])
    y1 = float(first["y"])
    x2 = float(second["x"])
    y2 = float(second["y"])
    x3 = float(edge_start[0])
    y3 = float(edge_start[1])
    x4 = float(edge_end[0])
    y4 = float(edge_end[1])
    denominator = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
    if abs(denominator) <= 1.0e-12:
        return None
    px = (((x1 * y2 - y1 * x2) * (x3 - x4)) - ((x1 - x2) * (x3 * y4 - y3 * x4))) / denominator
    py = (((x1 * y2 - y1 * x2) * (y3 - y4)) - ((y1 - y2) * (x3 * y4 - y3 * x4))) / denominator
    segment_length = math.hypot(x2 - x1, y2 - y1)
    t = 0.0 if segment_length <= 1.0e-12 else math.hypot(px - x1, py - y1) / segment_length
    t = max(0.0, min(1.0, t))
    z = float(first["z"]) + (float(second["z"]) - float(first["z"])) * t
    return {
        "x": px,
        "y": py,
        "z": z,
        "source": f"{first.get('source', '')}|{second.get('source', '')}:intersection",
    }


def _dedupe_xy_points(points: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for point in list(points or []):
        if output:
            previous = output[-1]
            if abs(float(previous["x"]) - float(point["x"])) <= 1.0e-9 and abs(float(previous["y"]) - float(point["y"])) <= 1.0e-9:
                continue
        output.append(point)
    if len(output) > 1:
        first = output[0]
        last = output[-1]
        if abs(float(first["x"]) - float(last["x"])) <= 1.0e-9 and abs(float(first["y"]) - float(last["y"])) <= 1.0e-9:
            output.pop()
    return output


def _build_intersection_surface_patch_tin(
    *,
    project_id: str,
    corridor_model,
    applied_section_set,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    surface_id: str,
):
    """Build a first-slice intersection patch TIN from intersection Applied Section fg points."""

    from ..models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex

    control_refs = set(str(value or "") for value in list(getattr(prerequisite, "control_region_refs", ()) or ()) if str(value or ""))
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    sections = _intersection_patch_center_sections(
        _intersection_patch_sections(applied_section_set, prerequisite),
        intersection_model=intersection_model,
        prerequisite=prerequisite,
    )
    superelevation_context = _intersection_patch_superelevation_context(sections)
    vertices: list[TINVertex] = []
    seen_xy: set[tuple[float, float]] = set()
    for section_index, section in enumerate(sections, start=1):
        alignment_id = str(getattr(section, "alignment_id", "") or "")
        station = float(getattr(section, "station", 0.0) or 0.0)
        for point_index, point in enumerate(list(getattr(section, "point_rows", []) or []), start=1):
            if str(getattr(point, "point_role", "") or "") != "fg_surface":
                continue
            x = float(getattr(point, "x", 0.0) or 0.0)
            y = float(getattr(point, "y", 0.0) or 0.0)
            z = float(getattr(point, "z", 0.0) or 0.0)
            xy_key = (round(x, 6), round(y, 6))
            if xy_key in seen_xy:
                continue
            seen_xy.add(xy_key)
            vertices.append(
                TINVertex(
                    vertex_id=f"v{len(vertices) + 1}",
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=f"{getattr(section, 'applied_section_id', '')}:fg:{point_index}",
                    notes=f"alignment={alignment_id}; station={station:.3f}; region={getattr(section, 'region_id', '')}",
                )
            )
    if len(vertices) < 3:
        raise ValueError("intersection_patch_boundary_too_few_points: at least three unique fg_surface points are required.")

    grading_policy = _intersection_grading_policy_for(intersection_model, intersection_id)
    grading_mode = str(getattr(grading_policy, "mode", "") or "use_normal_superelevation")
    original_z_values = [vertex.z for vertex in vertices]
    grading_plane = _intersection_grading_plane_for_policy(vertices, grading_policy)
    vertices = _apply_intersection_grading_policy(vertices, grading_policy, grading_plane=grading_plane)
    patch_boundary_point_count = 0
    patch_boundary_source_segment_count = 0
    patch_boundary_closed_value = 0
    patch_boundary_diagnostic_count = 0
    patch_boundary_polygon_area = 0.0
    patch_boundary_self_crossing_value = 0
    patch_boundary_ring_count = 0
    patch_boundary_hole_ring_count = 0
    patch_boundary_island_ring_count = 0
    patch_boundary_source = "convex_hull_fallback"
    boundary_segment_result = None
    try:
        tie_in_result = corridor_intersection_tie_in_edge_result(
            applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
        boundary_segment_result = corridor_intersection_boundary_segment_result(
            tie_in_result,
            intersection_model=intersection_model,
        )
        patch_boundary_result = corridor_intersection_patch_boundary_result(boundary_segment_result)
        patch_boundary_point_count = int(getattr(patch_boundary_result, "boundary_point_count", 0) or 0)
        patch_boundary_source_segment_count = int(getattr(patch_boundary_result, "source_segment_count", 0) or 0)
        patch_boundary_closed_value = 1 if bool(getattr(patch_boundary_result, "closed", False)) else 0
        patch_boundary_diagnostic_count = len(list(getattr(patch_boundary_result, "diagnostic_rows", []) or []))
        patch_boundary_polygon_area = float(getattr(patch_boundary_result, "polygon_area", 0.0) or 0.0)
        patch_boundary_self_crossing_value = 1 if bool(getattr(patch_boundary_result, "self_crossing", False)) else 0
        patch_boundary_ring_count = int(getattr(patch_boundary_result, "ring_count", 0) or 0)
        patch_boundary_hole_ring_count = int(getattr(patch_boundary_result, "hole_ring_count", 0) or 0)
        patch_boundary_island_ring_count = int(getattr(patch_boundary_result, "island_ring_count", 0) or 0)
        if patch_boundary_closed_value and patch_boundary_point_count >= 3:
            ordered_vertices = _intersection_patch_boundary_tin_vertices(
                patch_boundary_result,
                source_vertices=vertices,
                grading_plane=grading_plane,
                grading_mode=grading_mode,
            )
            if len(ordered_vertices) >= 3:
                vertices = ordered_vertices
                patch_boundary_source = "ordered_patch_boundary"
    except Exception:
        patch_boundary_diagnostic_count = 1
    if patch_boundary_source != "ordered_patch_boundary":
        vertices = _intersection_patch_boundary_hull(vertices)
    if len(vertices) < 3:
        raise ValueError("intersection_patch_boundary_too_few_points: at least three unique patch boundary points are required.")
    centroid_x = sum(vertex.x for vertex in vertices) / len(vertices)
    centroid_y = sum(vertex.y for vertex in vertices) / len(vertices)
    centroid_z = sum(vertex.z for vertex in vertices) / len(vertices)
    center = TINVertex(
        vertex_id="v:center",
        x=centroid_x,
        y=centroid_y,
        z=centroid_z,
        source_point_ref=f"{surface_id}:centroid",
        notes="intersection patch centroid",
    )
    all_vertices = [*vertices, center]
    drainage_hint = _intersection_patch_drainage_hint(vertices, all_vertices)
    triangulation = _intersection_patch_structured_strip_triangulation(
        tie_in_result if "tie_in_result" in locals() else None,
        source_vertices=vertices,
        center=center,
        intersection_model=intersection_model,
        boundary_segment_result=boundary_segment_result,
        intersection_id=intersection_id,
        policy=_intersection_patch_triangulation_policy(intersection_model, intersection_id),
    )
    if not list(triangulation.get("triangles", []) or []):
        triangulation = _intersection_patch_ordered_polygon_triangulation(
        vertices,
        center,
        intersection_id=intersection_id,
        policy=_intersection_patch_triangulation_policy(intersection_model, intersection_id),
        )
    triangles = list(triangulation["triangles"])
    all_vertices = list(triangulation.get("vertices", all_vertices) or all_vertices)
    if len(triangles) < 1:
        raise ValueError("intersection_patch_degenerate_triangle: ordered patch boundary did not produce usable triangles.")
    shape_quality = _intersection_patch_shape_quality(all_vertices, triangles)
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        surface_id=surface_id,
        surface_kind="intersection_surface",
        label=f"Intersection Surface - {intersection_id or getattr(corridor_model, 'corridor_id', '')}",
        source_refs=[
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            intersection_id,
            *list(getattr(prerequisite, "control_region_refs", ()) or ()),
        ],
        vertex_rows=all_vertices,
        triangle_rows=triangles,
        boundary_refs=[f"{surface_id}:boundary"],
        quality_rows=[
            TINQualityRow(f"{surface_id}:patch_boundary_point_count", "patch_boundary_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_source", "patch_boundary_source", patch_boundary_source),
            TINQualityRow(f"{surface_id}:participating_alignment_count", "participating_alignment_count", int(getattr(prerequisite, "participating_alignment_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:control_region_count", "control_region_count", int(getattr(prerequisite, "control_region_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:tie_in_edge_count", "tie_in_edge_count", int(getattr(prerequisite, "tie_in_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_triangle_count", "patch_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:patch_degenerate_triangle_count", "patch_degenerate_triangle_count", int(triangulation["degenerate_count"]), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_edge_max_length", "patch_boundary_edge_max_length", float(triangulation["max_edge_length"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_edge_long_count", "patch_boundary_edge_long_count", int(triangulation["long_edge_count"]), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_edge_long_factor", "patch_boundary_edge_long_factor", float(triangulation["long_edge_factor"]), "factor"),
            TINQualityRow(f"{surface_id}:patch_boundary_edge_long_limit", "patch_boundary_edge_long_limit", float(triangulation["long_edge_limit"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_edge_max_length_policy", "patch_boundary_edge_max_length_policy", float(triangulation["max_boundary_edge_length_policy"]), "m"),
            TINQualityRow(f"{surface_id}:patch_triangulation_mode", "patch_triangulation_mode", str(shape_quality["triangulation_mode"])),
            TINQualityRow(f"{surface_id}:patch_surface_boundary_strategy", "patch_surface_boundary_strategy", str(triangulation.get("boundary_strategy", "ordered_polygon"))),
            TINQualityRow(f"{surface_id}:patch_structured_strip_count", "patch_structured_strip_count", int(triangulation.get("structured_strip_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_curb_return_surface_edge_count", "patch_curb_return_surface_edge_count", int(triangulation.get("curb_return_surface_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_curb_return_arc_count", "patch_curb_return_arc_count", int(triangulation.get("curb_return_arc_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_curb_return_arc_sample_count", "patch_curb_return_arc_sample_count", int(triangulation.get("curb_return_arc_sample_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_curb_return_arc_segment_count", "patch_curb_return_arc_segment_count", int(triangulation.get("curb_return_arc_segment_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_edge_blend_face_count", "patch_edge_blend_face_count", int(triangulation.get("edge_blend_face_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_role_summary", "patch_boundary_role_summary", str(triangulation.get("boundary_role_summary", ""))),
            TINQualityRow(f"{surface_id}:patch_boundary_pavement_tie_in_edge_count", "patch_boundary_pavement_tie_in_edge_count", int(triangulation.get("pavement_tie_in_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_stem_tie_in_edge_count", "patch_boundary_stem_tie_in_edge_count", int(triangulation.get("stem_tie_in_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_overlap_cut_edge_count", "patch_boundary_overlap_cut_edge_count", int(triangulation.get("overlap_cut_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_curb_return_edge_count", "patch_boundary_curb_return_edge_count", int(triangulation.get("curb_return_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_x", "patch_boundary_bbox_x", float(shape_quality["bbox_x"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_y", "patch_boundary_bbox_y", float(shape_quality["bbox_y"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_aspect_ratio", "patch_boundary_bbox_aspect_ratio", float(shape_quality["bbox_aspect_ratio"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_min_quality", "patch_triangle_min_quality", float(shape_quality["triangle_min_quality"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_skinny_count", "patch_triangle_skinny_count", int(shape_quality["skinny_triangle_count"]), "count"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_point_count", "ordered_patch_boundary_point_count", patch_boundary_point_count, "count"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_source_segment_count", "ordered_patch_boundary_source_segment_count", patch_boundary_source_segment_count, "count"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_closed", "ordered_patch_boundary_closed", patch_boundary_closed_value, "boolean"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_diagnostic_count", "ordered_patch_boundary_diagnostic_count", patch_boundary_diagnostic_count, "count"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_polygon_area", "ordered_patch_boundary_polygon_area", patch_boundary_polygon_area, "m2"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_self_crossing", "ordered_patch_boundary_self_crossing", patch_boundary_self_crossing_value, "boolean"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_ring_count", "ordered_patch_boundary_ring_count", patch_boundary_ring_count, "count"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_hole_ring_count", "ordered_patch_boundary_hole_ring_count", patch_boundary_hole_ring_count, "count"),
            TINQualityRow(f"{surface_id}:ordered_patch_boundary_island_ring_count", "ordered_patch_boundary_island_ring_count", patch_boundary_island_ring_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_grading_mode", "intersection_grading_mode", grading_mode),
            TINQualityRow(f"{surface_id}:intersection_grading_z_delta_max", "intersection_grading_z_delta_max", _max_abs_delta(original_z_values, [vertex.z for vertex in vertices]), "m"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_source_count", "intersection_superelevation_source_count", int(superelevation_context["source_count"]), "count"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_transition_count", "intersection_superelevation_transition_count", int(superelevation_context["transition_count"]), "count"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_left_min", "intersection_superelevation_left_min", float(superelevation_context["left_min"]), "%"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_left_max", "intersection_superelevation_left_max", float(superelevation_context["left_max"]), "%"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_right_min", "intersection_superelevation_right_min", float(superelevation_context["right_min"]), "%"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_right_max", "intersection_superelevation_right_max", float(superelevation_context["right_max"]), "%"),
            TINQualityRow(f"{surface_id}:intersection_superelevation_context", "intersection_superelevation_context", str(superelevation_context["summary"])),
            TINQualityRow(f"{surface_id}:intersection_low_point_candidate_count", "intersection_low_point_candidate_count", int(drainage_hint["low_point_candidate_count"]), "count"),
            TINQualityRow(f"{surface_id}:intersection_low_point_x", "intersection_low_point_x", float(drainage_hint["low_point_x"]), "m"),
            TINQualityRow(f"{surface_id}:intersection_low_point_y", "intersection_low_point_y", float(drainage_hint["low_point_y"]), "m"),
            TINQualityRow(f"{surface_id}:intersection_low_point_z", "intersection_low_point_z", float(drainage_hint["low_point_z"]), "m"),
            TINQualityRow(f"{surface_id}:intersection_low_point_source_ref", "intersection_low_point_source_ref", str(drainage_hint["low_point_source_ref"])),
            TINQualityRow(f"{surface_id}:intersection_boundary_to_low_flow_hint_count", "intersection_boundary_to_low_flow_hint_count", int(drainage_hint["flow_hint_count"]), "count"),
            TINQualityRow(f"{surface_id}:intersection_boundary_to_low_flow_hint_summary", "intersection_boundary_to_low_flow_hint_summary", str(drainage_hint["flow_hint_summary"])),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{surface_id}:provenance:applied-sections",
                source_kind="intersection_applied_section_fg_surface",
                source_ref=str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
                notes=f"intersection={intersection_id}; control_regions={','.join(sorted(control_refs))}",
            )
        ],
    )


def _intersection_patch_drainage_hint(boundary_vertices: list[object], all_vertices: list[object]) -> dict[str, object]:
    vertices = [vertex for vertex in list(all_vertices or []) if vertex is not None]
    if not vertices:
        return {
            "low_point_candidate_count": 0,
            "low_point_x": 0.0,
            "low_point_y": 0.0,
            "low_point_z": 0.0,
            "low_point_source_ref": "",
            "flow_hint_count": 0,
            "flow_hint_summary": "no intersection patch vertices",
        }
    low_z = min(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices)
    low_points = [
        vertex for vertex in vertices
        if abs(float(getattr(vertex, "z", 0.0) or 0.0) - low_z) <= 0.001
    ]
    low_point = low_points[0]
    low_x = float(getattr(low_point, "x", 0.0) or 0.0)
    low_y = float(getattr(low_point, "y", 0.0) or 0.0)
    boundary = [vertex for vertex in list(boundary_vertices or []) if vertex is not None]
    flow_sources = [
        vertex for vertex in boundary
        if float(getattr(vertex, "z", 0.0) or 0.0) > low_z + 0.001
    ]
    if flow_sources:
        avg_dx = sum(low_x - float(getattr(vertex, "x", 0.0) or 0.0) for vertex in flow_sources) / len(flow_sources)
        avg_dy = sum(low_y - float(getattr(vertex, "y", 0.0) or 0.0) for vertex in flow_sources) / len(flow_sources)
        summary = f"boundary_to_low count={len(flow_sources)}; avg_vector=({avg_dx:.3f},{avg_dy:.3f})"
    else:
        summary = "boundary_to_low count=0; patch appears flat at low-point tolerance"
    return {
        "low_point_candidate_count": len(low_points),
        "low_point_x": low_x,
        "low_point_y": low_y,
        "low_point_z": low_z,
        "low_point_source_ref": str(getattr(low_point, "source_point_ref", "") or ""),
        "flow_hint_count": len(flow_sources),
        "flow_hint_summary": summary,
    }


def _intersection_patch_boundary_tin_vertices(
    patch_boundary_result: IntersectionPatchBoundaryResult,
    *,
    source_vertices: list[object],
    grading_plane: tuple[float, float, float] | None = None,
    grading_mode: str = "",
) -> list[object]:
    from ..models.result.tin_surface import TINVertex

    output: list[TINVertex] = []
    seen_xy: set[tuple[float, float]] = set()
    for row in list(getattr(patch_boundary_result, "point_rows", []) or []):
        x = float(getattr(row, "x", 0.0) or 0.0)
        y = float(getattr(row, "y", 0.0) or 0.0)
        xy_key = (round(x, 6), round(y, 6))
        if xy_key in seen_xy:
            continue
        seen_xy.add(xy_key)
        nearest = _nearest_tin_vertex_xy(source_vertices, x, y)
        if grading_plane is not None:
            z = _intersection_grading_plane_z(grading_plane, x, y)
            elevation_source_ref = "intersection_grading_plane"
            elevation_source_notes = f"intersection_grading={str(grading_mode or '')}; blend_basis=primary_side_plane"
        else:
            z = float(getattr(nearest, "z", getattr(row, "z", 0.0)) or 0.0) if nearest is not None else float(getattr(row, "z", 0.0) or 0.0)
            elevation_source_ref = str(getattr(nearest, "source_point_ref", "") or "") if nearest is not None else ""
            elevation_source_notes = str(getattr(nearest, "notes", "") or "") if nearest is not None else ""
        output.append(
            TINVertex(
                vertex_id=f"v{len(output) + 1}",
                x=x,
                y=y,
                z=z,
                source_point_ref=str(getattr(row, "boundary_point_id", "") or ""),
                notes=(
                    f"ordered_patch_boundary; source_segment={getattr(row, 'source_segment_ref', '')}; "
                    f"source_kind={getattr(row, 'source_kind', '')}; "
                    f"elevation_source={elevation_source_ref}; elevation_source_notes={elevation_source_notes}"
                ),
            )
        )
    return output


def _intersection_patch_superelevation_context(sections: list[object]) -> dict[str, object]:
    source_refs = {
        str(getattr(section, "active_superelevation_id", "") or "").strip()
        for section in list(sections or [])
        if str(getattr(section, "active_superelevation_id", "") or "").strip()
    }
    transition_refs = {
        str(getattr(section, "active_superelevation_transition_id", "") or "").strip()
        for section in list(sections or [])
        if str(getattr(section, "active_superelevation_transition_id", "") or "").strip()
    }
    left_values = [float(getattr(section, "superelevation_left_crossfall", 0.0) or 0.0) for section in list(sections or [])]
    right_values = [float(getattr(section, "superelevation_right_crossfall", 0.0) or 0.0) for section in list(sections or [])]
    left_min = min(left_values) if left_values else 0.0
    left_max = max(left_values) if left_values else 0.0
    right_min = min(right_values) if right_values else 0.0
    right_max = max(right_values) if right_values else 0.0
    if source_refs:
        summary = (
            f"sources={len(source_refs)}; transitions={len(transition_refs)}; "
            f"L {left_min:.3f}%..{left_max:.3f}%; R {right_min:.3f}%..{right_max:.3f}%"
        )
    else:
        summary = "sources=0; uses Applied Section default crossfall context"
    return {
        "source_count": len(source_refs),
        "transition_count": len(transition_refs),
        "left_min": left_min,
        "left_max": left_max,
        "right_min": right_min,
        "right_max": right_max,
        "summary": summary,
    }


def _intersection_patch_structured_strip_triangulation(
    tie_in_result,
    *,
    source_vertices: list[object],
    center: object,
    intersection_model=None,
    boundary_segment_result=None,
    intersection_id: str,
    policy: dict[str, float] | None = None,
) -> dict[str, object]:
    from ..models.result.tin_surface import TINTriangle, TINVertex

    empty = {
        "vertices": [*list(source_vertices or []), center],
        "triangles": [],
        "degenerate_count": 0,
        "max_edge_length": 0.0,
        "long_edge_count": 0,
        "long_edge_factor": max(float(dict(policy or {}).get("long_edge_factor", 2.5) or 2.5), 1.0),
        "long_edge_limit": 0.0,
        "max_boundary_edge_length_policy": float(dict(policy or {}).get("max_boundary_edge_length", 0.0) or 0.0),
        "boundary_strategy": "ordered_polygon",
        "structured_strip_count": 0,
        "curb_return_surface_edge_count": 0,
        "curb_return_arc_count": 0,
        "curb_return_arc_sample_count": 0,
        "curb_return_arc_segment_count": 0,
        "edge_blend_face_count": 0,
        "boundary_role_summary": "",
        "pavement_tie_in_edge_count": 0,
        "stem_tie_in_edge_count": 0,
        "overlap_cut_edge_count": 0,
        "curb_return_edge_count": 0,
    }
    if tie_in_result is None:
        return empty
    grouped: dict[str, list[IntersectionBoundarySegmentRow]] = {}
    for edge in list(getattr(tie_in_result, "edge_rows", []) or []):
        alignment_ref = str(getattr(edge, "alignment_ref", "") or "").strip()
        if not alignment_ref:
            continue
        grouped.setdefault(alignment_ref, []).append(
            IntersectionBoundarySegmentRow(
                boundary_segment_id=f"structured:{getattr(edge, 'tie_in_edge_id', '')}",
                intersection_id=intersection_id,
                segment_kind="tie_in",
                alignment_ref=alignment_ref,
                side=str(getattr(edge, "side", "") or ""),
                start_xyz=tuple(getattr(edge, "start_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
                end_xyz=tuple(getattr(edge, "end_xyz", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)),
            )
        )
    if len(grouped) < 2:
        return empty
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip()
    if not primary_ref or primary_ref not in grouped:
        primary_ref = next(iter(grouped.keys()))
    primary_polygon = _intersection_tie_in_strip_polygon(grouped.get(primary_ref, []))
    if primary_polygon is None:
        return empty
    polygons: list[list[tuple[float, float, float]]] = [primary_polygon]
    for alignment_ref, rows in grouped.items():
        if alignment_ref == primary_ref:
            continue
        polygon = _intersection_tie_in_strip_polygon(rows)
        if polygon is None:
            continue
        outside = _xy_polygon_outer_difference_candidate(polygon, primary_polygon)
        if outside is not None:
            polygons.append(outside)
    if len(polygons) < 2:
        return empty
    arc_surface_parts = _intersection_curb_return_surface_parts(boundary_segment_result)
    arc_stats = _intersection_curb_return_surface_arc_stats(boundary_segment_result)
    edge_blend_face_count = len([part for part in arc_surface_parts if str(part[1]) == "curb_return_blend"])
    role_counts = _intersection_patch_boundary_role_counts(
        grouped,
        primary_ref,
        arc_count=int(arc_stats["arc_count"]),
        overlap_cut_count=max(len(polygons) - 1, 0),
    )

    vertices: list[TINVertex] = []
    vertex_by_key: dict[tuple[float, float], TINVertex] = {}

    def vertex_for(point: tuple[float, float, float]) -> TINVertex:
        key = _xy_key(point)
        existing = vertex_by_key.get(key)
        if existing is not None:
            return existing
        nearest = _nearest_tin_vertex_xy(source_vertices, float(point[0]), float(point[1]))
        z = float(getattr(nearest, "z", point[2]) or point[2]) if nearest is not None else float(point[2])
        vertex = TINVertex(
            vertex_id=f"v{len(vertices) + 1}",
            x=float(point[0]),
            y=float(point[1]),
            z=z,
            source_point_ref=f"{intersection_id}:structured-strip:{len(vertices) + 1}",
            notes="intersection structured strip triangulation",
        )
        vertices.append(vertex)
        vertex_by_key[key] = vertex
        return vertex

    triangles: list[TINTriangle] = []
    degenerate_count = 0
    edge_lengths: list[float] = []
    surface_parts: list[tuple[list[tuple[float, float, float]], str]] = [
        (polygon, "structured_strip") for polygon in polygons
    ]
    surface_parts.extend(arc_surface_parts)
    for polygon_index, (polygon, quality_role) in enumerate(surface_parts, start=1):
        cleaned = _unique_xyz_points(polygon)
        if len(cleaned) < 3 or _xy_xyz_polygon_self_crossing(cleaned):
            continue
        if _xy_area_from_xyz_points(cleaned) < 0.0:
            cleaned.reverse()
        local_vertices = [vertex_for(point) for point in cleaned]
        if polygon_index <= len(polygons):
            edge_source_points = [(v.x, v.y, v.z) for v in local_vertices]
            edge_pairs = _xyz_closed_edges(edge_source_points)
        else:
            edge_pairs = []
        for first, second in edge_pairs:
            edge_lengths.append(_xy_distance((first[0], first[1]), (second[0], second[1])))
        indices = _intersection_patch_ear_clip_indices(local_vertices)
        if not indices and len(local_vertices) == 4:
            indices = [(0, 1, 2), (0, 2, 3)]
        for first_index, second_index, third_index in indices:
            first = local_vertices[first_index]
            second = local_vertices[second_index]
            third = local_vertices[third_index]
            area = abs(_xy_triangle_area(first, second, third))
            if area <= 1.0e-6:
                degenerate_count += 1
                continue
            triangles.append(
                TINTriangle(
                    triangle_id=f"t{len(triangles) + 1}",
                    v1=str(getattr(first, "vertex_id", "") or ""),
                    v2=str(getattr(second, "vertex_id", "") or ""),
                    v3=str(getattr(third, "vertex_id", "") or ""),
                    triangle_kind="intersection_surface_patch",
                    quality_ref=quality_role,
                    notes=f"intersection={intersection_id}; surface_part={polygon_index}; area={area:.6f}",
                )
            )
    if not triangles:
        return empty
    policy_values = dict(policy or {})
    long_edge_factor = max(float(policy_values.get("long_edge_factor", 2.5) or 2.5), 1.0)
    max_boundary_edge_length = float(policy_values.get("max_boundary_edge_length", 0.0) or 0.0)
    max_edge_length = max(edge_lengths) if edge_lengths else 0.0
    if edge_lengths:
        average = sum(edge_lengths) / len(edge_lengths)
        long_edge_limit = max_boundary_edge_length if max_boundary_edge_length > 0.0 else max(average * long_edge_factor, 1.0)
        long_edge_count = len([length for length in edge_lengths if length > long_edge_limit])
    else:
        long_edge_limit = 0.0
        long_edge_count = 0
    return {
        "vertices": vertices,
        "triangles": triangles,
        "degenerate_count": degenerate_count,
        "max_edge_length": max_edge_length,
        "long_edge_count": long_edge_count,
        "long_edge_factor": long_edge_factor,
        "long_edge_limit": long_edge_limit,
        "max_boundary_edge_length_policy": max_boundary_edge_length,
        "boundary_strategy": "structured_strip_curb_return_blend" if edge_blend_face_count else ("structured_strip_curb_return" if arc_stats["arc_count"] else "structured_strip_union"),
        "structured_strip_count": len(polygons),
        "curb_return_surface_edge_count": int(arc_stats["arc_count"]),
        "curb_return_arc_count": int(arc_stats["arc_count"]),
        "curb_return_arc_sample_count": int(arc_stats["sample_count"]),
        "curb_return_arc_segment_count": int(arc_stats["segment_count"]),
        "edge_blend_face_count": edge_blend_face_count,
        "boundary_role_summary": _intersection_patch_boundary_role_summary(role_counts),
        "pavement_tie_in_edge_count": int(role_counts["pavement_tie_in"]),
        "stem_tie_in_edge_count": int(role_counts["stem_tie_in"]),
        "overlap_cut_edge_count": int(role_counts["overlap_cut"]),
        "curb_return_edge_count": int(role_counts["curb_return"]),
    }


def _intersection_patch_boundary_role_counts(
    grouped: dict[str, list[IntersectionBoundarySegmentRow]],
    primary_ref: str,
    *,
    arc_count: int,
    overlap_cut_count: int,
) -> dict[str, int]:
    pavement_tie_in = len(list(grouped.get(primary_ref, []) or []))
    stem_tie_in = sum(
        len(list(rows or []))
        for alignment_ref, rows in grouped.items()
        if str(alignment_ref or "") != str(primary_ref or "")
    )
    return {
        "pavement_tie_in": int(pavement_tie_in),
        "stem_tie_in": int(stem_tie_in),
        "overlap_cut": int(max(overlap_cut_count, 0)),
        "curb_return": int(max(arc_count, 0)),
    }


def _intersection_patch_boundary_role_summary(role_counts: dict[str, int]) -> str:
    ordered_roles = ("pavement_tie_in", "stem_tie_in", "overlap_cut", "curb_return")
    return "; ".join(f"{role}={int(role_counts.get(role, 0) or 0)}" for role in ordered_roles)


def _intersection_curb_return_surface_arc_stats(boundary_segment_result) -> dict[str, int]:
    if boundary_segment_result is None:
        return {"arc_count": 0, "sample_count": 0, "segment_count": 0}
    arc_count = 0
    max_sample_count = 0
    segment_count = 0
    for row in list(getattr(boundary_segment_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        chord_points = list(getattr(row, "chord_points_xyz", []) or [])
        if len(chord_points) < 2:
            continue
        arc_count += 1
        max_sample_count = max(max_sample_count, len(chord_points))
        segment_count += max(len(chord_points) - 1, 0)
    return {"arc_count": arc_count, "sample_count": max_sample_count, "segment_count": segment_count}


def _intersection_curb_return_surface_parts(boundary_segment_result) -> list[tuple[list[tuple[float, float, float]], str]]:
    if boundary_segment_result is None:
        return []
    output: list[tuple[list[tuple[float, float, float]], str]] = []
    for row in list(getattr(boundary_segment_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        chord_points = [_xyz_tuple(point) for point in list(getattr(row, "chord_points_xyz", []) or [])]
        center = _xyz_tuple(getattr(row, "center_xyz", (0.0, 0.0, 0.0)))
        if len(chord_points) < 2:
            continue
        inner_points = [_lerp_xyz(center, point, 0.58) for point in chord_points]
        for index in range(len(chord_points) - 1):
            polygon = _unique_xyz_points([
                chord_points[index],
                chord_points[index + 1],
                inner_points[index + 1],
                inner_points[index],
            ])
            if _intersection_surface_part_is_valid(polygon):
                output.append((polygon, "curb_return_blend"))
        core = _unique_xyz_points([center, *inner_points])
        if _intersection_surface_part_is_valid(core):
            output.append((core, "curb_return_core"))
    return output


def _intersection_surface_part_is_valid(polygon: list[tuple[float, float, float]]) -> bool:
    return (
        len(polygon) >= 3
        and abs(_xy_area_from_xyz_points(polygon)) > 1.0e-6
        and not _xy_xyz_polygon_self_crossing(polygon)
    )


def _lerp_xyz(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    factor: float,
) -> tuple[float, float, float]:
    t = max(0.0, min(float(factor), 1.0))
    return (
        float(start[0]) + (float(end[0]) - float(start[0])) * t,
        float(start[1]) + (float(end[1]) - float(start[1])) * t,
        float(start[2]) + (float(end[2]) - float(start[2])) * t,
    )


def _intersection_curb_return_surface_polygons(boundary_segment_result) -> list[list[tuple[float, float, float]]]:
    if boundary_segment_result is None:
        return []
    output: list[list[tuple[float, float, float]]] = []
    for row in list(getattr(boundary_segment_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        chord_points = [_xyz_tuple(point) for point in list(getattr(row, "chord_points_xyz", []) or [])]
        center = _xyz_tuple(getattr(row, "center_xyz", (0.0, 0.0, 0.0)))
        if len(chord_points) < 2:
            continue
        polygon = _unique_xyz_points([center, *chord_points])
        if len(polygon) < 3 or abs(_xy_area_from_xyz_points(polygon)) <= 1.0e-6:
            continue
        if _xy_xyz_polygon_self_crossing(polygon):
            continue
        output.append(polygon)
    return output


def _xy_polygon_outer_difference_candidate(
    polygon: list[tuple[float, float, float]],
    clip_polygon: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]] | None:
    output: list[tuple[float, float, float]] = []
    clip_xy = [(float(point[0]), float(point[1])) for point in clip_polygon]
    for point in polygon:
        if not _xy_point_in_polygon_strict((float(point[0]), float(point[1])), clip_xy):
            output.append(point)
    for start, end in _xyz_closed_edges(polygon):
        for clip_start, clip_end in _xyz_closed_edges(clip_polygon):
            intersection = _xy_segment_intersection_point(start, end, clip_start, clip_end)
            if intersection is not None:
                output.append(intersection)
    output = _unique_xyz_points(output)
    if len(output) < 3:
        return None
    center_x = sum(point[0] for point in output) / len(output)
    center_y = sum(point[1] for point in output) / len(output)
    ordered = sorted(output, key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x))
    if abs(_xy_area_from_xyz_points(ordered)) <= 1.0e-6 or _xy_xyz_polygon_self_crossing(ordered):
        return None
    return ordered


def _intersection_patch_ordered_polygon_triangulation(
    vertices: list[object],
    center: object,
    *,
    intersection_id: str,
    policy: dict[str, float] | None = None,
) -> dict[str, object]:
    from ..models.result.tin_surface import TINTriangle

    policy_values = dict(policy or {})
    long_edge_factor = max(float(policy_values.get("long_edge_factor", 2.5) or 2.5), 1.0)
    max_boundary_edge_length = float(policy_values.get("max_boundary_edge_length", 0.0) or 0.0)
    triangles: list[TINTriangle] = []
    degenerate_count = 0
    long_edge_count = 0
    max_edge_length = 0.0
    long_edge_limit = 0.0
    edge_lengths: list[float] = []
    for index in range(len(vertices)):
        current = vertices[index]
        nxt = vertices[(index + 1) % len(vertices)]
        edge_length = _xy_distance(
            (float(getattr(current, "x", 0.0) or 0.0), float(getattr(current, "y", 0.0) or 0.0)),
            (float(getattr(nxt, "x", 0.0) or 0.0), float(getattr(nxt, "y", 0.0) or 0.0)),
        )
        edge_lengths.append(edge_length)
        max_edge_length = max(max_edge_length, edge_length)
    polygon_indices = _intersection_patch_ear_clip_indices(vertices)
    if polygon_indices:
        for first_index, second_index, third_index in polygon_indices:
            first = vertices[first_index]
            second = vertices[second_index]
            third = vertices[third_index]
            area = abs(_xy_triangle_area(first, second, third))
            if area <= 1.0e-6:
                degenerate_count += 1
                continue
            triangles.append(
                TINTriangle(
                    triangle_id=f"t{len(triangles) + 1}",
                    v1=str(getattr(first, "vertex_id", "") or ""),
                    v2=str(getattr(second, "vertex_id", "") or ""),
                    v3=str(getattr(third, "vertex_id", "") or ""),
                    triangle_kind="intersection_surface_patch",
                    quality_ref="ordered_polygon",
                    notes=f"intersection={intersection_id}; area={area:.6f}",
                )
            )
    else:
        for index in range(len(vertices)):
            current = vertices[index]
            nxt = vertices[(index + 1) % len(vertices)]
            area = abs(_xy_triangle_area(center, current, nxt))
            if area <= 1.0e-6:
                degenerate_count += 1
                continue
            triangles.append(
                TINTriangle(
                    triangle_id=f"t{len(triangles) + 1}",
                    v1=str(getattr(center, "vertex_id", "v:center") or "v:center"),
                    v2=str(getattr(current, "vertex_id", "") or ""),
                    v3=str(getattr(nxt, "vertex_id", "") or ""),
                    triangle_kind="intersection_surface_patch",
                    quality_ref="ordered_fan_fallback",
                    notes=f"intersection={intersection_id}; area={area:.6f}",
                )
            )
    if edge_lengths:
        average = sum(edge_lengths) / len(edge_lengths)
        long_edge_limit = max_boundary_edge_length if max_boundary_edge_length > 0.0 else max(average * long_edge_factor, 1.0)
        long_edge_count = len([length for length in edge_lengths if length > long_edge_limit])
    return {
        "triangles": triangles,
        "degenerate_count": degenerate_count,
        "max_edge_length": max_edge_length,
        "long_edge_count": long_edge_count,
        "long_edge_factor": long_edge_factor,
        "long_edge_limit": long_edge_limit,
        "max_boundary_edge_length_policy": max_boundary_edge_length,
        "boundary_strategy": "ordered_polygon",
        "structured_strip_count": 0,
        "curb_return_surface_edge_count": 0,
    }


def _intersection_patch_ear_clip_indices(vertices: list[object]) -> list[tuple[int, int, int]]:
    if len(vertices) < 3:
        return []
    polygon_area = _xy_polygon_signed_area(vertices)
    if abs(polygon_area) <= 1.0e-9:
        return []
    remaining = list(range(len(vertices)))
    if polygon_area < 0.0:
        remaining.reverse()
    triangles: list[tuple[int, int, int]] = []
    guard = 0
    while len(remaining) > 3 and guard < len(vertices) * len(vertices):
        guard += 1
        ear_index = None
        for index in range(len(remaining)):
            prev_index = remaining[(index - 1) % len(remaining)]
            current_index = remaining[index]
            next_index = remaining[(index + 1) % len(remaining)]
            if not _intersection_patch_is_ear(vertices, remaining, prev_index, current_index, next_index):
                continue
            ear_index = index
            triangles.append((prev_index, current_index, next_index))
            break
        if ear_index is None:
            if triangles and abs(_xy_polygon_signed_area([vertices[index] for index in remaining])) <= 1.0e-6:
                break
            return []
        remaining.pop(ear_index)
    if len(remaining) == 3:
        first, second, third = remaining
        if abs(_xy_triangle_area(vertices[first], vertices[second], vertices[third])) > 1.0e-6:
            triangles.append((first, second, third))
    return triangles


def _intersection_patch_shape_quality(vertices: list[object], triangles: list[object]) -> dict[str, object]:
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(vertices or [])
        if str(getattr(vertex, "vertex_id", "") or "")
    }
    xs = [float(getattr(vertex, "x", 0.0) or 0.0) for vertex in list(vertices or [])]
    ys = [float(getattr(vertex, "y", 0.0) or 0.0) for vertex in list(vertices or [])]
    bbox_x = (max(xs) - min(xs)) if xs else 0.0
    bbox_y = (max(ys) - min(ys)) if ys else 0.0
    min_axis = min(abs(bbox_x), abs(bbox_y))
    max_axis = max(abs(bbox_x), abs(bbox_y))
    aspect_ratio = (max_axis / min_axis) if min_axis > 1.0e-9 else 0.0
    quality_values: list[float] = []
    fan_fallback = False
    structured_strip = False
    curb_return_arc = False
    curb_return_blend = False
    for triangle in list(triangles or []):
        quality_ref = str(getattr(triangle, "quality_ref", "") or "")
        if "fan" in quality_ref:
            fan_fallback = True
        if "structured_strip" in quality_ref:
            structured_strip = True
        if "curb_return" in quality_ref:
            curb_return_arc = True
        if "curb_return_blend" in quality_ref:
            curb_return_blend = True
        tri_vertices = [
            vertex_map.get(str(getattr(triangle, attr, "") or ""))
            for attr in ("v1", "v2", "v3")
        ]
        if any(vertex is None for vertex in tri_vertices):
            continue
        quality_values.append(_xy_triangle_quality_ratio(tri_vertices[0], tri_vertices[1], tri_vertices[2]))
    min_quality = min(quality_values) if quality_values else 0.0
    skinny_count = len([value for value in quality_values if value < 0.08])
    if structured_strip and curb_return_blend:
        triangulation_mode = "structured_strip_curb_return_blend"
    elif structured_strip and curb_return_arc:
        triangulation_mode = "structured_strip_curb_return"
    else:
        triangulation_mode = "structured_strip" if structured_strip else ("fan_fallback" if fan_fallback else "ear_clip")
    return {
        "triangulation_mode": triangulation_mode,
        "bbox_x": bbox_x,
        "bbox_y": bbox_y,
        "bbox_aspect_ratio": aspect_ratio,
        "triangle_min_quality": min_quality,
        "skinny_triangle_count": skinny_count,
    }


def _xy_triangle_quality_ratio(a, b, c) -> float:
    points = [_xy_point_tuple(a), _xy_point_tuple(b), _xy_point_tuple(c)]
    edge_lengths = [
        _xy_distance(points[0], points[1]),
        _xy_distance(points[1], points[2]),
        _xy_distance(points[2], points[0]),
    ]
    denominator = sum(length * length for length in edge_lengths)
    if denominator <= 1.0e-12:
        return 0.0
    area = abs(_xy_triangle_area(a, b, c))
    return (4.0 * math.sqrt(3.0) * area) / denominator


def _intersection_patch_is_ear(
    vertices: list[object],
    remaining: list[int],
    prev_index: int,
    current_index: int,
    next_index: int,
) -> bool:
    prev_vertex = vertices[prev_index]
    current_vertex = vertices[current_index]
    next_vertex = vertices[next_index]
    if _xy_triangle_area(prev_vertex, current_vertex, next_vertex) <= 1.0e-9:
        return False
    triangle = (
        _xy_point_tuple(prev_vertex),
        _xy_point_tuple(current_vertex),
        _xy_point_tuple(next_vertex),
    )
    for candidate_index in remaining:
        if candidate_index in {prev_index, current_index, next_index}:
            continue
        if _xy_point_in_triangle(_xy_point_tuple(vertices[candidate_index]), triangle):
            return False
    return True


def _xy_polygon_signed_area(vertices: list[object]) -> float:
    area = 0.0
    for index in range(len(vertices)):
        current = vertices[index]
        nxt = vertices[(index + 1) % len(vertices)]
        area += float(getattr(current, "x", 0.0) or 0.0) * float(getattr(nxt, "y", 0.0) or 0.0)
        area -= float(getattr(nxt, "x", 0.0) or 0.0) * float(getattr(current, "y", 0.0) or 0.0)
    return area * 0.5


def _xy_point_tuple(vertex) -> tuple[float, float]:
    return (float(getattr(vertex, "x", 0.0) or 0.0), float(getattr(vertex, "y", 0.0) or 0.0))


def _xy_point_in_triangle(
    point: tuple[float, float],
    triangle: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> bool:
    a, b, c = triangle
    denominator = ((b[1] - c[1]) * (a[0] - c[0])) + ((c[0] - b[0]) * (a[1] - c[1]))
    if abs(denominator) <= 1.0e-12:
        return False
    first = (((b[1] - c[1]) * (point[0] - c[0])) + ((c[0] - b[0]) * (point[1] - c[1]))) / denominator
    second = (((c[1] - a[1]) * (point[0] - c[0])) + ((a[0] - c[0]) * (point[1] - c[1]))) / denominator
    third = 1.0 - first - second
    tolerance = 1.0e-9
    return first > tolerance and second > tolerance and third > tolerance


def _xy_triangle_area(a, b, c) -> float:
    ax = float(getattr(a, "x", 0.0) or 0.0)
    ay = float(getattr(a, "y", 0.0) or 0.0)
    bx = float(getattr(b, "x", 0.0) or 0.0)
    by = float(getattr(b, "y", 0.0) or 0.0)
    cx = float(getattr(c, "x", 0.0) or 0.0)
    cy = float(getattr(c, "y", 0.0) or 0.0)
    return 0.5 * ((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))


def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _nearest_tin_vertex_xy(vertices: list[object], x: float, y: float):
    nearest = None
    nearest_distance = None
    for vertex in list(vertices or []):
        dx = float(getattr(vertex, "x", 0.0) or 0.0) - float(x)
        dy = float(getattr(vertex, "y", 0.0) or 0.0) - float(y)
        distance = dx * dx + dy * dy
        if nearest_distance is None or distance < nearest_distance:
            nearest = vertex
            nearest_distance = distance
    return nearest


def _intersection_patch_center_sections(
    sections: list[object],
    *,
    intersection_model=None,
    prerequisite: IntersectionPatchPrerequisiteResult,
) -> list[object]:
    """Keep only the center-nearest Applied Section per participating Alignment."""

    if not sections:
        return []
    target_stations = _intersection_patch_target_stations_by_alignment(intersection_model, prerequisite)
    grouped: dict[str, list[object]] = {}
    for section in sections:
        alignment_id = str(getattr(section, "alignment_id", "") or "")
        grouped.setdefault(alignment_id, []).append(section)
    output: list[object] = []
    for alignment_id, rows in grouped.items():
        if len(rows) <= 1:
            output.extend(rows)
            continue
        target_station = target_stations.get(alignment_id)
        if target_station is None:
            stations = [float(getattr(row, "station", 0.0) or 0.0) for row in rows]
            target_station = sum(stations) / len(stations)
        nearest = min(rows, key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - float(target_station)))
        output.append(nearest)
    return _station_ordered_applied_sections(
        AppliedSectionSet(
            schema_version=1,
            project_id="",
            applied_section_set_id="intersection-patch:center-sections",
            corridor_id="",
            sections=output,
        )
    )


def _intersection_patch_target_stations_by_alignment(intersection_model, prerequisite: IntersectionPatchPrerequisiteResult) -> dict[str, float]:
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    output: dict[str, float] = {}
    if intersection_model is None:
        return output
    source_row = None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if not intersection_id or str(getattr(row, "intersection_id", "") or "") == intersection_id:
            source_row = row
            break
    if source_row is not None:
        primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip()
        if primary_ref:
            output[primary_ref] = float(getattr(source_row, "primary_station", 0.0) or 0.0)
        for alignment_ref, station in dict(getattr(source_row, "secondary_station_refs", {}) or {}).items():
            alignment_id = str(alignment_ref or "").strip()
            if alignment_id:
                output[alignment_id] = float(station or 0.0)
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if intersection_id and str(getattr(area, "intersection_id", "") or "") != intersection_id:
            continue
        alignment_id = str(getattr(area, "alignment_ref", "") or "").strip()
        if not alignment_id or alignment_id in output:
            continue
        ranges = list(getattr(area, "station_ranges", []) or [])
        centers: list[float] = []
        for station_start, station_end in ranges:
            try:
                centers.append((float(station_start) + float(station_end)) / 2.0)
            except Exception:
                continue
        if centers:
            output[alignment_id] = sum(centers) / len(centers)
    return output


def _intersection_patch_boundary_hull(vertices: list[object]) -> list[object]:
    """Return a non-self-crossing XY hull for first-slice intersection patch triangulation."""

    unique: dict[tuple[float, float], object] = {}
    for vertex in vertices:
        key = (round(float(getattr(vertex, "x", 0.0) or 0.0), 6), round(float(getattr(vertex, "y", 0.0) or 0.0), 6))
        unique.setdefault(key, vertex)
    points = sorted(unique.items(), key=lambda item: (item[0][0], item[0][1]))
    if len(points) <= 3:
        center_x = sum(float(getattr(vertex, "x", 0.0) or 0.0) for _, vertex in points) / max(1, len(points))
        center_y = sum(float(getattr(vertex, "y", 0.0) or 0.0) for _, vertex in points) / max(1, len(points))
        return sorted([vertex for _, vertex in points], key=lambda vertex: math.atan2(float(getattr(vertex, "y", 0.0) or 0.0) - center_y, float(getattr(vertex, "x", 0.0) or 0.0) - center_x))

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[tuple[float, float], object]] = []
    for item in points:
        while len(lower) >= 2 and cross(lower[-2][0], lower[-1][0], item[0]) <= 0.0:
            lower.pop()
        lower.append(item)
    upper: list[tuple[tuple[float, float], object]] = []
    for item in reversed(points):
        while len(upper) >= 2 and cross(upper[-2][0], upper[-1][0], item[0]) <= 0.0:
            upper.pop()
        upper.append(item)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        center_x = sum(float(getattr(vertex, "x", 0.0) or 0.0) for _, vertex in points) / len(points)
        center_y = sum(float(getattr(vertex, "y", 0.0) or 0.0) for _, vertex in points) / len(points)
        return sorted([vertex for _, vertex in points], key=lambda vertex: math.atan2(float(getattr(vertex, "y", 0.0) or 0.0) - center_y, float(getattr(vertex, "x", 0.0) or 0.0) - center_x))
    return [vertex for _, vertex in hull]


def _intersection_grading_policy_for(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    rows = list(getattr(intersection_model, "grading_policy_rows", []) or []) if intersection_model is not None else []
    for row in rows:
        if str(getattr(row, "intersection_id", "") or "") == target and str(getattr(row, "status", "") or "active") != "disabled":
            return row
    return None


def _intersection_patch_triangulation_policy(intersection_model, intersection_id: str) -> dict[str, float]:
    policy = _intersection_curb_return_policy_for(intersection_model, intersection_id)
    return {
        "long_edge_factor": float(getattr(policy, "long_edge_factor", 2.5) or 2.5),
        "max_boundary_edge_length": float(getattr(policy, "max_boundary_edge_length", 0.0) or 0.0),
    }


def _apply_intersection_grading_policy(
    vertices: list[object],
    grading_policy,
    *,
    grading_plane: tuple[float, float, float] | None = None,
) -> list[object]:
    mode = str(getattr(grading_policy, "mode", "") or "use_normal_superelevation").strip()
    if mode not in {"flatten_intersection", "keep_primary_crown", "blend_primary_side", "use_normal_superelevation"}:
        mode = "use_normal_superelevation"
    if mode == "use_normal_superelevation":
        return vertices
    if mode == "flatten_intersection":
        if not vertices:
            return vertices
        target_z = sum(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices) / len(vertices)
        return [replace(vertex, z=target_z, notes=f"{getattr(vertex, 'notes', '')}; intersection_grading={mode}") for vertex in vertices]
    if mode == "keep_primary_crown":
        return [replace(vertex, notes=f"{getattr(vertex, 'notes', '')}; intersection_grading={mode}") for vertex in vertices]
    if mode == "blend_primary_side":
        if grading_plane is None:
            grading_plane = _intersection_grading_plane_for_policy(vertices, grading_policy)
        if grading_plane is not None:
            return [
                replace(
                    vertex,
                    z=_intersection_grading_plane_z(
                        grading_plane,
                        float(getattr(vertex, "x", 0.0) or 0.0),
                        float(getattr(vertex, "y", 0.0) or 0.0),
                    ),
                    notes=f"{getattr(vertex, 'notes', '')}; intersection_grading={mode}; blend_basis=primary_side_plane",
                )
                for vertex in vertices
            ]
        primary_ref = str(getattr(grading_policy, "primary_alignment_ref", "") or "").strip()
        primary_vertices = [
            vertex for vertex in vertices
            if primary_ref and f"alignment={primary_ref}" in str(getattr(vertex, "notes", "") or "")
        ]
        if not primary_vertices:
            return [replace(vertex, notes=f"{getattr(vertex, 'notes', '')}; intersection_grading={mode}; blend_basis=missing_primary") for vertex in vertices]
        primary_z = sum(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in primary_vertices) / len(primary_vertices)
        output = []
        for vertex in vertices:
            notes = str(getattr(vertex, "notes", "") or "")
            z = float(getattr(vertex, "z", 0.0) or 0.0)
            if primary_ref and f"alignment={primary_ref}" in notes:
                output.append(replace(vertex, notes=f"{notes}; intersection_grading={mode}; blend_basis=primary_preserved"))
            else:
                output.append(replace(vertex, z=(z + primary_z) / 2.0, notes=f"{notes}; intersection_grading={mode}; blend_basis=primary_side_half"))
        return output
    return vertices


def _intersection_grading_plane_for_policy(vertices: list[object], grading_policy) -> tuple[float, float, float] | None:
    mode = str(getattr(grading_policy, "mode", "") or "").strip()
    if mode != "blend_primary_side":
        return None
    if len(list(vertices or [])) < 3:
        return None
    samples = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
            float(getattr(vertex, "z", 0.0) or 0.0),
        )
        for vertex in list(vertices or [])
    ]
    return _fit_z_plane(samples)


def _intersection_grading_plane_z(plane: tuple[float, float, float], x: float, y: float) -> float:
    a, b, c = plane
    return (float(a) * float(x)) + (float(b) * float(y)) + float(c)


def _fit_z_plane(samples: list[tuple[float, float, float]]) -> tuple[float, float, float] | None:
    valid = [(float(x), float(y), float(z)) for x, y, z in list(samples or [])]
    if len(valid) < 3:
        return None
    sx = sum(x for x, _y, _z in valid)
    sy = sum(y for _x, y, _z in valid)
    sz = sum(z for _x, _y, z in valid)
    sxx = sum(x * x for x, _y, _z in valid)
    syy = sum(y * y for _x, y, _z in valid)
    sxy = sum(x * y for x, y, _z in valid)
    sxz = sum(x * z for x, _y, z in valid)
    syz = sum(y * z for _x, y, z in valid)
    n = float(len(valid))
    return _solve_3x3(
        (
            (sxx, sxy, sx),
            (sxy, syy, sy),
            (sx, sy, n),
        ),
        (sxz, syz, sz),
    )


def _solve_3x3(matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]], values: tuple[float, float, float]) -> tuple[float, float, float] | None:
    a = [[float(value) for value in row] for row in matrix]
    b = [float(value) for value in values]
    for pivot in range(3):
        pivot_row = max(range(pivot, 3), key=lambda row: abs(a[row][pivot]))
        if abs(a[pivot_row][pivot]) <= 1.0e-12:
            return None
        if pivot_row != pivot:
            a[pivot], a[pivot_row] = a[pivot_row], a[pivot]
            b[pivot], b[pivot_row] = b[pivot_row], b[pivot]
        pivot_value = a[pivot][pivot]
        for column in range(pivot, 3):
            a[pivot][column] /= pivot_value
        b[pivot] /= pivot_value
        for row in range(3):
            if row == pivot:
                continue
            factor = a[row][pivot]
            if abs(factor) <= 1.0e-12:
                continue
            for column in range(pivot, 3):
                a[row][column] -= factor * a[pivot][column]
            b[row] -= factor * b[pivot]
    return (b[0], b[1], b[2])


def _max_abs_delta(before: list[float], after: list[float]) -> float:
    values = [abs(float(b) - float(a)) for b, a in zip(list(before or []), list(after or []))]
    return max(values) if values else 0.0


def _tin_quality_float(tin_surface, kind: str) -> float:
    for row in list(getattr(tin_surface, "quality_rows", []) or []):
        if str(getattr(row, "kind", "") or "") == str(kind or ""):
            try:
                return float(getattr(row, "value", 0.0) or 0.0)
            except Exception:
                return 0.0
    return 0.0


def _tin_quality_text(tin_surface, kind: str) -> str:
    for row in list(getattr(tin_surface, "quality_rows", []) or []):
        if str(getattr(row, "kind", "") or "") == str(kind or ""):
            return str(getattr(row, "value", "") or "")
    return ""


def _corridor_build_review_row(role: str, title: str, object_name: str, obj, *, diagnostic=None) -> dict[str, object]:
    if obj is None:
        notes = str(getattr(diagnostic, "PreviewDiagnostic", "") or "Not built yet.")
        status = _normalize_corridor_build_review_status(getattr(diagnostic, "PreviewStatus", "") or "missing")
        return {
            "role": role,
            "result": title,
            "object_name": object_name,
            "object_label": "",
            "status": status,
            "vertex_count": "",
            "triangle_or_point_count": "",
            "notes": notes,
        }
    if role == "centerline":
        point_count = int(getattr(obj, "PointCount", 0) or 0)
        curve_kind = str(getattr(obj, "DisplayCurveKind", "") or "")
        preview_source = str(getattr(obj, "PreviewSource", "") or "")
        source_note = f"; source={preview_source}" if preview_source else ""
        return {
            "role": role,
            "result": title,
            "object_name": str(getattr(obj, "Name", "") or object_name),
            "object_label": str(getattr(obj, "Label", "") or object_name),
            "status": "ready",
            "vertex_count": "",
            "triangle_or_point_count": point_count,
            "notes": f"Curve: {curve_kind or 'unknown'}{source_note}",
        }
    vertex_count = int(getattr(obj, "VertexCount", 0) or 0)
    triangle_count = int(getattr(obj, "TriangleCount", 0) or 0)
    notes = str(getattr(obj, "SlopeFaceDiagnosticSummary", "") or "")
    issue_stations = str(getattr(obj, "SlopeFaceIssueStations", "") or "")
    if notes and issue_stations:
        notes = f"{notes} | issues: {issue_stations}"
    if role == "intersection":
        notes = _intersection_surface_review_notes(obj)
    elif role in {"design", "daylight"}:
        clipped = int(getattr(obj, "IntersectionExclusionClippedTriangleCount", 0) or 0)
        kept = int(getattr(obj, "IntersectionExclusionKeptTriangleCount", 0) or 0)
        exclusion_status = str(getattr(obj, "IntersectionExclusionClipStatus", "") or "")
        if exclusion_status:
            boundary_strategy = str(getattr(obj, "IntersectionExclusionBoundaryStrategy", "") or "")
            aligned = int(getattr(obj, "IntersectionExclusionPracticalBoundaryAligned", 0) or 0)
            suffix_parts = [
                f"intersection exclusion={exclusion_status}",
                f"clipped={clipped}",
                f"kept={kept}",
            ]
            if boundary_strategy:
                suffix_parts.append(f"boundary={boundary_strategy}")
            if aligned:
                suffix_parts.append("aligned=practical")
            height_status = str(getattr(obj, "IntersectionHeightClipStatus", "") or "")
            if height_status:
                height_suppressed = int(getattr(obj, "IntersectionHeightClipSuppressedTriangleCount", 0) or 0)
                height_tested = int(getattr(obj, "IntersectionHeightClipTestedTriangleCount", 0) or 0)
                suffix_parts.append(f"height_clip={height_status} suppressed={height_suppressed}/{height_tested}")
            suffix = "; ".join(suffix_parts)
            notes = f"{notes} | {suffix}" if notes else suffix
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


def _intersection_surface_review_notes(obj) -> str:
    parts: list[str] = []
    tie_in_count = int(getattr(obj, "TieInEdgeCount", 0) or 0)
    boundary_count = int(getattr(obj, "PatchBoundaryPointCount", 0) or 0)
    grading_policy_ref = str(getattr(obj, "IntersectionGradingPolicyRef", "") or "")
    grading_mode = str(getattr(obj, "IntersectionGradingMode", "") or "")
    target_crossfall = str(getattr(obj, "IntersectionTargetCrossfallPercent", "") or "")
    grading_z_delta = float(getattr(obj, "IntersectionGradingZDeltaMax", 0.0) or 0.0)
    drainage_status = str(getattr(obj, "IntersectionDrainageCoverageStatus", "") or "")
    tie_in_preview_ref = str(getattr(obj, "TieInEdgePreviewRef", "") or "")
    tie_in_preview_status = str(getattr(obj, "TieInEdgePreviewStatus", "") or "")
    tie_in_diagnostic_count = int(getattr(obj, "TieInEdgeDiagnosticCount", 0) or 0)
    intersection_diagnostic_count = int(getattr(obj, "IntersectionDiagnosticCount", 0) or 0)
    boundary_status = str(getattr(obj, "IntersectionBoundaryStatus", "") or "")
    boundary_segment_count = int(getattr(obj, "IntersectionBoundarySegmentCount", 0) or 0)
    boundary_arc_count = int(getattr(obj, "IntersectionBoundaryArcSegmentCount", 0) or 0)
    boundary_preview_ref = str(getattr(obj, "IntersectionBoundaryPreviewRef", "") or "")
    boundary_diagnostic_count = int(getattr(obj, "IntersectionBoundaryDiagnosticCount", 0) or 0)
    patch_boundary_status = str(getattr(obj, "IntersectionPatchBoundaryStatus", "") or "")
    patch_boundary_point_count = int(getattr(obj, "IntersectionPatchBoundaryOrderedPointCount", 0) or 0)
    patch_boundary_closed = str(getattr(obj, "IntersectionPatchBoundaryClosed", "") or "")
    patch_boundary_self_crossing = str(getattr(obj, "IntersectionPatchBoundarySelfCrossing", "") or "")
    patch_boundary_diagnostic_count = int(getattr(obj, "IntersectionPatchBoundaryDiagnosticCount", 0) or 0)
    patch_boundary_diagnostics = [str(value or "") for value in list(getattr(obj, "IntersectionPatchBoundaryDiagnostics", []) or []) if str(value or "")]
    patch_boundary_hole_count = int(getattr(obj, "IntersectionPatchBoundaryHoleRingCount", 0) or 0)
    patch_boundary_island_count = int(getattr(obj, "IntersectionPatchBoundaryIslandRingCount", 0) or 0)
    superelevation_context = str(getattr(obj, "IntersectionSuperelevationContext", "") or "")
    low_point_count = int(getattr(obj, "IntersectionTINLowPointCandidateCount", 0) or 0)
    low_point_z = float(getattr(obj, "IntersectionTINLowPointZ", 0.0) or 0.0)
    flow_hint_summary = str(getattr(obj, "IntersectionBoundaryToLowFlowHintSummary", "") or "")
    patch_degenerate_count = int(getattr(obj, "PatchDegenerateTriangleCount", 0) or 0)
    patch_long_edge_count = int(getattr(obj, "PatchBoundaryLongEdgeCount", 0) or 0)
    patch_triangulation_mode = str(getattr(obj, "PatchTriangulationMode", "") or "")
    patch_boundary_strategy = str(getattr(obj, "PatchSurfaceBoundaryStrategy", "") or "")
    patch_structured_strip_count = int(getattr(obj, "PatchStructuredStripCount", 0) or 0)
    patch_curb_return_surface_edge_count = int(getattr(obj, "PatchCurbReturnSurfaceEdgeCount", 0) or 0)
    patch_curb_return_arc_count = int(getattr(obj, "PatchCurbReturnArcCount", 0) or 0)
    patch_curb_return_arc_sample_count = int(getattr(obj, "PatchCurbReturnArcSampleCount", 0) or 0)
    patch_curb_return_arc_segment_count = int(getattr(obj, "PatchCurbReturnArcSegmentCount", 0) or 0)
    patch_edge_blend_face_count = int(getattr(obj, "PatchEdgeBlendFaceCount", 0) or 0)
    patch_boundary_role_summary = str(getattr(obj, "PatchBoundaryRoleSummary", "") or "")
    patch_pavement_tie_in_edge_count = int(getattr(obj, "PatchPavementTieInEdgeCount", 0) or 0)
    patch_stem_tie_in_edge_count = int(getattr(obj, "PatchStemTieInEdgeCount", 0) or 0)
    patch_overlap_cut_edge_count = int(getattr(obj, "PatchOverlapCutEdgeCount", 0) or 0)
    patch_curb_return_edge_count = int(getattr(obj, "PatchCurbReturnEdgeCount", 0) or 0)
    patch_bbox_aspect_ratio = float(getattr(obj, "PatchBoundaryBBoxAspectRatio", 0.0) or 0.0)
    patch_min_triangle_quality = float(getattr(obj, "PatchTriangleMinQuality", 0.0) or 0.0)
    patch_skinny_triangle_count = int(getattr(obj, "PatchTriangleSkinnyCount", 0) or 0)
    implementation_mode = str(getattr(obj, "IntersectionImplementationMode", "") or "")
    redesign_path = str(getattr(obj, "IntersectionRedesignPath", "") or "")
    if tie_in_count:
        parts.append(f"tie-in edges={tie_in_count}")
    if boundary_count:
        parts.append(f"boundary points={boundary_count}")
    if grading_policy_ref:
        parts.append(f"grading policy={_display_source_id(grading_policy_ref, 'grading:')}")
    if grading_mode:
        parts.append(f"grading={grading_mode}")
    if target_crossfall:
        parts.append(f"target crossfall={target_crossfall}%")
    if grading_z_delta:
        parts.append(f"max z adjustment={grading_z_delta:.3f}m")
    if drainage_status:
        parts.append(f"drainage={drainage_status}")
    if superelevation_context:
        parts.append(f"superelevation={superelevation_context}")
    if low_point_count:
        parts.append(f"low-point candidates={low_point_count}, z={low_point_z:.3f}")
    if flow_hint_summary:
        parts.append(f"flow hint={flow_hint_summary}")
    if tie_in_preview_ref:
        parts.append(f"tie-in preview={tie_in_preview_ref}")
    if tie_in_preview_status:
        parts.append(f"tie-in status={tie_in_preview_status}")
    if tie_in_diagnostic_count:
        parts.append(f"tie-in diagnostics={tie_in_diagnostic_count}")
    if intersection_diagnostic_count:
        parts.append(f"intersection diagnostics={intersection_diagnostic_count}")
    if boundary_status:
        parts.append(f"boundary={boundary_status}")
    if boundary_segment_count:
        parts.append(f"boundary segments={boundary_segment_count}")
    if boundary_arc_count:
        parts.append(f"boundary arcs={boundary_arc_count}")
    if boundary_preview_ref:
        parts.append(f"boundary preview={boundary_preview_ref}")
    if boundary_diagnostic_count:
        parts.append(f"boundary diagnostics={boundary_diagnostic_count}")
    if patch_boundary_status:
        parts.append(f"patch boundary={patch_boundary_status}")
    if patch_boundary_point_count:
        parts.append(f"patch boundary points={patch_boundary_point_count}")
    if patch_boundary_closed:
        parts.append(f"patch boundary closed={patch_boundary_closed}")
    if patch_boundary_self_crossing == "Yes":
        parts.append("patch boundary self-crossing=Yes")
    if patch_boundary_hole_count:
        parts.append(f"patch boundary holes={patch_boundary_hole_count}")
    if patch_boundary_island_count:
        parts.append(f"patch boundary islands={patch_boundary_island_count}")
    if patch_boundary_diagnostic_count:
        parts.append(f"patch boundary diagnostics={patch_boundary_diagnostic_count}")
        if patch_boundary_diagnostics:
            parts.append(f"patch boundary first diagnostic={patch_boundary_diagnostics[0]}")
    if patch_degenerate_count:
        parts.append(f"degenerate triangles={patch_degenerate_count}")
    if patch_long_edge_count:
        parts.append(f"long boundary edges={patch_long_edge_count}")
    if patch_triangulation_mode:
        parts.append(f"triangulation={patch_triangulation_mode}")
    if patch_boundary_strategy:
        parts.append(f"surface boundary={patch_boundary_strategy}")
    if patch_structured_strip_count:
        parts.append(f"structured strips={patch_structured_strip_count}")
    if patch_curb_return_surface_edge_count:
        parts.append(f"curb-return surface edges={patch_curb_return_surface_edge_count}")
    if patch_curb_return_arc_count:
        parts.append(f"curb-return arcs={patch_curb_return_arc_count}")
    if patch_curb_return_arc_sample_count:
        parts.append(f"arc samples={patch_curb_return_arc_sample_count}")
    if patch_curb_return_arc_segment_count:
        parts.append(f"arc segments={patch_curb_return_arc_segment_count}")
    if patch_edge_blend_face_count:
        parts.append(f"edge blend faces={patch_edge_blend_face_count}")
    if patch_boundary_role_summary:
        parts.append(f"boundary roles={patch_boundary_role_summary}")
    if patch_pavement_tie_in_edge_count:
        parts.append(f"pavement tie-in edges={patch_pavement_tie_in_edge_count}")
    if patch_stem_tie_in_edge_count:
        parts.append(f"stem tie-in edges={patch_stem_tie_in_edge_count}")
    if patch_overlap_cut_edge_count:
        parts.append(f"overlap-cut edges={patch_overlap_cut_edge_count}")
    if patch_curb_return_edge_count:
        parts.append(f"curb-return edges={patch_curb_return_edge_count}")
    if patch_bbox_aspect_ratio:
        parts.append(f"boundary bbox ratio={patch_bbox_aspect_ratio:.3f}")
    if patch_min_triangle_quality:
        parts.append(f"min triangle quality={patch_min_triangle_quality:.3f}")
    if patch_skinny_triangle_count:
        parts.append(f"skinny triangles={patch_skinny_triangle_count}")
    if implementation_mode:
        parts.append(f"implementation={implementation_mode}")
    if redesign_path:
        parts.append(f"next={redesign_path}")
    return "; ".join(parts)


def _normalize_corridor_build_review_status(status: str, *, default: str = "missing") -> str:
    value = str(status or "").strip().lower()
    if value == "warn":
        value = "warning"
    if value == "not_built":
        value = "missing"
    if value in CORRIDOR_BUILD_REVIEW_STATUS_VALUES:
        return value
    return str(default or "missing")


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


def _corridor_build_preview_diagnostic_object(document, role: str):
    if document is None:
        return None
    name = CORRIDOR_BUILD_PREVIEW_DIAGNOSTIC_OBJECTS.get(str(role or ""))
    if not name:
        return None
    try:
        return document.getObject(name)
    except Exception:
        return None


def _record_corridor_build_preview_diagnostic(
    document,
    *,
    role: str,
    surface_kind: str,
    status: str,
    notes: str,
    project=None,
):
    if document is None:
        return None
    object_name = CORRIDOR_BUILD_PREVIEW_DIAGNOSTIC_OBJECTS.get(str(role or ""))
    if not object_name:
        return None
    try:
        obj = document.getObject(object_name)
        if obj is None:
            obj = document.addObject("App::FeaturePython", object_name)
        obj.Label = f"{surface_kind or role} preview diagnostic"
        _set_preview_property(obj, "CRRecordKind", "v1_corridor_surface_preview_diagnostic")
        _set_preview_property(obj, "SurfaceRole", str(role or ""))
        _set_preview_property(obj, "SurfaceKind", str(surface_kind or ""))
        _set_preview_property(obj, "PreviewStatus", str(status or "missing"))
        _set_preview_property(obj, "PreviewDiagnostic", str(notes or "Surface preview was not created."))
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project or find_project(document), obj)
        except Exception:
            pass
        return obj
    except Exception:
        return None


def _remove_corridor_build_preview_diagnostic(document, role: str) -> None:
    object_name = CORRIDOR_BUILD_PREVIEW_DIAGNOSTIC_OBJECTS.get(str(role or ""))
    if object_name:
        _remove_preview_object(document, object_name)


def _corridor_centerline_preview_points(document, app_module):
    centerline_result = _build_corridor_centerline3d_result(document)
    points, stations, result_id = _centerline_points_from_centerline3d_result(centerline_result, app_module)
    if len(points) >= 2:
        return points, stations, "centerline3d_result", result_id
    return [], [], "", ""


def _build_corridor_centerline3d_result(document):
    try:
        from .cmd_centerline3d import build_document_centerline3d_result

        return build_document_centerline3d_result(document)
    except Exception:
        return None


def _centerline_points_from_centerline3d_result(centerline_result, app_module):
    if str(getattr(centerline_result, "status", "") or "") != "ready":
        return [], [], ""
    try:
        from ..services.evaluation import Centerline3DFrameService

        frame_service = Centerline3DFrameService()
    except Exception:
        frame_service = None
    points = []
    stations = []
    for row in sorted(
        list(getattr(centerline_result, "point_rows", []) or []),
        key=lambda value: float(getattr(value, "station", 0.0) or 0.0),
    ):
        try:
            station = float(getattr(row, "station", 0.0) or 0.0)
            if frame_service is not None:
                frame = frame_service.resolve_station(centerline_result, station)
                point = app_module.Vector(float(frame.x), float(frame.y), float(frame.z))
            else:
                point = app_module.Vector(float(row.x), float(row.y), float(row.z))
        except Exception:
            continue
        if points and _same_centerline_point(points[-1], point):
            continue
        points.append(point)
        stations.append(station)
    return points, stations, str(getattr(centerline_result, "centerline3d_result_id", "") or "")


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


def _corridor_build_auxiliary_preview_objects(document) -> list[object]:
    if document is None:
        return []
    names = (
        "V1CorridorIntersectionTieInEdgePreview",
        "V1CorridorIntersectionBoundarySegmentPreview",
        "V1CorridorIntersectionExclusionZonePreview",
        "V1CorridorSlopeFaceGenerationBoundaryPreview",
        "V1CorridorIntersectionSlopeFaceBoundaryPreview",
        "V1CorridorIntersectionSlopeFaceOverlapPreview",
    )
    output = []
    for name in names:
        try:
            obj = document.getObject(name)
        except Exception:
            obj = None
        if obj is not None:
            output.append(obj)
    return output


def _corridor_build_region_preview_objects(document) -> list[object]:
    if document is None:
        return []
    output = []
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if name.startswith(("V1CorridorRegionSurface_", "V1CorridorRegionStructure_")):
            output.append(obj)
    return output


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
    _set_preview_integer_property(obj, "IntersectionCurbReturnSlopeBandEdgeCount", int(float(quality.get("intersection_curb_return_slope_band_edge_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionCurbReturnSlopeBandTriangleCount", int(float(quality.get("intersection_curb_return_slope_band_triangle_count", 0) or 0)))
    _set_preview_float_property(obj, "IntersectionCurbReturnSlopeBandWidth", float(quality.get("intersection_curb_return_slope_band_width", 0.0) or 0.0))
    _set_preview_float_property(obj, "IntersectionCurbReturnSlopeBandSlope", float(quality.get("intersection_curb_return_slope_band_slope", 0.0) or 0.0))
    _set_preview_integer_property(obj, "IntersectionSlopeTieInEdgeCount", int(float(quality.get("intersection_slope_tie_in_edge_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSlopeTieInTriangleCount", int(float(quality.get("intersection_slope_tie_in_triangle_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSideSlopeExtensionEdgeCount", int(float(quality.get("intersection_side_slope_extension_edge_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSideSlopeExtensionTriangleCount", int(float(quality.get("intersection_side_slope_extension_triangle_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSlopeGapClosureEdgePairCount", int(float(quality.get("intersection_slope_gap_closure_edge_pair_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSlopeGapClosureTriangleCount", int(float(quality.get("intersection_slope_gap_closure_triangle_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSlopeCornerClosureTriangleCount", int(float(quality.get("intersection_slope_corner_closure_triangle_count", 0) or 0)))
    _set_preview_float_property(obj, "IntersectionSlopeGapClosureMaxGapDistance", float(quality.get("intersection_slope_gap_closure_max_gap_distance", 0.0) or 0.0))
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
    used_vertex_ids = _tin_surface_used_vertex_ids(surface)
    for vertex in list(getattr(surface, "vertex_rows", []) or []):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        if used_vertex_ids and vertex_id not in used_vertex_ids:
            continue
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
    used_vertex_ids = _tin_surface_used_vertex_ids(surface)
    rows: list[dict[str, str]] = []
    for vertex in list(getattr(surface, "vertex_rows", []) or []):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        if used_vertex_ids and vertex_id not in used_vertex_ids:
            continue
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


def _tin_surface_used_vertex_ids(surface) -> set[str]:
    used: set[str] = set()
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        for value in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", "")):
            text = str(value or "")
            if text:
                used.add(text)
    return used


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
    for part_index in range(len(parts) - 1):
        token = str(parts[part_index] or "")
        if not token.startswith("v"):
            continue
        try:
            index = int(token[1:])
        except Exception:
            continue
        side = str(parts[part_index + 1] or "").strip().lower()
        if side not in {"left", "right"}:
            continue
        return index, "L" if side == "left" else "R"
    return None


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
