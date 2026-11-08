"""Drainage output contract for CorridorRoad v1.

The normalized Drainage handoff for review, reports and exchange: per Ditch Run its flowline and
the checks, the points with their places on the flowlines, the links with their grades and the
pipes they carry. Built
from the Drainage source and its evaluated result; it owns no engineering rule.

Units: stations, lengths and coordinates in meters, grades in percent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class DrainageFlowlineOutputRow:
    ditch_run_ref: str
    side: str
    subassembly_ref: str
    station_start: float
    station_end: float
    length_m: float
    min_grade_percent: float
    max_grade_percent: float
    # (station, elevation) along the flowline, for profile drawings
    profile: tuple[tuple[float, float], ...] = ()
    low_point_stations: tuple[float, ...] = ()
    high_point_stations: tuple[float, ...] = ()


@dataclass(frozen=True)
class DrainagePointOutputRow:
    point_ref: str
    kind: str
    station: float
    ditch_run_ref: str = ""
    side: str = ""
    # its place on the flowline; None when no flowline reaches it
    x: float | None = None
    y: float | None = None
    z: float | None = None


@dataclass(frozen=True)
class DrainageLinkOutputRow:
    link_ref: str
    from_ref: str
    to_ref: str
    length_m: float
    grade_percent: float


@dataclass(frozen=True)
class DrainagePipeOutputRow:
    """A pipe: the link it sits on, its diameter, 3D length, inverts, grade and barrel volume."""

    link_ref: str
    from_ref: str
    to_ref: str
    diameter_m: float
    length_m: float
    from_invert_z: float
    to_invert_z: float
    grade_percent: float
    volume_m3: float
    # end coordinates, for drawings and the 3D preview
    from_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    to_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class DrainageCheckOutputRow:
    check_ref: str
    kind: str
    severity: str
    ditch_run_ref: str
    station_start: float
    station_end: float
    message: str


@dataclass
class DrainageOutput(OutputModelBase):
    drainage_output_id: str = "drainage-output:main"
    status: str = "empty"
    min_grade_percent: float = 0.0
    max_inlet_spacing_m: float = 0.0
    low_point_rule: str = ""
    flowline_rows: list[DrainageFlowlineOutputRow] = field(default_factory=list)
    point_rows: list[DrainagePointOutputRow] = field(default_factory=list)
    link_rows: list[DrainageLinkOutputRow] = field(default_factory=list)
    pipe_rows: list[DrainagePipeOutputRow] = field(default_factory=list)
    check_rows: list[DrainageCheckOutputRow] = field(default_factory=list)


__all__ = [
    "DrainageCheckOutputRow",
    "DrainageFlowlineOutputRow",
    "DrainageLinkOutputRow",
    "DrainageOutput",
    "DrainagePipeOutputRow",
    "DrainagePointOutputRow",
]
