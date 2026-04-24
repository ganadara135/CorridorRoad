"""Mass-haul result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class MassCurveRow:
    """Minimal cumulative mass curve row."""

    curve_row_id: str
    kind: str
    station_values: list[float] = field(default_factory=list)
    cumulative_mass_values: list[float] = field(default_factory=list)
    unit: str = "m3"


@dataclass(frozen=True)
class BalancePointRow:
    """Minimal balance point row."""

    balance_point_row_id: str
    station: float
    kind: str = "balance_point"
    value: float = 0.0
    unit: str = "m3"


@dataclass(frozen=True)
class HaulZoneRow:
    """Minimal haul zone row."""

    haul_zone_row_id: str
    kind: str
    station_start: float
    station_end: float
    direction: str = ""
    value: float = 0.0
    unit: str = "m3"


@dataclass
class MassHaulModel(ResultModelBase):
    """Mass-haul analytical result family."""

    mass_haul_id: str = ""
    corridor_id: str = ""
    curve_rows: list[MassCurveRow] = field(default_factory=list)
    balance_point_rows: list[BalancePointRow] = field(default_factory=list)
    haul_zone_rows: list[HaulZoneRow] = field(default_factory=list)
