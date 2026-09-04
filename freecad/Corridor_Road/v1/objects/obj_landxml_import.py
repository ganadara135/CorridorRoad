"""FreeCAD provenance object for v1 LandXML import runs."""

from __future__ import annotations
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD unavailable in plain Python.
    App = None


class V1LandXMLImportObject:
    """Document object proxy that stores one LandXML import provenance snapshot."""

    Type = "LandXMLImport"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_landxml_import_properties(obj)

    def execute(self, obj):
        ensure_v1_landxml_import_properties(obj)
        return


class ViewProviderV1LandXMLImport:
    """Simple view provider for LandXML import provenance."""

    Type = "ViewProviderLandXMLImport"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("outputs_exchange.svg")
        except Exception:
            return ""


def ensure_v1_landxml_import_properties(obj) -> None:
    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "ImportId", "LandXML Import", "import id")
    _add_property(obj, "App::PropertyString", "SourcePath", "LandXML Import", "source file path")
    _add_property(obj, "App::PropertyString", "LandXMLVersion", "LandXML Import", "LandXML version")
    _add_property(obj, "App::PropertyString", "DetectedProducer", "LandXML Import", "detected producer")
    _add_property(obj, "App::PropertyBool", "SupportedProducer", "LandXML Import", "supported producer flag")
    _add_property(obj, "App::PropertyString", "LinearUnit", "LandXML Import", "linear unit")
    _add_property(obj, "App::PropertyInteger", "AlignmentCount", "LandXML Import", "alignment count")
    _add_property(obj, "App::PropertyInteger", "ProfileCount", "LandXML Import", "profile count")
    _add_property(obj, "App::PropertyInteger", "SurfaceCount", "LandXML Import", "surface count")
    _add_property(obj, "App::PropertyInteger", "CgPointCount", "LandXML Import", "CgPoint count")
    _add_property(obj, "App::PropertyStringList", "CreatedObjectRefs", "Traceability", "created object refs")
    _add_property(obj, "App::PropertyStringList", "DiagnosticRows", "Diagnostics", "diagnostic rows")
    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "LandXMLImport"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_landxml_import"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1


def create_or_update_v1_landxml_import_object(
    document=None,
    *,
    project=None,
    result=None,
    created_refs: list[str] | None = None,
):
    """Create/update the provenance object for one LandXML import result."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for LandXML import provenance.")
    if result is None:
        raise RuntimeError("A LandXML import result is required.")

    summary = result.summary
    import_id = _import_id(str(getattr(summary, "source_path", "") or "landxml-import"))
    object_name = _object_name(import_id)
    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1LandXMLImportObject(obj)
        try:
            ViewProviderV1LandXMLImport(obj.ViewObject)
        except Exception:
            pass
    else:
        V1LandXMLImportObject(obj)

    obj.Label = f"LandXML Import - {_file_label(str(summary.source_path or import_id))}"
    obj.ProjectId = _project_id(project)
    obj.ImportId = import_id
    obj.SourcePath = str(summary.source_path or "")
    obj.LandXMLVersion = str(summary.landxml_version or "")
    obj.DetectedProducer = str(summary.detected_producer or "")
    obj.SupportedProducer = bool(summary.supported_producer)
    obj.LinearUnit = str(summary.linear_unit or "")
    obj.AlignmentCount = int(summary.alignment_count or 0)
    obj.ProfileCount = int(summary.profile_count or 0)
    obj.SurfaceCount = int(summary.surface_count or 0)
    obj.CgPointCount = int(summary.cgpoint_count or 0)
    obj.CreatedObjectRefs = list(created_refs or [])
    obj.DiagnosticRows = [
        f"{row.severity}|{row.code}|{row.message}|{row.context}"
        for row in list(getattr(result, "diagnostics", []) or [])
    ]
    try:
        obj.touch()
    except Exception:
        pass
    if project is not None:
        try:
            route_object_to_project_tree(project, obj)
        except Exception:
            pass
    return obj


def _add_property(obj, property_type: str, name: str, group: str, doc: str = "") -> None:
    if obj is None or hasattr(obj, name):
        return
    try:
        obj.addProperty(property_type, name, group, doc)
    except Exception:
        pass


def _import_id(source_path: str) -> str:
    return f"landxml-import:{_slug(_file_label(source_path))}"


def _object_name(import_id: str) -> str:
    safe = _slug(import_id).replace(":", "_").replace("-", "_").replace(".", "_")
    if not safe.startswith("LandXMLImport"):
        safe = f"LandXMLImport_{safe}"
    return safe[:80] or "LandXMLImport"


def _file_label(source_path: str) -> str:
    try:
        from pathlib import Path

        return Path(str(source_path)).name or "LandXML"
    except Exception:
        return "LandXML"


def _slug(text: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_.:-]+", "-", str(text or "").strip()).strip("-") or "landxml"


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")
