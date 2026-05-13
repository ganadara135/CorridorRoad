"""FreeCAD source object for v1 DrainageModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.drainage_model import (
    DrainageElementRow,
    DrainageFlowRoute,
    DrainageModel,
    DrainagePolicySet,
)
from ..services.evaluation.drainage_resolution_service import DrainageValidationService


_OBSOLETE_FLOW_ROUTE_PROPERTIES = (
    "CollectionRegionCount",
    "CollectionStationStarts",
    "CollectionStationEnds",
    "CollectionAlignmentRefs",
    "CollectionRampRefs",
    "CollectionIntersectionRefs",
    "FlowRouteReceiverRefs",
    "CollectionRegionIds",
    "CollectionExpectedReceiverRefs",
    "CollectionRegionKinds",
    "CollectionRiskLevels",
)


class V1DrainageModelObject:
    """Document object proxy that stores a v1 DrainageModel contract."""

    Type = "DrainageModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_drainage_properties(obj)

    def execute(self, obj):
        ensure_v1_drainage_properties(obj)
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
    """Ensure the FreeCAD object has v1 DrainageModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "DrainageModelId", "CorridorRoad", "v1 drainage model id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "ElementCount", "Drainage Elements", "drainage element count")
    _add_property(obj, "App::PropertyStringList", "DrainageElementIds", "Drainage Elements", "drainage element ids")
    _add_property(obj, "App::PropertyStringList", "ElementKinds", "Drainage Elements", "drainage element kinds")
    _add_property(obj, "App::PropertyStringList", "ElementAlignmentRefs", "Drainage Elements", "alignment refs")
    _add_property(obj, "App::PropertyStringList", "ElementRampRefs", "Drainage Elements", "ramp refs")
    _add_property(obj, "App::PropertyStringList", "ElementIntersectionRefs", "Drainage Elements", "intersection refs")
    _add_property(obj, "App::PropertyStringList", "ElementStructureRefs", "Drainage Elements", "structure refs")
    _add_property(obj, "App::PropertyStringList", "ElementConnectionPointRefs", "Drainage Elements", "structure connection point refs")
    _add_property(obj, "App::PropertyStringList", "ElementSides", "Drainage Elements", "element sides")
    _add_property(obj, "App::PropertyStringList", "ElementRegionRefs", "Drainage Elements", "region refs")
    _add_property(obj, "App::PropertyStringList", "ElementAssemblyComponentRefs", "Drainage Elements", "assembly component refs")
    _add_property(obj, "App::PropertyFloatList", "ElementStationStarts", "Drainage Elements", "element start stations")
    _add_property(obj, "App::PropertyFloatList", "ElementStationEnds", "Drainage Elements", "element end stations")
    _add_property(obj, "App::PropertyStringList", "ElementPolicySetRefs", "Drainage Elements", "policy set refs")
    _add_property(obj, "App::PropertyInteger", "PolicyCount", "Policies", "policy row count")
    _add_property(obj, "App::PropertyStringList", "PolicySetIds", "Policies", "policy set ids")
    _add_property(obj, "App::PropertyStringList", "PolicyFlowIntents", "Policies", "flow intents")
    _add_property(obj, "App::PropertyStringList", "PolicyMinGradeRules", "Policies", "min grade rules")
    _add_property(obj, "App::PropertyStringList", "PolicyLowPointRules", "Policies", "low point rules")
    _add_property(obj, "App::PropertyStringList", "PolicyCollectionRules", "Policies", "collection rules")
    _add_property(obj, "App::PropertyStringList", "PolicyDischargeRules", "Policies", "discharge rules")
    _add_property(obj, "App::PropertyStringList", "PolicyEarthworkPriorities", "Policies", "earthwork priorities")
    _add_property(obj, "App::PropertyInteger", "FlowRouteCount", "Flow Routes", "flow route count")
    _add_property(obj, "App::PropertyStringList", "FlowRouteIds", "Flow Routes", "flow route ids")
    _add_property(obj, "App::PropertyStringList", "FlowRouteFromElementRefs", "Flow Routes", "from element refs")
    _add_property(obj, "App::PropertyStringList", "FlowRouteToElementRefs", "Flow Routes", "to element refs")
    _add_property(obj, "App::PropertyStringList", "FlowRouteOutletRefs", "Flow Routes", "outlet refs")
    _add_property(obj, "App::PropertyStringList", "FlowRouteDirections", "Flow Routes", "flow route directions")
    _add_property(obj, "App::PropertyStringList", "FlowRouteRiskLevels", "Flow Routes", "risk levels")
    _add_property(obj, "App::PropertyStringList", "FlowRouteNotes", "Flow Routes", "notes")
    _remove_obsolete_properties(obj, _OBSOLETE_FLOW_ROUTE_PROPERTIES)
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "source refs")
    _add_property(obj, "App::PropertyString", "ValidationStatus", "Diagnostics", "validation status")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "diagnostic rows")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1DrainageModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "DrainageModelId", "") or ""):
        obj.DrainageModelId = f"drainage:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_drainage_model"
    if not str(getattr(obj, "ValidationStatus", "") or ""):
        obj.ValidationStatus = "empty"


