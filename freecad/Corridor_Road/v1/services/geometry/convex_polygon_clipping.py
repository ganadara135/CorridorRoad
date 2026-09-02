"""Convex polygon clipping primitives for CorridorRoad v1."""

from __future__ import annotations

import math

from .xy_primitives import xy_polygon_signed_area


def xy_polygon_is_convex(points: list[tuple[float, float]]) -> bool:
    """Return whether an XY polygon has one consistent non-zero turn direction."""

    if len(points) < 3:
        return False
    sign = 0
    for index in range(len(points)):
        first = points[index]
        second = points[(index + 1) % len(points)]
        third = points[(index + 2) % len(points)]
        cross = (
            ((second[0] - first[0]) * (third[1] - second[1]))
            - ((second[1] - first[1]) * (third[0] - second[0]))
        )
        if abs(cross) <= 1.0e-9:
            continue
        current_sign = 1 if cross > 0.0 else -1
        if sign and current_sign != sign:
            return False
        sign = current_sign
    return bool(sign)


def intersect_payload_polygon_with_convex_polygon(
    source_polygon: list[dict[str, object]],
    clip_polygon: list[tuple[float, float]],
) -> list[dict[str, object]]:
    """Clip an XYZ/source payload polygon to one convex XY polygon."""

    if len(source_polygon) < 3 or len(clip_polygon) < 3 or not xy_polygon_is_convex(clip_polygon):
        return []
    orientation = 1.0 if xy_polygon_signed_area(clip_polygon) >= 0.0 else -1.0
    output = dedupe_xy_payload_points(source_polygon)
    for edge_start, edge_end in _closed_edges(clip_polygon):
        inside, _outside = _split_polygon_by_oriented_halfplane(
            output,
            edge_start,
            edge_end,
            orientation=orientation,
        )
        output = dedupe_xy_payload_points(inside)
        if len(output) < 3:
            return []
    return output


def subtract_convex_polygon_from_payload_polygon(
    source_polygon: list[dict[str, object]],
    exclusion_polygon: list[tuple[float, float]],
) -> list[list[dict[str, object]]]:
    """Return source payload fragments outside one convex exclusion polygon."""

    if len(source_polygon) < 3 or len(exclusion_polygon) < 3 or not xy_polygon_is_convex(exclusion_polygon):
        return []
    orientation = 1.0 if xy_polygon_signed_area(exclusion_polygon) >= 0.0 else -1.0
    remaining_inside = dedupe_xy_payload_points(source_polygon)
    outside_fragments: list[list[dict[str, object]]] = []
    for edge_start, edge_end in _closed_edges(exclusion_polygon):
        inside_fragment, outside_fragment = _split_polygon_by_oriented_halfplane(
            remaining_inside,
            edge_start,
            edge_end,
            orientation=orientation,
        )
        outside_fragment = dedupe_xy_payload_points(outside_fragment)
        if len(outside_fragment) >= 3 and abs(_payload_polygon_area(outside_fragment)) > 1.0e-9:
            outside_fragments.append(outside_fragment)
        remaining_inside = dedupe_xy_payload_points(inside_fragment)
        if len(remaining_inside) < 3:
            break
    return outside_fragments


def dedupe_xy_payload_points(points: list[dict[str, object]]) -> list[dict[str, object]]:
    """Remove consecutive and closing duplicate XY payload points."""

    output: list[dict[str, object]] = []
    for point in list(points or []):
        if output:
            previous = output[-1]
            if (
                abs(float(previous["x"]) - float(point["x"])) <= 1.0e-9
                and abs(float(previous["y"]) - float(point["y"])) <= 1.0e-9
            ):
                continue
        output.append(point)
    if len(output) > 1:
        first = output[0]
        last = output[-1]
        if (
            abs(float(first["x"]) - float(last["x"])) <= 1.0e-9
            and abs(float(first["y"]) - float(last["y"])) <= 1.0e-9
        ):
            output.pop()
    return output


def _split_polygon_by_oriented_halfplane(
    polygon: list[dict[str, object]],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
    *,
    orientation: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if len(polygon) < 3:
        return [], []
    inside: list[dict[str, object]] = []
    outside: list[dict[str, object]] = []
    for index, current in enumerate(polygon):
        previous = polygon[index - 1]
        previous_inside = _point_in_oriented_halfplane(
            previous,
            edge_start,
            edge_end,
            orientation=orientation,
        )
        current_inside = _point_in_oriented_halfplane(
            current,
            edge_start,
            edge_end,
            orientation=orientation,
        )
        if current_inside:
            if not previous_inside:
                intersection = _halfplane_segment_intersection(previous, current, edge_start, edge_end)
                if intersection:
                    inside.append(intersection)
                    outside.append(intersection)
            inside.append(current)
        else:
            if previous_inside:
                intersection = _halfplane_segment_intersection(previous, current, edge_start, edge_end)
                if intersection:
                    inside.append(intersection)
                    outside.append(intersection)
            outside.append(current)
    return dedupe_xy_payload_points(inside), dedupe_xy_payload_points(outside)


def _point_in_oriented_halfplane(
    point: dict[str, object],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
    *,
    orientation: float,
) -> bool:
    cross = (
        (float(edge_end[0]) - float(edge_start[0])) * (float(point["y"]) - float(edge_start[1]))
        - (float(edge_end[1]) - float(edge_start[1])) * (float(point["x"]) - float(edge_start[0]))
    )
    return cross * float(orientation or 1.0) >= -1.0e-9


def _halfplane_segment_intersection(
    first: dict[str, object],
    second: dict[str, object],
    edge_start: tuple[float, float],
    edge_end: tuple[float, float],
) -> dict[str, object] | None:
    x1 = float(first["x"])
    y1 = float(first["y"])
    x2 = float(second["x"])
    y2 = float(second["y"])
    x3 = float(edge_start[0])
    y3 = float(edge_start[1])
    x4 = float(edge_end[0])
    y4 = float(edge_end[1])
    denominator = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
    if abs(denominator) <= 1.0e-12:
        return None
    px = (((x1 * y2 - y1 * x2) * (x3 - x4)) - ((x1 - x2) * (x3 * y4 - y3 * x4))) / denominator
    py = (((x1 * y2 - y1 * x2) * (y3 - y4)) - ((y1 - y2) * (x3 * y4 - y3 * x4))) / denominator
    segment_length = math.hypot(x2 - x1, y2 - y1)
    ratio = 0.0 if segment_length <= 1.0e-12 else math.hypot(px - x1, py - y1) / segment_length
    ratio = max(0.0, min(1.0, ratio))
    z = float(first["z"]) + (float(second["z"]) - float(first["z"])) * ratio
    return {
        "x": px,
        "y": py,
        "z": z,
        "source": f"{first.get('source', '')}|{second.get('source', '')}:intersection",
    }


def _closed_edges(points: list[tuple[float, float]]):
    return [(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]


def _payload_polygon_area(points: list[dict[str, object]]) -> float:
    return xy_polygon_signed_area([(float(point["x"]), float(point["y"])) for point in points])
