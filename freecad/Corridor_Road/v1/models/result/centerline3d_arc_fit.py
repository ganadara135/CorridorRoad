"""Plan arc-fit result contracts for CorridorRoad v1 source geometry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Centerline3DArcFitResult:
    """Typed quality result for a plan-geometry arc fit."""

    accepted: bool = False
    arc: tuple[float, float, float, float, float] | None = None
    radial_error: float = 0.0
    tolerance: float = 0.0
