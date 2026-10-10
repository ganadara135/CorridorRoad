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

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ...objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree, find_project
from ..common.model_fields import (
    intersection_row_by_id,
    section_float_attr,
    section_region_id,
    section_station,
    section_structure_values,
    surface_point_role_counts,
    unique_join,
    unique_refs,
)
from ..exchange import export_exchange_package_to_ifc, export_exchange_package_to_json
from ..objects.obj_alignment import to_alignment_model
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_corridor import create_or_update_v1_corridor_model_object, find_v1_corridor_model, to_corridor_model
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_exchange_package import create_or_update_v1_exchange_package_object, find_v1_exchange_package
from ..objects.obj_intersection import (
    find_v1_intersection_model,
    stored_intersection_spec,
    to_intersection_model,
)
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..objects.obj_surface import create_or_update_v1_surface_model_object, find_v1_surface_model, to_surface_model
from ..objects.persistence_payload_adapter import read_incremental_record, write_incremental_record
from ..objects.project_document_adapter import ProjectDocumentAdapter
from ..objects.obj_surface_transition import (
    create_or_update_v1_surface_transition_model_object,
    find_v1_surface_transition_model,
    to_surface_transition_model,
)
from ..models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ..services.evaluation.incremental_rebuild_service import IncrementalRebuildService
from ..models.result import intersection_tie_in_edge as _intersection_tie_in_edge_models
from ..models.result.tin_surface import TINSurface
from ..models.result.shared_breakline import SharedBreaklinePointRow, SharedBreaklineResult, SharedBreaklineRow
from ..services.builders import (
    CorridorDesignSurfaceGeometryRequest,
    CorridorModelBuildRequest,
    CorridorModelService,
    CorridorSurfaceBuildRequest,
    CorridorSurfaceGeometryBuildRequest,
    CorridorSurfaceOrchestrationService,
    CorridorSurfaceService,
    QuantityBuildRequest,
    QuantityBuildService,
    StructureSolidBuildRequest,
    StructureSolidOutputService,
    supplemental_sampled_sections,
    transition_augmented_applied_section_set,
)
from ..services.builders.corridor_surface_geometry_service import (
    SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
    SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_summary,
)
from ..ui.presentation.intersection_kernel_review_presentation import (
    intersection_kernel_review_rows,
    intersection_kernel_row_polylines,
)
from ..services.builders.intersection_kernel_surface_service import (
    clip_tin_surface_by_station_spans,
    intersection_geometry_from_models,
    kernel_tin_surface,
)
from ..services.evaluation.surface_transition_validation_service import SurfaceTransitionValidationService
from ..services.evaluation.intersection_evaluation_service import (
    IntersectionPatchPrerequisiteResult,
)
from ..services.evaluation.region_boundary_continuity_evaluation_service import (
    region_boundary_diagnostic_summary,
    region_boundary_diagnostics,
    region_boundary_status,
    region_intersection_context_diagnostics,
    region_sample_coverage_diagnostics,
    region_source_range_diagnostics,
)
from ..services.evaluation.station_context_resolver import StationContextResolver
from ..services.evaluation.shared_breakline_audit_service import SharedBreaklineAuditService
from ..services.builders.shared_breakline_tin_builder_service import (
    tin_surface_with_shared_breakline_constraint_edges,
    tin_surface_with_shared_breakline_metadata,
)
from ..services.mapping import ExchangeOutputMapper, ExchangePackageRequest, QuantityOutputMapper, SectionOutputMapper
from ..services.mapping.tin_mesh_preview_mapper import TINMeshPreviewMapper
from ..services.mapping.preview_audit_row_mapper import shared_breakline_segment_rows
from ..services.geometry import xy_point_in_polygon, xy_point_in_polygon_strict
from ..ui.common.styles import apply_clickable_tab_style
# shared_breakline_audit_display_rows has no caller here: the build corridor
# panel receives it through the runtime binding map built from globals().
from ..ui.presentation.shared_breakline_audit_presentation import shared_breakline_audit_display_rows  # noqa: F401
from ..ui.presentation.shared_breakline_audit_presentation import (
    shared_breakline_audit_rows_from_preview_objects,
    SharedBreaklineAuditPresentationMapper,
    _normalize_corridor_build_review_status,
)
from ..ui.presentation.build_corridor_preview_adapter import (
    BuildCorridorPreviewAdapter,
)
from ..ui.viewers.build_corridor_view import (
    V1BuildCorridorTaskPanel,
    configure_build_corridor_task_panel_runtime,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree
from ..ui.presentation.drainage_flow_review_presentation import (
    DRAINAGE_FLOW_REVIEW_MISSING_MODEL_NOTE,
    DRAINAGE_FLOW_REVIEW_NO_ROUTES_NOTE,
    DRAINAGE_FLOW_REVIEW_PRESET_MODEL_NOTE,
    drainage_flow_review_placeholder_row,
    drainage_flow_review_rows,
)
from ..ui.presentation.subassembly_guided_review_presentation import subassembly_kind_guided_review_rows
from ..ui.presentation.build_review_presentation import (
    applied_sections_review_summary,
    subassembly_surface_role_review_note,
    _corridor_build_review_row,
    _with_applied_section_review_summary,
    _with_subassembly_surface_role_review_note,
)
from ..ui.presentation.drainage_review_presentation import (
    DRAINAGE_REVIEW_MISSING_APPLIED_SECTIONS_NOTE,
    DRAINAGE_REVIEW_NO_STATION_ROWS_NOTE,
    drainage_review_placeholder_row,
    drainage_review_station_rows,
    intersection_drainage_review_rows,
    _drainage_point_side,
    _drainage_review_marker_name,
)

IntersectionTieInEdgeRow = _intersection_tie_in_edge_models.IntersectionTieInEdgeRow


_BUILD_CORRIDOR_PANEL_RUNTIME_IMPORTS = (
    find_v1_surface_model,
    apply_clickable_tab_style,
)


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
    ("intersection_slope", "Intersection Slope Face Surface", "V1CorridorIntersectionSlopeFaceSurfacePreview"),
    ("intersection_tie_slope", "Intersection Tie Slope Surface", "V1CorridorIntersectionTieSlopeSurfacePreview"),
    ("drainage", "Drainage Surface", "V1CorridorDrainageSurfacePreview"),
)
CORRIDOR_BUILD_PREVIEW_DIAGNOSTIC_OBJECTS = {
    "design": "V1CorridorDesignSurfacePreviewDiagnostic",
    "intersection": "V1CorridorIntersectionSurfacePreviewDiagnostic",
    "intersection_slope": "V1CorridorIntersectionSlopeFaceSurfacePreviewDiagnostic",
    "intersection_tie_slope": "V1CorridorIntersectionTieSlopeSurfacePreviewDiagnostic",
    "subgrade": "V1CorridorSubgradeSurfacePreviewDiagnostic",
    "daylight": "V1CorridorDaylightSurfacePreviewDiagnostic",
    "drainage": "V1CorridorDrainageSurfacePreviewDiagnostic",
}
BUILD_PARAMETRIC_ESTIMATE_BASE_SECONDS = 3.0
BUILD_PARAMETRIC_ESTIMATE_MIN_PER_SECTION_SECONDS = 0.10
BUILD_PARAMETRIC_ESTIMATE_MAX_PER_SECTION_SECONDS = 0.22
BUILD_PARAMETRIC_ESTIMATE_MIN_PER_SUPPLEMENTAL_SECONDS = 0.18
BUILD_PARAMETRIC_ESTIMATE_MAX_PER_SUPPLEMENTAL_SECONDS = 0.42
CORRIDOR_BUILD_GUIDED_REVIEW_STEPS = (
    ("centerline", "1. Centerline", ("centerline",), "Check 3D centerline continuity and station ordering."),
    ("design", "2. Design Surface", ("centerline", "design"), "Check finished-grade surface continuity."),
    ("intersections", "4. Intersections", ("intersection",), "Check intersection-controlled Region context and Applied Sections handoff."),
    ("slope_issues", "5. Side Slope", ("daylight", "intersection_slope"), "Review ordinary and intersection-owned Side Slope result surfaces and their diagnostics separately."),
    ("drainage", "6. Drainage Surface", ("centerline", "drainage"), "Check roadside ditch surfaces and intersection low-point drainage coverage."),
    ("drainage_flow", "7. Drainage Flow", ("centerline", "drainage"), "Check Flow Route connections and linked drainage structures."),
)
BUILD_CORRIDOR_PANEL_MIN_WIDTH = 420
BUILD_CORRIDOR_PANEL_MAX_WIDTH = 16777215
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
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
    progress_callback=None,
):
    """Persist result stages in one transaction and perform one deliberate recompute."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    with ProjectDocumentAdapter(doc).transaction("Build v1 corridor", recompute=True):
        return _apply_v1_corridor_model_in_transaction(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            build_surfaces=build_surfaces,
            show_daylight_contact_markers=show_daylight_contact_markers,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
            progress_callback=progress_callback,
        )


def _apply_v1_corridor_model_in_transaction(
    *,
    document=None,
    project=None,
    corridor_model=None,
    build_surfaces: bool = True,
    show_daylight_contact_markers: bool = True,
    supplemental_sampling_enabled: bool = True,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
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
        _notify_progress(progress_callback, 45, "Building model...")
        corridor_model = build_document_corridor_model(doc, project=prj)
    surface_model = None
    if build_surfaces:
        _notify_progress(progress_callback, 50, "Building corridor surfaces...")
        surface_model = build_document_corridor_surface_model(doc, project=prj, corridor_model=corridor_model)
        corridor_model.surface_build_refs = [str(getattr(surface_model, "surface_model_id", "") or "surface:main")]
    _notify_progress(progress_callback, 65, "Writing CorridorModel object...")
    obj = _persist_incremental_corridor_model(doc, prj, corridor_model)
    if surface_model is not None:
        _notify_progress(progress_callback, 70, "Writing SurfaceModel object...")
        _persist_incremental_surface_model(doc, prj, surface_model)
        _notify_progress(progress_callback, 74, "Creating centerline preview...")
        create_corridor_centerline_3d_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            applied_section_set_ref=str(getattr(corridor_model, "applied_section_set_ref", "") or ""),
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        _notify_progress(progress_callback, 78, "Creating design surface preview...")
        create_corridor_design_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        _notify_progress(progress_callback, 80, "Creating Region surface objects...")
        create_corridor_region_surface_previews(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
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
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        _notify_progress(progress_callback, 86, "Creating slope face preview...")
        create_corridor_daylight_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            show_daylight_contact_markers=show_daylight_contact_markers,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        _notify_progress(progress_callback, 90, "Creating drainage preview...")
        create_corridor_drainage_surface_preview(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
            supplemental_sampling_enabled=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        _notify_progress(progress_callback, 91, "Creating Subassembly kind review objects...")
        create_corridor_subassembly_kind_review_previews(
            document=doc,
            project=prj,
        )
        _notify_progress(progress_callback, 92, "Creating transition span markers...")
        create_corridor_surface_transition_span_markers(
            document=doc,
            project=prj,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
    _notify_progress(progress_callback, 94, "Finalizing document transaction...")
    return obj


def _persist_incremental_corridor_model(document, project, corridor_model):
    existing = find_v1_corridor_model(document)
    previous_model = to_corridor_model(existing) if existing is not None else None
    previous_record = read_incremental_record(existing) if existing is not None else None
    service = IncrementalRebuildService()
    decision = service.decide(
        stage_name="corridor_model",
        service_version="corridor-model-persistence:1",
        engineering_input=corridor_model,
        previous_record=previous_record,
    )
    execution = service.execute(
        decision=decision,
        service_version="corridor-model-persistence:1",
        builder=lambda: corridor_model,
        previous_result=previous_model,
        previous_record=previous_record,
        consumed_source_refs=tuple(getattr(corridor_model, "source_refs", ()) or ()),
        consumed_result_refs=(str(getattr(corridor_model, "applied_section_set_ref", "") or ""),),
    )
    if decision.reuse_previous:
        return existing
    obj = create_or_update_v1_corridor_model_object(document=document, project=project, corridor_model=execution.result)
    write_incremental_record(obj, execution.record)
    return obj


def _persist_incremental_surface_model(document, project, surface_model):
    existing = find_v1_surface_model(document)
    previous_model = to_surface_model(existing) if existing is not None else None
    previous_record = read_incremental_record(existing) if existing is not None else None
    service = IncrementalRebuildService()
    decision = service.decide(
        stage_name="surface_model",
        service_version="surface-model-persistence:1",
        engineering_input=surface_model,
        previous_record=previous_record,
    )
    execution = service.execute(
        decision=decision,
        service_version="surface-model-persistence:1",
        builder=lambda: surface_model,
        previous_result=previous_model,
        previous_record=previous_record,
        consumed_source_refs=tuple(getattr(surface_model, "source_refs", ()) or ()),
        consumed_result_refs=(str(getattr(surface_model, "corridor_id", "") or ""),),
    )
    if decision.reuse_previous:
        return existing
    obj = create_or_update_v1_surface_model_object(document=document, project=project, surface_model=execution.result)
    write_incremental_record(obj, execution.record)
    return obj


def corridor_build_review_rows(document=None) -> list[dict[str, object]]:
    """Return display-ready Build Corridor result rows from document preview objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied_summary = corridor_applied_sections_review_summary(doc)
    rows: list[dict[str, object]] = []
    intersection_preview = _corridor_build_preview_object(doc, "intersection") if doc is not None else None
    is_roundabout_preview = (
        str(getattr(intersection_preview, "IntersectionKind", "") or "").strip().lower() == "roundabout"
    )
    # the kernel builds no tie slope; its two surfaces carry their own review notes
    kernel = _document_has_intersection(doc)
    for role, title, object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        if (is_roundabout_preview or kernel) and role == "intersection_tie_slope":
            continue
        obj = doc.getObject(object_name) if doc is not None else None
        diagnostic = _corridor_build_preview_diagnostic_object(doc, role)
        row = _corridor_build_review_row(
            role,
            title,
            object_name,
            obj,
            diagnostic=diagnostic,
            absent_note_for_role=lambda absent_role: _corridor_build_review_absent_note(doc, absent_role),
        )
        row = _with_subassembly_surface_role_review_note(
            row,
            lambda surface_role: _subassembly_surface_role_review_note(doc, surface_role=surface_role),
        )
        if kernel and role in {"intersection", "intersection_slope"}:
            row = _with_intersection_kernel_review_note(row, obj)
        rows.append(
            _with_applied_section_review_summary(
                row,
                applied_summary,
            )
        )
    return rows


def _with_intersection_kernel_review_note(row: dict[str, object], obj) -> dict[str, object]:
    """The review note of a kernel-built intersection surface: its status, triangles and quality."""

    if obj is None:
        return row
    quality = dict(
        (parts[0], parts[1])
        for parts in (str(value).split("|", 1) for value in list(getattr(obj, "IntersectionKernelQualityRows", []) or []))
        if len(parts) == 2
    )
    prefix = "patch" if str(row.get("role", "")) == "intersection" else "slope"
    notes = (
        f"Built by the intersection kernel; status={getattr(obj, 'IntersectionKernelStatus', '') or '-'}; "
        f"triangles={quality.get(prefix + '_triangle_count', '-')}; "
        f"min_quality={quality.get(prefix + '_triangle_min_quality', '-')}; "
        f"skinny={quality.get(prefix + '_triangle_skinny_count', '-')}"
    )
    diagnostics = [str(value) for value in list(getattr(obj, "IntersectionKernelDiagnosticRows", []) or [])]
    if diagnostics:
        notes += "; diagnostics=" + " / ".join(diagnostics)
    updated = dict(row)
    updated["notes"] = notes
    return updated


def corridor_shared_breakline_audit_rows(document=None) -> list[dict[str, object]]:
    """Return panel-friendly shared breakline audit rows from built preview objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return []
    preview_entries = []
    for role, title, object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        obj = _corridor_build_preview_object(doc, role)
        if obj is None:
            continue
        preview_entries.append((role, title, object_name, obj))
    return shared_breakline_audit_rows_from_preview_objects(preview_entries)


def corridor_shared_breakline_audit_summary(document=None) -> dict[str, object]:
    rows = corridor_shared_breakline_audit_rows(document)
    if not rows:
        return {
            "status": "missing",
            "title": "Shared breakline audit not available",
            "notes": "Build Parametric has not produced shared breakline audit metadata yet.",
            "issue_count": 0,
        }
    issue_rows = [
        row for row in rows
        if _shared_breakline_audit_summary_issue_reasons(row)
    ]
    if not issue_rows:
        return {
            "status": "ready",
            "title": "No shared breakline issues",
            "notes": f"{len(rows)} audited surface(s); contract and mesh endpoints match the shared breakline contract.",
            "issue_count": 0,
        }
    mismatch_count = sum(int(row.get("geometry_mismatch_count", 0) or 0) for row in issue_rows)
    mesh_mismatch_count = sum(int(row.get("mesh_mismatch_count", 0) or 0) for row in issue_rows)
    missing_count = sum(int(row.get("missing_consumer_count", 0) or 0) for row in issue_rows)
    shared_mismatch_count = sum(int(row.get("mismatch_count", 0) or 0) for row in issue_rows)
    reversed_count = sum(int(row.get("reversed_edge_count", 0) or 0) for row in issue_rows)
    status_warning_count = sum(
        1 for row in issue_rows
        if str(row.get("status", "") or "").strip().lower() not in {"", "ready"}
    )
    return {
        "status": "warning",
        "title": f"Shared breakline issues found: {len(issue_rows)} surface(s)",
        "notes": (
            f"geometry_mismatch={mismatch_count}; mesh_mismatch={mesh_mismatch_count}; "
            f"missing_consumer={missing_count}; mismatch={shared_mismatch_count}; reversed={reversed_count}; "
            f"status_warning={status_warning_count}"
        ),
        "issue_count": len(issue_rows),
    }


def _shared_breakline_audit_summary_issue_reasons(row: dict[str, object]) -> list[str]:
    count_fields = {
        "geometry_mismatch": "geometry_mismatch_count",
        "mesh_mismatch": "mesh_mismatch_count",
        "missing_consumer": "missing_consumer_count",
        "mismatch": "mismatch_count",
        "reversed": "reversed_edge_count",
    }
    return [reason for reason, field_name in count_fields.items() if int(row.get(field_name, 0) or 0)]


def _breakline_audit_surface_row_focuses_source_only(row: dict[str, object]) -> bool:
    """Return True when a surface summary row should not create overlay geometry."""

    if str(row.get("row_kind", "") or "") not in {"", "surface"}:
        return False
    role = str(row.get("role", "") or "")
    if role in {"intersection", "intersection_slope"}:
        return True
    return False


def corridor_build_review_outcome_matrix() -> list[dict[str, str]]:
    """Return the deterministic Build Parametric review status meanings."""

    return [
        {"status": str(status), "meaning": str(meaning)}
        for status, meaning in CORRIDOR_BUILD_REVIEW_OUTCOME_MATRIX
    ]


def _subassembly_surface_role_review_note(document, *, surface_role: str) -> str:
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    return subassembly_surface_role_review_note(applied, surface_role=surface_role)


def corridor_subassembly_kind_guided_review_rows(document=None) -> list[dict[str, object]]:
    """Return guided-review rows split by evaluated Subassembly kind."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return []
    sections = _station_ordered_applied_sections(applied)
    return subassembly_kind_guided_review_rows(sections)


def _subassembly_kind_display_name(kind: str) -> str:
    text = str(kind or "unknown").strip() or "unknown"
    return " ".join(part.capitalize() for part in text.replace("-", "_").split("_") if part)


def _format_count_summary(counts: dict[str, int], *, limit: int = 5) -> str:
    if not counts:
        return "none"
    rows = sorted(((str(key), int(value)) for key, value in counts.items()), key=lambda item: (-item[1], item[0]))
    text = ", ".join(f"{_display_source_ref(key)}:{value}" for key, value in rows[:limit])
    if len(rows) > limit:
        text += f", +{len(rows) - limit} more"
    return text


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
            row.setdefault("owner_context", "Ordinary road")
            rows.append(row)
    if not rows:
        rows = _parse_slope_face_issue_summary_text(str(getattr(obj, "SlopeFaceIssueStations", "") or ""))
    for row in rows:
        row.setdefault("owner_context", "Ordinary road")
        row["review_status"] = _slope_face_issue_review_status(row)
    return rows


def corridor_build_guided_review_steps(
    document=None,
    *,
    supplemental_sampling_enabled: bool = True,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
) -> list[dict[str, object]]:
    """Return ordered guided-review rows for the Build Corridor panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    review_by_role = {str(row.get("role", "") or ""): row for row in corridor_build_review_rows(doc)}
    issue_count = len(corridor_slope_face_issue_rows(doc))
    drainage_flow_summary = corridor_drainage_flow_review_summary(doc)
    intersection_summary = corridor_intersection_review_summary(doc)
    subassembly_kind_rows = corridor_subassembly_kind_guided_review_rows(doc)
    rows: list[dict[str, object]] = []
    for step_id, title, roles, default_notes in CORRIDOR_BUILD_GUIDED_REVIEW_STEPS:
        if step_id == "slope_issues":
            daylight = review_by_role.get("daylight", {})
            intersection_slope = review_by_role.get("intersection_slope", {})
            base_status = str(daylight.get("status", "missing") or "missing")
            intersection_status = str(intersection_slope.get("status", "missing") or "missing")
            if base_status == "error" or intersection_status == "error":
                status = "error"
            elif (base_status == "ready" or intersection_status == "ready") and issue_count:
                status = "warning"
            elif base_status == "ready" or intersection_status == "ready":
                status = "ready"
            else:
                status = intersection_status if intersection_status not in {"missing", "empty"} else base_status
            intersection_count = intersection_slope.get("triangle_or_point_count", "")
            intersection_note = f"; intersection slope triangles={intersection_count}" if intersection_count not in {"", None} else ""
            boundary_review_note = _slope_face_boundary_guided_review_suffix(daylight, intersection_slope)
            notes = f"{issue_count} Side Slope diagnostic(s) to review{intersection_note}." if issue_count else f"No Side Slope fallback diagnostics{intersection_note}."
            if boundary_review_note:
                notes = f"{notes} {boundary_review_note}"
            if intersection_status == "ready" and base_status == "ready":
                focus = "Intersection and Corridor Slope Face Surfaces"
            elif intersection_status == "ready":
                focus = "Intersection Slope Face Surface"
            elif base_status == "ready":
                focus = "Slope Face Surface"
            else:
                focus = "Side Slope Result Diagnostic"
        else:
            primary_role = str(list(roles)[-1] if roles else "")
            source = review_by_role.get(primary_role, {})
            status = str(source.get("status", "missing") or "missing")
            notes = default_notes if status == "ready" else str(source.get("notes", "") or "Not built yet.")
            focus = str(source.get("result", title) or title)
            output_path = str(source.get("output_path", "") or "")
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
                intersection_source = review_by_role.get("intersection", source)
                status = str(intersection_summary.get("status", status) or status)
                notes = str(intersection_summary.get("notes", default_notes) or default_notes)
                focus = str(intersection_summary.get("focus", "Intersections") or "Intersections")
                output_path = str(intersection_source.get("output_path", output_path) or output_path)
        rows.append(
            {
                "step_id": step_id,
                "title": title,
                "roles": list(roles),
                "status": status,
                "focus": focus,
                "output_path": output_path if step_id != "slope_issues" else str(intersection_slope.get("output_path", "") or daylight.get("output_path", "") or ""),
                "notes": notes,
            }
        )
        if step_id == "design":
            rows.extend(subassembly_kind_rows)
    return rows


def _slope_face_boundary_guided_review_suffix(*review_rows: dict[str, object]) -> str:
    boundary_note = _slope_face_boundary_review_note_from_rows(*review_rows)
    if not boundary_note:
        return ""
    return f"boundary_review=intersection_slope_face_boundary_result; {boundary_note}"


def _slope_face_boundary_review_note_from_rows(*review_rows: dict[str, object]) -> str:
    for row in review_rows:
        notes = str((row or {}).get("notes", "") or "")
        marker = "slope_face_boundary="
        index = notes.find(marker)
        if index < 0:
            continue
        tail = notes[index:].strip()
        if " | " in tail:
            tail = tail.split(" | ", 1)[0].strip()
        return tail
    return ""


def _applied_section_supplemental_consumption_summary(applied_section_set) -> dict[str, object]:
    rows = list(getattr(applied_section_set, "station_rows", []) or [])
    kind_counts: dict[str, int] = {}
    supplemental_count = 0
    for row in rows:
        kind = str(getattr(row, "kind", "") or "regular_sample").strip() or "regular_sample"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if "supplemental" in kind.lower():
            supplemental_count += 1
    total = len(rows)
    return {
        "source_section_count": max(total - supplemental_count, 0),
        "supplemental_section_count": supplemental_count,
        "total_section_count": total,
        "kind_counts": kind_counts,
    }


def _format_build_parametric_duration(seconds: float) -> str:
    value = max(0.0, float(seconds or 0.0))
    if value < 10.0:
        return "<10 sec"
    if value < 60.0:
        return f"{int(round(value / 5.0) * 5)} sec"
    minutes = value / 60.0
    if minutes < 10.0:
        return f"{minutes:.1f} min"
    return f"{int(round(minutes))} min"


def _build_parametric_supplemental_apply_estimate(applied_section_set) -> dict[str, object]:
    summary = _applied_section_supplemental_consumption_summary(applied_section_set)
    source_count = int(summary.get("source_section_count", 0) or 0)
    supplemental_count = int(summary.get("supplemental_section_count", 0) or 0)
    total_count = int(summary.get("total_section_count", 0) or 0)
    if supplemental_count <= 0 or total_count <= 0:
        return {
            "source_section_count": source_count,
            "supplemental_section_count": supplemental_count,
            "total_section_count": total_count,
            "min_seconds": 0.0,
            "max_seconds": 0.0,
            "message": "",
        }
    min_seconds = (
        BUILD_PARAMETRIC_ESTIMATE_BASE_SECONDS
        + (total_count * BUILD_PARAMETRIC_ESTIMATE_MIN_PER_SECTION_SECONDS)
        + (supplemental_count * BUILD_PARAMETRIC_ESTIMATE_MIN_PER_SUPPLEMENTAL_SECONDS)
    )
    max_seconds = (
        BUILD_PARAMETRIC_ESTIMATE_BASE_SECONDS
        + (total_count * BUILD_PARAMETRIC_ESTIMATE_MAX_PER_SECTION_SECONDS)
        + (supplemental_count * BUILD_PARAMETRIC_ESTIMATE_MAX_PER_SUPPLEMENTAL_SECONDS)
    )
    min_text = _format_build_parametric_duration(min_seconds)
    max_text = _format_build_parametric_duration(max_seconds)
    duration_text = min_text if min_text == max_text else f"{min_text} - {max_text}"
    return {
        "source_section_count": source_count,
        "supplemental_section_count": supplemental_count,
        "total_section_count": total_count,
        "min_seconds": min_seconds,
        "max_seconds": max_seconds,
        "duration_text": duration_text,
        "message": (
            "Supplemental Applied Sections detected.\n"
            f"Applied Sections: source {source_count}, supplemental {supplemental_count}, total {total_count}\n"
            f"Estimated Build Parametric time: about {duration_text}\n"
            "Dense supplemental rows can slow surface, drainage, and breakline review generation."
        ),
    }


def _build_parametric_compatibility_supplemental_sampling_enabled(
    document=None,
    *,
    applied_section_set=None,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
) -> bool:
    """Return false because Build Corridor no longer creates hidden supplemental frames."""

    return False


def _build_corridor_effective_hidden_supplemental_sampling_enabled(
    document=None,
    *,
    applied_section_set=None,
    requested: bool,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
) -> bool:
    """Build Corridor no longer performs hidden supplemental sampling."""

    return False


def corridor_intersection_review_summary(document=None) -> dict[str, object]:
    """Return a compact Build Parametric intersection summary from the intersection kernel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if not _document_has_intersection(doc):
        return {"status": "missing", "notes": "No Intersection source in this document.", "focus": "Intersections"}
    result = _document_intersection_kernel_result(doc)
    if result is None:
        return {"status": "missing", "notes": "Run Applied Sections: the intersection is built on them.", "focus": "Intersections"}
    quality = dict(result.quality_rows)
    legs = sum(1 for leg in result.legs if leg.enabled)
    skinny = int(quality.get("patch_triangle_skinny_count", 0)) + int(quality.get("slope_triangle_skinny_count", 0))
    notes = (
        f"Intersection kernel {result.status} for {result.intersection_id} ({result.kind}); {legs} legs; "
        f"intersection surface {int(quality.get('patch_triangle_count', 0))} triangles, "
        f"side slope {int(quality.get('slope_triangle_count', 0))} triangles, {skinny} skinny; "
        f"{len(result.diagnostics)} diagnostic(s)."
    )
    status = {"ready": "ready", "partial": "warning"}.get(result.status, "error")
    if status == "ready" and skinny:
        status = "warning"
    return {"status": status, "notes": notes, "focus": "Intersections"}


