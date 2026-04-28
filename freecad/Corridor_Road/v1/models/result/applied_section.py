"""Applied section result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class AppliedSectionPoint:
    """Minimal point row inside an applied section."""

    point_id: str
    x: float
    y: float
    z: float
    point_role: str = "section_point"
    lateral_offset: float = 0.0


@dataclass(frozen=True)
class AppliedSectionFrame:
    """Evaluated station frame used to place one applied section."""

    station: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    tangent_direction_deg: float = 0.0
    profile_grade: float = 0.0
    alignment_status: str = ""
    profile_status: str = ""
    active_alignment_element_id: str = ""
    active_profile_segment_start_id: str = ""
    active_profile_segment_end_id: str = ""
    active_vertical_curve_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class AppliedSectionComponentRow:
    """Minimal semantic component row inside an applied section."""

    component_id: str
    kind: str
    source_template_id: str = ""
    region_id: str = ""
    side: str = "center"
    width: float = 0.0
    slope: float = 0.0
    thickness: float = 0.0
    material: str = ""
    override_ids: list[str] = field(default_factory=list)
    structure_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedSectionQuantityFragment:
    """Minimal quantity fragment attached to one applied section."""

    fragment_id: str
    quantity_kind: str
    value: float
    unit: str
    component_id: str = ""


@dataclass
class AppliedSection(ResultModelBase):
    """Station-specific resolved section result."""

    applied_section_id: str = ""
    corridor_id: str = ""
    alignment_id: str = ""
    profile_id: str = ""
    assembly_id: str = ""
    station: float = 0.0
    template_id: str = ""
    region_id: str = ""
    frame: AppliedSectionFrame | None = None
    surface_left_width: float = 0.0
    surface_right_width: float = 0.0
    subgrade_depth: float = 0.0
    daylight_left_width: float = 0.0
    daylight_right_width: float = 0.0
    daylight_left_slope: float = 0.0
    daylight_right_slope: float = 0.0
    point_rows: list[AppliedSectionPoint] = field(default_factory=list)
    component_rows: list[AppliedSectionComponentRow] = field(default_factory=list)
    quantity_rows: list[AppliedSectionQuantityFragment] = field(default_factory=list)
