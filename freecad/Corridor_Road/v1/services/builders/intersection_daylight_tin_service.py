"""Pure Intersection/daylight TIN suppression and overlap clipping builders."""

from __future__ import annotations

import math
from dataclasses import replace

from ...models.result.tin_surface import TINQualityRow


def _suppress_daylight_triangles_inside_intersection_surface_footprint(surface, intersection_surface):
    if surface is None or intersection_surface is None:
        return surface
    from ...models.result.tin_surface import TINQualityRow

    surface_triangles = list(getattr(surface, "triangle_rows", []) or [])
    if not surface_triangles:
        return surface
    reference_triangles = tin_surface_reference_triangles(intersection_surface)
    if not reference_triangles:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    tested_count = 0
    suppressed_count = 0
    for triangle in surface_triangles:
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        tested_count += 1
        if _tin_triangle_has_sample_inside_reference_footprint(vertices, reference_triangles):
            suppressed_count += 1
            continue
        kept_triangles.append(triangle)
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_footprint_suppress_status",
            "intersection_footprint_suppress_method",
            "intersection_footprint_suppress_tested_triangle_count",
            "intersection_footprint_suppress_suppressed_triangle_count",
            "intersection_footprint_suppress_kept_triangle_count",
            "intersection_footprint_suppress_reference_surface_id",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    reference_surface_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_status", "intersection_footprint_suppress_status", "ready"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_method", "intersection_footprint_suppress_method", "sample_xy_footprint"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_tested_triangle_count", "intersection_footprint_suppress_tested_triangle_count", int(tested_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_suppressed_triangle_count", "intersection_footprint_suppress_suppressed_triangle_count", int(suppressed_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_kept_triangle_count", "intersection_footprint_suppress_kept_triangle_count", len(kept_triangles), "count"),
            TINQualityRow(f"{surface_id}:intersection_footprint_suppress_reference_surface_id", "intersection_footprint_suppress_reference_surface_id", reference_surface_id),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    if reference_surface_id and reference_surface_id not in void_refs:
        void_refs.append(reference_surface_id)
    return replace(surface, triangle_rows=kept_triangles, quality_rows=quality_rows, void_refs=void_refs)


def _tin_triangle_has_sample_inside_reference_footprint(vertices, reference_triangles) -> bool:
    for sample_x, sample_y, _sample_z in _tin_triangle_height_sample_points(vertices):
        if tin_surface_z_at_xy_from_reference_triangles(reference_triangles, sample_x, sample_y) is not None:
            return True
    return False


def _suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint(surface, intersection_slope_face_surface):
    if surface is None:
        return surface
    reference_triangles = tin_surface_reference_triangles(intersection_slope_face_surface) if intersection_slope_face_surface is not None else []
    if not reference_triangles:
        return _attach_daylight_slope_loop_suppression_quality(
            surface,
            status="skipped",
            method="ready_loop_footprint",
            reference_surface_id=str(getattr(intersection_slope_face_surface, "surface_id", "") or ""),
            ready_loop_count=0,
            tested_count=0,
            suppressed_count=0,
            kept_count=len(list(getattr(surface, "triangle_rows", []) or [])),
            reference_triangle_count=0,
        )
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    tested_count = 0
    suppressed_count = 0
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        tested_count += 1
        if tin_triangle_xy_overlaps_reference_triangles(vertices, reference_triangles):
            suppressed_count += 1
            continue
        kept_triangles.append(triangle)
    updated = _attach_daylight_slope_loop_suppression_quality(
        surface,
        status="ready",
        method="ready_loop_footprint_sample_xy",
        reference_surface_id=str(getattr(intersection_slope_face_surface, "surface_id", "") or ""),
        ready_loop_count=len(list(getattr(intersection_slope_face_surface, "boundary_refs", []) or [])),
        tested_count=tested_count,
        suppressed_count=suppressed_count,
        kept_count=len(kept_triangles),
        reference_triangle_count=len(reference_triangles),
    )
    void_refs = list(getattr(updated, "void_refs", []) or [])
    reference_id = str(getattr(intersection_slope_face_surface, "surface_id", "") or "")
    if suppressed_count and reference_id and reference_id not in void_refs:
        void_refs.append(reference_id)
    return replace(updated, triangle_rows=kept_triangles, void_refs=void_refs)


def _attach_daylight_slope_loop_suppression_quality(
    surface,
    *,
    status: str,
    method: str,
    reference_surface_id: str,
    ready_loop_count: int,
    tested_count: int,
    suppressed_count: int,
    kept_count: int,
    reference_triangle_count: int,
):
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_slope_loop_suppress_status",
            "intersection_slope_loop_suppress_method",
            "intersection_slope_loop_suppress_reference_surface_id",
            "intersection_slope_loop_suppress_ready_loop_count",
            "intersection_slope_loop_suppress_tested_triangle_count",
            "intersection_slope_loop_suppress_suppressed_triangle_count",
            "intersection_slope_loop_suppress_kept_triangle_count",
            "intersection_slope_loop_suppress_reference_triangle_count",
        }
    ]
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_status", "intersection_slope_loop_suppress_status", str(status or "")),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_method", "intersection_slope_loop_suppress_method", str(method or "")),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_reference_surface_id", "intersection_slope_loop_suppress_reference_surface_id", str(reference_surface_id or "")),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_ready_loop_count", "intersection_slope_loop_suppress_ready_loop_count", int(ready_loop_count or 0), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_tested_triangle_count", "intersection_slope_loop_suppress_tested_triangle_count", int(tested_count or 0), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_suppressed_triangle_count", "intersection_slope_loop_suppress_suppressed_triangle_count", int(suppressed_count or 0), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_kept_triangle_count", "intersection_slope_loop_suppress_kept_triangle_count", int(kept_count or 0), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_loop_suppress_reference_triangle_count", "intersection_slope_loop_suppress_reference_triangle_count", int(reference_triangle_count or 0), "count"),
        ]
    )
    return replace(surface, quality_rows=quality_rows)