def corridor_intersection_contract_review_rows(document=None, *, include_internal: bool = False) -> list[dict[str, object]]:
    """Return the intersection kernel's review rows for the Build Parametric Intersections tab."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    return intersection_kernel_review_rows(_document_intersection_kernel_result(doc))


def focus_corridor_intersection_contract_review_row(document=None, row_index: int = 0, *, include_internal: bool = False):
    """Create/select a clear 3D highlight for one intersection contract review row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_intersection_contract_review_rows(doc, include_internal=include_internal)
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
    """Create a bright linework overlay for one intersection review row: a leg's mouth, a corner's
    arc, the boundary, a drainage low point. None when the row has no linework of its own."""

    if document is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except ImportError:
        return None
    object_name = "ReviewIntersectionContractHighlight"
    _remove_preview_object(document, object_name)
    polylines = intersection_kernel_row_polylines(_document_intersection_kernel_result(document), row)
    shapes = [
        Part.makePolygon([AppModule.Vector(*point) for point in line])
        for line in polylines
        if len(line) >= 2
    ]
    if not shapes:
        return None
    obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = "Intersection Contract Highlight"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_intersection_contract_review_highlight", error=error)
    _set_preview_property(obj, "CRRecordKind", "v1_intersection_contract_review_highlight")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "intersection_contract_review")
    _set_preview_property(obj, "ContractFamily", str(row.get("contract_family", "") or ""))
    _set_preview_property(obj, "ContractRowId", str(row.get("row_id", "") or ""))
    try:
        obj.ViewObject.LineColor = (1.0, 0.85, 0.0)
        obj.ViewObject.LineWidth = 5.0
        obj.ViewObject.PointSize = 6.0
    except Exception:
        pass
    try:
        route_object_to_project_tree(find_project(document), obj)
    except Exception:
        pass
    return obj


def corridor_drainage_flow_review_rows(document=None) -> list[dict[str, object]]:
    """Return Flow Route review rows for Build Corridor Guided Review."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    if drainage_model is None:
        _remove_preview_object(doc, "ReviewIssueDrainageFlowRoutes")
        return [drainage_flow_review_placeholder_row(DRAINAGE_FLOW_REVIEW_MISSING_MODEL_NOTE)]
    if _is_intersection_preset_drainage_model(drainage_model):
        _remove_preview_object(doc, "ReviewIssueDrainageFlowRoutes")
        return [drainage_flow_review_placeholder_row(DRAINAGE_FLOW_REVIEW_PRESET_MODEL_NOTE)]
    structure_model = to_structure_model(find_v1_structure_model(doc))
    rows = drainage_flow_review_rows(
        drainage_model,
        structure_model,
        highlight_mode_for_route=lambda route_id: _drainage_flow_row_highlight_mode(doc, route_id),
    )
    if not rows:
        _remove_preview_object(doc, "ReviewIssueDrainageFlowRoutes")
        return [drainage_flow_review_placeholder_row(DRAINAGE_FLOW_REVIEW_NO_ROUTES_NOTE)]
    return rows


def _is_intersection_preset_drainage_model(drainage_model) -> bool:
    drainage_model_id = str(getattr(drainage_model, "drainage_model_id", "") or "")
    if drainage_model_id.startswith("drainage:intersection-preset-"):
        return True
    source_refs = [str(value or "") for value in list(getattr(drainage_model, "source_refs", []) or [])]
    if any(value.startswith("intersection:") for value in source_refs):
        flow_rows = list(getattr(drainage_model, "flow_route_rows", []) or [])
        return all(
            str(getattr(row, "flow_route_id", "") or "").startswith("flow-route:intersection-")
            for row in flow_rows
        )
    return False


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
        return [drainage_review_placeholder_row(DRAINAGE_REVIEW_MISSING_APPLIED_SECTIONS_NOTE)]
    region_model = to_region_model(find_v1_region_model(doc))
    drainage_model = to_drainage_model(find_v1_drainage_model(doc))
    output = drainage_review_station_rows(
        applied,
        active_ditch_rows_for=lambda station: _active_ditch_drainage_rows(
            drainage_model,
            region_model=region_model,
            station=station,
        ),
    )
    if not output:
        return [drainage_review_placeholder_row(DRAINAGE_REVIEW_NO_STATION_ROWS_NOTE)]
    output.extend(corridor_intersection_drainage_review_rows(doc, marker_start_index=len(output)))
    return output


def corridor_intersection_drainage_review_rows(document=None, *, marker_start_index: int = 0) -> list[dict[str, object]]:
    """Return intersection low-point and Drainage Element coverage diagnostics.

    The low point is the intersection kernel's drainage candidate (K7): the lowest vertex of the
    intersection surface, with its nearest road and station.
    """

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    result = _document_intersection_kernel_result(doc)
    if result is None or not result.drainage_candidates:
        return []
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    row = next(
        (r for r in list(getattr(intersection_model, "intersection_rows", []) or []) if str(getattr(r, "intersection_id", "") or "") == result.intersection_id),
        None,
    )
    context = IntersectionPatchPrerequisiteResult(
        status="ready",
        intersection_id=result.intersection_id,
        intersection_kind=result.kind,
        alignment_refs=tuple(ref for ref, _station in result.anchor_station_by_road),
        control_region_refs=tuple(str(ref) for ref in list(getattr(row, "control_region_refs", []) or [])),
    )
    patch_points = [
        {"alignment_id": candidate.road_ref, "station": candidate.station, "x": candidate.x, "y": candidate.y, "z": candidate.z}
        for candidate in result.drainage_candidates
    ]
    low_point = patch_points[0]
    coverage = _intersection_drainage_coverage(
        to_drainage_model(find_v1_drainage_model(doc)),
        context,
        low_point_station=float(low_point["station"]),
    )
    return intersection_drainage_review_rows(
        context,
        patch_points=patch_points,
        low_point=low_point,
        low_points=patch_points,
        coverage=coverage,
        marker_start_index=marker_start_index,
    )


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
            diagnostics.extend(region_boundary_diagnostics(groups[index - 1]["sections"][-1], first, boundary_side="start"))
        if index < len(groups) - 1:
            diagnostics.extend(region_boundary_diagnostics(last, groups[index + 1]["sections"][0], boundary_side="end"))
        boundary_status = region_boundary_status(diagnostics)
        row = {
            "alignment_id": unique_join(_section_text_values(group_sections, "alignment_id")),
            "region_id": str(group.get("region_id", "") or ""),
            "station_start": float(group.get("station_start", 0.0) or 0.0),
            "station_end": float(group.get("station_end", 0.0) or 0.0),
            "assembly": unique_join(_section_text_values(group_sections, "assembly_id")),
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
            "diagnostics": region_boundary_diagnostic_summary(diagnostics),
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
                "target_surfaces": unique_join(list(getattr(transition, "target_surface_kinds", []) or [])),
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
        sections = [section for section in sections if section_region_id(section) == selected_region]
    station_candidates = [
        (section_station(section), section_region_id(section))
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


def focus_corridor_build_guided_review_step(
    document=None,
    step_id: str = "centerline",
    *,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
):
    """Focus one guided review step and isolate its relevant preview layers."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    step_id_text = str(step_id or "").strip()
    if step_id_text.startswith("subassembly_kind:"):
        kind = step_id_text.split(":", 1)[1]
        set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
        return focus_corridor_subassembly_kind_review(doc, kind)
    if step_id_text == "supplemental_frames":
        if doc is None:
            raise RuntimeError("No active document.")
        set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
        obj = create_or_update_corridor_supplemental_frame_markers(
            document=doc,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
            visible=True,
        )
        if obj is None:
            raise RuntimeError("Supplemental frame markers were not created.")
        set_corridor_build_preview_visibility(doc, "centerline", True)
        set_corridor_build_preview_visibility(doc, "design", True)
        _set_object_visibility(obj, True)
        _select_and_fit_object(obj)
        return obj
    step = _corridor_build_guided_review_step(step_id)
    if doc is None or step is None:
        raise RuntimeError(f"Guided review step was not found: {step_id}")
    set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
    if step[0] != "slope_issues":
        for role in list(step[2] or []):
            set_corridor_build_preview_visibility(doc, role, True)
    if step[0] == "slope_issues":
        _remove_preview_object(doc, "ReviewIssueSubassemblyKind_side_slope")
        obj = _focus_corridor_side_slope_result_preview(doc)
        if obj is not None:
            return obj
        raise RuntimeError(_side_slope_review_missing_result_message(doc))
    if step[0] == "drainage_flow":
        return focus_corridor_drainage_flow_review(doc)
    focus_role = str(list(step[2])[-1] if step[2] else "")
    obj = _corridor_build_preview_object(doc, focus_role)
    if obj is None:
        raise RuntimeError(f"Guided review target has not been built: {step[1]}")
    _select_and_fit_object(obj)
    return obj


def focus_corridor_subassembly_kind_review(document=None, kind: str = ""):
    """Focus a review result for one evaluated Subassembly kind.

    Lane and Shoulder retain their Applied Section review strips.  Side Slope is
    a compatibility entry point that now routes to its accepted result surface.
    """

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    kind_text = str(kind or "").strip()
    if doc is None or not kind_text:
        raise RuntimeError("Subassembly kind review target was not found.")
    if kind_text == "side_slope":
        set_all_corridor_build_preview_visibility(doc, False, include_issue_markers=True)
        _remove_preview_object(doc, "ReviewIssueSubassemblyKind_side_slope")
        obj = _focus_corridor_side_slope_result_preview(doc)
        if obj is None:
            raise RuntimeError(_side_slope_review_missing_result_message(doc))
        return obj
    _set_subassembly_kind_review_previews_visibility(doc, False)
    if kind_text in {"lane", "shoulder"}:
        obj = _create_subassembly_kind_review_highlight(document=doc, kind=kind_text, visible=True)
    else:
        obj = _subassembly_kind_review_object(doc, kind_text)
        if obj is None:
            obj = _create_subassembly_kind_review_highlight(document=doc, kind=kind_text, visible=True)
    if obj is None:
        raise RuntimeError(f"No evaluated Subassembly geometry was found for kind: {kind_text}")
    _set_object_visibility(obj, True)
    _select_and_fit_object(obj)
    return obj


def _focus_corridor_side_slope_result_preview(document):
    """Show accepted Side Slope results, including Cross/T approach roads.

    The Intersection Slope Face Surface owns the control area. The ordinary
    Slope Face Surface owns the Primary/Secondary approach-road portions that
    are clipped around it. Both must be visible together for an at-grade
    intersection review, while the Intersection result remains the primary
    return value for compatibility with existing callers.
    """

    intersection = _corridor_build_preview_object(document, "intersection_slope")
    daylight = _corridor_build_preview_object(document, "daylight")
    intersection_ready = _corridor_side_slope_result_preview_is_usable(
        document,
        "intersection_slope",
        intersection,
    )
    daylight_ready = _corridor_side_slope_result_preview_is_usable(
        document,
        "daylight",
        daylight,
    )
    if intersection_ready:
        visible = [intersection]
        if daylight_ready:
            visible.append(daylight)
        for obj in visible:
            _set_object_visibility(obj, True)
        _select_and_fit_objects(visible)
        return intersection
    if daylight_ready:
        _set_object_visibility(daylight, True)
        _select_and_fit_object(daylight)
        return daylight
    return None


def _corridor_side_slope_result_preview_is_usable(document, role: str, obj) -> bool:
    """Return whether a Side Slope preview is an accepted, displayable result."""

    if obj is None:
        return False
    if int(getattr(obj, "VertexCount", 0) or 0) <= 0:
        return False
    if int(getattr(obj, "TriangleCount", 0) or 0) <= 0:
        return False
    diagnostic = _corridor_build_preview_diagnostic_object(document, role)
    if diagnostic is None:
        return True
    status = _normalize_corridor_build_review_status(
        getattr(diagnostic, "PreviewStatus", "") or "ready",
        default="ready",
    )
    return status not in {"error", "missing", "empty"}


def _side_slope_review_missing_result_message(document) -> str:
    """Return an actionable message without fabricating Side Slope geometry."""

    details = []
    for role in ("intersection_slope", "daylight"):
        diagnostic = _corridor_build_preview_diagnostic_object(document, role)
        if diagnostic is None:
            continue
        status = _normalize_corridor_build_review_status(
            getattr(diagnostic, "PreviewStatus", "") or "missing"
        )
        notes = str(getattr(diagnostic, "PreviewDiagnostic", "") or "")
        details.append(f"{_corridor_build_review_title(role)} status={status}{': ' + notes if notes else ''}")
    detail_text = " ".join(details)
    message = "No accepted Side Slope result is available. Build Parametric after the required daylight or Intersection slope result is available."
    return f"{message} {detail_text}".strip()


