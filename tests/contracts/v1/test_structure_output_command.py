import json
import tempfile
from pathlib import Path

import FreeCAD as App

import freecad.Corridor_Road.v1.commands.cmd_structure_output as structure_output_command
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    apply_v1_corridor_model,
    apply_v1_structure_output_package,
    build_document_structure_output_package,
    export_document_structure_output_package_ifc,
    export_document_structure_output_package_json,
    structure_output_package_summary,
)
from freecad.Corridor_Road.v1.exchange.exchange_package_export import exchange_package_payload
from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.source.structure_model import (
    BridgeGeometrySpec,
    StructureGeometrySpec,
    StructureModel,
    StructurePlacement,
    StructureRow,
)
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_corridor import find_v1_corridor_model
from freecad.Corridor_Road.v1.objects.obj_exchange_package import find_v1_exchange_package
from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object


def _new_project_doc():
    doc = App.newDocument("V1StructureOutputCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _sample_sections() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=0.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )


def _sample_benched_sections() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:bench",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:bench:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:bench:20"),
        ],
        sections=[
            _sample_benched_section("section:bench:0", 0.0, 10.0),
            _sample_benched_section("section:bench:20", 20.0, 11.0),
        ],
        source_refs=["assembly:bench-road", "region:bench-01"],
    )


def _sample_benched_section(section_id: str, station: float, elevation: float) -> AppliedSection:
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=section_id,
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        assembly_id="assembly:bench-road",
        station=station,
        template_id="template:bench-road",
        region_id="region:bench-01",
        frame=AppliedSectionFrame(station=station, x=station, y=0.0, z=elevation, tangent_direction_deg=0.0),
        surface_left_width=5.0,
        surface_right_width=4.0,
        subgrade_depth=0.25,
        daylight_left_width=3.0,
        daylight_right_width=3.0,
        daylight_left_slope=-0.5,
        daylight_right_slope=-0.5,
        component_rows=[
            AppliedSectionComponentRow(
                component_id="side-slope-right:bench:1",
                kind="bench",
                source_template_id="template:bench-road:side-slope-right",
                region_id="region:bench-01",
                side="right",
                width=1.0,
                slope=-0.02,
            )
        ],
        point_rows=[
            AppliedSectionPoint(
                point_id="side-slope-right:surface:1",
                x=station,
                y=-5.0,
                z=elevation - 0.5,
                point_role="side_slope_surface",
                lateral_offset=-5.0,
            ),
            AppliedSectionPoint(
                point_id="side-slope-right:bench:1",
                x=station,
                y=-6.0,
                z=elevation - 0.52,
                point_role="bench_surface",
                lateral_offset=-6.0,
            ),
            AppliedSectionPoint(
                point_id="side-slope-right:daylight",
                x=station,
                y=-7.0,
                z=elevation - 1.0,
                point_role="daylight_marker",
                lateral_offset=-7.0,
            ),
        ],
    )


def _sample_sections_with_centerline_curve() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:curved",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:0", 0.0, "section:0"),
            AppliedSectionStationRow("station:20", 20.0, "section:20"),
            AppliedSectionStationRow("station:40", 40.0, "section:40"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:0",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, x=0.0, y=0.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:20",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=20.0,
                frame=AppliedSectionFrame(station=20.0, x=20.0, y=4.0, z=11.0, tangent_direction_deg=10.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:40",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                station=40.0,
                frame=AppliedSectionFrame(station=40.0, x=40.0, y=0.0, z=12.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.0,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=3.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.5,
            ),
        ],
    )


def _sample_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="alignment:main",
        structure_rows=[
            StructureRow(
                structure_id="bridge:1",
                structure_kind="bridge",
                structure_role="active",
                placement=StructurePlacement(
                    placement_id="placement:bridge:1",
                    alignment_id="alignment:main",
                    station_start=5.0,
                    station_end=15.0,
                ),
                geometry_spec_ref="geom:bridge:1",
            ),
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                geometry_spec_id="geom:bridge:1",
                structure_ref="bridge:1",
                shape_kind="bridge_deck",
                width=12.0,
                height=0.5,
                material="concrete",
            ),
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec(
                geometry_spec_ref="geom:bridge:1",
                deck_width=11.0,
                deck_thickness=0.6,
            ),
        ],
    )


