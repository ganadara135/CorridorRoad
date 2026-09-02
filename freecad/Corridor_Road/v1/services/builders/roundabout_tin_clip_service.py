"""Clip typed TIN surfaces by accepted roundabout ownership contracts."""

from __future__ import annotations

import math
from dataclasses import replace

from ...models.result.tin_surface import (
    TINQualityRow,
    TINSurface,
    TINTriangle,
    TINVertex,
)
from ...services.geometry import (
    dedupe_xy_payload_points,
    ear_clip_triangulation_indices,
    intersect_payload_polygon_with_convex_polygon,
    subtract_convex_polygon_from_payload_polygon,
    xy_closed_edges,
    xy_point_in_triangle_strict,
    xy_point_segment_distance_with_ratio,
    xy_polygon_is_convex,
    xy_polygon_signed_area,
    xy_triangle_polygon_intersection_kind,
)


def _unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _roundabout_clip_boundary_role_for_surface(surface_role: str) -> str:
    text = str(surface_role or "").strip().lower()
    if text == "subgrade_surface":
        return "roundabout_subgrade_clip_boundary"
    if text in {"slope_face_surface", "daylight_surface", "daylight"}:
        return "roundabout_slope_handoff_boundary"
    return "roundabout_approach_clip_boundary"


def _roundabout_actual_clip_boundary_roles_for_surface(surface_role: str) -> set[str]:
    """Return accepted source boundary roles that may remove ordinary corridor geometry."""

    text = str(surface_role or "").strip().lower()
    if text in {"design_surface", "subgrade_surface", "slope_face_surface", "daylight_surface", "daylight"}:
        return {"roundabout_outer_ownership_boundary"}
    return {"roundabout_outer_ownership_boundary"}


def _roundabout_clip_boundary_contract_summary(
    boundary_result,
    *,
    surface_role: str,
) -> dict[str, object]:
    boundary_role = _roundabout_clip_boundary_role_for_surface(surface_role)
    if boundary_result is None:
        return {
            "status": "missing",
            "boundary_role": boundary_role,
            "surface_role": str(surface_role or ""),
            "boundary_result_id": "",
            "loop_count": 0,
            "segment_count": 0,
            "loop_refs": [],
            "segment_refs": [],
            "diagnostics": ["roundabout_clip_missing_boundary"],
        }
    loops = [
        row
        for row in list(getattr(boundary_result, "loop_rows", []) or [])
        if str(getattr(row, "loop_role", "") or "") == boundary_role
        and str(getattr(row, "status", "") or "") == "ready"
        and bool(getattr(row, "closed", False))
    ]
    loop_bboxes = [
        ",".join(f"{float(value):.3f}" for value in tuple(getattr(row, "bbox_xy", ()) or ()))
        for row in loops
        if tuple(getattr(row, "bbox_xy", ()) or ())
    ]
    loop_areas = [
        f"{float(getattr(row, 'area_xy', 0.0) or 0.0):.3f}"
        for row in loops
    ]
    approach_refs = _unique_text_values(
        [
            str(ref or "")
            for row in loops
            for ref in tuple(getattr(row, "source_refs", ()) or ())
            if str(ref or "").startswith("intersection-roundabout-approach-leg:")
        ]
    )
    approach_roles = _roundabout_approach_roles_from_refs(approach_refs)
    segment_refs = [
        str(segment_ref or "")
        for row in loops
        for segment_ref in list(getattr(row, "segment_refs", ()) or ())
        if str(segment_ref or "")
    ]
    diagnostics = []
    if not loops:
        diagnostics.append(f"roundabout_clip_boundary_role_missing:{boundary_role}")
    diagnostic_key = {
        "roundabout_approach_clip_boundary": "roundabout_design_clip_ready",
        "roundabout_subgrade_clip_boundary": "roundabout_subgrade_clip_ready",
        "roundabout_slope_handoff_boundary": "roundabout_slope_clip_ready",
    }.get(boundary_role, "roundabout_clip_ready")
    return {
        "status": "ready" if loops else "warning",
        "diagnostic_key": diagnostic_key,
        "boundary_role": boundary_role,
        "surface_role": str(surface_role or ""),
        "boundary_result_id": str(getattr(boundary_result, "boundary_loop_result_id", "") or ""),
        "loop_count": len(loops),
        "segment_count": len(segment_refs),
        "loop_refs": [str(getattr(row, "loop_id", "") or "") for row in loops],
        "loop_bboxes": loop_bboxes,
        "loop_areas": loop_areas,
        "segment_refs": segment_refs,
        "approach_leg_count": len(approach_roles),
        "approach_leg_roles": approach_roles,
        "approach_leg_source": "roundabout_approach_leg_contract" if approach_roles else "",
        "diagnostics": diagnostics,
    }


