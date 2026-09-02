"""Build Intersection slope-face TINs from accepted result contracts."""

from __future__ import annotations

import math
from dataclasses import replace

from ...models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
)
from ...models.result.intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryGraphResult,
)
from ...models.result.intersection_slope_face_boundary import (
    IntersectionSlopeFaceBoundaryResult,
)
from ...models.result.intersection_slope_face_cell import (
    IntersectionSlopeFaceCellResult,
)
from ...models.result.intersection_slope_face_loop import (
    IntersectionSlopeFaceLoopResult,
)
from ...models.result.shared_breakline import (
    SharedBreaklineResult,
    SharedBreaklineRow,
)
from ...models.result.tin_surface import (
    TINQualityRow,
    TINSurface,
    TINTriangle,
    TINVertex,
)
from ...services.geometry import (
    xy_distance,
    xy_polygon_self_intersects,
    xy_polygon_signed_area,
    xy_triangle_quality_ratio,
    xy_triangle_signed_area,
    xyz_point,
)
from ..evaluation.intersection_shared_boundary_graph_evaluation_service import (
    IntersectionSharedBoundaryGraphEvaluationRequest,
    IntersectionSharedBoundaryGraphEvaluationService,
    intersection_shared_boundary_graph_audit,
)
from ..evaluation.intersection_slope_face_cell_evaluation_service import (
    IntersectionSlopeFaceCellEvaluationRequest,
    IntersectionSlopeFaceCellEvaluationService,
)


_INTERSECTION_BOUNDARY_LOOP_AUDIT_CONSUMERS = (
    "intersection_surface",
    "design_surface",
    "intersection_slope_face_surface",
    "slope_face_surface",
    "intersection_tie_slope_surface",
)


def _intersection_shared_boundary_graph_edge_role_is_internal_seam(role: str) -> bool:
    return str(role or "") in {"upper_transition_internal_seam", "cell_closure_internal_seam"}


def _format_count_summary(counts: dict[str, int], *, limit: int = 5) -> str:
    if not counts:
        return "none"
    rows = sorted(((str(key), int(value)) for key, value in counts.items()), key=lambda item: (-item[1], item[0]))
    text = ", ".join(f"{_display_source_ref(key)}:{value}" for key, value in rows[:limit])
    if len(rows) > limit:
        text += f", +{len(rows) - limit} more"
    return text


def _xy_xyz_polygon_self_crossing(points: list[tuple[float, float, float]]) -> bool:
    return xy_polygon_self_intersects(points)


def _xyz_tuple(point) -> tuple[float, float, float]:
    return xyz_point(point)


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"


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


def _display_source_ref(value: object) -> str:
    text = str(value or "").strip()
    if ":" not in text:
        return text
    return text.split(":", 1)[1]


def _intersection_slope_face_loop_surface_generation_ready(row) -> bool:
    if row is None:
        return False
    return (
        str(getattr(row, "status", "") or "") == "ready"
        and str(getattr(row, "surface_generation_role", "") or "") == "surface_candidate"
        and str(getattr(row, "surface_generation_status", "") or "") == "ready"
        and _intersection_slope_face_loop_has_dedicated_perimeter_source(row)
        and bool(getattr(row, "closed_xy", False))
        and not bool(getattr(row, "self_crossing", False))
        and len(_intersection_slope_face_loop_simple_ring_points(row)) >= 3
    )


def _append_intersection_upper_slope_face_panel_tin(
    *,
    surface_id: str,
    candidate_rows: list[dict[str, object]],
    vertices: list[TINVertex],
    triangles: list[TINTriangle],
) -> dict[str, object]:
    """Append two-triangle rectangular panels from accepted upper panel candidates."""

    diagnostics: list[str] = []
    panel_refs: list[str] = []
    boundary_refs: list[str] = []
    panel_count = 0
    triangle_count = 0
    for panel_index, row in enumerate(list(candidate_rows or []), start=1):
        panel_id = str(row.get("candidate_id", "") or f"intersection-upper-slope-face-panel:{panel_index}")
        if str(row.get("status", "") or "") != "accepted":
            diagnostics.append(f"upper_panel_not_accepted:{panel_id}")
            continue
        points = [
            _xyz_tuple(point)
            for point in list(row.get("loop_points_xyz", ()) or ())
            if len(tuple(point or ())) >= 3
        ]
        if len(points) >= 2 and _intersection_slope_face_points_close_xy(points[0], points[-1]):
            points = points[:-1]
        points = _intersection_slope_face_simplified_closed_loop(points)
        if len(points) >= 2 and _intersection_slope_face_points_close_xy(points[0], points[-1]):
            points = points[:-1]
        if len(points) != 4:
            diagnostics.append(f"upper_panel_quad_points_invalid:{panel_id}:points={len(points)}")
            continue
        area = abs(_xy_polygon_area([(point[0], point[1]) for point in points]))
        if area <= 1.0e-6:
            diagnostics.append(f"upper_panel_zero_area:{panel_id}")
            continue
        if _xy_xyz_polygon_self_crossing(points):
            diagnostics.append(f"upper_panel_self_crossing:{panel_id}")
            continue

        panel_count += 1
        panel_refs.append(panel_id)
        boundary_refs.extend(
            str(value or "")
            for value in (
                row.get("inner_edge_ref", ""),
                row.get("outer_edge_ref", ""),
                row.get("left_cap_ref", ""),
                row.get("right_cap_ref", ""),
                *tuple(row.get("source_shared_breakline_refs", ()) or ()),
            )
            if str(value or "")
        )
        vertex_ids: list[str] = []
        for point_index, point in enumerate(points, start=1):
            vertex_id = f"{surface_id}:upper-panel-{panel_index:02d}:p-{point_index:02d}"
            vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=panel_id,
                    notes="upper rectangular Intersection Slope Face Surface panel vertex",
                )
            )
        first = _triangle_vertex_ids_with_upward_xy_normal(
            vertex_ids[0], points[0],
            vertex_ids[1], points[1],
            vertex_ids[2], points[2],
        )
        second = _triangle_vertex_ids_with_upward_xy_normal(
            vertex_ids[0], points[0],
            vertex_ids[2], points[2],
            vertex_ids[3], points[3],
        )
        triangles.append(
            TINTriangle(
                triangle_id=f"{surface_id}:upper-panel-{panel_index:02d}:tri-01",
                v1=first[0],
                v2=first[1],
                v3=first[2],
                triangle_kind="intersection_upper_slope_face_panel",
                quality_ref="intersection_upper_slope_face_panel",
                notes=panel_id,
            )
        )
        triangles.append(
            TINTriangle(
                triangle_id=f"{surface_id}:upper-panel-{panel_index:02d}:tri-02",
                v1=second[0],
                v2=second[1],
                v3=second[2],
                triangle_kind="intersection_upper_slope_face_panel",
                quality_ref="intersection_upper_slope_face_panel",
                notes=panel_id,
            )
        )
        triangle_count += 2
    return {
        "generation_mode": "upper_rectangular_panel" if panel_count else "no_accepted_upper_panel",
        "panel_count": panel_count,
        "triangle_count": triangle_count,
        "panel_refs": _unique_text_values(panel_refs),
        "boundary_refs": _unique_text_values(boundary_refs),
        "diagnostics": _unique_text_values(diagnostics),
    }


def _append_intersection_slope_face_cell_tin(
    *,
    surface_id: str,
    cell_result: IntersectionSlopeFaceCellResult | None,
    shared_breakline_result: SharedBreaklineResult | None,
    skip_upper_cells: bool = False,
    skip_upper_reason: str = "cell_superseded_by_shared_boundary_graph",
    vertices: list[TINVertex],
    triangles: list[TINTriangle],
) -> dict[str, object]:
    """Append strip triangles from ready IntersectionSlopeFaceCellResult rows."""

    if cell_result is None or shared_breakline_result is None:
        return {
            "generation_mode": "missing_cell_result",
            "cell_count": 0,
            "triangle_count": 0,
            "cell_refs": [],
            "boundary_refs": [],
            "diagnostics": ["intersection_slope_face_cell_result_missing"],
        }
    diagnostics: list[str] = []
    cell_refs: list[str] = []
    boundary_refs: list[str] = []
    generated_cell_roles: list[str] = []
    generated_upper_cell_refs: list[str] = []
    suppressed_upper_cell_refs: list[str] = []
    cell_count = 0
    triangle_count = 0
    for cell_index, row in enumerate(list(getattr(cell_result, "cell_rows", []) or []), start=1):
        cell_id = str(getattr(row, "cell_id", "") or f"cell:{cell_index}")
        if str(getattr(row, "status", "") or "") != "ready":
            diagnostics.append(f"cell_not_ready:{cell_id}")
            continue
        cell_role = str(getattr(row, "cell_role", "") or "")
        if skip_upper_cells and cell_role.startswith("upper_"):
            cell_refs.append(cell_id)
            generated_upper_cell_refs.append(cell_id)
            suppressed_upper_cell_refs.append(cell_id)
            boundary_refs.extend(str(ref or "") for ref in tuple(getattr(row, "boundary_breakline_refs", ()) or ()) if str(ref or ""))
            diagnostics.append(f"{str(skip_upper_reason or 'upper_cell_suppressed')}:{cell_id}")
            continue
        if cell_role.startswith("upper_"):
            inner_ref = str(getattr(row, "inner_breakline_ref", "") or "")
            outer_ref = str(getattr(row, "outer_breakline_ref", "") or "")
            triangle_kind = "intersection_slope_face_upper_transition_cell"
        elif cell_role.startswith("main_to_side_"):
            cell_refs.append(cell_id)
            boundary_refs.extend(str(ref or "") for ref in tuple(getattr(row, "boundary_breakline_refs", ()) or ()) if str(ref or ""))
            diagnostics.append(f"cell_main_side_tie_metadata_only:{cell_id}")
            continue
        elif cell_role.startswith("curb_return_"):
            inner_ref = str(getattr(row, "inner_breakline_ref", "") or "")
            outer_ref = str(getattr(row, "arc_breakline_ref", "") or getattr(row, "outer_breakline_ref", "") or "")
            triangle_kind = "intersection_slope_face_curb_return_cell"
        else:
            diagnostics.append(f"cell_role_not_supported:{cell_id}:{cell_role}")
            continue
        inner_points, outer_points = _intersection_slope_face_cell_surface_samples(row)
        if not inner_points or not outer_points:
            inner_points = _shared_breakline_points_xyz(shared_breakline_result, inner_ref)
            outer_points = _shared_breakline_points_xyz(shared_breakline_result, outer_ref)
        if len(inner_points) < 2 or len(outer_points) < 2:
            diagnostics.append(f"cell_breakline_points_too_few:{cell_id}")
            continue
        sample_count = max(len(inner_points), len(outer_points), 2)
        inner_samples = _resample_polyline_xyz(inner_points, sample_count)
        outer_samples = _resample_polyline_xyz(outer_points, sample_count)
        if len(inner_samples) != len(outer_samples) or len(inner_samples) < 2:
            diagnostics.append(f"cell_resample_failed:{cell_id}")
            continue
        cell_count += 1
        cell_refs.append(cell_id)
        generated_cell_roles.append(cell_role)
        if cell_role.startswith("upper_"):
            generated_upper_cell_refs.append(cell_id)
        boundary_refs.extend(str(ref or "") for ref in tuple(getattr(row, "boundary_breakline_refs", ()) or ()) if str(ref or ""))
        inner_vertex_ids: list[str] = []
        outer_vertex_ids: list[str] = []
        for point_index, point in enumerate(inner_samples, start=1):
            vertex_id = f"{surface_id}:cell-{cell_index:02d}:inner-{point_index:02d}"
            inner_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=cell_id,
                    notes=f"intersection slope-face cell inner point; role={cell_role}",
                )
            )
        for point_index, point in enumerate(outer_samples, start=1):
            vertex_id = f"{surface_id}:cell-{cell_index:02d}:outer-{point_index:02d}"
            outer_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=cell_id,
                    notes=f"intersection slope-face cell outer point; role={cell_role}",
                )
            )
        for segment_index in range(len(inner_vertex_ids) - 1):
            p00 = inner_samples[segment_index]
            p01 = inner_samples[segment_index + 1]
            p10 = outer_samples[segment_index]
            p11 = outer_samples[segment_index + 1]
            id00 = inner_vertex_ids[segment_index]
            id01 = inner_vertex_ids[segment_index + 1]
            id10 = outer_vertex_ids[segment_index]
            id11 = outer_vertex_ids[segment_index + 1]
            first = _triangle_vertex_ids_with_upward_xy_normal(id00, p00, id10, p10, id11, p11)
            second = _triangle_vertex_ids_with_upward_xy_normal(id00, p00, id11, p11, id01, p01)
            triangle_count += 2
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:cell-{cell_index:02d}:tri-{segment_index + 1:02d}a",
                    v1=first[0],
                    v2=first[1],
                    v3=first[2],
                    triangle_kind=triangle_kind,
                    quality_ref="intersection_slope_face_cell",
                    notes=cell_id,
                )
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:cell-{cell_index:02d}:tri-{segment_index + 1:02d}b",
                    v1=second[0],
                    v2=second[1],
                    v3=second[2],
                    triangle_kind=triangle_kind,
                    quality_ref="intersection_slope_face_cell",
                    notes=cell_id,
                )
            )
    return {
        "generation_mode": "cell_strip" if cell_count else "no_ready_cell",
        "cell_count": cell_count,
        "triangle_count": triangle_count,
        "cell_refs": _unique_text_values(cell_refs),
        "cell_role_summary": _format_count_summary(
            {role: generated_cell_roles.count(role) for role in _unique_text_values(generated_cell_roles)},
            limit=20,
        ),
        "upper_cell_refs": _unique_text_values(generated_upper_cell_refs),
        "suppressed_upper_cell_count": len(_unique_text_values(suppressed_upper_cell_refs)),
        "suppressed_upper_cell_refs": _unique_text_values(suppressed_upper_cell_refs),
        "boundary_refs": _unique_text_values(boundary_refs),
        "diagnostics": _unique_text_values(diagnostics),
    }


