from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
)
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
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
    )

    output = SectionOutputMapper().map_applied_section(applied_section)

    assert output.section_output_id == "sec-1"
    assert output.component_rows[0].template_ref == "tmpl-1"
    assert output.quantity_rows[0].component_ref == "lane-1"


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
