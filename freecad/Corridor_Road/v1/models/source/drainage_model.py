"""Drainage source model for CorridorRoad v1.

Drainage owns where road water is collected and where it goes: which Assembly ditches drain the
road (Ditch Runs), the inlets, outfalls and culverts along them (Points), what drains into what
(Links), and the Policy the evaluated flowlines are checked against. The ditch shape stays owned
by the Assembly. Flow direction, grades, low points and elevations are evaluated from the Applied
Sections, never authored here.

Units: stations and offsets in meters, grades in percent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


DITCH_RUN_SIDES = ("left", "right")
DRAINAGE_POINT_KINDS = ("inlet", "outfall", "culvert")
LOW_POINT_RULES = ("require_inlet", "allow_ponding")

DEFAULT_MIN_GRADE_PERCENT = 0.3
DEFAULT_MAX_INLET_SPACING_M = 60.0


@dataclass(frozen=True)
class DrainagePolicy:
    """The project's drainage check values."""

    min_grade_percent: float = DEFAULT_MIN_GRADE_PERCENT
    max_inlet_spacing_m: float = DEFAULT_MAX_INLET_SPACING_M
    low_point_rule: str = "require_inlet"


@dataclass(frozen=True)
class DitchRun:
    """One Assembly ditch on one side of one road, over a station span."""

    ditch_run_id: str
    side: str
    subassembly_ref: str
    station_start: float
    station_end: float
    alignment_ref: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class DrainagePoint:
    """An inlet, outfall or culvert at a station.

    A point on a Ditch Run takes the run's side and flowline; a culvert crosses the road.
    """

    point_id: str
    kind: str
    station: float
    side: str = ""
    offset_m: float = 0.0
    ditch_run_ref: str = ""
    alignment_ref: str = ""


@dataclass(frozen=True)
class DrainageLink:
    """Water from one point drains into another."""

    link_id: str
    from_ref: str
    to_ref: str


@dataclass
class DrainageModel(SourceModelBase):
    """Durable drainage source contract; one per project."""

    drainage_model_id: str = "drainage:main"
    policy: DrainagePolicy = field(default_factory=DrainagePolicy)
    ditch_run_rows: list[DitchRun] = field(default_factory=list)
    point_rows: list[DrainagePoint] = field(default_factory=list)
    link_rows: list[DrainageLink] = field(default_factory=list)


def ditch_run_covers(run: DitchRun, station: float, *, alignment_ref: str = "", tolerance: float = 1.0e-6) -> bool:
    """True when an enabled run covers `station` on `alignment_ref` (a run without one covers every road).

    The tolerance takes in stations stored rounded to 9 decimals, so a run ending at a road's last
    station still covers that station's section.
    """

    if not bool(getattr(run, "enabled", True)):
        return False
    run_alignment = str(getattr(run, "alignment_ref", "") or "")
    if run_alignment and alignment_ref and run_alignment != str(alignment_ref):
        return False
    start = min(float(run.station_start), float(run.station_end))
    end = max(float(run.station_start), float(run.station_end))
    return start - tolerance <= float(station) <= end + tolerance
