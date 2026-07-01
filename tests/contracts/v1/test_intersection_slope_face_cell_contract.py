from freecad.Corridor_Road.v1.models.result.intersection_slope_face_cell import (
    IntersectionSlopeFaceCellResult,
    IntersectionSlopeFaceCellRow,
)


def test_intersection_slope_face_cell_result_records_closed_shared_breakline_cell():
    row = IntersectionSlopeFaceCellRow(
        cell_id="cell:upper-left",
        intersection_id="intersection:starter-t_intersection",
        cell_role="upper_left_transition_cell",
        alignment_ref="alignment:main",
        side="left",
        inner_breakline_ref="patch-to-intersection-slope-face:1",
        outer_breakline_ref="intersection-slope-face-to-corridor-slope-face:1",
        left_breakline_ref="intersection-slope-face-to-design-surface:1",
        right_breakline_ref="main-side-slope-face-tie:1",
        boundary_breakline_refs=(
            "patch-to-intersection-slope-face:1",
            "intersection-slope-face-to-corridor-slope-face:1",
            "intersection-slope-face-to-design-surface:1",
            "main-side-slope-face-tie:1",
        ),
        loop_points_xyz=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
        source_applied_section_refs=("applied-section:main:108.000",),
        source_intersection_refs=("intersection-surface-zone:starter-t_intersection",),
        source_shared_breakline_refs=(
            "shared-breakline:patch-to-intersection-slope-face:1",
            "shared-breakline:intersection-slope-face-to-corridor-slope-face:1",
        ),
        closed_xy=True,
        point_count=5,
        surface_generation_status="ready",
        status="ready",
    )

    result = IntersectionSlopeFaceCellResult(
        schema_version=1,
        project_id="project:test",
        cell_result_id="intersection-slope-face-cells:test",
        intersection_id="intersection:starter-t_intersection",
        status="ready",
        cell_count=1,
        ready_count=1,
        cell_rows=[row],
    )

    assert result.status == "ready"
    assert result.cell_rows[0].consumer_surface_ref == "intersection_slope_face_surface"
    assert result.cell_rows[0].closed_xy is True
    assert "main-side-slope-face-tie:1" in result.cell_rows[0].boundary_breakline_refs


def test_intersection_slope_face_cell_result_reports_open_missing_edge_cell():
    row = IntersectionSlopeFaceCellRow(
        cell_id="cell:upper-gap",
        intersection_id="intersection:starter-t_intersection",
        cell_role="upper_mid_transition_cell",
        inner_breakline_ref="patch-to-intersection-slope-face:2",
        outer_breakline_ref="",
        boundary_breakline_refs=("patch-to-intersection-slope-face:2",),
        closed_xy=False,
        point_count=3,
        status="warning",
        diagnostics=("intersection_slope_face_cell_edge_missing", "intersection_slope_face_cell_open"),
    )

    result = IntersectionSlopeFaceCellResult(
        schema_version=1,
        project_id="project:test",
        cell_result_id="intersection-slope-face-cells:test",
        intersection_id="intersection:starter-t_intersection",
        status="warning",
        cell_count=1,
        warning_count=1,
        open_cell_count=1,
        missing_edge_count=1,
        diagnostic_rows=["intersection_slope_face_cell_edge_missing"],
        cell_rows=[row],
    )

    assert result.open_cell_count == 1
    assert result.missing_edge_count == 1
    assert "intersection_slope_face_cell_open" in result.cell_rows[0].diagnostics


def test_intersection_slope_face_cell_result_records_main_side_tie_cell():
    row = IntersectionSlopeFaceCellRow(
        cell_id="cell:main-side-left",
        intersection_id="intersection:starter-t_intersection",
        cell_role="main_to_side_left_tie_cell",
        alignment_ref="alignment:side",
        side="left",
        inner_breakline_ref="main-side-slope-face-tie:1",
        arc_breakline_ref="curb-return-to-intersection-slope-face:1",
        boundary_breakline_refs=(
            "main-side-slope-face-tie:1",
            "curb-return-to-intersection-slope-face:1",
        ),
        loop_points_xyz=(
            (0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
        source_intersection_refs=("intersection-boundary-segments:starter-t_intersection",),
        source_shared_breakline_refs=(
            "shared-breakline:main-side-slope-face-tie:1",
            "shared-breakline:curb-return-to-intersection-slope-face:1",
        ),
        closed_xy=True,
        point_count=4,
        surface_generation_status="ready",
        status="ready",
    )

    result = IntersectionSlopeFaceCellResult(
        schema_version=1,
        project_id="project:test",
        cell_result_id="intersection-slope-face-cells:test",
        intersection_id="intersection:starter-t_intersection",
        status="ready",
        cell_count=1,
        ready_count=1,
        cell_rows=[row],
    )

    assert result.cell_rows[0].cell_role == "main_to_side_left_tie_cell"
    assert result.cell_rows[0].arc_breakline_ref == "curb-return-to-intersection-slope-face:1"
