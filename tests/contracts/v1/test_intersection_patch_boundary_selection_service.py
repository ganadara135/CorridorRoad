from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchBoundarySelectionResult,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINVertex
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchBoundarySelectionRequest,
    IntersectionPatchBoundarySelectionService,
)


def _vertex(vertex_id: str, x: float, y: float, z: float):
    return TINVertex(
        vertex_id,
        x,
        y,
        z,
        source_point_ref=f"source:{vertex_id}",
        notes=f"notes:{vertex_id}",
    )


def _patch(*, closed: bool = True, points: list[object] | None = None):
    rows = points or [
        SimpleNamespace(
            boundary_point_id="patch:1",
            x=0.0,
            y=0.0,
            z=7.0,
            source_segment_ref="segment:1",
            source_kind="tie_in_edge",
        ),
        SimpleNamespace(
            boundary_point_id="patch:2",
            x=4.0,
            y=0.0,
            z=8.0,
            source_segment_ref="segment:2",
            source_kind="curb_return",
        ),
        SimpleNamespace(
            boundary_point_id="patch:3",
            x=0.0,
            y=4.0,
            z=9.0,
            source_segment_ref="segment:3",
            source_kind="tie_in_edge",
        ),
    ]
    return SimpleNamespace(
        boundary_point_count=len(rows),
        source_segment_count=3,
        closed=closed,
        point_rows=rows,
        diagnostic_rows=("patch-note",),
        polygon_area=8.0,
        self_crossing=False,
        ring_count=2,
        hole_ring_count=1,
        island_ring_count=0,
    )


def _loop(
    loop_id: str,
    area: float,
    points: tuple[tuple[float, float, float], ...],
    *,
    status: str = "ready",
    closed: bool = True,
):
    return SimpleNamespace(
        loop_id=loop_id,
        loop_role="outer_intersection_boundary",
        status=status,
        closed=closed,
        area_xy=area,
        point_count=len(points),
        segment_count=max(0, len(points) - 1),
        loop_points_xyz=points,
    )


def test_selection_prefers_largest_ready_authoritative_loop() -> None:
    source = (
        _vertex("a", 0.0, 0.0, 10.0),
        _vertex("b", 5.0, 0.0, 11.0),
        _vertex("c", 0.0, 5.0, 12.0),
    )
    small = _loop("loop:small", 4.0, ((0, 0, 1), (2, 0, 1), (0, 2, 1), (0, 0, 1)))
    large = _loop("loop:large", 12.5, ((0, 0, 1), (5, 0, 1), (0, 5, 1), (0, 0, 1)))

    result = IntersectionPatchBoundarySelectionService().select(
        IntersectionPatchBoundarySelectionRequest(
            source_vertices=source,
            patch_boundary_result=_patch(),
            boundary_loop_result=SimpleNamespace(loop_rows=[small, large]),
        )
    )

    assert isinstance(result, IntersectionPatchBoundarySelectionResult)
    assert result.status == "ready"
    assert result.boundary_source == "authoritative_boundary_loop"
    assert result.boundary_loop_source == "intersection_boundary_loop"
    assert result.boundary_loop_point_count == 4
    assert result.boundary_loop_segment_count == 3
    assert len(result.vertex_rows) == 3
    assert result.vertex_rows[0].source_point_ref == "loop:large:point:01"
    assert "authoritative_boundary_loop; loop=loop:large" in result.vertex_rows[0].notes