def create_corridor_subassembly_kind_review_previews(*, document=None, project=None) -> list[object]:
    """Create reusable Build Parametric review objects grouped by evaluated Subassembly kind."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return []
    for obj in _subassembly_kind_review_objects(doc):
        try:
            doc.removeObject(str(getattr(obj, "Name", "") or ""))
        except Exception:
            pass
    created: list[object] = []
    for row in corridor_subassembly_kind_guided_review_rows(doc):
        kind = str(row.get("kind", "") or "").strip()
        if not kind:
            continue
        obj = _create_subassembly_kind_review_highlight(
            document=doc,
            project=project,
            kind=kind,
            visible=False,
        )
        if obj is not None:
            created.append(obj)
    return created


def _subassembly_kind_review_object(document, kind: str):
    if document is None:
        return None
    object_name = f"ReviewIssueSubassemblyKind_{_safe_output_object_suffix(str(kind or '').strip())}"
    try:
        return document.getObject(object_name)
    except Exception:
        return None


def _subassembly_kind_review_objects(document) -> list[object]:
    if document is None:
        return []
    objects: list[object] = []
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if not name.startswith("ReviewIssueSubassemblyKind_"):
            continue
        objects.append(obj)
    return objects


def _set_subassembly_kind_review_previews_visibility(document, visible: bool) -> int:
    changed = 0
    for obj in _subassembly_kind_review_objects(document):
        _set_object_visibility(obj, bool(visible))
        changed += 1
    return changed


def _create_subassembly_kind_review_highlight(*, document=None, project=None, kind: str = "", visible: bool = True):
    if document is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    if applied is None:
        return None
    kind_text = str(kind or "").strip()
    if not kind_text:
        return None
    object_name = f"ReviewIssueSubassemblyKind_{_safe_output_object_suffix(kind_text)}"
    _remove_preview_object(document, object_name)
    if kind_text in {"lane", "shoulder"}:
        return _create_subassembly_surface_strip_review_highlight(
            document=document,
            project=project,
            kind=kind_text,
            object_name=object_name,
            visible=visible,
        )
    shapes: list[object] = []
    sections = _station_ordered_applied_sections(applied)
    section_count = 0
    link_count = 0
    shape_count = 0
    surface_patch_count = 0
    skipped_link_count = 0
    surface_roles: list[str] = []
    preset_refs: list[str] = []
    preset_statuses: list[str] = []
    source_instance_refs: list[str] = []
    previous_link_segments_by_scope: dict[str, dict[str, tuple[object, object]]] = {}

    def make_vector(point, *, z_offset: float = 0.0):
        return AppModule.Vector(
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0) + float(z_offset),
        )

    def append_triangle_face(a, b, c) -> bool:
        if _same_centerline_point(a, b) or _same_centerline_point(b, c) or _same_centerline_point(c, a):
            return False
        try:
            shapes.append(Part.Face(Part.makePolygon([a, b, c, a])))
            return True
        except Exception:
            return False

    for section in sections:
        continuity_scope = _subassembly_kind_review_continuity_scope(section)
        subassembly_by_id = {
            str(getattr(row, "subassembly_id", "") or "").strip(): row
            for row in list(getattr(section, "subassembly_rows", []) or [])
            if str(getattr(row, "subassembly_id", "") or "").strip()
        }
        target_refs = {
            subassembly_id
            for subassembly_id, row in subassembly_by_id.items()
            if str(getattr(row, "kind", "") or "").strip() == kind_text
        }
        if not target_refs:
            previous_link_segments_by_scope[continuity_scope] = {}
            continue
        previous_link_segments = previous_link_segments_by_scope.setdefault(continuity_scope, {})
        for subassembly_ref in sorted(target_refs):
            source_row = subassembly_by_id.get(subassembly_ref)
            if source_row is None:
                continue
            preset_ref = str(getattr(source_row, "preset_ref", "") or "").strip()
            preset_status = str(getattr(source_row, "preset_status", "") or "").strip()
            source_instance_ref = str(getattr(source_row, "source_instance_ref", "") or "").strip()
            if preset_ref:
                preset_refs.append(preset_ref)
            if preset_status:
                preset_statuses.append(preset_status)
            elif preset_ref:
                preset_statuses.append("linked")
            else:
                preset_statuses.append("snapshot")
            if source_instance_ref:
                source_instance_refs.append(source_instance_ref)
        points = {
            str(getattr(point, "point_id", "") or "").strip(): point
            for point in list(getattr(section, "subassembly_point_rows", []) or [])
            if str(getattr(point, "point_id", "") or "").strip()
        }
        section_has_geometry = False
        current_link_segments: dict[str, tuple[object, object]] = {}
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            subassembly_ref = str(getattr(link, "subassembly_ref", "") or "").strip()
            if subassembly_ref not in target_refs:
                continue
            start_ref = str(getattr(link, "start_point_ref", "") or "").strip()
            end_ref = str(getattr(link, "end_point_ref", "") or "").strip()
            start = points.get(start_ref)
            end = points.get(end_ref)
            if start is None or end is None:
                continue
            try:
                start_vector = make_vector(start, z_offset=0.08)
                end_vector = make_vector(end, z_offset=0.08)
                shapes.append(Part.makeLine(start_vector, end_vector))
                link_key = str(getattr(link, "link_id", "") or "").strip()
                if not link_key:
                    role_text = str(getattr(link, "surface_role", "") or "").strip()
                    link_key = f"{subassembly_ref}:{start_ref}:{end_ref}:{role_text}"
                current_link_segments[link_key] = (start_vector, end_vector)
                previous_segment = previous_link_segments.get(link_key)
                if previous_segment is not None:
                    previous_start, previous_end = previous_segment
                    if append_triangle_face(previous_start, previous_end, end_vector):
                        surface_patch_count += 1
                    if append_triangle_face(previous_start, end_vector, start_vector):
                        surface_patch_count += 1
                section_has_geometry = True
                link_count += 1
                role = str(getattr(link, "surface_role", "") or "").strip()
                if role:
                    surface_roles.append(role)
            except Exception:
                skipped_link_count += 1
        for shape_row in list(getattr(section, "subassembly_shape_rows", []) or []):
            if str(getattr(shape_row, "subassembly_ref", "") or "").strip() not in target_refs:
                continue
            vectors = []
            for point_ref in list(getattr(shape_row, "point_refs", []) or []):
                point = points.get(str(point_ref or "").strip())
                if point is None:
                    continue
                try:
                    vectors.append(
                        AppModule.Vector(
                            float(getattr(point, "x", 0.0) or 0.0),
                            float(getattr(point, "y", 0.0) or 0.0),
                            float(getattr(point, "z", 0.0) or 0.0) + 0.1,
                        )
                    )
                except Exception:
                    pass
            if len(vectors) < 2:
                continue
            try:
                if len(vectors) >= 3 and not _same_centerline_point(vectors[0], vectors[-1]):
                    vectors.append(vectors[0])
                shapes.append(Part.makePolygon(vectors))
                section_has_geometry = True
                shape_count += 1
            except Exception:
                skipped_link_count += 1
        if section_has_geometry:
            section_count += 1
        previous_link_segments_by_scope[continuity_scope] = current_link_segments
    if not shapes:
        return None
    try:
        obj = document.addObject("Part::Feature", object_name)
    except Exception:
        return None
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = f"Subassembly Highlight - {_subassembly_kind_display_name(kind_text)}"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_subassembly_kind_review_highlight", error=error)
    _set_preview_property(obj, "CRRecordKind", "v1_review_issue")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "subassembly_kind")
    _set_preview_property(obj, "SubassemblyKind", kind_text)
    _set_preview_string_list_property(obj, "PresetRefs", _unique_text_values(preset_refs))
    _set_preview_string_list_property(obj, "PresetStatuses", _unique_text_values(preset_statuses))
    _set_preview_string_list_property(obj, "SourceInstanceRefs", _unique_text_values(source_instance_refs))
    _set_preview_float_property(obj, "SectionCount", float(section_count))
    _set_preview_float_property(obj, "LinkCount", float(link_count))
    _set_preview_float_property(obj, "ShapeCount", float(shape_count))
    _set_preview_float_property(obj, "SurfacePatchCount", float(surface_patch_count))
    _set_preview_float_property(obj, "SkippedLinkCount", float(skipped_link_count))
    _set_preview_float_property(obj, "ContinuityScopeCount", float(len(previous_link_segments_by_scope)))
    _set_preview_string_list_property(obj, "SurfaceRoles", _unique_text_values(surface_roles))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            color = _subassembly_kind_review_color(kind_text)
            vobj.ShapeColor = color
            vobj.LineColor = color
            vobj.PointColor = color
            vobj.Transparency = 45
            vobj.LineWidth = 6.0
            vobj.PointSize = 8.0
            vobj.Visibility = bool(visible)
    except Exception:
        pass
    try:
        route_object_to_project_tree(project or find_project(document), obj)
    except Exception:
        pass
    return obj


def _create_subassembly_surface_strip_review_highlight(
    *,
    document=None,
    project=None,
    kind: str = "",
    object_name: str,
    visible: bool = True,
):
    """Create Lane/Shoulder review surface strips from evaluated Applied Section links."""

    if document is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    sections = _station_ordered_applied_sections(applied) if applied is not None else []
    kind_text = str(kind or "").strip()
    if not sections or not kind_text:
        return None
    shapes: list[object] = []
    section_count = 0
    link_count = 0
    surface_patch_count = 0
    surface_roles: list[str] = []
    preset_refs: list[str] = []
    preset_statuses: list[str] = []
    source_instance_refs: list[str] = []
    continuity_scopes: set[str] = set()
    skipped_intersection_section_count = 0
    skipped_roundabout_section_refs: set[str] = set()
    skipped_roundabout_segment_count = 0
    skipped_roundabout_strip_triangle_count = 0
    previous_link_segments_by_scope: dict[str, dict[str, tuple[object, object]]] = {}
    roundabout_clip_summary: dict[str, object] = {}
    roundabout_clip_polygons: list[list[tuple[float, float]]] = []
    if kind_text in {"lane", "shoulder"}:
        roundabout_clip_summary, roundabout_clip_polygons = _roundabout_kernel_clip_polygons(document)

    def vector_xy(vector) -> tuple[float, float]:
        return (
            float(getattr(vector, "x", 0.0) or 0.0),
            float(getattr(vector, "y", 0.0) or 0.0),
        )

    # The clip polygon is the intersection kernel's boundary, whose mouth edges are the mouth
    # sections themselves: a strip on a mouth touches the boundary without entering it. So a
    # segment or triangle is clipped when its midpoint / centroid lies strictly inside, the same
    # rule as the corridor's station-span clip and the ownership intrusion check.
    def segment_intersects_roundabout_clip(start_vector, end_vector) -> bool:
        if not roundabout_clip_polygons:
            return False
        start_xy = vector_xy(start_vector)
        end_xy = vector_xy(end_vector)
        midpoint = ((start_xy[0] + end_xy[0]) / 2.0, (start_xy[1] + end_xy[1]) / 2.0)
        return any(xy_point_in_polygon_strict(midpoint, polygon) for polygon in roundabout_clip_polygons)

    def triangle_intersects_roundabout_clip(a, b, c) -> bool:
        if not roundabout_clip_polygons:
            return False
        triangle = [vector_xy(a), vector_xy(b), vector_xy(c)]
        centroid = (sum(p[0] for p in triangle) / 3.0, sum(p[1] for p in triangle) / 3.0)
        return any(xy_point_in_polygon_strict(centroid, polygon) for polygon in roundabout_clip_polygons)

    def append_triangle_face(a, b, c) -> bool:
        nonlocal skipped_roundabout_strip_triangle_count
        if _same_centerline_point(a, b) or _same_centerline_point(b, c) or _same_centerline_point(c, a):
            return False
        if triangle_intersects_roundabout_clip(a, b, c):
            skipped_roundabout_strip_triangle_count += 1
            return False
        try:
            shapes.append(Part.Face(Part.makePolygon([a, b, c, a])))
            return True
        except Exception:
            return False

    for section in sections:
        continuity_scope = _subassembly_kind_review_continuity_scope(section)
        continuity_scopes.add(continuity_scope)
        if not _subassembly_kind_review_section_belongs_to_design_surface(section):
            previous_link_segments_by_scope[continuity_scope] = {}
            skipped_intersection_section_count += 1
            continue
        subassembly_by_id = {
            str(getattr(row, "subassembly_id", "") or "").strip(): row
            for row in list(getattr(section, "subassembly_rows", []) or [])
            if str(getattr(row, "subassembly_id", "") or "").strip()
        }
        target_refs = {
            subassembly_id
            for subassembly_id, row in subassembly_by_id.items()
            if str(getattr(row, "kind", "") or "").strip() == kind_text
        }
        if not target_refs:
            previous_link_segments_by_scope[continuity_scope] = {}
            continue
        previous_link_segments = previous_link_segments_by_scope.setdefault(continuity_scope, {})
        for subassembly_ref in sorted(target_refs):
            source_row = subassembly_by_id.get(subassembly_ref)
            if source_row is None:
                continue
            preset_ref = str(getattr(source_row, "preset_ref", "") or "").strip()
            preset_status = str(getattr(source_row, "preset_status", "") or "").strip()
            source_instance_ref = str(getattr(source_row, "source_instance_ref", "") or "").strip()
            if preset_ref:
                preset_refs.append(preset_ref)
            if preset_status:
                preset_statuses.append(preset_status)
            elif preset_ref:
                preset_statuses.append("linked")
            else:
                preset_statuses.append("snapshot")
            if source_instance_ref:
                source_instance_refs.append(source_instance_ref)
        points = {
            str(getattr(point, "point_id", "") or "").strip(): point
            for point in list(getattr(section, "subassembly_point_rows", []) or [])
            if str(getattr(point, "point_id", "") or "").strip()
        }
        section_has_geometry = False
        current_link_segments: dict[str, tuple[object, object]] = {}
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            subassembly_ref = str(getattr(link, "subassembly_ref", "") or "").strip()
            if subassembly_ref not in target_refs:
                continue
            start = points.get(str(getattr(link, "start_point_ref", "") or "").strip())
            end = points.get(str(getattr(link, "end_point_ref", "") or "").strip())
            if start is None or end is None:
                continue
            try:
                start_vector = AppModule.Vector(
                    float(getattr(start, "x", 0.0) or 0.0),
                    float(getattr(start, "y", 0.0) or 0.0),
                    float(getattr(start, "z", 0.0) or 0.0) + 0.08,
                )
                end_vector = AppModule.Vector(
                    float(getattr(end, "x", 0.0) or 0.0),
                    float(getattr(end, "y", 0.0) or 0.0),
                    float(getattr(end, "z", 0.0) or 0.0) + 0.08,
                )
                if _same_centerline_point(start_vector, end_vector):
                    continue
                link_key = str(getattr(link, "link_id", "") or "").strip()
                if not link_key:
                    role_text = str(getattr(link, "surface_role", "") or "").strip()
                    link_key = f"{subassembly_ref}:{getattr(link, 'start_point_ref', '')}:{getattr(link, 'end_point_ref', '')}:{role_text}"
                if segment_intersects_roundabout_clip(start_vector, end_vector):
                    skipped_roundabout_segment_count += 1
                    skipped_roundabout_section_refs.add(str(getattr(section, "section_id", "") or getattr(section, "station", "") or "section"))
                    previous_link_segments.pop(link_key, None)
                    continue
                current_link_segments[link_key] = (start_vector, end_vector)
                previous_segment = previous_link_segments.get(link_key)
                if previous_segment is not None:
                    previous_start, previous_end = previous_segment
                    triangle_skip_count = skipped_roundabout_strip_triangle_count
                    if append_triangle_face(previous_start, previous_end, end_vector):
                        surface_patch_count += 1
                    if append_triangle_face(previous_start, end_vector, start_vector):
                        surface_patch_count += 1
                    if skipped_roundabout_strip_triangle_count > triangle_skip_count:
                        skipped_roundabout_section_refs.add(
                            str(getattr(section, "section_id", "") or getattr(section, "station", "") or "section")
                        )
                section_has_geometry = True
                link_count += 1
                role = str(getattr(link, "surface_role", "") or "").strip()
                if role:
                    surface_roles.append(role)
            except Exception:
                continue
        if section_has_geometry:
            section_count += 1
        previous_link_segments_by_scope[continuity_scope] = current_link_segments
    if not shapes:
        return None
    try:
        obj = document.addObject("Part::Feature", object_name)
    except Exception:
        return None
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = f"Applied Section Highlight - {_subassembly_kind_display_name(kind_text)}"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_subassembly_surface_strip_review_highlight", error=error)
    _set_preview_property(obj, "CRRecordKind", "v1_review_issue")
    _set_preview_property(obj, "V1ObjectType", "ReviewIssue")
    _set_preview_property(obj, "IssueKind", "subassembly_kind")
    _set_preview_property(obj, "SubassemblyKind", kind_text)
    _set_preview_property(obj, "SourceMode", "applied_section_link_rows")
    _set_preview_property(obj, "DisplayMode", "section_surface_strips")
    _set_preview_string_list_property(obj, "PresetRefs", _unique_text_values(preset_refs))
    _set_preview_string_list_property(obj, "PresetStatuses", _unique_text_values(preset_statuses))
    _set_preview_string_list_property(obj, "SourceInstanceRefs", _unique_text_values(source_instance_refs))
    _set_preview_float_property(obj, "SectionCount", float(section_count))
    _set_preview_float_property(obj, "LinkCount", float(link_count))
    _set_preview_float_property(obj, "ShapeCount", 0.0)
    _set_preview_float_property(obj, "SurfacePatchCount", float(surface_patch_count))
    _set_preview_float_property(obj, "ContinuityScopeCount", float(len(continuity_scopes)))
    _set_preview_float_property(obj, "SkippedIntersectionSectionCount", float(skipped_intersection_section_count))
    reported_boundary_role = str(roundabout_clip_summary.get("boundary_role", "") or "")
    # the station-span clip removes the corridor inside the kernel's boundary, the polygon reported
    actual_boundary_roles = reported_boundary_role
    _set_preview_property(obj, "RoundaboutClipBoundaryRole", reported_boundary_role)
    _set_preview_property(obj, "RoundaboutReportedBoundaryRole", reported_boundary_role)
    _set_preview_property(obj, "RoundaboutActualClipBoundaryRole", actual_boundary_roles)
    _set_preview_property(
        obj,
        "RoundaboutActualClipBoundaryRoles",
        actual_boundary_roles,
    )
    _set_preview_property(obj, "RoundaboutReviewClipMode", "intersection_kernel_boundary" if reported_boundary_role else "")
    _set_preview_property(obj, "RoundaboutClipBoundaryStatus", str(roundabout_clip_summary.get("status", "") or ""))
    _set_preview_property(
        obj,
        "RoundaboutClipFallbackReason",
        "" if roundabout_clip_polygons else ("roundabout_clip_boundary_unavailable" if roundabout_clip_summary else ""),
    )
    _set_preview_float_property(obj, "RoundaboutClipBoundaryLoopCount", float(roundabout_clip_summary.get("loop_count", 0) or 0))
    _set_preview_float_property(obj, "SkippedRoundaboutSectionCount", float(len(skipped_roundabout_section_refs)))
    _set_preview_float_property(obj, "SkippedRoundaboutSegmentCount", float(skipped_roundabout_segment_count))
    _set_preview_float_property(obj, "SkippedRoundaboutStripTriangleCount", float(skipped_roundabout_strip_triangle_count))
    _set_preview_string_list_property(obj, "SurfaceRoles", _unique_text_values(surface_roles))
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            color = _subassembly_kind_review_color(kind_text)
            vobj.ShapeColor = color
            vobj.LineColor = color
            vobj.PointColor = color
            vobj.Transparency = 45
            vobj.LineWidth = 6.0
            vobj.PointSize = 8.0
            vobj.Visibility = bool(visible)
    except Exception:
        pass
    try:
        route_object_to_project_tree(project or find_project(document), obj)
    except Exception:
        pass
    return obj


def _subassembly_kind_review_continuity_scope(section) -> str:
    """Return the source scope where adjacent Subassembly review links may be stitched."""

    alignment_id = str(getattr(section, "alignment_id", "") or "").strip() or "(unassigned-alignment)"
    assembly_id = str(getattr(section, "assembly_id", "") or "").strip() or "(unassigned-assembly)"
    template_id = str(getattr(section, "template_id", "") or "").strip() or "(unassigned-template)"
    return f"{alignment_id}|{assembly_id}|{template_id}"


def _subassembly_kind_review_section_belongs_to_design_surface(section) -> bool:
    """Return whether Lane/Shoulder review strips should use this ordinary design section."""

    if section is None:
        return False
    intersection_fields = (
        "active_intersection_id",
        "active_intersection_control_area_id",
        "active_intersection_leg_id",
        "active_intersection_grading_policy_ref",
    )
    for field_name in intersection_fields:
        if str(getattr(section, field_name, "") or "").strip():
            return False
    if [str(ref or "").strip() for ref in list(getattr(section, "active_intersection_control_region_refs", []) or []) if str(ref or "").strip()]:
        return False
    region_id = str(getattr(section, "region_id", "") or "").strip().lower()
    if "intersection" in region_id:
        return False
    return True


def _subassembly_kind_review_color(kind: str) -> tuple[float, float, float]:
    kind_text = str(kind or "").strip().lower()
    if kind_text == "lane":
        return (0.15, 0.65, 1.0)
    if kind_text == "shoulder":
        return (0.35, 1.0, 0.35)
    if kind_text in {"ditch", "lined_ditch"}:
        return (0.0, 0.95, 0.95)
    if kind_text == "gutter":
        return (0.75, 0.45, 1.0)
    if kind_text == "curb":
        return (1.0, 0.55, 0.0)
    if kind_text == "side_slope":
        return (1.0, 0.85, 0.0)
    return (1.0, 0.9, 0.0)


def show_corridor_slope_face_issue_marker(document=None, row_index: int = 0):
    """Select and fit the 3D marker object related to one slope-face issue row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    rows = corridor_slope_face_issue_rows(doc)
    if row_index < 0 or row_index >= len(rows):
        raise IndexError("Slope Face issue row index is out of range.")
    row = rows[row_index]
    if str(row.get("review_status", "") or "") not in {"warning", "error"}:
        raise RuntimeError("Side Slope diagnostic marker is available only for warning or error results.")
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


def corridor_build_preview_visibility_note(document=None, role: str = "") -> str:
    """Return a user-facing note for a Build Parametric visibility role."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    role_text = str(role or "").strip()
    obj = _corridor_build_preview_object(doc, role_text)
    title = _corridor_build_review_title(role_text)
    if obj is not None:
        label = str(getattr(obj, "Label", getattr(obj, "Name", "")) or title or role_text)
        return f"Show or hide {label} in the 3D View."
    diagnostic = _corridor_build_preview_diagnostic_object(doc, role_text)
    status = _normalize_corridor_build_review_status(getattr(diagnostic, "PreviewStatus", "") or "missing")
    notes = str(getattr(diagnostic, "PreviewDiagnostic", "") or "")
    if not notes and role_text == "intersection_slope":
        notes = _intersection_slope_face_surface_absent_note(doc)
    if not notes:
        notes = "Preview object is absent. Rebuild Build Parametric after the required source/result contract is available."
    return f"{title or role_text} is unavailable; status={status}. {notes}"


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
    for obj in _subassembly_kind_review_objects(doc):
        _set_object_visibility(obj, bool(visible))
        changed += 1
    if include_issue_markers:
        for obj in _corridor_build_issue_marker_objects(doc):
            _set_object_visibility(obj, bool(visible))
            changed += 1
    return changed


def corridor_build_visibility_groups() -> list[dict[str, object]]:
    """Return user-facing Build Parametric visibility groups."""

    return [
        {
            "group_id": group_id,
            "title": title,
            "roles": tuple(roles),
            "object_names": tuple(object_names),
        }
        for group_id, title, roles, object_names in CORRIDOR_BUILD_VISIBILITY_GROUPS
    ]


def set_corridor_build_visibility_group(document=None, group_id: str = "", visible: bool = True) -> int:
    """Set grouped visibility for Build Parametric review layers."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return 0
    group = _corridor_build_visibility_group(str(group_id or ""))
    if group is None:
        return 0
    changed = 0
    for role in tuple(group[2] or ()):
        if set_corridor_build_preview_visibility(doc, str(role), bool(visible)) is not None:
            changed += 1
    for name in tuple(group[3] or ()):
        obj = doc.getObject(str(name or ""))
        if obj is not None:
            _set_object_visibility(obj, bool(visible))
            changed += 1
    if str(group[0]) == "diagnostics":
        for obj in _corridor_build_issue_marker_objects(doc):
            _set_object_visibility(obj, bool(visible))
            changed += 1
        for obj in _corridor_build_daylight_marker_objects(doc):
            _set_object_visibility(obj, bool(visible))
            changed += 1
    return changed


def corridor_build_visibility_group_visible(document=None, group_id: str = "") -> bool:
    """Return whether any object in one Build Parametric visibility group is visible."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return False
    group = _corridor_build_visibility_group(str(group_id or ""))
    if group is None:
        return False
    for role in tuple(group[2] or ()):
        obj = _corridor_build_preview_object(doc, str(role))
        if obj is not None and _object_visibility(obj):
            return True
    for name in tuple(group[3] or ()):
        obj = doc.getObject(str(name or ""))
        if obj is not None and _object_visibility(obj):
            return True
    if str(group[0]) == "diagnostics":
        return any(_object_visibility(obj) for obj in [*_corridor_build_issue_marker_objects(doc), *_corridor_build_daylight_marker_objects(doc)])
    return False


def _corridor_build_visibility_group(group_id: str):
    target = str(group_id or "").strip()
    for group in CORRIDOR_BUILD_VISIBILITY_GROUPS:
        if str(group[0]) == target:
            return group
    return None


def set_corridor_guided_review_step_visibility(document=None, step_id: str = "", visible: bool = True) -> int:
    """Set visibility for objects represented by one Guided Review row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return 0
    step_id_text = str(step_id or "").strip()
    if not step_id_text:
        return 0
    changed = 0
    if step_id_text.startswith("subassembly_kind:"):
        kind = step_id_text.split(":", 1)[1]
        obj = _subassembly_kind_review_object(doc, kind)
        if obj is None and visible:
            obj = _create_subassembly_kind_review_highlight(document=doc, kind=kind, visible=True)
        if obj is not None:
            _set_object_visibility(obj, bool(visible))
            changed += 1
        return changed
    if step_id_text == "supplemental_frames":
        obj = _corridor_supplemental_frame_marker_object(doc)
        if obj is None and visible:
            obj = create_or_update_corridor_supplemental_frame_markers(document=doc, visible=True)
        if obj is not None:
            _set_object_visibility(obj, bool(visible))
            changed += 1
        return changed
    step = _corridor_build_guided_review_step(step_id_text)
    if step is not None:
        for role in list(step[2] or []):
            if set_corridor_build_preview_visibility(doc, role, bool(visible)) is not None:
                changed += 1
    if step_id_text == "slope_issues":
        for marker in _corridor_build_issue_marker_objects(doc):
            _set_object_visibility(marker, bool(visible))
            changed += 1
    elif step_id_text == "drainage_flow":
        obj = doc.getObject("ReviewIssueDrainageFlowRoutes")
        if obj is not None:
            _set_object_visibility(obj, bool(visible))
            changed += 1
    return changed


def corridor_guided_review_step_visibility(document=None, step_id: str = "") -> bool:
    """Return whether any object represented by one Guided Review row is visible."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return False
    step_id_text = str(step_id or "").strip()
    if step_id_text.startswith("subassembly_kind:"):
        obj = _subassembly_kind_review_object(doc, step_id_text.split(":", 1)[1])
        return _object_visibility(obj) if obj is not None else False
    if step_id_text == "supplemental_frames":
        obj = _corridor_supplemental_frame_marker_object(doc)
        return _object_visibility(obj) if obj is not None else False
    step = _corridor_build_guided_review_step(step_id_text)
    if step is not None:
        for role in list(step[2] or []):
            obj = _corridor_build_preview_object(doc, role)
            if obj is not None and _object_visibility(obj):
                return True
    if step_id_text == "slope_issues":
        return any(_object_visibility(marker) for marker in _corridor_build_issue_marker_objects(doc))
    if step_id_text == "drainage_flow":
        obj = doc.getObject("ReviewIssueDrainageFlowRoutes")
        return _object_visibility(obj) if obj is not None else False
    return False


def corridor_guided_review_step_available(document=None, step_id: str = "") -> bool:
    """Return whether one Guided Review row has a built object that can be toggled."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return False
    step_id_text = str(step_id or "").strip()
    if step_id_text.startswith("subassembly_kind:"):
        kind = step_id_text.split(":", 1)[1]
        if _subassembly_kind_review_object(doc, kind) is not None:
            return True
        return any(
            str(row.get("step_id", "") or "") == step_id_text
            for row in corridor_subassembly_kind_guided_review_rows(doc)
        )
    if step_id_text == "supplemental_frames":
        return _corridor_supplemental_frame_marker_object(doc) is not None or find_v1_applied_section_set(doc) is not None
    step = _corridor_build_guided_review_step(step_id_text)
    if step is not None:
        for role in list(step[2] or []):
            if _corridor_build_preview_object(doc, role) is not None:
                return True
    if step_id_text == "slope_issues":
        return bool(_corridor_build_issue_marker_objects(doc))
    if step_id_text == "drainage_flow":
        return doc.getObject("ReviewIssueDrainageFlowRoutes") is not None
    return False


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
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
):
    """Create or update a 3D centerline preview from the shared Centerline3DResult."""

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

    shape, curve_kind, points, stations, source_mode, centerline_result_id = _corridor_centerline_preview_shape(
        doc,
        AppModule,
        Part,
    )
    if shape is None or len(points) < 2:
        return None
    obj = doc.getObject("V1CorridorCenterline3DPreview")
    if obj is None:
        obj = doc.addObject("Part::Feature", "V1CorridorCenterline3DPreview")
    try:
        obj.Shape = shape
        obj.Label = "Corridor 3D Centerline"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_corridor_centerline_3d_preview", error=error)
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
    _set_corridor_consumer_disclosure_properties(
        obj,
        document=doc,
        applied_section_set=applied_section_set,
        corridor_model=corridor_model,
        centerline_source_mode=source_mode,
        centerline_result_id=centerline_result_id,
        supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
        supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
        supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
    )
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
        route_object_to_project_tree(project or find_project(doc), obj)
    except Exception:
        pass
    return obj


def _set_corridor_consumer_disclosure_properties(
    obj,
    *,
    document=None,
    applied_section_set=None,
    corridor_model=None,
    centerline_source_mode: str = "",
    centerline_result_id: str = "",
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
) -> None:
    """Expose ordinary-road result contracts consumed by Build Corridor previews."""

    applied = applied_section_set
    if applied is None:
        return
    supplemental_summary = _applied_section_supplemental_consumption_summary(applied)
    source_section_count = int(supplemental_summary.get("source_section_count", 0) or 0)
    supplemental_section_count = int(supplemental_summary.get("supplemental_section_count", 0) or 0)
    total_section_count = int(supplemental_summary.get("total_section_count", 0) or 0)
    kind_counts = dict(supplemental_summary.get("kind_counts", {}) or {})
    result_contract_summary = _applied_section_result_contract_consumption_summary(applied)
    link_role_counts = dict(result_contract_summary.get("link_surface_role_counts", {}) or {})
    point_role_counts = dict(result_contract_summary.get("point_role_counts", {}) or {})
    shape_family_counts = dict(result_contract_summary.get("shape_family_counts", {}) or {})
    consumed_region_refs = list(result_contract_summary.get("region_refs", []) or [])
    consumed_intersection_control_region_refs = list(result_contract_summary.get("intersection_control_region_refs", []) or [])
    compatibility_fallback = False
    result_contract_fallback = bool(total_section_count > 0 and int(result_contract_summary.get("subassembly_link_count", 0) or 0) <= 0)
    result_contract_reason = (
        "No consumed Subassembly link rows were available; Build Corridor may rely on legacy width/point result fields."
        if result_contract_fallback
        else "Consumed Applied Section Subassembly link rows are available."
    )
    sampling_summary = {}
    try:
        sampling_summary = supplemental_sampling_summary(
            list(getattr(applied, "sections", []) or []),
            max_spacing=float(supplemental_sampling_max_spacing or SUPPLEMENTAL_SAMPLING_MAX_SPACING),
            tangent_delta_threshold_deg=float(supplemental_sampling_tangent_delta_deg or SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG),
            chord_deviation_threshold=float(supplemental_sampling_chord_deviation or SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD),
            frame_resolver=_corridor_supplemental_frame_resolver(document),
        )
    except Exception:
        sampling_summary = {}
    sampling_source_modes = dict(sampling_summary.get("source_mode_counts", {}) or {})
    sampling_source_mode_rows = [f"{key}={value}" for key, value in sorted(sampling_source_modes.items())]
    centerline_fallback_active = str(centerline_source_mode or "") not in {"", "centerline3d_source_geometry"}
    supplemental_policy = "applied_sections_only"
    supplemental_reason = "Applied Sections contain supplemental rows or no curved-span densification is required."
    if supplemental_section_count <= 0 and int(sampling_summary.get("supplemental_frame_count", 0) or 0) > 0:
        supplemental_policy = "rebuild_applied_sections_required"
        supplemental_reason = (
            "Build Corridor no longer creates hidden supplemental frames; "
            "rebuild Applied Sections so supplemental rows become explicit result data."
        )
    _set_preview_property(obj, "ConsumedAppliedSectionSetId", str(getattr(applied, "applied_section_set_id", "") or ""))
    _set_preview_property(obj, "ConsumedCenterline3DResultId", str(centerline_result_id or ""))
    _set_preview_property(obj, "ConsumedCenterlineSourceMode", str(centerline_source_mode or ""))
    _set_preview_integer_property(obj, "ConsumedSourceSectionCount", source_section_count)
    _set_preview_integer_property(obj, "ConsumedSupplementalSectionCount", supplemental_section_count)
    _set_preview_integer_property(obj, "ConsumedTotalSectionCount", total_section_count)
    _set_preview_string_list_property(obj, "ConsumedSectionKindCounts", [f"{key}={value}" for key, value in sorted(kind_counts.items())])
    _set_preview_integer_property(obj, "ConsumedSubassemblyLinkCount", int(result_contract_summary.get("subassembly_link_count", 0) or 0))
    _set_preview_integer_property(obj, "ConsumedSubassemblyPointCount", int(result_contract_summary.get("subassembly_point_count", 0) or 0))
    _set_preview_integer_property(obj, "ConsumedSubassemblyShapeCount", int(result_contract_summary.get("subassembly_shape_count", 0) or 0))
    _set_preview_string_list_property(obj, "ConsumedSurfaceRoleCounts", [f"{key}={value}" for key, value in sorted(link_role_counts.items())])
    _set_preview_string_list_property(obj, "ConsumedPointRoleCounts", [f"{key}={value}" for key, value in sorted(point_role_counts.items())])
    _set_preview_string_list_property(obj, "ConsumedShapeFamilyCounts", [f"{key}={value}" for key, value in sorted(shape_family_counts.items())])
    _set_preview_string_list_property(obj, "ConsumedRegionRefs", consumed_region_refs)
    _set_preview_integer_property(obj, "ConsumedRegionCount", len(consumed_region_refs))
    _set_preview_string_list_property(obj, "ConsumedIntersectionControlRegionRefs", consumed_intersection_control_region_refs)
    _set_preview_integer_property(obj, "ConsumedIntersectionControlRegionCount", len(consumed_intersection_control_region_refs))
    _set_preview_integer_property(obj, "ResultContractCompatibilityFallbackActive", int(bool(result_contract_fallback)))
    _set_preview_property(obj, "ResultContractCompatibilityReason", result_contract_reason)
    _set_preview_integer_property(obj, "CenterlineConsumerFallbackActive", int(bool(centerline_fallback_active)))
    _set_preview_integer_property(obj, "SupplementalCompatibilityFallbackActive", int(bool(compatibility_fallback)))
    _set_preview_property(obj, "SupplementalCompatibilityPolicy", supplemental_policy)
    _set_preview_property(obj, "SupplementalCompatibilityReason", supplemental_reason)
    _set_preview_integer_property(obj, "PotentialSupplementalFrameCount", int(sampling_summary.get("supplemental_frame_count", 0) or 0))
    _set_preview_integer_property(obj, "PotentialSupplementalFallbackCount", int(sampling_summary.get("fallback_count", 0) or 0))
    _set_preview_string_list_property(obj, "PotentialSupplementalSourceModes", sampling_source_mode_rows)
    _set_preview_property(
        obj,
        "BuildCorridorConsumerSummary",
        (
            f"applied={str(getattr(applied, 'applied_section_set_id', '') or '')}; "
            f"centerline={str(centerline_result_id or '')}; "
            f"source_mode={str(centerline_source_mode or '')}; "
            f"source_sections={source_section_count}; "
            f"supplemental_sections={supplemental_section_count}; "
            f"total_sections={total_section_count}; "
            f"links={int(result_contract_summary.get('subassembly_link_count', 0) or 0)}; "
            f"surface_roles={_format_count_summary(link_role_counts)}; "
            f"shapes={int(result_contract_summary.get('subassembly_shape_count', 0) or 0)}; "
            f"regions={len(consumed_region_refs)}; "
            f"intersection_control_regions={len(consumed_intersection_control_region_refs)}; "
            f"result_contract_fallback={int(bool(result_contract_fallback))}; "
            f"centerline_fallback={int(bool(centerline_fallback_active))}; "
            f"supplemental_compatibility_fallback={int(bool(compatibility_fallback))}"
        ),
    )
    _set_watertight_solid_readiness_properties(
        obj,
        document=document,
        applied_section_set=applied,
        corridor_model=corridor_model,
    )


