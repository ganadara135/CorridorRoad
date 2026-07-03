from freecad.Corridor_Road.v1.models.result.intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryCellRow,
    IntersectionSharedBoundaryEdgeRow,
    IntersectionSharedBoundaryGraphResult,
    IntersectionSharedBoundaryNodeRow,
)


def test_intersection_shared_boundary_graph_records_canonical_closed_cell():
    nodes = [
        IntersectionSharedBoundaryNodeRow("node:a", "intersection:t", "patch_corner", 0.0, 0.0, 0.0),
        IntersectionSharedBoundaryNodeRow("node:b", "intersection:t", "upper_split_point", 1.0, 0.0, 0.0),
        IntersectionSharedBoundaryNodeRow("node:c", "intersection:t", "corridor_slope_tie_point", 1.0, 1.0, 0.0),
        IntersectionSharedBoundaryNodeRow("node:d", "intersection:t", "design_tie_point", 0.0, 1.0, 0.0),
    ]
    edges = [
        IntersectionSharedBoundaryEdgeRow(
            "edge:patch",
            "intersection:t",
            "patch_to_intersection_slope_face",
            "node:a",
            "node:b",
            consumer_refs=("intersection_surface", "intersection_slope_face_surface"),
        ),
        IntersectionSharedBoundaryEdgeRow(
            "edge:outer",
            "intersection:t",
            "intersection_slope_face_to_corridor_slope_face",
            "node:b",
            "node:c",
            consumer_refs=("intersection_slope_face_surface", "slope_face_surface"),
        ),
        IntersectionSharedBoundaryEdgeRow(
            "edge:design",
            "intersection:t",
            "intersection_slope_face_to_design_surface",
            "node:c",
            "node:d",
            consumer_refs=("intersection_slope_face_surface", "design_surface"),
        ),
        IntersectionSharedBoundaryEdgeRow(
            "edge:close",
            "intersection:t",
            "upper_transition_internal_seam",
            "node:d",
            "node:a",
            consumer_refs=("intersection_slope_face_surface",),
        ),
    ]
    cell = IntersectionSharedBoundaryCellRow(
        "cell:upper-left",
        "intersection:t",
        "upper_left_transition_cell",
        boundary_edge_refs=("edge:patch", "edge:outer", "edge:design", "edge:close"),
        owner_surface_ref="intersection_slope_face_surface",
        adjacent_surface_refs=("intersection_surface", "slope_face_surface", "design_surface"),
        closed=True,
        status="ready",
    )

    result = IntersectionSharedBoundaryGraphResult(
        schema_version=1,
        project_id="project:test",
        graph_result_id="intersection-shared-boundary-graph:test",
        intersection_id="intersection:t",
        status="ready",
        node_count=len(nodes),
        edge_count=len(edges),
        cell_count=1,
        ready_edge_count=len(edges),
        ready_cell_count=1,
        node_rows=nodes,
        edge_rows=edges,
        cell_rows=[cell],
    )

    assert result.status == "ready"
    assert result.cell_rows[0].closed is True
    assert result.edge_rows[0].consumer_refs == ("intersection_surface", "intersection_slope_face_surface")
    assert "edge:outer" in result.cell_rows[0].boundary_edge_refs


def test_intersection_shared_boundary_graph_reports_missing_consumer_and_open_cell():
    edge = IntersectionSharedBoundaryEdgeRow(
        "edge:missing-consumer",
        "intersection:t",
        "intersection_slope_face_to_corridor_slope_face",
        "node:a",
        "node:b",
        consumer_refs=("intersection_slope_face_surface",),
        diagnostics=("shared_boundary_edge_missing_consumer:slope_face_surface",),
    )
    cell = IntersectionSharedBoundaryCellRow(
        "cell:open",
        "intersection:t",
        "upper_mid_transition_cell",
        boundary_edge_refs=("edge:missing-consumer",),
        owner_surface_ref="intersection_slope_face_surface",
        closed=False,
        status="warning",
        diagnostics=("shared_boundary_cell_not_graph_closed",),
    )

    result = IntersectionSharedBoundaryGraphResult(
        schema_version=1,
        project_id="project:test",
        graph_result_id="intersection-shared-boundary-graph:test",
        intersection_id="intersection:t",
        status="warning",
        edge_count=1,
        cell_count=1,
        warning_count=2,
        missing_consumer_count=1,
        graph_open_cell_count=1,
        diagnostic_rows=[
            "shared_boundary_edge_missing_consumer:slope_face_surface",
            "shared_boundary_cell_not_graph_closed",
        ],
        edge_rows=[edge],
        cell_rows=[cell],
    )

    assert result.missing_consumer_count == 1
    assert result.graph_open_cell_count == 1
    assert "shared_boundary_cell_not_graph_closed" in result.cell_rows[0].diagnostics

