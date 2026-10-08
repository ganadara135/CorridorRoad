"""The roundabout in the parametric intersection kernel (plan phase R6).

The starter ring: 12 m inscribed radius, 6.6 m circulatory roadway (central island 5.4 m), 0.99 m
outer apron, so the paved outer edge is a circle of 12.99 m. Two straight roads 10 m wide cross at
its centre. Each corner runs from one approach's flare onto the ring, round the ring, and off it
by the next approach's flare.
"""

import math

import pytest

from freecad.Corridor_Road.v1.models.source.intersection_spec import (
    IntersectionSpec,
    LegOverride,
    RoundaboutSpec,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_kernel import build_intersection_geometry

from test_intersection_kernel import _context, _road, _rotate

OUTER = 12.99
ISLAND = 5.4


def _roundabout(*, ring=None, turn=0.0, overrides=(), slope_width=4.0):
    context = _context(
        _road("ns", _rotate([(0.0, -130.0), (0.0, 130.0)], turn), crossfall=0.02, slope_width=slope_width),
        _road("ew", _rotate([(-130.0, 0.0), (130.0, 0.0)], turn), crossfall=0.02, slope_width=slope_width),
    )
    spec = IntersectionSpec("r", "roundabout", ("ns", "ew"), roundabout=ring or RoundaboutSpec(12.0, 6.6, 0.99), leg_overrides=tuple(overrides))
    return build_intersection_geometry(spec, context)


def _radius(point):
    return math.hypot(point[0], point[1])


def _quality(result, name):
    return dict(result.quality_rows)[name]


def _values(result, name):
    return {v.subject: (v.value, v.origin) for v in result.resolved_values if v.name == name}


def test_a_roundabout_has_four_ring_corners_an_island_and_no_skinny_triangle() -> None:
    result = _roundabout()
    assert result.status == "ready", result.diagnostics
    assert len(result.legs) == 4 and all(c.treatment == "ring" for c in result.corners)
    (island,) = result.boundary_holes_xyz
    assert all(_radius(p) == pytest.approx(ISLAND) for p in island)
    vertices = result.patch_vertices_xyz
    area = sum(
        abs((vertices[b][0] - vertices[a][0]) * (vertices[c][1] - vertices[a][1]) - (vertices[b][1] - vertices[a][1]) * (vertices[c][0] - vertices[a][0])) / 2.0
        for a, b, c in result.patch_triangles
    )
    assert area == pytest.approx(result.boundary_area_m2, rel=1.0e-9)
    assert _quality(result, "patch_triangle_skinny_count") == 0
    # no triangle covers the island
    for a, b, c in result.patch_triangles:
        centroid = [sum(vertices[i][k] for i in (a, b, c)) / 3.0 for k in (0, 1)]
        assert _radius(centroid) > ISLAND - 1.0e-9


def test_the_flares_are_tangent_to_the_pavement_edge_and_to_the_ring() -> None:
    result = _roundabout()
    entry = OUTER * 0.5
    exit_ = OUTER * 0.6
    # from the anchor along each approach the entry flare (left, looking outward) meets the edge at
    # x where its centre, w + R from the centreline, is r + R from the ring centre
    expected_entry = math.sqrt((OUTER + entry) ** 2 - (5.0 + entry) ** 2)
    expected_exit = math.sqrt((OUTER + exit_) ** 2 - (5.0 + exit_) ** 2)
    for leg in result.legs:
        assert abs(leg.mouth_station - 130.0) == pytest.approx(max(expected_entry, expected_exit), abs=1.0e-6)
    values = _values(result, "flare_radius_m")
    assert {round(v[0], 6) for v in values.values()} == {round(entry, 6), round(exit_, 6)}
    assert {v[1] for v in values.values()} == {"constant"}


def test_the_ring_falls_outward_and_the_mouths_keep_the_corridor_heights() -> None:
    result = _roundabout()
    outer_z = 10.0 - 0.02 * (OUTER - ISLAND)
    (island,) = result.boundary_holes_xyz
    assert all(p[2] == pytest.approx(10.0) for p in island)
    ring = [p for p in result.boundary_xyz if _radius(p) == pytest.approx(OUTER, abs=1.0e-6)]
    assert ring and all(p[2] == pytest.approx(outer_z) for p in ring)
    # at the mouth of ns ahead (y = mouth - 130), the edges are 10 cm below the 10 m crown
    mouth = next(leg for leg in result.legs if leg.leg_id == "ns:ahead")
    assert mouth.mouth_left_xyz[2] == pytest.approx(9.9) and mouth.mouth_right_xyz[2] == pytest.approx(9.9)


def test_the_side_slope_runs_round_the_flares_and_out_from_the_ring() -> None:
    result = _roundabout()
    assert _quality(result, "slope_vertex_without_daylight_count") == 0
    toes = [points for role, _subject, points in result.breaklines if role == "slope_toe"]
    assert len(toes) == 4
    # beyond the ring the toe is the slope width further out
    ring_toe = [p for points in toes for p in points if _radius(p) == pytest.approx(OUTER + 4.0, abs=1.0e-6)]
    assert ring_toe and all(p[2] == pytest.approx(10.0 - 0.02 * (OUTER - ISLAND) - 2.0) for p in ring_toe)


def test_clockwise_circulation_swaps_the_entry_and_exit_flares() -> None:
    ccw = _values(_roundabout(), "flare_radius_m")
    cw = _values(_roundabout(ring=RoundaboutSpec(12.0, 6.6, 0.99, circulation="cw")), "flare_radius_m")
    for key, (value, _origin) in ccw.items():
        other = key.replace(":from", ":tmp").replace(":to", ":from").replace(":tmp", ":to")
        assert cw[key][0] == pytest.approx(ccw[other][0]) or value == pytest.approx(cw[key][0])
    assert {round(v[0], 6) for v in cw.values()} == {round(v[0], 6) for v in ccw.values()}
    assert any(cw[k][0] != pytest.approx(ccw[k][0]) for k in ccw)


def test_one_approach_can_carry_its_own_entry_radius() -> None:
    result = _roundabout(overrides=[LegOverride("ns", "ahead", entry_radius_m=6.0)])
    values = _values(result, "flare_radius_m")
    overridden = [v for v in values.values() if v[1] == "override"]
    assert len(overridden) == 1 and overridden[0][0] == 6.0
    assert result.status == "ready"


def test_flares_too_large_for_the_ring_block() -> None:
    result = _roundabout(ring=RoundaboutSpec(12.0, 6.6, 0.99, entry_radius_m=15.0, exit_radius_m=20.0))
    assert result.status == "blocked"
    assert "roundabout_flares_overlap" in {row.code for row in result.diagnostics}


def test_the_roundabout_turns_with_its_roads() -> None:
    straight, turned = _roundabout(), _roundabout(turn=30.0)
    assert turned.status == "ready"
    assert turned.boundary_area_m2 == pytest.approx(straight.boundary_area_m2, rel=1.0e-9)
    assert _quality(turned, "patch_triangle_count") == _quality(straight, "patch_triangle_count")
