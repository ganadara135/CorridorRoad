from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
    AppliedSectionQuantityFragment,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.corridor_model import (
    CorridorModel,
    CorridorSamplingPolicy,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINSurface, TINTriangle, TINVertex
from freecad.Corridor_Road.v1.models.result.earthwork_balance_model import (
    EarthworkBalanceModel,
    EarthworkBalanceRow,
)
from freecad.Corridor_Road.v1.models.source import (
    AlignmentModel,
    AssemblyModel,
    OverrideModel,
    ProfileModel,
    RegionModel,
)
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    SectionTemplate,
    TemplateComponent,
)
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint
from freecad.Corridor_Road.v1.models.source.region_model import RegionRow
from freecad.Corridor_Road.v1.services.builders import (
    AppliedSectionBuildRequest,
    AppliedSectionSetBuildRequest,
    AppliedSectionSetService,
    AppliedSectionService,
    CorridorDesignSurfaceGeometryRequest,
    CorridorSurfaceBuildRequest,
    CorridorModelBuildRequest,
    CorridorModelService,
    CorridorSurfaceGeometryService,
    CorridorSurfaceService,
    EarthworkBalanceBuildRequest,
    EarthworkBalanceService,
    MassHaulBuildRequest,
    MassHaulService,
    QuantityBuildRequest,
    QuantityBuildService,
)


def test_applied_section_service_builds_component_rows_from_template() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-1",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-1",
        alignment_id="align-1",
        control_rows=[
            ProfileControlPoint(
                control_point_id="pvi-1",
                station=0.0,
                elevation=10.0,
            )
        ],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-1",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-1",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(component_id="lane-1", kind="lane", side="right", width=3.5, thickness=0.25),
                    TemplateComponent(component_id="shoulder-1", kind="shoulder", side="right", width=1.5, thickness=0.20),
                    TemplateComponent(component_id="side-slope-1", kind="side_slope", side="right", width=4.0, slope=-0.5),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-1",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-1",
                region_kind="mainline_region",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-1",
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-1",
        alignment_id="align-1",
    )

    request = AppliedSectionBuildRequest(
        project_id="proj-1",
        corridor_id="cor-1",
        alignment=alignment,
        profile=profile,
        assembly=assembly,
        region_model=region_model,
        override_model=override_model,
        station=10.0,
        applied_section_id="sec-1",
    )

    result = AppliedSectionService().build(request)

    assert result.template_id == "tmpl-1"
    assert len(result.component_rows) == 3
    assert result.component_rows[0].source_template_id == "tmpl-1"
    assert result.component_rows[0].side == "right"
    assert result.component_rows[0].width == 3.5
    assert result.component_rows[0].thickness == 0.25
    assert result.frame is not None
    assert result.surface_right_width == 5.0
    assert result.subgrade_depth == 0.25
    assert result.daylight_right_width == 4.0
    assert result.daylight_right_slope == -0.5
    assert [point.point_role for point in result.point_rows].count("fg_surface") >= 2
    assert [point.point_role for point in result.point_rows].count("subgrade_surface") >= 2
    assert min(point.lateral_offset for point in result.point_rows if point.point_role == "fg_surface") < 0.0


def test_applied_section_service_builds_ditch_surface_points_from_ditch_components() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-ditch",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-ditch",
        alignment_id="align-ditch",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-ditch",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-ditch",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-left", "lane", side="left", width=3.5),
                    TemplateComponent("lane-right", "lane", side="right", width=3.5),
                    TemplateComponent("ditch-left", "ditch", side="left", width=1.2, slope=-0.05),
                    TemplateComponent("ditch-right", "ditch", side="right", width=1.0, slope=-0.04),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-ditch",
        alignment_id="align-ditch",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-ditch")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-ditch",
        alignment_id="align-ditch",
    )

    result = AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="proj-1",
            corridor_id="cor-1",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            station=10.0,
            applied_section_id="sec-ditch",
        )
    )

    ditch_points = [point for point in result.point_rows if point.point_role == "ditch_surface"]
    assert [round(point.lateral_offset, 1) for point in ditch_points] == [-4.5, -3.5, 3.5, 4.7]
    assert min(point.z for point in ditch_points) < result.frame.z


