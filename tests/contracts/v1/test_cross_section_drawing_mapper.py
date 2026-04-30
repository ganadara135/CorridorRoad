from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.services.mapping.cross_section_drawing_mapper import CrossSectionDrawingMapper


def _sample_applied_section_set() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="project:cross-section-drawing",
        applied_section_set_id="sections:drawing",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="project:cross-section-drawing",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.30,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
            AppliedSection(
                schema_version=1,
                project_id="project:cross-section-drawing",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=12.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.30,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 20.0, -5.2, 11.7, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 20.0, -4.0, 12.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 20.0, 5.0, 12.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 20.0, 6.2, 11.7, "ditch_surface", 6.2),
                ],
            ),
        ],
    )


def test_cross_section_drawing_payload_builds_fallback_fg_subgrade_and_slope_rows() -> None:
    payload = CrossSectionDrawingMapper().map_applied_section_set(_sample_applied_section_set(), station=0.0)

    geometry_by_kind = {row.kind: row for row in payload.geometry_rows}
    slope_rows = [row for row in payload.geometry_rows if row.kind == "slope_face"]

    assert payload.drawing_id == "section:0:drawing"
    assert payload.station_label == "STA 0.000"
    assert geometry_by_kind["fg"].offset_values == [-4.0, 0.0, 5.0]
    assert geometry_by_kind["fg"].elevation_values == [10.0, 10.0, 10.0]
    assert geometry_by_kind["subgrade"].elevation_values == [9.7, 9.7]
    assert len(slope_rows) == 2
    assert any(row.offset_values == [5.0, 8.0] for row in slope_rows)
    assert any(row.offset_values == [-4.0, -6.0] for row in slope_rows)
    assert any(row.text == "CL" for row in payload.label_rows)
    assert any(row.text == "FG" and row.value == "9.000 m" for row in payload.label_rows)
    assert any(row.kind == "overall_width" and row.value == 14.0 for row in payload.dimension_rows)
    assert any(row.label == "Left FG" and row.value == 5.0 for row in payload.dimension_rows)


def test_cross_section_drawing_payload_uses_ditch_surface_points_for_ditch_geometry() -> None:
    payload = CrossSectionDrawingMapper().map_applied_section_set(_sample_applied_section_set(), station=20.0)

    ditch = next(row for row in payload.geometry_rows if row.kind == "ditch")
    ditch_labels = [row for row in payload.label_rows if "ditch" in row.text.lower()]

    assert payload.drawing_id == "section:20:drawing"
    assert ditch.style_role == "drainage"
    assert ditch.offset_values == [-5.2, -4.0, 5.0, 6.2]
    assert ditch.elevation_values == [11.7, 12.0, 12.0, 11.7]
    assert ditch_labels
    assert ditch_labels[0].value == "11.400 m"
    assert any(row.kind == "overall_width" and row.value == 11.4 for row in payload.dimension_rows)


def test_cross_section_drawing_payload_starts_slope_face_from_ditch_outer_edges() -> None:
    section = AppliedSection(
        schema_version=1,
        project_id="project:cross-section-drawing",
        applied_section_id="section:ditch-daylight",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station=40.0,
        frame=AppliedSectionFrame(station=40.0, x=40.0, y=0.0, z=20.0),
        surface_left_width=5.0,
        surface_right_width=4.0,
        daylight_left_width=3.0,
        daylight_right_width=2.0,
        daylight_left_slope=-0.5,
        daylight_right_slope=-0.4,
        point_rows=[
            AppliedSectionPoint("ditch:right-flow", 40.0, -5.2, 19.6, "ditch_surface", -5.2),
            AppliedSectionPoint("ditch:right-edge", 40.0, -4.0, 20.0, "ditch_surface", -4.0),
            AppliedSectionPoint("ditch:left-edge", 40.0, 5.0, 20.0, "ditch_surface", 5.0),
            AppliedSectionPoint("ditch:left-flow", 40.0, 6.2, 19.6, "ditch_surface", 6.2),
        ],
    )

    payload = CrossSectionDrawingMapper().map_applied_section(section)
    slope_rows = [row for row in payload.geometry_rows if row.kind == "slope_face"]

    assert any(row.offset_values == [6.2, 9.2] and row.elevation_values == [19.6, 18.1] for row in slope_rows)
    assert any(row.offset_values == [-5.2, -7.2] and row.elevation_values == [19.6, 18.8] for row in slope_rows)


