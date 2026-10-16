"""Stored Drainage result.

The Drainage evaluation writes its `DrainageResult` as a typed payload on one object per project,
`V1DrainageResult`, in the Drainage tree folder. Its check rows are also listed as text so the
property view shows them; the payload stays the contract.
"""

from __future__ import annotations

from ..models.result.drainage_result import DrainageResult
from .persistence_payload_adapter import (
    PAYLOAD_PROPERTIES,
    ensure_model_payload_properties,
    read_model_payload,
    write_model_payload,
)


DRAINAGE_RESULT_OBJECT_NAME = "V1DrainageResult"
DRAINAGE_RESULT_MODEL_TYPE = "DrainageResult"
DRAINAGE_RESULT_RECORD_KIND = "v1_drainage_result"


class V1DrainageResultObject:
    Type = "DrainageResult"

    def __init__(self, obj):
        obj.Proxy = self

    def execute(self, obj):
        return


def find_v1_drainage_result_object(document):
    return document.getObject(DRAINAGE_RESULT_OBJECT_NAME) if document is not None else None


def create_or_update_v1_drainage_result_object(document, result: DrainageResult):
    """Store the result on the project's Drainage result object, creating it when missing."""

    obj = find_v1_drainage_result_object(document)
    if obj is None:
        obj = document.addObject("App::FeaturePython", DRAINAGE_RESULT_OBJECT_NAME)
        V1DrainageResultObject(obj)
        obj.Label = "Drainage Result"
    for type_name, name, doc in (
        ("App::PropertyString", "V1ObjectType", "v1 object type"),
        ("App::PropertyString", "CRRecordKind", "v1 tree routing record kind"),
        ("App::PropertyString", "Status", "ok, warning, error or empty"),
        ("App::PropertyInteger", "FlowlineCount", "ditch run flowlines evaluated"),
        ("App::PropertyStringList", "CheckRows", "severity | ditch run | stations | message"),
    ):
        _add_property(obj, type_name, name, "Drainage", doc)
    ensure_model_payload_properties(obj, add_property=_add_property)
    obj.V1ObjectType = "V1DrainageResult"
    obj.CRRecordKind = DRAINAGE_RESULT_RECORD_KIND
    obj.Status = result.status
    obj.FlowlineCount = len(result.flowline_rows)
    obj.CheckRows = [
        f"{row.severity} | {row.ditch_run_ref} | STA {row.station_start:.3f}-{row.station_end:.3f} | {row.message}"
        for row in result.check_rows
    ]
    write_model_payload(
        obj,
        result,
        model_type=DRAINAGE_RESULT_MODEL_TYPE,
        row_fields=("flowline_rows", "check_rows"),
        required_refs=("project_id", "drainage_result_id"),
    )
    return obj


def to_drainage_result(obj) -> DrainageResult | None:
    if obj is None:
        return None
    restored = read_model_payload(obj, expected_model_type=DRAINAGE_RESULT_MODEL_TYPE, model_class=DrainageResult)
    return restored.model if restored is not None and restored.accepted else None


def drainage_result_fingerprint(obj) -> str:
    return str(getattr(obj, PAYLOAD_PROPERTIES.fingerprint, "") or "") if obj is not None else ""


def _add_property(obj, type_name: str, name: str, group: str, doc: str = "") -> None:
    if not hasattr(obj, name):
        obj.addProperty(type_name, name, group, doc)


__all__ = [
    "DRAINAGE_RESULT_OBJECT_NAME",
    "create_or_update_v1_drainage_result_object",
    "drainage_result_fingerprint",
    "find_v1_drainage_result_object",
    "to_drainage_result",
]
