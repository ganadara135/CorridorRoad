"""FreeCAD source object for v1 SurfaceTransitionModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange
from ..services.evaluation.surface_transition_validation_service import SurfaceTransitionValidationService


class V1SurfaceTransitionModelObject:
    """Document object proxy that stores a v1 SurfaceTransitionModel contract."""

    Type = "V1SurfaceTransitionModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_surface_transition_properties(obj)

    def execute(self, obj):
        ensure_v1_surface_transition_properties(obj)
        return


class ViewProviderV1SurfaceTransitionModel:
    """Simple view provider for v1 SurfaceTransition source objects."""

    Type = "ViewProviderV1SurfaceTransitionModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("regions.svg")
        except Exception:
            return ""


def ensure_v1_surface_transition_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 SurfaceTransitionModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "TransitionModelId", "CorridorRoad", "v1 surface transition model id")
    _add_property(obj, "App::PropertyString", "CorridorRef", "CorridorRoad", "linked corridor ref")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "TransitionRangeCount", "Transitions", "transition row count")
    _add_property(obj, "App::PropertyStringList", "TransitionIds", "Transitions", "transition ids")
    _add_property(obj, "App::PropertyFloatList", "StationStarts", "Transitions", "transition start stations")
    _add_property(obj, "App::PropertyFloatList", "StationEnds", "Transitions", "transition end stations")
    _add_property(obj, "App::PropertyStringList", "FromRegionRefs", "References", "from Region refs")
    _add_property(obj, "App::PropertyStringList", "ToRegionRefs", "References", "to Region refs")
    _add_property(obj, "App::PropertyStringList", "TargetSurfaceKindRows", "Transitions", "comma-separated target surface kinds")
    _add_property(obj, "App::PropertyStringList", "TransitionModes", "Transitions", "transition modes")
    _add_property(obj, "App::PropertyFloatList", "SampleIntervals", "Transitions", "transition sample intervals")
    _add_property(obj, "App::PropertyStringList", "EnabledRows", "Transitions", "transition enabled flags")
    _add_property(obj, "App::PropertyStringList", "ApprovalStatuses", "Transitions", "approval statuses")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "transition source refs")
    _add_property(obj, "App::PropertyStringList", "NotesRows", "Source", "transition notes")
    _add_property(obj, "App::PropertyString", "ValidationStatus", "Diagnostics", "transition validation status")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "transition diagnostics")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SurfaceTransitionModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "TransitionModelId", "") or ""):
        obj.TransitionModelId = f"surface-transitions:{str(getattr(obj, 'Name', '') or 'v1-surface-transitions')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_surface_transition_model"
    if not str(getattr(obj, "ValidationStatus", "") or ""):
        obj.ValidationStatus = "empty"


def create_or_update_v1_surface_transition_model_object(
    document=None,
    transition_model: SurfaceTransitionModel | None = None,
    *,
    project=None,
    object_name: str = "V1SurfaceTransitionModel",
    label: str = "Surface Transitions",
):
    """Create or update the durable v1 SurfaceTransitionModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SurfaceTransitionModel creation.")
    if transition_model is None:
        transition_model = SurfaceTransitionModel(
            schema_version=1,
            project_id=_project_id(project),
            transition_model_id="surface-transitions:v1",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SurfaceTransitionModelObject(obj)
        try:
            ViewProviderV1SurfaceTransitionModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SurfaceTransitionModelObject(obj)
    update_v1_surface_transition_model_object(obj, transition_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_surface_transition_model_object(
    obj,
    transition_model: SurfaceTransitionModel,
    *,
    label: str = "Surface Transitions",
):
    """Write SurfaceTransitionModel rows into an existing FreeCAD object."""

    ensure_v1_surface_transition_properties(obj)
    rows = list(getattr(transition_model, "transition_ranges", []) or [])
    validation = SurfaceTransitionValidationService().validate(transition_model)

    obj.Label = label
    obj.SchemaVersion = int(getattr(transition_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(transition_model, "project_id", "") or "corridorroad-v1")
    obj.TransitionModelId = str(
        getattr(transition_model, "transition_model_id", "") or getattr(obj, "TransitionModelId", "") or "surface-transitions:v1"
    )
    obj.CorridorRef = str(getattr(transition_model, "corridor_ref", "") or "")
    obj.CRRecordKind = "v1_surface_transition_model"
    obj.TransitionRangeCount = len(rows)
    obj.TransitionIds = [str(row.transition_id) for row in rows]
    obj.StationStarts = [float(row.station_start) for row in rows]
    obj.StationEnds = [float(row.station_end) for row in rows]
    obj.FromRegionRefs = [str(row.from_region_ref) for row in rows]
    obj.ToRegionRefs = [str(row.to_region_ref) for row in rows]
    obj.TargetSurfaceKindRows = [_join_refs(row.target_surface_kinds) for row in rows]
    obj.TransitionModes = [str(row.transition_mode) for row in rows]
    obj.SampleIntervals = [float(row.sample_interval) for row in rows]
    obj.EnabledRows = ["true" if bool(row.enabled) else "false" for row in rows]
    obj.ApprovalStatuses = [str(row.approval_status) for row in rows]
    obj.SourceRefs = [str(row.source_ref) for row in rows]
    obj.NotesRows = [str(row.notes) for row in rows]
    obj.ValidationStatus = validation.status
    obj.DiagnosticRows = [
        f"{row.severity}|{row.kind}|{row.source_ref}|{row.message}"
        for row in validation.diagnostic_rows
    ]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_surface_transition_model(obj) -> SurfaceTransitionModel | None:
    """Build a SurfaceTransitionModel from a v1 SurfaceTransition FreeCAD object."""

    if not _is_v1_surface_transition_model(obj):
        return None
    ensure_v1_surface_transition_properties(obj)
    ids = list(getattr(obj, "TransitionIds", []) or [])
    starts = _float_list(getattr(obj, "StationStarts", []) or [])
    ends = _float_list(getattr(obj, "StationEnds", []) or [])
    count = max(len(ids), len(starts), len(ends))
    transition_ranges: list[SurfaceTransitionRange] = []
    for index in range(count):
        transition_ranges.append(
            SurfaceTransitionRange(
                transition_id=_list_value(ids, index, f"surface-transition:{index + 1}"),
                station_start=_float_list_value(starts, index, 0.0),
                station_end=_float_list_value(ends, index, 0.0),
                from_region_ref=_list_value(getattr(obj, "FromRegionRefs", []), index, ""),
                to_region_ref=_list_value(getattr(obj, "ToRegionRefs", []), index, ""),
                target_surface_kinds=_split_refs(_list_value(getattr(obj, "TargetSurfaceKindRows", []), index, "")),
                transition_mode=_list_value(getattr(obj, "TransitionModes", []), index, "interpolate_matching_roles"),
                sample_interval=_float_list_value(_float_list(getattr(obj, "SampleIntervals", [])), index, 5.0),
                enabled=_bool_value(_list_value(getattr(obj, "EnabledRows", []), index, "true")),
                approval_status=_list_value(getattr(obj, "ApprovalStatuses", []), index, "draft"),
                source_ref=_list_value(getattr(obj, "SourceRefs", []), index, ""),
                notes=_list_value(getattr(obj, "NotesRows", []), index, ""),
            )
        )
    return SurfaceTransitionModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        transition_model_id=str(getattr(obj, "TransitionModelId", "") or "surface-transitions:v1"),
        corridor_ref=str(getattr(obj, "CorridorRef", "") or ""),
        label=str(getattr(obj, "Label", "") or "Surface Transitions"),
        transition_ranges=transition_ranges,
    )


def find_v1_surface_transition_model(document, preferred_transition_model=None):
    """Find a v1 SurfaceTransitionModel object in a document."""

    if _is_v1_surface_transition_model(preferred_transition_model):
        return preferred_transition_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_surface_transition_model(obj):
            return obj
    return None


def _is_v1_surface_transition_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SurfaceTransitionModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_surface_transition_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SurfaceTransitionModel" or name.startswith("V1SurfaceTransitionModel")


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
    return ",".join(str(value).strip() for value in list(values or []) if str(value).strip())


def _split_refs(value: object) -> list[str]:
    return [token.strip() for token in str(value or "").replace(";", ",").split(",") if token.strip()]


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


def _float_list_value(values: list[float], index: int, default: float = 0.0) -> float:
    return float(values[index]) if index < len(values) else float(default)


def _bool_value(value: object) -> bool:
    return str(value or "").strip().lower() not in {"", "0", "false", "no", "off", "disabled"}
