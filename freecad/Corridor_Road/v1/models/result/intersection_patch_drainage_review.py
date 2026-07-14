"""Typed result-only Intersection patch drainage review metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntersectionPatchDrainageReviewResult:
    status: str
    source_scope: str = "result_only_review_hint"
    low_point_tolerance: float = 0.001
    low_point_candidate_count: int = 0
    low_point_x: float = 0.0
    low_point_y: float = 0.0
    low_point_z: float = 0.0
    low_point_source_ref: str = ""
    flow_hint_count: int = 0
    average_flow_dx: float = 0.0
    average_flow_dy: float = 0.0
    flow_hint_summary: str = ""
    diagnostic_rows: tuple[str, ...] = ()
