"""The parametric intersection kernel on analytic roads (plan phases R1, R2 and R5).

No FreeCAD document takes part: the roads are plain polylines with pavement half widths, as
the Applied Sections would give them. Straight roads give exact results; the expected areas are
the paved band of each road plus the four (or two) corner pieces `R^2 (1 - pi / 4)`.
"""

import math

import pytest

from freecad.Corridor_Road.v1.models.source.intersection_spec import (
    AnchorSpec,
    CornerOverride,
    IntersectionSpec,
    LegOverride,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_kernel import (
    PolylineRoad,
    PolylineRoadContext,
    SurfaceProfile,
    build_intersection_geometry,
    intersection_input_fingerprint,
)


def _road(ref, points, *, left=5.0, right=5.0, z=10.0, widths=None, grade=0.0, z_station=0.0, crossfall=0.0, slope_width=4.0, slope_fall=2.0):
    """A road as the Applied Sections would give it: a section every 10 m with a crown at the
    centreline, `crossfall` down to both edges, and a side slope `slope_width` wide falling
    `slope_fall` beyond each edge. The centreline grade is `z + grade (station - z_station)`."""

    stations = [0.0]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        stations.append(stations[-1] + math.hypot(x1 - x0, y1 - y0))
    rows = widths if widths is not None else ((stations[0], left, right), (stations[-1], left, right))
    section_stations = sorted({*(s for s in range(0, int(stations[-1]) + 1, 10)), stations[-1]})
    profiles, grades = [], []
    for s in section_stations:
        zc = z + grade * (s - z_station)
        zl, zr = zc - crossfall * left, zc - crossfall * right
        profiles.append(
            SurfaceProfile(float(s), ((-right, zr), (0.0, zc), (left, zl)), (left + slope_width, zl - slope_fall), (-(right + slope_width), zr - slope_fall))
        )
        grades.append((float(s), zc))
    return PolylineRoad(ref, tuple(stations), tuple(points), tuple(rows), tuple(grades), profile_rows=tuple(profiles))


def _context(*roads):
    return PolylineRoadContext({road.road_ref: road for road in roads})


def _rotate(points, degrees):
    a = math.radians(degrees)
    return [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)) for x, y in points]


def _corner_piece(radius):
    return radius * radius * (1.0 - math.pi / 4.0)


def _starter_t(turn=0.0, **stem):
    return _context(
        _road("main", _rotate([(-120.0, 0.0), (120.0, 0.0)], turn)),
        _road("stem", _rotate([(0.0, -100.0), (0.0, 0.0)], turn), **stem),
    )


def _legs(result):
    return {leg.leg_id: leg for leg in result.legs}


def _corners(result):
    return {corner.corner_key: corner for corner in result.corners}


def _codes(result):
    return {row.code for row in result.diagnostics}


def test_a_starter_t_has_three_legs_two_fillets_and_the_exact_paved_area() -> None:
    result = build_intersection_geometry(IntersectionSpec("x1", "t", ("main", "stem")), _starter_t())
    assert result.status == "ready", result.diagnostics
    legs = _legs(result)
    # the side road ends at the anchor: it gives one leg, without any rule
    assert set(legs) == {"main:ahead", "main:back", "stem:back"}
    corners = _corners(result)
    assert corners["main:ahead|main:back"].treatment == "none"
    fillets = [c for c in corners.values() if c.treatment == "fillet"]
    assert len(fillets) == 2 and all(c.radius_m == 12.0 for c in fillets)
    # the fillet centre is 5 m (pavement) + 12 m (radius) from both centrelines
    assert {tuple(round(v, 6) for v in c.center_xy) for c in fillets} == {(17.0, -17.0), (-17.0, -17.0)}
    assert legs["main:ahead"].mouth_station == pytest.approx(137.0)
    assert legs["main:back"].mouth_station == pytest.approx(103.0)
    assert legs["stem:back"].mouth_station == pytest.approx(83.0)
    # main band 34 x 10, stem band 10 x 12, two corner pieces; the arc is a chord polygon
    expected = 34.0 * 10.0 + 10.0 * 12.0 + 2.0 * _corner_piece(12.0)
    assert result.boundary_area_m2 == pytest.approx(expected, abs=0.6)
    assert dict((ref, (start, end)) for ref, start, end in result.clip_spans) == {
        "main": pytest.approx((103.0, 137.0)),
        "stem": pytest.approx((83.0, 100.0)),
    }
    assert all(point[2] == 10.0 for point in result.boundary_xyz)


