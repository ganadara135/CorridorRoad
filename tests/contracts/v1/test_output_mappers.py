from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
    VerticalCurveRow,
)
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
    AppliedSectionQuantityFragment,
)
from freecad.Corridor_Road.v1.models.result.earthwork_balance_model import (
    EarthworkBalanceModel,
    EarthworkBalanceRow,
)
from freecad.Corridor_Road.v1.models.result.quantity_model import (
    QuantityAggregate,
    QuantityFragment,
    QuantityModel,
)
from freecad.Corridor_Road.v1.models.result.surface_model import (
    SurfaceBuildRelation,
    SurfaceModel,
    SurfaceRow,
)
from freecad.Corridor_Road.v1.models.output import (
    StructureExportDiagnosticRow,
    StructureSolidOutput,
    StructureSolidOutputRow,
    StructureSolidSegmentRow,
)
from freecad.Corridor_Road.v1.services.mapping import (
    EarthworkOutputMapper,
    ExchangeOutputMapper,
    ExchangePackageRequest,
    PlanOutputMapper,
    ProfileOutputMapper,
    QuantityOutputMapper,
    SectionOutputMapper,
    SurfaceOutputMapper,
)


def test_section_output_mapper_maps_components_and_quantities() -> None:
    applied_section = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="sec-1",
        alignment_id="align-1",
        station=10.0,
        component_rows=[
            AppliedSectionComponentRow(
                component_id="lane-1",
                kind="lane",
                source_template_id="tmpl-1",
                region_id="region-1",
            )
        ],
        quantity_rows=[
            AppliedSectionQuantityFragment(
                fragment_id="q-1",
                quantity_kind="pavement_quantity",
                value=12.0,
                unit="m2",
                component_id="lane-1",
            )
        ],
        point_rows=[
            AppliedSectionPoint("p-1", -5.0, 0.0, 10.0),
            AppliedSectionPoint("p-2", 5.0, 0.0, 10.0),
        ],
        frame=AppliedSectionFrame(
            station=10.0,
            x=1000.0,
            y=2000.0,
            z=12.5,
            tangent_direction_deg=15.0,
            profile_grade=0.025,
            alignment_status="ok",
            profile_status="ok",
        ),
    )

    output = SectionOutputMapper().map_applied_section(applied_section)

    assert output.section_output_id == "sec-1"
    assert output.component_rows[0].template_ref == "tmpl-1"
    assert output.quantity_rows[0].component_ref == "lane-1"
    assert output.geometry_rows[0].kind == "design_section"
    assert output.geometry_rows[0].x_values == [-5.0, 5.0]
    assert output.geometry_rows[0].z_values == [10.0, 10.0]
    summary_by_kind = {row.kind: row for row in output.summary_rows}
    assert summary_by_kind["frame_x"].value == 1000.0
    assert summary_by_kind["frame_z"].value == 12.5
    assert summary_by_kind["profile_grade"].value == 0.025
    assert summary_by_kind["frame_status"].value == "alignment=ok; profile=ok"


def test_section_output_mapper_marks_bench_rows_as_side_slope_scope() -> None:
    applied_section = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="sec-bench",
        alignment_id="align-1",
        assembly_id="assembly:bench-road",
        station=10.0,
        component_rows=[
            AppliedSectionComponentRow(
                component_id="side-slope-right:bench:1",
                kind="bench",
                source_template_id="tmpl-1",
                region_id="region-1",
                side="right",
                width=1.0,
                slope=-0.02,
            ),
            AppliedSectionComponentRow(
                component_id="side-slope-right:daylight",
                kind="daylight",
                source_template_id="tmpl-1",
                region_id="region-1",
                side="right",
            ),
        ],
        point_rows=[
            AppliedSectionPoint("slope:right:1", 10.0, -7.5, 8.0, "side_slope_surface", -7.5),
            AppliedSectionPoint("bench:right:1", 10.0, -8.0, 7.99, "bench_surface", -8.0),
            AppliedSectionPoint("daylight:right", 10.0, -8.0, 7.99, "daylight_marker", -8.0),
        ],
    )

    output = SectionOutputMapper().map_applied_section(applied_section)

    assert output.component_rows[0].notes == "scope=side_slope; side=right"
    assert output.component_rows[0].assembly_ref == "assembly:bench-road"
    assert output.component_rows[1].notes == "scope=side_slope; side=right"
    geometry_by_kind = {row.kind: row for row in output.geometry_rows}
    assert geometry_by_kind["bench_section"].style_role == "side_slope_bench"
    assert geometry_by_kind["bench_section"].x_values == [-8.0]
    assert geometry_by_kind["daylight_marker"].style_role == "side_slope"


