"""Applied Sections generation command for CorridorRoad v1."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None
    Part = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.result.centerline3d import Centerline3DResult
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ..models.source.assembly_model import AssemblySourceIdentity
from ..models.source.override_model import OverrideModel
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_applied_section import (
    create_or_update_v1_applied_section_set_object,
    find_v1_applied_section_set,
    to_applied_section_set,
)
from ..objects.obj_subassembly_assembly import (
    find_v1_assembly_subassembly_model,
    list_v1_assembly_subassembly_models,
    to_assembly_subassembly_model,
)
from ..objects.obj_subassembly_library import list_v1_subassembly_libraries, to_subassembly_library
from ..objects.obj_subassembly_preset_library import list_v1_subassembly_preset_libraries, to_subassembly_preset_library
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_intersection import find_v1_intersection_model, to_intersection_model
from ..objects.obj_profile import find_v1_profile, to_profile_model
from ..objects.obj_region import find_v1_region_model, to_region_model
from ..objects.obj_stationing import find_v1_stationing
from ..objects.obj_structure import find_v1_structure_model, to_structure_model
from ..objects.obj_superelevation import find_v1_superelevation_source, to_superelevation_model
from ..services.builders import AppliedSectionSetBuildRequest, AppliedSectionSetService
from ..services.builders.corridor_surface_geometry_service import (
    SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
    SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    SUPPLEMENTAL_SAMPLING_MAX_SPACING,
)
from ..services.evaluation import Centerline3DFrameService
from ..services.evaluation.intersection_evaluation_service import IntersectionEvaluationService


APPLIED_SECTION_REVIEW_ROW_COLORS = {
    "ok": (220, 245, 224),
    "warn": (255, 241, 205),
    "missing": (255, 220, 220),
}
APPLIED_SECTION_REVIEW_TEXT_COLOR = (20, 20, 20)
APPLIED_SECTION_SUPPLEMENTAL_DENSITY_DEFAULT = 11
APPLIED_SECTION_SUPPLEMENTAL_DENSITY_SPACING_SCALE = 3.0
APPLIED_SECTION_SUPPLEMENTAL_VERTICAL_CHORD_DEVIATION_DEFAULT = 0.10
APPLIED_SECTION_SUPPLEMENTAL_GRADE_DELTA_DEFAULT = 0.01


def build_document_applied_section_set(
    document=None,
    *,
    project=None,
    corridor_id: str = "corridor:main",
    supplemental_sections_enabled: bool = True,
    supplemental_sections_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sections_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sections_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
    supplemental_sections_vertical_chord_deviation: float = APPLIED_SECTION_SUPPLEMENTAL_VERTICAL_CHORD_DEVIATION_DEFAULT,
    supplemental_sections_grade_delta: float = APPLIED_SECTION_SUPPLEMENTAL_GRADE_DELTA_DEFAULT,
):
    """Build an AppliedSectionSet result from the active v1 source objects."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    source_bundles = _applied_section_source_bundles(doc)
    alignment_obj = find_v1_alignment(doc)
    profile_obj = find_v1_profile(doc)
    subassembly_objs = list_v1_assembly_subassembly_models(doc)
    subassembly_obj = subassembly_objs[0] if subassembly_objs else find_v1_assembly_subassembly_model(doc)
    region_obj = find_v1_region_model(doc)
    stationing_obj = find_v1_stationing(doc)
    structure_obj = find_v1_structure_model(doc)
    drainage_obj = find_v1_drainage_model(doc)
    superelevation_obj = find_v1_superelevation_source(doc)
    intersection_obj = find_v1_intersection_model(doc)

    alignment = to_alignment_model(alignment_obj)
    profile = to_profile_model(profile_obj)
    assembly_subassembly_models = [
        model for model in (to_assembly_subassembly_model(obj) for obj in subassembly_objs) if model is not None
    ]
    subassembly_libraries = [
        model for model in (to_subassembly_library(obj) for obj in list_v1_subassembly_libraries(doc)) if model is not None
    ]
    subassembly_preset_libraries = [
        model
        for model in (to_subassembly_preset_library(obj) for obj in list_v1_subassembly_preset_libraries(doc))
        if model is not None
    ]
    if not assembly_subassembly_models:
        single_subassembly_model = to_assembly_subassembly_model(subassembly_obj)
        if single_subassembly_model is not None:
            assembly_subassembly_models = [single_subassembly_model]
    assembly_models = _request_assembly_identity_models(assembly_subassembly_models)
    assembly = assembly_models[0] if assembly_models else None
    region_model = to_region_model(region_obj)
    structure_model = to_structure_model(structure_obj)
    drainage_model = to_drainage_model(drainage_obj)
    superelevation_model = to_superelevation_model(superelevation_obj)
    intersection_model = to_intersection_model(intersection_obj)
    source_stations = _station_values(stationing_obj)
    stations = _with_intersection_supplemental_stations(
        source_stations,
        intersection_model,
        str(getattr(alignment, "alignment_id", "") or ""),
    )
    station_kinds = _intersection_supplemental_station_kind_map(source_stations, stations)

    missing = []
    if alignment is None:
        missing.append("Alignment")
    if profile is None:
        missing.append("Profile")
    if assembly is None:
        missing.append("Assembly / Subassembly")
    if region_model is None:
        missing.append("Regions")
    if not stations:
        missing.append("Stations")
    if missing:
        raise RuntimeError("Required v1 sources are missing: " + ", ".join(missing))

    project_id = _project_id(project or find_project(doc))
    centerline3d_result = _build_applied_sections_centerline3d_result(doc)
    if len(source_bundles) > 1:
        return _build_multi_alignment_applied_section_set(
            source_bundles,
            project_id=project_id,
            corridor_id=corridor_id,
            assembly=assembly,
            assembly_models=assembly_models,
            assembly_subassembly_models=assembly_subassembly_models,
            subassembly_libraries=subassembly_libraries,
            subassembly_preset_libraries=subassembly_preset_libraries,
            structure_model=structure_model,
            drainage_model=drainage_model,
            superelevation_model=superelevation_model,
            intersection_model=intersection_model,
            existing_ground_surface=_resolve_applied_sections_existing_ground_tin_surface(doc),
            centerline3d_result=centerline3d_result,
            supplemental_sections_enabled=supplemental_sections_enabled,
            supplemental_sections_max_spacing=supplemental_sections_max_spacing,
            supplemental_sections_tangent_delta_deg=supplemental_sections_tangent_delta_deg,
            supplemental_sections_chord_deviation=supplemental_sections_chord_deviation,
            supplemental_sections_vertical_chord_deviation=supplemental_sections_vertical_chord_deviation,
            supplemental_sections_grade_delta=supplemental_sections_grade_delta,
        )
    override_model = OverrideModel(
        schema_version=1,
        project_id=project_id,
        override_model_id="overrides:empty",
        alignment_id=alignment.alignment_id,
    )
    existing_ground_surface = _resolve_applied_sections_existing_ground_tin_surface(doc)
    return AppliedSectionSetService().build(
        AppliedSectionSetBuildRequest(
            project_id=project_id,
            corridor_id=corridor_id,
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            assembly_models=assembly_models,
            assembly_subassembly_models=assembly_subassembly_models,
            subassembly_libraries=subassembly_libraries,
            subassembly_preset_libraries=subassembly_preset_libraries,
            region_model=region_model,
            structure_model=structure_model,
            drainage_model=drainage_model,
            superelevation_model=superelevation_model,
            intersection_model=intersection_model,
            override_model=override_model,
            stations=stations,
            station_kinds=station_kinds,
            supplemental_sections_enabled=supplemental_sections_enabled,
            supplemental_sections_max_spacing=supplemental_sections_max_spacing,
            supplemental_sections_tangent_delta_deg=supplemental_sections_tangent_delta_deg,
            supplemental_sections_chord_deviation=supplemental_sections_chord_deviation,
            supplemental_sections_vertical_chord_deviation=supplemental_sections_vertical_chord_deviation,
            supplemental_sections_grade_delta=supplemental_sections_grade_delta,
            applied_section_set_id="applied-sections:main",
            existing_ground_surface=existing_ground_surface,
            centerline3d_result=centerline3d_result,
        )
    )


