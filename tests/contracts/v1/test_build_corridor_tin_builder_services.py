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
