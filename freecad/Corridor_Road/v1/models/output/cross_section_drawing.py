"""Drawing-style cross-section output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class CrossSectionDrawingGeometryRow:
    """Polyline or filled span in station-local offset/elevation space."""

    row_id: str
    kind: str
    offset_values: list[float] = field(default_factory=list)
    elevation_values: list[float] = field(default_factory=list)
    closed: bool = False
    style_role: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class CrossSectionDrawingLabelRow:
    """Text annotation placed directly in the section drawing."""

    row_id: str
    text: str
    offset: float
    elevation: float
    role: str = ""
    value: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class CrossSectionDrawingDimensionRow:
    """Dimension guide in the lower drawing band."""

    row_id: str
    kind: str
    start_offset: float
    end_offset: float
    baseline_elevation: float
    label: str
    value: float
    unit: str = "m"
    role: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class CrossSectionDrawingSummaryRow:
    """Compact drawing payload summary row for diagnostics and UI status."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class CrossSectionDrawingPayload(OutputModelBase):
    """Normalized drawing payload consumed by the v1 Cross Section Viewer."""

    drawing_id: str = ""
    station: float = 0.0
    station_label: str = ""
    geometry_rows: list[CrossSectionDrawingGeometryRow] = field(default_factory=list)
    label_rows: list[CrossSectionDrawingLabelRow] = field(default_factory=list)
    dimension_rows: list[CrossSectionDrawingDimensionRow] = field(default_factory=list)
    summary_rows: list[CrossSectionDrawingSummaryRow] = field(default_factory=list)
