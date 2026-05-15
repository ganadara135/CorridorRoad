"""Applied-section solid profile result contracts for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


SOLID_PROFILE_ORIENTATION = "top_left_top_right_bottom_right_bottom_left"


@dataclass(frozen=True)
class SolidProfileNode:
    """One semantic node in a closed solid profile."""

    node_id: str
    semantic_role: str
    x: float
    y: float
    z: float
    lateral_offset: float = 0.0
    vertical_offset: float = 0.0
    source_point_ref: str = ""


@dataclass(frozen=True)
class SolidProfileEdge:
    """One semantic edge in a closed solid profile."""

    edge_id: str
    start_node_id: str
    end_node_id: str
    semantic_role: str
    source_ref: str = ""


@dataclass(frozen=True)
class AppliedSectionSolidProfile:
    """Closed semantic profile generated at one station for one solid target."""

    profile_id: str
    target_id: str
    station: float
    applied_section_ref: str
    region_ref: str = ""
    profile_role: str = "road_body_envelope"
    node_rows: list[SolidProfileNode] = field(default_factory=list)
    edge_rows: list[SolidProfileEdge] = field(default_factory=list)
    is_closed: bool = False
    orientation: str = SOLID_PROFILE_ORIENTATION
    diagnostic_refs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class AppliedSectionSolidProfileSet(ResultModelBase):
    """Ordered closed profiles prepared for topology-first solid generation."""

    profile_set_id: str = ""
    corridor_ref: str = ""
    target_ref: str = ""
    applied_section_set_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    profile_rows: list[AppliedSectionSolidProfile] = field(default_factory=list)