def test_applied_section_service_builds_shape_aware_ditch_surface_points() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-ditch-shapes",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-ditch-shapes",
        alignment_id="align-ditch-shapes",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-ditch-shapes",
        alignment_id="align-ditch-shapes",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-ditch-shapes")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-ditch-shapes",
        alignment_id="align-ditch-shapes",
    )
    cases = [
        (
            "trapezoid",
            {"shape": "trapezoid", "top_width": 4.0, "bottom_width": 1.0, "depth": 1.0, "inner_slope": 1.0, "outer_slope": 1.0},
            [3.5, 4.5, 5.5, 7.5],
        ),
        (
            "u",
            {"shape": "u", "bottom_width": 1.2, "depth": 0.8, "wall_thickness": 0.15},
            [3.5, 3.5, 4.7, 4.7],
        ),
        (
            "l",
            {"shape": "l", "top_width": 2.0, "bottom_width": 1.0, "depth": 0.6, "wall_side": "outer"},
            [3.5, 4.5, 5.5, 5.5],
        ),
        (
            "rectangular",
            {"shape": "rectangular", "bottom_width": 1.4, "depth": 0.7},
            [3.5, 3.5, 4.9, 4.9],
        ),
        (
            "v",
            {"shape": "v", "top_width": 2.0, "depth": 0.9, "invert_offset": 0.75},
            [3.5, 4.25, 5.5],
        ),
    ]
    for shape_name, parameters, expected_offsets in cases:
        assembly = AssemblyModel(
            schema_version=1,
            project_id="proj-1",
            assembly_id=f"asm-{shape_name}",
            template_rows=[
                SectionTemplate(
                    template_id="tmpl-ditch-shapes",
                    template_kind="roadway",
                    component_rows=[
                        TemplateComponent("lane-left", "lane", side="left", width=3.5),
                        TemplateComponent("lane-right", "lane", side="right", width=3.5),
                        TemplateComponent(f"ditch-{shape_name}", "ditch", side="left", width=float(parameters.get("top_width", 1.2) or 1.2), parameters=parameters),
                    ],
                )
            ],
        )

        result = AppliedSectionService().build(
            AppliedSectionBuildRequest(
                project_id="proj-1",
                corridor_id="cor-1",
                alignment=alignment,
                profile=profile,
                assembly=assembly,
                region_model=region_model,
                override_model=override_model,
                station=10.0,
                applied_section_id=f"sec-{shape_name}",
            )
        )

        ditch_points = [point for point in result.point_rows if point.point_role == "ditch_surface"]
        assert [round(point.lateral_offset, 2) for point in ditch_points] == expected_offsets
        assert min(point.z for point in ditch_points) < result.frame.z


def test_applied_section_service_reports_invalid_ditch_shape_parameters() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-ditch-validation",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-ditch-validation",
        alignment_id="align-ditch-validation",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-ditch-validation",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-ditch-validation",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-left", "lane", side="left", width=3.5),
                    TemplateComponent(
                        "ditch-left",
                        "ditch",
                        side="left",
                        width=1.2,
                        parameters={"shape": "trapezoid", "bottom_width": 0.5},
                    ),
                    TemplateComponent(
                        "ditch-right",
                        "ditch",
                        side="right",
                        width=1.2,
                        parameters={"shape": "box"},
                    ),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-ditch-validation",
        alignment_id="align-ditch-validation",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-ditch-validation")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-ditch-validation",
        alignment_id="align-ditch-validation",
    )

    result = AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="proj-1",
            corridor_id="cor-1",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            station=10.0,
            applied_section_id="sec-ditch-validation",
        )
    )

    messages = [row.message for row in result.diagnostic_rows if row.kind == "ditch_shape_parameter"]
    assert any("missing required parameter depth" in message for message in messages)
    assert any("unsupported shape 'box'" in message for message in messages)


