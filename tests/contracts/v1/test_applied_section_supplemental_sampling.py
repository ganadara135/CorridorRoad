from freecad.Corridor_Road.v1.models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from freecad.Corridor_Road.v1.models.source import AlignmentModel, AssemblySubassemblyModel, OverrideModel, ProfileModel, RegionModel
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement
from freecad.Corridor_Road.v1.models.source.assembly_model import SubassemblySectionTemplate, TemplateSubassembly
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, VerticalCurveRow
from freecad.Corridor_Road.v1.models.source.region_model import RegionRow
from freecad.Corridor_Road.v1.services.builders import AppliedSectionSetBuildRequest, AppliedSectionSetService
from freecad.Corridor_Road.v1.services.evaluation import Centerline3DEvaluationRequest, Centerline3DEvaluationService


def _curved_centerline_result() -> Centerline3DResult:
    return Centerline3DResult(
        schema_version=1,
        project_id="project:test",
        centerline3d_result_id="centerline3d:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        point_rows=(
            Centerline3DPointRow(0.0, 0.0, 0.0, 0.0),
            Centerline3DPointRow(50.0, 50.0, 25.0, 0.0),
            Centerline3DPointRow(100.0, 100.0, 0.0, 0.0),
        ),
        status="ready",
    )


def _straight_centerline_result() -> Centerline3DResult:
    return Centerline3DResult(
        schema_version=1,
        project_id="project:test",
        centerline3d_result_id="centerline3d:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        point_rows=(
            Centerline3DPointRow(0.0, 0.0, 0.0, 0.0),
            Centerline3DPointRow(100.0, 100.0, 0.0, 0.0),
        ),
        status="ready",
    )


