"""Clip typed TIN surfaces by accepted Intersection exclusion contracts."""

from __future__ import annotations

from dataclasses import replace

from ...models.result.tin_surface import TINTriangle, TINVertex
from ...services.geometry import (
    dedupe_xy_payload_points,
    ear_clip_triangulation_indices,
    intersect_payload_polygon_with_convex_polygon,
    subtract_convex_polygon_from_payload_polygon,
    xy_closed_edges,
    xy_point_in_polygon,
    xy_point_segment_distance_with_ratio,
    xy_polygon_is_convex,
    xy_polygon_signed_area,
    xy_segment_distance,
    xy_triangle_polygon_intersection_kind,
)
from .intersection_exclusion_geometry_service import (
    xy_triangle_intrudes_pavement_strip_protection,
    xy_triangle_near_curb_return_arc_protection,
)


def clip_tin_surface_by_intersection_exclusion(
    surface,
    *,
    exclusion,
    source_control_section_indices=(),
    surface_role: str,
):
    """Return a preview TIN with triangles inside the intersection exclusion polygon suppressed."""

    if exclusion is None:
        return surface
    practical_status = str(exclusion.get("practical_footprint_status", "") or "").strip().lower()
    if practical_status in {"missing", "degraded"}:
        return _surface_with_intersection_exclusion_quality(
            surface,
            surface_role=surface_role,
            exclusion=exclusion,
            clipped_count=0,
            kept_count=len(list(getattr(surface, "triangle_rows", []) or [])),
            exact_cut_candidate_count=0,
            boundary_crossing_count=0,
            exact_cut_generated_triangle_count=0,
            exact_cut_supported=False,
            exact_cut_method=f"conservative_skip_{practical_status}_practical_footprint",
            exact_cut_part_count=0,
            daylight_protection_offset=0.0,
            control_section_clipped_count=0,
        )
    polygon = list(exclusion.get("points", []) or [])
    if len(polygon) < 3:
        return surface
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
    }
    output_vertices = list(getattr(surface, "vertex_rows", []) or [])
    generated_vertex_index = 1
    generated_triangle_index = 1
    kept = []
    clipped_count = 0
    exact_cut_candidate_count = 0
    boundary_crossing_count = 0
    exact_cut_generated_triangle_count = 0
    exact_cut_parts = _xy_exact_cut_exclusion_parts(polygon)
    exact_cut_island_parts = [
        part
        for island in list(exclusion.get("islands", []) or [])
        for part in _xy_exact_cut_exclusion_parts(list(island or []))
    ]
    exact_cut_hole_parts = [
        part
        for hole in list(exclusion.get("holes", []) or [])
        for part in _xy_exact_cut_exclusion_parts(list(hole or []))
    ]
    exact_cut_polygon_supported = bool(exact_cut_parts) and all(len(part) >= 3 for part in exact_cut_hole_parts + exact_cut_island_parts)
    exact_cut_part_count = len(exact_cut_parts) + len(exact_cut_island_parts) + len(exact_cut_hole_parts)
    exact_cut_method = "exact_convex_polygon" if exact_cut_part_count == 1 else "exact_multiring_polygon" if exact_cut_hole_parts or exact_cut_island_parts else "exact_triangulated_polygon"
    hard_suppress = str(surface_role or "").strip().lower() == "daylight"
    test_polygon = polygon
    daylight_protection_offset = 0.0
    control_section_indices: set[int] = set(source_control_section_indices or ())
    if hard_suppress:
        daylight_protection_offset = _intersection_daylight_protection_offset(
            exclusion,
            polygon,
        )
        test_polygon = _xy_expand_polygon_from_centroid(
            polygon,
            daylight_protection_offset,
        )
        exact_cut_polygon_supported = False
        exact_cut_method = "hard_suppress_intersection"
    control_section_clipped_count = 0
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        vertices = [vertex_map.get(str(ref or "")) for ref in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", ""))]
        if any(vertex is None for vertex in vertices):
            kept.append(triangle)
            continue
        triangle_points = [
            (float(getattr(vertex, "x", 0.0) or 0.0), float(getattr(vertex, "y", 0.0) or 0.0))
            for vertex in vertices
        ]
        geometry_intersection_kind = _xy_triangle_polygon_intersection_kind(triangle_points, test_polygon)
        source_intersection_control = bool(
            hard_suppress
            and _slope_face_triangle_uses_intersection_control_section(
                triangle,
                control_section_indices=control_section_indices,
            )
        )
        curb_return_daylight_protection = bool(
            hard_suppress
            and xy_triangle_near_curb_return_arc_protection(
                triangle_points,
                list(exclusion.get("curb_return_arc_polylines", []) or []),
                max_distance=daylight_protection_offset,
            )
        )
        pavement_strip_protection = bool(
            hard_suppress
            and xy_triangle_intrudes_pavement_strip_protection(
                triangle_points,
                list(exclusion.get("pavement_strip_polygons", []) or []),
            )
        )
        intersection_kind = (
            "intersection_control_section"
            if source_intersection_control
            else "curb_return_daylight_protection"
            if curb_return_daylight_protection
            else "intersection_pavement_strip_protection"
            if pavement_strip_protection
            else geometry_intersection_kind
        )
        if intersection_kind:
            clipped_count += 1
            if intersection_kind == "edge_crossing":
                boundary_crossing_count += 1
            if intersection_kind in {"intersection_control_section", "curb_return_daylight_protection", "intersection_pavement_strip_protection"}:
                control_section_clipped_count += 1
            exact_cut_candidate = (
                intersection_kind not in {"intersection_control_section", "curb_return_daylight_protection", "intersection_pavement_strip_protection"}
                and not all(_xy_point_in_polygon(point, test_polygon) for point in triangle_points[:3])
            )
            if exact_cut_candidate:
                exact_cut_candidate_count += 1
            if exact_cut_candidate and exact_cut_polygon_supported and not hard_suppress:
                triangle_polygon = [
                    {
                        "x": float(getattr(vertex, "x", 0.0) or 0.0),
                        "y": float(getattr(vertex, "y", 0.0) or 0.0),
                        "z": float(getattr(vertex, "z", 0.0) or 0.0),
                        "source": str(getattr(vertex, "vertex_id", "") or ""),
                    }
                    for vertex in vertices
                ]
                fragments = _xy_subtract_exclusion_area_from_polygon(
                    triangle_polygon,
                    exclusion_parts=exact_cut_parts + exact_cut_island_parts,
                    hole_parts=exact_cut_hole_parts,
                )
                for fragment in fragments:
                    if len(fragment) < 3 or abs(_xy_polygon_area([(point["x"], point["y"]) for point in fragment])) <= 1.0e-9:
                        continue
                    fragment_vertex_ids = []
                    for point in fragment:
                        vertex_id = f"{str(getattr(surface, 'surface_id', '') or surface_role)}:intersection-exact:v{generated_vertex_index}"
                        generated_vertex_index += 1
                        output_vertices.append(
                            TINVertex(
                                vertex_id=vertex_id,
                                x=float(point["x"]),
                                y=float(point["y"]),
                                z=float(point["z"]),
                                source_point_ref=str(point.get("source", "") or ""),
                                notes=f"exact intersection exclusion fragment from {getattr(triangle, 'triangle_id', '')}",
                            )
                        )
                        fragment_vertex_ids.append(vertex_id)
                    for index in range(1, len(fragment_vertex_ids) - 1):
                        kept.append(
                            TINTriangle(
                                triangle_id=f"{getattr(triangle, 'triangle_id', 'triangle')}:intersection-exact:{generated_triangle_index}",
                                v1=fragment_vertex_ids[0],
                                v2=fragment_vertex_ids[index],
                                v3=fragment_vertex_ids[index + 1],
                                triangle_kind=str(getattr(triangle, "triangle_kind", "") or "primary_triangle"),
                                quality_ref="intersection_exclusion_exact_cut",
                                notes=f"generated outside exclusion fragment from {getattr(triangle, 'triangle_id', '')}",
                            )
                        )
                        generated_triangle_index += 1
                        exact_cut_generated_triangle_count += 1
            continue
        kept.append(triangle)
    if clipped_count <= 0:
        near_boundary_kept_count, max_kept_boundary_distance, near_boundary_kept_rows = _intersection_exclusion_kept_boundary_diagnostics(
            surface,
            kept,
            polygon,
        )
        return _surface_with_intersection_exclusion_quality(
            surface,
            surface_role=surface_role,
            exclusion=exclusion,
            clipped_count=0,
            kept_count=len(kept),
            exact_cut_candidate_count=0,
            boundary_crossing_count=0,
            exact_cut_generated_triangle_count=0,
            exact_cut_supported=exact_cut_polygon_supported,
            exact_cut_method=exact_cut_method,
            exact_cut_part_count=exact_cut_part_count,
            daylight_protection_offset=daylight_protection_offset,
            control_section_clipped_count=control_section_clipped_count,
            near_boundary_kept_count=near_boundary_kept_count,
            max_kept_boundary_distance=max_kept_boundary_distance,
            near_boundary_kept_rows=near_boundary_kept_rows,
        )
    near_boundary_kept_count, max_kept_boundary_distance, near_boundary_kept_rows = _intersection_exclusion_kept_boundary_diagnostics(
        replace(surface, vertex_rows=output_vertices, triangle_rows=kept),
        kept,
        polygon,
    )
    return _surface_with_intersection_exclusion_quality(
        replace(surface, vertex_rows=output_vertices, triangle_rows=kept),
        surface_role=surface_role,
        exclusion=exclusion,
        clipped_count=clipped_count,
        kept_count=len(kept),
        exact_cut_candidate_count=exact_cut_candidate_count,
        boundary_crossing_count=boundary_crossing_count,
        exact_cut_generated_triangle_count=exact_cut_generated_triangle_count,
        exact_cut_supported=exact_cut_polygon_supported,
        exact_cut_method=exact_cut_method,
        exact_cut_part_count=exact_cut_part_count,
        daylight_protection_offset=daylight_protection_offset,
        control_section_clipped_count=control_section_clipped_count,
        near_boundary_kept_count=near_boundary_kept_count,
        max_kept_boundary_distance=max_kept_boundary_distance,
        near_boundary_kept_rows=near_boundary_kept_rows,
    )


def _intersection_daylight_protection_offset(
    exclusion: dict[str, object],
    polygon: list[tuple[float, float]],
) -> float:
    points = list(polygon or [])
    if len(points) < 3:
        return 0.0
    area = abs(float(exclusion.get("area", 0.0) or xy_polygon_signed_area(points)))
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    bbox_axis = max(max(xs) - min(xs), max(ys) - min(ys))
    area_scale = area ** 0.5 if area > 0.0 else 0.0
    return max(4.0, min(max(area_scale * 0.18, bbox_axis * 0.08), 8.0))


def _xy_expand_polygon_from_centroid(
    points: list[tuple[float, float]],
    offset: float,
) -> list[tuple[float, float]]:
    if len(points) < 3 or float(offset or 0.0) <= 0.0:
        return list(points or [])
    centroid = (
        sum(float(point[0]) for point in points) / len(points),
        sum(float(point[1]) for point in points) / len(points),
    )
    expanded: list[tuple[float, float]] = []
    for point in points:
        dx = float(point[0]) - centroid[0]
        dy = float(point[1]) - centroid[1]
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= 1.0e-9:
            expanded.append((float(point[0]), float(point[1])))
            continue
        scale = (distance + float(offset or 0.0)) / distance
        expanded.append((centroid[0] + dx * scale, centroid[1] + dy * scale))
    return expanded


def _intersection_exclusion_kept_boundary_diagnostics(
    surface,
    kept_triangles: list[object],
    polygon: list[tuple[float, float]],
    *,
    near_distance: float = 0.25,
) -> tuple[int, float, list[str]]:
    if surface is None or len(polygon) < 3:
        return 0, 0.0, []
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
        if str(getattr(vertex, "vertex_id", "") or "")
    }
    near_count = 0
    max_distance = 0.0
    rows: list[str] = []
    for triangle in list(kept_triangles or []):
        vertices = [
            vertex_map.get(str(ref or ""))
            for ref in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", ""))
        ]
        if any(vertex is None for vertex in vertices):
            continue
        points = [
            (float(getattr(vertex, "x", 0.0) or 0.0), float(getattr(vertex, "y", 0.0) or 0.0))
            for vertex in vertices
        ]
        distance = _xy_triangle_min_distance_to_polygon(points, polygon)
        if distance <= float(near_distance or 0.0):
            near_count += 1
            max_distance = max(max_distance, distance)
            centroid_x = sum(point[0] for point in points[:3]) / 3.0
            centroid_y = sum(point[1] for point in points[:3]) / 3.0
            centroid_z = sum(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices[:3]) / 3.0
            triangle_id = str(getattr(triangle, "triangle_id", "") or "")
            rows.append(
                "|".join(
                    [
                        triangle_id.replace("|", "_"),
                        f"{centroid_x:.9g}",
                        f"{centroid_y:.9g}",
                        f"{centroid_z:.9g}",
                        f"{distance:.9g}",
                    ]
                )
            )
    return near_count, max_distance, rows


