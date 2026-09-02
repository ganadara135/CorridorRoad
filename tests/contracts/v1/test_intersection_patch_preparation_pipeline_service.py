from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchPreparationPipelineResult,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchBoundaryContextService,
    IntersectionPatchPreparationPipelineRequest,
    IntersectionPatchPreparationPipelineService,
)


def _section(points, *, superelevation_id=""):
    return SimpleNamespace(
        applied_section_id="section:1",
        alignment_id="alignment:primary",
        station=100.0,
        region_id="region:b",
        active_intersection_id="intersection:test",
        active_superelevation_id=superelevation_id,
        active_superelevation_transition_id=(
            "transition:test" if superelevation_id else ""
        ),
        superelevation_left_crossfall=-2.0,
        superelevation_right_crossfall=2.0,
        point_rows=tuple(
            SimpleNamespace(point_role="fg_surface", x=x, y=y, z=z)
            for x, y, z in points
        ),
    )


def _request(points, *, superelevation_id=""):
    section = _section(points, superelevation_id=superelevation_id)
    applied_section_set = SimpleNamespace(
        applied_section_set_id="sections:test",
        sections=(section,),
        station_rows=(
            SimpleNamespace(applied_section_id="section:1", station=100.0),
        ),
    )
    prerequisite = SimpleNamespace(
        intersection_id="intersection:test",
        control_region_refs=("region:b", "region:a", "region:b"),
        participating_alignment_count=2,
        control_region_count=2,
        tie_in_edge_count=4,
    )
    return IntersectionPatchPreparationPipelineRequest(
        project_id="project:test",
        surface_id="surface:test",
        corridor_id="corridor:test",
        applied_section_set=applied_section_set,
        prerequisite=prerequisite,
        triangulation_policy={
            "long_edge_factor": 2.5,
            "max_boundary_edge_length": 0.0,
        },
    )


def _boundary_context_service(calls, *, fail_patch=False):
    def tie_in(*_args, **_kwargs):
        calls.append("tie_in_edges")
        return SimpleNamespace(edge_rows=())

    def segments(*_args, **_kwargs):
        calls.append("boundary_segments")
        return SimpleNamespace(segment_rows=())

    def patch(*_args, **_kwargs):
        calls.append("ordered_patch_boundary")
        if fail_patch:
            raise ValueError("test boundary failure")
        return None

    def loops(*_args, **_kwargs):
        calls.append("authoritative_boundary_loops")
        return None

    def shared(*_args, **_kwargs):
        calls.append("shared_breaklines")
        return None

    return IntersectionPatchBoundaryContextService(
        tie_in_evaluator=tie_in,
        boundary_segment_evaluator=segments,
        patch_boundary_evaluator=patch,
        boundary_loop_evaluator=loops,
        shared_breakline_evaluator=shared,
    )


def test_preparation_pipeline_builds_final_tin_and_retains_stage_results() -> None:
    calls = []
    service = IntersectionPatchPreparationPipelineService(
        boundary_context_service=_boundary_context_service(calls)
    )

    result = service.build(
        _request(
            ((0.0, 0.0, 10.0), (4.0, 0.0, 11.0), (0.0, 4.0, 12.0)),
            superelevation_id="superelevation:test",
        )
    )

    assert isinstance(result, IntersectionPatchPreparationPipelineResult)
    assert result.status == "ready"
    assert result.completed_stages == (
        "input_preparation",
        "grading",
        "boundary_context",
        "patch_pipeline",
    )
    assert calls == [
        "tie_in_edges",
        "boundary_segments",
        "ordered_patch_boundary",
        "authoritative_boundary_loops",
        "shared_breaklines",
    ]
    assert result.prepared_input.control_region_refs == ("region:a", "region:b")
    assert result.prepared_input.superelevation_context.source_count == 1
    assert result.grading_result.vertex_rows == result.prepared_input.vertex_rows
    assert result.boundary_context.status == "ready"
    assert result.patch_pipeline.status == "ready"
    assert result.tin_surface is result.patch_pipeline.tin_surface
    assert len(result.tin_surface.quality_rows) == 69
    assert result.diagnostic_rows == (
        "intersection_grading_policy_missing_default_applied",
        "intersection_patch_boundary_fallback:convex_hull_fallback",
        "intersection_patch_triangulation_fallback:ordered_polygon",
    )


def test_preparation_pipeline_stops_on_insufficient_fg_points() -> None:
    calls = []
    service = IntersectionPatchPreparationPipelineService(
        boundary_context_service=_boundary_context_service(calls)
    )

    result = service.build(_request(((0.0, 0.0, 10.0), (1.0, 0.0, 10.0))))

    assert result.status == "error"
    assert result.failed_stage == "input_preparation"
    assert result.completed_stages == ()
    assert result.prepared_input.status == "error"
    assert result.grading_result is None
    assert result.boundary_context is None
    assert result.patch_pipeline is None
    assert calls == []
    assert result.error_message == (
        "intersection_patch_boundary_too_few_points: at least three unique "
        "fg_surface points are required."
    )


def test_boundary_context_failure_remains_visible_when_fallback_succeeds() -> None:
    calls = []
    service = IntersectionPatchPreparationPipelineService(
        boundary_context_service=_boundary_context_service(calls, fail_patch=True)
    )

    result = service.build(
        _request(((0.0, 0.0, 10.0), (4.0, 0.0, 11.0), (0.0, 4.0, 12.0)))
    )

    assert result.status == "ready"
    assert result.boundary_context.status == "error"
    assert result.boundary_context.failed_stage == "ordered_patch_boundary"
    assert result.boundary_context.tie_in_result is not None
    assert result.boundary_context.boundary_segment_result is not None
    assert result.patch_pipeline.boundary_selection.boundary_source == (
        "convex_hull_fallback"
    )
    assert any(
        row.startswith(
            "intersection_patch_boundary_context_failed:ordered_patch_boundary:"
        )
        for row in result.diagnostic_rows
    )
    assert "intersection_patch_boundary_fallback:convex_hull_fallback" in (
        result.diagnostic_rows
    )


def test_preparation_pipeline_reports_post_context_failure_with_partials() -> None:
    calls = []
    service = IntersectionPatchPreparationPipelineService(
        boundary_context_service=_boundary_context_service(calls)
    )

    result = service.build(
        _request(((0.0, 0.0, 10.0), (1.0, 0.0, 10.0), (2.0, 0.0, 10.0)))
    )

    assert result.status == "error"
    assert result.failed_stage == "patch_pipeline"
    assert result.completed_stages == (
        "input_preparation",
        "grading",
        "boundary_context",
    )
    assert result.prepared_input.status == "ready"
    assert result.grading_result.status == "ready"
    assert result.boundary_context.status == "ready"
    assert result.patch_pipeline.failed_stage == "triangulation"
    assert result.tin_surface is None
    assert result.error_message.startswith("intersection_patch_degenerate_triangle")