def _suppress_daylight_triangles_above_intersection_surface(surface, intersection_surface, *, tolerance: float = 0.05):
    if surface is None or intersection_surface is None:
        return surface
    from ...models.result.tin_surface import TINQualityRow

    surface_triangles = list(getattr(surface, "triangle_rows", []) or [])
    if not surface_triangles:
        return surface
    reference_triangles = tin_surface_reference_triangles(intersection_surface)
    if not reference_triangles:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    suppressed_count = 0
    tested_count = 0
    for triangle in surface_triangles:
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        centroid_x = sum(float(getattr(vertex, "x", 0.0) or 0.0) for vertex in vertices) / 3.0
        centroid_y = sum(float(getattr(vertex, "y", 0.0) or 0.0) for vertex in vertices) / 3.0
        centroid_z = sum(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices) / 3.0
        reference_z = tin_surface_z_at_xy_from_reference_triangles(reference_triangles, centroid_x, centroid_y)
        if reference_z is None:
            kept_triangles.append(triangle)
            continue
        tested_count += 1
        if centroid_z >= float(reference_z) - float(tolerance or 0.0):
            suppressed_count += 1
            continue
        kept_triangles.append(triangle)
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_height_clip_status",
            "intersection_height_clip_tolerance",
            "intersection_height_clip_tested_triangle_count",
            "intersection_height_clip_suppressed_triangle_count",
            "intersection_height_clip_kept_triangle_count",
            "intersection_height_clip_reference_surface_id",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    reference_surface_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_height_clip_status", "intersection_height_clip_status", "ready"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_tolerance", "intersection_height_clip_tolerance", float(tolerance or 0.0), "m"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_tested_triangle_count", "intersection_height_clip_tested_triangle_count", int(tested_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_suppressed_triangle_count", "intersection_height_clip_suppressed_triangle_count", int(suppressed_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_kept_triangle_count", "intersection_height_clip_kept_triangle_count", len(kept_triangles), "count"),
            TINQualityRow(f"{surface_id}:intersection_height_clip_reference_surface_id", "intersection_height_clip_reference_surface_id", reference_surface_id),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    if reference_surface_id and reference_surface_id not in void_refs:
        void_refs.append(reference_surface_id)
    if suppressed_count <= 0 and tested_count <= 0:
        return replace(surface, quality_rows=quality_rows, void_refs=void_refs)
    return replace(surface, triangle_rows=kept_triangles, quality_rows=quality_rows, void_refs=void_refs)


def _trim_daylight_triangles_above_intersection_surface_by_intersection_lines(surface, intersection_surface, *, tolerance: float = 0.05):
    if surface is None or intersection_surface is None:
        return surface
    from ...models.result.tin_surface import TINQualityRow

    surface_triangles = list(getattr(surface, "triangle_rows", []) or [])
    if not surface_triangles:
        return surface
    intersection_triangles = tin_surface_reference_triangles(intersection_surface)
    if not intersection_triangles:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    kept_triangles = []
    removed_count = 0
    intersecting_count = 0
    line_count = 0
    for triangle in surface_triangles:
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        if not _daylight_triangle_has_intersection_line_with_surface(vertices, intersection_triangles):
            kept_triangles.append(triangle)
            continue
        intersecting_count += 1
        line_count += 1
        if _tin_triangle_has_sample_above_reference_surface(vertices, intersection_triangles, tolerance=tolerance):
            removed_count += 1
            continue
        kept_triangles.append(triangle)
    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_slope_trim_status",
            "intersection_slope_trim_method",
            "intersection_slope_trim_tolerance",
            "intersection_slope_trim_intersecting_triangle_count",
            "intersection_slope_trim_removed_triangle_count",
            "intersection_slope_trim_kept_triangle_count",
            "intersection_slope_trim_intersection_line_count",
            "intersection_slope_trim_reference_surface_id",
        }
    ]
    surface_id = str(getattr(surface, "surface_id", "") or "daylight_surface")
    reference_id = str(getattr(intersection_surface, "surface_id", "") or "intersection_surface")
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_slope_trim_status", "intersection_slope_trim_status", "ready"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_method", "intersection_slope_trim_method", "coarse_remove_intersecting_above_triangles"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_tolerance", "intersection_slope_trim_tolerance", float(tolerance or 0.0), "m"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_intersecting_triangle_count", "intersection_slope_trim_intersecting_triangle_count", int(intersecting_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_removed_triangle_count", "intersection_slope_trim_removed_triangle_count", int(removed_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_kept_triangle_count", "intersection_slope_trim_kept_triangle_count", len(kept_triangles), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_intersection_line_count", "intersection_slope_trim_intersection_line_count", int(line_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_slope_trim_reference_surface_id", "intersection_slope_trim_reference_surface_id", reference_id),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    if reference_id and reference_id not in void_refs:
        void_refs.append(reference_id)
    return replace(surface, triangle_rows=kept_triangles, quality_rows=quality_rows, void_refs=void_refs)


