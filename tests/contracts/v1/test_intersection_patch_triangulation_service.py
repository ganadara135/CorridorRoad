from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchTriangulationResult,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchTriangulationRequest,
    IntersectionPatchTriangulationService,
)


def _vertices():
    boundary = (
        TINVertex("v1", 0.0, 0.0, 10.0),
        TINVertex("v2", 4.0, 0.0, 11.0),
        TINVertex("v3", 0.0, 4.0, 12.0),
    )
    center = TINVertex("v:center", 4.0 / 3.0, 4.0 / 3.0, 11.0)
    return boundary, center


def _triangle(quality_ref: str = "ordered_polygon"):
    return TINTriangle("t1", "v1", "v2", "v3", quality_ref=quality_ref)


def _request(boundary_source: str = "ordered_patch_boundary"):
    boundary, center = _vertices()
    return IntersectionPatchTriangulationRequest(
        boundary_source=boundary_source,
        boundary_vertices=boundary,
        center_vertex=center,
        intersection_id="intersection:test",
        policy={"long_edge_factor": 3.0, "max_boundary_edge_length": 8.0},
        tie_in_result=SimpleNamespace(result_id="tie-in:test"),
        intersection_model=SimpleNamespace(model_id="intersection-model:test"),
        boundary_segment_result=SimpleNamespace(result_id="boundary:test"),
    )


def test_authoritative_boundary_routes_directly_to_ordered_polygon() -> None:
    calls = []

    def ordered(vertices, center, **kwargs):
        calls.append((vertices, center, kwargs))
        return {
            "triangles": [_triangle()],
            "degenerate_count": 2,
            "max_edge_length": 4.0,
            "long_edge_count": 1,
            "long_edge_factor": 3.0,
            "long_edge_limit": 8.0,
            "max_boundary_edge_length_policy": 8.0,
            "boundary_strategy": "ordered_polygon",
        }

    def structured(*args, **kwargs):
        raise AssertionError("authoritative boundary must skip structured strips")

    request = _request("authoritative_boundary_loop")
    result = IntersectionPatchTriangulationService(
        ordered_polygon_builder=ordered,
        structured_strip_builder=structured,
    ).triangulate(request)

    assert isinstance(result, IntersectionPatchTriangulationResult)
    assert result.status == "ready"
    assert result.selection_path == "ordered_polygon_authoritative"
    assert result.vertex_rows == (*request.boundary_vertices, request.center_vertex)
    assert result.triangle_rows == (_triangle(),)
    assert result.degenerate_count == 2
    assert result.max_edge_length == 4.0
    assert result.long_edge_count == 1
    assert result.long_edge_factor == 3.0
    assert result.long_edge_limit == 8.0
    assert result.max_boundary_edge_length_policy == 8.0
    assert result.fallback_used is False
    assert len(calls) == 1
    assert calls[0][2] == {
        "intersection_id": "intersection:test",
        "policy": {
            "long_edge_factor": 3.0,
            "max_boundary_edge_length": 8.0,
        },
    }


def test_non_authoritative_boundary_prefers_structured_strip_and_metrics() -> None:
    request = _request()
    structured_vertices = tuple(reversed(request.boundary_vertices))

    def structured(tie_in_result, **kwargs):
        assert tie_in_result is request.tie_in_result
        assert kwargs["source_vertices"] == list(request.boundary_vertices)
        assert kwargs["center"] is request.center_vertex
        assert kwargs["intersection_model"] is request.intersection_model
        assert kwargs["boundary_segment_result"] is request.boundary_segment_result
        assert kwargs["intersection_id"] == "intersection:test"
        assert kwargs["policy"] == dict(request.policy)
        return {
            "vertices": structured_vertices,
            "triangles": [_triangle("structured_strip"), _triangle("curb_return_blend")],
            "boundary_strategy": "structured_strip_curb_return_blend",
            "structured_strip_count": 2,
            "curb_return_surface_edge_count": 2,
            "curb_return_arc_count": 2,
            "curb_return_arc_sample_count": 5,
            "curb_return_arc_segment_count": 8,
            "edge_blend_face_count": 6,
            "boundary_role_summary": "pavement_tie_in=2; stem_tie_in=2",
            "pavement_tie_in_edge_count": 2,
            "stem_tie_in_edge_count": 2,
            "overlap_cut_edge_count": 1,
            "curb_return_edge_count": 2,
        }

    result = IntersectionPatchTriangulationService(
        ordered_polygon_builder=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("structured result must not fall back")
        ),
        structured_strip_builder=structured,
    ).triangulate(request)

    assert result.status == "ready"
    assert result.selection_path == "structured_strip"
    assert result.vertex_rows == structured_vertices
    assert len(result.triangle_rows) == 2
    assert result.boundary_strategy == "structured_strip_curb_return_blend"
    assert result.structured_strip_count == 2
    assert result.curb_return_surface_edge_count == 2
    assert result.curb_return_arc_count == 2
    assert result.curb_return_arc_sample_count == 5
    assert result.curb_return_arc_segment_count == 8
    assert result.edge_blend_face_count == 6
    assert result.pavement_tie_in_edge_count == 2
    assert result.stem_tie_in_edge_count == 2
    assert result.overlap_cut_edge_count == 1
    assert result.curb_return_edge_count == 2