def _sample_long_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:main",
        alignment_id="alignment:main",
        structure_rows=[
            StructureRow(
                structure_id="bridge:long",
                structure_kind="bridge",
                structure_role="active",
                placement=StructurePlacement(
                    placement_id="placement:bridge:long",
                    alignment_id="alignment:main",
                    station_start=5.0,
                    station_end=35.0,
                ),
                geometry_spec_ref="geom:bridge:long",
            ),
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                geometry_spec_id="geom:bridge:long",
                structure_ref="bridge:long",
                shape_kind="bridge_deck",
                width=12.0,
                height=0.5,
                material="concrete",
            ),
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec(
                geometry_spec_ref="geom:bridge:long",
                deck_width=11.0,
                deck_thickness=0.6,
            ),
        ],
    )


def _sample_invalid_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:invalid",
        alignment_id="alignment:main",
        structure_rows=[
            StructureRow(
                structure_id="bridge:invalid",
                structure_kind="bridge",
                structure_role="active",
                placement=StructurePlacement(
                    placement_id="placement:bridge:invalid",
                    alignment_id="alignment:main",
                    station_start=10.0,
                    station_end=10.0,
                ),
                geometry_spec_ref="geom:bridge:invalid",
            ),
        ],
        geometry_spec_rows=[
            StructureGeometrySpec(
                geometry_spec_id="geom:bridge:invalid",
                structure_ref="bridge:invalid",
                shape_kind="bridge_deck",
                width=0.0,
                height=0.0,
                skew_angle_deg=12.0,
                material="concrete",
            ),
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec(
                geometry_spec_ref="geom:bridge:invalid",
                deck_width=0.0,
                deck_thickness=0.0,
            ),
        ],
    )


def _sample_large_structure_model(count: int = 180) -> StructureModel:
    structure_rows = []
    geometry_specs = []
    bridge_specs = []
    for index in range(count):
        structure_id = f"bridge:large-{index:03d}"
        spec_id = f"geom:bridge:large-{index:03d}"
        structure_rows.append(
            StructureRow(
                structure_id=structure_id,
                structure_kind="bridge",
                structure_role="active",
                placement=StructurePlacement(
                    placement_id=f"placement:{structure_id}",
                    alignment_id="alignment:main",
                    station_start=5.0,
                    station_end=15.0,
                    offset=float(index % 3),
                ),
                geometry_spec_ref=spec_id,
            )
        )
        geometry_specs.append(
            StructureGeometrySpec(
                geometry_spec_id=spec_id,
                structure_ref=structure_id,
                shape_kind="bridge_deck",
                width=12.0,
                height=0.5,
                material="concrete",
            )
        )
        bridge_specs.append(
            BridgeGeometrySpec(
                geometry_spec_ref=spec_id,
                deck_width=11.0,
                deck_thickness=0.6,
            )
        )
    return StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="structures:large",
        alignment_id="alignment:main",
        structure_rows=structure_rows,
        geometry_spec_rows=geometry_specs,
        bridge_geometry_spec_rows=bridge_specs,
    )


def test_structure_output_smoke_workflow_builds_corridor_package_json_and_ifc() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_structure_model())

        corridor_obj = apply_v1_corridor_model(document=doc, project=project)
        assert corridor_obj == find_v1_corridor_model(doc)
        assert corridor_obj.CorridorId == "corridor:main"

        package_result = build_document_structure_output_package(doc, project=project)
        package_obj = apply_v1_structure_output_package(document=doc, project=project, package_result=package_result)
        assert package_obj == find_v1_exchange_package(doc)
        assert package_obj.ExchangeOutputId == "exchange:structure-solids"
        assert int(package_obj.StructureSolidCount) == 1
        assert int(package_obj.QuantityFragmentCount) >= 1
        assert package_obj.ExportReadinessStatus == "warning"

        with tempfile.TemporaryDirectory(prefix="cr_v1_structure_smoke_") as temp_dir:
            json_path = Path(temp_dir) / "structure_exchange_package.json"
            ifc_path = Path(temp_dir) / "structure_exchange_package.ifc"
            json_info = export_document_structure_output_package_json(
                str(json_path),
                document=doc,
                project=project,
                exchange_package=package_obj,
            )
            ifc_info = export_document_structure_output_package_ifc(
                str(ifc_path),
                document=doc,
                project=project,
                exchange_package=package_obj,
            )
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
            ifc_text = ifc_path.read_text(encoding="utf-8")

            assert json_info["structure_solid_count"] == 1
            assert json_payload["structure_solid_rows"][0]["structure_id"] == "bridge:1"
            assert json_payload["quantity_fragment_rows"][0]["structure_ref"] == "bridge:1"
            assert ifc_info["structure_solid_count"] == 1
            assert "IFCBUILDINGELEMENTPROXY" in ifc_text
            assert "'StructureId',$,IFCTEXT('bridge:1')" in ifc_text
    finally:
        App.closeDocument(doc.Name)