def create_or_update_v1_drainage_model_object(
    document=None,
    drainage_model: DrainageModel | None = None,
    *,
    project=None,
    object_name: str = "V1DrainageModel",
    label: str = "Drainage",
):
    """Create or update the durable v1 DrainageModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 DrainageModel creation.")
    if drainage_model is None:
        drainage_model = DrainageModel(schema_version=1, project_id=_project_id(project), drainage_model_id="drainage:main")

    obj = doc.getObject(object_name)
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
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_drainage_model_object(obj, drainage_model: DrainageModel, *, label: str = "Drainage"):
    """Write DrainageModel rows into an existing FreeCAD object."""

    ensure_v1_drainage_properties(obj)
    element_rows = list(getattr(drainage_model, "element_rows", []) or [])
    policy_rows = list(getattr(drainage_model, "policy_rows", []) or [])
    flow_route_rows = list(getattr(drainage_model, "flow_route_rows", []) or [])
    validation = DrainageValidationService().validate(drainage_model)

    obj.Label = label
    obj.SchemaVersion = int(getattr(drainage_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(drainage_model, "project_id", "") or "corridorroad-v1")
    obj.DrainageModelId = str(getattr(drainage_model, "drainage_model_id", "") or getattr(obj, "DrainageModelId", "") or "drainage:main")
    obj.CRRecordKind = "v1_drainage_model"
    obj.ElementCount = len(element_rows)
    obj.DrainageElementIds = [str(row.drainage_element_id) for row in element_rows]
    obj.ElementKinds = [str(row.element_kind) for row in element_rows]
    obj.ElementAlignmentRefs = [str(row.alignment_ref) for row in element_rows]
    obj.ElementRampRefs = [str(row.ramp_ref) for row in element_rows]
    obj.ElementIntersectionRefs = [str(row.intersection_ref) for row in element_rows]
    obj.ElementStructureRefs = [str(row.structure_ref) for row in element_rows]
    obj.ElementConnectionPointRefs = [str(getattr(row, "connection_point_ref", "") or "") for row in element_rows]
    obj.ElementSides = [str(getattr(row, "side", "") or "") for row in element_rows]
    obj.ElementRegionRefs = [str(getattr(row, "region_ref", "") or "") for row in element_rows]
    obj.ElementAssemblyComponentRefs = [str(getattr(row, "assembly_component_ref", "") or "") for row in element_rows]
    obj.ElementStationStarts = [float(row.station_start) for row in element_rows]
    obj.ElementStationEnds = [float(row.station_end) for row in element_rows]
    obj.ElementPolicySetRefs = [str(row.policy_set_ref) for row in element_rows]
    obj.PolicyCount = len(policy_rows)
    obj.PolicySetIds = [str(row.policy_set_id) for row in policy_rows]
    obj.PolicyFlowIntents = [str(row.flow_intent) for row in policy_rows]
    obj.PolicyMinGradeRules = [str(row.min_grade_rule) for row in policy_rows]
    obj.PolicyLowPointRules = [str(row.low_point_rule) for row in policy_rows]
    obj.PolicyCollectionRules = [str(row.collection_rule) for row in policy_rows]
    obj.PolicyDischargeRules = [str(row.discharge_rule) for row in policy_rows]
    obj.PolicyEarthworkPriorities = [str(row.earthwork_priority) for row in policy_rows]
    obj.FlowRouteCount = len(flow_route_rows)
    obj.FlowRouteIds = [str(row.flow_route_id) for row in flow_route_rows]
    obj.FlowRouteFromElementRefs = [str(row.from_element_ref) for row in flow_route_rows]
    obj.FlowRouteToElementRefs = [str(row.to_element_ref) for row in flow_route_rows]
    obj.FlowRouteOutletRefs = [str(row.outlet_ref) for row in flow_route_rows]
    obj.FlowRouteDirections = [str(row.direction) for row in flow_route_rows]
    obj.FlowRouteRiskLevels = [str(row.risk_level) for row in flow_route_rows]
    obj.FlowRouteNotes = [str(row.notes) for row in flow_route_rows]
    obj.SourceRefs = [str(value) for value in list(getattr(drainage_model, "source_refs", []) or []) if str(value)]
    obj.ValidationStatus = validation.status
    obj.DiagnosticRows = [
        f"{getattr(row, 'severity', '')}|{getattr(row, 'kind', '')}|{getattr(row, 'source_ref', '')}|{getattr(row, 'message', '')}|{getattr(row, 'notes', '')}"
        for row in [
            *list(validation.diagnostic_rows or []),
            *list(getattr(drainage_model, "diagnostic_rows", []) or []),
        ]
    ]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_drainage_model(obj) -> DrainageModel | None:
    """Build a DrainageModel from a v1 Drainage FreeCAD object."""

    if not _is_v1_drainage_model(obj):
        return None
    ensure_v1_drainage_properties(obj)
    element_ids = list(getattr(obj, "DrainageElementIds", []) or [])
    element_count = max(
        len(element_ids),
        len(list(getattr(obj, "ElementStationStarts", []) or [])),
        len(list(getattr(obj, "ElementStationEnds", []) or [])),
    )
    element_rows = [
        DrainageElementRow(
            drainage_element_id=_list_value(element_ids, index, f"drainage:element:{index + 1}"),
            element_kind=_list_value(getattr(obj, "ElementKinds", []), index, "ditch"),
            alignment_ref=_list_value(getattr(obj, "ElementAlignmentRefs", []), index, ""),
            ramp_ref=_list_value(getattr(obj, "ElementRampRefs", []), index, ""),
            intersection_ref=_list_value(getattr(obj, "ElementIntersectionRefs", []), index, ""),
            structure_ref=_list_value(getattr(obj, "ElementStructureRefs", []), index, ""),
            connection_point_ref=_list_value(getattr(obj, "ElementConnectionPointRefs", []), index, ""),
            side=_list_value(getattr(obj, "ElementSides", []), index, ""),
            region_ref=_list_value(getattr(obj, "ElementRegionRefs", []), index, ""),
            assembly_component_ref=_list_value(getattr(obj, "ElementAssemblyComponentRefs", []), index, ""),
            station_start=_float_list_value(getattr(obj, "ElementStationStarts", []), index),
            station_end=_float_list_value(getattr(obj, "ElementStationEnds", []), index),
            policy_set_ref=_list_value(getattr(obj, "ElementPolicySetRefs", []), index, ""),
        )
        for index in range(element_count)
    ]
    policy_ids = list(getattr(obj, "PolicySetIds", []) or [])
    policy_rows = [
        DrainagePolicySet(
            policy_set_id=_list_value(policy_ids, index, f"drainage-policy:{index + 1}"),
            flow_intent=_list_value(getattr(obj, "PolicyFlowIntents", []), index, ""),
            min_grade_rule=_list_value(getattr(obj, "PolicyMinGradeRules", []), index, ""),
            low_point_rule=_list_value(getattr(obj, "PolicyLowPointRules", []), index, ""),
            collection_rule=_list_value(getattr(obj, "PolicyCollectionRules", []), index, ""),
            discharge_rule=_list_value(getattr(obj, "PolicyDischargeRules", []), index, ""),
            earthwork_priority=_list_value(getattr(obj, "PolicyEarthworkPriorities", []), index, ""),
        )
        for index in range(len(policy_ids))
    ]
    flow_route_rows = _flow_route_rows_from_object(obj)
    return DrainageModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        drainage_model_id=str(getattr(obj, "DrainageModelId", "") or "drainage:main"),
        label=str(getattr(obj, "Label", "") or "Drainage"),
        source_refs=[str(value) for value in list(getattr(obj, "SourceRefs", []) or []) if str(value)],
        element_rows=element_rows,
        policy_rows=policy_rows,
        flow_route_rows=flow_route_rows,
    )


def find_v1_drainage_model(document, preferred_drainage_model=None):
    """Find a v1 DrainageModel object in a document."""

    if _is_v1_drainage_model(preferred_drainage_model):
        return preferred_drainage_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_drainage_model(obj):
            return obj
    return None


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


def _flow_route_rows_from_object(obj) -> list[DrainageFlowRoute]:
    route_ids = list(getattr(obj, "FlowRouteIds", []) or [])
    route_from_refs = list(getattr(obj, "FlowRouteFromElementRefs", []) or [])
    route_outlets = list(getattr(obj, "FlowRouteOutletRefs", []) or [])
    route_count = max(
        len(route_ids),
        len(route_from_refs),
        len(route_outlets),
    )
    return [
        DrainageFlowRoute(
            flow_route_id=_list_value(route_ids, index, f"flow-route:{index + 1}"),
            from_element_ref=_list_value(getattr(obj, "FlowRouteFromElementRefs", []), index, ""),
            to_element_ref=_list_value(getattr(obj, "FlowRouteToElementRefs", []), index, ""),
            outlet_ref=_list_value(getattr(obj, "FlowRouteOutletRefs", []), index, ""),
            direction=_list_value(getattr(obj, "FlowRouteDirections", []), index, ""),
            risk_level=_list_value(getattr(obj, "FlowRouteRiskLevels", []), index, ""),
            notes=_list_value(getattr(obj, "FlowRouteNotes", []), index, ""),
        )
        for index in range(route_count)
    ]


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _remove_obsolete_properties(obj, names: tuple[str, ...]) -> None:
    if obj is None:
        return
    for name in names:
        if not hasattr(obj, name):
            continue
        try:
            obj.removeProperty(name)
        except Exception:
            try:
                obj.delProperty(name)
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
