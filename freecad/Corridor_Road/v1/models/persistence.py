"""Typed persistence contracts shared by v1 source, result, and output models."""

from __future__ import annotations

import hashlib
import json
import types
from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import Any, Callable, Mapping, TypeVar, Union, get_args, get_origin, get_type_hints


CURRENT_PAYLOAD_SCHEMA_VERSION = 2
ModelT = TypeVar("ModelT")
Migration = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class PersistenceDiagnostic:
    """Typed persistence failure or compatibility notice."""

    severity: str
    code: str
    message: str
    owner_ref: str = ""
    user_action: str = ""

    def as_text(self) -> str:
        values = [self.severity, self.code, self.message]
        if self.owner_ref:
            values.append(f"owner={self.owner_ref}")
        if self.user_action:
            values.append(f"action={self.user_action}")
        return "|".join(values)


@dataclass(frozen=True)
class VersionedPayload:
    """Canonical persisted model envelope."""

    payload_schema_version: int
    model_type: str
    model_schema_version: int
    data: dict[str, object]
    row_counts: dict[str, int]
    required_refs: tuple[str, ...]
    checksum: str
    source_fingerprint: str

    def to_json(self) -> str:
        return canonical_json(asdict(self))


@dataclass(frozen=True)
class PayloadRestoreResult:
    """Restore result that never hides malformed persisted state."""

    model: object | None
    diagnostics: tuple[PersistenceDiagnostic, ...] = ()
    migrated: bool = False
    source_fingerprint: str = ""
    payload_schema_version: int = 0

    @property
    def accepted(self) -> bool:
        return self.model is not None and not any(row.severity == "error" for row in self.diagnostics)


class PayloadMigrationRegistry:
    """Explicit payload-schema migration chain."""

    def __init__(self) -> None:
        self._steps: dict[int, Migration] = {}

    def register(self, from_version: int, migration: Migration) -> None:
        version = int(from_version)
        if version <= 0:
            raise ValueError("Migration source version must be positive.")
        self._steps[version] = migration

    def migrate(self, envelope: dict[str, object], *, target_version: int) -> tuple[dict[str, object], bool]:
        migrated = False
        current = int(envelope.get("payload_schema_version", 0) or 0)
        target = int(target_version)
        if current > target:
            raise ValueError(f"Payload schema {current} is newer than supported schema {target}.")
        result = dict(envelope)
        while current < target:
            migration = self._steps.get(current)
            if migration is None:
                raise ValueError(f"No payload migration registered for schema {current}.")
            result = dict(migration(dict(result)))
            next_version = int(result.get("payload_schema_version", 0) or 0)
            if next_version != current + 1:
                raise ValueError(f"Migration {current} must produce schema {current + 1}.")
            current = next_version
            migrated = True
        return result, migrated


def default_payload_migrations() -> PayloadMigrationRegistry:
    registry = PayloadMigrationRegistry()
    registry.register(1, _migrate_payload_v1_to_v2)
    return registry


def serialize_model_payload(
    model: object,
    *,
    model_type: str,
    row_fields: tuple[str, ...] = (),
    required_refs: tuple[str, ...] = (),
    payload_schema_version: int = CURRENT_PAYLOAD_SCHEMA_VERSION,
) -> VersionedPayload:
    """Serialize one dataclass model into a checksummed canonical envelope."""

    if not is_dataclass(model):
        raise TypeError("Persisted v1 models must be dataclass instances.")
    data = asdict(model)
    row_counts = {
        name: len(list(data.get(name, []) or []))
        for name in row_fields
        if name in data
    }
    refs = tuple(_unique_text(required_refs))
    body = {
        "payload_schema_version": int(payload_schema_version),
        "model_type": str(model_type or "").strip(),
        "model_schema_version": int(getattr(model, "schema_version", 1) or 1),
        "data": data,
        "row_counts": row_counts,
        "required_refs": list(refs),
    }
    checksum = checksum_for(body)
    return VersionedPayload(
        payload_schema_version=int(payload_schema_version),
        model_type=str(model_type or "").strip(),
        model_schema_version=int(getattr(model, "schema_version", 1) or 1),
        data=data,
        row_counts=row_counts,
        required_refs=refs,
        checksum=checksum,
        source_fingerprint=fingerprint_for(data),
    )


