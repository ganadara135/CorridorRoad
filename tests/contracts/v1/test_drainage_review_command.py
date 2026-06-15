from dataclasses import replace

import FreeCAD as App

from freecad.Corridor_Road.init_gui import corridorroad_workflow_toolbar_commands
from freecad.Corridor_Road.objects.obj_project import V1_TREE_DRAINAGE, V1_TREE_QUANTITIES, V1_TREE_STRUCTURES, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_drainage_review import (
    CmdV1DrainageReview,
    V1DrainageReviewTaskPanel,
    _drainage_review_navigation_targets,
    _filter_flow_route_rows,
    _filter_pipeline_candidate_rows,
    _filter_report_rows,
    _filter_region_assignment_rows,
    _geometry_rows_snapped_to_structure_previews,
    build_drainage_review_output,
    run_v1_drainage_review_command,
    show_drainage_flow_route_issue_preview_object,
    show_drainage_pipeline_candidate_preview_object,
    show_drainage_pipeline_network_preview_object,
    show_drainage_pipeline_networks_preview_object,
    show_drainage_pipeline_segment_preview_object,
)
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import drainage_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_structure_editor import structure_preset_model_from_document
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame, AppliedSectionPoint
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.models.output.drainage_output import (
    DrainageElementOutputRow,
    DrainageOutput,
    DrainagePipelineGeometryOutputRow,
    DrainagePipelineSegmentOutputRow,
)
from freecad.Corridor_Road.v1.models.result.quantity_model import QuantityFragment, QuantityModel
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageFlowRoute, DrainageModel
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.models.source.structure_model import StructureConnectionPoint, StructureModel, StructurePlacement, StructureRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment, to_alignment_model
from freecad.Corridor_Road.v1.objects.obj_applied_section import create_or_update_v1_applied_section_set_object
from freecad.Corridor_Road.v1.objects.obj_drainage import create_or_update_v1_drainage_model_object
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_quantity import create_or_update_v1_quantity_model_object, find_v1_quantity_model, to_quantity_model
from freecad.Corridor_Road.v1.objects.obj_region import create_or_update_v1_region_model_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_structure import create_or_update_v1_structure_model_object
from freecad.Corridor_Road.v1.services.evaluation.drainage_resolution_service import build_drainage_pipeline_result
from freecad.Corridor_Road.v1.services.mapping.drainage_review_mapper import DrainageReviewMapper

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _new_project_doc(name: str):
    doc = App.newDocument(name)
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:main",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:side-ditch-right",
                element_kind="ditch",
                side="right",
                region_ref="region:drainage",
                station_start=0.0,
                station_end=100.0,
                subassembly_ref="ditch:right",
                policy_set_ref="drainage-policy:lined-concrete",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outfall-right",
                element_kind="outfall_reference",
                side="right",
                region_ref="region:drainage",
                structure_ref="outfall:right",
                station_start=99.0,
                station_end=100.0,
                policy_set_ref="drainage-policy:lined-concrete",
            )
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:right",
                from_element_ref="drainage:side-ditch-right",
                to_element_ref="drainage:outfall-right",
                outlet_ref="drainage:outfall-right",
                direction="roadside_flow",
                risk_level="medium",
            )
        ],
    )


def _pipeline_drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:pipeline",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                structure_ref="structure:inlet-01",
                connection_point_ref="connection:inlet-01:pipe-out",
                station_start=30.0,
                station_end=32.0,
                policy_set_ref="drainage-policy:pipe",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outlet-01",
                element_kind="outfall_reference",
                structure_ref="structure:outlet-01",
                connection_point_ref="connection:outlet-01:pipe-in",
                station_start=90.0,
                station_end=92.0,
                policy_set_ref="drainage-policy:pipe",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:pipe-01",
                from_element_ref="drainage:inlet-01",
                to_element_ref="drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            )
        ],
    )


def _pipeline_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:pipeline",
        structure_rows=[
            StructureRow(
                structure_id="structure:inlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:inlet-01", "alignment:main", 30.0, 32.0),
                native_type="inlet",
            ),
            StructureRow(
                structure_id="structure:outlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:outlet-01", "alignment:main", 90.0, 92.0),
                native_type="outlet",
            ),
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:inlet-01:pipe-out",
                structure_ref="structure:inlet-01",
                point_role="pipe_out",
                station=32.0,
                offset=-4.5,
                invert_elevation=44.2,
                diameter=0.6,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:outlet-01:pipe-in",
                structure_ref="structure:outlet-01",
                point_role="pipe_in",
                station=90.0,
                offset=-6.0,
                invert_elevation=43.6,
                diameter=0.6,
                shape_kind="circular",
            ),
        ],
    )


def _pipeline_network_drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:pipeline-network",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                structure_ref="structure:inlet-01",
                connection_point_ref="connection:inlet-01:pipe-out",
                station_start=30.0,
                station_end=32.0,
                policy_set_ref="drainage-policy:pipe",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:junction-01",
                element_kind="junction_reference",
                structure_ref="structure:junction-01",
                connection_point_ref="connection:junction-01:pipe",
                station_start=60.0,
                station_end=61.0,
                policy_set_ref="drainage-policy:pipe",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outlet-01",
                element_kind="outfall_reference",
                structure_ref="structure:outlet-01",
                connection_point_ref="connection:outlet-01:pipe-in",
                station_start=90.0,
                station_end=92.0,
                policy_set_ref="drainage-policy:pipe",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:pipe-01",
                from_element_ref="drainage:inlet-01",
                to_element_ref="drainage:junction-01",
                outlet_ref="drainage:outlet-01",
            ),
            DrainageFlowRoute(
                flow_route_id="flow-route:pipe-02",
                from_element_ref="drainage:junction-01",
                to_element_ref="drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            ),
        ],
    )


def _pipeline_network_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:pipeline-network",
        structure_rows=[
            StructureRow(
                structure_id="structure:inlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:inlet-01", "alignment:main", 30.0, 32.0),
                native_type="inlet",
            ),
            StructureRow(
                structure_id="structure:junction-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:junction-01", "alignment:main", 60.0, 61.0),
                native_type="junction",
            ),
            StructureRow(
                structure_id="structure:outlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:outlet-01", "alignment:main", 90.0, 92.0),
                native_type="outlet",
            ),
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:inlet-01:pipe-out",
                structure_ref="structure:inlet-01",
                point_role="pipe_out",
                station=32.0,
                offset=-4.5,
                invert_elevation=44.2,
                diameter=0.6,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:junction-01:pipe",
                structure_ref="structure:junction-01",
                point_role="pipe_junction",
                station=60.0,
                offset=-5.2,
                invert_elevation=43.9,
                diameter=0.6,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:outlet-01:pipe-in",
                structure_ref="structure:outlet-01",
                point_role="pipe_in",
                station=90.0,
                offset=-6.0,
                invert_elevation=43.6,
                diameter=0.6,
                shape_kind="circular",
            ),
        ],
    )


def _culvert_through_drainage_model() -> DrainageModel:
    return DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:culvert-through",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                structure_ref="structure:inlet-01",
                connection_point_ref="connection:inlet-01:pipe-out",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:culvert-01",
                element_kind="culvert_reference",
                structure_ref="structure:culvert-01",
                connection_point_ref="connection:culvert-01:upstream",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outlet-01",
                element_kind="outfall_reference",
                structure_ref="structure:outlet-01",
                connection_point_ref="connection:outlet-01:pipe-in",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:flowId-01",
                from_element_ref="drainage:inlet-01",
                to_element_ref="drainage:culvert-01",
                outlet_ref="drainage:outlet-01",
            ),
            DrainageFlowRoute(
                flow_route_id="flow-route:flowId-02",
                from_element_ref="drainage:culvert-01",
                to_element_ref="drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            ),
        ],
    )


