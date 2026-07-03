import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from freecad.Corridor_Road.v1.exchange.exchange_package_export import export_exchange_package_to_json
from freecad.Corridor_Road.v1.exchange.ifc_export import export_exchange_package_to_ifc
from freecad.Corridor_Road.v1.models.output.watertight_solid_output import (
    WatertightSolidOutput,
    WatertightSolidOutputRow,
    WatertightSolidSegmentRow,
)
from freecad.Corridor_Road.v1.services.mapping.exchange_output_mapper import (
    ExchangeOutputMapper,
    ExchangePackageRequest,
)
from freecad.Corridor_Road.v1.services.mapping.quantity_output_mapper import QuantityOutputMapper


def _watertight_output() -> WatertightSolidOutput:
    return WatertightSolidOutput(
        schema_version=1,
        project_id="proj-1",
        watertight_solid_output_id="watertight-solids:main",
        corridor_id="corridor:main",
        source_refs=["corridor:main", "applied:main", "solid-target:region-body:region-1"],
        result_refs=["solid-profiles:region-1", "solid-edge-network:region-1"],
        solid_rows=[
            WatertightSolidOutputRow(
                output_object_id="watertight-solid:region-1",
                target_id="solid-target:region-body:region-1",
                target_family="region_body",
                scope_kind="region",
                station_start=10.0,
                station_end=30.0,
                validation_status="ok",
                is_watertight=True,
                is_valid_solid=True,
                volume=120.0,
                face_count=6,
                edge_count=12,
                profile_count=2,
                region_ref="region:1",
                assembly_ref="assembly:road",
                material_ref="material:asphalt",
                drainage_ref="drainage:right",
                flow_route_ref="flow-route:right",
                source_refs=[
                    "intersection:t-01",
                    "intersection-leg:intersection:t-01:primary",
                    "intersection-control-area:intersection:t-01:primary",
                    "intersection-edge-family:intersection:t-01:pavement",
                    "intersection-zone:intersection:t-01:pavement",
                    "intersection-edge-network:intersection:t-01",
                    "intersection-surface-zones:intersection:t-01",
                ],
                diagnostic_refs=["diag:intersection-zone:pavement"],
                notes="contract_status=accepted_surface_zone; digital_twin_handoff=accepted_zone_candidate",
            ),
            WatertightSolidOutputRow(
                output_object_id="watertight-solid:blocked",
                target_id="solid-target:region-body:blocked",
                target_family="region_body",
                scope_kind="region",
                station_start=30.0,
                station_end=40.0,
                validation_status="error",
                is_watertight=False,
                is_valid_solid=False,
                volume=0.0,
                region_ref="region:blocked",
            ),
        ],
        segment_rows=[
            WatertightSolidSegmentRow(
                segment_id="watertight-solid:region-1:segment:1",
                parent_output_object_id="watertight-solid:region-1",
                station_start=10.0,
                station_end=30.0,
                face_refs=["face:top", "face:bottom"],
                profile_refs=["profile:10", "profile:30"],
            )
        ],
    )


def test_quantity_output_mapper_creates_volume_fragments_from_accepted_watertight_solids() -> None:
    quantity_output = QuantityOutputMapper().map_watertight_solid_output(_watertight_output())

    assert quantity_output.quantity_output_id == "watertight-solids:main:quantities"
    assert len(quantity_output.fragment_rows) == 1
    fragment = quantity_output.fragment_rows[0]
    assert fragment.quantity_kind == "watertight_solid_volume"
    assert fragment.measurement_kind == "part_solid_volume"
    assert fragment.value == 120.0
    assert fragment.unit == "m3"
    assert fragment.station_start == 10.0
    assert fragment.station_end == 30.0
    assert fragment.region_ref == "region:1"
    assert fragment.drainage_ref == "drainage:right"
    assert fragment.flow_route_ref == "flow-route:right"
    assert quantity_output.aggregate_rows[0].value == 120.0
    assert quantity_output.summary_rows[0].value == 1


