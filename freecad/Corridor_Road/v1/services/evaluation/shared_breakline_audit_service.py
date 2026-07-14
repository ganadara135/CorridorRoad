"""Typed shared-breakline consumer and solid-readiness audit service."""

from __future__ import annotations

import math

from ...models.result.shared_breakline_audit import (
    SharedBreaklineAdjacencyResult,
    SharedBreaklineAuditResult,
)


class SharedBreaklineAuditService:
    """Audit normalized shared-breakline results without documents or UI state."""

    def adjacency(
        self,
        shared_result,
        *,
        tolerance: float = 1.0e-6,
    ) -> SharedBreaklineAdjacencyResult:
        if shared_result is None:
            return SharedBreaklineAdjacencyResult(
                status="missing",
                notes="shared_breakline_result_missing",
            )
        point_map = {
            str(getattr(point, "point_id", "") or ""): point
            for point in list(getattr(shared_result, "point_rows", []) or [])
            if str(getattr(point, "point_id", "") or "")
        }
        node_degree: dict[tuple[int, int, int], int] = {}
        edge_seen: dict[
            tuple[tuple[int, int, int], tuple[int, int, int]],
            tuple[str, str],
        ] = {}
        edge_count = 0
        duplicate_edge_count = 0
        reversed_edge_count = 0
        notes: list[str] = []
        for row in list(getattr(shared_result, "breakline_rows", []) or []):
            breakline_id = str(getattr(row, "breakline_id", "") or "")
            points = [
                point_map.get(str(ref or ""))
                for ref in tuple(getattr(row, "point_refs", ()) or ())
            ]
            points = [point for point in points if point is not None]
            if len(points) < 2:
                notes.append(f"open_breakline_points_missing:{breakline_id}")
                continue
            for start_point, end_point in zip(points[:-1], points[1:]):
                start_key = _adjacency_node_key(start_point, tolerance=tolerance)
                end_key = _adjacency_node_key(end_point, tolerance=tolerance)
                if start_key == end_key:
                    notes.append(f"zero_length_edge:{breakline_id}")
                    continue
                node_degree[start_key] = node_degree.get(start_key, 0) + 1
                node_degree[end_key] = node_degree.get(end_key, 0) + 1
                edge_count += 1
                canonical = tuple(sorted((start_key, end_key)))
                previous = edge_seen.get(canonical)
                direction = (
                    "forward" if canonical == (start_key, end_key) else "reverse",
                    breakline_id,
                )
                if previous is not None:
                    duplicate_edge_count += 1
                    notes.append(f"duplicate_edge:{breakline_id}:{previous[1]}")
                    if previous[0] != direction[0]:
                        reversed_edge_count += 1
                        notes.append(f"reversed_edge:{breakline_id}:{previous[1]}")
                else:
                    edge_seen[canonical] = direction
        open_nodes = [node for node, degree in node_degree.items() if degree == 1]
        non_manifold_nodes = [
            node for node, degree in node_degree.items() if degree > 2
        ]
        issue_count = (
            len(open_nodes)
            + duplicate_edge_count
            + reversed_edge_count
            + len(non_manifold_nodes)
        )
        if open_nodes:
            notes.append(f"open_end_count={len(open_nodes)}")
        if non_manifold_nodes:
            notes.append(f"non_manifold_node_count={len(non_manifold_nodes)}")
        status = "ready" if edge_count and issue_count == 0 else "warning" if edge_count else "missing"
        return SharedBreaklineAdjacencyResult(
            status=status,
            node_count=len(node_degree),
            edge_count=edge_count,
            open_end_count=len(open_nodes),
            duplicate_edge_count=duplicate_edge_count,
            reversed_edge_count=reversed_edge_count,
            non_manifold_node_count=len(non_manifold_nodes),
            notes="; ".join(notes) if notes else "shared_breakline_adjacency=closed",
        )

    def audit(
        self,
        shared_result,
        consumer_surfaces: dict[str, object] | None = None,
    ) -> SharedBreaklineAuditResult:
        if shared_result is None:
            return SharedBreaklineAuditResult(
                status="missing",
                solid_readiness_status="missing",
                solid_readiness_notes="shared_breakline_result_missing",
                notes="shared_breakline_result_missing",
            )
        surfaces = dict(consumer_surfaces or {})
        point_map = {
            str(getattr(point, "point_id", "") or ""): point
            for point in list(getattr(shared_result, "point_rows", []) or [])
            if str(getattr(point, "point_id", "") or "")
        }
        missing_consumer_count = 0
        mismatch_count = 0
        geometry_match_count = 0
        geometry_mismatch_count = 0
        mesh_match_count = 0
        mesh_mismatch_count = 0
        reversed_edge_count = 0
        notes: list[str] = []
        for row in list(getattr(shared_result, "breakline_rows", []) or []):
            breakline_id = str(getattr(row, "breakline_id", "") or "")
            breakline_points = [
                point_map.get(str(ref or ""))
                for ref in tuple(getattr(row, "point_refs", ()) or ())
            ]
            breakline_points = [point for point in breakline_points if point is not None]
            for consumer_ref in tuple(getattr(row, "consumer_refs", ()) or ()):
                consumer = str(consumer_ref or "")
                surface = surfaces.get(consumer)
                if surface is None:
                    continue
                if breakline_id not in list(getattr(surface, "boundary_refs", []) or []):
                    missing_consumer_count += 1
                    notes.append(f"missing_consumer:{consumer}:{breakline_id}")
                    continue
                contract_geometry = _constraint_matches(
                    surface,
                    breakline_id,
                    breakline_points,
                )
                contract_matched = bool(contract_geometry["matched"])
                mesh_geometry = None
                if len(breakline_points) >= 2 and list(
                    getattr(surface, "triangle_rows", []) or []
                ):
                    mesh_geometry = _boundary_edge_matches(surface, breakline_points)
                    if mesh_geometry["matched"]:
                        mesh_match_count += 1
                    elif contract_matched:
                        mesh_match_count += 1
                        _append_distance_note(
                            notes,
                            "mesh_constraint_covered",
                            consumer,
                            breakline_id,
                            mesh_geometry,
                        )
                    else:
                        mesh_mismatch_count += 1
                        _append_distance_note(
                            notes,
                            "mesh_drift",
                            consumer,
                            breakline_id,
                            mesh_geometry,
                        )
                if contract_matched:
                    geometry_match_count += 1
                    if contract_geometry["reversed"]:
                        reversed_edge_count += 1
                        notes.append(f"reversed_constraint_edge:{consumer}:{breakline_id}")
                    continue
                if mesh_geometry is not None:
                    if mesh_geometry["matched"]:
                        geometry_match_count += 1
                    else:
                        geometry_mismatch_count += 1
                        _append_distance_note(
                            notes,
                            "geometry_mismatch",
                            consumer,
                            breakline_id,
                            mesh_geometry,
                        )
        mismatch_count += int(getattr(shared_result, "error_count", 0) or 0)
        status = (
            "ready"
            if missing_consumer_count == 0
            and mismatch_count == 0
            and geometry_mismatch_count == 0
            and mesh_mismatch_count == 0
            and int(getattr(shared_result, "breakline_count", 0) or 0)
            else "warning"
        )
        solid_graph = self.adjacency(shared_result)
        return SharedBreaklineAuditResult(
            status=status,
            missing_consumer_count=missing_consumer_count,
            mismatch_count=mismatch_count,
            geometry_match_count=geometry_match_count,
            geometry_mismatch_count=geometry_mismatch_count,
            mesh_match_count=mesh_match_count,
            mesh_mismatch_count=mesh_mismatch_count,
            reversed_edge_count=reversed_edge_count,
            solid_readiness_status=solid_graph.status,
            solid_open_end_count=solid_graph.open_end_count,
            solid_duplicate_edge_count=solid_graph.duplicate_edge_count,
            solid_reversed_edge_count=solid_graph.reversed_edge_count,
            solid_non_manifold_node_count=solid_graph.non_manifold_node_count,
            solid_readiness_notes=solid_graph.notes,
            notes="; ".join(notes) if notes else "shared_breakline=ready",
            source_result_ref=str(
                getattr(shared_result, "shared_breakline_result_id", "") or ""
            ),
            consumer_refs=tuple(sorted(surfaces)),
        )