def _culvert_through_structure_model() -> StructureModel:
    return StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:culvert-through",
        structure_rows=[
            StructureRow("structure:inlet-01", "utility", "reference", StructurePlacement("placement:inlet-01", "alignment:main", 30.0, 32.0), native_type="inlet"),
            StructureRow("structure:culvert-01", "culvert", "crossing", StructurePlacement("placement:culvert-01", "alignment:main", 45.0, 55.0), native_type="pipe_culvert"),
            StructureRow("structure:outlet-01", "utility", "reference", StructurePlacement("placement:outlet-01", "alignment:main", 70.0, 72.0), native_type="outlet"),
        ],
        connection_point_rows=[
            StructureConnectionPoint("connection:inlet-01:pipe-out", "structure:inlet-01", "pipe_out", station=32.0, offset=-5.0, diameter=0.75),
            StructureConnectionPoint("connection:culvert-01:upstream", "structure:culvert-01", "upstream", station=45.0, offset=-5.0, diameter=0.9),
            StructureConnectionPoint("connection:culvert-01:downstream", "structure:culvert-01", "downstream", station=55.0, offset=5.8, diameter=0.9),
            StructureConnectionPoint("connection:outlet-01:pipe-in", "structure:outlet-01", "pipe_in", station=70.0, offset=5.8, diameter=0.9),
        ],
    )


def _region_model() -> RegionModel:
    return RegionModel(
        schema_version=1,
        project_id="proj-review",
        region_model_id="regions:main",
        region_rows=[
            RegionRow(
                region_id="region:drainage",
                station_start=0.0,
                station_end=100.0,
            )
        ],
    )


def _applied_set() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-review",
        applied_section_set_id="applied:main",
        corridor_id="corridor:main",
        station_rows=[AppliedSectionStationRow("station:0", 0.0, "section:0")],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-review",
                applied_section_id="section:0",
                station=0.0,
                frame=AppliedSectionFrame(station=0.0, z=10.0),
                point_rows=[
                    AppliedSectionPoint(
                        "ditch:right-edge",
                        0.0,
                        -5.0,
                        10.0,
                        "ditch_surface",
                        -5.0,
                        subassembly_ref="ditch:right",
                        side="right",
                        drainage_ref="drainage:side-ditch-right",
                    ),
                    AppliedSectionPoint(
                        "ditch:right-flow",
                        0.0,
                        -6.0,
                        9.8,
                        "ditch_surface",
                        -6.0,
                        subassembly_ref="ditch:right",
                        side="right",
                        drainage_ref="drainage:side-ditch-right",
                    ),
                ],
            )
        ],
    )


def test_drainage_review_mapper_reports_source_handoff_and_applied_context() -> None:
    output = DrainageReviewMapper().map(
        drainage_model=_drainage_model(),
        region_model=_region_model(),
        applied_section_set=_applied_set(),
        project_id="proj-review",
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}
    region_rows = [row for row in output.element_rows if row.kind == "region_assignment"]
    flow_route_rows = [row for row in output.element_rows if row.kind == "flow_route"]
    applied_rows = [row for row in output.element_rows if row.kind == "applied_section_ditch_context"]

    assert summary["summary:drainage-elements"] == 2
    assert summary["summary:flow-routes"] == 1
    assert summary["summary:pipeline-segment-candidates"] == 0
    assert summary["summary:region-assignments"] == 2
    assert summary["summary:region-assignment-issues"] == 0
    assert summary["summary:ditch-surface-points"] == 2
    assert summary["summary:ditch-surface-points-with-drainage"] == 2
    assert summary["summary:flowline-continuity-spans"] == 0
    assert summary["summary:flowline-continuity-issues"] == 0
    assert flow_route_rows[0].label == "flow-route:right"
    assert "chain=drainage:side-ditch-right -> drainage:outfall-right" in flow_route_rows[0].notes
    assert "from_region_ref=region:drainage" in flow_route_rows[0].notes
    assert "from_policy_set_ref=drainage-policy:lined-concrete" in flow_route_rows[0].notes
    assert any(
        row.source_ref == "drainage:side-ditch-right"
        and "region_ref=region:drainage" in row.notes
        and "status=ok" in row.notes
        for row in region_rows
    )
    assert applied_rows[0].notes == "ditch_points=2;drainage_refs=drainage:side-ditch-right;subassembly_refs=ditch:right;sides=right"
    assert output.source_refs == ["drainage:main", "regions:main", "applied:main"]


def test_drainage_review_mapper_reports_flowline_continuity_rows() -> None:
    applied_set = AppliedSectionSet(
        schema_version=1,
        project_id="proj-review",
        applied_section_set_id="applied:flowline",
        corridor_id="corridor:main",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-review",
                applied_section_id="section:0",
                station=0.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 0.0, -6.0, 10.0, "ditch_surface", -6.0, "ditch:right", "right", "drainage:right"),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-review",
                applied_section_id="section:10",
                station=10.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 10.0, -6.0, 9.8, "ditch_surface", -6.0, "ditch:right", "right", "drainage:right"),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-review",
                applied_section_id="section:20",
                station=20.0,
                point_rows=[
                    AppliedSectionPoint("ditch:right-flow", 20.0, -6.0, 10.1, "ditch_surface", -6.0, "ditch:right", "right", "drainage:right"),
                ],
            ),
        ],
    )

    output = DrainageReviewMapper().map(applied_section_set=applied_set, project_id="proj-review")
    summary = {row.summary_id: row.value for row in output.summary_rows}
    rows = [row for row in output.element_rows if row.kind == "flowline_continuity"]

    assert summary["summary:flowline-continuity-spans"] == 2
    assert summary["summary:flowline-continuity-issues"] == 1
    assert [row.label for row in rows] == ["ok", "reverse_grade"]
    assert rows[0].source_ref == "drainage:right"
    assert "fall=0.200" in rows[0].notes
    assert "fall=-0.300" in rows[1].notes


def test_drainage_review_mapper_reports_pipeline_segment_candidates_from_connection_points() -> None:
    output = DrainageReviewMapper().map(
        drainage_model=_pipeline_drainage_model(),
        structure_model=_pipeline_structure_model(),
        project_id="proj-review",
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}
    pipeline_rows = [row for row in output.element_rows if row.kind == "pipeline_segment_candidate"]

    assert summary["summary:pipeline-segment-candidates"] == 1
    assert len(pipeline_rows) == 1
    assert pipeline_rows[0].label == "flow-route:pipe-01"
    assert pipeline_rows[0].station_start == 32.0
    assert pipeline_rows[0].station_end == 90.0
    assert "status=ready" in pipeline_rows[0].notes
    assert "from_connection_point_ref=connection:inlet-01:pipe-out" in pipeline_rows[0].notes
    assert "to_connection_point_ref=connection:outlet-01:pipe-in" in pipeline_rows[0].notes
    assert "diameter=0.600" in pipeline_rows[0].notes
    assert output.source_refs == ["drainage:pipeline", "structures:pipeline"]


def test_drainage_pipeline_result_promotes_ready_candidates_to_segments() -> None:
    result = build_drainage_pipeline_result(
        _pipeline_drainage_model(),
        _pipeline_structure_model(),
        project_id="proj-review",
    )

    assert result.drainage_pipeline_result_id == "drainage-pipeline:main"
    assert result.source_refs == ["drainage:pipeline", "structures:pipeline"]
    assert len(result.segment_rows) == 1
    segment = result.segment_rows[0]
    assert segment.pipeline_segment_id == "pipeline-segment:flow-route-pipe-01"
    assert segment.flow_route_ref == "flow-route:pipe-01"
    assert segment.from_connection_point_ref == "connection:inlet-01:pipe-out"
    assert segment.to_connection_point_ref == "connection:outlet-01:pipe-in"
    assert segment.station_start == 32.0
    assert segment.station_end == 90.0
    assert segment.invert_start == 44.2
    assert segment.invert_end == 43.6
    assert segment.diameter == 0.6
    assert result.diagnostic_rows == []


