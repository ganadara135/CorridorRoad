import math
from dataclasses import dataclass

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.geometry import (
    ear_clip_triangulation_indices,
    xy_polygon_signed_area,
    xy_triangle_quality_ratio,
    xy_triangle_signed_area,
)


@dataclass(frozen=True)
class _Vertex:
    x: float
    y: float


def _triangulated_area(vertices, indices) -> float:
    return sum(abs(xy_triangle_signed_area(*(vertices[index] for index in row))) for row in indices)


def test_ear_clip_triangulates_both_polygon_windings_deterministically() -> None:
    counter_clockwise = [_Vertex(0.0, 0.0), _Vertex(4.0, 0.0), _Vertex(4.0, 3.0), _Vertex(0.0, 3.0)]
    clockwise = list(reversed(counter_clockwise))

    ccw_indices = ear_clip_triangulation_indices(counter_clockwise)
    cw_indices = ear_clip_triangulation_indices(clockwise)

    assert ccw_indices == [(3, 0, 1), (1, 2, 3)]
    assert cw_indices == [(0, 3, 2), (2, 1, 0)]
    assert _triangulated_area(counter_clockwise, ccw_indices) == 12.0
    assert _triangulated_area(clockwise, cw_indices) == 12.0


def test_ear_clip_preserves_concave_polygon_area() -> None:
    vertices = [
        _Vertex(0.0, 0.0),
        _Vertex(4.0, 0.0),
        _Vertex(4.0, 4.0),
        _Vertex(2.0, 1.5),
        _Vertex(0.0, 4.0),
    ]

    indices = ear_clip_triangulation_indices(vertices)

    assert len(indices) == 3
    assert _triangulated_area(vertices, indices) == abs(xy_polygon_signed_area(vertices))


def test_ear_clip_rejects_degenerate_polygon() -> None:
    assert ear_clip_triangulation_indices([]) == []
    assert ear_clip_triangulation_indices([_Vertex(0.0, 0.0), _Vertex(1.0, 1.0)]) == []
    assert ear_clip_triangulation_indices(
        [_Vertex(0.0, 0.0), _Vertex(1.0, 1.0), _Vertex(2.0, 2.0)]
    ) == []


def test_triangle_quality_distinguishes_equilateral_skinny_and_degenerate() -> None:
    equilateral = xy_triangle_quality_ratio((0.0, 0.0), (1.0, 0.0), (0.5, math.sqrt(3.0) * 0.5))
    skinny = xy_triangle_quality_ratio((0.0, 0.0), (100.0, 0.0), (50.0, 0.01))
    degenerate = xy_triangle_quality_ratio((0.0, 0.0), (1.0, 1.0), (2.0, 2.0))

    assert abs(equilateral - 1.0) <= 1.0e-12
    assert 0.0 < skinny < 0.08
    assert degenerate == 0.0


def test_build_corridor_triangulation_wrappers_match_geometry_service() -> None:
    vertices = [_Vertex(0.0, 0.0), _Vertex(4.0, 0.0), _Vertex(4.0, 3.0), _Vertex(0.0, 3.0)]

    assert cmd_build_corridor._intersection_patch_ear_clip_indices(vertices) == ear_clip_triangulation_indices(vertices)
    assert cmd_build_corridor._xy_triangle_quality_ratio(*vertices[:3]) == xy_triangle_quality_ratio(*vertices[:3])
