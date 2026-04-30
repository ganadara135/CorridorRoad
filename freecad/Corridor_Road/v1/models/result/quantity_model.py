"""Quantity result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class QuantityFragment:
    """Minimal quantity fragment row."""

    fragment_id: str
    quantity_kind: str
    measurement_kind: str
    value: float
    unit: str
    station_start: float | None = None
    station_end: float | None = None
    component_ref: str = ""
    assembly_ref: str = ""
    region_ref: str = ""
    structure_ref: str = ""


@dataclass(frozen=True)
class QuantityAggregate:
    """Minimal quantity aggregate row."""

    aggregate_id: str
    aggregate_kind: str
    grouping_ref: str
    value: float
    unit: str
    fragment_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QuantityGroupingRow:
    """Minimal quantity grouping row."""

    grouping_id: str
    grouping_kind: str
    grouping_key: str
    station_start: float | None = None
    station_end: float | None = None


@dataclass(frozen=True)
class QuantityComparisonRow:
    """Minimal quantity comparison row."""

    comparison_id: str
    comparison_kind: str
    base_ref: str
    compare_ref: str
    delta_value: float
    unit: str


@dataclass
class QuantityModel(ResultModelBase):
    """Grouped quantity result family."""

    quantity_model_id: str = ""
    corridor_id: str = ""
    fragment_rows: list[QuantityFragment] = field(default_factory=list)
    aggregate_rows: list[QuantityAggregate] = field(default_factory=list)
    grouping_rows: list[QuantityGroupingRow] = field(default_factory=list)
    comparison_rows: list[QuantityComparisonRow] = field(default_factory=list)
