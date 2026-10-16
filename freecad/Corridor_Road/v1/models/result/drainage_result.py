"""Drainage result contracts for CorridorRoad v1.

The evaluated state of the Drainage source over the Applied Sections: one flowline per Ditch Run
with its grades, low and high points and flow direction, and the checks against the Drainage
Policy. Rebuildable; nothing here is authored.

Units: stations, lengths and coordinates in meters (the Applied Section units), grades in percent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


# Flow along a flowline segment, by station direction.
FLOW_TOWARD_END = "toward_end"
FLOW_TOWARD_START = "toward_start"
FLOW_NONE = "none"

CHECK_ERROR = "error"
CHECK_WARNING = "warning"
CHECK_INFO = "info"


@dataclass(frozen=True)
class FlowlineStation:
    """The ditch flowline (its lowest point) at one Applied Section."""

    station: float
    x: float
    y: float
    z: float
    applied_section_ref: str = ""


@dataclass(frozen=True)
class FlowlineSegment:
    """The flowline between two consecutive stations; `grade_percent` rises with station."""

    station_start: float
    station_end: float
    length_m: float
    grade_percent: float
    flow: str = FLOW_NONE


@dataclass(frozen=True)
class DitchRunFlowline:
    ditch_run_ref: str
    side: str
    subassembly_ref: str
    alignment_ref: str = ""
    station_rows: list[FlowlineStation] = field(default_factory=list)
    segment_rows: list[FlowlineSegment] = field(default_factory=list)
    low_point_stations: list[float] = field(default_factory=list)
    high_point_stations: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class DrainageCheck:
    """One finding of the Drainage evaluation, at a station or over a station range."""

    check_id: str
    kind: str
    severity: str
    ditch_run_ref: str
    station_start: float
    station_end: float
    message: str


@dataclass(frozen=True)
class DrainageLinkRow:
    """A Link measured between its points' places on the flowlines; `grade_percent` falls negative."""

    link_ref: str
    from_ref: str
    to_ref: str
    length_m: float
    from_z: float
    to_z: float
    grade_percent: float


@dataclass(frozen=True)
class DrainageSuggestion:
    """A point the evaluation proposes; the Drainage panel adds it to the source on request."""

    suggestion_id: str
    kind: str
    ditch_run_ref: str
    station: float
    reason: str
    message: str


@dataclass
class DrainageResult(ResultModelBase):
    drainage_result_id: str = "drainage-result:main"
    drainage_model_ref: str = ""
    applied_section_set_ref: str = ""
    min_grade_percent: float = 0.0
    flowline_rows: list[DitchRunFlowline] = field(default_factory=list)
    check_rows: list[DrainageCheck] = field(default_factory=list)
    suggestion_rows: list[DrainageSuggestion] = field(default_factory=list)
    link_rows: list[DrainageLinkRow] = field(default_factory=list)
    status: str = "empty"
