"""FreeCAD-independent XY segment primitives for CorridorRoad v1."""

from __future__ import annotations

import math

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


def xy_segments_intersect(
    first_start: object,
    first_end: object,
    second_start: object,
    second_end: object,
) -> bool:
    """Return whether two XY segments cross, touch, or overlap collinearly."""

    a1 = xy_point(first_start)
    a2 = xy_point(first_end)
    b1 = xy_point(second_start)
    b2 = xy_point(second_end)
    first_orientation = _orientation(a1, a2, b1)
    second_orientation = _orientation(a1, a2, b2)
    third_orientation = _orientation(b1, b2, a1)
    fourth_orientation = _orientation(b1, b2, a2)
    if first_orientation * second_orientation < 0.0 and third_orientation * fourth_orientation < 0.0:
        return True
    if abs(first_orientation) <= 1.0e-9 and _on_segment(a1, b1, a2):
        return True
    if abs(second_orientation) <= 1.0e-9 and _on_segment(a1, b2, a2):
        return True
    if abs(third_orientation) <= 1.0e-9 and _on_segment(b1, a1, b2):
        return True
    if abs(fourth_orientation) <= 1.0e-9 and _on_segment(b1, a2, b2):
        return True
    return False


def xy_segments_cross_strict(
    first_start: object,
    first_end: object,
    second_start: object,
    second_end: object,
) -> bool:
    """Return whether segment interiors cross, excluding touch and collinear overlap."""

    a1 = xy_point(first_start)
    a2 = xy_point(first_end)
    b1 = xy_point(second_start)
    b2 = xy_point(second_end)
    first_orientation = _orientation(a1, a2, b1)
    second_orientation = _orientation(a1, a2, b2)
    third_orientation = _orientation(b1, b2, a1)
    fourth_orientation = _orientation(b1, b2, a2)
    return (
        first_orientation * second_orientation < -1.0e-12
        and third_orientation * fourth_orientation < -1.0e-12
    )


def xy_point_segment_distance_with_ratio(
    point: object,
    segment_start: object,
    segment_end: object,
) -> tuple[float, float]:
    """Return distance to a finite segment and the unclamped projection ratio."""

    px, py = xy_point(point)
    x1, y1 = xy_point(segment_start)
    x2, y2 = xy_point(segment_end)
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1.0e-18:
        return math.hypot(px - x1, py - y1), 0.0
    ratio = ((px - x1) * dx + (py - y1) * dy) / length_sq
    clamped = min(max(ratio, 0.0), 1.0)
    closest_x = x1 + dx * clamped
    closest_y = y1 + dy * clamped
    return math.hypot(px - closest_x, py - closest_y), ratio


def xy_segment_projection_ratio(point: object, segment_start: object, segment_end: object) -> float:
    """Return the unclamped XY projection ratio on a segment line."""

    return xy_point_segment_distance_with_ratio(point, segment_start, segment_end)[1]


def xy_segment_parameter_clamped(
    point: object,
    start: object,
    end: object,
) -> float:
    """Return the XY projection parameter clamped to one finite segment."""

    px, py = xy_point(point)
    sx, sy = xy_point(start)
    ex, ey = xy_point(end)
    dx = ex - sx
    dy = ey - sy
    denominator = dx * dx + dy * dy
    if denominator <= 1.0e-12:
        return 0.0
    ratio = ((px - sx) * dx + (py - sy) * dy) / denominator
    return max(0.0, min(1.0, ratio))


def xyz_segment_intersection_point(
    first_start: tuple[float, float, float],
    first_end: tuple[float, float, float],
    second_start: tuple[float, float, float],
    second_end: tuple[float, float, float],
) -> tuple[float, float, float] | None:
    """Return a finite XY segment intersection with averaged interpolated Z."""

    x1, y1 = float(first_start[0]), float(first_start[1])
    x2, y2 = float(first_end[0]), float(first_end[1])
    x3, y3 = float(second_start[0]), float(second_start[1])
    x4, y4 = float(second_end[0]), float(second_end[1])
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) <= 1.0e-9:
        return None
    first_determinant = x1 * y2 - y1 * x2
    second_determinant = x3 * y4 - y3 * x4
    px = (
        first_determinant * (x3 - x4)
        - (x1 - x2) * second_determinant
    ) / denominator
    py = (
        first_determinant * (y3 - y4)
        - (y1 - y2) * second_determinant
    ) / denominator
    if not xy_point_on_segment((px, py), (x1, y1), (x2, y2)):
        return None
    if not xy_point_on_segment((px, py), (x3, y3), (x4, y4)):
        return None
    first_ratio = xy_segment_parameter_clamped((px, py), (x1, y1), (x2, y2))
    second_ratio = xy_segment_parameter_clamped((px, py), (x3, y3), (x4, y4))
    first_z = float(first_start[2]) + (
        float(first_end[2]) - float(first_start[2])
    ) * first_ratio
    second_z = float(second_start[2]) + (
        float(second_end[2]) - float(second_start[2])
    ) * second_ratio
    return (px, py, (first_z + second_z) * 0.5)