def test_build_document_structure_output_package_maps_structure_solids_quantities_and_exchange() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_structure_model())

        result = build_document_structure_output_package(doc, project=project)

        assert result.corridor_model.corridor_id == "corridor:main"
        assert len(result.structure_solid_output.solid_rows) == 1
        solid = result.structure_solid_output.solid_rows[0]
        assert solid.structure_id == "bridge:1"
        assert solid.solid_kind == "bridge_deck_solid"
        assert solid.path_source == "3d_centerline"
        assert solid.volume == 66.0
        assert solid.placement_x == 5.0
        assert solid.placement_y == 0.0
        assert solid.placement_z == 10.25
        assert solid.tangent_direction_deg == 0.0
        assert solid.start_x == 5.0
        assert solid.start_y == 0.0
        assert solid.start_z == 10.25
        assert solid.end_x == 15.0
        assert solid.end_y == 0.0
        assert solid.end_z == 10.75
        assert solid.start_tangent_direction_deg == 0.0
        assert solid.end_tangent_direction_deg == 0.0
        assert len(result.structure_solid_output.solid_segment_rows) == 1
        segment = result.structure_solid_output.solid_segment_rows[0]
        assert segment.parent_output_object_id == "structure-solid:bridge:1"
        assert segment.station_start == 5.0
        assert segment.station_end == 15.0
        assert [row.kind for row in result.structure_solid_output.diagnostic_rows] == ["simplified_ifc_geometry"]
        quantity_kinds = [row.quantity_kind for row in result.quantity_model.fragment_rows]
        assert "bridge_deck_volume" in quantity_kinds
        assert result.quantity_output.quantity_output_id == "quantities:structures"
        assert result.exchange_output.exchange_output_id == "exchange:structure-solids"
        assert result.exchange_output.payload_metadata["structure_solid_count"] == 1
        assert result.exchange_output.payload_metadata["source_context_count"] == 2
        assert result.exchange_output.payload_metadata["structure_ref_count"] == 1
        assert result.exchange_output.payload_metadata["diagnostic_count"] == 1
        assert result.exchange_output.payload_metadata["diagnostic_warning_count"] == 1
        assert result.exchange_output.format_payload["structure_solid_rows"][0]["structure_id"] == "bridge:1"
        assert result.exchange_output.format_payload["source_context_rows"][0]["structure_ref"] == "bridge:1"
        assert result.exchange_output.format_payload["diagnostic_rows"][0]["output_object_id"] == "structure-solid:bridge:1"
        assert result.exchange_output.format_payload["output_ids"] == [
            "structure-solids:main",
            "quantities:structures",
            "section:0",
            "section:20",
        ]
        summary = structure_output_package_summary(result)
        assert summary["solid_count"] == 1
        assert summary["active_structure_count"] == 1
        assert summary["active_structure_refs"] == ["bridge:1"]
        assert summary["export_readiness_status"] == "warning"
        assert summary["export_diagnostic_count"] == 1
        assert summary["quantity_fragment_count"] >= 1
        assert summary["section_output_count"] == 2
        assert summary["exchange_output_count"] == 4

        obj = apply_v1_structure_output_package(document=doc, project=project, package_result=result)
        assert obj == find_v1_exchange_package(doc)
        assert obj.V1ObjectType == "ExchangePackage"
        assert obj.CRRecordKind == "v1_exchange_package"
        assert obj.ExchangeOutputId == "exchange:structure-solids"
        assert obj.ExchangeFormat == "ifc"
        assert obj.PackageKind == "structure_geometry"
        assert obj.StructureSolidOutputId == "structure-solids:main"
        assert int(obj.StructureSolidCount) == 1
        assert int(obj.StructureSolidSegmentCount) == 1
        assert obj.ExportReadinessStatus == "warning"
        assert int(obj.ExportDiagnosticCount) == 1
        assert obj.QuantityOutputId == "quantities:structures"
        assert int(obj.QuantityFragmentCount) >= 1
        assert list(obj.PackagedOutputIds) == ["structure-solids:main", "quantities:structures", "section:0", "section:20"]
        assert '"structure_solid_count":1' in obj.PayloadMetadataJson
        assert '"structure_solid_segment_count":1' in obj.PayloadMetadataJson
        assert '"structure_id":"bridge:1"' in obj.StructureSolidRowsJson
        assert '"segment_id":"structure-solid:bridge:1:segment:1"' in obj.StructureSolidSegmentRowsJson
        assert '"kind":"simplified_ifc_geometry"' in obj.ExportDiagnosticRowsJson

        with tempfile.TemporaryDirectory(prefix="cr_v1_exchange_export_") as temp_dir:
            export_path = Path(temp_dir) / "structure_exchange_package.json"
            info = export_document_structure_output_package_json(str(export_path), document=doc, project=project)
            payload = json.loads(export_path.read_text(encoding="utf-8"))
            assert info["path"] == str(export_path)
            assert info["structure_solid_count"] == 1
            assert info["structure_solid_segment_count"] == 1
            assert info["export_readiness_status"] == "warning"
            assert info["export_diagnostic_count"] == 1
            assert info["packaged_output_count"] == 4
            assert payload["exchange_output_id"] == "exchange:structure-solids"
            assert payload["format"] == "ifc"
            assert payload["structure_solid_rows"][0]["structure_id"] == "bridge:1"
            assert payload["source_context_rows"][0]["structure_ref"] == "bridge:1"
            assert payload["structure_solid_rows"][0]["placement_x"] == 5.0
            assert payload["structure_solid_rows"][0]["placement_z"] == 10.25
            assert payload["structure_solid_rows"][0]["start_x"] == 5.0
            assert payload["structure_solid_rows"][0]["end_x"] == 15.0
            assert payload["structure_solid_rows"][0]["end_z"] == 10.75
            assert payload["structure_solid_segment_count"] == 1
            assert payload["structure_solid_segment_rows"][0]["segment_index"] == 1
            assert payload["export_readiness_status"] == "warning"
            assert payload["export_diagnostic_rows"][0]["kind"] == "simplified_ifc_geometry"
            assert payload["quantity_fragment_rows"]

            ifc_path = Path(temp_dir) / "structure_exchange_package.ifc"
            ifc_info = export_document_structure_output_package_ifc(str(ifc_path), document=doc, project=project)
            ifc_text = ifc_path.read_text(encoding="utf-8")
            assert ifc_info["path"] == str(ifc_path)
            assert ifc_info["structure_solid_count"] == 1
            assert ifc_info["structure_solid_segment_count"] == 1
            assert ifc_info["export_readiness_status"] == "warning"
            assert ifc_info["export_diagnostic_count"] == 1
            assert ifc_info["ifc_entity_count"] > 5
            assert "ISO-10303-21;" in ifc_text
            assert "FILE_SCHEMA(('IFC4'));" in ifc_text
            assert "IFCBUILDINGELEMENTPROXY" in ifc_text
            assert "IFCLOCALPLACEMENT" in ifc_text
            assert "IFCCARTESIANPOINT((5.000000,0.000000,10.250000));" in ifc_text
            assert "IFCDIRECTION((1.000000000,0.000000000,0.));" in ifc_text
            assert "IFCRECTANGLEPROFILEDEF(.AREA.,'bridge:1:profile'" in ifc_text
            assert "IFCEXTRUDEDAREASOLID" in ifc_text
            assert "IFCSHAPEREPRESENTATION" in ifc_text
            assert "IFCPRODUCTDEFINITIONSHAPE" in ifc_text
            assert "IFCPROPERTYSET" in ifc_text
            assert "'PlacementZ',$,IFCLENGTHMEASURE(10.250000)" in ifc_text
            assert "'TangentDirectionDeg',$,IFCREAL(0.000000)" in ifc_text
            assert "'SegmentCount',$,IFCINTEGER(1)" in ifc_text
            assert "'GeometrySegmentation',$,IFCTEXT('single_segment')" in ifc_text
            assert "'ExportReadinessStatus',$,IFCTEXT('warning')" in ifc_text
            assert "'ExportDiagnosticKinds',$,IFCTEXT('simplified_ifc_geometry')" in ifc_text
            assert "'SourceStructureRef',$,IFCTEXT('bridge:1')" in ifc_text
            assert "'StartX',$,IFCLENGTHMEASURE(5.000000)" in ifc_text
            assert "'EndX',$,IFCLENGTHMEASURE(15.000000)" in ifc_text
            assert "'EndZ',$,IFCLENGTHMEASURE(10.750000)" in ifc_text
            assert "'EndTangentDirectionDeg',$,IFCREAL(0.000000)" in ifc_text
            assert "bridge:1" in ifc_text
            assert ",11.000000,0.600000);" in ifc_text
            assert "IFCEXTRUDEDAREASOLID" in ifc_text and ",10.000000);" in ifc_text
            assert "IFCVOLUMEMEASURE(66.000000)" in ifc_text
            assert "END-ISO-10303-21;" in ifc_text
    finally:
        App.closeDocument(doc.Name)


