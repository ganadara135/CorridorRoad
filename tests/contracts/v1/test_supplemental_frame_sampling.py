import math

import FreeCAD as App

from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
    AppliedSectionSubassemblyLink,
    AppliedSectionSubassemblyPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel
from freecad.Corridor_Road.v1.services.builders.corridor_surface_geometry_service import (
    CorridorDesignSurfaceGeometryRequest,
    CorridorSurfaceGeometryService,
    _supplemental_sampled_sections,
    supplemental_sampling_summary,
)


def _arc_frame(station, _first=None, _second=None, _ratio=0.0) -> AppliedSectionFrame:
    radius = 50.0
    length = 10.0
    angle_total = math.radians(10.0)
    theta = (float(station) / length) * angle_total
    return AppliedSectionFrame(
        station=float(station),
        x=radius * math.sin(theta),
        y=radius * (1.0 - math.cos(theta)),
        z=0.0,
        tangent_direction_deg=math.degrees(theta),
        notes="source=centerline3d_result",
    )


def _straight_frame(station, _first=None, _second=None, _ratio=0.0) -> AppliedSectionFrame:
    return AppliedSectionFrame(
        station=float(station),
        x=float(station),
        y=0.0,
        z=0.0,
        tangent_direction_deg=0.0,
        notes="source=centerline3d_result",
    )


def _section(section_id: str, station: float) -> AppliedSection:
    frame = _arc_frame(station)
    points = [
        AppliedSectionPoint("left", frame.x, frame.y + 2.0, 0.0, point_role="fg_surface", lateral_offset=2.0),
        AppliedSectionPoint("right", frame.x, frame.y - 2.0, 0.0, point_role="fg_surface", lateral_offset=-2.0),
    ]
    subassembly_points = [
        AppliedSectionSubassemblyPoint(
            "lane:left:start",
            "lane:left",
            "fg_surface",
            frame.x,
            frame.y,
            0.0,
            lateral_offset=0.0,
            side="left",
        ),
        AppliedSectionSubassemblyPoint(
            "lane:left:end",
            "lane:left",
            "fg_surface",
            frame.x,
            frame.y + 3.5,
            -0.07,
            lateral_offset=3.5,
            side="left",
        ),
    ]
    subassembly_links = [
        AppliedSectionSubassemblyLink(
            "lane:left:fg",
            "lane:left",
            "lane:left:start",
            "lane:left:end",
            "lane_fg",
            surface_role="design_surface",
        )
    ]
    return AppliedSection(
        schema_version=1,
        project_id="project:test",
        applied_section_id=section_id,
        corridor_id="corridor:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        assembly_id="assembly:test",
        station=station,
        frame=frame,
        point_rows=points,
        subassembly_point_rows=subassembly_points,
        subassembly_link_rows=subassembly_links,
        surface_left_width=2.0,
        surface_right_width=2.0,
    )


def _section_set(sections: list[AppliedSection]) -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="project:test",
        applied_section_set_id="sections:test",
        corridor_id="corridor:test",
        alignment_id="alignment:test",
        sections=sections,
        station_rows=[
            AppliedSectionStationRow(f"row:{index}", section.station, section.applied_section_id)
            for index, section in enumerate(sections, start=1)
        ],
    )


def test_supplemental_sampling_recursively_follows_centerline_frame() -> None:
    sections = [_section("s0", 0.0), _section("s10", 10.0)]

    low_sections = _supplemental_sampled_sections(sections, max_spacing=10.0, frame_resolver=_arc_frame)
    high_sections = _supplemental_sampled_sections(sections, max_spacing=1.0, frame_resolver=_arc_frame)

    assert len(low_sections) > 2
    assert len(high_sections) > len(low_sections)

    middle = min(high_sections, key=lambda section: abs(float(section.station) - 5.0))
    expected = _arc_frame(5.0)
    assert abs(float(middle.frame.x) - expected.x) < 1.0e-9
    assert abs(float(middle.frame.y) - expected.y) < 1.0e-9
    assert "source=centerline3d_result" in str(middle.frame.notes)


