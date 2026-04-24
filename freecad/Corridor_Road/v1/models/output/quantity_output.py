"""Quantity output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class QuantityFragmentRow:
    """Minimal quantity fragment row for quantity output."""

    fragment_row_id: str
    fragment_id: str
    quantity_kind: str
    measurement_kind: str
    value: float
    unit: str
    station_start: float | None = None
    station_end: float | None = None
    component_ref: str = ""
    region_ref: str = ""


@dataclass(frozen=True)
class QuantityAggregateRow:
    """Minimal aggregate row for quantity output."""

    aggregate_row_id: str
    aggregate_id: str
    aggregate_kind: str
    grouping_ref: str
    value: float
    unit: str
    fragment_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QuantityComparisonOutputRow:
    """Minimal comparison row for quantity output."""

    comparison_row_id: str
    comparison_id: str
    comparison_kind: str
    base_ref: str
    compare_ref: str
    delta_value: float
    unit: str


@dataclass(frozen=True)
class QuantitySummaryRow:
    """Minimal summary row for quantity output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class QuantityOutput(OutputModelBase):
    """Normalized quantity output payload."""

    quantity_output_id: str = ""
    corridor_id: str = ""
    fragment_rows: list[QuantityFragmentRow] = field(default_factory=list)
    aggregate_rows: list[QuantityAggregateRow] = field(default_factory=list)
    comparison_rows: list[QuantityComparisonOutputRow] = field(default_factory=list)
    summary_rows: list[QuantitySummaryRow] = field(default_factory=list)
