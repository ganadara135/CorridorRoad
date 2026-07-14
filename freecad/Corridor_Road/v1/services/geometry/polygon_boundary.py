"""FreeCAD-independent source-preserving polygon boundary geometry."""

from __future__ import annotations

from collections.abc import Sequence
import math

from .polygon_relations import xy_point_in_polygon_strict, xy_polygon_self_intersects
from .segment_geometry import xy_segment_parameter_clamped, xyz_segment_intersection_point
from .xy_primitives import xy_distance, xy_polygon_signed_area


def xyz_point(value: object) -> tuple[float, float, float]:
    """Normalize a coordinate sequence to one XYZ tuple."""

    try:
        values = tuple(value or (0.0, 0.0, 0.0))
    except Exception:
        values = ()
    return (
        float(values[0]) if len(values) > 0 else 0.0,
        float(values[1]) if len(values) > 1 else 0.0,
        float(values[2]) if len(values) > 2 else 0.0,
    )


def xyz_exterior_convex_hull(
    polygons: Sequence[Sequence[object]],
) -> list[tuple[float, float, float]]:
    """Return the CCW exterior XY convex hull while retaining source Z values."""

    point_by_key: dict[tuple[float, float], tuple[float, float, float]] = {}
    for polygon in polygons or ():
        for value in polygon or ():
            point = xyz_point(value)
            key = (round(point[0], 6), round(point[1], 6))
            point_by_key.setdefault(key, point)
    if len(point_by_key) < 3:
        return []
    sorted_keys = sorted(point_by_key)

    def cross(
        origin: tuple[float, float],
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return (
            (first[0] - origin[0]) * (second[1] - origin[1])
            - (first[1] - origin[1]) * (second[0] - origin[0])
        )

    lower: list[tuple[float, float]] = []
    for key in sorted_keys:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], key) <= 1.0e-9:
            lower.pop()
        lower.append(key)
    upper: list[tuple[float, float]] = []
    for key in reversed(sorted_keys):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], key) <= 1.0e-9:
            upper.pop()
        upper.append(key)
    hull_keys = lower[:-1] + upper[:-1]
    hull = [point_by_key[key] for key in hull_keys if key in point_by_key]
    if len(hull) < 3 or abs(xy_polygon_signed_area(hull)) <= 1.0e-6:
        return []
    if xy_polygon_signed_area(hull) < 0.0:
        hull.reverse()
    return hull


def xyz_polygon_union_outer_boundary(
    polygons: Sequence[Sequence[tuple[float, float, float]]],
) -> list[tuple[float, float, float]]:
    """Return the largest ordered exterior ring from overlapping XYZ polygons."""

    kept_segments: list[
        tuple[tuple[float, float, float], tuple[float, float, float]]
    ] = []
    polygon_list = [list(polygon) for polygon in polygons]
    for polygon_index, polygon in enumerate(polygon_list):
        other_polygons = [
            other for index, other in enumerate(polygon_list) if index != polygon_index
        ]
        for start, end in _xyz_closed_edges(polygon):
            split_points = [start, end]
            for other in other_polygons:
                for other_start, other_end in _xyz_closed_edges(other):
                    intersection = xyz_segment_intersection_point(
                        start,
                        end,
                        other_start,
                        other_end,
                    )
                    if intersection is not None:
                        split_points.append(intersection)
            split_points = _sort_points_along_segment(
                start,
                end,
                _unique_xyz_points(split_points),
            )
            for first, second in zip(split_points, split_points[1:]):
                if xy_distance(first, second) <= 1.0e-6:
                    continue
                midpoint = (
                    (first[0] + second[0]) * 0.5,
                    (first[1] + second[1]) * 0.5,
                    (first[2] + second[2]) * 0.5,
                )
                if any(
                    xy_point_in_polygon_strict(
                        midpoint,
                        [(point[0], point[1]) for point in other],
                    )
                    for other in other_polygons
                ):
                    continue
                kept_segments.append((first, second))
    return xyz_ordered_outer_boundary_from_segments(kept_segments)