def _daylight_triangle_has_intersection_line_with_surface(daylight_vertices, intersection_triangles) -> bool:
    daylight_box = triangle_xyz_bbox(daylight_vertices)
    for intersection_triangle in list(intersection_triangles or []):
        if not bbox3d_overlaps(daylight_box, triangle_xyz_bbox(intersection_triangle), tolerance=0.25):
            continue
        segment = triangle_triangle_intersection_segment(daylight_vertices, intersection_triangle)
        if segment is None:
            continue
        if xyz_distance(segment[0], segment[1]) > 1.0e-7:
            return True
    return False


def _tin_triangle_has_sample_above_reference_surface(vertices, reference_triangles, *, tolerance: float = 0.05) -> bool:
    for sample_x, sample_y, sample_z in _tin_triangle_height_sample_points(vertices):
        reference_z = tin_surface_z_at_xy_from_reference_triangles(reference_triangles, sample_x, sample_y)
        if reference_z is None:
            continue
        if float(sample_z) > float(reference_z) + float(tolerance or 0.0):
            return True
    return False


def _tin_triangle_height_sample_points(vertices) -> list[tuple[float, float, float]]:
    points = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
            float(getattr(vertex, "z", 0.0) or 0.0),
        )
        for vertex in list(vertices or [])
    ]
    if len(points) != 3:
        return points
    centroid = (
        sum(point[0] for point in points) / 3.0,
        sum(point[1] for point in points) / 3.0,
        sum(point[2] for point in points) / 3.0,
    )
    midpoints = [
        (
            (points[index][0] + points[(index + 1) % 3][0]) / 2.0,
            (points[index][1] + points[(index + 1) % 3][1]) / 2.0,
            (points[index][2] + points[(index + 1) % 3][2]) / 2.0,
        )
        for index in range(3)
    ]
    return [centroid] + points + midpoints


