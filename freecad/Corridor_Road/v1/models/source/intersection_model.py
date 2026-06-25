"""Intersection source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import SourceModelBase


INTERSECTION_KIND_PRESETS: dict[str, dict[str, object]] = {
    "t_intersection": {
        "label": "T Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "side_approach"),
        "minimum_alignment_count": 2,
    },
    "cross_intersection": {
        "label": "Cross Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "secondary_before", "secondary_after"),
        "minimum_alignment_count": 2,
    },
    "skewed_intersection": {
        "label": "Skewed Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "skew_before", "skew_after"),
        "minimum_alignment_count": 2,
    },
    "urban_curb_gutter_intersection": {
        "label": "Urban Curb/Gutter Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "urban_side_before", "urban_side_after"),
        "minimum_alignment_count": 2,
    },
    "drainage_sag_intersection": {
        "label": "Drainage-Sensitive Sag Intersection",
        "default_leg_roles": ("primary_before", "primary_after", "sag_side_before", "sag_side_after"),
        "minimum_alignment_count": 2,
    },
    "y_intersection": {
        "label": "Y Intersection",
        "default_leg_roles": ("primary_approach", "left_branch", "right_branch"),
        "minimum_alignment_count": 2,
    },
}


@dataclass(frozen=True)
class IntersectionAnchorRow:
    """Source anchor row for one intersection point and station mapping."""

    anchor_id: str
    intersection_id: str
    source_method: str = "detected"
    approval_status: str = "draft"
    primary_alignment_ref: str = ""
    primary_station: float = 0.0
    secondary_station_refs: dict[str, float] = field(default_factory=dict)
    point_x: float = 0.0
    point_y: float = 0.0
    point_z: float = 0.0
    tolerance: float = 0.0
    diagnostic_rows: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class IntersectionLegRow:
    """Minimal participating-leg row for one junction."""

    leg_id: str
    leg_role: str
    alignment_ref: str
    intersection_id: str = ""
    profile_ref: str = ""
    centerline3d_ref: str = ""
    region_ref: str = ""
    approach_station_start: float = 0.0
    approach_station_end: float = 0.0
    source_method: str = "manual"
    approval_status: str = "accepted"
    span_source: str = "explicit"
    arm_policy_ref: str = ""
    edge_policy_refs: list[str] = field(default_factory=list)
    grading_policy_ref: str = ""
    priority: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class IntersectionControlArea:
    """Minimal control-area row for one intersection."""

    control_area_id: str
    intersection_id: str
    alignment_ref: str = ""
    station_ranges: list[tuple[float, float]] = field(default_factory=list)
    influence_ranges: list[tuple[float, float]] = field(default_factory=list)
    control_region_refs: list[str] = field(default_factory=list)
    source_method: str = "manual"
    approval_status: str = "accepted"
    intent_status: str = "intersection_owned"
    source_region_refs: list[str] = field(default_factory=list)
    turn_lane_policy_ref: str = ""
    curb_return_policy_ref: str = ""
    grading_policy_ref: str = ""
    drainage_policy_ref: str = ""
    diagnostic_rows: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class IntersectionCornerRow:
    """Source corner row that owns curb-return attachment intent."""

    corner_id: str
    intersection_id: str
    control_area_ref: str = ""
    from_leg_ref: str = ""
    to_leg_ref: str = ""
    side: str = ""
    quadrant: str = ""
    curb_return_policy_ref: str = ""
    source_method: str = "manual"
    approval_status: str = "accepted"
    diagnostic_rows: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class IntersectionCurbReturnPolicyRow:
    """Source policy for first-slice intersection corner return preview geometry."""

    policy_id: str
    intersection_id: str
    radius: float
    side: str = "all"
    edge_role: str = "pavement_edge"
    long_edge_factor: float = 2.5
    max_boundary_edge_length: float = 0.0
    approach_leg_refs: list[str] = field(default_factory=list)
    corner_refs: list[str] = field(default_factory=list)
    status: str = "active"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionArmPolicyRow:
    """Source policy for one intersection road arm."""

    policy_id: str
    intersection_id: str
    leg_ref: str = ""
    arm_role: str = ""
    design_speed_kph: float = 0.0
    design_vehicle_ref: str = ""
    lane_count: int = 1
    lane_width: float = 3.5
    shoulder_width: float = 0.0
    median_width: float = 0.0
    turn_lane_policy_ref: str = ""
    status: str = "active"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionEdgePolicyRow:
    """Source policy for an intersection edge family before topology evaluation."""

    policy_id: str
    intersection_id: str
    leg_ref: str = ""
    edge_role: str = "pavement_edge"
    side: str = "both"
    offset_rule: str = ""
    offset_value: float = 0.0
    elevation_rule: str = "from_crossfall"
    profile_ref: str = ""
    source_policy_ref: str = ""
    edge_family_intent: str = ""
    source_method: str = "manual"
    approval_status: str = "accepted"
    assembly_ref: str = ""
    template_ref: str = ""
    subassembly_ref: str = ""
    subassembly_kind: str = ""
    diagnostic_rows: list[str] = field(default_factory=list)
    status: str = "active"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionLaneConnectionRow:
    """Source row for lane movement continuity through an intersection."""

    connection_id: str
    intersection_id: str
    movement_type: str = "through"
    from_leg_ref: str = ""
    to_leg_ref: str = ""
    from_edge_policy_ref: str = ""
    to_edge_policy_ref: str = ""
    from_lane_index: int = 1
    to_lane_index: int = 1
    source_method: str = "manual"
    approval_status: str = "accepted"
    diagnostic_rows: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class IntersectionGradingPolicyRow:
    """Source policy for intersection-area crossfall and grading behavior."""

    policy_id: str
    intersection_id: str
    mode: str = "flatten_intersection"
    target_crossfall_percent: float = 0.0
    primary_alignment_ref: str = ""
    secondary_alignment_refs: list[str] = field(default_factory=list)
    controlling_profile_ref: str = ""
    crown_behavior: str = "flatten"
    tie_in_rule: str = "blend_to_leg_profiles"
    crossfall_transition: str = "linear"
    low_point_strategy: str = "review_low_points"
    source_method: str = "manual"
    approval_status: str = "accepted"
    diagnostic_rows: list[str] = field(default_factory=list)
    status: str = "active"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionDrainagePolicyRow:
    """Source policy for intersection low-point and drainage handoff intent."""

    policy_id: str
    intersection_id: str
    capture_mode: str = "review_low_points"
    inlet_spacing: float = 0.0
    low_point_tolerance: float = 0.05
    gutter_edge_refs: list[str] = field(default_factory=list)
    drainage_element_refs: list[str] = field(default_factory=list)
    flow_route_refs: list[str] = field(default_factory=list)
    inlet_candidate_refs: list[str] = field(default_factory=list)
    low_point_refs: list[str] = field(default_factory=list)
    intent_status: str = "hint_only"
    source_method: str = "manual"
    approval_status: str = "accepted"
    diagnostic_rows: list[str] = field(default_factory=list)
    status: str = "active"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionRow:
    """Minimal at-grade intersection definition row."""

    intersection_id: str
    intersection_kind: str
    intersection_index: int = 0
    primary_alignment_ref: str = ""
    secondary_alignment_refs: list[str] = field(default_factory=list)
    intersection_point_x: float = 0.0
    intersection_point_y: float = 0.0
    intersection_point_z: float = 0.0
    primary_station: float = 0.0
    secondary_station_refs: dict[str, float] = field(default_factory=dict)
    control_region_refs: list[str] = field(default_factory=list)
    leg_rows: list[IntersectionLegRow] = field(default_factory=list)
    control_area_ref: str = ""
    grading_policy_ref: str = ""
    drainage_ref: str = ""
    design_criteria_ref: str = ""
    source_mode: str = "use_existing_alignments"
    policy_refs: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_supported_kind(self) -> bool:
        """Return whether this row uses a first-slice supported intersection type."""

        return self.intersection_kind in INTERSECTION_KIND_PRESETS


@dataclass
class IntersectionModel(SourceModelBase):
    """Durable at-grade junction source contract."""

    intersection_model_id: str = ""
    result_refs: list[str] = field(default_factory=list)
    anchor_rows: list[IntersectionAnchorRow] = field(default_factory=list)
    intersection_rows: list[IntersectionRow] = field(default_factory=list)
    control_area_rows: list[IntersectionControlArea] = field(default_factory=list)
    corner_rows: list[IntersectionCornerRow] = field(default_factory=list)
    arm_policy_rows: list[IntersectionArmPolicyRow] = field(default_factory=list)
    curb_return_policy_rows: list[IntersectionCurbReturnPolicyRow] = field(default_factory=list)
    edge_policy_rows: list[IntersectionEdgePolicyRow] = field(default_factory=list)
    lane_connection_rows: list[IntersectionLaneConnectionRow] = field(default_factory=list)
    grading_policy_rows: list[IntersectionGradingPolicyRow] = field(default_factory=list)
    drainage_policy_rows: list[IntersectionDrainagePolicyRow] = field(default_factory=list)


def intersection_preset_labels() -> list[str]:
    """Return user-facing labels for the first intersection type presets."""

    return [str(row["label"]) for row in INTERSECTION_KIND_PRESETS.values()]


def intersection_kind_from_label(label: str) -> str:
    """Resolve a user-facing preset label to an internal intersection kind."""

    normalized = str(label or "").strip().lower()
    for kind, preset in INTERSECTION_KIND_PRESETS.items():
        if normalized == str(preset.get("label", "") or "").strip().lower():
            return kind
    return ""


def intersection_row_from_kind(
    *,
    intersection_id: str,
    intersection_kind: str,
    primary_alignment_ref: str = "",
    secondary_alignment_refs: list[str] | None = None,
    control_region_refs: list[str] | None = None,
) -> IntersectionRow:
    """Create a first-slice intersection row from a supported kind preset."""

    kind = str(intersection_kind or "").strip()
    preset = INTERSECTION_KIND_PRESETS.get(kind)
    if preset is None:
        raise ValueError(f"Unsupported intersection kind: {intersection_kind}")

    secondaries = list(secondary_alignment_refs or [])
    roles = tuple(preset.get("default_leg_roles", ()) or ())
    leg_rows: list[IntersectionLegRow] = []
    for index, role in enumerate(roles):
        leg_id = f"{intersection_id}:leg-{index + 1:02d}"
        if str(role).startswith("primary"):
            alignment_ref = primary_alignment_ref
        else:
            alignment_ref = secondaries[0] if secondaries else ""
        leg_rows.append(
            IntersectionLegRow(
                leg_id=leg_id,
                intersection_id=intersection_id,
                leg_role=str(role),
                alignment_ref=alignment_ref,
                arm_policy_ref=f"arm-policy:{intersection_id}:leg-{index + 1:02d}",
                edge_policy_refs=[
                    f"edge-policy:{intersection_id}:leg-{index + 1:02d}:pavement",
                    f"edge-policy:{intersection_id}:leg-{index + 1:02d}:daylight",
                ],
                grading_policy_ref=f"grading:{intersection_id}:default",
                priority=index + 1,
            )
        )

    return IntersectionRow(
        intersection_id=intersection_id,
        intersection_kind=kind,
        primary_alignment_ref=primary_alignment_ref,
        secondary_alignment_refs=secondaries,
        control_region_refs=list(control_region_refs or []),
        leg_rows=leg_rows,
        control_area_ref=f"{intersection_id}:control-area",
        grading_policy_ref=f"grading:{intersection_id}:default",
        policy_refs=[
            f"curb-return:{intersection_id}:default",
            f"grading:{intersection_id}:default",
            f"drainage-policy:{intersection_id}:default",
            *[str(leg.arm_policy_ref) for leg in leg_rows if str(leg.arm_policy_ref)],
            *[
                str(edge_ref)
                for leg in leg_rows
                for edge_ref in list(getattr(leg, "edge_policy_refs", []) or [])
                if str(edge_ref)
            ],
        ],
    )
