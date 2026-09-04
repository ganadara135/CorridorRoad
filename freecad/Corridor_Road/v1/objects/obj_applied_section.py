"""FreeCAD result object for v1 AppliedSectionSet rows."""

from __future__ import annotations

import json
import math

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from ..common.diagnostics import DiagnosticMessage
from ..models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
    AppliedSectionSubassemblyLink,
    AppliedSectionSubassemblyPoint,
    AppliedSectionSubassemblyRow,
    AppliedSectionSubassemblyShape,
)
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from .persistence_payload_adapter import (
    ensure_incremental_result_properties,
    ensure_model_payload_properties,
    make_incremental_record,
    read_model_payload,
    write_incremental_record,
    write_model_payload,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


# Applied Sections can be large because each evaluated station carries point,
# subassembly, diagnostic, and context rows.  Review consumers commonly ask for
# the same accepted result several times during one UI interaction.  Cache only
# payload-backed results and key them by the persisted identity so a write or a
# source/result fingerprint change naturally invalidates the entry.
_APPLIED_SECTION_SET_PAYLOAD_CACHE: dict[
    int, tuple[tuple[str, str, str], AppliedSectionSet]
] = {}
_APPLIED_SECTION_SET_PAYLOAD_CACHE_LIMIT = 16


def _applied_section_set_payload_cache_key(obj) -> tuple[str, str, str] | None:
    payload_schema = str(getattr(obj, "PayloadSchemaVersion", "") or "")
    checksum = str(getattr(obj, "ModelPayloadChecksum", "") or "")
    fingerprint = str(getattr(obj, "SourceFingerprint", "") or "")
    if not checksum:
        return None
    return payload_schema, checksum, fingerprint


def clear_applied_section_set_payload_cache(obj=None) -> None:
    """Discard cached payload restoration for one result object or all objects."""

    if obj is None:
        _APPLIED_SECTION_SET_PAYLOAD_CACHE.clear()
        return
    _APPLIED_SECTION_SET_PAYLOAD_CACHE.pop(id(obj), None)


def _cache_applied_section_set_payload(
    obj,
    cache_key: tuple[str, str, str],
    model: AppliedSectionSet,
) -> None:
    _APPLIED_SECTION_SET_PAYLOAD_CACHE[id(obj)] = (cache_key, model)
    while len(_APPLIED_SECTION_SET_PAYLOAD_CACHE) > _APPLIED_SECTION_SET_PAYLOAD_CACHE_LIMIT:
        oldest_object_id = next(iter(_APPLIED_SECTION_SET_PAYLOAD_CACHE))
        _APPLIED_SECTION_SET_PAYLOAD_CACHE.pop(oldest_object_id, None)


class V1AppliedSectionSetObject:
    """Document object proxy that stores v1 AppliedSectionSet result summaries."""

    Type = "V1AppliedSectionSet"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_applied_section_set_properties(obj)

    def execute(self, obj):
        ensure_v1_applied_section_set_properties(obj)
        if str(getattr(obj, "ReviewShapeStatus", "") or "") == "built":
            build_v1_applied_section_set_review_shape(obj)
        else:
            _set_empty_applied_section_set_shape(obj)
        return


class ViewProviderV1AppliedSectionSet:
    """Simple view provider for v1 AppliedSectionSet result objects."""

    Type = "ViewProviderV1AppliedSectionSet"

    def __init__(self, vobj):
        vobj.Proxy = self
        _style_applied_section_set_view(vobj, visible=False)

    def onChanged(self, vobj, prop):
        if str(prop or "") != "Visibility":
            return
        try:
            if bool(getattr(vobj, "Visibility", False)):
                build_v1_applied_section_set_review_shape(getattr(vobj, "Object", None), visible=True)
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("sections.svg")
        except Exception:
            return ""


def ensure_v1_applied_section_set_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 AppliedSectionSet result properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "AppliedSectionSetId", "CorridorRoad", "v1 applied section set id")
    _add_property(obj, "App::PropertyString", "CorridorId", "CorridorRoad", "corridor id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "alignment id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "StationCount", "Stations", "applied section station count")
    _add_property(obj, "App::PropertyStringList", "StationRowIds", "Stations", "station row ids")
    _add_property(obj, "App::PropertyFloatList", "StationValues", "Stations", "station values")
    _add_property(obj, "App::PropertyStringList", "AppliedSectionIds", "Stations", "applied section ids")
    _add_property(obj, "App::PropertyStringList", "AlignmentIds", "Stations", "section alignment ids")
    _add_property(obj, "App::PropertyStringList", "StationKinds", "Stations", "station kinds")
    _add_property(obj, "App::PropertyFloatList", "FrameXValues", "Frames", "applied section frame x values")
    _add_property(obj, "App::PropertyFloatList", "FrameYValues", "Frames", "applied section frame y values")
    _add_property(obj, "App::PropertyFloatList", "FrameZValues", "Frames", "applied section frame z values")
    _add_property(obj, "App::PropertyFloatList", "FrameTangentDirections", "Frames", "frame tangent directions in degrees")
    _add_property(obj, "App::PropertyFloatList", "FrameProfileGrades", "Frames", "profile grades")
    _add_property(obj, "App::PropertyStringList", "FrameAlignmentStatuses", "Frames", "alignment statuses")
    _add_property(obj, "App::PropertyStringList", "FrameProfileStatuses", "Frames", "profile statuses")
    _add_property(obj, "App::PropertyStringList", "FrameSourceModes", "Frames", "frame source modes")
    _add_property(obj, "App::PropertyStringList", "FrameSourceStatuses", "Frames", "frame source statuses")
    _add_property(obj, "App::PropertyStringList", "FrameSourceDiagnosticRows", "Frames", "frame source diagnostics by section")
    _add_property(obj, "App::PropertyStringList", "FrameNotes", "Frames", "frame source and diagnostic notes")
    _add_property(obj, "App::PropertyFloatList", "SurfaceLeftWidths", "Surface", "left design surface widths")
    _add_property(obj, "App::PropertyFloatList", "SurfaceRightWidths", "Surface", "right design surface widths")
    _add_property(obj, "App::PropertyFloatList", "SubgradeDepths", "Surface", "subgrade depths")
    _add_property(obj, "App::PropertyFloatList", "DaylightLeftWidths", "Surface", "left daylight widths")
    _add_property(obj, "App::PropertyFloatList", "DaylightRightWidths", "Surface", "right daylight widths")
    _add_property(obj, "App::PropertyFloatList", "DaylightLeftSlopes", "Surface", "left daylight slopes")
    _add_property(obj, "App::PropertyFloatList", "DaylightRightSlopes", "Surface", "right daylight slopes")
    _add_property(obj, "App::PropertyStringList", "SuperelevationIds", "Superelevation", "active superelevation ids")
    _add_property(obj, "App::PropertyFloatList", "SuperelevationLeftCrossfalls", "Superelevation", "left effective crossfall percent")
    _add_property(obj, "App::PropertyFloatList", "SuperelevationRightCrossfalls", "Superelevation", "right effective crossfall percent")
    _add_property(obj, "App::PropertyStringList", "SuperelevationTransitionIds", "Superelevation", "active superelevation transition ids")
    _add_property(obj, "App::PropertyStringList", "SuperelevationSourceRows", "Superelevation", "superelevation source rows by section")
    _add_property(obj, "App::PropertyStringList", "IntersectionIds", "Intersections", "active intersection ids")
    _add_property(obj, "App::PropertyStringList", "IntersectionControlAreaIds", "Intersections", "active intersection control area ids")
    _add_property(obj, "App::PropertyStringList", "IntersectionLegIds", "Intersections", "active intersection leg ids")
    _add_property(obj, "App::PropertyStringList", "IntersectionLegRoles", "Intersections", "active intersection leg roles")
    _add_property(obj, "App::PropertyStringList", "IntersectionControlRegionRows", "Intersections", "active intersection control region refs by section")
    _add_property(obj, "App::PropertyStringList", "IntersectionGradingPolicyRefs", "Intersections", "active intersection grading policy refs")
    _add_property(obj, "App::PropertyStringList", "IntersectionSourceStatuses", "Intersections", "active intersection source status by section")
    _add_property(obj, "App::PropertyStringList", "IntersectionSourceDiagnosticRows", "Intersections", "active intersection source diagnostics by section")
    _add_property(obj, "App::PropertyStringList", "IntersectionSourceStageRows", "Intersections", "active intersection source stage rows by section")
    _add_property(obj, "App::PropertyStringList", "IntersectionDiagnosticRows", "Intersections", "intersection context diagnostics by section")
    _add_property(obj, "App::PropertyStringList", "PointRows", "Surface", "applied section point rows")
    _add_property(obj, "App::PropertyStringList", "SubassemblyRows", "Resolved Context", "applied section subassembly rows")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPointRows", "Resolved Context", "evaluated subassembly point rows")
    _add_property(obj, "App::PropertyStringList", "SubassemblyLinkRows", "Resolved Context", "evaluated subassembly link rows")
    _add_property(obj, "App::PropertyStringList", "SubassemblyShapeRows", "Resolved Context", "evaluated subassembly shape rows")
    _add_property(obj, "App::PropertyStringList", "RegionIds", "Resolved Context", "resolved region ids")
    _add_property(obj, "App::PropertyStringList", "AssemblyIds", "Resolved Context", "resolved assembly ids")
    _add_property(obj, "App::PropertyStringList", "TemplateIds", "Resolved Context", "resolved template ids")
    _add_property(obj, "App::PropertyStringList", "ActiveStructureRows", "Resolved Context", "active structure ids by section")
    _add_property(obj, "App::PropertyStringList", "ActiveStructureRuleRows", "Resolved Context", "active structure interaction rule ids by section")
    _add_property(obj, "App::PropertyStringList", "ActiveStructureInfluenceZoneRows", "Resolved Context", "active structure influence zone ids by section")
    _add_property(obj, "App::PropertyStringList", "StructureDiagnosticRows", "Resolved Context", "structure context diagnostic rows")
    _add_property(obj, "App::PropertyIntegerList", "SubassemblyCounts", "Resolved Context", "subassembly counts")
    _add_property(obj, "App::PropertyIntegerList", "DiagnosticCounts", "Diagnostics", "diagnostic counts")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "diagnostic summary rows")
    _add_property(obj, "App::PropertyInteger", "SourceSectionCount", "Diagnostics", "non-supplemental applied section count")
    _add_property(obj, "App::PropertyInteger", "SupplementalSectionCount", "Diagnostics", "supplemental applied section count")
    _add_property(obj, "App::PropertyInteger", "TotalSectionCount", "Diagnostics", "total applied section count")
    _add_property(obj, "App::PropertyStringList", "SectionKindCounts", "Diagnostics", "applied section count by station kind")
    _add_property(obj, "App::PropertyStringList", "CenterlineSourceModeCounts", "Diagnostics", "applied section count by consumed centerline source mode")
    _add_property(obj, "App::PropertyStringList", "CenterlineSourceStatusCounts", "Diagnostics", "applied section count by consumed centerline source status")
    _add_property(obj, "App::PropertyInteger", "CenterlineFallbackCount", "Diagnostics", "applied section frames using a centerline fallback")
    _add_property(obj, "App::PropertyInteger", "OverlapClipDiagnosticCount", "Diagnostics", "applied section overlap clipping diagnostic count")
    _add_property(obj, "App::PropertyInteger", "DitchShapeInferenceDiagnosticCount", "Diagnostics", "ditch shape compatibility diagnostic count")
    _add_property(obj, "App::PropertyInteger", "DaylightFallbackDiagnosticCount", "Diagnostics", "daylight fallback diagnostic count")
    _add_property(obj, "App::PropertyInteger", "IntersectionSourceSectionCount", "Diagnostics", "applied sections with active intersection source context")
    _add_property(obj, "App::PropertyInteger", "IntersectionSourceWarningCount", "Diagnostics", "applied sections with warning intersection source context")
    _add_property(obj, "App::PropertyInteger", "IntersectionSourceDiagnosticCount", "Diagnostics", "intersection source diagnostic row count")
    _add_property(obj, "App::PropertyStringList", "IntersectionSourceStatusCounts", "Diagnostics", "intersection source status counts")
    _add_property(obj, "App::PropertyString", "IntersectionSourceSummary", "Diagnostics", "compact intersection source summary")
    _add_property(obj, "App::PropertyInteger", "AppliedSectionDiagnosticCount", "Diagnostics", "total applied section diagnostic row count")
    _add_property(obj, "App::PropertyStringList", "AppliedSectionDiagnosticKinds", "Diagnostics", "applied section diagnostic kind counts")
    _add_property(obj, "App::PropertyString", "AppliedSectionDiagnosticSummary", "Diagnostics", "compact applied section diagnostic summary")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")
    _add_property(obj, "App::PropertyString", "ReviewShapeStatus", "Review", "full review shape build status")
    _add_property(obj, "App::PropertyInteger", "ReviewShapeStationCount", "Review", "station count used by the full review shape")
    ensure_model_payload_properties(obj, add_property=_add_property)
    ensure_incremental_result_properties(obj, add_property=_add_property)

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1AppliedSectionSet"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "AppliedSectionSetId", "") or ""):
        obj.AppliedSectionSetId = f"applied-sections:{str(getattr(obj, 'Name', '') or 'v1')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_applied_section_set"
    if not str(getattr(obj, "ReviewShapeStatus", "") or ""):
        obj.ReviewShapeStatus = "not_built"