def _append_intersection_slope_face_graph_cell_tin(
    *,
    surface_id: str,
    graph_result: IntersectionSharedBoundaryGraphResult | None,
    vertices: list[TINVertex],
    triangles: list[TINTriangle],
) -> dict[str, object]:
    """Append upper transition triangles from graph-owned boundary cells."""

    if graph_result is None:
        return {
            "generation_mode": "missing_graph_result",
            "cell_count": 0,
            "triangle_count": 0,
            "cell_refs": [],
            "boundary_refs": [],
            "diagnostics": ["intersection_shared_boundary_graph_result_missing"],
        }
    diagnostics: list[str] = []
    cell_refs: list[str] = []
    boundary_refs: list[str] = []
    cell_count = 0
    triangle_count = 0
    for cell_index, row in enumerate(list(getattr(graph_result, "cell_rows", []) or []), start=1):
        cell_id = str(getattr(row, "cell_id", "") or f"graph-cell:{cell_index}")
        cell_role = str(getattr(row, "cell_role", "") or "")
        if not cell_role.startswith("upper_"):
            continue
        boundary_refs.extend(str(ref or "") for ref in tuple(getattr(row, "boundary_edge_refs", ()) or ()) if str(ref or ""))
        diagnostics.append(f"graph_upper_cell_metadata_only:{cell_id}")
        continue
        if str(getattr(row, "status", "") or "") != "ready" or not bool(getattr(row, "closed", False)):
            diagnostics.append(f"graph_cell_not_ready:{cell_id}")
            continue
        inner_points, outer_points = _intersection_slope_face_cell_surface_samples(row)
        if len(inner_points) < 2 or len(outer_points) < 2:
            diagnostics.append(f"graph_cell_loop_points_too_few:{cell_id}")
            continue
        sample_count = max(len(inner_points), len(outer_points), 2)
        inner_samples = _resample_polyline_xyz(inner_points, sample_count)
        outer_samples = _resample_polyline_xyz(outer_points, sample_count)
        if len(inner_samples) != len(outer_samples) or len(inner_samples) < 2:
            diagnostics.append(f"graph_cell_resample_failed:{cell_id}")
            continue
        cell_count += 1
        cell_refs.append(cell_id)
        boundary_refs.extend(str(ref or "") for ref in tuple(getattr(row, "boundary_edge_refs", ()) or ()) if str(ref or ""))
        inner_vertex_ids: list[str] = []
        outer_vertex_ids: list[str] = []
        for point_index, point in enumerate(inner_samples, start=1):
            vertex_id = f"{surface_id}:graph-cell-{cell_index:02d}:inner-{point_index:02d}"
            inner_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=cell_id,
                    notes=f"intersection shared-boundary graph cell inner point; role={cell_role}",
                )
            )
        for point_index, point in enumerate(outer_samples, start=1):
            vertex_id = f"{surface_id}:graph-cell-{cell_index:02d}:outer-{point_index:02d}"
            outer_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=cell_id,
                    notes=f"intersection shared-boundary graph cell outer point; role={cell_role}",
                )
            )
        for segment_index in range(len(inner_vertex_ids) - 1):
            p00 = inner_samples[segment_index]
            p01 = inner_samples[segment_index + 1]
            p10 = outer_samples[segment_index]
            p11 = outer_samples[segment_index + 1]
            id00 = inner_vertex_ids[segment_index]
            id01 = inner_vertex_ids[segment_index + 1]
            id10 = outer_vertex_ids[segment_index]
            id11 = outer_vertex_ids[segment_index + 1]
            first = _triangle_vertex_ids_with_upward_xy_normal(id00, p00, id10, p10, id11, p11)
            second = _triangle_vertex_ids_with_upward_xy_normal(id00, p00, id11, p11, id01, p01)
            triangle_count += 2
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:graph-cell-{cell_index:02d}:tri-{segment_index + 1:02d}a",
                    v1=first[0],
                    v2=first[1],
                    v3=first[2],
                    triangle_kind="intersection_slope_face_shared_boundary_graph_cell",
                    quality_ref="intersection_shared_boundary_graph",
                    notes=cell_id,
                )
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:graph-cell-{cell_index:02d}:tri-{segment_index + 1:02d}b",
                    v1=second[0],
                    v2=second[1],
                    v3=second[2],
                    triangle_kind="intersection_slope_face_shared_boundary_graph_cell",
                    quality_ref="intersection_shared_boundary_graph",
                    notes=cell_id,
                )
            )
    return {
        "generation_mode": "shared_boundary_graph_cell_strip" if cell_count else "no_ready_graph_cell",
        "cell_count": cell_count,
        "triangle_count": triangle_count,
        "cell_refs": _unique_text_values(cell_refs),
        "boundary_refs": _unique_text_values(boundary_refs),
        "diagnostics": _unique_text_values(diagnostics),
    }


def _append_intersection_boundary_loop_slope_face_transition_tin(
    *,
    surface_id: str,
    shared_breakline_result: SharedBreaklineResult | None,
    vertices: list[TINVertex],
    triangles: list[TINTriangle],
) -> dict[str, object]:
    """Append narrow transition strips from authoritative boundary-loop shared edges."""

    if shared_breakline_result is None:
        return {
            "generation_mode": "missing_shared_breakline_result",
            "strip_count": 0,
            "triangle_count": 0,
            "boundary_refs": [],
            "diagnostics": ["shared_breakline_result_missing"],
        }

    allowed_roles = {
        "patch_to_design_surface",
        "intersection_slope_face_to_design_surface",
        "intersection_slope_face_to_corridor_slope_face",
        "main_road_tie",
        "side_road_tie",
    }
    refs = set(_boundary_loop_shared_breakline_refs(shared_breakline_result, consumer_ref="intersection_slope_face_surface"))
    if not refs:
        return {
            "generation_mode": "no_boundary_loop_shared_breakline",
            "strip_count": 0,
            "triangle_count": 0,
            "boundary_refs": [],
            "diagnostics": ["intersection_boundary_loop_shared_breaklines_missing"],
        }

    diagnostics: list[str] = []
    boundary_refs: list[str] = []
    role_counts: dict[str, int] = {}
    role_widths: dict[str, float] = {}
    transition_rows: list[str] = []
    transition_segments: list[dict[str, object]] = []
    strip_count = 0
    triangle_count = 0
    corner_fill_count = 0
    corner_fill_rows: list[str] = []
    centroid = _intersection_boundary_loop_transition_centroid(shared_breakline_result, refs)
    for row_index, row in enumerate(list(getattr(shared_breakline_result, "breakline_rows", []) or []), start=1):
        breakline_id = str(getattr(row, "breakline_id", "") or "")
        if breakline_id not in refs:
            continue
        role = str(getattr(row, "breakline_role", "") or "")
        if role not in allowed_roles:
            diagnostics.append(f"boundary_loop_transition_role_metadata_only:{breakline_id}:{role}")
            continue
        points = _shared_breakline_points_xyz(shared_breakline_result, breakline_id)
        if len(points) < 2:
            diagnostics.append(f"boundary_loop_transition_points_too_few:{breakline_id}")
            continue
        for segment_index in range(len(points) - 1):
            first_point = points[segment_index]
            second_point = points[segment_index + 1]
            dx = float(second_point[0]) - float(first_point[0])
            dy = float(second_point[1]) - float(first_point[1])
            length_xy = math.sqrt(dx * dx + dy * dy)
            if length_xy <= 1.0e-9:
                diagnostics.append(f"boundary_loop_transition_segment_degenerate:{breakline_id}:{segment_index + 1}")
                continue
            width = _intersection_boundary_loop_transition_width(role, length_xy)
            boundary_refs.append(breakline_id)
            if not _intersection_boundary_loop_transition_is_visible_strip(role, length_xy):
                diagnostics.append(
                    "boundary_loop_transition_metadata_only_segment:"
                    f"{breakline_id}:role={role}:length={length_xy:.6g}"
                )
                transition_rows.append(
                    "|".join(
                        [
                            breakline_id,
                            f"role={role}",
                            f"segment={segment_index + 1}",
                            f"length={length_xy:.6g}",
                            f"width={float(width):.6g}",
                            "mode=metadata_only",
                        ]
                    )
                )
                continue
            nx = -dy / length_xy
            ny = dx / length_xy
            midpoint_x = (float(first_point[0]) + float(second_point[0])) * 0.5
            midpoint_y = (float(first_point[1]) + float(second_point[1])) * 0.5
            if centroid is not None:
                toward_centroid = (float(centroid[0]) - midpoint_x) * nx + (float(centroid[1]) - midpoint_y) * ny
                if toward_centroid < 0.0:
                    nx = -nx
                    ny = -ny
            strip_count += 1
            role_counts[role] = role_counts.get(role, 0) + 1
            role_widths[role] = max(float(role_widths.get(role, 0.0) or 0.0), float(width or 0.0))
            base_id = f"{surface_id}:boundary-loop-transition-{row_index:02d}-{segment_index + 1:02d}"
            id00 = f"{base_id}:p00"
            id01 = f"{base_id}:p01"
            id10 = f"{base_id}:p10"
            id11 = f"{base_id}:p11"
            p00 = (first_point[0], first_point[1], first_point[2])
            p01 = (second_point[0], second_point[1], second_point[2])
            p10 = (first_point[0] + nx * width, first_point[1] + ny * width, first_point[2])
            p11 = (second_point[0] + nx * width, second_point[1] + ny * width, second_point[2])
            transition_segments.append(
                {
                    "order": _intersection_boundary_loop_transition_segment_order(row, fallback=row_index),
                    "breakline_id": breakline_id,
                    "role": role,
                    "boundary_start_id": id00,
                    "boundary_end_id": id01,
                    "inward_start_id": id10,
                    "inward_end_id": id11,
                    "boundary_start": p00,
                    "boundary_end": p01,
                    "inward_start": p10,
                    "inward_end": p11,
                }
            )
            transition_rows.append(
                "|".join(
                    [
                        breakline_id,
                        f"role={role}",
                        f"segment={segment_index + 1}",
                        f"length={length_xy:.6g}",
                        f"width={float(width):.6g}",
                        f"normal={nx:.6g},{ny:.6g}",
                        "mode=visible_strip",
                    ]
                )
            )
            vertex_data = [
                (id00, p00, "boundary-start"),
                (id01, p01, "boundary-end"),
                (id10, p10, "inward-start"),
                (id11, p11, "inward-end"),
            ]
            for vertex_id, point, point_role in vertex_data:
                vertices.append(
                    TINVertex(
                        vertex_id,
                        float(point[0]),
                        float(point[1]),
                        float(point[2]),
                        source_point_ref=breakline_id,
                        notes=f"boundary-loop transition strip point; role={role}; side={point_role}",
                    )
                )
            first = _triangle_vertex_ids_with_upward_xy_normal(
                f"{base_id}:p00",
                p00,
                f"{base_id}:p10",
                p10,
                f"{base_id}:p11",
                p11,
            )
            second = _triangle_vertex_ids_with_upward_xy_normal(
                f"{base_id}:p00",
                p00,
                f"{base_id}:p11",
                p11,
                f"{base_id}:p01",
                p01,
            )
            triangle_count += 2
            triangles.append(
                TINTriangle(
                    triangle_id=f"{base_id}:tri-a",
                    v1=first[0],
                    v2=first[1],
                    v3=first[2],
                    triangle_kind="intersection_slope_face_boundary_loop_transition_strip",
                    quality_ref="intersection_boundary_loop_transition",
                    notes=f"{breakline_id}; role={role}",
                )
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"{base_id}:tri-b",
                    v1=second[0],
                    v2=second[1],
                    v3=second[2],
                    triangle_kind="intersection_slope_face_boundary_loop_transition_strip",
                    quality_ref="intersection_boundary_loop_transition",
                    notes=f"{breakline_id}; role={role}",
                )
            )

    ordered_transition_segments = sorted(
        transition_segments,
        key=lambda item: (int(item.get("order", 0) or 0), str(item.get("breakline_id", "") or "")),
    )
    for corner_index, first_segment in enumerate(ordered_transition_segments, start=1):
        second_segment = ordered_transition_segments[corner_index % len(ordered_transition_segments)] if ordered_transition_segments else None
        if second_segment is None or second_segment is first_segment:
            continue
        boundary_end = first_segment.get("boundary_end")
        next_boundary_start = second_segment.get("boundary_start")
        inward_end = first_segment.get("inward_end")
        next_inward_start = second_segment.get("inward_start")
        if not (
            isinstance(boundary_end, tuple)
            and isinstance(next_boundary_start, tuple)
            and isinstance(inward_end, tuple)
            and isinstance(next_inward_start, tuple)
        ):
            continue
        if not _intersection_slope_face_points_close_xy(boundary_end, next_boundary_start):
            diagnostics.append(
                "boundary_loop_transition_corner_not_connected:"
                f"{first_segment.get('breakline_id', '')}->{second_segment.get('breakline_id', '')}"
            )
            continue
        if _xyz_distance(inward_end, next_inward_start) <= 1.0e-9:
            continue
        triangle_ids = _triangle_vertex_ids_with_upward_xy_normal(
            str(first_segment.get("boundary_end_id", "") or ""),
            boundary_end,
            str(first_segment.get("inward_end_id", "") or ""),
            inward_end,
            str(second_segment.get("inward_start_id", "") or ""),
            next_inward_start,
        )
        triangle_id = f"{surface_id}:boundary-loop-transition-corner-{corner_index:02d}"
        triangles.append(
            TINTriangle(
                triangle_id=triangle_id,
                v1=triangle_ids[0],
                v2=triangle_ids[1],
                v3=triangle_ids[2],
                triangle_kind="intersection_slope_face_boundary_loop_transition_corner",
                quality_ref="intersection_boundary_loop_transition",
                notes=(
                    f"{first_segment.get('breakline_id', '')}->{second_segment.get('breakline_id', '')}; "
                    f"roles={first_segment.get('role', '')}->{second_segment.get('role', '')}"
                ),
            )
        )
        triangle_count += 1
        corner_fill_count += 1
        corner_fill_rows.append(
            "|".join(
                [
                    triangle_id,
                    f"from={first_segment.get('breakline_id', '')}",
                    f"to={second_segment.get('breakline_id', '')}",
                    f"roles={first_segment.get('role', '')}->{second_segment.get('role', '')}",
                ]
            )
        )

    if strip_count <= 0:
        diagnostics.append("boundary_loop_transition_no_visible_roles")
    return {
        "generation_mode": "boundary_loop_shared_transition_strip" if strip_count else "metadata_only",
        "strip_count": strip_count,
        "triangle_count": triangle_count,
        "corner_fill_count": corner_fill_count,
        "boundary_refs": _unique_text_values(boundary_refs),
        "role_summary": ", ".join(f"{role}={count}" for role, count in sorted(role_counts.items())),
        "width_summary": ", ".join(
            f"{role}={width:.3f}m" for role, width in sorted(role_widths.items())
        ),
        "transition_rows": _unique_text_values(transition_rows),
        "corner_fill_rows": _unique_text_values(corner_fill_rows),
        "diagnostics": _unique_text_values(diagnostics),
    }


def _intersection_boundary_loop_transition_centroid(
    shared_breakline_result: SharedBreaklineResult | None,
    refs: set[str],
) -> tuple[float, float] | None:
    points: list[tuple[float, float, float]] = []
    for ref in sorted(str(value or "") for value in refs if str(value or "")):
        for point in _shared_breakline_points_xyz(shared_breakline_result, ref):
            points.append(point)
    if not points:
        return None
    return (
        sum(float(point[0]) for point in points) / len(points),
        sum(float(point[1]) for point in points) / len(points),
    )


def _intersection_boundary_loop_transition_segment_order(row, *, fallback: int) -> int:
    for value in tuple(getattr(row, "source_contract_refs", ()) or ()):
        text = str(value or "")
        marker = ":segment:"
        if marker not in text:
            continue
        suffix = text.split(marker, 1)[1]
        digits = []
        for char in suffix:
            if char.isdigit():
                digits.append(char)
            else:
                break
        if digits:
            return int("".join(digits))
    return int(fallback)


def _intersection_boundary_loop_consumer_coverage_summary(
    boundary_loop_edges: list[object],
    filled_refs: set[str],
) -> dict[str, str]:
    coverage_rows: list[str] = []
    missing_rows: list[str] = []
    for consumer_ref in _INTERSECTION_BOUNDARY_LOOP_AUDIT_CONSUMERS:
        edge_refs = [
            str(getattr(edge, "edge_id", "") or "")
            for edge in boundary_loop_edges
            if str(getattr(edge, "edge_id", "") or "")
            and consumer_ref in {str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ())}
        ]
        if not edge_refs:
            continue
        unique_edge_refs = _unique_text_values(edge_refs)
        filled_count = sum(1 for edge_ref in unique_edge_refs if edge_ref in filled_refs)
        missing_count = max(0, len(unique_edge_refs) - filled_count)
        coverage_rows.append(f"{consumer_ref}={filled_count}/{len(unique_edge_refs)}")
        if missing_count:
            missing_rows.append(f"{consumer_ref}={missing_count}")
    return {
        "consumer_coverage_summary": "; ".join(coverage_rows),
        "consumer_missing_summary": "; ".join(missing_rows),
    }


