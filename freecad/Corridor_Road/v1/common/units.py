"""Unit context helpers for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnitContext:
    """Minimal unit context shared across v1 models."""

    linear_unit: str = "m"
    area_unit: str = "m2"
    volume_unit: str = "m3"
    slope_unit: str = "percent"