def _append_distance_note(notes, kind, consumer, breakline_id, result) -> None:
    distance = result.get("distance", None)
    if distance is None:
        notes.append(f"{kind}:{consumer}:{breakline_id}")
    else:
        notes.append(
            f"{kind}:{consumer}:{breakline_id}:distance={float(distance):.4g}m"
        )


def _adjacency_node_key(point, *, tolerance: float) -> tuple[int, int, int]:
    scale = 1.0 / max(float(tolerance or 0.0), 1.0e-9)
    x, y, z = _row_xyz(point)
    return (int(round(x * scale)), int(round(y * scale)), int(round(z * scale)))


def _constraint_matches(
    surface,
    breakline_id: str,
    breakline_points: list[object],
    *,
    tolerance: float = 5.0e-2,
) -> dict[str, object]:
    target_points = [_row_xyz(point) for point in breakline_points]
    if len(target_points) < 2:
        return {"matched": False, "reversed": False}
    matching_rows = [
        row
        for row in _constraint_segment_rows(surface)
        if str(row.get("breakline_id", "") or "") == str(breakline_id or "")
    ]
    if not matching_rows:
        return {"matched": False, "reversed": False}
    return _segment_rows_cover_polyline(
        matching_rows,
        target_points,
        _polyline_stations(target_points),
        tolerance=tolerance,
    )


