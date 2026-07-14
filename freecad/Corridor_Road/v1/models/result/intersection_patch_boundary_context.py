"""Typed Intersection patch boundary evaluation context result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntersectionPatchBoundaryContextResult:
    status: str
    intersection_id: str
    tie_in_result: object | None = None
    boundary_segment_result: object | None = None
    patch_boundary_result: object | None = None
    boundary_loop_result: object | None = None
    shared_breakline_result: object | None = None
    completed_stages: tuple[str, ...] = ()
    failed_stage: str = ""
    boundary_evaluation_failed: bool = False
    boundary_loop_diagnostic_rows: tuple[str, ...] = ()
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
