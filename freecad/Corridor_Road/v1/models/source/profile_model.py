"""Profile source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class ProfileControlPoint:
    """Minimal profile control row."""

    control_point_id: str
    station: float
    elevation: float
    kind: str = "pvi"
    grade_in: float | None = None
    grade_out: float | None = None


@dataclass(frozen=True)
class VerticalCurveRow:
    """Minimal vertical-curve row."""

    vertical_curve_id: str
    kind: str
    station_start: float
    station_end: float
    curve_length: float = 0.0
    curve_parameter: float = 0.0


@dataclass(frozen=True)
class ProfileConstraint:
    """Minimal profile constraint row."""

    constraint_id: str
    kind: str
    value: float | str
    unit: str = ""
    hard_or_soft: str = "soft"


@dataclass
class ProfileModel(SourceModelBase):
    """Durable vertical profile source contract."""

    profile_id: str = ""
    alignment_id: str = ""
    profile_kind: str = "finished_grade"
    control_rows: list[ProfileControlPoint] = field(default_factory=list)
    vertical_curve_rows: list[VerticalCurveRow] = field(default_factory=list)
    constraint_rows: list[ProfileConstraint] = field(default_factory=list)
