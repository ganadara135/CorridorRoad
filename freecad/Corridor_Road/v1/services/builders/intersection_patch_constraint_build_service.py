"""Typed boundary for Intersection patch shared-breakline constraint builds."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Callable

from ...models.result.intersection_patch_constraint_build import (
    IntersectionPatchConstraintBuildResult,
)
from ...models.result.tin_surface import TINTriangle, TINVertex


ConstraintBuilder = Callable[..., tuple[list[object], list[object], dict[str, object]]]


@dataclass(frozen=True)
class IntersectionPatchConstraintBuildRequest:
    surface_id: str
    vertices: tuple[object, ...]
    triangles: tuple[object, ...]
    shared_breakline_result: object | None = None


class IntersectionPatchConstraintBuildService:
    """Normalize constraint output rows, metrics, pass-through, and failures."""

    def __init__(self, constraint_builder: ConstraintBuilder | None = None) -> None:
        self.constraint_builder = constraint_builder

    def build(
        self,
        request: IntersectionPatchConstraintBuildRequest,
    ) -> IntersectionPatchConstraintBuildResult:
        builder = self.constraint_builder or self.constraint_rows
        try:
            vertices, triangles, raw_stats = builder(
                vertices=list(request.vertices),
                triangles=list(request.triangles),
                shared_result=request.shared_breakline_result,
                surface_id=request.surface_id,
            )
        except Exception as exc:
            return IntersectionPatchConstraintBuildResult(
                status="error",
                surface_id=request.surface_id,
                vertex_rows=tuple(request.vertices),
                triangle_rows=tuple(request.triangles),
                diagnostic_rows=(
                    "intersection_patch_constraint_build_failed:"
                    f"{type(exc).__name__}:{exc}",
                ),
                error_message=str(exc),
            )
        stats = dict(raw_stats or {})
        role_counts = tuple(
            sorted(
                (
                    str(role or ""),
                    int(count or 0),
                )
                for role, count in dict(
                    stats.get("boundary_loop_role_counts", {}) or {}
                ).items()
                if str(role or "") and int(count or 0) > 0
            )
        )
        role_summary = ", ".join(
            f"{role}={count}" for role, count in role_counts
        )
        return IntersectionPatchConstraintBuildResult(
            status="ready",
            surface_id=request.surface_id,
            vertex_rows=tuple(vertices or ()),
            triangle_rows=tuple(triangles or ()),
            mode=str(stats.get("mode", "none") or "none"),
            segment_count=int(stats.get("segment_count", 0) or 0),
            edge_count=int(stats.get("edge_count", 0) or 0),
            inserted_vertex_count=int(stats.get("vertex_count", 0) or 0),
            boundary_loop_segment_count=int(
                stats.get("boundary_loop_segment_count", 0) or 0
            ),
            boundary_loop_edge_count=int(
                stats.get("boundary_loop_edge_count", 0) or 0
            ),
            boundary_loop_refs=tuple(
                str(value or "")
                for value in list(stats.get("boundary_loop_refs", []) or [])
                if str(value or "")
            ),
            boundary_loop_role_counts=role_counts,
            boundary_loop_role_summary=role_summary,
            snap_count=int(stats.get("snap_count", 0) or 0),
            snap_max_distance=float(
                stats.get("snap_max_distance", 0.0) or 0.0
            ),
            snap_diagnostic_rows=tuple(
                str(value or "")
                for value in list(stats.get("snap_diagnostics", []) or [])
                if str(value or "")
            ),
        )

    def constraint_rows(
        self,
        *,
        vertices: list[object],
        triangles: list[object],
        shared_result: object | None,
        surface_id: str,
        consumer_ref: str = "intersection_surface",
    ) -> tuple[list[object], list[object], dict[str, object]]:
        """Preserve accepted shared-breakline segments as TIN edges."""

        output_vertices = list(vertices or [])
        output_triangles = list(triangles or [])
        stats = _empty_constraint_stats()
        if shared_result is None:
            return output_vertices, output_triangles, stats
        breakline_refs = set(
            _breakline_refs_for_consumer(shared_result, consumer_ref)
        )
        if not breakline_refs:
            return output_vertices, output_triangles, stats
        point_rows_by_id = {
            str(getattr(point, "point_id", "") or ""): point
            for point in list(getattr(shared_result, "point_rows", []) or [])
            if str(getattr(point, "point_id", "") or "")
        }
        breakline_rows = [
            row
            for row in list(getattr(shared_result, "breakline_rows", []) or [])
            if str(getattr(row, "breakline_id", "") or "") in breakline_refs
        ]
        if not breakline_rows:
            return output_vertices, output_triangles, stats
        vertex_by_xyz = {
            _vertex_xyz_key(vertex): str(getattr(vertex, "vertex_id", "") or "")
            for vertex in output_vertices
            if str(getattr(vertex, "vertex_id", "") or "")
        }
        vertex_by_id = {
            str(getattr(vertex, "vertex_id", "") or ""): vertex
            for vertex in output_vertices
            if str(getattr(vertex, "vertex_id", "") or "")
        }
        edge_keys = _triangle_vertex_edge_keys(output_triangles)
        edge_xyz_keys = _triangle_xyz_edge_keys(output_triangles, vertex_by_id)
        next_vertex_index = len(output_vertices) + 1
        next_triangle_index = len(output_triangles) + 1
        snapped_vertex_ids: set[str] = set()
        stats["mode"] = "support_triangle_edge_preservation"
        for breakline in breakline_rows:
            breakline_id = str(getattr(breakline, "breakline_id", "") or "")
            source_refs_text = ",".join(
                str(value or "")
                for value in tuple(
                    getattr(breakline, "source_contract_refs", ()) or ()
                )
            )
            is_boundary_loop = bool(_boundary_loop_source_refs(source_refs_text))
            if is_boundary_loop:
                stats["boundary_loop_refs"] = _unique_text_values(
                    [*list(stats["boundary_loop_refs"]), breakline_id]
                )
                role = str(
                    getattr(breakline, "breakline_role", "") or "unknown"
                )
                role_counts = dict(stats["boundary_loop_role_counts"])
                role_counts[role] = int(role_counts.get(role, 0) or 0) + 1
                stats["boundary_loop_role_counts"] = role_counts
            points = [
                point_rows_by_id.get(str(point_ref or ""))
                for point_ref in list(
                    getattr(breakline, "point_refs", ()) or ()
                )
            ]
            points = sorted(
                (point for point in points if point is not None),
                key=lambda point: int(getattr(point, "sequence", 0) or 0),
            )
            for start_point, end_point in zip(points, points[1:]):
                stats["segment_count"] = int(stats["segment_count"]) + 1
                if is_boundary_loop:
                    stats["boundary_loop_segment_count"] = (
                        int(stats["boundary_loop_segment_count"]) + 1
                    )
                start_id, next_vertex_index, added_start = _ensure_vertex(
                    output_vertices,
                    vertex_by_xyz,
                    start_point,
                    surface_id=surface_id,
                    breakline_id=breakline_id,
                    next_vertex_index=next_vertex_index,
                    stats=stats,
                    snapped_vertex_ids=snapped_vertex_ids,
                )
                end_id, next_vertex_index, added_end = _ensure_vertex(
                    output_vertices,
                    vertex_by_xyz,
                    end_point,
                    surface_id=surface_id,
                    breakline_id=breakline_id,
                    next_vertex_index=next_vertex_index,
                    stats=stats,
                    snapped_vertex_ids=snapped_vertex_ids,
                )
                stats["vertex_count"] = (
                    int(stats["vertex_count"]) + added_start + added_end
                )
                for vertex_id in (start_id, end_id):
                    if vertex_id and vertex_id not in vertex_by_id:
                        added_vertex = _vertex_by_id(output_vertices, vertex_id)
                        if added_vertex is not None:
                            vertex_by_id[vertex_id] = added_vertex
                segment_edge_key = tuple(sorted((start_id, end_id)))
                start_vertex = vertex_by_id.get(start_id)
                end_vertex = vertex_by_id.get(end_id)
                segment_xyz_key = _edge_xyz_key(start_vertex, end_vertex)
                if start_id == end_id:
                    continue
                if segment_edge_key in edge_keys:
                    _record_preserved_edge(stats, is_boundary_loop)
                    continue
                if segment_xyz_key is not None and segment_xyz_key in edge_xyz_keys:
                    edge_keys.add(segment_edge_key)
                    _record_preserved_edge(stats, is_boundary_loop)
                    continue
                if _existing_edges_cover_segment(
                    output_triangles,
                    vertex_by_id,
                    start_vertex,
                    end_vertex,
                    tolerance=5.0e-2,
                ):
                    edge_keys.add(segment_edge_key)
                    _record_preserved_edge(stats, is_boundary_loop)
                    continue
                support_vertex, next_vertex_index = _support_vertex(
                    start_point,
                    end_point,
                    surface_id=surface_id,
                    breakline_id=breakline_id,
                    next_vertex_index=next_vertex_index,
                )
                if support_vertex is None:
                    continue
                output_vertices.append(support_vertex)
                vertex_by_xyz[_vertex_xyz_key(support_vertex)] = (
                    support_vertex.vertex_id
                )
                vertex_by_id[support_vertex.vertex_id] = support_vertex
                stats["vertex_count"] = int(stats["vertex_count"]) + 1
                triangle_id = (
                    f"{surface_id}:shared-breakline-constraint:"
                    f"{next_triangle_index}"
                )
                next_triangle_index += 1
                output_triangles.append(
                    TINTriangle(
                        triangle_id=triangle_id,
                        v1=start_id,
                        v2=end_id,
                        v3=support_vertex.vertex_id,
                        triangle_kind="constraint_support_triangle",
                        quality_ref="shared_breakline_constraint_edge",
                        notes=f"shared_breakline_ref={breakline_id}",
                    )
                )
                edge_keys.update(
                    {
                        segment_edge_key,
                        tuple(sorted((start_id, support_vertex.vertex_id))),
                        tuple(sorted((end_id, support_vertex.vertex_id))),
                    }
                )
                for first_vertex, second_vertex in (
                    (start_vertex, end_vertex),
                    (start_vertex, support_vertex),
                    (end_vertex, support_vertex),
                ):
                    edge_xyz_key = _edge_xyz_key(first_vertex, second_vertex)
                    if edge_xyz_key is not None:
                        edge_xyz_keys.add(edge_xyz_key)
                _record_preserved_edge(stats, is_boundary_loop)
        return output_vertices, output_triangles, stats


def _empty_constraint_stats() -> dict[str, object]:
    return {
        "mode": "none",
        "segment_count": 0,
        "edge_count": 0,
        "vertex_count": 0,
        "boundary_loop_segment_count": 0,
        "boundary_loop_edge_count": 0,
        "boundary_loop_refs": [],
        "boundary_loop_role_counts": {},
        "snap_count": 0,
        "snap_max_distance": 0.0,
        "snap_diagnostics": [],
    }


def _breakline_refs_for_consumer(shared_result, consumer_ref: str) -> list[str]:
    target = str(consumer_ref or "").strip()
    if shared_result is None or not target:
        return []
    return [
        str(getattr(row, "breakline_id", "") or "")
        for row in list(getattr(shared_result, "breakline_rows", []) or [])
        if target
        in {
            str(value or "").strip()
            for value in tuple(getattr(row, "consumer_refs", ()) or ())
        }
        and str(getattr(row, "breakline_id", "") or "")
    ]


def _boundary_loop_source_refs(source_refs: str) -> list[str]:
    return [
        value.strip()
        for value in str(source_refs or "").split(",")
        if value.strip()
        and (
            "intersection-boundary-loop" in value.strip()
            or "intersection-boundary-loops" in value.strip()
        )
    ]


def _unique_text_values(values) -> list[str]:
    output = []
    seen = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _record_preserved_edge(stats: dict[str, object], boundary_loop: bool) -> None:
    stats["edge_count"] = int(stats["edge_count"]) + 1
    if boundary_loop:
        stats["boundary_loop_edge_count"] = (
            int(stats["boundary_loop_edge_count"]) + 1
        )


def _vertex_xyz_key(vertex) -> tuple[float, float, float]:
    return tuple(round(value, 6) for value in _row_xyz(vertex))


def _row_xyz(row) -> tuple[float, float, float]:
    return (
        float(getattr(row, "x", 0.0) or 0.0),
        float(getattr(row, "y", 0.0) or 0.0),
        float(getattr(row, "z", 0.0) or 0.0),
    )


def _triangle_vertex_edge_keys(triangles) -> set[tuple[str, str]]:
    edges = set()
    for triangle in list(triangles or []):
        vertex_ids = _triangle_vertex_ids(triangle)
        for first, second in _triangle_edges(vertex_ids):
            if first and second and first != second:
                edges.add(tuple(sorted((first, second))))
    return edges


def _triangle_vertex_ids(triangle) -> list[str]:
    return [
        str(getattr(triangle, name, "") or "") for name in ("v1", "v2", "v3")
    ]


def _triangle_edges(vertex_ids) -> tuple[tuple[str, str], ...]:
    return (
        (vertex_ids[0], vertex_ids[1]),
        (vertex_ids[1], vertex_ids[2]),
        (vertex_ids[2], vertex_ids[0]),
    )


def _triangle_xyz_edge_keys(triangles, vertex_by_id):
    edges = set()
    for triangle in list(triangles or []):
        for first_id, second_id in _triangle_edges(_triangle_vertex_ids(triangle)):
            key = _edge_xyz_key(
                vertex_by_id.get(first_id),
                vertex_by_id.get(second_id),
            )
            if key is not None:
                edges.add(key)
    return edges


def _edge_xyz_key(first, second):
    if first is None or second is None:
        return None
    first_key = _vertex_xyz_key(first)
    second_key = _vertex_xyz_key(second)
    if first_key == second_key:
        return None
    return tuple(sorted((first_key, second_key)))


def _vertex_by_id(vertices, vertex_id: str):
    wanted = str(vertex_id or "")
    if not wanted:
        return None
    for vertex in reversed(list(vertices or [])):
        if str(getattr(vertex, "vertex_id", "") or "") == wanted:
            return vertex
    return None


def _ensure_vertex(
    vertices,
    vertex_by_xyz,
    point,
    *,
    surface_id,
    breakline_id,
    next_vertex_index,
    stats,
    snapped_vertex_ids,
):
    key = _vertex_xyz_key(point)
    existing_id = vertex_by_xyz.get(key)
    if existing_id:
        return existing_id, next_vertex_index, 0
    snapped = _snap_near_vertex(
        vertices,
        vertex_by_xyz,
        point,
        breakline_id=breakline_id,
        stats=stats,
        snapped_vertex_ids=snapped_vertex_ids,
    )
    if snapped:
        return snapped, next_vertex_index, 0
    vertex_id = f"{surface_id}:shared-breakline-point:{next_vertex_index}"
    vertices.append(
        TINVertex(
            vertex_id=vertex_id,
            x=float(getattr(point, "x", 0.0) or 0.0),
            y=float(getattr(point, "y", 0.0) or 0.0),
            z=float(getattr(point, "z", 0.0) or 0.0),
            source_point_ref=str(
                getattr(point, "source_point_ref", "") or ""
            ),
            notes=f"shared_breakline_ref={breakline_id}",
        )
    )
    vertex_by_xyz[key] = vertex_id
    return vertex_id, next_vertex_index + 1, 1


def _snap_near_vertex(
    vertices,
    vertex_by_xyz,
    point,
    *,
    breakline_id,
    stats,
    snapped_vertex_ids,
    tolerance: float = 5.0e-2,
) -> str:
    target = _row_xyz(point)
    best_index = -1
    best_distance = float(tolerance)
    for index, vertex in enumerate(list(vertices or [])):
        vertex_id = str(getattr(vertex, "vertex_id", "") or "")
        if not vertex_id or vertex_id in snapped_vertex_ids:
            continue
        distance = _distance_3d(_row_xyz(vertex), target)
        if distance <= best_distance:
            best_index = index
            best_distance = distance
    if best_index < 0:
        return ""
    original = vertices[best_index]
    vertex_id = str(getattr(original, "vertex_id", "") or "")
    original_key = _vertex_xyz_key(original)
    original_notes = str(getattr(original, "notes", "") or "")
    snap_note = (
        f"shared_breakline_ref={breakline_id}; snapped_to_accepted_breakline; "
        f"snap_distance={best_distance:.6g}m"
    )
    vertices[best_index] = replace(
        original,
        x=float(getattr(point, "x", 0.0) or 0.0),
        y=float(getattr(point, "y", 0.0) or 0.0),
        z=float(getattr(point, "z", 0.0) or 0.0),
        source_point_ref=str(
            getattr(original, "source_point_ref", "")
            or getattr(point, "source_point_ref", "")
            or ""
        ),
        notes=f"{original_notes}; {snap_note}" if original_notes else snap_note,
    )
    if vertex_by_xyz.get(original_key) == vertex_id:
        vertex_by_xyz.pop(original_key, None)
    vertex_by_xyz[_vertex_xyz_key(vertices[best_index])] = vertex_id
    snapped_vertex_ids.add(vertex_id)
    stats["snap_count"] = int(stats["snap_count"]) + 1
    stats["snap_max_distance"] = max(
        float(stats["snap_max_distance"]),
        float(best_distance),
    )
    stats["snap_diagnostics"] = [
        *list(stats["snap_diagnostics"]),
        (
            f"snapped_result_vertex:{vertex_id}:{breakline_id}:"
            f"distance={best_distance:.6g}m"
        ),
    ]
    return vertex_id


def _support_vertex(
    start_point,
    end_point,
    *,
    surface_id,
    breakline_id,
    next_vertex_index,
):
    sx, sy, sz = _row_xyz(start_point)
    ex, ey, ez = _row_xyz(end_point)
    dx = ex - sx
    dy = ey - sy
    length_xy = math.hypot(dx, dy)
    if length_xy <= 1.0e-9:
        return None, next_vertex_index
    offset = max(0.02, min(0.10, length_xy * 0.01))
    nx = -dy / length_xy
    ny = dx / length_xy
    return (
        TINVertex(
            vertex_id=(
                f"{surface_id}:shared-breakline-support:{next_vertex_index}"
            ),
            x=(sx + ex) * 0.5 + nx * offset,
            y=(sy + ey) * 0.5 + ny * offset,
            z=(sz + ez) * 0.5,
            source_point_ref=breakline_id,
            notes="support vertex for shared breakline constraint edge",
        ),
        next_vertex_index + 1,
    )


def _existing_edges_cover_segment(
    triangles,
    vertex_by_id,
    start_vertex,
    end_vertex,
    *,
    tolerance,
) -> bool:
    if start_vertex is None or end_vertex is None:
        return False
    target_points = [_row_xyz(start_vertex), _row_xyz(end_vertex)]
    if _distance_3d(*target_points) <= max(float(tolerance or 0.0), 1.0e-9):
        return False
    coverage = _boundary_coverage_matches(
        vertex_by_id,
        _edge_rows_from_triangles(triangles),
        target_points,
        tolerance=float(tolerance or 0.0),
    )
    return bool(coverage.get("matched", False))


def _edge_rows_from_triangles(triangles) -> list[dict[str, object]]:
    edge_counts = {}
    edge_values = {}
    for triangle in list(triangles or []):
        for first_id, second_id in _triangle_edges(_triangle_vertex_ids(triangle)):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            edge_values.setdefault(
                key,
                {
                    "first_id": first_id,
                    "second_id": second_id,
                    "quality_ref": str(
                        getattr(triangle, "quality_ref", "") or ""
                    ),
                    "triangle_id": str(
                        getattr(triangle, "triangle_id", "") or ""
                    ),
                },
            )
    rows = []
    for key, row in edge_values.items():
        item = dict(row)
        item["edge_count"] = int(edge_counts.get(key, 0) or 0)
        item["is_boundary"] = item["edge_count"] == 1
        rows.append(item)
    return rows


def _boundary_coverage_matches(
    vertex_map,
    boundary_edges,
    target_points,
    *,
    tolerance,
):
    stations = _polyline_stations(target_points)
    total_length = stations[-1] if stations else 0.0
    if total_length <= tolerance:
        return {"matched": False, "reversed": False, "coverage": 0.0}
    intervals = []
    distances = []
    forward_count = 0
    reversed_count = 0
    for edge in list(boundary_edges or []):
        first = vertex_map.get(str(edge.get("first_id", "") or ""))
        second = vertex_map.get(str(edge.get("second_id", "") or ""))
        if first is None or second is None:
            continue
        first_xyz = _row_xyz(first)
        second_xyz = _row_xyz(second)
        first_projection = _project_to_polyline(first_xyz, target_points, stations)
        second_projection = _project_to_polyline(second_xyz, target_points, stations)
        first_distance = float(first_projection["distance"])
        second_distance = float(second_projection["distance"])
        distances.extend([first_distance, second_distance])
        if first_distance > tolerance or second_distance > tolerance:
            continue
        first_station = float(first_projection["station"])
        second_station = float(second_projection["station"])
        span = abs(second_station - first_station)
        edge_length = _distance_3d(first_xyz, second_xyz)
        if span <= tolerance or edge_length <= tolerance:
            continue
        if abs(edge_length - span) > max(tolerance * 2.0, span * 0.15):
            continue
        intervals.append(
            (min(first_station, second_station), max(first_station, second_station))
        )
        if second_station >= first_station:
            forward_count += 1
        else:
            reversed_count += 1
    merged = _merge_intervals(
        intervals,
        gap_tolerance=max(tolerance, total_length * 0.01),
    )
    covered = sum(max(0.0, end - start) for start, end in merged)
    coverage = covered / total_length if total_length > 0.0 else 0.0
    start_covered = any(
        start <= tolerance and end >= min(total_length, tolerance)
        for start, end in merged
    )
    end_covered = any(
        start <= max(0.0, total_length - tolerance)
        and end >= total_length - tolerance
        for start, end in merged
    )
    return {
        "matched": coverage >= 0.95 and start_covered and end_covered,
        "reversed": reversed_count > forward_count,
        "coverage": coverage,
        "distance": min(distances) if distances else 0.0,
    }


def _polyline_stations(points) -> list[float]:
    stations = [0.0]
    for first, second in zip(list(points or [])[:-1], list(points or [])[1:]):
        stations.append(stations[-1] + _distance_3d(first, second))
    return stations


def _project_to_polyline(point, points, stations):
    best_distance = None
    best_station = 0.0
    for index, (start, end) in enumerate(
        zip(list(points or [])[:-1], list(points or [])[1:])
    ):
        projection = _project_to_segment(point, start, end)
        distance = float(projection["distance"])
        if best_distance is None or distance < best_distance:
            ratio = float(projection["ratio"])
            best_distance = distance
            best_station = float(stations[index]) + _distance_3d(start, end) * ratio
    return {
        "station": best_station,
        "distance": float(best_distance if best_distance is not None else 0.0),
    }


def _project_to_segment(point, start, end):
    vector = tuple(float(end[i]) - float(start[i]) for i in range(3))
    relative = tuple(float(point[i]) - float(start[i]) for i in range(3))
    length_sq = sum(value * value for value in vector)
    if length_sq <= 1.0e-18:
        return {"distance": _distance_3d(point, start), "ratio": 0.0}
    ratio = sum(relative[i] * vector[i] for i in range(3)) / length_sq
    ratio = max(0.0, min(1.0, ratio))
    closest = tuple(float(start[i]) + vector[i] * ratio for i in range(3))
    return {"distance": _distance_3d(point, closest), "ratio": ratio}


def _merge_intervals(intervals, *, gap_tolerance):
    ordered = sorted(
        (float(start), float(end))
        for start, end in list(intervals or [])
        if float(end) >= float(start)
    )
    if not ordered:
        return []
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + gap_tolerance:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _distance_3d(first, second) -> float:
    return math.sqrt(
        sum((float(first[i]) - float(second[i])) ** 2 for i in range(3))
    )