def test_surface_output_mapper_maps_surface_rows() -> None:
    surface_model = SurfaceModel(
        schema_version=1,
        project_id="proj-1",
        surface_model_id="surf-1",
        corridor_id="cor-1",
        surface_rows=[
            SurfaceRow(
                surface_id="surf-design",
                surface_kind="design_surface",
                tin_ref="surf-design:tin",
            )
        ],
        build_relation_rows=[
            SurfaceBuildRelation(
                build_relation_id="rel-1",
                surface_ref="surf-design",
                relation_kind="corridor_build",
            )
        ],
    )

    output = SurfaceOutputMapper().map_surface_model(surface_model)

    assert output.surface_output_id == "surf-1"
    assert output.surface_rows[0].surface_kind == "design_surface"


def test_quantity_output_mapper_maps_fragments_and_aggregates() -> None:
    quantity_model = QuantityModel(
        schema_version=1,
        project_id="proj-1",
        quantity_model_id="qty-1",
        corridor_id="cor-1",
        fragment_rows=[
            QuantityFragment(
                fragment_id="frag-1",
                quantity_kind="component_quantity",
                measurement_kind="area",
                value=100.0,
                unit="m2",
                component_ref="lane-1",
                assembly_ref="assembly:road",
                structure_ref="structure:bridge-01",
            )
        ],
        aggregate_rows=[
            QuantityAggregate(
                aggregate_id="agg-1",
                aggregate_kind="component_total",
                grouping_ref="grp-1",
                value=100.0,
                unit="m2",
                fragment_refs=["frag-1"],
            )
        ],
    )

    output = QuantityOutputMapper().map_quantity_model(quantity_model)

    assert output.quantity_output_id == "qty-1"
    assert output.fragment_rows[0].component_ref == "lane-1"
    assert output.fragment_rows[0].assembly_ref == "assembly:road"
    assert output.fragment_rows[0].structure_ref == "structure:bridge-01"
    assert output.aggregate_rows[0].fragment_refs == ["frag-1"]


def test_earthwork_output_mapper_maps_balance_rows() -> None:
    earthwork_model = EarthworkBalanceModel(
        schema_version=1,
        project_id="proj-1",
        earthwork_balance_id="ew-1",
        corridor_id="cor-1",
        balance_rows=[
            EarthworkBalanceRow(
                balance_row_id="bal-1",
                station_start=0.0,
                station_end=20.0,
                cut_value=50.0,
                fill_value=30.0,
                balance_ratio=1.5,
            )
        ],
    )

    output = EarthworkOutputMapper().map_earthwork_balance(earthwork_model)

    assert output.earthwork_output_id == "ew-1"
    assert output.balance_rows[0].cut_value == 50.0
    assert output.summary_rows[0].kind == "total_cut"


def test_plan_output_mapper_maps_alignment_geometry() -> None:
    alignment_model = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-1",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=50.0,
                geometry_payload={
                    "x_values": [1000.0, 1050.0],
                    "y_values": [2000.0, 2000.0],
                },
            )
        ],
    )

    output = PlanOutputMapper().map_alignment_model(alignment_model)

    assert output.plan_output_id == "align-1"
    assert output.geometry_rows[0].x_values == [1000.0, 1050.0]
    assert output.station_rows[0].x == 1000.0
    assert output.station_rows[-1].x == 1050.0
    assert len(output.station_rows) == 4


def test_profile_output_mapper_maps_control_rows_and_earthwork() -> None:
    profile_model = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-1",
        alignment_id="align-1",
        control_rows=[
            ProfileControlPoint(
                control_point_id="pvi-1",
                station=0.0,
                elevation=10.0,
            ),
            ProfileControlPoint(
                control_point_id="pvi-2",
                station=100.0,
                elevation=12.0,
            ),
        ],
    )
    earthwork_model = EarthworkBalanceModel(
        schema_version=1,
        project_id="proj-1",
        earthwork_balance_id="ew-1",
        corridor_id="cor-1",
        balance_rows=[
            EarthworkBalanceRow(
                balance_row_id="bal-1",
                station_start=0.0,
                station_end=20.0,
                cut_value=50.0,
                fill_value=30.0,
                usable_cut_value=40.0,
            )
        ],
    )

    output = ProfileOutputMapper().map_profile_model(profile_model, earthwork_model)

    assert output.profile_output_id == "prof-1"
    assert output.line_rows[0].station_values == [0.0, 100.0]
    assert output.earthwork_rows[0].value == 10.0