def test_empty_structured_result_falls_back_to_ordered_polygon() -> None:
    calls = []

    def ordered(*args, **kwargs):
        calls.append("ordered")
        return {"triangles": [_triangle()]}

    result = IntersectionPatchTriangulationService(
        ordered_polygon_builder=ordered,
        structured_strip_builder=lambda *args, **kwargs: {"triangles": []},
    ).triangulate(_request())

    assert calls == ["ordered"]
    assert result.status == "ready"
    assert result.selection_path == "ordered_polygon_fallback"
    assert result.fallback_used is True
    assert result.diagnostic_rows == (
        "intersection_patch_triangulation_fallback:ordered_polygon",
    )


def test_empty_final_result_preserves_degenerate_error_contract() -> None:
    result = IntersectionPatchTriangulationService(
        ordered_polygon_builder=lambda *args, **kwargs: {"triangles": []},
        structured_strip_builder=lambda *args, **kwargs: {"triangles": []},
    ).triangulate(_request())

    assert result.status == "error"
    assert result.selection_path == "ordered_polygon_fallback"
    assert result.fallback_used is True
    assert result.error_message == (
        "intersection_patch_degenerate_triangle: ordered patch boundary did "
        "not produce usable triangles."
    )
    assert result.diagnostic_rows == (
        "intersection_patch_degenerate_triangle",
    )


def test_default_service_uses_internal_structured_builder_then_ordered_fallback() -> None:
    result = IntersectionPatchTriangulationService().triangulate(_request())

    assert result.status == "ready"
    assert result.selection_path == "ordered_polygon_fallback"
    assert result.fallback_used is True
    assert result.diagnostic_rows == (
        "intersection_patch_triangulation_fallback:ordered_polygon",
    )


def test_builder_exception_is_normalized_without_losing_message() -> None:
    def ordered(*args, **kwargs):
        raise RuntimeError("triangulation exploded")

    result = IntersectionPatchTriangulationService(
        ordered_polygon_builder=ordered,
        structured_strip_builder=lambda *args, **kwargs: {"triangles": []},
    ).triangulate(_request())

    assert result.status == "error"
    assert result.error_message == "triangulation exploded"
    assert result.diagnostic_rows == (
        "intersection_patch_triangulation_failed:RuntimeError:triangulation exploded",
    )


def test_internal_ordered_polygon_uses_ear_clipping_with_stable_trace_rows() -> None:
    vertices = [
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 4.0, 0.0, 0.0),
        TINVertex("v3", 4.0, 4.0, 0.0),
        TINVertex("v4", 0.0, 4.0, 0.0),
    ]
    center = TINVertex("v:center", 2.0, 2.0, 0.0)

    result = IntersectionPatchTriangulationService().ordered_polygon_triangulation(
        vertices,
        center,
        intersection_id="intersection:test",
    )

    assert [
        (row.triangle_id, row.v1, row.v2, row.v3)
        for row in result["triangles"]
    ] == [
        ("t1", "v4", "v1", "v2"),
        ("t2", "v2", "v3", "v4"),
    ]
    assert all(
        row.triangle_kind == "intersection_surface_patch"
        and row.quality_ref == "ordered_polygon"
        and row.notes == "intersection=intersection:test; area=8.000000"
        for row in result["triangles"]
    )
    assert result["degenerate_count"] == 0
    assert result["max_edge_length"] == 4.0
    assert result["long_edge_factor"] == 2.5
    assert result["long_edge_limit"] == 10.0


def test_internal_ordered_polygon_preserves_centroid_fan_fallback() -> None:
    vertices = [
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 2.0, 0.0, 0.0),
        TINVertex("v3", 4.0, 0.0, 0.0),
    ]
    center = TINVertex("v:center", 2.0, 2.0, 0.0)

    result = IntersectionPatchTriangulationService().ordered_polygon_triangulation(
        vertices,
        center,
        intersection_id="intersection:test",
    )

    assert len(result["triangles"]) == 3
    assert [row.triangle_id for row in result["triangles"]] == ["t1", "t2", "t3"]
    assert all(
        row.v1 == "v:center" and row.quality_ref == "ordered_fan_fallback"
        for row in result["triangles"]
    )
    assert [row.notes for row in result["triangles"]] == [
        "intersection=intersection:test; area=2.000000",
        "intersection=intersection:test; area=2.000000",
        "intersection=intersection:test; area=4.000000",
    ]