def test_ditch_to_inlet_flow_route_is_capture_only_not_pipe_warning() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:capture",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:side-ditch-right-01",
                element_kind="ditch",
                station_start=0.0,
                station_end=50.0,
                subassembly_ref="ditch:right",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                structure_ref="structure:inlet-01",
                station_start=48.0,
                station_end=52.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:flowId-01",
                from_element_ref="drainage:side-ditch-right-01",
                to_element_ref="drainage:inlet-01",
            )
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:capture",
        structure_rows=[
            StructureRow(
                structure_id="structure:inlet-01",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:inlet-01", "alignment:main", 48.0, 52.0, offset=-5.2),
                native_type="inlet",
            )
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:inlet-01:pipe-out",
                structure_ref="structure:inlet-01",
                point_role="pipe_out",
                station=52.0,
                offset=-5.2,
                diameter=0.9,
            )
        ],
    )

    output = DrainageReviewMapper().map(
        drainage_model=drainage_model,
        structure_model=structure_model,
        project_id="proj-review",
    )
    result = build_drainage_pipeline_result(drainage_model, structure_model, project_id="proj-review")
    candidates = [row for row in output.element_rows if row.kind == "pipeline_segment_candidate"]
    summary = {row.summary_id: row.value for row in output.summary_rows}

    assert len(candidates) == 1
    assert "status=capture_only" in candidates[0].notes
    assert "flow_relationship=capture" in candidates[0].notes
    assert summary["summary:pipeline-segments"] == 0
    assert result.segment_rows == []
    assert result.diagnostic_rows == []


def test_drainage_pipeline_result_preserves_explicit_culvert_pipe_in_port() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:pipeline",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-03",
                element_kind="inlet",
                structure_ref="structure:inlet-03",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:culvert-01",
                element_kind="culvert_reference",
                structure_ref="structure:culvert-01",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:flowId-06",
                from_element_ref="drainage:inlet-03",
                to_element_ref="drainage:culvert-01",
            )
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:pipeline",
        structure_rows=[
            StructureRow(
                structure_id="structure:inlet-03",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:inlet-03", "alignment:main", 90.0, 92.0, offset=-5.2),
                native_type="inlet",
            ),
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:culvert-01", "alignment:main", 120.0, 140.0, offset=0.0),
                native_type="pipe_culvert",
            ),
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:inlet-03:pipe-out",
                structure_ref="structure:inlet-03",
                point_role="pipe_out",
                station=92.0,
                offset=-5.2,
                diameter=1.2,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:custom-in-port",
                structure_ref="structure:culvert-01",
                point_role="pipe_in",
                station=105.0,
                offset=-3.0,
                diameter=1.2,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:pipe-out",
                structure_ref="structure:culvert-01",
                point_role="pipe_out",
                station=150.0,
                offset=2.0,
                diameter=1.2,
                shape_kind="circular",
            ),
        ],
    )

    result = build_drainage_pipeline_result(drainage_model, structure_model, project_id="proj-review")

    assert len(result.segment_rows) == 1
    segment = result.segment_rows[0]
    assert segment.to_connection_point_ref == "connection:culvert-01:custom-in-port"
    assert segment.station_end == 105.0
    assert segment.to_offset == -3.0


def test_drainage_pipeline_result_snaps_derived_culvert_upstream_port_to_current_placement() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:pipeline",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-03",
                element_kind="inlet",
                structure_ref="structure:inlet-03",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:culvert-01",
                element_kind="culvert_reference",
                structure_ref="structure:culvert-01",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:flowId-06",
                from_element_ref="drainage:inlet-03",
                to_element_ref="drainage:culvert-01",
            )
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:pipeline",
        structure_rows=[
            StructureRow(
                structure_id="structure:inlet-03",
                structure_kind="utility",
                structure_role="reference",
                placement=StructurePlacement("placement:inlet-03", "alignment:main", 90.0, 92.0, offset=-5.2),
                native_type="inlet",
            ),
            StructureRow(
                structure_id="structure:culvert-01",
                structure_kind="culvert",
                structure_role="clearance_control",
                placement=StructurePlacement("placement:culvert-01", "alignment:main", 120.0, 140.0, offset=0.0),
                native_type="pipe_culvert",
            ),
        ],
        connection_point_rows=[
            StructureConnectionPoint(
                connection_point_id="connection:inlet-03:pipe-out",
                structure_ref="structure:inlet-03",
                point_role="pipe_out",
                station=92.0,
                offset=-5.2,
                diameter=1.2,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:upstream",
                structure_ref="structure:culvert-01",
                point_role="upstream",
                station=105.0,
                offset=-3.0,
                diameter=1.2,
                shape_kind="circular",
            ),
            StructureConnectionPoint(
                connection_point_id="connection:culvert-01:downstream",
                structure_ref="structure:culvert-01",
                point_role="downstream",
                station=150.0,
                offset=2.0,
                diameter=1.2,
                shape_kind="circular",
            ),
        ],
    )

    result = build_drainage_pipeline_result(drainage_model, structure_model, project_id="proj-review")

    assert len(result.segment_rows) == 1
    segment = result.segment_rows[0]
    assert segment.to_connection_point_ref == "connection:culvert-01:upstream"
    assert segment.station_end == 120.0
    assert segment.to_offset == 0.0


