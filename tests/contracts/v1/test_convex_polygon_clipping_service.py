from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.geometry import (
    intersect_payload_polygon_with_convex_polygon,
    subtract_convex_polygon_from_payload_polygon,
    xy_polygon_is_convex,
    xy_polygon_signed_area,
)


def _payload(points):
    return [
        {"x": float(x), "y": float(y), "z": float(index * 10), "source": f"p{index}"}
        for index, (x, y) in enumerate(points)
    ]


def _area(points) -> float:
    return abs(xy_polygon_signed_area([(row["x"], row["y"]) for row in points]))


def test_convex_polygon_classification_supports_winding_and_rejects_concavity() -> None:
    square = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]

    assert xy_polygon_is_convex(square) is True
    assert xy_polygon_is_convex(list(reversed(square))) is True
    assert xy_polygon_is_convex([(0.0, 0.0), (4.0, 0.0), (2.0, 1.0), (4.0, 4.0), (0.0, 4.0)]) is False


def test_convex_intersection_handles_containment_partial_overlap_and_disjoint() -> None:
    source = _payload([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])

    contained = intersect_payload_polygon_with_convex_polygon(source, [(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)])
    partial = intersect_payload_polygon_with_convex_polygon(source, [(2.0, -1.0), (5.0, -1.0), (5.0, 2.0), (2.0, 2.0)])
    disjoint = intersect_payload_polygon_with_convex_polygon(source, [(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)])

    assert _area(contained) == 4.0
    assert _area(partial) == 4.0
    assert disjoint == []
    assert any(":intersection" in str(row["source"]) for row in partial)


def test_convex_intersection_is_winding_independent_and_interpolates_z() -> None:
    source = _payload([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])
    clip = [(2.0, -1.0), (5.0, -1.0), (5.0, 2.0), (2.0, 2.0)]

    forward = intersect_payload_polygon_with_convex_polygon(source, clip)
    reversed_clip = intersect_payload_polygon_with_convex_polygon(source, list(reversed(clip)))

    assert _area(forward) == _area(reversed_clip) == 4.0
    assert sorted(round(float(row["z"]), 6) for row in forward) == sorted(
        round(float(row["z"]), 6) for row in reversed_clip
    )


def test_convex_intersection_boundary_touch_has_no_area_polygon() -> None:
    source = _payload([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])
    touching = [(4.0, 1.0), (6.0, 1.0), (6.0, 3.0), (4.0, 3.0)]

    assert intersect_payload_polygon_with_convex_polygon(source, touching) == []


def test_convex_subtraction_handles_containment_partial_overlap_and_disjoint() -> None:
    source = _payload([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])

    contained = subtract_convex_polygon_from_payload_polygon(source, [(-1.0, -1.0), (5.0, -1.0), (5.0, 5.0), (-1.0, 5.0)])
    partial = subtract_convex_polygon_from_payload_polygon(source, [(2.0, -1.0), (5.0, -1.0), (5.0, 5.0), (2.0, 5.0)])
    disjoint = subtract_convex_polygon_from_payload_polygon(source, [(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)])

    assert contained == []
    assert sum(_area(fragment) for fragment in partial) == 8.0
    assert sum(_area(fragment) for fragment in disjoint) == 16.0


def test_build_corridor_convex_clipping_wrappers_match_geometry_service() -> None:
    source = _payload([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])
    clip = [(2.0, -1.0), (5.0, -1.0), (5.0, 2.0), (2.0, 2.0)]

    assert cmd_build_corridor._xy_polygon_is_convex(clip) is True
    assert cmd_build_corridor._xy_intersect_polygon_with_convex_polygon(
        source, clip
    ) == intersect_payload_polygon_with_convex_polygon(source, clip)
    assert cmd_build_corridor._xy_subtract_convex_polygon_from_polygon(
        source, clip
    ) == subtract_convex_polygon_from_payload_polygon(source, clip)
