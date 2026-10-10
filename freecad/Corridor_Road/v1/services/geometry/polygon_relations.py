"""FreeCAD-independent polygon relation predicates for CorridorRoad v1."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from .segment_geometry import xy_point_on_segment
from .xy_primitives import xy_point


PointValue = TypeVar("PointValue")


def xy_closed_edges(points: Sequence[PointValue]) -> list[tuple[PointValue, PointValue]]:
    """Return consecutive polygon edges including the closing edge."""

    if len(points) < 2:
        return []
    return [(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]


def xy_point_in_polygon(point: object, polygon: Sequence[object]) -> bool:
    """Return the legacy ray-cast inclusion result for one XY polygon."""

    x, y = xy_point(point)
    if len(polygon) < 3:
        return False
    inside = False
    previous = xy_point(polygon[-1])
    for value in polygon:
        current = xy_point(value)
        xi, yi = current
        xj, yj = previous
        if ((yi > y) != (yj > y)) and x < (
            (xj - xi) * (y - yi) / ((yj - yi) or 1.0e-12) + xi
        ):
            inside = not inside
        previous = current
    return inside


def xy_point_in_polygon_strict(
    point: object,
    polygon: Sequence[object],
    *,
    boundary_tolerance: float = 1.0e-6,
) -> bool:
    """Return whether a point is inside a polygon and not on its boundary."""

    for start, end in xy_closed_edges(polygon):
        if xy_point_on_segment(point, start, end, tolerance=boundary_tolerance):
            return False
    return xy_point_in_polygon(point, polygon)