def _applied_section_result_contract_consumption_summary(applied_section_set) -> dict[str, object]:
    sections = list(getattr(applied_section_set, "sections", []) or []) if applied_section_set is not None else []
    link_role_counts: dict[str, int] = {}
    point_role_counts: dict[str, int] = {}
    shape_family_counts: dict[str, int] = {}
    region_refs: set[str] = set()
    intersection_control_region_refs: set[str] = set()
    link_count = 0
    point_count = 0
    shape_count = 0
    for section in sections:
        section_region = str(getattr(section, "region_id", "") or "").strip()
        if section_region:
            region_refs.add(section_region)
        for control_ref in list(getattr(section, "active_intersection_control_region_refs", []) or []):
            control_ref_text = str(control_ref or "").strip()
            if control_ref_text:
                intersection_control_region_refs.add(control_ref_text)
                region_refs.add(control_ref_text)
        for row in list(getattr(section, "subassembly_rows", []) or []):
            row_region = str(getattr(row, "region_id", "") or "").strip()
            if row_region:
                region_refs.add(row_region)
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            link_count += 1
            role = str(getattr(link, "surface_role", "") or "unassigned").strip() or "unassigned"
            link_role_counts[role] = int(link_role_counts.get(role, 0) or 0) + 1
        for point in list(getattr(section, "subassembly_point_rows", []) or []):
            point_count += 1
            role = str(getattr(point, "point_code", "") or "unassigned").strip() or "unassigned"
            point_role_counts[role] = int(point_role_counts.get(role, 0) or 0) + 1
        for shape in list(getattr(section, "subassembly_shape_rows", []) or []):
            shape_count += 1
            family = str(getattr(shape, "solid_family", "") or "unassigned").strip() or "unassigned"
            shape_family_counts[family] = int(shape_family_counts.get(family, 0) or 0) + 1
    return {
        "subassembly_link_count": link_count,
        "subassembly_point_count": point_count,
        "subassembly_shape_count": shape_count,
        "link_surface_role_counts": link_role_counts,
        "point_role_counts": point_role_counts,
        "shape_family_counts": shape_family_counts,
        "region_refs": sorted(region_refs),
        "intersection_control_region_refs": sorted(intersection_control_region_refs),
    }


def _set_watertight_solid_readiness_properties(
    obj,
    *,
    document=None,
    applied_section_set=None,
    corridor_model=None,
) -> None:
    """Expose ordinary-road readiness for downstream watertight solid targets."""

    if obj is None:
        return
    try:
        from ..services.builders.solid_target_discovery_service import SolidTargetDiscoveryRequest, SolidTargetDiscoveryService

        doc = document or getattr(obj, "Document", None)
        solid_targets = SolidTargetDiscoveryService().discover(
            SolidTargetDiscoveryRequest(
                project_id=str(getattr(applied_section_set, "project_id", "") or "corridorroad-v1"),
                corridor_ref=str(getattr(corridor_model, "corridor_id", "") or getattr(applied_section_set, "corridor_id", "") or "corridor:main"),
                applied_section_set=applied_section_set,
                corridor_model=corridor_model,
                region_model=to_region_model(find_v1_region_model(doc)) if doc is not None else None,
                intersection_model=to_intersection_model(find_v1_intersection_model(doc)) if doc is not None else None,
                structure_model=to_structure_model(find_v1_structure_model(doc)) if doc is not None else None,
                drainage_model=to_drainage_model(find_v1_drainage_model(doc)) if doc is not None else None,
            )
        )
    except Exception:
        _set_preview_property(obj, "WatertightSolidReadinessStatus", "unknown")
        _set_preview_property(obj, "WatertightSolidReadinessSummary", "watertight_solid_readiness=unknown")
        return

    rows = list(getattr(solid_targets, "target_rows", []) or [])
    diagnostics = list(getattr(solid_targets, "target_diagnostic_rows", []) or [])
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    physical_body_count = 0
    surface_like_count = 0
    envelope_count = 0
    target_region_refs: set[str] = set()
    target_material_refs: set[str] = set()
    target_station_span_rows: list[str] = []
    for row in rows:
        status = str(getattr(row, "readiness_status", "") or "planned")
        family = str(getattr(row, "target_family", "") or "unknown")
        target_class = _watertight_solid_target_contract_class(row)
        target_id = str(getattr(row, "target_id", "") or "")
        scope = str(getattr(row, "scope_kind", "") or "")
        region_ref = str(getattr(row, "region_ref", "") or "").strip()
        material_ref = str(getattr(row, "material_ref", "") or "").strip()
        if region_ref:
            target_region_refs.add(region_ref)
        if material_ref:
            target_material_refs.add(material_ref)
        target_station_span_rows.append(
            (
                f"{target_id}|{family}|{scope}|"
                f"{float(getattr(row, 'station_start', 0.0) or 0.0):.3f}|"
                f"{float(getattr(row, 'station_end', 0.0) or 0.0):.3f}|"
                f"{region_ref}|{material_ref}|{status}"
            )
        )
        status_counts[status] = status_counts.get(status, 0) + 1
        family_counts[f"{family}:{status}"] = family_counts.get(f"{family}:{status}", 0) + 1
        class_counts[f"{target_class}:{status}"] = class_counts.get(f"{target_class}:{status}", 0) + 1
        if target_class == "physical_body":
            physical_body_count += 1
        elif target_class == "surface_like":
            surface_like_count += 1
        elif target_class == "envelope":
            envelope_count += 1
    available_count = int(status_counts.get("available", 0) or 0)
    blocked_count = int(status_counts.get("blocked", 0) or 0)
    planned_count = int(status_counts.get("planned", 0) or 0)
    if available_count <= 0:
        readiness = "blocked"
    elif blocked_count > 0:
        readiness = "partial"
    else:
        readiness = "ready"
    physical_body_readiness = "ready" if physical_body_count > 0 else "blocked"
    physical_body_reason = (
        "Physical-body Watertight Solid targets are available."
        if physical_body_count > 0
        else "No physical-body Watertight Solid targets were discovered; closed Subassembly shape/material contracts may be missing."
    )
    digital_twin_readiness = "ready"
    if readiness == "blocked" or physical_body_readiness == "blocked":
        digital_twin_readiness = "blocked"
    elif readiness == "partial":
        digital_twin_readiness = "partial"
    blocked_diagnostics = [
        f"{str(getattr(row, 'kind', '') or '')}|{str(getattr(row, 'source_ref', '') or '')}|{str(getattr(row, 'message', '') or '')}"
        for row in diagnostics
        if str(getattr(row, "severity", "") or "").lower() in {"error", "warning"}
    ]
    missing_prerequisite_rows = [
        (
            f"{str(getattr(row, 'severity', '') or '')}|"
            f"{str(getattr(row, 'kind', '') or '')}|"
            f"{str(getattr(row, 'source_ref', '') or '')}|"
            f"{str(getattr(row, 'message', '') or '')}|"
            f"{str(getattr(row, 'notes', '') or '')}"
        )
        for row in diagnostics
        if str(getattr(row, "severity", "") or "").lower() in {"error", "warning"}
    ]
    diagnostic_refs_by_id = {
        str(getattr(row, "diagnostic_id", "") or ""): row
        for row in diagnostics
        if str(getattr(row, "diagnostic_id", "") or "")
    }
    blocked_target_rows = []
    for row in rows:
        status = str(getattr(row, "readiness_status", "") or "planned")
        if status not in {"blocked", "planned"}:
            continue
        diagnostic_kinds = []
        for diagnostic_ref in list(getattr(row, "diagnostic_refs", []) or []):
            diagnostic = diagnostic_refs_by_id.get(str(diagnostic_ref or ""))
            if diagnostic is not None:
                diagnostic_kinds.append(str(getattr(diagnostic, "kind", "") or "diagnostic"))
        blocked_target_rows.append(
            (
                f"{str(getattr(row, 'target_id', '') or '')}|"
                f"{str(getattr(row, 'target_family', '') or '')}|"
                f"{str(getattr(row, 'scope_kind', '') or '')}|"
                f"{str(getattr(row, 'region_ref', '') or '')}|"
                f"{str(getattr(row, 'material_ref', '') or '')}|"
                f"{status}|"
                f"diagnostics={','.join(diagnostic_kinds)}"
            )
        )
    digital_twin_summary = (
        f"digital_twin_readiness={digital_twin_readiness};"
        f"overall={readiness};"
        f"physical_body={physical_body_readiness};"
        f"available={available_count};"
        f"blocked={blocked_count};"
        f"missing_prerequisites={len(missing_prerequisite_rows)};"
        f"blocked_targets={len(blocked_target_rows)};"
        f"reason={physical_body_reason}"
    )
    _set_preview_property(obj, "WatertightSolidTargetModelId", str(getattr(solid_targets, "solid_target_model_id", "") or ""))
    _set_preview_property(obj, "WatertightSolidReadinessStatus", readiness)
    _set_preview_integer_property(obj, "WatertightSolidAvailableTargetCount", available_count)
    _set_preview_integer_property(obj, "WatertightSolidBlockedTargetCount", blocked_count)
    _set_preview_integer_property(obj, "WatertightSolidPlannedTargetCount", planned_count)
    _set_preview_integer_property(obj, "WatertightSolidDiagnosticCount", len(diagnostics))
    _set_preview_integer_property(obj, "WatertightSolidPhysicalBodyTargetCount", physical_body_count)
    _set_preview_integer_property(obj, "WatertightSolidSurfaceLikeTargetCount", surface_like_count)
    _set_preview_integer_property(obj, "WatertightSolidEnvelopeTargetCount", envelope_count)
    _set_preview_property(obj, "WatertightSolidPhysicalBodyReadinessStatus", physical_body_readiness)
    _set_preview_property(obj, "WatertightSolidPhysicalBodyReadinessReason", physical_body_reason)
    _set_preview_property(obj, "WatertightSolidDigitalTwinReadinessStatus", digital_twin_readiness)
    _set_preview_property(obj, "WatertightSolidDigitalTwinReadinessSummary", digital_twin_summary)
    _set_preview_integer_property(obj, "WatertightSolidStationSpanCount", len(target_station_span_rows))
    _set_preview_string_list_property(obj, "WatertightSolidTargetStationSpans", target_station_span_rows)
    _set_preview_string_list_property(obj, "WatertightSolidTargetRegionRefs", sorted(target_region_refs))
    _set_preview_string_list_property(obj, "WatertightSolidTargetMaterialRefs", sorted(target_material_refs))
    _set_preview_string_list_property(obj, "WatertightSolidTargetCounts", [f"{key}={value}" for key, value in sorted(status_counts.items())])
    _set_preview_string_list_property(obj, "WatertightSolidTargetFamilyCounts", [f"{key}={value}" for key, value in sorted(family_counts.items())])
    _set_preview_string_list_property(obj, "WatertightSolidTargetClassCounts", [f"{key}={value}" for key, value in sorted(class_counts.items())])
    _set_preview_string_list_property(obj, "WatertightSolidBlockedDiagnostics", blocked_diagnostics)
    _set_preview_integer_property(obj, "WatertightSolidMissingPrerequisiteCount", len(missing_prerequisite_rows))
    _set_preview_string_list_property(obj, "WatertightSolidMissingPrerequisiteRows", missing_prerequisite_rows)
    _set_preview_string_list_property(obj, "WatertightSolidBlockedTargetRows", blocked_target_rows)
    _set_preview_property(
        obj,
        "WatertightSolidReadinessSummary",
        (
            f"status={readiness};available={available_count};blocked={blocked_count};"
            f"planned={planned_count};diagnostics={len(diagnostics)};"
            f"physical_body_targets={physical_body_count};"
            f"physical_body_readiness={physical_body_readiness};"
            f"surface_like_targets={surface_like_count};"
            f"envelope_targets={envelope_count};"
            f"station_spans={len(target_station_span_rows)};"
            f"region_refs={len(target_region_refs)};"
            f"material_refs={len(target_material_refs)};"
            f"missing_prerequisites={len(missing_prerequisite_rows)};"
            f"blocked_targets={len(blocked_target_rows)}"
        ),
    )


def _watertight_solid_target_contract_class(row) -> str:
    family = str(getattr(row, "target_family", "") or "").strip().lower()
    scope = str(getattr(row, "scope_kind", "") or "").strip().lower()
    if family == "road_body_envelope":
        return "envelope"
    if family.endswith("_body"):
        return "physical_body"
    if "surface" in family or scope in {"surface", "terrain"}:
        return "surface_like"
    return "other"


def create_or_update_corridor_supplemental_frame_markers(
    *,
    document=None,
    project=None,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
    visible: bool = False,
):
    """Create or update output-only supplemental frame markers in the 3D View."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return None
    applied = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    sections = supplemental_sampled_sections(
        list(getattr(applied, "sections", []) or []),
        max_spacing=float(supplemental_sampling_max_spacing or SUPPLEMENTAL_SAMPLING_MAX_SPACING),
        tangent_delta_threshold_deg=float(supplemental_sampling_tangent_delta_deg or SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG),
        chord_deviation_threshold=float(supplemental_sampling_chord_deviation or SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD),
        frame_resolver=_corridor_supplemental_frame_resolver(doc),
    )
    supplemental_sections = [
        section
        for section in sections
        if "supplemental:" in str(getattr(section, "applied_section_id", "") or "")
        and getattr(section, "frame", None) is not None
    ]
    if not supplemental_sections:
        return None
    shapes = []
    station_rows: list[str] = []
    marker_size = 0.75
    tangent_size = 1.25
    for section in supplemental_sections:
        frame = getattr(section, "frame", None)
        x = float(getattr(frame, "x", 0.0) or 0.0)
        y = float(getattr(frame, "y", 0.0) or 0.0)
        z = float(getattr(frame, "z", 0.0) or 0.0)
        angle = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        tx = math.cos(angle)
        ty = math.sin(angle)
        nx = -math.sin(angle)
        ny = math.cos(angle)
        shapes.append(Part.makeLine(AppModule.Vector(x - nx * marker_size, y - ny * marker_size, z), AppModule.Vector(x + nx * marker_size, y + ny * marker_size, z)))
        shapes.append(Part.makeLine(AppModule.Vector(x, y, z), AppModule.Vector(x + tx * tangent_size, y + ty * tangent_size, z)))
        station_rows.append(f"{float(getattr(frame, 'station', 0.0) or 0.0):.3f}|{str(getattr(frame, 'notes', '') or '')}")
    object_name = "V1CorridorSupplementalFrameMarkers"
    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = "Corridor Supplemental Frame Markers"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_or_update_corridor_supplemental_frame_markers", error=error)
    _set_preview_property(obj, "CRRecordKind", "v1_corridor_supplemental_frame_markers")
    _set_preview_property(obj, "V1ObjectType", "V1CorridorSupplementalFrameMarkers")
    _set_preview_property(obj, "AppliedSectionSetId", str(getattr(applied, "applied_section_set_id", "") or ""))
    _set_preview_float_property(obj, "MaxSpacing", float(supplemental_sampling_max_spacing or SUPPLEMENTAL_SAMPLING_MAX_SPACING))
    _set_preview_float_property(obj, "TangentDeltaThresholdDeg", float(supplemental_sampling_tangent_delta_deg or SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG))
    _set_preview_float_property(obj, "ChordDeviationThreshold", float(supplemental_sampling_chord_deviation or SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD))
    _set_preview_integer_property(obj, "MarkerCount", len(supplemental_sections))
    _set_preview_string_list_property(obj, "StationRows", station_rows)
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.ShapeColor = (1.0, 0.78, 0.05)
            vobj.LineColor = (1.0, 0.78, 0.05)
            vobj.PointColor = (1.0, 0.78, 0.05)
            vobj.LineWidth = 3.0
            vobj.Visibility = bool(visible)
    except Exception:
        pass
    _set_object_visibility(obj, bool(visible))
    try:
        route_object_to_project_tree(project or find_project(doc), obj)
    except Exception:
        pass
    return obj


def _corridor_supplemental_frame_marker_object(document):
    if document is None:
        return None
    try:
        return document.getObject("V1CorridorSupplementalFrameMarkers")
    except Exception:
        return None


def _tin_surface_from_corridor_surface_build_result(build_result):
    if (
        str(getattr(build_result, "status", "") or "") == "ready"
        and getattr(build_result, "tin_surface", None) is not None
    ):
        return build_result.tin_surface
    message = str(getattr(build_result, "error_message", "") or "").strip()
    if not message:
        message = "; ".join(
            str(value or "").strip()
            for value in list(getattr(build_result, "diagnostic_rows", ()) or ())
            if str(value or "").strip()
        )
    raise RuntimeError(message or "Corridor surface geometry build failed.")


def create_corridor_design_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
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
    effective_supplemental_sampling_enabled = _build_corridor_effective_hidden_supplemental_sampling_enabled(
        doc,
        applied_section_set=applied_section_set,
        requested=supplemental_sampling_enabled,
        supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
        supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
        supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
    )
    supplemental_frame_resolver = _corridor_supplemental_frame_resolver(doc) if effective_supplemental_sampling_enabled else None
    try:
        build_result = CorridorSurfaceOrchestrationService().build(
            CorridorSurfaceGeometryBuildRequest(
                surface_role="design",
                geometry_request=CorridorDesignSurfaceGeometryRequest(
                    project_id=_project_id(project or find_project(doc)),
                    corridor=corridor_model,
                    applied_section_set=applied_section_set,
                    surface_id=surface_id,
                    supplemental_sampling_enabled=effective_supplemental_sampling_enabled,
                    supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
                    supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
                    supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
                    supplemental_frame_resolver=supplemental_frame_resolver,
                    surface_transition_model=transition_model,
                ),
            )
        )
        tin_surface = _tin_surface_from_corridor_surface_build_result(build_result)
        tin_surface = _clip_tin_surface_by_intersection_exclusion(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
            surface_role="design",
        )
        general_shared_breakline_result = corridor_general_shared_breakline_result(applied_section_set)
        region_shared_breakline_result = corridor_region_transition_shared_breakline_result(applied_section_set)
        # an intersection meets the corridor at its mouths, which are Applied Sections: the general
        # breaklines already run along them
        design_shared_breakline_result = combined_shared_breakline_result(
            general_shared_breakline_result,
            region_shared_breakline_result,
        )
        tin_surface = tin_surface_with_shared_breakline_constraint_edges(
            tin_surface,
            design_shared_breakline_result,
            consumer_ref="design_surface",
        )
        tin_surface = tin_surface_with_shared_breakline_metadata(
            tin_surface,
            design_shared_breakline_result,
            consumer_ref="design_surface",
        )
        tin_surface = _clip_tin_surface_by_roundabout_ownership(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
            surface_role="design_surface",
        )
        shared_breakline_audit_result = shared_breakline_audit(
            design_shared_breakline_result,
            {"design_surface": tin_surface},
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
    _attach_design_surface_preview_metadata(
        doc,
        preview_obj,
        applied_section_set=applied_section_set,
        corridor_model=corridor_model,
        design_shared_breakline_result=design_shared_breakline_result,
        project=project,
        result=result,
        shared_breakline_audit_result=shared_breakline_audit_result,
        surface_id=surface_id,
        surface_model=surface_model,
        tin_surface=tin_surface,
    )
    return preview_obj


def _attach_design_surface_preview_metadata(
    doc,
    preview_obj,
    *,
    applied_section_set,
    corridor_model,
    design_shared_breakline_result,
    project,
    result,
    shared_breakline_audit_result,
    surface_id,
    surface_model,
    tin_surface,
) -> None:
    """Record the design surface preview contract, shared breakline, and audit metadata."""

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
        _attach_shared_breakline_preview_metadata(
            preview_obj,
            design_shared_breakline_result if "design_shared_breakline_result" in locals() else None,
            consumer_ref="design_surface",
            audit=shared_breakline_audit_result if "shared_breakline_audit_result" in locals() else None,
        )
        _attach_shared_breakline_constraint_preview_metadata(preview_obj, tin_surface)
        _attach_roundabout_ownership_intrusion_metadata(
            preview_obj,
            tin_surface,
            doc,
            surface_role="design_surface",
        )
        try:
            route_object_to_project_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass


def create_corridor_intersection_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
):
    """Create or update the intersection surfaces: the kernel's patch and side slope."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_section_set = to_applied_section_set(find_v1_applied_section_set(doc))
    if applied_section_set is None:
        _clear_intersection_surface_previews_with_diagnostic(
            doc,
            project=project,
            status="missing",
            notes="Intersection Surface preview was not created because Applied Sections are required.",
        )
        return None
    if not _document_has_intersection(doc):
        return None
    return _create_kernel_intersection_surface_previews(doc, project=project, applied_section_set=applied_section_set)


def _roundabout_kernel_clip_polygons(document) -> tuple[dict[str, object], list[list[tuple[float, float]]]]:
    """A roundabout's boundary from the intersection kernel, as the clip polygon the subassembly kind
    review keeps lane and shoulder strips out of; nothing for any other intersection."""

    result = _document_intersection_kernel_result(document)
    if result is None or result.kind != "roundabout" or not result.boundary_xyz:
        return {}, []
    polygon = [(p[0], p[1]) for p in result.boundary_xyz]
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    summary = {
        "status": "ready" if result.status == "ready" else "warning",
        "boundary_role": "intersection_kernel_boundary",
        "boundary_result_id": f"intersection-kernel:{result.input_fingerprint}",
        "loop_count": 1,
        "segment_count": len(polygon),
        "loop_refs": [result.intersection_id],
        "loop_bboxes": [f"{min(xs):.3f},{min(ys):.3f},{max(xs):.3f},{max(ys):.3f}"],
        "loop_areas": [f"{result.boundary_area_m2:.3f}"],
        "diagnostics": [row.code for row in result.diagnostics],
    }
    return summary, [polygon]


def _document_intersection_kernel_result(document):
    """The kernel result of the document's intersection on its current Applied Sections, or None."""

    if not _document_has_intersection(document):
        return None
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    if applied is None:
        return None
    return _intersection_kernel_result(document, applied)


def _document_has_intersection(document) -> bool:
    """True when the document holds an Intersection source; the kernel builds it."""

    return document is not None and find_v1_intersection_model(document) is not None


def _intersection_kernel_result(document, applied_section_set):
    """The kernel's result on the document's intersection, Alignments and Applied Sections."""

    intersection_obj = find_v1_intersection_model(document)
    return intersection_geometry_from_models(
        to_intersection_model(intersection_obj),
        [model for model in (to_alignment_model(obj) for obj in list(getattr(document, "Objects", []) or [])) if model is not None],
        applied_section_set,
        spec=stored_intersection_spec(intersection_obj),
    )


def _clip_tin_surface_by_kernel_spans(surface, document, *, applied_section_set):
    applied = applied_section_set if applied_section_set is not None else to_applied_section_set(find_v1_applied_section_set(document))
    result = _intersection_kernel_result(document, applied)
    if result is None or result.status == "blocked":
        return surface
    return clip_tin_surface_by_station_spans(surface, applied, result.clip_spans)


def _create_kernel_intersection_surface_previews(doc, *, project, applied_section_set):
    """The kernel engine's intersection surfaces: its patch and its side slope.

    Every legacy intersection preview is removed first; the kernel builds two surfaces and keeps
    its own figures on them. A blocked kernel leaves no surface and records its diagnostics.
    """

    for name in (
        "V1CorridorIntersectionCurbReturnSlopePreview",
        "V1CorridorIntersectionTieInEdgePreview",
        "V1CorridorIntersectionBoundarySegmentPreview",
        "V1CorridorIntersectionExclusionZonePreview",
        "V1CorridorIntersectionSlopeFaceLoopPreview",
        "V1CorridorIntersectionTieSlopeSurfacePreview",
        "V1CorridorIntersectionSurfaceZoneOutputPreview",
        "V1CorridorRoundaboutApronSurfacePreview",
        "V1CorridorRoundaboutSubgradeSurfacePreview",
        "V1CorridorRoundaboutSlopeFaceSurfacePreview",
        "V1CorridorIntersectionSlopeFaceOverlapPreview",
        "ReviewIntersectionSharedBoundaryGraphHighlight",
        "ReviewIntersectionSharedBoundaryGraphInternalSeamHighlight",
        "ReviewIntersectionExclusionNearBoundaryKeptHighlight",
    ):
        _remove_preview_object(doc, name)
    project_obj = project or find_project(doc)
    result = _intersection_kernel_result(doc, applied_section_set)
    if result is None or result.status == "blocked" or not result.patch_triangles:
        _clear_intersection_surface_previews_with_diagnostic(
            doc,
            project=project_obj,
            status="error" if result is not None else "missing",
            notes="Intersection Surface was not built by the kernel: "
            + ("; ".join(row.as_text() for row in result.diagnostics) if result is not None else "no intersection row"),
        )
        return None
    intersection_model = to_intersection_model(find_v1_intersection_model(doc))
    kind = str(getattr((list(getattr(intersection_model, "intersection_rows", []) or []) or [None])[0], "intersection_kind", "") or "")
    rows = {
        "IntersectionKernelDiagnosticRows": [row.as_text() for row in result.diagnostics],
        "IntersectionKernelQualityRows": [f"{name}|{value:.6g}" for name, value in result.quality_rows],
        "IntersectionKernelClipSpanRows": [f"{ref}|{start:.6f}|{end:.6f}" for ref, start, end in result.clip_spans],
        "IntersectionKernelResolvedValueRows": [f"{v.name}|{v.subject}|{v.value}|{v.origin}" for v in result.resolved_values],
    }
    preview = None
    for part, object_name, label in (
        ("patch", "V1CorridorIntersectionSurfacePreview", "Intersection Surface"),
        ("slope", "V1CorridorIntersectionSlopeFaceSurfacePreview", "Intersection Slope Face Surface"),
    ):
        surface = kernel_tin_surface(result, part=part, surface_id=f"{result.intersection_id}:{part}", project_id=_project_id(project_obj))
        if not surface.triangle_rows:
            _remove_preview_object(doc, object_name)
            continue
        mapped = TINMeshPreviewMapper().create_or_update_preview_object(
            doc, surface, object_name=object_name, label_prefix=label, surface_role="intersection", recompute=False,
        )
        obj = doc.getObject(mapped.object_name) if str(getattr(mapped, "object_name", "") or "") else None
        if obj is None:
            continue
        _set_preview_property(obj, "IntersectionKind", kind)
        _set_preview_property(obj, "IntersectionKernelStatus", result.status)
        _set_preview_property(obj, "IntersectionKernelFingerprint", result.input_fingerprint)
        for name, values in rows.items():
            _set_preview_string_list_property(obj, name, values)
        try:
            route_object_to_project_tree(project_obj, obj)
        except Exception:
            pass
        if part == "patch":
            preview = obj
    return preview


