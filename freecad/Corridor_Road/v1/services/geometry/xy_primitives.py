"""FreeCAD-independent XY geometry primitives for CorridorRoad v1."""

from __future__ import annotations

import math


def xy_point(value: object) -> tuple[float, float]:
    """Normalize an object with x/y fields or a coordinate sequence to one XY pair."""

    if hasattr(value, "x") or hasattr(value, "y"):
        return (
            float(getattr(value, "x", 0.0) or 0.0),
            float(getattr(value, "y", 0.0) or 0.0),
        )
    try:
        sequence = tuple(value or ())
    except Exception:
        sequence = ()
    return (
        float(sequence[0]) if len(sequence) > 0 else 0.0,
        float(sequence[1]) if len(sequence) > 1 else 0.0,
    )


def xy_distance(first: object, second: object) -> float:
    """Return Euclidean distance between two XY-compatible values."""

    ax, ay = xy_point(first)
    bx, by = xy_point(second)
    return math.hypot(ax - bx, ay - by)


def xy_triangle_signed_area(first: object, second: object, third: object) -> float:
    """Return the signed XY area of one triangle."""

    ax, ay = xy_point(first)
    bx, by = xy_point(second)
    cx, cy = xy_point(third)
    return 0.5 * ((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))


def xy_point_in_triangle_strict(
    point: object,
    triangle: tuple[object, object, object],
    *,
    tolerance: float = 1.0e-9,
) -> bool:
    """Return whether a point lies strictly inside a non-degenerate XY triangle."""

    px, py = xy_point(point)
    a = xy_point(triangle[0])
    b = xy_point(triangle[1])
    c = xy_point(triangle[2])
    denominator = ((b[1] - c[1]) * (a[0] - c[0])) + ((c[0] - b[0]) * (a[1] - c[1]))
    if abs(denominator) <= 1.0e-12:
        return False
    first = (((b[1] - c[1]) * (px - c[0])) + ((c[0] - b[0]) * (py - c[1]))) / denominator
    second = (((c[1] - a[1]) * (px - c[0])) + ((a[0] - c[0]) * (py - c[1]))) / denominator
    third = 1.0 - first - second
    active_tolerance = max(float(tolerance), 0.0)
    return first > active_tolerance and second > active_tolerance and third > active_tolerance


def xy_polygon_signed_area(vertices: list[object] | tuple[object, ...]) -> float:
    """Return signed XY area for an open or closed polygon vertex sequence."""

    points = [xy_point(vertex) for vertex in list(vertices or [])]
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, current in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += current[0] * nxt[1]
        area -= nxt[0] * current[1]
    return area * 0.5
