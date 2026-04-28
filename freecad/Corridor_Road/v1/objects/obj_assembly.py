"""FreeCAD source object for v1 AssemblyModel rows."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.assembly_model import AssemblyModel, SectionTemplate, TemplateComponent


class V1AssemblyModelObject:
    """Document object proxy that stores a v1 AssemblyModel contract."""

    Type = "V1AssemblyModel"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_assembly_properties(obj)

    def execute(self, obj):
        ensure_v1_assembly_properties(obj)
        return


class ViewProviderV1AssemblyModel:
    """Simple view provider for v1 Assembly source objects."""

    Type = "ViewProviderV1AssemblyModel"

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


def ensure_v1_assembly_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 AssemblyModel source properties."""

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
    _add_property(obj, "App::PropertyInteger", "ComponentCount", "Components", "component count")
    _add_property(obj, "App::PropertyStringList", "ComponentTemplateRefs", "Components", "component template refs")
    _add_property(obj, "App::PropertyStringList", "ComponentIds", "Components", "component ids")
    _add_property(obj, "App::PropertyIntegerList", "ComponentIndices", "Components", "component indices")
    _add_property(obj, "App::PropertyStringList", "ComponentKinds", "Components", "component kinds")
    _add_property(obj, "App::PropertyStringList", "ComponentSides", "Components", "component sides")
    _add_property(obj, "App::PropertyFloatList", "ComponentWidths", "Components", "component widths")
    _add_property(obj, "App::PropertyFloatList", "ComponentSlopes", "Components", "component slopes")
    _add_property(obj, "App::PropertyFloatList", "ComponentThicknesses", "Components", "component thicknesses")
    _add_property(obj, "App::PropertyStringList", "ComponentMaterials", "Components", "component materials")
    _add_property(obj, "App::PropertyStringList", "ComponentTargetRefs", "Components", "component target refs")
    _add_property(obj, "App::PropertyIntegerList", "ComponentEnabledValues", "Components", "component enabled values")
    _add_property(obj, "App::PropertyStringList", "ComponentParameterRows", "Components", "component parameters")
    _add_property(obj, "App::PropertyStringList", "ComponentNotes", "Components", "component notes")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1AssemblyModel"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "AssemblyId", "") or ""):
        obj.AssemblyId = f"assembly:{str(getattr(obj, 'Name', '') or 'v1-assembly')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_assembly_model"