def _request(
    centerline3d_result: Centerline3DResult,
    *,
    enabled: bool = True,
    profile: ProfileModel | None = None,
    max_spacing: float = 25.0,
) -> AppliedSectionSetBuildRequest:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[AlignmentElement("alignment:test:tangent", "tangent", 0.0, 100.0)],
    )
    if profile is None:
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
    assembly = AssemblySubassemblyModel(
        schema_version=1,
        project_id="project:test",
        assembly_id="assembly:test",
        active_template_id="template:test",
        template_rows=[
            SubassemblySectionTemplate(
                "template:test",
                "roadway",
                subassembly_rows=[
                    TemplateSubassembly("lane:right", "lane", side="right", width=3.5),
                    TemplateSubassembly("shoulder:right", "shoulder", side="right", width=1.5),
                    TemplateSubassembly("slope:right", "side_slope", side="right", width=4.0, slope=-0.5),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="project:test",
        region_model_id="regions:test",
        alignment_id="alignment:test",
        region_rows=[
            RegionRow(
                "region:main",
                0.0,
                100.0,
                assembly_ref="assembly:test",
                template_ref="template:test",
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="project:test",
        override_model_id="overrides:test",
        alignment_id="alignment:test",
    )
    return AppliedSectionSetBuildRequest(
        project_id="project:test",
        corridor_id="corridor:test",
        alignment=alignment,
        profile=profile,
        assembly=assembly,
        assembly_models=[assembly],
        assembly_subassembly_models=[assembly],
        region_model=region_model,
        override_model=override_model,
        stations=[0.0, 100.0],
        applied_section_set_id="applied-sections:test",
        centerline3d_result=centerline3d_result,
        supplemental_sections_enabled=enabled,
        supplemental_sections_max_spacing=max_spacing,
        supplemental_sections_tangent_delta_deg=3.0,
        supplemental_sections_chord_deviation=0.25,
    )


def test_applied_sections_create_curve_supplemental_sections_with_centerline_result_fallback_payload() -> None:
    result = AppliedSectionSetService().build(_request(_curved_centerline_result()))

    kinds = [row.kind for row in result.station_rows]
    supplemental = [
        section
        for row, section in zip(result.station_rows, result.sections)
        if row.kind == "curve_supplemental"
    ]

    assert "curve_supplemental" in kinds
    assert supplemental
    assert all(section.subassembly_rows for section in supplemental)
    assert all(section.point_rows for section in supplemental)
    assert all(section.frame is not None for section in supplemental)
    assert all("source=centerline3d_result" in str(section.frame.notes) for section in supplemental)
    assert all(
        "supplemental_section_curve_trigger" in [diagnostic.kind for diagnostic in section.diagnostic_rows]
        for section in supplemental
    )


def test_applied_sections_do_not_densify_straight_centerline_by_spacing_only() -> None:
    result = AppliedSectionSetService().build(_request(_straight_centerline_result()))

    assert [row.kind for row in result.station_rows] == ["regular_sample", "regular_sample"]
    assert len(result.sections) == 2


def test_applied_sections_limit_curve_supplemental_density_to_spacing() -> None:
    result = AppliedSectionSetService().build(_request(_curved_centerline_result(), max_spacing=25.0))

    supplemental = [row for row in result.station_rows if row.kind == "curve_supplemental"]

    assert len(supplemental) == 3
    assert [round(row.station, 3) for row in result.station_rows] == [0.0, 25.0, 50.0, 75.0, 100.0]


def test_applied_sections_supplemental_option_can_be_disabled() -> None:
    result = AppliedSectionSetService().build(_request(_curved_centerline_result(), enabled=False))

    assert [row.kind for row in result.station_rows] == ["regular_sample", "regular_sample"]
    assert len(result.sections) == 2


def test_applied_sections_create_vertical_curve_supplemental_sections_on_straight_centerline() -> None:
    profile = ProfileModel(
        schema_version=1,
        project_id="project:test",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:0", 0.0, 0.0),
            ProfileControlPoint("pvi:50", 50.0, -20.0),
            ProfileControlPoint("pvi:100", 100.0, 0.0),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("vertical-curve:sag", "parabolic_vertical_curve", 0.0, 100.0, curve_length=100.0),
        ],
    )

    result = AppliedSectionSetService().build(_request(_straight_centerline_result(), profile=profile))
    supplemental = [
        section
        for row, section in zip(result.station_rows, result.sections)
        if row.kind == "vertical_curve_supplemental"
    ]

    assert "vertical_curve_supplemental" in [row.kind for row in result.station_rows]
    assert supplemental
    assert all(section.subassembly_rows for section in supplemental)
    assert all(section.point_rows for section in supplemental)
    assert all(
        "supplemental_section_vertical_curve_trigger" in [diagnostic.kind for diagnostic in section.diagnostic_rows]
        for section in supplemental
    )


def test_applied_section_origins_follow_centerline_frame_on_strong_vertical_curve() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="project:test",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                "alignment:test:tangent",
                "tangent",
                0.0,
                100.0,
                geometry_payload={"x_values": [0.0, 100.0], "y_values": [0.0, 0.0]},
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
            ProfileControlPoint("pvi:50", 50.0, -20.0),
            ProfileControlPoint("pvi:100", 100.0, 0.0),
        ],
        vertical_curve_rows=[
            VerticalCurveRow("vertical-curve:sag", "parabolic_vertical_curve", 0.0, 100.0, curve_length=100.0),
        ],
    )
    centerline = Centerline3DEvaluationService().evaluate(
        Centerline3DEvaluationRequest(
            alignment_model=alignment,
            profile_model=profile,
            station_values=(0.0, 100.0),
            stationing_id="stationing:test",
        )
    )

    result = AppliedSectionSetService().build(_request(centerline, profile=profile))
    middle = min(result.sections, key=lambda section: abs(float(section.station) - 50.0))

    assert centerline.point_count > 2
    assert abs(float(middle.station) - 50.0) <= 1.0e-9
    assert middle.frame is not None
    assert abs(float(middle.frame.z) - (-10.0)) <= 1.0e-9
    assert abs(float(middle.frame.z) - 0.0) > 1.0
    assert "source=centerline3d_result" in str(middle.frame.notes)


if __name__ == "__main__":
    test_applied_sections_create_curve_supplemental_sections_with_centerline_result_fallback_payload()
    test_applied_sections_do_not_densify_straight_centerline_by_spacing_only()
    test_applied_sections_supplemental_option_can_be_disabled()
    test_applied_sections_create_vertical_curve_supplemental_sections_on_straight_centerline()
    test_applied_section_origins_follow_centerline_frame_on_strong_vertical_curve()
    print("PASS: applied section supplemental sampling contract validation")