def _build_multi_alignment_applied_section_set(
    source_bundles: list[dict[str, object]],
    *,
    project_id: str,
    corridor_id: str,
    assembly,
    assembly_models: list[object],
    assembly_subassembly_models: list[object] | None = None,
    subassembly_libraries: list[object] | None = None,
    subassembly_preset_libraries: list[object] | None = None,
    structure_model=None,
    drainage_model=None,
    superelevation_model=None,
    intersection_model=None,
    existing_ground_surface=None,
    centerline3d_result=None,
    supplemental_sections_enabled: bool = True,
    supplemental_sections_max_spacing: float = SUPPLEMENTAL_SAMPLING_MAX_SPACING,
    supplemental_sections_tangent_delta_deg: float = SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG,
    supplemental_sections_chord_deviation: float = SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD,
    supplemental_sections_vertical_chord_deviation: float = APPLIED_SECTION_SUPPLEMENTAL_VERTICAL_CHORD_DEVIATION_DEFAULT,
    supplemental_sections_grade_delta: float = APPLIED_SECTION_SUPPLEMENTAL_GRADE_DELTA_DEFAULT,
) -> AppliedSectionSet:
    """Build one AppliedSectionSet from multiple alignment-scoped source bundles."""

    sections = []
    station_rows = []
    source_refs: list[str] = []
    service = AppliedSectionSetService()
    for bundle_index, bundle in enumerate(source_bundles, start=1):
        alignment = bundle["alignment"]
        profile = bundle["profile"]
        region_model = bundle["region_model"]
        source_stations = list(bundle["stations"])
        stations = _with_intersection_supplemental_stations(
            source_stations,
            intersection_model,
            str(getattr(bundle["alignment"], "alignment_id", "") or ""),
        )
        station_kinds = _intersection_supplemental_station_kind_map(source_stations, stations)
        alignment_id = str(getattr(alignment, "alignment_id", "") or f"alignment:{bundle_index}")
        set_id = f"applied-sections:{_safe_source_token(alignment_id)}"
        override_model = OverrideModel(
            schema_version=1,
            project_id=project_id,
            override_model_id=f"overrides:empty:{_safe_source_token(alignment_id)}",
            alignment_id=alignment_id,
        )
        partial = service.build(
            AppliedSectionSetBuildRequest(
                project_id=project_id,
                corridor_id=corridor_id,
                alignment=alignment,
                profile=profile,
                assembly=assembly,
                assembly_models=assembly_models,
                assembly_subassembly_models=list(assembly_subassembly_models or []),
                subassembly_libraries=list(subassembly_libraries or []),
                subassembly_preset_libraries=list(subassembly_preset_libraries or []),
                region_model=region_model,
                structure_model=structure_model,
                drainage_model=drainage_model,
                superelevation_model=superelevation_model,
                intersection_model=intersection_model,
                override_model=override_model,
                stations=stations,
                station_kinds=station_kinds,
                supplemental_sections_enabled=supplemental_sections_enabled,
                supplemental_sections_max_spacing=supplemental_sections_max_spacing,
                supplemental_sections_tangent_delta_deg=supplemental_sections_tangent_delta_deg,
                supplemental_sections_chord_deviation=supplemental_sections_chord_deviation,
                supplemental_sections_vertical_chord_deviation=supplemental_sections_vertical_chord_deviation,
                supplemental_sections_grade_delta=supplemental_sections_grade_delta,
                applied_section_set_id=set_id,
                existing_ground_surface=existing_ground_surface,
                centerline3d_result=_centerline3d_result_for_alignment(centerline3d_result, alignment_id),
            )
        )
        for row in list(getattr(partial, "station_rows", []) or []):
            station_rows.append(
                AppliedSectionStationRow(
                    station_row_id=str(getattr(row, "station_row_id", "") or f"{set_id}:station:{len(station_rows) + 1}"),
                    station=float(getattr(row, "station", 0.0) or 0.0),
                    applied_section_id=str(getattr(row, "applied_section_id", "") or ""),
                    kind=str(getattr(row, "kind", "") or "regular_sample"),
                )
            )
        sections.extend(list(getattr(partial, "sections", []) or []))
        source_refs.extend(list(getattr(partial, "source_refs", []) or []))
    return AppliedSectionSet(
        schema_version=1,
        project_id=project_id,
        applied_section_set_id="applied-sections:main",
        corridor_id=corridor_id,
        alignment_id="alignment:multiple",
        station_rows=station_rows,
        sections=sections,
        source_refs=_unique_text_refs(source_refs),
    )


def _applied_section_source_bundles(document) -> list[dict[str, object]]:
    """Return complete Alignment/Profile/Stationing/Region bundles keyed by alignment id."""

    alignments = [(obj, to_alignment_model(obj)) for obj in list(getattr(document, "Objects", []) or [])]
    alignments = [(obj, model) for obj, model in alignments if model is not None]
    profiles = [(obj, to_profile_model(obj)) for obj in list(getattr(document, "Objects", []) or [])]
    profiles = [(obj, model) for obj, model in profiles if model is not None]
    regions = [(obj, to_region_model(obj)) for obj in list(getattr(document, "Objects", []) or [])]
    regions = [(obj, model) for obj, model in regions if model is not None]
    stationings = [
        obj
        for obj in list(getattr(document, "Objects", []) or [])
        if str(getattr(obj, "V1ObjectType", "") or "") == "V1Stationing"
        or str(getattr(getattr(obj, "Proxy", None), "Type", "") or "") == "V1Stationing"
        or str(getattr(obj, "Name", "") or "").startswith("V1Stationing")
    ]
    output: list[dict[str, object]] = []
    for alignment_obj, alignment in alignments:
        alignment_id = str(getattr(alignment, "alignment_id", "") or getattr(alignment_obj, "AlignmentId", "") or "").strip()
        if not alignment_id:
            continue
        profile = _model_for_alignment(profiles, alignment_id)
        region_model = _model_for_alignment(regions, alignment_id)
        stationing_obj = _stationing_for_alignment(stationings, alignment_id)
        stations = _station_values(stationing_obj)
        if profile is None or region_model is None or not stations:
            continue
        output.append(
            {
                "alignment": alignment,
                "profile": profile,
                "region_model": region_model,
                "stations": stations,
            }
        )
    return output


def _model_for_alignment(rows: list[tuple[object, object]], alignment_id: str):
    target = str(alignment_id or "").strip()
    fallback = None
    for _obj, model in list(rows or []):
        model_alignment_id = str(getattr(model, "alignment_id", "") or "").strip()
        if fallback is None and not model_alignment_id:
            fallback = model
        if model_alignment_id == target:
            return model
    return fallback if len(rows) == 1 else None


def _stationing_for_alignment(rows: list[object], alignment_id: str):
    target = str(alignment_id or "").strip()
    fallback = None
    for obj in list(rows or []):
        obj_alignment_id = str(getattr(obj, "AlignmentId", "") or "").strip()
        if fallback is None and not obj_alignment_id:
            fallback = obj
        if obj_alignment_id == target:
            return obj
    return fallback if len(rows) == 1 else None


def _centerline3d_result_for_alignment(centerline3d_result, alignment_id: str):
    if centerline3d_result is None:
        return None
    target = str(alignment_id or "").strip()
    result_alignment_id = str(getattr(centerline3d_result, "alignment_id", "") or "").strip()
    if result_alignment_id == target:
        return centerline3d_result
    if result_alignment_id == "alignment:multiple":
        point_rows = tuple(
            row
            for row in list(getattr(centerline3d_result, "point_rows", ()) or ())
            if str(getattr(row, "source_alignment_ref", "") or "").strip() == target
        )
        if len(point_rows) >= 2:
            return Centerline3DResult(
                project_id=str(getattr(centerline3d_result, "project_id", "") or "corridorroad-v1"),
                centerline3d_result_id=f"centerline3d:{_safe_source_token(target)}",
                alignment_id=target,
                profile_id=str(getattr(point_rows[0], "source_profile_ref", "") or ""),
                stationing_id=str(getattr(point_rows[0], "source_station_ref", "") or ""),
                point_rows=point_rows,
                diagnostic_rows=tuple(
                    row
                    for row in list(getattr(centerline3d_result, "diagnostic_rows", ()) or ())
                    if str(row or "").startswith(f"{target}|") or target in str(row or "")
                ),
                status="ready",
                source_refs=tuple(getattr(centerline3d_result, "source_refs", ()) or ()),
            )
    return None


def _safe_source_token(value: object) -> str:
    text = str(value or "source").strip().replace(":", "-")
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text).strip("-") or "source"


def _assembly_identity_model_from_subassembly_model(model) -> AssemblySourceIdentity:
    """Return an id-only assembly identity for Subassembly builds."""

    return AssemblySourceIdentity(
        schema_version=int(getattr(model, "schema_version", 1) or 1),
        project_id=str(getattr(model, "project_id", "") or "corridorroad-v1"),
        assembly_id=str(getattr(model, "assembly_id", "") or "assembly:subassembly-main"),
        alignment_id=str(getattr(model, "alignment_id", "") or ""),
        active_template_id=str(getattr(model, "active_template_id", "") or ""),
        label=str(getattr(model, "label", "") or "Assembly / Subassembly"),
    )


def _request_assembly_identity_models(assembly_subassembly_models: list[object]) -> list[AssemblySourceIdentity]:
    """Build id-only assembly request identities from active Subassembly sources."""

    identity_models = [
        _assembly_identity_model_from_subassembly_model(model)
        for model in list(assembly_subassembly_models or [])
        if model is not None
    ]
    return _unique_assembly_models_for_build(identity_models)


def _unique_assembly_models_for_build(values: list[AssemblySourceIdentity]) -> list[AssemblySourceIdentity]:
    output: list[AssemblySourceIdentity] = []
    seen = set()
    for model in list(values or []):
        if model is None:
            continue
        assembly_id = str(getattr(model, "assembly_id", "") or "")
        key = assembly_id or str(id(model))
        if key in seen:
            continue
        seen.add(key)
        output.append(model)
    return output