def restore_model_payload(
    payload_json: str,
    *,
    expected_model_type: str,
    model_class: type[ModelT],
    owner_ref: str = "",
    current_payload_schema_version: int = CURRENT_PAYLOAD_SCHEMA_VERSION,
    migrations: PayloadMigrationRegistry | None = None,
) -> PayloadRestoreResult:
    """Validate, migrate, and reconstruct a model without silent repair."""

    diagnostics: list[PersistenceDiagnostic] = []
    try:
        raw = json.loads(str(payload_json or ""))
    except Exception as exc:
        return _restore_error("payload_json_invalid", f"Payload JSON is invalid: {exc}", owner_ref)
    if not isinstance(raw, dict):
        return _restore_error("payload_root_invalid", "Payload root must be an object.", owner_ref)

    original_body = _checksum_body(raw)
    expected_checksum = str(raw.get("checksum", "") or "")
    if not expected_checksum or checksum_for(original_body) != expected_checksum:
        return _restore_error(
            "payload_checksum_mismatch",
            "Payload checksum is missing or does not match persisted content.",
            owner_ref,
        )

    try:
        envelope, migrated = (migrations or default_payload_migrations()).migrate(
            raw,
            target_version=current_payload_schema_version,
        )
    except Exception as exc:
        return _restore_error("payload_migration_failed", str(exc), owner_ref)

    model_type = str(envelope.get("model_type", "") or "")
    if model_type != str(expected_model_type or ""):
        return _restore_error(
            "payload_model_type_mismatch",
            f"Expected {expected_model_type}, found {model_type or '<missing>'}.",
            owner_ref,
        )
    data = envelope.get("data")
    if not isinstance(data, dict):
        return _restore_error("payload_data_invalid", "Payload data must be an object.", owner_ref)

    diagnostics.extend(_validate_row_counts(data, envelope.get("row_counts", {}), owner_ref=owner_ref))
    diagnostics.extend(_validate_required_refs(data, envelope.get("required_refs", ()), owner_ref=owner_ref))
    if any(row.severity == "error" for row in diagnostics):
        return PayloadRestoreResult(
            model=None,
            diagnostics=tuple(diagnostics),
            migrated=migrated,
            payload_schema_version=int(envelope.get("payload_schema_version", 0) or 0),
        )
    try:
        model = dataclass_from_dict(model_class, data)
    except Exception as exc:
        return _restore_error("payload_model_restore_failed", str(exc), owner_ref, migrated=migrated)
    return PayloadRestoreResult(
        model=model,
        diagnostics=tuple(diagnostics),
        migrated=migrated,
        source_fingerprint=fingerprint_for(data),
        payload_schema_version=int(envelope.get("payload_schema_version", 0) or 0),
    )


def dataclass_from_dict(model_class: type[ModelT], data: Mapping[str, object]) -> ModelT:
    if not is_dataclass(model_class):
        raise TypeError(f"{model_class!r} is not a dataclass type.")
    hints = get_type_hints(model_class)
    values: dict[str, object] = {}
    for field in fields(model_class):
        if field.name not in data:
            continue
        values[field.name] = _restore_value(hints.get(field.name, field.type), data[field.name])
    return model_class(**values)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def checksum_for(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def fingerprint_for(value: object) -> str:
    return f"sha256:{checksum_for(value)}"


def _restore_value(annotation, value):
    if value is None:
        return None
    if annotation in (Any, object) or annotation is None:
        return value
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        last_error = None
        for option in args:
            if option is type(None):
                continue
            try:
                return _restore_value(option, value)
            except (TypeError, ValueError) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        return value
    if origin is list:
        item_type = args[0] if args else object
        return [_restore_value(item_type, item) for item in list(value or [])]
    if origin is tuple:
        item_types = args
        if len(item_types) == 2 and item_types[1] is Ellipsis:
            return tuple(_restore_value(item_types[0], item) for item in list(value or []))
        return tuple(
            _restore_value(item_types[index] if index < len(item_types) else object, item)
            for index, item in enumerate(list(value or []))
        )
    if origin is dict:
        key_type, value_type = args if len(args) == 2 else (object, object)
        return {
            _restore_value(key_type, key): _restore_value(value_type, item)
            for key, item in dict(value or {}).items()
        }
    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, Mapping):
            raise TypeError(f"Expected object for {annotation.__name__}.")
        return dataclass_from_dict(annotation, value)
    if annotation in (str, int, float, bool):
        return annotation(value)
    return value


