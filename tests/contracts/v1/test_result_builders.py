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
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    CulvertGeometrySpec,
    RetainingWallGeometrySpec,
    StructureGeometrySpec,
    StructureInfluenceZone,
    StructureInteractionRule,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
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
    StructureSolidBuildRequest,
    StructureSolidOutputService,
)
from freecad.Corridor_Road.v1.models.output import StructureSolidOutput, StructureSolidOutputRow


def _triangle_normal_z(surface: TINSurface, triangle: TINTriangle) -> float:
    vertices = surface.vertex_map()
    v1 = vertices[triangle.v1]
    v2 = vertices[triangle.v2]
    v3 = vertices[triangle.v3]
    ax = float(v2.x) - float(v1.x)
    ay = float(v2.y) - float(v1.y)
    bx = float(v3.x) - float(v1.x)
    by = float(v3.y) - float(v1.y)
    return ax * by - ay * bx


def _surface_vertices_by_prefix(surface: TINSurface, prefix: str) -> list[TINVertex]:
    return sorted(
        [vertex for vertex in surface.vertex_rows if vertex.vertex_id.startswith(prefix)],
        key=lambda vertex: int(str(vertex.vertex_id).rsplit(":p", 1)[-1]),
    )


def _rounded_vertex_xyz_rows(vertices: list[TINVertex]) -> list[tuple[float, float, float]]:
    return [
        (round(float(vertex.x), 6), round(float(vertex.y), 6), round(float(vertex.z), 6))
        for vertex in vertices
    ]


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


def test_applied_section_service_evaluates_side_slope_bench_rows() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-bench",
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
        profile_id="prof-bench",
        alignment_id="align-bench",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-bench",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-bench",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-right", "lane", side="right", width=3.5),
                    TemplateComponent(
                        "side-slope-right",
                        "side_slope",
                        side="right",
                        width=8.0,
                        slope=-0.5,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [
                                {
                                    "drop": 2.0,
                                    "width": 1.0,
                                    "slope": -0.02,
                                    "post_slope": -0.5,
                                    "row_id": "bench-1",
                                }
                            ],
                            "repeat_first_bench_to_daylight": True,
                            "daylight_mode": "terrain",
                            "daylight_max_width": 80.0,
                        },
                    ),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-bench",
        alignment_id="align-bench",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-bench")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-bench",
        alignment_id="align-bench",
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
            applied_section_id="sec-bench",
        )
    )

    assert result.daylight_right_width == 8.0
    assert [row.kind for row in result.component_rows] == [
        "lane",
        "side_slope",
        "side_slope",
        "bench",
        "side_slope",
        "daylight",
    ]
    assert [round(row.width, 2) for row in result.component_rows if row.component_id.startswith("side-slope-right:")] == [4.0, 1.0, 3.0, 0.0]
    bench_points = [point for point in result.point_rows if point.point_role in {"side_slope_surface", "bench_surface", "daylight_marker"}]
    assert [point.point_role for point in bench_points] == [
        "side_slope_surface",
        "bench_surface",
        "side_slope_surface",
        "daylight_marker",
    ]
    assert [round(point.lateral_offset, 2) for point in bench_points] == [-7.5, -8.5, -11.5, -11.5]
    assert round(bench_points[1].z, 2) == 7.98
    assert any(row.kind == "bench_daylight_fallback" for row in result.diagnostic_rows)


def test_applied_section_service_shortens_bench_rows_at_terrain_daylight() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-bench-terrain",
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
        profile_id="prof-bench-terrain",
        alignment_id="align-bench-terrain",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-bench-terrain",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-bench-terrain",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-right", "lane", side="right", width=3.5),
                    TemplateComponent(
                        "side-slope-right",
                        "side_slope",
                        side="right",
                        width=8.0,
                        slope=-0.5,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [
                                {
                                    "drop": 2.0,
                                    "width": 1.0,
                                    "slope": -0.02,
                                    "post_slope": -0.5,
                                }
                            ],
                            "daylight_mode": "terrain",
                            "daylight_search_step": 0.25,
                        },
                    ),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-bench-terrain",
        alignment_id="align-bench-terrain",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-bench-terrain")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-bench-terrain",
        alignment_id="align-bench-terrain",
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-bench",
        vertex_rows=[
            TINVertex("eg-0", 0.0, -20.0, 7.99),
            TINVertex("eg-1", 20.0, -20.0, 7.99),
            TINVertex("eg-2", 20.0, 20.0, 7.99),
            TINVertex("eg-3", 0.0, 20.0, 7.99),
        ],
        triangle_rows=[
            TINTriangle("eg-t0", "eg-0", "eg-1", "eg-2"),
            TINTriangle("eg-t1", "eg-0", "eg-2", "eg-3"),
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
            applied_section_id="sec-bench-terrain",
            existing_ground_surface=existing_ground,
        )
    )

    derived_rows = [row for row in result.component_rows if row.component_id.startswith("side-slope-right:")]
    assert [row.kind for row in derived_rows] == ["side_slope", "bench", "daylight"]
    assert [round(row.width, 2) for row in derived_rows] == [4.0, 0.5, 0.0]
    bench_points = [point for point in result.point_rows if point.point_role in {"side_slope_surface", "bench_surface", "daylight_marker"}]
    assert [round(point.lateral_offset, 2) for point in bench_points] == [-7.5, -8.0, -8.0]
    assert [round(point.z, 2) for point in bench_points] == [8.0, 7.99, 7.99]
    assert any(row.kind == "bench_daylight_shortened" for row in result.diagnostic_rows)
    assert any(row.kind == "bench_daylight_skipped" for row in result.diagnostic_rows)
    assert not any(row.kind == "bench_daylight_fallback" for row in result.diagnostic_rows)


