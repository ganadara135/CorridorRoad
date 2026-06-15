"""Intersection topology result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


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
    status: str = "candidate"
    notes: str = ""


@dataclass(frozen=True)
class IntersectionTopologyControlAreaRow:
    """One control-area span resolved for topology evaluation."""

    control_area_id: str
    intersection_id: str
    alignment_ref: str = ""
    station_ranges: tuple[tuple[float, float], ...] = ()
    influence_ranges: tuple[tuple[float, float], ...] = ()
    control_region_refs: tuple[str, ...] = ()
    curb_return_policy_ref: str = ""
    grading_policy_ref: str = ""
    drainage_policy_ref: str = ""
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
    leg_span_count: int = 0
    control_area_count: int = 0
    policy_refs: list[str] = field(default_factory=list)
    diagnostic_rows: list[str] = field(default_factory=list)
    leg_span_rows: list[IntersectionTopologyLegSpanRow] = field(default_factory=list)
    control_area_rows: list[IntersectionTopologyControlAreaRow] = field(default_factory=list)
