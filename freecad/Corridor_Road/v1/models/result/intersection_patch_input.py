"""Typed Intersection patch input preparation results."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINVertex


@dataclass(frozen=True)
class IntersectionPatchSuperelevationContext:
    source_count: int = 0
    transition_count: int = 0
    left_min: float = 0.0
    left_max: float = 0.0
    right_min: float = 0.0
    right_max: float = 0.0
    summary: str = ""


@dataclass(frozen=True)
class IntersectionPatchInputPreparationResult:
    status: str
    intersection_id: str
    control_region_refs: tuple[str, ...] = ()
    section_rows: tuple[object, ...] = ()
    vertex_rows: tuple[TINVertex, ...] = ()
    duplicate_xy_count: int = 0
    superelevation_context: IntersectionPatchSuperelevationContext = (
        IntersectionPatchSuperelevationContext()
    )
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