def _clear_intersection_surface_previews_with_diagnostic(
    doc,
    *,
    project,
    status: str,
    notes: str,
) -> None:
    """Remove every intersection preview object and record why the surface was not created."""

    _remove_preview_object(doc, "V1CorridorIntersectionSurfacePreview")
    _remove_preview_object(doc, "V1CorridorIntersectionCurbReturnSlopePreview")
    _remove_preview_object(doc, "V1CorridorIntersectionTieInEdgePreview")
    _remove_preview_object(doc, "V1CorridorIntersectionBoundarySegmentPreview")
    _remove_preview_object(doc, "V1CorridorIntersectionExclusionZonePreview")
    _remove_preview_object(doc, "V1CorridorIntersectionSlopeFaceLoopPreview")
    _remove_preview_object(doc, "V1CorridorIntersectionSlopeFaceSurfacePreview")
    _remove_preview_object(doc, "V1CorridorIntersectionTieSlopeSurfacePreview")
    _record_corridor_build_preview_diagnostic(
        doc,
        role="intersection",
        surface_kind="intersection_surface",
        status=status,
        notes=notes,
        project=project or find_project(doc),
    )


INTERSECTION_LEGACY_PATCH_COMPATIBILITY_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("PatchBoundaryPointCount", "IntersectionSurfacePatchBoundaryRowCount"),
    ("PatchTriangulationMode", "IntersectionSurfacePatchSummary"),
    ("PatchSurfaceBoundaryStrategy", "IntersectionSurfacePatchSummary"),
    ("PatchBoundaryRoleSummary", "IntersectionSurfacePatchBoundaryRowRefs"),
    ("PatchTriangleMinQuality", "IntersectionSurfacePatchQualityRowStatuses"),
    ("PatchTriangleSkinnyCount", "IntersectionSurfacePatchQualityRowStatuses"),
    ("IntersectionPatchBoundaryStatus", "IntersectionSurfacePatchBoundaryRowStatuses"),
    ("IntersectionPatchBoundaryDiagnostics", "IntersectionSurfacePatchRowDiagnostics"),
    ("PatchBoundaryLongEdgeCount", "IntersectionSurfacePatchRowDiagnostics"),
    ("PatchDegenerateTriangleCount", "IntersectionSurfacePatchQualityRowStatuses"),
)
CORRIDOR_BUILD_VISIBILITY_GROUPS = (
    ("design", "Design", ("design", "subgrade", "drainage"), ()),
    (
        "intersection",
        "Intersection",
        ("intersection", "intersection_slope"),
        (),
    ),
    ("slope_face", "Slope Face", ("daylight", "intersection_slope"), ()),
    (
        "breaklines",
        "Breaklines",
        (),
        (
            "ReviewSharedBreaklineHighlight",
            "ReviewIntersectionSharedBoundaryGraphHighlight",
            "ReviewIntersectionSharedBoundaryGraphInternalSeamHighlight",
            "ReviewIntersectionExclusionNearBoundaryKeptHighlight",
        ),
    ),
    (
        "diagnostics",
        "Diagnostics",
        (),
        (
            "ReviewDiagnosticSlopeFaceIntersectionMarkers",
            "ReviewDiagnosticSlopeFaceSampledEdgeMarkers",
            "ReviewDiagnosticSlopeFaceFallbackMarkers",
            "ReviewIssueSlopeFaceIntersectionMarkers",
            "ReviewIssueSlopeFaceSampledEdgeMarkers",
            "ReviewIssueSlopeFaceFallbackMarkers",
            "ReviewIssueDrainageFlowRoutes",
        ),
    ),
)


def create_corridor_region_surface_previews(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
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
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
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
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
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
    effective_supplemental_sampling_enabled = _build_corridor_effective_hidden_supplemental_sampling_enabled(
        doc,
        applied_section_set=applied_section_set,
        requested=supplemental_sampling_enabled,
        supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
        supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
        supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
    )
    supplemental_frame_resolver = _corridor_supplemental_frame_resolver(doc) if effective_supplemental_sampling_enabled else None
    try:
        build_result = CorridorSurfaceOrchestrationService().build(
            CorridorSurfaceGeometryBuildRequest(
                surface_role="subgrade",
                geometry_request=CorridorDesignSurfaceGeometryRequest(
                    project_id=_project_id(project or find_project(doc)),
                    corridor=corridor_model,
                    applied_section_set=applied_section_set,
                    surface_id=surface_id,
                    supplemental_sampling_enabled=effective_supplemental_sampling_enabled,
                    supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
                    supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
                    supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
                    supplemental_frame_resolver=supplemental_frame_resolver,
                    surface_transition_model=transition_model,
                ),
            )
        )
        tin_surface = _tin_surface_from_corridor_surface_build_result(build_result)
        tin_surface = _clip_tin_surface_by_roundabout_ownership(
            tin_surface,
            doc,
            applied_section_set=applied_section_set,
            surface_role="subgrade_surface",
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
        _attach_roundabout_ownership_intrusion_metadata(
            preview_obj,
            tin_surface,
            doc,
            surface_role="subgrade_surface",
        )
        try:
            route_object_to_project_tree(project or find_project(doc), preview_obj)
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
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
):
    """Create or update the first slope-face mesh preview for a corridor."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or corridor_model is None or surface_model is None:
        return None
    applied_obj = find_v1_applied_section_set(doc)
    applied_section_set = to_applied_section_set(applied_obj)
    if applied_section_set is None:
        return None
    # Slope Face Surface must consume the explicit AppliedSectionSet only.
    transition_model = to_surface_transition_model(find_v1_surface_transition_model(doc))
    surface_id = _surface_id(surface_model, "daylight_surface") or f"{corridor_model.corridor_id}:daylight"
    shared_breakline_result = None
    shared_breakline_audit_result = None
    effective_supplemental_sampling_enabled = _build_corridor_effective_hidden_supplemental_sampling_enabled(
        doc,
        applied_section_set=applied_section_set,
        requested=supplemental_sampling_enabled,
        supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
        supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
        supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
    )
    supplemental_frame_resolver = _corridor_supplemental_frame_resolver(doc) if effective_supplemental_sampling_enabled else None
    try:
        build_result = CorridorSurfaceOrchestrationService().build(
            CorridorSurfaceGeometryBuildRequest(
                surface_role="daylight",
                geometry_request=CorridorDesignSurfaceGeometryRequest(
                    project_id=_project_id(project or find_project(doc)),
                    corridor=corridor_model,
                    applied_section_set=applied_section_set,
                    surface_id=surface_id,
                    existing_ground_surface=_resolve_corridor_existing_ground_tin_surface(doc),
                    supplemental_sampling_enabled=effective_supplemental_sampling_enabled,
                    supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
                    supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
                    supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
                    supplemental_frame_resolver=supplemental_frame_resolver,
                    surface_transition_model=transition_model,
                ),
            )
        )
        tin_surface = _tin_surface_from_corridor_surface_build_result(build_result)
        # the intersection's side slope meets this surface at the mouths: clip it by the station spans
        tin_surface = _clip_tin_surface_by_kernel_spans(tin_surface, doc, applied_section_set=applied_section_set)
        shared_breakline_audit_result, shared_breakline_result, tin_surface = _build_daylight_surface_shared_breaklines(
            doc,
            applied_section_set=applied_section_set,
            tin_surface=tin_surface,
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
        label_prefix="",
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
    _attach_daylight_surface_preview_metadata(
        doc,
        preview_obj,
        applied_section_set=applied_section_set,
        corridor_model=corridor_model,
        project=project,
        result=result,
        shared_breakline_audit_result=shared_breakline_audit_result,
        shared_breakline_result=shared_breakline_result,
        show_daylight_contact_markers=show_daylight_contact_markers,
        surface_id=surface_id,
        surface_model=surface_model,
        tin_surface=tin_surface,
    )
    return preview_obj


def _build_daylight_surface_shared_breaklines(
    doc,
    *,
    applied_section_set,
    tin_surface,
) -> tuple:
    """Evaluate the general and region shared breaklines and fold them into the daylight surface."""

    general_shared_breakline_result = corridor_general_shared_breakline_result(applied_section_set)
    region_shared_breakline_result = corridor_region_transition_shared_breakline_result(applied_section_set)
    shared_breakline_result = combined_shared_breakline_result(
        general_shared_breakline_result,
        region_shared_breakline_result,
    )
    tin_surface = tin_surface_with_shared_breakline_constraint_edges(
        tin_surface,
        shared_breakline_result,
        consumer_ref="slope_face_surface",
    )
    tin_surface = tin_surface_with_shared_breakline_metadata(
        tin_surface,
        shared_breakline_result,
        consumer_ref="slope_face_surface",
    )
    tin_surface = _clip_tin_surface_by_roundabout_ownership(
        tin_surface,
        doc,
        applied_section_set=applied_section_set,
        surface_role="slope_face_surface",
    )
    shared_breakline_audit_result = shared_breakline_audit(
        shared_breakline_result,
        {"slope_face_surface": tin_surface},
    )

    return (shared_breakline_audit_result, shared_breakline_result, tin_surface)


def _attach_daylight_surface_preview_metadata(
    doc,
    preview_obj,
    *,
    applied_section_set,
    corridor_model,
    project,
    result,
    shared_breakline_audit_result,
    shared_breakline_result,
    show_daylight_contact_markers,
    surface_id,
    surface_model,
    tin_surface,
) -> None:
    """Record the daylight surface preview contract, shared breakline, and trim metadata."""

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
        _attach_shared_breakline_preview_metadata(
            preview_obj,
            shared_breakline_result,
            consumer_ref="slope_face_surface",
            audit=shared_breakline_audit_result,
        )
        _attach_shared_breakline_constraint_preview_metadata(preview_obj, tin_surface)
        _attach_roundabout_ownership_intrusion_metadata(
            preview_obj,
            tin_surface,
            doc,
            surface_role="slope_face_surface",
        )
        try:
            route_object_to_project_tree(project or find_project(doc), preview_obj)
        except Exception:
            pass
        _remove_preview_object(doc, "V1CorridorSlopeFaceGenerationBoundaryPreview")
        _remove_preview_object(doc, "V1CorridorIntersectionSlopeFaceBoundaryPreview")
        _create_slope_face_diagnostic_markers(
            document=doc,
            project=project or find_project(doc),
            surface=tin_surface,
            corridor_model=corridor_model,
            applied_section_set=applied_section_set,
            show_daylight_contact_markers=show_daylight_contact_markers,
        )


def create_corridor_drainage_surface_preview(
    *,
    document=None,
    project=None,
    corridor_model=None,
    surface_model=None,
    supplemental_sampling_enabled: bool = False,
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
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
        effective_supplemental_sampling_enabled = _build_corridor_effective_hidden_supplemental_sampling_enabled(
            doc,
            applied_section_set=applied_section_set,
            requested=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        supplemental_frame_resolver = _corridor_supplemental_frame_resolver(doc) if effective_supplemental_sampling_enabled else None
        build_result = CorridorSurfaceOrchestrationService().build(
            CorridorSurfaceGeometryBuildRequest(
                surface_role="drainage",
                geometry_request=CorridorDesignSurfaceGeometryRequest(
                    project_id=_project_id(project or find_project(doc)),
                    corridor=corridor_model,
                    applied_section_set=applied_section_set,
                    surface_id=surface_id,
                    supplemental_sampling_enabled=effective_supplemental_sampling_enabled,
                    supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
                    supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
                    supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
                    supplemental_frame_resolver=supplemental_frame_resolver,
                    surface_transition_model=transition_model,
                ),
            )
        )
        tin_surface = _tin_surface_from_corridor_surface_build_result(build_result)
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
            route_object_to_project_tree(project or find_project(doc), preview_obj)
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
        route_object_to_project_tree(project or find_project(doc), obj)
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
    _attach_applied_section_diagnostic_handoff_properties(obj, applied_section_set)
    _set_preview_string_list_property(
        obj,
        "SourceRefs",
        _corridor_surface_preview_source_refs(corridor_model, surface_model, applied_section_set),
    )
    _set_corridor_consumer_disclosure_properties(
        obj,
        document=getattr(obj, "Document", None),
        applied_section_set=applied_section_set,
        corridor_model=corridor_model,
        centerline_source_mode=_build_corridor_consumed_centerline_source_mode(getattr(obj, "Document", None)),
        centerline_result_id=_build_corridor_consumed_centerline_result_id(getattr(obj, "Document", None)),
    )
    _attach_corridor_surface_role_contract_review_properties(obj, role)


def _attach_corridor_surface_role_contract_review_properties(obj, role: str) -> None:
    expected_roles = _expected_surface_result_roles_for_build_role(role)
    consumed_counts = _preview_count_rows_to_dict(getattr(obj, "ConsumedSurfaceRoleCounts", []) or [])
    matched_rows = [
        f"{surface_role}={int(consumed_counts.get(surface_role, 0) or 0)}"
        for surface_role in expected_roles
        if int(consumed_counts.get(surface_role, 0) or 0) > 0
    ]
    if not expected_roles:
        status = "not_required"
    elif matched_rows:
        status = "ready"
    else:
        status = "missing"
    _set_preview_property(obj, "ResultContractExpectedSurfaceRoleStatus", status)
    _set_preview_string_list_property(obj, "ResultContractExpectedSurfaceRoles", list(expected_roles))
    _set_preview_string_list_property(obj, "ResultContractMatchedSurfaceRoles", matched_rows)


def _expected_surface_result_roles_for_build_role(role: str) -> tuple[str, ...]:
    role_key = str(role or "").strip().lower()
    if role_key == "design":
        return ("design_surface",)
    if role_key == "subgrade":
        return ("subgrade_surface", "subbase_surface")
    if role_key == "daylight":
        return ("slope_face_surface", "daylight_surface")
    if role_key == "drainage":
        return ("drainage_surface",)
    if role_key == "intersection_slope":
        return ("slope_face_surface",)
    return ()


def _preview_count_rows_to_dict(rows) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw in list(rows or []):
        text = str(raw or "").strip()
        if not text or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        if not key:
            continue
        try:
            counts[key] = int(float(str(value).strip() or 0))
        except Exception:
            counts[key] = 0
    return counts


def _attach_applied_section_diagnostic_handoff_properties(obj, applied_section_set) -> None:
    summary = _applied_section_diagnostic_handoff_summary(applied_section_set)
    _set_preview_property(obj, "AppliedSectionDiagnosticSummary", str(summary.get("summary", "") or "diagnostics=0"))
    _set_preview_integer_property(obj, "AppliedSectionDiagnosticCount", int(summary.get("diagnostic_count", 0) or 0))
    _set_preview_integer_property(obj, "AppliedSectionOverlapClipCount", int(summary.get("overlap_clip_count", 0) or 0))
    _set_preview_integer_property(obj, "AppliedSectionDaylightFallbackCount", int(summary.get("daylight_fallback_count", 0) or 0))
    _set_preview_integer_property(obj, "AppliedSectionDaylightTerrainHitCount", int(summary.get("daylight_terrain_hit_count", 0) or 0))
    _set_preview_string_list_property(obj, "AppliedSectionDiagnosticRows", list(summary.get("rows", []) or []))
    _set_preview_property(obj, "AppliedSectionClipReviewSummary", str(summary.get("clip_review_summary", "") or "clip_rows=0"))
    _set_preview_string_list_property(obj, "AppliedSectionClipReviewRows", list(summary.get("clip_review_rows", []) or []))


def _applied_section_diagnostic_handoff_summary(applied_section_set) -> dict[str, object]:
    sections = list(getattr(applied_section_set, "sections", []) or []) if applied_section_set is not None else []
    rows: list[str] = []
    clip_review_rows: list[str] = []
    kind_counts: dict[str, int] = {}
    daylight_fallback_count = 0
    daylight_terrain_hit_count = 0
    for section in sections:
        section_id = str(getattr(section, "applied_section_id", "") or "")
        station = float(getattr(section, "station", 0.0) or 0.0)
        for diagnostic in list(getattr(section, "diagnostic_rows", []) or []):
            kind = str(getattr(diagnostic, "kind", "") or "diagnostic")
            kind_counts[kind] = int(kind_counts.get(kind, 0) or 0) + 1
            notes = str(getattr(diagnostic, "notes", "") or "")
            if "daylight_status=fallback" in notes or kind in {"bench_daylight_fallback", "bench_daylight_no_hit"}:
                daylight_fallback_count += 1
            if "daylight_status=terrain_intersection" in notes or kind == "bench_daylight_shortened":
                daylight_terrain_hit_count += 1
            message = str(getattr(diagnostic, "message", "") or "")
            row = f"STA {station:.3f}|{section_id}|{kind}|{message}"
            if notes:
                row = f"{row}|{notes}"
            rows.append(row[:1000])
            if kind == "applied_section_overlap_clip":
                clip_review_rows.append(_applied_section_clip_review_row(station, section_id, notes))
    diagnostic_count = sum(kind_counts.values())
    overlap_clip_count = int(kind_counts.get("applied_section_overlap_clip", 0) or 0)
    parts = [
        f"diagnostics={diagnostic_count}",
        f"overlap_clip={overlap_clip_count}",
        f"daylight_fallback={daylight_fallback_count}",
        f"daylight_terrain_hit={daylight_terrain_hit_count}",
    ]
    if kind_counts:
        parts.append("kinds=" + _format_count_summary(kind_counts))
    clip_review_summary = f"clip_rows={len(clip_review_rows)}"
    if clip_review_rows:
        clip_review_summary = f"{clip_review_summary}; first={clip_review_rows[0]}"
    return {
        "diagnostic_count": diagnostic_count,
        "overlap_clip_count": overlap_clip_count,
        "daylight_fallback_count": daylight_fallback_count,
        "daylight_terrain_hit_count": daylight_terrain_hit_count,
        "summary": ";".join(parts),
        "rows": rows[:200],
        "clip_review_summary": clip_review_summary[:1000],
        "clip_review_rows": clip_review_rows[:200],
    }


def _applied_section_clip_review_row(station: float, section_id: str, notes: str) -> str:
    side = _diagnostic_note_value(notes, "side")
    clip_limit = _diagnostic_note_value(notes, "clip_limit")
    points = _diagnostic_note_value(notes, "clipped_point_ids")
    links = _diagnostic_note_value(notes, "clipped_link_ids")
    subassemblies = _diagnostic_note_value(notes, "subassembly_refs")
    previous = _diagnostic_note_value(notes, "previous_section_id")
    parts = [
        f"STA {float(station):.3f}",
        f"section={section_id}",
    ]
    if previous:
        parts.append(f"previous={previous}")
    if side:
        parts.append(f"side={side}")
    if clip_limit:
        parts.append(f"clip_limit={clip_limit}")
    if subassemblies:
        parts.append(f"subassemblies={subassemblies}")
    if points:
        parts.append(f"points={points}")
    if links:
        parts.append(f"links={links}")
    return ";".join(parts)[:1000]


def _diagnostic_note_value(notes: str, key: str) -> str:
    prefix = f"{str(key or '')}="
    for part in str(notes or "").split(";"):
        text = str(part or "").strip()
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return ""


def _build_corridor_consumed_centerline_source_mode(document=None) -> str:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return ""
    try:
        obj = doc.getObject("V1CorridorCenterline3DPreview")
    except Exception:
        obj = None
    if obj is not None:
        value = str(getattr(obj, "PreviewSource", "") or getattr(obj, "ConsumedCenterlineSourceMode", "") or "")
        if value:
            return value
    try:
        from .cmd_centerline3d import build_document_centerline3d_result

        result = build_document_centerline3d_result(doc)
        if result is not None:
            return "centerline3d_result"
    except Exception:
        pass
    return ""


def _build_corridor_consumed_centerline_result_id(document=None) -> str:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        return ""
    try:
        obj = doc.getObject("V1CorridorCenterline3DPreview")
    except Exception:
        obj = None
    if obj is not None:
        value = str(getattr(obj, "Centerline3DResultId", "") or getattr(obj, "ConsumedCenterline3DResultId", "") or "")
        if value:
            return value
    try:
        from .cmd_centerline3d import build_document_centerline3d_result

        result = build_document_centerline3d_result(doc)
        return str(getattr(result, "centerline3d_result_id", "") or "")
    except Exception:
        return ""


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


def _document_identity(document) -> str:
    if document is None:
        return ""
    for attr in ("Name", "Label"):
        try:
            value = str(getattr(document, attr, "") or "").strip()
        except Exception:
            value = ""
        if value:
            return value
    return str(id(document))


def _document_display_name(document) -> str:
    if document is None:
        return "No document"
    try:
        label = str(getattr(document, "Label", "") or "").strip()
    except Exception:
        label = ""
    try:
        name = str(getattr(document, "Name", "") or "").strip()
    except Exception:
        name = ""
    if label and name and label != name:
        return f"{label} ({name})"
    return label or name or "Unnamed"


def _compact_build_corridor_table(table, column_widths: list[int]) -> None:
    """Keep Build Parametric tables compact by default while allowing panel resize."""

    if table is None:
        return
    try:
        table.setMinimumWidth(0)
        table.setMaximumWidth(BUILD_CORRIDOR_PANEL_MAX_WIDTH)
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
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
    _fit_build_corridor_table_to_rows(table)


def _fit_build_corridor_table_to_rows(table, *, visible_rows: int = 10) -> None:
    """Fix Build Parametric table height to a stable visible row count."""

    if table is None:
        return
    try:
        row_count = max(int(table.rowCount()), 0)
        visible_rows = max(1, int(visible_rows))
        header_height = int(table.horizontalHeader().height()) if table.horizontalHeader() is not None else 28
        row_height = 0
        if row_count > 0:
            for row_index in range(min(row_count, visible_rows)):
                row_height = max(row_height, int(table.rowHeight(row_index)))
        if row_height <= 0:
            row_height = int(table.verticalHeader().defaultSectionSize()) if table.verticalHeader() is not None else 28
        row_height = max(row_height, 24)
        scrollbar_height = 18 if table.horizontalScrollBarPolicy() != QtCore.Qt.ScrollBarAlwaysOff else 0
        frame = int(table.frameWidth()) * 2 if hasattr(table, "frameWidth") else 4
        target_height = header_height + (visible_rows * row_height) + scrollbar_height + frame + 6
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        table.setFixedHeight(int(target_height))
    except Exception:
        return


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
    return applied_sections_review_summary(applied)


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
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=lambda section: section_station(section))


def _contiguous_region_groups(sections: list[object]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for section in list(sections or []):
        region_id = section_region_id(section)
        if not groups or str(groups[-1].get("region_id", "") or "") != region_id:
            groups.append({"region_id": region_id, "sections": [section]})
        else:
            groups[-1]["sections"].append(section)
    for group in groups:
        group_sections = list(group.get("sections", []) or [])
        stations = [section_station(section) for section in group_sections]
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
        diagnostics.extend(region_source_range_diagnostics(source_rows, index))
        diagnostics.extend(region_sample_coverage_diagnostics(source_row, group_sections))
        intersection_diagnostics = region_intersection_context_diagnostics(
            source_row,
            group_sections,
            intersection_model=intersection_model,
        )
        diagnostics.extend(intersection_diagnostics)
        if index > 0:
            previous_last = section_groups[index - 1][-1] if section_groups[index - 1] else None
            diagnostics.extend(region_boundary_diagnostics(previous_last, first, boundary_side="start"))
        if index < len(source_rows) - 1:
            next_first = section_groups[index + 1][0] if section_groups[index + 1] else None
            diagnostics.extend(region_boundary_diagnostics(last, next_first, boundary_side="end"))
        boundary_status = region_boundary_status(diagnostics)
        row = {
            "alignment_id": str(getattr(region_model, "alignment_id", "") or ""),
            "region_id": str(getattr(source_row, "region_id", "") or ""),
            "station_start": float(getattr(source_row, "station_start", 0.0) or 0.0),
            "station_end": float(getattr(source_row, "station_end", 0.0) or 0.0),
            "assembly": str(getattr(source_row, "assembly_ref", "") or "") or unique_join(_section_text_values(group_sections, "assembly_id")),
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
            "diagnostics": region_boundary_diagnostic_summary(diagnostics),
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
        if section_region_id(section) == region_id
        and low - tolerance <= section_station(section) <= high + tolerance
    ]
    return sorted(rows, key=lambda section: section_station(section))


def _section_text_values(sections: list[object], attr: str) -> list[str]:
    values: list[str] = []
    for section in list(sections or []):
        text = str(getattr(section, attr, "") or "").strip()
        if text:
            values.append(text)
    return values


def _region_group_structure_summary(sections: list[object], *, region_model=None, structure_model=None) -> str:
    values = list(section_structure_values(sections))
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
    return unique_join(values) or "-"


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
                station=section_station(section),
            )
        except Exception:
            continue
        section_region = section_region_id(section)
        context_region = str(getattr(getattr(context, "region_context", None), "region_id", "") or "")
        if section_region and context_region and section_region != context_region:
            continue
        contexts.append(context)
    return contexts


def _surface_transition_region_surface_contexts(applied_section_set) -> dict[str, str]:
    if applied_section_set is None:
        return {}
    groups: dict[str, list[object]] = {}
    for section in _station_ordered_applied_sections(applied_section_set):
        region_id = section_region_id(section)
        if not region_id:
            continue
        groups.setdefault(region_id, []).append(section)
    return {region_id: _region_surface_context_summary(sections) for region_id, sections in groups.items()}


def _region_surface_context_summary(sections: list[object]) -> str:
    if not sections:
        return "surface:missing"
    left_values = [section_float_attr(section, "surface_left_width") for section in sections]
    right_values = [section_float_attr(section, "surface_right_width") for section in sections]
    subgrade_values = [section_float_attr(section, "subgrade_depth") for section in sections]
    daylight_values = [
        max(section_float_attr(section, "daylight_left_width"), section_float_attr(section, "daylight_right_width"))
        for section in sections
    ]
    role_names = sorted(
        {
            role
            for section in sections
            for role, count in surface_point_role_counts(section).items()
            if count
        }
    )
    return (
        f"FG L {_range_summary(left_values)} / R {_range_summary(right_values)}; "
        f"SG {_range_summary(subgrade_values)}; DL {_range_summary(daylight_values)}; "
        f"roles {unique_join(role_names, max_items=2) or '-'}"
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
    ordered = sorted(list(sections or []), key=lambda section: section_station(section))
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = section_station(first)
        second_station = section_station(second)
        if min(first_station, second_station) - 1.0e-9 <= float(station) <= max(first_station, second_station) + 1.0e-9:
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (float(station) - first_station) / (second_station - first_station)
            return _interpolate_section_frame_point(getattr(first, "frame", None), getattr(second, "frame", None), ratio, z_offset=z_offset)
    nearest = min(ordered, key=lambda section: abs(section_station(section) - float(station)))
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
    drainage_summary = unique_join(drainage_refs)
    route_summary = unique_join(flow_route_refs)
    if drainage_summary:
        summary_parts.append(drainage_summary)
    if route_summary:
        summary_parts.append(f"routes: {route_summary}")
    if ditch_count:
        summary_parts.append(f"ditch points: {ditch_count}")
    return "; ".join(summary_parts) if summary_parts else "-"


def _region_group_intersection_summary(source_row, sections: list[object], *, intersection_model=None) -> str:
    source_ref = str(getattr(source_row, "intersection_ref", "") or "").strip() if source_row is not None else ""
    active_refs = unique_refs(
        [
            str(getattr(section, "active_intersection_id", "") or "")
            for section in list(sections or [])
            if str(getattr(section, "active_intersection_id", "") or "").strip()
        ]
    )
    leg_roles = unique_refs(
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
    if source_ref and intersection_model is not None and intersection_row_by_id(intersection_model, source_ref) is None:
        parts.append("unlinked")
    return " | ".join(part for part in parts if part) or "-"


def _region_group_surface_status(sections: list[object]) -> str:
    if not sections:
        return "missing"
    return "ready" if all(getattr(section, "frame", None) is not None for section in sections) else "warn"


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
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
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
        if section_region_id(section) == region_id
        and start - 1.0e-6 <= section_station(section) <= end + 1.0e-6
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
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
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
    supplemental_sampling_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sampling_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sampling_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
):
    if document is None or corridor_model is None or applied_section_set is None:
        return None
    region_id = str(row.get("region_id", "") or "")
    start = float(row.get("station_start", 0.0) or 0.0)
    end = float(row.get("station_end", start) or start)
    role = str(surface_role_spec.get("role", "") or "")
    object_name = str(surface_role_spec.get("object_name", "") or "")
    surface_id = f"{str(getattr(corridor_model, 'corridor_id', '') or 'corridor:main')}:region:{_safe_region_token(region_id)}:{role}"
    try:
        effective_supplemental_sampling_enabled = _build_corridor_effective_hidden_supplemental_sampling_enabled(
            document,
            applied_section_set=applied_section_set,
            requested=supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
        )
        supplemental_frame_resolver = _corridor_supplemental_frame_resolver(document) if effective_supplemental_sampling_enabled else None
        request = CorridorDesignSurfaceGeometryRequest(
            project_id=_project_id(project or find_project(document)),
            corridor=corridor_model,
            applied_section_set=applied_section_set,
            surface_id=surface_id,
            supplemental_sampling_enabled=effective_supplemental_sampling_enabled,
            supplemental_sampling_max_spacing=supplemental_sampling_max_spacing,
            supplemental_sampling_tangent_delta_deg=supplemental_sampling_tangent_delta_deg,
            supplemental_sampling_chord_deviation=supplemental_sampling_chord_deviation,
            supplemental_frame_resolver=supplemental_frame_resolver,
            surface_transition_model=None,
        )
        if role == "daylight":
            request = replace(request, existing_ground_surface=_resolve_corridor_existing_ground_tin_surface(document))
        build_result = CorridorSurfaceOrchestrationService().build(
            CorridorSurfaceGeometryBuildRequest(
                surface_role=role,
                geometry_request=request,
            )
        )
        if build_result.status != "ready" or build_result.tin_surface is None:
            return None
        tin_surface = build_result.tin_surface
    except Exception:
        return None
    # the corridor surfaces of a Region lose their triangles inside an intersection, as the full ones do
    if str(role or "").strip().lower() in {"design", "subgrade", "daylight"}:
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
    try:
        obj.Label = f"Corridor Region {str(surface_role_spec.get('label_role', role) or role).title()} - {region_id}"
    except Exception:
        pass
    try:
        route_object_to_project_tree(project or find_project(document), obj)
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
    ordered = sorted(list(sections or []), key=section_station)
    all_ordered = sorted(list(all_sections or ordered), key=section_station)
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
        station = float(getattr(frame, "station", section_station(section)) or section_station(section)) + length
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
    return any(abs(section_station(section) - float(station)) <= float(tolerance) for section in list(sections or []))


def _unique_sections_by_station(sections: list[object]) -> list[object]:
    rows: dict[float, object] = {}
    for section in sorted(list(sections or []), key=lambda item: (section_station(item), str(getattr(item, "applied_section_id", "") or ""))):
        rows[round(section_station(section), 6)] = section
    return [rows[key] for key in sorted(rows)]


def _region_boundary_virtual_section(
    sections: list[object],
    station: float,
    *,
    region_id: str,
    boundary_role: str,
):
    ordered = sorted([section for section in list(sections or []) if getattr(section, "frame", None) is not None], key=section_station)
    if not ordered:
        return None
    value = float(station)
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = section_station(first)
        second_station = section_station(second)
        low = min(first_station, second_station)
        high = max(first_station, second_station)
        if low - 1.0e-6 <= value <= high + 1.0e-6:
            ratio = 0.0 if abs(second_station - first_station) <= 1.0e-9 else (value - first_station) / (second_station - first_station)
            return _interpolate_region_boundary_section(first, second, ratio, station=value, region_id=region_id, boundary_role=boundary_role)
    nearest = min(ordered, key=lambda section: abs(section_station(section) - value))
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

        delta = float(station) - section_station(section)
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
    return first if abs(section_station(first) - float(station)) <= abs(section_station(second) - float(station)) else second


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
    ordered = sorted(list(sections or []), key=section_station)
    return AppliedSectionSet(
        schema_version=int(getattr(applied_section_set, "schema_version", 1) or 1),
        project_id=str(getattr(applied_section_set, "project_id", "") or "corridorroad-v1"),
        applied_section_set_id=f"{applied_id}:region:{safe}",
        corridor_id=str(getattr(applied_section_set, "corridor_id", "") or "corridor:main"),
        alignment_id=str(getattr(applied_section_set, "alignment_id", "") or ""),
        station_rows=[
            AppliedSectionStationRow(
                station_row_id=f"{applied_id}:region:{safe}:station:{index + 1}",
                station=section_station(section),
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


def _region_surface_role_specs(region_id: str) -> list[dict[str, object]]:
    return [
        {
            "role": "design",
            "object_name": _region_surface_preview_object_name(region_id, "design"),
            "label_prefix": "Corridor Region Design Surface",
            "label_role": "design surface",
            "style_role": "edited",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET,
        },
        {
            "role": "subgrade",
            "object_name": _region_surface_preview_object_name(region_id, "subgrade"),
            "label_prefix": "Corridor Region Subgrade Surface",
            "label_role": "subgrade surface",
            "style_role": "subgrade",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET + 0.08,
        },
        {
            "role": "daylight",
            "object_name": _region_surface_preview_object_name(region_id, "daylight"),
            "label_prefix": "Corridor Region Slope Surface",
            "label_role": "slope surface",
            "style_role": "daylight",
            "z_offset": REGION_SURFACE_DISPLAY_Z_OFFSET + 0.16,
        },
        {
            "role": "drainage",
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


def _drainage_review_context_label(row: dict[str, object]) -> str:
    context = str(row.get("context", "") or row.get("review_kind", "") or "").strip().lower()
    if context == "intersection_drainage":
        return "Intersection Drainage"
    return "Roadside Drainage"


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
    sections = sorted(list(getattr(applied, "sections", []) or []), key=lambda section: section_station(section)) if applied is not None else []
    shapes: list[object] = []
    route_refs: list[str] = []
    structure_refs: list[str] = []
    connection_point_refs: list[str] = []
    pipe_segment_count = 0
    station_span_count = 0
    skipped_segment_count = 0
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
                        skipped_segment_count += 1
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
                skipped_segment_count += 1
    if not shapes:
        return None
    obj = document.getObject("ReviewIssueDrainageFlowRoutes")
    if obj is None:
        obj = document.addObject("Part::Feature", "ReviewIssueDrainageFlowRoutes")
    try:
        obj.Shape = Part.makeCompound(shapes)
        obj.Label = "Drainage Flow Highlight"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_drainage_flow_review_highlight", error=error)
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
    _set_preview_integer_property(obj, "SkippedSegmentCount", skipped_segment_count)
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
        route_object_to_project_tree(find_project(document), obj)
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
    ordered = sorted(list(sections or []), key=lambda section: section_station(section))
    for index in range(len(ordered) - 1):
        first = ordered[index]
        second = ordered[index + 1]
        first_station = section_station(first)
        second_station = section_station(second)
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
    nearest = min(ordered, key=lambda section: abs(section_station(section) - float(station)))
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
        station = section_station(section)
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
        route_object_to_project_tree(find_project(document), obj)
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
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_drainage_review_highlight_compound", error=error)
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
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_drainage_review_point_marker", error=error)
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
    # Silence is the fallback mechanism here, not a hidden failure. A marker is
    # built as sphere plus stem, and degrades to a cross and then to a single
    # vertex below. The caller always receives at least one shape, so a skipped
    # primitive changes marker style only and loses no review information.
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
    # Last stage of the marker fallback chain described in
    # _point_sphere_marker_shapes. A dropped axis line degrades the cross, and
    # the vertex below is the final fallback, so silence is intended here.
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


def _surface_id(surface_model, surface_kind: str) -> str:
    for row in list(getattr(surface_model, "surface_rows", []) or []):
        if str(getattr(row, "surface_kind", "") or "") == surface_kind:
            return str(getattr(row, "surface_id", "") or "")
    return ""


def _roundabout_ownership_intrusion_summary(tin_surface: TINSurface | None, document=None) -> dict[str, object]:
    """Corridor triangles left inside a roundabout: centroid inside the intersection kernel's
    boundary and outside its central island. Not applicable to other intersections."""

    result = _document_intersection_kernel_result(document)
    if tin_surface is None or result is None or result.kind != "roundabout" or not result.boundary_xyz:
        return {"status": "not_applicable", "tested": 0, "intrusion_count": 0, "intrusion_refs": [], "radius": 0.0, "intersection_id": ""}
    boundary = [(p[0], p[1]) for p in result.boundary_xyz]
    holes = [[(p[0], p[1]) for p in hole] for hole in result.boundary_holes_xyz]
    values = {value.name: value.value for value in result.resolved_values}
    radius = float(values.get("roundabout_inscribed_radius_m", 0.0) or 0.0) + float(values.get("roundabout_apron_width_m", 0.0) or 0.0)
    vertex_map = tin_surface.vertex_map()
    tested = 0
    intrusion_refs: list[str] = []
    for triangle in list(getattr(tin_surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            continue
        tested += 1
        centroid = (sum(float(v.x) for v in vertices) / 3.0, sum(float(v.y) for v in vertices) / 3.0)
        if xy_point_in_polygon(centroid, boundary) and not any(xy_point_in_polygon(centroid, hole) for hole in holes):
            intrusion_refs.append(str(getattr(triangle, "triangle_id", "") or ""))
    return {
        "status": "warning" if intrusion_refs else "ready",
        "tested": tested,
        "intrusion_count": len(intrusion_refs),
        "intrusion_refs": intrusion_refs,
        "radius": radius,
        "intersection_id": result.intersection_id,
    }


def _clip_tin_surface_by_roundabout_ownership(
    tin_surface: TINSurface | None,
    document=None,
    *,
    applied_section_set=None,
    surface_role: str,
) -> TINSurface | None:
    """A roundabout is clipped by its station spans like any other intersection; a surface the
    exclusion step already clipped loses nothing more."""

    return _clip_tin_surface_by_kernel_spans(tin_surface, document, applied_section_set=applied_section_set)


def _attach_roundabout_ownership_intrusion_metadata(obj, tin_surface: TINSurface | None, document=None, *, surface_role: str) -> None:
    """Record whether a corridor surface leaves triangles inside a roundabout (the kernel's
    boundary less its central island); the station-span clip should leave none."""

    summary = _roundabout_ownership_intrusion_summary(tin_surface, document)
    status = str(summary.get("status", "") or "not_applicable")
    _set_preview_property(obj, "RoundaboutOwnershipIntrusionStatus", status)
    _set_preview_property(obj, "RoundaboutOwnershipSurfaceRole", str(surface_role or ""))
    _set_preview_property(obj, "RoundaboutOwnershipBoundarySource", "intersection_kernel" if status != "not_applicable" else "")
    _set_preview_property(obj, "RoundaboutOwnershipIntersectionId", str(summary.get("intersection_id", "") or ""))
    _set_preview_integer_property(obj, "RoundaboutOwnershipTestedTriangleCount", int(summary.get("tested", 0) or 0))
    _set_preview_integer_property(obj, "RoundaboutOwnershipIntrusionTriangleCount", int(summary.get("intrusion_count", 0) or 0))
    _set_preview_string_list_property(
        obj,
        "RoundaboutOwnershipIntrusionTriangleRefs",
        [str(ref or "") for ref in list(summary.get("intrusion_refs", []) or [])[:50]],
    )
    _set_preview_float_property(obj, "RoundaboutOwnershipRadius", float(summary.get("radius", 0.0) or 0.0))
    action = (
        "Corridor triangles remain inside the roundabout: rebuild Applied Sections, then Build Parametric."
        if status == "warning"
        else "No action required."
        if status == "ready"
        else ""
    )
    _set_preview_property(obj, "RoundaboutOwnershipRecommendedAction", action)


_INTERSECTION_BOUNDARY_LOOP_AUDIT_CONSUMERS = (
    "intersection_surface",
    "design_surface",
    "intersection_slope_face_surface",
    "slope_face_surface",
    "intersection_tie_slope_surface",
)


def _clip_tin_surface_by_intersection_exclusion(
    surface,
    document,
    *,
    applied_section_set=None,
    source_applied_section_set=None,
    surface_role: str,
):
    """Drop each road's corridor triangles between its two intersection mouths."""

    return _clip_tin_surface_by_kernel_spans(surface, document, applied_section_set=source_applied_section_set or applied_section_set)


INTERSECTION_SHARED_BOUNDARY_GRAPH_ROLES = {
    "patch_to_design_surface",
    "patch_to_intersection_slope_face",
    "intersection_slope_face_to_design_surface",
    "intersection_slope_face_to_corridor_slope_face",
    "main_road_tie",
    "side_road_tie",
    "main_side_slope_face_tie",
    "curb_return_to_intersection_slope_face",
    "curb_return_bridge_to_intersection_slope_face",
    "intersection_tie_slope_transition_inner",
    "intersection_tie_slope_transition_outer",
    "intersection_tie_slope_start_cap",
    "intersection_tie_slope_end_cap",
    "roundabout_island_to_circulatory",
    "roundabout_circulatory_to_apron",
    "roundabout_apron_to_slope_face",
    "roundabout_entry_exit_connector_boundary",
    "roundabout_approach_clip_to_design_surface",
    "roundabout_subgrade_clip_to_subgrade_surface",
    "roundabout_subgrade_to_approach_subgrade",
    "roundabout_slope_handoff_to_slope_face_surface",
    "roundabout_slope_to_corridor_slope_face",
    "intersection_upper_slope_face_panel_inner",
    "intersection_upper_slope_face_panel_outer",
    "intersection_upper_slope_face_panel_left_cap",
    "intersection_upper_slope_face_panel_right_cap",
    "upper_transition_internal_seam",
    "cell_closure_internal_seam",
}


def corridor_general_shared_breakline_result(applied_section_set) -> SharedBreaklineResult:
    """Build corridor-wide shared breakline rows from ordinary Applied Section link roles."""

    project_id = str(getattr(applied_section_set, "project_id", "") or "")
    corridor_id = str(getattr(applied_section_set, "corridor_id", "") or "corridor")
    result_id = f"shared-breakline:corridor:{corridor_id or 'main'}"
    point_rows: list[SharedBreaklinePointRow] = []
    breakline_rows: list[SharedBreaklineRow] = []
    diagnostics: list[str] = []
    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, object]]] = {}
    for section_sequence, section in enumerate(_ordered_applied_sections_for_breaklines(applied_section_set)):
        if str(getattr(section, "active_intersection_id", "") or ""):
            continue
        station = float(getattr(section, "station", 0.0) or 0.0)
        alignment_ref = str(getattr(section, "alignment_id", "") or "")
        region_ref = str(getattr(section, "region_id", "") or "")
        _append_slope_face_applied_section_breakline_group_entries(
            groups,
            section=section,
            station=station,
            alignment_ref=alignment_ref,
            region_ref=region_ref,
            section_sequence=section_sequence,
        )
        point_lookup = _applied_section_subassembly_point_lookup(section)
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            surface_role = _normal_shared_breakline_surface_role(getattr(link, "surface_role", ""))
            if surface_role not in {"design_surface", "slope_face_surface", "drainage_surface"}:
                continue
            if surface_role == "slope_face_surface":
                continue
            for endpoint_kind, point_ref in (("start", getattr(link, "start_point_ref", "")), ("end", getattr(link, "end_point_ref", ""))):
                point = point_lookup.get(str(point_ref or ""))
                if point is None:
                    diagnostics.append(f"missing_link_point:{getattr(section, 'applied_section_id', '')}:{getattr(link, 'link_id', '')}:{point_ref}")
                    continue
                point_code = str(getattr(point, "point_code", "") or point_ref or endpoint_kind)
                side = str(getattr(point, "side", "") or _subassembly_side_for_ref(section, getattr(link, "subassembly_ref", "")) or "")
                breakline_role = _general_breakline_role_for_link(link, endpoint_kind=endpoint_kind)
                key = (
                    alignment_ref,
                    region_ref,
                    surface_role,
                    breakline_role,
                    side,
                    f"{str(getattr(link, 'subassembly_ref', '') or '')}:{point_code}:{endpoint_kind}",
                )
                groups.setdefault(key, []).append(
                    {
                        "section": section,
                        "link": link,
                        "point": point,
                        "station": station,
                        "alignment_ref": alignment_ref,
                        "region_ref": region_ref,
                        "side": side,
                    }
                )
    breakline_index = 1
    for _index, (key, entries) in enumerate(sorted(groups.items(), key=lambda item: item[0]), start=1):
        ordered = sorted(entries, key=lambda entry: float(entry.get("station", 0.0) or 0.0))
        alignment_ref, region_ref, surface_role, breakline_role, side, endpoint_key = key
        safe_role = _safe_breakline_id_part(breakline_role)
        safe_endpoint = _safe_breakline_id_part(endpoint_key)
        for run_entries in _contiguous_shared_breakline_entry_runs(ordered):
            if len(run_entries) < 2:
                continue
            breakline_id = f"{result_id}:{safe_role}:{breakline_index}:{safe_endpoint}"
            breakline_index += 1
            refs: list[str] = []
            for point_index, entry in enumerate(run_entries):
                point = entry["point"]
                section = entry["section"]
                point_id = f"{breakline_id}:p{point_index + 1}"
                refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=breakline_id,
                        sequence=point_index,
                        x=float(getattr(point, "x", 0.0) or 0.0),
                        y=float(getattr(point, "y", 0.0) or 0.0),
                        z=float(getattr(point, "z", 0.0) or 0.0),
                        station=float(entry.get("station", 0.0) or 0.0),
                        offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                        source_point_ref=f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                        notes=str(entry.get("source_note", "") or "corridor-wide shared breakline from Applied Section subassembly link endpoint"),
                    )
                )
            consumer = _general_breakline_consumer_for_surface_role(surface_role)
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="corridor",
                    domain_ref=corridor_id,
                    breakline_role=breakline_role,
                    source_contract_refs=tuple(
                        _unique_text_values(
                            [
                                *[
                                    _shared_breakline_entry_source_ref(entry)
                                    for entry in run_entries
                                ],
                                *[
                                    ref
                                    for entry in run_entries
                                    for ref in _applied_section_profile_source_refs(entry["section"])
                                ],
                            ]
                        )
                    ),
                    consumer_refs=(consumer,),
                    from_output_role=consumer,
                    to_output_role=consumer,
                    point_refs=tuple(refs),
                    station_start=float(run_entries[0].get("station", 0.0) or 0.0),
                    station_end=float(run_entries[-1].get("station", 0.0) or 0.0),
                    alignment_ref=alignment_ref,
                    side=side,
                    material_role=surface_role,
                    source_status="ready",
                    handoff_target="applied_sections",
                    notes=f"Ordinary corridor breakline for {surface_role}; region={region_ref}; endpoint={endpoint_key}; source={_shared_breakline_entry_source_mode(run_entries)}",
                )
            )
    status = "ready" if breakline_rows else "missing"
    if not breakline_rows and not diagnostics:
        diagnostics.append("corridor_shared_breakline_rows_missing")
    return SharedBreaklineResult(
        schema_version=1,
        project_id=project_id,
        breakline_result_id=result_id,
        domain_kind="corridor",
        domain_ref=corridor_id,
        status=status,
        breakline_count=len(breakline_rows),
        ready_count=len(breakline_rows),
        warning_count=0,
        error_count=0,
        diagnostic_rows=diagnostics,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )


def _applied_section_profile_source_refs(section) -> list[str]:
    refs: list[str] = []
    for attr in ("profile_id", "active_profile_id", "profile_ref"):
        ref = str(getattr(section, attr, "") or "").strip()
        if ref:
            refs.append(ref)
    frame = getattr(section, "frame", None)
    if frame is not None:
        for attr in ("active_profile_segment_start_id", "active_profile_segment_end_id", "active_vertical_curve_id"):
            ref = str(getattr(frame, attr, "") or "").strip()
            if ref:
                refs.append(ref)
    return _unique_text_values(refs)


def _append_slope_face_applied_section_breakline_group_entries(
    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, object]]],
    *,
    section,
    station: float,
    alignment_ref: str,
    region_ref: str,
    section_sequence: int,
) -> None:
    for side in ("left", "right"):
        rows = _applied_section_slope_face_boundary_points(section, side_label=side)
        if len(rows) < 2:
            continue
        for slot in _applied_section_slope_face_breakline_slots(rows, side_label=side):
            point = slot["point"]
            breakline_role = str(slot["breakline_role"])
            endpoint_key = str(slot["endpoint_key"])
            key = (
                alignment_ref,
                region_ref,
                "slope_face_surface",
                breakline_role,
                side,
                endpoint_key,
            )
            groups.setdefault(key, []).append(
                {
                    "section": section,
                    "link": None,
                    "point": point,
                    "station": station,
                    "alignment_ref": alignment_ref,
                    "region_ref": region_ref,
                    "side": side,
                    "source_mode": "applied_section_side_slope_point_rows",
                    "source_note": "corridor-wide shared breakline from Applied Section side slope boundary point",
                    "source_section_sequence": int(section_sequence),
                }
            )


