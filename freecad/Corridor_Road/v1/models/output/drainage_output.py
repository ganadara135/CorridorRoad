"""Drainage review output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class DrainageElementOutputRow:
    """Minimal drainage output row."""

    row_id: str
    kind: str
    station_start: float
    station_end: float
    label: str = ""
    source_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class DrainageSummaryRow:
    """Minimal drainage summary row."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class DrainageOutput(OutputModelBase):
    """Normalized drainage review payload."""

    drainage_output_id: str = ""
    alignment_id: str = ""
    drainage_model_id: str = ""
    element_rows: list[DrainageElementOutputRow] = field(default_factory=list)
    summary_rows: list[DrainageSummaryRow] = field(default_factory=list)
