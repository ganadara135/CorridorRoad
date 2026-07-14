"""Typed Intersection patch grading evaluation result."""

from __future__ import annotations

from dataclasses import dataclass

from .tin_surface import TINVertex


@dataclass(frozen=True)
class IntersectionPatchGradingResult:
    status: str
    intersection_id: str
    grading_policy: object | None
    grading_mode: str
    vertex_rows: tuple[TINVertex, ...] = ()
    grading_plane: tuple[float, float, float] | None = None
    max_z_delta: float = 0.0
    diagnostic_rows: tuple[str, ...] = ()
