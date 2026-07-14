from __future__ import annotations

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.geometry import (
    xy_closed_edges,
    xy_point_in_polygon,
    xy_point_in_polygon_strict,
    xy_point_on_segment,
    xy_triangle_intersects_polygon,
    xy_triangle_polygon_intersection_kind,
)


def test_closed_edges_preserve_order_closure_and_short_inputs() -> None:
    points = [(0.0, 0.0), (2.0, 0.0), (1.0, 1.0)]

    assert xy_closed_edges([]) == []
    assert xy_closed_edges(points[:1]) == []
    assert xy_closed_edges(points) == [
        (points[0], points[1]),
        (points[1], points[2]),
        (points[2], points[0]),
    ]


def test_point_in_polygon_preserves_inside_outside_and_legacy_boundary_result() -> None:
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]

    assert xy_point_in_polygon((2.0, 2.0), square)
    assert not xy_point_in_polygon((5.0, 2.0), square)
    assert xy_point_in_polygon((0.0, 2.0), square)
    assert not xy_point_in_polygon((4.0, 2.0), square)
    assert not xy_point_in_polygon((0.0, 0.0), square[:2])


def test_strict_point_in_polygon_excludes_every_boundary_side() -> None:
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]

    assert xy_point_in_polygon_strict((2.0, 2.0), square)
    assert not xy_point_in_polygon_strict((0.0, 2.0), square)
    assert not xy_point_in_polygon_strict((4.0, 2.0), square)
    assert not xy_point_in_polygon_strict((0.0, 0.0), square)


def test_point_on_segment_preserves_tolerance_and_zero_length_behavior() -> None:
    assert xy_point_on_segment((1.0, 0.0), (0.0, 0.0), (2.0, 0.0))
    assert xy_point_on_segment((1.0, 5.0e-7), (0.0, 0.0), (2.0, 0.0))
    assert not xy_point_on_segment((1.0, 2.0e-6), (0.0, 0.0), (2.0, 0.0))
    assert xy_point_on_segment((1.0, 1.0), (1.0, 1.0), (1.0, 1.0))


def test_concave_polygon_and_triangle_relation_kinds_are_deterministic() -> None:
    concave = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (2.0, 2.0), (0.0, 4.0)]
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]

    assert xy_point_in_polygon((1.0, 2.0), concave)
    assert not xy_point_in_polygon((2.0, 3.0), concave)
    assert xy_triangle_polygon_intersection_kind(
        [(-1.0, 1.0), (1.0, 1.0), (0.0, 2.0)], square
    ) == "edge_crossing"
    assert xy_triangle_polygon_intersection_kind(
        [(1.0, 1.0), (3.0, 1.0), (2.0, 3.0)], square
    ) == "centroid_inside"
    assert xy_triangle_polygon_intersection_kind(
        [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)],
        [(1.0, 1.0), (2.0, 1.0), (1.0, 2.0)],
    ) == "polygon_vertex_inside_triangle"


def test_triangle_relation_handles_touch_disjoint_degenerate_and_wrappers() -> None:
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]
    touching = [(-2.0, -1.0), (0.0, 0.0), (-1.0, 1.0)]
    disjoint = [(5.0, 5.0), (6.0, 5.0), (5.0, 6.0)]

    assert xy_triangle_polygon_intersection_kind(touching, square) == "edge_crossing"
    assert xy_triangle_intersects_polygon(touching, square)
    assert xy_triangle_polygon_intersection_kind(disjoint, square) == ""
    assert not xy_triangle_intersects_polygon(disjoint, square)
    assert xy_triangle_polygon_intersection_kind(disjoint[:2], square) == ""
    assert cmd_build_corridor._xy_closed_edges(square) == xy_closed_edges(square)
    assert cmd_build_corridor._xy_point_in_polygon((2.0, 2.0), square)
    assert not cmd_build_corridor._xy_point_in_polygon_strict((0.0, 2.0), square)
    assert cmd_build_corridor._xy_triangle_polygon_intersection_kind(
        touching, square
    ) == "edge_crossing"
    assert cmd_build_corridor._xy_triangle_intersects_polygon(touching, square)
    assert cmd_build_corridor._xy_polygon_area(square) == 16.0