def test_profile_output_mapper_can_sample_parabolic_finished_grade_line() -> None:
    profile_model = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-curve",
        alignment_id="align-1",
        control_rows=[
            ProfileControlPoint("pvi-0", 0.0, 10.0),
            ProfileControlPoint("pvi-50", 50.0, 15.0),
            ProfileControlPoint("pvi-100", 100.0, 12.5),
        ],
        vertical_curve_rows=[
            VerticalCurveRow(
                vertical_curve_id="curve-1",
                kind="parabolic_vertical_curve",
                station_start=40.0,
                station_end=60.0,
                curve_length=20.0,
            )
        ],
    )

    output = ProfileOutputMapper().map_profile_model(
        profile_model,
        station_interval=20.0,
    )

    line = output.line_rows[0]
    station_to_elevation = dict(zip(line.station_values, line.elevation_values))
    assert line.kind == "finished_grade_line"
    assert 40.0 in station_to_elevation
    assert 60.0 in station_to_elevation
    assert abs(station_to_elevation[40.0] - 14.0) < 1e-9
    assert abs(station_to_elevation[60.0] - 14.5) < 1e-9


def test_exchange_output_mapper_packages_multiple_outputs() -> None:
    plan_output = PlanOutputMapper().map_alignment_model(
        AlignmentModel(
            schema_version=1,
            project_id="proj-1",
            alignment_id="align-1",
        )
    )
    profile_output = ProfileOutputMapper().map_profile_model(
        ProfileModel(
            schema_version=1,
            project_id="proj-1",
            profile_id="prof-1",
            alignment_id="align-1",
        )
    )

    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id="proj-1",
            exchange_output_id="pkg-1",
            format="landxml",
            package_kind="engineering_exchange",
            outputs=[plan_output, profile_output],
        )
    )

    assert exchange_output.exchange_output_id == "pkg-1"
    assert len(exchange_output.output_refs) == 2
    assert exchange_output.payload_metadata["output_count"] == 2


def test_exchange_output_mapper_packages_structure_solid_output_geometry() -> None:
    structure_output = StructureSolidOutput(
        schema_version=1,
        project_id="proj-1",
        structure_solid_output_id="structure-solids:main",
        corridor_id="corridor:main",
        structure_model_id="structures:main",
        source_refs=["structures:main"],
        result_refs=["corridor:main"],
        solid_rows=[
            StructureSolidOutputRow(
                output_object_id="solid:bridge-01",
                structure_id="structure:bridge-01",
                geometry_spec_id="geometry-spec:bridge-01",
                solid_kind="bridge_deck_solid",
                station_start=10.0,
                station_end=30.0,
                path_source="3d_centerline",
                material="concrete",
                width=14.0,
                height=1.5,
                length=20.0,
                volume=420.0,
                region_ref="region:bridge-01",
                assembly_ref="assembly:bridge-deck",
                structure_ref="structure:bridge-01",
            )
        ],
        solid_segment_rows=[
            StructureSolidSegmentRow(
                segment_id="solid:bridge-01:segment:1",
                parent_output_object_id="solid:bridge-01",
                structure_id="structure:bridge-01",
                geometry_spec_id="geometry-spec:bridge-01",
                segment_index=1,
                station_start=10.0,
                station_end=20.0,
                start_x=10.0,
                start_y=0.0,
                start_z=0.0,
                end_x=20.0,
                end_y=2.0,
                end_z=1.0,
                length=10.0,
                volume=210.0,
                region_ref="region:bridge-01",
                assembly_ref="assembly:bridge-deck",
                structure_ref="structure:bridge-01",
            ),
            StructureSolidSegmentRow(
                segment_id="solid:bridge-01:segment:2",
                parent_output_object_id="solid:bridge-01",
                structure_id="structure:bridge-01",
                geometry_spec_id="geometry-spec:bridge-01",
                segment_index=2,
                station_start=20.0,
                station_end=30.0,
                start_x=20.0,
                start_y=2.0,
                start_z=1.0,
                end_x=30.0,
                end_y=4.0,
                end_z=2.0,
                length=10.0,
                volume=210.0,
                region_ref="region:bridge-01",
                assembly_ref="assembly:bridge-deck",
                structure_ref="structure:bridge-01",
            ),
        ],
        diagnostic_rows=[
            StructureExportDiagnosticRow(
                diagnostic_id="structure-export:simplified_ifc_geometry:bridge-01",
                severity="warning",
                kind="simplified_ifc_geometry",
                structure_id="structure:bridge-01",
                geometry_spec_id="geometry-spec:bridge-01",
                output_object_id="solid:bridge-01",
                message="IFC export will use a simplified rectangular swept solid proxy.",
            )
        ],
    )

    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id="proj-1",
            exchange_output_id="pkg-structures",
            format="ifc",
            package_kind="structure_geometry_exchange",
            outputs=[structure_output],
        )
    )

    assert exchange_output.output_refs[0].output_kind == "structuresolid"
    assert exchange_output.output_refs[0].output_id == "structure-solids:main"
    assert exchange_output.payload_metadata["structure_solid_count"] == 1
    assert exchange_output.payload_metadata["structure_solid_segment_count"] == 2
    assert exchange_output.payload_metadata["source_context_count"] == 1
    assert exchange_output.payload_metadata["region_ref_count"] == 1
    assert exchange_output.payload_metadata["assembly_ref_count"] == 1
    assert exchange_output.payload_metadata["structure_ref_count"] == 1
    assert exchange_output.payload_metadata["diagnostic_count"] == 1
    assert exchange_output.payload_metadata["diagnostic_warning_count"] == 1
    assert exchange_output.format_payload["structure_solid_rows"][0]["structure_id"] == "structure:bridge-01"
    assert exchange_output.format_payload["structure_solid_rows"][0]["region_ref"] == "region:bridge-01"
    assert exchange_output.format_payload["source_context_rows"][0]["region_ref"] == "region:bridge-01"
    assert exchange_output.format_payload["source_context_rows"][0]["assembly_ref"] == "assembly:bridge-deck"
    assert exchange_output.format_payload["source_context_rows"][0]["structure_ref"] == "structure:bridge-01"
    assert exchange_output.format_payload["structure_solid_segment_rows"][1]["segment_index"] == 2
    assert exchange_output.format_payload["diagnostic_rows"][0]["kind"] == "simplified_ifc_geometry"
    assert exchange_output.format_payload["diagnostic_rows"][0]["output_object_id"] == "solid:bridge-01"
    assert exchange_output.format_payload["structure_solid_rows"][0]["geometry_spec_id"] == "geometry-spec:bridge-01"
    assert exchange_output.source_refs == ["structures:main"]
    assert exchange_output.result_refs == ["corridor:main"]


