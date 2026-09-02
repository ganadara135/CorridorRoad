from dataclasses import dataclass

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.geometry import (
    xy_distance,
    xy_point,
    xy_point_in_triangle_strict,
    xy_polygon_signed_area,
    xy_triangle_signed_area,
)


@dataclass(frozen=True)
class _Point:
    x: float
    y: float


def test_xy_point_and_distance_accept_objects_and_sequences() -> None:
    assert xy_point(_Point(3.0, 4.0)) == (3.0, 4.0)
    assert xy_point((6.0, 8.0, 10.0)) == (6.0, 8.0)
    assert xy_point(None) == (0.0, 0.0)
    assert xy_distance(_Point(0.0, 0.0), (3.0, 4.0)) == 5.0


def test_xy_triangle_signed_area_preserves_orientation() -> None:
    assert xy_triangle_signed_area((0.0, 0.0), (4.0, 0.0), (0.0, 3.0)) == 6.0
    assert xy_triangle_signed_area((0.0, 0.0), (0.0, 3.0), (4.0, 0.0)) == -6.0


def test_xy_point_in_triangle_is_strict_at_edges_and_degenerate_rows() -> None:
    triangle = ((0.0, 0.0), (4.0, 0.0), (0.0, 4.0))

    assert xy_point_in_triangle_strict((1.0, 1.0), triangle) is True
    assert xy_point_in_triangle_strict((2.0, 0.0), triangle) is False
    assert xy_point_in_triangle_strict((3.0, 3.0), triangle) is False
    assert xy_point_in_triangle_strict((0.0, 0.0), ((0.0, 0.0), (1.0, 1.0), (2.0, 2.0))) is False


def test_xy_polygon_signed_area_supports_both_orientations() -> None:
    counter_clockwise = [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)]

    assert xy_polygon_signed_area(counter_clockwise) == 12.0
    assert xy_polygon_signed_area(tuple(reversed(counter_clockwise))) == -12.0
    assert xy_polygon_signed_area([(0.0, 0.0), (1.0, 1.0)]) == 0.0


def test_build_corridor_xy_compatibility_wrappers_use_geometry_service_results() -> None:
    vertices = [_Point(0.0, 0.0), _Point(4.0, 0.0), _Point(0.0, 3.0)]

    assert cmd_build_corridor._xy_point_tuple(vertices[1]) == xy_point(vertices[1])
    assert cmd_build_corridor._xy_distance((0.0, 0.0), (3.0, 4.0)) == 5.0
    assert cmd_build_corridor._xy_triangle_area(*vertices) == 6.0
    assert cmd_build_corridor._xy_polygon_signed_area(vertices) == 6.0
    assert cmd_build_corridor._xy_point_in_triangle(
        (1.0, 1.0),
        ((0.0, 0.0), (4.0, 0.0), (0.0, 3.0)),
    ) is True
