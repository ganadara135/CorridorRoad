from freecad.Corridor_Road.v1.models.result.intersection_slope_face_loop import (
    IntersectionSlopeFaceLoopResult,
    IntersectionSlopeFaceLoopRow,
)
from freecad.Corridor_Road.v1.models.result.shared_breakline import (
    SharedBreaklinePointRow,
    SharedBreaklineResult,
    SharedBreaklineRow,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINSurface,
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.services.builders.intersection_daylight_tin_service import (
    suppress_daylight_triangles_above_intersection_surface,
)
from freecad.Corridor_Road.v1.services.builders.intersection_slope_face_tin_builder_service import (
    build_intersection_slope_face_surface_from_ready_loops,
)
from freecad.Corridor_Road.v1.services.builders.intersection_tin_clip_service import (
    clip_tin_surface_by_intersection_exclusion,
)
from freecad.Corridor_Road.v1.services.builders.roundabout_tin_clip_service import (
    clip_tin_surface_by_roundabout_ownership,
)
from freecad.Corridor_Road.v1.services.builders.shared_breakline_tin_builder_service import (
    tin_surface_with_shared_breakline_constraint_edges,
)


def _surface(surface_id: str, rows, triangles) -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="project:test",
        surface_id=surface_id,
        surface_kind="daylight_surface",
        vertex_rows=list(rows),
        triangle_rows=list(triangles),
    )


def test_daylight_height_suppression_service_consumes_typed_tin_results() -> None:
    reference = _surface(
        "surface:reference",
        [TINVertex("r1", 0, 0, 10), TINVertex("r2", 10, 0, 10), TINVertex("r3", 0, 10, 10)],
        [TINTriangle("reference", "r1", "r2", "r3")],
    )
    daylight = _surface(
        "surface:daylight",
        [
            TINVertex("a1", 1, 1, 11),
            TINVertex("a2", 2, 1, 11),
            TINVertex("a3", 1, 2, 11),
            TINVertex("b1", 20, 20, 11),
            TINVertex("b2", 21, 20, 11),
            TINVertex("b3", 20, 21, 11),
        ],
        [TINTriangle("above", "a1", "a2", "a3"), TINTriangle("outside", "b1", "b2", "b3")],
    )

    result = suppress_daylight_triangles_above_intersection_surface(daylight, reference)

    assert [row.triangle_id for row in result.triangle_rows] == ["outside"]


def test_intersection_exclusion_service_applies_daylight_protection_contract() -> None:
    surface = _surface(
        "surface:daylight",
        [
            TINVertex("n1", 2.8, 0.2, 0),
            TINVertex("n2", 3.8, 0.2, 0),
            TINVertex("n3", 2.8, 1.2, 0),
            TINVertex("o1", 20, 20, 0),
            TINVertex("o2", 21, 20, 0),
            TINVertex("o3", 20, 21, 0),
        ],
        [TINTriangle("near", "n1", "n2", "n3"), TINTriangle("outside", "o1", "o2", "o3")],
    )

    result = clip_tin_surface_by_intersection_exclusion(
        surface,
        exclusion={"points": [(0, 0), (2, 0), (0, 2)], "area": 2.0},
        surface_role="daylight",
    )

    assert [row.triangle_id for row in result.triangle_rows] == ["outside"]


def test_shared_breakline_constraint_service_adds_only_missing_support_edge() -> None:
    breakline_id = "breakline:test"
    shared = SharedBreaklineResult(
        schema_version=1,
        project_id="project:test",
        breakline_result_id="breaklines:test",
        status="ready",
        breakline_rows=[
            SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="intersection",
                domain_ref="intersection:test",
                breakline_role="patch_to_design",
                consumer_refs=("intersection_surface",),
                point_refs=("p0", "p1"),
                source_status="ready",
            )
        ],
        point_rows=[
            SharedBreaklinePointRow("p0", breakline_id, 0, 0, 0, 0),
            SharedBreaklinePointRow("p1", breakline_id, 1, 10, 0, 0),
        ],
    )
    surface = _surface(
        "surface:intersection",
        [TINVertex("a", 0, 0, 0), TINVertex("b", 10, 0, 0), TINVertex("c", 5, 3, 0)],
        [TINTriangle("base", "a", "c", "b")],
    )

    result = tin_surface_with_shared_breakline_constraint_edges(
        surface,
        shared,
        consumer_ref="intersection_surface",
    )

    assert len(result.triangle_rows) == 1
    assert not [row for row in result.triangle_rows if row.quality_ref == "shared_breakline_constraint_edge"]


def test_roundabout_clip_and_slope_face_builder_are_freecad_independent() -> None:
    surface = _surface(
        "surface:roundabout",
        [
            TINVertex("i1", -0.5, -0.5, 0),
            TINVertex("i2", 0.5, -0.5, 0),
            TINVertex("i3", 0, 0.5, 0),
            TINVertex("o1", 10, 10, 0),
            TINVertex("o2", 11, 10, 0),
            TINVertex("o3", 10, 11, 0),
        ],
        [TINTriangle("inside", "i1", "i2", "i3"), TINTriangle("outside", "o1", "o2", "o3")],
    )
    clipped = clip_tin_surface_by_roundabout_ownership(
        surface,
        ownership_spec={"center": (0, 0, 0), "ownership_radius": 2.0},
        boundary_loop_result=None,
        surface_role="design_surface",
    )
    assert [row.triangle_id for row in clipped.triangle_rows] == ["outside"]

    loop_result = IntersectionSlopeFaceLoopResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="intersection:test",
        status="ready",
        loop_count=1,
        ready_count=1,
        loop_rows=[
            IntersectionSlopeFaceLoopRow(
                loop_id="loop:test",
                intersection_id="intersection:test",
                loop_family="primary_outside",
                loop_points_xyz=((0, 0, 0), (4, 0, 0), (4, 3, -1), (0, 3, -1), (0, 0, 0)),
                closed_xy=True,
                point_count=5,
                boundary_edge_refs=("curb-return-to-slope-face:test",),
                source_edge_network_refs=("edge:test",),
                source_surface_zone_refs=("zone:test",),
                surface_generation_role="surface_candidate",
                surface_generation_status="ready",
                status="ready",
            )
        ],
    )
    built = build_intersection_slope_face_surface_from_ready_loops(loop_result)
    assert built.surface_kind == "intersection_slope_face_surface"
    assert built.triangle_rows
