"""Typed Intersection exclusion-boundary and TIN edge geometry builders."""

from __future__ import annotations

from ...models.result.intersection_boundary_loop import IntersectionBoundaryLoopResult
from ...models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
    IntersectionBoundarySegmentRow,
)
from ..evaluation.intersection_boundary_loop_evaluation_service import (
    IntersectionBoundaryLoopEvaluationService,
)
from .intersection_patch_triangulation_service import (
    IntersectionPatchTriangulationService,
)
from ..geometry import (
    xy_closed_edges,
    xy_point_in_polygon,
    xy_point_segment_distance_with_ratio,
    xy_polygon_signed_area,
    xy_segment_distance,
    xy_segments_cross_strict,
    xyz_exterior_convex_hull,
    xyz_polygon_union_outer_boundary,
)


def _intersection_row_by_id(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "").strip() == target:
            return row
    return None


def _intersection_tie_in_strip_polygon(rows: list[IntersectionBoundarySegmentRow]) -> list[tuple[float, float, float]] | None:
    return IntersectionPatchTriangulationService().tie_in_strip_polygon(rows)


def _xy_polygon_union_outer_boundary(
    polygons: list[list[tuple[float, float, float]]],
) -> list[tuple[float, float, float]]:
    return xyz_polygon_union_outer_boundary(polygons)


def _xy_polygon_exterior_hull_boundary(
    polygons: list[list[tuple[float, float, float]]],
) -> list[tuple[float, float, float]]:
    return xyz_exterior_convex_hull(polygons)


def _preview_xyz_tuple(value) -> tuple[float, float, float]:
    try:
        seq = tuple(value or ())
    except Exception:
        seq = ()
    x = float(seq[0]) if len(seq) > 0 else 0.0
    y = float(seq[1]) if len(seq) > 1 else 0.0
    z = float(seq[2]) if len(seq) > 2 else 0.0
    return (x, y, z)


def _preview_same_xy(a: tuple[float, float, float], b: tuple[float, float, float], tolerance: float = 1.0e-6) -> bool:
    return abs(float(a[0]) - float(b[0])) <= tolerance and abs(float(a[1]) - float(b[1])) <= tolerance