def test_applied_section_service_orients_bench_side_slope_up_for_cut_context() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-bench-cut",
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
        profile_id="prof-bench-cut",
        alignment_id="align-bench-cut",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-bench-cut",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-bench-cut",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-right", "lane", side="right", width=3.5),
                    TemplateComponent(
                        "side-slope-right",
                        "side_slope",
                        side="right",
                        width=8.0,
                        slope=-0.5,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [{"drop": 2.0, "width": 1.0, "slope": -0.02, "post_slope": -0.5}],
                            "daylight_mode": "terrain",
                            "daylight_search_step": 0.25,
                        },
                    ),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-bench-cut",
        alignment_id="align-bench-cut",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-bench-cut")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-bench-cut",
        alignment_id="align-bench-cut",
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-bench-cut",
        vertex_rows=[
            TINVertex("eg-0", 0.0, -20.0, 12.0),
            TINVertex("eg-1", 20.0, -20.0, 12.0),
            TINVertex("eg-2", 20.0, 20.0, 12.0),
            TINVertex("eg-3", 0.0, 20.0, 12.0),
        ],
        triangle_rows=[
            TINTriangle("eg-t0", "eg-0", "eg-1", "eg-2"),
            TINTriangle("eg-t1", "eg-0", "eg-2", "eg-3"),
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
            applied_section_id="sec-bench-cut",
            existing_ground_surface=existing_ground,
        )
    )

    derived_rows = [row for row in result.component_rows if row.component_id.startswith("side-slope-right:")]
    bench_points = [point for point in result.point_rows if point.point_role in {"side_slope_surface", "bench_surface", "daylight_marker"}]
    assert [row.kind for row in derived_rows] == ["side_slope", "daylight"]
    assert round(derived_rows[0].width, 2) == 4.0
    assert derived_rows[0].slope == 0.5
    assert [round(point.z, 2) for point in bench_points] == [12.0, 12.0]
    assert any(row.kind == "bench_cut_fill_context" and "cut terrain context" in row.message for row in result.diagnostic_rows)


def test_applied_section_service_repeats_bench_profile_to_daylight_max_width_before_corridor_build() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-bench-max-daylight",
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
        profile_id="prof-bench-max-daylight",
        alignment_id="align-bench-max-daylight",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-bench-max-daylight",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-bench-max-daylight",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-right", "lane", side="right", width=3.5),
                    TemplateComponent(
                        "side-slope-right",
                        "side_slope",
                        side="right",
                        width=8.0,
                        slope=-0.5,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [{"drop": 2.0, "width": 1.0, "slope": -0.02, "post_slope": -0.5}],
                            "repeat_first_bench_to_daylight": True,
                            "daylight_mode": "terrain",
                            "daylight_max_width": 20.0,
                            "daylight_search_step": 0.25,
                        },
                    ),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-bench-max-daylight",
        alignment_id="align-bench-max-daylight",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-bench-max-daylight")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-bench-max-daylight",
        alignment_id="align-bench-max-daylight",
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-bench-max-daylight",
        vertex_rows=[
            TINVertex("eg-0", 0.0, -30.0, 15.0),
            TINVertex("eg-1", 20.0, -30.0, 15.0),
            TINVertex("eg-2", 20.0, 20.0, 15.0),
            TINVertex("eg-3", 0.0, 20.0, 15.0),
        ],
        triangle_rows=[
            TINTriangle("eg-t0", "eg-0", "eg-1", "eg-2"),
            TINTriangle("eg-t1", "eg-0", "eg-2", "eg-3"),
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
            applied_section_id="sec-bench-max-daylight",
            existing_ground_surface=existing_ground,
        )
    )

    bench_points = [point for point in result.point_rows if point.point_role in {"side_slope_surface", "bench_surface", "daylight_marker"}]
    daylight_point = bench_points[-1]
    assert daylight_point.point_role == "daylight_marker"
    assert round(daylight_point.z, 2) == 15.0
    assert daylight_point.lateral_offset < -11.5
    assert not any(row.kind == "bench_daylight_no_hit" for row in result.diagnostic_rows)
    assert any(row.kind == "bench_daylight_shortened" for row in result.diagnostic_rows)


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


def test_applied_section_service_starts_benched_slope_after_ditch_outer_edge() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-bench-ditch",
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
        profile_id="prof-bench-ditch",
        alignment_id="align-bench-ditch",
        control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0)],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-bench-ditch",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-bench-ditch",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent("lane-right", "lane", component_index=1, side="right", width=3.5),
                    TemplateComponent("ditch-right", "ditch", component_index=2, side="right", width=1.0, slope=-0.04),
                    TemplateComponent(
                        "slope-right",
                        "side_slope",
                        component_index=3,
                        side="right",
                        width=4.0,
                        slope=-0.5,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [{"drop": 1.0, "width": 1.0, "slope": -0.02, "post_slope": -0.5}],
                        },
                    ),
                ],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-bench-ditch",
        alignment_id="align-bench-ditch",
        region_rows=[RegionRow("region-1", 0.0, 100.0, template_ref="tmpl-bench-ditch")],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-bench-ditch",
        alignment_id="align-bench-ditch",
    )

    result = AppliedSectionService().build(
        AppliedSectionBuildRequest(
            project_id="proj-1",
            corridor_id="cor-bench-ditch",
            alignment=alignment,
            profile=profile,
            assembly=assembly,
            region_model=region_model,
            override_model=override_model,
            station=10.0,
            applied_section_id="sec-bench-ditch",
        )
    )

    ditch_outer = min(
        (point for point in result.point_rows if point.point_role == "ditch_surface"),
        key=lambda point: point.lateral_offset,
    )
    slope_points = [
        point
        for point in result.point_rows
        if point.point_role in {"side_slope_surface", "bench_surface", "daylight_marker"}
    ]
    assert round(ditch_outer.lateral_offset, 2) == -4.50
    assert [round(point.lateral_offset, 2) for point in slope_points] == [-6.50, -7.50, -8.50, -8.50]
    assert round(slope_points[0].z, 2) == round(ditch_outer.z - 1.0, 2)


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