def xy_segment_distance(
    first_start: object,
    first_end: object,
    second_start: object,
    second_end: object,
) -> float:
    """Return the minimum distance between two finite XY segments."""

    if xy_segments_intersect(first_start, first_end, second_start, second_end):
        return 0.0
    return min(
        xy_point_segment_distance_with_ratio(first_start, second_start, second_end)[0],
        xy_point_segment_distance_with_ratio(first_end, second_start, second_end)[0],
        xy_point_segment_distance_with_ratio(second_start, first_start, first_end)[0],
        xy_point_segment_distance_with_ratio(second_end, first_start, first_end)[0],
    )


def _orientation(
    first: tuple[float, float],
    second: tuple[float, float],
    third: tuple[float, float],
) -> float:
    return (
        (second[1] - first[1]) * (third[0] - second[0])
        - (second[0] - first[0]) * (third[1] - second[1])
    )


def _on_segment(
    first: tuple[float, float],
    point: tuple[float, float],
    second: tuple[float, float],
) -> bool:
    return (
        min(first[0], second[0]) - 1.0e-9 <= point[0] <= max(first[0], second[0]) + 1.0e-9
        and min(first[1], second[1]) - 1.0e-9 <= point[1] <= max(first[1], second[1]) + 1.0e-9
    )


def clip_polyline_points_to_anchor_window(
    points: list[tuple[float, float, float]],
    anchor: tuple[float, float, float],
    *,
    half_length: float,
) -> list[tuple[float, float, float]]:
    """Clip a two-point 3D segment to a length window around an anchor."""

    if len(points) != 2:
        return points
    start, end = points
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    dz = float(end[2]) - float(start[2])
    length = (dx * dx + dy * dy + dz * dz) ** 0.5
    if length <= 1.0e-9:
        return points
    anchor_vector = (
        float(anchor[0]) - float(start[0]),
        float(anchor[1]) - float(start[1]),
        float(anchor[2]) - float(start[2]),
    )
    center_distance = sum(a * b for a, b in zip(anchor_vector, (dx, dy, dz))) / length
    center_distance = max(0.0, min(length, center_distance))
    start_distance = max(0.0, center_distance - float(half_length or 0.0))
    end_distance = min(length, center_distance + float(half_length or 0.0))
    if end_distance - start_distance <= 1.0e-9:
        return points
    unit = (dx / length, dy / length, dz / length)
    return [
        tuple(float(start[index]) + unit[index] * start_distance for index in range(3)),
        tuple(float(start[index]) + unit[index] * end_distance for index in range(3)),
    ]


def clip_segment_to_anchor_box(
    points: list[tuple[float, float, float]],
    anchor: tuple[float, float, float],
    *,
    half_extent: float,
) -> list[tuple[float, float, float]]:
    """Clip a two-point 3D segment to an axis-aligned XY box."""

    if len(points) != 2:
        return points
    start, end = points
    xmin = float(anchor[0]) - float(half_extent or 0.0)
    xmax = float(anchor[0]) + float(half_extent or 0.0)
    ymin = float(anchor[1]) - float(half_extent or 0.0)
    ymax = float(anchor[1]) + float(half_extent or 0.0)
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    dz = float(end[2]) - float(start[2])
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, float(start[0]) - xmin),
        (dx, xmax - float(start[0])),
        (-dy, float(start[1]) - ymin),
        (dy, ymax - float(start[1])),
    ):
        if abs(p) <= 1.0e-12:
            if q < 0.0:
                return []
            continue
        ratio = q / p
        if p < 0.0:
            if ratio > t1:
                return []
            t0 = max(t0, ratio)
        else:
            if ratio < t0:
                return []
            t1 = min(t1, ratio)
    if t1 - t0 <= 1.0e-12:
        return []
    return [
        (
            float(start[0]) + dx * t0,
            float(start[1]) + dy * t0,
            float(start[2]) + dz * t0,
        ),
        (
            float(start[0]) + dx * t1,
            float(start[1]) + dy * t1,
            float(start[2]) + dz * t1,
        ),
    ]
