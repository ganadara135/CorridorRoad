"""Heights, patch TIN and side slope of the parametric intersection kernel (plan phase R5).

Analytic roads with Applied-Section-like profiles: a 2 % crossfall to 5 m edges and a side slope
4 m wide falling 2 m on both sides. The checks are the three defects of the current pipeline:
the curb return side slope left unfilled, skinny patch triangles, and side slope missing beside
the stem; plus the continuity the current grading breaks at the mouths.
"""

import math

import pytest

from freecad.Corridor_Road.v1.models.source.intersection_spec import IntersectionSpec
from freecad.Corridor_Road.v1.services.evaluation.intersection_kernel import build_intersection_geometry

from test_intersection_kernel import _context, _road, _rotate

SKINNY = 0.08


def _t(*, grading=None, turn=0.0, main_grade=0.0, stem_grade=0.0, slope_width=4.0, radius=None):
    context = _context(
        _road("main", _rotate([(-120.0, 0.0), (120.0, 0.0)], turn), crossfall=0.02, grade=main_grade, z_station=120.0, slope_width=slope_width),
        _road("stem", _rotate([(0.0, -100.0), (0.0, 0.0)], turn), crossfall=0.02, grade=stem_grade, z_station=100.0, slope_width=slope_width),
    )
    spec = IntersectionSpec("t", "t", ("main", "stem"), grading_mode=grading, corner_radius_m=radius)
    return build_intersection_geometry(spec, context), context


def _cross():
    context = _context(
        _road("main", [(-120.0, 0.0), (120.0, 0.0)], crossfall=0.02),
        _road("cross", [(0.0, -120.0), (0.0, 120.0)], crossfall=0.02),
    )
    return build_intersection_geometry(IntersectionSpec("c", "cross", ("main", "cross")), context), context


def _quality(result, name):
    return dict(result.quality_rows)[name]


def _area(vertices, triangles):
    return sum(
        abs((vertices[b][0] - vertices[a][0]) * (vertices[c][1] - vertices[a][1]) - (vertices[b][1] - vertices[a][1]) * (vertices[c][0] - vertices[a][0])) / 2.0
        for a, b, c in triangles
    )


def _inside(point, polygon):
    x, y = point[0], point[1]
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if (a[1] > y) != (b[1] > y) and a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) > x:
            inside = not inside
    return inside


@pytest.mark.parametrize("build", [_t, _cross])
def test_the_patch_covers_the_boundary_with_no_skinny_triangle(build) -> None:
    result, _context_ = build()
    assert result.status == "ready", result.diagnostics
    assert _area(result.patch_vertices_xyz, result.patch_triangles) == pytest.approx(result.boundary_area_m2, rel=1.0e-9)
    assert _quality(result, "patch_triangle_skinny_count") == 0
    assert _quality(result, "patch_triangle_min_quality") > SKINNY


def test_every_boundary_vertex_keeps_the_corridor_height() -> None:
    result, context = _t(main_grade=0.02, stem_grade=-0.03)
    boundary = {(round(p[0], 6), round(p[1], 6)): p[2] for p in result.boundary_xyz}
    patch = {(round(p[0], 6), round(p[1], 6)): p[2] for p in result.patch_vertices_xyz}
    for key, z in boundary.items():
        assert patch[key] == z
    # the mouth of the main road ahead: its cut is the road's own profile at station 137
    profile = context.surface_profile("main", 137.0)
    for offset, z in profile.fg:
        assert boundary[(137.0 - 120.0, round(offset, 6))] == pytest.approx(z, abs=1.0e-9)


def test_blend_keeps_the_primary_crown_and_slopes_the_side_road_to_it() -> None:
    result, context = _t(grading="blend_primary_side", main_grade=0.02, stem_grade=-0.03)
    crowns = {subject: points for role, subject, points in result.breaklines if role == "crown"}
    for point in crowns["main:ahead"]:
        assert point[2] == pytest.approx(context.finished_grade_z("main", 120.0 + point[0]))
    stem = crowns["stem:back"]
    # straight from the stem's own crown at its mouth (station 83) to the main road's at the anchor
    assert stem[0][2] == pytest.approx(context.finished_grade_z("stem", 83.0))
    assert stem[-1][2] == pytest.approx(context.finished_grade_z("main", 120.0))


def test_flatten_takes_the_mean_of_the_mouth_crowns_at_the_anchor() -> None:
    result, context = _t(grading="flatten_intersection", main_grade=0.02, stem_grade=-0.03)
    mouths = [context.finished_grade_z("main", 137.0), context.finished_grade_z("main", 103.0), context.finished_grade_z("stem", 83.0)]
    anchor = [p for p in result.patch_vertices_xyz if abs(p[0]) < 1.0e-9 and abs(p[1]) < 1.0e-9]
    assert len(anchor) == 1 and anchor[0][2] == pytest.approx(sum(mouths) / 3.0)


