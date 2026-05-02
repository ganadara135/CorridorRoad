"""FreeCAD result object for v1 CorridorModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.result.corridor_model import CorridorModel, CorridorSamplingPolicy, CorridorStationRow


class V1CorridorModelObject:
    """Document object proxy that stores a v1 CorridorModel result summary."""

    Type = "V1CorridorModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_corridor_model_properties(obj)

    def execute(self, obj):
        ensure_v1_corridor_model_properties(obj)
        return


class ViewProviderV1CorridorModel:
    """Simple view provider for v1 CorridorModel result objects."""

    Type = "ViewProviderV1CorridorModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("corridor.svg")
        except Exception:
            return ""


def ensure_v1_corridor_model_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 CorridorModel result properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "CorridorId", "CorridorRoad", "corridor id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "alignment id")
    _add_property(obj, "App::PropertyString", "RegionModelRef", "CorridorRoad", "region model ref")
    _add_property(obj, "App::PropertyString", "AppliedSectionSetRef", "CorridorRoad", "applied section set ref")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyStringList", "SurfaceBuildRefs", "CorridorRoad", "surface build refs")
    _add_property(obj, "App::PropertyStringList", "SolidBuildRefs", "CorridorRoad", "solid build refs")
    _add_property(obj, "App::PropertyFloat", "StationInterval", "Sampling", "station interval")
    _add_property(obj, "App::PropertyInteger", "StationCount", "Stations", "corridor station count")
    _add_property(obj, "App::PropertyStringList", "StationRowIds", "Stations", "station row ids")
    _add_property(obj, "App::PropertyFloatList", "StationValues", "Stations", "station values")
    _add_property(obj, "App::PropertyStringList", "StationKinds", "Stations", "station kinds")
    _add_property(obj, "App::PropertyStringList", "StationSourceReasons", "Stations", "station source reasons")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1CorridorModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "CorridorId", "") or ""):
        obj.CorridorId = f"corridor:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_corridor_model"


def create_or_update_v1_corridor_model_object(
    document=None,
    corridor_model: CorridorModel | None = None,
    *,
    project=None,
    object_name: str = "V1CorridorModel",
    label: str = "Corridor Model",
):
    """Create or update the durable v1 CorridorModel result object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 CorridorModel creation.")
    if corridor_model is None:
        corridor_model = CorridorModel(schema_version=1, project_id=_project_id(project), corridor_id="corridor:main")

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1CorridorModelObject(obj)
        try:
            ViewProviderV1CorridorModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1CorridorModelObject(obj)
    update_v1_corridor_model_object(obj, corridor_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_corridor_model_object(obj, corridor_model: CorridorModel, *, label: str = "Corridor Model"):
    """Write CorridorModel result summaries into a FreeCAD object."""

    ensure_v1_corridor_model_properties(obj)
    rows = list(getattr(corridor_model, "station_rows", []) or [])
    policy = getattr(corridor_model, "sampling_policy", None)
    obj.Label = label
    obj.SchemaVersion = int(getattr(corridor_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(corridor_model, "project_id", "") or "corridorroad-v1")
    obj.CorridorId = str(getattr(corridor_model, "corridor_id", "") or "corridor:main")
    obj.AlignmentId = str(getattr(corridor_model, "alignment_id", "") or "")
    obj.RegionModelRef = str(getattr(corridor_model, "region_model_ref", "") or "")
    obj.AppliedSectionSetRef = str(getattr(corridor_model, "applied_section_set_ref", "") or "")
    obj.CRRecordKind = "v1_corridor_model"
    obj.SurfaceBuildRefs = [str(ref) for ref in list(getattr(corridor_model, "surface_build_refs", []) or []) if str(ref)]
    obj.SolidBuildRefs = [str(ref) for ref in list(getattr(corridor_model, "solid_build_refs", []) or []) if str(ref)]
    obj.StationInterval = float(getattr(policy, "station_interval", 0.0) or 0.0) if policy is not None else 0.0
    obj.StationCount = len(rows)
    obj.StationRowIds = [str(row.station_row_id) for row in rows]
    obj.StationValues = [float(row.station) for row in rows]
    obj.StationKinds = [str(row.kind) for row in rows]
    obj.StationSourceReasons = [str(row.source_reason) for row in rows]
    obj.SourceRefs = [str(ref) for ref in list(getattr(corridor_model, "source_refs", []) or []) if str(ref)]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_corridor_model(obj) -> CorridorModel | None:
    """Build a summary CorridorModel from a v1 result FreeCAD object."""

    if not _is_v1_corridor_model(obj):
        return None
    ensure_v1_corridor_model_properties(obj)
    stations = _float_list(getattr(obj, "StationValues", []) or [])
    rows = [
        CorridorStationRow(
            station_row_id=_list_value(getattr(obj, "StationRowIds", []), index, f"station:{index + 1}"),
            station=float(station),
            kind=_list_value(getattr(obj, "StationKinds", []), index, "regular_sample"),
            source_reason=_list_value(getattr(obj, "StationSourceReasons", []), index, ""),
        )
        for index, station in enumerate(stations)
    ]
    corridor_id = str(getattr(obj, "CorridorId", "") or "corridor:main")
    return CorridorModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        corridor_id=corridor_id,
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        region_model_ref=str(getattr(obj, "RegionModelRef", "") or ""),
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id=f"{corridor_id}:sampling",
            station_interval=float(getattr(obj, "StationInterval", 0.0) or 0.0),
        ),
        station_rows=rows,
        applied_section_set_ref=str(getattr(obj, "AppliedSectionSetRef", "") or ""),
        surface_build_refs=[str(ref) for ref in list(getattr(obj, "SurfaceBuildRefs", []) or []) if str(ref)],
        solid_build_refs=[str(ref) for ref in list(getattr(obj, "SolidBuildRefs", []) or []) if str(ref)],
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
    )


def find_v1_corridor_model(document, preferred_corridor_model=None):
    """Find a v1 CorridorModel result object in a document."""

    if _is_v1_corridor_model(preferred_corridor_model):
        return preferred_corridor_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_corridor_model(obj):
            return obj
    return None


def _is_v1_corridor_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1CorridorModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_corridor_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1CorridorModel" or name.startswith("V1CorridorModel")


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


def _float_list(values) -> list[float]:
    output = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            output.append(0.0)
    return output
