"""Shared UI helpers for CorridorRoad v1."""

from .legacy_handoff import run_legacy_command
from .station_context import (
    context_station_label,
    context_station_row,
    context_station_value,
    nearest_span_index,
    nearest_value_index,
)
from .ui_state import clear_ui_context, get_ui_context, set_ui_context, update_ui_context

__all__ = [
    "clear_ui_context",
    "context_station_label",
    "context_station_row",
    "context_station_value",
    "get_ui_context",
    "nearest_span_index",
    "nearest_value_index",
    "run_legacy_command",
    "set_ui_context",
    "update_ui_context",
]