def test_supplemental_sampling_does_not_densify_straight_centerline_by_spacing_only() -> None:
    sections = [_section("s0", 0.0), _section("s100", 100.0)]

    sampled = _supplemental_sampled_sections(sections, max_spacing=1.0, frame_resolver=_straight_frame)

    assert sampled == sections


def test_supplemental_sampling_summary_reports_source_and_density() -> None:
    sections = [_section("s0", 0.0), _section("s10", 10.0)]

    low = supplemental_sampling_summary(sections, max_spacing=10.0, frame_resolver=_arc_frame)
    high = supplemental_sampling_summary(sections, max_spacing=1.0, frame_resolver=_arc_frame)

    assert int(low["supplemental_frame_count"]) > 0
    assert int(high["supplemental_frame_count"]) > int(low["supplemental_frame_count"])
    assert int(high["fallback_count"]) == 0
    assert dict(high["source_mode_counts"]).get("centerline3d_result", 0) > 0


def test_supplemental_sections_preserve_subassembly_surface_ownership() -> None:
    sections = [_section("s0", 0.0), _section("s10", 10.0)]

    sampled = _supplemental_sampled_sections(sections, max_spacing=5.0, frame_resolver=None)
    supplemental = [section for section in sampled if "supplemental:" in section.applied_section_id]

    assert supplemental
    assert supplemental[0].subassembly_point_rows
    assert supplemental[0].subassembly_link_rows
    assert all("supplemental:subassembly:" in point.point_id for point in supplemental[0].subassembly_point_rows)


def test_design_surface_uses_supplemental_frame_series() -> None:
    sections = [_section("s0", 0.0), _section("s10", 10.0)]
    high_sections = _supplemental_sampled_sections(sections, max_spacing=1.0, frame_resolver=_arc_frame)
    surface = CorridorSurfaceGeometryService().build_design_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="project:test",
            corridor=CorridorModel(schema_version=1, project_id="project:test", corridor_id="corridor:test"),
            applied_section_set=_section_set(sections),
            surface_id="surface:test",
            supplemental_sampling_enabled=True,
            supplemental_sampling_max_spacing=1.0,
            supplemental_frame_resolver=_arc_frame,
        )
    )

    station_counts = [row for row in surface.quality_rows if row.kind == "station_count"]
    assert station_counts
    assert int(station_counts[0].value) == len(high_sections)


def test_build_corridor_supplemental_frame_marker_preview() -> None:
    import freecad.Corridor_Road.v1.commands.cmd_build_corridor as cmd

    doc = App.newDocument("SupplementalFrameMarkerContract")
    try:
        applied = _section_set([_section("s0", 0.0), _section("s10", 10.0)])
        original_find = cmd.find_v1_applied_section_set
        original_to = cmd.to_applied_section_set
        original_resolver = cmd._corridor_supplemental_frame_resolver
        original_project = cmd.find_project
        cmd.find_v1_applied_section_set = lambda _document: object()
        cmd.to_applied_section_set = lambda _obj: applied
        cmd._corridor_supplemental_frame_resolver = lambda _document: _arc_frame
        cmd.find_project = lambda _document: None
        obj = cmd.create_or_update_corridor_supplemental_frame_markers(
            document=doc,
            supplemental_sampling_max_spacing=1.0,
            visible=True,
        )
        assert obj is not None
        assert obj.Name == "V1CorridorSupplementalFrameMarkers"
        assert int(getattr(obj, "MarkerCount", 0) or 0) > 0
        assert any("source=centerline3d_result" in str(row) for row in list(getattr(obj, "StationRows", []) or []))
    finally:
        cmd.find_v1_applied_section_set = original_find
        cmd.to_applied_section_set = original_to
        cmd._corridor_supplemental_frame_resolver = original_resolver
        cmd.find_project = original_project
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    test_supplemental_sampling_recursively_follows_centerline_frame()
    test_supplemental_sampling_does_not_densify_straight_centerline_by_spacing_only()
    test_supplemental_sampling_summary_reports_source_and_density()
    test_supplemental_sections_preserve_subassembly_surface_ownership()
    test_design_surface_uses_supplemental_frame_series()
    test_build_corridor_supplemental_frame_marker_preview()
    print("PASS: supplemental frame sampling contract validation")