def test_applied_section_service_attaches_structure_context_rows() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-structure-context",
        geometry_sequence=[
            AlignmentElement("el-1", "tangent", station_start=0.0, station_end=100.0)
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-structure-context",
        alignment_id="align-structure-context",
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
        region_model_id="regions:structure-context",
        alignment_id="align-structure-context",
        region_rows=[RegionRow("region:main", station_start=0.0, station_end=100.0)],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="overrides:empty",
        alignment_id="align-structure-context",
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="align-structure-context",
        structure_rows=[
            StructureRow(
                "structure:bridge-01",
                "bridge",
                "interface",
                StructurePlacement("placement:bridge-01", "align-structure-context", 20.0, 40.0),
            )
        ],
        interaction_rule_rows=[
            StructureInteractionRule("rule:bridge-section", "structure:bridge-01", "section_handoff", "section")
        ],
        influence_zone_rows=[
            StructureInfluenceZone("zone:bridge-01", "structure:bridge-01", "clearance", 15.0, 45.0)
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
            station=30.0,
            applied_section_id="sec-structure-context",
            structure_model=structure_model,
        )
    )

    assert result.active_structure_ids == ["structure:bridge-01"]
    assert result.active_structure_rule_ids == ["rule:bridge-section"]
    assert result.active_structure_influence_zone_ids == ["zone:bridge-01"]
    assert result.structure_diagnostic_rows == []
    assert result.component_rows[0].structure_ids == ["structure:bridge-01"]


def test_applied_section_service_filters_structure_context_by_region_structure_ref() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-structure-filter",
        geometry_sequence=[
            AlignmentElement(
                "tangent-1",
                "tangent",
                0.0,
                100.0,
                length=100.0,
                geometry_payload={"x_values": [0.0, 100.0], "y_values": [0.0, 0.0]},
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="profile-structure-filter",
        alignment_id="align-structure-filter",
        control_rows=[
            ProfileControlPoint("pvi-1", 0.0, 10.0),
            ProfileControlPoint("pvi-2", 100.0, 12.0),
        ],
    )
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:road",
        active_template_id="template:road",
        template_rows=[
            SectionTemplate(
                template_id="template:road",
                template_kind="roadway",
                component_rows=[TemplateComponent(component_id="lane-1", kind="lane")],
            )
        ],
    )
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:structure-filter",
        alignment_id="align-structure-filter",
        region_rows=[
            RegionRow(
                region_id="region:main",
                station_start=0.0,
                station_end=100.0,
                assembly_ref="assembly:road",
                structure_ref="structure:bridge-01",
            )
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="align-structure-filter",
        structure_rows=[
            StructureRow("structure:bridge-01", "bridge", "interface", StructurePlacement("placement:bridge", "align-structure-filter", 20.0, 40.0)),
            StructureRow("structure:wall-01", "retaining_wall", "interface", StructurePlacement("placement:wall", "align-structure-filter", 20.0, 40.0)),
        ],
        interaction_rule_rows=[
            StructureInteractionRule("rule:bridge", "structure:bridge-01", "section_handoff", "section"),
            StructureInteractionRule("rule:wall", "structure:wall-01", "section_handoff", "section"),
        ],
        influence_zone_rows=[
            StructureInfluenceZone("zone:bridge", "structure:bridge-01", "clearance", 15.0, 45.0),
            StructureInfluenceZone("zone:wall", "structure:wall-01", "clearance", 15.0, 45.0),
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
            override_model=OverrideModel(schema_version=1, project_id="proj-1", override_model_id="overrides:empty"),
            station=30.0,
            applied_section_id="sec-structure-filter",
            structure_model=structure_model,
        )
    )

    assert result.active_structure_ids == ["structure:bridge-01"]
    assert result.active_structure_rule_ids == ["rule:bridge"]
    assert result.active_structure_influence_zone_ids == ["zone:bridge"]
    assert result.component_rows[0].structure_ids == ["structure:bridge-01"]


def test_structure_solid_output_service_builds_source_traceable_rows() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
        applied_section_set_ref="sections:main",
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=0.0),
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=4.0, z=2.0, tangent_direction_deg=10.0),
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:40",
                station=40.0,
                frame=AppliedSectionFrame(station=40.0, x=40.0, y=8.0, z=4.0, tangent_direction_deg=20.0),
            ),
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                "structure:bridge-01",
                "bridge",
                "interface",
                StructurePlacement("placement:bridge-01", "alignment:main", 10.0, 30.0),
                geometry_spec_ref="geometry-spec:bridge-01",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                "geometry-spec:bridge-01",
                "structure:bridge-01",
                width=12.0,
                height=1.2,
                material="concrete",
            )
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec("geometry-spec:bridge-01", deck_width=14.0, deck_thickness=1.5)
        ],
    )

    output = StructureSolidOutputService().build(
        StructureSolidBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied,
            structure_model=structure_model,
        )
    )

    assert isinstance(output, StructureSolidOutput)
    assert output.solid_rows[0].solid_kind == "bridge_deck_solid"
    assert output.solid_rows[0].structure_id == "structure:bridge-01"
    assert output.solid_rows[0].geometry_spec_id == "geometry-spec:bridge-01"
    assert output.solid_rows[0].path_source == "3d_centerline"
    assert output.solid_rows[0].width == 14.0
    assert output.solid_rows[0].height == 1.5
    assert output.solid_rows[0].volume == 420.0
    assert output.solid_rows[0].start_x == 10.0
    assert output.solid_rows[0].start_y == 2.0
    assert output.solid_rows[0].start_z == 1.0
    assert output.solid_rows[0].end_x == 30.0
    assert output.solid_rows[0].end_y == 6.0
    assert output.solid_rows[0].end_z == 3.0
    assert output.solid_rows[0].start_tangent_direction_deg == 5.0
    assert output.solid_rows[0].end_tangent_direction_deg == 15.0
    assert len(output.solid_segment_rows) == 2
    assert [row.station_start for row in output.solid_segment_rows] == [10.0, 20.0]
    assert [row.station_end for row in output.solid_segment_rows] == [20.0, 30.0]
    assert [row.segment_index for row in output.solid_segment_rows] == [1, 2]
    assert output.solid_segment_rows[0].end_x == 20.0
    assert output.solid_segment_rows[1].start_x == 20.0
    assert sum(row.volume for row in output.solid_segment_rows) == output.solid_rows[0].volume