def tin_triangle_xy_overlaps_reference_triangles(vertices: list[object], reference_triangles: list[tuple[object, object, object]]) -> bool:
    for sample_x, sample_y in tin_triangle_overlap_sample_points_xy(vertices):
        if tin_surface_z_at_xy_from_reference_triangles(reference_triangles, sample_x, sample_y) is not None:
            return True
    return False


def tin_triangle_overlap_sample_points_xy(vertices: list[object]) -> list[tuple[float, float]]:
    points = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
        )
        for vertex in list(vertices or [])
    ]
    if len(points) != 3:
        return points
    centroid = (
        sum(point[0] for point in points) / 3.0,
        sum(point[1] for point in points) / 3.0,
    )
    midpoints = [
        (
            (points[index][0] + points[(index + 1) % 3][0]) / 2.0,
            (points[index][1] + points[(index + 1) % 3][1]) / 2.0,
        )
        for index in range(3)
    ]
    return [centroid] + points + midpoints


def triangle_triangle_intersection_segment(triangle_a, triangle_b):
    points: list[tuple[float, float, float]] = []
    points.extend(triangle_edges_intersect_other_triangle_plane(triangle_a, triangle_b))
    points.extend(triangle_edges_intersect_other_triangle_plane(triangle_b, triangle_a))
    unique = unique_xyz_points(points, tolerance=1.0e-6)
    if len(unique) < 2:
        return None
    best_pair = None
    best_distance = 0.0
    for index, first in enumerate(unique):
        for second in unique[index + 1:]:
            distance = xyz_distance(first, second)
            if distance > best_distance:
                best_distance = distance
                best_pair = (first, second)
    if best_pair is None or best_distance <= 1.0e-7:
        return None
    return best_pair


def triangle_edges_intersect_other_triangle_plane(source_triangle, target_triangle) -> list[tuple[float, float, float]]:
    plane = triangle_plane(target_triangle)
    if plane is None:
        return []
    normal, plane_d = plane
    source_points = [vertex_xyz(vertex) for vertex in source_triangle]
    target_points = [vertex_xyz(vertex) for vertex in target_triangle]
    output: list[tuple[float, float, float]] = []
    for first, second in ((source_points[0], source_points[1]), (source_points[1], source_points[2]), (source_points[2], source_points[0])):
        first_distance = dot3(normal, first) + plane_d
        second_distance = dot3(normal, second) + plane_d
        if abs(first_distance) <= 1.0e-7 and point_in_triangle_3d(first, target_points):
            output.append(first)
        if abs(second_distance) <= 1.0e-7 and point_in_triangle_3d(second, target_points):
            output.append(second)
        if first_distance * second_distance > 0.0:
            continue
        denominator = first_distance - second_distance
        if abs(denominator) <= 1.0e-12:
            continue
        ratio = first_distance / denominator
        if ratio < -1.0e-7 or ratio > 1.0 + 1.0e-7:
            continue
        point = (
            first[0] + (second[0] - first[0]) * ratio,
            first[1] + (second[1] - first[1]) * ratio,
            first[2] + (second[2] - first[2]) * ratio,
        )
        if point_in_triangle_3d(point, target_points):
            output.append(point)
    return output


def triangle_plane(triangle):
    points = [vertex_xyz(vertex) for vertex in triangle]
    ab = sub3(points[1], points[0])
    ac = sub3(points[2], points[0])
    normal = cross3(ab, ac)
    length = length3(normal)
    if length <= 1.0e-12:
        return None
    normal = (normal[0] / length, normal[1] / length, normal[2] / length)
    return normal, -dot3(normal, points[0])


def point_in_triangle_3d(point: tuple[float, float, float], triangle_points: list[tuple[float, float, float]]) -> bool:
    a, b, c = triangle_points
    v0 = sub3(c, a)
    v1 = sub3(b, a)
    v2 = sub3(point, a)
    dot00 = dot3(v0, v0)
    dot01 = dot3(v0, v1)
    dot02 = dot3(v0, v2)
    dot11 = dot3(v1, v1)
    dot12 = dot3(v1, v2)
    denominator = dot00 * dot11 - dot01 * dot01
    if abs(denominator) <= 1.0e-12:
        return False
    inv = 1.0 / denominator
    u = (dot11 * dot02 - dot01 * dot12) * inv
    v = (dot00 * dot12 - dot01 * dot02) * inv
    tolerance = 1.0e-6
    return u >= -tolerance and v >= -tolerance and (u + v) <= 1.0 + tolerance


