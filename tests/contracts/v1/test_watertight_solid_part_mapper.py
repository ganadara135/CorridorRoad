import sys
from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.result.solid_edge_network import SolidEdgeNetwork
from freecad.Corridor_Road.v1.models.source.solid_target_model import SolidTargetRow
from freecad.Corridor_Road.v1.services.builders.solid_edge_network_service import (
    SolidEdgeNetworkBuildRequest,
    SolidEdgeNetworkService,
)
from freecad.Corridor_Road.v1.services.builders.solid_profile_service import (
    AppliedSectionSolidProfileService,
    SolidProfileBuildRequest,
)
from freecad.Corridor_Road.v1.services.mapping.watertight_solid_part_mapper import (
    WatertightSolidPartMapper,
    WatertightSolidPartMappingResult,
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


def _profile_set_and_network():
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[_section(0.0), _section(100.0)],
    )
    profile_set = AppliedSectionSolidProfileService().build(
        SolidProfileBuildRequest(
            project_id="proj-1",
            solid_target=SolidTargetRow(
                target_id="solid-target:road-body-envelope",
                target_family="road_body_envelope",
                scope_kind="whole_corridor",
                station_start=0.0,
                station_end=100.0,
            ),
            applied_section_set=applied,
        )
    )
    edge_network = SolidEdgeNetworkService().build(
        SolidEdgeNetworkBuildRequest(project_id="proj-1", profile_set=profile_set)
    )
    return profile_set, edge_network


def test_watertight_solid_part_mapping_result_preserves_status() -> None:
    result = WatertightSolidPartMappingResult(
        target_ref="solid-target:road-body-envelope",
        validation_status="ok",
        is_watertight=True,
        is_valid_solid=True,
        volume=500.0,
        face_count=6,
        edge_count=12,
    )

    assert result.validation_status == "ok"
    assert result.volume == 500.0
    assert result.face_count == 6


def test_watertight_solid_part_mapper_creates_valid_part_solid_from_valid_edge_network() -> None:
    profile_set, edge_network = _profile_set_and_network()

    result = WatertightSolidPartMapper().map_edge_network(edge_network, profile_set)

    assert result.validation_status == "ok"
    assert result.is_watertight is True
    assert result.is_valid_solid is True
    assert result.face_count == 6
    assert result.edge_count == 12
    assert result.volume > 0.0
    assert result.solid_shape is not None
    assert result.diagnostic_rows == []


def test_watertight_solid_part_mapper_blocks_when_topology_gate_fails() -> None:
    profile_set, _edge_network = _profile_set_and_network()
    blocked_network = SolidEdgeNetwork(
        schema_version=1,
        project_id="proj-1",
        edge_network_id="solid-edge-network:blocked",
        target_ref="solid-target:road-body-envelope",
        profile_set_ref=profile_set.profile_set_id,
        validation_status="error",
        is_shell_closed=False,
    )

    result = WatertightSolidPartMapper().map_edge_network(blocked_network, profile_set)

    assert result.validation_status == "blocked"
    assert result.solid_shape is None
    assert {row.kind for row in result.diagnostic_rows} == {
        "topology_gate_failed",
        "shell_not_closed",
    }


def test_watertight_solid_part_mapper_triangulates_part_faces_when_needed() -> None:
    profile_set, edge_network = _profile_set_and_network()

    original_freecad = sys.modules.get("FreeCAD")
    original_part = sys.modules.get("Part")
    had_freecad = "FreeCAD" in sys.modules
    had_part = "Part" in sys.modules

    class FakeVector:
        def __init__(self, x, y, z):
            self.x = x
            self.y = y
            self.z = z

    class FakePolygon:
        def __init__(self, points):
            self.points = points

    class FakeFace:
        def __init__(self, polygon):
            if len(polygon.points) > 4:
                raise ValueError("fake non-planar polygon")
            self.polygon = polygon

    class FakeShell:
        def __init__(self, faces):
            self.faces = faces

        def isValid(self):
            return True

    class FakeSolid:
        Volume = 1.0

        def __init__(self, shell):
            self.shell = shell

        def isValid(self):
            return True

    fake_part = SimpleNamespace(
        makePolygon=lambda points: FakePolygon(points),
        Face=FakeFace,
        Shell=FakeShell,
        Solid=FakeSolid,
    )

    try:
        sys.modules["FreeCAD"] = SimpleNamespace(Vector=FakeVector)
        sys.modules["Part"] = fake_part

        result = WatertightSolidPartMapper().map_edge_network(edge_network, profile_set)
    finally:
        if had_freecad:
            sys.modules["FreeCAD"] = original_freecad
        else:
            sys.modules.pop("FreeCAD", None)
        if had_part:
            sys.modules["Part"] = original_part
        else:
            sys.modules.pop("Part", None)

    assert result.validation_status == "ok"
    assert result.is_watertight is True
    assert result.is_valid_solid is True
    assert result.face_count == 12
    assert result.solid_shape is not None
    assert {row.kind for row in result.diagnostic_rows} == {"part_face_triangulated"}