def test_structure_solid_output_service_filters_by_applied_section_structure_ref() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
        applied_section_set_ref="sections:main",
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                station=20.0,
                assembly_id="assembly:bridge-deck",
                region_id="region:bridge-01",
                active_structure_ids=["structure:bridge-01"],
            )
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                "structure:bridge-01",
                "bridge",
                "interface",
                StructurePlacement("placement:bridge-01", "alignment:main", 10.0, 30.0),
                geometry_spec_ref="geometry-spec:bridge-01",
            ),
            StructureRow(
                "structure:wall-01",
                "retaining_wall",
                "interface",
                StructurePlacement("placement:wall-01", "alignment:main", 10.0, 30.0),
                geometry_spec_ref="geometry-spec:wall-01",
            ),
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:bridge-01", "structure:bridge-01", width=12.0, height=1.2),
            StructureGeometrySpec("geometry-spec:wall-01", "structure:wall-01", width=0.4, height=3.0),
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec("geometry-spec:bridge-01", deck_width=14.0, deck_thickness=1.5)
        ],
        retaining_wall_geometry_spec_rows=[
            RetainingWallGeometrySpec("geometry-spec:wall-01", wall_height=3.0, wall_thickness=0.4)
        ],
    )

    output = StructureSolidOutputService().build(
        StructureSolidBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied,
            structure_model=structure_model,
        )
    )

    assert [row.structure_id for row in output.solid_rows] == ["structure:bridge-01"]
    assert output.solid_rows[0].region_ref == "region:bridge-01"
    assert output.solid_rows[0].assembly_ref == "assembly:bridge-deck"
    assert output.solid_rows[0].structure_ref == "structure:bridge-01"
    assert output.solid_segment_rows[0].region_ref == "region:bridge-01"
    assert "structure:bridge-01" in output.source_refs
    assert "region:bridge-01" in output.source_refs
    assert "assembly:bridge-deck" in output.source_refs
    assert "structure:wall-01" not in output.source_refs


def test_quantity_build_service_adds_structure_quantity_fragments() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
            )
        ],
    )
    structure_solid_output = StructureSolidOutput(
        schema_version=1,
        project_id="proj-1",
        structure_solid_output_id="structure-solids:main",
        corridor_id="corridor:main",
        solid_rows=[
            StructureSolidOutputRow(
                output_object_id="solid:culvert-01",
                structure_id="structure:culvert-01",
                geometry_spec_id="geometry-spec:culvert-01",
                solid_kind="culvert_body_solid",
                station_start=10.0,
                station_end=20.0,
                width=3.0,
                height=2.0,
                length=10.0,
                volume=60.0,
            )
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                "structure:culvert-01",
                "culvert",
                "active",
                StructurePlacement("placement:culvert-01", "alignment:main", 10.0, 20.0),
                geometry_spec_ref="geometry-spec:culvert-01",
            )
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:culvert-01", "structure:culvert-01", width=3.0, height=2.0)
        ],
        culvert_geometry_spec_rows=[
            CulvertGeometrySpec(
                "geometry-spec:culvert-01",
                barrel_shape="box",
                barrel_count=2,
                span=3.0,
                rise=2.0,
                wall_thickness=0.25,
                headwall_type="straight",
                wingwall_type="flared",
            )
        ],
    )

    result = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="quantity:main",
            structure_solid_output=structure_solid_output,
            structure_model=structure_model,
        )
    )

    structure_rows = [
        row
        for row in result.fragment_rows
        if row.measurement_kind == "structure_solid_output"
    ]

    assert [row.quantity_kind for row in structure_rows] == [
        "culvert_barrel_volume",
        "culvert_opening_area",
        "culvert_barrel_count",
        "culvert_wall_volume",
        "culvert_headwall_count",
        "culvert_wingwall_count",
    ]
    assert [row.value for row in structure_rows] == [60.0, 6.0, 2.0, 27.5, 2.0, 4.0]
    assert all(row.structure_ref == "structure:culvert-01" for row in structure_rows)
    assert "structure-solids:main" in result.source_refs


def test_quantity_build_service_uses_singular_component_structure_ref() -> None:
    corridor = CorridorModel(schema_version=1, project_id="proj-1", corridor_id="corridor:main")
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                region_id="region:main",
                component_rows=[
                    AppliedSectionComponentRow(
                        component_id="lane-1",
                        kind="lane",
                        structure_ids=["structure:bridge-01", "structure:wall-01"],
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
            quantity_model_id="quantity:main",
        )
    )

    assert result.fragment_rows[0].structure_ref == "structure:bridge-01"