def test_structure_output_package_json_preserves_bench_source_context() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_benched_sections())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_structure_model())

        result = build_document_structure_output_package(doc, project=project)
        package_obj = apply_v1_structure_output_package(document=doc, project=project, package_result=result)
        persisted_payload = exchange_package_payload(package_obj)
        persisted_context = list(persisted_payload["source_context_rows"])
        component_contexts = [
            row for row in persisted_context if row.get("context_kind") == "section_side_slope_component"
        ]
        quantity_contexts = [
            row for row in persisted_context if row.get("context_kind") == "side_slope_quantity_fragment"
        ]

        assert result.exchange_output.payload_metadata["side_slope_source_context_count"] >= 2
        assert result.exchange_output.payload_metadata["bench_source_context_count"] >= 2
        assert persisted_payload["payload_metadata"]["side_slope_source_context_count"] >= 2
        assert persisted_payload["payload_metadata"]["bench_source_context_count"] >= 2
        assert component_contexts
        assert quantity_contexts
        assert component_contexts[0]["assembly_ref"] == "assembly:bench-road"
        assert component_contexts[0]["region_ref"] == "region:bench-01"
        assert component_contexts[0]["component_ref"] == "side-slope-right:bench:1"
        assert component_contexts[0]["component_kind"] == "bench"
        assert quantity_contexts[0]["assembly_ref"] == "assembly:bench-road"
        assert quantity_contexts[0]["region_ref"] == "region:bench-01"
        assert quantity_contexts[0]["measurement_kind"] == "section_side_slope_breakline"

        with tempfile.TemporaryDirectory(prefix="cr_v1_bench_exchange_export_") as temp_dir:
            export_path = Path(temp_dir) / "bench_exchange_package.json"
            ifc_path = Path(temp_dir) / "bench_exchange_package.ifc"
            info = export_document_structure_output_package_json(
                str(export_path),
                document=doc,
                project=project,
                exchange_package=package_obj,
            )
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            exported_context = list(exported["source_context_rows"])
            exported_component_contexts = [
                row for row in exported_context if row.get("context_kind") == "section_side_slope_component"
            ]
            exported_quantity_contexts = [
                row for row in exported_context if row.get("context_kind") == "side_slope_quantity_fragment"
            ]

            assert info["side_slope_source_context_count"] >= 2
            assert info["bench_source_context_count"] >= 2
            assert exported["payload_metadata"]["side_slope_source_context_count"] >= 2
            assert exported["payload_metadata"]["bench_source_context_count"] >= 2
            assert exported_component_contexts[0]["assembly_ref"] == "assembly:bench-road"
            assert exported_component_contexts[0]["region_ref"] == "region:bench-01"
            assert exported_component_contexts[0]["component_ref"] == "side-slope-right:bench:1"
            exported_bench_quantity_contexts = [
                row for row in exported_quantity_contexts if row.get("quantity_kind") == "bench_surface_length"
            ]
            assert exported_bench_quantity_contexts
            assert exported_bench_quantity_contexts[0]["measurement_kind"] == "section_side_slope_breakline"

            ifc_info = export_document_structure_output_package_ifc(
                str(ifc_path),
                document=doc,
                project=project,
                exchange_package=package_obj,
            )
            after_ifc_payload = exchange_package_payload(package_obj)
            after_ifc_bench_contexts = [
                row
                for row in list(after_ifc_payload["source_context_rows"])
                if row.get("component_kind") == "bench" or row.get("quantity_kind") == "bench_surface_length"
            ]
            assert ifc_info["export_diagnostic_count"] == 1
            assert after_ifc_bench_contexts
    finally:
        App.closeDocument(doc.Name)


