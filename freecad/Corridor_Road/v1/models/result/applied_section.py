"""Applied section result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class AppliedSectionPoint:
    """Point row inside an applied section."""

    point_id: str
    x: float
    y: float
    z: float
    point_role: str = "section_point"
    lateral_offset: float = 0.0
    subassembly_ref: str = ""
    side: str = ""
    drainage_ref: str = ""


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
    source_mode: str = ""
    source_status: str = ""
    source_diagnostic_rows: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class AppliedSectionSubassemblyRow:
    """Resolved Subassembly row inside an applied section."""

    subassembly_id: str
    kind: str
    source_template_id: str = ""
    definition_ref: str = ""
    preset_ref: str = ""
    preset_version: str = ""
    preset_status: str = ""
    source_instance_ref: str = ""
    region_id: str = ""
    side: str = "center"
    width: float = 0.0
    slope: float = 0.0
    thickness: float = 0.0
    material: str = ""
    override_ids: list[str] = field(default_factory=list)
    structure_ids: list[str] = field(default_factory=list)
    drainage_refs: list[str] = field(default_factory=list)
    parameters: dict[str, object] = field(default_factory=dict)
    point_code_rules: tuple[str, ...] = field(default_factory=tuple)
    link_code_rules: tuple[str, ...] = field(default_factory=tuple)
    shape_code_rules: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedSectionSubassemblyPoint:
    """Evaluated point emitted by one Subassembly."""

    point_id: str
    subassembly_ref: str
    point_code: str
    x: float
    y: float
    z: float
    lateral_offset: float = 0.0
    side: str = ""
    target_ref: str = ""
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedSectionSubassemblyLink:
    """Evaluated link emitted by one Subassembly."""

    link_id: str
    subassembly_ref: str
    start_point_ref: str
    end_point_ref: str
    link_code: str
    surface_role: str = ""
    material: str = ""
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedSectionSubassemblyShape:
    """Evaluated closed shape emitted by one Subassembly."""

    shape_id: str
    subassembly_ref: str
    point_refs: list[str] = field(default_factory=list)
    shape_code: str = ""
    material: str = ""
    thickness: float = 0.0
    solid_family: str = ""
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedSectionQuantityFragment:
    """Minimal quantity fragment attached to one applied section."""

    fragment_id: str
    quantity_kind: str
    value: float
    unit: str
    subassembly_id: str = ""


@dataclass
class AppliedSection(ResultModelBase):
    """Station-specific resolved section result.

    `subassembly_rows` and Subassembly point/link/shape rows are the active
    result contract.
    """

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
    active_superelevation_id: str = ""
    superelevation_left_crossfall: float = 0.0
    superelevation_right_crossfall: float = 0.0
    active_superelevation_transition_id: str = ""
    superelevation_source_rows: list[str] = field(default_factory=list)
    active_intersection_id: str = ""
    active_intersection_control_area_id: str = ""
    active_intersection_leg_id: str = ""
    active_intersection_leg_role: str = ""
    active_intersection_control_region_refs: list[str] = field(default_factory=list)
    active_intersection_grading_policy_ref: str = ""
    active_intersection_source_status: str = ""
    active_intersection_source_diagnostic_rows: list[str] = field(default_factory=list)
    active_intersection_source_stage_rows: list[str] = field(default_factory=list)
    intersection_diagnostic_rows: list[str] = field(default_factory=list)
    point_rows: list[AppliedSectionPoint] = field(default_factory=list)
    subassembly_rows: list[AppliedSectionSubassemblyRow] = field(default_factory=list)
    subassembly_point_rows: list[AppliedSectionSubassemblyPoint] = field(default_factory=list)
    subassembly_link_rows: list[AppliedSectionSubassemblyLink] = field(default_factory=list)
    subassembly_shape_rows: list[AppliedSectionSubassemblyShape] = field(default_factory=list)
    quantity_rows: list[AppliedSectionQuantityFragment] = field(default_factory=list)
    active_structure_ids: list[str] = field(default_factory=list)
    active_structure_rule_ids: list[str] = field(default_factory=list)
    active_structure_influence_zone_ids: list[str] = field(default_factory=list)
    structure_diagnostic_rows: list[str] = field(default_factory=list)