def test_applied_section_service_uses_region_assembly_ref_active_template() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-assembly-ref",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-assembly-ref",
        alignment_id="align-assembly-ref",
        control_rows=[ProfileControlPoint("pvi-1", station=0.0, elevation=10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:basic-road",
        active_template_id="template:basic-road",
        template_rows=[
            SectionTemplate(
                template_id="template:basic-road",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(component_id="lane-1", kind="lane"),
                    TemplateComponent(component_id="ditch-1", kind="ditch", enabled=False),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-assembly-ref",
        alignment_id="align-assembly-ref",
        region_rows=[
            RegionRow(
                region_id="region-assembly-ref",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                assembly_ref="assembly:basic-road",
                structure_refs=["structure:wall-01"],
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-assembly-ref",
        alignment_id="align-assembly-ref",
    )

    result = AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="proj-1",
            corridor_id="cor-1",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            station=10.0,
            applied_section_id="sec-assembly-ref",
        )
    )

    assert result.assembly_id == "assembly:basic-road"
    assert result.template_id == "template:basic-road"
    assert result.region_id == "region-assembly-ref"
    assert [row.component_id for row in result.component_rows] == ["lane-1"]
    assert result.component_rows[0].structure_ids == ["structure:wall-01"]
    assert result.diagnostic_rows == []


def test_applied_section_service_warns_on_region_assembly_ref_mismatch() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-assembly-mismatch",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-assembly-mismatch",
        alignment_id="align-assembly-mismatch",
        control_rows=[ProfileControlPoint("pvi-1", station=0.0, elevation=10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:basic-road",
        active_template_id="template:basic-road",
        template_rows=[
            SectionTemplate(
                template_id="template:basic-road",
                template_kind="roadway",
                component_rows=[TemplateComponent(component_id="lane-1", kind="lane")],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-assembly-mismatch",
        alignment_id="align-assembly-mismatch",
        region_rows=[
            RegionRow(
                region_id="region-mismatch",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                assembly_ref="assembly:other-road",
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-assembly-mismatch",
        alignment_id="align-assembly-mismatch",
    )

    result = AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="proj-1",
            corridor_id="cor-1",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            station=10.0,
            applied_section_id="sec-assembly-mismatch",
        )
    )

    assert result.template_id == ""
    assert result.component_rows == []
    assert [row.kind for row in result.diagnostic_rows] == ["assembly_ref_mismatch", "missing_template_ref"]


def test_applied_section_set_service_builds_station_ordered_sections() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-section-set",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-section-set",
        alignment_id="align-section-set",
        control_rows=[ProfileControlPoint("pvi-1", station=0.0, elevation=10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:basic-road",
        active_template_id="template:basic-road",
        template_rows=[
            SectionTemplate(
                template_id="template:basic-road",
                template_kind="roadway",
                component_rows=[TemplateComponent(component_id="lane-1", kind="lane")],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-section-set",
        alignment_id="align-section-set",
        region_rows=[
            RegionRow(
                region_id="region-main",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                assembly_ref="assembly:basic-road",
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-section-set",
        alignment_id="align-section-set",
    )

    result = AppliedSectionSetService().build(
        AppliedSectionSetBuildRequest(
            project_id="proj-1",
            corridor_id="cor-1",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            stations=[20.0, 0.0, 20.0],
            applied_section_set_id="sections:main",
        )
    )

    assert [row.station for row in result.station_rows] == [0.0, 20.0]
    assert [section.station for section in result.sections] == [0.0, 20.0]
    assert result.sections[0].template_id == "template:basic-road"
    assert result.sections[0].component_rows[0].component_id == "lane-1"


def test_applied_section_set_service_selects_region_specific_assembly_model() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-multi-assembly",
        geometry_sequence=[
            AlignmentElement(
                element_id="tangent-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
                length=100.0,
                geometry_payload={"x_values": [0.0, 100.0], "y_values": [0.0, 0.0]},
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="profile-multi-assembly",
        alignment_id="align-multi-assembly",
        control_rows=[
            ProfileControlPoint("pvi-0", 0.0, 10.0),
            ProfileControlPoint("pvi-100", 100.0, 12.0),
        ],
    )
    road = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:road",
        active_template_id="template:road",
        template_rows=[
            SectionTemplate(
                template_id="template:road",
                template_kind="roadway",
                component_rows=[TemplateComponent("lane-road", "lane", side="right", width=3.5)],
            )
        ],
    )
    bridge = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:bridge",
        active_template_id="template:bridge",
        template_rows=[
            SectionTemplate(
                template_id="template:bridge",
                template_kind="bridge_deck",
                component_rows=[TemplateComponent("deck-interface", "structure_interface", side="center", width=10.0)],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:multi-assembly",
        alignment_id="align-multi-assembly",
        region_rows=[
            RegionRow("region:road", 0.0, 50.0, assembly_ref="assembly:road"),
            RegionRow("region:bridge", 50.0, 100.0, primary_kind="bridge", assembly_ref="assembly:bridge"),
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="overrides:none",
        alignment_id="align-multi-assembly",
    )

    result = AppliedSectionSetService().build(
        AppliedSectionSetBuildRequest(
            project_id="proj-1",
            corridor_id="corridor:main",
            alignment=alignment,
            profile=profile,
            assembly=road,
            assembly_models=[road, bridge],
            region_model=region_model,
            override_model=override_model,
            stations=[25.0, 75.0],
            applied_section_set_id="sections:multi-assembly",
        )
    )

    assert [section.assembly_id for section in result.sections] == ["assembly:road", "assembly:bridge"]
    assert [section.template_id for section in result.sections] == ["template:road", "template:bridge"]
    assert result.sections[1].component_rows[0].component_id == "deck-interface"
    assert "assembly:bridge" in result.source_refs


def test_applied_section_service_attaches_alignment_profile_frame() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-frame",
        geometry_sequence=[
            AlignmentElement(
                element_id="align-frame:tangent-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
                length=100.0,
                geometry_payload={
                    "x_values": [1000.0, 1100.0],
                    "y_values": [2000.0, 2000.0],
                },
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-frame",
        alignment_id="align-frame",
        control_rows=[
            ProfileControlPoint(
                control_point_id="pvi-0",
                station=0.0,
                elevation=10.0,
            ),
            ProfileControlPoint(
                control_point_id="pvi-100",
                station=100.0,
                elevation=15.0,
            ),
        ],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-1",
        template_rows=[SectionTemplate(template_id="tmpl-1", template_kind="roadway")],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-1",
        alignment_id="align-frame",
        region_rows=[
            RegionRow(
                region_id="region-1",
                region_kind="mainline_region",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-1",
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-1",
        alignment_id="align-frame",
    )

    result = AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="proj-1",
            corridor_id="cor-1",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            station=50.0,
            applied_section_id="sec-frame",
        )
    )

    assert result.frame is not None
    assert result.frame.alignment_status == "ok"
    assert result.frame.profile_status == "ok"
    assert abs(result.frame.x - 1050.0) < 1e-9
    assert abs(result.frame.y - 2000.0) < 1e-9
    assert abs(result.frame.z - 12.5) < 1e-9
    assert abs(result.frame.profile_grade - 0.05) < 1e-9
    assert result.frame.active_alignment_element_id == "align-frame:tangent-1"
    assert result.frame.active_profile_segment_start_id == "pvi-0"


def test_corridor_surface_service_builds_surface_family_rows() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow(
                station_row_id="sta-1",
                station=10.0,
                applied_section_id="sec-1",
            )
        ],
    )

    result = CorridorSurfaceService().build(
        CorridorSurfaceBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_model_id="surf-1",
        )
    )

    assert result.corridor_id == "cor-1"
    assert len(result.surface_rows) == 3
    assert result.surface_rows[0].surface_kind == "design_surface"
    assert result.build_relation_rows[0].relation_kind == "corridor_build"


def test_corridor_surface_service_adds_drainage_surface_when_ditch_points_exist() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-ditch",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[AppliedSectionStationRow("sta-1", 0.0, "sec-1")],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(station=0.0),
                point_rows=[AppliedSectionPoint("ditch:1", 0.0, 0.0, 0.0, "ditch_surface", 0.0)],
            )
        ],
    )

    result = CorridorSurfaceService().build(
        CorridorSurfaceBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_model_id="surf-1",
        )
    )

    assert [row.surface_kind for row in result.surface_rows] == [
        "design_surface",
        "subgrade_surface",
        "daylight_surface",
        "drainage_surface",
    ]
    assert result.surface_rows[3].parent_surface_ref == "cor-1:design"
    assert result.build_relation_rows[3].operation_summary == "Built from AppliedSection ditch_surface point rows."


def test_corridor_surface_geometry_service_builds_design_surface_ribbon() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
            AppliedSectionStationRow("sta-3", 20.0, "sec-3"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.5, 0.0),
                surface_left_width=6.0,
                surface_right_width=4.0,
                subgrade_depth=0.20,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-3",
                frame=AppliedSectionFrame(20.0, 20.0, 0.0, 11.0, 0.0),
                surface_left_width=5.5,
                surface_right_width=4.5,
                subgrade_depth=0.30,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_design_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:design",
            fallback_half_width=5.0,
        )
    )

    assert result.surface_id == "cor-1:design"
    assert result.surface_kind == "design_surface"
    assert len(result.vertex_rows) == 6
    assert len(result.triangle_rows) == 4
    assert result.quality_rows[0].kind == "station_count"
    assert result.quality_rows[1].kind == "left_width_min"
    assert result.quality_rows[1].value == 5.0


def test_corridor_surface_geometry_service_builds_subgrade_surface_below_design() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 11.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.30,
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_subgrade_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:subgrade",
        )
    )

    assert result.surface_id == "cor-1:subgrade"
    assert result.surface_kind == "subgrade_surface"
    assert len(result.vertex_rows) == 4
    assert len(result.triangle_rows) == 2
    assert min(vertex.z for vertex in result.vertex_rows) == 9.75
    assert max(vertex.z for vertex in result.vertex_rows) == 10.7


def test_corridor_surface_geometry_service_builds_surface_from_applied_section_points() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                point_rows=[
                    AppliedSectionPoint("fg:r", 0.0, -4.0, 9.9, "fg_surface", -4.0),
                    AppliedSectionPoint("fg:c", 0.0, 0.0, 10.0, "fg_surface", 0.0),
                    AppliedSectionPoint("fg:l", 0.0, 5.0, 9.8, "fg_surface", 5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 11.0, 0.0),
                point_rows=[
                    AppliedSectionPoint("fg:r", 10.0, -4.0, 10.9, "fg_surface", -4.0),
                    AppliedSectionPoint("fg:c", 10.0, 0.0, 11.0, "fg_surface", 0.0),
                    AppliedSectionPoint("fg:l", 10.0, 5.0, 10.8, "fg_surface", 5.0),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_design_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:design",
        )
    )

    assert len(result.vertex_rows) == 6
    assert len(result.triangle_rows) == 4
    assert result.boundary_refs == ["cor-1:design:section-point-boundary"]
    assert result.provenance_rows[0].source_kind == "applied_section_points"
    assert result.quality_rows[1].kind == "section_point_count"
    assert result.quality_rows[1].value == 3


def test_corridor_surface_geometry_service_builds_drainage_surface_from_ditch_points() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-ditch",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                point_rows=[
                    AppliedSectionPoint("ditch:r-flow", 0.0, -4.5, 9.8, "ditch_surface", -4.5),
                    AppliedSectionPoint("ditch:r-edge", 0.0, -3.5, 10.0, "ditch_surface", -3.5),
                    AppliedSectionPoint("ditch:l-edge", 0.0, 3.5, 10.0, "ditch_surface", 3.5),
                    AppliedSectionPoint("ditch:l-flow", 0.0, 4.7, 9.8, "ditch_surface", 4.7),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.5, 0.0),
                point_rows=[
                    AppliedSectionPoint("ditch:r-flow", 10.0, -4.5, 10.3, "ditch_surface", -4.5),
                    AppliedSectionPoint("ditch:r-edge", 10.0, -3.5, 10.5, "ditch_surface", -3.5),
                    AppliedSectionPoint("ditch:l-edge", 10.0, 3.5, 10.5, "ditch_surface", 3.5),
                    AppliedSectionPoint("ditch:l-flow", 10.0, 4.7, 10.3, "ditch_surface", 4.7),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_drainage_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:drainage",
        )
    )

    assert result.surface_kind == "drainage_surface"
    assert len(result.vertex_rows) == 8
    assert len(result.triangle_rows) == 6
    assert result.provenance_rows[0].source_kind == "applied_section_points"
    assert result.quality_rows[1].kind == "section_point_count"
    assert result.quality_rows[1].value == 4


def test_corridor_surface_geometry_service_builds_daylight_surface_from_side_slopes() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 11.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:daylight",
        )
    )

    assert result.surface_id == "cor-1:daylight"
    assert result.surface_kind == "daylight_surface"
    assert len(result.vertex_rows) == 8
    assert len(result.triangle_rows) == 4
    assert min(vertex.z for vertex in result.vertex_rows) == 8.5
    assert max(vertex.z for vertex in result.vertex_rows) == 11.0


