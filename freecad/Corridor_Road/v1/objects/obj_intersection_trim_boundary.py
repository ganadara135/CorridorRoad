"""FreeCAD result object for v1 IntersectionTrimBoundaryResult rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.result.intersection_trim_boundary import (
    IntersectionTrimBoundaryPair,
    IntersectionTrimBoundaryResult,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


class V1IntersectionTrimBoundaryResultObject:
    """Document object proxy that stores v1 intersection trim-boundary result rows."""

    Type = "V1IntersectionTrimBoundaryResult"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_intersection_trim_boundary_properties(obj)

    def execute(self, obj):
        ensure_v1_intersection_trim_boundary_properties(obj)
        return


class ViewProviderV1IntersectionTrimBoundaryResult:
    """Simple view provider for intersection trim-boundary result objects."""

    Type = "ViewProviderV1IntersectionTrimBoundaryResult"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("watertight_solids.svg")
        except Exception:
            return ""


def ensure_v1_intersection_trim_boundary_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 trim-boundary result properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "TrimBoundaryResultId", "Trim Boundaries", "trim-boundary result id")
    _add_property(obj, "App::PropertyFloat", "Tolerance", "Trim Boundaries", "candidate tolerance")
    _add_property(obj, "App::PropertyString", "ApplicationStatus", "Trim Boundaries", "trim application status")
    _add_property(obj, "App::PropertyInteger", "ReadyPairCount", "Trim Boundaries", "ready trim pair count")
    _add_property(obj, "App::PropertyInteger", "BlockedPairCount", "Trim Boundaries", "blocked trim pair count")
    _add_property(obj, "App::PropertyInteger", "BoundaryPairCount", "Trim Boundaries", "candidate pair count")
    _add_property(obj, "App::PropertyStringList", "BoundaryPairIds", "Trim Boundaries", "candidate pair ids")
    _add_property(obj, "App::PropertyStringList", "PatchOutputRefs", "Trim Boundaries", "patch output refs")
    _add_property(obj, "App::PropertyStringList", "RoadOutputRefs", "Trim Boundaries", "road output refs")
    _add_property(obj, "App::PropertyFloatList", "DistancesXY", "Trim Boundaries", "candidate XY distances")
    _add_property(obj, "App::PropertyStringList", "PatchSegmentsXYZ", "Trim Boundaries", "patch segment xyz rows")
    _add_property(obj, "App::PropertyStringList", "RoadSegmentsXYZ", "Trim Boundaries", "road segment xyz rows")
    _add_property(obj, "App::PropertyStringList", "Statuses", "Trim Boundaries", "candidate statuses")
    _add_property(obj, "App::PropertyStringList", "NotesRows", "Trim Boundaries", "candidate notes")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", "source refs")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1IntersectionTrimBoundaryResult"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_intersection_trim_boundary_result"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "TrimBoundaryResultId", "") or ""):
        obj.TrimBoundaryResultId = "intersection-trim-boundaries:watertight"
    if not str(getattr(obj, "ApplicationStatus", "") or ""):
        obj.ApplicationStatus = "not_evaluated"


def create_or_update_v1_intersection_trim_boundary_result_object(
    document=None,
    trim_boundary_result: IntersectionTrimBoundaryResult | None = None,
    *,
    project=None,
    object_name: str = "V1IntersectionTrimBoundaryResult",
    label: str = "Intersection Trim Boundary Result",
):
    """Create or update the durable v1 IntersectionTrimBoundaryResult object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 IntersectionTrimBoundaryResult creation.")
    if trim_boundary_result is None:
        trim_boundary_result = IntersectionTrimBoundaryResult(schema_version=1, project_id=_project_id(project))

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1IntersectionTrimBoundaryResultObject(obj)
        try:
            ViewProviderV1IntersectionTrimBoundaryResult(obj.ViewObject)
        except Exception:
            pass
    else:
        V1IntersectionTrimBoundaryResultObject(obj)
    update_v1_intersection_trim_boundary_result_object(obj, trim_boundary_result, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_intersection_trim_boundary_result_object(
    obj,
    trim_boundary_result: IntersectionTrimBoundaryResult,
    *,
    label: str = "Intersection Trim Boundary Result",
):
    """Write IntersectionTrimBoundaryResult rows into an existing FreeCAD object."""

    ensure_v1_intersection_trim_boundary_properties(obj)
    rows = list(getattr(trim_boundary_result, "boundary_pair_rows", []) or [])
    obj.Label = label
    obj.V1ObjectType = "V1IntersectionTrimBoundaryResult"
    obj.CRRecordKind = "v1_intersection_trim_boundary_result"
    obj.SchemaVersion = int(getattr(trim_boundary_result, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(trim_boundary_result, "project_id", "") or "corridorroad-v1")
    obj.TrimBoundaryResultId = str(getattr(trim_boundary_result, "trim_boundary_result_id", "") or "intersection-trim-boundaries:watertight")
    obj.Tolerance = float(getattr(trim_boundary_result, "tolerance", 0.05) or 0.0)
    obj.ApplicationStatus = str(getattr(trim_boundary_result, "application_status", "") or "not_evaluated")
    obj.ReadyPairCount = int(getattr(trim_boundary_result, "ready_pair_count", 0) or 0)
    obj.BlockedPairCount = int(getattr(trim_boundary_result, "blocked_pair_count", 0) or 0)
    obj.BoundaryPairCount = len(rows)
    obj.BoundaryPairIds = [str(row.boundary_pair_id) for row in rows]
    obj.PatchOutputRefs = [str(row.patch_output_ref) for row in rows]
    obj.RoadOutputRefs = [str(row.road_output_ref) for row in rows]
    obj.DistancesXY = [float(row.distance_xy) for row in rows]
    obj.PatchSegmentsXYZ = [_segment_text(row.patch_segment_xyz) for row in rows]
    obj.RoadSegmentsXYZ = [_segment_text(row.road_segment_xyz) for row in rows]
    obj.Statuses = [str(row.status) for row in rows]
    obj.NotesRows = [str(row.notes) for row in rows]
    obj.SourceRefs = [str(ref) for ref in list(getattr(trim_boundary_result, "source_refs", []) or []) if str(ref)]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_intersection_trim_boundary_result(obj) -> IntersectionTrimBoundaryResult | None:
    """Build an IntersectionTrimBoundaryResult from a v1 FreeCAD object."""

    if not _is_v1_intersection_trim_boundary_result(obj):
        return None
    ensure_v1_intersection_trim_boundary_properties(obj)
    ids = list(getattr(obj, "BoundaryPairIds", []) or [])
    count = max(
        len(ids),
        len(list(getattr(obj, "PatchOutputRefs", []) or [])),
        len(list(getattr(obj, "RoadOutputRefs", []) or [])),
        len(list(getattr(obj, "DistancesXY", []) or [])),
    )
    rows: list[IntersectionTrimBoundaryPair] = []
    for index in range(count):
        rows.append(
            IntersectionTrimBoundaryPair(
                boundary_pair_id=_list_value(ids, index, f"intersection-trim-boundary:{index + 1}"),
                patch_output_ref=_list_value(getattr(obj, "PatchOutputRefs", []), index, ""),
                road_output_ref=_list_value(getattr(obj, "RoadOutputRefs", []), index, ""),
                distance_xy=_float_list_value(getattr(obj, "DistancesXY", []), index, 0.0),
                patch_segment_xyz=_segment_tuple(_list_value(getattr(obj, "PatchSegmentsXYZ", []), index, "")),
                road_segment_xyz=_segment_tuple(_list_value(getattr(obj, "RoadSegmentsXYZ", []), index, "")),
                status=_list_value(getattr(obj, "Statuses", []), index, "candidate"),
                notes=_list_value(getattr(obj, "NotesRows", []), index, ""),
            )
        )
    return IntersectionTrimBoundaryResult(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        label=str(getattr(obj, "Label", "") or "Intersection Trim Boundary Result"),
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
        trim_boundary_result_id=str(getattr(obj, "TrimBoundaryResultId", "") or "intersection-trim-boundaries:watertight"),
        tolerance=float(getattr(obj, "Tolerance", 0.05) or 0.0),
        application_status=str(getattr(obj, "ApplicationStatus", "") or "not_evaluated"),
        ready_pair_count=int(getattr(obj, "ReadyPairCount", 0) or 0),
        blocked_pair_count=int(getattr(obj, "BlockedPairCount", 0) or 0),
        boundary_pair_rows=rows,
    )


def find_v1_intersection_trim_boundary_result(document, preferred_result=None):
    """Find a v1 IntersectionTrimBoundaryResult object in a document."""

    if _is_v1_intersection_trim_boundary_result(preferred_result):
        return preferred_result
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_intersection_trim_boundary_result(obj):
            return obj
    return None


def _is_v1_intersection_trim_boundary_result(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1IntersectionTrimBoundaryResult":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_intersection_trim_boundary_result":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1IntersectionTrimBoundaryResult" or name.startswith("V1IntersectionTrimBoundaryResult")


def _segment_text(segment: tuple[float, float, float, float, float, float]) -> str:
    return "|".join(f"{float(value):.9g}" for value in segment)


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


def _float_list_value(values, index: int, default: float = 0.0) -> float:
    try:
        values_list = list(values or [])
        return float(values_list[index]) if index < len(values_list) else float(default)
    except Exception:
        return float(default)
