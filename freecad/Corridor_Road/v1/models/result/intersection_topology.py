"""Intersection topology result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionTopologyAnchorRow:
    """One accepted or pending intersection anchor resolved from source intent."""

    anchor_result_id: str
    source_anchor_ref: str
    intersection_id: str
    source_method: str = "manual"
    approval_status: str = "accepted"
    primary_alignment_ref: str = ""
    primary_station: float = 0.0
    secondary_station_refs: tuple[tuple[str, float], ...] = ()
    station_lineage_status: str = "accepted"
    handoff_target: str = ""
    point_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    tolerance: float = 0.0
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    status: str = "candidate"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionTopologyLegSpanRow:
    """One participating intersection leg span resolved from source intent."""

    leg_span_id: str
    intersection_id: str
    leg_ref: str
    leg_role: str
    alignment_ref: str
    region_ref: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    control_area_ref: str = ""
    arm_policy_ref: str = ""
    edge_policy_refs: tuple[str, ...] = ()
    grading_policy_ref: str = ""
    source_method: str = ""
    approval_status: str = ""
    span_source: str = ""
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    status: str = "candidate"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionTopologyControlAreaRow:
    """One control-area span resolved for topology evaluation."""

    control_area_id: str
    intersection_id: str
    control_area_result_id: str = ""
    source_control_area_ref: str = ""
    alignment_ref: str = ""
    station_ranges: tuple[tuple[float, float], ...] = ()
    influence_ranges: tuple[tuple[float, float], ...] = ()
    control_region_refs: tuple[str, ...] = ()
    result_region_refs: tuple[str, ...] = ()
    source_method: str = "manual"
    approval_status: str = "accepted"
    intent_status: str = "intersection_owned"
    source_region_refs: tuple[str, ...] = ()
    region_lineage_status: str = "result_only"
    clipping_boundary_ref: str = ""
    region_handoff_status: str = "accepted"
    clipping_handoff_status: str = "accepted"
    handoff_target: str = ""
    surface_zone_scope: str = "intersection_control_area"
    curb_return_policy_ref: str = ""
    grading_policy_ref: str = ""
    drainage_policy_ref: str = ""
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    status: str = "candidate"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionTopologyLaneConnectionRow:
    """One lane movement relationship resolved from source intent."""

    connection_id: str
    intersection_id: str
    lane_connection_result_id: str = ""
    source_lane_connection_ref: str = ""
    movement_type: str = "through"
    from_leg_ref: str = ""
    to_leg_ref: str = ""
    from_edge_policy_ref: str = ""
    to_edge_policy_ref: str = ""
    from_lane_index: int = 1
    to_lane_index: int = 1
    from_leg_source_status: str = ""
    to_leg_source_status: str = ""
    from_edge_family_intent: str = ""
    to_edge_family_intent: str = ""
    from_edge_source_status: str = ""
    to_edge_source_status: str = ""
    movement_lineage_status: str = "connected"
    leg_handoff_status: str = "accepted"
    edge_handoff_status: str = "accepted"
    handoff_scope: str = "lane_connection"
    handoff_target: str = ""
    source_method: str = "manual"
    approval_status: str = "accepted"
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    status: str = "candidate"
    notes: str = ""


@dataclass
class IntersectionTopologyResult(ResultModelBase):
    """Deterministic source-level topology result before edge or surface generation."""

    topology_result_id: str = "intersection-topology:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    participating_alignment_count: int = 0
    control_region_count: int = 0
    anchor_count: int = 0
    leg_span_count: int = 0
    control_area_count: int = 0
    lane_connection_count: int = 0
    policy_refs: list[str] = field(default_factory=list)
    diagnostic_rows: list[str] = field(default_factory=list)
    anchor_rows: list[IntersectionTopologyAnchorRow] = field(default_factory=list)
    leg_span_rows: list[IntersectionTopologyLegSpanRow] = field(default_factory=list)
    control_area_rows: list[IntersectionTopologyControlAreaRow] = field(default_factory=list)
    lane_connection_rows: list[IntersectionTopologyLaneConnectionRow] = field(default_factory=list)