def _checksum_body(envelope: Mapping[str, object]) -> dict[str, object]:
    return {
        "payload_schema_version": int(envelope.get("payload_schema_version", 0) or 0),
        "model_type": str(envelope.get("model_type", "") or ""),
        "model_schema_version": int(envelope.get("model_schema_version", 0) or 0),
        "data": envelope.get("data", {}),
        "row_counts": envelope.get("row_counts", {}),
        "required_refs": envelope.get("required_refs", []),
    }


def _migrate_payload_v1_to_v2(envelope: dict[str, object]) -> dict[str, object]:
    result = dict(envelope)
    result["payload_schema_version"] = 2
    result.setdefault("row_counts", {})
    result.setdefault("required_refs", [])
    result["checksum"] = checksum_for(_checksum_body(result))
    return result


def _validate_row_counts(data, persisted_counts, *, owner_ref: str) -> list[PersistenceDiagnostic]:
    if not isinstance(persisted_counts, dict):
        return [PersistenceDiagnostic("error", "row_counts_invalid", "Row counts must be an object.", owner_ref)]
    diagnostics: list[PersistenceDiagnostic] = []
    for name, persisted in persisted_counts.items():
        rows = data.get(str(name))
        if not isinstance(rows, (list, tuple)):
            diagnostics.append(PersistenceDiagnostic("error", "row_field_missing", f"Row field {name} is missing.", owner_ref))
            continue
        if len(rows) != int(persisted):
            diagnostics.append(
                PersistenceDiagnostic(
                    "error",
                    "row_count_mismatch",
                    f"{name}: expected {int(persisted)}, found {len(rows)}.",
                    owner_ref,
                    "Restore from a valid backup or rebuild from owning source data.",
                )
            )
    return diagnostics


def _validate_required_refs(data, required_refs, *, owner_ref: str) -> list[PersistenceDiagnostic]:
    diagnostics: list[PersistenceDiagnostic] = []
    for name in _unique_text(required_refs or ()):
        value = data.get(name)
        if value is None or value == "" or value == []:
            diagnostics.append(
                PersistenceDiagnostic(
                    "error",
                    "required_ref_missing",
                    f"Required persisted ref {name} is missing.",
                    owner_ref,
                    "Restore the owning source reference before rebuilding results.",
                )
            )
    return diagnostics


def _restore_error(code: str, message: str, owner_ref: str, *, migrated: bool = False) -> PayloadRestoreResult:
    return PayloadRestoreResult(
        model=None,
        diagnostics=(
            PersistenceDiagnostic(
                "error",
                code,
                message,
                owner_ref,
                "Restore from a valid backup or rebuild from accepted source contracts.",
            ),
        ),
        migrated=migrated,
    )


def _unique_text(values) -> list[str]:
    result: list[str] = []
    for value in list(values or []):
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


__all__ = [
    "CURRENT_PAYLOAD_SCHEMA_VERSION",
    "PayloadMigrationRegistry",
    "PayloadRestoreResult",
    "PersistenceDiagnostic",
    "VersionedPayload",
    "canonical_json",
    "checksum_for",
    "dataclass_from_dict",
    "default_payload_migrations",
    "fingerprint_for",
    "restore_model_payload",
    "serialize_model_payload",
]
