"""FreeCAD output object for v1 WatertightSolidOutput rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.output.watertight_solid_output import (
    WatertightSolidOutput,
    WatertightSolidOutputDiagnosticRow,
    WatertightSolidOutputRow,
    WatertightSolidSegmentRow,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


class V1WatertightSolidOutputObject:
    """Document object proxy that stores one v1 WatertightSolidOutput summary."""

    Type = "V1WatertightSolidOutput"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_watertight_solid_output_properties(obj)

    def execute(self, obj):
        ensure_v1_watertight_solid_output_properties(obj)
        return


class ViewProviderV1WatertightSolidOutput:
    """Simple view provider for v1 watertight solid output objects."""

    Type = "ViewProviderV1WatertightSolidOutput"

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("structure.svg")
        except Exception:
            return ""


def ensure_v1_watertight_solid_output_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 watertight solid output properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "WatertightSolidOutputId", "CorridorRoad", "output id")
    _add_property(obj, "App::PropertyString", "CorridorId", "CorridorRoad", "corridor id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SolidCount", "Solid Rows", "solid row count")
    _add_property(obj, "App::PropertyStringList", "OutputObjectIds", "Solid Rows", "output object ids")
    _add_property(obj, "App::PropertyStringList", "TargetIds", "Solid Rows", "target ids")
    _add_property(obj, "App::PropertyStringList", "TargetFamilies", "Solid Rows", "target families")
    _add_property(obj, "App::PropertyStringList", "ScopeKinds", "Solid Rows", "scope kinds")
    _add_property(obj, "App::PropertyStringList", "StationRanges", "Solid Rows", "station ranges")
    _add_property(obj, "App::PropertyStringList", "GeneratedObjectRefs", "Solid Rows", "generated object refs")
    _add_property(obj, "App::PropertyStringList", "ValidationStatuses", "Solid Rows", "validation statuses")
    _add_property(obj, "App::PropertyStringList", "WatertightStatuses", "Solid Rows", "watertight flags")
    _add_property(obj, "App::PropertyStringList", "ValidSolidStatuses", "Solid Rows", "valid solid flags")
    _add_property(obj, "App::PropertyFloatList", "Volumes", "Solid Rows", "solid volumes")
    _add_property(obj, "App::PropertyIntegerList", "FaceCounts", "Solid Rows", "face counts")
    _add_property(obj, "App::PropertyIntegerList", "EdgeCounts", "Solid Rows", "edge counts")
    _add_property(obj, "App::PropertyIntegerList", "ProfileCounts", "Solid Rows", "profile counts")
    _add_property(obj, "App::PropertyStringList", "RegionRefs", "Solid Rows", "region refs")
    _add_property(obj, "App::PropertyStringList", "AssemblyRefs", "Solid Rows", "assembly refs")
    _add_property(obj, "App::PropertyStringList", "SubassemblyRefs", "Solid Rows", "subassembly refs")
    _add_property(obj, "App::PropertyStringList", "StructureRefs", "Solid Rows", "structure refs")
    _add_property(obj, "App::PropertyStringList", "DrainageRefs", "Solid Rows", "drainage refs")
    _add_property(obj, "App::PropertyStringList", "FlowRouteRefs", "Solid Rows", "flow route refs")
    _add_property(obj, "App::PropertyStringList", "MaterialRefs", "Solid Rows", "material refs")
    _add_property(obj, "App::PropertyStringList", "SolidSourceRefs", "Solid Rows", "row-level source refs")
    _add_property(obj, "App::PropertyStringList", "SolidNotes", "Solid Rows", "row-level notes")
    _add_property(obj, "App::PropertyStringList", "PathSources", "Solid Rows", "solid path source contracts")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRefs", "Solid Rows", "diagnostic refs")
    _add_property(obj, "App::PropertyStringList", "SolidBoundaryTraceRows", "Solid Rows", "solid boundary trace rows")
    _add_property(obj, "App::PropertyStringList", "SolidBoundaryAdjacencyRows", "Solid Rows", "solid boundary adjacency rows")
    _add_property(obj, "App::PropertyInteger", "SegmentCount", "Segments", "segment row count")
    _add_property(obj, "App::PropertyStringList", "SegmentIds", "Segments", "segment ids")
    _add_property(obj, "App::PropertyStringList", "SegmentStationRanges", "Segments", "segment station ranges")
    _add_property(obj, "App::PropertyStringList", "SegmentFaceRefs", "Segments", "segment face refs")
    _add_property(obj, "App::PropertyStringList", "SegmentProfileRefs", "Segments", "segment profile refs")
    _add_property(obj, "App::PropertyInteger", "DiagnosticCount", "Diagnostics", "diagnostic row count")
    _add_property(obj, "App::PropertyStringList", "DiagnosticIds", "Diagnostics", "diagnostic ids")
    _add_property(obj, "App::PropertyStringList", "DiagnosticSeverities", "Diagnostics", "diagnostic severities")
    _add_property(obj, "App::PropertyStringList", "DiagnosticKinds", "Diagnostics", "diagnostic kinds")
    _add_property(obj, "App::PropertyStringList", "DiagnosticMessages", "Diagnostics", "diagnostic messages")
    _add_property(obj, "App::PropertyStringList", "DiagnosticNotes", "Diagnostics", "diagnostic notes")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")
    _add_property(obj, "App::PropertyStringList", "ResultRefs", "Source", "result refs")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1WatertightSolidOutput"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "WatertightSolidOutputId", "") or ""):
        obj.WatertightSolidOutputId = f"watertight-solids:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_watertight_solid_output"


def create_or_update_v1_watertight_solid_output_object(
    document=None,
    watertight_solid_output: WatertightSolidOutput | None = None,
    *,
    shape=None,
    project=None,
    object_name: str = "V1WatertightSolidOutput",
    label: str = "Watertight Solid Output",
):
    """Create or update the durable v1 WatertightSolidOutput object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 WatertightSolidOutput creation.")
    if watertight_solid_output is None:
        watertight_solid_output = WatertightSolidOutput(
            schema_version=1,
            project_id=_project_id(project),
            watertight_solid_output_id="watertight-solids:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("Part::FeaturePython", object_name)
        V1WatertightSolidOutputObject(obj)
        try:
            ViewProviderV1WatertightSolidOutput(obj.ViewObject)
        except Exception:
            pass
    else:
        V1WatertightSolidOutputObject(obj)
    update_v1_watertight_solid_output_object(obj, watertight_solid_output, shape=shape, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_watertight_solid_output_object(
    obj,
    watertight_solid_output: WatertightSolidOutput,
    *,
    shape=None,
    label: str = "Watertight Solid Output",
):
    """Write WatertightSolidOutput summary rows into a FreeCAD object."""

    ensure_v1_watertight_solid_output_properties(obj)
    rows = list(getattr(watertight_solid_output, "solid_rows", []) or [])
    segments = list(getattr(watertight_solid_output, "segment_rows", []) or [])
    diagnostics = list(getattr(watertight_solid_output, "solid_diagnostic_rows", []) or [])

    obj.Label = label
    obj.SchemaVersion = int(getattr(watertight_solid_output, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(watertight_solid_output, "project_id", "") or "corridorroad-v1")
    obj.WatertightSolidOutputId = str(getattr(watertight_solid_output, "watertight_solid_output_id", "") or "watertight-solids:main")
    obj.CorridorId = str(getattr(watertight_solid_output, "corridor_id", "") or "")
    obj.CRRecordKind = "v1_watertight_solid_output"
    obj.SolidCount = len(rows)
    obj.OutputObjectIds = [str(row.output_object_id) for row in rows]
    obj.TargetIds = [str(row.target_id) for row in rows]
    obj.TargetFamilies = [str(row.target_family) for row in rows]
    obj.ScopeKinds = [str(row.scope_kind) for row in rows]
    obj.StationRanges = [f"{float(row.station_start):.12g}|{float(row.station_end):.12g}" for row in rows]
    obj.GeneratedObjectRefs = [str(row.generated_object_ref) for row in rows]
    obj.ValidationStatuses = [str(row.validation_status) for row in rows]
    obj.WatertightStatuses = ["true" if row.is_watertight else "false" for row in rows]
    obj.ValidSolidStatuses = ["true" if row.is_valid_solid else "false" for row in rows]
    obj.Volumes = [float(row.volume) for row in rows]
    obj.FaceCounts = [int(row.face_count) for row in rows]
    obj.EdgeCounts = [int(row.edge_count) for row in rows]
    obj.ProfileCounts = [int(row.profile_count) for row in rows]
    obj.RegionRefs = [str(row.region_ref) for row in rows]
    obj.AssemblyRefs = [str(row.assembly_ref) for row in rows]
    obj.SubassemblyRefs = [str(getattr(row, "subassembly_ref", "") or "") for row in rows]
    obj.StructureRefs = [str(row.structure_ref) for row in rows]
    obj.DrainageRefs = [str(row.drainage_ref) for row in rows]
    obj.FlowRouteRefs = [str(getattr(row, "flow_route_ref", "") or "") for row in rows]
    obj.MaterialRefs = [str(getattr(row, "material_ref", "") or "") for row in rows]
    obj.SolidSourceRefs = [_join_refs(getattr(row, "source_refs", []) or []) for row in rows]
    obj.SolidNotes = [str(getattr(row, "notes", "") or "") for row in rows]
    obj.PathSources = [str(getattr(row, "path_source", "") or "") for row in rows]
    obj.DiagnosticRefs = [_join_refs(row.diagnostic_refs) for row in rows]
    obj.SolidBoundaryTraceRows = [_join_rows(getattr(row, "boundary_trace_rows", []) or []) for row in rows]
    obj.SolidBoundaryAdjacencyRows = [_join_rows(getattr(row, "boundary_adjacency_rows", []) or []) for row in rows]
    obj.SegmentCount = len(segments)
    obj.SegmentIds = [str(row.segment_id) for row in segments]
    obj.SegmentStationRanges = [f"{float(row.station_start):.12g}|{float(row.station_end):.12g}" for row in segments]
    obj.SegmentFaceRefs = [_join_refs(row.face_refs) for row in segments]
    obj.SegmentProfileRefs = [_join_refs(row.profile_refs) for row in segments]
    obj.DiagnosticCount = len(diagnostics)
    obj.DiagnosticIds = [str(row.diagnostic_id) for row in diagnostics]
    obj.DiagnosticSeverities = [str(row.severity) for row in diagnostics]
    obj.DiagnosticKinds = [str(row.kind) for row in diagnostics]
    obj.DiagnosticMessages = [str(row.message) for row in diagnostics]
    obj.DiagnosticNotes = [str(row.notes) for row in diagnostics]
    obj.SourceRefs = [str(ref) for ref in list(getattr(watertight_solid_output, "source_refs", []) or []) if str(ref)]
    obj.ResultRefs = [str(ref) for ref in list(getattr(watertight_solid_output, "result_refs", []) or []) if str(ref)]
    if shape is not None:
        try:
            obj.Shape = shape
        except Exception:
            pass
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_watertight_solid_output(obj) -> WatertightSolidOutput | None:
    """Build a WatertightSolidOutput summary from a v1 FreeCAD object."""

    if not _is_v1_watertight_solid_output(obj):
        return None
    ensure_v1_watertight_solid_output_properties(obj)
    output_ids = list(getattr(obj, "OutputObjectIds", []) or [])
    rows = [
        WatertightSolidOutputRow(
            output_object_id=_list_value(output_ids, index, f"watertight-solid:{index + 1}"),
            target_id=_list_value(getattr(obj, "TargetIds", []), index, ""),
            target_family=_list_value(getattr(obj, "TargetFamilies", []), index, ""),
            scope_kind=_list_value(getattr(obj, "ScopeKinds", []), index, ""),
            station_start=_station_range_value(_list_value(getattr(obj, "StationRanges", []), index, ""), 0),
            station_end=_station_range_value(_list_value(getattr(obj, "StationRanges", []), index, ""), 1),
            generated_object_ref=_list_value(getattr(obj, "GeneratedObjectRefs", []), index, ""),
            validation_status=_list_value(getattr(obj, "ValidationStatuses", []), index, ""),
            is_watertight=_bool_value(_list_value(getattr(obj, "WatertightStatuses", []), index, "")),
            is_valid_solid=_bool_value(_list_value(getattr(obj, "ValidSolidStatuses", []), index, "")),
            volume=_float_list_value(getattr(obj, "Volumes", []), index),
            face_count=_int_list_value(getattr(obj, "FaceCounts", []), index),
            edge_count=_int_list_value(getattr(obj, "EdgeCounts", []), index),
            profile_count=_int_list_value(getattr(obj, "ProfileCounts", []), index),
            diagnostic_refs=_split_refs(_list_value(getattr(obj, "DiagnosticRefs", []), index, "")),
            boundary_trace_rows=_split_rows(_list_value(getattr(obj, "SolidBoundaryTraceRows", []), index, "")),
            boundary_adjacency_rows=_split_rows(_list_value(getattr(obj, "SolidBoundaryAdjacencyRows", []), index, "")),
            region_ref=_list_value(getattr(obj, "RegionRefs", []), index, ""),
            assembly_ref=_list_value(getattr(obj, "AssemblyRefs", []), index, ""),
            subassembly_ref=_list_value(getattr(obj, "SubassemblyRefs", []), index, ""),
            structure_ref=_list_value(getattr(obj, "StructureRefs", []), index, ""),
            drainage_ref=_list_value(getattr(obj, "DrainageRefs", []), index, ""),
            flow_route_ref=_list_value(getattr(obj, "FlowRouteRefs", []), index, ""),
            material_ref=_list_value(getattr(obj, "MaterialRefs", []), index, ""),
            source_refs=_split_refs(_list_value(getattr(obj, "SolidSourceRefs", []), index, "")),
            path_source=_list_value(getattr(obj, "PathSources", []), index, ""),
            notes=_list_value(getattr(obj, "SolidNotes", []), index, ""),
        )
        for index, _output_id in enumerate(output_ids)
    ]
    segment_ids = list(getattr(obj, "SegmentIds", []) or [])
    segments = [
        WatertightSolidSegmentRow(
            segment_id=_list_value(segment_ids, index, f"segment:{index + 1}"),
            parent_output_object_id=rows[0].output_object_id if rows else "",
            station_start=_station_range_value(_list_value(getattr(obj, "SegmentStationRanges", []), index, ""), 0),
            station_end=_station_range_value(_list_value(getattr(obj, "SegmentStationRanges", []), index, ""), 1),
            face_refs=_split_refs(_list_value(getattr(obj, "SegmentFaceRefs", []), index, "")),
            profile_refs=_split_refs(_list_value(getattr(obj, "SegmentProfileRefs", []), index, "")),
        )
        for index, _segment_id in enumerate(segment_ids)
    ]
    diagnostic_ids = list(getattr(obj, "DiagnosticIds", []) or [])
    diagnostics = [
        WatertightSolidOutputDiagnosticRow(
            diagnostic_id=_list_value(diagnostic_ids, index, f"diagnostic:{index + 1}"),
            severity=_list_value(getattr(obj, "DiagnosticSeverities", []), index, "info"),
            kind=_list_value(getattr(obj, "DiagnosticKinds", []), index, ""),
            source_ref=rows[0].output_object_id if rows else "",
            message=_list_value(getattr(obj, "DiagnosticMessages", []), index, ""),
            notes=_list_value(getattr(obj, "DiagnosticNotes", []), index, ""),
        )
        for index, _diagnostic_id in enumerate(diagnostic_ids)
    ]
    return WatertightSolidOutput(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        watertight_solid_output_id=str(getattr(obj, "WatertightSolidOutputId", "") or "watertight-solids:main"),
        corridor_id=str(getattr(obj, "CorridorId", "") or ""),
        label=str(getattr(obj, "Label", "") or ""),
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
        result_refs=[str(ref) for ref in list(getattr(obj, "ResultRefs", []) or []) if str(ref)],
        solid_rows=rows,
        segment_rows=segments,
        solid_diagnostic_rows=diagnostics,
    )


def find_v1_watertight_solid_output(document, preferred_output=None):
    """Find a v1 WatertightSolidOutput object in a document."""

    if _is_v1_watertight_solid_output(preferred_output):
        return preferred_output
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_watertight_solid_output(obj):
            return obj
    return None


def _is_v1_watertight_solid_output(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1WatertightSolidOutput":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_watertight_solid_output":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1WatertightSolidOutput" or name.startswith("V1WatertightSolidOutput")


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


def _split_refs(value: str) -> list[str]:
    return [part for part in str(value or "").split("|") if part]


def _join_rows(values) -> str:
    return ";;".join(str(value).replace(";;", "; ;") for value in list(values or []) if str(value))


def _split_rows(value: str) -> list[str]:
    return [part for part in str(value or "").split(";;") if part]


def _list_value(values, index: int, default: str = "") -> str:
    try:
        values_list = list(values or [])
        return str(values_list[index]) if index < len(values_list) else str(default)
    except Exception:
        return str(default)


def _station_range_value(value: str, index: int) -> float:
    try:
        parts = str(value or "").split("|")
        return float(parts[index]) if index < len(parts) else 0.0
    except Exception:
        return 0.0


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


def _bool_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}
