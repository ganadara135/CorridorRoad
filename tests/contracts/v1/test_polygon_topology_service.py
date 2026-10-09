from __future__ import annotations


from freecad.Corridor_Road.v1.services.geometry import (
    xy_polygon_boundaries_intersect,
    xy_polygon_self_intersects,
)


def test_polygon_self_intersection_excludes_adjacent_and_closing_edge_pairs() -> None:
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]
    concave = [(0.0, 0.0), (4.0, 0.0), (2.0, 2.0), (4.0, 4.0), (0.0, 4.0)]

    assert not xy_polygon_self_intersects(square)
    assert not xy_polygon_self_intersects(concave)


def test_polygon_self_intersection_detects_cross_touch_and_collinear_overlap() -> None:
    crossing = [(0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0)]
    nonadjacent_touch = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (2.0, 0.0), (0.0, 4.0)]
    collinear_overlap = [
        (0.0, 0.0),
        (4.0, 0.0),
        (4.0, 4.0),
        (1.0, 0.0),
        (3.0, 0.0),
        (0.0, 4.0),
    ]

    assert xy_polygon_self_intersects(crossing)
    assert xy_polygon_self_intersects(nonadjacent_touch)
    assert xy_polygon_self_intersects(collinear_overlap)


def test_polygon_self_intersection_preserves_short_and_closed_input_behavior() -> None:
    explicitly_closed_square = [
        (0.0, 0.0),
        (4.0, 0.0),
        (4.0, 4.0),
        (0.0, 4.0),
        (0.0, 0.0),
    ]

    assert not xy_polygon_self_intersects([])
    assert not xy_polygon_self_intersects([(0.0, 0.0), (1.0, 0.0)])
    assert not xy_polygon_self_intersects([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    assert xy_polygon_self_intersects(explicitly_closed_square)


def test_polygon_boundary_intersection_distinguishes_containment_touch_and_overlap() -> None:
    outer = [(0.0, 0.0), (6.0, 0.0), (6.0, 6.0), (0.0, 6.0)]
    contained = [(1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)]
    disjoint = [(7.0, 1.0), (8.0, 1.0), (8.0, 2.0), (7.0, 2.0)]
    endpoint_touch = [(6.0, 6.0), (7.0, 6.0), (7.0, 7.0), (6.0, 7.0)]
    edge_overlap = [(2.0, 0.0), (4.0, 0.0), (4.0, -1.0), (2.0, -1.0)]

    assert not xy_polygon_boundaries_intersect(outer, contained)
    assert not xy_polygon_boundaries_intersect(outer, disjoint)
    assert xy_polygon_boundaries_intersect(outer, endpoint_touch)
    assert xy_polygon_boundaries_intersect(outer, edge_overlap)
    assert not xy_polygon_boundaries_intersect(outer[:1], contained)