def _point_segment_distance_with_ratio(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[float, float]:
    return xy_point_segment_distance_with_ratio((px, py), (x1, y1), (x2, y2))


def _intersection_boundary_loop_result_for_shared_breaklines(
    applied_section_set,
    *,
    prerequisite,
    intersection_model,
    diagnostics: list[str],
) -> IntersectionBoundaryLoopResult | None:
    """Compatibility wrapper for typed boundary-loop chain evaluation."""

    return IntersectionBoundaryLoopEvaluationService().evaluate_context(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
        diagnostics=diagnostics,
    )


def _tin_surface_boundary_edge_rows(surface) -> list[dict[str, object]]:
    edge_counts: dict[tuple[str, str], int] = {}
    edge_values: dict[tuple[str, str], dict[str, object]] = {}
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        ids = [
            str(getattr(triangle, "v1", "") or ""),
            str(getattr(triangle, "v2", "") or ""),
            str(getattr(triangle, "v3", "") or ""),
        ]
        for first_id, second_id in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            edge_values.setdefault(
                key,
                {
                    "first_id": first_id,
                    "second_id": second_id,
                    "quality_ref": str(getattr(triangle, "quality_ref", "") or ""),
                    "triangle_id": str(getattr(triangle, "triangle_id", "") or ""),
                },
            )
    return [edge_values[key] for key, count in edge_counts.items() if count == 1]


def _tin_surface_all_edge_rows(surface) -> list[dict[str, object]]:
    edge_counts: dict[tuple[str, str], int] = {}
    edge_values: dict[tuple[str, str], dict[str, object]] = {}
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        ids = [
            str(getattr(triangle, "v1", "") or ""),
            str(getattr(triangle, "v2", "") or ""),
            str(getattr(triangle, "v3", "") or ""),
        ]
        for first_id, second_id in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            edge_values.setdefault(
                key,
                {
                    "first_id": first_id,
                    "second_id": second_id,
                    "quality_ref": str(getattr(triangle, "quality_ref", "") or ""),
                    "triangle_id": str(getattr(triangle, "triangle_id", "") or ""),
                },
            )
    rows: list[dict[str, object]] = []
    for key, row in edge_values.items():
        item = dict(row)
        item["edge_count"] = int(edge_counts.get(key, 0) or 0)
        item["is_boundary"] = int(edge_counts.get(key, 0) or 0) == 1
        rows.append(item)
    return rows


def _intersection_practical_exclusion_polygon_from_boundary_segments(
    boundary_result: IntersectionBoundarySegmentResult,
    *,
    intersection_model=None,
) -> dict[str, object] | None:
    candidate = _intersection_practical_exclusion_polygon_candidate_from_boundary_segments(
        boundary_result,
        intersection_model=intersection_model,
    )
    return candidate if str(candidate.get("status", "") or "") == "ready" else None


def _intersection_boundary_loop_exclusion_polygon_candidate(
    applied_section_set,
    *,
    prerequisite,
    intersection_model=None,
) -> dict[str, object] | None:
    """Return an exclusion polygon from the authoritative IntersectionBoundaryLoopResult."""

    diagnostics: list[str] = []
    loop_result = _intersection_boundary_loop_result_for_shared_breaklines(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
        diagnostics=diagnostics,
    )
    if loop_result is None:
        return None
    ready_loops = [
        row
        for row in list(getattr(loop_result, "loop_rows", []) or [])
        if str(getattr(row, "loop_role", "") or "") == "outer_intersection_boundary"
        and str(getattr(row, "status", "") or "") == "ready"
        and bool(getattr(row, "closed", False))
    ]
    if not ready_loops:
        return {
            "intersection_id": str(getattr(loop_result, "intersection_id", "") or getattr(prerequisite, "intersection_id", "") or ""),
            "status": "missing",
            "points": [],
            "holes": [],
            "islands": [],
            "area": 0.0,
            "boundary_source": "intersection_boundary_loop",
            "boundary_strategy": "authoritative_boundary_loop",
            "practical_boundary_aligned": False,
            "practical_footprint_status": "missing",
            "practical_footprint_diagnostics": [
                *diagnostics,
                *[str(value or "") for value in list(getattr(loop_result, "diagnostic_rows", []) or []) if str(value or "")],
                "intersection_boundary_loop_ready_outer_missing",
            ],
        }
    selected = max(ready_loops, key=lambda row: abs(float(getattr(row, "area_xy", 0.0) or 0.0)))
    points_3d = [_preview_xyz_tuple(point) for point in tuple(getattr(selected, "loop_points_xyz", ()) or ())]
    points: list[tuple[float, float]] = []
    for point in points_3d:
        xy = (float(point[0]), float(point[1]))
        if points and _preview_same_xy((points[-1][0], points[-1][1], 0.0), (xy[0], xy[1], 0.0)):
            continue
        points.append(xy)
    if len(points) >= 2 and _preview_same_xy((points[0][0], points[0][1], 0.0), (points[-1][0], points[-1][1], 0.0)):
        points = points[:-1]
    area = abs(_xy_polygon_area(points)) if len(points) >= 3 else 0.0
    if len(points) < 3 or area <= 1.0e-6:
        return {
            "intersection_id": str(getattr(loop_result, "intersection_id", "") or getattr(prerequisite, "intersection_id", "") or ""),
            "status": "missing",
            "points": points,
            "holes": [],
            "islands": [],
            "area": area,
            "boundary_source": "intersection_boundary_loop",
            "boundary_strategy": "authoritative_boundary_loop",
            "practical_boundary_aligned": False,
            "practical_footprint_status": "missing",
            "practical_footprint_diagnostics": [
                *diagnostics,
                f"intersection_boundary_loop_polygon_invalid:points={len(points)};area={area:.6g}",
            ],
        }
    return {
        "intersection_id": str(getattr(loop_result, "intersection_id", "") or getattr(selected, "intersection_id", "") or ""),
        "status": "ready",
        "points": points,
        "holes": [],
        "islands": [],
        "area": area,
        "boundary_source": "intersection_boundary_loop",
        "boundary_strategy": "authoritative_outer_intersection_boundary",
        "practical_boundary_aligned": True,
        "boundary_loop_result_id": str(getattr(loop_result, "boundary_loop_result_id", "") or ""),
        "boundary_loop_id": str(getattr(selected, "loop_id", "") or ""),
        "boundary_loop_point_count": len(points),
        "boundary_loop_segment_count": int(getattr(selected, "segment_count", 0) or 0),
        "practical_footprint_status": "ready",
        "practical_footprint_diagnostics": diagnostics,
        "diagnostics": diagnostics,
    }


def _intersection_practical_exclusion_polygon_candidate_from_boundary_segments(
    boundary_result: IntersectionBoundarySegmentResult,
    *,
    intersection_model=None,
) -> dict[str, object]:
    intersection_id = str(getattr(boundary_result, "intersection_id", "") or "").strip()
    diagnostics: list[str] = []
    grouped: dict[str, list[IntersectionBoundarySegmentRow]] = {}
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "tie_in":
            continue
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        if alignment_ref:
            grouped.setdefault(alignment_ref, []).append(row)
    arc_stats = _intersection_curb_return_surface_arc_stats(boundary_result)
    edge_blend_face_count = len([
        role for _polygon, role in _intersection_curb_return_surface_parts(boundary_result)
        if str(role) == "curb_return_blend"
    ])
    if edge_blend_face_count:
        strategy = "structured_strip_curb_return_blend"
    elif int(arc_stats["arc_count"]):
        strategy = "structured_strip_curb_return"
    else:
        strategy = "structured_strip_union"
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip()
    if not primary_ref or primary_ref not in grouped:
        primary_ref = next(iter(grouped.keys()), "")
    primary_polygon = _intersection_tie_in_strip_polygon(grouped.get(primary_ref, []))
    if primary_polygon is None:
        diagnostics.append(
            f"intersection_exclusion_footprint_primary_strip_invalid:{primary_ref or 'primary'}"
        )
        return {
            "intersection_id": intersection_id,
            "status": "missing",
            "points": [],
            "holes": [],
            "islands": [],
            "area": 0.0,
            "boundary_source": "practical_intersection_surface_boundary",
            "boundary_strategy": strategy,
            "practical_boundary_aligned": False,
            "edge_blend_face_count": edge_blend_face_count,
            "curb_return_arc_count": int(arc_stats["arc_count"]),
            "diagnostics": diagnostics,
        }
    pavement_strip_polygons: list[list[tuple[float, float, float]]] = [primary_polygon]
    polygons: list[list[tuple[float, float, float]]] = [primary_polygon]
    for alignment_ref, rows in grouped.items():
        if alignment_ref == primary_ref:
            continue
        polygon = _intersection_tie_in_strip_polygon(rows)
        if polygon is None:
            diagnostics.append(f"intersection_exclusion_footprint_strip_invalid:{alignment_ref}")
            continue
        pavement_strip_polygons.append(polygon)
        outside = _xy_polygon_outer_difference_candidate(polygon, primary_polygon)
        polygons.append(outside or polygon)
    for polygon, _role in _intersection_curb_return_surface_parts(boundary_result):
        polygons.append(polygon)
    union_points = _xy_polygon_union_outer_boundary(polygons)
    if len(union_points) < 3:
        diagnostics.append(
            "intersection_exclusion_footprint_union_invalid:no_closed_outer_loop"
        )
        union_points = _xy_polygon_exterior_hull_boundary(polygons)
        if len(union_points) >= 3:
            diagnostics.append("intersection_exclusion_footprint_outer_loop_recovered:exterior_hull")
        else:
            if int(arc_stats["arc_count"]):
                diagnostics.append(
                    f"intersection_exclusion_footprint_curb_return_surface_ready:arcs={int(arc_stats['arc_count'])}; segments={int(arc_stats['segment_count'])}"
                )
            return {
                "intersection_id": intersection_id,
                "status": "missing",
                "points": [],
                "holes": [],
                "islands": [],
                "area": 0.0,
                "boundary_source": "practical_intersection_surface_boundary",
                "boundary_strategy": strategy,
                "practical_boundary_aligned": False,
                "edge_blend_face_count": edge_blend_face_count,
                "curb_return_arc_count": int(arc_stats["arc_count"]),
                "diagnostics": diagnostics,
                "pavement_strip_polygons": _intersection_xyz_polygons_to_xy(pavement_strip_polygons),
            }
    points = [(float(point[0]), float(point[1])) for point in union_points]
    area = abs(_xy_polygon_area(points))
    if area <= 1.0e-6:
        diagnostics.append("intersection_exclusion_footprint_zero_area")
        return {
            "intersection_id": intersection_id,
            "status": "missing",
            "points": points,
            "holes": [],
            "islands": [],
            "area": area,
            "boundary_source": "practical_intersection_surface_boundary",
            "boundary_strategy": strategy,
            "practical_boundary_aligned": False,
            "edge_blend_face_count": edge_blend_face_count,
            "curb_return_arc_count": int(arc_stats["arc_count"]),
            "diagnostics": diagnostics,
        }
    return {
        "intersection_id": intersection_id,
        "status": str(getattr(boundary_result, "status", "") or "ready"),
        "points": points,
        "holes": [],
        "islands": [],
        "area": area,
        "boundary_source": "practical_intersection_surface_boundary",
        "boundary_strategy": strategy,
        "practical_boundary_aligned": True,
        "edge_blend_face_count": edge_blend_face_count,
        "curb_return_arc_count": int(arc_stats["arc_count"]),
        "curb_return_arc_polylines": _intersection_curb_return_arc_polylines_xy(boundary_result),
        "pavement_strip_polygons": _intersection_xyz_polygons_to_xy(pavement_strip_polygons),
        "practical_footprint_status": "ready",
        "practical_footprint_diagnostics": diagnostics,
        "diagnostics": diagnostics,
    }


def _intersection_xyz_polygons_to_xy(polygons: list[list[tuple[float, float, float]]]) -> list[list[tuple[float, float]]]:
    output: list[list[tuple[float, float]]] = []
    for polygon in list(polygons or []):
        points = [(float(point[0]), float(point[1])) for point in list(polygon or [])]
        if len(points) >= 3 and abs(_xy_polygon_area(points)) > 1.0e-6:
            output.append(points)
    return output


def _intersection_curb_return_arc_polylines_xy(boundary_result) -> list[list[tuple[float, float]]]:
    if boundary_result is None:
        return []
    output: list[list[tuple[float, float]]] = []
    for row in list(getattr(boundary_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        points = [
            (float(point[0]), float(point[1]))
            for point in list(getattr(row, "chord_points_xyz", []) or [])
            if len(tuple(point or ())) >= 2
        ]
        if len(points) >= 2:
            output.append(points)
    return output


def _xy_point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    return xy_point_in_polygon(point, polygon)


def _xy_triangle_near_curb_return_arc_protection(
    triangle: list[tuple[float, float]],
    arc_polylines: list[list[tuple[float, float]]],
    *,
    max_distance: float,
) -> bool:
    if len(triangle) < 3 or float(max_distance or 0.0) <= 0.0:
        return False
    centroid = (
        sum(float(point[0]) for point in triangle[:3]) / 3.0,
        sum(float(point[1]) for point in triangle[:3]) / 3.0,
    )
    triangle_edges = _xy_closed_edges(triangle[:3])
    limit = float(max_distance)
    for polyline in list(arc_polylines or []):
        points = list(polyline or [])
        if len(points) < 2:
            continue
        for index in range(len(points) - 1):
            arc_start = points[index]
            arc_end = points[index + 1]
            if _point_segment_distance_with_ratio(centroid[0], centroid[1], arc_start[0], arc_start[1], arc_end[0], arc_end[1])[0] <= limit:
                return True
            for point in triangle[:3]:
                if _point_segment_distance_with_ratio(point[0], point[1], arc_start[0], arc_start[1], arc_end[0], arc_end[1])[0] <= limit:
                    return True
            for tri_start, tri_end in triangle_edges:
                if _xy_segment_distance(tri_start, tri_end, arc_start, arc_end) <= limit:
                    return True
    return False


def _xy_triangle_intrudes_pavement_strip_protection(
    triangle: list[tuple[float, float]],
    pavement_strip_polygons: list[list[tuple[float, float]]],
) -> bool:
    if len(triangle) < 3:
        return False
    centroid = (
        sum(float(point[0]) for point in triangle[:3]) / 3.0,
        sum(float(point[1]) for point in triangle[:3]) / 3.0,
    )
    triangle_edges = _xy_closed_edges(triangle[:3])
    for polygon in list(pavement_strip_polygons or []):
        strip = list(polygon or [])
        if len(strip) < 3:
            continue
        if _xy_point_in_polygon(centroid, strip):
            return True
        if any(_xy_point_in_polygon(point, strip) for point in triangle[:3]):
            return True
        for first_start, first_end in triangle_edges:
            for second_start, second_end in _xy_closed_edges(strip):
                if _xy_segments_cross_strict(first_start, first_end, second_start, second_end):
                    return True
    return False


def _xy_segments_cross_strict(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    return xy_segments_cross_strict(a1, a2, b1, b2)


def _xy_segment_distance(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> float:
    return xy_segment_distance(first_start, first_end, second_start, second_end)


def _xy_closed_edges(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    return xy_closed_edges(points)


def _xy_polygon_area(points: list[tuple[float, float]]) -> float:
    return xy_polygon_signed_area(points)


def _intersection_curb_return_surface_arc_stats(boundary_segment_result) -> dict[str, int]:
    return IntersectionPatchTriangulationService().curb_return_surface_arc_stats(
        boundary_segment_result
    )


def _intersection_curb_return_surface_parts(boundary_segment_result) -> list[tuple[list[tuple[float, float, float]], str]]:
    return IntersectionPatchTriangulationService().curb_return_surface_parts(
        boundary_segment_result
    )


def _xy_polygon_outer_difference_candidate(
    polygon: list[tuple[float, float, float]],
    clip_polygon: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]] | None:
    return IntersectionPatchTriangulationService().polygon_outer_difference_candidate(
        polygon,
        clip_polygon,
    )


def intersection_practical_exclusion_polygon_from_boundary_segments(*args, **kwargs):
    return _intersection_practical_exclusion_polygon_from_boundary_segments(*args, **kwargs)


def intersection_boundary_loop_exclusion_polygon_candidate(*args, **kwargs):
    return _intersection_boundary_loop_exclusion_polygon_candidate(*args, **kwargs)


def intersection_practical_exclusion_polygon_candidate_from_boundary_segments(*args, **kwargs):
    return _intersection_practical_exclusion_polygon_candidate_from_boundary_segments(*args, **kwargs)


def tin_surface_boundary_edge_rows(surface) -> list[dict[str, object]]:
    return _tin_surface_boundary_edge_rows(surface)


def tin_surface_all_edge_rows(surface) -> list[dict[str, object]]:
    return _tin_surface_all_edge_rows(surface)


def xy_triangle_near_curb_return_arc_protection(*args, **kwargs):
    return _xy_triangle_near_curb_return_arc_protection(*args, **kwargs)


def xy_triangle_intrudes_pavement_strip_protection(*args, **kwargs):
    return _xy_triangle_intrudes_pavement_strip_protection(*args, **kwargs)
