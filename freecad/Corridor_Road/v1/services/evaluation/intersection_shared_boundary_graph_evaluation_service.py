"""Build the canonical Intersection shared-boundary graph from result contracts."""

from __future__ import annotations


from ...models.result.intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryGraphResult,
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


def _intersection_shared_boundary_node_key(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return (round(float(point[0]), 6), round(float(point[1]), 6), round(float(point[2]), 6))


__all__ = [
    "intersection_shared_boundary_graph_audit",
]
