from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.result.applied_section_solid_profile import (
    AppliedSectionSolidProfile,
    AppliedSectionSolidProfileSet,
    SolidProfileNode,
)
from freecad.Corridor_Road.v1.models.result.solid_edge_network import (
    SolidEdgeNetwork,
    SolidFaceRow,
    SolidTopologyEdgeRow,
)
from freecad.Corridor_Road.v1.models.source.solid_target_model import SolidTargetRow
from freecad.Corridor_Road.v1.services.builders.solid_edge_network_service import (
    SolidEdgeNetworkBuildRequest,
    SolidEdgeNetworkService,
)
from freecad.Corridor_Road.v1.services.builders.solid_profile_service import (
    AppliedSectionSolidProfileService,
    SolidProfileBuildRequest,
)


def _section(station: float) -> AppliedSection:
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=f"section:{station:g}",
        corridor_id="corridor:main",
        station=station,
        region_id="region:1",
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0),
        point_rows=[
            AppliedSectionPoint("fg:left", station, 5.0, 10.0, "fg_surface", 5.0),
            AppliedSectionPoint("fg:right", station, -5.0, 10.0, "fg_surface", -5.0),
            AppliedSectionPoint("subgrade:left", station, 5.0, 9.5, "subgrade_surface", 5.0),
            AppliedSectionPoint("subgrade:right", station, -5.0, 9.5, "subgrade_surface", -5.0),
        ],
    )


def _profile_set(*stations: float) -> AppliedSectionSolidProfileSet:
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[_section(station) for station in stations],
    )
    return AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=SolidTargetRow(
                target_id="solid-target:road-body-envelope",
                target_family="road_body_envelope",
                scope_kind="whole_corridor",
                station_start=min(stations),
                station_end=max(stations),
            ),
            applied_section_set=applied,
        )
    )


def _manual_profile(profile_id: str, station: float, *, width: float = 10.0, depth: float = 0.5) -> AppliedSectionSolidProfile:
    left = width * 0.5
    right = -width * 0.5
    return AppliedSectionSolidProfile(
        profile_id=profile_id,
        target_id="solid-target:road-body-envelope",
        station=station,
        applied_section_ref=f"section:{station:g}",
        is_closed=True,
        node_rows=[
            SolidProfileNode(f"{profile_id}:top-left", "top_left", station, left, 10.0),
            SolidProfileNode(f"{profile_id}:top-right", "top_right", station, right, 10.0),
            SolidProfileNode(f"{profile_id}:bottom-right", "bottom_right", station, right, 10.0 - depth),
            SolidProfileNode(f"{profile_id}:bottom-left", "bottom_left", station, left, 10.0 - depth),
        ],
    )


def test_solid_edge_network_contract_preserves_face_and_edge_rows() -> None:
    face = SolidFaceRow(
        face_id="face:1",
        target_id="target:1",
        face_kind="unknown_kind",
        node_ids=["n1", "n2", "n3"],
        edge_ids=["e1", "e2", "e3"],
    )
    edge = SolidTopologyEdgeRow(
        edge_id="edge:1",
        start_node_id="n1",
        end_node_id="n2",
        usage_count=2,
        face_refs=["face:1", "face:2"],
    )
    network = SolidEdgeNetwork(
        schema_version=1,
        project_id="proj-1",
        edge_network_id="network:1",
        face_rows=[face],
        edge_rows=[edge],
    )

    assert network.face_rows[0].face_kind == "transition"
    assert network.edge_rows[0].usage_count == 2


def test_solid_edge_network_service_builds_closed_six_face_shell_from_two_profiles() -> None:
    network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(
            project_id="proj-1",
            profile_set=_profile_set(0.0, 100.0),
        )
    )

    assert network.validation_status == "ok"
    assert network.is_shell_closed is True
    assert network.face_count == 6
    assert network.edge_count == 12
    assert {face.face_kind for face in network.face_rows} == {
        "top",
        "right_side",
        "bottom",
        "left_side",
        "start_cap",
        "end_cap",
    }
    assert all(edge.usage_count == 2 for edge in network.edge_rows)


def test_solid_edge_network_service_builds_strip_faces_between_multiple_profiles() -> None:
    network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(
            project_id="proj-1",
            profile_set=_profile_set(0.0, 50.0, 100.0),
        )
    )

    assert network.validation_status == "ok"
    assert network.profile_count == 3
    assert network.face_count == 10
    assert network.edge_count == 20
    assert len([face for face in network.face_rows if face.face_kind == "top"]) == 2
    assert all(edge.usage_count == 2 for edge in network.edge_rows)


def test_solid_edge_network_service_blocks_invalid_profile_node_order() -> None:
    profile = AppliedSectionSolidProfile(
        profile_id="profile:bad",
        target_id="solid-target:road-body-envelope",
        station=0.0,
        applied_section_ref="section:0",
        is_closed=True,
        node_rows=[
            SolidProfileNode("node:1", "top_right", 0.0, -5.0, 10.0),
            SolidProfileNode("node:2", "top_left", 0.0, 5.0, 10.0),
            SolidProfileNode("node:3", "bottom_right", 0.0, -5.0, 9.5),
            SolidProfileNode("node:4", "bottom_left", 0.0, 5.0, 9.5),
        ],
    )
    good_profile = _profile_set(100.0, 200.0).profile_rows[0]
    profile_set = AppliedSectionSolidProfileSet(
        schema_version=1,
        project_id="proj-1",
        profile_set_id="solid-profiles:bad",
        target_ref="solid-target:road-body-envelope",
        profile_rows=[profile, good_profile],
    )

    network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(project_id="proj-1", profile_set=profile_set)
    )

    assert network.validation_status == "error"
    assert network.face_count == 0
    assert any(row.kind == "invalid_profile_node_order" for row in network.diagnostic_rows)


def test_solid_edge_network_service_reports_quality_warnings_without_blocking_closed_shell() -> None:
    profile_set = AppliedSectionSolidProfileSet(
        schema_version=1,
        project_id="proj-1",
        profile_set_id="solid-profiles:quality-warning",
        target_ref="solid-target:road-body-envelope",
        profile_rows=[
            _manual_profile("profile:0", 0.0, width=0.00001),
            _manual_profile("profile:1", 0.0000000001, width=0.00001),
        ],
    )

    network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(project_id="proj-1", profile_set=profile_set)
    )

    assert network.validation_status == "ok"
    assert network.is_shell_closed is True
    assert any(row.kind == "short_topology_edge" for row in network.diagnostic_rows)
    assert any(row.kind == "tiny_topology_face_area" for row in network.diagnostic_rows)
    assert all(row.severity != "error" for row in network.diagnostic_rows)
