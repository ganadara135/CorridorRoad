from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
)
from freecad.Corridor_Road.v1.models.result.intersection_tie_in_edge import (
    IntersectionTieInEdgeResult,
    IntersectionTieInEdgeRow,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionBoundarySegmentEvaluationRequest,
    IntersectionBoundarySegmentEvaluationService,
)


def _tie_in_result(*, include_secondary=True):
    rows = [
        IntersectionTieInEdgeRow(
            "tie-in:test:primary:left",
            "intersection:test",
            "primary",
            side="left",
            start_xyz=(96.0, 5.0, 10.0),
            end_xyz=(144.0, 5.0, 10.0),
            notes="target_station=120.000",
        ),
        IntersectionTieInEdgeRow(
            "tie-in:test:primary:right",
            "intersection:test",
            "primary",
            side="right",
            start_xyz=(96.0, -5.0, 10.0),
            end_xyz=(144.0, -5.0, 10.0),
            notes="target_station=120.000",
        ),
    ]
    if include_secondary:
        rows.extend(
            (
                IntersectionTieInEdgeRow(
                    "tie-in:test:side:left",
                    "intersection:test",
                    "side",
                    side="left",
                    start_xyz=(116.0, -24.0, 12.0),
                    end_xyz=(116.0, 24.0, 12.0),
                ),
                IntersectionTieInEdgeRow(
                    "tie-in:test:side:right",
                    "intersection:test",
                    "side",
                    side="right",
                    start_xyz=(124.0, -24.0, 12.0),
                    end_xyz=(124.0, 24.0, 12.0),
                ),
            )
        )
    return IntersectionTieInEdgeResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="intersection:test",
        status="ready",
        edge_count=len(rows),
        edge_rows=rows,
    )


def _model(kind="t_intersection", policy=None):
    return SimpleNamespace(
        intersection_rows=(
            SimpleNamespace(
                intersection_id="intersection:test",
                intersection_kind=kind,
                primary_alignment_ref="primary",
                secondary_alignment_refs=("side",),
                intersection_point_x=120.0,
                intersection_point_y=0.0,
                intersection_point_z=11.0,
            ),
        ),
        curb_return_policy_rows=(() if policy is None else (policy,)),
    )


def _evaluate(*, kind="t_intersection", policy=None, include_secondary=True):
    return IntersectionBoundarySegmentEvaluationService().evaluate(
        IntersectionBoundarySegmentEvaluationRequest(
            tie_in_result=_tie_in_result(include_secondary=include_secondary),
            intersection_model=_model(kind, policy),
        )
    )


def test_service_maps_tie_ins_and_builds_traceable_curb_return_arcs() -> None:
    policy = SimpleNamespace(
        policy_id="curb-return:test",
        intersection_id="intersection:test",
        radius=12.0,
        status="active",
    )

    result = _evaluate(policy=policy)

    assert isinstance(result, IntersectionBoundarySegmentResult)
    assert result.status == "ready"
    assert result.segment_count == 6
    assert result.tie_in_segment_count == 4
    assert result.arc_segment_count == 2
    assert result.diagnostic_rows == []
    assert [row.source_ref for row in result.segment_rows[:4]] == [
        "tie-in:test:primary:left",
        "tie-in:test:primary:right",
        "tie-in:test:side:left",
        "tie-in:test:side:right",
    ]
    arc_rows = result.segment_rows[4:]
    assert [row.boundary_segment_id for row in arc_rows] == [
        "boundary:intersection:test:curb-return:1",
        "boundary:intersection:test:curb-return:2",
    ]
    assert all(row.source_ref == "curb-return:test" for row in arc_rows)
    assert all(row.center_xyz == (120.0, 0.0, 11.0) for row in arc_rows)
    assert all(row.radius == 12.0 for row in arc_rows)
    assert all(len(row.chord_points_xyz) == 11 for row in arc_rows)
    assert all("arc_samples=11" in row.notes for row in arc_rows)


@pytest.mark.parametrize(
    ("kind", "expected_radius", "expected_arcs"),
    (
        ("t_intersection", 12.0, 2),
        ("cross_intersection", 10.0, 4),
        ("y_intersection", 15.0, 2),
    ),
)
def test_service_preserves_intersection_kind_defaults_and_arc_counts(
    kind,
    expected_radius,
    expected_arcs,
) -> None:
    result = _evaluate(kind=kind)

    arc_rows = [row for row in result.segment_rows if row.segment_kind == "arc"]
    assert result.status == "ready"
    assert len(arc_rows) == expected_arcs
    assert all(row.radius == expected_radius for row in arc_rows)
    assert all(f"kind={kind}" in row.notes for row in arc_rows)


def test_service_validates_radius_and_clamps_explicit_sample_count() -> None:
    policy = SimpleNamespace(
        policy_id="curb-return:invalid",
        intersection_id="intersection:test",
        radius=0.0,
        arc_sample_count=3,
        status="active",
    )

    result = _evaluate(policy=policy)

    arc_rows = [row for row in result.segment_rows if row.segment_kind == "arc"]
    assert result.status == "ready"
    assert all(row.radius == 12.0 for row in arc_rows)
    assert all(len(row.chord_points_xyz) == 5 for row in arc_rows)
    assert result.diagnostic_rows[0] == (
        "warning:intersection_curb_return_radius_invalid: radius 0.000 is not "
        "positive; default radius used."
    )


def test_service_retains_incomplete_and_direction_fallback_diagnostics() -> None:
    result = _evaluate(include_secondary=False)

    assert result.status == "warning"
    assert result.tie_in_segment_count == 2
    assert result.arc_segment_count == 2
    assert any(
        row.startswith(
            "warning:intersection_boundary_direction_fallback: secondary"
        )
        for row in result.diagnostic_rows
    )
    assert (
        "intersection_boundary_tie_in_edges_incomplete: expected at least 4 "
        "tie-in segments, found 2."
        in result.diagnostic_rows
    )


def test_service_reports_large_radius_without_blocking_ready_result() -> None:
    policy = SimpleNamespace(
        policy_id="curb-return:large",
        intersection_id="intersection:test",
        radius=80.0,
        status="active",
    )

    result = _evaluate(policy=policy)

    assert result.status == "ready"
    assert any(
        row.startswith("warning:intersection_curb_return_radius_large:")
        for row in result.diagnostic_rows
    )


def test_command_wrapper_and_preparation_pipeline_use_boundary_service() -> None:
    wrapper_source = inspect.getsource(
        cmd_build_corridor.corridor_intersection_boundary_segment_result
    )
    pipeline_source = inspect.getsource(
        cmd_build_corridor._build_intersection_surface_patch_tin
    )

    assert "IntersectionBoundarySegmentEvaluationService().evaluate(" in (
        wrapper_source
    )
    assert "IntersectionBoundarySegmentEvaluationRequest(" in wrapper_source
    assert "IntersectionBoundarySegmentRow(" not in wrapper_source
    assert (
        "IntersectionBoundarySegmentEvaluationService().evaluate_context"
        in pipeline_source
    )