def test_a_cross_has_four_fillets_of_the_cross_radius() -> None:
    context = _context(
        _road("main", [(-120.0, 0.0), (120.0, 0.0)]),
        _road("cross", [(0.0, -120.0), (0.0, 120.0)]),
    )
    result = build_intersection_geometry(IntersectionSpec("x2", "cross", ("main", "cross")), context)
    assert result.status == "ready", result.diagnostics
    assert len(result.legs) == 4
    assert [c.treatment for c in result.corners] == ["fillet"] * 4
    assert all(c.radius_m == 10.0 for c in result.corners)
    expected = 30.0 * 10.0 * 2.0 - 10.0 * 10.0 + 4.0 * _corner_piece(10.0)
    assert result.boundary_area_m2 == pytest.approx(expected, abs=0.6)
    assert all(leg.mouth_station == pytest.approx(135.0 if leg.side == "ahead" else 105.0) for leg in result.legs)


def test_turning_the_roads_turns_the_result_and_keeps_its_measures() -> None:
    straight = build_intersection_geometry(IntersectionSpec("x1", "t", ("main", "stem")), _starter_t())
    turned = build_intersection_geometry(IntersectionSpec("x1", "t", ("main", "stem")), _starter_t(30.0))
    assert turned.status == "ready"
    assert turned.boundary_area_m2 == pytest.approx(straight.boundary_area_m2, abs=1.0e-6)
    for a, b in zip(sorted(straight.legs, key=lambda leg: leg.leg_id), sorted(turned.legs, key=lambda leg: leg.leg_id)):
        assert a.mouth_station == pytest.approx(b.mouth_station)
    centres = sorted(tuple(round(v, 6) for v in c.center_xy) for c in turned.corners if c.center_xy)
    assert centres == sorted(tuple(round(v, 6) for v in p) for p in _rotate([(17.0, -17.0), (-17.0, -17.0)], 30.0))


def test_the_t_rule_closes_the_shorter_side_of_a_side_road_that_crosses() -> None:
    context = _context(_road("main", [(-120.0, 0.0), (120.0, 0.0)]), _road("side", [(0.0, -100.0), (0.0, 40.0)]))
    result = build_intersection_geometry(IntersectionSpec("x3", "t", ("main", "side")), context)
    legs = _legs(result)
    assert legs["side:ahead"].enabled is False and legs["side:back"].enabled is True
    assert any(v.name == "leg_enabled" and v.subject == "side:ahead" and v.origin == "derived:t_rule" for v in result.resolved_values)
    assert result.status == "ready"
    # a leg override wins over the rule
    reopened = IntersectionSpec("x3", "t", ("main", "side"), leg_overrides=(LegOverride("side", "ahead", True), LegOverride("side", "back", False)))
    legs = _legs(build_intersection_geometry(reopened, context))
    assert legs["side:ahead"].enabled is True and legs["side:back"].enabled is False


def test_a_skewed_cross_has_fillets_tangent_to_both_pavement_edges() -> None:
    context = _context(_road("main", [(-120.0, 0.0), (120.0, 0.0)]), _road("skew", _rotate([(0.0, -120.0), (0.0, 120.0)], -30.0)))
    result = build_intersection_geometry(IntersectionSpec("x4", "cross", ("main", "skew")), context)
    assert result.status == "ready", result.diagnostics
    skew_normal = _rotate([(1.0, 0.0)], -30.0)[0]
    for corner in result.corners:
        cx, cy = corner.center_xy
        # 5 m from each centreline to the edge, 10 m from the edge to the centre
        assert abs(cy) == pytest.approx(15.0)
        assert abs(cx * skew_normal[0] + cy * skew_normal[1]) == pytest.approx(15.0)
    # the sharp corners (60 degrees) reach further along the legs than the blunt ones (120 degrees)
    distances = sorted(abs(leg.mouth_station - 120.0) for leg in result.legs)
    assert distances[0] == pytest.approx(distances[1]) and distances[2] == pytest.approx(distances[3])


