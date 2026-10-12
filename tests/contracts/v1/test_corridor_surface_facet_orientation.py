"""Corridor surface triangles wind counterclockwise in plan, so every facet faces up.

Section point rows come in the order the subassemblies emit them, which may run either way
across the road. The Design, Subgrade and Drainage strips used a fixed corner order and faced
down for the usual right-to-left rows, while Daylight strips and the intersection kernel faced up.
"""

from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel, CorridorSamplingPolicy
from freecad.Corridor_Road.v1.services.builders import (
    CorridorDesignSurfaceGeometryRequest,
    CorridorSurfaceGeometryService,
)


def _section(section_id: str, station: float, points: list[tuple[float, float, str, str]]) -> AppliedSection:
    # x is the station and y the lateral offset (left positive): the alignment runs along +x
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=section_id,
        corridor_id="cor-1",
        alignment_id="align-1",
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0, tangent_direction_deg=0.0),
        point_rows=[
            AppliedSectionPoint(
                f"{section_id}:p{index}",
                station,
                offset,
                z,
                point_role,
                offset,
                group_id,
                "left" if offset > 0.0 else "right",
                group_id,
            )
            for index, (offset, z, point_role, group_id) in enumerate(points)
        ],
    )


def _request(points: list[tuple[float, float, str, str]], surface_id: str) -> CorridorDesignSurfaceGeometryRequest:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(sampling_policy_id="sp-1", station_interval=10.0),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[AppliedSectionStationRow("sta-1", 0.0, "sec-1"), AppliedSectionStationRow("sta-2", 10.0, "sec-2")],
        sections=[_section("sec-1", 0.0, points), _section("sec-2", 10.0, points)],
    )
    return CorridorDesignSurfaceGeometryRequest(
        project_id="proj-1",
        corridor=corridor,
        applied_section_set=applied_section_set,
        surface_id=surface_id,
        fallback_half_width=5.0,
    )


def _plan_orientations(surface) -> list[float]:
    points = {vertex.vertex_id: (vertex.x, vertex.y) for vertex in surface.vertex_rows}
    rows = []
    for triangle in surface.triangle_rows:
        (x1, y1), (x2, y2), (x3, y3) = points[triangle.v1], points[triangle.v2], points[triangle.v3]
        rows.append((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
    return rows


def _fg_points(offsets: list[float]) -> list[tuple[float, float, str, str]]:
    return [(offset, 10.0 - 0.02 * abs(offset), "fg_surface", "") for offset in offsets]


def test_design_strips_face_up_for_right_to_left_rows() -> None:
    surface = CorridorSurfaceGeometryService().build_design_surface(
        _request(_fg_points([-5.0, -3.5, 0.0, 3.5, 5.0]), "surface:design")
    )

    assert len(surface.triangle_rows) == 8
    assert all(value > 0.0 for value in _plan_orientations(surface))


def test_design_strips_face_up_for_left_to_right_rows() -> None:
    surface = CorridorSurfaceGeometryService().build_design_surface(
        _request(_fg_points([5.0, 3.5, 0.0, -3.5, -5.0]), "surface:design")
    )

    assert len(surface.triangle_rows) == 8
    assert all(value > 0.0 for value in _plan_orientations(surface))


def test_a_vertical_strip_keeps_its_order() -> None:
    # a curb face at -3.5 m: two points at the same offset, 0.15 m apart in height
    points = _fg_points([-5.0, -3.5, 0.0])
    points.insert(2, (-3.5, 10.08, "fg_surface", ""))
    surface = CorridorSurfaceGeometryService().build_design_surface(_request(points, "surface:design"))

    orientations = dict(zip((row.triangle_id for row in surface.triangle_rows), _plan_orientations(surface)))
    assert orientations["span:0:p1:a"] == 0.0
    assert orientations["span:0:p1:b"] == 0.0
    assert all(value > 0.0 for key, value in orientations.items() if not key.startswith("span:0:p1:"))


def test_drainage_strips_face_up_on_both_sides() -> None:
    points = [
        (-4.5, 9.8, "ditch_surface", "drainage:right"),
        (-3.5, 10.0, "ditch_surface", "drainage:right"),
        (3.5, 10.0, "ditch_surface", "drainage:left"),
        (4.7, 9.8, "ditch_surface", "drainage:left"),
    ]
    surface = CorridorSurfaceGeometryService().build_drainage_surface(_request(points, "surface:drainage"))

    assert len(surface.triangle_rows) == 4
    assert all(value > 0.0 for value in _plan_orientations(surface))