def test_corridor_surface_geometry_service_ties_daylight_outer_points_to_existing_ground() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 11.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                daylight_left_width=3.0,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg",
        vertex_rows=[
            TINVertex("eg-0", -1.0, -10.0, 100.0),
            TINVertex("eg-1", 11.0, -10.0, 100.0),
            TINVertex("eg-2", 11.0, 10.0, 100.0),
            TINVertex("eg-3", -1.0, 10.0, 100.0),
        ],
        triangle_rows=[
            TINTriangle("eg-t0", "eg-0", "eg-1", "eg-2"),
            TINTriangle("eg-t1", "eg-0", "eg-2", "eg-3"),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:daylight",
            existing_ground_surface=existing_ground,
        )
    )

    vertices = result.vertex_map()
    assert abs(vertices["v0:left:outer"].z - 100.0) < 1e-9
    assert abs(vertices["v0:right:outer"].z - 100.0) < 1e-9
    assert abs(vertices["v1:left:outer"].z - 100.0) < 1e-9
    assert abs(vertices["v1:right:outer"].z - 100.0) < 1e-9
    assert vertices["v0:left:inner"].z == 10.0
    quality = {row.kind: row.value for row in result.quality_rows}
    assert quality["eg_tie_in_hit_count"] == 4
    assert quality["eg_tie_in_miss_count"] == 0
    assert quality["eg_outer_edge_sample_count"] == 4
    assert quality["slope_face_fallback_count"] == 0
    assert quality["slope_face_no_existing_ground_count"] == 0
    assert quality["slope_face_no_eg_hit_count"] == 0


