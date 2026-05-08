from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.source.solid_target_model import SolidTargetRow
from freecad.Corridor_Road.v1.services.builders.solid_edge_network_service import (
    SolidEdgeNetworkBuildRequest,
    SolidEdgeNetworkService,
)
from freecad.Corridor_Road.v1.services.builders.solid_profile_service import (
    AppliedSectionSolidProfileService,
    SolidProfileBuildRequest,
)
from freecad.Corridor_Road.v1.services.mapping.watertight_solid_output_mapper import (
    WatertightSolidOutputMapper,
    WatertightSolidOutputMappingRequest,
)
from freecad.Corridor_Road.v1.services.mapping.exchange_output_mapper import (
    ExchangeOutputMapper,
    ExchangePackageRequest,
)
from freecad.Corridor_Road.v1.services.mapping.watertight_solid_part_mapper import WatertightSolidPartMapper


def _section(station: float, *, include_component: bool = True) -> AppliedSection:
    components = []
    if include_component:
        components.append(
            AppliedSectionComponentRow(
                "pavement:base",
                "pavement_layer",
                side="center",
                width=6.0,
                thickness=0.25,
                material="asphalt",
            )
        )
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=f"section:{station:g}",
        corridor_id="corridor:main",
        station=station,
        region_id="region:1",
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0),
        component_rows=components,
    )


def test_pavement_layer_component_target_builds_independent_watertight_solid_output() -> None:
    target = SolidTargetRow(
        target_id="solid-target:pavement-layer:pavement-base",
        target_family="pavement_layer_body",
        scope_kind="assembly_component",
        component_ref="pavement:base",
        material_ref="asphalt",
        station_start=0.0,
        station_end=100.0,
        source_refs=["corridor:main", "applied:main", "pavement:base"],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            _section(0.0),
            _section(50.0, include_component=False),
            _section(100.0),
        ],
    )

    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(project_id="proj-1", solid_target=target, applied_section_set=applied)
    )
    edge_network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(project_id="proj-1", profile_set=profile_set)
    )
    part_result = WatertightSolidPartMapper().map_edge_network(edge_network, profile_set)
    output = WatertightSolidOutputMapper().map_result(
        WatertightSolidOutputMappingRequest(
            project_id="proj-1",
            corridor_id="corridor:main",
            solid_target=target,
            profile_set=profile_set,
            edge_network=edge_network,
            part_result=part_result,
        )
    )

    assert [row.station for row in profile_set.profile_rows] == [0.0, 100.0]
    assert any(row.kind == "skipped_missing_component_profile" for row in profile_set.diagnostic_rows)
    assert any(row.kind == "component_boundary_cap_profiles" for row in profile_set.diagnostic_rows)
    assert edge_network.validation_status == "ok"
    assert part_result.validation_status == "ok"
    assert part_result.volume > 0.0
    assert output.solid_rows[0].target_family == "pavement_layer_body"
    assert output.solid_rows[0].scope_kind == "assembly_component"
    assert output.solid_rows[0].component_ref == "pavement:base"
    assert output.solid_rows[0].material_ref == "asphalt"


def test_pavement_layer_component_profile_uses_component_width_and_thickness() -> None:
    target = SolidTargetRow(
        target_id="solid-target:pavement-layer:pavement-base",
        target_family="pavement_layer_body",
        scope_kind="assembly_component",
        component_ref="pavement:base",
        station_start=0.0,
        station_end=100.0,
    )
    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=target,
            applied_section_set=AppliedSectionSet(
                schema_version=1,
                project_id="proj-1",
                applied_section_set_id="applied:main",
                corridor_id="corridor:main",
                sections=[_section(0.0), _section(100.0)],
            ),
        )
    )

    first = profile_set.profile_rows[0]
    offsets = [node.lateral_offset for node in first.node_rows]
    elevations = [node.z for node in first.node_rows]
    assert offsets == [3.0, -3.0, -3.0, 3.0]
    assert elevations == [10.0, 10.0, 9.75, 9.75]


