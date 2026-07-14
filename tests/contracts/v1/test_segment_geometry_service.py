from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.geometry import (
    clip_polyline_points_to_anchor_window,
    clip_segment_to_anchor_box,
    xy_point_segment_distance_with_ratio,
    xy_segment_distance,
    xy_segment_parameter_clamped,
    xy_segment_projection_ratio,
    xy_segments_cross_strict,
    xy_segments_intersect,
    xyz_segment_intersection_point,
)


def test_anchor_window_clipping_keeps_two_point_contract_and_interpolates_z() -> None:
    clipped = clip_polyline_points_to_anchor_window(
        [(0.0, 0.0, 0.0), (20.0, 0.0, 20.0)],
        (10.0, 0.0, 10.0),
        half_length=5.0 * (2.0 ** 0.5),
    )
    assert [tuple(round(value, 9) for value in point) for point in clipped] == [
        (5.0, 0.0, 5.0),
        (15.0, 0.0, 15.0),
    ]
    assert clip_polyline_points_to_anchor_window(
        [(1.0, 2.0, 3.0)],
        (0.0, 0.0, 0.0),
        half_length=2.0,
    ) == [(1.0, 2.0, 3.0)]


def test_anchor_box_clipping_handles_crossing_outside_and_z_interpolation() -> None:
    assert clip_segment_to_anchor_box(
        [(-5.0, 0.0, 0.0), (5.0, 0.0, 10.0)],
        (0.0, 0.0, 0.0),
        half_extent=2.0,
    ) == [(-2.0, 0.0, 3.0), (2.0, 0.0, 7.0)]
    assert clip_segment_to_anchor_box(
        [(5.0, 5.0, 0.0), (8.0, 5.0, 3.0)],
        (0.0, 0.0, 0.0),
        half_extent=2.0,
    ) == []


def test_build_corridor_anchor_clip_wrappers_match_geometry_service() -> None:
    points = [(-5.0, 0.0, 0.0), (5.0, 0.0, 10.0)]
    anchor = (0.0, 0.0, 0.0)
    assert cmd_build_corridor._clip_segment_to_anchor_box(
        points,
        anchor,
        half_extent=2.0,
    ) == clip_segment_to_anchor_box(points, anchor, half_extent=2.0)


def test_segment_intersection_distinguishes_cross_touch_collinear_and_disjoint() -> None:
    assert xy_segments_intersect((0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0)) is True
    assert xy_segments_intersect((0.0, 0.0), (2.0, 0.0), (2.0, 0.0), (4.0, 0.0)) is True
    assert xy_segments_intersect((0.0, 0.0), (3.0, 0.0), (1.0, 0.0), (4.0, 0.0)) is True
    assert xy_segments_intersect((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)) is False


def test_strict_segment_crossing_excludes_endpoint_and_collinear_touch() -> None:
    assert xy_segments_cross_strict((0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0)) is True
    assert xy_segments_cross_strict((0.0, 0.0), (2.0, 0.0), (2.0, 0.0), (2.0, 2.0)) is False
    assert xy_segments_cross_strict((0.0, 0.0), (3.0, 0.0), (1.0, 0.0), (4.0, 0.0)) is False


def test_point_segment_distance_keeps_unclamped_projection_ratio() -> None:
    assert xy_point_segment_distance_with_ratio((2.0, 3.0), (0.0, 0.0), (4.0, 0.0)) == (3.0, 0.5)
    assert xy_point_segment_distance_with_ratio((6.0, 0.0), (0.0, 0.0), (4.0, 0.0)) == (2.0, 1.5)
    assert xy_point_segment_distance_with_ratio((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)) == (5.0, 0.0)
    assert xy_segment_projection_ratio((-2.0, 0.0), (0.0, 0.0), (4.0, 0.0)) == -0.5


def test_segment_distance_handles_crossing_parallel_and_zero_length() -> None:
    assert xy_segment_distance((0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0)) == 0.0
    assert xy_segment_distance((0.0, 0.0), (4.0, 0.0), (0.0, 3.0), (4.0, 3.0)) == 3.0
    assert xy_segment_distance((0.0, 0.0), (0.0, 0.0), (3.0, 4.0), (3.0, 4.0)) == 5.0


def test_clamped_segment_parameter_handles_inside_outside_and_zero_length() -> None:
    assert xy_segment_parameter_clamped((2.0, 3.0), (0.0, 0.0), (4.0, 0.0)) == 0.5
    assert xy_segment_parameter_clamped((-2.0, 0.0), (0.0, 0.0), (4.0, 0.0)) == 0.0
    assert xy_segment_parameter_clamped((6.0, 0.0), (0.0, 0.0), (4.0, 0.0)) == 1.0
    assert xy_segment_parameter_clamped((6.0, 0.0), (1.0, 1.0), (1.0, 1.0)) == 0.0


def test_xyz_segment_intersection_interpolates_and_averages_z() -> None:
    result = xyz_segment_intersection_point(
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 10.0),
        (5.0, -5.0, 20.0),
        (5.0, 5.0, 40.0),
    )

    assert result == (5.0, 0.0, 17.5)


def test_xyz_segment_intersection_includes_endpoint_and_rejects_infinite_lines() -> None:
    assert xyz_segment_intersection_point(
        (0.0, 0.0, 2.0),
        (10.0, 0.0, 12.0),
        (10.0, 0.0, 30.0),
        (10.0, 5.0, 40.0),
    ) == (10.0, 0.0, 21.0)
    assert xyz_segment_intersection_point(
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 1.0),
        (2.0, -1.0, 2.0),
        (2.0, 1.0, 3.0),
    ) is None


def test_xyz_segment_intersection_rejects_parallel_collinear_and_zero_length() -> None:
    assert xyz_segment_intersection_point(
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 4.0),
        (0.0, 1.0, 5.0),
        (4.0, 1.0, 9.0),
    ) is None
    assert xyz_segment_intersection_point(
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 4.0),
        (2.0, 0.0, 8.0),
        (6.0, 0.0, 12.0),
    ) is None
    assert xyz_segment_intersection_point(
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, -1.0, 1.0),
        (0.0, 1.0, 2.0),
    ) is None


def test_build_corridor_segment_and_simple_triangulation_wrappers_match_services() -> None:
    polygon = [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)]

    assert cmd_build_corridor._xy_segments_intersect(
        (0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0)
    ) is True
    assert cmd_build_corridor._xy_segments_cross_strict(
        (0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0)
    ) is True
    assert cmd_build_corridor._xy_segment_distance(
        (0.0, 0.0), (4.0, 0.0), (0.0, 3.0), (4.0, 3.0)
    ) == 3.0
    assert cmd_build_corridor._xy_segment_parameter(
        (6.0, 0.0), (0.0, 0.0), (4.0, 0.0)
    ) == 1.0
    assert cmd_build_corridor._xy_segment_intersection_point(
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 10.0),
        (5.0, -5.0, 20.0),
        (5.0, 5.0, 40.0),
    ) == (5.0, 0.0, 17.5)
    assert cmd_build_corridor._xy_triangulate_simple_polygon_points(polygon) == [
        [(0.0, 3.0), (0.0, 0.0), (4.0, 0.0)],
        [(4.0, 0.0), (4.0, 3.0), (0.0, 3.0)],
    ]