def create_or_update_v1_assembly_model_object(
    document=None,
    assembly_model: AssemblyModel | None = None,
    *,
    project=None,
    object_name: str = "V1AssemblyModel",
    label: str = "Assembly",
):
    """Create or update the durable v1 AssemblyModel source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 AssemblyModel creation.")
    if assembly_model is None:
        assembly_model = AssemblyModel(schema_version=1, project_id=_project_id(project), assembly_id="assembly:main")

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1AssemblyModelObject(obj)
        try:
            ViewProviderV1AssemblyModel(obj.ViewObject)
        except Exception:
            pass
    else:
        V1AssemblyModelObject(obj)
    update_v1_assembly_model_object(obj, assembly_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_assembly_model_object(obj, assembly_model: AssemblyModel, *, label: str = "Assembly"):
    """Write AssemblyModel rows into an existing FreeCAD object."""

    ensure_v1_assembly_properties(obj)
    templates = list(getattr(assembly_model, "template_rows", []) or [])
    components: list[tuple[str, TemplateComponent]] = []
    for template in templates:
        for component in list(template.component_rows or []):
            components.append((template.template_id, component))

    obj.Label = label
    obj.SchemaVersion = int(getattr(assembly_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(assembly_model, "project_id", "") or "corridorroad-v1")
    obj.AssemblyId = str(getattr(assembly_model, "assembly_id", "") or getattr(obj, "AssemblyId", "") or "assembly:main")
    obj.AlignmentId = str(getattr(assembly_model, "alignment_id", "") or "")
    obj.ActiveTemplateId = str(getattr(assembly_model, "active_template_id", "") or "")
    obj.CRRecordKind = "v1_assembly_model"
    obj.TemplateCount = len(templates)
    obj.TemplateIds = [str(row.template_id) for row in templates]
    obj.TemplateKinds = [str(row.template_kind) for row in templates]
    obj.TemplateLabels = [str(row.label) for row in templates]
    obj.TemplateNotes = [str(row.notes) for row in templates]
    obj.ComponentCount = len(components)
    obj.ComponentTemplateRefs = [template_id for template_id, _component in components]
    obj.ComponentIds = [str(component.component_id) for _template_id, component in components]
    obj.ComponentIndices = [int(component.component_index or index + 1) for index, (_template_id, component) in enumerate(components)]
    obj.ComponentKinds = [str(component.kind) for _template_id, component in components]
    obj.ComponentSides = [str(component.side) for _template_id, component in components]
    obj.ComponentWidths = [float(component.width) for _template_id, component in components]
    obj.ComponentSlopes = [float(component.slope) for _template_id, component in components]
    obj.ComponentThicknesses = [float(component.thickness) for _template_id, component in components]
    obj.ComponentMaterials = [str(component.material) for _template_id, component in components]
    obj.ComponentTargetRefs = [str(component.target_ref) for _template_id, component in components]
    obj.ComponentEnabledValues = [1 if bool(component.enabled) else 0 for _template_id, component in components]
    obj.ComponentParameterRows = [_join_parameters(component.parameters) for _template_id, component in components]
    obj.ComponentNotes = [str(component.notes) for _template_id, component in components]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_assembly_model(obj) -> AssemblyModel | None:
    """Build an AssemblyModel from a v1 Assembly FreeCAD object."""

    if not _is_v1_assembly_model(obj):
        return None
    ensure_v1_assembly_properties(obj)
    template_ids = list(getattr(obj, "TemplateIds", []) or [])
    templates: list[SectionTemplate] = []
    for index, template_id in enumerate(template_ids):
        components = []
        for component_index, component_template_ref in enumerate(list(getattr(obj, "ComponentTemplateRefs", []) or [])):
            if str(component_template_ref) != str(template_id):
                continue
            components.append(
                TemplateComponent(
                    component_id=_list_value(getattr(obj, "ComponentIds", []), component_index, f"component:{component_index + 1}"),
                    component_index=_int_list_value(getattr(obj, "ComponentIndices", []), component_index, component_index + 1),
                    kind=_list_value(getattr(obj, "ComponentKinds", []), component_index, "lane"),
                    side=_list_value(getattr(obj, "ComponentSides", []), component_index, "center"),
                    width=_float_list_value(getattr(obj, "ComponentWidths", []), component_index, 0.0),
                    slope=_float_list_value(getattr(obj, "ComponentSlopes", []), component_index, 0.0),
                    thickness=_float_list_value(getattr(obj, "ComponentThicknesses", []), component_index, 0.0),
                    material=_list_value(getattr(obj, "ComponentMaterials", []), component_index, ""),
                    target_ref=_list_value(getattr(obj, "ComponentTargetRefs", []), component_index, ""),
                    parameters=_split_parameters(_list_value(getattr(obj, "ComponentParameterRows", []), component_index, "")),
                    notes=_list_value(getattr(obj, "ComponentNotes", []), component_index, ""),
                    enabled=bool(_int_list_value(getattr(obj, "ComponentEnabledValues", []), component_index, 1)),
                )
            )
        templates.append(
            SectionTemplate(
                template_id=str(template_id),
                template_kind=_list_value(getattr(obj, "TemplateKinds", []), index, "roadway"),
                template_index=index + 1,
                label=_list_value(getattr(obj, "TemplateLabels", []), index, str(template_id)),
                component_rows=components,
                notes=_list_value(getattr(obj, "TemplateNotes", []), index, ""),
            )
        )
    return AssemblyModel(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        assembly_id=str(getattr(obj, "AssemblyId", "") or "assembly:main"),
        alignment_id=str(getattr(obj, "AlignmentId", "") or ""),
        active_template_id=str(getattr(obj, "ActiveTemplateId", "") or (templates[0].template_id if templates else "")),
        label=str(getattr(obj, "Label", "") or "Assembly"),
        template_rows=templates,
    )


def find_v1_assembly_model(document, preferred_assembly_model=None):
    """Find a v1 AssemblyModel object in a document."""

    if _is_v1_assembly_model(preferred_assembly_model):
        return preferred_assembly_model
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_assembly_model(obj):
            return obj
    return None


def list_v1_assembly_models(document) -> list:
    """Return all v1 AssemblyModel objects in document order."""

    if document is None:
        return []
    output = []
    seen = set()
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_v1_assembly_model(obj):
            continue
        key = str(getattr(obj, "Name", "") or "")
        if key in seen:
            continue
        seen.add(key)
        output.append(obj)
    return output


def assembly_model_ids(document) -> list[str]:
    """Return stable AssemblyModel ids available for Region references."""

    ids: list[str] = []
    seen = set()
    for obj in list_v1_assembly_models(document):
        assembly_id = str(getattr(obj, "AssemblyId", "") or "").strip()
        if not assembly_id or assembly_id in seen:
            continue
        seen.add(assembly_id)
        ids.append(assembly_id)
    return ids


def _is_v1_assembly_model(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1AssemblyModel":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_assembly_model":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1AssemblyModel" or name.startswith("V1AssemblyModel")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _join_parameters(parameters: dict[str, object]) -> str:
    return ";".join(f"{key}={value}" for key, value in sorted(dict(parameters or {}).items()) if str(key).strip())


def _split_parameters(value: object) -> dict[str, str]:
    output: dict[str, str] = {}
    for token in str(value or "").split(";"):
        if "=" not in token:
            continue
        key, raw = token.split("=", 1)
        key = key.strip()
        if key:
            output[key] = raw.strip()
    return output


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