def test_corridor_surface_geometry_service_resolves_actual_slope_face_intersections() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sp-1",
            station_interval=10.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-1", 0.0, "sec-1"),
            AppliedSectionStationRow("sta-2", 10.0, "sec-2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                daylight_left_width=8.0,
                daylight_right_width=8.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                daylight_left_width=8.0,
                daylight_right_width=8.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-flat",
        vertex_rows=[
            TINVertex("eg-0", -1.0, -20.0, 8.0),
            TINVertex("eg-1", 11.0, -20.0, 8.0),
            TINVertex("eg-2", 11.0, 20.0, 8.0),
            TINVertex("eg-3", -1.0, 20.0, 8.0),
        ],
        triangle_rows=[
            TINTriangle("eg-t0", "eg-0", "eg-1", "eg-2"),
            TINTriangle("eg-t1", "eg-0", "eg-2", "eg-3"),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-1:daylight",
            existing_ground_surface=existing_ground,
        )
    )

    vertices = result.vertex_map()
    assert abs(vertices["v0:left:outer"].y - 9.0) < 1e-6
    assert abs(vertices["v0:right:outer"].y - -8.0) < 1e-6
    assert abs(vertices["v1:left:outer"].y - 9.0) < 1e-6
    assert abs(vertices["v1:right:outer"].y - -8.0) < 1e-6
    assert abs(vertices["v0:left:outer"].z - 8.0) < 1e-6
    quality = {row.kind: row.value for row in result.quality_rows}
    assert quality["eg_tie_in_hit_count"] == 4
    assert quality["eg_tie_in_miss_count"] == 0
    assert quality["eg_intersection_count"] == 4
    assert quality["eg_outer_edge_sample_count"] == 0
    assert quality["slope_face_fallback_count"] == 0
    assert quality["slope_face_no_existing_ground_count"] == 0
    assert quality["slope_face_no_eg_hit_count"] == 0


