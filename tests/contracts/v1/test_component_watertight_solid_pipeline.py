from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
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
