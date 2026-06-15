"""FreeCAD result object for v1 QuantityModel rows."""

from __future__ import annotations

from dataclasses import asdict, fields
import json

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.result.quantity_model import (
    QuantityAggregate,
    QuantityComparisonRow,
    QuantityFragment,
    QuantityGroupingRow,
    QuantityModel,
)


class V1QuantityModelObject:
    """Document object proxy that stores a v1 QuantityModel result."""

    Type = "V1QuantityModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_quantity_model_properties(obj)

    def execute(self, obj):
        ensure_v1_quantity_model_properties(obj)
        return


class ViewProviderV1QuantityModel:
    """Simple view provider for v1 QuantityModel objects."""

    Type = "ViewProviderV1QuantityModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("quantity.svg")
        except Exception:
            return ""


def ensure_v1_quantity_model_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 QuantityModel result properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "QuantityModelId", "CorridorRoad", "v1 quantity model id")
    _add_property(obj, "App::PropertyString", "CorridorId", "CorridorRoad", "corridor id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "FragmentCount", "Quantities", "quantity fragment row count")
    _add_property(obj, "App::PropertyInteger", "AggregateCount", "Quantities", "quantity aggregate row count")
    _add_property(obj, "App::PropertyInteger", "GroupingCount", "Quantities", "quantity grouping row count")
    _add_property(obj, "App::PropertyInteger", "ComparisonCount", "Quantities", "quantity comparison row count")
    _add_property(obj, "App::PropertyStringList", "FragmentRowsJson", "Payload", "quantity fragment rows as JSON")
    _add_property(obj, "App::PropertyStringList", "AggregateRowsJson", "Payload", "quantity aggregate rows as JSON")
    _add_property(obj, "App::PropertyStringList", "GroupingRowsJson", "Payload", "quantity grouping rows as JSON")
    _add_property(obj, "App::PropertyStringList", "ComparisonRowsJson", "Payload", "quantity comparison rows as JSON")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "diagnostic summary rows")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1QuantityModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "QuantityModelId", "") or ""):
        obj.QuantityModelId = f"quantity:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_quantity_model"


def create_or_update_v1_quantity_model_object(
    document=None,
    quantity_model: QuantityModel | None = None,
    *,
    project=None,
    object_name: str = "V1QuantityModel",
    label: str = "Quantities",
):
    """Create or update the durable v1 QuantityModel result object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 QuantityModel creation.")
    if quantity_model is None:
        quantity_model = QuantityModel(schema_version=1, project_id=_project_id(project), quantity_model_id="quantity:main")

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1QuantityModelObject(obj)
        try:
            ViewProviderV1QuantityModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1QuantityModelObject(obj)
    update_v1_quantity_model_object(obj, quantity_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_quantity_model_object(obj, quantity_model: QuantityModel, *, label: str = "Quantities"):
    """Write QuantityModel rows into an existing FreeCAD object."""

    ensure_v1_quantity_model_properties(obj)
    fragment_rows = list(getattr(quantity_model, "fragment_rows", []) or [])
    aggregate_rows = list(getattr(quantity_model, "aggregate_rows", []) or [])
    grouping_rows = list(getattr(quantity_model, "grouping_rows", []) or [])
    comparison_rows = list(getattr(quantity_model, "comparison_rows", []) or [])

    obj.Label = label
    obj.SchemaVersion = int(getattr(quantity_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(quantity_model, "project_id", "") or "corridorroad-v1")
    obj.QuantityModelId = str(getattr(quantity_model, "quantity_model_id", "") or "quantity:main")
    obj.CorridorId = str(getattr(quantity_model, "corridor_id", "") or "")
    obj.CRRecordKind = "v1_quantity_model"
    obj.FragmentCount = len(fragment_rows)
    obj.AggregateCount = len(aggregate_rows)
    obj.GroupingCount = len(grouping_rows)
    obj.ComparisonCount = len(comparison_rows)
    obj.FragmentRowsJson = [_json_dumps(asdict(row)) for row in fragment_rows]
    obj.AggregateRowsJson = [_json_dumps(asdict(row)) for row in aggregate_rows]
    obj.GroupingRowsJson = [_json_dumps(asdict(row)) for row in grouping_rows]
    obj.ComparisonRowsJson = [_json_dumps(asdict(row)) for row in comparison_rows]
    obj.SourceRefs = [str(value) for value in list(getattr(quantity_model, "source_refs", []) or []) if str(value)]
    obj.DiagnosticRows = [str(getattr(row, "kind", row)) for row in list(getattr(quantity_model, "diagnostic_rows", []) or [])]
    return obj


def find_v1_quantity_model(document=None):
    """Return the preferred v1 QuantityModel object from a document."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        return None
    preferred = None
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_v1_quantity_model_object(obj):
            if str(getattr(obj, "Name", "") or "") == "V1QuantityModel":
                return obj
            preferred = preferred or obj
    return preferred


def to_quantity_model(obj) -> QuantityModel | None:
    """Convert a v1 QuantityModel FreeCAD object back into a dataclass model."""

    if obj is None or not _is_v1_quantity_model_object(obj):
        return None
    ensure_v1_quantity_model_properties(obj)
    return QuantityModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        quantity_model_id=str(getattr(obj, "QuantityModelId", "") or "quantity:main"),
        corridor_id=str(getattr(obj, "CorridorId", "") or ""),
        fragment_rows=[QuantityFragment(**_known_dataclass_values(QuantityFragment, row)) for row in _json_rows(getattr(obj, "FragmentRowsJson", []) or [])],
        aggregate_rows=[QuantityAggregate(**row) for row in _json_rows(getattr(obj, "AggregateRowsJson", []) or [])],
        grouping_rows=[QuantityGroupingRow(**row) for row in _json_rows(getattr(obj, "GroupingRowsJson", []) or [])],
        comparison_rows=[QuantityComparisonRow(**row) for row in _json_rows(getattr(obj, "ComparisonRowsJson", []) or [])],
        source_refs=[str(value) for value in list(getattr(obj, "SourceRefs", []) or []) if str(value)],
    )


def _is_v1_quantity_model_object(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_quantity_model":
        return True
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1QuantityModel":
        return True
    proxy = getattr(obj, "Proxy", None)
    return str(getattr(proxy, "Type", "") or "") == "V1QuantityModel"


def _known_dataclass_values(row_type, values: dict[str, object]) -> dict[str, object]:
    known = {field.name for field in fields(row_type)}
    return {str(key): value for key, value in dict(values or {}).items() if str(key) in known}


def _json_rows(values) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for value in list(values or []):
        try:
            payload = json.loads(str(value or "{}"))
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _json_dumps(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _add_property(obj, prop_type: str, name: str, group: str, doc: str) -> None:
    if hasattr(obj, name):
        return
    try:
        obj.addProperty(prop_type, name, group, doc)
    except Exception:
        pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")
