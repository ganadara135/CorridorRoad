"""FreeCAD source object for reusable v1 Subassembly definitions."""

from __future__ import annotations

import json
from dataclasses import asdict

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.subassembly_definition_model import (
    SubassemblyDefinition,
    SubassemblyLibrary,
    SubassemblyLinkRow,
    SubassemblyParameterRow,
    SubassemblyPointRow,
    SubassemblyShapeRow,
    SubassemblyTargetRow,
)
from .persistence_payload_adapter import (
    ensure_model_payload_properties,
    read_model_payload,
    write_model_payload,
)
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


class V1SubassemblyLibraryObject:
    """Document object proxy that stores reusable Subassembly definition source rows."""

    Type = "V1SubassemblyLibrary"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_subassembly_library_properties(obj)

    def execute(self, obj):
        ensure_v1_subassembly_library_properties(obj)
        return


class ViewProviderV1SubassemblyLibrary:
    """Simple view provider for reusable Subassembly library source objects."""

    Type = "ViewProviderV1SubassemblyLibrary"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("subassembly_designer.svg")
        except Exception:
            return ""


def ensure_v1_subassembly_library_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 SubassemblyLibrary source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "LibraryId", "Subassembly Library", "v1 subassembly library id")
    _add_property(obj, "App::PropertyString", "PresetName", "Subassembly Library", "loaded preset name")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "DefinitionCount", "Subassembly Definitions", "definition row count")
    _add_property(obj, "App::PropertyStringList", "DefinitionIds", "Subassembly Definitions", "definition ids")
    _add_property(obj, "App::PropertyStringList", "DefinitionNames", "Subassembly Definitions", "definition names")
    _add_property(obj, "App::PropertyStringList", "DefinitionKinds", "Subassembly Definitions", "definition kinds")
    _add_property(obj, "App::PropertyStringList", "DefinitionRows", "Subassembly Definitions", "definition rows as JSON")
    ensure_model_payload_properties(obj, add_property=_add_property)

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SubassemblyLibrary"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "LibraryId", "") or ""):
        obj.LibraryId = f"subassembly-library:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_subassembly_library"


