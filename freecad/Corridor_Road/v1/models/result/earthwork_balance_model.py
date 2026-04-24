"""Earthwork balance result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class EarthworkBalanceRow:
    """Minimal station-based earthwork balance row."""

    balance_row_id: str
    station_start: float | None
    station_end: float | None
    cut_value: float
    fill_value: float
    usable_cut_value: float = 0.0
    unusable_cut_value: float = 0.0
    balance_ratio: float = 0.0
    unit: str = "m3"


@dataclass(frozen=True)
class EarthworkMaterialRow:
    """Minimal material interpretation row."""

    material_row_id: str
    kind: str
    value: float
    unit: str
    station_start: float | None = None
    station_end: float | None = None
    material_class: str = ""


@dataclass(frozen=True)
class EarthworkZoneRow:
    """Minimal earthwork zone row."""

    zone_row_id: str
    kind: str
    station_start: float
    station_end: float
    value: float = 0.0
    unit: str = "m3"


@dataclass
class EarthworkBalanceModel(ResultModelBase):
    """Earthwork balance analytical result family."""

    earthwork_balance_id: str = ""
    corridor_id: str = ""
    balance_rows: list[EarthworkBalanceRow] = field(default_factory=list)
    material_rows: list[EarthworkMaterialRow] = field(default_factory=list)
    zone_rows: list[EarthworkZoneRow] = field(default_factory=list)