def test_corridor_model_service_builds_from_applied_section_set() -> None:
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
    )

    result = CorridorModelService().build(
        CorridorModelBuildRequest(
            project_id="proj-1",
            corridor_id="corridor:main",
            applied_section_set=applied_section_set,
            region_model_ref="regions:main",
        )
    )

    assert result.corridor_id == "corridor:main"
    assert result.applied_section_set_ref == "sections:main"
    assert result.region_model_ref == "regions:main"
    assert result.sampling_policy.station_interval == 20.0
    assert [row.station for row in result.station_rows] == [0.0, 20.0]


def test_quantity_build_service_aggregates_section_quantity_fragments() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow(
                station_row_id="sta-1",
                station=0.0,
                applied_section_id="sec-1",
            )
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                corridor_id="cor-1",
                alignment_id="align-1",
                profile_id="prof-1",
                station=0.0,
                region_id="region-1",
                component_rows=[
                    AppliedSectionComponentRow(
                        component_id="lane-1",
                        kind="lane",
                    )
                ],
                quantity_rows=[
                    AppliedSectionQuantityFragment(
                        fragment_id="qty-1",
                        quantity_kind="pavement_area",
                        value=25.0,
                        unit="m2",
                        component_id="lane-1",
                    )
                ],
            )
        ],
    )

    result = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="qty-model-1",
        )
    )

    assert result.corridor_id == "cor-1"
    assert len(result.fragment_rows) == 1
    assert result.fragment_rows[0].quantity_kind == "pavement_area"
    assert result.aggregate_rows[0].value == 25.0


