from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import IntersectionPatchPipelineResult
from freecad.Corridor_Road.v1.models.result.tin_surface import TINVertex
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchPipelineRequest,
    IntersectionPatchPipelineService,
)


def _request(vertices):
    return IntersectionPatchPipelineRequest(
        project_id="project:test",
        surface_id="surface:test",
        intersection_id="intersection:test",
        corridor_id="corridor:test",
        applied_section_set_id="sections:test",
        source_control_region_refs=("region:b", "region:a"),
        evaluated_control_region_refs=("region:b", "region:a"),
        participating_alignment_count=2,
        control_region_count=2,
        tie_in_edge_count=4,
        graded_vertices=tuple(vertices),
        grading_plane=None,
        grading_result=SimpleNamespace(
            grading_mode="use_normal_superelevation",
            max_z_delta=0.0,
        ),
        superelevation_context=SimpleNamespace(
            source_count=0,
            transition_count=0,
            left_min=0.0,
            left_max=0.0,
            right_min=0.0,
            right_max=0.0,
            summary="sources=0; uses Applied Section default crossfall context",
        ),
        boundary_context=SimpleNamespace(
            tie_in_result=None,
            boundary_segment_result=None,
            patch_boundary_result=None,
            boundary_loop_result=None,
            shared_breakline_result=None,
            boundary_evaluation_failed=False,
        ),
        intersection_model=None,
        triangulation_policy={
            "long_edge_factor": 2.5,
            "max_boundary_edge_length": 0.0,
        },
    )


def test_pipeline_builds_final_tin_and_exposes_all_typed_stages() -> None:
    vertices = (
        TINVertex("v1", 0.0, 0.0, 10.0, source_point_ref="source:v1"),
        TINVertex("v2", 4.0, 0.0, 11.0, source_point_ref="source:v2"),
        TINVertex("v3", 0.0, 4.0, 12.0, source_point_ref="source:v3"),
    )

    result = IntersectionPatchPipelineService().build(_request(vertices))

    assert isinstance(result, IntersectionPatchPipelineResult)
    assert result.status == "ready"
    assert result.completed_stages == (
        "boundary_selection",
        "centroid",
        "drainage_review",
        "triangulation",
        "shared_breakline_constraints",
        "shape_quality",
        "tin_assembly",
    )
    assert result.failed_stage == ""
    assert result.boundary_selection.boundary_source == "convex_hull_fallback"
    assert result.center_vertex.vertex_id == "v:center"
    assert result.center_vertex.x == 4.0 / 3.0
    assert result.center_vertex.y == 4.0 / 3.0
    assert result.center_vertex.z == 11.0
    assert result.center_vertex.source_point_ref == "surface:test:centroid"
    assert result.center_vertex.notes == "intersection patch centroid"
    assert result.drainage_review.low_point_source_ref == "source:v1"
    assert result.triangulation.selection_path == "ordered_polygon_fallback"
    assert result.constraint_build.mode == "none"
    assert result.shape_quality.triangulation_mode == "ear_clip"
    assert result.assembly.status == "ready"
    assert result.tin_surface is result.assembly.tin_surface
    assert len(result.tin_surface.quality_rows) == 69
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_fallback:convex_hull_fallback",
        "intersection_patch_triangulation_fallback:ordered_polygon",
    )


def test_pipeline_reports_boundary_selection_failure_without_losing_result() -> None:
    vertices = (
        TINVertex("v1", 0.0, 0.0, 10.0),
        TINVertex("v2", 1.0, 0.0, 10.0),
    )

    result = IntersectionPatchPipelineService().build(_request(vertices))

    assert result.status == "error"
    assert result.failed_stage == "boundary_selection"
    assert result.completed_stages == ()
    assert result.boundary_selection.status == "error"
    assert result.center_vertex is None
    assert result.tin_surface is None
    assert result.error_message == (
        "intersection_patch_boundary_too_few_points: at least three unique "
        "patch boundary points are required."
    )


def test_pipeline_reports_degenerate_triangulation_with_partial_stages() -> None:
    vertices = (
        TINVertex("v1", 0.0, 0.0, 10.0),
        TINVertex("v2", 1.0, 0.0, 10.0),
        TINVertex("v3", 2.0, 0.0, 10.0),
    )

    result = IntersectionPatchPipelineService().build(_request(vertices))

    assert result.status == "error"
    assert result.failed_stage == "triangulation"
    assert result.completed_stages == (
        "boundary_selection",
        "centroid",
        "drainage_review",
    )
    assert result.boundary_selection.status == "ready"
    assert result.center_vertex is not None
    assert result.drainage_review.status == "ready"
    assert result.triangulation.status == "error"
    assert result.constraint_build is None
    assert result.tin_surface is None
    assert result.error_message.startswith("intersection_patch_degenerate_triangle")
