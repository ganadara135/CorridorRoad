from __future__ import annotations

import inspect
from types import SimpleNamespace

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchTinAssemblyResult,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchTinAssemblyRequest,
    IntersectionPatchTinAssemblyService,
)


EXPECTED_QUALITY_KINDS = (
    "patch_boundary_point_count",
    "patch_boundary_source",
    "participating_alignment_count",
    "control_region_count",
    "tie_in_edge_count",
    "patch_triangle_count",
    "patch_degenerate_triangle_count",
    "patch_boundary_edge_max_length",
    "patch_boundary_edge_long_count",
    "patch_boundary_edge_long_factor",
    "patch_boundary_edge_long_limit",
    "patch_boundary_edge_max_length_policy",
    "patch_triangulation_mode",
    "patch_surface_boundary_strategy",
    "patch_structured_strip_count",
    "patch_curb_return_surface_edge_count",
    "patch_curb_return_arc_count",
    "patch_curb_return_arc_sample_count",
    "patch_curb_return_arc_segment_count",
    "patch_edge_blend_face_count",
    "patch_boundary_role_summary",
    "patch_boundary_pavement_tie_in_edge_count",
    "patch_boundary_stem_tie_in_edge_count",
    "patch_boundary_overlap_cut_edge_count",
    "patch_boundary_curb_return_edge_count",
    "shared_breakline_constraint_mode",
    "shared_breakline_constraint_segment_count",
    "shared_breakline_constraint_edge_count",
    "shared_breakline_constraint_vertex_count",
    "shared_breakline_boundary_loop_constraint_segment_count",
    "shared_breakline_boundary_loop_constraint_edge_count",
    "shared_breakline_boundary_loop_constraint_refs",
    "shared_breakline_boundary_loop_constraint_role_summary",
    "shared_breakline_constraint_snap_count",
    "shared_breakline_constraint_snap_max_distance",
    "shared_breakline_constraint_snap_diagnostics",
    "patch_boundary_bbox_x",
    "patch_boundary_bbox_y",
    "patch_boundary_bbox_aspect_ratio",
    "patch_triangle_min_quality",
    "patch_triangle_skinny_count",
    "ordered_patch_boundary_point_count",
    "ordered_patch_boundary_source_segment_count",
    "ordered_patch_boundary_closed",
    "ordered_patch_boundary_diagnostic_count",
    "ordered_patch_boundary_polygon_area",
    "ordered_patch_boundary_self_crossing",
    "ordered_patch_boundary_ring_count",
    "ordered_patch_boundary_hole_ring_count",
    "ordered_patch_boundary_island_ring_count",
    "authoritative_boundary_loop_source",
    "authoritative_boundary_loop_point_count",
    "authoritative_boundary_loop_segment_count",
    "intersection_grading_mode",
    "intersection_grading_z_delta_max",
    "intersection_superelevation_source_count",
    "intersection_superelevation_transition_count",
    "intersection_superelevation_left_min",
    "intersection_superelevation_left_max",
    "intersection_superelevation_right_min",
    "intersection_superelevation_right_max",
    "intersection_superelevation_context",
    "intersection_low_point_candidate_count",
    "intersection_low_point_x",
    "intersection_low_point_y",
    "intersection_low_point_z",
    "intersection_low_point_source_ref",
    "intersection_boundary_to_low_flow_hint_count",
    "intersection_boundary_to_low_flow_hint_summary",
)