def _intersection_boundary_loop_graph_fill_coverage(
    *,
    shared_breakline_result: SharedBreaklineResult | None,
    graph_result: IntersectionSharedBoundaryGraphResult | None,
    graph_surface_stats: dict[str, object] | None,
    boundary_loop_transition_stats: dict[str, object] | None,
) -> dict[str, object]:
    if graph_result is None:
        return {
            "status": "missing",
            "boundary_loop_graph_edge_count": 0,
            "consumer_edge_count": 0,
            "filled_edge_count": 0,
            "missing_edge_count": 0,
            "non_consumer_edge_count": 0,
            "boundary_loop_graph_edge_refs": [],
            "consumer_edge_refs": [],
            "filled_edge_refs": [],
            "missing_edge_refs": [],
            "non_consumer_edge_refs": [],
            "non_consumer_edge_rows": [],
            "non_consumer_role_summary": "",
            "consumer_coverage_summary": "",
            "consumer_missing_summary": "",
        }
    shared_by_id = {
        str(getattr(row, "breakline_id", "") or ""): row
        for row in list(getattr(shared_breakline_result, "breakline_rows", []) or [])
        if str(getattr(row, "breakline_id", "") or "")
    }
    boundary_loop_edges = [
        edge
        for edge in list(getattr(graph_result, "edge_rows", []) or [])
        if _intersection_authoritative_boundary_loop_segment_source_refs(tuple(getattr(edge, "source_refs", ()) or ()))
    ]
    boundary_loop_edge_refs = [
        str(getattr(edge, "edge_id", "") or "")
        for edge in boundary_loop_edges
        if str(getattr(edge, "edge_id", "") or "")
    ]
    consumer_edges = [
        edge
        for edge in boundary_loop_edges
        if "intersection_slope_face_surface"
        in {str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ())}
    ]
    consumer_edge_refs = [
        str(getattr(edge, "edge_id", "") or "")
        for edge in consumer_edges
        if str(getattr(edge, "edge_id", "") or "")
    ]
    consumer_edge_ref_set = set(consumer_edge_refs)
    non_consumer_edges = [
        edge
        for edge in boundary_loop_edges
        if str(getattr(edge, "edge_id", "") or "") not in consumer_edge_ref_set
    ]
    non_consumer_edge_refs = [
        str(getattr(edge, "edge_id", "") or "")
        for edge in non_consumer_edges
        if str(getattr(edge, "edge_id", "") or "")
    ]
    non_consumer_role_counts: dict[str, int] = {}
    non_consumer_edge_rows: list[str] = []
    for edge in non_consumer_edges:
        role = str(getattr(edge, "edge_role", "") or "unknown")
        non_consumer_role_counts[role] = non_consumer_role_counts.get(role, 0) + 1
        source_refs = tuple(getattr(edge, "source_refs", ()) or ())
        segment_refs = _intersection_authoritative_boundary_loop_segment_source_refs(source_refs)
        owner_refs = [
            str(value or "")
            for value in source_refs
            if str(value or "").startswith("intersection-boundary-owner:")
        ]
        consumer_refs = [
            str(value or "")
            for value in tuple(getattr(edge, "consumer_refs", ()) or ())
            if str(value or "")
        ]
        non_consumer_edge_rows.append(
            "|".join(
                [
                    str(getattr(edge, "edge_id", "") or ""),
                    f"role={role}",
                    f"left={str(getattr(edge, 'left_owner', '') or '')}",
                    f"right={str(getattr(edge, 'right_owner', '') or '')}",
                    f"consumers={','.join(_unique_text_values(consumer_refs))}",
                    f"segments={','.join(_unique_text_values(segment_refs))}",
                    f"owners={','.join(_unique_text_values(owner_refs))}",
                ]
            )
        )
    filled_refs = {
        str(value or "")
        for value in list((graph_surface_stats or {}).get("boundary_refs", []) or [])
        if str(value or "")
    }
    transition_shared_refs = {
        str(value or "")
        for value in list((boundary_loop_transition_stats or {}).get("boundary_refs", []) or [])
        if str(value or "")
    }
    if transition_shared_refs:
        transition_source_refs: set[str] = set()
        for shared_ref in transition_shared_refs:
            shared_row = shared_by_id.get(shared_ref)
            if shared_row is None:
                continue
            transition_source_refs.update(
                str(value or "")
                for value in tuple(getattr(shared_row, "source_contract_refs", ()) or ())
                if _is_intersection_authoritative_boundary_loop_segment_ref(str(value or ""))
            )
        for edge in boundary_loop_edges:
            edge_id = str(getattr(edge, "edge_id", "") or "")
            edge_source_refs = {
                str(value or "")
                for value in tuple(getattr(edge, "source_refs", ()) or ())
                if str(value or "")
            }
            if edge_id and edge_source_refs.intersection(transition_source_refs):
                filled_refs.add(edge_id)
    filled_edge_refs = _unique_text_values(ref for ref in filled_refs if ref in set(boundary_loop_edge_refs))
    missing_edge_refs = _unique_text_values(ref for ref in consumer_edge_refs if ref not in set(filled_edge_refs))
    consumer_coverage = _intersection_boundary_loop_consumer_coverage_summary(
        boundary_loop_edges,
        set(filled_edge_refs),
    )
    status = "ready" if consumer_edge_refs and not missing_edge_refs else "warning" if consumer_edge_refs else "missing"
    return {
        "status": status,
        "boundary_loop_graph_edge_count": len(_unique_text_values(boundary_loop_edge_refs)),
        "consumer_edge_count": len(_unique_text_values(consumer_edge_refs)),
        "filled_edge_count": len(_unique_text_values(filled_edge_refs)),
        "missing_edge_count": len(missing_edge_refs),
        "non_consumer_edge_count": len(_unique_text_values(non_consumer_edge_refs)),
        "boundary_loop_graph_edge_refs": _unique_text_values(boundary_loop_edge_refs),
        "consumer_edge_refs": _unique_text_values(consumer_edge_refs),
        "filled_edge_refs": _unique_text_values(filled_edge_refs),
        "missing_edge_refs": missing_edge_refs,
        "non_consumer_edge_refs": _unique_text_values(non_consumer_edge_refs),
        "non_consumer_edge_rows": _unique_text_values(non_consumer_edge_rows),
        "non_consumer_role_summary": ", ".join(
            f"{role}={count}" for role, count in sorted(non_consumer_role_counts.items())
        ),
        "consumer_coverage_summary": str(consumer_coverage.get("consumer_coverage_summary", "") or ""),
        "consumer_missing_summary": str(consumer_coverage.get("consumer_missing_summary", "") or ""),
    }


def _intersection_authoritative_boundary_loop_segment_source_refs(source_refs: tuple[object, ...]) -> list[str]:
    return [
        str(value or "")
        for value in tuple(source_refs or ())
        if _is_intersection_authoritative_boundary_loop_segment_ref(str(value or ""))
    ]


def _is_intersection_authoritative_boundary_loop_segment_ref(value: str) -> bool:
    text = str(value or "")
    return (
        (text.startswith("intersection-boundary-loop:") and ":segment:" in text)
        or text.startswith("intersection-boundary-envelope:")
    )


def _intersection_boundary_loop_transition_width(role: str, segment_length_xy: float) -> float:
    """Return a conservative review-strip width for a boundary-loop transition edge."""

    clean_role = str(role or "")
    role_width = {
        "patch_to_design_surface": 2.4,
        "main_road_tie": 1.2,
        "side_road_tie": 1.2,
        "intersection_slope_face_to_design_surface": 0.9,
        "intersection_slope_face_to_corridor_slope_face": 1.0,
    }.get(clean_role, 0.75)
    length_factor = 0.16 if clean_role == "patch_to_design_surface" else 0.08
    max_width = 3.0 if clean_role == "patch_to_design_surface" else 1.5
    length_width = max(0.20, min(float(segment_length_xy) * length_factor, max_width))
    return min(max(role_width, length_width), max_width)


def _intersection_boundary_loop_transition_is_visible_strip(role: str, segment_length_xy: float) -> bool:
    """Return whether boundary-loop transition rows should emit visible mesh.

    The boundary loop is the authoritative shared-breakline contract for several
    consumers. Transition rows are handoff metadata, not source geometry.
    Emitting physical strips from them repeatedly creates alignment-direction
    artifacts outside the local intersection slope-face cells.
    """

    return False


def _intersection_slope_face_cell_surface_samples(row) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    points = [_preview_xyz_tuple(point) for point in tuple(getattr(row, "loop_points_xyz", ()) or ())]
    if len(points) < 5:
        return [], []
    if not _intersection_slope_face_points_close_xy(points[0], points[-1]):
        return [], []
    unique_points = points[:-1]
    if len(unique_points) < 4:
        return [], []
    if str(getattr(row, "cell_role", "") or "").startswith("upper_"):
        return [unique_points[0], unique_points[1]], [unique_points[-2], unique_points[-3]]
    return [], []


def _shared_breakline_points_xyz(shared_breakline_result: SharedBreaklineResult | None, breakline_ref: str) -> list[tuple[float, float, float]]:
    if shared_breakline_result is None or not str(breakline_ref or ""):
        return []
    target_ref = str(breakline_ref or "")
    point_map = {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(shared_breakline_result, "point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }
    rows = [
        row for row in list(getattr(shared_breakline_result, "breakline_rows", []) or [])
        if str(getattr(row, "breakline_id", "") or "") == target_ref
    ]
    if not rows:
        return []
    points: list[tuple[float, float, float]] = []
    for point_ref in tuple(getattr(rows[0], "point_refs", ()) or ()):
        point = point_map.get(str(point_ref or ""))
        if point is None:
            continue
        points.append(_row_xyz_tuple(point))
    return points


def _intersection_slope_face_cell_audit_rows(cell_result: IntersectionSlopeFaceCellResult | None) -> list[str]:
    if cell_result is None:
        return []
    rows: list[str] = []
    for row in list(getattr(cell_result, "cell_rows", []) or []):
        cell_id = str(getattr(row, "cell_id", "") or "")
        if not cell_id:
            continue
        diagnostics = ",".join(str(value or "") for value in tuple(getattr(row, "diagnostics", ()) or ()) if str(value or ""))
        boundary_refs = ",".join(str(value or "") for value in tuple(getattr(row, "boundary_breakline_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    _audit_field(cell_id),
                    _audit_field(str(getattr(row, "cell_role", "") or "")),
                    _audit_field(str(getattr(row, "status", "") or "")),
                    "0" if bool(getattr(row, "closed_xy", False)) else "1",
                    str(
                        sum(
                            1
                            for diagnostic in tuple(getattr(row, "diagnostics", ()) or ())
                            if str(diagnostic).startswith("intersection_slope_face_cell_edge_missing")
                        )
                    ),
                    str(int(getattr(row, "point_count", 0) or 0)),
                    _audit_field(boundary_refs),
                    _audit_field(diagnostics),
                ]
            )
        )
    return rows


def _intersection_shared_boundary_graph_audit_rows(graph_result: IntersectionSharedBoundaryGraphResult | None) -> list[str]:
    if graph_result is None:
        return []
    rows: list[str] = []
    graph_audit = intersection_shared_boundary_graph_audit(graph_result)
    for edge in list(getattr(graph_result, "edge_rows", []) or []):
        diagnostics = ",".join(str(value or "") for value in tuple(getattr(edge, "diagnostics", ()) or ()) if str(value or ""))
        consumers = ",".join(str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ()) if str(value or ""))
        source_refs = ",".join(str(value or "") for value in tuple(getattr(edge, "source_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    "edge",
                    _audit_field(str(getattr(edge, "edge_id", "") or "")),
                    _audit_field(str(getattr(edge, "edge_role", "") or "")),
                    _audit_field(str(getattr(edge, "from_node_ref", "") or "")),
                    _audit_field(str(getattr(edge, "to_node_ref", "") or "")),
                    _audit_field(consumers),
                    _audit_field(diagnostics),
                    _audit_field(source_refs),
                ]
            )
        )
    for cell in list(getattr(graph_result, "cell_rows", []) or []):
        diagnostics = ",".join(str(value or "") for value in tuple(getattr(cell, "diagnostics", ()) or ()) if str(value or ""))
        boundary_refs = ",".join(str(value or "") for value in tuple(getattr(cell, "boundary_edge_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    "cell",
                    _audit_field(str(getattr(cell, "cell_id", "") or "")),
                    _audit_field(str(getattr(cell, "cell_role", "") or "")),
                    "1" if bool(getattr(cell, "closed", False)) else "0",
                    _audit_field(str(getattr(cell, "owner_surface_ref", "") or "")),
                    _audit_field(boundary_refs),
                    _audit_field(diagnostics),
                    "",
                ]
            )
        )
    for diagnostic in list(graph_audit.get("diagnostic_rows", []) or []):
        rows.append("|".join(["graph", _audit_field(str(diagnostic or "")), "", "", "", "", ""]))
    return rows


def _audit_field(value: object) -> str:
    return str(value or "").replace("|", "/").replace(";;", ";").strip()


def _intersection_boundary_loop_source_refs(source_refs: str) -> list[str]:
    return [
        value.strip()
        for value in str(source_refs or "").split(",")
        if value.strip()
        and (
            "intersection-boundary-loop" in value.strip()
            or "intersection-boundary-loops" in value.strip()
        )
    ]


def _intersection_shared_boundary_graph_segment_rows(graph_result: IntersectionSharedBoundaryGraphResult | None) -> list[str]:
    if graph_result is None:
        return []
    node_by_id = {
        str(getattr(node, "node_id", "") or ""): node
        for node in list(getattr(graph_result, "node_rows", []) or [])
        if str(getattr(node, "node_id", "") or "")
    }
    rows: list[str] = []
    for edge in list(getattr(graph_result, "edge_rows", []) or []):
        from_ref = str(getattr(edge, "from_node_ref", "") or "")
        to_ref = str(getattr(edge, "to_node_ref", "") or "")
        from_node = node_by_id.get(from_ref)
        to_node = node_by_id.get(to_ref)
        if from_node is None or to_node is None:
            continue
        consumers = ",".join(str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ()) if str(value or ""))
        rows.append(
            "|".join(
                [
                    _audit_field(str(getattr(edge, "edge_id", "") or "")),
                    _audit_field(str(getattr(edge, "edge_role", "") or "")),
                    _audit_field(from_ref),
                    _audit_field(to_ref),
                    f"{float(getattr(from_node, 'x', 0.0) or 0.0):.9f}",
                    f"{float(getattr(from_node, 'y', 0.0) or 0.0):.9f}",
                    f"{float(getattr(from_node, 'z', 0.0) or 0.0):.9f}",
                    f"{float(getattr(to_node, 'x', 0.0) or 0.0):.9f}",
                    f"{float(getattr(to_node, 'y', 0.0) or 0.0):.9f}",
                    f"{float(getattr(to_node, 'z', 0.0) or 0.0):.9f}",
                    _audit_field(consumers),
                ]
            )
        )
    return rows


def _intersection_slope_face_loop_has_dedicated_perimeter_source(row) -> bool:
    """Only generate dedicated surfaces from intersection-owned perimeter loops."""

    refs = [
        *[str(value or "") for value in tuple(getattr(row, "boundary_edge_refs", ()) or ())],
        *[str(value or "") for value in tuple(getattr(row, "source_edge_network_refs", ()) or ())],
    ]
    text = " ".join(refs).lower()
    if "curb-return-to-slope-face" in text or "curb_return_to_slope_face" in text:
        return True
    if "curb-return-outer" in text or "curb_return_outer" in text:
        return True
    if _intersection_slope_face_loop_has_applied_section_boundary_source(row):
        return True
    return False