def create_or_update_v1_subassembly_library_object(
    document=None,
    library_model: SubassemblyLibrary | None = None,
    *,
    project=None,
    object_name: str = "V1SubassemblyLibrary",
    label: str = "SubAssembly Library",
):
    """Create or update the durable v1 SubassemblyLibrary source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SubassemblyLibrary creation.")
    if library_model is None:
        library_model = SubassemblyLibrary(
            schema_version=1,
            project_id=_project_id(project),
            library_id="subassembly-library:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SubassemblyLibraryObject(obj)
        try:
            ViewProviderV1SubassemblyLibrary(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SubassemblyLibraryObject(obj)
    update_v1_subassembly_library_object(obj, library_model, label=label)

    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_subassembly_library_object(
    obj,
    library_model: SubassemblyLibrary,
    *,
    label: str = "SubAssembly Library",
):
    """Write SubassemblyLibrary rows into an existing FreeCAD object."""

    ensure_v1_subassembly_library_properties(obj)
    definitions = list(getattr(library_model, "definition_rows", []) or [])
    obj.Label = _display_label(label, getattr(library_model, "library_id", ""))
    obj.SchemaVersion = int(getattr(library_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(library_model, "project_id", "") or "corridorroad-v1")
    obj.LibraryId = str(getattr(library_model, "library_id", "") or getattr(obj, "LibraryId", "") or "subassembly-library:main")
    obj.PresetName = str(getattr(library_model, "preset_name", "") or "")
    obj.CRRecordKind = "v1_subassembly_library"
    obj.DefinitionCount = len(definitions)
    obj.DefinitionIds = [str(row.definition_id) for row in definitions]
    obj.DefinitionNames = [str(row.name) for row in definitions]
    obj.DefinitionKinds = [str(row.kind) for row in definitions]
    obj.DefinitionRows = [_json_row(row) for row in definitions]
    write_model_payload(
        obj,
        library_model,
        model_type="SubassemblyLibrary",
        row_fields=("definition_rows",),
        required_refs=("project_id", "library_id"),
    )
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_subassembly_library(obj) -> SubassemblyLibrary | None:
    """Build a SubassemblyLibrary from a FreeCAD object."""

    if not _is_v1_subassembly_library(obj):
        return None
    ensure_v1_subassembly_library_properties(obj)
    payload_result = read_model_payload(
        obj,
        expected_model_type="SubassemblyLibrary",
        model_class=SubassemblyLibrary,
    )
    if payload_result is not None:
        return payload_result.model if payload_result.accepted else None
    definitions = [_definition_from_json_row(row) for row in _json_rows(getattr(obj, "DefinitionRows", []) or [])]
    return SubassemblyLibrary(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        label=str(getattr(obj, "Label", "") or "SubAssembly Library"),
        library_id=str(getattr(obj, "LibraryId", "") or "subassembly-library:main"),
        preset_name=str(getattr(obj, "PresetName", "") or ""),
        definition_rows=[definition for definition in definitions if definition is not None],
    )


def find_v1_subassembly_library(document, preferred_library=None):
    """Find a v1 SubassemblyLibrary object in a document."""

    if _is_v1_subassembly_library(preferred_library):
        return preferred_library
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_subassembly_library(obj):
            return obj
    return None


def list_v1_subassembly_libraries(document) -> list:
    """Return all v1 SubassemblyLibrary objects in document order."""

    if document is None:
        return []
    output = []
    seen = set()
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_v1_subassembly_library(obj):
            continue
        key = str(getattr(obj, "Name", "") or "")
        if key in seen:
            continue
        seen.add(key)
        output.append(obj)
    return output


def _definition_from_json_row(row: dict[str, object]) -> SubassemblyDefinition | None:
    try:
        return SubassemblyDefinition(
            definition_id=str(row.get("definition_id", "") or ""),
            name=str(row.get("name", "") or ""),
            kind=str(row.get("kind", "") or "lane"),
            category=str(row.get("category", "") or ""),
            side_behavior=str(row.get("side_behavior", "") or "agnostic"),
            parameter_rows=[
                SubassemblyParameterRow(**_dict_value(parameter_row))
                for parameter_row in _list_value(row.get("parameter_rows", []))
            ],
            point_rows=[
                SubassemblyPointRow(**_dict_value(point_row))
                for point_row in _list_value(row.get("point_rows", []))
            ],
            link_rows=[
                SubassemblyLinkRow(**_dict_value(link_row))
                for link_row in _list_value(row.get("link_rows", []))
            ],
            shape_rows=[
                SubassemblyShapeRow(**_dict_value(shape_row))
                for shape_row in _list_value(row.get("shape_rows", []))
            ],
            target_rows=[
                SubassemblyTargetRow(**_dict_value(target_row))
                for target_row in _list_value(row.get("target_rows", []))
            ],
            enabled=bool(row.get("enabled", True)),
            notes=str(row.get("notes", "") or ""),
        )
    except Exception:
        return None


def _is_v1_subassembly_library(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SubassemblyLibrary":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_subassembly_library":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SubassemblyLibrary" or name.startswith("V1SubassemblyLibrary")


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _display_label(label: str, library_id: str) -> str:
    base = str(label or "SubAssembly Library").strip() or "SubAssembly Library"
    ref = str(library_id or "").strip()
    if not ref:
        return base
    short_ref = ref.split(":", 1)[1] if ":" in ref else ref
    if ref in base or short_ref in base:
        return base
    return f"{base} - {short_ref}"


def _json_row(row) -> str:
    return json.dumps(asdict(row), sort_keys=True, separators=(",", ":"))


def _json_rows(values) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for value in list(values or []):
        try:
            row = json.loads(str(value or "{}"))
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}