def test_selection_uses_ordered_patch_and_preserves_patch_metrics() -> None:
    source = (
        _vertex("a", 0.0, 0.0, 10.0),
        _vertex("b", 4.0, 0.0, 11.0),
        _vertex("c", 0.0, 4.0, 12.0),
    )

    result = IntersectionPatchBoundarySelectionService().select(
        IntersectionPatchBoundarySelectionRequest(
            source_vertices=source,
            patch_boundary_result=_patch(),
        )
    )

    assert result.status == "ready"
    assert result.boundary_source == "ordered_patch_boundary"
    assert [row.z for row in result.vertex_rows] == [10.0, 11.0, 12.0]
    assert "source_segment=segment:1" in result.vertex_rows[0].notes
    assert "elevation_source=source:a" in result.vertex_rows[0].notes
    assert result.patch_boundary_point_count == 3
    assert result.patch_boundary_source_segment_count == 3
    assert result.patch_boundary_closed is True
    assert result.patch_boundary_diagnostic_count == 1
    assert result.patch_boundary_polygon_area == 8.0
    assert result.patch_boundary_ring_count == 2
    assert result.patch_boundary_hole_ring_count == 1


def test_selection_grading_plane_overrides_boundary_elevation() -> None:
    result = IntersectionPatchBoundarySelectionService().select(
        IntersectionPatchBoundarySelectionRequest(
            source_vertices=(
                _vertex("a", 0.0, 0.0, 100.0),
                _vertex("b", 4.0, 0.0, 100.0),
                _vertex("c", 0.0, 4.0, 100.0),
            ),
            patch_boundary_result=_patch(),
            grading_plane=(1.0, 2.0, 3.0),
            grading_mode="blend_primary_side",
        )
    )

    assert [row.z for row in result.vertex_rows] == [3.0, 7.0, 11.0]
    assert all(
        "elevation_source=intersection_grading_plane" in row.notes
        and "blend_basis=primary_side_plane" in row.notes
        for row in result.vertex_rows
    )


def test_authoritative_loop_preserves_zero_nearest_elevation_fallback() -> None:
    loop = _loop(
        "loop:zero",
        8.0,
        ((0.0, 0.0, 7.0), (4.0, 0.0, 8.0), (0.0, 4.0, 9.0), (0.0, 0.0, 7.0)),
    )
    source = (
        _vertex("a", 0.0, 0.0, 0.0),
        _vertex("b", 4.0, 0.0, 0.0),
        _vertex("c", 0.0, 4.0, 0.0),
    )

    rows = IntersectionPatchBoundarySelectionService().boundary_loop_vertices(
        loop,
        source_vertices=list(source),
    )

    assert [row.z for row in rows] == [7.0, 8.0, 9.0]
    assert len(rows) == 3


def test_selection_falls_back_to_convex_hull_and_keeps_source_objects() -> None:
    outer = [
        _vertex("a", 0.0, 0.0, 1.0),
        _vertex("b", 4.0, 0.0, 2.0),
        _vertex("c", 4.0, 4.0, 3.0),
        _vertex("d", 0.0, 4.0, 4.0),
    ]
    interior = _vertex("inside", 2.0, 2.0, 99.0)

    result = IntersectionPatchBoundarySelectionService().select(
        IntersectionPatchBoundarySelectionRequest(
            source_vertices=tuple([*outer, interior]),
            patch_boundary_result=_patch(closed=False),
            boundary_evaluation_failed=True,
        )
    )

    assert result.status == "ready"
    assert result.boundary_source == "convex_hull_fallback"
    assert result.fallback_used is True
    assert result.vertex_rows == tuple(outer)
    assert interior not in result.vertex_rows
    assert result.patch_boundary_diagnostic_count == 1
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_fallback:convex_hull_fallback",
    )


def test_selection_returns_typed_error_for_too_few_unique_points() -> None:
    result = IntersectionPatchBoundarySelectionService().select(
        IntersectionPatchBoundarySelectionRequest(
            source_vertices=(
                _vertex("a", 0.0, 0.0, 1.0),
                _vertex("duplicate", 0.0, 0.0, 2.0),
                _vertex("b", 1.0, 0.0, 3.0),
            )
        )
    )

    assert result.status == "error"
    assert len(result.vertex_rows) == 2
    assert result.error_message == (
        "intersection_patch_boundary_too_few_points: at least three unique "
        "patch boundary points are required."
    )
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_too_few_points",
    )