def test_structure_ifc_export_uses_segmented_swept_solids_for_multi_frame_ranges() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections_with_centerline_curve())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_long_structure_model())

        result = build_document_structure_output_package(doc, project=project)

        assert len(result.structure_solid_output.solid_rows) == 1
        assert len(result.structure_solid_output.solid_segment_rows) == 2
        assert [row.station_start for row in result.structure_solid_output.solid_segment_rows] == [5.0, 20.0]
        assert [row.station_end for row in result.structure_solid_output.solid_segment_rows] == [20.0, 35.0]
        assert [row.kind for row in result.structure_solid_output.diagnostic_rows] == ["ifc_segmented_proxy_geometry"]
        assert result.exchange_output.payload_metadata["structure_solid_segment_count"] == 2
        assert result.exchange_output.payload_metadata["diagnostic_count"] == 1

        package_obj = apply_v1_structure_output_package(document=doc, project=project, package_result=result)
        assert package_obj.ExportReadinessStatus == "ready"
        assert int(package_obj.ExportDiagnosticCount) == 1
        with tempfile.TemporaryDirectory(prefix="cr_v1_ifc_segment_export_") as temp_dir:
            ifc_path = Path(temp_dir) / "structure_exchange_package.ifc"
            info = export_document_structure_output_package_ifc(str(ifc_path), document=doc, project=project, exchange_package=package_obj)
            ifc_text = ifc_path.read_text(encoding="utf-8")

            assert info["structure_solid_segment_count"] == 2
            assert info["export_readiness_status"] == "ready"
            assert info["export_diagnostic_count"] == 1
            assert ifc_text.count("IFCEXTRUDEDAREASOLID") == 2
            assert "IFCSHAPEREPRESENTATION" in ifc_text
            assert "bridge:long:segment:1:profile" in ifc_text
            assert "bridge:long:segment:2:profile" in ifc_text
            assert "'SegmentCount',$,IFCINTEGER(2)" in ifc_text
            assert "'GeometrySegmentation',$,IFCTEXT('segmented')" in ifc_text
            assert "'IFCGeometryMode',$,IFCTEXT('segmented_swept_solid')" in ifc_text
            assert "'ExportReadinessStatus',$,IFCTEXT('ready')" in ifc_text
            assert "'ExportDiagnosticKinds',$,IFCTEXT('ifc_segmented_proxy_geometry')" in ifc_text
    finally:
        App.closeDocument(doc.Name)


