"""Contract tests for intersection shared-boundary graph builder."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result.shared_breakline import (
    SharedBreaklinePointRow,
    SharedBreaklineResult,
    SharedBreaklineRow,
)
from freecad.Corridor_Road.v1.models.result.intersection_boundary_loop import (
    IntersectionBoundaryLoopResult,
    IntersectionBoundaryLoopRow,
    IntersectionBoundarySegmentRow,
)
from freecad.Corridor_Road.v1.models.result.intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryCellRow,
    IntersectionSharedBoundaryEdgeRow,
    IntersectionSharedBoundaryGraphResult,
    IntersectionSharedBoundaryNodeRow,
)


def _point(point_id: str, breakline_ref: str, sequence: int, x: float, y: float, z: float = 0.0):
    return SharedBreaklinePointRow(
        point_id=point_id,
        breakline_ref=breakline_ref,
        sequence=sequence,
        x=x,
        y=y,
        z=z,
    )


def _breakline(
    breakline_id: str,
    role: str,
    point_refs: tuple[str, ...],
    consumers: tuple[str, ...],
):
    return SharedBreaklineRow(
        breakline_id=breakline_id,
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        breakline_role=role,
        consumer_refs=consumers,
        from_output_role=consumers[0] if consumers else "",
        to_output_role=consumers[1] if len(consumers) > 1 else "",
        point_refs=point_refs,
        source_contract_refs=("source:test",),
        source_status="accepted",
    )


def _upper_cell_breakline_result() -> SharedBreaklineResult:
    breakline_ids = (
        "shared:patch-to-intersection-slope-face:1",
        "shared:intersection-slope-face-to-design-surface:1",
        "shared:intersection-slope-face-to-corridor-slope-face:1",
    )
    points = [
        _point("p1", breakline_ids[0], 1, 0.0, 0.0),
        _point("p2", breakline_ids[0], 2, 2.0, 0.0),
        _point("p3", breakline_ids[1], 1, 2.0, 0.0),
        _point("p4", breakline_ids[1], 2, 2.0, 1.0),
        _point("p5", breakline_ids[2], 1, 0.0, 1.0),
        _point("p6", breakline_ids[2], 2, 2.0, 1.0),
    ]
    rows = [
        _breakline(
            breakline_ids[0],
            "patch_to_intersection_slope_face",
            ("p1", "p2"),
            ("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
        ),
        _breakline(
            breakline_ids[1],
            "intersection_slope_face_to_design_surface",
            ("p3", "p4"),
            ("intersection_slope_face_surface", "design_surface", "intersection_slope_face_cell_result"),
        ),
        _breakline(
            breakline_ids[2],
            "intersection_slope_face_to_corridor_slope_face",
            ("p6", "p5"),
            ("intersection_slope_face_surface", "slope_face_surface", "intersection_slope_face_cell_result"),
        ),
    ]
    return SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="ready",
        breakline_count=len(rows),
        ready_count=len(rows),
        breakline_rows=rows,
        point_rows=points,
    )


def test_intersection_shared_boundary_graph_preserves_curb_return_bridge_candidate():
    bridge_id = "shared:curb-return-bridge-to-intersection-slope-face:1"
    shared = SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="warning",
        breakline_count=1,
        warning_count=1,
        breakline_rows=[
            _breakline(
                bridge_id,
                "curb_return_bridge_to_intersection_slope_face",
                ("bridge:p1", "bridge:p2"),
                ("intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            )
        ],
        point_rows=[
            _point("bridge:p1", bridge_id, 1, -12.0, 4.5),
            _point("bridge:p2", bridge_id, 2, -12.0, 9.0),
        ],
    )

    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        shared,
        intersection_id="starter-t_intersection",
    )

    bridge_edges = [
        row
        for row in graph.edge_rows
        if row.edge_role == "curb_return_bridge_to_intersection_slope_face"
    ]
    assert len(bridge_edges) == 1
    assert bridge_edges[0].consumer_refs == (
        "intersection_slope_face_surface",
        "intersection_slope_face_cell_result",
    )
    assert bridge_edges[0].left_owner == "intersection_slope_face_surface"
    assert bridge_edges[0].right_owner == "intersection_slope_face_cell_result"


def test_intersection_curb_return_bridge_diagnostics_create_shared_breaklines():
    boundary_loops = IntersectionBoundaryLoopResult(
        schema_version=1,
        project_id="project:test",
        boundary_loop_result_id="intersection-boundary-loops:starter-t",
        intersection_id="starter-t_intersection",
        status="warning",
        diagnostic_rows=[
            "warning:intersection_boundary_curb_arc_bridge_required:"
            "intersection-edge:starter-t:curb-return:01:"
            "missing_segments=1;candidate_segments=2;sample=-12.000:4.500->-12.000:9.000"
        ],
    )
    shared_rows = []
    point_rows = []
    diagnostics = []

    cmd_build_corridor._append_intersection_curb_return_bridge_breaklines(
        result_id="shared-breakline:intersection:starter-t_intersection",
        intersection_id="starter-t_intersection",
        boundary_loop_result=boundary_loops,
        breakline_rows=shared_rows,
        point_rows=point_rows,
        diagnostics=diagnostics,
    )

    assert len(shared_rows) == 1
    assert shared_rows[0].breakline_role == "curb_return_bridge_to_intersection_slope_face"
    assert shared_rows[0].consumer_refs == (
        "intersection_slope_face_surface",
        "intersection_slope_face_cell_result",
    )
    assert shared_rows[0].source_status == "diagnostic"
    assert len(point_rows) == 2
    assert (point_rows[0].x, point_rows[0].y, point_rows[1].x, point_rows[1].y) == (-12.0, 4.5, -12.0, 9.0)
    assert diagnostics == ["intersection_curb_return_bridge_shared_breaklines:1"]


def test_intersection_slope_face_cell_result_consumes_curb_return_bridge_candidate():
    curb_id = "shared:curb-return-to-intersection-slope-face:1"
    bridge_id = "shared:curb-return-bridge-to-intersection-slope-face:1"
    shared = SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="ready",
        breakline_count=2,
        ready_count=2,
        breakline_rows=[
            _breakline(
                curb_id,
                "curb_return_to_intersection_slope_face",
                ("curb:p1", "curb:p2"),
                ("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            ),
            _breakline(
                bridge_id,
                "curb_return_bridge_to_intersection_slope_face",
                ("bridge:p1", "bridge:p2"),
                ("intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            ),
        ],
        point_rows=[
            _point("curb:p1", curb_id, 1, -12.0, 4.5),
            _point("curb:p2", curb_id, 2, -10.0, 4.5),
            _point("bridge:p1", bridge_id, 1, -12.0, 4.5),
            _point("bridge:p2", bridge_id, 2, -12.0, 9.0),
        ],
    )

    cells = cmd_build_corridor.corridor_intersection_slope_face_cell_result(
        shared,
        intersection_id="starter-t_intersection",
    )

    bridge_cells = [row for row in cells.cell_rows if row.cell_role == "curb_return_bridge_cell"]
    assert len(bridge_cells) == 1
    assert bridge_cells[0].status == "ready"
    assert bridge_cells[0].inner_breakline_ref == curb_id
    assert bridge_cells[0].arc_breakline_ref == bridge_id
    assert bridge_id in bridge_cells[0].boundary_breakline_refs


def test_intersection_slope_face_cell_result_prefers_curb_bridge_shared_endpoint():
    shared_curb_id = "shared:curb-return-to-intersection-slope-face:shared"
    near_curb_id = "shared:curb-return-to-intersection-slope-face:near"
    bridge_id = "shared:curb-return-bridge-to-intersection-slope-face:1"
    shared = SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="ready",
        breakline_count=3,
        ready_count=3,
        breakline_rows=[
            _breakline(
                near_curb_id,
                "curb_return_to_intersection_slope_face",
                ("near:p1", "near:p2"),
                ("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            ),
            _breakline(
                shared_curb_id,
                "curb_return_to_intersection_slope_face",
                ("shared:p1", "shared:p2"),
                ("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            ),
            _breakline(
                bridge_id,
                "curb_return_bridge_to_intersection_slope_face",
                ("bridge:p1", "bridge:p2"),
                ("intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            ),
        ],
        point_rows=[
            _point("near:p1", near_curb_id, 1, -12.0, 4.6),
            _point("near:p2", near_curb_id, 2, -10.0, 4.6),
            _point("shared:p1", shared_curb_id, 1, -12.0, 4.5),
            _point("shared:p2", shared_curb_id, 2, -10.0, 4.5),
            _point("bridge:p1", bridge_id, 1, -12.0, 4.5),
            _point("bridge:p2", bridge_id, 2, -12.0, 9.0),
        ],
    )

    cells = cmd_build_corridor.corridor_intersection_slope_face_cell_result(
        shared,
        intersection_id="starter-t_intersection",
    )

    bridge_cells = [row for row in cells.cell_rows if row.cell_role == "curb_return_bridge_cell"]
    assert len(bridge_cells) == 1
    assert bridge_cells[0].inner_breakline_ref == shared_curb_id


def test_intersection_slope_face_cell_result_rejects_full_control_area_caps_as_cells():
    entry_id = "shared:control-area-entry:slope"
    exit_id = "shared:control-area-exit:slope"
    shared = SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="ready",
        breakline_count=2,
        ready_count=2,
        breakline_rows=[
            SharedBreaklineRow(
                entry_id,
                "intersection_control_area",
                "control-area:main",
                "control_area_entry",
                consumer_refs=("intersection_surface", "slope_face_surface"),
                from_output_role="intersection_surface",
                to_output_role="slope_face_surface",
                point_refs=("entry:p1", "entry:p2"),
                alignment_ref="alignment:main",
                material_role="slope_face_surface",
                source_contract_refs=("section:entry", "control-area:main"),
                source_status="ready",
            ),
            SharedBreaklineRow(
                exit_id,
                "intersection_control_area",
                "control-area:main",
                "control_area_exit",
                consumer_refs=("intersection_surface", "slope_face_surface"),
                from_output_role="intersection_surface",
                to_output_role="slope_face_surface",
                point_refs=("exit:p1", "exit:p2"),
                alignment_ref="alignment:main",
                material_role="slope_face_surface",
                source_contract_refs=("section:exit", "control-area:main"),
                source_status="ready",
            ),
        ],
        point_rows=[
            _point("entry:p1", entry_id, 0, 0.0, -5.0),
            _point("entry:p2", entry_id, 1, 0.0, 5.0),
            _point("exit:p1", exit_id, 0, 10.0, -5.0),
            _point("exit:p2", exit_id, 1, 10.0, 5.0),
        ],
    )

    cells = cmd_build_corridor.corridor_intersection_slope_face_cell_result(
        shared,
        intersection_id="starter-t_intersection",
    )

    assert cells.cell_rows == []
    assert not any("control_area_transition" in row for row in cells.diagnostic_rows)


def test_intersection_slope_face_local_clip_caps_are_emitted_from_boundary_row():
    calls = []

    def add_breakline(**kwargs):
        calls.append(kwargs)

    row = SimpleNamespace(
        boundary_id="boundary:main-left",
        alignment_ref="alignment:main",
        side="left",
        status="ready",
        diagnostics=(),
    )
    slope_boundary_result = SimpleNamespace(boundary_result_id="intersection-slope-face-boundaries:test")

    cmd_build_corridor._append_intersection_slope_face_local_clip_cap_breaklines(
        add_breakline=add_breakline,
        row=row,
        row_index=7,
        inner_points=((0.0, 0.0, 0.0), (2.0, 0.0, 0.0)),
        outer_points=((0.0, 1.0, 0.0), (2.0, 1.0, 0.0)),
        slope_boundary_result=slope_boundary_result,
    )

    assert [call["role"] for call in calls] == ["control_area_entry", "control_area_exit"]
    assert calls[0]["base_id"] == "7:local-clip-start"
    assert calls[1]["base_id"] == "7:local-clip-end"
    assert calls[0]["points"] == ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    assert calls[1]["points"] == ((2.0, 0.0, 0.0), (2.0, 1.0, 0.0))
    assert calls[0]["material_role"] == "slope_face_surface"
    assert "intersection_slope_face_cell_result" in calls[0]["consumer_refs"]
    assert "local_clip cap" in calls[0]["notes"]


def _split_upper_cell_breakline_result() -> SharedBreaklineResult:
    breakline_ids = (
        "shared:patch-to-intersection-slope-face:split",
        "shared:intersection-slope-face-to-design-surface:split",
        "shared:intersection-slope-face-to-corridor-slope-face:split",
    )
    points = []
    for index, x in enumerate((0.0, 1.0, 2.0, 3.0), start=1):
        points.append(_point(f"pi{index}", breakline_ids[0], index, x, 0.0))
        points.append(_point(f"pd{index}", breakline_ids[1], index, x, 0.25))
        points.append(_point(f"po{index}", breakline_ids[2], index, x, 1.0))
    rows = [
        _breakline(
            breakline_ids[0],
            "patch_to_intersection_slope_face",
            tuple(f"pi{index}" for index in range(1, 5)),
            ("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
        ),
        _breakline(
            breakline_ids[1],
            "intersection_slope_face_to_design_surface",
            tuple(f"pd{index}" for index in range(1, 5)),
            ("intersection_slope_face_surface", "design_surface", "intersection_slope_face_cell_result"),
        ),
        _breakline(
            breakline_ids[2],
            "intersection_slope_face_to_corridor_slope_face",
            tuple(f"po{index}" for index in range(1, 5)),
            ("intersection_slope_face_surface", "slope_face_surface", "intersection_slope_face_cell_result"),
        ),
    ]
    return SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="ready",
        breakline_count=len(rows),
        ready_count=len(rows),
        breakline_rows=rows,
        point_rows=points,
    )


def test_intersection_shared_boundary_graph_builder_creates_canonical_edges_and_cells():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )

    assert graph.status == "ready"
    assert graph.node_count == 4
    assert graph.edge_count == 4
    assert graph.cell_count == 1
    assert graph.ready_cell_count == 1
    assert graph.duplicate_edge_count == 0
    assert graph.missing_consumer_count == 0

    roles = {row.edge_role for row in graph.edge_rows}
    assert roles == {
        "patch_to_intersection_slope_face",
        "intersection_slope_face_to_design_surface",
        "intersection_slope_face_to_corridor_slope_face",
        "cell_closure_internal_seam",
    }
    assert set(graph.cell_rows[0].boundary_edge_refs) == {row.edge_id for row in graph.edge_rows}


def test_intersection_shared_boundary_graph_builder_promotes_upper_internal_seams():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )

    seam_edges = [row for row in graph.edge_rows if row.edge_role == "upper_transition_internal_seam"]
    assert graph.status == "ready"
    assert graph.cell_count == 3
    assert len(seam_edges) == 4
    for cell in graph.cell_rows:
        assert cell.closed
        assert any(edge_ref in cell.boundary_edge_refs for edge_ref in {row.edge_id for row in seam_edges})


def test_intersection_slope_face_surface_can_generate_upper_cells_from_graph():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )
    vertices = []
    triangles = []

    stats = cmd_build_corridor._append_intersection_slope_face_graph_cell_tin(
        surface_id="surface:test",
        graph_result=graph,
        vertices=vertices,
        triangles=triangles,
    )

    assert stats["generation_mode"] == "no_ready_graph_cell"
    assert stats["cell_count"] == 0
    assert stats["triangle_count"] == 0
    assert vertices == []
    assert triangles == []
    assert all("graph_upper_cell_metadata_only" in diagnostic for diagnostic in stats["diagnostics"])


def test_intersection_shared_boundary_graph_metadata_filters_edges_by_consumer():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )

    design_refs = cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
        graph,
        "design_surface",
    )
    intersection_refs = cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
        graph,
        "intersection_surface",
    )
    slope_refs = cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
        graph,
        "slope_face_surface",
    )
    dedicated_refs = cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
        graph,
        "intersection_slope_face_surface",
    )

    assert len(design_refs) == 1
    assert len(intersection_refs) == 1
    assert len(slope_refs) == 1
    assert len(dedicated_refs) == graph.edge_count
    assert design_refs[0] in dedicated_refs
    assert intersection_refs[0] in dedicated_refs
    assert slope_refs[0] in dedicated_refs


def test_intersection_shared_boundary_graph_pair_audit_checks_adjacent_consumers():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )
    audit_rows = cmd_build_corridor._intersection_shared_boundary_graph_audit_rows(graph)
    rows = []
    for role, consumer in (
        ("design", "design_surface"),
        ("intersection", "intersection_surface"),
        ("daylight", "slope_face_surface"),
        ("intersection_slope", "intersection_slope_face_surface"),
    ):
        rows.append(
            {
                "role": role,
                "status": "ready",
                "graph_refs": cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(graph, consumer),
                "graph_audit_rows": audit_rows,
                "graph_status": graph.status,
                "graph_node_count": graph.node_count,
                "graph_edge_count": graph.edge_count,
                "graph_cell_count": graph.cell_count,
                "graph_consumed_edge_count": len(cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(graph, consumer)),
                "notes": "",
                "recommended_action": "No action needed",
            }
        )

    audited = cmd_build_corridor._shared_boundary_graph_pair_audit_rows(rows)
    assert sum(int(row.get("graph_pair_missing_count", 0) or 0) for row in audited) == 0
    assert sum(int(row.get("graph_pair_match_count", 0) or 0) for row in audited) >= 3

    broken_rows = [dict(row) for row in rows]
    for row in broken_rows:
        if row["role"] == "daylight":
            row["graph_refs"] = []
    broken = cmd_build_corridor._shared_boundary_graph_pair_audit_rows(broken_rows)
    daylight = next(row for row in broken if row["role"] == "daylight")
    assert daylight["status"] == "warning"
    assert daylight["graph_pair_missing_count"] == 1
    assert "pair_missing:intersection_slope_face_to_corridor_slope_face" in daylight["graph_pair_notes"]

    display_rows = cmd_build_corridor.shared_breakline_audit_display_rows(broken, include_internal=True)
    pair_rows = [row for row in display_rows if row.get("row_kind") == "graph_pair"]
    assert any(
        "intersection_slope_face_to_corridor_slope_face" in str(row.get("surface", ""))
        and row.get("status") == "warning"
        for row in pair_rows
    )


def test_intersection_shared_boundary_graph_consumer_audit_reports_foreign_edges():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )
    audit_rows = cmd_build_corridor._intersection_shared_boundary_graph_audit_rows(graph)
    rows = [
        {
            "role": "design",
            "status": "ready",
            "graph_refs": cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
                graph,
                "intersection_slope_face_surface",
            ),
            "graph_audit_rows": audit_rows,
            "notes": "",
            "recommended_action": "No action needed",
        }
    ]

    audited = cmd_build_corridor._shared_boundary_graph_consumer_audit_rows(rows)
    design = audited[0]

    assert design["status"] == "warning"
    assert design["graph_foreign_edge_count"] > 0
    assert "shared_boundary_surface_owns_foreign_edge:design" in design["graph_foreign_edge_notes"]
    assert "consumer ownership" in design["recommended_action"]


def test_intersection_shared_boundary_graph_display_rows_carry_highlight_refs_and_segments():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )
    audit_rows = cmd_build_corridor._intersection_shared_boundary_graph_audit_rows(graph)
    rows = [
        {
            "role": "intersection_slope",
            "surface": "Intersection Slope Face Surface",
            "status": "ready",
            "graph_refs": cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
                graph,
                "intersection_slope_face_surface",
            ),
            "graph_audit_rows": audit_rows,
            "graph_status": graph.status,
            "graph_node_count": graph.node_count,
            "graph_edge_count": graph.edge_count,
            "graph_cell_count": graph.cell_count,
            "graph_consumed_edge_count": graph.edge_count,
            "notes": "",
            "recommended_action": "No action needed",
        }
    ]

    display_rows = cmd_build_corridor.shared_breakline_audit_display_rows(rows, include_internal=True)
    graph_edge_rows = [row for row in display_rows if row.get("row_kind") == "graph_edge"]
    graph_cell_rows = [row for row in display_rows if row.get("row_kind") == "graph_cell"]
    internal_seam_rows = [row for row in display_rows if row.get("row_kind") == "graph_internal_seam"]
    segment_rows = cmd_build_corridor._intersection_shared_boundary_graph_segment_rows(graph)
    parsed_segment = cmd_build_corridor._parse_intersection_shared_boundary_graph_segment_row(segment_rows[0])

    assert graph_edge_rows
    assert graph_cell_rows
    assert internal_seam_rows
    assert all(row["graph_edge_refs"] for row in internal_seam_rows)
    assert {
        row["breakline_role_filter"]
        for row in internal_seam_rows
    } == {"intersection_shared_boundary_graph_internal_seam"}
    assert graph_edge_rows[0]["graph_edge_refs"]
    assert graph_cell_rows[0]["graph_edge_refs"]
    assert parsed_segment is not None
    assert parsed_segment["edge_id"]
    assert len(parsed_segment["start"]) == 3
    assert len(parsed_segment["end"]) == 3


def test_boundary_loop_handoff_display_row_exposes_constraint_coverage():
    ready_rows = cmd_build_corridor.shared_breakline_audit_display_rows(
        [
            {
                "role": "design",
                "surface": "Design Surface",
                "status": "ready",
                "boundary_loop_ref_count": 4,
                "boundary_loop_constraint_segment_count": 8,
                "boundary_loop_constraint_edge_count": 8,
                "intersection_exclusion_tested_triangle_count": 20,
                "intersection_exclusion_clipped_triangle_count": 5,
                "intersection_exclusion_boundary_crossing_triangle_count": 2,
                "intersection_exclusion_near_boundary_kept_triangle_count": 3,
                "intersection_exclusion_clip_ratio": 0.25,
                "notes": "",
                "recommended_action": "No action needed",
            }
        ],
        include_internal=True,
    )
    warning_rows = cmd_build_corridor.shared_breakline_audit_display_rows(
        [
            {
                "role": "daylight",
                "surface": "Slope Face Surface",
                "status": "ready",
                "boundary_loop_ref_count": 4,
                "boundary_loop_constraint_segment_count": 8,
                "boundary_loop_constraint_edge_count": 0,
                "notes": "",
                "recommended_action": "No action needed",
            }
        ],
        include_internal=True,
    )
    near_warning_rows = cmd_build_corridor.shared_breakline_audit_display_rows(
        [
            {
                "role": "daylight",
                "surface": "Slope Face Surface",
                "status": "ready",
                "boundary_loop_ref_count": 4,
                "boundary_loop_constraint_segment_count": 8,
                "boundary_loop_constraint_edge_count": 8,
                "intersection_exclusion_tested_triangle_count": 40,
                "intersection_exclusion_clipped_triangle_count": 10,
                "intersection_exclusion_near_boundary_kept_triangle_count": 30,
                "boundary_loop_near_kept_warning": True,
                "notes": "",
                "recommended_action": "No action needed",
            }
        ],
        include_internal=True,
    )

    ready_handoff = next(row for row in ready_rows if row.get("row_kind") == "boundary_loop_handoff")
    warning_handoff = next(row for row in warning_rows if row.get("row_kind") == "boundary_loop_handoff")
    near_warning_handoff = next(row for row in near_warning_rows if row.get("row_kind") == "boundary_loop_handoff")

    assert ready_handoff["status"] == "ready"
    assert ready_handoff["consumed"] == 8
    assert ready_handoff["breakline_role_filter"] == "intersection_boundary_loop"
    assert "clip=5/20" in ready_handoff["role_summary"]
    assert "near_kept=3" in ready_handoff["role_summary"]
    assert "ratio=0.250" in ready_handoff["role_summary"]
    assert warning_handoff["status"] == "warning"
    assert warning_handoff["recommended_action"] == "Rebuild boundary-loop constrained surfaces"
    assert near_warning_handoff["status"] == "warning"
    assert near_warning_handoff["recommended_action"] == "Review boundary-loop clipping residuals, then rebuild constrained surfaces"


def test_intersection_shared_boundary_graph_internal_seam_highlight_uses_separate_kind():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )
    segment_rows = cmd_build_corridor._intersection_shared_boundary_graph_segment_rows(graph)
    source_obj = type(
        "Source",
        (),
        {
            "IntersectionSharedBoundaryGraphSegmentRows": segment_rows,
            "IntersectionSharedBoundaryGraphResultId": graph.graph_result_id,
            "Name": "SourceGraph",
            "Label": "Source Graph",
        },
    )()
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return type("Highlight", (), {"Name": "Highlight", "Label": "Highlight"})()

    original_create = cmd_build_corridor._create_intersection_shared_boundary_graph_highlight
    original_visibility = cmd_build_corridor._set_object_visibility
    original_select = cmd_build_corridor._select_and_fit_object
    original_app = cmd_build_corridor.App
    try:
        cmd_build_corridor._create_intersection_shared_boundary_graph_highlight = fake_create
        cmd_build_corridor._set_object_visibility = lambda *_args, **_kwargs: None
        cmd_build_corridor._select_and_fit_object = lambda *_args, **_kwargs: None
        cmd_build_corridor.App = type("App", (), {"ActiveDocument": object()})()

        seam_refs = cmd_build_corridor._intersection_shared_boundary_graph_internal_seam_refs(
            graph,
            "intersection_slope_face_surface",
        )
        cmd_build_corridor.show_intersection_shared_boundary_graph_highlight(
            source_obj=source_obj,
            edge_refs=seam_refs[:1],
            highlight_kind="internal_seam",
        )
    finally:
        cmd_build_corridor._create_intersection_shared_boundary_graph_highlight = original_create
        cmd_build_corridor._set_object_visibility = original_visibility
        cmd_build_corridor._select_and_fit_object = original_select
        cmd_build_corridor.App = original_app

    assert captured["highlight_kind"] == "internal_seam"
    assert captured["rows"]
    assert captured["rows"][0]["edge_id"] == seam_refs[0]


def test_intersection_exclusion_near_boundary_highlight_uses_serialized_centroids():
    raw_rows = [
        "tri-1|10.0|20.0|30.0|0.125",
        "tri-2|11.0|21.0|31.0|0.050",
        "bad-row",
    ]
    source_obj = type(
        "Source",
        (),
        {
            "IntersectionExclusionNearBoundaryKeptTriangleRows": raw_rows,
            "Name": "SourceSurface",
            "Label": "Source Surface",
        },
    )()
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return type("Highlight", (), {"Name": "Highlight", "Label": "Highlight"})()

    original_create = cmd_build_corridor._create_intersection_exclusion_near_boundary_highlight
    original_visibility = cmd_build_corridor._set_object_visibility
    original_select = cmd_build_corridor._select_and_fit_object
    original_app = cmd_build_corridor.App
    try:
        cmd_build_corridor._create_intersection_exclusion_near_boundary_highlight = fake_create
        cmd_build_corridor._set_object_visibility = lambda *_args, **_kwargs: None
        cmd_build_corridor._select_and_fit_object = lambda *_args, **_kwargs: None
        cmd_build_corridor.App = type("App", (), {"ActiveDocument": object()})()

        parsed = cmd_build_corridor._parse_intersection_exclusion_near_boundary_kept_triangle_row(raw_rows[0])
        cmd_build_corridor.show_intersection_exclusion_near_boundary_highlight(source_obj=source_obj)
    finally:
        cmd_build_corridor._create_intersection_exclusion_near_boundary_highlight = original_create
        cmd_build_corridor._set_object_visibility = original_visibility
        cmd_build_corridor._select_and_fit_object = original_select
        cmd_build_corridor.App = original_app

    assert parsed["triangle_id"] == "tri-1"
    assert parsed["centroid"] == (10.0, 20.0, 30.0)
    assert parsed["distance"] == 0.125
    assert len(captured["rows"]) == 2
    assert captured["rows"][1]["triangle_id"] == "tri-2"


def test_intersection_boundary_loop_graph_edges_are_visible_in_breakline_audit_rows():
    shared = _upper_cell_breakline_result()
    shared.breakline_rows = [
        replace(
            shared.breakline_rows[0],
            breakline_role="main_road_tie",
            consumer_refs=("intersection_surface", "design_surface", "intersection_slope_face_surface"),
            source_contract_refs=(
                "intersection-boundary-loops:starter-t_intersection",
                "intersection-boundary-loop:starter-t_intersection:outer",
                "intersection-boundary-segment:starter-t_intersection:main-road-tie:1",
                "intersection-boundary-owner:leg:01:east",
            ),
        )
    ]
    shared.point_rows = [
        point for point in shared.point_rows
        if str(point.breakline_ref) == str(shared.breakline_rows[0].breakline_id)
    ]
    shared.breakline_count = 1
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        shared,
        intersection_id="starter-t_intersection",
    )
    audit_rows = cmd_build_corridor._intersection_shared_boundary_graph_audit_rows(graph)
    parsed_edges = [
        cmd_build_corridor._parse_intersection_shared_boundary_graph_audit_row(raw)
        for raw in audit_rows
    ]
    parsed_edges = [row for row in parsed_edges if row and row["row_kind"] == "edge"]
    rows = [
        {
            "role": "intersection_slope",
            "surface": "Intersection Slope Face Surface",
            "status": "ready",
            "graph_refs": cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
                graph,
                "intersection_slope_face_surface",
            ),
            "graph_audit_rows": audit_rows,
            "graph_status": graph.status,
            "graph_node_count": graph.node_count,
            "graph_edge_count": graph.edge_count,
            "graph_cell_count": graph.cell_count,
            "graph_consumed_edge_count": graph.edge_count,
            "notes": "",
            "recommended_action": "No action needed",
        }
    ]

    display_rows = cmd_build_corridor.shared_breakline_audit_display_rows(rows, include_internal=True)
    boundary_rows = [row for row in display_rows if row.get("row_kind") == "graph_boundary_loop"]
    owner_rows = [row for row in display_rows if row.get("row_kind") == "graph_boundary_owner"]

    assert parsed_edges
    assert "intersection-boundary-loop" in parsed_edges[0]["source_refs"]
    assert boundary_rows
    assert owner_rows
    assert boundary_rows[0]["breakline_role_filter"] == "intersection_boundary_loop"
    assert boundary_rows[0]["graph_edge_refs"]
    assert "source_refs=intersection-boundary-loops" in boundary_rows[0]["notes"]
    assert "owner_refs=intersection-boundary-owner:leg:01:east" in boundary_rows[0]["notes"]
    assert (
        "owner_consumers=intersection-boundary-owner:leg:01:east->"
        "intersection_surface+design_surface+intersection_slope_face_surface"
    ) in boundary_rows[0]["notes"]
    assert owner_rows[0]["status"] == "ready"
    assert owner_rows[0]["breakline_role_filter"] == "intersection_boundary_owner"
    assert "owner_ref=intersection-boundary-owner:leg:01:east" in owner_rows[0]["notes"]
    assert "consumers=design_surface+intersection_slope_face_surface+intersection_surface" in owner_rows[0]["notes"]


def test_intersection_boundary_loop_graph_owner_missing_consumers_are_visible():
    shared = _upper_cell_breakline_result()
    shared.breakline_rows = [
        replace(
            shared.breakline_rows[0],
            breakline_role="side_road_tie",
            consumer_refs=("intersection_surface",),
            source_contract_refs=(
                "intersection-boundary-loops:starter-t_intersection",
                "intersection-boundary-loop:starter-t_intersection:outer",
                "intersection-boundary-segment:starter-t_intersection:side-road-tie:1",
                "intersection-boundary-owner:leg:02:south",
            ),
        )
    ]
    shared.point_rows = [
        point for point in shared.point_rows
        if str(point.breakline_ref) == str(shared.breakline_rows[0].breakline_id)
    ]
    shared.breakline_count = 1
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        shared,
        intersection_id="starter-t_intersection",
    )
    rows = [
        {
            "role": "intersection",
            "surface": "Intersection Surface",
            "status": "ready",
            "graph_refs": cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(
                graph,
                "intersection_surface",
            ),
            "graph_audit_rows": cmd_build_corridor._intersection_shared_boundary_graph_audit_rows(graph),
            "graph_status": graph.status,
            "graph_node_count": graph.node_count,
            "graph_edge_count": graph.edge_count,
            "graph_cell_count": graph.cell_count,
            "graph_consumed_edge_count": graph.edge_count,
            "notes": "",
            "recommended_action": "No action needed",
        }
    ]

    display_rows = cmd_build_corridor.shared_breakline_audit_display_rows(rows, include_internal=True)
    boundary_row = next(row for row in display_rows if row.get("row_kind") == "graph_boundary_loop")
    owner_row = next(row for row in display_rows if row.get("row_kind") == "graph_boundary_owner")

    assert boundary_row["status"] == "warning"
    assert "owner_refs=intersection-boundary-owner:leg:02:south" in boundary_row["notes"]
    assert (
        "owner_missing_consumers=intersection-boundary-owner:leg:02:south->"
        "design_surface+intersection_slope_face_surface"
    ) in boundary_row["notes"]
    assert owner_row["status"] == "warning"
    assert owner_row["recommended_action"] == "Review owner boundary-loop consumers, then rebuild surfaces"
    assert "owner_ref=intersection-boundary-owner:leg:02:south" in owner_row["notes"]
    assert "owner_missing_consumers=intersection-boundary-owner:leg:02:south->design_surface+intersection_slope_face_surface" in owner_row["notes"]


def test_boundary_loop_promoted_edges_share_graph_ids_across_consumers():
    boundary_loop = IntersectionBoundaryLoopResult(
        schema_version=1,
        project_id="project:test",
        boundary_loop_result_id="intersection-boundary-loops:starter-t_intersection",
        intersection_id="starter-t_intersection",
        status="ready",
        loop_count=1,
        ready_count=1,
        segment_count=3,
        loop_rows=[
            IntersectionBoundaryLoopRow(
                loop_id="intersection-boundary-loop:starter-t_intersection:outer",
                intersection_id="starter-t_intersection",
                loop_role="outer_intersection_boundary",
                status="ready",
                closed=True,
                point_count=3,
                segment_count=3,
                segment_refs=(
                    "intersection-boundary-segment:starter-t_intersection:main-road-tie:1",
                    "intersection-boundary-segment:starter-t_intersection:patch-to-design:1",
                    "intersection-boundary-segment:starter-t_intersection:side-road-tie:1",
                ),
            )
        ],
        segment_rows=[
            IntersectionBoundarySegmentRow(
                segment_id="intersection-boundary-segment:starter-t_intersection:main-road-tie:1",
                intersection_id="starter-t_intersection",
                loop_ref="intersection-boundary-loop:starter-t_intersection:outer",
                segment_role="main_road_tie",
                from_point_ref="outer:p1",
                to_point_ref="outer:p2",
                from_xyz=(0.0, 0.0, 0.0),
                to_xyz=(4.0, 0.0, 0.0),
                source_refs=("intersection-boundary-owner:leg:01:south",),
                expected_consumers=("intersection_surface", "design_surface", "intersection_slope_face_surface"),
                shared_breakline_ref="shared-boundary-loop:main-road-tie:1",
            ),
            IntersectionBoundarySegmentRow(
                segment_id="intersection-boundary-segment:starter-t_intersection:patch-to-design:1",
                intersection_id="starter-t_intersection",
                loop_ref="intersection-boundary-loop:starter-t_intersection:outer",
                segment_role="patch_to_design_surface",
                from_point_ref="outer:p2",
                to_point_ref="outer:p3",
                from_xyz=(4.0, 0.0, 0.0),
                to_xyz=(2.0, 3.0, 0.0),
                source_refs=("intersection-boundary-owner:patch:north",),
                expected_consumers=("intersection_surface", "design_surface", "intersection_slope_face_surface"),
                shared_breakline_ref="shared-boundary-loop:patch-to-design:1",
            ),
            IntersectionBoundarySegmentRow(
                segment_id="intersection-boundary-segment:starter-t_intersection:side-road-tie:1",
                intersection_id="starter-t_intersection",
                loop_ref="intersection-boundary-loop:starter-t_intersection:outer",
                segment_role="side_road_tie",
                from_point_ref="outer:p3",
                to_point_ref="outer:p1",
                from_xyz=(2.0, 3.0, 0.0),
                to_xyz=(0.0, 0.0, 0.0),
                source_refs=("intersection-boundary-owner:leg:02:south",),
                expected_consumers=("intersection_surface", "design_surface", "intersection_slope_face_surface"),
                shared_breakline_ref="shared-boundary-loop:side-road-tie:1",
            ),
        ],
    )
    shared = SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared-breakline:intersection:starter-t_intersection",
        domain_kind="intersection",
        domain_ref="starter-t_intersection",
        status="ready",
    )
    diagnostics: list[str] = []

    cmd_build_corridor._append_intersection_boundary_loop_shared_breaklines(
        result_id=shared.breakline_result_id,
        intersection_id="starter-t_intersection",
        boundary_loop_result=boundary_loop,
        breakline_rows=shared.breakline_rows,
        point_rows=shared.point_rows,
        diagnostics=diagnostics,
    )
    shared.breakline_count = len(shared.breakline_rows)
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        shared,
        intersection_id="starter-t_intersection",
    )

    intersection_refs = set(
        cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(graph, "intersection_surface")
    )
    design_refs = set(
        cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(graph, "design_surface")
    )
    slope_refs = set(
        cmd_build_corridor._intersection_shared_boundary_graph_refs_for_consumer(graph, "intersection_slope_face_surface")
    )
    main_edge = next(row for row in graph.edge_rows if row.edge_role == "main_road_tie")
    patch_edge = next(row for row in graph.edge_rows if row.edge_role == "patch_to_design_surface")
    side_edge = next(row for row in graph.edge_rows if row.edge_role == "side_road_tie")

    assert len(shared.breakline_rows) == 3
    assert not diagnostics
    assert main_edge.edge_id in intersection_refs & design_refs & slope_refs
    assert side_edge.edge_id in intersection_refs & design_refs & slope_refs
    assert patch_edge.edge_id in intersection_refs & design_refs & slope_refs
    assert "intersection-boundary-owner:leg:01:south" in main_edge.source_refs
    assert "intersection-boundary-owner:leg:02:south" in side_edge.source_refs


def test_intersection_shared_boundary_graph_summary_notes_expose_counts_and_status():
    rows = [
        {
            "graph_status": "ready",
            "graph_node_count": 4,
            "graph_edge_count": 5,
            "graph_cell_count": 2,
            "graph_consumed_edge_count": 5,
            "graph_duplicate_edge_count": 0,
            "graph_missing_consumer_count": 0,
            "graph_open_cell_count": 0,
            "graph_endpoint_mismatch_count": 0,
            "graph_not_snapped_count": 0,
            "graph_foreign_edge_count": 0,
            "graph_pair_missing_count": 0,
        }
    ]

    ready_notes = cmd_build_corridor._shared_boundary_graph_summary_notes(rows)
    warning_notes = cmd_build_corridor._shared_boundary_graph_summary_notes(
        [{**rows[0], "graph_pair_missing_count": 1}]
    )

    assert "Shared Boundary Graph: ready" in ready_notes
    assert "nodes=4" in ready_notes
    assert "edges=5" in ready_notes
    assert "cells=2" in ready_notes
    assert "surface_consumed_edges=5" in ready_notes
    assert "pair_missing=1" in warning_notes


def test_intersection_shared_boundary_graph_builder_reports_duplicate_and_missing_consumers():
    result = _upper_cell_breakline_result()
    duplicate_id = "shared:intersection-slope-face-to-corridor-slope-face:duplicate"
    result.point_rows.extend(
        [
            _point("pd1", duplicate_id, 1, 0.0, 1.0),
            _point("pd2", duplicate_id, 2, 2.0, 1.0),
        ]
    )
    result.breakline_rows.append(
        _breakline(
            duplicate_id,
            "intersection_slope_face_to_corridor_slope_face",
            ("pd1", "pd2"),
            ("intersection_slope_face_surface",),
        )
    )

    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        result,
        intersection_id="starter-t_intersection",
    )

    assert graph.status == "warning"
    assert graph.duplicate_edge_count == 1
    assert graph.missing_consumer_count == 1
    notes = ";".join(graph.diagnostic_rows)
    assert "shared_boundary_edge_duplicate_parallel" in notes
    assert "shared_boundary_edge_missing_consumer" in notes


def test_intersection_shared_boundary_graph_audit_reports_endpoint_and_snap_issues():
    graph = cmd_build_corridor.corridor_intersection_shared_boundary_graph_result(
        _split_upper_cell_breakline_result(),
        intersection_id="starter-t_intersection",
    )

    ready_audit = cmd_build_corridor.intersection_shared_boundary_graph_audit(graph)
    assert ready_audit["status"] == "ready"
    assert ready_audit["endpoint_mismatch_count"] == 0
    assert ready_audit["not_snapped_count"] == 0

    broken_graph = replace(graph)
    broken_graph.edge_rows = list(graph.edge_rows)
    broken_graph.node_rows = list(graph.node_rows)
    broken_graph.cell_rows = list(graph.cell_rows)
    broken_graph.edge_rows[0] = replace(graph.edge_rows[0], from_node_ref="missing-node")
    broken_graph.node_rows.append(replace(graph.node_rows[0], node_id="duplicate-node"))

    audit = cmd_build_corridor.intersection_shared_boundary_graph_audit(broken_graph)
    diagnostics = ";".join(audit["diagnostic_rows"])

    assert audit["status"] == "warning"
    assert audit["endpoint_mismatch_count"] == 1
    assert audit["not_snapped_count"] == 1
    assert "shared_boundary_edge_endpoint_mismatch" in diagnostics
    assert "shared_boundary_consumer_not_snapped" in diagnostics


def test_intersection_shared_boundary_graph_audit_reports_geometrically_closed_but_graph_open_cell():
    nodes = [
        IntersectionSharedBoundaryNodeRow(f"n{index}", "starter-t_intersection", "test", x, y, 0.0)
        for index, (x, y) in enumerate(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), start=1)
    ]
    edges = [
        IntersectionSharedBoundaryEdgeRow("e1", "starter-t_intersection", "upper_transition_internal_seam", "n1", "n2"),
        IntersectionSharedBoundaryEdgeRow("e2", "starter-t_intersection", "upper_transition_internal_seam", "n2", "n3"),
        IntersectionSharedBoundaryEdgeRow("e3", "starter-t_intersection", "upper_transition_internal_seam", "n3", "n4"),
        IntersectionSharedBoundaryEdgeRow("e4", "starter-t_intersection", "upper_transition_internal_seam", "n1", "n3"),
    ]
    graph = IntersectionSharedBoundaryGraphResult(
        schema_version=1,
        project_id="project:test",
        graph_result_id="intersection-shared-boundary-graph:manual",
        intersection_id="starter-t_intersection",
        status="ready",
        node_rows=nodes,
        edge_rows=edges,
        cell_rows=[
            IntersectionSharedBoundaryCellRow(
                "cell:manual",
                "starter-t_intersection",
                "upper_manual_cell",
                boundary_edge_refs=("e1", "e2", "e3", "e4"),
                loop_points_xyz=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0)),
                closed=True,
                status="ready",
            )
        ],
    )

    audit = cmd_build_corridor.intersection_shared_boundary_graph_audit(graph)
    diagnostics = ";".join(audit["diagnostic_rows"])

    assert audit["status"] == "warning"
    assert audit["graph_open_cell_count"] == 1
    assert "shared_boundary_cell_not_graph_closed" in diagnostics
    assert "node_degree" in diagnostics