def test_drainage_network_preview_geometry_snaps_culvert_endpoint_to_structure_preview() -> None:
    doc, project = _new_project_doc("V1DrainagePipelinePreviewSnapTest")
    try:
        create_sample_v1_alignment(doc, project=project)
        create_or_update_v1_structure_model_object(
            doc,
            project=project,
            structure_model=StructureModel(
                schema_version=1,
                project_id="proj-review",
                structure_model_id="structures:pipeline",
                structure_rows=[
                    StructureRow(
                        structure_id="structure:culvert-01",
                        structure_kind="culvert",
                        structure_role="clearance_control",
                        placement=StructurePlacement("placement:culvert-01", "alignment:main", 120.0, 140.0, offset=0.0),
                        native_type="pipe_culvert",
                    )
                ],
                connection_point_rows=[
                    StructureConnectionPoint(
                        connection_point_id="connection:culvert-01:any-saved-in-port",
                        structure_ref="structure:culvert-01",
                        point_role="pipe_in",
                        station=105.0,
                        offset=-5.2,
                        diameter=1.2,
                        shape_kind="circular",
                    )
                ],
            ),
        )
        output = DrainageOutput(
            schema_version=1,
            project_id="proj-review",
            drainage_output_id="drainage-review:main",
            pipeline_segment_rows=[
                DrainagePipelineSegmentOutputRow(
                    pipeline_segment_id="pipeline-segment:flow-route-flowId-06",
                    flow_route_ref="flow-route:flowId-06",
                    from_connection_point_ref="connection:inlet-03:pipe-out",
                    to_connection_point_ref="connection:culvert-01:any-saved-in-port",
                    station_start=95.0,
                    station_end=105.0,
                )
            ],
        )
        rows = [
            DrainagePipelineGeometryOutputRow(
                geometry_row_id="pipeline-geometry:flow-route-flowId-06",
                pipeline_segment_id="pipeline-segment:flow-route-flowId-06",
                flow_route_ref="flow-route:flowId-06",
                centerline_points=[(95.0, -5.2, 0.0), (105.0, -5.2, 0.0)],
                diameter=1.2,
                shape_kind="circular",
            )
        ]

        snapped = _geometry_rows_snapped_to_structure_previews(doc, output, rows)

        assert snapped[0].centerline_points[0] == (95.0, -5.2, 0.0)
        assert snapped[0].centerline_points[-1] != (105.0, -5.2, 0.0)
        assert snapped[0].centerline_points[-1][1] == 18.0
        assert "preview_endpoint_snap=structure_culvert" in snapped[0].notes
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_mapper_reports_pipeline_segment_output_rows() -> None:
    output = DrainageReviewMapper().map(
        drainage_model=_pipeline_drainage_model(),
        structure_model=_pipeline_structure_model(),
        project_id="proj-review",
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}
    flow_route_rows = [row for row in output.element_rows if row.kind == "flow_route"]

    assert summary["summary:pipeline-segments"] == 1
    assert summary["summary:pipeline-geometries"] == 1
    assert summary["summary:pipeline-solid-candidates"] == 1
    assert summary["summary:pipeline-solid-length"] > 50.0
    assert summary["summary:report-inlet-count"] == 1
    assert summary["summary:report-culvert-count"] == 0
    assert summary["summary:report-outlet-count"] == 1
    assert summary["summary:report-pipe-length"] > 50.0
    assert summary["summary:report-pipe-policy-groups"] == 1
    assert summary["summary:report-pipe-policy-warnings"] == 0
    assert output.result_refs == ["drainage-pipeline:main"]
    assert len(output.pipeline_segment_rows) == 1
    segment = output.pipeline_segment_rows[0]
    assert segment.pipeline_segment_id == "pipeline-segment:flow-route-pipe-01"
    assert segment.flow_route_ref == "flow-route:pipe-01"
    assert segment.from_connection_point_ref == "connection:inlet-01:pipe-out"
    assert segment.to_connection_point_ref == "connection:outlet-01:pipe-in"
    assert segment.shape_kind == "circular"
    assert len(output.pipeline_geometry_rows) == 1
    geometry = output.pipeline_geometry_rows[0]
    assert geometry.pipeline_segment_id == "pipeline-segment:flow-route-pipe-01"
    assert geometry.coordinate_mode == "station_offset_fallback"
    assert len(geometry.centerline_points) == 2
    assert geometry.centerline_points[0] == (32.0, -4.5, 44.2)
    assert geometry.centerline_points[-1] == (90.0, -6.0, 43.6)
    assert len(output.pipeline_solid_rows) == 1
    solid = output.pipeline_solid_rows[0]
    assert solid.pipeline_segment_id == "pipeline-segment:flow-route-pipe-01"
    assert solid.flow_route_ref == "flow-route:pipe-01"
    assert solid.is_capped is True
    assert solid.cap_count == 2
    assert solid.length > 50.0
    assert solid.volume > 0.0
    assert "pipeline_solid_status=ready" in flow_route_rows[0].notes
    assert "pipeline_solid_caps=2" in flow_route_rows[0].notes
    report_rows = [row for row in output.element_rows if row.kind == "drainage_report"]
    assert any(row.label == "inlet_count" and "value=1" in row.notes for row in report_rows)
    assert any(row.label == "outlet_count" and "value=1" in row.notes for row in report_rows)
    assert any(
        row.label == "pipe_length_by_policy"
        and row.source_ref == "drainage-policy:pipe"
        and "flow_route_refs=flow-route:pipe-01" in row.notes
        for row in report_rows
    )


def test_drainage_review_mapper_reports_mixed_policy_pipe_warning() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:mixed-policy",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                structure_ref="structure:inlet-01",
                connection_point_ref="connection:inlet-01:pipe-out",
                station_start=30.0,
                station_end=32.0,
                policy_set_ref="drainage-policy:small-pipe",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:outlet-01",
                element_kind="outfall_reference",
                structure_ref="structure:outlet-01",
                connection_point_ref="connection:outlet-01:pipe-in",
                station_start=90.0,
                station_end=92.0,
                policy_set_ref="drainage-policy:large-pipe",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:mixed-policy",
                from_element_ref="drainage:inlet-01",
                to_element_ref="drainage:outlet-01",
                outlet_ref="drainage:outlet-01",
            )
        ],
    )

    output = DrainageReviewMapper().map(
        drainage_model=drainage_model,
        structure_model=_pipeline_structure_model(),
        project_id="proj-review",
    )
    summary = {row.summary_id: row.value for row in output.summary_rows}
    report_rows = [row for row in output.element_rows if row.kind == "drainage_report"]

    assert summary["summary:report-pipe-policy-groups"] == 1
    assert summary["summary:report-pipe-policy-warnings"] == 1
    assert any(
        row.label == "pipe_length_by_policy"
        and row.source_ref == "mixed-policy"
        and "flow_route_refs=flow-route:mixed-policy" in row.notes
        for row in report_rows
    )
    assert any(
        row.label == "pipe_policy_warning"
        and row.source_ref == "flow-route:mixed-policy"
        and "policy_refs=drainage-policy:small-pipe,drainage-policy:large-pipe" in row.notes
        for row in report_rows
    )
    warning_rows = _filter_report_rows(report_rows, warnings_only=True)
    assert [row.label for row in warning_rows] == ["pipe_policy_warning"]


def test_drainage_review_mapper_reports_pipeline_network_output_rows() -> None:
    output = DrainageReviewMapper().map(
        drainage_model=_pipeline_network_drainage_model(),
        structure_model=_pipeline_network_structure_model(),
        project_id="proj-review",
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}

    assert summary["summary:pipeline-segments"] == 2
    assert summary["summary:pipeline-solid-candidates"] == 2
    assert summary["summary:pipeline-networks"] == 1
    assert summary["summary:pipeline-network-length"] > 50.0
    assert summary["summary:pipeline-junctions"] == 1
    assert summary["summary:pipeline-terminals"] == 2
    assert len(output.pipeline_network_rows) == 1
    assert len(output.pipeline_junction_rows) == 3
    network = output.pipeline_network_rows[0]
    junctions = [row for row in output.pipeline_junction_rows if row.junction_kind == "junction"]
    terminals = [row for row in output.pipeline_junction_rows if row.junction_kind == "terminal"]
    assert network.network_id == "drainage-pipeline-network:main"
    assert network.pipeline_segment_refs == [
        "pipeline-segment:flow-route-pipe-01",
        "pipeline-segment:flow-route-pipe-02",
    ]
    assert network.flow_route_refs == ["flow-route:pipe-01", "flow-route:pipe-02"]
    assert network.segment_count == 2
    assert network.junction_count == 1
    assert network.volume > 0.0
    assert network.validation_status == "ready"
    assert "fuse_mode=compound_first_slice" in network.notes
    assert len(junctions) == 1
    assert len(terminals) == 2
    assert junctions[0].degree == 2
    assert junctions[0].pipeline_segment_refs == [
        "pipeline-segment:flow-route-pipe-01",
        "pipeline-segment:flow-route-pipe-02",
    ]
    assert "connection_point_refs=connection:junction-01:pipe" in junctions[0].notes
    assert "structure_refs=structure:junction-01" in junctions[0].notes
    assert "trim_status=pending" in junctions[0].notes
    assert all("structure_connector_status=pending" in row.notes for row in terminals)
    assert {row.notes for row in terminals} == {
        "endpoint_count=1;connection_point_refs=connection:inlet-01:pipe-out;structure_refs=structure:inlet-01;trim_status=pending;structure_connector_status=pending",
        "endpoint_count=1;connection_point_refs=connection:outlet-01:pipe-in;structure_refs=structure:outlet-01;trim_status=pending;structure_connector_status=pending",
    }


