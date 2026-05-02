"""Export adapters for persisted v1 exchange package objects."""

from __future__ import annotations

import json
from pathlib import Path


def exchange_package_payload(exchange_package_obj) -> dict[str, object]:
    """Build a serializable payload from one persisted v1 ExchangePackage object."""

    if exchange_package_obj is None:
        raise RuntimeError("A v1 ExchangePackage object is required for export.")
    format_payload = _json_property(exchange_package_obj, "FormatPayloadJson", {})
    return {
        "schema_version": int(getattr(exchange_package_obj, "SchemaVersion", 1) or 1),
        "project_id": str(getattr(exchange_package_obj, "ProjectId", "") or ""),
        "exchange_output_id": str(getattr(exchange_package_obj, "ExchangeOutputId", "") or ""),
        "format": str(getattr(exchange_package_obj, "ExchangeFormat", "") or ""),
        "package_kind": str(getattr(exchange_package_obj, "PackageKind", "") or ""),
        "corridor_id": str(getattr(exchange_package_obj, "CorridorId", "") or ""),
        "structure_solid_output_id": str(getattr(exchange_package_obj, "StructureSolidOutputId", "") or ""),
        "structure_solid_count": int(getattr(exchange_package_obj, "StructureSolidCount", 0) or 0),
        "structure_solid_segment_count": int(getattr(exchange_package_obj, "StructureSolidSegmentCount", 0) or 0),
        "export_readiness_status": str(getattr(exchange_package_obj, "ExportReadinessStatus", "") or ""),
        "export_diagnostic_count": int(getattr(exchange_package_obj, "ExportDiagnosticCount", 0) or 0),
        "payload_storage_mode": str(getattr(exchange_package_obj, "PayloadStorageMode", "") or "inline"),
        "payload_byte_count": int(getattr(exchange_package_obj, "PayloadByteCount", 0) or 0),
        "quantity_output_id": str(getattr(exchange_package_obj, "QuantityOutputId", "") or ""),
        "quantity_fragment_count": int(getattr(exchange_package_obj, "QuantityFragmentCount", 0) or 0),
        "packaged_output_ids": list(getattr(exchange_package_obj, "PackagedOutputIds", []) or []),
        "source_refs": list(getattr(exchange_package_obj, "SourceRefs", []) or []),
        "result_refs": list(getattr(exchange_package_obj, "ResultRefs", []) or []),
        "payload_metadata": _json_property(exchange_package_obj, "PayloadMetadataJson", {}),
        "format_payload": format_payload,
        "structure_solid_rows": _json_property(exchange_package_obj, "StructureSolidRowsJson", []),
        "structure_solid_segment_rows": _json_property(exchange_package_obj, "StructureSolidSegmentRowsJson", []),
        "source_context_rows": list(format_payload.get("source_context_rows", []) or []) if isinstance(format_payload, dict) else [],
        "export_diagnostic_rows": _json_property(exchange_package_obj, "ExportDiagnosticRowsJson", []),
        "quantity_fragment_rows": _json_property(exchange_package_obj, "QuantityFragmentRowsJson", []),
    }


def export_exchange_package_to_json(path: str | Path, exchange_package_obj) -> dict[str, object]:
    """Write one persisted v1 ExchangePackage object to a JSON file."""

    export_path = Path(path)
    if not str(export_path):
        raise RuntimeError("An export path is required.")
    payload = exchange_package_payload(exchange_package_obj)
    payload_metadata = payload.get("payload_metadata", {}) or {}
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return {
        "path": str(export_path),
        "exchange_output_id": payload["exchange_output_id"],
        "structure_solid_count": payload["structure_solid_count"],
        "structure_solid_segment_count": payload["structure_solid_segment_count"],
        "export_readiness_status": payload["export_readiness_status"],
        "export_diagnostic_count": payload["export_diagnostic_count"],
        "payload_storage_mode": payload["payload_storage_mode"],
        "payload_byte_count": payload["payload_byte_count"],
        "quantity_fragment_count": payload["quantity_fragment_count"],
        "source_context_count": int(payload_metadata.get("source_context_count", 0) or 0),
        "side_slope_source_context_count": int(payload_metadata.get("side_slope_source_context_count", 0) or 0),
        "bench_source_context_count": int(payload_metadata.get("bench_source_context_count", 0) or 0),
        "packaged_output_count": len(list(payload["packaged_output_ids"] or [])),
    }


def _json_property(obj, property_name: str, fallback):
    chunks = list(getattr(obj, f"{property_name}Chunks", []) or [])
    if chunks:
        raw_from_chunks = "".join(str(chunk or "") for chunk in chunks)
        try:
            return json.loads(raw_from_chunks)
        except Exception:
            return fallback
    raw = str(getattr(obj, property_name, "") or "")
    if not raw:
        return fallback
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("storage") == "__corridorroad_chunked_json__":
            return fallback
        return parsed
    except Exception:
        return fallback
