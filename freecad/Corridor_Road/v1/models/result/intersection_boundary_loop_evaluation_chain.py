"""Typed authoritative Intersection boundary-loop evaluation chain result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntersectionBoundaryLoopEvaluationChainResult:
    status: str
    intersection_id: str
    topology_result: object | None = None
    edge_network_result: object | None = None
    surface_zone_result: object | None = None
    slope_face_loop_result: object | None = None
    boundary_loop_result: object | None = None
    completed_stages: tuple[str, ...] = ()
    failed_stage: str = ""
    diagnostic_rows: tuple[str, ...] = ()
    error_message: str = ""
