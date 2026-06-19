"""FreeCAD source object for v1 Subassembly and Assembly preset libraries."""

from __future__ import annotations

import json
from dataclasses import asdict

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None

from ..models.source.subassembly_preset_model import (
    AssemblyPreset,
    AssemblySubassemblyInstance,
    SubassemblyPreset,
    SubassemblyPresetLibrary,
)


class V1SubassemblyPresetLibraryObject:
    """Document object proxy that stores shared Subassembly preset source rows."""

    Type = "V1SubassemblyPresetLibrary"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_subassembly_preset_library_properties(obj)

    def execute(self, obj):
        ensure_v1_subassembly_preset_library_properties(obj)
        return


class ViewProviderV1SubassemblyPresetLibrary:
    """Simple view provider for shared Subassembly preset library source objects."""

    Type = "ViewProviderV1SubassemblyPresetLibrary"

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


def ensure_v1_subassembly_preset_library_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 SubassemblyPresetLibrary source properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "LibraryId", "Preset Library", "v1 subassembly preset library id")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SubassemblyPresetCount", "Preset Library", "subassembly preset count")
    _add_property(obj, "App::PropertyInteger", "AssemblyPresetCount", "Preset Library", "assembly preset count")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPresetIds", "Subassembly Presets", "subassembly preset ids")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPresetNames", "Subassembly Presets", "subassembly preset names")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPresetKinds", "Subassembly Presets", "subassembly preset kinds")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPresetVersions", "Subassembly Presets", "subassembly preset versions")
    _add_property(obj, "App::PropertyStringList", "SubassemblyPresetRows", "Subassembly Presets", "subassembly preset rows as JSON")
    _add_property(obj, "App::PropertyStringList", "AssemblyPresetIds", "Assembly Presets", "assembly preset ids")
    _add_property(obj, "App::PropertyStringList", "AssemblyPresetNames", "Assembly Presets", "assembly preset names")
    _add_property(obj, "App::PropertyStringList", "AssemblyPresetVersions", "Assembly Presets", "assembly preset versions")
    _add_property(obj, "App::PropertyStringList", "AssemblyPresetRows", "Assembly Presets", "assembly preset rows as JSON")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1SubassemblyPresetLibrary"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "LibraryId", "") or ""):
        obj.LibraryId = f"subassembly-preset-library:{str(getattr(obj, 'Name', '') or 'main')}"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_subassembly_preset_library"