def _unique_text_refs(values: list[object]) -> list[str]:
    output = []
    seen = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def apply_v1_applied_section_set(
    *,
    document=None,
    project=None,
    applied_section_set=None,
):
    """Persist a v1 AppliedSectionSet result object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
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
    if applied_section_set is None:
        applied_section_set = build_document_applied_section_set(doc, project=prj)
    obj = create_or_update_v1_applied_section_set_object(
        document=doc,
        project=prj,
        applied_section_set=applied_section_set,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def applied_section_review_rows(applied_section_set) -> list[dict[str, object]]:
    """Return compact station-wise review rows for an AppliedSectionSet."""

    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    sections = list(getattr(applied_section_set, "sections", []) or [])
    section_by_id = {str(getattr(section, "applied_section_id", "") or ""): section for section in sections}
    output: list[dict[str, object]] = []
    for station_row in station_rows:
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        frame = getattr(section, "frame", None) if section is not None else None
        diagnostic_count = _applied_section_diagnostic_count(section) if section is not None else 1
        subassembly_count = len(list(getattr(section, "subassembly_rows", []) or [])) if section is not None else 0
        subassembly_summary = _subassembly_summary(section)
        preset_summary = _subassembly_preset_review_summary(section)
        ditch_summary = _ditch_review_summary(section)
        slope_face_summary = _slope_face_review_summary(section)
        superelevation_summary = _superelevation_review_summary(section)
        intersection_summary = _intersection_review_summary(section)
        frame_source = _frame_source_summary(frame)
        diagnostic_summary = _diagnostic_summary(section) if section is not None else "Missing AppliedSection result."
        output.append(
            {
                "station": float(getattr(station_row, "station", 0.0) or 0.0),
                "station_kind": str(getattr(station_row, "kind", "") or "regular_sample"),
                "applied_section_id": section_id,
                "x": float(getattr(frame, "x", 0.0) or 0.0),
                "y": float(getattr(frame, "y", 0.0) or 0.0),
                "z": float(getattr(frame, "z", 0.0) or 0.0),
                "region_id": str(getattr(section, "region_id", "") or "") if section is not None else "",
                "assembly_id": str(getattr(section, "assembly_id", "") or "") if section is not None else "",
                "template_id": str(getattr(section, "template_id", "") or "") if section is not None else "",
                "surface_left_width": float(getattr(section, "surface_left_width", 0.0) or 0.0) if section is not None else 0.0,
                "surface_right_width": float(getattr(section, "surface_right_width", 0.0) or 0.0) if section is not None else 0.0,
                "subgrade_depth": float(getattr(section, "subgrade_depth", 0.0) or 0.0) if section is not None else 0.0,
                "daylight_left_width": float(getattr(section, "daylight_left_width", 0.0) or 0.0) if section is not None else 0.0,
                "daylight_right_width": float(getattr(section, "daylight_right_width", 0.0) or 0.0) if section is not None else 0.0,
                "subassembly_count": subassembly_count,
                "subassembly_summary": subassembly_summary,
                "preset_summary": preset_summary,
                "ditch_summary": ditch_summary,
                "slope_face_summary": slope_face_summary,
                "superelevation_summary": superelevation_summary,
                "intersection_summary": intersection_summary,
                "frame_source": frame_source,
                "diagnostic_count": diagnostic_count,
                "diagnostic_summary": diagnostic_summary,
                "status": "warn" if diagnostic_count else "ok",
            }
        )
    return output


def show_applied_section_preview_object(document, applied_section_set, row_index: int):
    """Create or update a 3D preview line for one AppliedSection row."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Applied Section preview.")
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    if row_index < 0 or row_index >= len(station_rows):
        raise IndexError("Applied Section row index is out of range.")
    section_by_id = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    station_row = station_rows[row_index]
    section = section_by_id.get(str(getattr(station_row, "applied_section_id", "") or ""))
    if section is None:
        raise ValueError("Applied Section row has no matching section result.")
    shape = applied_section_preview_shape(section)
    obj = document.getObject("V1AppliedSectionShowPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1AppliedSectionShowPreview")
    station = float(getattr(section, "station", getattr(station_row, "station", 0.0)) or 0.0)
    obj.Label = f"Applied Section Preview - STA {station:.3f}"
    obj.Shape = shape
    _set_preview_string_property(obj, "CRRecordKind", "v1_applied_section_show_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1AppliedSectionShowPreview")
    _set_preview_string_property(obj, "AppliedSectionId", str(getattr(section, "applied_section_id", "") or ""))
    _set_preview_string_property(obj, "RegionId", str(getattr(section, "region_id", "") or ""))
    _set_preview_string_property(obj, "AssemblyId", str(getattr(section, "assembly_id", "") or ""))
    _set_preview_string_property(obj, "TemplateId", str(getattr(section, "template_id", "") or ""))
    _set_preview_string_property(obj, "PreviewMode", _applied_section_preview_mode(section))
    _set_preview_integer_property(obj, "PreviewPointCount", _applied_section_preview_point_count(section))
    _set_preview_float_property(obj, "Station", station)
    _style_applied_section_preview_object(obj)
    _remove_applied_section_station_marker_object(document)
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


def show_all_applied_sections_preview_object(document, applied_section_set):
    """Create or update a 3D preview containing every AppliedSection row."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Applied Sections preview.")
    sections = list(getattr(applied_section_set, "sections", []) or [])
    if not sections:
        raise ValueError("No Applied Section rows are available for preview.")
    shapes = []
    preview_point_count = 0
    stations = []
    for section in sections:
        try:
            shape = applied_section_preview_shape(section)
            if shape is not None and not shape.isNull():
                shapes.append(shape)
                preview_point_count += _applied_section_preview_point_count(section)
                stations.append(float(getattr(section, "station", 0.0) or 0.0))
        except Exception:
            continue
    if not shapes:
        raise ValueError("No Applied Section preview geometry could be built.")
    obj = document.getObject("V1AppliedSectionsShowAllPreview")
    if obj is None:
        obj = document.addObject("Part::Feature", "V1AppliedSectionsShowAllPreview")
    obj.Label = f"Applied Sections Preview - All ({len(shapes)})"
    obj.Shape = Part.Compound(shapes)
    _set_preview_string_property(obj, "CRRecordKind", "v1_applied_sections_show_all_preview")
    _set_preview_string_property(obj, "V1ObjectType", "V1AppliedSectionsShowAllPreview")
    _set_preview_string_property(obj, "AppliedSectionSetId", str(getattr(applied_section_set, "applied_section_set_id", "") or ""))
    _set_preview_string_property(obj, "PreviewMode", "all_section_points")
    _set_preview_integer_property(obj, "PreviewSectionCount", len(shapes))
    _set_preview_integer_property(obj, "PreviewPointCount", preview_point_count)
    if stations:
        _set_preview_float_property(obj, "StationStart", min(stations))
        _set_preview_float_property(obj, "StationEnd", max(stations))
    _style_applied_section_preview_object(obj)
    _remove_applied_section_station_marker_object(document)
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


def hide_applied_sections_preview_objects(document) -> int:
    """Hide Applied Sections review preview objects without deleting result data."""

    if document is None:
        return 0
    preview_kinds = {
        "v1_applied_section_show_preview",
        "v1_applied_sections_show_all_preview",
        "v1_applied_section_station_marker",
    }
    preview_names = {
        "V1AppliedSectionShowPreview",
        "V1AppliedSectionsShowAllPreview",
        "V1AppliedSectionStationMarker",
    }
    hidden_count = 0
    seen_names: set[str] = set()
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        if name not in preview_names and record_kind not in preview_kinds:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        view_object = getattr(obj, "ViewObject", None)
        if view_object is None:
            continue
        try:
            if bool(getattr(view_object, "Visibility", False)):
                hidden_count += 1
            view_object.Visibility = False
        except Exception:
            continue
    try:
        document.recompute()
    except Exception:
        pass
    return hidden_count


def _remove_applied_section_station_marker_object(document) -> None:
    if document is None:
        return
    marker = document.getObject("V1AppliedSectionStationMarker")
    if marker is None:
        return
    try:
        document.removeObject(marker.Name)
    except Exception:
        try:
            marker.ViewObject.Visibility = False
        except Exception:
            pass


def show_applied_section_station_marker_object(document, section, *, station: float | None = None):
    """Create or update a clear marker at the selected Applied Section station."""

    if document is None:
        raise RuntimeError("No active document.")
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required for Applied Section station marker.")
    frame = getattr(section, "frame", None)
    if frame is None:
        raise ValueError("Applied Section station marker requires a station frame.")
    center = App.Vector(float(getattr(frame, "x", 0.0) or 0.0), float(getattr(frame, "y", 0.0) or 0.0), float(getattr(frame, "z", 0.0) or 0.0))
    radius = _applied_section_station_marker_radius(section)
    marker = document.getObject("V1AppliedSectionStationMarker")
    if marker is None:
        marker = document.addObject("Part::Feature", "V1AppliedSectionStationMarker")
    active_station = float(station if station is not None else getattr(section, "station", 0.0) or 0.0)
    marker.Label = f"Applied Section Station - STA {active_station:.3f}"
    marker.Shape = _applied_section_station_marker_shape(center, radius, frame)
    _set_preview_string_property(marker, "CRRecordKind", "v1_applied_section_station_marker")
    _set_preview_string_property(marker, "V1ObjectType", "V1AppliedSectionStationMarker")
    _set_preview_string_property(marker, "MarkerShape", "target_cross")
    _set_preview_string_property(marker, "AppliedSectionId", str(getattr(section, "applied_section_id", "") or ""))
    _set_preview_float_property(marker, "Station", active_station)
    _set_preview_float_property(marker, "MarkerX", float(center.x))
    _set_preview_float_property(marker, "MarkerY", float(center.y))
    _set_preview_float_property(marker, "MarkerZ", float(center.z))
    _style_applied_section_station_marker(marker)
    return marker


def applied_section_preview_shape(section):
    """Build a visible 3D cross-section preview from one AppliedSection result."""

    if App is None or Part is None:
        return None
    frame = getattr(section, "frame", None)
    if frame is None:
        raise ValueError("Applied Section preview requires a station frame.")
    polylines = _applied_section_preview_polylines(section, frame)
    all_points = [point for _role, points in polylines for point in points]
    shapes = []
    for _role, points in polylines:
        wire = _make_applied_section_wire(points)
        if wire is not None:
            shapes.append(wire)
    return Part.Compound(shapes) if shapes else Part.Shape()


def run_v1_applied_sections_command():
    """Open the v1 Applied Sections generation panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    panel = V1AppliedSectionsTaskPanel(document=App.ActiveDocument)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_applied_section_set(App.ActiveDocument)