def test_quantity_build_service_adds_bridge_and_wall_detail_fragments() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="corridor:main",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
        sections=[AppliedSection(schema_version=1, project_id="proj-1", applied_section_id="section:0", station=0.0)],
    )
    structure_solid_output = StructureSolidOutput(
        schema_version=1,
        project_id="proj-1",
        structure_solid_output_id="structure-solids:main",
        corridor_id="corridor:main",
        solid_rows=[
            StructureSolidOutputRow(
                output_object_id="solid:bridge-01",
                structure_id="structure:bridge-01",
                geometry_spec_id="geometry-spec:bridge-01",
                solid_kind="bridge_deck_solid",
                station_start=0.0,
                station_end=20.0,
                width=12.0,
                height=1.0,
                length=20.0,
                volume=240.0,
            ),
            StructureSolidOutputRow(
                output_object_id="solid:wall-01",
                structure_id="structure:wall-01",
                geometry_spec_id="geometry-spec:wall-01",
                solid_kind="retaining_wall_solid",
                station_start=0.0,
                station_end=20.0,
                width=0.5,
                height=4.0,
                length=20.0,
                volume=40.0,
            ),
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        structure_rows=[
            StructureRow(
                "structure:bridge-01",
                "bridge",
                "active",
                StructurePlacement("placement:bridge-01", "alignment:main", 0.0, 20.0),
                geometry_spec_ref="geometry-spec:bridge-01",
            ),
            StructureRow(
                "structure:wall-01",
                "retaining_wall",
                "active",
                StructurePlacement("placement:wall-01", "alignment:main", 0.0, 20.0),
                geometry_spec_ref="geometry-spec:wall-01",
            ),
        ],
        geometry_spec_rows=[
            StructureGeometrySpec("geometry-spec:bridge-01", "structure:bridge-01", width=12.0, height=1.0),
            StructureGeometrySpec("geometry-spec:wall-01", "structure:wall-01", width=0.5, height=4.0),
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec(
                "geometry-spec:bridge-01",
                deck_width=12.0,
                deck_thickness=1.0,
                girder_depth=1.5,
                barrier_height=1.0,
                abutment_start_offset=0.5,
                abutment_end_offset=0.5,
                pier_station_refs=["pier:10"],
                approach_slab_length=5.0,
            )
        ],
        retaining_wall_geometry_spec_rows=[
            RetainingWallGeometrySpec(
                "geometry-spec:wall-01",
                wall_height=4.0,
                wall_thickness=0.5,
                footing_width=1.5,
                footing_thickness=0.4,
                coping_height=0.2,
                drainage_layer_ref="drainage:wall-01",
            )
        ],
    )

    result = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="quantity:main",
            structure_solid_output=structure_solid_output,
            structure_model=structure_model,
        )
    )

    rows = [row for row in result.fragment_rows if row.measurement_kind == "structure_solid_output"]
    by_kind = {row.quantity_kind: row for row in rows}
    assert by_kind["bridge_deck_volume"].value == 240.0
    assert by_kind["bridge_girder_depth_length"].value == 30.0
    assert by_kind["bridge_barrier_face_area"].value == 40.0
    assert by_kind["bridge_approach_slab_area"].value == 120.0
    assert by_kind["bridge_support_count"].value == 3.0
    assert by_kind["wall_body_volume"].value == 40.0
    assert by_kind["wall_footing_volume"].value == 12.0
    assert by_kind["wall_coping_volume"].value == 2.0
    assert by_kind["wall_drainage_layer_length"].value == 20.0
    assert by_kind["bridge_deck_volume"].structure_ref == "structure:bridge-01"
    assert by_kind["wall_body_volume"].structure_ref == "structure:wall-01"


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


def test_corridor_surface_geometry_service_uses_bench_breakline_points_for_daylight_surface() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench",
        corridor_id="cor-bench",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=3.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.5, 8.0, "side_slope_surface", -7.5),
                    AppliedSectionPoint("bench:right:1", 0.0, -8.0, 7.99, "bench_surface", -8.0),
                    AppliedSectionPoint("daylight:right", 0.0, -8.0, 7.99, "daylight_marker", -8.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 11.0, 0.0),
                surface_right_width=3.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 10.0, -7.5, 9.0, "side_slope_surface", -7.5),
                    AppliedSectionPoint("bench:right:1", 10.0, -8.0, 8.99, "bench_surface", -8.0),
                    AppliedSectionPoint("daylight:right", 10.0, -8.0, 8.99, "daylight_marker", -8.0),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-bench:daylight",
        )
    )

    quality = {row.kind: row.value for row in result.quality_rows}
    vertices = result.vertex_map()
    assert result.surface_kind == "daylight_surface"
    assert len(result.triangle_rows) == 4
    assert quality["bench_breakline_count"] == 2
    assert quality["daylight_marker_count"] == 2
    assert vertices["v0:right:r0:p0"].y == -3.5
    assert vertices["v0:right:r0:p2"].notes == "bench_surface"
    assert vertices["v0:right:r1:p2"].z == 8.99