def _constraint_segment_rows(surface) -> list[dict[str, object]]:
    text = _quality_text(surface, "shared_breakline_constraint_segment_rows")
    rows: list[dict[str, object]] = []
    for raw in str(text or "").split(";;") if text else []:
        parsed = _parse_segment_row(raw)
        if parsed is not None:
            rows.append(parsed)
    return rows


def _parse_segment_row(row: object) -> dict[str, object] | None:
    parts = str(row or "").split("|")
    if len(parts) not in {10, 11, 12}:
        return None
    try:
        return {
            "breakline_id": parts[0],
            "role": parts[1],
            "status": parts[2],
            "segment_index": int(parts[3] or 0),
            "start": (float(parts[4]), float(parts[5]), float(parts[6])),
            "end": (float(parts[7]), float(parts[8]), float(parts[9])),
            "material": parts[10] if len(parts) > 10 else "",
            "consumers": parts[11] if len(parts) > 11 else "",
        }
    except Exception:
        return None


def _segment_rows_cover_polyline(rows, points, stations, *, tolerance) -> dict[str, object]:
    total_length = stations[-1] if stations else 0.0
    if total_length <= tolerance:
        return {"matched": False, "reversed": False, "coverage": 0.0}
    intervals = []
    forward_count = 0
    reversed_count = 0
    distances = []
    for row in rows:
        start = tuple(float(value) for value in row.get("start", ()))
        end = tuple(float(value) for value in row.get("end", ()))
        if len(start) != 3 or len(end) != 3:
            continue
        start_projection = _project_to_polyline(start, points, stations)
        end_projection = _project_to_polyline(end, points, stations)
        start_distance = float(start_projection.get("distance", 0.0) or 0.0)
        end_distance = float(end_projection.get("distance", 0.0) or 0.0)
        distances.extend([start_distance, end_distance])
        if start_distance > tolerance or end_distance > tolerance:
            continue
        start_station = float(start_projection.get("station", 0.0) or 0.0)
        end_station = float(end_projection.get("station", 0.0) or 0.0)
        if abs(end_station - start_station) <= tolerance:
            continue
        intervals.append((min(start_station, end_station), max(start_station, end_station)))
        if end_station >= start_station:
            forward_count += 1
        else:
            reversed_count += 1
    merged = _merge_intervals(intervals, gap_tolerance=max(tolerance, total_length * 0.01))
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


def _boundary_edge_matches(surface, breakline_points, *, tolerance=5.0e-2):
    target_points = [_row_xyz(point) for point in breakline_points]
    target_start = target_points[0]
    target_end = target_points[-1]
    vertex_map = {
        str(getattr(vertex, "vertex_id", "") or ""): vertex
        for vertex in list(getattr(surface, "vertex_rows", []) or [])
        if str(getattr(vertex, "vertex_id", "") or "")
    }
    edges = _all_edge_rows(surface)
    for edge in edges:
        start = vertex_map.get(str(edge.get("first_id", "") or ""))
        end = vertex_map.get(str(edge.get("second_id", "") or ""))
        if start is None or end is None:
            continue
        start_xyz = _row_xyz(start)
        end_xyz = _row_xyz(end)
        if _distance(start_xyz, target_start) <= tolerance and _distance(end_xyz, target_end) <= tolerance:
            return {"matched": True, "reversed": False}
        if _distance(start_xyz, target_end) <= tolerance and _distance(end_xyz, target_start) <= tolerance:
            return {"matched": True, "reversed": True}
    chain = _boundary_chain_matches(vertex_map, edges, target_points, tolerance=tolerance)
    if chain["matched"]:
        return chain
    coverage = _boundary_coverage_matches(vertex_map, edges, target_points, tolerance=tolerance)
    if coverage["matched"]:
        return coverage
    return {
        "matched": False,
        "reversed": False,
        "distance": coverage.get("distance", _boundary_min_distance(vertex_map, edges, target_points)),
        "coverage": coverage.get("coverage", 0.0),
    }