def test_drainage_pipeline_routes_through_culvert_upstream_and_downstream_points() -> None:
    output = DrainageReviewMapper().map(
        drainage_model=_culvert_through_drainage_model(),
        structure_model=_culvert_through_structure_model(),
        project_id="proj-review",
    )

    segments = output.pipeline_segment_rows

    assert [row.flow_route_ref for row in segments] == ["flow-route:flowId-01", "flow-route:flowId-02"]
    assert segments[0].from_connection_point_ref == "connection:inlet-01:pipe-out"
    assert segments[0].to_connection_point_ref == "connection:culvert-01:upstream"
    assert segments[1].from_connection_point_ref == "connection:culvert-01:downstream"
    assert segments[1].to_connection_point_ref == "connection:outlet-01:pipe-in"
    assert segments[1].station_start == 55.0


def test_drainage_structures_flow_preset_resolves_structure_connection_chain() -> None:
    doc, project = _new_project_doc("V1DrainageStructuresFlowPresetChainTest")
    try:
        create_sample_v1_alignment(doc, project=project)
        structure_model = structure_preset_model_from_document(
            "Drainage Structures",
            document=doc,
            project=project,
        )
        drainage_model = drainage_preset_model_from_document(
            "Drainage Structures Flow",
            document=doc,
            project=project,
        )

        output = DrainageReviewMapper().map(
            drainage_model=drainage_model,
            structure_model=structure_model,
            project_id="proj-review",
        )
        result = build_drainage_pipeline_result(
            drainage_model,
            structure_model,
            project_id="proj-review",
        )
        candidates_by_route = {
            row.label: row
            for row in output.element_rows
            if row.kind == "pipeline_segment_candidate"
        }
        segments_by_route = {row.flow_route_ref: row for row in result.segment_rows}

        assert [row.flow_route_ref for row in result.segment_rows] == [
            "flow-route:flowId-04",
            "flow-route:flowId-05",
            "flow-route:flowId-06",
            "flow-route:flowId-07",
        ]
        assert "status=capture_only" in candidates_by_route["flow-route:flowId-01"].notes
        assert "status=capture_only" in candidates_by_route["flow-route:flowId-02"].notes
        assert "status=capture_only" in candidates_by_route["flow-route:flowId-03"].notes
        assert segments_by_route["flow-route:flowId-04"].from_connection_point_ref == "connection:inlet-01:pipe-out"
        assert segments_by_route["flow-route:flowId-04"].to_connection_point_ref == "connection:inlet-02:pipe-in"
        assert segments_by_route["flow-route:flowId-05"].from_connection_point_ref == "connection:inlet-02:pipe-out"
        assert segments_by_route["flow-route:flowId-05"].to_connection_point_ref == "connection:inlet-03:pipe-in"
        assert segments_by_route["flow-route:flowId-06"].from_connection_point_ref == "connection:inlet-03:pipe-out"
        assert segments_by_route["flow-route:flowId-06"].to_connection_point_ref == "connection:culvert-01:pipe-in"
        assert segments_by_route["flow-route:flowId-07"].from_connection_point_ref == "connection:culvert-01:pipe-out"
        assert segments_by_route["flow-route:flowId-07"].to_connection_point_ref == "connection:outlet-01:pipe-in"
        assert result.diagnostic_rows == []
    finally:
        App.closeDocument(doc.Name)


def test_drainage_pipeline_geometry_preserves_from_to_connection_point_direction() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:reverse-station",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:upper",
                element_kind="inlet_reference",
                structure_ref="structure:upper",
                connection_point_ref="connection:upper:pipe-out",
            ),
            DrainageElementRow(
                drainage_element_id="drainage:lower",
                element_kind="outfall_reference",
                structure_ref="structure:lower",
                connection_point_ref="connection:lower:pipe-in",
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:reverse",
                from_element_ref="drainage:upper",
                to_element_ref="drainage:lower",
                outlet_ref="drainage:lower",
            ),
        ],
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-review",
        structure_model_id="structures:reverse-station",
        structure_rows=[
            StructureRow("structure:upper", "utility", "reference", StructurePlacement("placement:upper", "alignment:main", 100.0, 102.0), native_type="inlet"),
            StructureRow("structure:lower", "utility", "reference", StructurePlacement("placement:lower", "alignment:main", 60.0, 62.0), native_type="outlet"),
        ],
        connection_point_rows=[
            StructureConnectionPoint("connection:upper:pipe-out", "structure:upper", "pipe_out", station=100.0, offset=-4.0, invert_elevation=20.0, diameter=1.0),
            StructureConnectionPoint("connection:lower:pipe-in", "structure:lower", "pipe_in", station=60.0, offset=5.0, invert_elevation=18.0, diameter=1.0),
        ],
    )

    output = DrainageReviewMapper().map(
        drainage_model=drainage_model,
        structure_model=structure_model,
        project_id="proj-review",
    )
    segment = output.pipeline_segment_rows[0]
    geometry = output.pipeline_geometry_rows[0]

    assert segment.station_start == 100.0
    assert segment.station_end == 60.0
    assert geometry.centerline_points[0] == (100.0, -4.0, 20.0)
    assert geometry.centerline_points[-1] == (60.0, 5.0, 18.0)
    assert geometry.centerline_points[0] != geometry.centerline_points[-1]


def test_show_drainage_pipeline_candidate_preview_object_creates_pipe_candidate() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineCandidatePreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())

        preview = show_drainage_pipeline_candidate_preview_object(doc, row_index=0)

        assert preview.Name == "V1DrainagePipelineCandidatePreview"
        assert preview.CRRecordKind == "v1_drainage_pipeline_candidate_preview"
        assert preview.V1ObjectType == "V1DrainagePipelineCandidatePreview"
        assert preview.FlowRouteRef == "flow-route:pipe-01"
        assert preview.CandidateStatus == "ready"
        assert preview.CoordinateMode == "station_offset_fallback"
        assert preview.FromConnectionPointRef == "connection:inlet-01:pipe-out"
        assert preview.ToConnectionPointRef == "connection:outlet-01:pipe-in"
        assert preview.Shape.BoundBox.XLength > 50.0
        assert preview.Shape.BoundBox.ZMin >= 43.55
        assert preview.Shape.BoundBox.ZLength >= 0.5
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_candidate_preview_marks_unresolved_issue() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineCandidateIssuePreviewTest")
    try:
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        structure_model = _pipeline_structure_model()
        structure_model.connection_point_rows = structure_model.connection_point_rows[:1]
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=structure_model)

        preview = show_drainage_pipeline_candidate_preview_object(doc, row_index=0)

        assert preview.CRRecordKind == "v1_drainage_pipeline_candidate_preview"
        assert preview.FlowRouteRef == "flow-route:pipe-01"
        assert preview.CandidateStatus == "missing_connection_point_ref"
        assert preview.IssueKind == "drainage_pipeline_candidate"
        assert preview.IssueStatus == "missing_connection_point_ref"
        assert preview.DisplayMode == "drainage_pipeline_issue"
        assert preview.FromElementRef == "drainage:inlet-01"
        assert preview.ToElementRef == "drainage:outlet-01"
        assert preview.Shape.BoundBox.XLength > 50.0
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_panel_flow_route_double_click_shows_candidate_issue_preview() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageFlowRouteIssuePreviewPanelTest")
    try:
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        structure_model = _pipeline_structure_model()
        structure_model.connection_point_rows = structure_model.connection_point_rows[:1]
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=structure_model)

        panel = V1DrainageReviewTaskPanel(document=doc)
        panel._show_flow_route_issue(0)

        preview = doc.getObject("V1DrainagePipelineCandidatePreview")
        assert preview is not None
        assert preview.FlowRouteRef == "flow-route:pipe-01"
        assert preview.IssueStatus == "missing_connection_point_ref"
        assert "Flow Route preview: flow-route:pipe-01" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_filters_pipeline_candidate_route_statuses() -> None:
    rows = [
        DrainageElementOutputRow("candidate:ready", "pipeline_segment_candidate", 0.0, 10.0, label="flow-route:ready", notes="status=ready"),
        DrainageElementOutputRow("candidate:capture", "pipeline_segment_candidate", 10.0, 20.0, label="flow-route:capture", notes="status=capture_only"),
        DrainageElementOutputRow(
            "candidate:unresolved",
            "pipeline_segment_candidate",
            20.0,
            30.0,
            label="flow-route:unresolved",
            notes="status=missing_connection_point_ref",
        ),
    ]

    assert [row.label for row in _filter_pipeline_candidate_rows(rows, mode="Pipe-producing")] == ["flow-route:ready"]
    assert [row.label for row in _filter_pipeline_candidate_rows(rows, mode="Capture-only")] == ["flow-route:capture"]
    assert [row.label for row in _filter_pipeline_candidate_rows(rows, mode="Unresolved")] == ["flow-route:unresolved"]