def test_exchange_output_mapper_packages_watertight_solids_separately_from_structure_solids() -> None:
    watertight_output = _watertight_output()
    quantity_output = QuantityOutputMapper().map_watertight_solid_output(watertight_output)

    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id="proj-1",
            exchange_output_id="pkg-watertight",
            format="json",
            package_kind="watertight_solid_exchange",
            outputs=[watertight_output, quantity_output],
        )
    )

    assert exchange_output.output_refs[0].output_kind == "watertightsolid"
    assert exchange_output.output_refs[0].output_id == "watertight-solids:main"
    assert exchange_output.payload_metadata["structure_solid_count"] == 0
    assert exchange_output.payload_metadata["watertight_solid_count"] == 2
    assert exchange_output.payload_metadata["watertight_solid_segment_count"] == 1
    assert exchange_output.payload_metadata["watertight_solid_volume"] == 120.0
    assert exchange_output.payload_metadata["watertight_intersection_source_context_count"] == 1
    assert exchange_output.payload_metadata["watertight_intersection_surface_zone_context_count"] == 1
    assert exchange_output.payload_metadata["watertight_intersection_diagnostic_ref_count"] == 1
    assert exchange_output.payload_metadata["region_ref_count"] == 2
    assert exchange_output.format_payload["watertight_solid_rows"][0]["target_id"] == "solid-target:region-body:region-1"
    assert exchange_output.format_payload["watertight_solid_rows"][0]["material_ref"] == "material:asphalt"
    assert "intersection:t-01" in exchange_output.format_payload["watertight_solid_rows"][0]["source_refs"]
    assert exchange_output.format_payload["watertight_solid_segment_rows"][0]["profile_refs"] == ["profile:10", "profile:30"]
    context_rows = exchange_output.format_payload["source_context_rows"]
    assert any(row["context_kind"] == "watertight_solid" for row in context_rows)
    assert any(
        row["context_kind"] == "watertight_solid"
        and row["intersection_ref"] == "intersection:t-01"
        and row["intersection_leg_ref"] == "intersection-leg:intersection:t-01:primary"
        and row["intersection_control_area_ref"] == "intersection-control-area:intersection:t-01:primary"
        and row["intersection_edge_family_ref"] == "intersection-edge-family:intersection:t-01:pavement"
        and row["intersection_surface_zone_ref"] == "intersection-zone:intersection:t-01:pavement"
        and row["intersection_edge_network_ref"] == "intersection-edge-network:intersection:t-01"
        and row["intersection_surface_zone_result_ref"] == "intersection-surface-zones:intersection:t-01"
        and row["diagnostic_refs"] == ["diag:intersection-zone:pavement"]
        and "contract_status=accepted_surface_zone" in row["notes"]
        and row["material_ref"] == "material:asphalt"
        and row["station_start"] == 10.0
        and row["station_end"] == 30.0
        for row in context_rows
    )
    assert any(
        row["context_kind"] == "watertight_solid"
        and row["flow_route_ref"] == "flow-route:right"
        for row in context_rows
    )
    assert any(
        row["context_kind"] == "quantity_fragment"
        and row["flow_route_ref"] == "flow-route:right"
        for row in context_rows
    )


def test_exchange_package_exports_preserve_watertight_intersection_lineage_metadata() -> None:
    watertight_output = _watertight_output()
    exchange_output = ExchangeOutputMapper().map_output_package(
        ExchangePackageRequest(
            project_id="proj-1",
            exchange_output_id="pkg-watertight",
            format="ifc",
            package_kind="watertight_solid_exchange",
            outputs=[watertight_output],
        )
    )
    package_obj = SimpleNamespace(
        SchemaVersion=1,
        ProjectId="proj-1",
        ExchangeOutputId=exchange_output.exchange_output_id,
        ExchangeFormat=exchange_output.format,
        PackageKind=exchange_output.package_kind,
        CorridorId="corridor:main",
        StructureSolidOutputId="",
        StructureSolidCount=0,
        StructureSolidSegmentCount=0,
        ExportReadinessStatus="warning",
        ExportDiagnosticCount=0,
        PayloadStorageMode="inline",
        PayloadByteCount=0,
        QuantityOutputId="",
        QuantityFragmentCount=0,
        PackagedOutputIds=[row.output_id for row in exchange_output.output_refs],
        SourceRefs=exchange_output.source_refs,
        ResultRefs=exchange_output.result_refs,
        PayloadMetadataJson=json.dumps(exchange_output.payload_metadata),
        FormatPayloadJson=json.dumps(exchange_output.format_payload),
        StructureSolidRowsJson="[]",
        StructureSolidSegmentRowsJson="[]",
        ExportDiagnosticRowsJson="[]",
        QuantityFragmentRowsJson="[]",
    )

    with tempfile.TemporaryDirectory(prefix="cr_v1_watertight_intersection_exchange_") as temp_dir:
        json_path = Path(temp_dir) / "watertight_exchange_package.json"
        ifc_path = Path(temp_dir) / "watertight_exchange_package.ifc"
        json_info = export_exchange_package_to_json(json_path, package_obj)
        ifc_info = export_exchange_package_to_ifc(ifc_path, package_obj)
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        ifc_text = ifc_path.read_text(encoding="utf-8")

    assert json_info["watertight_intersection_source_context_count"] == 1
    assert json_info["watertight_intersection_surface_zone_context_count"] == 1
    assert json_info["watertight_intersection_diagnostic_ref_count"] == 1
    assert ifc_info["watertight_intersection_source_context_count"] == 1
    assert ifc_info["watertight_intersection_surface_zone_context_count"] == 1
    assert ifc_info["watertight_intersection_diagnostic_ref_count"] == 1
    assert payload["payload_metadata"]["watertight_intersection_source_context_count"] == 1
    assert payload["source_context_rows"][0]["intersection_leg_ref"] == "intersection-leg:intersection:t-01:primary"
    assert payload["source_context_rows"][0]["diagnostic_refs"] == ["diag:intersection-zone:pavement"]
    assert "'WatertightIntersectionSourceContextCount',$,IFCINTEGER(1)" in ifc_text
    assert "'WatertightIntersectionSurfaceZoneContextCount',$,IFCINTEGER(1)" in ifc_text
    assert "'WatertightIntersectionDiagnosticRefCount',$,IFCINTEGER(1)" in ifc_text