def create_or_update_v1_applied_section_set_object(
    document=None,
    applied_section_set: AppliedSectionSet | None = None,
    *,
    project=None,
    object_name: str = "V1AppliedSectionSet",
    label: str = "Applied Sections",
):
    """Create or update the durable v1 AppliedSectionSet result object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 AppliedSectionSet creation.")
    if applied_section_set is None:
        applied_section_set = AppliedSectionSet(
            schema_version=1,
            project_id=_project_id(project),
            applied_section_set_id="applied-sections:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        try:
            obj = doc.addObject("Part::FeaturePython", object_name)
        except Exception:
            obj = doc.addObject("App::FeaturePython", object_name)
        V1AppliedSectionSetObject(obj)
        try:
            ViewProviderV1AppliedSectionSet(obj.ViewObject)
        except Exception:
            pass
    else:
        V1AppliedSectionSetObject(obj)
    _style_applied_section_set_view(getattr(obj, "ViewObject", None), visible=False)
    update_v1_applied_section_set_object(obj, applied_section_set, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_applied_section_set_object(obj, applied_section_set: AppliedSectionSet, *, label: str = "Applied Sections"):
    """Write AppliedSectionSet result summaries into a FreeCAD object."""

    clear_applied_section_set_payload_cache(obj)
    ensure_v1_applied_section_set_properties(obj)
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    sections = list(getattr(applied_section_set, "sections", []) or [])
    section_by_id = {str(section.applied_section_id): section for section in sections}

    obj.Label = label
    obj.SchemaVersion = int(getattr(applied_section_set, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(applied_section_set, "project_id", "") or "corridorroad-v1")
    obj.AppliedSectionSetId = str(getattr(applied_section_set, "applied_section_set_id", "") or "applied-sections:main")
    obj.CorridorId = str(getattr(applied_section_set, "corridor_id", "") or "")
    obj.AlignmentId = str(getattr(applied_section_set, "alignment_id", "") or "")
    obj.CRRecordKind = "v1_applied_section_set"
    obj.StationCount = len(station_rows)
    obj.StationRowIds = [str(row.station_row_id) for row in station_rows]
    obj.StationValues = [float(row.station) for row in station_rows]
    obj.AppliedSectionIds = [str(row.applied_section_id) for row in station_rows]
    obj.AlignmentIds = [str(getattr(section_by_id.get(str(row.applied_section_id)), "alignment_id", "") or getattr(applied_section_set, "alignment_id", "") or "") for row in station_rows]
    obj.StationKinds = [str(row.kind) for row in station_rows]
    frames = [_section_frame(section_by_id.get(str(row.applied_section_id))) for row in station_rows]
    obj.FrameXValues = [float(getattr(frame, "x", 0.0) or 0.0) for frame in frames]
    obj.FrameYValues = [float(getattr(frame, "y", 0.0) or 0.0) for frame in frames]
    obj.FrameZValues = [float(getattr(frame, "z", 0.0) or 0.0) for frame in frames]
    obj.FrameTangentDirections = [float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0) for frame in frames]
    obj.FrameProfileGrades = [float(getattr(frame, "profile_grade", 0.0) or 0.0) for frame in frames]
    obj.FrameAlignmentStatuses = [str(getattr(frame, "alignment_status", "") or "") for frame in frames]
    obj.FrameProfileStatuses = [str(getattr(frame, "profile_status", "") or "") for frame in frames]
    obj.FrameSourceModes = [_frame_source_mode(frame) for frame in frames]
    obj.FrameSourceStatuses = [_frame_source_status(frame) for frame in frames]
    obj.FrameSourceDiagnosticRows = _section_frame_source_diagnostic_rows(station_rows, section_by_id)
    obj.FrameNotes = [str(getattr(frame, "notes", "") or "") for frame in frames]
    obj.SurfaceLeftWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "surface_left_width", 0.0) or 0.0) for row in station_rows]
    obj.SurfaceRightWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "surface_right_width", 0.0) or 0.0) for row in station_rows]
    obj.SubgradeDepths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "subgrade_depth", 0.0) or 0.0) for row in station_rows]
    obj.DaylightLeftWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_left_width", 0.0) or 0.0) for row in station_rows]
    obj.DaylightRightWidths = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_right_width", 0.0) or 0.0) for row in station_rows]
    obj.DaylightLeftSlopes = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_left_slope", 0.0) or 0.0) for row in station_rows]
    obj.DaylightRightSlopes = [float(getattr(section_by_id.get(str(row.applied_section_id)), "daylight_right_slope", 0.0) or 0.0) for row in station_rows]
    obj.SuperelevationIds = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_superelevation_id", "") or "") for row in station_rows]
    obj.SuperelevationLeftCrossfalls = [float(getattr(section_by_id.get(str(row.applied_section_id)), "superelevation_left_crossfall", 0.0) or 0.0) for row in station_rows]
    obj.SuperelevationRightCrossfalls = [float(getattr(section_by_id.get(str(row.applied_section_id)), "superelevation_right_crossfall", 0.0) or 0.0) for row in station_rows]
    obj.SuperelevationTransitionIds = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_superelevation_transition_id", "") or "") for row in station_rows]
    obj.SuperelevationSourceRows = _section_list_rows(station_rows, section_by_id, "superelevation_source_rows")
    obj.IntersectionIds = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_intersection_id", "") or "") for row in station_rows]
    obj.IntersectionControlAreaIds = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_intersection_control_area_id", "") or "") for row in station_rows]
    obj.IntersectionLegIds = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_intersection_leg_id", "") or "") for row in station_rows]
    obj.IntersectionLegRoles = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_intersection_leg_role", "") or "") for row in station_rows]
    obj.IntersectionControlRegionRows = _section_list_rows(station_rows, section_by_id, "active_intersection_control_region_refs")
    obj.IntersectionGradingPolicyRefs = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_intersection_grading_policy_ref", "") or "") for row in station_rows]
    obj.IntersectionSourceStatuses = [str(getattr(section_by_id.get(str(row.applied_section_id)), "active_intersection_source_status", "") or "") for row in station_rows]
    obj.IntersectionSourceDiagnosticRows = _section_list_rows(station_rows, section_by_id, "active_intersection_source_diagnostic_rows")
    obj.IntersectionSourceStageRows = _section_list_rows(station_rows, section_by_id, "active_intersection_source_stage_rows")
    obj.IntersectionDiagnosticRows = _section_list_rows(station_rows, section_by_id, "intersection_diagnostic_rows")
    obj.PointRows = _point_rows(station_rows, section_by_id)
    obj.SubassemblyRows = _subassembly_rows(station_rows, section_by_id)
    obj.SubassemblyPointRows = _subassembly_point_rows(station_rows, section_by_id)
    obj.SubassemblyLinkRows = _subassembly_link_rows(station_rows, section_by_id)
    obj.SubassemblyShapeRows = _subassembly_shape_rows(station_rows, section_by_id)
    obj.RegionIds = [str(getattr(section_by_id.get(row.applied_section_id), "region_id", "") or "") for row in station_rows]
    obj.AssemblyIds = [str(getattr(section_by_id.get(row.applied_section_id), "assembly_id", "") or "") for row in station_rows]
    obj.TemplateIds = [str(getattr(section_by_id.get(row.applied_section_id), "template_id", "") or "") for row in station_rows]
    obj.ActiveStructureRows = _section_list_rows(station_rows, section_by_id, "active_structure_ids")
    obj.ActiveStructureRuleRows = _section_list_rows(station_rows, section_by_id, "active_structure_rule_ids")
    obj.ActiveStructureInfluenceZoneRows = _section_list_rows(station_rows, section_by_id, "active_structure_influence_zone_ids")
    obj.StructureDiagnosticRows = _section_list_rows(station_rows, section_by_id, "structure_diagnostic_rows")
    _clear_existing_property(obj, "CompatibilityRowCounts")
    obj.SubassemblyCounts = [len(list(getattr(section_by_id.get(row.applied_section_id), "subassembly_rows", []) or [])) for row in station_rows]
    obj.DiagnosticCounts = [len(list(getattr(section_by_id.get(row.applied_section_id), "diagnostic_rows", []) or [])) for row in station_rows]
    obj.DiagnosticRows = _diagnostic_rows(sections)
    _set_applied_section_diagnostic_summary(obj, station_rows, sections)
    obj.SourceRefs = [str(ref) for ref in list(getattr(applied_section_set, "source_refs", []) or []) if str(ref)]
    result_fingerprint = write_model_payload(
        obj,
        applied_section_set,
        model_type="AppliedSectionSet",
        row_fields=("station_rows", "sections"),
        required_refs=("project_id", "applied_section_set_id"),
    )
    write_incremental_record(
        obj,
        make_incremental_record(
            stage_name="applied_sections",
            result_fingerprint=result_fingerprint,
            consumed_source_refs=getattr(applied_section_set, "source_refs", ()),
        ),
    )
    obj.ReviewShapeStatus = "not_built"
    obj.ReviewShapeStationCount = 0
    _set_empty_applied_section_set_shape(obj)
    _style_applied_section_set_view(getattr(obj, "ViewObject", None), visible=False)
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def build_v1_applied_section_set_review_shape(obj, *, visible: bool | None = None):
    """Build and attach the full all-station review shape on demand."""

    if obj is None:
        return None
    ensure_v1_applied_section_set_properties(obj)
    shape = build_v1_applied_section_set_shape(obj)
    if shape is not None:
        try:
            obj.Shape = shape
            obj.ReviewShapeStatus = "built"
            obj.ReviewShapeStationCount = int(getattr(obj, "StationCount", 0) or 0)
        except Exception:
            pass
    _style_applied_section_set_view(getattr(obj, "ViewObject", None), visible=visible)
    return shape


def _set_empty_applied_section_set_shape(obj) -> None:
    if obj is None or Part is None:
        return
    try:
        obj.Shape = Part.Shape()
    except Exception:
        pass


def _style_applied_section_set_view(vobj, *, visible: bool | None = None) -> None:
    """Style the whole AppliedSectionSet review shape as a quiet, hidden reference layer."""

    if vobj is None:
        return
    try:
        review_color = (0.58, 0.70, 0.88)
        vobj.LineColor = review_color
        vobj.PointColor = review_color
        vobj.ShapeColor = review_color
        vobj.LineWidth = 1.0
        vobj.PointSize = 3.0
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if visible is not None:
            target = bool(visible)
            if bool(getattr(vobj, "Visibility", False)) != target:
                vobj.Visibility = target
    except Exception:
        pass


def build_v1_applied_section_set_shape(obj):
    """Build a hidden-by-default 3D review shape for the whole AppliedSectionSet."""

    if App is None or Part is None:
        return None
    ensure_v1_applied_section_set_properties(obj)
    section_ids = list(getattr(obj, "AppliedSectionIds", []) or [])
    point_rows_by_section = _parse_point_rows(getattr(obj, "PointRows", []) or [])
    edges = []
    for index, section_id in enumerate(section_ids):
        section_key = str(section_id or "")
        point_rows = point_rows_by_section.get(section_key, [])
        for points in _applied_section_display_point_groups(point_rows):
            edge = _display_edge_from_applied_points(points)
            if edge is not None:
                edges.append(edge)
        if point_rows:
            continue
        fallback_edge = _fallback_section_width_edge(obj, index)
        if fallback_edge is not None:
            edges.append(fallback_edge)
    if not edges:
        return Part.Shape()
    if len(edges) == 1:
        return edges[0]
    return Part.Compound(edges)


def _applied_section_display_point_groups(point_rows: list[AppliedSectionPoint]) -> list[list[AppliedSectionPoint]]:
    rows = list(point_rows or [])
    if not rows:
        return []
    role_groups = [
        {"fg_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"},
        {"subgrade_surface"},
    ]
    output: list[list[AppliedSectionPoint]] = []
    for roles in role_groups:
        points = [point for point in rows if str(getattr(point, "point_role", "") or "") in roles]
        points.sort(key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
        unique_points = _unique_display_points(points)
        if len(unique_points) >= 2:
            output.append(unique_points)
    return output


def _unique_display_points(points: list[AppliedSectionPoint]) -> list[AppliedSectionPoint]:
    output: list[AppliedSectionPoint] = []
    for point in list(points or []):
        if output:
            previous = output[-1]
            if (
                abs(float(getattr(point, "x", 0.0) or 0.0) - float(getattr(previous, "x", 0.0) or 0.0)) <= 1.0e-9
                and abs(float(getattr(point, "y", 0.0) or 0.0) - float(getattr(previous, "y", 0.0) or 0.0)) <= 1.0e-9
                and abs(float(getattr(point, "z", 0.0) or 0.0) - float(getattr(previous, "z", 0.0) or 0.0)) <= 1.0e-9
            ):
                continue
        output.append(point)
    return output


def _display_edge_from_applied_points(points: list[AppliedSectionPoint]):
    vectors = [
        App.Vector(
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0),
        )
        for point in list(points or [])
    ]
    if len(vectors) < 2:
        return None
    try:
        return Part.makePolygon(vectors)
    except Exception:
        edges = []
        for start, end in zip(vectors, vectors[1:]):
            try:
                if (end - start).Length > 1.0e-9:
                    edges.append(Part.makeLine(start, end))
            except Exception:
                pass
        if not edges:
            return None
        return Part.Compound(edges) if len(edges) > 1 else edges[0]


def _fallback_section_width_edge(obj, index: int):
    frame_x = _float_value(getattr(obj, "FrameXValues", []), index, 0.0)
    frame_y = _float_value(getattr(obj, "FrameYValues", []), index, 0.0)
    frame_z = _float_value(getattr(obj, "FrameZValues", []), index, 0.0)
    heading = math.radians(_float_value(getattr(obj, "FrameTangentDirections", []), index, 0.0))
    normal_x = -math.sin(heading)
    normal_y = math.cos(heading)
    left_width = _float_value(getattr(obj, "SurfaceLeftWidths", []), index, 0.0)
    right_width = _float_value(getattr(obj, "SurfaceRightWidths", []), index, 0.0)
    if left_width <= 0.0 and right_width <= 0.0:
        return None
    left = App.Vector(frame_x + normal_x * left_width, frame_y + normal_y * left_width, frame_z)
    right = App.Vector(frame_x - normal_x * right_width, frame_y - normal_y * right_width, frame_z)
    try:
        return Part.makeLine(left, right)
    except Exception:
        return None


def to_applied_section_set(obj) -> AppliedSectionSet | None:
    """Build a summary AppliedSectionSet from a v1 result FreeCAD object."""

    if not _is_v1_applied_section_set(obj):
        return None
    ensure_v1_applied_section_set_properties(obj)
    payload_cache_key = _applied_section_set_payload_cache_key(obj)
    cached = _APPLIED_SECTION_SET_PAYLOAD_CACHE.get(id(obj))
    if cached is not None and cached[0] == payload_cache_key:
        return cached[1]
    payload_result = read_model_payload(obj, expected_model_type="AppliedSectionSet", model_class=AppliedSectionSet)
    if payload_result is not None:
        model = payload_result.model if payload_result.accepted else None
        if model is not None and payload_cache_key is not None:
            _cache_applied_section_set_payload(obj, payload_cache_key, model)
        elif cached is not None:
            clear_applied_section_set_payload_cache(obj)
        return model
    station_values = _float_list(getattr(obj, "StationValues", []) or [])
    section_ids = list(getattr(obj, "AppliedSectionIds", []) or [])
    station_rows: list[AppliedSectionStationRow] = []
    sections: list[AppliedSection] = []
    point_rows_by_section = _parse_point_rows(getattr(obj, "PointRows", []) or [])
    active_structures_by_section = _parse_section_list_rows(getattr(obj, "ActiveStructureRows", []) or [])
    active_rules_by_section = _parse_section_list_rows(getattr(obj, "ActiveStructureRuleRows", []) or [])
    active_zones_by_section = _parse_section_list_rows(getattr(obj, "ActiveStructureInfluenceZoneRows", []) or [])
    structure_diagnostics_by_section = _parse_section_list_rows(getattr(obj, "StructureDiagnosticRows", []) or [])
    superelevation_sources_by_section = _parse_section_list_rows(getattr(obj, "SuperelevationSourceRows", []) or [])
    frame_source_diagnostics_by_section = _parse_section_list_rows(getattr(obj, "FrameSourceDiagnosticRows", []) or [])
    intersection_control_regions_by_section = _parse_section_list_rows(getattr(obj, "IntersectionControlRegionRows", []) or [])
    intersection_source_diagnostics_by_section = _parse_section_list_rows(getattr(obj, "IntersectionSourceDiagnosticRows", []) or [])
    intersection_source_stages_by_section = _parse_section_list_rows(getattr(obj, "IntersectionSourceStageRows", []) or [])
    intersection_diagnostics_by_section = _parse_section_list_rows(getattr(obj, "IntersectionDiagnosticRows", []) or [])
    diagnostics_by_section = _parse_diagnostic_rows(getattr(obj, "DiagnosticRows", []) or [])
    subassembly_rows_by_section = _parse_subassembly_rows(getattr(obj, "SubassemblyRows", []) or [])
    subassembly_point_rows_by_section = _parse_subassembly_point_rows(getattr(obj, "SubassemblyPointRows", []) or [])
    subassembly_link_rows_by_section = _parse_subassembly_link_rows(getattr(obj, "SubassemblyLinkRows", []) or [])
    subassembly_shape_rows_by_section = _parse_subassembly_shape_rows(getattr(obj, "SubassemblyShapeRows", []) or [])
    for index, station in enumerate(station_values):
        section_id = _list_value(section_ids, index, f"section:{index + 1}")
        section_subassembly_rows = subassembly_rows_by_section.get(section_id) or _subassembly_placeholders(
            _integer_value(getattr(obj, "SubassemblyCounts", []), index, 0),
            _list_value(getattr(obj, "TemplateIds", []), index, ""),
            _list_value(getattr(obj, "RegionIds", []), index, ""),
        )
        station_rows.append(
            AppliedSectionStationRow(
                station_row_id=_list_value(getattr(obj, "StationRowIds", []), index, f"station:{index + 1}"),
                station=float(station),
                applied_section_id=section_id,
                kind=_list_value(getattr(obj, "StationKinds", []), index, "regular_sample"),
            )
        )
        sections.append(
            AppliedSection(
                schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
                project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
                applied_section_id=section_id,
                corridor_id=str(getattr(obj, "CorridorId", "") or ""),
                alignment_id=_list_value(getattr(obj, "AlignmentIds", []), index, str(getattr(obj, "AlignmentId", "") or "")),
                assembly_id=_list_value(getattr(obj, "AssemblyIds", []), index, ""),
                station=float(station),
                template_id=_list_value(getattr(obj, "TemplateIds", []), index, ""),
                region_id=_list_value(getattr(obj, "RegionIds", []), index, ""),
                surface_left_width=_float_value(getattr(obj, "SurfaceLeftWidths", []), index, 0.0),
                surface_right_width=_float_value(getattr(obj, "SurfaceRightWidths", []), index, 0.0),
                subgrade_depth=_float_value(getattr(obj, "SubgradeDepths", []), index, 0.0),
                daylight_left_width=_float_value(getattr(obj, "DaylightLeftWidths", []), index, 0.0),
                daylight_right_width=_float_value(getattr(obj, "DaylightRightWidths", []), index, 0.0),
                daylight_left_slope=_float_value(getattr(obj, "DaylightLeftSlopes", []), index, 0.0),
                daylight_right_slope=_float_value(getattr(obj, "DaylightRightSlopes", []), index, 0.0),
                active_superelevation_id=_list_value(getattr(obj, "SuperelevationIds", []), index, ""),
                superelevation_left_crossfall=_float_value(getattr(obj, "SuperelevationLeftCrossfalls", []), index, 0.0),
                superelevation_right_crossfall=_float_value(getattr(obj, "SuperelevationRightCrossfalls", []), index, 0.0),
                active_superelevation_transition_id=_list_value(getattr(obj, "SuperelevationTransitionIds", []), index, ""),
                superelevation_source_rows=superelevation_sources_by_section.get(section_id, []),
                active_intersection_id=_list_value(getattr(obj, "IntersectionIds", []), index, ""),
                active_intersection_control_area_id=_list_value(getattr(obj, "IntersectionControlAreaIds", []), index, ""),
                active_intersection_leg_id=_list_value(getattr(obj, "IntersectionLegIds", []), index, ""),
                active_intersection_leg_role=_list_value(getattr(obj, "IntersectionLegRoles", []), index, ""),
                active_intersection_control_region_refs=intersection_control_regions_by_section.get(section_id, []),
                active_intersection_grading_policy_ref=_list_value(getattr(obj, "IntersectionGradingPolicyRefs", []), index, ""),
                active_intersection_source_status=_list_value(getattr(obj, "IntersectionSourceStatuses", []), index, ""),
                active_intersection_source_diagnostic_rows=intersection_source_diagnostics_by_section.get(section_id, []),
                active_intersection_source_stage_rows=intersection_source_stages_by_section.get(section_id, []),
                intersection_diagnostic_rows=intersection_diagnostics_by_section.get(section_id, []),
                diagnostic_rows=diagnostics_by_section.get(section_id, []),
                subassembly_rows=section_subassembly_rows,
                subassembly_point_rows=subassembly_point_rows_by_section.get(section_id, []),
                subassembly_link_rows=subassembly_link_rows_by_section.get(section_id, []),
                subassembly_shape_rows=subassembly_shape_rows_by_section.get(section_id, []),
                point_rows=point_rows_by_section.get(section_id, []),
                active_structure_ids=active_structures_by_section.get(section_id, []),
                active_structure_rule_ids=active_rules_by_section.get(section_id, []),
                active_structure_influence_zone_ids=active_zones_by_section.get(section_id, []),
                structure_diagnostic_rows=structure_diagnostics_by_section.get(section_id, []),
                frame=AppliedSectionFrame(
                    station=float(station),
                    x=_float_value(getattr(obj, "FrameXValues", []), index, 0.0),
                    y=_float_value(getattr(obj, "FrameYValues", []), index, 0.0),
                    z=_float_value(getattr(obj, "FrameZValues", []), index, 0.0),
                    tangent_direction_deg=_float_value(getattr(obj, "FrameTangentDirections", []), index, 0.0),
                    profile_grade=_float_value(getattr(obj, "FrameProfileGrades", []), index, 0.0),
                    alignment_status=_list_value(getattr(obj, "FrameAlignmentStatuses", []), index, ""),
                    profile_status=_list_value(getattr(obj, "FrameProfileStatuses", []), index, ""),
                    source_mode=_list_value(getattr(obj, "FrameSourceModes", []), index, ""),
                    source_status=_list_value(getattr(obj, "FrameSourceStatuses", []), index, ""),
                    source_diagnostic_rows=frame_source_diagnostics_by_section.get(section_id, []),
                    notes=_list_value(getattr(obj, "FrameNotes", []), index, ""),
                ),
            )
        )
    return AppliedSectionSet(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        applied_section_set_id=str(getattr(obj, "AppliedSectionSetId", "") or "applied-sections:main"),
        corridor_id=str(getattr(obj, "CorridorId", "") or ""),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        station_rows=station_rows,
        sections=sections,
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
    )


def find_v1_applied_section_set(document, preferred_applied_section_set=None):
    """Find a v1 AppliedSectionSet result object in a document."""

    if _is_v1_applied_section_set(preferred_applied_section_set):
        return preferred_applied_section_set
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_applied_section_set(obj):
            return obj
    return None


def _is_v1_applied_section_set(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1AppliedSectionSet":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_applied_section_set":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1AppliedSectionSet" or name.startswith("V1AppliedSectionSet")


def _diagnostic_rows(sections) -> list[str]:
    output: list[str] = []
    for section in list(sections or []):
        section_id = str(getattr(section, "applied_section_id", "") or "")
        for diagnostic in list(getattr(section, "diagnostic_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(diagnostic, "severity", "")),
                        _escape_row_value(getattr(diagnostic, "kind", "")),
                        _escape_row_value(getattr(diagnostic, "message", "")),
                        _escape_row_value(getattr(diagnostic, "notes", "")),
                    ]
                )
            )
    return output


def _point_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for point in list(getattr(section, "point_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(point, "point_id", "")),
                        _escape_row_value(getattr(point, "point_role", "")),
                        f"{float(getattr(point, 'lateral_offset', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'x', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'y', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'z', 0.0) or 0.0):.12g}",
                        _escape_row_value(getattr(point, "side", "")),
                        _escape_row_value(getattr(point, "drainage_ref", "")),
                        _escape_row_value(getattr(point, "subassembly_ref", "")),
                    ]
                )
            )
    return output


def _subassembly_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for subassembly in list(getattr(section, "subassembly_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(subassembly, "subassembly_id", "")),
                        _escape_row_value(getattr(subassembly, "kind", "")),
                        _escape_row_value(getattr(subassembly, "source_template_id", "")),
                        _escape_row_value(getattr(subassembly, "region_id", "")),
                        _escape_row_value(getattr(subassembly, "side", "")),
                        f"{float(getattr(subassembly, 'width', 0.0) or 0.0):.12g}",
                        f"{float(getattr(subassembly, 'slope', 0.0) or 0.0):.12g}",
                        f"{float(getattr(subassembly, 'thickness', 0.0) or 0.0):.12g}",
                        _escape_row_value(getattr(subassembly, "material", "")),
                        ",".join(
                            _escape_row_value(value)
                            for value in list(getattr(subassembly, "structure_ids", []) or [])
                            if str(value or "")
                        ),
                        ",".join(
                            _escape_row_value(value)
                            for value in list(getattr(subassembly, "drainage_refs", []) or [])
                            if str(value or "")
                        ),
                        _escape_row_value(json.dumps(dict(getattr(subassembly, "parameters", {}) or {}), sort_keys=True)),
                        ";".join(_escape_row_value(value) for value in tuple(getattr(subassembly, "point_code_rules", ()) or ())),
                        ";".join(_escape_row_value(value) for value in tuple(getattr(subassembly, "link_code_rules", ()) or ())),
                        ";".join(_escape_row_value(value) for value in tuple(getattr(subassembly, "shape_code_rules", ()) or ())),
                        ",".join(
                            _escape_row_value(value)
                            for value in list(getattr(subassembly, "override_ids", []) or [])
                            if str(value or "")
                        ),
                        ";".join(_escape_row_value(value) for value in list(getattr(subassembly, "diagnostics", []) or [])),
                        _escape_row_value(getattr(subassembly, "definition_ref", "")),
                        _escape_row_value(getattr(subassembly, "preset_ref", "")),
                        _escape_row_value(getattr(subassembly, "preset_version", "")),
                        _escape_row_value(getattr(subassembly, "preset_status", "")),
                        _escape_row_value(getattr(subassembly, "source_instance_ref", "")),
                    ]
                )
            )
    return output


def _set_applied_section_diagnostic_summary(obj, station_rows, sections) -> None:
    rows = list(station_rows or [])
    section_rows = list(sections or [])
    section_kind_counts = _count_strings(str(getattr(row, "kind", "") or "regular_sample") for row in rows)
    diagnostic_kind_counts: dict[str, int] = {}
    centerline_source_counts: dict[str, int] = {}
    centerline_source_status_counts: dict[str, int] = {}
    centerline_fallback_count = 0
    overlap_clip_count = 0
    ditch_shape_count = 0
    daylight_fallback_count = 0
    diagnostic_count = 0
    intersection_source_count = 0
    intersection_source_warning_count = 0
    intersection_source_diagnostic_count = 0
    intersection_source_status_counts: dict[str, int] = {}

    for section in section_rows:
        frame = _section_frame(section)
        source_mode = _frame_source_mode(frame)
        source_status = _frame_source_status(frame)
        centerline_source_counts[source_mode] = centerline_source_counts.get(source_mode, 0) + 1
        centerline_source_status_counts[source_status] = centerline_source_status_counts.get(source_status, 0) + 1
        if source_mode not in {"", "centerline3d_source_geometry"}:
            centerline_fallback_count += 1
        for diagnostic in list(getattr(section, "diagnostic_rows", []) or []):
            diagnostic_count += 1
            kind = str(getattr(diagnostic, "kind", "") or "unknown")
            diagnostic_kind_counts[kind] = diagnostic_kind_counts.get(kind, 0) + 1
            kind_lower = kind.lower()
            if kind_lower == "applied_section_overlap_clip":
                overlap_clip_count += 1
            if "ditch_shape" in kind_lower:
                ditch_shape_count += 1
            if "daylight" in kind_lower and "fallback" in kind_lower:
                daylight_fallback_count += 1
        if str(getattr(section, "active_intersection_id", "") or ""):
            intersection_source_count += 1
            status = str(getattr(section, "active_intersection_source_status", "") or "missing")
            intersection_source_status_counts[status] = intersection_source_status_counts.get(status, 0) + 1
            if status not in {"accepted", "ready", "locked"}:
                intersection_source_warning_count += 1
            intersection_source_diagnostic_count += len(
                [item for item in list(getattr(section, "active_intersection_source_diagnostic_rows", []) or []) if str(item)]
            )
            intersection_source_diagnostic_count += len(
                [
                    item
                    for item in list(getattr(section, "active_intersection_source_stage_rows", []) or [])
                    if "|" in str(item) and "|accepted|" not in str(item)
                ]
            )

    supplemental_count = sum(1 for row in rows if "supplemental" in str(getattr(row, "kind", "") or "").lower())
    source_count = max(len(rows) - supplemental_count, 0)
    obj.SourceSectionCount = source_count
    obj.SupplementalSectionCount = supplemental_count
    obj.TotalSectionCount = len(rows)
    obj.SectionKindCounts = _format_count_rows(section_kind_counts)
    obj.CenterlineSourceModeCounts = _format_count_rows(centerline_source_counts)
    obj.CenterlineSourceStatusCounts = _format_count_rows(centerline_source_status_counts)
    obj.CenterlineFallbackCount = centerline_fallback_count
    obj.OverlapClipDiagnosticCount = overlap_clip_count
    obj.DitchShapeInferenceDiagnosticCount = ditch_shape_count
    obj.DaylightFallbackDiagnosticCount = daylight_fallback_count
    obj.IntersectionSourceSectionCount = intersection_source_count
    obj.IntersectionSourceWarningCount = intersection_source_warning_count
    obj.IntersectionSourceDiagnosticCount = intersection_source_diagnostic_count
    obj.IntersectionSourceStatusCounts = _format_count_rows(intersection_source_status_counts)
    obj.IntersectionSourceSummary = (
        f"intersection_sections={intersection_source_count};"
        f"intersection_warnings={intersection_source_warning_count};"
        f"intersection_source_diagnostics={intersection_source_diagnostic_count}"
    )
    obj.AppliedSectionDiagnosticCount = diagnostic_count
    obj.AppliedSectionDiagnosticKinds = _format_count_rows(diagnostic_kind_counts)
    obj.AppliedSectionDiagnosticSummary = (
        f"sections={len(rows)};source={source_count};supplemental={supplemental_count};"
        f"centerline_fallback={centerline_fallback_count};overlap_clip={overlap_clip_count};"
        f"ditch_shape={ditch_shape_count};daylight_fallback={daylight_fallback_count};"
        f"diagnostics={diagnostic_count}"
    )


def _frame_source_mode(frame: AppliedSectionFrame) -> str:
    value = str(getattr(frame, "source_mode", "") or "").strip()
    if value:
        return value
    return _centerline_source_mode_from_notes(str(getattr(frame, "notes", "") or ""))


def _frame_source_status(frame: AppliedSectionFrame) -> str:
    value = str(getattr(frame, "source_status", "") or "").strip()
    if value:
        return value
    source_mode = _frame_source_mode(frame)
    if source_mode == "centerline3d_source_geometry":
        return "source_geometry"
    if source_mode in {"centerline3d_result"}:
        return "result"
    if source_mode in {"alignment_profile_fallback", "unknown"}:
        return "fallback"
    return "accepted" if source_mode else ""


def _section_frame_source_diagnostic_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    rows: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        frame = _section_frame(section_by_id.get(section_id))
        diagnostics = [str(item) for item in list(getattr(frame, "source_diagnostic_rows", []) or []) if str(item)]
        if diagnostics:
            rows.append(section_id + "|" + "|".join(_escape_row_value(value) for value in diagnostics))
    return rows


def _centerline_source_mode_from_notes(notes: str) -> str:
    text = str(notes or "")
    if "source=centerline3d_source_geometry" in text:
        return "centerline3d_source_geometry"
    if "source=centerline3d_result" in text:
        return "centerline3d_result"
    if "source=alignment_profile_fallback" in text:
        return "alignment_profile_fallback"
    if "source=" in text:
        for token in text.replace(";", " ").split():
            if token.startswith("source="):
                return token.split("=", 1)[1].strip()
    return "unknown"


def _count_strings(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _format_count_rows(counts: dict[str, int]) -> list[str]:
    return [f"{key}={int(counts[key])}" for key in sorted(counts)]


def _subassembly_point_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for point in list(getattr(section, "subassembly_point_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(point, "point_id", "")),
                        _escape_row_value(getattr(point, "subassembly_ref", "")),
                        _escape_row_value(getattr(point, "point_code", "")),
                        f"{float(getattr(point, 'lateral_offset', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'x', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'y', 0.0) or 0.0):.12g}",
                        f"{float(getattr(point, 'z', 0.0) or 0.0):.12g}",
                        _escape_row_value(getattr(point, "side", "")),
                        _escape_row_value(getattr(point, "target_ref", "")),
                        ";".join(_escape_row_value(value) for value in list(getattr(point, "diagnostics", []) or [])),
                    ]
                )
            )
    return output


def _subassembly_link_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(link, "link_id", "")),
                        _escape_row_value(getattr(link, "subassembly_ref", "")),
                        _escape_row_value(getattr(link, "start_point_ref", "")),
                        _escape_row_value(getattr(link, "end_point_ref", "")),
                        _escape_row_value(getattr(link, "link_code", "")),
                        _escape_row_value(getattr(link, "surface_role", "")),
                        _escape_row_value(getattr(link, "material", "")),
                        ";".join(_escape_row_value(value) for value in list(getattr(link, "diagnostics", []) or [])),
                    ]
                )
            )
    return output


def _subassembly_shape_rows(station_rows, section_by_id: dict[str, AppliedSection]) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        for shape in list(getattr(section, "subassembly_shape_rows", []) or []):
            output.append(
                "|".join(
                    [
                        section_id,
                        _escape_row_value(getattr(shape, "shape_id", "")),
                        _escape_row_value(getattr(shape, "subassembly_ref", "")),
                        ";".join(_escape_row_value(value) for value in list(getattr(shape, "point_refs", []) or [])),
                        _escape_row_value(getattr(shape, "shape_code", "")),
                        _escape_row_value(getattr(shape, "material", "")),
                        f"{float(getattr(shape, 'thickness', 0.0) or 0.0):.12g}",
                        _escape_row_value(getattr(shape, "solid_family", "")),
                        ";".join(_escape_row_value(value) for value in list(getattr(shape, "diagnostics", []) or [])),
                    ]
                )
            )
    return output


def _section_list_rows(station_rows, section_by_id: dict[str, AppliedSection], attr_name: str) -> list[str]:
    output: list[str] = []
    for station_row in list(station_rows or []):
        section_id = str(getattr(station_row, "applied_section_id", "") or "")
        section = section_by_id.get(section_id)
        values = [
            _escape_row_value(value)
            for value in list(getattr(section, attr_name, []) or [])
            if str(value or "")
        ]
        if values:
            output.append(section_id + "|" + "|".join(values))
    return output


def _parse_section_list_rows(values) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 2:
            continue
        section_id = _unescape_row_value(parts[0])
        output[section_id] = [_unescape_row_value(value) for value in parts[1:] if str(value or "")]
    return output


def _parse_diagnostic_rows(values) -> dict[str, list[DiagnosticMessage]]:
    output: dict[str, list[DiagnosticMessage]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 4:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        output.setdefault(section_id, []).append(
            DiagnosticMessage(
                severity=_unescape_row_value(parts[1]),
                kind=_unescape_row_value(parts[2]),
                message=_unescape_row_value(parts[3]),
                notes=_unescape_row_value(parts[4] if len(parts) > 4 else ""),
            )
        )
    return output


def _parse_point_rows(values) -> dict[str, list[AppliedSectionPoint]]:
    output: dict[str, list[AppliedSectionPoint]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 7:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        output.setdefault(section_id, []).append(
            _applied_section_point_from_parts(parts)
        )
    for rows in output.values():
        rows.sort(key=lambda point: (str(getattr(point, "point_role", "") or ""), float(getattr(point, "lateral_offset", 0.0) or 0.0)))
    return output


def _applied_section_point_from_parts(parts: list[str]) -> AppliedSectionPoint:
    """Parse current point rows."""

    side_index = 7
    drainage_index = 8
    subassembly_index = 9
    return AppliedSectionPoint(
        point_id=_unescape_row_value(parts[1]),
        point_role=_unescape_row_value(parts[2]),
        lateral_offset=_safe_float(parts[3]),
        x=_safe_float(parts[4]),
        y=_safe_float(parts[5]),
        z=_safe_float(parts[6]),
        side=_unescape_row_value(parts[side_index]) if len(parts) > side_index else "",
        drainage_ref=_unescape_row_value(parts[drainage_index]) if len(parts) > drainage_index else "",
        subassembly_ref=_unescape_row_value(parts[subassembly_index]) if len(parts) > subassembly_index else "",
    )


def _parse_subassembly_rows(values) -> dict[str, list[AppliedSectionSubassemblyRow]]:
    output: dict[str, list[AppliedSectionSubassemblyRow]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 10:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        structure_ids = [
            _unescape_row_value(value)
            for value in str(parts[10] if len(parts) > 10 else "" or "").split(",")
            if str(value or "")
        ]
        drainage_refs = [
            _unescape_row_value(value)
            for value in str(parts[11] if len(parts) > 11 else "" or "").split(",")
            if str(value or "")
        ]
        parameters = {}
        if len(parts) > 12:
            try:
                parsed = json.loads(_unescape_row_value(parts[12]))
                if isinstance(parsed, dict):
                    parameters = parsed
            except Exception:
                parameters = {}
        point_code_rules = _parse_semicolon_tuple(parts[13] if len(parts) > 13 else "")
        link_code_rules = _parse_semicolon_tuple(parts[14] if len(parts) > 14 else "")
        shape_code_rules = _parse_semicolon_tuple(parts[15] if len(parts) > 15 else "")
        override_ids = [
            _unescape_row_value(value)
            for value in str(parts[16] if len(parts) > 16 else "" or "").split(",")
            if str(value or "")
        ]
        diagnostics = list(_parse_semicolon_tuple(parts[17] if len(parts) > 17 else ""))
        definition_ref = _unescape_row_value(parts[18]) if len(parts) > 18 else ""
        preset_ref = _unescape_row_value(parts[19]) if len(parts) > 19 else ""
        preset_version = _unescape_row_value(parts[20]) if len(parts) > 20 else ""
        preset_status = _unescape_row_value(parts[21]) if len(parts) > 21 else ""
        source_instance_ref = _unescape_row_value(parts[22]) if len(parts) > 22 else ""
        output.setdefault(section_id, []).append(
            AppliedSectionSubassemblyRow(
                subassembly_id=_unescape_row_value(parts[1]),
                kind=_unescape_row_value(parts[2]),
                definition_ref=definition_ref,
                preset_ref=preset_ref,
                preset_version=preset_version,
                preset_status=preset_status,
                source_instance_ref=source_instance_ref,
                source_template_id=_unescape_row_value(parts[3]),
                region_id=_unescape_row_value(parts[4]),
                side=_unescape_row_value(parts[5]),
                width=_safe_float(parts[6]),
                slope=_safe_float(parts[7]),
                thickness=_safe_float(parts[8]),
                material=_unescape_row_value(parts[9]),
                structure_ids=structure_ids,
                drainage_refs=drainage_refs,
                parameters=parameters,
                point_code_rules=point_code_rules,
                link_code_rules=link_code_rules,
                shape_code_rules=shape_code_rules,
                override_ids=override_ids,
                diagnostics=diagnostics,
            )
        )
    return output


def _parse_subassembly_point_rows(values) -> dict[str, list[AppliedSectionSubassemblyPoint]]:
    output: dict[str, list[AppliedSectionSubassemblyPoint]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 8:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        output.setdefault(section_id, []).append(
            AppliedSectionSubassemblyPoint(
                point_id=_unescape_row_value(parts[1]),
                subassembly_ref=_unescape_row_value(parts[2]),
                point_code=_unescape_row_value(parts[3]),
                lateral_offset=_safe_float(parts[4]),
                x=_safe_float(parts[5]),
                y=_safe_float(parts[6]),
                z=_safe_float(parts[7]),
                side=_unescape_row_value(parts[8]) if len(parts) > 8 else "",
                target_ref=_unescape_row_value(parts[9]) if len(parts) > 9 else "",
                diagnostics=list(_parse_semicolon_tuple(parts[10] if len(parts) > 10 else "")),
            )
        )
    for rows in output.values():
        rows.sort(key=lambda point: (str(getattr(point, "subassembly_ref", "") or ""), float(getattr(point, "lateral_offset", 0.0) or 0.0)))
    return output


def _parse_subassembly_link_rows(values) -> dict[str, list[AppliedSectionSubassemblyLink]]:
    output: dict[str, list[AppliedSectionSubassemblyLink]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 8:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        output.setdefault(section_id, []).append(
            AppliedSectionSubassemblyLink(
                link_id=_unescape_row_value(parts[1]),
                subassembly_ref=_unescape_row_value(parts[2]),
                start_point_ref=_unescape_row_value(parts[3]),
                end_point_ref=_unescape_row_value(parts[4]),
                link_code=_unescape_row_value(parts[5]),
                surface_role=_unescape_row_value(parts[6]),
                material=_unescape_row_value(parts[7]),
                diagnostics=list(_parse_semicolon_tuple(parts[8] if len(parts) > 8 else "")),
            )
        )
    return output


def _parse_subassembly_shape_rows(values) -> dict[str, list[AppliedSectionSubassemblyShape]]:
    output: dict[str, list[AppliedSectionSubassemblyShape]] = {}
    for raw in list(values or []):
        parts = str(raw or "").split("|")
        if len(parts) < 8:
            continue
        section_id = _unescape_row_value(parts[0])
        if not section_id:
            continue
        output.setdefault(section_id, []).append(
            AppliedSectionSubassemblyShape(
                shape_id=_unescape_row_value(parts[1]),
                subassembly_ref=_unescape_row_value(parts[2]),
                point_refs=list(_parse_semicolon_tuple(parts[3])),
                shape_code=_unescape_row_value(parts[4]),
                material=_unescape_row_value(parts[5]),
                thickness=_safe_float(parts[6]),
                solid_family=_unescape_row_value(parts[7]),
                diagnostics=list(_parse_semicolon_tuple(parts[8] if len(parts) > 8 else "")),
            )
        )
    return output


def _parse_semicolon_tuple(value: object) -> tuple[str, ...]:
    return tuple(_unescape_row_value(part) for part in str(value or "").split(";") if str(part or ""))


def _escape_row_value(value: object) -> str:
    return str(value or "").replace("\\", "\\\\").replace("|", "\\p")


def _unescape_row_value(value: object) -> str:
    text = str(value or "")
    return text.replace("\\p", "|").replace("\\\\", "\\")


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _section_frame(section) -> AppliedSectionFrame:
    frame = getattr(section, "frame", None)
    if frame is not None:
        return frame
    return AppliedSectionFrame(station=float(getattr(section, "station", 0.0) or 0.0))


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _clear_existing_property(obj, name: str) -> None:
    if obj is None or not hasattr(obj, name):
        return
    try:
        setattr(obj, name, [])
    except Exception:
        pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _list_value(values, index: int, default: str = "") -> str:
    try:
        values_list = list(values or [])
        return str(values_list[index]) if index < len(values_list) else str(default)
    except Exception:
        return str(default)


def _float_list(values) -> list[float]:
    output = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            output.append(0.0)
    return output


def _float_value(values, index: int, default: float = 0.0) -> float:
    try:
        values_list = list(values or [])
        return float(values_list[index]) if index < len(values_list) else float(default)
    except Exception:
        return float(default)


def _integer_value(values, index: int, default: int = 0) -> int:
    try:
        values_list = list(values or [])
        return int(values_list[index]) if index < len(values_list) else int(default)
    except Exception:
        return int(default)


def _subassembly_placeholders(count: int, template_id: str, region_id: str) -> list[AppliedSectionSubassemblyRow]:
    rows = []
    for index in range(max(int(count or 0), 0)):
        rows.append(
            AppliedSectionSubassemblyRow(
                subassembly_id=f"subassembly:{index + 1}",
                kind="subassembly",
                source_template_id=str(template_id or ""),
                region_id=str(region_id or ""),
            )
        )
    return rows
