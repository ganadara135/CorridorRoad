"""Profile output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class ProfileLineRow:
    """Minimal line row for profile output."""

    line_row_id: str
    kind: str
    station_values: list[float] = field(default_factory=list)
    elevation_values: list[float] = field(default_factory=list)
    style_role: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class ProfilePviRow:
    """Minimal PVI row for profile output."""

    pvi_row_id: str
    station: float
    elevation: float
    label: str = ""


@dataclass(frozen=True)
class ProfileEarthworkRow:
    """Minimal attached earthwork row for profile output."""

    earthwork_row_id: str
    kind: str
    station_start: float
    station_end: float
    value: float
    unit: str


@dataclass(frozen=True)
class ProfileSummaryRow:
    """Minimal summary row for profile output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class ProfileOutput(OutputModelBase):
    """Normalized profile output payload."""

    profile_output_id: str = ""
    alignment_id: str = ""
    profile_id: str = ""
    line_rows: list[ProfileLineRow] = field(default_factory=list)
    pvi_rows: list[ProfilePviRow] = field(default_factory=list)
    earthwork_rows: list[ProfileEarthworkRow] = field(default_factory=list)
    summary_rows: list[ProfileSummaryRow] = field(default_factory=list)