def test_exchange_output_mapper_packages_side_slope_bench_source_context() -> None:
    applied_section = AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id="sec-bench",
        alignment_id="align-1",
        assembly_id="assembly:bench-road",
        station=20.0,
        source_refs=["assembly:bench-road", "region:bench-01"],
        component_rows=[
            AppliedSectionComponentRow(
                component_id="side-slope-right:bench:1",
                kind="bench",
                source_template_id="tmpl-side-slope-right",
                region_id="region:bench-01",
                side="right",
            )
        ],
    )
    section_output = SectionOutputMapper().map_applied_section(applied_section)
    quantity_output = QuantityOutputMapper().map_quantity_model(
        QuantityModel(
            schema_version=1,
            project_id="proj-1",
            quantity_model_id="qty-bench",
            corridor_id="corridor:main",
            fragment_rows=[
                QuantityFragment(
                    fragment_id="frag-bench-length",
                    quantity_kind="bench_surface_length",
                    measurement_kind="section_side_slope_breakline",
                    value=12.5,
                    unit="m",
                    component_ref="side-slope-right:bench:1",
                    assembly_ref="assembly:bench-road",
                    region_ref="region:bench-01",
                )
            ],
        )
    )

    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id="proj-1",
            exchange_output_id="pkg-bench",
            format="json",
            package_kind="corridor_source_trace_exchange",
            outputs=[section_output, quantity_output],
        )
    )

    context_rows = exchange_output.format_payload["source_context_rows"]
    context_by_kind = {row["context_kind"]: row for row in context_rows}
    component_context = context_by_kind["section_side_slope_component"]
    quantity_context = context_by_kind["side_slope_quantity_fragment"]

    assert exchange_output.payload_metadata["source_context_count"] == 2
    assert exchange_output.payload_metadata["side_slope_source_context_count"] == 2
    assert exchange_output.payload_metadata["bench_source_context_count"] == 2
    assert component_context["scope"] == "side_slope"
    assert component_context["assembly_ref"] == "assembly:bench-road"
    assert component_context["region_ref"] == "region:bench-01"
    assert component_context["component_ref"] == "side-slope-right:bench:1"
    assert component_context["template_ref"] == "tmpl-side-slope-right"
    assert component_context["component_kind"] == "bench"
    assert quantity_context["scope"] == "side_slope"
    assert quantity_context["assembly_ref"] == "assembly:bench-road"
    assert quantity_context["region_ref"] == "region:bench-01"
    assert quantity_context["component_ref"] == "side-slope-right:bench:1"
    assert quantity_context["quantity_kind"] == "bench_surface_length"
    assert quantity_context["measurement_kind"] == "section_side_slope_breakline"