def test_structure_ifc_export_blocks_error_readiness_diagnostics() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_invalid_structure_model())

        result = build_document_structure_output_package(doc, project=project)

        diagnostic_kinds = [row.kind for row in result.structure_solid_output.diagnostic_rows]
        assert "missing_or_invalid_dimensions" in diagnostic_kinds
        assert "zero_length" in diagnostic_kinds
        assert "unsupported_skew" in diagnostic_kinds
        summary = structure_output_package_summary(result)
        assert summary["export_readiness_status"] == "error"
        assert summary["export_diagnostic_count"] == 4

        package_obj = apply_v1_structure_output_package(document=doc, project=project, package_result=result)
        assert package_obj.ExportReadinessStatus == "error"
        assert int(package_obj.ExportDiagnosticCount) == 4
        with tempfile.TemporaryDirectory(prefix="cr_v1_ifc_invalid_export_") as temp_dir:
            ifc_path = Path(temp_dir) / "structure_exchange_package.ifc"
            try:
                export_document_structure_output_package_ifc(
                    str(ifc_path),
                    document=doc,
                    project=project,
                    exchange_package=package_obj,
                )
            except RuntimeError as exc:
                assert "blocking diagnostic" in str(exc)
                assert "missing_or_invalid_dimensions" in str(exc)
            else:
                raise AssertionError("IFC export should block structures with error readiness diagnostics.")
            assert not ifc_path.exists()
    finally:
        App.closeDocument(doc.Name)