def _roundabout_clip_boundary_polygons(
    boundary_result,
    *,
    surface_role: str,
) -> list[list[tuple[float, float]]]:
    if boundary_result is None:
        return []
    accepted_roles = _roundabout_actual_clip_boundary_roles_for_surface(surface_role)
    polygons: list[list[tuple[float, float]]] = []
    for row in list(getattr(boundary_result, "loop_rows", []) or []):
        if str(getattr(row, "loop_role", "") or "") not in accepted_roles:
            continue
        if str(getattr(row, "status", "") or "") != "ready" or not bool(getattr(row, "closed", False)):
            continue
        points_xyz = list(getattr(row, "loop_points_xyz", ()) or ())
        if len(points_xyz) >= 2 and _intersection_slope_face_points_close_xy(points_xyz[0], points_xyz[-1]):
            points_xyz = points_xyz[:-1]
        polygon = [(float(point[0]), float(point[1])) for point in points_xyz if len(point) >= 2]
        if len(polygon) < 3 or abs(_xy_polygon_area(polygon)) <= 1.0e-6:
            continue
        polygons.append(polygon)
    return polygons


def _roundabout_clip_boundary_quality_rows(surface_id: str, summary: dict[str, object]) -> list[TINQualityRow]:
    prefix = str(surface_id or "roundabout-surface")
    loop_refs = [str(value or "") for value in list(summary.get("loop_refs", []) or []) if str(value or "")]
    loop_bboxes = [str(value or "") for value in list(summary.get("loop_bboxes", []) or []) if str(value or "")]
    loop_areas = [str(value or "") for value in list(summary.get("loop_areas", []) or []) if str(value or "")]
    segment_refs = [str(value or "") for value in list(summary.get("segment_refs", []) or []) if str(value or "")]
    diagnostics = [str(value or "") for value in list(summary.get("diagnostics", []) or []) if str(value or "")]
    diagnostic_key = str(summary.get("diagnostic_key", "") or "")
    if diagnostic_key:
        diagnostics = [diagnostic_key, *diagnostics]
    approach_roles = [str(value or "") for value in list(summary.get("approach_leg_roles", []) or []) if str(value or "")]
    actual_clip_roles = sorted(_roundabout_actual_clip_boundary_roles_for_surface(str(summary.get("surface_role", "") or "")))
    return [
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-status",
            "roundabout_clip_boundary_status",
            str(summary.get("status", "") or ""),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-role",
            "roundabout_clip_boundary_role",
            str(summary.get("boundary_role", "") or ""),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-actual-clip-boundary-roles",
            "roundabout_actual_clip_boundary_roles",
            ",".join(actual_clip_roles),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-result-id",
            "roundabout_clip_boundary_result_id",
            str(summary.get("boundary_result_id", "") or ""),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-loop-count",
            "roundabout_clip_boundary_loop_count",
            int(summary.get("loop_count", 0) or 0),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-segment-count",
            "roundabout_clip_boundary_segment_count",
            int(summary.get("segment_count", 0) or 0),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-loop-refs",
            "roundabout_clip_boundary_loop_refs",
            ",".join(loop_refs[:50]),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-loop-bboxes",
            "roundabout_clip_boundary_loop_bboxes",
            ";".join(loop_bboxes[:50]),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-loop-areas",
            "roundabout_clip_boundary_loop_areas",
            ",".join(loop_areas[:50]),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-segment-refs",
            "roundabout_clip_boundary_segment_refs",
            ",".join(segment_refs[:50]),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-approach-leg-count",
            "roundabout_clip_boundary_approach_leg_count",
            int(summary.get("approach_leg_count", 0) or 0),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-approach-leg-roles",
            "roundabout_clip_boundary_approach_leg_roles",
            ",".join(approach_roles),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-approach-leg-source",
            "roundabout_clip_boundary_approach_leg_source",
            str(summary.get("approach_leg_source", "") or ""),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-diagnostics",
            "roundabout_clip_boundary_diagnostics",
            ";".join(diagnostics[:20]),
        ),
    ]