def test_quantity_build_service_derives_earthwork_volumes_from_section_areas() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow(
                station_row_id="sta-0",
                station=0.0,
                applied_section_id="sec-0",
            ),
            AppliedSectionStationRow(
                station_row_id="sta-10",
                station=10.0,
                applied_section_id="sec-10",
            ),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                corridor_id="cor-1",
                alignment_id="align-1",
                profile_id="prof-1",
                station=0.0,
                region_id="region-1",
                quantity_rows=[
                    AppliedSectionQuantityFragment(
                        fragment_id="cut-area-0",
                        quantity_kind="cut_area",
                        value=2.0,
                        unit="m2",
                    ),
                    AppliedSectionQuantityFragment(
                        fragment_id="fill-area-0",
                        quantity_kind="fill_area",
                        value=1.0,
                        unit="m2",
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                corridor_id="cor-1",
                alignment_id="align-1",
                profile_id="prof-1",
                station=10.0,
                region_id="region-1",
                quantity_rows=[
                    AppliedSectionQuantityFragment(
                        fragment_id="cut-area-10",
                        quantity_kind="cut_area",
                        value=4.0,
                        unit="m2",
                    ),
                    AppliedSectionQuantityFragment(
                        fragment_id="fill-area-10",
                        quantity_kind="fill_area",
                        value=3.0,
                        unit="m2",
                    ),
                ],
            ),
        ],
    )

    quantity_model = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="qty-model-1",
        )
    )
    earthwork_model = EarthworkBalanceService().build(
        EarthworkBalanceBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model=quantity_model,
            earthwork_balance_id="earth-1",
        )
    )

    volume_rows = [
        row
        for row in quantity_model.fragment_rows
        if row.measurement_kind == "average_end_area_volume"
    ]

    assert [row.quantity_kind for row in volume_rows] == ["cut", "fill"]
    assert [row.value for row in volume_rows] == [30.0, 20.0]
    assert earthwork_model.balance_rows[0].cut_value == 30.0
    assert earthwork_model.balance_rows[0].fill_value == 20.0