def test_cross_section_drawing_payload_uses_bench_point_rows_for_side_slope_geometry() -> None:
    section = AppliedSection(
        schema_version=1,
        project_id="project:cross-section-drawing",
        applied_section_id="section:bench",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station=60.0,
        frame=AppliedSectionFrame(station=60.0, x=60.0, y=0.0, z=10.0),
        surface_right_width=3.5,
        point_rows=[
            AppliedSectionPoint("fg:right", 60.0, -3.5, 10.0, "fg_surface", -3.5),
            AppliedSectionPoint("fg:center", 60.0, 0.0, 10.0, "fg_surface", 0.0),
            AppliedSectionPoint("slope:right:1", 60.0, -7.5, 8.0, "side_slope_surface", -7.5),
            AppliedSectionPoint("bench:right:1", 60.0, -8.0, 7.99, "bench_surface", -8.0),
            AppliedSectionPoint("daylight:right", 60.0, -8.0, 7.99, "daylight_marker", -8.0),
        ],
    )

    payload = CrossSectionDrawingMapper().map_applied_section(section)

    side_slope_rows = [row for row in payload.geometry_rows if row.kind == "side_slope"]
    bench_rows = [row for row in payload.geometry_rows if row.kind == "bench"]
    labels = {(row.text, row.role) for row in payload.label_rows}

    assert side_slope_rows[0].style_role == "side_slope"
    assert side_slope_rows[0].offset_values == [-3.5, -7.5]
    assert side_slope_rows[0].elevation_values == [10.0, 8.0]
    assert bench_rows[0].style_role == "side_slope_bench"
    assert bench_rows[0].offset_values == [-7.5, -8.0]
    assert bench_rows[0].elevation_values == [8.0, 7.99]
    assert ("Right bench", "side_slope_bench") in labels
    assert ("Right daylight", "side_slope:daylight") in labels


def test_cross_section_drawing_payload_synthesizes_v0_style_rows_from_components() -> None:
    section = AppliedSection(
        schema_version=1,
        project_id="project:cross-section-drawing",
        applied_section_id="section:component-only",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station=20.0,
        frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=12.0),
        subgrade_depth=0.30,
        component_rows=[
            AppliedSectionComponentRow("lane:left", "lane", side="left", width=3.5, slope=-0.02),
            AppliedSectionComponentRow("lane:right", "lane", side="right", width=3.5, slope=-0.02),
            AppliedSectionComponentRow("shoulder:left", "shoulder", side="left", width=1.8, slope=-0.04),
            AppliedSectionComponentRow("shoulder:right", "shoulder", side="right", width=1.8, slope=-0.04),
            AppliedSectionComponentRow("ditch:left", "ditch", side="left", width=1.8, slope=-0.12),
            AppliedSectionComponentRow("ditch:right", "ditch", side="right", width=1.8, slope=-0.12),
            AppliedSectionComponentRow("slope:left", "side_slope", side="left", width=6.0, slope=0.33),
            AppliedSectionComponentRow("slope:right", "side_slope", side="right", width=6.0, slope=0.33),
        ],
    )

    payload = CrossSectionDrawingMapper().map_applied_section(section)
    fg = next(row for row in payload.geometry_rows if row.kind == "fg")
    slope_rows = [row for row in payload.geometry_rows if row.kind == "slope_face"]

    assert min(fg.offset_values) == -5.3
    assert max(fg.offset_values) == 5.3
    assert any(row.kind == "ditch" for row in payload.geometry_rows)
    assert len(slope_rows) == 2
    assert any(row.offset_values == [7.1, 13.1] for row in slope_rows)
    assert any(row.offset_values == [-7.1, -13.1] for row in slope_rows)
    assert any(row.text == "ditch L" and row.value == "1.800 m" for row in payload.label_rows)
    assert any(row.text == "daylight R" and row.value == "6.000 m" for row in payload.label_rows)
    assert any(row.kind == "overall_width" and abs(row.value - 26.2) < 1.0e-9 for row in payload.dimension_rows)
    assert sum(1 for row in payload.dimension_rows if row.kind == "component_width") == 8


def test_cross_section_drawing_payload_returns_empty_state_without_sections() -> None:
    payload = CrossSectionDrawingMapper().map_applied_section_set(
        AppliedSectionSet(
            schema_version=1,
            project_id="project:empty",
            applied_section_set_id="sections:empty",
            corridor_id="corridor:main",
            alignment_id="alignment:main",
        )
    )

    assert payload.drawing_id == "sections:empty:empty-drawing"
    assert payload.geometry_rows == []
    assert payload.summary_rows[0].kind == "missing_section"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 cross-section drawing mapper contract tests completed.")