def test_a_curved_main_road_keeps_the_fillet_on_its_real_edge() -> None:
    # the main road is an arc of radius 300 m about (0, 300), sampled every half degree
    radius = 300.0
    arc = [(radius * math.sin(math.radians(a / 2.0)), radius - radius * math.cos(math.radians(a / 2.0))) for a in range(-60, 61)]
    context = _context(_road("main", arc), _road("stem", [(0.0, -100.0), (0.0, 0.0)]))
    result = build_intersection_geometry(IntersectionSpec("x5", "t", ("main", "stem")), context)
    assert result.status == "ready", result.diagnostics
    for corner in result.corners:
        if corner.treatment != "fillet":
            continue
        # the arc runs from the from leg's tangent point to the to leg's
        start = corner.arc_xyz[0] if corner.from_leg_id.startswith("main:") else corner.arc_xyz[-1]
        # the tangent point on the main road lies on its outer pavement edge, 305 m from the arc centre,
        # within the sagitta of the half-degree chords the alignment is sampled with (2.8 mm)
        assert math.hypot(start[0], start[1] - radius) == pytest.approx(radius + 5.0, abs=3.0e-3)
        # and the fillet centre is the radius beyond that edge, within the chord sampling error
        assert math.hypot(corner.center_xy[0], corner.center_xy[1] - radius) == pytest.approx(radius + 17.0, abs=0.02)


def test_unequal_left_and_right_widths_are_read_from_the_road() -> None:
    result = build_intersection_geometry(IntersectionSpec("x6", "t", ("main", "stem")), _starter_t(left=6.0, right=4.0))
    assert result.status == "ready"
    # only the stem has them: it runs north, so its left edge is at x = -6 and its right edge at x = +4
    centres = sorted(tuple(round(v, 6) for v in c.center_xy) for c in result.corners if c.center_xy)
    assert centres == [(-18.0, -17.0), (16.0, -17.0)]


def test_a_road_without_applied_section_widths_blocks_with_its_owner_named() -> None:
    result = build_intersection_geometry(IntersectionSpec("x7", "t", ("main", "stem")), _starter_t(widths=()))
    assert result.status == "blocked"
    row = next(row for row in result.diagnostics if row.code == "pavement_edge_owner_missing")
    assert row.subject == "stem" and row.effect == "blocked" and "Applied Section" in row.inspect


def test_a_radius_too_large_for_a_short_leg_blocks() -> None:
    context = _context(_road("main", [(-120.0, 0.0), (120.0, 0.0)]), _road("stem", [(0.0, -10.0), (0.0, 0.0)]))
    result = build_intersection_geometry(IntersectionSpec("x8", "t", ("main", "stem"), corner_radius_m=30.0), context)
    assert result.status == "blocked"
    assert _codes(result) & {"corner_fillet_no_solution", "leg_too_short_for_corner"}


def test_a_corner_override_changes_one_radius_only() -> None:
    spec = IntersectionSpec("x9", "t", ("main", "stem"), corner_overrides=(CornerOverride("stem:back|main:ahead", radius_m=20.0),))
    result = build_intersection_geometry(spec, _starter_t())
    corners = _corners(result)
    assert corners["stem:back|main:ahead"].radius_m == 20.0
    assert corners["main:back|stem:back"].radius_m == 12.0
    assert _legs(result)["main:ahead"].mouth_station == pytest.approx(145.0)


def test_a_manual_anchor_uses_the_given_stations() -> None:
    spec = IntersectionSpec("x10", "t", ("main", "stem"), anchor=AnchorSpec("manual", (("main", 120.0), ("stem", 100.0))))
    assert build_intersection_geometry(spec, _starter_t()).status == "ready"
    wrong = IntersectionSpec("x10", "t", ("main", "stem"), anchor=AnchorSpec("manual", (("main", 120.0), ("stem", 90.0))))
    assert "anchor_roads_do_not_meet" in _codes(build_intersection_geometry(wrong, _starter_t()))


def test_the_fingerprint_follows_the_inputs() -> None:
    spec = IntersectionSpec("x1", "t", ("main", "stem"))
    assert intersection_input_fingerprint(spec, _starter_t()) == intersection_input_fingerprint(spec, _starter_t())
    assert intersection_input_fingerprint(spec, _starter_t()) != intersection_input_fingerprint(spec, _starter_t(left=5.5))
    assert intersection_input_fingerprint(spec, _starter_t()) != intersection_input_fingerprint(
        IntersectionSpec("x1", "t", ("main", "stem"), corner_radius_m=15.0), _starter_t()
    )


def test_a_roundabout_resolves_but_builds_no_geometry_yet() -> None:
    context = _context(_road("ns", [(0.0, -130.0), (0.0, 130.0)]), _road("ew", [(-130.0, 0.0), (130.0, 0.0)]))
    result = build_intersection_geometry(IntersectionSpec("x11", "roundabout", ("ns", "ew")), context)
    assert result.status == "not_implemented"
    assert len(result.legs) == 0 and result.boundary_xyz == ()
