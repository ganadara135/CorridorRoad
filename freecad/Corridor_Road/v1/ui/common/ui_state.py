"""Shared UI state helpers for CorridorRoad v1 preview workflows."""

from __future__ import annotations

from copy import deepcopy

_STATE: dict[str, object] = {}


def set_ui_context(**payload) -> dict[str, object]:
    """Replace the shared v1 UI context with a shallow payload copy."""

    global _STATE
    _STATE = dict(payload or {})
    return get_ui_context()


def update_ui_context(**payload) -> dict[str, object]:
    """Merge values into the shared v1 UI context."""

    global _STATE
    next_state = dict(_STATE)
    next_state.update(payload or {})
    _STATE = next_state
    return get_ui_context()


def get_ui_context() -> dict[str, object]:
    """Return a defensive copy of the shared v1 UI context."""

    return deepcopy(dict(_STATE))


def clear_ui_context() -> None:
    """Clear the shared v1 UI context."""

    global _STATE
    _STATE = {}
