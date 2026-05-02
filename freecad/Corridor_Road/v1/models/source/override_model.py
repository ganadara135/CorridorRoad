"""Override source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class OverrideScope:
    """Minimal override scope row."""

    scope_id: str
    scope_kind: str
    station_start: float | None = None
    station_end: float | None = None
    region_ref: str = ""
    event_ref: str = ""
    component_side: str = ""


@dataclass(frozen=True)
class OverrideTarget:
    """Minimal override target row."""

    target_id: str
    target_kind: str
    target_ref: str
    component_ref: str = ""
    side: str = ""


@dataclass(frozen=True)
class OverrideRow:
    """Minimal override row."""

    override_id: str
    override_kind: str
    target: OverrideTarget
    scope: OverrideScope
    parameter: str
    value: float | str
    unit: str = ""
    priority: int = 0
    activation_state: str = "active"


@dataclass
class OverrideModel(SourceModelBase):
    """Durable override source contract."""

    override_model_id: str = ""
    alignment_id: str = ""
    override_rows: list[OverrideRow] = field(default_factory=list)
