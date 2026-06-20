"""Contract tests for Assembly/Subassembly preview and Applied Sections consistency."""

from freecad.Corridor_Road.v1.commands.assembly_preset_data import ASSEMBLY_PRESETS, assembly_preset_names
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import _assembly_section_preview_segments, _preset_subassemblies
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement, AlignmentModel
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    AssemblySourceIdentity,
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
)
from freecad.Corridor_Road.v1.models.source.override_model import OverrideModel
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, ProfileModel
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel
from freecad.Corridor_Road.v1.services.builders.applied_section_service import AppliedSectionBuildRequest, AppliedSectionService
from freecad.Corridor_Road.v1.services.builders.solid_target_discovery_service import (
    SolidTargetDiscoveryRequest,
    SolidTargetDiscoveryService,
)


def _ordinary_rows() -> list[TemplateSubassembly]:
    return [
        TemplateSubassembly("lane:right", "lane", 1, "right", 3.5, -0.02, 0.22, "asphalt"),
        TemplateSubassembly("shoulder:right", "shoulder", 2, "right", 1.0, -0.04, 0.18, "asphalt"),
        TemplateSubassembly("sidewalk:right", "sidewalk", 3, "right", 1.5, 0.01, 0.15, "concrete"),
        TemplateSubassembly(
            "ditch:right",
            "ditch",
            4,
            "right",
            1.0,
            0.0,
            0.0,
            "earth",
            parameters={"shape": "trapezoid", "top_width": 1.0, "bottom_width": 0.4, "depth": 0.3},
        ),
        TemplateSubassembly("side_slope:right", "side_slope", 5, "right", 4.0, -0.5, 0.0, "earth"),
    ]


def _benched_rows() -> list[TemplateSubassembly]:
    return [
        TemplateSubassembly("lane:right", "lane", 1, "right", 3.5, -0.02, 0.22, "asphalt"),
        TemplateSubassembly(
            "side_slope:right",
            "side_slope",
            2,
            "right",
            5.0,
            -0.5,
            0.0,
            "earth",
            parameters={
                "bench_mode": "rows",
                "bench_rows": [{"drop": 1.0, "width": 1.0, "slope": -0.02, "post_slope": -0.25}],
            },
        ),
    ]


def test_digital_twin_ready_preset_exposes_physical_body_contract_rows() -> None:
    assert "Digital Twin Ready Road" in assembly_preset_names()

    rows = _preset_subassemblies(ASSEMBLY_PRESETS["Digital Twin Ready Road"])
    by_id = {row.subassembly_id: row for row in rows}

    pavement = by_id["pavement_layer:main"]
    assert pavement.kind == "pavement_layer"
    assert pavement.width == 7.0
    assert pavement.thickness == 0.18
    assert pavement.material == "asphalt_surface"
    assert pavement.parameters["solid_family"] == "pavement_layer"
    assert pavement.parameters["shape_code"] == "pavement_body"

    subbase = by_id["subbase:main"]
    assert subbase.kind == "subbase"
    assert subbase.width == 8.4
    assert subbase.thickness == 0.30
    assert subbase.material == "crushed_stone"
    assert subbase.parameters["solid_family"] == "subbase"

    assert by_id["shoulder:left"].material == "aggregate_shoulder"
    assert by_id["shoulder:left"].thickness == 0.16
    assert by_id["shoulder:right"].material == "aggregate_shoulder"
    assert by_id["shoulder:right"].thickness == 0.16


