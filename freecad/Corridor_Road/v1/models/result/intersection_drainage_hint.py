"""Intersection drainage hint result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionDrainageHintRow:
    """One review-only drainage hint derived from intersection surface zones."""

    hint_id: str
    intersection_id: str
    hint_kind: str
    zone_ref: str = ""
    zone_role: str = ""
    surface_role: str = ""
    recommended_element_kind: str = ""
    drainage_policy_ref: str = ""
    drainage_mode: str = "review_low_points"
    grading_context_ref: str = ""
    crossfall_context: str = ""
    control_area_refs: tuple[str, ...] = ()
    source_edge_refs: tuple[str, ...] = ()
    boundary_edge_refs: tuple[str, ...] = ()
    station_ranges: tuple[tuple[float, float], ...] = ()
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionDrainageHintResult(ResultModelBase):
    """Source-driven low-point and inlet recommendation handoff for intersections."""

    drainage_hint_result_id: str = "intersection-drainage-hints:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    hint_row_count: int = 0
    low_point_hint_count: int = 0
    inlet_recommendation_count: int = 0
    outlet_handoff_count: int = 0
    missing_coverage_count: int = 0
    ready_hint_count: int = 0
    warning_hint_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    hint_rows: list[IntersectionDrainageHintRow] = field(default_factory=list)
