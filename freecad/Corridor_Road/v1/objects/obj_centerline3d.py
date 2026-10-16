"""Stored 3D Centerline result.

The 3D Centerline command writes its `Centerline3DResult` as a typed payload on its object
(`V1Centerline3DPreview`). Applied Sections and Build Parametric read that stored result instead
of evaluating their own, so the station frames have one owner, and result freshness reports when
it no longer matches the Alignment, Profile and Stations.
"""

from __future__ import annotations

from ..models.result.centerline3d import Centerline3DResult
from .persistence_payload_adapter import (
    PAYLOAD_PROPERTIES,
    ensure_model_payload_properties,
    read_model_payload,
    write_model_payload,
)


CENTERLINE3D_OBJECT_NAME = "V1Centerline3DPreview"
CENTERLINE3D_MODEL_TYPE = "Centerline3DResult"


def find_v1_centerline3d_object(document):
    return document.getObject(CENTERLINE3D_OBJECT_NAME) if document is not None else None


def write_v1_centerline3d_result(obj, result: Centerline3DResult) -> str:
    """Store the result on its object and return its content fingerprint."""

    ensure_model_payload_properties(obj, add_property=_add_property)
    return write_model_payload(
        obj,
        result,
        model_type=CENTERLINE3D_MODEL_TYPE,
        row_fields=("point_rows",),
        required_refs=("project_id", "centerline3d_result_id"),
    )


def to_centerline3d_result(obj) -> Centerline3DResult | None:
    """The stored result, or None when the object holds none (generated before results were stored)."""

    if obj is None:
        return None
    restored = read_model_payload(obj, expected_model_type=CENTERLINE3D_MODEL_TYPE, model_class=Centerline3DResult)
    return restored.model if restored is not None else None


def centerline3d_result_fingerprint(obj) -> str:
    return str(getattr(obj, PAYLOAD_PROPERTIES.fingerprint, "") or "") if obj is not None else ""


def _add_property(obj, type_name: str, name: str, group: str, doc: str) -> None:
    if not hasattr(obj, name):
        obj.addProperty(type_name, name, group, doc)


__all__ = [
    "CENTERLINE3D_OBJECT_NAME",
    "centerline3d_result_fingerprint",
    "find_v1_centerline3d_object",
    "to_centerline3d_result",
    "write_v1_centerline3d_result",
]