def _xy_triangle_min_distance_to_polygon(
    triangle: list[tuple[float, float]],
    polygon: list[tuple[float, float]],
) -> float:
    if len(triangle) < 3 or len(polygon) < 3:
        return 0.0
    distances: list[float] = []
    polygon_edges = _xy_closed_edges(polygon)
    triangle_edges = _xy_closed_edges(triangle[:3])
    for point in triangle[:3]:
        for start, end in polygon_edges:
            distances.append(_point_segment_distance_with_ratio(point[0], point[1], start[0], start[1], end[0], end[1])[0])
    for point in polygon:
        for start, end in triangle_edges:
            distances.append(_point_segment_distance_with_ratio(point[0], point[1], start[0], start[1], end[0], end[1])[0])
    for tri_start, tri_end in triangle_edges:
        for poly_start, poly_end in polygon_edges:
            distances.append(_xy_segment_distance(tri_start, tri_end, poly_start, poly_end))
    return min(distances) if distances else 0.0


def _surface_with_intersection_exclusion_quality(
    surface,
    *,
    surface_role: str,
    exclusion: dict[str, object],
    clipped_count: int,
    kept_count: int,
    exact_cut_candidate_count: int = 0,
    boundary_crossing_count: int = 0,
    exact_cut_generated_triangle_count: int = 0,
    exact_cut_supported: bool = False,
    exact_cut_method: str = "exact_convex_polygon",
    exact_cut_part_count: int = 0,
    daylight_protection_offset: float = 0.0,
    control_section_clipped_count: int = 0,
    near_boundary_kept_count: int = 0,
    max_kept_boundary_distance: float = 0.0,
    near_boundary_kept_rows: list[str] | None = None,
):
    from ...models.result.tin_surface import TINQualityRow

    quality_rows = [
        row for row in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in {
            "intersection_exclusion_status",
            "intersection_exclusion_boundary_source",
            "intersection_exclusion_boundary_strategy",
            "intersection_exclusion_boundary_loop_result_id",
            "intersection_exclusion_boundary_loop_id",
            "intersection_exclusion_boundary_loop_point_count",
            "intersection_exclusion_boundary_loop_segment_count",
            "intersection_exclusion_practical_boundary_aligned",
            "intersection_exclusion_point_count",
            "intersection_exclusion_area",
            "intersection_exclusion_clip_method",
            "intersection_exclusion_tested_triangle_count",
            "intersection_exclusion_clip_ratio",
            "intersection_exclusion_clipped_triangle_count",
            "intersection_exclusion_kept_triangle_count",
            "intersection_exclusion_boundary_crossing_triangle_count",
            "intersection_exclusion_near_boundary_kept_triangle_count",
            "intersection_exclusion_max_kept_boundary_distance",
            "intersection_exclusion_near_boundary_kept_triangle_rows",
            "intersection_exclusion_exact_cut_candidate_count",
            "intersection_exclusion_exact_cut_recommended",
            "intersection_exclusion_exact_cut_generated_triangle_count",
            "intersection_exclusion_exact_cut_supported",
            "intersection_exclusion_exact_cut_part_count",
            "intersection_exclusion_hole_ring_count",
            "intersection_exclusion_island_ring_count",
            "intersection_exclusion_daylight_protection_offset",
            "intersection_exclusion_control_section_clipped_triangle_count",
            "intersection_exclusion_practical_footprint_status",
            "intersection_exclusion_practical_footprint_diagnostics",
        }
    ]
    practical_status = str(
        exclusion.get("practical_footprint_status", "")
        or ("ready" if bool(exclusion.get("practical_boundary_aligned", False)) else str(exclusion.get("status", "") or ""))
    )
    practical_diagnostics = [
        str(value or "")
        for value in list(
            exclusion.get("practical_footprint_diagnostics", [])
            or exclusion.get("diagnostics", [])
            or []
        )
        if str(value or "")
    ]
    surface_id = str(getattr(surface, "surface_id", "") or f"{surface_role}:surface")
    hard_suppressed = str(exact_cut_method or "") == "hard_suppress_intersection"
    tested_count = int(clipped_count or 0) + int(kept_count or 0)
    clip_ratio = (float(clipped_count or 0) / float(tested_count)) if tested_count > 0 else 0.0
    exact_cut_recommended = 0 if hard_suppressed else 1 if int(exact_cut_candidate_count or 0) > int(exact_cut_generated_triangle_count or 0) else 0
    clip_method = (
        "hard_suppress_intersection"
        if hard_suppressed
        else str(exact_cut_method or "")
        if str(exact_cut_method or "").startswith("conservative_skip_")
        else str(exact_cut_method or "exact_convex_polygon") if int(exact_cut_generated_triangle_count or 0) > 0
        else "centroid_or_intersection"
    )
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:intersection_exclusion_status", "intersection_exclusion_status", str(exclusion.get("status", "") or "ready")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_source", "intersection_exclusion_boundary_source", str(exclusion.get("boundary_source", "") or "patch_boundary")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_strategy", "intersection_exclusion_boundary_strategy", str(exclusion.get("boundary_strategy", "") or "ordered_patch_boundary")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_loop_result_id", "intersection_exclusion_boundary_loop_result_id", str(exclusion.get("boundary_loop_result_id", "") or "")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_loop_id", "intersection_exclusion_boundary_loop_id", str(exclusion.get("boundary_loop_id", "") or "")),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_loop_point_count", "intersection_exclusion_boundary_loop_point_count", int(exclusion.get("boundary_loop_point_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_loop_segment_count", "intersection_exclusion_boundary_loop_segment_count", int(exclusion.get("boundary_loop_segment_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_practical_boundary_aligned", "intersection_exclusion_practical_boundary_aligned", 1 if bool(exclusion.get("practical_boundary_aligned", False)) else 0, "bool"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_point_count", "intersection_exclusion_point_count", len(list(exclusion.get("points", []) or [])), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_area", "intersection_exclusion_area", float(exclusion.get("area", 0.0) or 0.0), "m2"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_clip_method", "intersection_exclusion_clip_method", clip_method),
            TINQualityRow(f"{surface_id}:intersection_exclusion_tested_triangle_count", "intersection_exclusion_tested_triangle_count", tested_count, "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_clip_ratio", "intersection_exclusion_clip_ratio", clip_ratio, "ratio"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_clipped_triangle_count", "intersection_exclusion_clipped_triangle_count", int(clipped_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_kept_triangle_count", "intersection_exclusion_kept_triangle_count", int(kept_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_boundary_crossing_triangle_count", "intersection_exclusion_boundary_crossing_triangle_count", int(boundary_crossing_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_near_boundary_kept_triangle_count", "intersection_exclusion_near_boundary_kept_triangle_count", int(near_boundary_kept_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_max_kept_boundary_distance", "intersection_exclusion_max_kept_boundary_distance", float(max_kept_boundary_distance or 0.0), "m"),
            TINQualityRow(
                f"{surface_id}:intersection_exclusion_near_boundary_kept_triangle_rows",
                "intersection_exclusion_near_boundary_kept_triangle_rows",
                ";;".join(list(near_boundary_kept_rows or [])),
                "rows",
            ),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_candidate_count", "intersection_exclusion_exact_cut_candidate_count", int(exact_cut_candidate_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_recommended", "intersection_exclusion_exact_cut_recommended", exact_cut_recommended, "bool"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_generated_triangle_count", "intersection_exclusion_exact_cut_generated_triangle_count", int(exact_cut_generated_triangle_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_supported", "intersection_exclusion_exact_cut_supported", 1 if exact_cut_supported else 0, "bool"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_exact_cut_part_count", "intersection_exclusion_exact_cut_part_count", int(exact_cut_part_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_hole_ring_count", "intersection_exclusion_hole_ring_count", len(list(exclusion.get("holes", []) or [])), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_island_ring_count", "intersection_exclusion_island_ring_count", len(list(exclusion.get("islands", []) or [])), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_daylight_protection_offset", "intersection_exclusion_daylight_protection_offset", float(daylight_protection_offset or 0.0), "m"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_control_section_clipped_triangle_count", "intersection_exclusion_control_section_clipped_triangle_count", int(control_section_clipped_count), "count"),
            TINQualityRow(f"{surface_id}:intersection_exclusion_practical_footprint_status", "intersection_exclusion_practical_footprint_status", practical_status),
            TINQualityRow(f"{surface_id}:intersection_exclusion_practical_footprint_diagnostics", "intersection_exclusion_practical_footprint_diagnostics", "; ".join(practical_diagnostics)),
        ]
    )
    void_refs = list(getattr(surface, "void_refs", []) or [])
    exclusion_ref = str(exclusion.get("intersection_id", "") or "intersection")
    if exclusion_ref not in void_refs:
        void_refs.append(exclusion_ref)
    return replace(surface, quality_rows=quality_rows, void_refs=void_refs)


def _point_segment_distance_with_ratio(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[float, float]:
    return xy_point_segment_distance_with_ratio((px, py), (x1, y1), (x2, y2))


def _slope_face_triangle_uses_intersection_control_section(triangle, *, control_section_indices: set[int]) -> bool:
    if not control_section_indices:
        return False
    candidate_indices: set[int] = set()
    for value in (getattr(triangle, "v1", ""), getattr(triangle, "v2", ""), getattr(triangle, "v3", "")):
        parsed = _parse_slope_face_vertex_id(str(value or ""))
        if parsed is not None:
            candidate_indices.add(int(parsed[0]))
    candidate_indices.update(_parse_slope_face_triangle_span_section_indices(str(getattr(triangle, "triangle_id", "") or "")))
    return bool(candidate_indices.intersection(control_section_indices))


def _parse_slope_face_triangle_span_section_indices(triangle_id: str) -> set[int]:
    parts = str(triangle_id or "").split(":")
    indices: set[int] = set()
    for index, token in enumerate(parts[:-1]):
        if token != "span":
            continue
        try:
            span_index = int(parts[index + 1])
        except Exception:
            continue
        indices.add(span_index)
        indices.add(span_index + 1)
    return indices


def _xy_point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    return xy_point_in_polygon(point, polygon)


def _xy_triangle_polygon_intersection_kind(triangle: list[tuple[float, float]], polygon: list[tuple[float, float]]) -> str:
    return xy_triangle_polygon_intersection_kind(triangle, polygon)


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


def _parse_slope_face_vertex_id(vertex_id: str) -> tuple[int, str] | None:
    parts = str(vertex_id or "").split(":")
    if len(parts) < 3:
        return None
    for part_index in range(len(parts) - 1):
        token = str(parts[part_index] or "")
        if not token.startswith("v"):
            continue
        try:
            index = int(token[1:])
        except Exception:
            continue
        side = str(parts[part_index + 1] or "").strip().lower()
        if side not in {"left", "right"}:
            continue
        return index, "L" if side == "left" else "R"
    return None


# __SERVICE_BODY_END__


__all__ = ["clip_tin_surface_by_intersection_exclusion"]
