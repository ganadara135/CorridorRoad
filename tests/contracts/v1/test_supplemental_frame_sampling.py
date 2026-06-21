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
from freecad.Corridor_Road.v1.services.builders.applied_section_service import (
    _clip_overlapping_applied_sections,
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


def _source_geometry_arc_frame(station, _first=None, _second=None, _ratio=0.0) -> AppliedSectionFrame:
    frame = _arc_frame(station, _first, _second, _ratio)
    return AppliedSectionFrame(
        station=frame.station,
        x=frame.x,
        y=frame.y,
        z=frame.z,
        tangent_direction_deg=frame.tangent_direction_deg,
        profile_grade=frame.profile_grade,
        alignment_status=frame.alignment_status,
        profile_status=frame.profile_status,
        active_alignment_element_id=frame.active_alignment_element_id,
        active_profile_segment_start_id=frame.active_profile_segment_start_id,
        active_profile_segment_end_id=frame.active_profile_segment_end_id,
        active_vertical_curve_id=frame.active_vertical_curve_id,
        notes="source=centerline3d_source_geometry;compatible_source=centerline3d_result",
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


def test_supplemental_sampling_summary_treats_source_geometry_as_centerline_source() -> None:
    sections = [_section("s0", 0.0), _section("s10", 10.0)]

    summary = supplemental_sampling_summary(sections, max_spacing=1.0, frame_resolver=_source_geometry_arc_frame)

    assert int(summary["supplemental_frame_count"]) > 0
    assert int(summary["fallback_count"]) == 0
    assert dict(summary["source_mode_counts"]).get("centerline3d_source_geometry", 0) > 0


def test_supplemental_sections_preserve_subassembly_surface_ownership() -> None:
    sections = [_section("s0", 0.0), _section("s10", 10.0)]

    sampled = _supplemental_sampled_sections(sections, max_spacing=5.0, frame_resolver=None)
    supplemental = [section for section in sampled if "supplemental:" in section.applied_section_id]

    assert supplemental
    assert supplemental[0].subassembly_point_rows
    assert supplemental[0].subassembly_link_rows
    assert all("supplemental:subassembly:" in point.point_id for point in supplemental[0].subassembly_point_rows)


def test_applied_section_overlap_guard_clips_overlapping_regular_and_supplemental_sections() -> None:
    first = AppliedSection(
        schema_version=1,
        project_id="project:test",
        applied_section_id="base:0",
        corridor_id="corridor:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        assembly_id="assembly:test",
        station=0.0,
        frame=AppliedSectionFrame(0.0, 0.0, 0.0, 0.0, tangent_direction_deg=0.0),
        surface_left_width=2.0,
        surface_right_width=2.0,
        daylight_left_width=8.0,
        daylight_right_width=8.0,
    )
    overlapping_supplemental = AppliedSection(
        schema_version=1,
        project_id="project:test",
        applied_section_id="supplemental:1",
        corridor_id="corridor:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        assembly_id="assembly:test",
        station=1.0,
        frame=AppliedSectionFrame(1.0, 1.0, 0.0, 0.0, tangent_direction_deg=10.0),
        surface_left_width=2.0,
        surface_right_width=2.0,
        daylight_left_width=8.0,
        daylight_right_width=8.0,
        subassembly_point_rows=[
            AppliedSectionSubassemblyPoint(
                "slope:left:daylight",
                "slope:left",
                "daylight_marker",
                1.0,
                10.0,
                0.0,
                lateral_offset=10.0,
                side="left",
            )
        ],
        subassembly_link_rows=[
            AppliedSectionSubassemblyLink(
                "slope:left:link",
                "slope:left",
                "slope:left:hinge",
                "slope:left:daylight",
                "slope_face",
                surface_role="slope_face_surface",
            )
        ],
    )
    overlapping_regular = AppliedSection(
        schema_version=1,
        project_id="project:test",
        applied_section_id="regular:2",
        corridor_id="corridor:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        assembly_id="assembly:test",
        station=2.0,
        frame=AppliedSectionFrame(2.0, 1.0, 0.0, 0.0, tangent_direction_deg=10.0),
        surface_left_width=2.0,
        surface_right_width=2.0,
        daylight_left_width=8.0,
        daylight_right_width=8.0,
    )
    sections, rows = _clip_overlapping_applied_sections(
        [first, overlapping_supplemental, overlapping_regular],
        [
            AppliedSectionStationRow("row:0", 0.0, "base:0", kind="regular_sample"),
            AppliedSectionStationRow("row:1", 1.0, "supplemental:1", kind="supplemental_horizontal_curve"),
            AppliedSectionStationRow("row:2", 2.0, "regular:2", kind="regular_sample"),
        ],
    )

    assert [section.applied_section_id for section in sections] == ["base:0", "supplemental:1", "regular:2"]
    assert [row.applied_section_id for row in rows] == ["base:0", "supplemental:1", "regular:2"]
    assert sections[1].surface_left_width == 2.0
    assert sections[1].surface_right_width == 2.0
    assert sections[1].daylight_left_width < 8.0 or sections[1].daylight_right_width < 8.0
    assert overlapping_supplemental.daylight_left_width == 8.0
    assert overlapping_supplemental.daylight_right_width == 8.0
    assert overlapping_supplemental.subassembly_point_rows[0].lateral_offset == 10.0
    assert overlapping_supplemental.subassembly_link_rows[0].end_point_ref == "slope:left:daylight"
    assert any(row.kind == "applied_section_overlap_clip" for row in sections[1].diagnostic_rows)
    clip = next(row for row in sections[1].diagnostic_rows if row.kind == "applied_section_overlap_clip")
    assert "section_id=supplemental:1" in clip.notes
    assert "previous_section_id=base:0" in clip.notes
    assert "clipped_point_ids=slope:left:daylight" in clip.notes
    assert "clipped_link_ids=slope:left:link" in clip.notes
    assert "subassembly_refs=slope:left" in clip.notes
    regular_sections, regular_rows = _clip_overlapping_applied_sections(
        [first, overlapping_regular],
        [
            AppliedSectionStationRow("row:0", 0.0, "base:0", kind="regular_sample"),
            AppliedSectionStationRow("row:2", 2.0, "regular:2", kind="regular_sample"),
        ],
    )
    assert [row.applied_section_id for row in regular_rows] == ["base:0", "regular:2"]
    assert regular_sections[1].surface_left_width == 2.0
    assert regular_sections[1].surface_right_width == 2.0
    assert regular_sections[1].daylight_left_width < 8.0 or regular_sections[1].daylight_right_width < 8.0
    assert any(row.kind == "applied_section_overlap_clip" for row in regular_sections[1].diagnostic_rows)


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
    test_supplemental_sampling_summary_treats_source_geometry_as_centerline_source()
    test_supplemental_sections_preserve_subassembly_surface_ownership()
    test_applied_section_overlap_guard_clips_overlapping_regular_and_supplemental_sections()
    test_design_surface_uses_supplemental_frame_series()
    test_build_corridor_supplemental_frame_marker_preview()
    print("PASS: supplemental frame sampling contract validation")
