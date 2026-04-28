from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
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
    assert len(result.component_rows) == 2
    assert result.component_rows[0].source_template_id == "tmpl-1"
    assert result.frame is not None
    assert result.surface_right_width == 5.0
    assert result.subgrade_depth == 0.25


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
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-2",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.5, 0.0),
                surface_left_width=6.0,
                surface_right_width=4.0,
                subgrade_depth=0.20,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-3",
                frame=AppliedSectionFrame(20.0, 20.0, 0.0, 11.0, 0.0),
                surface_left_width=5.5,
                surface_right_width=4.5,
                subgrade_depth=0.30,
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
