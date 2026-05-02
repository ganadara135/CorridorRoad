"""Earthwork output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class EarthworkBalanceRowOutput:
    """Minimal balance row for earthwork output."""

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
class MassCurveRowOutput:
    """Minimal mass-haul curve row for earthwork output."""

    curve_row_id: str
    kind: str
    station_values: list[float] = field(default_factory=list)
    cumulative_mass_values: list[float] = field(default_factory=list)
    unit: str = "m3"


@dataclass(frozen=True)
class EarthworkSummaryRow:
    """Minimal summary row for earthwork output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class EarthworkBalanceOutput(OutputModelBase):
    """Normalized earthwork balance output payload."""

    earthwork_output_id: str = ""
    corridor_id: str = ""
    balance_rows: list[EarthworkBalanceRowOutput] = field(default_factory=list)
    summary_rows: list[EarthworkSummaryRow] = field(default_factory=list)


@dataclass
class MassHaulOutput(OutputModelBase):
    """Normalized mass-haul output payload."""

    mass_haul_output_id: str = ""
    corridor_id: str = ""
    curve_rows: list[MassCurveRowOutput] = field(default_factory=list)
    summary_rows: list[EarthworkSummaryRow] = field(default_factory=list)
