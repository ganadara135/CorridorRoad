from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
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
from freecad.Corridor_Road.v1.services.mapping.watertight_solid_part_mapper import WatertightSolidPartMapper


def _section(station: float, region_id: str) -> AppliedSection:
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=f"section:{station:g}",
        corridor_id="corridor:main",
        station=station,
        region_id=region_id,
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0),
        point_rows=[
            AppliedSectionPoint("fg:left", station, 5.0, 10.0, "fg_surface", 5.0),
            AppliedSectionPoint("fg:right", station, -5.0, 10.0, "fg_surface", -5.0),
            AppliedSectionPoint("subgrade:left", station, 5.0, 9.5, "subgrade_surface", 5.0),
            AppliedSectionPoint("subgrade:right", station, -5.0, 9.5, "subgrade_surface", -5.0),
        ],
    )


def test_region_target_builds_independent_capped_watertight_solid_output() -> None:
    target = SolidTargetRow(
        target_id="solid-target:region-body:region-2",
        target_family="region_body",
        scope_kind="region",
        region_ref="region:2",
        station_start=40.0,
        station_end=80.0,
        source_refs=["corridor:main", "applied:main", "region:2"],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[
            _section(0.0, "region:1"),
            _section(50.0, "region:2"),
            _section(75.0, "region:2"),
            _section(100.0, "region:3"),
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

    assert [row.station for row in profile_set.profile_rows] == [40.0, 50.0, 75.0, 80.0]
    assert edge_network.validation_status == "ok"
    assert edge_network.is_shell_closed is True
    assert part_result.validation_status == "ok"
    assert part_result.volume > 0.0
    assert output.solid_rows[0].scope_kind == "region"
    assert output.solid_rows[0].region_ref == "region:2"
    assert output.solid_rows[0].is_watertight is True
    assert output.segment_rows[0].station_start == 40.0
    assert output.segment_rows[-1].station_end == 80.0