def _intersection_slope_face_loop_has_applied_section_boundary_source(row) -> bool:
    """Allow Applied Section-completed intersection slope loops to become dedicated surface output."""

    boundary_refs = [
        str(value or "").lower()
        for value in tuple(getattr(row, "boundary_edge_refs", ()) or ())
        if str(value or "")
    ]
    if not any("applied-section-boundary" in ref or "applied_section_boundary" in ref for ref in boundary_refs):
        return False
    source_applied_refs = tuple(
        str(value or "")
        for value in tuple(getattr(row, "source_applied_section_refs", ()) or ())
        if str(value or "")
    )
    if not source_applied_refs:
        return False
    notes = str(getattr(row, "notes", "") or "").lower()
    return "applied_section_boundary_completion=used" in notes


def _intersection_slope_face_loop_is_applied_section_boundary_completion(row) -> bool:
    """Return true when a loop is an Applied Section completion aid, not a preferred fill polygon."""

    if row is None:
        return False
    refs = [
        str(value or "").lower()
        for value in tuple(getattr(row, "boundary_edge_refs", ()) or ())
        if str(value or "")
    ]
    notes = str(getattr(row, "notes", "") or "").lower()
    return (
        any("applied-section-boundary" in ref or "applied_section_boundary" in ref for ref in refs)
        and "applied_section_boundary_completion=used" in notes
    )


def _intersection_slope_face_loop_simple_ring_points(row) -> list[tuple[float, float, float]]:
    if row is None:
        return []
    raw_points = list(getattr(row, "loop_points_xyz", ()) or ())
    points: list[tuple[float, float, float]] = []
    for point in raw_points:
        xyz = _preview_xyz_tuple(point)
        if points and _preview_same_xy(points[-1], xyz):
            continue
        points.append(xyz)
    if len(points) >= 2 and _preview_same_xy(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3:
        return []
    return points


def _triangle_vertex_ids_with_upward_xy_normal(
    v1: str,
    p1: tuple[float, float, float],
    v2: str,
    p2: tuple[float, float, float],
    v3: str,
    p3: tuple[float, float, float],
) -> tuple[str, str, str]:
    """Return triangle vertex ids wound with a non-negative XY normal."""

    z_normal = (
        (float(p2[0]) - float(p1[0])) * (float(p3[1]) - float(p1[1]))
        - (float(p2[1]) - float(p1[1])) * (float(p3[0]) - float(p1[0]))
    )
    if z_normal < 0.0:
        return v1, v3, v2
    return v1, v2, v3


def _append_intersection_slope_face_boundary_strip_tin(
    *,
    surface_id: str,
    boundary_result: IntersectionSlopeFaceBoundaryResult | None,
    boundary_segment_result: IntersectionBoundarySegmentResult | None = None,
    vertices: list[TINVertex],
    triangles: list[TINTriangle],
    emit_geometry: bool = True,
) -> dict[str, object]:
    """Append strip triangles between intersection boundary and Applied Section Slope Face boundary."""

    if boundary_result is None:
        return {
            "generation_mode": "missing_boundary_result",
            "strip_count": 0,
            "triangle_count": 0,
            "boundary_refs": [],
            "diagnostics": ["intersection_slope_face_boundary_result_missing"],
        }
    diagnostics: list[str] = []
    boundary_refs: list[str] = []
    strip_count = 0
    triangle_count = 0
    transition_strip_count = 0
    transition_triangle_count = 0
    visible_boundary_ids = _intersection_slope_face_visible_transition_boundary_ids(
        boundary_result,
        boundary_segment_result,
    )
    for boundary_index, row in enumerate(list(getattr(boundary_result, "boundary_rows", []) or []), start=1):
        boundary_id = str(getattr(row, "boundary_id", "") or f"boundary:{boundary_index}")
        if str(getattr(row, "status", "") or "") != "ready":
            diagnostics.append(f"boundary_not_ready:{boundary_id}")
            continue
        if visible_boundary_ids and boundary_id not in visible_boundary_ids:
            diagnostics.append(f"boundary_suppressed:not_visible_transition:{boundary_id}")
            continue
        inner_points = [_preview_xyz_tuple(point) for point in list(getattr(row, "inner_points_xyz", ()) or ())]
        outer_points = [_preview_xyz_tuple(point) for point in list(getattr(row, "outer_points_xyz", ()) or ())]
        if len(inner_points) < 2 or len(outer_points) < 2:
            diagnostics.append(f"boundary_points_too_few:{boundary_id}")
            continue
        sample_count = max(len(inner_points), len(outer_points), 2)
        inner_samples = _resample_polyline_xyz(inner_points, sample_count)
        outer_samples = _resample_polyline_xyz(outer_points, sample_count)
        if len(inner_samples) != len(outer_samples) or len(inner_samples) < 2:
            diagnostics.append(f"boundary_resample_failed:{boundary_id}")
            continue
        visible_segment_indices = _intersection_slope_face_visible_transition_segment_indices(row, inner_samples)
        if not visible_segment_indices:
            diagnostics.append(f"boundary_suppressed:no_visible_segments:{boundary_id}")
            continue
        boundary_family = _intersection_slope_face_boundary_row_family(row)
        triangle_kind = (
            "intersection_slope_face_transition_strip"
            if boundary_family in {"main_transition_strip", "side_transition_strip"}
            else "intersection_slope_face_boundary_strip"
        )
        quality_ref = (
            "intersection_slope_face_transition"
            if triangle_kind == "intersection_slope_face_transition_strip"
            else "intersection_slope_face_boundary"
        )
        strip_count += 1
        if triangle_kind == "intersection_slope_face_transition_strip":
            transition_strip_count += 1
        boundary_refs.append(boundary_id)
        if not emit_geometry:
            diagnostics.append(f"boundary_strip_geometry_suppressed:cell_surface_available:{boundary_id}")
            continue
        inner_vertex_ids: list[str] = []
        outer_vertex_ids: list[str] = []
        for point_index, point in enumerate(inner_samples, start=1):
            vertex_id = f"{surface_id}:boundary-{boundary_index:02d}:inner-{point_index:02d}"
            inner_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=boundary_id,
                    notes="intersection slope-face strip inner boundary point",
                )
            )
        for point_index, point in enumerate(outer_samples, start=1):
            vertex_id = f"{surface_id}:boundary-{boundary_index:02d}:outer-{point_index:02d}"
            outer_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=boundary_id,
                    notes="intersection slope-face strip outer Applied Section point",
                )
            )
        for point_index in range(len(inner_vertex_ids) - 1):
            if point_index not in visible_segment_indices:
                continue
            i0 = inner_vertex_ids[point_index]
            i1 = inner_vertex_ids[point_index + 1]
            o0 = outer_vertex_ids[point_index]
            o1 = outer_vertex_ids[point_index + 1]
            inner0 = inner_samples[point_index]
            inner1 = inner_samples[point_index + 1]
            outer0 = outer_samples[point_index]
            outer1 = outer_samples[point_index + 1]
            a_v1, a_v2, a_v3 = _triangle_vertex_ids_with_upward_xy_normal(
                i0,
                inner0,
                i1,
                inner1,
                o1,
                outer1,
            )
            b_v1, b_v2, b_v3 = _triangle_vertex_ids_with_upward_xy_normal(
                i0,
                inner0,
                o1,
                outer1,
                o0,
                outer0,
            )
            first_triangle = TINTriangle(
                triangle_id=f"{surface_id}:boundary-{boundary_index:02d}:strip-{point_index + 1:02d}:a",
                v1=a_v1,
                v2=a_v2,
                v3=a_v3,
                triangle_kind=triangle_kind,
                quality_ref=quality_ref,
                notes=boundary_id,
            )
            second_triangle = TINTriangle(
                triangle_id=f"{surface_id}:boundary-{boundary_index:02d}:strip-{point_index + 1:02d}:b",
                v1=b_v1,
                v2=b_v2,
                v3=b_v3,
                triangle_kind=triangle_kind,
                quality_ref=quality_ref,
                notes=boundary_id,
            )
            triangles.extend([first_triangle, second_triangle])
            triangle_count += 2
            if triangle_kind == "intersection_slope_face_transition_strip":
                transition_triangle_count += 2
    return {
        "generation_mode": "boundary_strip" if strip_count and emit_geometry else "metadata_only" if strip_count else "no_ready_boundary_strip",
        "strip_count": strip_count,
        "triangle_count": triangle_count,
        "transition_strip_count": transition_strip_count,
        "transition_triangle_count": transition_triangle_count,
        "boundary_refs": boundary_refs,
        "diagnostics": diagnostics,
    }


def _append_intersection_curb_return_slope_face_perimeter_tin(
    *,
    surface_id: str,
    boundary_segment_result: IntersectionBoundarySegmentResult | None,
    applied_section_set,
    vertices: list[TINVertex],
    triangles: list[TINTriangle],
) -> dict[str, object]:
    """Append strips from curb-return exterior arcs to Applied Section side-slope/daylight points."""

    if boundary_segment_result is None:
        return {
            "generation_mode": "missing_boundary_segments",
            "strip_count": 0,
            "triangle_count": 0,
            "boundary_refs": [],
            "diagnostics": ["curb_return_slope_face_perimeter_boundary_segments_missing"],
        }
    candidate_points = _intersection_applied_section_slope_face_candidate_points(applied_section_set)
    if not candidate_points:
        return {
            "generation_mode": "missing_applied_section_slope_face_points",
            "strip_count": 0,
            "triangle_count": 0,
            "boundary_refs": [],
            "diagnostics": ["curb_return_slope_face_perimeter_applied_section_points_missing"],
        }
    strip_count = 0
    triangle_count = 0
    boundary_refs: list[str] = []
    diagnostics: list[str] = []
    for arc_index, row in enumerate(list(getattr(boundary_segment_result, "segment_rows", []) or []), start=1):
        if str(getattr(row, "segment_kind", "") or "") != "arc":
            continue
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        boundary_id = str(getattr(row, "boundary_segment_id", "") or f"curb-return:{arc_index}")
        center = _xyz_tuple(getattr(row, "center_xyz", (0.0, 0.0, 0.0)))
        chord_points = [_xyz_tuple(point) for point in list(getattr(row, "chord_points_xyz", ()) or ())]
        chord_points = _unique_xyz_points(chord_points)
        if len(chord_points) < 2:
            diagnostics.append(f"curb_return_slope_face_perimeter_arc_points_too_few:{boundary_id}")
            continue
        outer_points: list[tuple[float, float, float]] = []
        for point in chord_points:
            outer = _intersection_outer_slope_point_for_curb_return_point(
                point,
                center=center,
                candidate_points=candidate_points,
            )
            if outer is None:
                diagnostics.append(f"curb_return_slope_face_perimeter_outer_point_missing:{boundary_id}")
                outer_points = []
                break
            outer_points.append(outer)
        if len(outer_points) != len(chord_points) or len(outer_points) < 2:
            continue
        strip_count += 1
        boundary_refs.append(boundary_id)
        inner_vertex_ids: list[str] = []
        outer_vertex_ids: list[str] = []
        for point_index, point in enumerate(chord_points, start=1):
            vertex_id = f"{surface_id}:curb-return-{arc_index:02d}:inner-{point_index:02d}"
            inner_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=boundary_id,
                    notes="curb-return exterior boundary for intersection slope-face perimeter",
                )
            )
        for point_index, point in enumerate(outer_points, start=1):
            vertex_id = f"{surface_id}:curb-return-{arc_index:02d}:outer-{point_index:02d}"
            outer_vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=boundary_id,
                    notes="Applied Section side-slope/daylight boundary projected from curb return",
                )
            )
        for point_index in range(len(inner_vertex_ids) - 1):
            i0 = inner_vertex_ids[point_index]
            i1 = inner_vertex_ids[point_index + 1]
            o0 = outer_vertex_ids[point_index]
            o1 = outer_vertex_ids[point_index + 1]
            inner0 = chord_points[point_index]
            inner1 = chord_points[point_index + 1]
            outer0 = outer_points[point_index]
            outer1 = outer_points[point_index + 1]
            a_v1, a_v2, a_v3 = _triangle_vertex_ids_with_upward_xy_normal(
                i0,
                inner0,
                i1,
                inner1,
                o1,
                outer1,
            )
            b_v1, b_v2, b_v3 = _triangle_vertex_ids_with_upward_xy_normal(
                i0,
                inner0,
                o1,
                outer1,
                o0,
                outer0,
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:curb-return-{arc_index:02d}:perimeter-{point_index + 1:02d}:a",
                    v1=a_v1,
                    v2=a_v2,
                    v3=a_v3,
                    triangle_kind="intersection_slope_face_curb_return_perimeter",
                    quality_ref="curb_return_to_slope_face",
                    notes=boundary_id,
                )
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:curb-return-{arc_index:02d}:perimeter-{point_index + 1:02d}:b",
                    v1=b_v1,
                    v2=b_v2,
                    v3=b_v3,
                    triangle_kind="intersection_slope_face_curb_return_perimeter",
                    quality_ref="curb_return_to_slope_face",
                    notes=boundary_id,
                )
            )
            triangle_count += 2
    return {
        "generation_mode": "curb_return_to_slope_face_perimeter" if strip_count else "no_curb_return_perimeter_strip",
        "strip_count": strip_count,
        "triangle_count": triangle_count,
        "boundary_refs": boundary_refs,
        "diagnostics": diagnostics,
    }


def _intersection_slope_face_boundary_row_family(row) -> str:
    notes = str(getattr(row, "notes", "") or "")
    for part in notes.split(";"):
        text = part.strip()
        if text.startswith("boundary_family="):
            return text.split("=", 1)[1].strip()
    return ""


def _intersection_slope_face_visible_transition_boundary_ids(
    boundary_result: IntersectionSlopeFaceBoundaryResult | None,
    boundary_segment_result: IntersectionBoundarySegmentResult | None,
) -> set[str]:
    rows = [
        row
        for row in list(getattr(boundary_result, "boundary_rows", []) or [])
        if _intersection_slope_face_boundary_row_family(row) == "main_transition_strip"
    ]
    if not rows:
        return set()
    curb_points = _intersection_curb_return_reference_points(boundary_segment_result)
    if not curb_points:
        return {str(getattr(row, "boundary_id", "") or "") for row in rows}

    def score(row) -> float:
        points = [_preview_xyz_tuple(point) for point in list(getattr(row, "outer_points_xyz", ()) or ())]
        if not points:
            points = [_preview_xyz_tuple(point) for point in list(getattr(row, "inner_points_xyz", ()) or ())]
        if not points:
            return -1.0
        mid = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        return min(_xy_distance(mid, (point[0], point[1])) for point in curb_points)

    selected = max(rows, key=score)
    selected_id = str(getattr(selected, "boundary_id", "") or "")
    return {selected_id} if selected_id else set()


def _intersection_curb_return_reference_points(boundary_segment_result) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for row in list(getattr(boundary_segment_result, "segment_rows", []) or []):
        if str(getattr(row, "segment_role", "") or "") != "curb_return":
            continue
        for point in list(getattr(row, "chord_points_xyz", ()) or ()):
            try:
                if len(tuple(point or ())) >= 3:
                    points.append(_preview_xyz_tuple(point))
            except Exception:
                continue
    return points


def _intersection_slope_face_visible_transition_segment_indices(
    row,
    inner_samples: list[tuple[float, float, float]],
) -> set[int]:
    if _intersection_slope_face_boundary_row_family(row) != "main_transition_strip":
        return set()
    segment_count = max(len(inner_samples) - 1, 0)
    if segment_count <= 0:
        return set()
    if segment_count <= 2:
        return set(range(segment_count))
    return {0, segment_count - 1}