def _boundary_chain_matches(vertex_map, edges, points, *, tolerance):
    if len(points) < 2:
        return {"matched": False, "reversed": False}
    target_start, target_end = points[0], points[-1]
    if sum(_distance(a, b) for a, b in zip(points[:-1], points[1:])) <= tolerance:
        return {"matched": False, "reversed": False}
    candidate_edges = []
    vertex_ids = set()
    for edge in edges:
        first_id = str(edge.get("first_id", "") or "")
        second_id = str(edge.get("second_id", "") or "")
        first = vertex_map.get(first_id)
        second = vertex_map.get(second_id)
        if first is None or second is None:
            continue
        if (
            _point_near_polyline(_row_xyz(first), points, tolerance=tolerance)
            and _point_near_polyline(_row_xyz(second), points, tolerance=tolerance)
        ):
            candidate_edges.append((first_id, second_id))
            vertex_ids.update((first_id, second_id))
    if not candidate_edges:
        return {"matched": False, "reversed": False}
    start_ids = [value for value in vertex_ids if _distance(_row_xyz(vertex_map[value]), target_start) <= tolerance]
    end_ids = [value for value in vertex_ids if _distance(_row_xyz(vertex_map[value]), target_end) <= tolerance]
    graph = {}
    oriented = set(candidate_edges)
    for first_id, second_id in candidate_edges:
        graph.setdefault(first_id, set()).add(second_id)
        graph.setdefault(second_id, set()).add(first_id)
    for start_id in start_ids:
        for end_id in end_ids:
            path = _graph_path(graph, start_id, end_id)
            if path:
                forward = sum((a, b) in oriented for a, b in zip(path[:-1], path[1:]))
                reversed_count = sum((b, a) in oriented for a, b in zip(path[:-1], path[1:]))
                return {"matched": True, "reversed": reversed_count > forward}
    return {"matched": False, "reversed": False}


def _boundary_coverage_matches(vertex_map, edges, points, *, tolerance):
    stations = _polyline_stations(points)
    total_length = stations[-1] if stations else 0.0
    if total_length <= tolerance:
        return {"matched": False, "reversed": False, "coverage": 0.0}
    intervals = []
    distances = []
    forward_count = 0
    reversed_count = 0
    for edge in edges:
        first = vertex_map.get(str(edge.get("first_id", "") or ""))
        second = vertex_map.get(str(edge.get("second_id", "") or ""))
        if first is None or second is None:
            continue
        first_xyz, second_xyz = _row_xyz(first), _row_xyz(second)
        first_projection = _project_to_polyline(first_xyz, points, stations)
        second_projection = _project_to_polyline(second_xyz, points, stations)
        first_distance = float(first_projection.get("distance", 0.0) or 0.0)
        second_distance = float(second_projection.get("distance", 0.0) or 0.0)
        distances.extend([first_distance, second_distance])
        if first_distance > tolerance or second_distance > tolerance:
            continue
        first_station = float(first_projection.get("station", 0.0) or 0.0)
        second_station = float(second_projection.get("station", 0.0) or 0.0)
        span = abs(second_station - first_station)
        edge_length = _distance(first_xyz, second_xyz)
        if span <= tolerance or edge_length <= tolerance:
            continue
        if abs(edge_length - span) > max(tolerance * 2.0, span * 0.15):
            continue
        intervals.append((min(first_station, second_station), max(first_station, second_station)))
        if second_station >= first_station:
            forward_count += 1
        else:
            reversed_count += 1
    merged = _merge_intervals(intervals, gap_tolerance=max(tolerance, total_length * 0.01))
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


