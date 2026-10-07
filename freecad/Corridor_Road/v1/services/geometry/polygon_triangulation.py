"""Deterministic polygon triangulation and quality metrics for CorridorRoad v1."""

from __future__ import annotations

import math

from .xy_primitives import (
    xy_distance,
    xy_point,
    xy_point_in_triangle_strict,
    xy_polygon_signed_area,
    xy_triangle_signed_area,
)


def ear_clip_triangulation_indices(
    vertices: list[object],
    *,
    final_triangle_area_tolerance: float = 1.0e-6,
) -> list[tuple[int, int, int]]:
    """Triangulate one simple XY polygon into deterministic source vertex indices."""

    if len(vertices) < 3:
        return []
    polygon_area = xy_polygon_signed_area(vertices)
    if abs(polygon_area) <= 1.0e-9:
        return []
    remaining = list(range(len(vertices)))
    if polygon_area < 0.0:
        remaining.reverse()
    triangles: list[tuple[int, int, int]] = []
    guard = 0
    while len(remaining) > 3 and guard < len(vertices) * len(vertices):
        guard += 1
        ear_index = None
        for index in range(len(remaining)):
            prev_index = remaining[(index - 1) % len(remaining)]
            current_index = remaining[index]
            next_index = remaining[(index + 1) % len(remaining)]
            if not _is_ear(vertices, remaining, prev_index, current_index, next_index):
                continue
            ear_index = index
            triangles.append((prev_index, current_index, next_index))
            break
        if ear_index is None:
            remainder = [vertices[index] for index in remaining]
            if triangles and abs(xy_polygon_signed_area(remainder)) <= 1.0e-6:
                break
            return []
        remaining.pop(ear_index)
    if len(remaining) == 3:
        first, second, third = remaining
        if abs(xy_triangle_signed_area(vertices[first], vertices[second], vertices[third])) > max(
            float(final_triangle_area_tolerance),
            0.0,
        ):
            triangles.append((first, second, third))
    return triangles


def delaunay_flip_triangulation_indices(
    vertices: list[object],
    triangles: list[tuple[int, int, int]],
    *,
    incircle_tolerance: float = 1.0e-9,
) -> list[tuple[int, int, int]]:
    """Improve a triangulation of a simple XY polygon by flipping interior diagonals.

    The triangles are counter-clockwise index triples, as `ear_clip_triangulation_indices` returns
    them. An interior edge is flipped when the opposite vertex of its neighbour lies inside the
    circumcircle (the Delaunay criterion, which maximises the smallest angle) and the quadrilateral
    is strictly convex, so the new diagonal stays inside the polygon. No vertex is added and no
    boundary edge changes, so the polygon, its area and its triangle count are kept. Edges are
    visited in sorted order, so the result is deterministic.
    """

    points = [xy_point(vertex) for vertex in vertices]
    result = [tuple(triangle) for triangle in triangles]
    if len(result) < 2:
        return result
    for _ in range(max(len(result) * len(result), 1) * 4):
        owners: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        for triangle_index, (first, second, third) in enumerate(result):
            for start, end in ((first, second), (second, third), (third, first)):
                owners.setdefault((min(start, end), max(start, end)), []).append((triangle_index, start, end))
        flipped = False
        for key in sorted(owners):
            pair = owners[key]
            if len(pair) != 2:
                continue
            (first_index, a, b), (second_index, _other_start, _other_end) = pair
            first_triangle = result[first_index]
            second_triangle = result[second_index]
            p = next(vertex for vertex in first_triangle if vertex not in (a, b))
            q = next(vertex for vertex in second_triangle if vertex not in (a, b))
            if _incircle_determinant(points[a], points[b], points[p], points[q]) <= incircle_tolerance:
                continue
            new_first = (a, q, p)
            new_second = (q, b, p)
            if (
                xy_triangle_signed_area(points[a], points[q], points[p]) <= 1.0e-9
                or xy_triangle_signed_area(points[q], points[b], points[p]) <= 1.0e-9
            ):
                continue
            result[first_index] = new_first
            result[second_index] = new_second
            flipped = True
            break
        if not flipped:
            break
    return result


def _incircle_determinant(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]) -> float:
    """Return a positive value when d lies inside the circle through the counter-clockwise a, b, c."""

    adx, ady = a[0] - d[0], a[1] - d[1]
    bdx, bdy = b[0] - d[0], b[1] - d[1]
    cdx, cdy = c[0] - d[0], c[1] - d[1]
    return (
        (adx * adx + ady * ady) * (bdx * cdy - cdx * bdy)
        - (bdx * bdx + bdy * bdy) * (adx * cdy - cdx * ady)
        + (cdx * cdx + cdy * cdy) * (adx * bdy - bdx * ady)
    )


def xy_triangle_quality_ratio(first: object, second: object, third: object) -> float:
    """Return the normalized 0..1 XY triangle quality ratio."""

    points = [xy_point(first), xy_point(second), xy_point(third)]
    edge_lengths = [
        xy_distance(points[0], points[1]),
        xy_distance(points[1], points[2]),
        xy_distance(points[2], points[0]),
    ]
    denominator = sum(length * length for length in edge_lengths)
    if denominator <= 1.0e-12:
        return 0.0
    area = abs(xy_triangle_signed_area(first, second, third))
    return (4.0 * math.sqrt(3.0) * area) / denominator


def triangulate_simple_polygon_points(
    points: list[tuple[float, float]],
) -> list[list[tuple[float, float]]]:
    """Return deterministic point triangles for a simple XY polygon."""

    normalized = [xy_point(point) for point in list(points or [])]
    return [
        [normalized[first], normalized[second], normalized[third]]
        for first, second, third in ear_clip_triangulation_indices(normalized)
    ]


def _is_ear(
    vertices: list[object],
    remaining: list[int],
    prev_index: int,
    current_index: int,
    next_index: int,
) -> bool:
    prev_vertex = vertices[prev_index]
    current_vertex = vertices[current_index]
    next_vertex = vertices[next_index]
    if xy_triangle_signed_area(prev_vertex, current_vertex, next_vertex) <= 1.0e-9:
        return False
    triangle = (
        xy_point(prev_vertex),
        xy_point(current_vertex),
        xy_point(next_vertex),
    )
    for candidate_index in remaining:
        if candidate_index in {prev_index, current_index, next_index}:
            continue
        if xy_point_in_triangle_strict(vertices[candidate_index], triangle):
            return False
    return True
