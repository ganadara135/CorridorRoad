import FreeCAD as App

from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.output.watertight_solid_output import (
    WatertightSolidOutput,
    WatertightSolidOutputDiagnosticRow,
    WatertightSolidOutputRow,
)
from freecad.Corridor_Road.v1.models.source.solid_target_model import SolidTargetRow
from freecad.Corridor_Road.v1.objects.obj_watertight_solid import (
    create_or_update_v1_watertight_solid_output_object,
    find_v1_watertight_solid_output,
    to_watertight_solid_output,
)
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


def _solid_pipeline():
    target = SolidTargetRow(
        target_id="solid-target:road-body-envelope",
        target_family="road_body_envelope",
        scope_kind="whole_corridor",
        station_start=0.0,
        station_end=100.0,
        source_refs=["corridor:main", "applied:main"],
    )
    applied = AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        sections=[_section(0.0), _section(100.0)],
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
            generated_object_ref="V1WatertightSolidOutput",
        )
    )
    return output, part_result


def test_watertight_solid_output_contract_preserves_rows_and_diagnostics() -> None:
    row = WatertightSolidOutputRow(
        output_object_id="watertight-solid:1",
        target_id="solid-target:road-body-envelope",
        target_family="road_body_envelope",
        scope_kind="whole_corridor",
        station_start=0.0,
        station_end=100.0,
        validation_status="ok",
        is_watertight=True,
        is_valid_solid=True,
        volume=500.0,
    )
    diagnostic = WatertightSolidOutputDiagnosticRow(
        diagnostic_id="diag:1",
        severity="info",
        kind="shape_ready",
        source_ref=row.output_object_id,
        message="Shape is ready.",
    )
    output = WatertightSolidOutput(
        schema_version=1,
        project_id="proj-1",
        watertight_solid_output_id="watertight-solids:main",
        solid_rows=[row],
        solid_diagnostic_rows=[diagnostic],
    )

    assert output.solid_rows[0].volume == 500.0
    assert output.solid_diagnostic_rows[0].source_ref == "watertight-solid:1"


def test_watertight_solid_output_mapper_preserves_shape_metadata_and_refs() -> None:
    output, part_result = _solid_pipeline()

    row = output.solid_rows[0]
    assert row.validation_status == "ok"
    assert row.is_watertight is True
    assert row.is_valid_solid is True
    assert row.volume == part_result.volume
    assert row.face_count == 6
    assert row.edge_count == 12
    assert row.profile_count == 2
    assert "corridor:main" in row.source_refs
    assert output.segment_rows[0].station_start == 0.0
    assert output.segment_rows[0].station_end == 100.0


def test_v1_watertight_solid_output_object_roundtrips_summary_and_shape() -> None:
    output, part_result = _solid_pipeline()
    doc = App.newDocument("V1WatertightSolidOutputTest")
    try:
        obj = create_or_update_v1_watertight_solid_output_object(
            document=doc,
            watertight_solid_output=output,
            shape=part_result.solid_shape,
        )

        assert obj.V1ObjectType == "V1WatertightSolidOutput"
        assert obj.CRRecordKind == "v1_watertight_solid_output"
        assert obj.SolidCount == 1
        assert obj.Shape.Volume > 0.0
        assert find_v1_watertight_solid_output(doc) == obj

        roundtrip = to_watertight_solid_output(obj)
        assert roundtrip is not None
        assert roundtrip.solid_rows[0].target_id == "solid-target:road-body-envelope"
        assert roundtrip.solid_rows[0].validation_status == "ok"
        assert roundtrip.solid_rows[0].volume == output.solid_rows[0].volume
        assert roundtrip.segment_rows[0].profile_refs == output.segment_rows[0].profile_refs
    finally:
        App.closeDocument(doc.Name)