def test_earthwork_and_mass_haul_services_build_minimal_analysis_rows() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow(
                station_row_id="sta-1",
                station=0.0,
                applied_section_id="sec-1",
            ),
            AppliedSectionStationRow(
                station_row_id="sta-2",
                station=10.0,
                applied_section_id="sec-2",
            ),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-1",
                corridor_id="cor-1",
                alignment_id="align-1",
                profile_id="prof-1",
                station=0.0,
                region_id="region-1",
                quantity_rows=[
                    AppliedSectionQuantityFragment(
                        fragment_id="cut-1",
                        quantity_kind="cut",
                        value=100.0,
                        unit="m3",
                    ),
                    AppliedSectionQuantityFragment(
                        fragment_id="fill-1",
                        quantity_kind="fill",
                        value=60.0,
                        unit="m3",
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                corridor_id="cor-1",
                alignment_id="align-1",
                profile_id="prof-1",
                station=10.0,
                region_id="region-1",
            ),
        ],
    )

    quantity_model = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="qty-model-1",
        )
    )
    earthwork_model = EarthworkBalanceService().build(
        EarthworkBalanceBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model=quantity_model,
            earthwork_balance_id="earth-1",
        )
    )
    mass_haul_model = MassHaulService().build(
        MassHaulBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            earthwork_balance_model=earthwork_model,
            mass_haul_id="mass-1",
        )
    )

    assert len(earthwork_model.balance_rows) == 1
    assert earthwork_model.balance_rows[0].cut_value == 100.0
    assert earthwork_model.balance_rows[0].fill_value == 60.0
    assert len(mass_haul_model.curve_rows) == 1
    assert mass_haul_model.curve_rows[0].cumulative_mass_values[-1] == 25.0


def test_mass_haul_service_interpolates_balance_points_inside_windows() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    earthwork_model = EarthworkBalanceModel(
        schema_version=1,
        project_id="proj-1",
        earthwork_balance_id="earth-1",
        corridor_id="cor-1",
        balance_rows=[
            EarthworkBalanceRow(
                balance_row_id="balance-1",
                station_start=0.0,
                station_end=10.0,
                cut_value=0.0,
                fill_value=50.0,
                usable_cut_value=0.0,
            ),
            EarthworkBalanceRow(
                balance_row_id="balance-2",
                station_start=10.0,
                station_end=20.0,
                cut_value=100.0,
                fill_value=0.0,
                usable_cut_value=100.0,
            ),
        ],
    )

    result = MassHaulService().build(
        MassHaulBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            earthwork_balance_model=earthwork_model,
            mass_haul_id="mass-1",
        )
    )

    assert result.curve_rows[0].station_values == [0.0, 10.0, 20.0]
    assert result.curve_rows[0].cumulative_mass_values == [0.0, -50.0, 50.0]
    assert len(result.balance_point_rows) == 1
    assert result.balance_point_rows[0].station == 15.0
