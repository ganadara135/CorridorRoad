"""Build the canonical Intersection shared-boundary graph from result contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryCellRow,
    IntersectionSharedBoundaryEdgeRow,
    IntersectionSharedBoundaryGraphResult,
    IntersectionSharedBoundaryNodeRow,
)
from ...models.result.shared_breakline import SharedBreaklineResult
from .intersection_slope_face_cell_evaluation_service import (
    IntersectionSlopeFaceCellEvaluationRequest,
    IntersectionSlopeFaceCellEvaluationService,
)


INTERSECTION_SHARED_BOUNDARY_GRAPH_ROLES = {
    "patch_to_design_surface",
    "patch_to_intersection_slope_face",
    "intersection_slope_face_to_design_surface",
    "intersection_slope_face_to_corridor_slope_face",
    "main_road_tie",
    "side_road_tie",
    "main_side_slope_face_tie",
    "curb_return_to_intersection_slope_face",
    "curb_return_bridge_to_intersection_slope_face",
    "intersection_tie_slope_transition_inner",
    "intersection_tie_slope_transition_outer",
    "intersection_tie_slope_start_cap",
    "intersection_tie_slope_end_cap",
    "roundabout_island_to_circulatory",
    "roundabout_circulatory_to_apron",
    "roundabout_apron_to_slope_face",
    "roundabout_entry_exit_connector_boundary",
    "roundabout_approach_clip_to_design_surface",
    "roundabout_subgrade_clip_to_subgrade_surface",
    "roundabout_subgrade_to_approach_subgrade",
    "roundabout_slope_handoff_to_slope_face_surface",
    "roundabout_slope_to_corridor_slope_face",
    "intersection_upper_slope_face_panel_inner",
    "intersection_upper_slope_face_panel_outer",
    "intersection_upper_slope_face_panel_left_cap",
    "intersection_upper_slope_face_panel_right_cap",
    "upper_transition_internal_seam",
    "cell_closure_internal_seam",
}

INTERSECTION_SHARED_BOUNDARY_EXPECTED_CONSUMERS = {
    "patch_to_design_surface": (
        "intersection_surface",
        "design_surface",
        "intersection_slope_face_surface",
    ),
    "patch_to_intersection_slope_face": (
        "intersection_surface",
        "intersection_slope_face_surface",
    ),
    "intersection_slope_face_to_design_surface": (
        "intersection_slope_face_surface",
        "design_surface",
    ),
    "intersection_slope_face_to_corridor_slope_face": (
        "intersection_slope_face_surface",
        "slope_face_surface",
    ),
    "main_road_tie": (
        "intersection_surface",
        "design_surface",
        "intersection_slope_face_surface",
    ),
    "side_road_tie": (
        "intersection_surface",
        "design_surface",
        "intersection_slope_face_surface",
    ),
    "main_side_slope_face_tie": ("intersection_slope_face_surface",),
    "curb_return_to_intersection_slope_face": (
        "intersection_surface",
        "intersection_slope_face_surface",
    ),
    "curb_return_bridge_to_intersection_slope_face": (
        "intersection_slope_face_surface",
        "intersection_slope_face_cell_result",
    ),
    "intersection_tie_slope_transition_inner": (
        "intersection_tie_slope_surface",
        "intersection_slope_face_surface",
        "intersection_surface",
    ),
    "intersection_tie_slope_transition_outer": (
        "intersection_tie_slope_surface",
        "slope_face_surface",
    ),
    "intersection_tie_slope_start_cap": ("intersection_tie_slope_surface",),
    "intersection_tie_slope_end_cap": ("intersection_tie_slope_surface",),
    "roundabout_island_to_circulatory": (
        "intersection_surface",
        "roundabout_central_island",
        "roundabout_circulatory_surface",
    ),
    "roundabout_circulatory_to_apron": (
        "intersection_surface",
        "roundabout_circulatory_surface",
        "roundabout_apron_surface",
    ),
    "roundabout_apron_to_slope_face": (
        "roundabout_apron_surface",
        "roundabout_slope_face_surface",
    ),
    "roundabout_entry_exit_connector_boundary": (
        "roundabout_entry_exit_connector",
        "design_surface",
        "roundabout_circulatory_surface",
    ),
    "roundabout_approach_clip_to_design_surface": ("design_surface",),
    "roundabout_subgrade_clip_to_subgrade_surface": (
        "subgrade_surface",
        "roundabout_subgrade_surface",
    ),
    "roundabout_subgrade_to_approach_subgrade": (
        "subgrade_surface",
        "roundabout_subgrade_surface",
    ),
    "roundabout_slope_handoff_to_slope_face_surface": ("slope_face_surface",),
    "roundabout_slope_to_corridor_slope_face": ("slope_face_surface",),
    "roundabout_central_island_boundary": (
        "intersection_surface",
        "roundabout_central_island",
        "roundabout_circulatory_surface",
    ),
    "roundabout_circulatory_outer_boundary": (
        "intersection_surface",
        "roundabout_circulatory_surface",
        "roundabout_apron_surface",
    ),
    "roundabout_outer_ownership_boundary": (
        "roundabout_apron_surface",
        "roundabout_slope_face_surface",
    ),
    "intersection_upper_slope_face_panel_inner": (
        "intersection_upper_slope_face_panel_handoff",
    ),
    "intersection_upper_slope_face_panel_outer": (
        "intersection_upper_slope_face_panel_handoff",
    ),
    "intersection_upper_slope_face_panel_left_cap": (
        "intersection_upper_slope_face_panel_handoff",
    ),
    "intersection_upper_slope_face_panel_right_cap": (
        "intersection_upper_slope_face_panel_handoff",
    ),
    "upper_transition_internal_seam": ("intersection_slope_face_surface",),
    "cell_closure_internal_seam": ("intersection_slope_face_surface",),
}


@dataclass(frozen=True)
class IntersectionSharedBoundaryGraphEvaluationRequest:
    """Typed input for shared-boundary graph evaluation."""

    shared_breakline_result: SharedBreaklineResult | None
    intersection_id: str = ""


class IntersectionSharedBoundaryGraphEvaluationService:
    """Evaluate canonical topology without FreeCAD document or preview state."""

    def evaluate(
        self,
        request: IntersectionSharedBoundaryGraphEvaluationRequest,
    ) -> IntersectionSharedBoundaryGraphResult:
        return _evaluate_intersection_shared_boundary_graph(
            request.shared_breakline_result,
            intersection_id=request.intersection_id,
        )


def _evaluate_intersection_shared_boundary_graph(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_id: str = "",
) -> IntersectionSharedBoundaryGraphResult:
    """Convert intersection shared breaklines into canonical shared-boundary graph edges."""

    if shared_breakline_result is None:
        return IntersectionSharedBoundaryGraphResult(
            schema_version=1,
            project_id="",
            graph_result_id="intersection-shared-boundary-graph:main",
            intersection_id=str(intersection_id or ""),
            status="missing",
            diagnostic_rows=["shared_breakline_result_missing"],
        )

    project_id = str(getattr(shared_breakline_result, "project_id", "") or "")
    target_intersection_id = str(intersection_id or getattr(shared_breakline_result, "domain_ref", "") or "")
    result_id = f"intersection-shared-boundary-graph:{target_intersection_id or 'main'}"
    point_map = {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(shared_breakline_result, "point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }
    node_rows: list[IntersectionSharedBoundaryNodeRow] = []
    edge_rows: list[IntersectionSharedBoundaryEdgeRow] = []
    cell_rows: list[IntersectionSharedBoundaryCellRow] = []
    diagnostic_rows: list[str] = []
    node_ref_by_xyz: dict[tuple[float, float, float], str] = {}
    duplicate_key_owner: dict[tuple[str, tuple[tuple[float, float, float], tuple[float, float, float]]], str] = {}
    edge_ref_by_breakline_ref: dict[str, str] = {}
    duplicate_edge_count = 0
    missing_consumer_count = 0

    def node_ref_for_xyz(
        xyz: tuple[float, float, float],
        *,
        role: str,
        source_refs: tuple[str, ...] = (),
    ) -> str:
        key = _intersection_shared_boundary_node_key(xyz)
        existing = node_ref_by_xyz.get(key)
        if existing:
            return existing
        node_id = f"{result_id}:node:{len(node_rows) + 1}"
        node_ref_by_xyz[key] = node_id
        node_rows.append(
            IntersectionSharedBoundaryNodeRow(
                node_id=node_id,
                intersection_id=target_intersection_id,
                node_role=_intersection_shared_boundary_node_role(role),
                x=xyz[0],
                y=xyz[1],
                z=xyz[2],
                source_refs=tuple(str(value or "") for value in source_refs if str(value or "")),
                notes=f"Canonical shared-boundary node from {role}.",
            )
        )
        return node_id

    def node_ref_for_point(point, *, role: str, source_ref: str) -> str:
        return node_ref_for_xyz(
            _row_xyz_tuple(point),
            role=role,
            source_refs=(source_ref, str(getattr(point, "source_point_ref", "") or "")),
        )

    for index, row in enumerate(list(getattr(shared_breakline_result, "breakline_rows", []) or []), start=1):
        role = str(getattr(row, "breakline_role", "") or "")
        if role not in INTERSECTION_SHARED_BOUNDARY_GRAPH_ROLES:
            continue
        raw_consumers = {
            str(value or "")
            for value in tuple(getattr(row, "consumer_refs", ()) or ())
            if str(value or "")
        }
        if role in {"control_area_entry", "control_area_exit"} and "intersection_slope_face_cell_result" not in raw_consumers:
            continue
        breakline_id = str(getattr(row, "breakline_id", "") or "")
        ordered_points = [
            point_map.get(str(point_ref or ""))
            for point_ref in tuple(getattr(row, "point_refs", ()) or ())
        ]
        ordered_points = [point for point in ordered_points if point is not None]
        if len(ordered_points) < 2:
            diagnostic_rows.append(f"shared_boundary_edge_points_missing:{breakline_id or index}")
            continue
        from_node_ref = node_ref_for_point(ordered_points[0], role=role, source_ref=breakline_id)
        to_node_ref = node_ref_for_point(ordered_points[-1], role=role, source_ref=breakline_id)
        start_key = _intersection_shared_boundary_node_key(_row_xyz_tuple(ordered_points[0]))
        end_key = _intersection_shared_boundary_node_key(_row_xyz_tuple(ordered_points[-1]))
        duplicate_key = (role, tuple(sorted((start_key, end_key))))
        diagnostics = [str(value) for value in tuple(getattr(row, "diagnostic_rows", ()) or ()) if str(value)]
        previous_edge_id = duplicate_key_owner.get(duplicate_key)
        if previous_edge_id:
            duplicate_edge_count += 1
            diagnostics.append(f"shared_boundary_edge_duplicate_parallel:{previous_edge_id}")
            diagnostic_rows.append(f"shared_boundary_edge_duplicate_parallel:{breakline_id}:{previous_edge_id}")
        else:
            duplicate_key_owner[duplicate_key] = breakline_id
        consumers = tuple(_unique_text_values(str(value or "") for value in tuple(getattr(row, "consumer_refs", ()) or ())))
        for expected_consumer in INTERSECTION_SHARED_BOUNDARY_EXPECTED_CONSUMERS.get(role, ()):
            if expected_consumer not in consumers:
                missing_consumer_count += 1
                diagnostics.append(f"shared_boundary_edge_missing_consumer:{expected_consumer}")
                diagnostic_rows.append(f"shared_boundary_edge_missing_consumer:{breakline_id}:{expected_consumer}")
        edge_id = f"{result_id}:edge:{role}:{len(edge_rows) + 1}"
        edge_ref_by_breakline_ref[breakline_id] = edge_id
        edge_rows.append(
            IntersectionSharedBoundaryEdgeRow(
                edge_id=edge_id,
                intersection_id=target_intersection_id,
                edge_role=role,
                from_node_ref=from_node_ref,
                to_node_ref=to_node_ref,
                point_refs=tuple(str(value or "") for value in tuple(getattr(row, "point_refs", ()) or ()) if str(value or "")),
                consumer_refs=consumers,
                left_owner=str(getattr(row, "from_output_role", "") or ""),
                right_owner=str(getattr(row, "to_output_role", "") or ""),
                source_refs=tuple(str(value or "") for value in tuple(getattr(row, "source_contract_refs", ()) or ()) if str(value or "")),
                source_status=str(getattr(row, "source_status", "") or "candidate"),
                diagnostics=tuple(diagnostics),
                notes=f"Canonical graph edge converted from SharedBreakline row {breakline_id}.",
            )
        )

    cell_result = IntersectionSlopeFaceCellEvaluationService().evaluate(
        IntersectionSlopeFaceCellEvaluationRequest(
            shared_breakline_result=shared_breakline_result,
            intersection_id=target_intersection_id,
        )
    )
    seam_edge_ref_by_segment_key: dict[tuple[tuple[float, float, float], tuple[float, float, float]], str] = {}
    seam_sources_by_segment_key: dict[tuple[tuple[float, float, float], tuple[float, float, float]], list[str]] = {}
    for source_cell in list(getattr(cell_result, "cell_rows", []) or []):
        if str(getattr(source_cell, "status", "") or "") != "ready":
            continue
        role = str(getattr(source_cell, "cell_role", "") or "")
        if not role.startswith("upper_"):
            continue
        points = list(getattr(source_cell, "loop_points_xyz", ()) or ())
        if len(points) < 4:
            continue
        clean_points = [_xyz_tuple(point) for point in points]
        for first, second in zip(clean_points, clean_points[1:]):
            if _intersection_slope_face_points_close_xyz(first, second):
                continue
            segment_key = _intersection_shared_boundary_segment_key(first, second)
            seam_sources_by_segment_key.setdefault(segment_key, []).append(str(getattr(source_cell, "cell_id", "") or ""))
    existing_segment_keys = {
        _intersection_shared_boundary_segment_key(
            _row_xyz_tuple(ordered_points[0]),
            _row_xyz_tuple(ordered_points[-1]),
        )
        for row in list(getattr(shared_breakline_result, "breakline_rows", []) or [])
        for ordered_points in [[
            point_map.get(str(point_ref or ""))
            for point_ref in tuple(getattr(row, "point_refs", ()) or ())
            if point_map.get(str(point_ref or "")) is not None
        ]]
        if len(ordered_points) >= 2
    }
    for segment_index, (segment_key, source_cell_refs) in enumerate(sorted(seam_sources_by_segment_key.items()), start=1):
        if len(source_cell_refs) < 2 or segment_key in existing_segment_keys:
            continue
        start, end = segment_key
        edge_id = f"{result_id}:edge:upper_transition_internal_seam:{len(edge_rows) + 1}"
        seam_edge_ref_by_segment_key[segment_key] = edge_id
        edge_rows.append(
            IntersectionSharedBoundaryEdgeRow(
                edge_id=edge_id,
                intersection_id=target_intersection_id,
                edge_role="upper_transition_internal_seam",
                from_node_ref=node_ref_for_xyz(start, role="upper_transition_internal_seam", source_refs=tuple(source_cell_refs)),
                to_node_ref=node_ref_for_xyz(end, role="upper_transition_internal_seam", source_refs=tuple(source_cell_refs)),
                point_refs=(),
                consumer_refs=("intersection_slope_face_surface", "intersection_slope_face_cell_result"),
                left_owner="intersection_slope_face_cell",
                right_owner="intersection_slope_face_cell",
                source_refs=tuple(_unique_text_values(source_cell_refs)),
                source_status="accepted",
                notes=f"Canonical seam between upper transition subcells {segment_index}.",
            )
        )
    closure_edge_ref_by_segment_key: dict[tuple[tuple[float, float, float], tuple[float, float, float]], str] = {}
    for source_cell in list(getattr(cell_result, "cell_rows", []) or []):
        if str(getattr(source_cell, "status", "") or "") != "ready":
            continue
        cell_points = [_xyz_tuple(point) for point in tuple(getattr(source_cell, "loop_points_xyz", ()) or ())]
        if len(cell_points) < 4:
            continue
        source_cell_ref = str(getattr(source_cell, "cell_id", "") or "")
        for first, second in zip(cell_points, cell_points[1:]):
            if _intersection_slope_face_points_close_xyz(first, second):
                continue
            segment_key = _intersection_shared_boundary_segment_key(first, second)
            if segment_key in existing_segment_keys or segment_key in seam_edge_ref_by_segment_key:
                continue
            if segment_key in closure_edge_ref_by_segment_key:
                continue
            start, end = segment_key
            edge_id = f"{result_id}:edge:cell_closure_internal_seam:{len(edge_rows) + 1}"
            closure_edge_ref_by_segment_key[segment_key] = edge_id
            edge_rows.append(
                IntersectionSharedBoundaryEdgeRow(
                    edge_id=edge_id,
                    intersection_id=target_intersection_id,
                    edge_role="cell_closure_internal_seam",
                    from_node_ref=node_ref_for_xyz(start, role="cell_closure_internal_seam", source_refs=(source_cell_ref,)),
                    to_node_ref=node_ref_for_xyz(end, role="cell_closure_internal_seam", source_refs=(source_cell_ref,)),
                    point_refs=(),
                    consumer_refs=("intersection_slope_face_surface", "intersection_slope_face_cell_result"),
                    left_owner="intersection_slope_face_cell",
                    right_owner="intersection_slope_face_cell",
                    source_refs=(source_cell_ref,) if source_cell_ref else (),
                    source_status="accepted",
                    notes="Canonical internal seam closing an evaluated intersection slope-face cell loop.",
                )
            )
    for source_cell in list(getattr(cell_result, "cell_rows", []) or []):
        if str(getattr(source_cell, "status", "") or "") != "ready":
            continue
        boundary_breakline_refs = tuple(str(value or "") for value in tuple(getattr(source_cell, "boundary_breakline_refs", ()) or ()) if str(value or ""))
        boundary_edge_refs = list(edge_ref_by_breakline_ref[value] for value in boundary_breakline_refs if value in edge_ref_by_breakline_ref)
        cell_points = [_xyz_tuple(point) for point in tuple(getattr(source_cell, "loop_points_xyz", ()) or ())]
        for first, second in zip(cell_points, cell_points[1:]):
            seam_ref = seam_edge_ref_by_segment_key.get(_intersection_shared_boundary_segment_key(first, second))
            if seam_ref and seam_ref not in boundary_edge_refs:
                boundary_edge_refs.append(seam_ref)
            closure_ref = closure_edge_ref_by_segment_key.get(_intersection_shared_boundary_segment_key(first, second))
            if closure_ref and closure_ref not in boundary_edge_refs:
                boundary_edge_refs.append(closure_ref)
        missing_refs = tuple(value for value in boundary_breakline_refs if value not in edge_ref_by_breakline_ref)
        diagnostics = [str(value) for value in tuple(getattr(source_cell, "diagnostics", ()) or ()) if str(value)]
        if missing_refs:
            diagnostics.append("shared_boundary_cell_not_graph_closed")
            diagnostic_rows.append(f"shared_boundary_cell_not_graph_closed:{getattr(source_cell, 'cell_id', '')}:missing={','.join(missing_refs)}")
        closed = bool(getattr(source_cell, "closed_xy", False)) and not missing_refs
        if not closed and "shared_boundary_cell_not_graph_closed" not in diagnostics:
            diagnostics.append("shared_boundary_cell_not_graph_closed")
            diagnostic_rows.append(f"shared_boundary_cell_not_graph_closed:{getattr(source_cell, 'cell_id', '')}")
        cell_edge_consumers: list[str] = []
        for edge_ref in boundary_edge_refs:
            edge_row = next((edge for edge in edge_rows if str(getattr(edge, "edge_id", "") or "") == edge_ref), None)
            if edge_row is not None:
                cell_edge_consumers.extend(str(value or "") for value in tuple(getattr(edge_row, "consumer_refs", ()) or ()))
        adjacent_surface_refs = tuple(
            value
            for value in _unique_text_values(cell_edge_consumers)
            if value and value != "intersection_slope_face_surface" and value != "intersection_slope_face_cell_result"
        )
        warning_diagnostics = _intersection_shared_boundary_graph_warning_diagnostics(diagnostics)
        status = "ready" if closed and not warning_diagnostics else "warning"
        cell_rows.append(
            IntersectionSharedBoundaryCellRow(
                cell_id=str(getattr(source_cell, "cell_id", "") or f"{result_id}:cell:{len(cell_rows) + 1}"),
                intersection_id=target_intersection_id,
                cell_role=str(getattr(source_cell, "cell_role", "") or "intersection_slope_face_cell"),
                boundary_edge_refs=tuple(boundary_edge_refs),
                loop_points_xyz=tuple(_xyz_tuple(point) for point in tuple(getattr(source_cell, "loop_points_xyz", ()) or ())),
                owner_surface_ref=str(getattr(source_cell, "consumer_surface_ref", "") or "intersection_slope_face_surface"),
                adjacent_surface_refs=adjacent_surface_refs,
                source_refs=tuple(str(value or "") for value in tuple(getattr(source_cell, "source_shared_breakline_refs", ()) or ()) if str(value or "")),
                closed=closed,
                self_crossing=bool(getattr(source_cell, "self_crossing", False)),
                status=status,
                diagnostics=tuple(diagnostics),
                notes="Graph cell derived from IntersectionSlopeFaceCellResult boundary refs.",
            )
        )

    warning_count = sum(
        1
        for row in list(edge_rows) + list(cell_rows)
        if _intersection_shared_boundary_graph_warning_diagnostics(tuple(getattr(row, "diagnostics", ()) or ()))
        or str(getattr(row, "status", "") or "") == "warning"
    )
    error_count = sum(1 for row in list(edge_rows) + list(cell_rows) if str(getattr(row, "status", "") or "") == "error")
    graph_open_cell_count = sum(1 for row in cell_rows if not bool(getattr(row, "closed", False)))
    provisional_graph = IntersectionSharedBoundaryGraphResult(
        schema_version=1,
        project_id=project_id,
        graph_result_id=result_id,
        intersection_id=target_intersection_id,
        node_rows=node_rows,
        edge_rows=edge_rows,
        cell_rows=cell_rows,
    )
    graph_audit = intersection_shared_boundary_graph_audit(provisional_graph)
    audit_endpoint_mismatch_count = int(graph_audit.get("endpoint_mismatch_count", 0) or 0)
    audit_not_snapped_count = int(graph_audit.get("not_snapped_count", 0) or 0)
    duplicate_edge_count = max(duplicate_edge_count, int(graph_audit.get("duplicate_edge_count", 0) or 0))
    missing_consumer_count = max(missing_consumer_count, int(graph_audit.get("missing_consumer_count", 0) or 0))
    graph_open_cell_count = max(graph_open_cell_count, int(graph_audit.get("graph_open_cell_count", 0) or 0))
    if audit_endpoint_mismatch_count or audit_not_snapped_count:
        warning_count += audit_endpoint_mismatch_count + audit_not_snapped_count
    diagnostic_rows.extend(str(value or "") for value in list(graph_audit.get("diagnostic_rows", []) or []) if str(value or ""))
    if not edge_rows:
        status = "missing"
    elif error_count:
        status = "error"
    elif warning_count or diagnostic_rows:
        status = "warning"
    else:
        status = "ready"
    return IntersectionSharedBoundaryGraphResult(
        schema_version=1,
        project_id=project_id,
        graph_result_id=result_id,
        intersection_id=target_intersection_id,
        status=status,
        node_count=len(node_rows),
        edge_count=len(edge_rows),
        cell_count=len(cell_rows),
        ready_edge_count=sum(1 for row in edge_rows if not tuple(getattr(row, "diagnostics", ()) or ())),
        ready_cell_count=sum(1 for row in cell_rows if str(getattr(row, "status", "") or "") == "ready"),
        warning_count=warning_count,
        error_count=error_count,
        duplicate_edge_count=duplicate_edge_count,
        missing_consumer_count=missing_consumer_count,
        not_snapped_count=audit_endpoint_mismatch_count + audit_not_snapped_count,
        graph_open_cell_count=graph_open_cell_count,
        diagnostic_rows=_unique_text_values(diagnostic_rows),
        node_rows=node_rows,
        edge_rows=edge_rows,
        cell_rows=cell_rows,
    )


def _xyz_tuple(point) -> tuple[float, float, float]:
    values = tuple(point or ())
    if len(values) < 3:
        values = values + (0.0,) * (3 - len(values))
    return (float(values[0]), float(values[1]), float(values[2]))


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


def intersection_shared_boundary_graph_audit(graph_result: IntersectionSharedBoundaryGraphResult | None) -> dict[str, object]:
    """Audit canonical graph topology before surface consumers trust it."""

    if graph_result is None:
        return {
            "status": "missing",
            "endpoint_mismatch_count": 0,
            "not_snapped_count": 0,
            "duplicate_edge_count": 0,
            "missing_consumer_count": 0,
            "source_segment_split_count": 0,
            "graph_open_cell_count": 0,
            "diagnostic_rows": ["intersection_shared_boundary_graph_missing"],
        }
    node_rows = list(getattr(graph_result, "node_rows", []) or [])
    edge_rows = list(getattr(graph_result, "edge_rows", []) or [])
    cell_rows = list(getattr(graph_result, "cell_rows", []) or [])
    node_by_id = {
        str(getattr(node, "node_id", "") or ""): node
        for node in node_rows
        if str(getattr(node, "node_id", "") or "")
    }
    diagnostic_rows: list[str] = []
    not_snapped_count = 0
    endpoint_mismatch_count = 0
    duplicate_edge_count = 0
    missing_consumer_count = 0
    source_segment_split_count = 0
    graph_open_cell_count = 0

    node_owner_by_key: dict[tuple[float, float, float], str] = {}
    for node in node_rows:
        node_id = str(getattr(node, "node_id", "") or "")
        if not node_id:
            continue
        key = _intersection_shared_boundary_node_key((float(getattr(node, "x", 0.0) or 0.0), float(getattr(node, "y", 0.0) or 0.0), float(getattr(node, "z", 0.0) or 0.0)))
        previous = node_owner_by_key.get(key)
        if previous and previous != node_id:
            not_snapped_count += 1
            diagnostic_rows.append(f"shared_boundary_consumer_not_snapped:duplicate-node:{node_id}:{previous}")
        else:
            node_owner_by_key[key] = node_id

    edge_owner_by_key: dict[tuple[str, tuple[tuple[float, float, float], tuple[float, float, float]]], str] = {}
    for edge in edge_rows:
        edge_id = str(getattr(edge, "edge_id", "") or "")
        edge_role = str(getattr(edge, "edge_role", "") or "")
        from_ref = str(getattr(edge, "from_node_ref", "") or "")
        to_ref = str(getattr(edge, "to_node_ref", "") or "")
        from_node = node_by_id.get(from_ref)
        to_node = node_by_id.get(to_ref)
        if from_node is None:
            endpoint_mismatch_count += 1
            diagnostic_rows.append(f"shared_boundary_edge_endpoint_mismatch:{edge_id}:{from_ref}")
        if to_node is None:
            endpoint_mismatch_count += 1
            diagnostic_rows.append(f"shared_boundary_edge_endpoint_mismatch:{edge_id}:{to_ref}")
        consumers = {str(value or "") for value in tuple(getattr(edge, "consumer_refs", ()) or ()) if str(value or "")}
        for expected_consumer in INTERSECTION_SHARED_BOUNDARY_EXPECTED_CONSUMERS.get(edge_role, ()):
            if expected_consumer not in consumers:
                missing_consumer_count += 1
                diagnostic_rows.append(f"shared_boundary_edge_missing_consumer:{edge_id}:{expected_consumer}")
        if from_node is None or to_node is None:
            continue
        from_key = _intersection_shared_boundary_node_key((float(getattr(from_node, "x", 0.0) or 0.0), float(getattr(from_node, "y", 0.0) or 0.0), float(getattr(from_node, "z", 0.0) or 0.0)))
        to_key = _intersection_shared_boundary_node_key((float(getattr(to_node, "x", 0.0) or 0.0), float(getattr(to_node, "y", 0.0) or 0.0), float(getattr(to_node, "z", 0.0) or 0.0)))
        duplicate_key = (edge_role, tuple(sorted((from_key, to_key))))
        previous_edge = edge_owner_by_key.get(duplicate_key)
        if previous_edge and previous_edge != edge_id:
            duplicate_edge_count += 1
            diagnostic_rows.append(f"shared_boundary_edge_duplicate_parallel:{edge_id}:{previous_edge}")
        else:
            edge_owner_by_key[duplicate_key] = edge_id

    edges_by_boundary_segment_ref: dict[str, list[object]] = {}
    for edge in edge_rows:
        for segment_ref in _intersection_authoritative_boundary_loop_segment_source_refs(
            tuple(getattr(edge, "source_refs", ()) or ())
        ):
            edges_by_boundary_segment_ref.setdefault(segment_ref, []).append(edge)
    for segment_ref, segment_edges in sorted(edges_by_boundary_segment_ref.items()):
        edge_ids = _unique_text_values(
            str(getattr(edge, "edge_id", "") or "")
            for edge in segment_edges
            if str(getattr(edge, "edge_id", "") or "")
        )
        if len(edge_ids) <= 1:
            continue
        source_segment_split_count += 1
        consumers = _unique_text_values(
            consumer_ref
            for edge in segment_edges
            for consumer_ref in tuple(getattr(edge, "consumer_refs", ()) or ())
            if str(consumer_ref or "")
        )
        diagnostic_rows.append(
            "shared_boundary_source_segment_split:"
            f"{segment_ref}:edges={','.join(edge_ids)}:consumers={','.join(consumers)}"
        )

    edge_by_id = {str(getattr(edge, "edge_id", "") or ""): edge for edge in edge_rows}
    for cell in cell_rows:
        cell_id = str(getattr(cell, "cell_id", "") or "")
        boundary_edge_refs = [
            str(edge_ref or "")
            for edge_ref in tuple(getattr(cell, "boundary_edge_refs", ()) or ())
            if str(edge_ref or "")
        ]
        missing_refs = [
            str(edge_ref or "")
            for edge_ref in boundary_edge_refs
            if str(edge_ref or "") not in edge_by_id
        ]
        node_degree: dict[str, int] = {}
        strict_graph_closed_check = len(boundary_edge_refs) >= 4
        for edge_ref in boundary_edge_refs:
            edge = edge_by_id.get(edge_ref)
            if edge is None:
                continue
            if len(tuple(getattr(edge, "point_refs", ()) or ())) > 2:
                strict_graph_closed_check = False
            from_ref = str(getattr(edge, "from_node_ref", "") or "")
            to_ref = str(getattr(edge, "to_node_ref", "") or "")
            if from_ref:
                node_degree[from_ref] = int(node_degree.get(from_ref, 0) or 0) + 1
            if to_ref:
                node_degree[to_ref] = int(node_degree.get(to_ref, 0) or 0) + 1
        dangling_nodes = sorted(node_ref for node_ref, degree in node_degree.items() if int(degree or 0) != 2)
        graph_closed = (
            len(boundary_edge_refs) >= 3
            and not missing_refs
            and bool(getattr(cell, "closed", False))
            and (
                not strict_graph_closed_check
                or (bool(node_degree) and not dangling_nodes)
            )
        )
        if not graph_closed:
            graph_open_cell_count += 1
            diagnostic_rows.append(f"shared_boundary_cell_not_graph_closed:{cell_id}")
        for edge_ref in missing_refs:
            diagnostic_rows.append(f"shared_boundary_cell_not_graph_closed:{cell_id}:missing-edge:{edge_ref}")
        if strict_graph_closed_check:
            for node_ref in dangling_nodes:
                diagnostic_rows.append(
                    f"shared_boundary_cell_not_graph_closed:{cell_id}:node_degree:{node_ref}:{node_degree.get(node_ref, 0)}"
                )

    status = "ready"
    if not edge_rows:
        status = "missing"
    elif (
        endpoint_mismatch_count
        or not_snapped_count
        or duplicate_edge_count
        or missing_consumer_count
        or source_segment_split_count
        or graph_open_cell_count
    ):
        status = "warning"
    return {
        "status": status,
        "endpoint_mismatch_count": endpoint_mismatch_count,
        "not_snapped_count": not_snapped_count,
        "duplicate_edge_count": duplicate_edge_count,
        "missing_consumer_count": missing_consumer_count,
        "source_segment_split_count": source_segment_split_count,
        "graph_open_cell_count": graph_open_cell_count,
        "diagnostic_rows": _unique_text_values(diagnostic_rows),
    }


def _intersection_shared_boundary_graph_warning_diagnostics(diagnostics) -> tuple[str, ...]:
    informational_prefixes: tuple[str, ...] = ()
    output: list[str] = []
    for diagnostic in tuple(diagnostics or ()):
        text = str(diagnostic or "")
        if not text:
            continue
        if any(text.startswith(prefix) for prefix in informational_prefixes):
            continue
        output.append(text)
    return tuple(output)


def _intersection_shared_boundary_node_key(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return (round(float(point[0]), 6), round(float(point[1]), 6), round(float(point[2]), 6))


def _intersection_shared_boundary_segment_key(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    first_key = _intersection_shared_boundary_node_key(first)
    second_key = _intersection_shared_boundary_node_key(second)
    return tuple(sorted((first_key, second_key)))


def _intersection_shared_boundary_node_role(edge_role: str) -> str:
    role = str(edge_role or "")
    if "curb_return" in role:
        return "curb_return_arc_point"
    if "main_side" in role:
        return "main_side_contact_point"
    if "design_surface" in role:
        return "design_tie_point"
    if "corridor_slope_face" in role:
        return "corridor_slope_tie_point"
    return "patch_corner"


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


def _row_xyz_tuple(row) -> tuple[float, float, float]:
    return (
        float(getattr(row, "x", 0.0) or 0.0),
        float(getattr(row, "y", 0.0) or 0.0),
        float(getattr(row, "z", 0.0) or 0.0),
    )


__all__ = [
    "IntersectionSharedBoundaryGraphEvaluationRequest",
    "IntersectionSharedBoundaryGraphEvaluationService",
    "intersection_shared_boundary_graph_audit",
]
