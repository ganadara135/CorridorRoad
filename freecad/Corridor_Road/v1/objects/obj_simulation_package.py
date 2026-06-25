"""FreeCAD output object for v1 SimulationPackageOutput manifests."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.output.simulation_package_output import (
    SimulationPackageOutput,
    SimulationPackageSolidRow,
)


class V1SimulationPackageOutputObject:
    """Document object proxy that stores one v1 simulation package manifest."""

    Type = "V1SimulationPackageOutput"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_simulation_package_output_properties(obj)

    def execute(self, obj):
        ensure_v1_simulation_package_output_properties(obj)
        return


class ViewProviderV1SimulationPackageOutput:
    """Simple view provider for v1 simulation package output objects."""

    Type = "ViewProviderV1SimulationPackageOutput"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("export.svg")
        except Exception:
            return ""


def ensure_v1_simulation_package_output_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 simulation package output properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "SimulationPackageOutputId", "Simulation Package", "simulation package output id")
    _add_property(obj, "App::PropertyString", "PackageStatus", "Simulation Package", "package readiness status")
    _add_property(obj, "App::PropertyBool", "SimulationReady", "Simulation Package", "simulation readiness flag")
    _add_property(obj, "App::PropertyString", "SimulationQaOutputRef", "Simulation Package", "simulation QA output ref")
    _add_property(obj, "App::PropertyString", "TerrainStatus", "Simulation Package", "terrain readiness status")
    _add_property(obj, "App::PropertyString", "TerrainRef", "Simulation Package", "terrain source/output ref")
    _add_property(obj, "App::PropertyString", "TerrainBoundBox", "Simulation Package", "terrain bound box")
    _add_property(obj, "App::PropertyString", "DrainageReadinessStatus", "Simulation Package", "drainage readiness status")
    _add_property(obj, "App::PropertyString", "DrainageSourceStatus", "Simulation Package", "drainage source status")
    _add_property(obj, "App::PropertyInteger", "DrainageFlowRouteCount", "Simulation Package", "drainage flow route count")
    _add_property(obj, "App::PropertyInteger", "DrainageCaptureOnlyRouteCount", "Simulation Package", "drainage capture-only route count")
    _add_property(obj, "App::PropertyInteger", "DrainagePipeCandidateCount", "Simulation Package", "drainage pipe candidate count")
    _add_property(obj, "App::PropertyInteger", "DrainageUnresolvedPortRouteCount", "Simulation Package", "drainage unresolved port route count")
    _add_property(obj, "App::PropertyInteger", "DrainageMissingElementRouteCount", "Simulation Package", "drainage missing element route count")
    _add_property(obj, "App::PropertyInteger", "DrainageLinedDitchTargetCount", "Simulation Package", "drainage lined ditch target count")
    _add_property(obj, "App::PropertyInteger", "DrainagePipeSegmentTargetCount", "Simulation Package", "drainage pipe segment target count")
    _add_property(obj, "App::PropertyInteger", "DrainagePipelineNetworkTargetCount", "Simulation Package", "drainage pipeline network target count")
    _add_property(obj, "App::PropertyInteger", "DrainageStructureBodyTargetCount", "Simulation Package", "drainage structure body target count")
    _add_property(obj, "App::PropertyInteger", "DrainageBuiltOutputCount", "Simulation Package", "built drainage solid output count")
    _add_property(obj, "App::PropertyString", "DrainageNetworkFuseStatus", "Simulation Package", "drainage network fuse status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimStatus", "Simulation Package", "intersection trim readiness status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimResultRef", "Simulation Package", "intersection trim-boundary result ref")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimBoundaryPairCount", "Simulation Package", "intersection trim boundary-pair count")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimReadyPairCount", "Simulation Package", "intersection ready trim-pair count")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimBlockedPairCount", "Simulation Package", "intersection blocked trim-pair count")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimPairIds", "Intersection Trim", "intersection trim pair ids")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimPairStatuses", "Intersection Trim", "intersection trim pair statuses")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimPatchOutputRefs", "Intersection Trim", "intersection trim patch output refs")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimRoadOutputRefs", "Intersection Trim", "intersection trim road output refs")
    _add_property(obj, "App::PropertyFloatList", "IntersectionTrimDistancesXY", "Intersection Trim", "intersection trim pair XY distances")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimPatchSegmentsXYZ", "Intersection Trim", "intersection trim patch segment XYZ rows")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimRoadSegmentsXYZ", "Intersection Trim", "intersection trim road segment XYZ rows")
    _add_property(obj, "App::PropertyString", "IntersectionTrimFuseStatus", "Intersection Trim", "intersection trim fuse candidate status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimHandoffStatus", "Intersection Trim", "intersection trim accepted/fallback handoff status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimFuseCandidateRef", "Intersection Trim", "intersection trim fuse candidate object ref")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimFuseSourceCount", "Intersection Trim", "intersection trim fuse source count")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimFuseFaceCount", "Intersection Trim", "intersection trim fuse face count")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimFuseOpenEdgeCount", "Intersection Trim", "intersection trim fuse open edge count")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimFuseSourceRefs", "Intersection Trim", "intersection trim fuse source refs")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimHandoffChainRefs", "Intersection Trim", "intersection trim handoff chain object refs")
    _add_property(obj, "App::PropertyStringList", "IntersectionTrimHandoffStageStatuses", "Intersection Trim", "intersection trim handoff stage statuses")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffReadinessStatus", "Intersection Handoff", "intersection watertight handoff readiness status")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffFinalQualityStatus", "Intersection Handoff", "intersection final-quality handoff status")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffStatus", "Intersection Handoff", "intersection Digital Twin handoff status")
    _add_property(obj, "App::PropertyInteger", "IntersectionHandoffTargetCount", "Intersection Handoff", "intersection watertight target count")
    _add_property(obj, "App::PropertyInteger", "IntersectionHandoffPatchTargetCount", "Intersection Handoff", "intersection transitional patch target count")
    _add_property(obj, "App::PropertyInteger", "IntersectionHandoffAcceptedZoneTargetCount", "Intersection Handoff", "intersection accepted zone target count")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffReplacementGateStatus", "Intersection Handoff", "intersection replacement gate status")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffReplacementReadinessStatus", "Intersection Handoff", "intersection replacement readiness status")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffReplacementHandoffPreference", "Intersection Handoff", "intersection replacement handoff preference")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffDownstreamSelectedRole", "Intersection Handoff", "intersection downstream selected handoff role")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffLegacyPatchReviewVisibility", "Intersection Handoff", "intersection legacy patch review visibility")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffLegacyPatchCompatibilityAuditSummary", "Intersection Handoff", "intersection legacy patch compatibility audit summary")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffReplacementBlockerKind", "Intersection Handoff", "intersection replacement blocker diagnostic kind")
    _add_property(obj, "App::PropertyInteger", "OutputCount", "Simulation Package", "packaged solid output count")
    _add_property(obj, "App::PropertyFloat", "TotalVolume", "Simulation Package", "packaged total solid volume")
    _add_property(obj, "App::PropertyStringList", "TargetFamilies", "Simulation Package", "target families")
    _add_property(obj, "App::PropertyStringList", "MissingContexts", "Simulation Package", "missing simulation contexts")
    _add_property(obj, "App::PropertyStringList", "DiagnosticKinds", "Simulation Package", "diagnostic kinds")
    _add_property(obj, "App::PropertyInteger", "SolidRowCount", "Solids", "solid manifest row count")
    _add_property(obj, "App::PropertyStringList", "SolidOutputRefs", "Solids", "solid output refs")
    _add_property(obj, "App::PropertyStringList", "SolidTargetFamilies", "Solids", "solid target families")
    _add_property(obj, "App::PropertyStringList", "SolidSubassemblyRefs", "Solids", "solid subassembly refs")
    _add_property(obj, "App::PropertyStringList", "SolidStructureRefs", "Solids", "solid structure refs")
    _add_property(obj, "App::PropertyStringList", "SolidDrainageRefs", "Solids", "solid drainage refs")
    _add_property(obj, "App::PropertyStringList", "SolidFlowRouteRefs", "Solids", "solid flow route refs")
    _add_property(obj, "App::PropertyStringList", "SolidMaterialRefs", "Solids", "solid material refs")
    _add_property(obj, "App::PropertyStringList", "SolidSourceRefs", "Solids", "solid source refs")
    _add_property(obj, "App::PropertyFloatList", "SolidVolumes", "Solids", "solid volumes")
    _add_property(obj, "App::PropertyStringList", "SolidShapeValidStatuses", "Solids", "solid shape valid statuses")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", "source refs")
    _add_property(obj, "App::PropertyStringList", "ResultRefs", "Traceability", "result refs")
    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SimulationPackageOutput"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_simulation_package_output"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "SimulationPackageOutputId", "") or ""):
        obj.SimulationPackageOutputId = "simulation-package:watertight-solids"


def create_or_update_v1_simulation_package_output_object(
    document=None,
    simulation_package_output: SimulationPackageOutput | None = None,
    *,
    project=None,
    object_name: str = "V1SimulationPackageOutput",
    label: str = "Simulation Package Output",
):
    """Create or update the durable v1 SimulationPackageOutput object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SimulationPackageOutput creation.")
    if simulation_package_output is None:
        simulation_package_output = SimulationPackageOutput(
            schema_version=1,
            project_id=_project_id(project),
            simulation_package_output_id="simulation-package:watertight-solids",
        )
    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SimulationPackageOutputObject(obj)
        try:
            ViewProviderV1SimulationPackageOutput(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SimulationPackageOutputObject(obj)
    update_v1_simulation_package_output_object(obj, simulation_package_output, label=label)
    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_simulation_package_output_object(
    obj,
    simulation_package_output: SimulationPackageOutput,
    *,
    label: str = "Simulation Package Output",
):
    """Write SimulationPackageOutput manifest rows into a FreeCAD object."""

    ensure_v1_simulation_package_output_properties(obj)
    rows = list(getattr(simulation_package_output, "solid_rows", []) or [])
    obj.Label = label
    obj.V1ObjectType = "V1SimulationPackageOutput"
    obj.CRRecordKind = "v1_simulation_package_output"
    obj.SchemaVersion = int(getattr(simulation_package_output, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(simulation_package_output, "project_id", "") or "corridorroad-v1")
    obj.SimulationPackageOutputId = str(getattr(simulation_package_output, "simulation_package_output_id", "") or "simulation-package:watertight-solids")
    obj.PackageStatus = str(getattr(simulation_package_output, "package_status", "") or "blocked")
    obj.SimulationReady = bool(getattr(simulation_package_output, "simulation_ready", False))
    obj.SimulationQaOutputRef = str(getattr(simulation_package_output, "simulation_qa_output_ref", "") or "")
    obj.TerrainStatus = str(getattr(simulation_package_output, "terrain_status", "") or "missing")
    obj.TerrainRef = str(getattr(simulation_package_output, "terrain_ref", "") or "")
    obj.TerrainBoundBox = _bound_box_text(getattr(simulation_package_output, "terrain_bound_box", None))
    obj.DrainageReadinessStatus = str(getattr(simulation_package_output, "drainage_readiness_status", "") or "missing")
    obj.DrainageSourceStatus = str(getattr(simulation_package_output, "drainage_source_status", "") or "missing")
    obj.DrainageFlowRouteCount = int(getattr(simulation_package_output, "drainage_flow_route_count", 0) or 0)
    obj.DrainageCaptureOnlyRouteCount = int(getattr(simulation_package_output, "drainage_capture_only_route_count", 0) or 0)
    obj.DrainagePipeCandidateCount = int(getattr(simulation_package_output, "drainage_pipe_candidate_count", 0) or 0)
    obj.DrainageUnresolvedPortRouteCount = int(getattr(simulation_package_output, "drainage_unresolved_port_route_count", 0) or 0)
    obj.DrainageMissingElementRouteCount = int(getattr(simulation_package_output, "drainage_missing_element_route_count", 0) or 0)
    obj.DrainageLinedDitchTargetCount = int(getattr(simulation_package_output, "drainage_lined_ditch_target_count", 0) or 0)
    obj.DrainagePipeSegmentTargetCount = int(getattr(simulation_package_output, "drainage_pipe_segment_target_count", 0) or 0)
    obj.DrainagePipelineNetworkTargetCount = int(getattr(simulation_package_output, "drainage_pipeline_network_target_count", 0) or 0)
    obj.DrainageStructureBodyTargetCount = int(getattr(simulation_package_output, "drainage_structure_body_target_count", 0) or 0)
    obj.DrainageBuiltOutputCount = int(getattr(simulation_package_output, "drainage_built_output_count", 0) or 0)
    obj.DrainageNetworkFuseStatus = str(getattr(simulation_package_output, "drainage_network_fuse_status", "") or "not_available")
    obj.IntersectionTrimStatus = str(getattr(simulation_package_output, "intersection_trim_status", "") or "not_available")
    obj.IntersectionTrimResultRef = str(getattr(simulation_package_output, "intersection_trim_result_ref", "") or "")
    obj.IntersectionTrimBoundaryPairCount = int(getattr(simulation_package_output, "intersection_trim_boundary_pair_count", 0) or 0)
    obj.IntersectionTrimReadyPairCount = int(getattr(simulation_package_output, "intersection_trim_ready_pair_count", 0) or 0)
    obj.IntersectionTrimBlockedPairCount = int(getattr(simulation_package_output, "intersection_trim_blocked_pair_count", 0) or 0)
    trim_pairs = list(getattr(simulation_package_output, "intersection_trim_pair_rows", []) or [])
    obj.IntersectionTrimPairIds = [str(row.get("boundary_pair_id", "") or "") for row in trim_pairs]
    obj.IntersectionTrimPairStatuses = [str(row.get("status", "") or "") for row in trim_pairs]
    obj.IntersectionTrimPatchOutputRefs = [str(row.get("patch_output_ref", "") or "") for row in trim_pairs]
    obj.IntersectionTrimRoadOutputRefs = [str(row.get("road_output_ref", "") or "") for row in trim_pairs]
    obj.IntersectionTrimDistancesXY = [float(row.get("distance_xy", 0.0) or 0.0) for row in trim_pairs]
    obj.IntersectionTrimPatchSegmentsXYZ = [_segment_text(row.get("patch_segment_xyz", ())) for row in trim_pairs]
    obj.IntersectionTrimRoadSegmentsXYZ = [_segment_text(row.get("road_segment_xyz", ())) for row in trim_pairs]
    obj.IntersectionTrimFuseStatus = str(getattr(simulation_package_output, "intersection_trim_fuse_status", "") or "not_available")
    obj.IntersectionTrimHandoffStatus = str(getattr(simulation_package_output, "intersection_trim_handoff_status", "") or "not_available")
    obj.IntersectionTrimFuseCandidateRef = str(getattr(simulation_package_output, "intersection_trim_fuse_candidate_ref", "") or "")
    obj.IntersectionTrimFuseSourceCount = int(getattr(simulation_package_output, "intersection_trim_fuse_source_count", 0) or 0)
    obj.IntersectionTrimFuseFaceCount = int(getattr(simulation_package_output, "intersection_trim_fuse_face_count", 0) or 0)
    obj.IntersectionTrimFuseOpenEdgeCount = int(getattr(simulation_package_output, "intersection_trim_fuse_open_edge_count", 0) or 0)
    obj.IntersectionTrimFuseSourceRefs = [str(ref) for ref in list(getattr(simulation_package_output, "intersection_trim_fuse_source_refs", []) or []) if str(ref)]
    obj.IntersectionTrimHandoffChainRefs = [
        str(ref)
        for ref in list(getattr(simulation_package_output, "intersection_trim_handoff_chain_refs", []) or [])
        if str(ref)
    ]
    obj.IntersectionTrimHandoffStageStatuses = [
        str(value)
        for value in list(getattr(simulation_package_output, "intersection_trim_handoff_stage_statuses", []) or [])
        if str(value)
    ]
    obj.IntersectionHandoffReadinessStatus = str(getattr(simulation_package_output, "intersection_handoff_readiness_status", "") or "not_available")
    obj.IntersectionHandoffFinalQualityStatus = str(getattr(simulation_package_output, "intersection_handoff_final_quality_status", "") or "not_available")
    obj.IntersectionHandoffStatus = str(getattr(simulation_package_output, "intersection_handoff_status", "") or "not_available")
    obj.IntersectionHandoffTargetCount = int(getattr(simulation_package_output, "intersection_handoff_target_count", 0) or 0)
    obj.IntersectionHandoffPatchTargetCount = int(getattr(simulation_package_output, "intersection_handoff_patch_target_count", 0) or 0)
    obj.IntersectionHandoffAcceptedZoneTargetCount = int(getattr(simulation_package_output, "intersection_handoff_accepted_zone_target_count", 0) or 0)
    obj.IntersectionHandoffReplacementGateStatus = str(getattr(simulation_package_output, "intersection_handoff_replacement_gate_status", "") or "")
    obj.IntersectionHandoffReplacementReadinessStatus = str(getattr(simulation_package_output, "intersection_handoff_replacement_readiness_status", "") or "")
    obj.IntersectionHandoffReplacementHandoffPreference = str(getattr(simulation_package_output, "intersection_handoff_replacement_handoff_preference", "") or "")
    obj.IntersectionHandoffDownstreamSelectedRole = str(getattr(simulation_package_output, "intersection_handoff_downstream_selected_role", "") or "")
    obj.IntersectionHandoffLegacyPatchReviewVisibility = str(getattr(simulation_package_output, "intersection_handoff_legacy_patch_review_visibility", "") or "")
    obj.IntersectionHandoffLegacyPatchCompatibilityAuditSummary = str(getattr(simulation_package_output, "intersection_handoff_legacy_patch_compatibility_audit_summary", "") or "")
    obj.IntersectionHandoffReplacementBlockerKind = str(getattr(simulation_package_output, "intersection_handoff_replacement_blocker_kind", "") or "")
    obj.OutputCount = int(getattr(simulation_package_output, "output_count", 0) or 0)
    obj.TotalVolume = float(getattr(simulation_package_output, "total_volume", 0.0) or 0.0)
    obj.TargetFamilies = [str(value) for value in list(getattr(simulation_package_output, "target_families", []) or []) if str(value)]
    obj.MissingContexts = [str(value) for value in list(getattr(simulation_package_output, "missing_contexts", []) or []) if str(value)]
    obj.DiagnosticKinds = [str(value) for value in list(getattr(simulation_package_output, "diagnostic_kinds", []) or []) if str(value)]
    obj.SolidRowCount = len(rows)
    obj.SolidOutputRefs = [str(getattr(row, "output_ref", "") or "") for row in rows]
    obj.SolidTargetFamilies = [_join_refs(getattr(row, "target_families", []) or []) for row in rows]
    obj.SolidSubassemblyRefs = [_join_refs(getattr(row, "subassembly_refs", []) or []) for row in rows]
    obj.SolidStructureRefs = [_join_refs(getattr(row, "structure_refs", []) or []) for row in rows]
    obj.SolidDrainageRefs = [_join_refs(getattr(row, "drainage_refs", []) or []) for row in rows]
    obj.SolidFlowRouteRefs = [_join_refs(getattr(row, "flow_route_refs", []) or []) for row in rows]
    obj.SolidMaterialRefs = [_join_refs(getattr(row, "material_refs", []) or []) for row in rows]
    obj.SolidSourceRefs = [_join_refs(getattr(row, "source_refs", []) or []) for row in rows]
    obj.SolidVolumes = [float(getattr(row, "volume", 0.0) or 0.0) for row in rows]
    obj.SolidShapeValidStatuses = ["true" if bool(getattr(row, "shape_valid", False)) else "false" for row in rows]
    obj.SourceRefs = [str(ref) for ref in list(getattr(simulation_package_output, "source_refs", []) or []) if str(ref)]
    obj.ResultRefs = [str(ref) for ref in list(getattr(simulation_package_output, "result_refs", []) or []) if str(ref)]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_simulation_package_output(obj) -> SimulationPackageOutput | None:
    """Build a SimulationPackageOutput manifest from a v1 FreeCAD object."""

    if not _is_v1_simulation_package_output(obj):
        return None
    ensure_v1_simulation_package_output_properties(obj)
    output_refs = list(getattr(obj, "SolidOutputRefs", []) or [])
    rows = [
        SimulationPackageSolidRow(
            output_ref=_list_value(output_refs, index, ""),
            target_families=_split_refs(_list_value(getattr(obj, "SolidTargetFamilies", []), index, "")),
            subassembly_refs=_split_refs(_list_value(getattr(obj, "SolidSubassemblyRefs", []), index, "")),
            structure_refs=_split_refs(_list_value(getattr(obj, "SolidStructureRefs", []), index, "")),
            drainage_refs=_split_refs(_list_value(getattr(obj, "SolidDrainageRefs", []), index, "")),
            flow_route_refs=_split_refs(_list_value(getattr(obj, "SolidFlowRouteRefs", []), index, "")),
            material_refs=_split_refs(_list_value(getattr(obj, "SolidMaterialRefs", []), index, "")),
            source_refs=_split_refs(_list_value(getattr(obj, "SolidSourceRefs", []), index, "")),
            volume=_float_list_value(getattr(obj, "SolidVolumes", []), index),
            shape_valid=_bool_value(_list_value(getattr(obj, "SolidShapeValidStatuses", []), index, "")),
        )
        for index, _ref in enumerate(output_refs)
    ]
    return SimulationPackageOutput(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        simulation_package_output_id=str(getattr(obj, "SimulationPackageOutputId", "") or "simulation-package:watertight-solids"),
        label=str(getattr(obj, "Label", "") or ""),
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
        result_refs=[str(ref) for ref in list(getattr(obj, "ResultRefs", []) or []) if str(ref)],
        package_status=str(getattr(obj, "PackageStatus", "") or "blocked"),
        simulation_ready=bool(getattr(obj, "SimulationReady", False)),
        simulation_qa_output_ref=str(getattr(obj, "SimulationQaOutputRef", "") or ""),
        terrain_status=str(getattr(obj, "TerrainStatus", "") or "missing"),
        terrain_ref=str(getattr(obj, "TerrainRef", "") or ""),
        terrain_bound_box=_bound_box_tuple(str(getattr(obj, "TerrainBoundBox", "") or "")),
        drainage_readiness_status=str(getattr(obj, "DrainageReadinessStatus", "") or "missing"),
        drainage_source_status=str(getattr(obj, "DrainageSourceStatus", "") or "missing"),
        drainage_flow_route_count=int(getattr(obj, "DrainageFlowRouteCount", 0) or 0),
        drainage_capture_only_route_count=int(getattr(obj, "DrainageCaptureOnlyRouteCount", 0) or 0),
        drainage_pipe_candidate_count=int(getattr(obj, "DrainagePipeCandidateCount", 0) or 0),
        drainage_unresolved_port_route_count=int(getattr(obj, "DrainageUnresolvedPortRouteCount", 0) or 0),
        drainage_missing_element_route_count=int(getattr(obj, "DrainageMissingElementRouteCount", 0) or 0),
        drainage_lined_ditch_target_count=int(getattr(obj, "DrainageLinedDitchTargetCount", 0) or 0),
        drainage_pipe_segment_target_count=int(getattr(obj, "DrainagePipeSegmentTargetCount", 0) or 0),
        drainage_pipeline_network_target_count=int(getattr(obj, "DrainagePipelineNetworkTargetCount", 0) or 0),
        drainage_structure_body_target_count=int(getattr(obj, "DrainageStructureBodyTargetCount", 0) or 0),
        drainage_built_output_count=int(getattr(obj, "DrainageBuiltOutputCount", 0) or 0),
        drainage_network_fuse_status=str(getattr(obj, "DrainageNetworkFuseStatus", "") or "not_available"),
        intersection_trim_status=str(getattr(obj, "IntersectionTrimStatus", "") or "not_available"),
        intersection_trim_result_ref=str(getattr(obj, "IntersectionTrimResultRef", "") or ""),
        intersection_trim_boundary_pair_count=int(getattr(obj, "IntersectionTrimBoundaryPairCount", 0) or 0),
        intersection_trim_ready_pair_count=int(getattr(obj, "IntersectionTrimReadyPairCount", 0) or 0),
        intersection_trim_blocked_pair_count=int(getattr(obj, "IntersectionTrimBlockedPairCount", 0) or 0),
        intersection_trim_pair_rows=_intersection_trim_pair_rows_from_object(obj),
        intersection_trim_fuse_status=str(getattr(obj, "IntersectionTrimFuseStatus", "") or "not_available"),
        intersection_trim_handoff_status=str(getattr(obj, "IntersectionTrimHandoffStatus", "") or "not_available"),
        intersection_trim_fuse_candidate_ref=str(getattr(obj, "IntersectionTrimFuseCandidateRef", "") or ""),
        intersection_trim_fuse_source_count=int(getattr(obj, "IntersectionTrimFuseSourceCount", 0) or 0),
        intersection_trim_fuse_face_count=int(getattr(obj, "IntersectionTrimFuseFaceCount", 0) or 0),
        intersection_trim_fuse_open_edge_count=int(getattr(obj, "IntersectionTrimFuseOpenEdgeCount", 0) or 0),
        intersection_trim_fuse_source_refs=[str(ref) for ref in list(getattr(obj, "IntersectionTrimFuseSourceRefs", []) or []) if str(ref)],
        intersection_trim_handoff_chain_refs=[str(ref) for ref in list(getattr(obj, "IntersectionTrimHandoffChainRefs", []) or []) if str(ref)],
        intersection_trim_handoff_stage_statuses=[
            str(value)
            for value in list(getattr(obj, "IntersectionTrimHandoffStageStatuses", []) or [])
            if str(value)
        ],
        intersection_handoff_readiness_status=str(getattr(obj, "IntersectionHandoffReadinessStatus", "") or "not_available"),
        intersection_handoff_final_quality_status=str(getattr(obj, "IntersectionHandoffFinalQualityStatus", "") or "not_available"),
        intersection_handoff_status=str(getattr(obj, "IntersectionHandoffStatus", "") or "not_available"),
        intersection_handoff_target_count=int(getattr(obj, "IntersectionHandoffTargetCount", 0) or 0),
        intersection_handoff_patch_target_count=int(getattr(obj, "IntersectionHandoffPatchTargetCount", 0) or 0),
        intersection_handoff_accepted_zone_target_count=int(getattr(obj, "IntersectionHandoffAcceptedZoneTargetCount", 0) or 0),
        intersection_handoff_replacement_gate_status=str(getattr(obj, "IntersectionHandoffReplacementGateStatus", "") or ""),
        intersection_handoff_replacement_readiness_status=str(getattr(obj, "IntersectionHandoffReplacementReadinessStatus", "") or ""),
        intersection_handoff_replacement_handoff_preference=str(getattr(obj, "IntersectionHandoffReplacementHandoffPreference", "") or ""),
        intersection_handoff_downstream_selected_role=str(getattr(obj, "IntersectionHandoffDownstreamSelectedRole", "") or ""),
        intersection_handoff_legacy_patch_review_visibility=str(getattr(obj, "IntersectionHandoffLegacyPatchReviewVisibility", "") or ""),
        intersection_handoff_legacy_patch_compatibility_audit_summary=str(getattr(obj, "IntersectionHandoffLegacyPatchCompatibilityAuditSummary", "") or ""),
        intersection_handoff_replacement_blocker_kind=str(getattr(obj, "IntersectionHandoffReplacementBlockerKind", "") or ""),
        output_count=int(getattr(obj, "OutputCount", 0) or 0),
        total_volume=float(getattr(obj, "TotalVolume", 0.0) or 0.0),
        target_families=[str(value) for value in list(getattr(obj, "TargetFamilies", []) or []) if str(value)],
        missing_contexts=[str(value) for value in list(getattr(obj, "MissingContexts", []) or []) if str(value)],
        diagnostic_kinds=[str(value) for value in list(getattr(obj, "DiagnosticKinds", []) or []) if str(value)],
        solid_rows=rows,
    )


def find_v1_simulation_package_output(document, preferred_output=None):
    """Find a v1 SimulationPackageOutput object in a document."""

    if _is_v1_simulation_package_output(preferred_output):
        return preferred_output
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_simulation_package_output(obj):
            return obj
    return None


def _is_v1_simulation_package_output(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SimulationPackageOutput":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_simulation_package_output":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SimulationPackageOutput" or name.startswith("V1SimulationPackageOutput")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _join_refs(values) -> str:
    return "|".join(str(value) for value in list(values or []) if str(value))


def _bound_box_text(value) -> str:
    if value is None:
        return ""
    try:
        return "|".join(f"{float(part):.12g}" for part in list(value))
    except Exception:
        return ""


def _bound_box_tuple(value: str) -> tuple[float, float, float, float, float, float] | None:
    try:
        parts = [float(part) for part in str(value or "").split("|") if str(part)]
        if len(parts) != 6:
            return None
        return (parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
    except Exception:
        return None


def _split_refs(value: str) -> list[str]:
    return [part for part in str(value or "").split("|") if part]


def _intersection_trim_pair_rows_from_object(obj) -> list[dict[str, object]]:
    pair_ids = list(getattr(obj, "IntersectionTrimPairIds", []) or [])
    count = max(
        len(pair_ids),
        len(list(getattr(obj, "IntersectionTrimPairStatuses", []) or [])),
        len(list(getattr(obj, "IntersectionTrimPatchOutputRefs", []) or [])),
        len(list(getattr(obj, "IntersectionTrimRoadOutputRefs", []) or [])),
        len(list(getattr(obj, "IntersectionTrimDistancesXY", []) or [])),
    )
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "boundary_pair_id": _list_value(pair_ids, index, f"intersection-trim-boundary:{index + 1}"),
                "status": _list_value(getattr(obj, "IntersectionTrimPairStatuses", []), index, ""),
                "patch_output_ref": _list_value(getattr(obj, "IntersectionTrimPatchOutputRefs", []), index, ""),
                "road_output_ref": _list_value(getattr(obj, "IntersectionTrimRoadOutputRefs", []), index, ""),
                "distance_xy": _float_list_value(getattr(obj, "IntersectionTrimDistancesXY", []), index),
                "patch_segment_xyz": _segment_tuple(_list_value(getattr(obj, "IntersectionTrimPatchSegmentsXYZ", []), index, "")),
                "road_segment_xyz": _segment_tuple(_list_value(getattr(obj, "IntersectionTrimRoadSegmentsXYZ", []), index, "")),
            }
        )
    return rows


def _segment_text(segment) -> str:
    values = list(segment or [])
    while len(values) < 6:
        values.append(0.0)
    return "|".join(f"{float(value):.9g}" for value in values[:6])


def _segment_tuple(value: object) -> tuple[float, float, float, float, float, float]:
    parts = []
    for token in str(value or "").replace(",", "|").split("|"):
        try:
            parts.append(float(token))
        except Exception:
            parts.append(0.0)
    while len(parts) < 6:
        parts.append(0.0)
    return tuple(parts[:6])  # type: ignore[return-value]


def _list_value(values, index: int, default: str = "") -> str:
    try:
        values_list = list(values or [])
        return str(values_list[index]) if index < len(values_list) else str(default)
    except Exception:
        return str(default)


def _float_list_value(values, index: int) -> float:
    try:
        values_list = list(values or [])
        return float(values_list[index]) if index < len(values_list) else 0.0
    except Exception:
        return 0.0


def _bool_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}
