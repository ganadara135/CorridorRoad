"""FreeCAD source object for v1 AssemblySubassemblyModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.assembly_model import (
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
    parse_code_rules,
    parse_subassembly_parameters,
    serialize_code_rules,
    serialize_subassembly_parameters,
)


class V1AssemblySubassemblyModelObject:
    """Document object proxy that stores a v1 subassembly-based Assembly source."""

    Type = "V1AssemblySubassemblyModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_assembly_subassembly_properties(obj)

    def execute(self, obj):
        ensure_v1_assembly_subassembly_properties(obj)
        return


class ViewProviderV1AssemblySubassemblyModel:
    """Simple view provider for v1 Assembly/Subassembly source objects."""

    Type = "ViewProviderV1AssemblySubassemblyModel"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("typical_section.svg")
        except Exception:
            return ""


def ensure_v1_assembly_subassembly_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 AssemblySubassemblyModel properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "AssemblyId", "CorridorRoad", "v1 assembly id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked alignment id")
    _add_property(obj, "App::PropertyString", "ActiveTemplateId", "Assembly", "active template id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "TemplateCount", "Assembly", "template count")
    _add_property(obj, "App::PropertyStringList", "TemplateIds", "Assembly", "template ids")
    _add_property(obj, "App::PropertyStringList", "TemplateKinds", "Assembly", "template kinds")
    _add_property(obj, "App::PropertyStringList", "TemplateLabels", "Assembly", "template labels")
    _add_property(obj, "App::PropertyStringList", "TemplateNotes", "Assembly", "template notes")
    _add_property(obj, "App::PropertyInteger", "SubassemblyCount", "Subassemblies", "subassembly count")
    _add_property(obj, "App::PropertyStringList", "SubassemblyTemplateRefs", "Subassemblies", "subassembly template refs")
    _add_property(obj, "App::PropertyStringList", "SubassemblyIds", "Subassemblies", "subassembly ids")
    _add_property(obj, "App::PropertyIntegerList", "SubassemblyIndices", "Subassemblies", "subassembly indices")
    _add_property(obj, "App::PropertyStringList", "SubassemblyKinds", "Subassemblies", "subassembly kinds")
    _add_property(obj, "App::PropertyStringList", "SubassemblySides", "Subassemblies", "subassembly sides")
    _add_property(obj, "App::PropertyFloatList", "SubassemblyWidths", "Subassemblies", "subassembly widths")
    _add_property(obj, "App::PropertyFloatList", "SubassemblySlopes", "Subassemblies", "subassembly slopes")
    _add_property(obj, "App::PropertyFloatList", "SubassemblyThicknesses", "Subassemblies", "subassembly thicknesses")
    _add_property(obj, "App::PropertyStringList", "SubassemblyMaterials", "Subassemblies", "subassembly materials")
    _add_property(obj, "App::PropertyStringList", "SubassemblyTargetRefs", "Subassemblies", "subassembly target refs")
    _add_property(obj, "App::PropertyIntegerList", "SubassemblyEnabledValues", "Subassemblies", "subassembly enabled values")
    _add_property(obj, "App::PropertyStringList", "SubassemblyParameterRows", "Subassemblies", "subassembly parameters")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPointCodeRows", "Subassemblies", "point code rules")
    _add_property(obj, "App::PropertyStringList", "SubassemblyLinkCodeRows", "Subassemblies", "link code rules")
    _add_property(obj, "App::PropertyStringList", "SubassemblyShapeCodeRows", "Subassemblies", "shape code rules")
    _add_property(obj, "App::PropertyStringList", "SubassemblyNotes", "Subassemblies", "subassembly notes")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1AssemblySubassemblyModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "AssemblyId", "") or ""):
        obj.AssemblyId = f"assembly:{str(getattr(obj, 'Name', '') or 'v1-assembly-subassembly')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_assembly_subassembly_model"


def create_or_update_v1_assembly_subassembly_model_object(
    document=None,
    assembly_model: AssemblySubassemblyModel | None = None,
    *,
    project=None,
    object_name: str = "V1AssemblySubassemblyModel",
    label: str = "Assembly / Subassembly",
):
    """Create or update the durable v1 AssemblySubassemblyModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 Assembly/Subassembly creation.")
    if assembly_model is None:
        assembly_model = AssemblySubassemblyModel(
            schema_version=1,
            project_id=_project_id(project),
            assembly_id="assembly:subassembly-main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1AssemblySubassemblyModelObject(obj)
        try:
            ViewProviderV1AssemblySubassemblyModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1AssemblySubassemblyModelObject(obj)
    update_v1_assembly_subassembly_model_object(obj, assembly_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_assembly_subassembly_model_object(
    obj,
    assembly_model: AssemblySubassemblyModel,
    *,
    label: str = "Assembly / Subassembly",
):
    """Write AssemblySubassemblyModel rows into an existing FreeCAD object."""

    ensure_v1_assembly_subassembly_properties(obj)
    templates = list(getattr(assembly_model, "template_rows", []) or [])
    subassemblies: list[tuple[str, TemplateSubassembly]] = []
    for template in templates:
        for subassembly in list(template.subassembly_rows or []):
            subassemblies.append((template.template_id, subassembly))

    obj.Label = _display_label(label, getattr(assembly_model, "assembly_id", ""))
    obj.SchemaVersion = int(getattr(assembly_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(assembly_model, "project_id", "") or "corridorroad-v1")
    obj.AssemblyId = str(getattr(assembly_model, "assembly_id", "") or getattr(obj, "AssemblyId", "") or "assembly:subassembly-main")
    obj.AlignmentId = str(getattr(assembly_model, "alignment_id", "") or "")
    obj.ActiveTemplateId = str(getattr(assembly_model, "active_template_id", "") or "")
    obj.CRRecordKind = "v1_assembly_subassembly_model"
    obj.TemplateCount = len(templates)
    obj.TemplateIds = [str(row.template_id) for row in templates]
    obj.TemplateKinds = [str(row.template_kind) for row in templates]
    obj.TemplateLabels = [str(row.label) for row in templates]
    obj.TemplateNotes = [str(row.notes) for row in templates]
    obj.SubassemblyCount = len(subassemblies)
    obj.SubassemblyTemplateRefs = [template_id for template_id, _subassembly in subassemblies]
    obj.SubassemblyIds = [str(subassembly.subassembly_id) for _template_id, subassembly in subassemblies]
    obj.SubassemblyIndices = [
        int(subassembly.subassembly_index or index + 1)
        for index, (_template_id, subassembly) in enumerate(subassemblies)
    ]
    obj.SubassemblyKinds = [str(subassembly.kind) for _template_id, subassembly in subassemblies]
    obj.SubassemblySides = [str(subassembly.side) for _template_id, subassembly in subassemblies]
    obj.SubassemblyWidths = [float(subassembly.width) for _template_id, subassembly in subassemblies]
    obj.SubassemblySlopes = [float(subassembly.slope) for _template_id, subassembly in subassemblies]
    obj.SubassemblyThicknesses = [float(subassembly.thickness) for _template_id, subassembly in subassemblies]
    obj.SubassemblyMaterials = [str(subassembly.material) for _template_id, subassembly in subassemblies]
    obj.SubassemblyTargetRefs = [str(subassembly.target_ref) for _template_id, subassembly in subassemblies]
    obj.SubassemblyEnabledValues = [1 if bool(subassembly.enabled) else 0 for _template_id, subassembly in subassemblies]
    obj.SubassemblyParameterRows = [serialize_subassembly_parameters(subassembly.parameters) for _template_id, subassembly in subassemblies]
    obj.SubassemblyPointCodeRows = [serialize_code_rules(subassembly.point_code_rules) for _template_id, subassembly in subassemblies]
    obj.SubassemblyLinkCodeRows = [serialize_code_rules(subassembly.link_code_rules) for _template_id, subassembly in subassemblies]
    obj.SubassemblyShapeCodeRows = [serialize_code_rules(subassembly.shape_code_rules) for _template_id, subassembly in subassemblies]
    obj.SubassemblyNotes = [str(subassembly.notes) for _template_id, subassembly in subassemblies]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_assembly_subassembly_model(obj) -> AssemblySubassemblyModel | None:
    """Build an AssemblySubassemblyModel from a FreeCAD object."""

    if not _is_v1_assembly_subassembly_model(obj):
        return None
    ensure_v1_assembly_subassembly_properties(obj)
    template_ids = list(getattr(obj, "TemplateIds", []) or [])
    templates: list[SubassemblySectionTemplate] = []
    for index, template_id in enumerate(template_ids):
        subassemblies = []
        for subassembly_index, template_ref in enumerate(list(getattr(obj, "SubassemblyTemplateRefs", []) or [])):
            if str(template_ref) != str(template_id):
                continue
            subassemblies.append(
                TemplateSubassembly(
                    subassembly_id=_list_value(getattr(obj, "SubassemblyIds", []), subassembly_index, f"subassembly:{subassembly_index + 1}"),
                    subassembly_index=_int_list_value(getattr(obj, "SubassemblyIndices", []), subassembly_index, subassembly_index + 1),
                    kind=_list_value(getattr(obj, "SubassemblyKinds", []), subassembly_index, "lane"),
                    side=_list_value(getattr(obj, "SubassemblySides", []), subassembly_index, "center"),
                    width=_float_list_value(getattr(obj, "SubassemblyWidths", []), subassembly_index, 0.0),
                    slope=_float_list_value(getattr(obj, "SubassemblySlopes", []), subassembly_index, 0.0),
                    thickness=_float_list_value(getattr(obj, "SubassemblyThicknesses", []), subassembly_index, 0.0),
                    material=_list_value(getattr(obj, "SubassemblyMaterials", []), subassembly_index, ""),
                    target_ref=_list_value(getattr(obj, "SubassemblyTargetRefs", []), subassembly_index, ""),
                    parameters=parse_subassembly_parameters(_list_value(getattr(obj, "SubassemblyParameterRows", []), subassembly_index, "")),
                    point_code_rules=parse_code_rules(_list_value(getattr(obj, "SubassemblyPointCodeRows", []), subassembly_index, "")),
                    link_code_rules=parse_code_rules(_list_value(getattr(obj, "SubassemblyLinkCodeRows", []), subassembly_index, "")),
                    shape_code_rules=parse_code_rules(_list_value(getattr(obj, "SubassemblyShapeCodeRows", []), subassembly_index, "")),
                    notes=_list_value(getattr(obj, "SubassemblyNotes", []), subassembly_index, ""),
                    enabled=bool(_int_list_value(getattr(obj, "SubassemblyEnabledValues", []), subassembly_index, 1)),
                )
            )
        templates.append(
            SubassemblySectionTemplate(
                template_id=str(template_id),
                template_kind=_list_value(getattr(obj, "TemplateKinds", []), index, "roadway"),
                template_index=index + 1,
                label=_list_value(getattr(obj, "TemplateLabels", []), index, str(template_id)),
                subassembly_rows=subassemblies,
                notes=_list_value(getattr(obj, "TemplateNotes", []), index, ""),
            )
        )
    return AssemblySubassemblyModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        assembly_id=str(getattr(obj, "AssemblyId", "") or "assembly:subassembly-main"),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        active_template_id=str(getattr(obj, "ActiveTemplateId", "") or (templates[0].template_id if templates else "")),
        label=str(getattr(obj, "Label", "") or "Assembly / Subassembly"),
        template_rows=templates,
    )


def _display_label(label: str, assembly_id: str) -> str:
    base = str(label or "Assembly / Subassembly").strip() or "Assembly / Subassembly"
    ref = str(assembly_id or "").strip()
    if not ref:
        return base
    short_ref = ref.split(":", 1)[1] if ":" in ref else ref
    if ref in base or short_ref in base:
        return base
    return f"{base} - {short_ref}"


def find_v1_assembly_subassembly_model(document, preferred_assembly_model=None):
    """Find a v1 AssemblySubassemblyModel object in a document."""

    if _is_v1_assembly_subassembly_model(preferred_assembly_model):
        return preferred_assembly_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_assembly_subassembly_model(obj):
            return obj
    return None


def list_v1_assembly_subassembly_models(document) -> list:
    """Return all v1 AssemblySubassemblyModel objects in document order."""

    if document is None:
        return []
    output = []
    seen = set()
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_v1_assembly_subassembly_model(obj):
            continue
        key = str(getattr(obj, "Name", "") or "")
        if key in seen:
            continue
        seen.add(key)
        output.append(obj)
    return output


def assembly_subassembly_model_ids(document) -> list[str]:
    """Return stable AssemblySubassemblyModel ids available for references."""

    ids: list[str] = []
    seen = set()
    for obj in list_v1_assembly_subassembly_models(document):
        assembly_id = str(getattr(obj, "AssemblyId", "") or "").strip()
        if not assembly_id or assembly_id in seen:
            continue
        seen.add(assembly_id)
        ids.append(assembly_id)
    return ids


def _is_v1_assembly_subassembly_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1AssemblySubassemblyModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_assembly_subassembly_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1AssemblySubassemblyModel" or name.startswith("V1AssemblySubassemblyModel")


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


def _int_list_value(values, index: int, default: int = 0) -> int:
    try:
        values_list = list(values or [])
        return int(values_list[index]) if index < len(values_list) else int(default)
    except Exception:
        return int(default)