class V1AppliedSectionsTaskPanel:
    """Small build-gated panel for creating AppliedSectionSet results."""

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
        widget.setWindowTitle("ParametricRoad v1 - Applied Sections")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Applied Sections")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel(
            "Build station-by-station AppliedSection results from Alignment, Profile, Stations, Assembly / Subassembly, and Regions. "
            "This does not generate corridor solids."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        options_box = QtWidgets.QGroupBox("Supplemental Sections")
        options_layout = QtWidgets.QVBoxLayout(options_box)
        self._supplemental_sections_check = QtWidgets.QCheckBox("Create supplemental Applied Sections on curved 3D Centerline spans")
        self._supplemental_sections_check.setToolTip(
            "Applied Sections creates result-only supplemental sections for horizontal and vertical curves before Build Parametric runs."
        )
        self._supplemental_sections_check.setChecked(True)
        self._supplemental_sections_check.toggled.connect(lambda _checked: self._sync_supplemental_sections_summary())
        options_layout.addWidget(self._supplemental_sections_check)

        density_row = QtWidgets.QHBoxLayout()
        density_row.addWidget(QtWidgets.QLabel("Density"))
        self._supplemental_sections_density_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._supplemental_sections_density_slider.setRange(1, 25)
        self._supplemental_sections_density_slider.setValue(APPLIED_SECTION_SUPPLEMENTAL_DENSITY_DEFAULT)
        self._supplemental_sections_density_slider.setTickInterval(4)
        self._supplemental_sections_density_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self._supplemental_sections_density_slider.setToolTip(
            "Higher density creates more supplemental Applied Sections on curved horizontal or vertical spans."
        )
        self._supplemental_sections_density_slider.valueChanged.connect(lambda _value: self._sync_supplemental_sections_summary())
        density_row.addWidget(self._supplemental_sections_density_slider, 1)
        self._supplemental_sections_density_value = QtWidgets.QLabel("")
        density_row.addWidget(self._supplemental_sections_density_value)
        options_layout.addLayout(density_row)

        threshold_row = QtWidgets.QHBoxLayout()
        threshold_row.addWidget(QtWidgets.QLabel("Tangent >"))
        self._supplemental_sections_tangent_spin = QtWidgets.QDoubleSpinBox()
        self._supplemental_sections_tangent_spin.setRange(0.1, 45.0)
        self._supplemental_sections_tangent_spin.setDecimals(2)
        self._supplemental_sections_tangent_spin.setSingleStep(0.25)
        self._supplemental_sections_tangent_spin.setValue(float(SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG))
        self._supplemental_sections_tangent_spin.setSuffix(" deg")
        self._supplemental_sections_tangent_spin.setToolTip("Add supplemental sections when horizontal tangent direction changes more than this value.")
        self._supplemental_sections_tangent_spin.valueChanged.connect(lambda _value: self._sync_supplemental_sections_summary())
        threshold_row.addWidget(self._supplemental_sections_tangent_spin)
        threshold_row.addWidget(QtWidgets.QLabel("Chord >"))
        self._supplemental_sections_chord_spin = QtWidgets.QDoubleSpinBox()
        self._supplemental_sections_chord_spin.setRange(0.001, 10.0)
        self._supplemental_sections_chord_spin.setDecimals(3)
        self._supplemental_sections_chord_spin.setSingleStep(0.05)
        self._supplemental_sections_chord_spin.setValue(float(SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD))
        self._supplemental_sections_chord_spin.setSuffix(" m")
        self._supplemental_sections_chord_spin.setToolTip("Add supplemental sections when 3D Centerline chord deviation exceeds this value.")
        self._supplemental_sections_chord_spin.valueChanged.connect(lambda _value: self._sync_supplemental_sections_summary())
        threshold_row.addWidget(self._supplemental_sections_chord_spin)
        threshold_row.addStretch(1)
        options_layout.addLayout(threshold_row)

        vertical_threshold_row = QtWidgets.QHBoxLayout()
        vertical_threshold_row.addWidget(QtWidgets.QLabel("Vertical Chord >"))
        self._supplemental_sections_vertical_chord_spin = QtWidgets.QDoubleSpinBox()
        self._supplemental_sections_vertical_chord_spin.setRange(0.001, 10.0)
        self._supplemental_sections_vertical_chord_spin.setDecimals(3)
        self._supplemental_sections_vertical_chord_spin.setSingleStep(0.05)
        self._supplemental_sections_vertical_chord_spin.setValue(float(APPLIED_SECTION_SUPPLEMENTAL_VERTICAL_CHORD_DEVIATION_DEFAULT))
        self._supplemental_sections_vertical_chord_spin.setSuffix(" m")
        self._supplemental_sections_vertical_chord_spin.setToolTip("Add supplemental sections when a vertical curve deviates from the straight endpoint grade chord by more than this value.")
        self._supplemental_sections_vertical_chord_spin.valueChanged.connect(lambda _value: self._sync_supplemental_sections_summary())
        vertical_threshold_row.addWidget(self._supplemental_sections_vertical_chord_spin)
        vertical_threshold_row.addWidget(QtWidgets.QLabel("Grade Delta >"))
        self._supplemental_sections_grade_delta_spin = QtWidgets.QDoubleSpinBox()
        self._supplemental_sections_grade_delta_spin.setRange(0.01, 50.0)
        self._supplemental_sections_grade_delta_spin.setDecimals(2)
        self._supplemental_sections_grade_delta_spin.setSingleStep(0.25)
        self._supplemental_sections_grade_delta_spin.setValue(float(APPLIED_SECTION_SUPPLEMENTAL_GRADE_DELTA_DEFAULT) * 100.0)
        self._supplemental_sections_grade_delta_spin.setSuffix(" %")
        self._supplemental_sections_grade_delta_spin.setToolTip("Add supplemental sections when profile grade changes more than this percent between evaluated stations.")
        self._supplemental_sections_grade_delta_spin.valueChanged.connect(lambda _value: self._sync_supplemental_sections_summary())
        vertical_threshold_row.addWidget(self._supplemental_sections_grade_delta_spin)
        vertical_threshold_row.addStretch(1)
        options_layout.addLayout(vertical_threshold_row)

        self._supplemental_sections_count_label = QtWidgets.QLabel("Sections: n/a")
        self._supplemental_sections_count_label.setToolTip("Source, existing supplemental, and total Applied Section counts.")
        options_layout.addWidget(self._supplemental_sections_count_label)
        layout.addWidget(options_box)
        self._sync_supplemental_sections_summary()

        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setFixedHeight(160)
        layout.addWidget(self._summary)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Ready")
        layout.addWidget(self._progress)

        self._review_table = QtWidgets.QTableWidget(0, 18)
        self._review_table.setHorizontalHeaderLabels(
            [
                "STA",
                "Kind",
                "X",
                "Y",
                "Z",
                "Region",
                "Assembly",
                "Template",
                "L/R Width",
                "Subassemblies",
                "Presets",
                "Ditch",
                "Slope Face",
                "Superelevation",
                "Intersection",
                "Frame Source",
                "Diagnostics",
                "Status",
            ]
        )
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
        self._review_table.cellDoubleClicked.connect(lambda row, _col: self._show_review_row(row))
        layout.addWidget(self._review_table, 1)

        action_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_summary)
        action_row.addWidget(refresh_button)
        build_button = QtWidgets.QPushButton("Build Sections")
        build_button.clicked.connect(lambda: self._apply(close_after=False))
        action_row.addWidget(build_button)
        show_all_button = QtWidgets.QPushButton("Show All")
        show_all_button.setToolTip("Show every generated Applied Section in the 3D View.")
        show_all_button.clicked.connect(self._show_all_review_rows)
        action_row.addWidget(show_all_button)
        hide_all_button = QtWidgets.QPushButton("Hide All")
        hide_all_button.setToolTip("Hide Applied Section preview objects in the 3D View.")
        hide_all_button.clicked.connect(self._hide_all_review_rows)
        action_row.addWidget(hide_all_button)
        action_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        action_row.addWidget(close_button)
        layout.addLayout(action_row)
        return widget

    def _refresh_summary(self) -> None:
        try:
            station_count = len(_station_values(find_v1_stationing(self.document)))
            lines = [
                f"Alignment: {_source_status(find_v1_alignment(self.document))}",
                f"Profile: {_source_status(find_v1_profile(self.document))}",
                f"Assembly / Subassembly: {_assembly_source_status(self.document)}",
                f"Regions: {_source_status(find_v1_region_model(self.document))}",
                f"Intersections: {_source_status(find_v1_intersection_model(self.document))}",
                f"Structures: {_source_status(find_v1_structure_model(self.document))}",
                f"Stations: {station_count} row(s)",
                "",
                "Click Build Sections to validate sources and create or update the v1 AppliedSectionSet result.",
            ]
            existing = to_applied_section_set(find_v1_applied_section_set(self.document))
            if existing is not None:
                review_rows = applied_section_review_rows(existing)
                lines.extend(
                    [
                        "",
                        f"Existing Applied Sections: {len(review_rows)} row(s)",
                        f"Intersection supplemental: {sum(1 for row in review_rows if str(row.get('station_kind', '') or '') == 'intersection_supplemental')}",
                        f"Existing diagnostics: {sum(int(row.get('diagnostic_count', 0) or 0) for row in review_rows)}",
                    ]
                )
                self._set_review_rows(review_rows)
            else:
                self._set_review_rows([])
            self._summary.setPlainText("\n".join(lines))
        except Exception as exc:
            self._summary.setPlainText(f"Summary failed:\n{exc}")
            self._set_review_rows([])

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            if not self._validate(show_message=False):
                self._set_progress(0, "Applied Sections validation failed")
                return False
            self._set_progress(0, "Preparing Applied Sections...")
            self._set_progress(15, "Reading v1 source models...")
            result = build_document_applied_section_set(
                self.document,
                supplemental_sections_enabled=self._use_supplemental_sections(),
                supplemental_sections_max_spacing=self._supplemental_sections_max_spacing(),
                supplemental_sections_tangent_delta_deg=self._supplemental_sections_tangent_delta_deg(),
                supplemental_sections_chord_deviation=self._supplemental_sections_chord_deviation(),
                supplemental_sections_vertical_chord_deviation=self._supplemental_sections_vertical_chord_deviation(),
                supplemental_sections_grade_delta=self._supplemental_sections_grade_delta(),
            )
            self._set_progress(65, "Writing AppliedSectionSet result...")
            obj = apply_v1_applied_section_set(document=self.document, applied_section_set=result)
            self._set_progress(85, "Refreshing station review...")
            diagnostic_count = sum(len(section.diagnostic_rows) for section in result.sections)
            supplemental_count = _supplemental_applied_section_count(result)
            source_count = max(len(result.station_rows) - supplemental_count, 0)
            message = (
                f"Applied Sections have been built.\n"
                f"Source sections: {source_count}\n"
                f"Supplemental sections: {supplemental_count}\n"
                f"Total sections: {len(result.station_rows)}\n"
                f"Diagnostics: {diagnostic_count}"
            )
            self._summary.setPlainText(message + f"\nObject: {obj.Label}")
            self._set_review_rows(applied_section_review_rows(result))
            self._set_progress(100, "Applied Sections complete")
            self._sync_supplemental_sections_summary(result)
            _show_message(self.form, "Applied Sections", message)
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_progress(0, "Applied Sections failed")
            self._summary.setPlainText(f"Applied Sections were not built:\n{exc}")
            _show_message(self.form, "Applied Sections", f"Applied Sections were not built.\n{exc}")
            return False

    def _validate(self, *, show_message: bool = True) -> bool:
        try:
            diagnostics = _applied_sections_source_diagnostics(self.document)
            if diagnostics:
                message = "Applied Sections validation failed:\n" + "\n".join(diagnostics)
                self._summary.setPlainText(message)
                if show_message:
                    _show_message(self.form, "Applied Sections", message)
                return False
            message = "Applied Sections validation passed."
            self._summary.setPlainText(message)
            if show_message:
                _show_message(self.form, "Applied Sections", message)
            return True
        except Exception as exc:
            message = f"Applied Sections validation failed:\n{exc}"
            self._summary.setPlainText(message)
            if show_message:
                _show_message(self.form, "Applied Sections", message)
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

    def _use_supplemental_sections(self) -> bool:
        check = getattr(self, "_supplemental_sections_check", None)
        if check is None:
            return True
        try:
            return bool(check.isChecked())
        except Exception:
            return True

    def _supplemental_sections_max_spacing(self) -> float:
        slider = getattr(self, "_supplemental_sections_density_slider", None)
        if slider is None:
            return float(SUPPLEMENTAL_SAMPLING_MAX_SPACING)
        try:
            density = max(1, min(25, int(slider.value())))
            return float(max(1.0, (26 - density) * APPLIED_SECTION_SUPPLEMENTAL_DENSITY_SPACING_SCALE))
        except Exception:
            return float(SUPPLEMENTAL_SAMPLING_MAX_SPACING)

    def _supplemental_sections_tangent_delta_deg(self) -> float:
        spin = getattr(self, "_supplemental_sections_tangent_spin", None)
        if spin is None:
            return float(SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG)
        try:
            return float(spin.value())
        except Exception:
            return float(SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG)

    def _supplemental_sections_chord_deviation(self) -> float:
        spin = getattr(self, "_supplemental_sections_chord_spin", None)
        if spin is None:
            return float(SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD)
        try:
            return float(spin.value())
        except Exception:
            return float(SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD)

    def _supplemental_sections_vertical_chord_deviation(self) -> float:
        spin = getattr(self, "_supplemental_sections_vertical_chord_spin", None)
        if spin is None:
            return float(APPLIED_SECTION_SUPPLEMENTAL_VERTICAL_CHORD_DEVIATION_DEFAULT)
        try:
            return float(spin.value())
        except Exception:
            return float(APPLIED_SECTION_SUPPLEMENTAL_VERTICAL_CHORD_DEVIATION_DEFAULT)

    def _supplemental_sections_grade_delta(self) -> float:
        spin = getattr(self, "_supplemental_sections_grade_delta_spin", None)
        if spin is None:
            return float(APPLIED_SECTION_SUPPLEMENTAL_GRADE_DELTA_DEFAULT)
        try:
            return float(spin.value()) / 100.0
        except Exception:
            return float(APPLIED_SECTION_SUPPLEMENTAL_GRADE_DELTA_DEFAULT)

    def _sync_supplemental_sections_summary(self, applied_section_set: AppliedSectionSet | None = None) -> None:
        value_label = getattr(self, "_supplemental_sections_density_value", None)
        count_label = getattr(self, "_supplemental_sections_count_label", None)
        try:
            density = APPLIED_SECTION_SUPPLEMENTAL_DENSITY_DEFAULT
            slider = getattr(self, "_supplemental_sections_density_slider", None)
            if slider is not None:
                density = int(slider.value())
            spacing = self._supplemental_sections_max_spacing()
            if value_label is not None:
                value_label.setText(f"{density}/25 ({spacing:g} m)")
                value_label.setToolTip(f"Approximate maximum curved-span spacing: {spacing:g} m.")
            if count_label is None:
                return
            applied = applied_section_set or to_applied_section_set(find_v1_applied_section_set(self.document))
            if applied is None:
                state = "on" if self._use_supplemental_sections() else "off"
                count_label.setText(f"Sections: n/a; supplemental setting {state}")
                return
            total = len(list(getattr(applied, "station_rows", []) or []))
            supplemental = _supplemental_applied_section_count(applied)
            source = max(total - supplemental, 0)
            count_label.setText(f"Sections: source {source}, supplemental {supplemental}, total {total}")
            count_label.setToolTip(
                "Existing supplemental count includes intersection and future curve/spacing supplemental Applied Sections."
            )
        except Exception:
            if count_label is not None:
                count_label.setText("Sections: unavailable")

    def _set_review_rows(self, rows: list[dict[str, object]]) -> None:
        if not hasattr(self, "_review_table"):
            return
        self._review_table.setRowCount(0)
        for row in list(rows or []):
            row_index = self._review_table.rowCount()
            self._review_table.insertRow(row_index)
            values = [
                _format_float(row.get("station", 0.0)),
                str(row.get("station_kind", "") or "regular_sample"),
                _format_float(row.get("x", 0.0)),
                _format_float(row.get("y", 0.0)),
                _format_float(row.get("z", 0.0)),
                str(row.get("region_id", "") or ""),
                _display_source_id(row.get("assembly_id", ""), "assembly:"),
                _display_source_id(row.get("template_id", ""), "template:"),
                f"{_format_float(row.get('surface_left_width', 0.0))} / {_format_float(row.get('surface_right_width', 0.0))}",
                _review_subassembly_summary_text(row),
                str(row.get("preset_summary", "") or ""),
                str(row.get("ditch_summary", "") or ""),
                str(row.get("slope_face_summary", "") or ""),
                str(row.get("superelevation_summary", "") or ""),
                str(row.get("intersection_summary", "") or ""),
                str(row.get("frame_source", "") or ""),
                str(row.get("diagnostic_summary", "") or ""),
                _review_status_text(row),
            ]
            for col, value in enumerate(values):
                self._review_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(str(value)))
            self._apply_review_row_style(row_index, str(row.get("status", "") or ""))

    def _show_review_row(self, row_index: int) -> None:
        try:
            applied = to_applied_section_set(find_v1_applied_section_set(self.document))
            if applied is None:
                applied = build_document_applied_section_set(self.document)
            preview = show_applied_section_preview_object(self.document, applied, int(row_index))
            marker = self.document.getObject("V1AppliedSectionStationMarker") if self.document is not None else None
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(preview)
                except Exception:
                    pass
                _fit_selected_preview()
            station = float(getattr(preview, "Station", 0.0) or 0.0)
            self._summary.setPlainText(
                f"Applied Section preview shown.\nSTA: {station:.3f}\nObject: {preview.Label}\n\nDouble-click another row to inspect it."
            )
        except Exception as exc:
            self._summary.setPlainText(f"Applied Section preview was not shown:\n{exc}")
            _show_message(self.form, "Applied Sections", f"Applied Section preview was not shown.\n{exc}")

    def _show_all_review_rows(self) -> None:
        try:
            applied = to_applied_section_set(find_v1_applied_section_set(self.document))
            if applied is None:
                applied = build_document_applied_section_set(self.document)
            preview = show_all_applied_sections_preview_object(self.document, applied)
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(preview)
                except Exception:
                    pass
                _fit_selected_preview()
            section_count = int(getattr(preview, "PreviewSectionCount", 0) or 0)
            station_start = float(getattr(preview, "StationStart", 0.0) or 0.0)
            station_end = float(getattr(preview, "StationEnd", 0.0) or 0.0)
            self._summary.setPlainText(
                "All Applied Sections preview shown.\n"
                f"Sections: {section_count}\n"
                f"STA: {station_start:.3f} -> {station_end:.3f}\n"
                f"Object: {preview.Label}\n\n"
                "Double-click a table row to inspect one section."
            )
        except Exception as exc:
            self._summary.setPlainText(f"All Applied Sections preview was not shown:\n{exc}")
            _show_message(self.form, "Applied Sections", f"All Applied Sections preview was not shown.\n{exc}")

    def _hide_all_review_rows(self) -> None:
        try:
            hidden_count = hide_applied_sections_preview_objects(self.document)
            if Gui is not None:
                try:
                    Gui.Selection.clearSelection()
                except Exception:
                    pass
            self._summary.setPlainText(
                "Applied Sections previews hidden.\n"
                f"Objects hidden: {hidden_count}\n\n"
                "Use Show All or double-click a table row to show previews again."
            )
        except Exception as exc:
            self._summary.setPlainText(f"Applied Sections previews were not hidden:\n{exc}")
            _show_message(self.form, "Applied Sections", f"Applied Sections previews were not hidden.\n{exc}")

    def _apply_review_row_style(self, row_index: int, status: str) -> None:
        color = applied_section_review_row_color(status)
        if color is None:
            return
        try:
            from freecad.Corridor_Road.qt_compat import QtGui

            brush = QtGui.QBrush(QtGui.QColor(*color))
            text_brush = QtGui.QBrush(QtGui.QColor(*APPLIED_SECTION_REVIEW_TEXT_COLOR))
            for column_index in range(int(self._review_table.columnCount())):
                item = self._review_table.item(int(row_index), column_index)
                if item is not None:
                    item.setBackground(brush)
                    item.setForeground(text_brush)
        except Exception:
            pass