def _roundabout_triangle_ownership_clip_reason(
    vertices: list[object],
    *,
    center_x: float,
    center_y: float,
    radius: float,
) -> str:
    """Return why a triangle belongs to roundabout ownership clipping."""

    if len(vertices) < 3:
        return ""
    xy_points = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
        )
        for vertex in vertices[:3]
    ]
    centroid = (
        sum(point[0] for point in xy_points) / 3.0,
        sum(point[1] for point in xy_points) / 3.0,
    )
    tolerance = 1.0e-6
    if math.hypot(centroid[0] - center_x, centroid[1] - center_y) <= radius + tolerance:
        return "centroid_inside"
    if any(math.hypot(point[0] - center_x, point[1] - center_y) <= radius + tolerance for point in xy_points):
        return "vertex_inside"
    for start, end in _xy_closed_edges(xy_points):
        distance, _ratio = _point_segment_distance_with_ratio(
            center_x,
            center_y,
            start[0],
            start[1],
            end[0],
            end[1],
        )
        if distance <= radius + tolerance:
            return "edge_crosses"
    if _xy_point_in_triangle((center_x, center_y), (xy_points[0], xy_points[1], xy_points[2])):
        return "center_inside_triangle"
    return ""


def _roundabout_triangle_boundary_clip_reason(
    vertices: list[object],
    *,
    clip_polygons: list[list[tuple[float, float]]],
) -> str:
    if len(vertices) < 3 or not clip_polygons:
        return ""
    xy_points = [
        (
            float(getattr(vertex, "x", 0.0) or 0.0),
            float(getattr(vertex, "y", 0.0) or 0.0),
        )
        for vertex in vertices[:3]
    ]
    for polygon in clip_polygons:
        kind = _xy_triangle_polygon_intersection_kind(xy_points, polygon)
        if kind == "centroid_inside":
            return "centroid_inside"
        if kind == "triangle_vertex_inside":
            return "vertex_inside"
        if kind == "edge_crossing":
            return "edge_crosses"
        if kind == "polygon_vertex_inside_triangle":
            return "center_inside_triangle"
    return ""


def _roundabout_boundary_exact_clip_parts(
    clip_polygons: list[list[tuple[float, float]]],
) -> tuple[list[list[tuple[float, float]]], bool, str]:
    parts: list[list[tuple[float, float]]] = []
    for polygon in list(clip_polygons or []):
        polygon_points = [tuple(point) for point in list(polygon or [])]
        polygon_parts = _xy_exact_cut_exclusion_parts(polygon_points)
        if len(polygon_points) >= 3 and not polygon_parts:
            return [], False, "roundabout_boundary_exact_unsupported"
        parts.extend(polygon_parts)
    if not parts:
        return [], False, "roundabout_boundary_exact_missing"
    method = "exact_convex_polygon" if len(parts) == len(list(clip_polygons or [])) else "exact_triangulated_polygon"
    return parts, True, method