def test_corridor_surface_geometry_service_orients_benched_daylight_triangles_up_on_both_sides() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-orientation",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-orientation",
        corridor_id="cor-bench-orientation",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:left:1", 0.0, 7.0, 8.5, "side_slope_surface", 7.0),
                    AppliedSectionPoint("bench:left:1", 0.0, 8.0, 8.45, "bench_surface", 8.0),
                    AppliedSectionPoint("daylight:left", 0.0, 9.0, 8.0, "daylight_marker", 9.0),
                    AppliedSectionPoint("slope:right:1", 0.0, -6.0, 8.8, "side_slope_surface", -6.0),
                    AppliedSectionPoint("bench:right:1", 0.0, -7.0, 8.75, "bench_surface", -7.0),
                    AppliedSectionPoint("daylight:right", 0.0, -8.0, 8.0, "daylight_marker", -8.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 11.0, 0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:left:1", 10.0, 7.0, 9.5, "side_slope_surface", 7.0),
                    AppliedSectionPoint("bench:left:1", 10.0, 8.0, 9.45, "bench_surface", 8.0),
                    AppliedSectionPoint("daylight:left", 10.0, 9.0, 9.0, "daylight_marker", 9.0),
                    AppliedSectionPoint("slope:right:1", 10.0, -6.0, 9.8, "side_slope_surface", -6.0),
                    AppliedSectionPoint("bench:right:1", 10.0, -7.0, 9.75, "bench_surface", -7.0),
                    AppliedSectionPoint("daylight:right", 10.0, -8.0, 9.0, "daylight_marker", -8.0),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-bench-orientation:daylight",
        )
    )

    assert {":left:" in row.triangle_id for row in result.triangle_rows} == {False, True}
    assert min(_triangle_normal_z(result, triangle) for triangle in result.triangle_rows) > 0.0


def test_corridor_surface_geometry_service_preserves_applied_daylight_line_when_eg_exists() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-cut-rebuild",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-cut-rebuild",
        corridor_id="cor-bench-cut-rebuild",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                daylight_right_width=8.0,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:wrong", 0.0, -7.5, 8.0, "side_slope_surface", -7.5),
                    AppliedSectionPoint("daylight:right:wrong", 0.0, -7.5, 8.0, "daylight_marker", -7.5),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                daylight_right_width=8.0,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:wrong", 10.0, -7.5, 8.0, "side_slope_surface", -7.5),
                    AppliedSectionPoint("daylight:right:wrong", 10.0, -7.5, 8.0, "daylight_marker", -7.5),
                ],
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-cut-rebuild",
        vertex_rows=[
            TINVertex("eg-0", -1.0, -20.0, 12.0),
            TINVertex("eg-1", 11.0, -20.0, 12.0),
            TINVertex("eg-2", 11.0, 5.0, 12.0),
            TINVertex("eg-3", -1.0, 5.0, 12.0),
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
            surface_id="cor-bench-cut-rebuild:daylight",
            existing_ground_surface=existing_ground,
        )
    )

    vertices = result.vertex_map()
    quality = {row.kind: row.value for row in result.quality_rows}
    assert vertices["v0:right:r0:p0"].y == -4.0
    assert abs(vertices["v0:right:r0:p1"].y - -7.5) < 1.0e-6
    assert abs(vertices["v0:right:r0:p1"].z - 8.0) < 1.0e-6
    assert quality["daylight_marker_count"] == 2


def test_corridor_surface_geometry_service_preserves_bench_breakline_when_retying_cut_daylight() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-cut-preserve",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-cut-preserve",
        corridor_id="cor-bench-cut-preserve",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                daylight_right_width=8.0,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 0.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 0.0, -8.5, 8.47, "daylight_marker", -8.5),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                daylight_right_width=8.0,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 10.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 10.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 10.0, -8.5, 8.47, "daylight_marker", -8.5),
                ],
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-cut-preserve",
        vertex_rows=[
            TINVertex("eg-0", -1.0, -20.0, 15.0),
            TINVertex("eg-1", 11.0, -20.0, 15.0),
            TINVertex("eg-2", 11.0, 5.0, 15.0),
            TINVertex("eg-3", -1.0, 5.0, 15.0),
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
            surface_id="cor-bench-cut-preserve:daylight",
            existing_ground_surface=existing_ground,
        )
    )

    quality = {row.kind: row.value for row in result.quality_rows}
    assert quality["bench_breakline_count"] == 2
    daylight_vertices = [vertex for vertex in result.vertex_rows if vertex.notes == "daylight_marker"]
    assert daylight_vertices
    assert all(abs(vertex.y - -8.5) < 1.0e-6 for vertex in daylight_vertices)
    assert len(result.triangle_rows) >= 4


def test_corridor_surface_geometry_service_preserves_benched_profile_daylight_after_bench() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-piecewise",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-piecewise",
        corridor_id="cor-bench-piecewise",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                daylight_right_width=8.0,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 0.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("slope:right:2", 0.0, -9.5, 7.97, "side_slope_surface", -9.5),
                    AppliedSectionPoint("daylight:right", 0.0, -9.5, 7.97, "daylight_marker", -9.5),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                daylight_right_width=8.0,
                daylight_right_slope=-0.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 10.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 10.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("slope:right:2", 10.0, -9.5, 7.97, "side_slope_surface", -9.5),
                    AppliedSectionPoint("daylight:right", 10.0, -9.5, 7.97, "daylight_marker", -9.5),
                ],
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-piecewise",
        vertex_rows=[
            TINVertex("eg-0", -1.0, -20.0, 12.0),
            TINVertex("eg-1", 11.0, -20.0, 12.0),
            TINVertex("eg-2", 11.0, 5.0, 12.0),
            TINVertex("eg-3", -1.0, 5.0, 12.0),
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
            surface_id="cor-bench-piecewise:daylight",
            existing_ground_surface=existing_ground,
        )
    )

    daylight_vertices = [vertex for vertex in result.vertex_rows if vertex.notes == "daylight_marker"]
    assert daylight_vertices
    assert all(vertex.y < -8.5 for vertex in daylight_vertices)
    assert all(abs(vertex.z - 7.97) < 1.0e-6 for vertex in daylight_vertices)


