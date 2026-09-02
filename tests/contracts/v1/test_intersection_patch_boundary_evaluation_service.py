from __future__ import annotations

import inspect

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
    IntersectionBoundarySegmentRow,
)
from freecad.Corridor_Road.v1.models.result.intersection_patch_boundary import (
    IntersectionPatchBoundaryResult,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionPatchBoundaryEvaluationRequest,
    IntersectionPatchBoundaryEvaluationService,
)


def _result(rows, *, diagnostics=()):
    return IntersectionBoundarySegmentResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="intersection:test",
        status="ready",
        segment_count=len(rows),
        diagnostic_rows=list(diagnostics),
        segment_rows=list(rows),
    )


def _segment(segment_id, start, end, *, role="outer", kind="tie_in"):
    return IntersectionBoundarySegmentRow(
        boundary_segment_id=segment_id,
        intersection_id="intersection:test",
        segment_kind=kind,
        segment_role=role,
        start_xyz=start,
        end_xyz=end,
    )


def test_service_prefers_tie_in_strip_union_and_preserves_identity() -> None:
    rows = (
        IntersectionBoundarySegmentRow(
            "boundary:primary:left",
            "intersection:test",
            "tie_in",
            alignment_ref="primary",
            side="left",
            start_xyz=(0.0, 2.0, 10.0),
            end_xyz=(10.0, 2.0, 10.0),
        ),
        IntersectionBoundarySegmentRow(
            "boundary:primary:right",
            "intersection:test",
            "tie_in",
            alignment_ref="primary",
            side="right",
            start_xyz=(0.0, -2.0, 10.0),
            end_xyz=(10.0, -2.0, 10.0),
        ),
        IntersectionBoundarySegmentRow(
            "boundary:side:left",
            "intersection:test",
            "tie_in",
            alignment_ref="side",
            side="left",
            start_xyz=(4.0, -6.0, 11.0),
            end_xyz=(4.0, 6.0, 11.0),
        ),
        IntersectionBoundarySegmentRow(
            "boundary:side:right",
            "intersection:test",
            "tie_in",
            alignment_ref="side",
            side="right",
            start_xyz=(6.0, -6.0, 11.0),
            end_xyz=(6.0, 6.0, 11.0),
        ),
    )

    result = IntersectionPatchBoundaryEvaluationService().evaluate(
        IntersectionPatchBoundaryEvaluationRequest(_result(rows))
    )

    assert isinstance(result, IntersectionPatchBoundaryResult)
    assert result.status == "ready"
    assert result.boundary_mode == "tie_in_strip_union"
    assert result.closed is True
    assert result.source_segment_count == 4
    assert result.boundary_point_count >= 8
    assert result.ring_count == 1
    assert result.self_crossing is False
    assert result.polygon_area > 0.0
    assert [row.order_index for row in result.point_rows] == list(
        range(1, result.boundary_point_count + 1)
    )
    assert all(row.source_kind == "tie_in_union" for row in result.point_rows)
    assert all(
        row.boundary_point_id.startswith(
            "patch-boundary:intersection:test:tie-in-union:"
        )
        for row in result.point_rows
    )


def test_service_preserves_hole_ring_and_subtracts_its_area() -> None:
    rows = (
        _segment("boundary:outer-1", (0.0, 0.0, 0.0), (20.0, 0.0, 0.0)),
        _segment("boundary:outer-2", (20.0, 0.0, 0.0), (20.0, 20.0, 0.0)),
        _segment("boundary:outer-3", (20.0, 20.0, 0.0), (0.0, 20.0, 0.0)),
        _segment("boundary:outer-4", (0.0, 20.0, 0.0), (0.0, 0.0, 0.0)),
        IntersectionBoundarySegmentRow(
            "boundary:hole-1",
            "intersection:test",
            "control_edge",
            segment_role="hole",
            chord_points_xyz=(
                (8.0, 8.0, 0.0),
                (12.0, 8.0, 0.0),
                (12.0, 12.0, 0.0),
                (8.0, 12.0, 0.0),
            ),
        ),
    )

    result = IntersectionPatchBoundaryEvaluationService().evaluate(
        IntersectionPatchBoundaryEvaluationRequest(_result(rows))
    )

    assert result.status == "ready"
    assert result.closed is True
    assert result.boundary_point_count == 8
    assert result.ring_count == 2
    assert result.outer_ring_count == 1
    assert result.hole_ring_count == 1
    assert result.island_ring_count == 0
    assert result.polygon_area == 384.0
    assert [row.ring_role for row in result.point_rows[:4]] == ["outer"] * 4
    assert [row.ring_role for row in result.point_rows[4:]] == ["hole"] * 4


def test_service_reports_outside_hole_and_retains_source_diagnostics() -> None:
    rows = (
        _segment("boundary:outer-1", (0.0, 0.0, 0.0), (20.0, 0.0, 0.0)),
        _segment("boundary:outer-2", (20.0, 0.0, 0.0), (20.0, 20.0, 0.0)),
        _segment("boundary:outer-3", (20.0, 20.0, 0.0), (0.0, 20.0, 0.0)),
        _segment("boundary:outer-4", (0.0, 20.0, 0.0), (0.0, 0.0, 0.0)),
        IntersectionBoundarySegmentRow(
            "boundary:hole-1",
            "intersection:test",
            "control_edge",
            segment_role="hole",
            chord_points_xyz=(
                (30.0, 30.0, 0.0),
                (34.0, 30.0, 0.0),
                (34.0, 34.0, 0.0),
                (30.0, 34.0, 0.0),
            ),
        ),
    )

    result = IntersectionPatchBoundaryEvaluationService().evaluate(
        IntersectionPatchBoundaryEvaluationRequest(
            _result(rows, diagnostics=("warning:source_boundary_observation",))
        )
    )

    assert result.status == "warning"
    assert result.closed is False
    assert result.diagnostic_rows[0] == "warning:source_boundary_observation"
    assert any(
        row.startswith("intersection_patch_boundary_inner_ring_outside_outer:")
        for row in result.diagnostic_rows
    )


def test_service_rejects_zero_area_ordered_outer_boundary() -> None:
    rows = (
        _segment("boundary:1", (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)),
        _segment("boundary:2", (10.0, 0.0, 0.0), (20.0, 0.0, 0.0)),
        _segment("boundary:3", (20.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    )

    result = IntersectionPatchBoundaryEvaluationService().evaluate(
        IntersectionPatchBoundaryEvaluationRequest(_result(rows))
    )

    assert result.status == "warning"
    assert result.closed is False
    assert result.polygon_area == 0.0
    assert any(
        row.startswith("intersection_patch_boundary_zero_area:")
        for row in result.diagnostic_rows
    )


def test_command_wrapper_and_preparation_pipeline_use_patch_boundary_service() -> None:
    wrapper_source = inspect.getsource(
        cmd_build_corridor.corridor_intersection_patch_boundary_result
    )
    pipeline_source = inspect.getsource(
        cmd_build_corridor._build_intersection_surface_patch_tin
    )

    assert "IntersectionPatchBoundaryEvaluationService().evaluate(" in wrapper_source
    assert "IntersectionPatchBoundaryEvaluationRequest(" in wrapper_source
    assert "IntersectionPatchBoundaryPointRow(" not in wrapper_source
    assert (
        "IntersectionPatchBoundaryEvaluationService().evaluate_context"
        in pipeline_source
    )
