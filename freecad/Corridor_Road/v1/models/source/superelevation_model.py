"""Superelevation source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class CrossfallControlRow:
    """Minimal crossfall control row."""

    control_row_id: str
    station: float
    side: str
    crossfall_value: float
    crossfall_unit: str = "percent"
    kind: str = "reference_crossfall"


@dataclass(frozen=True)
class RunoffTransitionRow:
    """Minimal runoff transition row."""

    transition_id: str
    station_start: float
    station_end: float
    kind: str
    transition_policy: str = "linear"


@dataclass(frozen=True)
class SuperelevationConstraint:
    """Minimal superelevation constraint row."""

    constraint_id: str
    kind: str
    value: float | str
    unit: str = ""
    hard_or_soft: str = "soft"


@dataclass
class SuperelevationModel(SourceModelBase):
    """Durable superelevation source contract."""

    superelevation_id: str = ""
    alignment_id: str = ""
    profile_id: str = ""
    superelevation_kind: str = "roadway_superelevation"
    control_rows: list[CrossfallControlRow] = field(default_factory=list)
    transition_rows: list[RunoffTransitionRow] = field(default_factory=list)
    constraint_rows: list[SuperelevationConstraint] = field(default_factory=list)