@pytest.mark.parametrize("build", [_t, _cross])
def test_the_side_slope_runs_round_every_curb_return_and_along_the_closed_side(build) -> None:
    result, _context_ = build()
    assert _quality(result, "slope_vertex_without_daylight_count") == 0
    assert _quality(result, "slope_triangle_count") > 0
    # one strip per pair of neighbouring legs, each with its toe line
    toes = [points for role, _subject, points in result.breaklines if role == "slope_toe"]
    assert len(toes) == len(result.corners)
    boundary = [(p[0], p[1]) for p in result.boundary_xyz]
    for points in toes:
        assert not any(_inside(point, boundary) for point in points)
    # the slope covers all of the boundary but the mouths: its inner edge is as long as that
    mouth_length = sum(math.dist(leg.mouth_left_xyz[:2], leg.mouth_right_xyz[:2]) for leg in result.legs if leg.mouth_station is not None)
    perimeter = sum(math.dist(boundary[i], boundary[(i + 1) % len(boundary)]) for i in range(len(boundary)))
    inner = 0.0
    slope = result.slope_vertices_xyz
    for a, b, c in result.slope_triangles:
        for u, v in ((a, b), (b, c), (c, a)):
            pu, pv = slope[u], slope[v]
            if _on_boundary(pu, boundary) and _on_boundary(pv, boundary):
                inner += math.dist(pu[:2], pv[:2])
    assert inner == pytest.approx(perimeter - mouth_length, rel=1.0e-6)


def _on_boundary(point, boundary):
    return any(math.dist(point[:2], q) < 1.0e-9 for q in boundary)


def test_at_a_mouth_the_strip_ends_on_the_corridor_side_slope_line() -> None:
    result, context = _t()
    profile = context.surface_profile("main", 137.0)
    daylight_right = (17.0, profile.right_daylight[0], profile.right_daylight[1])
    daylight_left = (17.0, profile.left_daylight[0], profile.left_daylight[1])
    slope = {(round(p[0], 6), round(p[1], 6)): p[2] for p in result.slope_vertices_xyz}
    for x, y, z in (daylight_right, daylight_left):
        assert slope[(x, round(y, 6))] == pytest.approx(z)


def test_the_curb_return_slope_falls_toward_the_fillet_centre() -> None:
    result, _context_ = _t()
    corner = next(c for c in result.corners if c.treatment == "fillet")
    cx, cy = corner.center_xy
    # every arc vertex has a slope point 4 m nearer the centre and 2 m lower
    slope = result.slope_vertices_xyz
    for point in corner.arc_xyz[1:-1]:
        outer = [q for q in slope if math.dist(q[:2], (cx, cy)) == pytest.approx(math.dist(point[:2], (cx, cy)) - 4.0, abs=1.0e-6)
                 and abs(math.atan2(q[1] - cy, q[0] - cx) - math.atan2(point[1] - cy, point[0] - cx)) < 1.0e-6]
        assert outer and outer[0][2] == pytest.approx(point[2] - 2.0)


def test_a_side_slope_wider_than_the_radius_stops_at_the_centre_and_says_so() -> None:
    result, _context_ = _t(slope_width=15.0, radius=12.0)
    assert "corner_side_slope_wider_than_radius" in {row.code for row in result.diagnostics}
    assert result.status == "partial"


def test_the_surfaces_turn_with_the_roads() -> None:
    straight, _ = _t()
    turned, _ = _t(turn=30.0)
    for name in ("patch_triangle_count", "patch_triangle_min_quality", "slope_triangle_count"):
        assert _quality(turned, name) == pytest.approx(_quality(straight, name), rel=1.0e-6), name


def test_the_drainage_candidate_is_the_lowest_point_of_the_patch_with_its_road_and_station() -> None:
    # the main road rises 2 % with station, the side road is level: water collects at the main road's
    # back mouth (station 103), on both pavement edges, 2 % crossfall below the crown
    result, _context_ = _t(main_grade=0.02)
    candidates = result.drainage_candidates
    assert len(candidates) == 2
    expected_z = 10.0 + 0.02 * (103.0 - 120.0) - 0.02 * 5.0
    for candidate in candidates:
        assert candidate.road_ref == "main"
        assert candidate.station == pytest.approx(103.0, abs=1.0e-6)
        assert candidate.z == pytest.approx(expected_z, abs=1.0e-9)
        assert abs(candidate.y) == pytest.approx(5.0)
