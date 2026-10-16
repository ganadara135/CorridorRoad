"""FreeCAD source object for the v1 DrainageModel.

The model is stored as its typed payload; the count properties only summarize it in the property
view. A Drainage object written before the 2026-10-16 rework restores as an empty model, and its
old row properties are removed the next time it is written.
"""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.drainage_model import DrainageModel
from .persistence_payload_adapter import (
    ensure_model_payload_properties,
    read_model_payload,
    write_model_payload,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


_RETIRED_PROPERTIES = (
    "ElementCount",
    "DrainageElementIds",
    "ElementKinds",
    "ElementAlignmentRefs",
    "ElementIntersectionRefs",
    "ElementStructureRefs",
    "ElementConnectionPointRefs",
    "ElementSides",
    "ElementRegionRefs",
    "ElementSubassemblyRefs",
    "ElementStationStarts",
    "ElementStationEnds",
    "ElementPolicySetRefs",
    "PolicyCount",
    "PolicySetIds",
    "PolicyFlowIntents",
    "PolicyMinGradeRules",
    "PolicyLowPointRules",
    "PolicyCollectionRules",
    "PolicyDischargeRules",
    "PolicyEarthworkPriorities",
    "FlowRouteCount",
    "FlowRouteIds",
    "FlowRouteFromElementRefs",
    "FlowRouteToElementRefs",
    "FlowRouteOutletRefs",
    "FlowRouteDirections",
    "FlowRouteRiskLevels",
    "FlowRouteNotes",
    "ValidationStatus",
    "DiagnosticRows",
)


class V1DrainageModelObject:
    """Document object proxy that stores a v1 DrainageModel contract."""

    Type = "DrainageModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_drainage_properties(obj)

    def execute(self, obj):
        return


class ViewProviderV1DrainageModel:
    """Simple view provider for v1 Drainage source objects."""

    Type = "DrainageModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("drainage.svg")
        except Exception:
            return ""


def ensure_v1_drainage_properties(obj) -> None:
    """Ensure the FreeCAD object has the v1 DrainageModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "DrainageModelId", "CorridorRoad", "v1 drainage model id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "DitchRunCount", "Drainage", "ditch run count")
    _add_property(obj, "App::PropertyInteger", "PointCount", "Drainage", "inlet, outfall and culvert count")
    _add_property(obj, "App::PropertyInteger", "LinkCount", "Drainage", "link count")
    _add_property(obj, "App::PropertyFloat", "MinGradePercent", "Drainage", "policy minimum flowline grade (%)")
    _add_property(obj, "App::PropertyFloat", "MaxInletSpacing", "Drainage", "policy maximum inlet spacing (m)")
    _add_property(obj, "App::PropertyString", "LowPointRule", "Drainage", "policy low point rule")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")
    ensure_model_payload_properties(obj, add_property=_add_property)

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1DrainageModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "DrainageModelId", "") or ""):
        obj.DrainageModelId = "drainage:main"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_drainage_model"


def create_or_update_v1_drainage_model_object(
    document=None,
    drainage_model: DrainageModel | None = None,
    *,
    project=None,
    object_name: str = "V1DrainageModel",
    label: str = "Drainage",
):
    """Create or update the project's Drainage source object.

    A project has one Drainage source. The model is written into the existing object;
    `object_name` only names a new object.
    """

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 DrainageModel creation.")
    if drainage_model is None:
        drainage_model = DrainageModel(schema_version=1, project_id=_project_id(project))

    obj = find_v1_drainage_model(doc)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1DrainageModelObject(obj)
        try:
            ViewProviderV1DrainageModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1DrainageModelObject(obj)
    update_v1_drainage_model_object(obj, drainage_model, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_drainage_model_object(obj, drainage_model: DrainageModel, *, label: str = "Drainage"):
    """Write a DrainageModel into an existing FreeCAD object."""

    _remove_properties(obj, _RETIRED_PROPERTIES)
    ensure_v1_drainage_properties(obj)
    policy = drainage_model.policy
    obj.Label = label
    obj.SchemaVersion = int(getattr(drainage_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(drainage_model, "project_id", "") or "corridorroad-v1")
    obj.DrainageModelId = str(getattr(drainage_model, "drainage_model_id", "") or "drainage:main")
    obj.CRRecordKind = "v1_drainage_model"
    obj.DitchRunCount = len(drainage_model.ditch_run_rows)
    obj.PointCount = len(drainage_model.point_rows)
    obj.LinkCount = len(drainage_model.link_rows)
    obj.MinGradePercent = float(policy.min_grade_percent)
    obj.MaxInletSpacing = float(policy.max_inlet_spacing_m)
    obj.LowPointRule = str(policy.low_point_rule)
    obj.SourceRefs = [str(value) for value in list(getattr(drainage_model, "source_refs", []) or []) if str(value)]
    write_model_payload(
        obj,
        drainage_model,
        model_type="DrainageModel",
        row_fields=("ditch_run_rows", "point_rows", "link_rows"),
        required_refs=("project_id", "drainage_model_id"),
    )
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_drainage_model(obj) -> DrainageModel | None:
    """Build a DrainageModel from a v1 Drainage FreeCAD object.

    An object without a payload, or with one written before the rework, gives an empty model:
    its old rows have no meaning in the new model.
    """

    if not _is_v1_drainage_model(obj):
        return None
    payload_result = read_model_payload(
        obj,
        expected_model_type="DrainageModel",
        model_class=DrainageModel,
    )
    if payload_result is not None:
        return payload_result.model if payload_result.accepted else None
    return DrainageModel(
        schema_version=1,
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        drainage_model_id=str(getattr(obj, "DrainageModelId", "") or "drainage:main"),
        label=str(getattr(obj, "Label", "") or "Drainage"),
    )


def find_v1_drainage_model(document, preferred_drainage_model=None):
    """Find the project's v1 DrainageModel object in a document."""

    if _is_v1_drainage_model(preferred_drainage_model):
        return preferred_drainage_model
    rows = list_v1_drainage_models(document)
    return rows[0] if rows else None


def list_v1_drainage_models(document) -> list:
    """Return every v1 DrainageModel object in document order."""

    return [obj for obj in list(getattr(document, "Objects", []) or []) if _is_v1_drainage_model(obj)]


def _is_v1_drainage_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1DrainageModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_drainage_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "DrainageModel" or name.startswith("V1DrainageModel") or name.startswith("DrainageModel")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _remove_properties(obj, names: tuple[str, ...]) -> None:
    for name in names:
        if not hasattr(obj, name):
            continue
        try:
            obj.removeProperty(name)
        except Exception:
            pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")