class CmdV1AppliedSections:
    """Build v1 AppliedSectionSet results."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("sections.svg"),
            "MenuText": "Applied Sections",
            "ToolTip": "Build v1 AppliedSectionSet results from alignment, profile, stations, assembly, and regions",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_applied_sections_command()


def _station_values(stationing_obj) -> list[float]:
    values = []
    for value in list(getattr(stationing_obj, "StationValues", []) or []):
        try:
            values.append(float(value))
        except Exception:
            pass
    return values


def _active_intersection_model_for_document(document):
    try:
        return to_intersection_model(find_v1_intersection_model(document))
    except Exception:
        return None


def _with_intersection_supplemental_stations(
    stations: list[float],
    intersection_model,
    alignment_id: str,
) -> list[float]:
    """Merge intersection boundary and curb-return control stations into a station list."""

    base = _unique_station_values(stations)
    if intersection_model is None or not base:
        return base
    low = min(base)
    high = max(base)
    supplemental = _intersection_supplemental_stations_for_alignment(
        intersection_model,
        alignment_id,
        station_min=low,
        station_max=high,
    )
    return _unique_station_values([*base, *supplemental])


def _intersection_supplemental_station_kind_map(source_stations: list[float], built_stations: list[float]) -> dict[float, str]:
    source = _unique_station_values(source_stations)
    output: dict[float, str] = {}
    for station in _unique_station_values(built_stations):
        output[station] = "regular_sample" if _station_in_list(station, source) else "intersection_supplemental"
    return output


def _supplemental_applied_section_count(applied_section_set: AppliedSectionSet | None) -> int:
    if applied_section_set is None:
        return 0
    count = 0
    for row in list(getattr(applied_section_set, "station_rows", []) or []):
        kind = str(getattr(row, "kind", "") or "").strip().lower()
        if "supplemental" in kind:
            count += 1
    return count


def _station_in_list(station: float, stations: list[float], *, tolerance: float = 1.0e-6) -> bool:
    for value in list(stations or []):
        try:
            if abs(float(value) - float(station)) <= tolerance:
                return True
        except Exception:
            continue
    return False


def _intersection_supplemental_stations_for_alignment(
    intersection_model,
    alignment_id: str,
    *,
    station_min: float,
    station_max: float,
) -> list[float]:
    """Return result-only Applied Section stations needed for intersection handoff."""

    alignment_ref = str(alignment_id or "").strip()
    if not alignment_ref:
        return []
    output: list[float] = []
    output.extend(
        _intersection_edge_network_contact_stations_for_alignment(
            intersection_model,
            alignment_ref,
        )
    )
    curb_radius = _intersection_default_curb_radius(intersection_model)

    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        center_station = None
        if alignment_ref == str(getattr(row, "primary_alignment_ref", "") or "").strip():
            center_station = _float_or_none(getattr(row, "primary_station", None))
        else:
            secondary_refs = dict(getattr(row, "secondary_station_refs", {}) or {})
            center_station = _float_or_none(secondary_refs.get(alignment_ref))
        if center_station is not None:
            output.extend(_intersection_center_control_stations(center_station, curb_radius))
        for leg in list(getattr(row, "leg_rows", []) or []):
            if alignment_ref != str(getattr(leg, "alignment_ref", "") or "").strip():
                continue
            output.append(float(getattr(leg, "approach_station_start", 0.0) or 0.0))
            output.append(float(getattr(leg, "approach_station_end", 0.0) or 0.0))

    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if alignment_ref != str(getattr(area, "alignment_ref", "") or "").strip():
            continue
        for start, end in list(getattr(area, "station_ranges", []) or []):
            output.extend([float(start), float(end), (float(start) + float(end)) * 0.5])
        for start, end in list(getattr(area, "influence_ranges", []) or []):
            output.extend([float(start), float(end)])

    return _unique_station_values(
        [
            _clamp_station(value, station_min=station_min, station_max=station_max)
            for value in output
            if _is_finite_number(value)
        ]
    )


def _intersection_edge_network_contact_stations_for_alignment(
    intersection_model,
    alignment_id: str,
) -> list[float]:
    """Read exact intersection edge-network contact stations when the contract exposes them."""

    alignment_ref = str(alignment_id or "").strip()
    if intersection_model is None or not alignment_ref:
        return []
    output: list[float] = []
    try:
        edge_network = IntersectionEvaluationService().evaluate_edge_network(intersection_model)
    except Exception:
        return []
    for row in list(getattr(edge_network, "edge_rows", []) or []):
        if str(getattr(row, "edge_family", "") or "") != "curb_return":
            continue
        contact_refs = dict(getattr(row, "contact_station_refs", {}) or {})
        output.extend([float(value) for value in list(contact_refs.get(alignment_ref, ()) or ()) if _is_finite_number(value)])
    return _unique_station_values(output)


def _intersection_center_control_stations(center_station: float, curb_radius: float) -> list[float]:
    radius = max(float(curb_radius or 0.0), 0.0)
    if radius <= 1.0e-9:
        return [float(center_station)]
    return [
        float(center_station) - radius,
        float(center_station) - radius * 0.5,
        float(center_station),
        float(center_station) + radius * 0.5,
        float(center_station) + radius,
    ]


def _intersection_default_curb_radius(intersection_model) -> float:
    radii = [
        max(float(getattr(row, "radius", 0.0) or 0.0), 0.0)
        for row in list(getattr(intersection_model, "curb_return_policy_rows", []) or [])
        if str(getattr(row, "status", "active") or "active") != "disabled"
    ]
    return max(radii) if radii else 0.0


def _unique_station_values(values: list[float], *, tolerance: float = 1.0e-6) -> list[float]:
    output: list[float] = []
    for value in sorted(float(v) for v in list(values or []) if _is_finite_number(v)):
        if output and abs(output[-1] - value) <= tolerance:
            continue
        output.append(value)
    return output


def _float_or_none(value) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return number


def _is_finite_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def _clamp_station(value: float, *, station_min: float, station_max: float) -> float:
    return max(float(station_min), min(float(station_max), float(value)))


def _build_applied_sections_centerline3d_result(document):
    try:
        from .cmd_centerline3d import build_document_centerline3d_result

        return build_document_centerline3d_result(document)
    except Exception:
        return None


def _source_status(obj) -> str:
    if obj is None:
        return "missing"
    return str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "ok")


def _assembly_source_status(document) -> str:
    subassembly_objs = list_v1_assembly_subassembly_models(document)
    if subassembly_objs:
        if len(subassembly_objs) == 1:
            return "Subassembly source: " + _source_status(subassembly_objs[0])
        return f"{len(subassembly_objs)} Subassembly source model(s)"
    return "missing"


def _applied_sections_source_diagnostics(document) -> list[str]:
    diagnostics: list[str] = []
    alignment_obj = find_v1_alignment(document)
    profile_obj = find_v1_profile(document)
    subassembly_objs = list_v1_assembly_subassembly_models(document)
    region_obj = find_v1_region_model(document)
    stationing_obj = find_v1_stationing(document)
    stations = _station_values(stationing_obj)
    missing = []
    if alignment_obj is None:
        missing.append("Alignment")
    if profile_obj is None:
        missing.append("Profile")
    if not subassembly_objs:
        missing.append("Assembly / Subassembly")
    if region_obj is None:
        missing.append("Regions")
    if not stations:
        missing.append("Stations")
    if missing:
        diagnostics.append("missing_required_sources: " + ", ".join(missing))
        if "Assembly / Subassembly" in missing:
            diagnostics.append(
                "missing_required_sources_detail: Create or apply an Assembly / Subassembly source before Build Sections."
            )
        return diagnostics
    alignment = to_alignment_model(alignment_obj)
    profile = to_profile_model(profile_obj)
    if alignment is None:
        diagnostics.append("alignment_source_not_readable: Alignment source model could not be read.")
        return diagnostics
    if profile is None:
        diagnostics.append("profile_source_not_readable: Profile source model could not be read.")
        return diagnostics

    centerline_result = _build_applied_sections_centerline3d_result(document)
    if centerline_result is None:
        diagnostics.append("missing_centerline3d_result: 3D Centerline could not be evaluated.")
        return diagnostics
    if str(getattr(centerline_result, "status", "") or "") != "ready":
        diagnostics.append(
            "centerline3d_not_ready: "
            + "; ".join(list(getattr(centerline_result, "diagnostic_rows", []) or []) or ["3D Centerline is not ready."])
        )
        return diagnostics

    frame_service = Centerline3DFrameService()
    for station in stations:
        frame = frame_service.resolve_station(centerline_result, station, alignment=alignment, profile=profile)
        if str(getattr(frame, "status", "") or "") == "blocked":
            diagnostics.extend(str(row) for row in list(getattr(frame, "diagnostic_rows", []) or []))
    diagnostics.extend(_applied_sections_preset_source_diagnostics(document))
    return diagnostics


def _applied_sections_preset_source_diagnostics(document) -> list[str]:
    """Return pre-build diagnostics for Assembly/Subassembly preset linkage health."""

    diagnostics: list[str] = []
    preset_versions = _applied_sections_subassembly_preset_version_map(document)
    preset_ids = set(preset_versions.keys())
    for model in (
        to_assembly_subassembly_model(obj)
        for obj in list_v1_assembly_subassembly_models(document)
    ):
        if model is None:
            continue
        for template in list(getattr(model, "template_rows", []) or []):
            for subassembly in list(getattr(template, "subassembly_rows", []) or []):
                if not bool(getattr(subassembly, "enabled", True)):
                    continue
                subassembly_id = str(getattr(subassembly, "subassembly_id", "") or "").strip()
                preset_ref = str(getattr(subassembly, "preset_ref", "") or "").strip()
                preset_version = str(getattr(subassembly, "preset_version", "") or "").strip()
                preset_status = str(getattr(subassembly, "preset_status", "") or "").strip()
                if not preset_ref:
                    continue
                if preset_ref not in preset_ids:
                    diagnostics.append(f"missing_subassembly_preset:{subassembly_id}:{preset_ref}")
                    continue
                library_version = str(preset_versions.get(preset_ref, "") or "").strip()
                if preset_version and library_version and preset_version != library_version:
                    diagnostics.append(
                        f"outdated_subassembly_preset:{subassembly_id}:{preset_ref}:row={preset_version}:library={library_version}"
                    )
    return diagnostics


def _applied_sections_subassembly_preset_version_map(document) -> dict[str, str]:
    output: dict[str, str] = {}
    for library in (
        to_subassembly_preset_library(obj)
        for obj in list_v1_subassembly_preset_libraries(document)
    ):
        if library is None:
            continue
        for preset in list(getattr(library, "subassembly_preset_rows", []) or []):
            preset_id = str(getattr(preset, "preset_id", "") or "").strip()
            if preset_id:
                output[preset_id] = str(getattr(preset, "version", "") or "").strip()
    return output


def _review_status_text(row: dict[str, object]) -> str:
    diagnostics = int(row.get("diagnostic_count", 0) or 0)
    if diagnostics:
        return f"WARN ({diagnostics})"
    return "OK"


def _review_subassembly_summary_text(row: dict[str, object]) -> str:
    subassembly_summary = str(row.get("subassembly_summary", "") or "").strip()
    if subassembly_summary:
        return subassembly_summary
    subassembly_count = int(row.get("subassembly_count", 0) or 0)
    if subassembly_count:
        return str(subassembly_count)
    return "0"


def _display_source_id(value: object, prefix: str) -> str:
    text = str(value or "")
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text


def applied_section_review_row_color(status: object) -> tuple[int, int, int] | None:
    """Return dark-theme-readable Applied Sections review-row background color."""

    return APPLIED_SECTION_REVIEW_ROW_COLORS.get(str(status or "").strip())


def _subassembly_summary(section) -> str:
    subassembly_rows = list(getattr(section, "subassembly_rows", []) or []) if section is not None else []
    if not subassembly_rows:
        return ""
    counts: dict[str, int] = {}
    order: list[str] = []
    for subassembly in subassembly_rows:
        kind = str(getattr(subassembly, "kind", "") or "subassembly").strip() or "subassembly"
        if kind not in counts:
            order.append(kind)
            counts[kind] = 0
        counts[kind] += 1
    return ", ".join(f"{kind}:{counts[kind]}" for kind in order)


def _subassembly_preset_review_summary(section) -> str:
    subassembly_rows = list(getattr(section, "subassembly_rows", []) or []) if section is not None else []
    if not subassembly_rows:
        return ""
    status_counts: dict[str, int] = {}
    linked_refs: list[str] = []
    diagnostic_count = 0
    for subassembly in subassembly_rows:
        preset_ref = str(getattr(subassembly, "preset_ref", "") or "").strip()
        status = str(getattr(subassembly, "preset_status", "") or "").strip()
        if not status:
            status = "linked" if preset_ref else "snapshot"
        status_counts[status] = status_counts.get(status, 0) + 1
        if preset_ref and preset_ref not in linked_refs:
            linked_refs.append(preset_ref)
        diagnostic_count += len(
            [
                value
                for value in list(getattr(subassembly, "diagnostics", []) or [])
                if "subassembly_preset" in str(value or "")
            ]
        )
    parts = [f"{status}:{count}" for status, count in status_counts.items()]
    if linked_refs:
        shown_refs = [_display_source_id(ref, "subassembly-preset:") for ref in linked_refs[:2]]
        ref_text = ",".join(shown_refs)
        if len(linked_refs) > 2:
            ref_text += f",+{len(linked_refs) - 2}"
        parts.append(f"refs={ref_text}")
    if diagnostic_count:
        parts.append(f"preset diagnostics={diagnostic_count}")
    return " | ".join(parts)


def _frame_source_summary(frame) -> str:
    if frame is None:
        return "missing frame"
    notes = str(getattr(frame, "notes", "") or "").strip()
    if "source=centerline3d_source_geometry" in notes:
        return "Centerline3D Source Geometry"
    if "source=centerline3d_result" in notes:
        return "Centerline3D"
    if notes:
        return f"Alignment/Profile fallback | {notes}"
    return "Alignment/Profile fallback"


def _applied_section_diagnostic_count(section) -> int:
    if section is None:
        return 1
    count = len(list(getattr(section, "diagnostic_rows", []) or []))
    for subassembly in list(getattr(section, "subassembly_rows", []) or []):
        count += len(list(getattr(subassembly, "diagnostics", []) or []))
    for point in list(getattr(section, "subassembly_point_rows", []) or []):
        count += len(list(getattr(point, "diagnostics", []) or []))
    for link in list(getattr(section, "subassembly_link_rows", []) or []):
        count += len(list(getattr(link, "diagnostics", []) or []))
    for shape in list(getattr(section, "subassembly_shape_rows", []) or []):
        count += len(list(getattr(shape, "diagnostics", []) or []))
    return count


def _ditch_review_summary(section) -> str:
    if section is None:
        return ""
    subassembly_rows = list(getattr(section, "subassembly_rows", []) or [])
    point_rows = list(getattr(section, "point_rows", []) or [])
    ditch_subassemblies = [row for row in subassembly_rows if str(getattr(row, "kind", "") or "") == "ditch"]
    ditch_points = [row for row in point_rows if str(getattr(row, "point_role", "") or "") == "ditch_surface"]
    if not ditch_subassemblies and not ditch_points:
        return ""
    parts = []
    if ditch_subassemblies:
        sides = sorted({str(getattr(row, "side", "") or "").strip() for row in ditch_subassemblies if str(getattr(row, "side", "") or "").strip()})
        side_text = f" ({'/'.join(sides)})" if sides else ""
        parts.append(f"subassemblies:{len(ditch_subassemblies)}{side_text}")
    if ditch_points:
        parts.append(f"points:{len(ditch_points)}")
    return " | ".join(parts)


def _slope_face_review_summary(section) -> str:
    if section is None:
        return ""
    left_width = float(getattr(section, "daylight_left_width", 0.0) or 0.0)
    right_width = float(getattr(section, "daylight_right_width", 0.0) or 0.0)
    left_slope = float(getattr(section, "daylight_left_slope", 0.0) or 0.0)
    right_slope = float(getattr(section, "daylight_right_slope", 0.0) or 0.0)
    parts = []
    if left_width > 0.0:
        parts.append(f"L {_format_float(left_width)} @ {_format_float(left_slope)}")
    if right_width > 0.0:
        parts.append(f"R {_format_float(right_width)} @ {_format_float(right_slope)}")
    return " / ".join(parts)


def _superelevation_review_summary(section) -> str:
    if section is None:
        return ""
    superelevation_id = str(getattr(section, "active_superelevation_id", "") or "").strip()
    if not superelevation_id:
        return ""
    left = float(getattr(section, "superelevation_left_crossfall", 0.0) or 0.0)
    right = float(getattr(section, "superelevation_right_crossfall", 0.0) or 0.0)
    transition_id = str(getattr(section, "active_superelevation_transition_id", "") or "").strip()
    parts = [
        f"L {_format_float(left)}%",
        f"R {_format_float(right)}%",
    ]
    if transition_id:
        parts.append(_display_source_id(transition_id, "transition:"))
    return " | ".join(parts)


def _intersection_review_summary(section) -> str:
    if section is None:
        return ""
    intersection_id = str(getattr(section, "active_intersection_id", "") or "").strip()
    if not intersection_id:
        return ""
    leg_role = str(getattr(section, "active_intersection_leg_role", "") or "").strip()
    control_area = str(getattr(section, "active_intersection_control_area_id", "") or "").strip()
    parts = [_display_source_id(intersection_id, "intersection:")]
    if leg_role:
        parts.append(leg_role)
    if control_area:
        parts.append(_display_source_id(control_area, f"{intersection_id}:"))
    return " | ".join(parts)


def _diagnostic_summary(section) -> str:
    rows = list(getattr(section, "diagnostic_rows", []) or [])
    subassembly_diagnostics = _subassembly_diagnostic_summary_rows(section)
    if not rows and not subassembly_diagnostics:
        return ""
    values = []
    for row in rows[:2]:
        severity = str(getattr(row, "severity", "") or "").strip()
        kind = str(getattr(row, "kind", "") or "").strip()
        message = str(getattr(row, "message", "") or "").strip()
        label = ":".join(part for part in [severity, kind] if part)
        values.append(f"{label} {message}".strip())
    remaining_slots = max(2 - len(values), 0)
    values.extend(subassembly_diagnostics[:remaining_slots])
    total_count = len(rows) + len(subassembly_diagnostics)
    if total_count > len(values):
        values.append(f"+{total_count - len(values)} more")
    return " | ".join(values)


def _subassembly_diagnostic_summary_rows(section) -> list[str]:
    output: list[str] = []
    if section is None:
        return output
    for subassembly in list(getattr(section, "subassembly_rows", []) or []):
        subassembly_id = _display_source_id(getattr(subassembly, "subassembly_id", ""), "subassembly:")
        for diagnostic in list(getattr(subassembly, "diagnostics", []) or []):
            text = str(diagnostic or "").strip()
            if text:
                output.append(f"{subassembly_id}: {text}")
    return output


def _applied_section_preview_polylines(section, frame):
    fg_points = _applied_section_point_role_vectors(section, "fg_surface")
    subgrade_points = _applied_section_point_role_vectors(section, "subgrade_surface")
    polylines = []
    if len(fg_points) >= 2:
        polylines.append(("fg_surface", fg_points))
    if len(subgrade_points) >= 2:
        polylines.append(("subgrade_surface", subgrade_points))
        for fg_point, subgrade_point in _matched_offset_point_pairs(section, "fg_surface", "subgrade_surface"):
            polylines.append(("subgrade_link", [fg_point, subgrade_point]))
    if fg_points:
        polylines.extend(_applied_section_ditch_point_polylines(section))
        side_slope_polylines = _applied_section_side_slope_point_polylines(section)
        if side_slope_polylines:
            polylines.extend(side_slope_polylines)
        else:
            polylines.extend(_applied_section_daylight_polylines(section, frame, fg_points))
    if polylines:
        return polylines
    return [("fallback_section", _applied_section_preview_points(section, frame))]


def _applied_section_point_role_vectors(section, point_role: str):
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == point_role
    ]
    rows.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    vectors = []
    for point in rows:
        try:
            vectors.append(App.Vector(float(point.x), float(point.y), float(point.z)))
        except Exception:
            pass
    return _unique_preview_points(vectors)


def _applied_section_ditch_point_polylines(section):
    fg_edges = _applied_section_fg_edge_rows(section)
    if len(fg_edges) < 2:
        return []
    ditch_rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    ]
    if not ditch_rows:
        return []

    right_edge = fg_edges[0]
    left_edge = fg_edges[-1]
    polylines = []
    for side_label, edge, direction in (
        ("left", left_edge, 1.0),
        ("right", right_edge, -1.0),
    ):
        edge_offset = float(getattr(edge, "lateral_offset", 0.0) or 0.0)
        side_points = []
        for point in ditch_rows:
            offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
            if (offset - edge_offset) * direction < -1.0e-9:
                continue
            side_points.append(point)
        side_points.sort(key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0) - edge_offset) * direction)
        vectors = [_point_row_vector(edge)]
        vectors.extend(_point_row_vector(point) for point in side_points)
        vectors = _unique_preview_points([vector for vector in vectors if vector is not None])
        if len(vectors) >= 2:
            polylines.append((f"{side_label}_ditch_points", vectors))
    return polylines


def _matched_offset_point_pairs(section, first_role: str, second_role: str):
    first = {
        round(float(getattr(point, "lateral_offset", 0.0) or 0.0), 6): point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == first_role
    }
    second = {
        round(float(getattr(point, "lateral_offset", 0.0) or 0.0), 6): point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == second_role
    }
    pairs = []
    for offset in sorted(set(first).intersection(second)):
        try:
            a = first[offset]
            b = second[offset]
            pairs.append((App.Vector(float(a.x), float(a.y), float(a.z)), App.Vector(float(b.x), float(b.y), float(b.z))))
        except Exception:
            pass
    return pairs


def _applied_section_side_slope_point_polylines(section):
    terminal_edges = _applied_section_terminal_edge_rows(section)
    if terminal_edges is None:
        return []
    left_edge, right_edge = terminal_edges
    point_rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") in {"side_slope_surface", "bench_surface", "daylight_marker"}
    ]
    if not point_rows:
        return []
    polylines = []
    side_specs = [
        ("left", left_edge, 1.0),
        ("right", right_edge, -1.0),
    ]
    for side_label, edge, direction in side_specs:
        edge_offset = float(getattr(edge, "lateral_offset", 0.0) or 0.0)
        side_points = []
        for point in point_rows:
            offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
            if (offset - edge_offset) * float(direction) < -1.0e-9:
                continue
            side_points.append(point)
        side_points.sort(key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0) - edge_offset) * float(direction))
        vectors = [_point_row_vector(edge)]
        vectors.extend(_point_row_vector(point) for point in side_points)
        vectors = _unique_preview_points([vector for vector in vectors if vector is not None])
        if len(vectors) >= 2:
            polylines.append((f"{side_label}_side_slope_points", vectors))
    return polylines


def _applied_section_terminal_edge_rows(section):
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") in {"fg_surface", "ditch_surface"}
    ]
    if not rows:
        return None
    left_edge = max(rows, key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0), float(getattr(point, "z", 0.0) or 0.0)))
    right_edge = min(rows, key=lambda point: (float(getattr(point, "lateral_offset", 0.0) or 0.0), -float(getattr(point, "z", 0.0) or 0.0)))
    return left_edge, right_edge


def _applied_section_fg_edge_rows(section):
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "fg_surface"
    ]
    rows.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
    return rows


def _point_row_vector(point):
    try:
        return App.Vector(float(point.x), float(point.y), float(point.z))
    except Exception:
        return None


def _applied_section_daylight_polylines(section, frame, fg_points):
    if not fg_points:
        return []
    tangent = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal = App.Vector(-math.sin(tangent), math.cos(tangent), 0.0)
    left_daylight = max(float(getattr(section, "daylight_left_width", 0.0) or 0.0), 0.0)
    right_daylight = max(float(getattr(section, "daylight_right_width", 0.0) or 0.0), 0.0)
    left_slope = float(getattr(section, "daylight_left_slope", 0.0) or 0.0)
    right_slope = float(getattr(section, "daylight_right_slope", 0.0) or 0.0)
    polylines = []
    if left_daylight > 0.0:
        left_edge = fg_points[-1]
        polylines.append(("left_slope_face", [left_edge, left_edge + normal * left_daylight + App.Vector(0.0, 0.0, left_slope * left_daylight)]))
    if right_daylight > 0.0:
        right_edge = fg_points[0]
        polylines.append(("right_slope_face", [right_edge, right_edge - normal * right_daylight + App.Vector(0.0, 0.0, right_slope * right_daylight)]))
    return polylines


def _resolve_applied_sections_existing_ground_tin_surface(document):
    try:
        from .cmd_build_corridor import _resolve_corridor_existing_ground_tin_surface

        return _resolve_corridor_existing_ground_tin_surface(document)
    except Exception:
        return None


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


def _applied_section_preview_points(section, frame):
    x = float(getattr(frame, "x", 0.0) or 0.0)
    y = float(getattr(frame, "y", 0.0) or 0.0)
    z = float(getattr(frame, "z", 0.0) or 0.0)
    tangent = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(tangent)
    normal_y = math.cos(tangent)
    left_width = max(float(getattr(section, "surface_left_width", 0.0) or 0.0), 0.0)
    right_width = max(float(getattr(section, "surface_right_width", 0.0) or 0.0), 0.0)
    left_daylight = max(float(getattr(section, "daylight_left_width", 0.0) or 0.0), 0.0)
    right_daylight = max(float(getattr(section, "daylight_right_width", 0.0) or 0.0), 0.0)
    left_slope = float(getattr(section, "daylight_left_slope", 0.0) or 0.0)
    right_slope = float(getattr(section, "daylight_right_slope", 0.0) or 0.0)
    offsets = [
        (left_width + left_daylight, z + left_slope * left_daylight),
        (left_width, z),
        (0.0, z),
        (-right_width, z),
        (-(right_width + right_daylight), z + right_slope * right_daylight),
    ]
    points = []
    for offset, elevation in offsets:
        points.append(App.Vector(x + normal_x * offset, y + normal_y * offset, elevation))
    return _unique_preview_points(points)


def _applied_section_preview_mode(section) -> str:
    point_count = _applied_section_preview_point_count(section)
    return "section_points" if point_count else "width_fallback"


def _applied_section_preview_point_count(section) -> int:
    return len(
        [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "") in {"fg_surface", "subgrade_surface"}
        ]
    )


def _unique_preview_points(points):
    output = []
    for point in list(points or []):
        if output and _same_preview_point(output[-1], point):
            continue
        output.append(point)
    return output


def _same_preview_point(left, right, tolerance: float = 1.0e-7) -> bool:
    try:
        return (
            abs(float(left.x) - float(right.x)) <= tolerance
            and abs(float(left.y) - float(right.y)) <= tolerance
            and abs(float(left.z) - float(right.z)) <= tolerance
        )
    except Exception:
        return False


def _applied_section_stroke_width(points) -> float:
    if not points:
        return 0.1
    xs = [float(point.x) for point in points]
    ys = [float(point.y) for point in points]
    zs = [float(point.z) for point in points]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)
    return max(0.08, min(0.35, span * 0.015))


def _make_applied_section_wire(points):
    clean_points = _unique_preview_points(list(points or []))
    if len(clean_points) < 2 or Part is None:
        return None
    try:
        return Part.makePolygon(clean_points)
    except Exception:
        edges = []
        for start, end in zip(clean_points, clean_points[1:]):
            try:
                if (end - start).Length <= 1.0e-9:
                    continue
                edges.append(Part.makeLine(start, end))
            except Exception:
                pass
        return Part.Compound(edges) if edges else None


def _make_applied_section_segment_stroke(start, end, stroke_width: float):
    width = float(stroke_width or 0.0)
    if width <= 0.0 or Part is None:
        return None
    try:
        direction = end - start
        if direction.Length <= 1.0e-9:
            return None
        tangent = App.Vector(direction)
        tangent.normalize()
        up = App.Vector(0.0, 0.0, 1.0)
        normal = tangent.cross(up)
        if normal.Length <= 1.0e-9:
            normal = App.Vector(1.0, 0.0, 0.0)
        normal.normalize()
        normal = normal * (width * 0.5)
        points = [
            start + normal,
            end + normal,
            end - normal,
            start - normal,
            start + normal,
        ]
        face = Part.Face(Part.makePolygon(points))
        return face.extrude(App.Vector(0.0, 0.0, max(0.04, width * 0.2)))
    except Exception:
        return None


def _style_applied_section_preview_object(obj) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        daylight_color = (0.10, 0.85, 0.25)
        vobj.Visibility = True
        vobj.DisplayMode = "Wireframe"
        vobj.ShapeColor = daylight_color
        vobj.LineColor = daylight_color
        vobj.PointColor = daylight_color
        vobj.LineWidth = 5.0
        vobj.PointSize = 1.0
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if hasattr(vobj, "Lighting"):
            try:
                vobj.Lighting = "Two side"
            except Exception:
                pass
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0
    except Exception:
        pass


def _style_applied_section_station_marker(obj) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        vobj.Visibility = True
        vobj.DisplayMode = "Wireframe"
        vobj.DrawStyle = "Solid"
        vobj.ShapeColor = (1.0, 0.86, 0.05)
        vobj.LineColor = (0.02, 0.02, 0.02)
        vobj.PointColor = (1.0, 0.95, 0.1)
        vobj.LineWidth = 4.0
        vobj.PointSize = 1.0
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0
    except Exception:
        pass


def _applied_section_station_marker_shape(center, radius: float, frame):
    """Build a wire target marker that stays legible without shaded sphere artifacts."""

    radius = max(float(radius or 0.0), 0.25)
    tangent_deg = float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0)
    try:
        import math

        angle = math.radians(tangent_deg)
        tangent = App.Vector(math.cos(angle), math.sin(angle), 0.0)
        normal = App.Vector(-math.sin(angle), math.cos(angle), 0.0)
    except Exception:
        tangent = App.Vector(1.0, 0.0, 0.0)
        normal = App.Vector(0.0, 1.0, 0.0)
    vertical = App.Vector(0.0, 0.0, 1.0)
    shapes = []
    try:
        shapes.append(Part.makeCircle(radius, center, vertical))
    except Exception:
        pass
    for axis, scale in ((tangent, 1.35), (normal, 1.35), (vertical, 0.9)):
        try:
            factor = radius * scale
            delta = App.Vector(float(axis.x) * factor, float(axis.y) * factor, float(axis.z) * factor)
            shapes.append(Part.makeLine(center - delta, center + delta))
        except Exception:
            pass
    return Part.Compound(shapes) if shapes else Part.makeSphere(radius, center)


def _applied_section_station_marker_radius(section) -> float:
    frame = getattr(section, "frame", None)
    points = []
    if frame is not None:
        points = [point for _role, row_points in _applied_section_preview_polylines(section, frame) for point in list(row_points or [])]
    if len(points) >= 2:
        xs = [float(point.x) for point in points]
        ys = [float(point.y) for point in points]
        zs = [float(point.z) for point in points]
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)
        return max(0.25, min(span * 0.06, 2.5))
    return 0.6


def _set_preview_string_property(obj, name: str, value: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_float_property(obj, name: str, value: float) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyFloat", name, "CorridorRoad", name)
        setattr(obj, name, float(value or 0.0))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _fit_selected_preview() -> None:
    if Gui is None:
        return
    try:
        if hasattr(Gui, "updateGui"):
            Gui.updateGui()
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


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1AppliedSections", CmdV1AppliedSections())
