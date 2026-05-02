"""FreeCAD output object for v1 exchange packages."""

from __future__ import annotations

import json
from dataclasses import asdict

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None


JSON_INLINE_LIMIT = 16000
JSON_CHUNK_SIZE = 12000
CHUNKED_JSON_MARKER = "__corridorroad_chunked_json__"


class V1ExchangePackageObject:
    """Document object proxy that stores a normalized v1 exchange package snapshot."""

    Type = "ExchangePackage"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_exchange_package_properties(obj)

    def execute(self, obj):
        ensure_v1_exchange_package_properties(obj)
        return


class ViewProviderV1ExchangePackage:
    """Simple view provider for v1 exchange package output objects."""

    Type = "ViewProviderExchangePackage"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = False
        except Exception:
            pass

    def getIcon(self):
        return ""


def ensure_v1_exchange_package_properties(obj) -> None:
    """Ensure the FreeCAD object has v1 exchange package properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyString", "CRRecordKind", "CorridorRoad", "v1 tree routing record kind")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "ExchangeOutputId", "Exchange", "exchange output id")
    _add_property(obj, "App::PropertyString", "ExchangeFormat", "Exchange", "exchange format")
    _add_property(obj, "App::PropertyString", "PackageKind", "Exchange", "package kind")
    _add_property(obj, "App::PropertyString", "CorridorId", "Exchange", "corridor id")
    _add_property(obj, "App::PropertyString", "StructureSolidOutputId", "Structure Output", "structure solid output id")
    _add_property(obj, "App::PropertyInteger", "StructureSolidCount", "Structure Output", "structure solid row count")
    _add_property(obj, "App::PropertyInteger", "StructureSolidSegmentCount", "Structure Output", "structure solid segment row count")
    _add_property(obj, "App::PropertyString", "ExportReadinessStatus", "Diagnostics", "export readiness status")
    _add_property(obj, "App::PropertyInteger", "ExportDiagnosticCount", "Diagnostics", "export diagnostic row count")
    _add_property(obj, "App::PropertyString", "QuantityOutputId", "Quantity Output", "quantity output id")
    _add_property(obj, "App::PropertyInteger", "QuantityFragmentCount", "Quantity Output", "quantity fragment row count")
    _add_property(obj, "App::PropertyStringList", "PackagedOutputIds", "Exchange", "packaged output ids")
    _add_property(obj, "App::PropertyStringList", "SourceRefs", "Traceability", "source refs")
    _add_property(obj, "App::PropertyStringList", "ResultRefs", "Traceability", "result refs")
    _add_property(obj, "App::PropertyString", "PayloadStorageMode", "Payload", "payload storage mode")
    _add_property(obj, "App::PropertyInteger", "PayloadByteCount", "Payload", "total serialized payload byte count")
    _add_property(obj, "App::PropertyString", "PayloadMetadataJson", "Payload", "exchange payload metadata")
    _add_property(obj, "App::PropertyStringList", "PayloadMetadataJsonChunks", "Payload", "chunked exchange payload metadata")
    _add_property(obj, "App::PropertyString", "FormatPayloadJson", "Payload", "exchange format payload")
    _add_property(obj, "App::PropertyStringList", "FormatPayloadJsonChunks", "Payload", "chunked exchange format payload")
    _add_property(obj, "App::PropertyString", "StructureSolidRowsJson", "Payload", "structure solid output rows")
    _add_property(obj, "App::PropertyStringList", "StructureSolidRowsJsonChunks", "Payload", "chunked structure solid output rows")
    _add_property(obj, "App::PropertyString", "StructureSolidSegmentRowsJson", "Payload", "structure solid segment output rows")
    _add_property(obj, "App::PropertyStringList", "StructureSolidSegmentRowsJsonChunks", "Payload", "chunked structure solid segment output rows")
    _add_property(obj, "App::PropertyString", "ExportDiagnosticRowsJson", "Payload", "export readiness diagnostic rows")
    _add_property(obj, "App::PropertyStringList", "ExportDiagnosticRowsJsonChunks", "Payload", "chunked export readiness diagnostic rows")
    _add_property(obj, "App::PropertyString", "QuantityFragmentRowsJson", "Payload", "quantity fragment output rows")
    _add_property(obj, "App::PropertyStringList", "QuantityFragmentRowsJsonChunks", "Payload", "chunked quantity fragment output rows")
    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "ExchangePackage"
    if not str(getattr(obj, "CRRecordKind", "") or ""):
        obj.CRRecordKind = "v1_exchange_package"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1


def create_or_update_v1_exchange_package_object(
    document=None,
    *,
    project=None,
    package_result=None,
    object_name: str = "ExchangePackageStructureGeometry",
    label: str = "Structure Geometry Exchange Package",
):
    """Create or update a persisted v1 ExchangePackage output object."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 exchange package creation.")
    if package_result is None:
        raise RuntimeError("A structure output package result is required.")

    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("App::FeaturePython", object_name)
        V1ExchangePackageObject(obj)
        try:
            ViewProviderV1ExchangePackage(obj.ViewObject)
        except Exception:
            pass
    else:
        V1ExchangePackageObject(obj)
    update_v1_exchange_package_object(obj, package_result, label=label)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_exchange_package_object(obj, package_result, *, label: str = "Structure Geometry Exchange Package"):
    """Write a structure output package result into an existing FreeCAD object."""

    ensure_v1_exchange_package_properties(obj)
    exchange_output = package_result.exchange_output
    structure_output = package_result.structure_solid_output
    quantity_output = package_result.quantity_output
    quantity_model = package_result.quantity_model
    obj.Label = label
    obj.V1ObjectType = "ExchangePackage"
    obj.CRRecordKind = "v1_exchange_package"
    obj.SchemaVersion = int(getattr(exchange_output, "schema_version", 1) or 1)
    obj.ProjectId = str(getattr(exchange_output, "project_id", "") or "")
    obj.ExchangeOutputId = str(getattr(exchange_output, "exchange_output_id", "") or "")
    obj.ExchangeFormat = str(getattr(exchange_output, "format", "") or "")
    obj.PackageKind = str(getattr(exchange_output, "package_kind", "") or "")
    obj.CorridorId = str(getattr(structure_output, "corridor_id", "") or getattr(quantity_model, "corridor_id", "") or "")
    obj.StructureSolidOutputId = str(getattr(structure_output, "structure_solid_output_id", "") or "")
    obj.StructureSolidCount = len(list(getattr(structure_output, "solid_rows", []) or []))
    obj.StructureSolidSegmentCount = len(list(getattr(structure_output, "solid_segment_rows", []) or []))
    export_diagnostics = list(getattr(structure_output, "diagnostic_rows", []) or [])
    obj.ExportReadinessStatus = _export_readiness_status(export_diagnostics)
    obj.ExportDiagnosticCount = len(export_diagnostics)
    obj.QuantityOutputId = str(getattr(quantity_output, "quantity_output_id", "") or "")
    obj.QuantityFragmentCount = len(list(getattr(quantity_output, "fragment_rows", []) or []))
    obj.PackagedOutputIds = [
        str(getattr(row, "output_id", "") or "")
        for row in list(getattr(exchange_output, "output_refs", []) or [])
        if str(getattr(row, "output_id", "") or "")
    ]
    obj.SourceRefs = list(getattr(exchange_output, "source_refs", []) or [])
    obj.ResultRefs = list(getattr(exchange_output, "result_refs", []) or [])
    payload_byte_count = 0
    payload_byte_count += _set_json_payload(obj, "PayloadMetadataJson", getattr(exchange_output, "payload_metadata", {}) or {})
    payload_byte_count += _set_json_payload(obj, "FormatPayloadJson", getattr(exchange_output, "format_payload", {}) or {})
    payload_byte_count += _set_json_payload(obj, "StructureSolidRowsJson", [asdict(row) for row in list(getattr(structure_output, "solid_rows", []) or [])])
    payload_byte_count += _set_json_payload(obj, "StructureSolidSegmentRowsJson", [asdict(row) for row in list(getattr(structure_output, "solid_segment_rows", []) or [])])
    payload_byte_count += _set_json_payload(obj, "ExportDiagnosticRowsJson", [asdict(row) for row in export_diagnostics])
    payload_byte_count += _set_json_payload(obj, "QuantityFragmentRowsJson", [asdict(row) for row in list(getattr(quantity_output, "fragment_rows", []) or [])])
    obj.PayloadByteCount = payload_byte_count
    obj.PayloadStorageMode = _payload_storage_mode(obj)
    try:
        obj.touch()
    except Exception:
        pass
    return obj