def _contiguous_shared_breakline_entry_runs(entries: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    ordered = list(entries or [])
    if len(ordered) < 2:
        return [ordered] if ordered else []
    if not any("source_section_sequence" in entry for entry in ordered):
        return [ordered]
    runs: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    previous_sequence: int | None = None
    for entry in ordered:
        sequence_value = entry.get("source_section_sequence")
        try:
            sequence = int(sequence_value)
        except Exception:
            sequence = None
        if (
            current
            and sequence is not None
            and previous_sequence is not None
            and sequence != previous_sequence + 1
        ):
            runs.append(current)
            current = []
        current.append(entry)
        previous_sequence = sequence
    if current:
        runs.append(current)
    return runs


def _applied_section_slope_face_breakline_slots(rows: list[object], *, side_label: str) -> list[dict[str, object]]:
    """Return stable shared-breakline slots for an AppliedSection side slope.

    Internal side-slope points can appear/disappear as supplemental sampling,
    terrain daylight, or intersection clipping changes.  Shared breaklines must
    therefore follow stable boundary semantics instead of raw point indices.
    """

    points = list(rows or [])
    if len(points) < 2:
        return []
    side = str(side_label or "").strip().lower() or "side"
    slots: list[dict[str, object]] = []
    inner = points[0]
    outer = points[-1]
    slots.append(
        {
            "point": inner,
            "breakline_role": "shoulder_to_side_slope",
            "endpoint_key": f"applied-section-side-slope:{side}:inner:{_applied_section_slope_face_slot_role(inner)}",
        }
    )
    slots.append(
        {
            "point": outer,
            "breakline_role": "side_slope_to_daylight",
            "endpoint_key": f"applied-section-side-slope:{side}:outer:{_applied_section_slope_face_slot_role(outer)}",
        }
    )
    return slots


def _applied_section_slope_face_slot_role(point) -> str:
    role = str(getattr(point, "point_role", "") or "").strip()
    if role in {"side_slope_surface", "bench_surface", "daylight_marker"}:
        return role
    return "slope_face_point"


def _applied_section_slope_face_boundary_points(section, *, side_label: str) -> list[object]:
    side = str(side_label or "").strip().lower()
    rows = []
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        point_side = str(getattr(point, "side", "") or "").strip().lower()
        point_id = str(getattr(point, "point_id", "") or "").strip().lower()
        id_matches_side = f":{side}" in point_id or point_id.startswith(f"{side}:") or point_id.endswith(f":{side}")
        offset_matches_side = (side == "left" and offset >= -1.0e-9) or (side == "right" and offset <= 1.0e-9)
        if point_side and point_side != side:
            continue
        if not point_side and not id_matches_side and not offset_matches_side:
            continue
        rows.append(point)
    if side == "left":
        rows.sort(key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0), str(getattr(point, "point_id", "") or "")))
    else:
        rows.sort(key=lambda point: (-float(getattr(point, "lateral_offset", 0.0) or 0.0), str(getattr(point, "point_id", "") or "")))
    return rows


def _shared_breakline_entry_source_ref(entry: dict[str, object]) -> str:
    section = entry.get("section")
    link = entry.get("link")
    point = entry.get("point")
    if link is not None:
        return f"{getattr(section, 'applied_section_id', '')}:{getattr(link, 'link_id', '')}"
    return f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}"


def _shared_breakline_entry_source_mode(entries: list[dict[str, object]]) -> str:
    modes = _unique_text_values(str(entry.get("source_mode", "") or "subassembly_link_rows") for entry in list(entries or []))
    return ",".join(modes) if modes else "subassembly_link_rows"


def combined_shared_breakline_result(*results) -> SharedBreaklineResult | None:
    """Combine multiple SharedBreaklineResult values for one preview/audit surface."""

    clean = [result for result in list(results or []) if result is not None]
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    first = clean[0]
    breakline_rows: list[SharedBreaklineRow] = []
    point_rows: list[SharedBreaklinePointRow] = []
    diagnostics: list[str] = []
    for result in clean:
        breakline_rows.extend(list(getattr(result, "breakline_rows", []) or []))
        point_rows.extend(list(getattr(result, "point_rows", []) or []))
        diagnostics.extend(str(row) for row in list(getattr(result, "diagnostic_rows", []) or []) if str(row))
    error_count = sum(int(getattr(result, "error_count", 0) or 0) for result in clean)
    warning_count = sum(int(getattr(result, "warning_count", 0) or 0) for result in clean)
    ready_count = sum(int(getattr(result, "ready_count", 0) or 0) for result in clean)
    status = "ready" if breakline_rows and error_count == 0 else "missing" if not breakline_rows else "warning"
    return SharedBreaklineResult(
        schema_version=1,
        project_id=str(getattr(first, "project_id", "") or ""),
        breakline_result_id="shared-breakline:combined:" + ",".join(str(getattr(result, "breakline_result_id", "") or "") for result in clean),
        domain_kind="combined",
        domain_ref=",".join(str(getattr(result, "domain_ref", "") or "") for result in clean if str(getattr(result, "domain_ref", "") or "")),
        status=status,
        breakline_count=len(breakline_rows),
        ready_count=ready_count,
        warning_count=warning_count,
        error_count=error_count,
        diagnostic_rows=diagnostics,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )


def corridor_region_transition_shared_breakline_result(applied_section_set) -> SharedBreaklineResult:
    """Build shared breaklines for ordinary corridor Region start/end boundaries."""

    project_id = str(getattr(applied_section_set, "project_id", "") or "")
    corridor_id = str(getattr(applied_section_set, "corridor_id", "") or "corridor")
    result_id = f"shared-breakline:region-transition:{corridor_id or 'main'}"
    point_rows: list[SharedBreaklinePointRow] = []
    breakline_rows: list[SharedBreaklineRow] = []
    grouped: dict[tuple[str, str], list[object]] = {}
    for section in _ordered_applied_sections_for_breaklines(applied_section_set):
        if str(getattr(section, "active_intersection_id", "") or ""):
            continue
        key = (str(getattr(section, "alignment_id", "") or ""), str(getattr(section, "region_id", "") or ""))
        grouped.setdefault(key, []).append(section)
    for group_index, ((alignment_ref, region_ref), sections) in enumerate(sorted(grouped.items(), key=lambda item: item[0]), start=1):
        ordered_sections = sorted(sections, key=lambda section: float(getattr(section, "station", 0.0) or 0.0))
        for boundary_kind, section in (("region_start_boundary", ordered_sections[0]), ("region_end_boundary", ordered_sections[-1])):
            role_points = _section_surface_role_boundary_points(section)
            for surface_role, points in sorted(role_points.items()):
                if len(points) < 2:
                    continue
                consumer = _general_breakline_consumer_for_surface_role(surface_role)
                safe_role = _safe_breakline_id_part(boundary_kind)
                safe_surface = _safe_breakline_id_part(surface_role)
                breakline_id = f"{result_id}:{safe_role}:{group_index}:{safe_surface}"
                refs: list[str] = []
                for point_index, point in enumerate(points):
                    point_id = f"{breakline_id}:p{point_index + 1}"
                    refs.append(point_id)
                    point_rows.append(
                        SharedBreaklinePointRow(
                            point_id=point_id,
                            breakline_ref=breakline_id,
                            sequence=point_index,
                            x=float(getattr(point, "x", 0.0) or 0.0),
                            y=float(getattr(point, "y", 0.0) or 0.0),
                            z=float(getattr(point, "z", 0.0) or 0.0),
                            station=float(getattr(section, "station", 0.0) or 0.0),
                            offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                            source_point_ref=f"{getattr(section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                            notes="corridor Region boundary shared breakline from Applied Section surface-role endpoints",
                        )
                    )
                breakline_rows.append(
                    SharedBreaklineRow(
                        breakline_id=breakline_id,
                        domain_kind="region_transition",
                        domain_ref=region_ref,
                        breakline_role=boundary_kind,
                        source_contract_refs=(str(getattr(section, "applied_section_id", "") or ""),),
                        consumer_refs=(consumer,),
                        from_output_role=consumer,
                        to_output_role=consumer,
                        point_refs=tuple(refs),
                        station_start=float(getattr(section, "station", 0.0) or 0.0),
                        station_end=float(getattr(section, "station", 0.0) or 0.0),
                        alignment_ref=alignment_ref,
                        side="cross_section",
                        material_role=surface_role,
                        source_status="ready",
                        handoff_target="region_model",
                        notes=f"Region {boundary_kind}; region={region_ref}; surface={surface_role}",
                    )
                )
    _append_region_assembly_change_breaklines(
        applied_section_set=applied_section_set,
        result_id=result_id,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )
    status = "ready" if breakline_rows else "missing"
    diagnostics = [] if breakline_rows else ["region_transition_shared_breakline_rows_missing"]
    return SharedBreaklineResult(
        schema_version=1,
        project_id=project_id,
        breakline_result_id=result_id,
        domain_kind="region_transition",
        domain_ref=corridor_id,
        status=status,
        breakline_count=len(breakline_rows),
        ready_count=len(breakline_rows),
        warning_count=0,
        error_count=0,
        diagnostic_rows=diagnostics,
        breakline_rows=breakline_rows,
        point_rows=point_rows,
    )


def _append_region_assembly_change_breaklines(
    *,
    applied_section_set,
    result_id: str,
    breakline_rows: list[SharedBreaklineRow],
    point_rows: list[SharedBreaklinePointRow],
) -> None:
    sections_by_alignment: dict[str, list[object]] = {}
    for section in _ordered_applied_sections_for_breaklines(applied_section_set):
        if str(getattr(section, "active_intersection_id", "") or ""):
            continue
        alignment_ref = str(getattr(section, "alignment_id", "") or "")
        sections_by_alignment.setdefault(alignment_ref, []).append(section)
    next_index = len(breakline_rows) + 1
    for alignment_ref, sections in sorted(sections_by_alignment.items()):
        ordered = sorted(
            sections,
            key=lambda section: (
                float(getattr(section, "station", 0.0) or 0.0),
                str(getattr(section, "region_id", "") or ""),
                str(getattr(section, "applied_section_id", "") or ""),
            ),
        )
        for previous, current in zip(ordered[:-1], ordered[1:]):
            previous_region = str(getattr(previous, "region_id", "") or "")
            current_region = str(getattr(current, "region_id", "") or "")
            if not previous_region or previous_region == current_region:
                continue
            previous_assembly = str(getattr(previous, "assembly_id", "") or "")
            current_assembly = str(getattr(current, "assembly_id", "") or "")
            if not previous_assembly or not current_assembly or previous_assembly == current_assembly:
                continue
            boundary_section = current
            role_points = _section_surface_role_boundary_points(boundary_section)
            for surface_role, points in sorted(role_points.items()):
                if len(points) < 2:
                    continue
                consumer = _general_breakline_consumer_for_surface_role(surface_role)
                safe_surface = _safe_breakline_id_part(surface_role)
                breakline_id = f"{result_id}:assembly_change_boundary:{next_index}:{safe_surface}"
                next_index += 1
                refs: list[str] = []
                for point_index, point in enumerate(points):
                    point_id = f"{breakline_id}:p{point_index + 1}"
                    refs.append(point_id)
                    point_rows.append(
                        SharedBreaklinePointRow(
                            point_id=point_id,
                            breakline_ref=breakline_id,
                            sequence=point_index,
                            x=float(getattr(point, "x", 0.0) or 0.0),
                            y=float(getattr(point, "y", 0.0) or 0.0),
                            z=float(getattr(point, "z", 0.0) or 0.0),
                            station=float(getattr(boundary_section, "station", 0.0) or 0.0),
                            offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                            source_point_ref=f"{getattr(boundary_section, 'applied_section_id', '')}:{getattr(point, 'point_id', '')}",
                            notes="corridor Region assembly-change shared breakline from Applied Section surface-role endpoints",
                        )
                    )
                breakline_rows.append(
                    SharedBreaklineRow(
                        breakline_id=breakline_id,
                        domain_kind="region_transition",
                        domain_ref=f"{previous_region}->{current_region}",
                        breakline_role="assembly_change_boundary",
                        source_contract_refs=(
                            str(getattr(previous, "applied_section_id", "") or ""),
                            str(getattr(current, "applied_section_id", "") or ""),
                            previous_assembly,
                            current_assembly,
                        ),
                        consumer_refs=(consumer,),
                        from_output_role=consumer,
                        to_output_role=consumer,
                        point_refs=tuple(refs),
                        station_start=float(getattr(boundary_section, "station", 0.0) or 0.0),
                        station_end=float(getattr(boundary_section, "station", 0.0) or 0.0),
                        alignment_ref=alignment_ref,
                        side="cross_section",
                        material_role=surface_role,
                        source_status="ready",
                        handoff_target="region_assembly_change",
                        notes=(
                            "Region assembly_change_boundary; "
                            f"from_region={previous_region}; to_region={current_region}; "
                            f"from_assembly={previous_assembly}; to_assembly={current_assembly}; surface={surface_role}"
                        ),
                    )
                )


def _section_surface_role_boundary_points(section) -> dict[str, list[object]]:
    point_lookup = _applied_section_subassembly_point_lookup(section)
    grouped: dict[str, dict[str, object]] = {}
    for link in list(getattr(section, "subassembly_link_rows", []) or []):
        surface_role = _normal_shared_breakline_surface_role(getattr(link, "surface_role", ""))
        if surface_role not in {"design_surface", "slope_face_surface", "drainage_surface"}:
            continue
        role_points = grouped.setdefault(surface_role, {})
        for point_ref in (getattr(link, "start_point_ref", ""), getattr(link, "end_point_ref", "")):
            point = point_lookup.get(str(point_ref or ""))
            if point is None:
                continue
            key = f"{round(float(getattr(point, 'x', 0.0) or 0.0), 6)}:{round(float(getattr(point, 'y', 0.0) or 0.0), 6)}:{round(float(getattr(point, 'z', 0.0) or 0.0), 6)}"
            role_points[key] = point
    output: dict[str, list[object]] = {}
    for surface_role, points in grouped.items():
        output[surface_role] = sorted(
            points.values(),
            key=lambda point: (
                float(getattr(point, "lateral_offset", 0.0) or 0.0),
                str(getattr(point, "point_id", "") or ""),
            ),
        )
    return output


def _ordered_applied_sections_for_breaklines(applied_section_set) -> list[object]:
    return sorted(
        list(getattr(applied_section_set, "sections", []) or []),
        key=lambda section: (
            str(getattr(section, "alignment_id", "") or ""),
            str(getattr(section, "region_id", "") or ""),
            float(getattr(section, "station", 0.0) or 0.0),
            str(getattr(section, "applied_section_id", "") or ""),
        ),
    )