def test_shoulder_component_profile_uses_side_specific_offsets() -> None:
    target = SolidTargetRow(
        target_id="solid-target:shoulder:shoulder-left",
        target_family="shoulder_body",
        scope_kind="assembly_component",
        component_ref="shoulder:left",
        station_start=0.0,
        station_end=100.0,
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                station=0.0,
                region_id="region:1",
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0),
                component_rows=[
                    AppliedSectionComponentRow(
                        "shoulder:left",
                        "shoulder",
                        side="left",
                        width=1.5,
                        thickness=0.2,
                        material="aggregate",
                    )
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:100",
                station=100.0,
                region_id="region:1",
                frame=AppliedSectionFrame(station=100.0, x=100.0, y=0.0, z=10.0),
                component_rows=[
                    AppliedSectionComponentRow(
                        "shoulder:left",
                        "shoulder",
                        side="left",
                        width=1.5,
                        thickness=0.2,
                        material="aggregate",
                    )
                ],
            ),
        ],
    )

    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(project_id="proj-1", solid_target=target, applied_section_set=applied)
    )
    edge_network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(project_id="proj-1", profile_set=profile_set)
    )

    first = profile_set.profile_rows[0]
    offsets = [node.lateral_offset for node in first.node_rows]
    elevations = [node.z for node in first.node_rows]
    assert offsets == [1.5, 0.0, 0.0, 1.5]
    assert elevations == [10.0, 10.0, 9.8, 9.8]
    assert edge_network.validation_status == "ok"


def test_lined_ditch_target_builds_independent_watertight_solid_output() -> None:
    def ditch_section(station: float) -> AppliedSection:
        return AppliedSection(
            schema_version=1,
            project_id="proj-1",
            applied_section_id=f"section:{station:g}",
            corridor_id="corridor:main",
            station=station,
            region_id="region:1",
            frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0),
            point_rows=[
                AppliedSectionPoint("ditch:right-edge", station, -5.0, 10.0, "ditch_surface", -5.0),
                AppliedSectionPoint("ditch:right-mid", station, -5.6, 9.7, "ditch_surface", -5.6),
                AppliedSectionPoint("ditch:right-flow", station, -6.2, 9.8, "ditch_surface", -6.2),
            ],
            component_rows=[
                AppliedSectionComponentRow(
                    "ditch:right",
                    "ditch",
                    side="right",
                    width=1.2,
                    material="concrete",
                    parameters={"lining_thickness": "0.15"},
                )
            ],
        )

    target = SolidTargetRow(
        target_id="solid-target:lined-ditch:right",
        target_family="lined_ditch_body",
        scope_kind="drainage",
        drainage_ref="lined_ditch:right",
        component_ref="ditch:right",
        material_ref="concrete",
        station_start=0.0,
        station_end=100.0,
        source_refs=["corridor:main", "applied:main", "ditch:right"],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[ditch_section(0.0), ditch_section(100.0)],
    )

    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(project_id="proj-1", solid_target=target, applied_section_set=applied)
    )
    edge_network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(project_id="proj-1", profile_set=profile_set)
    )
    part_result = WatertightSolidPartMapper().map_edge_network(edge_network, profile_set)
    output = WatertightSolidOutputMapper().map_result(
        WatertightSolidOutputMappingRequest(
            project_id="proj-1",
            corridor_id="corridor:main",
            solid_target=target,
            profile_set=profile_set,
            edge_network=edge_network,
            part_result=part_result,
        )
    )

    assert edge_network.validation_status == "ok"
    assert len(profile_set.profile_rows[0].node_rows) == 6
    assert edge_network.face_count == 8
    assert edge_network.edge_count == 18
    assert part_result.validation_status == "ok"
    assert part_result.volume > 0.0
    assert output.solid_rows[0].target_family == "lined_ditch_body"
    assert output.solid_rows[0].scope_kind == "drainage"
    assert output.solid_rows[0].drainage_ref == "lined_ditch:right"
    assert output.solid_rows[0].component_ref == "ditch:right"
    assert output.solid_rows[0].material_ref == "concrete"
    provenance_rows = [row for row in output.solid_diagnostic_rows if row.kind == "lined_ditch_shape_provenance"]
    assert len(provenance_rows) == 1
    assert "drainage_ref=lined_ditch:right" in provenance_rows[0].notes
    assert "component_ref=ditch:right" in provenance_rows[0].notes
    assert "side=right" in provenance_rows[0].notes
    assert "material=concrete" in provenance_rows[0].notes
    assert "lining_thickness=0.15" in provenance_rows[0].notes
    assert "offset_method=section_normal_polyline" in provenance_rows[0].notes
    assert "join_policy=normal_average" in provenance_rows[0].notes
    assert "miter_limit=2" in provenance_rows[0].notes
    assert "top_point_count=3" in provenance_rows[0].notes

    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id="proj-1",
            exchange_output_id="pkg-lined-ditch",
            format="json",
            package_kind="watertight_solid_exchange",
            outputs=[output],
        )
    )
    exchange_diagnostics = exchange_output.format_payload["diagnostic_rows"]
    assert any(row["kind"] == "lined_ditch_shape_provenance" for row in exchange_diagnostics)
    context_rows = exchange_output.format_payload["source_context_rows"]
    assert any(
        row["context_kind"] == "watertight_solid"
        and row["drainage_ref"] == "lined_ditch:right"
        and row["material_ref"] == "concrete"
        for row in context_rows
    )