def find_v1_exchange_package(document, preferred_exchange_package=None):
    """Find a v1 ExchangePackage object in a document."""

    if _is_v1_exchange_package(preferred_exchange_package):
        return preferred_exchange_package
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_exchange_package(obj):
            return obj
    return None


def _is_v1_exchange_package(obj) -> bool:
    if obj is None:
        return False
    v1_type = str(getattr(obj, "V1ObjectType", "") or "")
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    return (
        v1_type == "ExchangePackage"
        or record_kind == "v1_exchange_package"
        or proxy_type == "ExchangePackage"
        or name.startswith("ExchangePackage")
    )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _set_json_payload(obj, property_name: str, value: object) -> int:
    text = _json(value)
    byte_count = len(text.encode("utf-8"))
    chunks_property = f"{property_name}Chunks"
    if byte_count > JSON_INLINE_LIMIT:
        chunks = _chunk_text(text)
        setattr(obj, chunks_property, chunks)
        setattr(
            obj,
            property_name,
            _json(
                {
                    "storage": CHUNKED_JSON_MARKER,
                    "chunk_property": chunks_property,
                    "chunk_count": len(chunks),
                    "byte_count": byte_count,
                }
            ),
        )
    else:
        setattr(obj, property_name, text)
        setattr(obj, chunks_property, [])
    return byte_count


def _chunk_text(text: str) -> list[str]:
    if not text:
        return []
    return [text[index : index + JSON_CHUNK_SIZE] for index in range(0, len(text), JSON_CHUNK_SIZE)]


def _payload_storage_mode(obj) -> str:
    for property_name in (
        "PayloadMetadataJsonChunks",
        "FormatPayloadJsonChunks",
        "StructureSolidRowsJsonChunks",
        "StructureSolidSegmentRowsJsonChunks",
        "ExportDiagnosticRowsJsonChunks",
        "QuantityFragmentRowsJsonChunks",
    ):
        if list(getattr(obj, property_name, []) or []):
            return "chunked"
    return "inline"


def _export_readiness_status(diagnostics: list[object]) -> str:
    severities = {str(getattr(row, "severity", "") or "").strip().lower() for row in list(diagnostics or [])}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warning"
    return "ready"


def _add_property(obj, property_type: str, name: str, group: str, description: str) -> None:
    try:
        existing = set(obj.PropertiesList)
    except Exception:
        existing = set()
    if name in existing:
        return
    try:
        obj.addProperty(property_type, name, group, description)
    except Exception:
        pass