def _applied_section_subassembly_point_lookup(section) -> dict[str, object]:
    return {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(section, "subassembly_point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }


def _subassembly_side_for_ref(section, subassembly_ref: object) -> str:
    target = str(subassembly_ref or "")
    for row in list(getattr(section, "subassembly_rows", []) or []):
        if str(getattr(row, "subassembly_id", "") or "") == target:
            return str(getattr(row, "side", "") or "")
    return ""


def _normal_shared_breakline_surface_role(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"design", "fg", "fg_surface", "finished_grade", "finished-grade"}:
        return "design_surface"
    if text in {"slope_face", "side_slope", "side-slope", "daylight", "daylight_surface"}:
        return "slope_face_surface"
    if text in {"drainage", "ditch", "gutter"}:
        return "drainage_surface"
    return text


def _general_breakline_consumer_for_surface_role(surface_role: str) -> str:
    if surface_role == "design_surface":
        return "design_surface"
    if surface_role == "slope_face_surface":
        return "slope_face_surface"
    if surface_role == "drainage_surface":
        return "drainage_surface"
    return str(surface_role or "")


def _shared_breakline_consumer_for_review_role(review_role: str) -> str:
    role = str(review_role or "").strip().lower()
    return {
        "design": "design_surface",
        "intersection": "intersection_surface",
        "subgrade": "subgrade_surface",
        "daylight": "slope_face_surface",
        "intersection_slope": "intersection_slope_face_surface",
        "intersection_tie_slope": "intersection_tie_slope",
        "drainage": "drainage_surface",
    }.get(role, "")


def _general_breakline_role_for_link(link, *, endpoint_kind: str) -> str:
    surface_role = _normal_shared_breakline_surface_role(getattr(link, "surface_role", ""))
    text = " ".join(
        [
            str(getattr(link, "link_code", "") or ""),
            str(getattr(link, "link_id", "") or ""),
            str(getattr(link, "subassembly_ref", "") or ""),
        ]
    ).lower()
    endpoint = str(endpoint_kind or "")
    if surface_role == "design_surface":
        if "shoulder" in text:
            return "lane_to_shoulder" if endpoint == "start" else "shoulder_edge"
        return "lane_to_lane" if endpoint == "start" else "lane_to_shoulder"
    if surface_role == "slope_face_surface":
        if endpoint == "start":
            return "shoulder_to_side_slope"
        return "side_slope_to_daylight"
    if surface_role == "drainage_surface":
        if "gutter" in text:
            return "corridor_gutter_handoff"
        return "corridor_ditch_handoff"
    return f"{surface_role}_boundary"


def _safe_breakline_id_part(value: object) -> str:
    text = str(value or "").strip()
    output = []
    for char in text:
        output.append(char if char.isalnum() or char in {"_", "-"} else "-")
    return "".join(output).strip("-") or "boundary"


def _shared_breakline_refs_for_consumer(shared_result, consumer_ref: str) -> list[str]:
    target = str(consumer_ref or "").strip()
    if shared_result is None or not target:
        return []
    return [
        str(getattr(row, "breakline_id", "") or "")
        for row in list(getattr(shared_result, "breakline_rows", []) or [])
        if target in {str(value or "").strip() for value in tuple(getattr(row, "consumer_refs", ()) or ())}
        and str(getattr(row, "breakline_id", "") or "")
    ]


def _attach_shared_breakline_preview_metadata(obj, shared_result, *, consumer_ref: str = "", audit=None) -> None:
    if obj is None or shared_result is None:
        return
    refs = _shared_breakline_refs_for_consumer(shared_result, consumer_ref) if consumer_ref else [
        str(getattr(row, "breakline_id", "") or "")
        for row in list(getattr(shared_result, "breakline_rows", []) or [])
        if str(getattr(row, "breakline_id", "") or "")
    ]
    _set_preview_property(obj, "SharedBreaklineResultId", str(getattr(shared_result, "breakline_result_id", "") or ""))
    _set_preview_property(obj, "SharedBreaklineStatus", str(getattr(shared_result, "status", "") or ""))
    _set_preview_integer_property(obj, "SharedBreaklineCount", len(refs))
    _set_preview_integer_property(obj, "SharedBreaklineGlobalCount", int(getattr(shared_result, "breakline_count", 0) or 0))
    _set_preview_integer_property(obj, "SharedBreaklineReadyCount", int(getattr(shared_result, "ready_count", 0) or 0))
    _set_preview_integer_property(obj, "SharedBreaklineWarningCount", int(getattr(shared_result, "warning_count", 0) or 0))
    _set_preview_integer_property(obj, "SharedBreaklineErrorCount", int(getattr(shared_result, "error_count", 0) or 0))
    _set_preview_integer_property(obj, "SharedBreaklineConsumedCount", len(refs))
    _set_preview_string_list_property(obj, "SharedBreaklineRefs", refs)
    _set_preview_property(obj, "SharedBreaklineMaterialSummary", _shared_breakline_material_summary(shared_result, refs))
    _set_preview_property(obj, "SharedBreaklineRoleSummary", _shared_breakline_role_summary(shared_result, refs))
    _set_preview_string_list_property(obj, "SharedBreaklineSegmentRows", shared_breakline_segment_rows(shared_result, refs))
    _set_preview_string_list_property(obj, "SharedBreaklineSolidBoundaryTraceRows", shared_breakline_solid_boundary_trace_rows(shared_result, refs))
    _set_preview_string_list_property(obj, "SharedBreaklineDiagnostics", list(getattr(shared_result, "diagnostic_rows", []) or []))
    if audit is not None:
        _attach_shared_breakline_audit_preview_metadata(obj, audit)


def _attach_shared_breakline_constraint_preview_metadata(obj, surface) -> None:
    if obj is None or surface is None:
        return
    _set_preview_property(obj, "SharedBreaklineConstraintMode", _tin_quality_text(surface, "shared_breakline_constraint_mode"))
    _set_preview_integer_property(
        obj,
        "SharedBreaklineConstraintSegmentCount",
        int(_tin_quality_float(surface, "shared_breakline_constraint_segment_count") or 0),
    )
    _set_preview_integer_property(
        obj,
        "SharedBreaklineConstraintEdgeCount",
        int(_tin_quality_float(surface, "shared_breakline_constraint_edge_count") or 0),
    )
    _set_preview_integer_property(
        obj,
        "SharedBreaklineConstraintVertexCount",
        int(_tin_quality_float(surface, "shared_breakline_constraint_vertex_count") or 0),
    )
    _set_preview_integer_property(
        obj,
        "SharedBreaklineBoundaryLoopConstraintSegmentCount",
        int(_tin_quality_float(surface, "shared_breakline_boundary_loop_constraint_segment_count") or 0),
    )
    _set_preview_integer_property(
        obj,
        "SharedBreaklineBoundaryLoopConstraintEdgeCount",
        int(_tin_quality_float(surface, "shared_breakline_boundary_loop_constraint_edge_count") or 0),
    )
    boundary_loop_constraint_refs = _tin_quality_text(surface, "shared_breakline_boundary_loop_constraint_refs")
    if boundary_loop_constraint_refs:
        _set_preview_string_list_property(
            obj,
            "SharedBreaklineBoundaryLoopConstraintRefs",
            [value.strip() for value in boundary_loop_constraint_refs.split(",") if value.strip()],
        )
    _set_preview_property(
        obj,
        "SharedBreaklineBoundaryLoopConstraintRoleSummary",
        _tin_quality_text(surface, "shared_breakline_boundary_loop_constraint_role_summary"),
    )
    _set_preview_integer_property(
        obj,
        "SharedBreaklineConstraintSnapCount",
        int(_tin_quality_float(surface, "shared_breakline_constraint_snap_count") or 0),
    )
    _set_preview_float_property(
        obj,
        "SharedBreaklineConstraintSnapMaxDistance",
        _tin_quality_float(surface, "shared_breakline_constraint_snap_max_distance"),
    )
    _set_preview_property(
        obj,
        "SharedBreaklineConstraintSnapDiagnostics",
        _tin_quality_text(surface, "shared_breakline_constraint_snap_diagnostics"),
    )


def _shared_breakline_material_summary(shared_result, refs: list[str] | None = None) -> str:
    return _shared_breakline_count_summary(shared_result, refs, attr_name="material_role")


def _shared_breakline_role_summary(shared_result, refs: list[str] | None = None) -> str:
    return _shared_breakline_count_summary(shared_result, refs, attr_name="breakline_role")


def _shared_breakline_count_summary(shared_result, refs: list[str] | None = None, *, attr_name: str) -> str:
    if shared_result is None:
        return ""
    wanted = {str(ref or "") for ref in list(refs or []) if str(ref or "")}
    counts: dict[str, int] = {}
    for row in list(getattr(shared_result, "breakline_rows", []) or []):
        breakline_id = str(getattr(row, "breakline_id", "") or "")
        if wanted and breakline_id not in wanted:
            continue
        key = str(getattr(row, attr_name, "") or "").strip()
        if not key:
            key = str(getattr(row, "breakline_role", "") or "unknown").strip() or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _shared_breakline_summary_keys(summary: str) -> list[str]:
    keys: list[str] = []
    for part in str(summary or "").split(","):
        key = str(part or "").strip().split("=", 1)[0].strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def shared_breakline_solid_boundary_trace_rows(shared_result, refs: list[str] | None = None) -> list[str]:
    """Serialize source traceability rows for downstream solid boundary consumers."""

    if shared_result is None:
        return []
    wanted = {str(ref or "") for ref in list(refs or []) if str(ref or "")}
    rows: list[str] = []
    for breakline in list(getattr(shared_result, "breakline_rows", []) or []):
        breakline_id = str(getattr(breakline, "breakline_id", "") or "")
        if not breakline_id or (wanted and breakline_id not in wanted):
            continue
        source_refs = ",".join(str(value or "") for value in tuple(getattr(breakline, "source_contract_refs", ()) or ()) if str(value or ""))
        consumer_refs = ",".join(str(value or "") for value in tuple(getattr(breakline, "consumer_refs", ()) or ()) if str(value or ""))
        values = [
            breakline_id,
            str(getattr(breakline, "breakline_role", "") or ""),
            str(getattr(breakline, "domain_kind", "") or ""),
            str(getattr(breakline, "domain_ref", "") or ""),
            str(getattr(breakline, "alignment_ref", "") or ""),
            f"{float(getattr(breakline, 'station_start', 0.0) or 0.0):.6f}",
            f"{float(getattr(breakline, 'station_end', 0.0) or 0.0):.6f}",
            str(getattr(breakline, "material_role", "") or ""),
            str(getattr(breakline, "source_status", "") or ""),
            source_refs,
            consumer_refs,
            str(getattr(breakline, "handoff_target", "") or ""),
        ]
        rows.append("|".join(value.replace("|", "_") for value in values))
    return rows


def _parse_shared_breakline_segment_row(row: object) -> dict[str, object] | None:
    parts = str(row or "").split("|")
    if len(parts) not in {10, 11, 12}:
        return None
    try:
        return {
            "breakline_id": parts[0],
            "role": parts[1],
            "status": parts[2],
            "segment_index": int(parts[3] or 0),
            "start": (float(parts[4]), float(parts[5]), float(parts[6])),
            "end": (float(parts[7]), float(parts[8]), float(parts[9])),
            "material": parts[10] if len(parts) > 10 else "",
            "consumers": parts[11] if len(parts) > 11 else "",
        }
    except Exception:
        return None


def show_shared_breakline_highlight(
    document=None,
    source_obj=None,
    *,
    role_filter: str = "",
    material_filter: str = "",
    consumer_filter: str = "",
    clip_to_source_bounds: bool = False,
):
    """Create/select a 3D highlight for the shared breakline rows stored on a preview object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if source_obj is None:
        raise RuntimeError("No shared breakline source object.")
    rows = [
        parsed
        for parsed in (_parse_shared_breakline_segment_row(row) for row in list(getattr(source_obj, "SharedBreaklineSegmentRows", []) or []))
        if parsed is not None
    ]
    role_text = str(role_filter or "").strip()
    material_text = str(material_filter or "").strip()
    if role_text:
        rows = [row for row in rows if str(row.get("role", "") or "") == role_text]
    if material_text:
        rows = [row for row in rows if str(row.get("material", "") or "") == material_text]
    consumer_text = str(consumer_filter or "").strip()
    if consumer_text:
        rows = [
            row
            for row in rows
            if consumer_text in {value.strip() for value in str(row.get("consumers", "") or "").split(",") if value.strip()}
        ]
    if clip_to_source_bounds:
        rows = _shared_breakline_rows_inside_source_bounds(source_obj, rows)
    if not rows:
        raise RuntimeError("Selected surface has no matching shared breakline geometry to highlight. Rebuild Build Parametric first or choose another role.")
    highlight = _create_shared_breakline_highlight(
        document=doc,
        source_obj=source_obj,
        rows=rows,
        role_filter=role_text,
        material_filter=material_text,
        consumer_filter=consumer_text,
        clip_to_source_bounds=clip_to_source_bounds,
    )
    if highlight is None:
        raise RuntimeError("Shared breakline highlight was not created.")
    _set_object_visibility(highlight, True)
    _select_and_fit_object(highlight)
    return highlight


def _shared_breakline_rows_inside_source_bounds(source_obj, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    bbox = None
    try:
        shape = getattr(source_obj, "Shape", None)
        bbox = getattr(shape, "BoundBox", None)
        if bbox is None or not bool(getattr(shape, "isValid", lambda: False)()):
            return list(rows or [])
    except Exception:
        return list(rows or [])
    try:
        xmin = float(getattr(bbox, "XMin", 0.0) or 0.0)
        xmax = float(getattr(bbox, "XMax", 0.0) or 0.0)
        ymin = float(getattr(bbox, "YMin", 0.0) or 0.0)
        ymax = float(getattr(bbox, "YMax", 0.0) or 0.0)
        zmin = float(getattr(bbox, "ZMin", 0.0) or 0.0)
        zmax = float(getattr(bbox, "ZMax", 0.0) or 0.0)
    except Exception:
        return list(rows or [])
    span = max(xmax - xmin, ymax - ymin, 1.0)
    margin = max(2.0, min(12.0, span * 0.15))
    z_margin = max(2.0, min(12.0, max(zmax - zmin, 1.0) * 0.25))

    def _point_inside(point: tuple[float, float, float]) -> bool:
        if len(point) < 3:
            return False
        x, y, z = float(point[0]), float(point[1]), float(point[2])
        return (
            xmin - margin <= x <= xmax + margin
            and ymin - margin <= y <= ymax + margin
            and zmin - z_margin <= z <= zmax + z_margin
        )

    filtered: list[dict[str, object]] = []
    for row in list(rows or []):
        start = tuple(row.get("start", ()) or ())
        end = tuple(row.get("end", ()) or ())
        if _point_inside(start) or _point_inside(end):
            filtered.append(row)
    return filtered


def _create_shared_breakline_highlight(
    *,
    document=None,
    source_obj=None,
    rows: list[dict[str, object]] | None = None,
    role_filter: str = "",
    material_filter: str = "",
    consumer_filter: str = "",
    clip_to_source_bounds: bool = False,
):
    if document is None:
        return None
    try:
        import FreeCAD as AppModule
        import Part
    except Exception:
        return None
    shapes: list[object] = []
    refs: list[str] = []
    z_lift = 0.02
    for row in list(rows or []):
        try:
            start = tuple(float(value) for value in row.get("start", ()))
            end = tuple(float(value) for value in row.get("end", ()))
            if len(start) != 3 or len(end) != 3:
                continue
            start_vec = AppModule.Vector(start[0], start[1], start[2] + z_lift)
            end_vec = AppModule.Vector(end[0], end[1], end[2] + z_lift)
            shapes.append(Part.makeLine(start_vec, end_vec))
            refs.append(str(row.get("breakline_id", "") or ""))
        except Exception:
            continue
    if not shapes:
        return None
    object_name = "ReviewSharedBreaklineHighlight"
    obj = document.getObject(object_name)
    if obj is None:
        obj = document.addObject("Part::Feature", object_name)
    try:
        obj.Shape = Part.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
        obj.Label = "Shared Breakline Highlight"
    except Exception as error:
        return _mark_preview_shape_failure(obj, preview_kind="create_shared_breakline_highlight", error=error)
    _set_preview_property(obj, "CRRecordKind", "v1_shared_breakline_highlight")
    _set_preview_property(obj, "V1ObjectType", "ReviewDiagnostic")
    _set_preview_property(obj, "DiagnosticKind", "shared_breakline_highlight")
    _set_preview_property(obj, "SourceObject", str(getattr(source_obj, "Name", "") or ""))
    _set_preview_property(obj, "SourceObjectLabel", str(getattr(source_obj, "Label", "") or ""))
    _set_preview_property(obj, "SharedBreaklineResultId", str(getattr(source_obj, "SharedBreaklineResultId", "") or ""))
    _set_preview_property(obj, "SharedBreaklineAuditStatus", str(getattr(source_obj, "SharedBreaklineAuditStatus", "") or ""))
    _set_preview_property(obj, "SharedBreaklineRoleFilter", str(role_filter or ""))
    _set_preview_property(obj, "SharedBreaklineMaterialFilter", str(material_filter or ""))
    _set_preview_property(obj, "SharedBreaklineConsumerFilter", str(consumer_filter or ""))
    _set_preview_property(obj, "SharedBreaklineClipToSourceBounds", "Yes" if bool(clip_to_source_bounds) else "No")
    _set_preview_string_list_property(obj, "SharedBreaklineRefs", _unique_text_values(refs))
    _set_preview_integer_property(obj, "SharedBreaklineSegmentCount", len(shapes))
    highlight_color = _shared_breakline_highlight_color(role_filter=role_filter, material_filter=material_filter)
    _set_preview_property(
        obj,
        "SharedBreaklineHighlightColor",
        ",".join(f"{float(value):.3f}" for value in highlight_color),
    )
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = True
            vobj.ShapeColor = highlight_color
            vobj.LineColor = highlight_color
            vobj.PointColor = highlight_color
            vobj.LineWidth = 11.0
            vobj.PointSize = 6.0
    except Exception:
        pass
    try:
        route_object_to_project_tree(find_project(document), obj)
    except Exception:
        pass
    try:
        document.recompute()
    except Exception:
        pass
    return obj


def _shared_breakline_highlight_color(*, role_filter: str = "", material_filter: str = "") -> tuple[float, float, float]:
    material = str(material_filter or "").strip().lower()
    role = str(role_filter or "").strip().lower()
    if role in {"lane_to_lane", "lane-to-lane"}:
        return (1.00, 0.88, 0.05)
    if role in {"lane_to_shoulder", "lane-to-shoulder", "shoulder_edge", "shoulder-edge"}:
        return (0.65, 1.00, 0.35)
    if role in {"shoulder_to_side_slope", "shoulder-to-side-slope", "side_slope_to_daylight", "side-slope-to-daylight"}:
        return (0.05, 0.95, 0.25)
    if role in {"corridor_gutter_handoff", "corridor-gutter-handoff", "corridor_ditch_handoff", "corridor-ditch-handoff"}:
        return (0.10, 0.55, 1.00)
    if material in {"pavement", "design_surface"}:
        return (1.00, 0.88, 0.05)
    if material == "shoulder":
        return (0.65, 1.00, 0.35)
    if material in {"side_slope", "slope_face_surface"}:
        return (0.05, 0.95, 0.25)
    if material == "drainage_surface" or "gutter" in role or "ditch" in role:
        return (0.10, 0.55, 1.00)
    if material == "curb_return" or "curb_return" in role or "curb-return" in role:
        return (1.00, 0.52, 0.05)
    if "patch_to_design" in role or "patch-to-design" in role:
        return (1.00, 0.88, 0.05)
    if "patch_to_slope_face" in role or "patch-to-slope-face" in role:
        return (0.05, 0.95, 0.25)
    return (0.00, 0.95, 1.00)


def _attach_shared_breakline_audit_preview_metadata(obj, audit) -> None:
    if obj is None or audit is None:
        return
    presentation = SharedBreaklineAuditPresentationMapper().map(audit)
    _set_preview_property(obj, "SharedBreaklineAuditStatus", presentation.status)
    _set_preview_integer_property(obj, "SharedBreaklineMissingConsumerCount", presentation.missing_consumer_count)
    _set_preview_integer_property(obj, "SharedBreaklineMismatchCount", presentation.mismatch_count)
    _set_preview_integer_property(obj, "SharedBreaklineGeometryMatchCount", presentation.geometry_match_count)
    _set_preview_integer_property(obj, "SharedBreaklineGeometryMismatchCount", presentation.geometry_mismatch_count)
    _set_preview_integer_property(obj, "SharedBreaklineMeshMatchCount", presentation.mesh_match_count)
    _set_preview_integer_property(obj, "SharedBreaklineMeshMismatchCount", presentation.mesh_mismatch_count)
    _set_preview_integer_property(obj, "SharedBreaklineReversedEdgeCount", presentation.reversed_edge_count)
    _set_preview_property(obj, "SharedBreaklineSolidReadinessStatus", presentation.solid_readiness_status)
    _set_preview_integer_property(obj, "SharedBreaklineSolidOpenEndCount", presentation.solid_open_end_count)
    _set_preview_integer_property(obj, "SharedBreaklineSolidDuplicateEdgeCount", presentation.solid_duplicate_edge_count)
    _set_preview_integer_property(obj, "SharedBreaklineSolidReversedEdgeCount", presentation.solid_reversed_edge_count)
    _set_preview_integer_property(obj, "SharedBreaklineSolidNonManifoldNodeCount", presentation.solid_non_manifold_node_count)
    _set_preview_property(obj, "SharedBreaklineSolidReadinessNotes", presentation.solid_readiness_notes)
    _set_preview_property(obj, "SharedBreaklineAuditSummary", presentation.summary)
    _set_preview_string_list_property(obj, "SharedBreaklineAuditNotes", list(presentation.note_rows))


def _shared_breakline_audit_summary(audit) -> str:
    if audit is None:
        return ""
    return SharedBreaklineAuditPresentationMapper().map(audit).summary


def shared_breakline_adjacency_graph(
    shared_result,
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Return the legacy mapping for the typed shared-breakline adjacency result."""

    return SharedBreaklineAuditService().adjacency(
        shared_result,
        tolerance=tolerance,
    ).to_legacy_dict()


def shared_breakline_audit(
    shared_result,
    consumer_surfaces: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return the legacy mapping for the typed shared-breakline audit result."""

    return SharedBreaklineAuditService().audit(
        shared_result,
        consumer_surfaces,
    ).to_legacy_dict()


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


def _corridor_build_review_absent_note(document, role: str) -> str:
    """Explain why a dedicated Intersection surface preview is absent; reads the document."""

    if role == "intersection_slope":
        return _intersection_slope_face_surface_absent_note(document)
    return ""


def _corridor_build_review_title(role: str) -> str:
    role_text = str(role or "").strip()
    for candidate_role, title, _object_name in CORRIDOR_BUILD_REVIEW_OBJECTS:
        if candidate_role == role_text:
            return str(title or "")
    return role_text


def _intersection_slope_face_surface_absent_note(document=None) -> str:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None or not _document_has_intersection(doc):
        return ""
    result = _document_intersection_kernel_result(doc)
    if result is None:
        return "Run Applied Sections: the intersection side slope is built on them."
    if result.diagnostics:
        return "The intersection kernel built no side slope: " + "; ".join(row.as_text() for row in result.diagnostics)
    return "The intersection kernel built no side slope; rebuild Build Parametric."


def _mark_preview_shape_failure(obj, *, preview_kind: str, error: BaseException):
    """Tag a preview object whose Shape assignment failed, then return it.

    A preview failure must not abort a Build Parametric run, so the object is
    still returned to the caller. Without a marker the caller receives an object
    that has no Shape and never reached its record-kind tagging, which is
    indistinguishable from a successful empty preview. These two properties make
    the fallback visible and traceable in the document rather than only in the
    console.
    """

    _set_preview_property(obj, "PreviewShapeStatus", "shape_build_failed")
    _set_preview_property(
        obj,
        "PreviewShapeDiagnostic",
        f"{preview_kind}: {type(error).__name__}: {str(error)[:200]}",
    )
    return obj


def _set_preview_property(obj, name: str, value: str) -> None:
    BuildCorridorPreviewAdapter.set_string(obj, name, value)


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    BuildCorridorPreviewAdapter.set_integer(obj, name, value)


def _set_preview_string_list_property(obj, name: str, values: list[str]) -> None:
    BuildCorridorPreviewAdapter.set_string_list(obj, name, values)


def _set_preview_float_property(obj, name: str, value: float) -> None:
    BuildCorridorPreviewAdapter.set_float(obj, name, value)


def _remove_preview_object(document, object_name: str) -> None:
    BuildCorridorPreviewAdapter.remove_object(document, object_name)


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
            route_object_to_project_tree(project or find_project(document), obj)
        except Exception:
            pass
        return obj
    except Exception:
        return None


def _remove_corridor_build_preview_diagnostic(document, role: str) -> None:
    object_name = CORRIDOR_BUILD_PREVIEW_DIAGNOSTIC_OBJECTS.get(str(role or ""))
    if object_name:
        _remove_preview_object(document, object_name)


def _corridor_centerline_preview_shape(document, app_module, part_module):
    centerline_result = _build_corridor_centerline3d_result(document)
    points, stations, result_id = _centerline_points_from_centerline3d_result(centerline_result, app_module)
    if len(points) < 2:
        return None, "empty", points, stations, "", result_id
    try:
        from .cmd_centerline3d import _centerline3d_preview_point_groups, _make_centerline3d_compound_curve_shape

        point_groups = _centerline3d_preview_point_groups(centerline_result)
        grouped_shape, grouped_curve_kind = _make_centerline3d_compound_curve_shape(point_groups, display_mode="bspline")
        if len(point_groups) > 1:
            return (
                grouped_shape,
                f"grouped_bspline_display_{grouped_curve_kind}",
                points,
                stations,
                "centerline3d_source_geometry",
                result_id,
            )
        return (
            grouped_shape,
            f"bspline_display_{grouped_curve_kind}",
            points,
            stations,
            "centerline3d_source_geometry",
            result_id,
        )
    except Exception:
        shape, curve_kind = _make_centerline_shape(points, part_module)
        return shape, curve_kind, points, stations, "centerline3d_result_fallback", result_id


def _build_corridor_centerline3d_result(document):
    try:
        from .cmd_centerline3d import build_document_centerline3d_result

        return build_document_centerline3d_result(document)
    except Exception:
        return None


def _corridor_supplemental_frame_resolver(document):
    centerline_result = _build_corridor_centerline3d_result(document)
    if str(getattr(centerline_result, "status", "") or "") != "ready":
        return None
    try:
        from ..services.evaluation import Centerline3DFrameService

        frame_service = Centerline3DFrameService()
    except Exception:
        return None
    result_cache: dict[str, object] = {}

    def resolve(station: float, first, second, ratio: float):
        alignment_id = _supplemental_alignment_id(first, second)
        result = _supplemental_centerline_result_for_alignment(centerline_result, alignment_id, result_cache)
        frame = frame_service.resolve_station(result, float(station))
        notes = str(getattr(frame, "notes", "") or "").strip()
        if "source=centerline3d_result" not in notes:
            notes = f"{notes};source=centerline3d_result" if notes else "source=centerline3d_result"
        if "supplemental_sampling_source_resolved" not in notes:
            notes = f"{notes};supplemental_sampling_source_resolved"
        try:
            return replace(frame, station=float(station), notes=notes)
        except Exception:
            return frame

    return resolve


def _supplemental_alignment_id(first, second) -> str:
    first_id = str(getattr(first, "alignment_id", "") or "").strip()
    second_id = str(getattr(second, "alignment_id", "") or "").strip()
    if first_id and first_id == second_id:
        return first_id
    return first_id or second_id


def _supplemental_centerline_result_for_alignment(centerline_result, alignment_id: str, cache: dict[str, object]):
    key = str(alignment_id or "").strip()
    if not key:
        return centerline_result
    if key in cache:
        return cache[key]
    rows = []
    for row in list(getattr(centerline_result, "point_rows", []) or []):
        row_alignment = str(getattr(row, "source_alignment_ref", "") or getattr(row, "alignment_id", "") or "").strip()
        if not row_alignment or row_alignment == key:
            rows.append(row)
    if len(rows) < 2:
        cache[key] = centerline_result
        return centerline_result
    try:
        result = replace(centerline_result, point_rows=rows)
    except Exception:
        result = centerline_result
    cache[key] = result
    return result


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
    gui_doc = _activate_gui_document_for_objects([obj])
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
        view = getattr(gui_doc, "ActiveView", None) or Gui.ActiveDocument.ActiveView
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
    gui_doc = _activate_gui_document_for_objects(clean)
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
        view = getattr(gui_doc, "ActiveView", None) or Gui.ActiveDocument.ActiveView
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


def _activate_gui_document_for_objects(objects: list[object]):
    if Gui is None:
        return None
    document = None
    for obj in list(objects or []):
        try:
            document = getattr(obj, "Document", None)
        except Exception:
            document = None
        if document is not None:
            break
    if document is None:
        try:
            return Gui.ActiveDocument
        except Exception:
            return None
    name = _document_identity(document)
    if not name:
        try:
            return Gui.ActiveDocument
        except Exception:
            return None
    try:
        active = getattr(Gui, "ActiveDocument", None)
        if _document_identity(getattr(active, "Document", None)) != name and hasattr(Gui, "setActiveDocument"):
            Gui.setActiveDocument(name)
    except Exception:
        pass
    try:
        if hasattr(Gui, "getDocument"):
            return Gui.getDocument(name)
    except Exception:
        pass
    try:
        return Gui.ActiveDocument
    except Exception:
        return None


def _corridor_build_preview_object(document, role: str):
    if document is None:
        return None
    role_text = str(role or "").strip()
    extra_roles = {}
    if role_text in extra_roles:
        try:
            return document.getObject(extra_roles[role_text])
        except Exception:
            return None
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
    # the Intersection Slope Face surface has its own review role, so the role sweep
    # already covers it and listing it here would toggle and count it twice
    names = (
        "V1CorridorIntersectionTieInEdgePreview",
        "V1CorridorIntersectionBoundarySegmentPreview",
        "V1CorridorIntersectionExclusionZonePreview",
        "V1CorridorIntersectionSlopeFaceOverlapPreview",
        "V1CorridorSupplementalFrameMarkers",
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
            "ReviewIssueSlopeFaceIssue",
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
        return document.getObject("ReviewDiagnosticSlopeFaceIntersectionMarkers") or document.getObject("ReviewIssueSlopeFaceIntersectionMarkers")
    except Exception:
        return None


def _corridor_build_daylight_marker_objects(document) -> list[object]:
    if document is None:
        return []
    names = (
        "ReviewDiagnosticSlopeFaceIntersectionMarkers",
        "ReviewDiagnosticSlopeFaceSampledEdgeMarkers",
        "ReviewDiagnosticSlopeFaceFallbackMarkers",
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
    _set_preview_integer_property(obj, "IntersectionSlopeTieInEdgeCount", int(float(quality.get("intersection_slope_tie_in_edge_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSlopeTieInTriangleCount", int(float(quality.get("intersection_slope_tie_in_triangle_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSideSlopeExtensionEdgeCount", int(float(quality.get("intersection_side_slope_extension_edge_count", 0) or 0)))
    _set_preview_integer_property(obj, "IntersectionSideSlopeExtensionTriangleCount", int(float(quality.get("intersection_side_slope_extension_triangle_count", 0) or 0)))
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
        ("intersection", "ReviewDiagnosticSlopeFaceIntersectionMarkers", "Slope Face Daylight / EG Intersections", daylight_marker_color, 1.8),
        ("sampled_outer_edge", "ReviewDiagnosticSlopeFaceSampledEdgeMarkers", "Slope Face Outer Edge Samples", daylight_marker_color),
        ("fallback", "ReviewDiagnosticSlopeFaceFallbackMarkers", "Slope Face Fallback / No Hit", daylight_marker_color),
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
            record_kind="v1_review_diagnostic",
            object_type="ReviewDiagnostic",
            issue_kind="slope_face_tie_in_diagnostic",
        )
        if obj is not None:
            _set_object_visibility(obj, bool(show_daylight_contact_markers))
            created.append(obj)
            try:
                route_object_to_project_tree(project or find_project(document), obj)
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
        "ReviewDiagnosticSlopeFaceIntersectionMarkers",
        "ReviewDiagnosticSlopeFaceSampledEdgeMarkers",
        "ReviewDiagnosticSlopeFaceFallbackMarkers",
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
        points = _slope_face_issue_breakline_points(row, applied_section_set)
        if not points:
            points = [point]
        elif not _same_xyz(points[-1], point):
            points.append(point)
        object_name = str(row.get("marker_object", "") or "")
        if not object_name:
            continue
        obj = _create_marker_compound(
            document=document,
            object_name=object_name,
            label=f"Slope Face Issue - {row.get('station_label', '')} {row.get('side', '')}",
            points=points,
            radius=max(float(radius or 0.5) * 1.6, 0.3),
            color=(0.10, 0.85, 0.25),
            surface=surface,
            corridor_model=corridor_model,
            record_kind="v1_review_issue",
            object_type="ReviewIssue",
            issue_kind="slope_face_fallback",
            connect_points=True,
        )
        if obj is None:
            continue
        _set_preview_property(obj, "IssueStation", str(row.get("station_label", "") or ""))
        _set_preview_property(obj, "IssueSide", str(row.get("side", "") or ""))
        _set_preview_property(obj, "IssueReason", str(row.get("reason", "") or ""))
        _set_object_visibility(obj, bool(visible))
        created.append(obj)
        try:
            route_object_to_project_tree(project or find_project(document), obj)
        except Exception:
            pass
    return created


def _slope_face_issue_breakline_points(row: dict[str, str], applied_section_set=None) -> list[tuple[float, float, float]]:
    section = _slope_face_issue_section(row, applied_section_set)
    if section is None:
        return []
    side_label = _slope_face_issue_side_label(row)
    if not side_label:
        return []
    return _unique_xyz(_slope_face_applied_section_breakline_points(section, side_label=side_label))


def _slope_face_issue_section(row: dict[str, str], applied_section_set=None):
    if applied_section_set is None:
        return None
    try:
        station_index = int(str(row.get("station_index", "") or ""))
    except Exception:
        return None
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    if station_index < 0 or station_index >= len(station_rows):
        return None
    section_id = str(getattr(station_rows[station_index], "applied_section_id", "") or "")
    if not section_id:
        return None
    for section in list(getattr(applied_section_set, "sections", []) or []):
        if str(getattr(section, "applied_section_id", "") or "") == section_id:
            return section
    return None


def _slope_face_issue_side_label(row: dict[str, str]) -> str:
    side = str(row.get("side", "") or "").strip().upper()
    if side == "L":
        return "left"
    if side == "R":
        return "right"
    return ""


def _slope_face_applied_section_breakline_points(section, *, side_label: str) -> list[tuple[float, float, float]]:
    roles = {"side_slope_surface", "bench_surface", "daylight_marker"}
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") in roles and _point_matches_side(point, side_label=side_label)
    ]
    return _breakline_points_from_rows(rows, side_label=side_label, role_attr="point_role")


def _point_matches_side(point, *, side_label: str) -> bool:
    side = str(getattr(point, "side", "") or "").strip().lower()
    if side in {"left", "right"}:
        return side == side_label
    offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
    return offset >= -1.0e-9 if side_label == "left" else offset <= 1.0e-9


def _breakline_points_from_rows(rows: list[object], *, side_label: str, role_attr: str) -> list[tuple[float, float, float]]:
    direction = 1.0 if side_label == "left" else -1.0
    ordered = sorted(
        list(rows or []),
        key=lambda point: (
            float(getattr(point, "lateral_offset", 0.0) or 0.0) * direction,
            _slope_face_role_order(str(getattr(point, role_attr, "") or "")),
        ),
    )
    return [
        (
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0),
        )
        for point in ordered
    ]


def _slope_face_role_order(role: str) -> int:
    text = str(role or "").strip().lower()
    if "hinge" in text or text == "side_slope_surface":
        return 0
    if "bench" in text:
        return 1
    if "daylight" in text:
        return 2
    return 3


def _unique_xyz(points: list[tuple[float, float, float]], *, tolerance: float = 1.0e-7) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    for point in list(points or []):
        if output and _same_xyz(output[-1], point, tolerance=tolerance):
            continue
        output.append(point)
    return output


def _same_xyz(first: tuple[float, float, float], second: tuple[float, float, float], *, tolerance: float = 1.0e-7) -> bool:
    return (
        abs(float(first[0]) - float(second[0])) <= tolerance
        and abs(float(first[1]) - float(second[1])) <= tolerance
        and abs(float(first[2]) - float(second[2])) <= tolerance
    )


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
        elif status.startswith("fallback"):
            key = "fallback"
        else:
            continue
        points[key].append((float(vertex.x), float(vertex.y), float(vertex.z)))
    return points


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


def _slope_face_issue_review_status(row: dict[str, str]) -> str:
    """Normalize a typed Side Slope diagnostic to the review status vocabulary."""

    status = str(row.get("status", "") or "").strip().lower()
    if status.startswith("error"):
        return "error"
    if status.startswith(("warning", "warn", "fallback")):
        return "warning"
    return "warning" if status else "missing"


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
                "marker_object": "ReviewDiagnosticSlopeFaceFallbackMarkers",
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
    record_kind: str = "v1_review_issue",
    object_type: str = "ReviewIssue",
    issue_kind: str = "slope_face_tie_in",
    connect_points: bool = False,
):
    """Compatibility wrapper for the Build Corridor preview adapter."""

    try:
        import Part
        import FreeCAD as AppModule
    except Exception:
        return None
    return BuildCorridorPreviewAdapter().create_marker_compound(
        document=document,
        object_name=object_name,
        label=label,
        points=points,
        radius=radius,
        color=color,
        surface=surface,
        corridor_model=corridor_model,
        record_kind=record_kind,
        object_type=object_type,
        issue_kind=issue_kind,
        connect_points=connect_points,
        app_module=AppModule,
        part_module=Part,
    )


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


def _confirm_message(parent, title: str, message: str) -> bool:
    try:
        buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        result = QtWidgets.QMessageBox.question(parent, title, message, buttons, QtWidgets.QMessageBox.No)
        return result == QtWidgets.QMessageBox.Yes
    except Exception:
        return True


def open_structure_output_panel(*, document=None):
    """Open the Structure Output panel for the Build Parametric task panel."""

    # imported here: cmd_structure_output imports this module
    from .cmd_structure_output import run_v1_structure_output_command

    return run_v1_structure_output_command(document=document)


# Explicit command/controller callback boundary for the UI-owned task panel.
configure_build_corridor_task_panel_runtime(globals())
