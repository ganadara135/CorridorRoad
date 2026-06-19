"""Profile curve preview result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class ProfileCurvePreviewPointRow:
    """One sampled point in the profile curve preview."""

    point_id: str
    station: float
    elevation: float
    grade: float = 0.0
    role: str = "evaluated_curve"
    curve_ref: str = ""
    source_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ProfileCurvePreviewAnnotationRow:
    """One label or marker in the profile curve preview."""

    annotation_id: str
    kind: str
    label: str
    station: float = 0.0
    elevation: float = 0.0
    value: str = ""
    curve_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ProfileCurvePreviewCurveRow:
    """Resolved vertical-curve information for the preview info panel."""

    curve_id: str
    kind: str
    station_start: float
    station_end: float
    length: float = 0.0
    bvc_station: float = 0.0
    bvc_elevation: float = 0.0
    pvi_station: float = 0.0
    pvi_elevation: float = 0.0
    evc_station: float = 0.0
    evc_elevation: float = 0.0
    grade_in: float = 0.0
    grade_out: float = 0.0
    algebraic_grade_difference: float = 0.0
    k_value: float = 0.0
    high_low_kind: str = ""
    high_low_station: float = 0.0
    high_low_elevation: float = 0.0
    max_chord_deviation: float = 0.0
    status: str = "ok"
    notes: str = ""


@dataclass
class ProfileCurvePreviewResult(ResultModelBase):
    """Read-only preview data for Profile panel curve visualization."""

    profile_id: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    sample_interval: float = 5.0
    status: str = "empty"
    point_rows: list[ProfileCurvePreviewPointRow] = field(default_factory=list)
    annotation_rows: list[ProfileCurvePreviewAnnotationRow] = field(default_factory=list)
    curve_rows: list[ProfileCurvePreviewCurveRow] = field(default_factory=list)