def create_or_update_v1_subassembly_preset_library_object(
    document=None,
    library_model: SubassemblyPresetLibrary | None = None,
    *,
    project=None,
    object_name: str = "V1SubassemblyPresetLibrary",
    label: str = "SubAssembly Preset Library",
):
    """Create or update the durable v1 SubassemblyPresetLibrary source object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 SubassemblyPresetLibrary creation.")
    if library_model is None:
        library_model = SubassemblyPresetLibrary(
            schema_version=1,
            project_id=_project_id(project),
            library_id="subassembly-preset-library:main",
        )

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1SubassemblyPresetLibraryObject(obj)
        try:
            ViewProviderV1SubassemblyPresetLibrary(obj.ViewObject)
        except Exception:
            pass
    else:
        V1SubassemblyPresetLibraryObject(obj)
    update_v1_subassembly_preset_library_object(obj, library_model, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_subassembly_preset_library_object(
    obj,
    library_model: SubassemblyPresetLibrary,
    *,
    label: str = "SubAssembly Preset Library",
):
    """Write SubassemblyPresetLibrary rows into an existing FreeCAD object."""

    ensure_v1_subassembly_preset_library_properties(obj)
    subassembly_presets = list(getattr(library_model, "subassembly_preset_rows", []) or [])
    assembly_presets = list(getattr(library_model, "assembly_preset_rows", []) or [])
    obj.Label = _display_label(label, getattr(library_model, "library_id", ""))
    obj.SchemaVersion = int(getattr(library_model, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(library_model, "project_id", "") or "corridorroad-v1")
    obj.LibraryId = str(getattr(library_model, "library_id", "") or getattr(obj, "LibraryId", "") or "subassembly-preset-library:main")
    obj.CRRecordKind = "v1_subassembly_preset_library"
    obj.SubassemblyPresetCount = len(subassembly_presets)
    obj.AssemblyPresetCount = len(assembly_presets)
    obj.SubassemblyPresetIds = [str(row.preset_id) for row in subassembly_presets]
    obj.SubassemblyPresetNames = [str(row.name) for row in subassembly_presets]
    obj.SubassemblyPresetKinds = [str(row.kind) for row in subassembly_presets]
    obj.SubassemblyPresetVersions = [str(row.version) for row in subassembly_presets]
    obj.SubassemblyPresetRows = [_json_row(row) for row in subassembly_presets]
    obj.AssemblyPresetIds = [str(row.preset_id) for row in assembly_presets]
    obj.AssemblyPresetNames = [str(row.name) for row in assembly_presets]
    obj.AssemblyPresetVersions = [str(row.version) for row in assembly_presets]
    obj.AssemblyPresetRows = [_json_row(row) for row in assembly_presets]
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def to_subassembly_preset_library(obj) -> SubassemblyPresetLibrary | None:
    """Build a SubassemblyPresetLibrary from a FreeCAD object."""

    if not _is_v1_subassembly_preset_library(obj):
        return None
    ensure_v1_subassembly_preset_library_properties(obj)
    subassembly_presets = [
        preset
        for preset in (_subassembly_preset_from_json_row(row) for row in _json_rows(getattr(obj, "SubassemblyPresetRows", []) or []))
        if preset is not None
    ]
    assembly_presets = [
        preset
        for preset in (_assembly_preset_from_json_row(row) for row in _json_rows(getattr(obj, "AssemblyPresetRows", []) or []))
        if preset is not None
    ]
    return SubassemblyPresetLibrary(
        schema_version=int(getattr(obj, "SchemaVersion", 1) or 1),
        project_id=str(getattr(obj, "ProjectId", "") or "corridorroad-v1"),
        label=str(getattr(obj, "Label", "") or "SubAssembly Preset Library"),
        library_id=str(getattr(obj, "LibraryId", "") or "subassembly-preset-library:main"),
        subassembly_preset_rows=subassembly_presets,
        assembly_preset_rows=assembly_presets,
    )


def find_v1_subassembly_preset_library(document, preferred_library=None):
    """Find a v1 SubassemblyPresetLibrary object in a document."""

    if _is_v1_subassembly_preset_library(preferred_library):
        return preferred_library
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_subassembly_preset_library(obj):
            return obj
    return None


def list_v1_subassembly_preset_libraries(document) -> list:
    """Return all v1 SubassemblyPresetLibrary objects in document order."""

    if document is None:
        return []
    output = []
    seen = set()
    for obj in list(getattr(document, "Objects", []) or []):
        if not _is_v1_subassembly_preset_library(obj):
            continue
        key = str(getattr(obj, "Name", "") or "")
        if key in seen:
            continue
        seen.add(key)
        output.append(obj)
    return output


def _subassembly_preset_from_json_row(row: dict[str, object]) -> SubassemblyPreset | None:
    try:
        return SubassemblyPreset(**_dict_value(row))
    except Exception:
        return None


def _assembly_preset_from_json_row(row: dict[str, object]) -> AssemblyPreset | None:
    try:
        data = _dict_value(row)
        data["instance_rows"] = tuple(
            AssemblySubassemblyInstance(**_dict_value(instance_row))
            for instance_row in _list_value(data.get("instance_rows", []))
        )
        return AssemblyPreset(**data)
    except Exception:
        return None


def _is_v1_subassembly_preset_library(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1SubassemblyPresetLibrary":
        return True
    if str(getattr(obj, "CRRecordKind", "") or "") == "v1_subassembly_preset_library":
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return proxy_type == "V1SubassemblyPresetLibrary" or name.startswith("V1SubassemblyPresetLibrary")


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
    base = str(label or "SubAssembly Preset Library").strip() or "SubAssembly Preset Library"
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
    output: list[dict[str, object]] = []
    for value in list(values or []):
        try:
            data = json.loads(str(value or "{}"))
            if isinstance(data, dict):
                output.append(data)
        except Exception:
            continue
    return output


def _dict_value(value: object) -> dict[str, object]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _list_value(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []
