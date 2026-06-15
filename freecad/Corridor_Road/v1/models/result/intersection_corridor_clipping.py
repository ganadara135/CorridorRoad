"""Intersection ordinary-corridor clipping result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class IntersectionCorridorClipRow:
    """One ordinary-corridor clipping responsibility before surface merge."""

    clip_id: str
    intersection_id: str
    control_area_ref: str
    alignment_ref: str
    surface_role: str
    clip_boundary_source: str = "intersection_control_area"
    clip_timing: str = "before_surface_merge"
    clip_method: str = "station_control_area_boundary"
    station_ranges: tuple[tuple[float, float], ...] = ()
    influence_ranges: tuple[tuple[float, float], ...] = ()
    control_region_refs: tuple[str, ...] = ()
    protected_zone_refs: tuple[str, ...] = ()
    status: str = "candidate"
    diagnostic_rows: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class IntersectionCorridorClipResult(ResultModelBase):
    """Source-driven clipping handoff for ordinary corridor surfaces."""

    clip_result_id: str = "intersection-corridor-clipping:main"
    intersection_id: str = ""
    intersection_kind: str = ""
    status: str = "not_evaluated"
    clip_row_count: int = 0
    design_clip_count: int = 0
    slope_clip_count: int = 0
    ready_clip_count: int = 0
    warning_clip_count: int = 0
    diagnostic_rows: list[str] = field(default_factory=list)
    clip_rows: list[IntersectionCorridorClipRow] = field(default_factory=list)
