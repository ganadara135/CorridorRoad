"""Alignment curve preview result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class AlignmentCurvePreviewPointRow:
    """One sampled point in the Alignment curve preview."""

    point_id: str
    station: float
    x: float
    y: float
    tangent_direction_deg: float = 0.0
    role: str = "evaluated_path"
    element_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class AlignmentCurvePreviewAnnotationRow:
    """One label or marker in the Alignment curve preview."""

    annotation_id: str
    kind: str
    label: str
    station: float = 0.0
    x: float = 0.0
    y: float = 0.0
    value: str = ""
    element_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class AlignmentCurvePreviewElementRow:
    """Resolved alignment element information for the preview info panel."""

    element_id: str
    kind: str
    station_start: float
    station_end: float
    length: float = 0.0
    point_count: int = 0
    radius: float = 0.0
    central_angle_deg: float = 0.0
    curve_direction: str = ""
    status: str = "ok"
    notes: str = ""


@dataclass
class AlignmentCurvePreviewResult(ResultModelBase):
    """Read-only preview data for Alignment panel curve visualization."""

    alignment_id: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    sample_interval: float = 5.0
    status: str = "empty"
    point_rows: list[AlignmentCurvePreviewPointRow] = field(default_factory=list)
    annotation_rows: list[AlignmentCurvePreviewAnnotationRow] = field(default_factory=list)
    element_rows: list[AlignmentCurvePreviewElementRow] = field(default_factory=list)