def _roundabout_boundary_exact_clip_fragments(
    vertices: list[object],
    *,
    clip_parts: list[list[tuple[float, float]]],
) -> list[list[dict[str, object]]]:
    if len(vertices) < 3 or not clip_parts:
        return []
    triangle_polygon = [
        {
            "x": float(getattr(vertex, "x", 0.0) or 0.0),
            "y": float(getattr(vertex, "y", 0.0) or 0.0),
            "z": float(getattr(vertex, "z", 0.0) or 0.0),
            "source": str(getattr(vertex, "vertex_id", "") or ""),
        }
        for vertex in vertices[:3]
    ]
    return _xy_subtract_exclusion_area_from_polygon(
        triangle_polygon,
        exclusion_parts=clip_parts,
    )


def _roundabout_clip_reason_quality_rows(
    surface_id: str,
    reason_counts: dict[str, int],
    *,
    clip_mode: str,
    fallback_reason: str = "",
    exact_candidate_count: int = 0,
    exact_generated_triangle_count: int = 0,
    exact_fallback_count: int = 0,
    exact_supported: bool = False,
    exact_method: str = "",
    exact_part_count: int = 0,
) -> list[TINQualityRow]:
    prefix = str(surface_id or "roundabout-surface")
    ordered = [
        ("centroid_inside", int(reason_counts.get("centroid_inside", 0) or 0)),
        ("vertex_inside", int(reason_counts.get("vertex_inside", 0) or 0)),
        ("edge_crosses", int(reason_counts.get("edge_crosses", 0) or 0)),
        ("center_inside_triangle", int(reason_counts.get("center_inside_triangle", 0) or 0)),
    ]
    return [
        TINQualityRow(
            f"{prefix}:roundabout-ownership-clip-mode",
            "roundabout_ownership_clip_mode",
            str(clip_mode or "circle_intersection"),
            "",
            "Roundabout ownership clipping tests source boundary polygons before fallback ownership-circle suppression.",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-ownership-clip-fallback-reason",
            "roundabout_ownership_clip_fallback_reason",
            str(fallback_reason or ""),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-boundary-crossing-candidate-count",
            "roundabout_clip_boundary_crossing_candidate_count",
            sum(count for _name, count in ordered),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-exact-candidate-count",
            "roundabout_clip_exact_candidate_count",
            int(exact_candidate_count),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-exact-generated-triangle-count",
            "roundabout_clip_exact_generated_triangle_count",
            int(exact_generated_triangle_count),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-exact-fallback-count",
            "roundabout_clip_exact_fallback_count",
            int(exact_fallback_count),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-exact-supported",
            "roundabout_clip_exact_supported",
            1 if bool(exact_supported) else 0,
            "bool",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-exact-method",
            "roundabout_clip_exact_method",
            str(exact_method or ""),
        ),
        TINQualityRow(
            f"{prefix}:roundabout-clip-exact-part-count",
            "roundabout_clip_exact_part_count",
            int(exact_part_count),
            "count",
        ),
        TINQualityRow(
            f"{prefix}:roundabout-ownership-clip-reason-summary",
            "roundabout_ownership_clip_reason_summary",
            ",".join(f"{name}={count}" for name, count in ordered),
        ),
        *[
            TINQualityRow(
                f"{prefix}:roundabout-ownership-clip-{name.replace('_', '-')}-count",
                f"roundabout_ownership_clip_{name}_count",
                count,
                "count",
            )
            for name, count in ordered
        ],
    ]


