"""Contract tests for intersection shared-boundary graph builder."""

from __future__ import annotations

from dataclasses import replace

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result.shared_breakline import (
    SharedBreaklinePointRow,
    SharedBreaklineResult,
    SharedBreaklineRow,
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


def _cross_upper_panel_breakline_result() -> SharedBreaklineResult:
    rows: list[SharedBreaklineRow] = []
    points: list[SharedBreaklinePointRow] = []
    groups = (
        ("primary", "left", 0.0),
        ("primary", "right", 10.0),
        ("secondary", "left", 20.0),
        ("secondary", "right", 30.0),
    )
    for index, (alignment_ref, side, x0) in enumerate(groups, start=1):
        prefix = f"shared:cross-upper:{index}"
        patch_id = f"{prefix}:patch"
        design_id = f"{prefix}:design"
        outer_id = f"{prefix}:outer"
        patch_points = (f"{patch_id}:p1", f"{patch_id}:p2")
        design_points = (f"{design_id}:p1", f"{design_id}:p2")
        outer_points = (f"{outer_id}:p1", f"{outer_id}:p2")
        points.extend(
            [
                _point(patch_points[0], patch_id, 1, x0, 0.0),
                _point(patch_points[1], patch_id, 2, x0 + 2.0, 0.0),
                _point(design_points[0], design_id, 1, x0 + 2.0, 0.0),
                _point(design_points[1], design_id, 2, x0 + 2.0, 1.0),
                _point(outer_points[0], outer_id, 1, x0, 1.0),
                _point(outer_points[1], outer_id, 2, x0 + 2.0, 1.0),
            ]
        )
        rows.extend(
            [
                replace(
                    _breakline(
                        patch_id,
                        "patch_to_intersection_slope_face",
                        patch_points,
                        (
                            "intersection_surface",
                            "intersection_slope_face_surface",
                            "intersection_slope_face_cell_result",
                        ),
                    ),
                    alignment_ref=alignment_ref,
                    side=side,
                ),
                replace(
                    _breakline(
                        design_id,
                        "intersection_slope_face_to_design_surface",
                        design_points,
                        (
                            "intersection_slope_face_surface",
                            "design_surface",
                            "intersection_slope_face_cell_result",
                        ),
                    ),
                    alignment_ref=alignment_ref,
                    side=side,
                ),
                replace(
                    _breakline(
                        outer_id,
                        "intersection_slope_face_to_corridor_slope_face",
                        outer_points,
                        (
                            "intersection_slope_face_surface",
                            "slope_face_surface",
                            "intersection_slope_face_cell_result",
                        ),
                    ),
                    alignment_ref=alignment_ref,
                    side=side,
                ),
            ]
        )
    return SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="shared:intersection:cross-01",
        domain_kind="intersection",
        domain_ref="cross-01",
        status="ready",
        breakline_count=len(rows),
        ready_count=len(rows),
        breakline_rows=rows,
        point_rows=points,
    )


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


def test_intersection_shared_boundary_graph_audit_reports_split_boundary_source_segments():
    nodes = [
        IntersectionSharedBoundaryNodeRow(f"n{index}", "cross-01", "test", x, y, 0.0)
        for index, (x, y) in enumerate(((0.0, 0.0), (1.0, 0.0), (2.0, 0.0)), start=1)
    ]
    source_ref = "intersection-boundary-envelope:cross-01:corner:01:arc:01"
    graph = IntersectionSharedBoundaryGraphResult(
        schema_version=1,
        project_id="project:test",
        graph_result_id="intersection-shared-boundary-graph:split",
        intersection_id="cross-01",
        status="ready",
        node_rows=nodes,
        edge_rows=[
            IntersectionSharedBoundaryEdgeRow(
                "edge:surface-a",
                "cross-01",
                "curb_return_to_intersection_slope_face",
                "n1",
                "n2",
                consumer_refs=("intersection_surface",),
                source_refs=(source_ref,),
            ),
            IntersectionSharedBoundaryEdgeRow(
                "edge:surface-b",
                "cross-01",
                "curb_return_to_intersection_slope_face",
                "n2",
                "n3",
                consumer_refs=("intersection_slope_face_surface",),
                source_refs=(source_ref,),
            ),
        ],
    )

    audit = cmd_build_corridor.intersection_shared_boundary_graph_audit(graph)
    diagnostics = ";".join(audit["diagnostic_rows"])

    assert audit["status"] == "warning"
    assert audit["source_segment_split_count"] == 1
    assert "shared_boundary_source_segment_split" in diagnostics
    assert source_ref in diagnostics
