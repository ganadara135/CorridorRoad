"""FreeCAD source object for v1 RegionModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.region_model import RegionModel, RegionRow
from ..services.evaluation.region_resolution_service import RegionValidationService


class V1RegionModelObject:
    """Document object proxy that stores a v1 RegionModel contract."""

    Type = "V1RegionModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_region_properties(obj)

    def execute(self, obj):
        ensure_v1_region_properties(obj)
        return


class ViewProviderV1RegionModel:
    """Simple view provider for v1 Region source objects."""

    Type = "ViewProviderV1RegionModel"

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


def ensure_v1_region_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 RegionModel source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "RegionModelId", "CorridorRoad", "v1 region model id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked alignment id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "RegionCount", "Regions", "region row count")
    _add_property(obj, "App::PropertyStringList", "RegionIds", "Regions", "region ids")
    _add_property(obj, "App::PropertyIntegerList", "RegionIndices", "Regions", "region indices")
    _add_property(obj, "App::PropertyStringList", "PrimaryKinds", "Regions", "primary region kinds")
    _add_property(obj, "App::PropertyStringList", "AppliedLayerRows", "Regions", "comma-separated applied layer rows")
    _add_property(obj, "App::PropertyFloatList", "StationStarts", "Regions", "region start stations")
    _add_property(obj, "App::PropertyFloatList", "StationEnds", "Regions", "region end stations")
    _add_property(obj, "App::PropertyStringList", "AssemblyRefs", "References", "assembly refs")
    _add_property(obj, "App::PropertyStringList", "TemplateRefs", "References", "template refs")
    _add_property(obj, "App::PropertyStringList", "PolicySetRefs", "References", "policy set refs")
    _add_property(obj, "App::PropertyStringList", "StructureRefRows", "References", "comma-separated structure refs")
    _add_property(obj, "App::PropertyStringList", "DrainageRefRows", "References", "comma-separated drainage refs")
    _add_property(obj, "App::PropertyStringList", "RampRefs", "References", "ramp refs")
    _add_property(obj, "App::PropertyStringList", "IntersectionRefs", "References", "intersection refs")
    _add_property(obj, "App::PropertyStringList", "SuperelevationRefs", "References", "superelevation refs")
    _add_property(obj, "App::PropertyStringList", "OverrideRefRows", "References", "comma-separated override refs")
    _add_property(obj, "App::PropertyIntegerList", "Priorities", "Regions", "region priorities")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Source", "region source refs")
    _add_property(obj, "App::PropertyStringList", "NotesRows", "Source", "region notes")
    _add_property(obj, "App::PropertyString", "ValidationStatus", "Diagnostics", "region validation status")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "region diagnostics")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1RegionModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "RegionModelId", "") or ""):
        obj.RegionModelId = f"regions:{str(getattr(obj, 'Name', '') or 'v1-regions')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_region_model"
    if not str(getattr(obj, "ValidationStatus", "") or ""):
        obj.ValidationStatus = "empty"


def create_or_update_v1_region_model_object(
    document=None,
    region_model: RegionModel | None = None,
    *,
    project=None,
    object_name: str = "V1RegionModel",
    label: str = "Regions",
):
    """Create or update the durable v1 RegionModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 RegionModel creation.")
    if region_model is None:
        region_model = RegionModel(schema_version=1, project_id=_project_id(project), region_model_id="regions:v1")

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1RegionModelObject(obj)
        try:
            ViewProviderV1RegionModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1RegionModelObject(obj)
    update_v1_region_model_object(obj, region_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_region_model_object(obj, region_model: RegionModel, *, label: str = "Regions"):
    """Write RegionModel rows into an existing FreeCAD object."""

    ensure_v1_region_properties(obj)
    rows = list(getattr(region_model, "region_rows", []) or [])
    validation = RegionValidationService().validate(region_model)

    obj.Label = label
    obj.SchemaVersion = int(getattr(region_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(region_model, "project_id", "") or "corridorroad-v1")
    obj.RegionModelId = str(getattr(region_model, "region_model_id", "") or getattr(obj, "RegionModelId", "") or "regions:v1")
    obj.AlignmentId = str(getattr(region_model, "alignment_id", "") or "")
    obj.CRRecordKind = "v1_region_model"
    obj.RegionCount = len(rows)
    obj.RegionIds = [str(row.region_id) for row in rows]
    obj.RegionIndices = [int(getattr(row, "region_index", index + 1) or index + 1) for index, row in enumerate(rows)]
    obj.PrimaryKinds = [str(row.primary_kind) for row in rows]
    obj.AppliedLayerRows = [_join_refs(row.applied_layers) for row in rows]
    obj.StationStarts = [float(row.station_start) for row in rows]
    obj.StationEnds = [float(row.station_end) for row in rows]
    obj.AssemblyRefs = [str(row.assembly_ref) for row in rows]
    obj.TemplateRefs = [str(row.template_ref) for row in rows]
    obj.PolicySetRefs = [str(row.policy_set_ref) for row in rows]
    obj.StructureRefRows = [_join_refs(row.structure_refs) for row in rows]
    obj.DrainageRefRows = [_join_refs(row.drainage_refs) for row in rows]
    obj.RampRefs = [str(row.ramp_ref) for row in rows]
    obj.IntersectionRefs = [str(row.intersection_ref) for row in rows]
    obj.SuperelevationRefs = [str(row.superelevation_ref) for row in rows]
    obj.OverrideRefRows = [_join_refs(row.override_refs) for row in rows]
    obj.Priorities = [int(row.priority) for row in rows]
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


def to_region_model(obj) -> RegionModel | None:
    """Build a RegionModel from a v1 Region FreeCAD object."""

    if not _is_v1_region_model(obj):
        return None
    ensure_v1_region_properties(obj)
    ids = list(getattr(obj, "RegionIds", []) or [])
    starts = _float_list(getattr(obj, "StationStarts", []) or [])
    ends = _float_list(getattr(obj, "StationEnds", []) or [])
    count = max(len(ids), len(starts), len(ends))
    region_rows: list[RegionRow] = []
    for index in range(count):
        region_rows.append(
            RegionRow(
                region_id=_list_value(ids, index, f"region:{index + 1}"),
                region_index=_int_list_value(getattr(obj, "RegionIndices", []), index, index + 1),
                primary_kind=_list_value(getattr(obj, "PrimaryKinds", []), index, "normal_road"),
                applied_layers=_split_refs(_list_value(getattr(obj, "AppliedLayerRows", []), index, "")),
                station_start=_float_list_value(starts, index, 0.0),
                station_end=_float_list_value(ends, index, 0.0),
                assembly_ref=_list_value(getattr(obj, "AssemblyRefs", []), index, ""),
                template_ref=_list_value(getattr(obj, "TemplateRefs", []), index, ""),
                policy_set_ref=_list_value(getattr(obj, "PolicySetRefs", []), index, ""),
                structure_refs=_split_refs(_list_value(getattr(obj, "StructureRefRows", []), index, "")),
                drainage_refs=_split_refs(_list_value(getattr(obj, "DrainageRefRows", []), index, "")),
                ramp_ref=_list_value(getattr(obj, "RampRefs", []), index, ""),
                intersection_ref=_list_value(getattr(obj, "IntersectionRefs", []), index, ""),
                superelevation_ref=_list_value(getattr(obj, "SuperelevationRefs", []), index, ""),
                override_refs=_split_refs(_list_value(getattr(obj, "OverrideRefRows", []), index, "")),
                priority=_int_list_value(getattr(obj, "Priorities", []), index, 0),
                source_ref=_list_value(getattr(obj, "SourceRefs", []), index, ""),
                notes=_list_value(getattr(obj, "NotesRows", []), index, ""),
            )
        )
    return RegionModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        region_model_id=str(getattr(obj, "RegionModelId", "") or "regions:v1"),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        label=str(getattr(obj, "Label", "") or "Regions"),
        region_rows=region_rows,
    )


def find_v1_region_model(document, preferred_region_model=None):
    """Find a v1 RegionModel object in a document."""

    if _is_v1_region_model(preferred_region_model):
        return preferred_region_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_region_model(obj):
            return obj
    return None


def _is_v1_region_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1RegionModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_region_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1RegionModel" or name.startswith("V1RegionModel")


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


def _int_list_value(values, index: int, default: int = 0) -> int:
    try:
        values_list = list(values or [])
        return int(values_list[index]) if index < len(values_list) else int(default)
    except Exception:
        return int(default)
