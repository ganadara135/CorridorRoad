from __future__ import annotations

from freecad.Corridor_Road.v1.services.geometry import (
    xy_closed_edges,
    xy_point_in_polygon,
    xy_point_in_polygon_strict,
    xy_point_on_segment,
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


def test_concave_polygon_point_in_polygon_is_deterministic() -> None:
    concave = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (2.0, 2.0), (0.0, 4.0)]

    assert xy_point_in_polygon((1.0, 2.0), concave)
    assert not xy_point_in_polygon((2.0, 3.0), concave)
