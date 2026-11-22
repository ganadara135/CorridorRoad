"""Clipped section lines stay on their own slope and leave no folded Daylight facets."""

import math

import pytest

from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel
from freecad.Corridor_Road.v1.services.builders.applied_section_service import (
    _clip_overlapping_applied_sections,
    _nearest_crossing_sections,
)
from freecad.Corridor_Road.v1.services.builders.corridor_surface_geometry_service import (
    CorridorDesignSurfaceGeometryRequest,
    _build_daylight_surface_from_side_slope_points,
)

# Road edge at 4 m and elevation 10, a 1:2 slope, a bench, a second slope and the daylight point.
SLOPE_CHAIN = [
    (8.0, 8.0, "side_slope_surface"),
    (9.0, 8.0, "bench_surface"),
    (13.0, 6.0, "side_slope_surface"),
    (13.0, 6.0, "daylight_marker"),
]


def _section(index: int, x: float, y: float, heading_deg: float) -> AppliedSection:
    angle = math.radians(heading_deg)
    normal_x, normal_y = -math.sin(angle), math.cos(angle)
    points = []
    for sign, side in ((1.0, "left"), (-1.0, "right")):
        points.append(
            AppliedSectionPoint(
                f"fg:{side}", x + normal_x * sign * 4.0, y + normal_y * sign * 4.0, 10.0, "fg_surface", sign * 4.0, side=side
            )
        )
        for row, (offset, z, role) in enumerate(SLOPE_CHAIN):
            points.append(
                AppliedSectionPoint(
                    f"slope:{side}:{row}",
                    x + normal_x * sign * offset,
                    y + normal_y * sign * offset,
                    z,
                    role,
                    sign * offset,
                    "slope",
                    side,
                )
            )
    return AppliedSection(
        schema_version=1,
        project_id="project:test",
        applied_section_id=f"section:{index}",
        corridor_id="corridor:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        assembly_id="assembly:test",
        station=index * 2.0,
        frame=AppliedSectionFrame(index * 2.0, x, y, 10.0, tangent_direction_deg=heading_deg),
        surface_left_width=4.0,
        surface_right_width=4.0,
        daylight_left_width=9.0,
        daylight_right_width=9.0,
        point_rows=points,
    )


def _kinked_sections(turn_deg: float) -> list[AppliedSection]:
    sections = []
    x = y = 0.0
    for index, heading in enumerate([0.0, 0.0, 0.0, turn_deg, turn_deg, turn_deg]):
        sections.append(_section(index, x, y, heading))
        x += 2.0 * math.cos(math.radians(heading))
        y += 2.0 * math.sin(math.radians(heading))
    return sections


def _side_rows(section: AppliedSection, side: str) -> list[AppliedSectionPoint]:
    return sorted((p for p in section.point_rows if p.side == side), key=lambda p: abs(p.lateral_offset))


@pytest.mark.parametrize(("turn_deg", "side"), [(25.0, "left"), (-25.0, "right")])
def test_clipped_points_take_the_elevation_of_their_slope_at_the_cap(turn_deg, side) -> None:
    clipped, _rows = _clip_overlapping_applied_sections(_kinked_sections(turn_deg), [])

    gathered = [p for p in _side_rows(clipped[3], side) if p.point_role != "fg_surface"]
    cap = abs(gathered[0].lateral_offset)
    assert 4.0 < cap < 8.0
    assert all(abs(p.lateral_offset) == pytest.approx(cap) for p in gathered)
    assert all(p.z == pytest.approx(10.0 - (cap - 4.0) * 0.5) for p in gathered)


@pytest.mark.parametrize("turn_deg", [25.0, -25.0])
def test_section_is_clipped_against_an_earlier_section_it_still_crosses(turn_deg) -> None:
    side = "left" if turn_deg > 0.0 else "right"

    clipped, _rows = _clip_overlapping_applied_sections(_kinked_sections(turn_deg), [])

    assert any(row.kind == "applied_section_overlap_clip" for row in clipped[4].diagnostic_rows)
    outer = _side_rows(clipped[4], side)[-1]
    assert 9.0 < abs(outer.lateral_offset) < 13.0
    assert outer.z == pytest.approx(8.0 - (abs(outer.lateral_offset) - 9.0) * 0.5)


@pytest.mark.parametrize("turn_deg", [25.0, -25.0])
def test_daylight_strip_over_clipped_sections_has_no_folded_facets(turn_deg) -> None:
    clipped, _rows = _clip_overlapping_applied_sections(_kinked_sections(turn_deg), [])
    request = CorridorDesignSurfaceGeometryRequest(
        project_id="project:test",
        corridor=CorridorModel(schema_version=1, project_id="project:test", corridor_id="corridor:test"),
        applied_section_set=AppliedSectionSet(
            schema_version=1,
            project_id="project:test",
            applied_section_set_id="set:test",
            corridor_id="corridor:test",
            alignment_id="alignment:test",
            sections=clipped,
        ),
        surface_id="surface:test",
    )

    surface = _build_daylight_surface_from_side_slope_points(request, sections=clipped, fallback_half_width=4.0)

    vertices = {row.vertex_id: row for row in surface.vertex_rows}
    assert surface.triangle_rows
    for triangle in surface.triangle_rows:
        a, b, c = vertices[triangle.v1], vertices[triangle.v2], vertices[triangle.v3]
        plan_area = 0.5 * ((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x))
        assert plan_area > 1.0e-9


def test_a_straight_road_is_not_clipped() -> None:
    sections = [_section(index, index * 2.0, 0.0, 0.0) for index in range(4)]

    clipped, _rows = _clip_overlapping_applied_sections(sections, [])

    assert clipped == sections


def test_search_stops_at_another_leg_of_a_hairpin() -> None:
    first_leg = _section(0, 0.0, 0.0, 0.0)
    other_leg = _section(1, 2.0, 3.0, 120.0)

    assert _nearest_crossing_sections([first_leg], other_leg) == []
