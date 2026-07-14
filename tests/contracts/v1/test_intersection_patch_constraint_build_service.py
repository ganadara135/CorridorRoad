from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchConstraintBuildResult,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchConstraintBuildRequest,
    IntersectionPatchConstraintBuildService,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINTriangle, TINVertex


def _request(shared_result=None):
    return IntersectionPatchConstraintBuildRequest(
        surface_id="surface:test",
        vertices=(SimpleNamespace(vertex_id="v1"),),
        triangles=(SimpleNamespace(triangle_id="t1"),),
        shared_breakline_result=shared_result,
    )


def test_constraint_service_forwards_request_and_normalizes_all_stats() -> None:
    shared = SimpleNamespace(result_id="shared:test")
    request = _request(shared)
    added_vertex = SimpleNamespace(vertex_id="v2")
    added_triangle = SimpleNamespace(triangle_id="t2")
    calls = []

    def builder(**kwargs):
        calls.append(kwargs)
        return (
            [*kwargs["vertices"], added_vertex],
            [*kwargs["triangles"], added_triangle],
            {
                "mode": "support_triangle_edge_preservation",
                "segment_count": 5,
                "edge_count": 4,
                "vertex_count": 3,
                "boundary_loop_segment_count": 2,
                "boundary_loop_edge_count": 1,
                "boundary_loop_refs": ["loop:b", "", "loop:a"],
                "boundary_loop_role_counts": {
                    "curb_return": 2,
                    "outer": 1,
                    "ignored": 0,
                },
                "snap_count": 2,
                "snap_max_distance": 0.025,
                "snap_diagnostics": ["snap:first", "", "snap:second"],
            },
        )

    result = IntersectionPatchConstraintBuildService(builder).build(request)

    assert isinstance(result, IntersectionPatchConstraintBuildResult)
    assert result.status == "ready"
    assert result.surface_id == "surface:test"
    assert result.vertex_rows == (*request.vertices, added_vertex)
    assert result.triangle_rows == (*request.triangles, added_triangle)
    assert result.mode == "support_triangle_edge_preservation"
    assert result.segment_count == 5
    assert result.edge_count == 4
    assert result.inserted_vertex_count == 3
    assert result.boundary_loop_segment_count == 2
    assert result.boundary_loop_edge_count == 1
    assert result.boundary_loop_refs == ("loop:b", "loop:a")
    assert result.boundary_loop_role_counts == (
        ("curb_return", 2),
        ("outer", 1),
    )
    assert result.boundary_loop_role_summary == "curb_return=2, outer=1"
    assert result.snap_count == 2
    assert result.snap_max_distance == 0.025
    assert result.snap_diagnostic_rows == ("snap:first", "snap:second")
    assert result.diagnostic_rows == ()
    assert calls == [
        {
            "vertices": list(request.vertices),
            "triangles": list(request.triangles),
            "shared_result": shared,
            "surface_id": "surface:test",
        }
    ]


def test_constraint_service_preserves_no_constraint_pass_through_defaults() -> None:
    request = _request()

    result = IntersectionPatchConstraintBuildService(
        lambda **kwargs: (kwargs["vertices"], kwargs["triangles"], {})
    ).build(request)

    assert result.status == "ready"
    assert result.vertex_rows == request.vertices
    assert result.triangle_rows == request.triangles
    assert result.mode == "none"
    assert result.segment_count == 0
    assert result.edge_count == 0
    assert result.inserted_vertex_count == 0
    assert result.boundary_loop_refs == ()
    assert result.boundary_loop_role_counts == ()
    assert result.boundary_loop_role_summary == ""
    assert result.snap_count == 0
    assert result.snap_max_distance == 0.0
    assert result.snap_diagnostic_rows == ()


def test_constraint_service_preserves_empty_builder_rows() -> None:
    result = IntersectionPatchConstraintBuildService(
        lambda **_kwargs: (None, None, None)
    ).build(_request())

    assert result.status == "ready"
    assert result.vertex_rows == ()
    assert result.triangle_rows == ()
    assert result.mode == "none"


def test_constraint_service_uses_internal_builder_by_default() -> None:
    request = _request()

    result = IntersectionPatchConstraintBuildService().build(request)

    assert result.status == "ready"
    assert result.vertex_rows == request.vertices
    assert result.triangle_rows == request.triangles
    assert result.mode == "none"
    assert result.segment_count == 0
    assert result.edge_count == 0
    assert result.diagnostic_rows == ()


