from __future__ import annotations

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.geometry import (
    xy_polygon_signed_area,
    xyz_exterior_convex_hull,
    xyz_ordered_outer_boundary_from_segments,
    xyz_point,
    xyz_polygon_union_outer_boundary,
)


def test_xyz_point_normalizes_short_and_numeric_sequences() -> None:
    assert xyz_point(None) == (0.0, 0.0, 0.0)
    assert xyz_point((2,)) == (2.0, 0.0, 0.0)
    assert xyz_point((2, 3)) == (2.0, 3.0, 0.0)
    assert xyz_point((2, 3, 4, 5)) == (2.0, 3.0, 4.0)


def test_xyz_exterior_hull_removes_interior_and_edge_collinear_points() -> None:
    polygon = [
        (0.0, 0.0, 10.0),
        (2.0, 0.0, 15.0),
        (4.0, 0.0, 20.0),
        (4.0, 4.0, 30.0),
        (2.0, 2.0, 50.0),
        (0.0, 4.0, 40.0),
    ]

    assert xyz_exterior_convex_hull([polygon]) == [
        (0.0, 0.0, 10.0),
        (4.0, 0.0, 20.0),
        (4.0, 4.0, 30.0),
        (0.0, 4.0, 40.0),
    ]


def test_xyz_exterior_hull_preserves_first_z_for_six_decimal_xy_identity() -> None:
    first = [
        (0.0000001, 0.0, 10.0),
        (4.0, 0.0, 20.0),
        (4.0, 4.0, 30.0),
        (0.0, 4.0, 40.0),
    ]
    duplicate = [(0.0000004, 0.0, 99.0)]

    hull = xyz_exterior_convex_hull([first, duplicate])

    assert hull[0] == (0.0000001, 0.0, 10.0)
    assert all(point[2] != 99.0 for point in hull)


def test_xyz_exterior_hull_is_ccw_and_rejects_degenerate_inputs() -> None:
    clockwise = [
        (0.0, 0.0, 0.0),
        (0.0, 4.0, 4.0),
        (4.0, 4.0, 8.0),
        (4.0, 0.0, 4.0),
    ]

    hull = xyz_exterior_convex_hull([clockwise])

    assert xy_polygon_signed_area(hull) > 0.0
    assert xyz_exterior_convex_hull([]) == []
    assert xyz_exterior_convex_hull([clockwise[:2]]) == []
    assert xyz_exterior_convex_hull(
        [[(0.0, 0.0, 0.0), (1.0, 0.0, 1.0), (2.0, 0.0, 2.0)]]
    ) == []


def test_xyz_exterior_hull_preserves_turn_tolerance_and_command_wrappers() -> None:
    polygon = [
        (0.0, 0.0, 0.0),
        (1.0, -0.0000000005, 1.0),
        (2.0, 0.0, 2.0),
        (2.0, 2.0, 4.0),
        (0.0, 2.0, 2.0),
    ]

    hull = xyz_exterior_convex_hull([polygon])

    assert (1.0, -0.0000000005, 1.0) not in hull
    assert cmd_build_corridor._xy_polygon_exterior_hull_boundary([polygon]) == hull
    assert cmd_build_corridor._xyz_tuple((2, 3)) == (2.0, 3.0, 0.0)
    assert cmd_build_corridor._xy_area_from_xyz_points(hull) == xy_polygon_signed_area(hull)


def test_xyz_polygon_union_returns_single_polygon_boundary_ccw() -> None:
    square = [
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 0.0),
        (4.0, 4.0, 0.0),
        (0.0, 4.0, 0.0),
    ]

    boundary = xyz_polygon_union_outer_boundary([square])

    assert set(boundary) == set(square)
    assert xy_polygon_signed_area(boundary) == 16.0


def test_xyz_polygon_union_splits_intersections_and_averages_source_z() -> None:
    first = [
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 0.0),
        (4.0, 4.0, 0.0),
        (0.0, 4.0, 0.0),
    ]
    second = [
        (2.0, -1.0, 10.0),
        (5.0, -1.0, 10.0),
        (5.0, 3.0, 10.0),
        (2.0, 3.0, 10.0),
    ]

    boundary = xyz_polygon_union_outer_boundary([first, second])

    assert xy_polygon_signed_area(boundary) == 22.0
    assert (2.0, 0.0, 5.0) in boundary
    assert (4.0, 3.0, 5.0) in boundary
    assert (4.0, 0.0, 0.0) not in boundary
    assert (2.0, 3.0, 10.0) not in boundary


def test_xyz_polygon_union_excludes_contained_boundary_by_strict_midpoint() -> None:
    outer = [
        (0.0, 0.0, 0.0),
        (6.0, 0.0, 0.0),
        (6.0, 6.0, 0.0),
        (0.0, 6.0, 0.0),
    ]
    inner = [
        (1.0, 1.0, 5.0),
        (2.0, 1.0, 5.0),
        (2.0, 2.0, 5.0),
        (1.0, 2.0, 5.0),
    ]

    boundary = xyz_polygon_union_outer_boundary([outer, inner])

    assert set(boundary) == set(outer)
    assert xy_polygon_signed_area(boundary) == 36.0


def test_ordered_outer_boundary_deduplicates_edges_and_selects_largest_ring() -> None:
    large = [
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 0.0),
        (4.0, 4.0, 0.0),
        (0.0, 4.0, 0.0),
    ]
    small = [
        (10.0, 10.0, 1.0),
        (11.0, 10.0, 1.0),
        (11.0, 11.0, 1.0),
        (10.0, 11.0, 1.0),
    ]
    segments = [
        *((large[index], large[(index + 1) % 4]) for index in range(4)),
        *((small[index], small[(index + 1) % 4]) for index in range(4)),
        (large[1], large[0]),
        (large[0], (0.0000004, 0.0, 9.0)),
    ]

    boundary = xyz_ordered_outer_boundary_from_segments(segments)

    assert set(boundary) == set(large)
    assert xy_polygon_signed_area(boundary) == 16.0


def test_polygon_union_command_wrappers_match_geometry_service() -> None:
    square = [
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 0.0),
        (4.0, 4.0, 0.0),
        (0.0, 4.0, 0.0),
    ]
    segments = [
        (square[index], square[(index + 1) % 4]) for index in range(4)
    ]

    assert cmd_build_corridor._xy_polygon_union_outer_boundary(
        [square]
    ) == xyz_polygon_union_outer_boundary([square])
    assert cmd_build_corridor._ordered_outer_boundary_from_segments(
        segments
    ) == xyz_ordered_outer_boundary_from_segments(segments)
