"""Alignment source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


@dataclass(frozen=True)
class AlignmentElement:
    """Minimal geometric element in an alignment sequence."""

    element_id: str
    kind: str
    station_start: float
    station_end: float
    length: float = 0.0
    geometry_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class StationEquation:
    """Minimal station equation row."""

    equation_id: str
    station_back: float
    station_ahead: float
    equation_kind: str


@dataclass(frozen=True)
class AlignmentConstraint:
    """Minimal alignment constraint row."""

    constraint_id: str
    kind: str
    value: float | str
    unit: str = ""
    hard_or_soft: str = "soft"


@dataclass
class AlignmentModel(SourceModelBase):
    """Durable horizontal alignment source contract."""

    alignment_id: str = ""
    alignment_kind: str = "road_centerline"
    geometry_sequence: list[AlignmentElement] = field(default_factory=list)
    station_equations: list[StationEquation] = field(default_factory=list)
    constraint_rows: list[AlignmentConstraint] = field(default_factory=list)