def clip_tin_surface_by_roundabout_ownership(
    tin_surface: TINSurface | None,
    *,
    ownership_spec,
    boundary_loop_result,
    surface_role: str,
    boundary_summary=None,
    boundary_clip_polygons=None,
) -> TINSurface | None:
    """Suppress ordinary corridor triangles owned by a roundabout source boundary."""

    spec = ownership_spec
    if tin_surface is None or spec is None:
        return tin_surface
    center_x, center_y, _center_z = tuple(spec.get("center", (0.0, 0.0, 0.0)))
    radius = float(spec.get("ownership_radius", 0.0) or 0.0)
    if radius <= 0.0:
        return tin_surface
    if boundary_summary is None:
        boundary_summary = _roundabout_clip_boundary_contract_summary(
            boundary_loop_result,
            surface_role=surface_role,
        )
    if boundary_clip_polygons is None:
        boundary_clip_polygons = _roundabout_clip_boundary_polygons(
            boundary_loop_result,
            surface_role=surface_role,
        )
    surface_role_text = str(surface_role or "")
    use_boundary_clip = (
        surface_role_text in {"design_surface", "subgrade_surface", "slope_face_surface", "daylight_surface", "daylight"}
        and bool(boundary_clip_polygons)
    )
    clip_mode = "roundabout_boundary_loop" if use_boundary_clip else "circle_intersection"
    fallback_reason = "" if use_boundary_clip else (
        "roundabout_clip_boundary_unavailable"
        if surface_role_text in {"design_surface", "slope_face_surface", "daylight_surface", "daylight"}
        else ""
    )
    exact_clip_parts: list[list[tuple[float, float]]] = []
    exact_supported = False
    exact_method = ""
    if use_boundary_clip:
        exact_clip_parts, exact_supported, exact_method = _roundabout_boundary_exact_clip_parts(boundary_clip_polygons)
    vertex_map = tin_surface.vertex_map()
    output_vertices = list(getattr(tin_surface, "vertex_rows", []) or [])
    kept_triangles = []
    clipped_refs: list[str] = []
    reason_counts: dict[str, int] = {}
    tested = 0
    exact_candidate_count = 0
    exact_generated_triangle_count = 0
    exact_fallback_count = 0
    generated_vertex_index = 0
    generated_triangle_index = 0
    for triangle in list(getattr(tin_surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (triangle.v1, triangle.v2, triangle.v3)]
        if any(vertex is None for vertex in vertices):
            kept_triangles.append(triangle)
            continue
        tested += 1
        valid_vertices = [vertex for vertex in vertices if vertex is not None]
        if use_boundary_clip:
            reason = _roundabout_triangle_boundary_clip_reason(
                valid_vertices,
                clip_polygons=boundary_clip_polygons,
            )
        else:
            reason = _roundabout_triangle_ownership_clip_reason(
                valid_vertices,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
            )
        if reason:
            clipped_refs.append(str(getattr(triangle, "triangle_id", "") or ""))
            reason_counts[reason] = int(reason_counts.get(reason, 0) or 0) + 1
            if use_boundary_clip:
                exact_candidate_count += 1
                if exact_supported:
                    fragments = _roundabout_boundary_exact_clip_fragments(
                        valid_vertices,
                        clip_parts=exact_clip_parts,
                    )
                    generated_for_triangle = 0
                    for fragment in fragments:
                        if len(fragment) < 3 or abs(_xy_polygon_area([(point["x"], point["y"]) for point in fragment])) <= 1.0e-9:
                            continue
                        fragment_vertex_ids = []
                        for point in fragment:
                            vertex_id = f"{str(getattr(tin_surface, 'surface_id', '') or surface_role_text)}:roundabout-exact:v{generated_vertex_index}"
                            generated_vertex_index += 1
                            output_vertices.append(
                                TINVertex(
                                    vertex_id=vertex_id,
                                    x=float(point["x"]),
                                    y=float(point["y"]),
                                    z=float(point["z"]),
                                    source_point_ref=str(point.get("source", "") or ""),
                                    notes=f"exact roundabout ownership clip fragment from {getattr(triangle, 'triangle_id', '')}",
                                )
                            )
                            fragment_vertex_ids.append(vertex_id)
                        for index in range(1, len(fragment_vertex_ids) - 1):
                            kept_triangles.append(
                                TINTriangle(
                                    triangle_id=f"{getattr(triangle, 'triangle_id', 'triangle')}:roundabout-exact:{generated_triangle_index}",
                                    v1=fragment_vertex_ids[0],
                                    v2=fragment_vertex_ids[index],
                                    v3=fragment_vertex_ids[index + 1],
                                    triangle_kind=str(getattr(triangle, "triangle_kind", "") or "primary_triangle"),
                                    quality_ref="roundabout_ownership_exact_clip",
                                    notes=f"generated outside roundabout clip fragment from {getattr(triangle, 'triangle_id', '')}",
                                )
                            )
                            generated_triangle_index += 1
                            generated_for_triangle += 1
                    exact_generated_triangle_count += generated_for_triangle
                    if generated_for_triangle:
                        continue
                exact_fallback_count += 1
            continue
        kept_triangles.append(triangle)
    if not clipped_refs:
        quality_rows = [
            row
            for row in list(getattr(tin_surface, "quality_rows", []) or [])
            if str(getattr(row, "kind", "") or "") not in {
                "roundabout_ownership_clip_status",
                "roundabout_ownership_clip_triangle_count",
                "roundabout_ownership_clip_tested_triangle_count",
                "roundabout_ownership_clip_radius",
                "roundabout_ownership_clip_surface_role",
                "roundabout_ownership_clip_boundary_source",
                "roundabout_ownership_clip_mode",
                "roundabout_ownership_clip_reason_summary",
                "roundabout_ownership_clip_centroid_inside_count",
                "roundabout_ownership_clip_vertex_inside_count",
                "roundabout_ownership_clip_edge_crosses_count",
                "roundabout_ownership_clip_center_inside_triangle_count",
                "roundabout_ownership_clip_fallback_reason",
                "roundabout_clip_boundary_crossing_candidate_count",
                "roundabout_clip_boundary_status",
                "roundabout_clip_boundary_role",
                "roundabout_clip_boundary_result_id",
                "roundabout_clip_boundary_loop_count",
                "roundabout_clip_boundary_segment_count",
                "roundabout_clip_boundary_loop_refs",
                "roundabout_clip_boundary_loop_bboxes",
                "roundabout_clip_boundary_loop_areas",
                "roundabout_clip_boundary_segment_refs",
                "roundabout_clip_boundary_diagnostics",
                "roundabout_actual_clip_boundary_roles",
                "roundabout_clip_exact_candidate_count",
                "roundabout_clip_exact_generated_triangle_count",
                "roundabout_clip_exact_fallback_count",
                "roundabout_clip_exact_supported",
                "roundabout_clip_exact_method",
                "roundabout_clip_exact_part_count",
            }
        ]
        quality_rows.extend(
            [
                TINQualityRow(
                    f"{tin_surface.surface_id}:roundabout-ownership-clip-status",
                    "roundabout_ownership_clip_status",
                    "ready",
                ),
                TINQualityRow(
                    f"{tin_surface.surface_id}:roundabout-ownership-clip-triangle-count",
                    "roundabout_ownership_clip_triangle_count",
                    0,
                    "count",
                ),
                TINQualityRow(
                    f"{tin_surface.surface_id}:roundabout-ownership-clip-tested-triangle-count",
                    "roundabout_ownership_clip_tested_triangle_count",
                    tested,
                    "count",
                ),
                TINQualityRow(
                    f"{tin_surface.surface_id}:roundabout-ownership-clip-radius",
                    "roundabout_ownership_clip_radius",
                    radius,
                    "m",
                ),
                TINQualityRow(
                    f"{tin_surface.surface_id}:roundabout-ownership-clip-surface-role",
                    "roundabout_ownership_clip_surface_role",
                    str(surface_role or ""),
                ),
                TINQualityRow(
                    f"{tin_surface.surface_id}:roundabout-ownership-clip-boundary-source",
                    "roundabout_ownership_clip_boundary_source",
                    str(boundary_summary.get("boundary_result_id", "") or spec.get("source", "") or ""),
                ),
                *_roundabout_clip_boundary_quality_rows(tin_surface.surface_id, boundary_summary),
                *_roundabout_clip_reason_quality_rows(
                    tin_surface.surface_id,
                    reason_counts,
                    clip_mode=clip_mode,
                    fallback_reason=fallback_reason,
                    exact_candidate_count=exact_candidate_count,
                    exact_generated_triangle_count=exact_generated_triangle_count,
                    exact_fallback_count=exact_fallback_count,
                    exact_supported=exact_supported,
                    exact_method=exact_method,
                    exact_part_count=len(exact_clip_parts),
                ),
            ]
        )
        return replace(tin_surface, quality_rows=quality_rows)
    clipped_surface = replace(tin_surface, vertex_rows=output_vertices, triangle_rows=kept_triangles)
    quality_rows = [
        row
        for row in list(getattr(clipped_surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "roundabout_ownership_clip_status",
            "roundabout_ownership_clip_triangle_count",
            "roundabout_ownership_clip_tested_triangle_count",
            "roundabout_ownership_clip_radius",
            "roundabout_ownership_clip_surface_role",
            "roundabout_ownership_clip_boundary_source",
            "roundabout_ownership_clip_triangle_refs",
            "roundabout_ownership_clip_mode",
            "roundabout_ownership_clip_reason_summary",
            "roundabout_ownership_clip_centroid_inside_count",
            "roundabout_ownership_clip_vertex_inside_count",
            "roundabout_ownership_clip_edge_crosses_count",
            "roundabout_ownership_clip_center_inside_triangle_count",
            "roundabout_ownership_clip_fallback_reason",
            "roundabout_clip_boundary_crossing_candidate_count",
            "roundabout_clip_boundary_status",
            "roundabout_clip_boundary_role",
            "roundabout_clip_boundary_result_id",
            "roundabout_clip_boundary_loop_count",
            "roundabout_clip_boundary_segment_count",
            "roundabout_clip_boundary_loop_refs",
            "roundabout_clip_boundary_loop_bboxes",
            "roundabout_clip_boundary_loop_areas",
            "roundabout_clip_boundary_segment_refs",
            "roundabout_clip_boundary_diagnostics",
            "roundabout_actual_clip_boundary_roles",
            "roundabout_clip_exact_candidate_count",
            "roundabout_clip_exact_generated_triangle_count",
            "roundabout_clip_exact_fallback_count",
            "roundabout_clip_exact_supported",
            "roundabout_clip_exact_method",
            "roundabout_clip_exact_part_count",
        }
    ]
    quality_rows.extend(
        [
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-status",
                "roundabout_ownership_clip_status",
                "ready",
            ),
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-triangle-count",
                "roundabout_ownership_clip_triangle_count",
                len(clipped_refs),
                "count",
            ),
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-tested-triangle-count",
                "roundabout_ownership_clip_tested_triangle_count",
                tested,
                "count",
            ),
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-radius",
                "roundabout_ownership_clip_radius",
                radius,
                "m",
            ),
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-surface-role",
                "roundabout_ownership_clip_surface_role",
                str(surface_role or ""),
            ),
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-boundary-source",
                "roundabout_ownership_clip_boundary_source",
                str(boundary_summary.get("boundary_result_id", "") or spec.get("source", "") or ""),
            ),
            TINQualityRow(
                f"{tin_surface.surface_id}:roundabout-ownership-clip-triangle-refs",
                "roundabout_ownership_clip_triangle_refs",
                ",".join(ref for ref in clipped_refs[:50] if ref),
            ),
            *_roundabout_clip_boundary_quality_rows(tin_surface.surface_id, boundary_summary),
            *_roundabout_clip_reason_quality_rows(
                tin_surface.surface_id,
                reason_counts,
                clip_mode=clip_mode,
                fallback_reason=fallback_reason,
                exact_candidate_count=exact_candidate_count,
                exact_generated_triangle_count=exact_generated_triangle_count,
                exact_fallback_count=exact_fallback_count,
                exact_supported=exact_supported,
                exact_method=exact_method,
                exact_part_count=len(exact_clip_parts),
            ),
        ]
    )
    return replace(clipped_surface, quality_rows=quality_rows)