def _all_edge_rows(surface):
    counts = {}
    values = {}
    for triangle in list(getattr(surface, "triangle_rows", []) or []):
        ids = [str(getattr(triangle, name, "") or "") for name in ("v1", "v2", "v3")]
        for first_id, second_id in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if not first_id or not second_id:
                continue
            key = tuple(sorted((first_id, second_id)))
            counts[key] = counts.get(key, 0) + 1
            values.setdefault(key, {"first_id": first_id, "second_id": second_id})
    rows = []
    for key, row in values.items():
        item = dict(row)
        item["edge_count"] = counts[key]
        item["is_boundary"] = counts[key] == 1
        rows.append(item)
    return rows


def _quality_text(surface, kind):
    for row in list(getattr(surface, "quality_rows", []) or []):
        if str(getattr(row, "kind", "") or "") == str(kind or ""):
            return str(getattr(row, "value", "") or "")
    return ""


def _polyline_stations(points):
    stations = [0.0]
    for first, second in zip(points[:-1], points[1:]):
        stations.append(stations[-1] + _distance(first, second))
    return stations


def _project_to_polyline(point, points, stations):
    best_distance = None
    best_station = 0.0
    for index, (start, end) in enumerate(zip(points[:-1], points[1:])):
        projection = _project_to_segment(point, start, end)
        distance = float(projection["distance"])
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_station = float(stations[index]) + _distance(start, end) * float(projection["ratio"])
    return {"station": best_station, "distance": float(best_distance or 0.0)}


def _merge_intervals(intervals, *, gap_tolerance):
    ordered = sorted((float(start), float(end)) for start, end in intervals if float(end) >= float(start))
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


def _point_near_polyline(point, points, *, tolerance):
    return any(
        _point_to_segment_distance(point, start, end) <= tolerance
        for start, end in zip(points[:-1], points[1:])
    )


def _boundary_min_distance(vertex_map, edges, points):
    distances = []
    for edge in edges:
        for vertex_id in (str(edge.get("first_id", "") or ""), str(edge.get("second_id", "") or "")):
            vertex = vertex_map.get(vertex_id)
            if vertex is not None:
                distances.append(_point_to_polyline_distance(_row_xyz(vertex), points))
    return min(distances) if distances else 0.0


def _point_to_polyline_distance(point, points):
    distances = [_point_to_segment_distance(point, start, end) for start, end in zip(points[:-1], points[1:])]
    return min(distances) if distances else 0.0


def _graph_path(graph, start_id, end_id):
    if start_id == end_id:
        return [start_id]
    pending = [[start_id]]
    visited = {start_id}
    while pending:
        path = pending.pop(0)
        for next_id in sorted(graph.get(path[-1], set())):
            if next_id in visited:
                continue
            next_path = path + [next_id]
            if next_id == end_id:
                return next_path
            visited.add(next_id)
            pending.append(next_path)
    return []


def _point_to_segment_distance(point, start, end):
    return float(_project_to_segment(point, start, end)["distance"])


def surface_boundary_edge_matches_shared_breakline(
    surface,
    breakline_points,
    *,
    tolerance: float = 5.0e-2,
) -> dict[str, object]:
    """Expose the typed mesh-boundary audit used by compatibility callers."""

    return _boundary_edge_matches(
        surface,
        breakline_points,
        tolerance=tolerance,
    )


def _project_to_segment(point, start, end):
    vector = tuple(float(end[i]) - float(start[i]) for i in range(3))
    offset = tuple(float(point[i]) - float(start[i]) for i in range(3))
    length_sq = sum(value * value for value in vector)
    if length_sq <= 1.0e-18:
        return {"distance": _distance(point, start), "ratio": 0.0}
    ratio = sum(offset[i] * vector[i] for i in range(3)) / length_sq
    ratio = max(0.0, min(1.0, ratio))
    closest = tuple(float(start[i]) + vector[i] * ratio for i in range(3))
    return {"distance": _distance(point, closest), "ratio": ratio}


def _row_xyz(row):
    return tuple(float(getattr(row, name, 0.0) or 0.0) for name in ("x", "y", "z"))


def _distance(first, second):
    return math.sqrt(sum((float(first[i]) - float(second[i])) ** 2 for i in range(3)))