def test_drainage_review_filters_flow_route_source_rows_by_candidate_status() -> None:
    flow_rows = [
        DrainageElementOutputRow("route:ready", "flow_route", 0.0, 10.0, label="flow-route:ready"),
        DrainageElementOutputRow("route:capture", "flow_route", 10.0, 20.0, label="flow-route:capture"),
        DrainageElementOutputRow("route:unresolved", "flow_route", 20.0, 30.0, label="flow-route:unresolved"),
    ]
    candidate_rows = [
        DrainageElementOutputRow("candidate:ready", "pipeline_segment_candidate", 0.0, 10.0, label="flow-route:ready", notes="status=ready"),
        DrainageElementOutputRow("candidate:capture", "pipeline_segment_candidate", 10.0, 20.0, label="flow-route:capture", notes="status=capture_only"),
        DrainageElementOutputRow(
            "candidate:unresolved",
            "pipeline_segment_candidate",
            20.0,
            30.0,
            label="flow-route:unresolved",
            notes="status=missing_connection_point_ref",
        ),
    ]

    assert [row.label for row in _filter_flow_route_rows(flow_rows, candidate_rows, mode="Pipe-producing")] == ["flow-route:ready"]
    assert [row.label for row in _filter_flow_route_rows(flow_rows, candidate_rows, mode="Capture-only")] == ["flow-route:capture"]
    assert [row.label for row in _filter_flow_route_rows(flow_rows, candidate_rows, mode="Unresolved")] == ["flow-route:unresolved"]


def test_drainage_review_filters_region_assignment_issues() -> None:
    rows = [
        DrainageElementOutputRow("region:ok", "region_assignment", 0.0, 10.0, label="region:1", source_ref="drainage:ditch-01", notes="status=ok"),
        DrainageElementOutputRow(
            "region:missing",
            "region_assignment",
            10.0,
            20.0,
            label="",
            source_ref="drainage:ditch-02",
            notes="status=missing_region",
        ),
    ]

    filtered = _filter_region_assignment_rows(rows, issues_only=True)

    assert [row.source_ref for row in filtered] == ["drainage:ditch-02"]


def test_drainage_review_mapper_reports_outlet_chain_issue_rows() -> None:
    drainage_model = DrainageModel(
        schema_version=1,
        project_id="proj-review",
        drainage_model_id="drainage:outlet-chain-issue",
        element_rows=[
            DrainageElementRow(
                drainage_element_id="drainage:inlet-01",
                element_kind="inlet_reference",
                station_start=30.0,
                station_end=32.0,
            ),
            DrainageElementRow(
                drainage_element_id="drainage:junction-01",
                element_kind="junction_reference",
                station_start=60.0,
                station_end=61.0,
            ),
        ],
        flow_route_rows=[
            DrainageFlowRoute(
                flow_route_id="flow-route:no-outlet",
                from_element_ref="drainage:inlet-01",
                to_element_ref="drainage:junction-01",
            )
        ],
    )

    output = DrainageReviewMapper().map(drainage_model=drainage_model, project_id="proj-review")
    issue_rows = [row for row in output.element_rows if row.kind == "flow_route_issue"]

    assert len(issue_rows) == 1
    assert issue_rows[0].label == "flow_route_no_reachable_outlet"
    assert issue_rows[0].source_ref == "flow-route:no-outlet"
    assert "from_element_ref=drainage:inlet-01" in issue_rows[0].notes
    assert any(row.summary_id == "summary:flow-route-issues" and row.value == 1 for row in output.summary_rows)


def test_show_drainage_flow_route_issue_preview_object_creates_issue_marker() -> None:
    doc, project = _new_project_doc("V1DrainageFlowRouteIssuePreviewTest")
    try:
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-review",
                drainage_model_id="drainage:outlet-chain-issue",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:inlet-01",
                        element_kind="inlet_reference",
                        station_start=30.0,
                        station_end=32.0,
                    ),
                    DrainageElementRow(
                        drainage_element_id="drainage:junction-01",
                        element_kind="junction_reference",
                        station_start=60.0,
                        station_end=61.0,
                    ),
                ],
                flow_route_rows=[
                    DrainageFlowRoute(
                        flow_route_id="flow-route:no-outlet",
                        from_element_ref="drainage:inlet-01",
                        to_element_ref="drainage:junction-01",
                    )
                ],
            ),
        )

        preview = show_drainage_flow_route_issue_preview_object(doc, row_index=0)

        assert preview.CRRecordKind == "v1_drainage_flow_route_issue_preview"
        assert preview.V1ObjectType == "V1DrainageFlowRouteIssuePreview"
        assert preview.IssueKind == "flow_route_no_reachable_outlet"
        assert preview.IssueStatus == "warning"
        assert preview.DisplayMode == "drainage_flow_route_issue"
        assert preview.FlowRouteRefs == "flow-route:no-outlet"
        assert preview.FromElementRef == "drainage:inlet-01"
        assert preview.Shape.BoundBox.XLength > 20.0
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_segment_preview_object_creates_pipe_segment() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineSegmentPreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())

        preview = show_drainage_pipeline_segment_preview_object(doc, row_index=0)

        assert preview.Name == "V1DrainagePipelineSegmentPreview"
        assert preview.CRRecordKind == "v1_drainage_pipeline_segment_preview"
        assert preview.V1ObjectType == "V1DrainagePipelineSegmentPreview"
        assert preview.PipelineSegmentId == "pipeline-segment:flow-route-pipe-01"
        assert preview.FlowRouteRef == "flow-route:pipe-01"
        assert preview.CoordinateMode == "station_offset_fallback"
        assert preview.FromConnectionPointRef == "connection:inlet-01:pipe-out"
        assert preview.ToConnectionPointRef == "connection:outlet-01:pipe-in"
        assert preview.Shape.BoundBox.XLength > 50.0
        assert preview.Shape.BoundBox.ZMin >= 43.55
        assert preview.Shape.BoundBox.ZLength >= 0.5
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_segment_preview_uses_alignment_station_offset_frame() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineSegmentAlignmentPreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        create_sample_v1_alignment(doc, project=project)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())

        preview = show_drainage_pipeline_segment_preview_object(doc, row_index=0)

        assert preview.CoordinateMode == "alignment_station_offset"
        assert preview.Shape.BoundBox.XMin < 35.0
        assert preview.Shape.BoundBox.XMax < 100.0
        assert preview.Shape.BoundBox.YLength > 10.0
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_segment_preview_prefers_centerline3d_result_frame() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineSegmentCenterline3DPreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())

        preview = show_drainage_pipeline_segment_preview_object(doc, row_index=0)

        assert preview.CoordinateMode == "centerline3d_result"
        assert preview.Shape.BoundBox.ZMin > 40.0
        assert preview.Shape.BoundBox.YLength > 10.0
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_output_prefers_centerline3d_result_for_pipeline_geometry() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineGeometryCenterline3DOutputTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_structure_model())

        output = build_drainage_review_output(doc)
        geometry = output.pipeline_geometry_rows[0]

        assert geometry.coordinate_mode == "centerline3d_result"
        assert len(geometry.centerline_points) == 2
        assert geometry.centerline_points[0][2] == 44.2
        assert geometry.centerline_points[-1][2] == 43.6
    finally:
        App.closeDocument(doc.Name)