def _request():
    boundary = SimpleNamespace(
        boundary_source="authoritative_boundary_loop",
        patch_boundary_point_count=8,
        patch_boundary_source_segment_count=6,
        patch_boundary_closed=True,
        patch_boundary_diagnostic_count=2,
        patch_boundary_polygon_area=45.5,
        patch_boundary_self_crossing=False,
        patch_boundary_ring_count=2,
        patch_boundary_hole_ring_count=1,
        patch_boundary_island_ring_count=0,
        boundary_loop_source="intersection_boundary_loop",
        boundary_loop_point_count=9,
        boundary_loop_segment_count=8,
    )
    triangulation = SimpleNamespace(
        degenerate_count=1,
        max_edge_length=12.0,
        long_edge_count=2,
        long_edge_factor=2.5,
        long_edge_limit=10.0,
        max_boundary_edge_length_policy=10.0,
        boundary_strategy="structured_strip_curb_return_blend",
        structured_strip_count=2,
        curb_return_surface_edge_count=2,
        curb_return_arc_count=2,
        curb_return_arc_sample_count=5,
        curb_return_arc_segment_count=8,
        edge_blend_face_count=8,
        boundary_role_summary="pavement_tie_in=2; stem_tie_in=2",
        pavement_tie_in_edge_count=2,
        stem_tie_in_edge_count=2,
        overlap_cut_edge_count=1,
        curb_return_edge_count=2,
    )
    constraint = SimpleNamespace(
        mode="support_triangle_edge_preservation",
        segment_count=4,
        edge_count=3,
        inserted_vertex_count=2,
        boundary_loop_segment_count=2,
        boundary_loop_edge_count=2,
        boundary_loop_refs=("loop:b", "", "loop:a", "loop:b"),
        boundary_loop_role_summary="outer=2",
        snap_count=1,
        snap_max_distance=0.02,
        snap_diagnostic_rows=("snap:v1", "snap:v2"),
    )
    return IntersectionPatchTinAssemblyRequest(
        project_id="project:test",
        surface_id="surface:test",
        intersection_id="intersection:test",
        corridor_id="corridor:test",
        applied_section_set_id="sections:test",
        source_control_region_refs=("region:z", "region:a"),
        evaluated_control_region_refs=("region:z", "region:a"),
        participating_alignment_count=2,
        control_region_count=2,
        tie_in_edge_count=4,
        boundary_vertex_count=9,
        vertex_rows=(
            TINVertex("v1", 0.0, 0.0, 10.0),
            TINVertex("v2", 1.0, 0.0, 10.0),
            TINVertex("v3", 0.0, 1.0, 10.0),
        ),
        triangle_rows=(TINTriangle("t1", "v1", "v2", "v3"),),
        boundary_selection=boundary,
        triangulation=triangulation,
        constraint_build=constraint,
        grading_result=SimpleNamespace(
            grading_mode="blend_primary_side",
            max_z_delta=0.4,
        ),
        superelevation_context=SimpleNamespace(
            source_count=1,
            transition_count=2,
            left_min=-3.0,
            left_max=-1.0,
            right_min=1.0,
            right_max=4.0,
            summary="superelevation:test",
        ),
        drainage_review=SimpleNamespace(
            low_point_candidate_count=2,
            low_point_x=1.0,
            low_point_y=2.0,
            low_point_z=9.5,
            low_point_source_ref="source:low",
            flow_hint_count=3,
            flow_hint_summary="boundary_to_low count=3",
        ),
        shape_quality=SimpleNamespace(
            triangulation_mode="structured_strip_curb_return_blend",
            bbox_x=20.0,
            bbox_y=10.0,
            bbox_aspect_ratio=2.0,
            triangle_min_quality=0.25,
            skinny_triangle_count=1,
        ),
    )


def test_tin_assembly_preserves_identity_quality_order_and_provenance() -> None:
    request = _request()

    result = IntersectionPatchTinAssemblyService().build(request)
    surface = result.tin_surface

    assert isinstance(result, IntersectionPatchTinAssemblyResult)
    assert result.status == "ready"
    assert surface is not None
    assert surface.project_id == "project:test"
    assert surface.surface_id == "surface:test"
    assert surface.surface_kind == "intersection_surface"
    assert surface.label == "Intersection Surface - intersection:test"
    assert surface.source_refs == [
        "sections:test",
        "intersection:test",
        "region:z",
        "region:a",
    ]
    assert surface.vertex_rows == list(request.vertex_rows)
    assert surface.triangle_rows == list(request.triangle_rows)
    assert surface.boundary_refs == ["surface:test:boundary"]
    assert tuple(row.kind for row in surface.quality_rows) == EXPECTED_QUALITY_KINDS
    assert result.quality_row_count == len(EXPECTED_QUALITY_KINDS) == 69
    assert all(
        row.quality_id == f"surface:test:{row.kind}"
        for row in surface.quality_rows
    )
    values = {row.kind: row.value for row in surface.quality_rows}
    units = {row.kind: row.unit for row in surface.quality_rows}
    assert values["shared_breakline_boundary_loop_constraint_refs"] == (
        "loop:b,loop:a"
    )
    assert values["shared_breakline_constraint_snap_diagnostics"] == (
        "snap:v1; snap:v2"
    )
    assert values["ordered_patch_boundary_closed"] == 1
    assert values["ordered_patch_boundary_self_crossing"] == 0
    assert values["intersection_grading_mode"] == "blend_primary_side"
    assert values["intersection_low_point_source_ref"] == "source:low"
    assert units["ordered_patch_boundary_polygon_area"] == "m2"
    assert units["intersection_superelevation_left_min"] == "%"
    assert result.provenance_row_count == 1
    assert surface.provenance_rows[0].source_ref == "sections:test"
    assert surface.provenance_rows[0].notes == (
        "intersection=intersection:test; "
        "control_regions=region:a,region:z"
    )


def test_tin_assembly_returns_typed_error_for_invalid_result_contract() -> None:
    request = _request()
    invalid = IntersectionPatchTinAssemblyRequest(
        **{
            **request.__dict__,
            "shape_quality": SimpleNamespace(),
        }
    )

    result = IntersectionPatchTinAssemblyService().build(invalid)

    assert result.status == "error"
    assert result.tin_surface is None
    assert result.error_message == (
        "'types.SimpleNamespace' object has no attribute 'triangulation_mode'"
    )
    assert result.diagnostic_rows == (
        "intersection_patch_tin_assembly_failed:AttributeError:"
        "'types.SimpleNamespace' object has no attribute 'triangulation_mode'",
    )


def test_command_non_roundabout_builder_delegates_preparation_pipeline() -> None:
    source = inspect.getsource(
        cmd_build_corridor._build_intersection_surface_patch_tin
    )

    assert "IntersectionPatchPreparationPipelineService(" in source
    assert "IntersectionPatchPreparationPipelineRequest(" in source
    assert "return TINSurface(" not in source