def test_exchange_package_persists_large_payloads_as_chunks() -> None:
    doc, project = _new_project_doc()
    try:
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_large_structure_model())

        result = build_document_structure_output_package(doc, project=project)
        package_obj = apply_v1_structure_output_package(document=doc, project=project, package_result=result)

        assert package_obj.PayloadStorageMode == "chunked"
        assert int(package_obj.PayloadByteCount) > 16000
        assert list(package_obj.StructureSolidRowsJsonChunks)
        assert list(package_obj.QuantityFragmentRowsJsonChunks)
        assert "__corridorroad_chunked_json__" in package_obj.StructureSolidRowsJson
        payload = exchange_package_payload(package_obj)
        assert payload["payload_storage_mode"] == "chunked"
        assert payload["structure_solid_count"] == 180
        assert len(payload["structure_solid_rows"]) == 180
        assert payload["structure_solid_rows"][-1]["structure_id"] == "bridge:large-179"
        assert len(payload["quantity_fragment_rows"]) == 180

        with tempfile.TemporaryDirectory(prefix="cr_v1_exchange_chunked_export_") as temp_dir:
            export_path = Path(temp_dir) / "structure_exchange_package.json"
            info = export_document_structure_output_package_json(str(export_path), document=doc, project=project)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            assert info["structure_solid_count"] == 180
            assert exported["payload_storage_mode"] == "chunked"
            assert exported["structure_solid_rows"][0]["structure_id"] == "bridge:large-000"
            assert exported["quantity_fragment_rows"][-1]["structure_ref"] == "bridge:large-179"
            fcstd_path = Path(temp_dir) / "chunked_exchange_package.FCStd"
            doc.saveAs(str(fcstd_path))
            doc_name = doc.Name
            App.closeDocument(doc_name)
            doc = None
            reopened = App.openDocument(str(fcstd_path))
            try:
                reloaded_package = find_v1_exchange_package(reopened)
                reloaded_payload = exchange_package_payload(reloaded_package)
                assert reloaded_payload["payload_storage_mode"] == "chunked"
                assert len(reloaded_payload["structure_solid_rows"]) == 180
                assert reloaded_payload["structure_solid_rows"][-1]["structure_id"] == "bridge:large-179"
            finally:
                App.closeDocument(reopened.Name)
    finally:
        if doc is not None:
            App.closeDocument(doc.Name)


def test_structure_output_panel_can_build_structure_output_package() -> None:
    class FakeSummary:
        def __init__(self):
            self.text = ""

        def setPlainText(self, text):
            self.text = str(text)

        def toPlainText(self):
            return self.text

    doc, project = _new_project_doc()
    original_show_message = structure_output_command._show_message
    try:
        structure_output_command._show_message = lambda *_args, **_kwargs: None
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_sample_sections())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_sample_structure_model())
        panel = structure_output_command.V1StructureOutputTaskPanel.__new__(
            structure_output_command.V1StructureOutputTaskPanel
        )
        panel.document = doc
        panel.form = None
        panel._summary = FakeSummary()
        panel._last_structure_output_package = None

        assert panel._build_structure_output_package() is True
        assert panel._last_structure_output_package is not None
        summary_text = panel._summary.toPlainText()
        assert "Structure output package has been built." in summary_text
        assert "Structure solids: 1" in summary_text
        assert "Structure segments: 1" in summary_text
        assert "IFC export: allowed with warnings" in summary_text
        assert "Diagnostic summary: warning 1; kinds: simplified_ifc_geometry" in summary_text
        assert "Section outputs: 2" in summary_text
        assert "Source contexts:" in summary_text
        assert "Packaged outputs: 4" in summary_text
        assert "Object: Structure Geometry Exchange Package" in summary_text
        package_obj = find_v1_exchange_package(doc)
        assert package_obj is not None
        assert package_obj.ExchangeOutputId == "exchange:structure-solids"

        panel._refresh_summary()
        refreshed_text = panel._summary.toPlainText()
        assert "Current persisted package:" in refreshed_text
        assert "IFC export: allowed with warnings" in refreshed_text
        assert "Diagnostic summary: warning 1; kinds: simplified_ifc_geometry" in refreshed_text
    finally:
        structure_output_command._show_message = original_show_message
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 structure output command contract tests completed.")
