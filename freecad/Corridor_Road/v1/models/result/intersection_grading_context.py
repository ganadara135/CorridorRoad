"""Intersection grading/crossfall result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionGradingContextRow:
    """One resolved grading/crossfall contract row for an intersection surface zone."""

    context_id: str
    intersection_id: str
    zone_ref: str
    zone_role: str
    surface_role: str
    surface_priority: int = 0
    grading_policy_ref: str = ""
    source_grading_policy_ref: str = ""
    grading_mode: str = "use_normal_superelevation"
    target_crossfall_percent: float = 0.0
    crossfall_context: str = "normal_superelevation"
    controlling_profile_ref: str = ""
    profile_lineage_status: str = "missing"
    profile_handoff_status: str = "missing"
    superelevation_source_ref: str = ""
    superelevation_source_status: str = "not_used"
    superelevation_handoff_status: str = "not_used"
    vertical_handoff_status: str = "candidate"
    handoff_target: str = ""
    grading_source_scope: str = "intersection_policy"
    fallback_status: str = "none"
    crown_behavior: str = ""
    tie_in_rule: str = ""
    crossfall_transition: str = ""
    low_point_strategy: str = ""
    source_method: str = "manual"
    approval_status: str = "accepted"
    source_status: str = "accepted"
    source_diagnostic_rows: tuple[str, ...] = ()
    primary_alignment_ref: str = ""
    secondary_alignment_refs: tuple[str, ...] = ()
    alignment_refs: tuple[str, ...] = ()
    control_area_refs: tuple[str, ...] = ()
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionGradingContextResult(ResultModelBase):
    """Source-driven intersection grading/crossfall handoff before surface generation."""

    grading_context_result_id: str = "intersection-grading-context:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    context_count: int = 0
    intersection_override_count: int = 0
    normal_superelevation_count: int = 0
    warning_context_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    context_rows: list[IntersectionGradingContextRow] = field(default_factory=list)
