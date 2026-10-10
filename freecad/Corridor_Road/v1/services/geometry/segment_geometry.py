"""FreeCAD-independent XY segment primitives for CorridorRoad v1."""

from __future__ import annotations

from .xy_primitives import xy_point


def xy_point_on_segment(
    point: object,
    start: object,
    end: object,
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    """Return whether a point lies on a finite XY segment within tolerance."""

    px, py = xy_point(point)
    sx, sy = xy_point(start)
    ex, ey = xy_point(end)
    active_tolerance = max(float(tolerance), 0.0)
    cross = (py - sy) * (ex - sx) - (px - sx) * (ey - sy)
    if abs(cross) > active_tolerance:
        return False
    return (
        min(sx, ex) - active_tolerance <= px <= max(sx, ex) + active_tolerance
        and min(sy, ey) - active_tolerance <= py <= max(sy, ey) + active_tolerance
    )