def test_constraint_service_reports_failure_without_losing_input_rows() -> None:
    request = _request()

    def builder(**_kwargs):
        raise RuntimeError("constraint exploded")

    result = IntersectionPatchConstraintBuildService(builder).build(request)

    assert result.status == "error"
    assert result.vertex_rows == request.vertices
    assert result.triangle_rows == request.triangles
    assert result.error_message == "constraint exploded"
    assert result.diagnostic_rows == (
        "intersection_patch_constraint_build_failed:"
        "RuntimeError:constraint exploded",
    )


def test_internal_constraint_builder_inserts_traceable_support_triangle() -> None:
    breakline_id = "breakline:test"
    shared = SimpleNamespace(
        breakline_rows=[
            SimpleNamespace(
                breakline_id=breakline_id,
                breakline_role="patch_to_design",
                consumer_refs=("intersection_surface",),
                point_refs=("p0", "p1"),
                source_contract_refs=("intersection-boundary-loop:test",),
            )
        ],
        point_rows=[
            SimpleNamespace(
                point_id="p0",
                sequence=0,
                x=0.0,
                y=0.0,
                z=10.0,
                source_point_ref="source:p0",
            ),
            SimpleNamespace(
                point_id="p1",
                sequence=1,
                x=10.0,
                y=0.0,
                z=10.0,
                source_point_ref="source:p1",
            ),
        ],
    )
    result = IntersectionPatchConstraintBuildService().build(
        IntersectionPatchConstraintBuildRequest(
            surface_id="surface:test",
            vertices=(),
            triangles=(),
            shared_breakline_result=shared,
        )
    )

    assert result.status == "ready"
    assert result.mode == "support_triangle_edge_preservation"
    assert result.segment_count == 1
    assert result.edge_count == 1
    assert result.inserted_vertex_count == 3
    assert [row.vertex_id for row in result.vertex_rows] == [
        "surface:test:shared-breakline-point:1",
        "surface:test:shared-breakline-point:2",
        "surface:test:shared-breakline-support:3",
    ]
    assert result.vertex_rows[0].source_point_ref == "source:p0"
    assert result.vertex_rows[1].source_point_ref == "source:p1"
    assert result.vertex_rows[2].source_point_ref == breakline_id
    assert result.triangle_rows == (
        TINTriangle(
            triangle_id="surface:test:shared-breakline-constraint:1",
            v1="surface:test:shared-breakline-point:1",
            v2="surface:test:shared-breakline-point:2",
            v3="surface:test:shared-breakline-support:3",
            triangle_kind="constraint_support_triangle",
            quality_ref="shared_breakline_constraint_edge",
            notes="shared_breakline_ref=breakline:test",
        ),
    )
    assert result.boundary_loop_segment_count == 1
    assert result.boundary_loop_edge_count == 1
    assert result.boundary_loop_refs == (breakline_id,)
    assert result.boundary_loop_role_counts == (("patch_to_design", 1),)


def test_internal_constraint_builder_reuses_six_decimal_coordinate_edge() -> None:
    breakline_id = "breakline:existing"
    shared = SimpleNamespace(
        breakline_rows=[
            SimpleNamespace(
                breakline_id=breakline_id,
                consumer_refs=("intersection_surface",),
                point_refs=("p0", "p1"),
                source_contract_refs=(),
            )
        ],
        point_rows=[
            SimpleNamespace(point_id="p0", sequence=0, x=0.0000004, y=0, z=0),
            SimpleNamespace(point_id="p1", sequence=1, x=10.0000004, y=0, z=0),
        ],
    )
    vertices = (
        TINVertex("v1", 0.0, 0.0, 0.0),
        TINVertex("v2", 10.0, 0.0, 0.0),
        TINVertex("v3", 5.0, 2.0, 0.0),
    )
    triangles = (TINTriangle("t1", "v1", "v2", "v3"),)

    result = IntersectionPatchConstraintBuildService().build(
        IntersectionPatchConstraintBuildRequest(
            surface_id="surface:test",
            vertices=vertices,
            triangles=triangles,
            shared_breakline_result=shared,
        )
    )

    assert result.vertex_rows == vertices
    assert result.triangle_rows == triangles
    assert result.segment_count == 1
    assert result.edge_count == 1
    assert result.inserted_vertex_count == 0
    assert result.snap_count == 0
