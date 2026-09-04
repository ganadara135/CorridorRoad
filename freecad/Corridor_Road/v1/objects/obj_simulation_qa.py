"""FreeCAD output object for v1 SimulationQaOutput rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.output.simulation_qa_output import (
    SimulationQaDiagnosticRow,
    SimulationQaFamilyRow,
    SimulationQaOutput,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


class V1SimulationQaOutputObject:
    """Document object proxy that stores one v1 SimulationQaOutput summary."""

    Type = "V1SimulationQaOutput"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_simulation_qa_output_properties(obj)

    def execute(self, obj):
        ensure_v1_simulation_qa_output_properties(obj)
        return


class ViewProviderV1SimulationQaOutput:
    """Simple view provider for v1 simulation QA output objects."""

    Type = "ViewProviderV1SimulationQaOutput"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("report.svg")
        except Exception:
            return ""


def ensure_v1_simulation_qa_output_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 simulation QA output properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "SimulationQaOutputId", "Simulation QA", "simulation QA output id")
    _add_property(obj, "App::PropertyInteger", "OutputCount", "Simulation QA", "watertight output object count")
    _add_property(obj, "App::PropertyString", "RoadBodyStatus", "Simulation QA", "road body readiness status")
    _add_property(obj, "App::PropertyString", "TerrainStatus", "Simulation QA", "terrain readiness status")
    _add_property(obj, "App::PropertyString", "DrainageStatus", "Simulation QA", "drainage readiness status")
    _add_property(obj, "App::PropertyString", "StructureStatus", "Simulation QA", "structure readiness status")
    _add_property(obj, "App::PropertyString", "SolidValidityStatus", "Simulation QA", "solid validity status")
    _add_property(obj, "App::PropertyString", "GeometryContactStatus", "Simulation QA", "geometry contact status")
    _add_property(obj, "App::PropertyString", "TerrainDomainStatus", "Simulation QA", "terrain domain status")
    _add_property(obj, "App::PropertyString", "PortConnectionStatus", "Simulation QA", "pipe/structure port connection status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimStatus", "Simulation QA", "intersection trim readiness status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimFuseStatus", "Simulation QA", "intersection trim fuse status")
    _add_property(obj, "App::PropertyString", "IntersectionTrimHandoffStatus", "Simulation QA", "intersection trim handoff status")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffFinalQualityStatus", "Simulation QA", "intersection final-quality handoff status")
    _add_property(obj, "App::PropertyString", "IntersectionHandoffStatus", "Simulation QA", "intersection Digital Twin handoff status")
    _add_property(obj, "App::PropertyString", "IntersectionReplacementReadinessStatus", "Simulation QA", "intersection replacement readiness status")
    _add_property(obj, "App::PropertyString", "IntersectionReplacementBlockerKind", "Simulation QA", "intersection replacement blocker diagnostic kind")
    _add_property(obj, "App::PropertyBool", "SimulationReady", "Simulation QA", "first-slice simulation readiness")
    _add_property(obj, "App::PropertyInteger", "InvalidOutputCount", "Simulation QA", "invalid output count")
    _add_property(obj, "App::PropertyInteger", "ZeroVolumeOutputCount", "Simulation QA", "zero-volume output count")
    _add_property(obj, "App::PropertyInteger", "ContactIssueCount", "Simulation QA", "geometry contact issue count")
    _add_property(obj, "App::PropertyInteger", "TerrainIssueCount", "Simulation QA", "terrain domain issue count")
    _add_property(obj, "App::PropertyInteger", "PortIssueCount", "Simulation QA", "pipe/structure port issue count")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimReadyPairCount", "Simulation QA", "intersection trim ready pair count")
    _add_property(obj, "App::PropertyInteger", "IntersectionTrimBlockedPairCount", "Simulation QA", "intersection trim blocked pair count")
    _add_property(obj, "App::PropertyFloat", "IntersectionTrimMaxGap", "Simulation QA", "intersection trim maximum XY gap")
    _add_property(obj, "App::PropertyFloat", "TotalVolume", "Simulation QA", "total built solid volume")
    _add_property(obj, "App::PropertyStringList", "MissingContexts", "Simulation QA", "missing simulation contexts")
    _add_property(obj, "App::PropertyInteger", "FamilyCount", "Families", "family row count")
    _add_property(obj, "App::PropertyStringList", "FamilyNames", "Families", "family names")
    _add_property(obj, "App::PropertyStringList", "FamilyStatuses", "Families", "family statuses")
    _add_property(obj, "App::PropertyIntegerList", "FamilyOutputCounts", "Families", "family output counts")
    _add_property(obj, "App::PropertyFloatList", "FamilyTotalVolumes", "Families", "family total volumes")
    _add_property(obj, "App::PropertyStringList", "FamilyNotes", "Families", "family notes")
    _add_property(obj, "App::PropertyInteger", "DiagnosticCount", "Diagnostics", "diagnostic row count")
    _add_property(obj, "App::PropertyStringList", "DiagnosticIds", "Diagnostics", "diagnostic ids")
    _add_property(obj, "App::PropertyStringList", "DiagnosticSeverities", "Diagnostics", "diagnostic severities")
    _add_property(obj, "App::PropertyStringList", "DiagnosticKinds", "Diagnostics", "diagnostic kinds")
    _add_property(obj, "App::PropertyStringList", "DiagnosticSourceRefs", "Diagnostics", "diagnostic source refs")
    _add_property(obj, "App::PropertyStringList", "DiagnosticMessages", "Diagnostics", "diagnostic messages")
    _add_property(obj, "App::PropertyStringList", "DiagnosticNotes", "Diagnostics", "diagnostic notes")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", "source refs")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SimulationQaOutput"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_simulation_qa_output"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "SimulationQaOutputId", "") or ""):
        obj.SimulationQaOutputId = "simulation-qa:watertight-solids"


def create_or_update_v1_simulation_qa_output_object(
    document=None,
    simulation_qa_output: SimulationQaOutput | None = None,
    *,
    project=None,
    object_name: str = "V1SimulationQaOutput",
    label: str = "Simulation QA Output",
):
    """Create or update the durable v1 SimulationQaOutput object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SimulationQaOutput creation.")
    if simulation_qa_output is None:
        simulation_qa_output = SimulationQaOutput(
            schema_version=1,
            project_id=_project_id(project),
            simulation_qa_output_id="simulation-qa:watertight-solids",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SimulationQaOutputObject(obj)
        try:
            ViewProviderV1SimulationQaOutput(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SimulationQaOutputObject(obj)
    update_v1_simulation_qa_output_object(obj, simulation_qa_output, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_simulation_qa_output_object(
    obj,
    simulation_qa_output: SimulationQaOutput,
    *,
    label: str = "Simulation QA Output",
):
    """Write SimulationQaOutput summary rows into a FreeCAD object."""

    ensure_v1_simulation_qa_output_properties(obj)
    families = list(getattr(simulation_qa_output, "family_rows", []) or [])
    diagnostics = list(getattr(simulation_qa_output, "diagnostic_rows", []) or [])

    obj.Label = label
    obj.V1ObjectType = "V1SimulationQaOutput"
    obj.CRRecordKind = "v1_simulation_qa_output"
    obj.SchemaVersion = int(getattr(simulation_qa_output, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(simulation_qa_output, "project_id", "") or "corridorroad-v1")
    obj.SimulationQaOutputId = str(getattr(simulation_qa_output, "simulation_qa_output_id", "") or "simulation-qa:watertight-solids")
    obj.OutputCount = int(getattr(simulation_qa_output, "output_count", 0) or 0)
    obj.RoadBodyStatus = str(getattr(simulation_qa_output, "road_body_status", "") or "missing")
    obj.TerrainStatus = str(getattr(simulation_qa_output, "terrain_status", "") or "missing")
    obj.DrainageStatus = str(getattr(simulation_qa_output, "drainage_status", "") or "missing")
    obj.StructureStatus = str(getattr(simulation_qa_output, "structure_status", "") or "missing")
    obj.SolidValidityStatus = str(getattr(simulation_qa_output, "solid_validity_status", "") or "check")
    obj.GeometryContactStatus = str(getattr(simulation_qa_output, "geometry_contact_status", "") or "not_checked")
    obj.TerrainDomainStatus = str(getattr(simulation_qa_output, "terrain_domain_status", "") or "not_checked")
    obj.PortConnectionStatus = str(getattr(simulation_qa_output, "port_connection_status", "") or "not_checked")
    obj.IntersectionTrimStatus = str(getattr(simulation_qa_output, "intersection_trim_status", "") or "not_available")
    obj.IntersectionTrimFuseStatus = str(getattr(simulation_qa_output, "intersection_trim_fuse_status", "") or "not_available")
    obj.IntersectionTrimHandoffStatus = str(getattr(simulation_qa_output, "intersection_trim_handoff_status", "") or "not_available")
    obj.IntersectionHandoffFinalQualityStatus = str(getattr(simulation_qa_output, "intersection_handoff_final_quality_status", "") or "not_available")
    obj.IntersectionHandoffStatus = str(getattr(simulation_qa_output, "intersection_handoff_status", "") or "not_available")
    obj.IntersectionReplacementReadinessStatus = str(getattr(simulation_qa_output, "intersection_replacement_readiness_status", "") or "")
    obj.IntersectionReplacementBlockerKind = str(getattr(simulation_qa_output, "intersection_replacement_blocker_kind", "") or "")
    obj.SimulationReady = bool(getattr(simulation_qa_output, "simulation_ready", False))
    obj.InvalidOutputCount = int(getattr(simulation_qa_output, "invalid_output_count", 0) or 0)
    obj.ZeroVolumeOutputCount = int(getattr(simulation_qa_output, "zero_volume_output_count", 0) or 0)
    obj.ContactIssueCount = int(getattr(simulation_qa_output, "contact_issue_count", 0) or 0)
    obj.TerrainIssueCount = int(getattr(simulation_qa_output, "terrain_issue_count", 0) or 0)
    obj.PortIssueCount = int(getattr(simulation_qa_output, "port_issue_count", 0) or 0)
    obj.IntersectionTrimReadyPairCount = int(getattr(simulation_qa_output, "intersection_trim_ready_pair_count", 0) or 0)
    obj.IntersectionTrimBlockedPairCount = int(getattr(simulation_qa_output, "intersection_trim_blocked_pair_count", 0) or 0)
    obj.IntersectionTrimMaxGap = float(getattr(simulation_qa_output, "intersection_trim_max_gap", 0.0) or 0.0)
    obj.TotalVolume = float(getattr(simulation_qa_output, "total_volume", 0.0) or 0.0)
    obj.MissingContexts = [str(value) for value in list(getattr(simulation_qa_output, "missing_contexts", []) or []) if str(value)]
    obj.FamilyCount = len(families)
    obj.FamilyNames = [str(getattr(row, "family", "") or "") for row in families]
    obj.FamilyStatuses = [str(getattr(row, "status", "") or "") for row in families]
    obj.FamilyOutputCounts = [int(getattr(row, "output_count", 0) or 0) for row in families]
    obj.FamilyTotalVolumes = [float(getattr(row, "total_volume", 0.0) or 0.0) for row in families]
    obj.FamilyNotes = [str(getattr(row, "notes", "") or "") for row in families]
    obj.DiagnosticCount = len(diagnostics)
    obj.DiagnosticIds = [str(getattr(row, "diagnostic_id", "") or "") for row in diagnostics]
    obj.DiagnosticSeverities = [str(getattr(row, "severity", "") or "") for row in diagnostics]
    obj.DiagnosticKinds = [str(getattr(row, "kind", "") or "") for row in diagnostics]
    obj.DiagnosticSourceRefs = [str(getattr(row, "source_ref", "") or "") for row in diagnostics]
    obj.DiagnosticMessages = [str(getattr(row, "message", "") or "") for row in diagnostics]
    obj.DiagnosticNotes = [str(getattr(row, "notes", "") or "") for row in diagnostics]
    obj.SourceRefs = [str(ref) for ref in list(getattr(simulation_qa_output, "source_refs", []) or []) if str(ref)]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_simulation_qa_output(obj) -> SimulationQaOutput | None:
    """Build a SimulationQaOutput summary from a v1 FreeCAD object."""

    if not _is_v1_simulation_qa_output(obj):
        return None
    ensure_v1_simulation_qa_output_properties(obj)
    family_names = list(getattr(obj, "FamilyNames", []) or [])
    families = [
        SimulationQaFamilyRow(
            family=_list_value(family_names, index, ""),
            status=_list_value(getattr(obj, "FamilyStatuses", []), index, ""),
            output_count=_int_list_value(getattr(obj, "FamilyOutputCounts", []), index),
            total_volume=_float_list_value(getattr(obj, "FamilyTotalVolumes", []), index),
            notes=_list_value(getattr(obj, "FamilyNotes", []), index, ""),
        )
        for index, _name in enumerate(family_names)
    ]
    diagnostic_ids = list(getattr(obj, "DiagnosticIds", []) or [])
    diagnostics = [
        SimulationQaDiagnosticRow(
            diagnostic_id=_list_value(diagnostic_ids, index, f"simulation-qa:diagnostic:{index + 1}"),
            severity=_list_value(getattr(obj, "DiagnosticSeverities", []), index, "info"),
            kind=_list_value(getattr(obj, "DiagnosticKinds", []), index, ""),
            source_ref=_list_value(getattr(obj, "DiagnosticSourceRefs", []), index, ""),
            message=_list_value(getattr(obj, "DiagnosticMessages", []), index, ""),
            notes=_list_value(getattr(obj, "DiagnosticNotes", []), index, ""),
        )
        for index, _diagnostic_id in enumerate(diagnostic_ids)
    ]
    return SimulationQaOutput(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        simulation_qa_output_id=str(getattr(obj, "SimulationQaOutputId", "") or "simulation-qa:watertight-solids"),
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
        output_count=int(getattr(obj, "OutputCount", 0) or 0),
        road_body_status=str(getattr(obj, "RoadBodyStatus", "") or "missing"),
        terrain_status=str(getattr(obj, "TerrainStatus", "") or "missing"),
        drainage_status=str(getattr(obj, "DrainageStatus", "") or "missing"),
        structure_status=str(getattr(obj, "StructureStatus", "") or "missing"),
        solid_validity_status=str(getattr(obj, "SolidValidityStatus", "") or "check"),
        geometry_contact_status=str(getattr(obj, "GeometryContactStatus", "") or "not_checked"),
        terrain_domain_status=str(getattr(obj, "TerrainDomainStatus", "") or "not_checked"),
        port_connection_status=str(getattr(obj, "PortConnectionStatus", "") or "not_checked"),
        intersection_trim_status=str(getattr(obj, "IntersectionTrimStatus", "") or "not_available"),
        intersection_trim_fuse_status=str(getattr(obj, "IntersectionTrimFuseStatus", "") or "not_available"),
        intersection_trim_handoff_status=str(getattr(obj, "IntersectionTrimHandoffStatus", "") or "not_available"),
        intersection_handoff_final_quality_status=str(getattr(obj, "IntersectionHandoffFinalQualityStatus", "") or "not_available"),
        intersection_handoff_status=str(getattr(obj, "IntersectionHandoffStatus", "") or "not_available"),
        intersection_replacement_readiness_status=str(getattr(obj, "IntersectionReplacementReadinessStatus", "") or ""),
        intersection_replacement_blocker_kind=str(getattr(obj, "IntersectionReplacementBlockerKind", "") or ""),
        simulation_ready=bool(getattr(obj, "SimulationReady", False)),
        invalid_output_count=int(getattr(obj, "InvalidOutputCount", 0) or 0),
        zero_volume_output_count=int(getattr(obj, "ZeroVolumeOutputCount", 0) or 0),
        contact_issue_count=int(getattr(obj, "ContactIssueCount", 0) or 0),
        terrain_issue_count=int(getattr(obj, "TerrainIssueCount", 0) or 0),
        port_issue_count=int(getattr(obj, "PortIssueCount", 0) or 0),
        intersection_trim_ready_pair_count=int(getattr(obj, "IntersectionTrimReadyPairCount", 0) or 0),
        intersection_trim_blocked_pair_count=int(getattr(obj, "IntersectionTrimBlockedPairCount", 0) or 0),
        intersection_trim_max_gap=float(getattr(obj, "IntersectionTrimMaxGap", 0.0) or 0.0),
        total_volume=float(getattr(obj, "TotalVolume", 0.0) or 0.0),
        missing_contexts=[str(value) for value in list(getattr(obj, "MissingContexts", []) or []) if str(value)],
        family_rows=families,
        diagnostic_rows=diagnostics,
    )


def find_v1_simulation_qa_output(document, preferred_output=None):
    """Find a v1 SimulationQaOutput object in a document."""

    if _is_v1_simulation_qa_output(preferred_output):
        return preferred_output
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_simulation_qa_output(obj):
            return obj
    return None


def _is_v1_simulation_qa_output(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SimulationQaOutput":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_simulation_qa_output":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SimulationQaOutput" or name.startswith("V1SimulationQaOutput")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
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


def _float_list_value(values, index: int) -> float:
    try:
        values_list = list(values or [])
        return float(values_list[index]) if index < len(values_list) else 0.0
    except Exception:
        return 0.0


def _int_list_value(values, index: int) -> int:
    try:
        values_list = list(values or [])
        return int(values_list[index]) if index < len(values_list) else 0
    except Exception:
        return 0
