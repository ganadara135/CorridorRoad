"""Recorded stage inputs on a result object.

When a result stage is built it records one content fingerprint per input it consumed and the
build options it used, so a later freshness check can tell which inputs changed and Rebuild
Downstream can run the stage again with the same options. This module imports no other object
adapter, so every result writer can use it.
"""

from __future__ import annotations

import json

from ..services.evaluation.incremental_rebuild_service import PRESENTATION_ONLY_FIELDS, IncrementalRebuildService


STAGE_INPUT_ROWS = "StageInputRows"
STAGE_BUILD_OPTIONS = "StageBuildOptions"
# A label names an object for the user; renaming one changes no result.
_IGNORED_FIELDS = PRESENTATION_ONLY_FIELDS | frozenset({"label"})


def input_fingerprint(value: object) -> str:
    """Content fingerprint of one input: a source model, a list of them, or plain rows."""

    return IncrementalRebuildService().engineering_fingerprint(value, ignored_fields=_IGNORED_FIELDS)


def scoped_input_key(kind: str, alignment_id: str) -> str:
    """Key of an input that exists once per road, such as `profile@alignment:main`."""

    return f"{kind}@{alignment_id}"


def record_stage_inputs(obj, inputs: dict[str, str], options: dict[str, object] | None = None) -> None:
    """Store the inputs a stage consumed and the options it was built with."""

    _ensure(obj, STAGE_INPUT_ROWS, "App::PropertyStringList", "consumed input fingerprints, key=fingerprint")
    _ensure(obj, STAGE_BUILD_OPTIONS, "App::PropertyString", "build options as JSON")
    setattr(obj, STAGE_INPUT_ROWS, [f"{key}={value}" for key, value in sorted(inputs.items())])
    setattr(obj, STAGE_BUILD_OPTIONS, json.dumps(dict(options or {}), sort_keys=True))


def read_stage_inputs(obj) -> dict[str, str] | None:
    """The recorded inputs, or None when the result was built before inputs were recorded."""

    if obj is None or not hasattr(obj, STAGE_INPUT_ROWS):
        return None
    output: dict[str, str] = {}
    for row in list(getattr(obj, STAGE_INPUT_ROWS, []) or []):
        key, _sep, value = str(row).partition("=")
        output[key] = value
    return output


def read_stage_options(obj) -> dict[str, object]:
    text = str(getattr(obj, STAGE_BUILD_OPTIONS, "") or "")
    try:
        value = json.loads(text) if text else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _ensure(obj, name: str, type_name: str, doc: str) -> None:
    if not hasattr(obj, name):
        obj.addProperty(type_name, name, "Incremental Build", doc)


__all__ = [
    "STAGE_BUILD_OPTIONS",
    "STAGE_INPUT_ROWS",
    "input_fingerprint",
    "read_stage_inputs",
    "read_stage_options",
    "record_stage_inputs",
    "scoped_input_key",
]
