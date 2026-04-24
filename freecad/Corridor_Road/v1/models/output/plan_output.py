"""Plan output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class PlanGeometryRow:
    """Minimal plan geometry row."""

    row_id: str
    kind: str
    x_values: list[float] = field(default_factory=list)
    y_values: list[float] = field(default_factory=list)
    closed: bool = False
    style_role: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class PlanStationRow:
    """Minimal station marker row for plan output."""

    station_row_id: str
    station: float
    station_label: str
    x: float
    y: float
    kind: str = "regular_station"


@dataclass(frozen=True)
class PlanSummaryRow:
    """Minimal summary row for plan output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class PlanOutput(OutputModelBase):
    """Normalized plan output payload."""

    plan_output_id: str = ""
    alignment_id: str = ""
    geometry_rows: list[PlanGeometryRow] = field(default_factory=list)
    station_rows: list[PlanStationRow] = field(default_factory=list)
    summary_rows: list[PlanSummaryRow] = field(default_factory=list)