def _intersection_applied_section_slope_face_candidate_points(applied_section_set) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    if applied_section_set is None:
        return points
    for section in list(getattr(applied_section_set, "sections", []) or []):
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") not in {"side_slope_surface", "bench_surface", "daylight_marker"}:
                continue
            points.append(
                (
                    float(getattr(point, "x", 0.0) or 0.0),
                    float(getattr(point, "y", 0.0) or 0.0),
                    float(getattr(point, "z", 0.0) or 0.0),
                )
            )
    return _unique_xyz_points(points)


def _intersection_outer_slope_point_for_curb_return_point(
    point: tuple[float, float, float],
    *,
    center: tuple[float, float, float],
    candidate_points: list[tuple[float, float, float]],
) -> tuple[float, float, float] | None:
    vx = float(point[0]) - float(center[0])
    vy = float(point[1]) - float(center[1])
    radius = math.hypot(vx, vy)
    if radius <= 1.0e-9:
        return None
    ux = vx / radius
    uy = vy / radius
    best: tuple[float, float, tuple[float, float, float]] | None = None
    for candidate in list(candidate_points or []):
        cx = float(candidate[0]) - float(center[0])
        cy = float(candidate[1]) - float(center[1])
        radial = cx * ux + cy * uy
        if radial <= radius + 0.25:
            continue
        if radial > radius + _intersection_curb_return_outer_candidate_max_offset(radius):
            continue
        perpendicular = abs(cx * (-uy) + cy * ux)
        if perpendicular > max(12.0, radius * 1.5):
            continue
        score = (perpendicular, radial)
        if best is None or score < (best[0], best[1]):
            best = (perpendicular, radial, candidate)
    if best is None:
        return None
    radial = max(float(best[1]), radius + 2.0)
    candidate = best[2]
    return (
        float(center[0]) + ux * radial,
        float(center[1]) + uy * radial,
        float(candidate[2]),
    )


def _intersection_curb_return_outer_candidate_max_offset(radius: float) -> float:
    """Return the local search distance for curb-return slope-face candidates."""

    clean_radius = max(0.0, float(radius or 0.0))
    return max(4.0, min(8.0, clean_radius * 0.45))


def _resample_polyline_xyz(points: list[tuple[float, float, float]], sample_count: int) -> list[tuple[float, float, float]]:
    if sample_count <= 0 or not points:
        return []
    if len(points) == 1:
        return [points[0] for _index in range(sample_count)]
    if sample_count == 1:
        return [points[0]]
    cumulative = [0.0]
    for first, second in zip(points[:-1], points[1:]):
        cumulative.append(cumulative[-1] + _xyz_distance(first, second))
    total = cumulative[-1]
    if total <= 1.0e-9:
        return [points[0] for _index in range(sample_count)]
    samples: list[tuple[float, float, float]] = []
    for sample_index in range(sample_count):
        distance = total * (float(sample_index) / float(sample_count - 1))
        segment_index = 0
        while segment_index < len(cumulative) - 2 and cumulative[segment_index + 1] < distance:
            segment_index += 1
        start = points[segment_index]
        end = points[segment_index + 1]
        segment_length = max(cumulative[segment_index + 1] - cumulative[segment_index], 1.0e-9)
        ratio = (distance - cumulative[segment_index]) / segment_length
        samples.append(
            (
                float(start[0]) + (float(end[0]) - float(start[0])) * ratio,
                float(start[1]) + (float(end[1]) - float(start[1])) * ratio,
                float(start[2]) + (float(end[2]) - float(start[2])) * ratio,
            )
        )
    return samples


def _intersection_slope_face_loop_fan_quality(
    points: list[tuple[float, float, float]],
    center: tuple[float, float, float],
) -> dict[str, object]:
    min_quality = 1.0
    degenerate_count = 0
    skinny_count = 0
    for point_index, current in enumerate(points):
        nxt = points[(point_index + 1) % len(points)]
        area = abs(_xy_triangle_area(center, current, nxt))
        quality = _xy_triangle_quality_ratio(center, current, nxt)
        min_quality = min(min_quality, quality)
        if area <= 1.0e-6:
            degenerate_count += 1
        elif quality < 0.08:
            skinny_count += 1
    return {
        "min_quality": min_quality if points else 0.0,
        "degenerate_count": degenerate_count,
        "skinny_count": skinny_count,
    }


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


def _unique_xyz_points(points: list[tuple[float, float, float]], *, tolerance: float = 1.0e-6) -> list[tuple[float, float, float]]:
    output = []
    for point in list(points or []):
        if any(_xyz_distance(point, existing) <= tolerance for existing in output):
            continue
        output.append(point)
    return output


def _xyz_distance(first, second) -> float:
    return math.sqrt(
        (float(first[0]) - float(second[0])) ** 2
        + (float(first[1]) - float(second[1])) ** 2
        + (float(first[2]) - float(second[2])) ** 2
    )


def corridor_intersection_slope_face_cell_result(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_id: str = "",
) -> IntersectionSlopeFaceCellResult:
    """Compatibility wrapper for typed Intersection slope-face cell evaluation."""

    return IntersectionSlopeFaceCellEvaluationService().evaluate(
        IntersectionSlopeFaceCellEvaluationRequest(
            shared_breakline_result=shared_breakline_result,
            intersection_id=intersection_id,
        )
    )


