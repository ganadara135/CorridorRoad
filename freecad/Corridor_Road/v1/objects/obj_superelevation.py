"""FreeCAD source object for v1 SuperelevationModel rows."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.superelevation_model import (
    CrossfallControlRow,
    RunoffTransitionRow,
    SuperelevationConstraint,
    SuperelevationModel,
)


class V1SuperelevationSourceObject:
    """Document object proxy that stores a v1 SuperelevationModel contract."""

    Type = "V1SuperelevationSource"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_superelevation_properties(obj)

    def execute(self, obj):
        ensure_v1_superelevation_properties(obj)
        return


class ViewProviderV1SuperelevationSource:
    """Simple view provider for v1 Superelevation source objects."""

    Type = "ViewProviderV1SuperelevationSource"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("superelevation.svg")
        except Exception:
            return ""


def ensure_v1_superelevation_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 SuperelevationModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "SuperelevationId", "CorridorRoad", "v1 superelevation id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked alignment id")
    _add_property(obj, "App::PropertyString", "ProfileId", "CorridorRoad", "linked profile id")
    _add_property(obj, "App::PropertyString", "SuperelevationKind", "CorridorRoad", "superelevation kind")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyString", "ControlRowsJson", "Controls", "crossfall control rows")
    _add_property(obj, "App::PropertyString", "TransitionRowsJson", "Transitions", "runoff transition rows")
    _add_property(obj, "App::PropertyString", "ConstraintRowsJson", "Constraints", "superelevation constraint rows")
    _add_property(obj, "App::PropertyString", "SourceRefsJson", "Source", "source refs")
    _add_property(obj, "App::PropertyString", "DiagnosticRowsJson", "Diagnostics", "diagnostic rows")
    _add_property(obj, "App::PropertyString", "LastValidationStatus", "Diagnostics", "last validation status")
    _add_property(obj, "App::PropertyInteger", "ControlRowCount", "Summary", "control row count")
    _add_property(obj, "App::PropertyInteger", "TransitionRowCount", "Summary", "transition row count")
    _add_property(obj, "App::PropertyInteger", "ConstraintRowCount", "Summary", "constraint row count")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SuperelevationSource"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "SuperelevationId", "") or ""):
        obj.SuperelevationId = f"superelevation:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "SuperelevationKind", "") or ""):
        obj.SuperelevationKind = "roadway_superelevation"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_superelevation_source"
    if not str(getattr(obj, "LastValidationStatus", "") or ""):
        obj.LastValidationStatus = "empty"
    for name in ("ControlRowsJson", "TransitionRowsJson", "ConstraintRowsJson", "SourceRefsJson", "DiagnosticRowsJson"):
        if not str(getattr(obj, name, "") or ""):
            setattr(obj, name, "[]")


def create_or_update_v1_superelevation_source_object(
    document=None,
    superelevation_model: SuperelevationModel | None = None,
    *,
    project=None,
    object_name: str = "V1SuperelevationSource",
    label: str = "Superelevation",
):
    """Create or update the durable v1 SuperelevationModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SuperelevationModel creation.")
    if superelevation_model is None:
        superelevation_model = SuperelevationModel(
            schema_version=1,
            project_id=_project_id(project),
            superelevation_id="superelevation:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SuperelevationSourceObject(obj)
        try:
            ViewProviderV1SuperelevationSource(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SuperelevationSourceObject(obj)
    update_v1_superelevation_source_object(obj, superelevation_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_superelevation_source_object(obj, superelevation_model: SuperelevationModel, *, label: str = "Superelevation"):
    """Write SuperelevationModel rows into an existing FreeCAD object."""

    ensure_v1_superelevation_properties(obj)
    control_rows = list(getattr(superelevation_model, "control_rows", []) or [])
    transition_rows = list(getattr(superelevation_model, "transition_rows", []) or [])
    constraint_rows = list(getattr(superelevation_model, "constraint_rows", []) or [])
    source_refs = list(getattr(superelevation_model, "source_refs", []) or [])
    diagnostic_rows = list(getattr(superelevation_model, "diagnostic_rows", []) or [])

    obj.Label = label or str(getattr(superelevation_model, "label", "") or "Superelevation")
    obj.SchemaVersion = int(getattr(superelevation_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(superelevation_model, "project_id", "") or "corridorroad-v1")
    obj.SuperelevationId = str(
        getattr(superelevation_model, "superelevation_id", "") or getattr(obj, "SuperelevationId", "") or "superelevation:main"
    )
    obj.AlignmentId = str(getattr(superelevation_model, "alignment_id", "") or "")
    obj.ProfileId = str(getattr(superelevation_model, "profile_id", "") or "")
    obj.SuperelevationKind = str(getattr(superelevation_model, "superelevation_kind", "") or "roadway_superelevation")
    obj.CRRecordKind = "v1_superelevation_source"
    obj.ControlRowsJson = _json_dumps(control_rows)
    obj.TransitionRowsJson = _json_dumps(transition_rows)
    obj.ConstraintRowsJson = _json_dumps(constraint_rows)
    obj.SourceRefsJson = _json_dumps([str(value) for value in source_refs])
    obj.DiagnosticRowsJson = _json_dumps(diagnostic_rows)
    obj.ControlRowCount = len(control_rows)
    obj.TransitionRowCount = len(transition_rows)
    obj.ConstraintRowCount = len(constraint_rows)
    if str(getattr(obj, "LastValidationStatus", "") or "") in {"", "empty"}:
        obj.LastValidationStatus = "stored" if control_rows or transition_rows else "empty"
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_superelevation_model(obj) -> SuperelevationModel | None:
    """Build a SuperelevationModel from a v1 Superelevation FreeCAD object."""

    if not _is_v1_superelevation_source(obj):
        return None
    ensure_v1_superelevation_properties(obj)
    return SuperelevationModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        label=str(getattr(obj, "Label", "") or "Superelevation"),
        superelevation_id=str(getattr(obj, "SuperelevationId", "") or "superelevation:main"),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        profile_id=str(getattr(obj, "ProfileId", "") or ""),
        superelevation_kind=str(getattr(obj, "SuperelevationKind", "") or "roadway_superelevation"),
        control_rows=[
            CrossfallControlRow(
                control_row_id=str(row.get("control_row_id", "") or f"control:{index + 1}"),
                station=_float_value(row.get("station", 0.0)),
                side=str(row.get("side", "") or "both"),
                crossfall_value=_float_value(row.get("crossfall_value", 0.0)),
                crossfall_unit=str(row.get("crossfall_unit", "") or "percent"),
                kind=str(row.get("kind", "") or "reference_crossfall"),
            )
            for index, row in enumerate(_json_list(getattr(obj, "ControlRowsJson", "[]")))
        ],
        transition_rows=[
            RunoffTransitionRow(
                transition_id=str(row.get("transition_id", "") or f"transition:{index + 1}"),
                station_start=_float_value(row.get("station_start", 0.0)),
                station_end=_float_value(row.get("station_end", 0.0)),
                kind=str(row.get("kind", "") or "crossfall_blend"),
                transition_policy=str(row.get("transition_policy", "") or "linear"),
            )
            for index, row in enumerate(_json_list(getattr(obj, "TransitionRowsJson", "[]")))
        ],
        constraint_rows=[
            SuperelevationConstraint(
                constraint_id=str(row.get("constraint_id", "") or f"constraint:{index + 1}"),
                kind=str(row.get("kind", "") or ""),
                value=row.get("value", ""),
                unit=str(row.get("unit", "") or ""),
                hard_or_soft=str(row.get("hard_or_soft", "") or "soft"),
            )
            for index, row in enumerate(_json_list(getattr(obj, "ConstraintRowsJson", "[]")))
        ],
        source_refs=[str(value) for value in _json_any_list(getattr(obj, "SourceRefsJson", "[]"))],
        diagnostic_rows=[],
    )


def find_v1_superelevation_source(document, preferred_superelevation=None):
    """Find a v1 Superelevation source object in a document."""

    if _is_v1_superelevation_source(preferred_superelevation):
        return preferred_superelevation
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_superelevation_source(obj):
            return obj
    return None


def _is_v1_superelevation_source(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SuperelevationSource":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_superelevation_source":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SuperelevationSource" or name.startswith("V1SuperelevationSource")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _json_dumps(value: object) -> str:
    rows = []
    if isinstance(value, list):
        rows = [_as_plain_json(row) for row in value]
    else:
        rows = _as_plain_json(value)
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))


def _as_plain_json(value: object):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _as_plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_plain_json(item) for item in value]
    return value


def _json_list(text: object) -> list[dict[str, object]]:
    rows = _json_any_list(text)
    return [row for row in rows if isinstance(row, dict)]


def _json_any_list(text: object) -> list[object]:
    try:
        data = json.loads(str(text or "[]"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _float_value(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")
