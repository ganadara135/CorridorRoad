"""Corridor surfaces drop the zero-area triangles of zero-width section strips.

Adjacent subassemblies each emit their shared boundary point, so a section row holds that point
twice. The strip between the two copies used to become two zero-area triangles, which FreeCAD
merged into a non-manifold mesh and reported as defective when a saved document opened.
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


def _section(section_id: str, station: float, offsets: list[float], rise: dict[int, float] | None = None) -> AppliedSection:
    # crown at 10 m falling 2 % to each edge; x is the station, y the lateral offset; `rise` lifts
    # single points, as a curb top does above the lane edge at the same offset
    rise = dict(rise or {})
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=section_id,
        corridor_id="cor-1",
        alignment_id="align-1",
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0, tangent_direction_deg=0.0),
        point_rows=[
            AppliedSectionPoint(f"{section_id}:p{index}", station, offset, 10.0 - 0.02 * abs(offset) + rise.get(index, 0.0), "fg_surface", offset)
            for index, offset in enumerate(offsets)
        ],
    )


def _design_surface(offsets: list[float], *, first_rise=None, second_rise=None):
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
        sections=[_section("sec-1", 0.0, offsets, first_rise), _section("sec-2", 10.0, offsets, second_rise)],
    )
    return CorridorSurfaceGeometryService().build_design_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="surface:design",
            fallback_half_width=5.0,
        )
    )


def _coincident_triangles(surface) -> list[str]:
    points = {vertex.vertex_id: (vertex.x, vertex.y, vertex.z) for vertex in surface.vertex_rows}
    return [
        triangle.triangle_id
        for triangle in surface.triangle_rows
        if len({points[triangle.v1], points[triangle.v2], points[triangle.v3]}) < 3
    ]


def test_a_boundary_point_shared_by_two_subassemblies_leaves_no_zero_area_triangle() -> None:
    offsets = [-5.0, -3.5, -3.5, 0.0, 3.5, 5.0]  # lane end and shoulder start both at -3.5 m
    surface = _design_surface(offsets)

    # every source point stays a vertex, with its own provenance
    assert len(surface.vertex_rows) == 12
    # five strips, one of them without width: four strips of two triangles
    assert len(surface.triangle_rows) == 8
    assert _coincident_triangles(surface) == []


def test_a_strip_that_closes_at_one_station_keeps_its_one_real_triangle() -> None:
    # a curb face at -3.5 m: no height at the first station, 0.15 m at the second
    surface = _design_surface([-5.0, -3.5, -3.5, 0.0, 3.5, 5.0], second_rise={1: 0.15})

    assert len(surface.triangle_rows) == 9
    assert _coincident_triangles(surface) == []
    narrowing = [row.triangle_id for row in surface.triangle_rows if row.triangle_id.startswith("span:0:p1:")]
    assert narrowing == ["span:0:p1:b"]
