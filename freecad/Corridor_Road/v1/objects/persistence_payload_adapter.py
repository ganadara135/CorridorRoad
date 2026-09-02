"""FreeCAD property adapter for typed v1 model payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..models.persistence import (
    CURRENT_PAYLOAD_SCHEMA_VERSION,
    PersistenceDiagnostic,
    PayloadRestoreResult,
    fingerprint_for,
    restore_model_payload,
    serialize_model_payload,
)
from ..models.result.incremental_rebuild import IncrementalStageRecord


@dataclass(frozen=True)
class PayloadPropertyNames:
    schema_version: str = "PayloadSchemaVersion"
    json: str = "ModelPayloadJson"
    checksum: str = "ModelPayloadChecksum"
    fingerprint: str = "SourceFingerprint"
    diagnostics: str = "PersistenceDiagnosticRows"


PAYLOAD_PROPERTIES = PayloadPropertyNames()


@dataclass(frozen=True)
class IncrementalPropertyNames:
    stage_name: str = "BuildStageName"
    service_version: str = "BuildServiceVersion"
    input_fingerprint: str = "InputFingerprint"
    result_fingerprint: str = "ResultFingerprint"
    source_refs: str = "ConsumedSourceRefs"
    result_refs: str = "ConsumedResultRefs"
    accepted: str = "BuildAccepted"
    duration_ms: str = "BuildDurationMs"
    changed_stages: str = "ChangedStages"
    stale_reasons: str = "StaleReasons"


INCREMENTAL_PROPERTIES = IncrementalPropertyNames()


def ensure_model_payload_properties(obj, *, add_property) -> None:
    add_property(obj, "App::PropertyInteger", PAYLOAD_PROPERTIES.schema_version, "Persistence", "payload schema version")
    add_property(obj, "App::PropertyString", PAYLOAD_PROPERTIES.json, "Persistence", "canonical typed model payload")
    add_property(obj, "App::PropertyString", PAYLOAD_PROPERTIES.checksum, "Persistence", "payload checksum")
    add_property(obj, "App::PropertyString", PAYLOAD_PROPERTIES.fingerprint, "Persistence", "source/result fingerprint")
    add_property(obj, "App::PropertyStringList", PAYLOAD_PROPERTIES.diagnostics, "Persistence", "typed restore diagnostics")
    if int(getattr(obj, PAYLOAD_PROPERTIES.schema_version, 0) or 0) <= 0:
        setattr(obj, PAYLOAD_PROPERTIES.schema_version, CURRENT_PAYLOAD_SCHEMA_VERSION)


def ensure_incremental_result_properties(obj, *, add_property) -> None:
    names = INCREMENTAL_PROPERTIES
    add_property(obj, "App::PropertyString", names.stage_name, "Incremental Build", "engineering result stage")
    add_property(obj, "App::PropertyString", names.service_version, "Incremental Build", "builder service version")
    add_property(obj, "App::PropertyString", names.input_fingerprint, "Incremental Build", "engineering input fingerprint")
    add_property(obj, "App::PropertyString", names.result_fingerprint, "Incremental Build", "accepted result fingerprint")
    add_property(obj, "App::PropertyStringList", names.source_refs, "Incremental Build", "consumed source refs")
    add_property(obj, "App::PropertyStringList", names.result_refs, "Incremental Build", "consumed result refs")
    add_property(obj, "App::PropertyBool", names.accepted, "Incremental Build", "accepted result flag")
    add_property(obj, "App::PropertyFloat", names.duration_ms, "Incremental Build", "last build duration in milliseconds")
    add_property(obj, "App::PropertyStringList", names.changed_stages, "Incremental Build", "changed stages")
    add_property(obj, "App::PropertyStringList", names.stale_reasons, "Incremental Build", "explicit stale reasons")


def write_incremental_record(obj, record: IncrementalStageRecord) -> None:
    names = INCREMENTAL_PROPERTIES
    setattr(obj, names.stage_name, str(record.stage_name))
    setattr(obj, names.service_version, str(record.service_version))
    setattr(obj, names.input_fingerprint, str(record.input_fingerprint))
    setattr(obj, names.result_fingerprint, str(record.result_fingerprint))
    setattr(obj, names.source_refs, list(record.consumed_source_refs))
    setattr(obj, names.result_refs, list(record.consumed_result_refs))
    setattr(obj, names.accepted, bool(record.accepted))
    setattr(obj, names.duration_ms, float(record.duration_ms))
    setattr(obj, names.changed_stages, list(record.changed_stages))
    setattr(obj, names.stale_reasons, list(record.stale_reasons))


def read_incremental_record(obj) -> IncrementalStageRecord | None:
    names = INCREMENTAL_PROPERTIES
    stage_name = str(getattr(obj, names.stage_name, "") or "")
    if not stage_name:
        return None
    return IncrementalStageRecord(
        stage_name=stage_name,
        service_version=str(getattr(obj, names.service_version, "") or ""),
        input_fingerprint=str(getattr(obj, names.input_fingerprint, "") or ""),
        result_fingerprint=str(getattr(obj, names.result_fingerprint, "") or ""),
        consumed_source_refs=tuple(str(value) for value in list(getattr(obj, names.source_refs, []) or [])),
        consumed_result_refs=tuple(str(value) for value in list(getattr(obj, names.result_refs, []) or [])),
        accepted=bool(getattr(obj, names.accepted, False)),
        duration_ms=float(getattr(obj, names.duration_ms, 0.0) or 0.0),
        changed_stages=tuple(str(value) for value in list(getattr(obj, names.changed_stages, []) or [])),
        stale_reasons=tuple(str(value) for value in list(getattr(obj, names.stale_reasons, []) or [])),
    )


def make_incremental_record(
    *,
    stage_name: str,
    result_fingerprint: str,
    consumed_source_refs=(),
    consumed_result_refs=(),
    service_version: str = "persistence-adapter:1",
) -> IncrementalStageRecord:
    source_refs = tuple(str(value) for value in consumed_source_refs or () if str(value))
    result_refs = tuple(str(value) for value in consumed_result_refs or () if str(value))
    return IncrementalStageRecord(
        stage_name=stage_name,
        service_version=service_version,
        input_fingerprint=fingerprint_for({"source_refs": source_refs, "result_refs": result_refs}),
        result_fingerprint=result_fingerprint,
        consumed_source_refs=source_refs,
        consumed_result_refs=result_refs,
        accepted=True,
        changed_stages=(stage_name,),
        stale_reasons=("persisted_result_updated",),
    )


def write_model_payload(
    obj,
    model,
    *,
    model_type: str,
    row_fields: tuple[str, ...] = (),
    required_refs: tuple[str, ...] = (),
) -> str:
    payload = serialize_model_payload(
        model,
        model_type=model_type,
        row_fields=row_fields,
        required_refs=required_refs,
    )
    setattr(obj, PAYLOAD_PROPERTIES.schema_version, payload.payload_schema_version)
    setattr(obj, PAYLOAD_PROPERTIES.json, payload.to_json())
    setattr(obj, PAYLOAD_PROPERTIES.checksum, payload.checksum)
    setattr(obj, PAYLOAD_PROPERTIES.fingerprint, payload.source_fingerprint)
    setattr(obj, PAYLOAD_PROPERTIES.diagnostics, [])
    return payload.source_fingerprint


def read_model_payload(
    obj,
    *,
    expected_model_type: str,
    model_class,
) -> PayloadRestoreResult | None:
    payload_json = str(getattr(obj, PAYLOAD_PROPERTIES.json, "") or "")
    if not payload_json:
        return None
    owner_ref = str(getattr(obj, "Name", "") or "")
    persisted_checksum = str(getattr(obj, PAYLOAD_PROPERTIES.checksum, "") or "")
    try:
        embedded_checksum = str(json.loads(payload_json).get("checksum", "") or "")
    except Exception:
        embedded_checksum = ""
    if persisted_checksum and persisted_checksum != embedded_checksum:
        result = PayloadRestoreResult(
            model=None,
            diagnostics=(
                PersistenceDiagnostic(
                    "error",
                    "payload_property_checksum_mismatch",
                    "The separate payload checksum does not match the embedded envelope checksum.",
                    owner_ref,
                    "Restore from a valid backup or rebuild from owning source data.",
                ),
            ),
        )
        try:
            setattr(obj, PAYLOAD_PROPERTIES.diagnostics, [row.as_text() for row in result.diagnostics])
        except Exception:
            pass
        return result
    result = restore_model_payload(
        payload_json,
        expected_model_type=expected_model_type,
        model_class=model_class,
        owner_ref=owner_ref,
    )
    persisted_fingerprint = str(getattr(obj, PAYLOAD_PROPERTIES.fingerprint, "") or "")
    if result.accepted and persisted_fingerprint and persisted_fingerprint != result.source_fingerprint:
        result = PayloadRestoreResult(
            model=None,
            diagnostics=(
                PersistenceDiagnostic(
                    "error",
                    "payload_property_fingerprint_mismatch",
                    "The persisted model fingerprint does not match restored typed data.",
                    owner_ref,
                    "Restore from a valid backup or rebuild from owning source data.",
                ),
            ),
            migrated=result.migrated,
            source_fingerprint=result.source_fingerprint,
            payload_schema_version=result.payload_schema_version,
        )
    try:
        setattr(obj, PAYLOAD_PROPERTIES.diagnostics, [row.as_text() for row in result.diagnostics])
    except Exception:
        pass
    return result


__all__ = [
    "INCREMENTAL_PROPERTIES",
    "PAYLOAD_PROPERTIES",
    "IncrementalPropertyNames",
    "PayloadPropertyNames",
    "ensure_incremental_result_properties",
    "ensure_model_payload_properties",
    "make_incremental_record",
    "read_incremental_record",
    "read_model_payload",
    "write_incremental_record",
    "write_model_payload",
]