def _point_segment_distance_with_ratio(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[float, float]:
    return xy_point_segment_distance_with_ratio((px, py), (x1, y1), (x2, y2))


def _intersection_slope_face_points_close_xy(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    return math.hypot(float(first[0]) - float(second[0]), float(first[1]) - float(second[1])) <= tolerance


def _xy_triangle_polygon_intersection_kind(triangle: list[tuple[float, float]], polygon: list[tuple[float, float]]) -> str:
    return xy_triangle_polygon_intersection_kind(triangle, polygon)


def _xy_closed_edges(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    return xy_closed_edges(points)


def _xy_polygon_area(points: list[tuple[float, float]]) -> float:
    return xy_polygon_signed_area(points)


def _xy_polygon_is_convex(points: list[tuple[float, float]]) -> bool:
    return xy_polygon_is_convex(points)


def _xy_subtract_convex_polygon_from_polygon(
    source_polygon: list[dict[str, object]],
    exclusion_polygon: list[tuple[float, float]],
) -> list[list[dict[str, object]]]:
    """Return source polygon fragments outside a convex exclusion polygon."""

    return subtract_convex_polygon_from_payload_polygon(source_polygon, exclusion_polygon)


def _xy_exact_cut_exclusion_parts(polygon: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    if len(polygon) < 3:
        return []
    if _xy_polygon_is_convex(polygon):
        return [polygon]
    triangles = _xy_triangulate_simple_polygon_points(polygon)
    return [triangle for triangle in triangles if len(triangle) == 3 and abs(_xy_polygon_area(triangle)) > 1.0e-9]


def _xy_subtract_convex_polygon_parts_from_polygon(
    source_polygon: list[dict[str, object]],
    exclusion_parts: list[list[tuple[float, float]]],
) -> list[list[dict[str, object]]]:
    fragments = [_dedupe_xy_points(source_polygon)]
    for exclusion_part in list(exclusion_parts or []):
        next_fragments: list[list[dict[str, object]]] = []
        for fragment in fragments:
            next_fragments.extend(_xy_subtract_convex_polygon_from_polygon(fragment, exclusion_part))
        fragments = [
            fragment for fragment in next_fragments
            if len(fragment) >= 3 and abs(_xy_polygon_area([(point["x"], point["y"]) for point in fragment])) > 1.0e-9
        ]
        if not fragments:
            break
    return fragments


def _xy_subtract_exclusion_area_from_polygon(
    source_polygon: list[dict[str, object]],
    *,
    exclusion_parts: list[list[tuple[float, float]]],
    hole_parts: list[list[tuple[float, float]]] | None = None,
) -> list[list[dict[str, object]]]:
    outside_fragments = _xy_subtract_convex_polygon_parts_from_polygon(source_polygon, exclusion_parts)
    hole_fragments: list[list[dict[str, object]]] = []
    for hole_part in list(hole_parts or []):
        clipped = _xy_intersect_polygon_with_convex_polygon(source_polygon, hole_part)
        if len(clipped) >= 3 and abs(_xy_polygon_area([(point["x"], point["y"]) for point in clipped])) > 1.0e-9:
            hole_fragments.append(clipped)
    return outside_fragments + hole_fragments


def _xy_intersect_polygon_with_convex_polygon(
    source_polygon: list[dict[str, object]],
    clip_polygon: list[tuple[float, float]],
) -> list[dict[str, object]]:
    return intersect_payload_polygon_with_convex_polygon(source_polygon, clip_polygon)


def _xy_triangulate_simple_polygon_points(points: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    indices = ear_clip_triangulation_indices(
        points,
        final_triangle_area_tolerance=1.0e-9,
    )
    return [[points[index] for index in triangle] for triangle in indices]


def _dedupe_xy_points(points: list[dict[str, object]]) -> list[dict[str, object]]:
    return dedupe_xy_payload_points(points)


def _roundabout_approach_roles_from_refs(refs: list[str]) -> list[str]:
    """Return stable approach role tokens from approach-leg source refs."""

    roles: list[str] = []
    for ref in refs:
        token = str(ref or "").strip().split(":")[-1]
        if token:
            roles.append(token)
    return _unique_text_values(roles)


def _xy_point_in_triangle(
    point: tuple[float, float],
    triangle: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> bool:
    return xy_point_in_triangle_strict(point, triangle)


# __SERVICE_BODY_END__


__all__ = ["clip_tin_surface_by_roundabout_ownership"]