def test_digital_twin_ready_preset_discovers_physical_body_solid_targets() -> None:
    rows = _preset_subassemblies(ASSEMBLY_PRESETS["Digital Twin Ready Road"])
    section_start = _section(rows, station=0.0, applied_section_id="section:0")
    section_end = _section(rows, station=100.0, applied_section_id="section:100")
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="project:test",
        applied_section_set_id="applied:digital-twin-ready-road",
        corridor_id="corridor:test",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:100", 100.0, "section:100"),
        ],
        sections=[section_start, section_end],
    )

    model = SolidTargetDiscoveryService().discover(
        SolidTargetDiscoveryRequest(
            project_id="project:test",
            corridor_ref="corridor:test",
            applied_section_set=applied,
            corridor_model=CorridorModel(
                schema_version=1,
                project_id="project:test",
                corridor_id="corridor:test",
                applied_section_set_ref="applied:digital-twin-ready-road",
            ),
        )
    )

    targets = {row.target_id: row for row in model.target_rows}
    pavement = targets["solid-target:pavement-layer:pavement_layer-main"]
    assert pavement.target_family == "pavement_layer_body"
    assert pavement.material_ref == "asphalt_surface"
    assert pavement.station_start == 0.0
    assert pavement.station_end == 100.0
    assert pavement.readiness_status == "available"

    subbase = targets["solid-target:subbase:subbase-main"]
    assert subbase.target_family == "subbase_body"
    assert subbase.material_ref == "crushed_stone"
    assert subbase.readiness_status == "available"

    assert targets["solid-target:shoulder:shoulder-left"].readiness_status == "available"
    assert targets["solid-target:shoulder:shoulder-right"].readiness_status == "available"


def _assembly_model(rows: list[TemplateSubassembly]) -> AssemblySubassemblyModel:
    return AssemblySubassemblyModel(
        schema_version=1,
        project_id="project:test",
        assembly_id="assembly:test",
        alignment_id="alignment:test",
        active_template_id="template:test",
        template_rows=[
            SubassemblySectionTemplate(
                template_id="template:test",
                template_kind="roadway",
                template_index=1,
                subassembly_rows=rows,
            )
        ],
    )


def _section(rows: list[TemplateSubassembly], *, station: float = 50.0, applied_section_id: str = "section:test"):
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "line:1",
                "line",
                0.0,
                100.0,
                100.0,
                {"x_values": [0.0, 100.0], "y_values": [0.0, 0.0]},
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 0.0),
            ProfileControlPoint("pvi:100", 100.0, 0.0),
        ],
    )
    assembly = AssemblySourceIdentity(
        schema_version=1,
        project_id="project:test",
        assembly_id="assembly:test",
        alignment_id="alignment:test",
        active_template_id="template:test",
    )
    return AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="project:test",
            corridor_id="corridor:test",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            assembly_models=[assembly],
            assembly_subassembly_models=[_assembly_model(rows)],
            region_model=RegionModel(
                schema_version=1,
                project_id="project:test",
                region_model_id="regions:test",
                alignment_id="alignment:test",
                region_rows=[
                    RegionRow(
                        "region:test",
                        0.0,
                        100.0,
                        assembly_ref="assembly:test",
                        template_ref="template:test",
                    )
                ],
            ),
            override_model=OverrideModel(
                schema_version=1,
                project_id="project:test",
                override_model_id="overrides:test",
                alignment_id="alignment:test",
            ),
            station=station,
            applied_section_id=applied_section_id,
        )
    )


def _preview_segment_by_id(segments: list[dict[str, object]], subassembly_id: str) -> dict[str, object]:
    return next(
        segment
        for segment in segments
        if str(getattr(segment.get("row"), "subassembly_id", "") or "") == subassembly_id
    )


def _point(section, *, role: str, offset: float, point_id_contains: str = ""):
    return next(
        point
        for point in section.point_rows
        if str(point.point_role) == role and abs(float(point.lateral_offset) - float(offset)) <= 1.0e-9
        and str(point_id_contains or "") in str(point.point_id)
    )


def _assert_point_matches(point: tuple[float, float], expected: tuple[float, float]) -> None:
    assert round(float(point[0]), 9) == round(float(expected[0]), 9)
    assert round(float(point[1]), 9) == round(float(expected[1]), 9)


def _segment_start(segment: dict[str, object]) -> tuple[float, float]:
    topline = tuple(segment.get("topline", ()) or ())
    assert topline
    return tuple(topline[0])