def test_drainage_pipeline_geometry_uses_centerline_height_when_invert_is_missing() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineGeometryCenterlineHeightFallbackTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        drainage_model = _pipeline_drainage_model()
        structure_model = _pipeline_structure_model()
        structure_model.connection_point_rows = [
            StructureConnectionPoint(
                connection_point_id=row.connection_point_id,
                structure_ref=row.structure_ref,
                point_role=row.point_role,
                station=row.station,
                offset=row.offset,
                diameter=row.diameter,
                shape_kind=row.shape_kind,
            )
            for row in structure_model.connection_point_rows
        ]
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=drainage_model)
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=structure_model)

        output = build_drainage_review_output(doc)
        geometry = output.pipeline_geometry_rows[0]

        assert geometry.coordinate_mode == "centerline3d_result"
        assert geometry.centerline_points[0][2] > 10.0
        assert geometry.centerline_points[-1][2] > geometry.centerline_points[0][2]
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_network_preview_object_creates_network_compound() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineNetworkPreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_network_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_network_structure_model())

        preview = show_drainage_pipeline_network_preview_object(doc, row_index=0)

        assert preview.Name == "V1DrainagePipelineNetworkPreview"
        assert preview.CRRecordKind == "v1_drainage_pipeline_network_preview"
        assert preview.V1ObjectType == "V1DrainagePipelineNetworkPreview"
        assert preview.NetworkId == "drainage-pipeline-network:main"
        assert preview.FlowRouteRefs == "flow-route:pipe-01,flow-route:pipe-02"
        assert preview.PipelineSegmentRefs == "pipeline-segment:flow-route-pipe-01,pipeline-segment:flow-route-pipe-02"
        assert preview.CoordinateMode == "station_offset_fallback"
        assert preview.FuseMode == "compound_first_slice"
        assert preview.Shape.BoundBox.XLength > 50.0
        assert preview.Shape.BoundBox.ZLength >= 0.5
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_networks_preview_object_creates_full_network_compound() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineNetworksPreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_network_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_network_structure_model())

        preview = show_drainage_pipeline_networks_preview_object(doc)

        assert preview.Name == "V1DrainagePipelineNetworksPreview"
        assert preview.CRRecordKind == "v1_drainage_pipeline_networks_preview"
        assert preview.V1ObjectType == "V1DrainagePipelineNetworksPreview"
        assert preview.NetworkIds == "drainage-pipeline-network:main"
        assert preview.FlowRouteRefs == "flow-route:pipe-01,flow-route:pipe-02"
        assert preview.PipelineSegmentRefs == "pipeline-segment:flow-route-pipe-01,pipeline-segment:flow-route-pipe-02"
        assert preview.ConnectionPointRefs == "connection:inlet-01:pipe-out,connection:junction-01:pipe,connection:outlet-01:pipe-in"
        assert preview.NetworkCount == "1"
        assert preview.Shape.BoundBox.XLength > 50.0
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
        segment_preview = doc.getObject("V1DrainagePipelineSegment_pipeline_segment_flow_route_pipe_01")
        assert segment_preview is not None
        assert segment_preview.CRRecordKind == "v1_drainage_pipeline_segment_output_preview"
        assert segment_preview.PipelineSegmentId == "pipeline-segment:flow-route-pipe-01"
        assert segment_preview.FlowRouteRef == "flow-route:pipe-01"
        assert segment_preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
        assert segment_preview.Name in preview.LinkedPreviewObjects
        point_preview = doc.getObject("V1StructurePipeConnectionPoint_connection_inlet_01_pipe_out")
        assert point_preview is not None
        assert point_preview.CRRecordKind == "v1_structure_pipe_connection_point_preview"
        assert point_preview.V1ObjectType == "V1StructurePipeConnectionPointPreview"
        assert point_preview.ConnectionPointRef == "connection:inlet-01:pipe-out"
        assert point_preview.PointRole == "pipe_out"
        assert point_preview.Name in _group_names(tree[V1_TREE_STRUCTURES])
        assert point_preview.Name in preview.LinkedPreviewObjects
        structure_preview = doc.getObject("V1StructurePreview_structure_inlet_01")
        assert structure_preview is not None
        assert structure_preview.Name in _group_names(tree[V1_TREE_STRUCTURES])
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_networks_preview_prefers_centerline3d_result_frame() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineNetworksCenterline3DPreviewTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_pipeline_network_drainage_model())
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=_pipeline_network_structure_model())

        preview = show_drainage_pipeline_networks_preview_object(doc)

        assert preview.CoordinateMode == "centerline3d_result"
        assert preview.Shape.BoundBox.ZMin > 40.0
        assert preview.Name in _group_names(tree[V1_TREE_DRAINAGE])
        segment_preview = doc.getObject("V1DrainagePipelineSegment_pipeline_segment_flow_route_pipe_01")
        assert segment_preview is not None
        assert segment_preview.CoordinateMode == "centerline3d_result"
        assert segment_preview.Shape.BoundBox.ZMin > 40.0
    finally:
        App.closeDocument(doc.Name)


