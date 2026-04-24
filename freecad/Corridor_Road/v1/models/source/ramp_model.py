"""Ramp source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class RampTieInRow:
    """Minimal tie-in row for one ramp connection."""

    tie_in_id: str
    tie_in_kind: str
    target_kind: str
    target_ref: str
    station_start: float
    station_end: float
    offset_rule: str = ""
    grade_match_rule: str = ""


@dataclass(frozen=True)
class RampZoneRow:
    """Minimal zone row for gore, taper, and merge/diverge context."""

    zone_id: str
    zone_kind: str
    station_start: float
    station_end: float
    region_ref: str = ""
    template_ref: str = ""
    drainage_ref: str = ""


@dataclass(frozen=True)
class RampRow:
    """Minimal ramp definition row."""

    ramp_id: str
    ramp_kind: str
    alignment_ref: str
    profile_ref: str = ""
    superelevation_ref: str = ""
    parent_alignment_ref: str = ""
    intersection_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    design_criteria_ref: str = ""
    tie_in_rows: list[RampTieInRow] = field(default_factory=list)
    zone_rows: list[RampZoneRow] = field(default_factory=list)


@dataclass
class RampModel(SourceModelBase):
    """Durable ramp and tie-in source contract."""

    ramp_model_id: str = ""
    ramp_rows: list[RampRow] = field(default_factory=list)