def _intersection_upper_slope_face_panel_candidate_rows(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_id: str = "",
    intersection_kind: str = "",
) -> list[dict[str, object]]:
    """Return source-boundary candidates for upper rectangular slope-face panels.

    These rows are diagnostic/result candidates only. They intentionally do not
    consume generated upper cell triangles or preview object geometry.
    """

    if shared_breakline_result is None:
        return []
    if not _intersection_upper_slope_face_panel_supported(intersection_kind):
        return []
    target_intersection_id = str(intersection_id or getattr(shared_breakline_result, "domain_ref", "") or "")
    point_map = {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(shared_breakline_result, "point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }
    rows_by_role: dict[str, list[SharedBreaklineRow]] = {}
    for row in list(getattr(shared_breakline_result, "breakline_rows", []) or []):
        role = str(getattr(row, "breakline_role", "") or "")
        if role:
            rows_by_role.setdefault(role, []).append(row)

    patch_rows = rows_by_role.get("patch_to_intersection_slope_face", [])
    outer_rows = rows_by_role.get("intersection_slope_face_to_corridor_slope_face", [])
    design_rows = rows_by_role.get("intersection_slope_face_to_design_surface", [])
    output: list[dict[str, object]] = []
    used_outer_refs: set[str] = set()
    for index, patch_row in enumerate(patch_rows, start=1):
        alignment_ref = str(getattr(patch_row, "alignment_ref", "") or "")
        side = str(getattr(patch_row, "side", "") or "")
        outer_row, outer_match_mode = _matching_intersection_slope_face_cell_breakline_for_panel(
            outer_rows,
            patch_row,
            alignment_ref=alignment_ref,
            side=side,
            used_refs=used_outer_refs,
            point_map=point_map,
        )
        if outer_row is not None:
            used_outer_refs.add(str(getattr(outer_row, "breakline_id", "") or ""))
        design_row, design_match_mode = _matching_intersection_slope_face_cell_breakline_for_panel(
            design_rows,
            patch_row,
            alignment_ref=alignment_ref,
            side=side,
            used_refs=set(),
            point_map=point_map,
        )
        diagnostics: list[str] = []
        inner_points = _intersection_slope_face_cell_row_points(patch_row, point_map)
        outer_points = _intersection_slope_face_cell_row_points(outer_row, point_map) if outer_row is not None else []
        if len(inner_points) < 2:
            diagnostics.append("intersection_upper_slope_face_panel_inner_edge_missing")
        if len(outer_points) < 2:
            diagnostics.append("intersection_upper_slope_face_panel_outer_edge_missing")
        if outer_row is None:
            diagnostics.append("intersection_upper_slope_face_panel_outer_breakline_missing")
        if design_row is None:
            diagnostics.append("intersection_upper_slope_face_panel_cap_source_missing")
        inner_len = _polyline_length_xyz(inner_points)
        outer_len = _polyline_length_xyz(outer_points)
        aligned_outer_points = list(outer_points)
        if len(inner_points) >= 2 and len(aligned_outer_points) >= 2:
            inner_start = inner_points[0]
            inner_end = inner_points[-1]
            outer_start = aligned_outer_points[0]
            outer_end = aligned_outer_points[-1]
            same_direction = _xy_distance(inner_start, outer_start) + _xy_distance(inner_end, outer_end)
            reversed_direction = _xy_distance(inner_start, outer_end) + _xy_distance(inner_end, outer_start)
            if reversed_direction < same_direction:
                aligned_outer_points = list(reversed(aligned_outer_points))
        inner_ref = str(getattr(patch_row, "breakline_id", "") or "")
        outer_ref = str(getattr(outer_row, "breakline_id", "") or "") if outer_row is not None else ""
        design_ref = str(getattr(design_row, "breakline_id", "") or "") if design_row is not None else ""
        base_candidate_id = (
            "intersection-upper-slope-face-panel:"
            f"{_safe_id_fragment(target_intersection_id or 'main')}:{index:02d}"
        )
        output.extend(
            _intersection_upper_slope_face_panel_segment_candidate_rows(
                base_candidate_id=base_candidate_id,
                intersection_id=target_intersection_id,
                alignment_ref=alignment_ref,
                side=side,
                inner_points=inner_points,
                outer_points=aligned_outer_points,
                base_diagnostics=diagnostics,
                inner_ref=inner_ref,
                outer_ref=outer_ref,
                design_ref=design_ref,
                outer_match_mode=outer_match_mode,
                design_match_mode=design_match_mode,
                inner_len=inner_len,
                outer_len=outer_len,
            )
        )
    return output


def _intersection_upper_slope_face_panel_segment_candidate_rows(
    *,
    base_candidate_id: str,
    intersection_id: str,
    alignment_ref: str,
    side: str,
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    base_diagnostics: list[str],
    inner_ref: str,
    outer_ref: str,
    design_ref: str,
    outer_match_mode: str,
    design_match_mode: str,
    inner_len: float,
    outer_len: float,
) -> list[dict[str, object]]:
    """Split long upper panel candidates into source-breakline sub-panels."""

    if len(inner_points) < 2 or len(outer_points) < 2:
        return [
            _intersection_upper_slope_face_panel_candidate_row(
                candidate_id=base_candidate_id,
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                side=side,
                loop_points=[],
                diagnostics=[*base_diagnostics, "intersection_upper_slope_face_panel_open_loop"],
                inner_ref=inner_ref,
                outer_ref=outer_ref,
                design_ref=design_ref,
                outer_match_mode=outer_match_mode,
                design_match_mode=design_match_mode,
                inner_len=inner_len,
                outer_len=outer_len,
            )
        ]

    coarse_loop = _intersection_slope_face_simplified_closed_loop(
        [inner_points[0], inner_points[-1], outer_points[-1], outer_points[0], inner_points[0]]
    )
    coarse_polygon = (
        coarse_loop[:-1]
        if coarse_loop and _intersection_slope_face_points_close_xy(coarse_loop[0], coarse_loop[-1])
        else coarse_loop
    )
    coarse_area = abs(_xy_polygon_area([(point[0], point[1]) for point in coarse_polygon])) if coarse_polygon else 0.0
    _bbox_diag, coarse_aspect, _bbox_fill = _intersection_upper_slope_face_panel_bbox_metrics(
        coarse_polygon,
        coarse_area,
    )
    split_count = 1
    if outer_match_mode == "exact" and design_match_mode == "exact" and coarse_aspect > 8.0:
        split_count = max(1, min(8, int(math.ceil(coarse_aspect / 8.0))))
    inner_samples = _resample_polyline_xyz(inner_points, split_count + 1)
    outer_samples = _resample_polyline_xyz(outer_points, split_count + 1)
    if len(inner_samples) != split_count + 1 or len(outer_samples) != split_count + 1:
        inner_samples = [inner_points[0], inner_points[-1]]
        outer_samples = [outer_points[0], outer_points[-1]]
        split_count = 1

    rows: list[dict[str, object]] = []
    for segment_index in range(split_count):
        inner_start = inner_samples[segment_index]
        inner_end = inner_samples[segment_index + 1]
        outer_start = outer_samples[segment_index]
        outer_end = outer_samples[segment_index + 1]
        loop_points = _intersection_slope_face_simplified_closed_loop(
            [inner_start, inner_end, outer_end, outer_start, inner_start]
        )
        candidate_id = base_candidate_id if split_count == 1 else f"{base_candidate_id}:segment-{segment_index + 1:02d}"
        rows.append(
            _intersection_upper_slope_face_panel_candidate_row(
                candidate_id=candidate_id,
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                side=side,
                loop_points=loop_points,
                diagnostics=list(base_diagnostics),
                inner_ref=inner_ref,
                outer_ref=outer_ref,
                design_ref=design_ref,
                outer_match_mode=outer_match_mode,
                design_match_mode=design_match_mode,
                inner_len=_polyline_length_xyz([inner_start, inner_end]),
                outer_len=_polyline_length_xyz([outer_start, outer_end]),
            )
        )
    return rows


def _intersection_upper_slope_face_panel_candidate_row(
    *,
    candidate_id: str,
    intersection_id: str,
    alignment_ref: str,
    side: str,
    loop_points: list[tuple[float, float, float]],
    diagnostics: list[str],
    inner_ref: str,
    outer_ref: str,
    design_ref: str,
    outer_match_mode: str,
    design_match_mode: str,
    inner_len: float,
    outer_len: float,
) -> dict[str, object]:
    left_cap_len = 0.0
    right_cap_len = 0.0
    loop_area = 0.0
    self_crossing = False
    bbox_diag = 0.0
    bbox_fill_ratio = 0.0
    bbox_aspect = 0.0
    if len(loop_points) >= 4:
        polygon = loop_points[:-1] if _intersection_slope_face_points_close_xy(loop_points[0], loop_points[-1]) else loop_points
        loop_area = abs(_xy_polygon_area([(point[0], point[1]) for point in polygon]))
        self_crossing = _xy_xyz_polygon_self_crossing(polygon)
        bbox_diag, bbox_aspect, bbox_fill_ratio = _intersection_upper_slope_face_panel_bbox_metrics(polygon, loop_area)
        left_cap_len = _xy_distance(loop_points[0], loop_points[-2])
        right_cap_len = _xy_distance(loop_points[1], loop_points[2])
        if left_cap_len <= 1.0e-6:
            diagnostics.append("intersection_upper_slope_face_panel_left_cap_missing")
        if right_cap_len <= 1.0e-6:
            diagnostics.append("intersection_upper_slope_face_panel_right_cap_missing")
        if loop_area <= 1.0e-6:
            diagnostics.append("intersection_upper_slope_face_panel_zero_area")
        if self_crossing:
            diagnostics.append("intersection_upper_slope_face_panel_self_crossing")
        remote_risk_diagnostics = _intersection_upper_slope_face_panel_remote_risk_diagnostics(
            bbox_diag=bbox_diag,
            bbox_aspect=bbox_aspect,
            bbox_fill_ratio=bbox_fill_ratio,
            inner_len=inner_len,
            outer_len=outer_len,
            left_cap_len=left_cap_len,
            right_cap_len=right_cap_len,
        )
        if not (outer_match_mode == "exact" and design_match_mode == "exact"):
            diagnostics.extend(remote_risk_diagnostics)
    else:
        diagnostics.append("intersection_upper_slope_face_panel_open_loop")
    status = "accepted" if not diagnostics else "warning"
    return {
        "candidate_id": candidate_id,
        "intersection_id": intersection_id,
        "alignment_ref": alignment_ref,
        "side": side,
        "status": status,
        "source_mode": "accepted_upper_rectangular_panel_boundary",
        "outer_match_mode": outer_match_mode,
        "design_match_mode": design_match_mode,
        "inner_edge_ref": inner_ref,
        "outer_edge_ref": outer_ref,
        "left_cap_ref": f"{inner_ref}<->{outer_ref}:start" if inner_ref and outer_ref else "",
        "right_cap_ref": f"{inner_ref}<->{outer_ref}:end" if inner_ref and outer_ref else "",
        "design_cap_source_ref": design_ref,
        "loop_points_xyz": tuple(loop_points),
        "loop_area_xy": loop_area,
        "inner_edge_length": inner_len,
        "outer_edge_length": outer_len,
        "left_cap_length": left_cap_len,
        "right_cap_length": right_cap_len,
        "bbox_diagonal": bbox_diag,
        "bbox_aspect": bbox_aspect,
        "bbox_fill_ratio": bbox_fill_ratio,
        "self_crossing": self_crossing,
        "diagnostics": tuple(_unique_text_values(diagnostics)),
        "source_shared_breakline_refs": tuple(_unique_text_values([inner_ref, outer_ref, design_ref])),
    }


def _intersection_upper_slope_face_panel_supported(intersection_kind: str) -> bool:
    """Return whether the T-oriented upper slope-face panel generator may run."""

    kind = str(intersection_kind or "").strip().lower().replace("-", "_")
    if not kind:
        return True
    return kind == "t_intersection" or kind.endswith("_t_intersection") or kind.startswith("t_intersection")


def _polyline_length_xyz(points: list[tuple[float, float, float]]) -> float:
    total = 0.0
    for first, second in zip(points, points[1:]):
        total += _xy_distance(first, second)
    return total


def _intersection_upper_slope_face_panel_bbox_metrics(
    polygon: list[tuple[float, float, float]],
    loop_area: float,
) -> tuple[float, float, float]:
    xs = [float(point[0]) for point in list(polygon or [])]
    ys = [float(point[1]) for point in list(polygon or [])]
    if not xs or not ys:
        return 0.0, 0.0, 0.0
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    bbox_area = max(0.0, width) * max(0.0, height)
    bbox_diag = math.sqrt(width * width + height * height)
    min_axis = max(min(abs(width), abs(height)), 1.0e-9)
    max_axis = max(abs(width), abs(height))
    bbox_aspect = max_axis / min_axis if min_axis > 1.0e-9 else 0.0
    bbox_fill_ratio = abs(float(loop_area or 0.0)) / bbox_area if bbox_area > 1.0e-9 else 0.0
    return bbox_diag, bbox_aspect, bbox_fill_ratio


def _intersection_upper_slope_face_panel_remote_risk_diagnostics(
    *,
    bbox_diag: float,
    bbox_aspect: float,
    bbox_fill_ratio: float,
    inner_len: float,
    outer_len: float,
    left_cap_len: float,
    right_cap_len: float,
) -> list[str]:
    diagnostics: list[str] = []
    edge_scale = max(float(inner_len or 0.0), float(outer_len or 0.0), 1.0)
    cap_scale = max(float(left_cap_len or 0.0), float(right_cap_len or 0.0), 1.0)
    if float(bbox_diag or 0.0) > max(30.0, edge_scale * 5.0, cap_scale * 6.0):
        diagnostics.append(f"intersection_upper_slope_face_panel_remote_fan_risk:bbox={float(bbox_diag):.3f}")
    if float(cap_scale or 0.0) > max(18.0, edge_scale * 3.0):
        diagnostics.append(f"intersection_upper_slope_face_panel_remote_fan_risk:cap={float(cap_scale):.3f}")
    if float(bbox_aspect or 0.0) > 8.0:
        diagnostics.append(f"intersection_upper_slope_face_panel_remote_fan_risk:aspect={float(bbox_aspect):.3f}")
    if float(bbox_fill_ratio or 0.0) < 0.05 and float(bbox_diag or 0.0) > edge_scale * 3.0:
        diagnostics.append(f"intersection_upper_slope_face_panel_remote_fan_risk:fill={float(bbox_fill_ratio):.3f}")
    return diagnostics


def _intersection_upper_slope_face_panel_candidate_audit_rows(rows: list[dict[str, object]]) -> list[str]:
    output: list[str] = []
    for row in list(rows or []):
        diagnostics = ",".join(str(value or "") for value in tuple(row.get("diagnostics", ()) or ()) if str(value or ""))
        refs = ",".join(str(value or "") for value in tuple(row.get("source_shared_breakline_refs", ()) or ()) if str(value or ""))
        output.append(
            "|".join(
                [
                    _audit_field(str(row.get("candidate_id", "") or "")),
                    _audit_field(str(row.get("status", "") or "")),
                    _audit_field(str(row.get("alignment_ref", "") or "")),
                    _audit_field(str(row.get("side", "") or "")),
                    f"{float(row.get('loop_area_xy', 0.0) or 0.0):.3f}",
                    _audit_field(str(row.get("inner_edge_ref", "") or "")),
                    _audit_field(str(row.get("outer_edge_ref", "") or "")),
                    _audit_field(str(row.get("left_cap_ref", "") or "")),
                    _audit_field(str(row.get("right_cap_ref", "") or "")),
                    f"inner_len={float(row.get('inner_edge_length', 0.0) or 0.0):.3f}",
                    f"outer_len={float(row.get('outer_edge_length', 0.0) or 0.0):.3f}",
                    f"caps={float(row.get('left_cap_length', 0.0) or 0.0):.3f}/{float(row.get('right_cap_length', 0.0) or 0.0):.3f}",
                    f"bbox_diag={float(row.get('bbox_diagonal', 0.0) or 0.0):.3f}",
                    f"bbox_aspect={float(row.get('bbox_aspect', 0.0) or 0.0):.3f}",
                    f"bbox_fill={float(row.get('bbox_fill_ratio', 0.0) or 0.0):.3f}",
                    f"match={str(row.get('outer_match_mode', '') or '-')}/{str(row.get('design_match_mode', '') or '-')}",
                    _audit_field(refs),
                    _audit_field(diagnostics),
                ]
            )
        )
    return output


def _intersection_upper_slope_face_panel_expected_groups(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_kind: str = "",
) -> list[str]:
    if shared_breakline_result is None:
        return []
    if not _intersection_upper_slope_face_panel_supported(intersection_kind):
        return []
    relevant_roles = {
        "patch_to_intersection_slope_face",
        "intersection_slope_face_to_corridor_slope_face",
        "intersection_slope_face_to_design_surface",
    }
    groups: set[str] = set()
    for row in list(getattr(shared_breakline_result, "breakline_rows", []) or []):
        role = str(getattr(row, "breakline_role", "") or "")
        if role not in relevant_roles:
            continue
        alignment_ref = str(getattr(row, "alignment_ref", "") or "").strip()
        side = str(getattr(row, "side", "") or "").strip()
        if not alignment_ref or not side:
            continue
        groups.add(f"{alignment_ref}:{side}")
    return sorted(groups)


def _intersection_upper_slope_face_panel_coverage_summary(
    rows: list[dict[str, object]],
    *,
    expected_groups: list[str] | tuple[str, ...] | set[str] | None = None,
    unsupported_reason: str = "",
) -> dict[str, object]:
    if unsupported_reason:
        return {
            "status": "suppressed",
            "summary": f"{unsupported_reason}; groups=0 accepted_groups=0 missing_groups=0 expected_groups=0",
            "group_count": 0,
            "accepted_group_count": 0,
            "expected_group_count": 0,
            "missing_group_count": 0,
            "missing_groups": [],
        }
    groups: dict[str, dict[str, int]] = {}
    for row in list(rows or []):
        alignment_ref = str(row.get("alignment_ref", "") or "").strip() or "alignment:unknown"
        side = str(row.get("side", "") or "").strip() or "side:unknown"
        group_key = f"{alignment_ref}:{side}"
        counts = groups.setdefault(group_key, {"candidate": 0, "accepted": 0})
        counts["candidate"] += 1
        if str(row.get("status", "") or "") == "accepted":
            counts["accepted"] += 1
    missing_groups = [
        group_key
        for group_key, counts in sorted(groups.items())
        if int(counts.get("accepted", 0) or 0) <= 0
    ]
    accepted_groups = [
        group_key
        for group_key, counts in sorted(groups.items())
        if int(counts.get("accepted", 0) or 0) > 0
    ]
    expected_group_set = {
        str(value or "").strip()
        for value in list(expected_groups or [])
        if str(value or "").strip()
    }
    expected_missing_groups = [
        group_key
        for group_key in sorted(expected_group_set)
        if group_key not in set(accepted_groups)
    ]
    all_missing_groups = sorted(set(missing_groups) | set(expected_missing_groups))
    status = "missing" if not groups else "warning" if all_missing_groups else "ready"
    return {
        "status": status,
        "summary": (
            f"groups={len(groups)} accepted_groups={len(accepted_groups)} "
            f"missing_groups={len(all_missing_groups)} expected_groups={len(expected_group_set)}"
        ),
        "group_count": len(groups),
        "accepted_group_count": len(accepted_groups),
        "expected_group_count": len(expected_group_set),
        "missing_group_count": len(all_missing_groups),
        "missing_groups": all_missing_groups,
    }


def corridor_intersection_shared_boundary_graph_result(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_id: str = "",
) -> IntersectionSharedBoundaryGraphResult:
    """Compatibility wrapper for typed shared-boundary graph evaluation."""

    return IntersectionSharedBoundaryGraphEvaluationService().evaluate(
        IntersectionSharedBoundaryGraphEvaluationRequest(
            shared_breakline_result=shared_breakline_result,
            intersection_id=intersection_id,
        )
    )


def _matching_intersection_slope_face_cell_breakline_for_panel(
    rows: list[SharedBreaklineRow],
    target_row,
    *,
    alignment_ref: str,
    side: str,
    used_refs: set[str],
    point_map: dict[str, object],
):
    exact_candidates: list[SharedBreaklineRow] = []
    nearest_candidates: list[SharedBreaklineRow] = []
    for row in list(rows or []):
        row_id = str(getattr(row, "breakline_id", "") or "")
        if row_id in used_refs:
            continue
        nearest_candidates.append(row)
        if alignment_ref and str(getattr(row, "alignment_ref", "") or "") != alignment_ref:
            continue
        if side and str(getattr(row, "side", "") or "") != side:
            continue
        exact_candidates.append(row)
    if exact_candidates:
        return exact_candidates[0], "exact"
    nearest = _nearest_intersection_slope_face_cell_breakline(
        nearest_candidates,
        target_row,
        point_map=point_map,
    )
    if nearest is not None:
        return nearest, "nearest"
    return None, "missing"


def _nearest_intersection_slope_face_cell_breakline(
    rows: list[SharedBreaklineRow],
    target_row,
    *,
    point_map: dict[str, object],
):
    target_points = _intersection_slope_face_cell_row_points(target_row, point_map)
    if not target_points:
        return None
    best_row = None
    best_score: tuple[int, float] | None = None
    for row in list(rows or []):
        points = _intersection_slope_face_cell_row_points(row, point_map)
        if not points:
            continue
        distance = min(_xy_distance(first, second) for first in target_points for second in points)
        shared_endpoint = any(
            _intersection_slope_face_points_close_xy(first, second)
            for first in target_points
            for second in points
        )
        score = (0 if shared_endpoint else 1, distance)
        if best_score is None or score < best_score:
            best_score = score
            best_row = row
    return best_row


def _intersection_slope_face_cell_row_points(row, point_map: dict[str, object]) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    if row is None:
        return points
    for ref in tuple(getattr(row, "point_refs", ()) or ()):
        point = point_map.get(str(ref or ""))
        if point is None:
            continue
        xyz = _row_xyz_tuple(point)
        if not points or not _intersection_slope_face_points_close_xyz(points[-1], xyz):
            points.append(xyz)
    return points


def _intersection_slope_face_simplified_closed_loop(
    points: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    for point in list(points or []):
        if not output or not _intersection_slope_face_points_close_xy(output[-1], point):
            output.append(point)
    if output and not _intersection_slope_face_points_close_xy(output[0], output[-1]):
        output.append(output[0])
    return output


def _intersection_slope_face_points_close_xy(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    return math.hypot(float(first[0]) - float(second[0]), float(first[1]) - float(second[1])) <= tolerance


def _intersection_slope_face_points_close_xyz(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    return (
        math.sqrt(
            (float(first[0]) - float(second[0])) ** 2
            + (float(first[1]) - float(second[1])) ** 2
            + (float(first[2]) - float(second[2])) ** 2
        )
        <= tolerance
    )


def _shared_breakline_refs_for_consumer(shared_result, consumer_ref: str) -> list[str]:
    target = str(consumer_ref or "").strip()
    if shared_result is None or not target:
        return []
    return [
        str(getattr(row, "breakline_id", "") or "")
        for row in list(getattr(shared_result, "breakline_rows", []) or [])
        if target in {str(value or "").strip() for value in tuple(getattr(row, "consumer_refs", ()) or ())}
        and str(getattr(row, "breakline_id", "") or "")
    ]


def _tin_surface_with_shared_breakline_metadata(surface, shared_result, *, consumer_ref: str):
    if surface is None or shared_result is None:
        return surface
    surface_id = str(getattr(surface, "surface_id", "") or "surface")
    refs = _shared_breakline_refs_for_consumer(shared_result, consumer_ref)
    boundary_refs = list(getattr(surface, "boundary_refs", []) or [])
    for ref in refs:
        if ref not in boundary_refs:
            boundary_refs.append(ref)
    filtered_quality = [
        quality
        for quality in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(quality, "kind", "") or "") not in {
            "shared_breakline_result_id",
            "shared_breakline_status",
            "shared_breakline_count",
            "shared_breakline_consumed_count",
            "shared_breakline_refs",
            "shared_breakline_constraint_segment_rows",
        }
    ]
    filtered_quality.extend(
        [
            TINQualityRow(f"{surface_id}:shared_breakline_result_id", "shared_breakline_result_id", str(getattr(shared_result, "breakline_result_id", "") or "")),
            TINQualityRow(f"{surface_id}:shared_breakline_status", "shared_breakline_status", str(getattr(shared_result, "status", "") or "")),
            TINQualityRow(f"{surface_id}:shared_breakline_count", "shared_breakline_count", len(refs), "count"),
            TINQualityRow(f"{surface_id}:shared_breakline_consumed_count", "shared_breakline_consumed_count", len(refs), "count"),
            TINQualityRow(f"{surface_id}:shared_breakline_refs", "shared_breakline_refs", ",".join(refs)),
            TINQualityRow(
                f"{surface_id}:shared_breakline_constraint_segment_rows",
                "shared_breakline_constraint_segment_rows",
                ";;".join(_shared_breakline_segment_rows(shared_result, refs)),
                "rows",
                "Surface consumes these SharedBreaklineResult segments as normalized constraint edges.",
            ),
        ]
    )
    return replace(surface, boundary_refs=boundary_refs, quality_rows=filtered_quality)


def _boundary_loop_shared_breakline_refs(shared_result, *, consumer_ref: str = "") -> list[str]:
    target = str(consumer_ref or "").strip()
    refs: list[str] = []
    for row in list(getattr(shared_result, "breakline_rows", []) or []):
        breakline_id = str(getattr(row, "breakline_id", "") or "")
        if not breakline_id:
            continue
        if target and target not in {str(value or "").strip() for value in tuple(getattr(row, "consumer_refs", ()) or ())}:
            continue
        source_refs = ",".join(str(value or "") for value in tuple(getattr(row, "source_contract_refs", ()) or ()))
        if _intersection_boundary_loop_source_refs(source_refs):
            refs.append(breakline_id)
    return _unique_text_values(refs)


def _intersection_shared_boundary_graph_internal_seam_refs(
    graph_result: IntersectionSharedBoundaryGraphResult | None,
    consumer_ref: str,
) -> list[str]:
    target = str(consumer_ref or "").strip()
    if graph_result is None or not target:
        return []
    return [
        str(getattr(row, "edge_id", "") or "")
        for row in list(getattr(graph_result, "edge_rows", []) or [])
        if _intersection_shared_boundary_graph_edge_role_is_internal_seam(str(getattr(row, "edge_role", "") or ""))
        and target in {str(value or "").strip() for value in tuple(getattr(row, "consumer_refs", ()) or ())}
        and str(getattr(row, "edge_id", "") or "")
    ]


def _shared_breakline_segment_rows(shared_result, refs: list[str] | None = None) -> list[str]:
    """Serialize breakline segment geometry for presentation-only 3D audit highlights."""

    if shared_result is None:
        return []
    wanted = {str(ref or "") for ref in list(refs or []) if str(ref or "")}
    point_by_ref: dict[str, list[object]] = {}
    for point in list(getattr(shared_result, "point_rows", []) or []):
        ref = str(getattr(point, "breakline_ref", "") or "")
        if not ref:
            continue
        point_by_ref.setdefault(ref, []).append(point)
    rows: list[str] = []
    for breakline in list(getattr(shared_result, "breakline_rows", []) or []):
        breakline_id = str(getattr(breakline, "breakline_id", "") or "")
        if not breakline_id or (wanted and breakline_id not in wanted):
            continue
        points = sorted(point_by_ref.get(breakline_id, []), key=lambda point: int(getattr(point, "sequence", 0) or 0))
        if len(points) < 2:
            continue
        role = str(getattr(breakline, "breakline_role", "") or "")
        material = str(getattr(breakline, "material_role", "") or "") or role
        status = str(getattr(breakline, "source_status", "") or "")
        consumer_refs = ",".join(str(value or "") for value in tuple(getattr(breakline, "consumer_refs", ()) or ()) if str(value or ""))
        for index, (start, end) in enumerate(zip(points[:-1], points[1:])):
            try:
                values = [
                    breakline_id,
                    role,
                    status,
                    str(index),
                    f"{float(getattr(start, 'x', 0.0) or 0.0):.9g}",
                    f"{float(getattr(start, 'y', 0.0) or 0.0):.9g}",
                    f"{float(getattr(start, 'z', 0.0) or 0.0):.9g}",
                    f"{float(getattr(end, 'x', 0.0) or 0.0):.9g}",
                    f"{float(getattr(end, 'y', 0.0) or 0.0):.9g}",
                    f"{float(getattr(end, 'z', 0.0) or 0.0):.9g}",
                    material,
                ]
                if consumer_refs:
                    values.append(consumer_refs)
                rows.append("|".join(value.replace("|", "_") for value in values))
            except Exception:
                continue
    return rows


def _row_xyz_tuple(row) -> tuple[float, float, float]:
    return (
        float(getattr(row, "x", 0.0) or 0.0),
        float(getattr(row, "y", 0.0) or 0.0),
        float(getattr(row, "z", 0.0) or 0.0),
    )


def _xy_polygon_area(points: list[tuple[float, float]]) -> float:
    return xy_polygon_signed_area(points)


def _xy_triangle_quality_ratio(a, b, c) -> float:
    return xy_triangle_quality_ratio(a, b, c)


def _xy_triangle_area(a, b, c) -> float:
    return xy_triangle_signed_area(a, b, c)


def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return xy_distance(a, b)


def build_intersection_slope_face_surface_from_ready_loops(
    loop_result: IntersectionSlopeFaceLoopResult,
    *,
    project_id: str = "",
    boundary_result: IntersectionSlopeFaceBoundaryResult | None = None,
    boundary_segment_result: IntersectionBoundarySegmentResult | None = None,
    applied_section_set=None,
    shared_breakline_result=None,
) -> TINSurface:
    """Build a small review TIN from ready slope-face loop rows only."""

    surface_id = f"intersection-slope-face:{_safe_id_fragment(str(getattr(loop_result, 'intersection_id', '') or 'main'))}"
    vertices: list[TINVertex] = []
    triangles: list[TINTriangle] = []
    quality_rows: list[TINQualityRow] = []
    rejected_loop_refs: list[str] = []
    generated_loop_refs: list[str] = []
    consumed_loop_refs: list[str] = []
    rejected_degenerate_count = 0
    rejected_skinny_count = 0
    suppressed_applied_boundary_loop_count = 0
    suppressed_preferred_component_loop_fan_count = 0
    min_fan_quality = 1.0
    intersection_kind = str(getattr(loop_result, "intersection_kind", "") or "")
    upper_panel_supported = _intersection_upper_slope_face_panel_supported(intersection_kind)
    curb_return_perimeter_stats = _append_intersection_curb_return_slope_face_perimeter_tin(
        surface_id=surface_id,
        boundary_segment_result=boundary_segment_result,
        applied_section_set=applied_section_set,
        vertices=vertices,
        triangles=triangles,
    )
    cell_result = corridor_intersection_slope_face_cell_result(
        shared_breakline_result,
        intersection_id=str(getattr(loop_result, "intersection_id", "") or ""),
    ) if shared_breakline_result is not None else None
    graph_result = corridor_intersection_shared_boundary_graph_result(
        shared_breakline_result,
        intersection_id=str(getattr(loop_result, "intersection_id", "") or ""),
    ) if shared_breakline_result is not None else None
    upper_panel_candidate_rows = (
        _intersection_upper_slope_face_panel_candidate_rows(
            shared_breakline_result,
            intersection_id=str(getattr(loop_result, "intersection_id", "") or ""),
            intersection_kind=intersection_kind,
        )
        if upper_panel_supported
        else []
    )
    upper_panel_expected_groups = (
        _intersection_upper_slope_face_panel_expected_groups(
            shared_breakline_result,
            intersection_kind=intersection_kind,
        )
        if upper_panel_supported
        else []
    )
    upper_panel_coverage = _intersection_upper_slope_face_panel_coverage_summary(
        upper_panel_candidate_rows,
        expected_groups=upper_panel_expected_groups,
        unsupported_reason="" if upper_panel_supported else f"suppressed_for_intersection_kind:{intersection_kind or 'unknown'}",
    )
    upper_panel_surface_stats = (
        _append_intersection_upper_slope_face_panel_tin(
            surface_id=surface_id,
            candidate_rows=upper_panel_candidate_rows,
            vertices=vertices,
            triangles=triangles,
        )
        if upper_panel_supported
        else {
            "generation_mode": "suppressed_non_t_intersection",
            "panel_count": 0,
            "triangle_count": 0,
            "panel_refs": [],
            "boundary_refs": [],
            "diagnostics": [f"intersection_upper_slope_face_panel_suppressed:{intersection_kind or 'unknown'}"],
        }
    )
    boundary_loop_shared_refs = _boundary_loop_shared_breakline_refs(
        shared_breakline_result,
        consumer_ref="intersection_slope_face_surface",
    ) if shared_breakline_result is not None else []
    graph_audit = intersection_shared_boundary_graph_audit(graph_result)
    graph_surface_stats = _append_intersection_slope_face_graph_cell_tin(
        surface_id=surface_id,
        graph_result=graph_result,
        vertices=vertices,
        triangles=triangles,
    )
    boundary_loop_transition_stats = _append_intersection_boundary_loop_slope_face_transition_tin(
        surface_id=surface_id,
        shared_breakline_result=shared_breakline_result,
        vertices=vertices,
        triangles=triangles,
    )
    boundary_loop_graph_coverage = _intersection_boundary_loop_graph_fill_coverage(
        shared_breakline_result=shared_breakline_result,
        graph_result=graph_result,
        graph_surface_stats=graph_surface_stats,
        boundary_loop_transition_stats=boundary_loop_transition_stats,
    )
    cell_surface_stats = _append_intersection_slope_face_cell_tin(
        surface_id=surface_id,
        cell_result=cell_result,
        shared_breakline_result=shared_breakline_result,
        skip_upper_cells=(
            int(upper_panel_surface_stats.get("panel_count", 0) or 0) > 0
            or not upper_panel_supported
        ),
        skip_upper_reason=(
            "cell_suppressed_for_non_t_intersection"
            if not upper_panel_supported
            else "cell_superseded_by_shared_boundary_graph"
        ),
        vertices=vertices,
        triangles=triangles,
    )
    preferred_components_before_boundary_strip = any(
        int(stats.get("triangle_count", 0) or 0) > 0
        for stats in (
            curb_return_perimeter_stats,
            graph_surface_stats,
            boundary_loop_transition_stats,
            upper_panel_surface_stats,
            cell_surface_stats,
        )
    )
    boundary_strip_stats = _append_intersection_slope_face_boundary_strip_tin(
        surface_id=surface_id,
        boundary_result=boundary_result,
        boundary_segment_result=boundary_segment_result,
        vertices=vertices,
        triangles=triangles,
        emit_geometry=not preferred_components_before_boundary_strip,
    )
    preferred_surface_components_available = any(
        int(stats.get("triangle_count", 0) or 0) > 0
        for stats in (
            curb_return_perimeter_stats,
            graph_surface_stats,
            boundary_loop_transition_stats,

            upper_panel_surface_stats,
            cell_surface_stats,
        )
    )
    ready_rows = [
        row for row in list(getattr(loop_result, "loop_rows", []) or [])
        if _intersection_slope_face_loop_surface_generation_ready(row)
    ]
    skipped_rows = [
        row for row in list(getattr(loop_result, "loop_rows", []) or [])
        if not _intersection_slope_face_loop_surface_generation_ready(row)
    ]
    for loop_index, loop in enumerate(ready_rows, start=1):
        loop_id = str(getattr(loop, "loop_id", "") or "")
        consumed_loop_refs.append(loop_id)
        if (
            _intersection_slope_face_loop_is_applied_section_boundary_completion(loop)
            and (
                int(curb_return_perimeter_stats.get("triangle_count", 0) or 0) > 0
                or int(boundary_strip_stats.get("triangle_count", 0) or 0) > 0
            )
        ):
            suppressed_applied_boundary_loop_count += 1
            skipped_rows.append(loop)
            continue
        if preferred_surface_components_available:
            suppressed_preferred_component_loop_fan_count += 1
            skipped_rows.append(loop)
            continue
        points = _intersection_slope_face_loop_simple_ring_points(loop)
        if len(points) < 3:
            skipped_rows.append(loop)
            continue
        center = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
            sum(point[2] for point in points) / len(points),
        )
        fan_quality = _intersection_slope_face_loop_fan_quality(points, center)
        min_fan_quality = min(min_fan_quality, float(fan_quality.get("min_quality", 1.0) or 0.0))
        if int(fan_quality.get("degenerate_count", 0) or 0) > 0:
            rejected_degenerate_count += 1
            rejected_loop_refs.append(loop_id)
            skipped_rows.append(loop)
            continue
        if int(fan_quality.get("skinny_count", 0) or 0) > 0:
            rejected_skinny_count += 1
        generated_loop_refs.append(loop_id)
        center_id = f"{surface_id}:loop-{loop_index:02d}:center"
        vertices.append(
            TINVertex(
                center_id,
                center[0],
                center[1],
                center[2],
                source_point_ref=str(getattr(loop, "loop_id", "") or ""),
                notes="intersection slope-face loop fan center",
            )
        )
        point_ids: list[str] = []
        for point_index, point in enumerate(points, start=1):
            vertex_id = f"{surface_id}:loop-{loop_index:02d}:p-{point_index:02d}"
            point_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id,
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    source_point_ref=str(getattr(loop, "loop_id", "") or ""),
                    notes="intersection slope-face loop boundary point",
                )
            )
        for point_index, vertex_id in enumerate(point_ids):
            next_id = point_ids[(point_index + 1) % len(point_ids)]
            point = points[point_index]
            next_point = points[(point_index + 1) % len(points)]
            v1, v2, v3 = _triangle_vertex_ids_with_upward_xy_normal(
                center_id,
                center,
                vertex_id,
                point,
                next_id,
                next_point,
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"{surface_id}:loop-{loop_index:02d}:tri-{point_index + 1:02d}",
                    v1=v1,
                    v2=v2,
                    v3=v3,
                    triangle_kind="intersection_slope_face_loop_triangle",
                    quality_ref="intersection_slope_face_loop",
                    notes=str(getattr(loop, "loop_id", "") or ""),
                )
            )
    quality_rows.extend(
        [
            TINQualityRow(f"{surface_id}:ready_loop_count", "ready_loop_count", len(ready_rows), "count"),
            TINQualityRow(f"{surface_id}:generated_loop_count", "generated_loop_count", len(generated_loop_refs), "count"),
            TINQualityRow(f"{surface_id}:skipped_loop_count", "skipped_loop_count", len(skipped_rows), "count"),
            TINQualityRow(f"{surface_id}:rejected_degenerate_loop_count", "rejected_degenerate_loop_count", rejected_degenerate_count, "count"),
            TINQualityRow(f"{surface_id}:rejected_skinny_loop_count", "rejected_skinny_loop_count", rejected_skinny_count, "count"),
            TINQualityRow(
                f"{surface_id}:suppressed_applied_boundary_loop_count",
                "suppressed_applied_boundary_loop_count",
                suppressed_applied_boundary_loop_count,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:suppressed_preferred_component_loop_fan_count",
                "suppressed_preferred_component_loop_fan_count",
                suppressed_preferred_component_loop_fan_count,
                "count",
            ),
            TINQualityRow(f"{surface_id}:fan_min_quality", "fan_min_quality", min_fan_quality if ready_rows else 0.0, "ratio"),
            TINQualityRow(f"{surface_id}:triangle_count", "triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:loop_result_id", "loop_result_id", str(getattr(loop_result, "loop_result_id", "") or "")),
            TINQualityRow(f"{surface_id}:rejected_loop_refs", "rejected_loop_refs", ",".join(_unique_text_values(rejected_loop_refs))),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_result_id",
                "intersection_slope_face_cell_result_id",
                str(getattr(cell_result, "cell_result_id", "") or ""),
            ),
            TINQualityRow(

                f"{surface_id}:intersection_slope_face_cell_status",
                "intersection_slope_face_cell_status",
                str(getattr(cell_result, "status", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_count",
                "intersection_slope_face_cell_count",
                int(getattr(cell_result, "cell_count", 0) or 0) if cell_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_ready_count",
                "intersection_slope_face_cell_ready_count",
                int(getattr(cell_result, "ready_count", 0) or 0) if cell_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_open_count",
                "intersection_slope_face_cell_open_count",
                int(getattr(cell_result, "open_cell_count", 0) or 0) if cell_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_missing_edge_count",
                "intersection_slope_face_cell_missing_edge_count",
                int(getattr(cell_result, "missing_edge_count", 0) or 0) if cell_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_triangle_count",
                "intersection_slope_face_cell_triangle_count",
                int(cell_surface_stats.get("triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_refs",
                "intersection_slope_face_cell_refs",
                ",".join(_unique_text_values(list(cell_surface_stats.get("cell_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_role_summary",
                "intersection_slope_face_cell_role_summary",
                str(cell_surface_stats.get("cell_role_summary", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_upper_cell_refs",
                "intersection_slope_face_upper_cell_refs",
                ",".join(_unique_text_values(list(cell_surface_stats.get("upper_cell_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_suppressed_upper_cell_count",
                "intersection_slope_face_suppressed_upper_cell_count",
                int(cell_surface_stats.get("suppressed_upper_cell_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_suppressed_upper_cell_refs",
                "intersection_slope_face_suppressed_upper_cell_refs",
                ",".join(_unique_text_values(list(cell_surface_stats.get("suppressed_upper_cell_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_diagnostic",
                "intersection_slope_face_cell_diagnostic",
                "; ".join(
                    _unique_text_values(
                        [
                            *list(getattr(cell_result, "diagnostic_rows", []) or []),
                            *list(cell_surface_stats.get("diagnostics", []) or []),
                        ]
                    )
                ),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_cell_audit_rows",
                "intersection_slope_face_cell_audit_rows",
                ";;".join(_intersection_slope_face_cell_audit_rows(cell_result)),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_candidate_count",
                "intersection_upper_slope_face_panel_candidate_count",
                len(upper_panel_candidate_rows),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_accepted_count",
                "intersection_upper_slope_face_panel_accepted_count",
                sum(1 for row in upper_panel_candidate_rows if str(row.get("status", "") or "") == "accepted"),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_coverage_summary",
                "intersection_upper_slope_face_panel_coverage_summary",
                upper_panel_coverage.get("summary", ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_expected_group_count",
                "intersection_upper_slope_face_panel_expected_group_count",
                int(upper_panel_coverage.get("expected_group_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_coverage_status",
                "intersection_upper_slope_face_panel_coverage_status",
                upper_panel_coverage.get("status", ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_missing_groups",
                "intersection_upper_slope_face_panel_missing_groups",
                ",".join(upper_panel_coverage.get("missing_groups", [])),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_candidate_rows",
                "intersection_upper_slope_face_panel_candidate_rows",
                ";;".join(_intersection_upper_slope_face_panel_candidate_audit_rows(upper_panel_candidate_rows)),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_source_mode",

                "intersection_upper_slope_face_panel_source_mode",
                (
                    "accepted_upper_rectangular_panel_boundary"
                    if upper_panel_candidate_rows
                    else "suppressed_non_t_intersection"
                    if not upper_panel_supported
                    else "missing"
                ),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_generation_mode",
                "intersection_upper_slope_face_panel_generation_mode",
                str(upper_panel_surface_stats.get("generation_mode", "") or "not_evaluated"),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_triangle_count",
                "intersection_upper_slope_face_panel_triangle_count",
                int(upper_panel_surface_stats.get("triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_generated_count",
                "intersection_upper_slope_face_panel_generated_count",
                int(upper_panel_surface_stats.get("panel_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_refs",
                "intersection_upper_slope_face_panel_refs",
                ",".join(_unique_text_values(list(upper_panel_surface_stats.get("panel_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_boundary_refs",
                "intersection_upper_slope_face_panel_boundary_refs",
                ",".join(_unique_text_values(list(upper_panel_surface_stats.get("boundary_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_upper_slope_face_panel_diagnostic",
                "intersection_upper_slope_face_panel_diagnostic",
                "; ".join(_unique_text_values(list(upper_panel_surface_stats.get("diagnostics", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_result_id",
                "intersection_shared_boundary_graph_result_id",
                str(getattr(graph_result, "graph_result_id", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_status",
                "intersection_shared_boundary_graph_status",
                str(getattr(graph_result, "status", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_node_count",
                "intersection_shared_boundary_graph_node_count",
                int(getattr(graph_result, "node_count", 0) or 0) if graph_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_edge_count",
                "intersection_shared_boundary_graph_edge_count",
                int(getattr(graph_result, "edge_count", 0) or 0) if graph_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_cell_count",
                "intersection_shared_boundary_graph_cell_count",
                int(getattr(graph_result, "cell_count", 0) or 0) if graph_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_duplicate_edge_count",
                "intersection_shared_boundary_graph_duplicate_edge_count",
                int(getattr(graph_result, "duplicate_edge_count", 0) or 0) if graph_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_missing_consumer_count",
                "intersection_shared_boundary_graph_missing_consumer_count",
                int(getattr(graph_result, "missing_consumer_count", 0) or 0) if graph_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_source_segment_split_count",
                "intersection_shared_boundary_graph_source_segment_split_count",
                int(graph_audit.get("source_segment_split_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_open_cell_count",
                "intersection_shared_boundary_graph_open_cell_count",
                int(getattr(graph_result, "graph_open_cell_count", 0) or 0) if graph_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_endpoint_mismatch_count",
                "intersection_shared_boundary_graph_endpoint_mismatch_count",
                int(graph_audit.get("endpoint_mismatch_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_not_snapped_count",
                "intersection_shared_boundary_graph_not_snapped_count",
                int(graph_audit.get("not_snapped_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_audit_rows",
                "intersection_shared_boundary_graph_audit_rows",
                ";;".join(_intersection_shared_boundary_graph_audit_rows(graph_result)),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_segment_rows",
                "intersection_shared_boundary_graph_segment_rows",

                ";;".join(_intersection_shared_boundary_graph_segment_rows(graph_result)),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_surface_generation_mode",
                "intersection_shared_boundary_graph_surface_generation_mode",
                str(graph_surface_stats.get("generation_mode", "") or "not_evaluated"),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_surface_triangle_count",
                "intersection_shared_boundary_graph_surface_triangle_count",
                int(graph_surface_stats.get("triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_internal_seam_count",
                "intersection_shared_boundary_graph_internal_seam_count",
                len(_intersection_shared_boundary_graph_internal_seam_refs(graph_result, "intersection_slope_face_surface")),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_internal_seam_refs",
                "intersection_shared_boundary_graph_internal_seam_refs",
                ",".join(_intersection_shared_boundary_graph_internal_seam_refs(graph_result, "intersection_slope_face_surface")),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_surface_cell_refs",
                "intersection_shared_boundary_graph_surface_cell_refs",
                ",".join(_unique_text_values(list(graph_surface_stats.get("cell_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_surface_boundary_refs",
                "intersection_shared_boundary_graph_surface_boundary_refs",
                ",".join(_unique_text_values(list(graph_surface_stats.get("boundary_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_shared_boundary_graph_surface_diagnostic",
                "intersection_shared_boundary_graph_surface_diagnostic",
                "; ".join(_unique_text_values(list(graph_surface_stats.get("diagnostics", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_shared_breakline_count",
                "intersection_boundary_loop_shared_breakline_count",
                len(boundary_loop_shared_refs),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_shared_breakline_refs",
                "intersection_boundary_loop_shared_breakline_refs",
                ",".join(_unique_text_values(boundary_loop_shared_refs)),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_generation_mode",
                "intersection_boundary_loop_transition_generation_mode",
                str(boundary_loop_transition_stats.get("generation_mode", "") or "not_evaluated"),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_strip_count",
                "intersection_boundary_loop_transition_strip_count",
                int(boundary_loop_transition_stats.get("strip_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_triangle_count",
                "intersection_boundary_loop_transition_triangle_count",
                int(boundary_loop_transition_stats.get("triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_corner_fill_count",
                "intersection_boundary_loop_transition_corner_fill_count",
                int(boundary_loop_transition_stats.get("corner_fill_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_refs",
                "intersection_boundary_loop_transition_refs",
                ",".join(_unique_text_values(list(boundary_loop_transition_stats.get("boundary_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_diagnostic",
                "intersection_boundary_loop_transition_diagnostic",
                "; ".join(_unique_text_values(list(boundary_loop_transition_stats.get("diagnostics", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_role_summary",
                "intersection_boundary_loop_transition_role_summary",
                str(boundary_loop_transition_stats.get("role_summary", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_width_summary",
                "intersection_boundary_loop_transition_width_summary",
                str(boundary_loop_transition_stats.get("width_summary", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_rows",
                "intersection_boundary_loop_transition_rows",
                ";;".join(_unique_text_values(list(boundary_loop_transition_stats.get("transition_rows", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_transition_corner_fill_rows",
                "intersection_boundary_loop_transition_corner_fill_rows",
                ";;".join(_unique_text_values(list(boundary_loop_transition_stats.get("corner_fill_rows", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_coverage_status",

                "intersection_boundary_loop_graph_coverage_status",
                str(boundary_loop_graph_coverage.get("status", "") or "not_evaluated"),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_edge_count",
                "intersection_boundary_loop_graph_edge_count",
                int(boundary_loop_graph_coverage.get("boundary_loop_graph_edge_count", 0) or 0),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_consumer_edge_count",
                "intersection_boundary_loop_graph_consumer_edge_count",
                int(boundary_loop_graph_coverage.get("consumer_edge_count", 0) or 0),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_filled_edge_count",
                "intersection_boundary_loop_graph_filled_edge_count",
                int(boundary_loop_graph_coverage.get("filled_edge_count", 0) or 0),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_missing_edge_count",
                "intersection_boundary_loop_graph_missing_edge_count",
                int(boundary_loop_graph_coverage.get("missing_edge_count", 0) or 0),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_non_consumer_edge_count",
                "intersection_boundary_loop_graph_non_consumer_edge_count",
                int(boundary_loop_graph_coverage.get("non_consumer_edge_count", 0) or 0),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_non_consumer_role_summary",
                "intersection_boundary_loop_graph_non_consumer_role_summary",
                str(boundary_loop_graph_coverage.get("non_consumer_role_summary", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_consumer_coverage_summary",
                "intersection_boundary_loop_graph_consumer_coverage_summary",
                str(boundary_loop_graph_coverage.get("consumer_coverage_summary", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_consumer_missing_summary",
                "intersection_boundary_loop_graph_consumer_missing_summary",
                str(boundary_loop_graph_coverage.get("consumer_missing_summary", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_edge_refs",
                "intersection_boundary_loop_graph_edge_refs",
                ",".join(_unique_text_values(list(boundary_loop_graph_coverage.get("boundary_loop_graph_edge_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_consumer_edge_refs",
                "intersection_boundary_loop_graph_consumer_edge_refs",
                ",".join(_unique_text_values(list(boundary_loop_graph_coverage.get("consumer_edge_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_filled_edge_refs",
                "intersection_boundary_loop_graph_filled_edge_refs",
                ",".join(_unique_text_values(list(boundary_loop_graph_coverage.get("filled_edge_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_missing_edge_refs",
                "intersection_boundary_loop_graph_missing_edge_refs",
                ",".join(_unique_text_values(list(boundary_loop_graph_coverage.get("missing_edge_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_non_consumer_edge_refs",
                "intersection_boundary_loop_graph_non_consumer_edge_refs",
                ",".join(_unique_text_values(list(boundary_loop_graph_coverage.get("non_consumer_edge_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_boundary_loop_graph_non_consumer_edge_rows",
                "intersection_boundary_loop_graph_non_consumer_edge_rows",
                ";;".join(_unique_text_values(list(boundary_loop_graph_coverage.get("non_consumer_edge_rows", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:curb_return_slope_face_perimeter_count",
                "curb_return_slope_face_perimeter_count",
                int(curb_return_perimeter_stats.get("strip_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:curb_return_slope_face_perimeter_triangle_count",
                "curb_return_slope_face_perimeter_triangle_count",
                int(curb_return_perimeter_stats.get("triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:curb_return_slope_face_perimeter_generation_mode",
                "curb_return_slope_face_perimeter_generation_mode",
                str(curb_return_perimeter_stats.get("generation_mode", "") or "not_evaluated"),
            ),
            TINQualityRow(
                f"{surface_id}:curb_return_slope_face_perimeter_refs",
                "curb_return_slope_face_perimeter_refs",
                ",".join(_unique_text_values(list(curb_return_perimeter_stats.get("boundary_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:curb_return_slope_face_perimeter_diagnostic",
                "curb_return_slope_face_perimeter_diagnostic",
                "; ".join(_unique_text_values(list(curb_return_perimeter_stats.get("diagnostics", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_result_id",

                "intersection_slope_face_boundary_result_id",
                str(getattr(boundary_result, "boundary_result_id", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_status",
                "intersection_slope_face_boundary_status",
                str(getattr(boundary_result, "status", "") or ""),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_count",
                "intersection_slope_face_boundary_count",
                int(getattr(boundary_result, "boundary_count", 0) or 0) if boundary_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_ready_count",
                "intersection_slope_face_boundary_ready_count",
                int(getattr(boundary_result, "ready_count", 0) or 0) if boundary_result is not None else 0,
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_count",
                "intersection_slope_face_boundary_strip_count",
                int(boundary_strip_stats.get("strip_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_triangle_count",
                "intersection_slope_face_boundary_strip_triangle_count",
                int(boundary_strip_stats.get("triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_transition_strip_count",
                "intersection_slope_face_transition_strip_count",
                int(boundary_strip_stats.get("transition_strip_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_transition_strip_triangle_count",
                "intersection_slope_face_transition_strip_triangle_count",
                int(boundary_strip_stats.get("transition_triangle_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_generation_mode",
                "intersection_slope_face_boundary_strip_generation_mode",
                str(boundary_strip_stats.get("generation_mode", "") or "not_evaluated"),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_output_path",
                "intersection_slope_face_boundary_strip_output_path",
                "visible_surface" if int(boundary_strip_stats.get("triangle_count", 0) or 0) > 0 else "metadata_only",
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_refs",
                "intersection_slope_face_boundary_refs",
                ",".join(_unique_text_values(list(boundary_strip_stats.get("boundary_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:intersection_slope_face_boundary_strip_diagnostic",
                "intersection_slope_face_boundary_strip_diagnostic",
                "; ".join(_unique_text_values(list(boundary_strip_stats.get("diagnostics", []) or []))),
            ),
        ]
    )
    surface = TINSurface(
        schema_version=int(getattr(loop_result, "schema_version", 1) or 1),
        project_id=str(project_id or getattr(loop_result, "project_id", "") or ""),
        surface_id=surface_id,
        surface_kind="intersection_slope_face_surface",
        label=f"Intersection Slope Face Surface - {getattr(loop_result, 'intersection_id', '') or 'main'}",
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=_unique_text_values([
            *consumed_loop_refs,
            *generated_loop_refs,
            *boundary_loop_shared_refs,
            *list(boundary_loop_transition_stats.get("boundary_refs", []) or []),
            *list(graph_surface_stats.get("cell_refs", []) or []),
            *list(graph_surface_stats.get("boundary_refs", []) or []),
            *list(cell_surface_stats.get("cell_refs", []) or []),
            *list(cell_surface_stats.get("boundary_refs", []) or []),
            *list(curb_return_perimeter_stats.get("boundary_refs", []) or []),
            *list(boundary_strip_stats.get("boundary_refs", []) or []),
        ]),
        quality_rows=quality_rows,
        source_refs=list(getattr(loop_result, "source_refs", []) or []),
    )
    if shared_breakline_result is not None:
        surface = _tin_surface_with_shared_breakline_metadata(
            surface,
            shared_breakline_result,
            consumer_ref="intersection_slope_face_surface",
        )
    return surface


def intersection_upper_slope_face_panel_candidate_rows(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_id: str = "",
    intersection_kind: str = "",
) -> list[dict[str, object]]:
    """Return source-boundary candidates for upper slope-face panels."""

    return _intersection_upper_slope_face_panel_candidate_rows(
        shared_breakline_result,
        intersection_id=intersection_id,
        intersection_kind=intersection_kind,
    )


# __SERVICE_BODY_END__


__all__ = [
    "build_intersection_slope_face_surface_from_ready_loops",
    "intersection_upper_slope_face_panel_candidate_rows",
]
