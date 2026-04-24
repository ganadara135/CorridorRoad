"""Applied section set result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .applied_section import AppliedSection
from .base import ResultModelBase


@dataclass(frozen=True)
class AppliedSectionStationRow:
    """Ordered station reference row for an applied section set."""

    station_row_id: str
    station: float
    applied_section_id: str
    kind: str = "regular_sample"


@dataclass
class AppliedSectionSet(ResultModelBase):
    """Ordered collection of applied sections for a corridor scope."""

    applied_section_set_id: str = ""
    corridor_id: str = ""
    alignment_id: str = ""
    station_rows: list[AppliedSectionStationRow] = field(default_factory=list)
    sections: list[AppliedSection] = field(default_factory=list)
