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