def test_corridor_surface_geometry_service_keeps_bench_when_adjacent_station_has_fewer_breaks() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-variable",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-variable",
        corridor_id="cor-bench-variable",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 0.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 0.0, -9.0, 8.2, "daylight_marker", -9.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("daylight:right", 10.0, -7.5, 8.25, "daylight_marker", -7.5),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-bench-variable:daylight",
        )
    )

    quality = {row.kind: row.value for row in result.quality_rows}
    assert quality["bench_breakline_count"] == 1
    assert any(vertex.notes == "bench_surface" for vertex in result.vertex_rows)
    assert len(result.triangle_rows) >= 2
    assert not any(triangle.notes == "daylight_transition_cap" for triangle in result.triangle_rows)
    assert min(_triangle_normal_z(result, triangle) for triangle in result.triangle_rows) > 0.0


def test_corridor_surface_geometry_service_uses_supplemental_sampling_between_daylight_contacts() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-densified-contact",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-densified-contact",
        corridor_id="cor-bench-densified-contact",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-20", 20.0, "sec-20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 0.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 0.0, -9.0, 10.0, "daylight_marker", -9.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-20",
                frame=AppliedSectionFrame(20.0, 20.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 20.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 20.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 20.0, -9.0, 12.0, "daylight_marker", -9.0),
                ],
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-densified-contact",
        vertex_rows=[
            TINVertex("eg-0", -5.0, -20.0, 10.0),
            TINVertex("eg-1", 25.0, -20.0, 13.0),
            TINVertex("eg-2", 25.0, 5.0, 13.0),
            TINVertex("eg-3", -5.0, 5.0, 10.0),
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
            surface_id="cor-bench-densified-contact:daylight",
            existing_ground_surface=existing_ground,
            supplemental_sampling_enabled=True,
        )
    )

    daylight_vertices = [vertex for vertex in result.vertex_rows if vertex.notes == "daylight_marker"]
    quality = {row.kind: row.value for row in result.quality_rows}
    assert len(daylight_vertices) > 2
    assert len(result.triangle_rows) > 4
    assert any(10.0 < vertex.z < 13.0 for vertex in daylight_vertices)
    assert quality["daylight_marker_count"] > 2


def test_corridor_surface_geometry_service_supplemental_sampling_keeps_mismatched_side_slope_rows() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-supplemental-mismatch",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-supplemental-mismatch",
        corridor_id="cor-bench-supplemental-mismatch",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-20", 20.0, "sec-20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("daylight:right", 0.0, -18.0, 10.0, "daylight_marker", -18.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-20",
                frame=AppliedSectionFrame(20.0, 20.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 20.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 20.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 20.0, -9.0, 8.2, "daylight_marker", -9.0),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-bench-supplemental-mismatch:daylight",
            supplemental_sampling_enabled=True,
            supplemental_sampling_max_spacing=5.0,
        )
    )

    quality = {row.kind: row.value for row in result.quality_rows}
    provenance = {row.source_kind for row in result.provenance_rows}
    assert quality["station_count"] > 2
    assert quality["daylight_marker_count"] > 2
    assert min(vertex.y for vertex in result.vertex_rows) <= -17.999999
    assert "applied_section_side_slope_points" in provenance
    assert not any("supplemental" in vertex.source_point_ref and vertex.notes == "" for vertex in result.vertex_rows)


def test_corridor_surface_geometry_service_uses_shared_station_breaks_across_adjacent_daylight_spans() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-shared-breaks",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-shared-breaks",
        corridor_id="cor-bench-shared-breaks",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
            AppliedSectionStationRow("sta-20", 20.0, "sec-20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("daylight:right", 0.0, -7.0, 8.5, "daylight_marker", -7.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 10.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 10.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("daylight:right", 10.0, -9.0, 8.2, "daylight_marker", -9.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-20",
                frame=AppliedSectionFrame(20.0, 20.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 20.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("bench:right:1", 20.0, -8.5, 8.47, "bench_surface", -8.5),
                    AppliedSectionPoint("slope:right:2", 20.0, -10.0, 7.72, "side_slope_surface", -10.0),
                    AppliedSectionPoint("daylight:right", 20.0, -10.0, 7.72, "daylight_marker", -10.0),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-bench-shared-breaks:daylight",
        )
    )

    first_span_boundary = _surface_vertices_by_prefix(result, "v0:right:r1:p")
    second_span_boundary = _surface_vertices_by_prefix(result, "v1:right:r0:p")
    assert first_span_boundary
    assert second_span_boundary
    assert not any(triangle.notes == "daylight_transition_cap" for triangle in result.triangle_rows)


def test_corridor_surface_geometry_service_connects_applied_daylight_rows_without_span_rule() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-daylight-tear-fill",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-daylight-tear-fill",
        corridor_id="cor-daylight-tear-fill",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow("sta-0", 0.0, "sec-0"),
            AppliedSectionStationRow("sta-10", 10.0, "sec-10"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-0",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("daylight:right", 0.0, -18.0, 10.0, "daylight_marker", -18.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-10",
                frame=AppliedSectionFrame(10.0, 10.0, 0.0, 10.0, 0.0),
                surface_right_width=4.0,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 10.0, -7.0, 8.5, "side_slope_surface", -7.0),
                    AppliedSectionPoint("daylight:right", 10.0, -8.0, 9.0, "daylight_marker", -8.0),
                ],
            ),
        ],
    )
    existing_ground = TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="tin:eg-daylight-tear-fill",
        vertex_rows=[
            TINVertex("eg-0", -5.0, -35.0, 10.0),
            TINVertex("eg-1", 15.0, -35.0, 11.0),
            TINVertex("eg-2", 15.0, 5.0, 11.0),
            TINVertex("eg-3", -5.0, 5.0, 10.0),
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
            surface_id="cor-daylight-tear-fill:daylight",
            existing_ground_surface=existing_ground,
        )
    )

    vertices = list(result.vertex_rows)
    miter_vertices = [vertex for vertex in vertices if "upstream-slope-miter" in vertex.source_point_ref]
    quality = {row.kind: row.value for row in result.quality_rows}
    assert not miter_vertices
    assert min(vertex.y for vertex in vertices) <= -17.999999
    assert not any(triangle.triangle_id.endswith(":fan") for triangle in result.triangle_rows)
    assert not any(triangle.triangle_kind == "corridor_daylight_taper_cap" for triangle in result.triangle_rows)
    assert "daylight_taper_cap_triangle_count" not in quality


