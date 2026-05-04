"""FreeCAD result object for v1 SurfaceModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.result.surface_model import SurfaceBuildRelation, SurfaceModel, SurfaceRow, SurfaceSpanRow


class V1SurfaceModelObject:
    """Document object proxy that stores a v1 SurfaceModel result summary."""

    Type = "V1SurfaceModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_surface_model_properties(obj)

    def execute(self, obj):
        ensure_v1_surface_model_properties(obj)
        return


class ViewProviderV1SurfaceModel:
    """Simple view provider for v1 SurfaceModel result objects."""

    Type = "ViewProviderV1SurfaceModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("terrain.svg")
        except Exception:
            return ""


def ensure_v1_surface_model_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 SurfaceModel result properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "SurfaceModelId", "CorridorRoad", "surface model id")
    _add_property(obj, "App::PropertyString", "CorridorId", "CorridorRoad", "corridor id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SurfaceCount", "Surface Rows", "surface row count")
    _add_property(obj, "App::PropertyStringList", "SurfaceIds", "Surface Rows", "surface ids")
    _add_property(obj, "App::PropertyStringList", "SurfaceKinds", "Surface Rows", "surface kinds")
    _add_property(obj, "App::PropertyStringList", "TinRefs", "Surface Rows", "TIN refs")
    _add_property(obj, "App::PropertyStringList", "SurfaceStatuses", "Surface Rows", "surface statuses")
    _add_property(obj, "App::PropertyStringList", "ParentSurfaceRefs", "Surface Rows", "parent surface refs")
    _add_property(obj, "App::PropertyInteger", "BuildRelationCount", "Build Relations", "build relation count")
    _add_property(obj, "App::PropertyStringList", "BuildRelationIds", "Build Relations", "build relation ids")
    _add_property(obj, "App::PropertyStringList", "BuildRelationSurfaceRefs", "Build Relations", "surface refs")
    _add_property(obj, "App::PropertyStringList", "BuildRelationKinds", "Build Relations", "relation kinds")
    _add_property(obj, "App::PropertyStringList", "BuildRelationInputRefs", "Build Relations", "input refs")
    _add_property(obj, "App::PropertyStringList", "BuildRelationSummaries", "Build Relations", "operation summaries")
    _add_property(obj, "App::PropertyInteger", "SurfaceSpanCount", "Surface Spans", "surface span count")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanIds", "Surface Spans", "surface span ids")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanSurfaceRefs", "Surface Spans", "surface refs")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanStationRanges", "Surface Spans", "station ranges")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanRegionRefs", "Surface Spans", "region refs")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanKinds", "Surface Spans", "span kinds")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanTransitionRefs", "Surface Spans", "transition refs")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanContinuityStatuses", "Surface Spans", "continuity statuses")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanDiagnosticRefs", "Surface Spans", "diagnostic refs")
    _add_property(obj, "App::PropertyStringList", "SurfaceSpanNotes", "Surface Spans", "span notes")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SurfaceModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "SurfaceModelId", "") or ""):
        obj.SurfaceModelId = f"surface:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_surface_model"


def create_or_update_v1_surface_model_object(
    document=None,
    surface_model: SurfaceModel | None = None,
    *,
    project=None,
    object_name: str = "V1SurfaceModel",
    label: str = "Corridor Surfaces",
):
    """Create or update the durable v1 SurfaceModel result object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SurfaceModel creation.")
    if surface_model is None:
        surface_model = SurfaceModel(
            schema_version=1,
            project_id=_project_id(project),
            surface_model_id="surface:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SurfaceModelObject(obj)
        try:
            ViewProviderV1SurfaceModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SurfaceModelObject(obj)
    update_v1_surface_model_object(obj, surface_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_surface_model_object(obj, surface_model: SurfaceModel, *, label: str = "Corridor Surfaces"):
    """Write SurfaceModel result summaries into a FreeCAD object."""

    ensure_v1_surface_model_properties(obj)
    rows = list(getattr(surface_model, "surface_rows", []) or [])
    relations = list(getattr(surface_model, "build_relation_rows", []) or [])
    spans = list(getattr(surface_model, "span_rows", []) or [])

    obj.Label = label
    obj.SchemaVersion = int(getattr(surface_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(surface_model, "project_id", "") or "corridorroad-v1")
    obj.SurfaceModelId = str(getattr(surface_model, "surface_model_id", "") or "surface:main")
    obj.CorridorId = str(getattr(surface_model, "corridor_id", "") or "")
    obj.CRRecordKind = "v1_surface_model"
    obj.SurfaceCount = len(rows)
    obj.SurfaceIds = [str(row.surface_id) for row in rows]
    obj.SurfaceKinds = [str(row.surface_kind) for row in rows]
    obj.TinRefs = [str(row.tin_ref) for row in rows]
    obj.SurfaceStatuses = [str(row.status) for row in rows]
    obj.ParentSurfaceRefs = [str(row.parent_surface_ref) for row in rows]
    obj.BuildRelationCount = len(relations)
    obj.BuildRelationIds = [str(row.build_relation_id) for row in relations]
    obj.BuildRelationSurfaceRefs = [str(row.surface_ref) for row in relations]
    obj.BuildRelationKinds = [str(row.relation_kind) for row in relations]
    obj.BuildRelationInputRefs = [_join_refs(row.input_refs) for row in relations]
    obj.BuildRelationSummaries = [str(row.operation_summary) for row in relations]
    obj.SurfaceSpanCount = len(spans)
    obj.SurfaceSpanIds = [str(row.span_id) for row in spans]
    obj.SurfaceSpanSurfaceRefs = [str(row.surface_ref) for row in spans]
    obj.SurfaceSpanStationRanges = [f"{float(row.station_start):.12g}|{float(row.station_end):.12g}" for row in spans]
    obj.SurfaceSpanRegionRefs = [f"{str(row.from_region_ref)}|{str(row.to_region_ref)}" for row in spans]
    obj.SurfaceSpanKinds = [str(row.span_kind) for row in spans]
    obj.SurfaceSpanTransitionRefs = [str(row.transition_ref) for row in spans]
    obj.SurfaceSpanContinuityStatuses = [str(row.continuity_status) for row in spans]
    obj.SurfaceSpanDiagnosticRefs = [_join_refs(row.diagnostic_refs) for row in spans]
    obj.SurfaceSpanNotes = [str(row.notes) for row in spans]
    obj.SourceRefs = [str(ref) for ref in list(getattr(surface_model, "source_refs", []) or []) if str(ref)]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_surface_model(obj) -> SurfaceModel | None:
    """Build a summary SurfaceModel from a v1 result FreeCAD object."""

    if not _is_v1_surface_model(obj):
        return None
    ensure_v1_surface_model_properties(obj)
    surface_ids = list(getattr(obj, "SurfaceIds", []) or [])
    surface_rows = [
        SurfaceRow(
            surface_id=_list_value(surface_ids, index, f"surface:{index + 1}"),
            surface_kind=_list_value(getattr(obj, "SurfaceKinds", []), index, ""),
            tin_ref=_list_value(getattr(obj, "TinRefs", []), index, ""),
            status=_list_value(getattr(obj, "SurfaceStatuses", []), index, "ready"),
            parent_surface_ref=_list_value(getattr(obj, "ParentSurfaceRefs", []), index, ""),
        )
        for index, _surface_id in enumerate(surface_ids)
    ]
    relation_ids = list(getattr(obj, "BuildRelationIds", []) or [])
    build_relation_rows = [
        SurfaceBuildRelation(
            build_relation_id=_list_value(relation_ids, index, f"build:{index + 1}"),
            surface_ref=_list_value(getattr(obj, "BuildRelationSurfaceRefs", []), index, ""),
            relation_kind=_list_value(getattr(obj, "BuildRelationKinds", []), index, ""),
            input_refs=_split_refs(_list_value(getattr(obj, "BuildRelationInputRefs", []), index, "")),
            operation_summary=_list_value(getattr(obj, "BuildRelationSummaries", []), index, ""),
        )
        for index, _relation_id in enumerate(relation_ids)
    ]
    span_ids = list(getattr(obj, "SurfaceSpanIds", []) or [])
    span_rows = [
        SurfaceSpanRow(
            span_id=_list_value(span_ids, index, f"span:{index + 1}"),
            surface_ref=_list_value(getattr(obj, "SurfaceSpanSurfaceRefs", []), index, ""),
            station_start=_station_range_value(_list_value(getattr(obj, "SurfaceSpanStationRanges", []), index, ""), 0),
            station_end=_station_range_value(_list_value(getattr(obj, "SurfaceSpanStationRanges", []), index, ""), 1),
            from_region_ref=_span_region_value(_list_value(getattr(obj, "SurfaceSpanRegionRefs", []), index, ""), 0),
            to_region_ref=_span_region_value(_list_value(getattr(obj, "SurfaceSpanRegionRefs", []), index, ""), 1),
            span_kind=_list_value(getattr(obj, "SurfaceSpanKinds", []), index, "same_region"),
            transition_ref=_list_value(getattr(obj, "SurfaceSpanTransitionRefs", []), index, ""),
            continuity_status=_list_value(getattr(obj, "SurfaceSpanContinuityStatuses", []), index, "ok"),
            diagnostic_refs=_split_refs(_list_value(getattr(obj, "SurfaceSpanDiagnosticRefs", []), index, "")),
            notes=_list_value(getattr(obj, "SurfaceSpanNotes", []), index, ""),
        )
        for index, _span_id in enumerate(span_ids)
    ]
    return SurfaceModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        surface_model_id=str(getattr(obj, "SurfaceModelId", "") or "surface:main"),
        corridor_id=str(getattr(obj, "CorridorId", "") or ""),
        label=str(getattr(obj, "Label", "") or ""),
        source_refs=[str(ref) for ref in list(getattr(obj, "SourceRefs", []) or []) if str(ref)],
        surface_rows=surface_rows,
        build_relation_rows=build_relation_rows,
        comparison_rows=[],
        span_rows=span_rows,
    )


def find_v1_surface_model(document, preferred_surface_model=None):
    """Find a v1 SurfaceModel result object in a document."""

    if _is_v1_surface_model(preferred_surface_model):
        return preferred_surface_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_surface_model(obj):
            return obj
    return None


def _is_v1_surface_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SurfaceModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_surface_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SurfaceModel" or name.startswith("V1SurfaceModel")


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


def _span_region_value(value: str, index: int) -> str:
    try:
        parts = str(value or "").split("|")
        return str(parts[index]) if index < len(parts) else ""
    except Exception:
        return ""
