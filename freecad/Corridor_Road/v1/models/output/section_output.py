"""Section output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class SectionGeometryRow:
    """Minimal geometry row for section output."""

    row_id: str
    kind: str
    x_values: list[float] = field(default_factory=list)
    y_values: list[float] = field(default_factory=list)
    z_values: list[float] = field(default_factory=list)
    closed: bool = False
    style_role: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class SectionComponentRow:
    """Minimal component row for section output."""

    component_row_id: str
    component_id: str
    kind: str
    template_ref: str = ""
    region_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class SectionQuantityRow:
    """Minimal quantity row attached to section output."""

    quantity_row_id: str
    quantity_kind: str
    value: float
    unit: str
    component_ref: str = ""


@dataclass(frozen=True)
class SectionSummaryRow:
    """Minimal summary row for section output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class SectionOutput(OutputModelBase):
    """Normalized section output payload."""

    section_output_id: str = ""
    alignment_id: str = ""
    station: float = 0.0
    geometry_rows: list[SectionGeometryRow] = field(default_factory=list)
    component_rows: list[SectionComponentRow] = field(default_factory=list)
    quantity_rows: list[SectionQuantityRow] = field(default_factory=list)
    summary_rows: list[SectionSummaryRow] = field(default_factory=list)