def test_corridor_surface_geometry_service_starts_daylight_from_ditch_outer_edges() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-ditch-daylight",
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
        applied_section_set_id="set-ditch-daylight",
        corridor_id="cor-ditch-daylight",
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
                point_rows=[
                    AppliedSectionPoint("fg:right", 0.0, -4.0, 10.0, "fg_surface", -4.0),
                    AppliedSectionPoint("fg:left", 0.0, 5.0, 10.0, "fg_surface", 5.0),
                    AppliedSectionPoint("ditch:right-flow", 0.0, -5.2, 9.7, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 0.0, -4.0, 10.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 0.0, 5.0, 10.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 0.0, 6.2, 9.7, "ditch_surface", 6.2),
                ],
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
                point_rows=[
                    AppliedSectionPoint("fg:right", 10.0, -4.0, 11.0, "fg_surface", -4.0),
                    AppliedSectionPoint("fg:left", 10.0, 5.0, 11.0, "fg_surface", 5.0),
                    AppliedSectionPoint("ditch:right-flow", 10.0, -5.2, 10.7, "ditch_surface", -5.2),
                    AppliedSectionPoint("ditch:right-edge", 10.0, -4.0, 11.0, "ditch_surface", -4.0),
                    AppliedSectionPoint("ditch:left-edge", 10.0, 5.0, 11.0, "ditch_surface", 5.0),
                    AppliedSectionPoint("ditch:left-flow", 10.0, 6.2, 10.7, "ditch_surface", 6.2),
                ],
            ),
        ],
    )

    result = CorridorSurfaceGeometryService().build_daylight_surface(
        CorridorDesignSurfaceGeometryRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            surface_id="cor-ditch-daylight:daylight",
        )
    )

    vertices = result.vertex_map()
    assert abs(vertices["v0:left:inner"].y - 6.2) < 1e-9
    assert abs(vertices["v0:right:inner"].y - -5.2) < 1e-9
    assert abs(vertices["v0:left:inner"].z - 9.7) < 1e-9
    assert abs(vertices["v0:right:inner"].z - 9.7) < 1e-9
    assert abs(vertices["v0:left:outer"].y - 9.2) < 1e-9
    assert abs(vertices["v0:right:outer"].y - -7.2) < 1e-9


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


def test_corridor_surface_geometry_service_orients_slope_face_up_for_cut_intersections() -> None:
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
        surface_id="tin:eg-flat-cut",
        vertex_rows=[
            TINVertex("eg-0", -1.0, -20.0, 12.0),
            TINVertex("eg-1", 11.0, -20.0, 12.0),
            TINVertex("eg-2", 11.0, 20.0, 12.0),
            TINVertex("eg-3", -1.0, 20.0, 12.0),
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
    assert abs(vertices["v0:left:outer"].z - 12.0) < 1e-6
    assert abs(vertices["v0:right:outer"].z - 12.0) < 1e-6
    quality = {row.kind: row.value for row in result.quality_rows}
    assert quality["eg_intersection_count"] == 4
    assert quality["slope_face_fallback_count"] == 0
    assert min(_triangle_normal_z(result, triangle) for triangle in result.triangle_rows) > 0.0


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


def test_quantity_build_service_adds_bench_and_slope_face_length_fragments() -> None:
    corridor = CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-bench-qty",
        alignment_id="align-1",
        profile_id="prof-1",
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="set-bench-qty",
        corridor_id="cor-bench-qty",
        alignment_id="align-1",
        station_rows=[AppliedSectionStationRow("sta-1", 0.0, "sec-bench-qty")],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="sec-bench-qty",
                corridor_id="cor-bench-qty",
                alignment_id="align-1",
                profile_id="prof-1",
                assembly_id="assembly-bench",
                station=0.0,
                region_id="region-bench",
                frame=AppliedSectionFrame(0.0, 0.0, 0.0, 10.0, 0.0),
                surface_right_width=3.5,
                point_rows=[
                    AppliedSectionPoint("slope:right:1", 0.0, -7.5, 8.0, "side_slope_surface", -7.5),
                    AppliedSectionPoint("bench:right:1", 0.0, -8.0, 7.99, "bench_surface", -8.0),
                    AppliedSectionPoint("daylight:right", 0.0, -8.0, 7.99, "daylight_marker", -8.0),
                ],
            )
        ],
    )

    result = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="qty-bench",
        )
    )

    rows = {row.quantity_kind: row for row in result.fragment_rows}
    assert abs(rows["slope_face_length"].value - (4.0**2 + 2.0**2) ** 0.5) < 1.0e-9
    assert abs(rows["bench_surface_length"].value - (0.5**2 + 0.01**2) ** 0.5) < 1.0e-9
    assert rows["bench_surface_length"].measurement_kind == "section_side_slope_breakline"
    assert rows["bench_surface_length"].assembly_ref == "assembly-bench"
    assert rows["bench_surface_length"].region_ref == "region-bench"


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