def triangle_xyz_bbox(triangle) -> tuple[float, float, float, float, float, float]:
    points = [vertex_xyz(vertex) for vertex in triangle]
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        min(point[2] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
        max(point[2] for point in points),
    )


def bbox3d_overlaps(first, second, *, tolerance: float = 0.0) -> bool:
    return not (
        first[3] < second[0] - tolerance
        or second[3] < first[0] - tolerance
        or first[4] < second[1] - tolerance
        or second[4] < first[1] - tolerance
        or first[5] < second[2] - tolerance
        or second[5] < first[2] - tolerance
    )


def unique_xyz_points(points: list[tuple[float, float, float]], *, tolerance: float = 1.0e-6) -> list[tuple[float, float, float]]:
    output = []
    for point in list(points or []):
        if any(xyz_distance(point, existing) <= tolerance for existing in output):
            continue
        output.append(point)
    return output


def vertex_xyz(vertex) -> tuple[float, float, float]:
    return (
        float(getattr(vertex, "x", 0.0) or 0.0),
        float(getattr(vertex, "y", 0.0) or 0.0),
        float(getattr(vertex, "z", 0.0) or 0.0),
    )


def sub3(first, second) -> tuple[float, float, float]:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def dot3(first, second) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def cross3(first, second) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def length3(value) -> float:
    return math.sqrt(dot3(value, value))


def xyz_distance(first, second) -> float:
    return math.sqrt(
        (float(first[0]) - float(second[0])) ** 2
        + (float(first[1]) - float(second[1])) ** 2
        + (float(first[2]) - float(second[2])) ** 2
    )


def tin_surface_reference_triangles(surface) -> list[tuple[object, object, object]]:
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    output = []
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            continue
        output.append((vertices[0], vertices[1], vertices[2]))
    return output


def tin_surface_z_at_xy_from_reference_triangles(reference_triangles, x: float, y: float):
    for a, b, c in list(reference_triangles or []):
        z_value = triangle_z_at_xy(a, b, c, x, y)
        if z_value is not None:
            return z_value
    return None


def triangle_z_at_xy(a, b, c, x: float, y: float):
    ax = float(getattr(a, "x", 0.0) or 0.0)
    ay = float(getattr(a, "y", 0.0) or 0.0)
    az = float(getattr(a, "z", 0.0) or 0.0)
    bx = float(getattr(b, "x", 0.0) or 0.0)
    by = float(getattr(b, "y", 0.0) or 0.0)
    bz = float(getattr(b, "z", 0.0) or 0.0)
    cx = float(getattr(c, "x", 0.0) or 0.0)
    cy = float(getattr(c, "y", 0.0) or 0.0)
    cz = float(getattr(c, "z", 0.0) or 0.0)
    denominator = ((by - cy) * (ax - cx)) + ((cx - bx) * (ay - cy))
    if abs(denominator) <= 1.0e-12:
        return None
    first = (((by - cy) * (float(x) - cx)) + ((cx - bx) * (float(y) - cy))) / denominator
    second = (((cy - ay) * (float(x) - cx)) + ((ax - cx) * (float(y) - cy))) / denominator
    third = 1.0 - first - second
    tolerance = 1.0e-8
    if first < -tolerance or second < -tolerance or third < -tolerance:
        return None
    return (first * az) + (second * bz) + (third * cz)


def suppress_daylight_triangles_inside_intersection_surface_footprint(surface, intersection_surface):
    return _suppress_daylight_triangles_inside_intersection_surface_footprint(surface, intersection_surface)


def suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint(surface, intersection_slope_face_surface):
    return _suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint(surface, intersection_slope_face_surface)


def suppress_daylight_triangles_above_intersection_surface(surface, intersection_surface, *, tolerance: float = 0.05):
    return _suppress_daylight_triangles_above_intersection_surface(surface, intersection_surface, tolerance=tolerance)


def trim_daylight_triangles_above_intersection_surface_by_intersection_lines(surface, intersection_surface, *, tolerance: float = 0.05):
    return _trim_daylight_triangles_above_intersection_surface_by_intersection_lines(surface, intersection_surface, tolerance=tolerance)