def xyz_ordered_outer_boundary_from_segments(
    segments: Sequence[
        tuple[tuple[float, float, float], tuple[float, float, float]]
    ],
) -> list[tuple[float, float, float]]:
    """Build the largest valid CCW ring from an unordered XYZ segment graph."""

    normalized_segments = [
        (start, end)
        for start, end in segments
        if xy_distance(start, end) > 1.0e-6
    ]
    if len(normalized_segments) < 3:
        return []
    point_by_key: dict[tuple[float, float], tuple[float, float, float]] = {}
    adjacency: dict[tuple[float, float], list[tuple[float, float]]] = {}
    edge_set: set[frozenset[tuple[float, float]]] = set()
    for start, end in normalized_segments:
        start_key = _xy_key(start)
        end_key = _xy_key(end)
        if start_key == end_key:
            continue
        point_by_key.setdefault(start_key, start)
        point_by_key.setdefault(end_key, end)
        edge_key = frozenset((start_key, end_key))
        if edge_key in edge_set:
            continue
        edge_set.add(edge_key)
        adjacency.setdefault(start_key, []).append(end_key)
        adjacency.setdefault(end_key, []).append(start_key)
    rings = _closed_boundary_rings_from_adjacency(adjacency, point_by_key)
    if not rings:
        return []
    return max(rings, key=lambda ring: abs(xy_polygon_signed_area(ring)))


def _closed_boundary_rings_from_adjacency(
    adjacency: dict[tuple[float, float], list[tuple[float, float]]],
    point_by_key: dict[tuple[float, float], tuple[float, float, float]],
) -> list[list[tuple[float, float, float]]]:
    unused_edges: set[frozenset[tuple[float, float]]] = set()
    for key, neighbors in adjacency.items():
        for neighbor in neighbors:
            unused_edges.add(frozenset((key, neighbor)))
    rings: list[list[tuple[float, float, float]]] = []
    while unused_edges:
        edge = next(iter(unused_edges))
        start_key, next_key = tuple(edge)
        ring_keys = [start_key]
        previous_key = start_key
        current_key = next_key
        guard = 0
        while guard < max(8, len(unused_edges) + len(adjacency) * 4):
            guard += 1
            unused_edges.discard(frozenset((previous_key, current_key)))
            ring_keys.append(current_key)
            if current_key == start_key:
                break
            candidates = [
                key
                for key in list(adjacency.get(current_key, []) or [])
                if key != previous_key
                and frozenset((current_key, key)) in unused_edges
            ]
            if not candidates:
                break
            current_point = point_by_key.get(current_key, (0.0, 0.0, 0.0))
            previous_point = point_by_key.get(previous_key, current_point)
            current_angle = math.atan2(
                current_point[1] - previous_point[1],
                current_point[0] - previous_point[0],
            )
            next_key = min(
                candidates,
                key=lambda key: _positive_angle_delta(
                    current_angle,
                    math.atan2(
                        point_by_key.get(key, current_point)[1] - current_point[1],
                        point_by_key.get(key, current_point)[0] - current_point[0],
                    ),
                ),
            )
            previous_key, current_key = current_key, next_key
        if len(ring_keys) >= 4 and ring_keys[-1] == start_key:
            unique_keys = ring_keys[:-1]
            ring = [
                point_by_key[key]
                for key in unique_keys
                if key in point_by_key
            ]
            if len(ring) >= 3 and not xy_polygon_self_intersects(ring):
                if xy_polygon_signed_area(ring) < 0.0:
                    ring.reverse()
                rings.append(ring)
    return rings


def _positive_angle_delta(current_angle: float, next_angle: float) -> float:
    delta = float(next_angle) - float(current_angle)
    while delta <= 0.0:
        delta += math.tau
    return delta


def _xy_key(point: tuple[float, float, float]) -> tuple[float, float]:
    return (round(float(point[0]), 6), round(float(point[1]), 6))


def _xyz_closed_edges(
    points: Sequence[tuple[float, float, float]],
) -> list[
    tuple[tuple[float, float, float], tuple[float, float, float]]
]:
    return [
        (points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    ]


def _unique_xyz_points(
    points: Sequence[tuple[float, float, float]],
    *,
    tolerance: float = 1.0e-6,
) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    for point in points:
        if any(_xyz_distance(point, existing) <= tolerance for existing in output):
            continue
        output.append(point)
    return output


def _xyz_distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return math.sqrt(
        (float(first[0]) - float(second[0])) ** 2
        + (float(first[1]) - float(second[1])) ** 2
        + (float(first[2]) - float(second[2])) ** 2
    )


def _sort_points_along_segment(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    points: Sequence[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    return sorted(
        points,
        key=lambda point: xy_segment_parameter_clamped(point, start, end),
    )
