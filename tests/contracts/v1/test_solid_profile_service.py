from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.applied_section_solid_profile import (
    SOLID_PROFILE_ORIENTATION,
    AppliedSectionSolidProfileSet,
    SolidProfileEdge,
    SolidProfileNode,
)
from freecad.Corridor_Road.v1.models.source.solid_target_model import SolidTargetRow
from freecad.Corridor_Road.v1.services.builders.solid_profile_service import (
    AppliedSectionSolidProfileService,
    SolidProfileBuildRequest,
)


def _section(station: float, *, region_id: str = "region:1", include_subgrade: bool = True) -> AppliedSection:
    points = [
        AppliedSectionPoint("fg:left", station, 5.0, 10.0, "fg_surface", 5.0),
        AppliedSectionPoint("fg:right", station, -5.0, 10.0, "fg_surface", -5.0),
    ]
    if include_subgrade:
        points.extend(
            [
                AppliedSectionPoint("subgrade:left", station, 5.0, 9.5, "subgrade_surface", 5.0),
                AppliedSectionPoint("subgrade:right", station, -5.0, 9.5, "subgrade_surface", -5.0),
            ]
        )
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=f"section:{station:g}",
        corridor_id="corridor:main",
        station=station,
        region_id=region_id,
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=10.0),
        point_rows=points,
    )


def _applied_set(*sections: AppliedSection) -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        station_rows=[
            AppliedSectionStationRow(f"station:{section.station:g}", section.station, section.applied_section_id)
            for section in sections
        ],
        sections=list(sections),
    )


def _target(**overrides) -> SolidTargetRow:
    values = {
        "target_id": "solid-target:road-body-envelope",
        "target_family": "road_body_envelope",
        "scope_kind": "whole_corridor",
        "station_start": 0.0,
        "station_end": 100.0,
    }
    values.update(overrides)
    return SolidTargetRow(**values)


def test_applied_section_solid_profile_contract_preserves_rows() -> None:
    node = SolidProfileNode(
        node_id="node:top-left",
        semantic_role="top_left",
        x=0.0,
        y=5.0,
        z=10.0,
        lateral_offset=5.0,
    )
    edge = SolidProfileEdge(
        edge_id="edge:top",
        start_node_id="node:top-left",
        end_node_id="node:top-right",
        semantic_role="top_edge",
    )
    profile_set = AppliedSectionSolidProfileSet(
        schema_version=1,
        project_id="proj-1",
        profile_set_id="solid-profiles:main",
        target_ref="solid-target:road-body-envelope",
        profile_rows=[],
    )

    assert node.semantic_role == "top_left"
    assert edge.semantic_role == "top_edge"
    assert profile_set.target_ref == "solid-target:road-body-envelope"


def test_solid_profile_service_builds_closed_profiles_from_applied_sections() -> None:
    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=_target(),
            applied_section_set=_applied_set(_section(0.0), _section(100.0)),
        )
    )

    assert len(profile_set.profile_rows) == 2
    first = profile_set.profile_rows[0]
    assert first.is_closed is True
    assert first.orientation == SOLID_PROFILE_ORIENTATION
    assert [node.semantic_role for node in first.node_rows] == [
        "top_left",
        "top_right",
        "bottom_right",
        "bottom_left",
    ]
    assert [edge.semantic_role for edge in first.edge_rows] == [
        "top_edge",
        "right_side_edge",
        "bottom_edge",
        "left_side_edge",
    ]


def test_solid_profile_service_interpolates_region_boundary_profile_without_mutating_applied_sections() -> None:
    applied = _applied_set(_section(0.0, region_id="region:1"), _section(100.0, region_id="region:2"))
    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=_target(
                target_id="solid-target:region-body:region-2",
                target_family="region_body",
                scope_kind="region",
                region_ref="region:2",
                station_start=40.0,
                station_end=100.0,
            ),
            applied_section_set=applied,
        )
    )

    stations = [row.station for row in profile_set.profile_rows]
    assert stations == [40.0, 100.0]
    assert profile_set.profile_rows[0].applied_section_ref.startswith("interpolated:")
    assert profile_set.profile_rows[0].region_ref == "region:2"
    assert any(row.kind == "interpolated_boundary_profile" for row in profile_set.diagnostic_rows)
    assert [section.station for section in applied.sections] == [0.0, 100.0]


def test_solid_profile_service_filters_region_body_to_target_region_profiles() -> None:
    applied = _applied_set(
        _section(0.0, region_id="region:1"),
        _section(50.0, region_id="region:other"),
        _section(75.0, region_id="region:2"),
        _section(100.0, region_id="region:3"),
    )

    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=_target(
                target_id="solid-target:region-body:region-2",
                target_family="region_body",
                scope_kind="region",
                region_ref="region:2",
                station_start=40.0,
                station_end=80.0,
            ),
            applied_section_set=applied,
        )
    )

    assert [row.station for row in profile_set.profile_rows] == [40.0, 75.0, 80.0]
    assert all(row.region_ref == "region:2" for row in profile_set.profile_rows)
    assert any(row.kind == "skipped_non_region_profile" for row in profile_set.diagnostic_rows)
    assert any(row.kind == "region_boundary_cap_profiles" for row in profile_set.diagnostic_rows)


def test_solid_profile_service_warns_when_region_body_has_only_boundary_profiles() -> None:
    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=_target(
                target_id="solid-target:region-body:region-2",
                target_family="region_body",
                scope_kind="region",
                region_ref="region:2",
                station_start=40.0,
                station_end=80.0,
            ),
            applied_section_set=_applied_set(
                _section(0.0, region_id="region:1"),
                _section(100.0, region_id="region:3"),
            ),
        )
    )

    assert [row.station for row in profile_set.profile_rows] == [40.0, 80.0]
    assert any(row.kind == "region_target_no_matching_source_profiles" for row in profile_set.diagnostic_rows)


def test_solid_profile_service_uses_fallback_depth_when_subgrade_points_are_missing() -> None:
    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=_target(),
            applied_section_set=_applied_set(
                _section(0.0, include_subgrade=False),
                _section(100.0, include_subgrade=False),
            ),
            fallback_depth=0.75,
        )
    )

    bottom_right = profile_set.profile_rows[0].node_rows[2]
    assert bottom_right.z == 9.25
    assert any(row.kind == "fallback_profile_depth" for row in profile_set.diagnostic_rows)
