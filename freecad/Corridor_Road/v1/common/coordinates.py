"""Coordinate context helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoordinateContext:
    """Minimal coordinate context shared across v1 models."""

    coordinate_mode: str = "model"
    crs_code: str = ""
    origin_mode: str = "project"
    north_rotation: float = 0.0
    vertical_reference: str = ""