def test_show_drainage_pipeline_networks_preview_uses_centerline3d_height_for_presets() -> None:
    doc, project = _new_project_doc("V1DrainagePresetPipelineNetworksCenterline3DPreviewTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        drainage_model = drainage_preset_model_from_document("Drainage Structures Flow", doc, project=project)
        structure_model = structure_preset_model_from_document("Drainage Structures", doc, project=project, alignment=alignment)
        assert all(row.invert_elevation is None for row in structure_model.connection_point_rows)
        structure_model.connection_point_rows = [
            replace(row, invert_elevation=0.0, notes="")
            for row in structure_model.connection_point_rows
        ]
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=drainage_model)
        create_or_update_v1_structure_model_object(doc, project=project, structure_model=structure_model)

        preview = show_drainage_pipeline_networks_preview_object(doc)

        assert preview.CoordinateMode == "centerline3d_result"
        assert preview.Shape.BoundBox.ZMin > 5.0
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_mapper_builds_alignment_based_pipeline_geometry_rows() -> None:
    doc, project = _new_project_doc("V1DrainagePipelineGeometryOutputTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        output = DrainageReviewMapper().map(
            drainage_model=_pipeline_drainage_model(),
            alignment_model=to_alignment_model(alignment),
            structure_model=_pipeline_structure_model(),
            project_id="proj-review",
        )

        geometry = output.pipeline_geometry_rows[0]

        assert geometry.coordinate_mode == "alignment_station_offset"
        assert geometry.geometry_kind == "centerline_polyline"
        assert output.alignment_id == alignment.AlignmentId
        assert alignment.AlignmentId in output.source_refs
        assert len(geometry.centerline_points) == 2
        assert geometry.centerline_points[-1][0] < 100.0
        assert geometry.centerline_points[-1][1] > 0.0
        assert "point_count=2" in geometry.notes
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_mapper_reports_drainage_quantity_summary() -> None:
    quantity_model = QuantityModel(
        schema_version=1,
        project_id="proj-review",
        quantity_model_id="quantity:drainage",
        corridor_id="corridor:main",
        fragment_rows=[
            QuantityFragment(
                fragment_id="quantity:ditch",
                quantity_kind="drainage_ditch_length",
                measurement_kind="drainage_applied_section_longitudinal",
                value=20.0,
                unit="m",
                station_start=0.0,
                station_end=20.0,
                subassembly_ref="ditch:right",
                drainage_ref="drainage:side-ditch-right",
            ),
            QuantityFragment(
                fragment_id="quantity:flowline",
                quantity_kind="drainage_flowline_length",
                measurement_kind="drainage_applied_section_flowline",
                value=19.5,
                unit="m",
                station_start=0.0,
                station_end=20.0,
                subassembly_ref="ditch:right",
                drainage_ref="drainage:side-ditch-right",
                flow_route_ref="flow-route:right",
            ),
        ],
    )

    output = DrainageReviewMapper().map(
        drainage_model=_drainage_model(),
        region_model=_region_model(),
        applied_section_set=_applied_set(),
        quantity_model=quantity_model,
    )

    summary = {row.summary_id: row.value for row in output.summary_rows}
    quantity_rows = [row for row in output.element_rows if row.kind == "drainage_quantity"]
    assert summary["summary:drainage-ditch-length"] == 20.0
    assert summary["summary:drainage-flowline-length"] == 19.5
    assert summary["summary:report-quantity-flow-route-groups"] == 1
    assert len(quantity_rows) == 2
    assert quantity_rows[0].source_ref == "drainage:side-ditch-right"
    report_rows = [row for row in output.element_rows if row.kind == "drainage_report"]
    assert any(
        row.label == "quantity_by_flow_route"
        and row.source_ref == "flow-route:right"
        and "quantity_kind=drainage_flowline_length" in row.notes
        and "value=19.5" in row.notes
        for row in report_rows
    )
    assert "quantity:drainage" in output.source_refs


def test_drainage_review_auto_loads_persisted_quantity_model() -> None:
    doc, project = _new_project_doc("V1DrainageReviewQuantityAutoLoadTest")
    try:
        tree = ensure_project_tree(project, include_references=False)
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_drainage_model())
        create_or_update_v1_region_model_object(doc, project=project, region_model=_region_model())
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_applied_set())
        quantity_model = QuantityModel(
            schema_version=1,
            project_id="proj-review",
            quantity_model_id="quantity:drainage",
            fragment_rows=[
                QuantityFragment(
                    fragment_id="quantity:ditch",
                    quantity_kind="drainage_ditch_length",
                    measurement_kind="plan_length",
                    value=20.0,
                    unit="m",
                    drainage_ref="drainage:side-ditch-right",
                )
            ],
            source_refs=["applied:main"],
        )
        quantity_obj = create_or_update_v1_quantity_model_object(doc, project=project, quantity_model=quantity_model)

        loaded = to_quantity_model(find_v1_quantity_model(doc))
        output = build_drainage_review_output(doc)
        summary = {row.summary_id: row.value for row in output.summary_rows}

        assert loaded is not None
        assert loaded.quantity_model_id == "quantity:drainage"
        assert quantity_obj.Name in _group_names(tree[V1_TREE_QUANTITIES])
        assert summary["summary:drainage-ditch-length"] == 20.0
        assert "quantity:drainage" in output.source_refs
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_panel_loads_document_context() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("V1DrainageReviewPanelTest")
    try:
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_drainage_model())
        create_or_update_v1_region_model_object(doc, project=project, region_model=_region_model())
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_applied_set())

        panel = V1DrainageReviewTaskPanel(document=doc)

        assert panel._summary_table.rowCount() == 28
        assert panel._element_table.rowCount() == 2
        assert panel._flow_route_table.rowCount() == 1
        assert panel._tabs.tabText(1) == "Flow Routes"
        assert panel._flow_route_table.item(0, 0).text() == "flow-route:right"
        assert panel._flow_route_table.item(0, 5).text() == "drainage:side-ditch-right -> drainage:outfall-right"
        assert panel._tabs.tabText(2) == "Flow Route Issues"
        assert panel._flow_route_issue_table.rowCount() == 0
        assert panel._tabs.tabText(3) == "Pipeline Candidates"
        assert panel._pipeline_table.rowCount() == 0
        assert panel._tabs.tabText(4) == "Pipeline Segments"
        assert panel._pipeline_segment_table.rowCount() == 0
        assert panel._tabs.tabText(5) == "Pipeline Networks"
        assert panel._pipeline_network_table.rowCount() == 0
        assert panel._tabs.tabText(6) == "Pipeline Junctions"
        assert panel._pipeline_junction_table.rowCount() == 0
        assert panel._tabs.tabText(7) == "Region Assignments"
        assert panel._region_table.rowCount() == 2
        assert panel._applied_table.rowCount() == 1
        assert panel._flowline_table.rowCount() == 0
        assert panel._report_table.rowCount() == 3
        panel._report_warnings_only.setChecked(True)
        assert panel._report_table.rowCount() == 0
        panel._report_warnings_only.setChecked(False)
        assert panel._report_table.rowCount() == 3
        assert "Region drainage ref" not in panel._status.toPlainText()
        assert "Flow Routes: 1 source route" in panel._status.toPlainText()
        assert [label for _target, label in _drainage_review_navigation_targets()] == [
            "Drainage",
            "Regions",
            "Assembly",
            "Structures",
            "Cross Sections",
        ]
        button_labels = {button.text() for button in panel.form.findChildren(QtWidgets.QPushButton)}
        assert {"Drainage", "Regions", "Assembly", "Structures", "Cross Sections"}.issubset(button_labels)
    finally:
        App.closeDocument(doc.Name)


def test_run_v1_drainage_review_command_returns_panel() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc("V1DrainageReviewRunCommandTest")
    try:
        panel = run_v1_drainage_review_command(document=doc)

        assert isinstance(panel, V1DrainageReviewTaskPanel)
        assert panel.document == doc
    finally:
        App.closeDocument(doc.Name)


def test_build_drainage_review_output_reads_document_objects() -> None:
    doc, project = _new_project_doc("V1DrainageReviewOutputTest")
    try:
        create_or_update_v1_drainage_model_object(doc, project=project, drainage_model=_drainage_model())
        create_or_update_v1_region_model_object(doc, project=project, region_model=_region_model())
        create_or_update_v1_applied_section_set_object(doc, project=project, applied_section_set=_applied_set())

        output = build_drainage_review_output(doc)

        assert output.drainage_model_id == "drainage:main"
        assert len(output.element_rows) == 9
    finally:
        App.closeDocument(doc.Name)


def test_drainage_review_resources_and_toolbar_order() -> None:
    resources = CmdV1DrainageReview().GetResources()
    commands = corridorroad_workflow_toolbar_commands()

    assert resources["MenuText"] == "Drainage Review"
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("drainage_review.svg")
    assert commands.index("CorridorRoad_V1EditRegions") < commands.index("CorridorRoad_V1EditStructures")
    assert commands.index("CorridorRoad_V1EditStructures") < commands.index("CorridorRoad_V1EditDrainage")
    assert commands.index("CorridorRoad_V1EditDrainage") < commands.index("CorridorRoad_V1DrainageReview")
    assert commands.index("CorridorRoad_V1DrainageReview") < commands.index("CorridorRoad_V1AppliedSections")


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}
