"""Surface output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class SurfaceRowOutput:
    """Minimal surface family row for surface output."""

    surface_row_id: str
    surface_id: str
    surface_kind: str
    tin_ref: str
    status: str = "ready"
    parent_surface_ref: str = ""


@dataclass(frozen=True)
class SurfaceBoundaryRow:
    """Minimal boundary row for surface output."""

    boundary_row_id: str
    surface_ref: str
    boundary_kind: str
    vertex_refs: list[str] = field(default_factory=list)
    closed: bool = True


@dataclass(frozen=True)
class SurfaceComparisonOutputRow:
    """Minimal comparison row for surface output."""

    comparison_row_id: str
    comparison_id: str
    comparison_kind: str
    base_surface_ref: str
    compare_surface_ref: str
    result_surface_ref: str = ""


@dataclass(frozen=True)
class SurfaceSpanOutputRow:
    """Station span metadata for surface output consumers."""

    span_row_id: str
    surface_ref: str
    station_start: float
    station_end: float
    from_region_ref: str = ""
    to_region_ref: str = ""
    span_kind: str = "same_region"
    transition_ref: str = ""
    continuity_status: str = "ok"
    diagnostic_refs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class IntersectionSurfaceZoneOutputRow:
    """Accepted output handoff row for one intersection surface zone."""

    output_row_id: str
    intersection_id: str
    surface_zone_ref: str
    surface_zone_result_ref: str
    edge_network_result_ref: str
    zone_family: str
    design_zone_role: str = ""
    surface_role: str = "design"
    source_edge_refs: tuple[str, ...] = ()
    boundary_edge_refs: tuple[str, ...] = ()
    inner_edge_refs: tuple[str, ...] = ()
    outer_edge_refs: tuple[str, ...] = ()
    tie_edge_refs: tuple[str, ...] = ()
    leg_refs: tuple[str, ...] = ()
    alignment_refs: tuple[str, ...] = ()
    control_area_refs: tuple[str, ...] = ()
    vertical_policy_ref: str = ""
    output_contract_status: str = "accepted_surface_zone"
    digital_twin_handoff: str = "accepted_zone_candidate"
    build_backend: str = "planned_edge_network_zone_surface"
    source_status: str = "accepted"
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionSurfaceZoneOutput(OutputModelBase):
    """Normalized output rows that consume accepted Intersection Surface Zone results."""

    surface_zone_output_id: str = "intersection-surface-zone-output:main"
    intersection_id: str = ""
    status: str = "not_evaluated"
    output_contract_status: str = "accepted_surface_zone"
    digital_twin_handoff: str = "accepted_zone_candidate"
    surface_zone_result_ref: str = ""
    edge_network_result_ref: str = ""
    zone_output_rows: list[IntersectionSurfaceZoneOutputRow] = field(default_factory=list)
    diagnostic_rows: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IntersectionSurfaceReplacementDecision:
    """Downstream handoff decision between transitional patch and accepted zone surface."""

    readiness: str
    selected_ref: str
    selected_role: str
    selection_reason: str
    patch_selected: bool
    zone_selected: bool
    patch_handoff_preference: str
    zone_handoff_preference: str


def intersection_surface_replacement_readiness(gate_status: str) -> str:
    """Normalize a replacement gate value into handoff readiness."""

    gate = str(gate_status or "")
    if gate == "ready_to_replace":
        return "ready_to_replace"
    if gate == "blocked":
        return "blocked"
    if gate:
        return "review_only"
    return ""


def intersection_surface_replacement_handoff_preference(readiness: str, handoff_role: str) -> str:
    """Return the handoff label for one side of the replacement decision."""

    role = str(handoff_role or "")
    state = str(readiness or "")
    if role == "transitional_patch":
        if state == "ready_to_replace":
            return "fallback_until_replaced"
        if state == "blocked":
            return "fallback_blocked_replacement"
        if state == "review_only":
            return "fallback_review_required"
        return "fallback"
    if role == "accepted_zone_surface":
        if state == "ready_to_replace":
            return "preferred_ready_to_replace"
        if state == "blocked":
            return "candidate_blocked"
        if state == "review_only":
            return "preferred_candidate_review_only"
        return "candidate"
    return state


def intersection_surface_replacement_blocker_kind(readiness: str, selected_role: str = "") -> str:
    """Return the readiness-specific blocker kind for transitional patch fallback handoff."""

    state = str(readiness or "")
    role = str(selected_role or "")
    if state == "review_only":
        return "intersection_replacement_gate_review_required"
    if state == "blocked":
        return "intersection_replacement_gate_blocked"
    if state == "ready_to_replace" and role == "transitional_patch_fallback":
        return "intersection_replacement_ready_patch_fallback"
    return ""


def decide_intersection_surface_downstream_handoff(
    *,
    gate_status: str,
    patch_ref: str,
    zone_surface_ref: str = "",
) -> IntersectionSurfaceReplacementDecision:
    """Choose which intersection surface is currently selected for downstream handoff."""

    readiness = intersection_surface_replacement_readiness(gate_status)
    patch = str(patch_ref or "")
    zone = str(zone_surface_ref or "")
    if readiness == "ready_to_replace" and zone:
        selected_ref = zone
        selected_role = "accepted_zone_surface"
        reason = "replacement_gate_ready_to_replace"
    elif readiness == "blocked":
        selected_ref = patch
        selected_role = "transitional_patch_fallback"
        reason = "replacement_gate_blocked"
    else:
        selected_ref = patch
        selected_role = "transitional_patch_fallback"
        reason = "replacement_gate_review_only"
    return IntersectionSurfaceReplacementDecision(
        readiness=readiness,
        selected_ref=selected_ref,
        selected_role=selected_role,
        selection_reason=reason,
        patch_selected=bool(selected_ref and selected_ref == patch),
        zone_selected=bool(selected_ref and selected_ref == zone),
        patch_handoff_preference=intersection_surface_replacement_handoff_preference(readiness, "transitional_patch"),
        zone_handoff_preference=intersection_surface_replacement_handoff_preference(readiness, "accepted_zone_surface"),
    )


@dataclass(frozen=True)
class SurfaceSummaryRow:
    """Minimal summary row for surface output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class SurfaceOutput(OutputModelBase):
    """Normalized surface output payload."""

    surface_output_id: str = ""
    corridor_id: str = ""
    surface_rows: list[SurfaceRowOutput] = field(default_factory=list)
    boundary_rows: list[SurfaceBoundaryRow] = field(default_factory=list)
    span_rows: list[SurfaceSpanOutputRow] = field(default_factory=list)
    comparison_rows: list[SurfaceComparisonOutputRow] = field(default_factory=list)
    summary_rows: list[SurfaceSummaryRow] = field(default_factory=list)