def test_urban_preset_preview_keeps_side_chains_connected() -> None:
    rows = _preset_subassemblies(ASSEMBLY_PRESETS["Urban Curb & Gutter"])
    segments = _assembly_section_preview_segments(rows)

    assert {str(getattr(segment.get("row"), "kind", "") or "") for segment in segments} >= {
        "lane",
        "gutter",
        "curb",
        "sidewalk",
        "green_strip",
    }
    for side in ("left", "right"):
        side_segments = [segment for segment in segments if str(segment.get("side", "") or "") == side]
        assert [str(getattr(segment.get("row"), "subassembly_id", "") or "") for segment in side_segments] == [
            f"lane:{side}",
            f"gutter:{side}",
            f"curb:{side}",
            f"sidewalk:{side}",
            f"green_strip:{side}",
        ]
        for previous, current in zip(side_segments, side_segments[1:]):
            _assert_point_matches(_segment_start(current), tuple(previous["end"]))


def test_section_preview_matches_applied_sections_for_ordinary_subassembly_endpoints() -> None:
    rows = _ordinary_rows()
    segments = _assembly_section_preview_segments(rows)
    section = _section(rows)

    lane = _preview_segment_by_id(segments, "lane:right")
    shoulder = _preview_segment_by_id(segments, "shoulder:right")
    sidewalk = _preview_segment_by_id(segments, "sidewalk:right")
    ditch = _preview_segment_by_id(segments, "ditch:right")
    side_slope = _preview_segment_by_id(segments, "side_slope:right")

    lane_end = tuple(lane["end"])
    shoulder_start = tuple(shoulder["points"][0])
    shoulder_end = tuple(shoulder["end"])
    sidewalk_start = tuple(sidewalk["points"][0])
    sidewalk_end = tuple(sidewalk["end"])
    ditch_start = tuple(ditch["topline"][0])
    side_slope_hinge = tuple(side_slope["topline"][0])

    assert len(tuple(ditch["topline"])) == 4
    assert tuple(ditch["topline"][1]) == (-6.0, -0.395)
    assert tuple(ditch["topline"][2]) == (-6.4, -0.395)
    _assert_point_matches(lane_end, (-3.5, _point(section, role="fg_surface", offset=-3.5).z))
    _assert_point_matches(shoulder_start, lane_end)
    _assert_point_matches(shoulder_end, (-4.5, _point(section, role="fg_surface", offset=-4.5).z))
    _assert_point_matches(sidewalk_start, shoulder_end)
    _assert_point_matches(sidewalk_end, (-6.0, _point(section, role="fg_surface", offset=-6.0).z))
    _assert_point_matches(ditch_start, sidewalk_end)
    _assert_point_matches(ditch_start, (-6.0, _point(section, role="ditch_surface", offset=-6.0, point_id_contains="inner_edge").z))
    _assert_point_matches(side_slope_hinge, (-7.0, _point(section, role="ditch_surface", offset=-7.0, point_id_contains="outer_edge").z))


def test_section_preview_matches_applied_sections_for_side_slope_bench_breaks() -> None:
    rows = _benched_rows()
    segments = _assembly_section_preview_segments(rows)
    section = _section(rows)

    side_slope = _preview_segment_by_id(segments, "side_slope:right")
    topline = tuple(side_slope["topline"])

    assert len(topline) == 4
    _assert_point_matches(topline[1], (-5.5, _point(section, role="side_slope_surface", offset=-5.5).z))
    _assert_point_matches(topline[2], (-6.5, _point(section, role="bench_surface", offset=-6.5).z))
    _assert_point_matches(topline[3], (-8.5, _point(section, role="side_slope_surface", offset=-8.5).z))


if __name__ == "__main__":
    test_urban_preset_preview_keeps_side_chains_connected()
    test_section_preview_matches_applied_sections_for_ordinary_subassembly_endpoints()
    test_section_preview_matches_applied_sections_for_side_slope_bench_breaks()
    print("[PASS] section preview consistency contract tests completed.")
