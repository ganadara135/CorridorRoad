import math
from dataclasses import dataclass

from freecad.Corridor_Road.v1.services.geometry import (
    delaunay_flip_triangulation_indices,
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


def _boundary_edges(indices) -> set:
    counts = {}
    for row in indices:
        for first, second in ((row[0], row[1]), (row[1], row[2]), (row[2], row[0])):
            key = (min(first, second), max(first, second))
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count == 1}


def _minimum_quality(vertices, indices) -> float:
    return min(xy_triangle_quality_ratio(*(vertices[index] for index in row)) for row in indices)


def test_delaunay_flip_improves_a_thin_ear_clip_without_changing_the_polygon() -> None:
    # a long thin ellipse: the ear clip leaves slivers across it
    vertices = [
        _Vertex(15.0 * math.cos(2.0 * math.pi * index / 24.0), 3.0 * math.sin(2.0 * math.pi * index / 24.0))
        for index in range(24)
    ]
    clipped = ear_clip_triangulation_indices(vertices)
    flipped = delaunay_flip_triangulation_indices(vertices, clipped)

    assert len(flipped) == len(clipped)
    assert math.isclose(_triangulated_area(vertices, flipped), _triangulated_area(vertices, clipped), rel_tol=1.0e-12)
    assert _boundary_edges(flipped) == _boundary_edges(clipped)
    assert all(xy_triangle_signed_area(*(vertices[index] for index in row)) > 0.0 for row in flipped)
    assert _minimum_quality(vertices, flipped) > _minimum_quality(vertices, clipped)
    assert delaunay_flip_triangulation_indices(vertices, clipped) == flipped


def test_delaunay_flip_keeps_a_triangulation_that_is_already_delaunay() -> None:
    square = [_Vertex(0.0, 0.0), _Vertex(4.0, 0.0), _Vertex(4.0, 4.0), _Vertex(0.0, 4.0)]
    clipped = ear_clip_triangulation_indices(square)
    assert delaunay_flip_triangulation_indices(square, clipped) == clipped
    assert delaunay_flip_triangulation_indices(square, []) == []


def test_delaunay_flip_never_leaves_a_concave_polygon() -> None:
    # an L shape: the diagonal across the reflex corner would leave the polygon and must stay
    vertices = [
        _Vertex(0.0, 0.0), _Vertex(6.0, 0.0), _Vertex(6.0, 2.0), _Vertex(2.0, 2.0), _Vertex(2.0, 6.0), _Vertex(0.0, 6.0),
    ]
    clipped = ear_clip_triangulation_indices(vertices)
    flipped = delaunay_flip_triangulation_indices(vertices, clipped)
    assert math.isclose(_triangulated_area(vertices, flipped), xy_polygon_signed_area(vertices), rel_tol=1.0e-12)
    assert _boundary_edges(flipped) == _boundary_edges(clipped)