def test_internal_ordered_polygon_counts_degenerate_fan_triangles() -> None:
    vertices = [
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 2.0, 0.0, 0.0),
        TINVertex("v3", 4.0, 0.0, 0.0),
    ]
    center = TINVertex("v:center", 2.0, 0.0, 0.0)

    result = IntersectionPatchTriangulationService().ordered_polygon_triangulation(
        vertices,
        center,
        intersection_id="intersection:test",
    )

    assert result["triangles"] == []
    assert result["degenerate_count"] == 3


def test_default_service_uses_internal_ordered_builder_for_authoritative_loop() -> None:
    result = IntersectionPatchTriangulationService().triangulate(
        _request("authoritative_boundary_loop")
    )

    assert result.status == "ready"
    assert result.selection_path == "ordered_polygon_authoritative"
    assert len(result.triangle_rows) == 1
    assert result.triangle_rows[0].quality_ref == "ordered_polygon"
    assert result.max_edge_length > 0.0


def _structured_tie_in_result():
    def edge(edge_id, alignment, side, start, end):
        return SimpleNamespace(
            tie_in_edge_id=edge_id,
            alignment_ref=alignment,
            side=side,
            start_xyz=start,
            end_xyz=end,
        )

    return SimpleNamespace(
        edge_rows=[
            edge("primary:left", "alignment:primary", "left", (0, 5, 10), (40, 5, 10)),
            edge("primary:right", "alignment:primary", "right", (0, -5, 10), (40, -5, 10)),
            edge("side:left", "alignment:side", "left", (16, -24, 10), (16, 0, 10)),
            edge("side:right", "alignment:side", "right", (24, -24, 10), (24, 0, 10)),
        ]
    )


def test_internal_structured_strip_preserves_roles_policy_and_source_elevation() -> None:
    source_vertices = [
        TINVertex(
            "source:primary-left",
            0.0,
            5.0,
            77.0,
            source_point_ref="section:primary:left",
        )
    ]
    model = SimpleNamespace(
        intersection_rows=[
            SimpleNamespace(
                intersection_id="intersection:test",
                primary_alignment_ref="alignment:primary",
            )
        ]
    )

    result = IntersectionPatchTriangulationService().structured_strip_triangulation(
        _structured_tie_in_result(),
        source_vertices=source_vertices,
        center=TINVertex("v:center", 20.0, -4.0, 10.0),
        intersection_model=model,
        intersection_id="intersection:test",
        policy={"max_boundary_edge_length": 10.0, "long_edge_factor": 2.5},
    )

    assert len(result["triangles"]) >= 4
    assert result["boundary_strategy"] == "structured_strip_union"
    assert result["structured_strip_count"] == 2
    assert result["pavement_tie_in_edge_count"] == 2
    assert result["stem_tie_in_edge_count"] == 2
    assert result["overlap_cut_edge_count"] == 1
    assert result["curb_return_edge_count"] == 0
    assert result["boundary_role_summary"] == (
        "pavement_tie_in=2; stem_tie_in=2; overlap_cut=1; curb_return=0"
    )
    assert result["long_edge_limit"] == 10.0
    primary_left = next(
        row
        for row in result["vertices"]
        if row.x == 0.0 and row.y == 5.0
    )
    assert primary_left.z == 77.0
    assert primary_left.source_point_ref == "intersection:test:structured-strip:4"
    assert primary_left.notes == "intersection structured strip triangulation"


def test_internal_structured_strip_returns_policy_aware_empty_contract() -> None:
    one_alignment = SimpleNamespace(
        edge_rows=_structured_tie_in_result().edge_rows[:2]
    )
    center = TINVertex("v:center", 0.0, 0.0, 0.0)

    result = IntersectionPatchTriangulationService().structured_strip_triangulation(
        one_alignment,
        source_vertices=[],
        center=center,
        intersection_id="intersection:test",
        policy={"long_edge_factor": 0.5, "max_boundary_edge_length": 9.0},
    )

    assert result["vertices"] == [center]
    assert result["triangles"] == []
    assert result["boundary_strategy"] == "ordered_polygon"
    assert result["long_edge_factor"] == 1.0
    assert result["max_boundary_edge_length_policy"] == 9.0
