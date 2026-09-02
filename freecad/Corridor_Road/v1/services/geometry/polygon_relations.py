"""FreeCAD-independent polygon relation predicates for CorridorRoad v1."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from .segment_geometry import xy_point_on_segment, xy_segments_intersect
from .xy_primitives import xy_point, xy_point_in_triangle_strict


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


def xy_triangle_polygon_intersection_kind(
    triangle: Sequence[object],
    polygon: Sequence[object],
) -> str:
    """Classify the first legacy triangle/polygon intersection condition."""

    if len(triangle) < 3 or len(polygon) < 3:
        return ""
    triangle_points = [xy_point(value) for value in triangle[:3]]
    polygon_points = [xy_point(value) for value in polygon]
    for first_start, first_end in xy_closed_edges(triangle_points):
        for second_start, second_end in xy_closed_edges(polygon_points):
            if xy_segments_intersect(first_start, first_end, second_start, second_end):
                return "edge_crossing"
    centroid = (
        sum(point[0] for point in triangle_points) / 3.0,
        sum(point[1] for point in triangle_points) / 3.0,
    )
    if xy_point_in_polygon(centroid, polygon_points):
        return "centroid_inside"
    if any(xy_point_in_polygon(point, polygon_points) for point in triangle_points):
        return "triangle_vertex_inside"
    triangle_tuple = (triangle_points[0], triangle_points[1], triangle_points[2])
    if any(xy_point_in_triangle_strict(point, triangle_tuple) for point in polygon_points):
        return "polygon_vertex_inside_triangle"
    return ""


def xy_triangle_intersects_polygon(
    triangle: Sequence[object],
    polygon: Sequence[object],
) -> bool:
    """Return whether the triangle/polygon relation has any intersection kind."""

    return bool(xy_triangle_polygon_intersection_kind(triangle, polygon))


def xy_polygon_self_intersects(polygon: Sequence[object]) -> bool:
    """Return whether any non-adjacent polygon edges intersect or touch."""

    points = [xy_point(value) for value in polygon]
    edge_count = len(points)
    for index in range(edge_count):
        first_start = points[index]
        first_end = points[(index + 1) % edge_count]
        for other_index in range(index + 1, edge_count):
            if abs(index - other_index) <= 1:
                continue
            if index == 0 and other_index == edge_count - 1:
                continue
            second_start = points[other_index]
            second_end = points[(other_index + 1) % edge_count]
            if xy_segments_intersect(
                first_start,
                first_end,
                second_start,
                second_end,
            ):
                return True
    return False


def xy_polygon_boundaries_intersect(
    first: Sequence[object],
    second: Sequence[object],
) -> bool:
    """Return whether the closed boundaries of two polygons intersect or touch."""

    if len(first) < 2 or len(second) < 2:
        return False
    first_points = [xy_point(value) for value in first]
    second_points = [xy_point(value) for value in second]
    for first_start, first_end in xy_closed_edges(first_points):
        for second_start, second_end in xy_closed_edges(second_points):
            if xy_segments_intersect(
                first_start,
                first_end,
                second_start,
                second_end,
            ):
                return True
    return False
