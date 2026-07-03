from pathlib import Path
import tempfile

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    build_intersection_model_from_sources,
    create_starter_intersection_sources,
    intersection_ref_for_kind,
    list_intersection_control_region_choices,
    list_v1_alignment_choices,
)
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionEdgePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLaneConnectionRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    create_or_update_v1_intersection_model_object,
    to_intersection_model,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import IntersectionEvaluationService


def _new_project_doc():
    doc = App.newDocument("V1IntersectionSourceObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def test_intersection_source_object_round_trips_phase2_policy_rows() -> None:
    doc, project = _new_project_doc()
    try:
        model = IntersectionModel(
            schema_version=1,
            project_id="project:demo",
            intersection_model_id="intersections:main",
            result_refs=[
                "intersection-topology:intersection:t-01",
                "intersection-surface-zones:intersection:t-01",
            ],
            anchor_rows=[
                IntersectionAnchorRow(
                    anchor_id="anchor:intersection:t-01:main",
                    intersection_id="intersection:t-01",
                    source_method="manual",
                    approval_status="locked",
                    primary_alignment_ref="alignment:main",
                    primary_station=100.0,
                    secondary_station_refs={"alignment:side": 40.0},
                    point_x=12.0,
                    point_y=34.0,
                    point_z=1.5,
                    tolerance=0.05,
                    diagnostic_rows=["anchor_locked_by_user"],
                    notes="QA locked anchor.",
                )
            ],
            intersection_rows=[
                IntersectionRow(
                    intersection_id="intersection:t-01",
                    intersection_kind="t_intersection",
                    primary_alignment_ref="alignment:main",
                    secondary_alignment_refs=["alignment:side"],
                    leg_rows=[
                        IntersectionLegRow(
                            leg_id="intersection:t-01:leg-01",
                            leg_role="primary_before",
                            alignment_ref="alignment:main",
                            intersection_id="intersection:t-01",
                            source_method="manual",
                            approval_status="locked",
                            span_source="explicit",
                            arm_policy_ref="arm-policy:intersection:t-01:leg-01",
                            edge_policy_refs=[
                                "edge-policy:intersection:t-01:leg-01:pavement",
                                "edge-policy:intersection:t-01:leg-01:daylight",
                            ],
                            grading_policy_ref="grading:intersection:t-01:default",
                            diagnostic_rows=["leg_locked_by_user"],
                        )
                    ],
                    policy_refs=[
                        "arm-policy:intersection:t-01:leg-01",
                        "edge-policy:intersection:t-01:leg-01:pavement",
                        "grading:intersection:t-01:default",
                        "drainage-policy:intersection:t-01:default",
                    ],
                )
            ],
            control_area_rows=[
                IntersectionControlArea(
                    control_area_id="intersection:t-01:control-area:01",
                    intersection_id="intersection:t-01",
                    alignment_ref="alignment:main",
                    station_ranges=[(90.0, 120.0)],
                    source_method="region_derived",
                    approval_status="draft",
                    intent_status="region_derived",
                    source_region_refs=["regions:main/region:main-intersection"],
                    diagnostic_rows=["control_area_region_derived"],
                )
            ],
            corner_rows=[
                IntersectionCornerRow(
                    corner_id="corner:intersection:t-01:left",
                    intersection_id="intersection:t-01",
                    control_area_ref="intersection:t-01:control-area:01",
                    from_leg_ref="intersection:t-01:leg-01",
                    to_leg_ref="intersection:t-01:leg-02",
                    side="left",
                    quadrant="left",
                    curb_return_policy_ref="curb-return:intersection:t-01:default",
                    source_method="manual",
                    approval_status="locked",
                    diagnostic_rows=["corner_locked_by_user"],
                )
            ],
            arm_policy_rows=[
                IntersectionArmPolicyRow(
                    policy_id="arm-policy:intersection:t-01:leg-01",
                    intersection_id="intersection:t-01",
                    leg_ref="intersection:t-01:leg-01",
                    lane_width=3.6,
                )
            ],
            curb_return_policy_rows=[
                IntersectionCurbReturnPolicyRow(
                    policy_id="curb-return:intersection:t-01:default",
                    intersection_id="intersection:t-01",
                    radius=12.0,
                    long_edge_factor=3.0,
                    max_boundary_edge_length=2.0,
                    corner_refs=["corner:intersection:t-01:left"],
                )
            ],
            edge_policy_rows=[
                IntersectionEdgePolicyRow(
                    policy_id="edge-policy:intersection:t-01:leg-01:pavement",
                    intersection_id="intersection:t-01",
                    leg_ref="intersection:t-01:leg-01",
                    edge_role="pavement_edge",
                    offset_rule="lane_width_from_arm_policy",
                    edge_family_intent="lane",
                    source_method="subassembly_derived",
                    approval_status="locked",
                    assembly_ref="assembly:basic-road",
                    template_ref="template:basic-road",
                    subassembly_ref="subassembly:lane",
                    subassembly_kind="lane",
                    diagnostic_rows=["edge_family_locked_by_user"],
                )
            ],
            lane_connection_rows=[
                IntersectionLaneConnectionRow(
                    connection_id="lane-connection:intersection:t-01:turn-01",
                    intersection_id="intersection:t-01",
                    movement_type="turn",
                    from_leg_ref="intersection:t-01:leg-01",
                    to_leg_ref="intersection:t-01:leg-02",
                    from_edge_policy_ref="edge-policy:intersection:t-01:leg-01:pavement",
                    to_edge_policy_ref="edge-policy:intersection:t-01:leg-02:pavement",
                    source_method="manual",
                    approval_status="locked",
                    diagnostic_rows=["lane_connection_locked_by_user"],
                )
            ],
            grading_policy_rows=[
                IntersectionGradingPolicyRow(
                    policy_id="grading:intersection:t-01:default",
                    intersection_id="intersection:t-01",
                    mode="flatten_intersection",
                    primary_alignment_ref="alignment:main",
                    controlling_profile_ref="profile:main",
                    crown_behavior="flatten",
                    tie_in_rule="blend_to_leg_profiles",
                    crossfall_transition="linear",
                    low_point_strategy="review_low_points",
                    source_method="manual",
                    approval_status="locked",
                    diagnostic_rows=["grading_locked_by_user"],
                )
            ],
            drainage_policy_rows=[
                IntersectionDrainagePolicyRow(
                    policy_id="drainage-policy:intersection:t-01:default",
                    intersection_id="intersection:t-01",
                    gutter_edge_refs=["edge-policy:intersection:t-01:leg-01:pavement"],
                    drainage_element_refs=["drainage:inlet-01"],
                    flow_route_refs=["flow-route:intersection:t-01"],
                    inlet_candidate_refs=["inlet-candidate:t-01:01"],
                    low_point_refs=["low-point:t-01:central"],
                    intent_status="accepted",
                    source_method="manual",
                    approval_status="locked",
                    diagnostic_rows=["drainage_locked_by_user"],
                )
            ],
        )

        obj = create_or_update_v1_intersection_model_object(doc, intersection_model=model, project=project)
        restored = to_intersection_model(obj)

        assert obj.AnchorCount == 1
        assert obj.CornerCount == 1
        assert obj.ArmPolicyCount == 1
        assert obj.EdgePolicyCount == 1
        assert obj.LaneConnectionCount == 1
        assert obj.DrainagePolicyCount == 1
        assert restored is not None
        assert restored.result_refs == [
            "intersection-topology:intersection:t-01",
            "intersection-surface-zones:intersection:t-01",
        ]
        assert restored.anchor_rows[0].anchor_id == "anchor:intersection:t-01:main"
        assert restored.anchor_rows[0].approval_status == "locked"
        assert restored.anchor_rows[0].secondary_station_refs == {"alignment:side": 40.0}
        assert restored.anchor_rows[0].diagnostic_rows == ["anchor_locked_by_user"]
        assert restored.intersection_rows[0].leg_rows[0].arm_policy_ref == "arm-policy:intersection:t-01:leg-01"
        assert restored.intersection_rows[0].leg_rows[0].approval_status == "locked"
        assert restored.intersection_rows[0].leg_rows[0].span_source == "explicit"
        assert restored.intersection_rows[0].leg_rows[0].diagnostic_rows == ["leg_locked_by_user"]
        assert restored.intersection_rows[0].leg_rows[0].edge_policy_refs == [
            "edge-policy:intersection:t-01:leg-01:pavement",
            "edge-policy:intersection:t-01:leg-01:daylight",
        ]
        assert restored.control_area_rows[0].source_method == "region_derived"
        assert restored.control_area_rows[0].approval_status == "draft"
        assert restored.control_area_rows[0].intent_status == "region_derived"
        assert restored.control_area_rows[0].source_region_refs == ["regions:main/region:main-intersection"]
        assert restored.control_area_rows[0].diagnostic_rows == ["control_area_region_derived"]
        assert restored.corner_rows[0].corner_id == "corner:intersection:t-01:left"
        assert restored.corner_rows[0].approval_status == "locked"
        assert restored.corner_rows[0].curb_return_policy_ref == "curb-return:intersection:t-01:default"
        assert restored.corner_rows[0].diagnostic_rows == ["corner_locked_by_user"]
        assert restored.arm_policy_rows[0].lane_width == 3.6
        assert restored.curb_return_policy_rows[0].long_edge_factor == 3.0
        assert restored.curb_return_policy_rows[0].max_boundary_edge_length == 2.0
        assert restored.curb_return_policy_rows[0].corner_refs == ["corner:intersection:t-01:left"]
        assert restored.edge_policy_rows[0].offset_rule == "lane_width_from_arm_policy"
        assert restored.edge_policy_rows[0].edge_family_intent == "lane"
        assert restored.edge_policy_rows[0].approval_status == "locked"
        assert restored.edge_policy_rows[0].assembly_ref == "assembly:basic-road"
        assert restored.edge_policy_rows[0].subassembly_kind == "lane"
        assert restored.edge_policy_rows[0].diagnostic_rows == ["edge_family_locked_by_user"]
        assert restored.lane_connection_rows[0].movement_type == "turn"
        assert restored.lane_connection_rows[0].approval_status == "locked"
        assert restored.lane_connection_rows[0].diagnostic_rows == ["lane_connection_locked_by_user"]
        assert restored.grading_policy_rows[0].controlling_profile_ref == "profile:main"
        assert restored.grading_policy_rows[0].crown_behavior == "flatten"
        assert restored.grading_policy_rows[0].tie_in_rule == "blend_to_leg_profiles"
        assert restored.grading_policy_rows[0].approval_status == "locked"
        assert restored.grading_policy_rows[0].diagnostic_rows == ["grading_locked_by_user"]
        assert restored.drainage_policy_rows[0].gutter_edge_refs == [
            "edge-policy:intersection:t-01:leg-01:pavement"
        ]
        assert restored.drainage_policy_rows[0].drainage_element_refs == ["drainage:inlet-01"]
        assert restored.drainage_policy_rows[0].flow_route_refs == ["flow-route:intersection:t-01"]
        assert restored.drainage_policy_rows[0].inlet_candidate_refs == ["inlet-candidate:t-01:01"]
        assert restored.drainage_policy_rows[0].low_point_refs == ["low-point:t-01:central"]
        assert restored.drainage_policy_rows[0].intent_status == "accepted"
        assert restored.drainage_policy_rows[0].approval_status == "locked"
        assert restored.drainage_policy_rows[0].diagnostic_rows == ["drainage_locked_by_user"]
    finally:
        App.closeDocument(doc.Name)


def test_intersection_source_object_reopened_document_restores_source_intent_rows() -> None:
    doc, project = _new_project_doc()
    try:
        model = IntersectionModel(
            schema_version=1,
            project_id="project:reload",
            intersection_model_id="intersections:reload",
            source_refs=["intersection-preset:reload:source-completeness"],
            result_refs=[
                "intersection-topology:intersection:reload",
                "intersection-drainage-hints:intersection:reload",
            ],
            anchor_rows=[
                IntersectionAnchorRow(
                    anchor_id="anchor:intersection:reload:main",
                    intersection_id="intersection:reload",
                    source_method="manual",
                    approval_status="locked",
                    primary_alignment_ref="alignment:main",
                    primary_station=120.0,
                    secondary_station_refs={"alignment:side": 60.0},
                    tolerance=0.025,
                    diagnostic_rows=["anchor_reload_locked"],
                )
            ],
            intersection_rows=[
                IntersectionRow(
                    intersection_id="intersection:reload",
                    intersection_kind="drainage_sag_intersection",
                    primary_alignment_ref="alignment:main",
                    secondary_alignment_refs=["alignment:side"],
                    control_region_refs=["regions:main/region:intersection"],
                    leg_rows=[
                        IntersectionLegRow(
                            leg_id="intersection:reload:leg:01",
                            intersection_id="intersection:reload",
                            leg_role="primary_before",
                            alignment_ref="alignment:main",
                            profile_ref="profile:main",
                            region_ref="regions:main/region:intersection",
                            source_method="region_derived",
                            approval_status="draft",
                            span_source="control_region",
                            edge_policy_refs=["edge-policy:intersection:reload:leg:01:gutter"],
                            grading_policy_ref="grading:intersection:reload:sag",
                            diagnostic_rows=["leg_reload_review"],
                        )
                    ],
                    policy_refs=[
                        "edge-policy:intersection:reload:leg:01:gutter",
                        "lane-connection:intersection:reload:01",
                        "grading:intersection:reload:sag",
                        "drainage-policy:intersection:reload:sag",
                    ],
                )
            ],
            corner_rows=[
                IntersectionCornerRow(
                    corner_id="corner:intersection:reload:sag-01",
                    intersection_id="intersection:reload",
                    from_leg_ref="intersection:reload:leg:01",
                    to_leg_ref="intersection:reload:leg:02",
                    side="sag_quadrant_01",
                    quadrant="sag_quadrant_01",
                    curb_return_policy_ref="curb-return:intersection:reload:default",
                    source_method="preset_default",
                    approval_status="draft",
                    diagnostic_rows=["corner_reload_review"],
                )
            ],
            edge_policy_rows=[
                IntersectionEdgePolicyRow(
                    policy_id="edge-policy:intersection:reload:leg:01:gutter",
                    intersection_id="intersection:reload",
                    leg_ref="intersection:reload:leg:01",
                    edge_role="gutter_edge",
                    side="right",
                    offset_rule="urban_curb_gutter_offset",
                    offset_value=4.2,
                    elevation_rule="from_grading_policy",
                    profile_ref="profile:main",
                    source_policy_ref="arm-policy:intersection:reload:leg:01",
                    edge_family_intent="gutter",
                    source_method="urban_preset_default",
                    approval_status="draft",
                    assembly_ref="assembly:urban",
                    template_ref="template:urban",
                    subassembly_ref="subassembly:gutter",
                    subassembly_kind="gutter",
                    diagnostic_rows=["edge_reload_review"],
                )
            ],
            lane_connection_rows=[
                IntersectionLaneConnectionRow(
                    connection_id="lane-connection:intersection:reload:01",
                    intersection_id="intersection:reload",
                    movement_type="through",
                    from_leg_ref="intersection:reload:leg:01",
                    to_leg_ref="intersection:reload:leg:02",
                    from_edge_policy_ref="edge-policy:intersection:reload:leg:01:gutter",
                    to_edge_policy_ref="edge-policy:intersection:reload:leg:02:gutter",
                    from_lane_index=1,
                    to_lane_index=2,
                    source_method="preset_default",
                    approval_status="draft",
                    diagnostic_rows=["lane_reload_review"],
                )
            ],
            grading_policy_rows=[
                IntersectionGradingPolicyRow(
                    policy_id="grading:intersection:reload:sag",
                    intersection_id="intersection:reload",
                    mode="blend_primary_side",
                    primary_alignment_ref="alignment:main",
                    secondary_alignment_refs=["alignment:side"],
                    controlling_profile_ref="profile:main",
                    crown_behavior="blend_primary_side_crowns",
                    tie_in_rule="blend_to_leg_profiles",
                    crossfall_transition="linear",
                    low_point_strategy="sag_low_point_review",
                    source_method="preset_default",
                    approval_status="draft",
                    diagnostic_rows=["grading_reload_review"],
                )
            ],
            drainage_policy_rows=[
                IntersectionDrainagePolicyRow(
                    policy_id="drainage-policy:intersection:reload:sag",
                    intersection_id="intersection:reload",
                    capture_mode="sag_low_point_inlets",
                    inlet_spacing=35.0,
                    low_point_tolerance=0.025,
                    gutter_edge_refs=["edge-policy:intersection:reload:leg:01:gutter"],
                    drainage_element_refs=["drainage:sag-inlet-candidate:01"],
                    flow_route_refs=["flow-route:sag-intersection:reload:outlet-review"],
                    inlet_candidate_refs=["drainage:sag-inlet-candidate:01"],
                    low_point_refs=["drainage:sag-low-point:01"],
                    intent_status="hint_only",
                    source_method="preset_default",
                    approval_status="draft",
                    diagnostic_rows=["drainage_reload_review"],
                )
            ],
        )

        obj = create_or_update_v1_intersection_model_object(doc, intersection_model=model, project=project)
        doc.recompute()

        with tempfile.TemporaryDirectory(prefix="cr_v1_intersection_reload_") as temp_dir:
            path = Path(temp_dir) / "intersection_source_reload.FCStd"
            doc_name = doc.Name
            obj_name = obj.Name
            doc.saveAs(str(path))
            App.closeDocument(doc_name)
            doc = None

            reopened = App.openDocument(str(path))
            try:
                restored = to_intersection_model(reopened.getObject(obj_name))

                assert restored is not None
                assert restored.source_refs == ["intersection-preset:reload:source-completeness"]
                assert restored.result_refs == [
                    "intersection-topology:intersection:reload",
                    "intersection-drainage-hints:intersection:reload",
                ]
                assert restored.anchor_rows[0].approval_status == "locked"
                assert restored.anchor_rows[0].secondary_station_refs == {"alignment:side": 60.0}
                assert restored.anchor_rows[0].diagnostic_rows == ["anchor_reload_locked"]
                assert restored.corner_rows[0].approval_status == "draft"
                assert restored.corner_rows[0].diagnostic_rows == ["corner_reload_review"]
                assert restored.edge_policy_rows[0].edge_role == "gutter_edge"
                assert restored.edge_policy_rows[0].offset_value == 4.2
                assert restored.edge_policy_rows[0].approval_status == "draft"
                assert restored.edge_policy_rows[0].subassembly_kind == "gutter"
                assert restored.edge_policy_rows[0].diagnostic_rows == ["edge_reload_review"]
                assert restored.lane_connection_rows[0].to_lane_index == 2
                assert restored.lane_connection_rows[0].approval_status == "draft"
                assert restored.lane_connection_rows[0].diagnostic_rows == ["lane_reload_review"]
                assert restored.grading_policy_rows[0].low_point_strategy == "sag_low_point_review"
                assert restored.grading_policy_rows[0].approval_status == "draft"
                assert restored.grading_policy_rows[0].diagnostic_rows == ["grading_reload_review"]
                assert restored.drainage_policy_rows[0].capture_mode == "sag_low_point_inlets"
                assert restored.drainage_policy_rows[0].inlet_spacing == 35.0
                assert restored.drainage_policy_rows[0].flow_route_refs == [
                    "flow-route:sag-intersection:reload:outlet-review"
                ]
                assert restored.drainage_policy_rows[0].low_point_refs == ["drainage:sag-low-point:01"]
                assert restored.drainage_policy_rows[0].approval_status == "draft"
                assert restored.drainage_policy_rows[0].diagnostic_rows == ["drainage_reload_review"]
            finally:
                App.closeDocument(reopened.Name)
    finally:
        if doc is not None:
            App.closeDocument(doc.Name)


def test_intersection_editor_source_builder_creates_phase2_default_policy_rows() -> None:
    model = build_intersection_model_from_sources(
        intersection_kind="t_intersection",
        source_mode="Create Starter Sources",
        primary_alignment_ref="alignment:primary",
        secondary_alignment_ref="alignment:side",
        control_region_choices=[
            {
                "control_region_ref": "regions:primary/region:primary-intersection",
                "region_id": "region:primary-intersection",
                "alignment_ref": "alignment:primary",
                "station_start": 96.0,
                "station_end": 144.0,
            },
            {
                "control_region_ref": "regions:side/region:side-intersection",
                "region_id": "region:side-intersection",
                "alignment_ref": "alignment:side",
                "station_start": 0.0,
                "station_end": 48.0,
            },
        ],
    )

    intersection = model.intersection_rows[0]

    assert len(intersection.leg_rows) == 2
    assert len(model.anchor_rows) == 1
    assert model.anchor_rows[0].source_method == "preset_default"
    assert model.anchor_rows[0].approval_status == "draft"
    assert model.anchor_rows[0].diagnostic_rows == ["anchor_source_defaulted"]
    assert intersection.leg_rows[0].source_method == "region_derived"
    assert intersection.leg_rows[0].approval_status == "draft"
    assert intersection.leg_rows[0].span_source == "control_region"
    assert "leg_approval_pending" in intersection.leg_rows[0].diagnostic_rows
    assert model.control_area_rows[0].source_method == "region_derived"
    assert model.control_area_rows[0].approval_status == "draft"
    assert model.control_area_rows[0].intent_status == "region_derived"
    assert "control_area_region_derived" in model.control_area_rows[0].diagnostic_rows
    assert "control_area_approval_pending" in model.control_area_rows[0].diagnostic_rows
    assert len(model.corner_rows) == 2
    assert model.corner_rows[0].source_method == "preset_default"
    assert model.corner_rows[0].approval_status == "draft"
    assert "corner_approval_pending" in model.corner_rows[0].diagnostic_rows
    assert model.curb_return_policy_rows[0].corner_refs == [row.corner_id for row in model.corner_rows]
    assert len(model.arm_policy_rows) == 2
    assert len(model.edge_policy_rows) == 4
    assert len(model.drainage_policy_rows) == 1
    assert intersection.leg_rows[0].arm_policy_ref == model.arm_policy_rows[0].policy_id
    assert intersection.leg_rows[0].edge_policy_refs[0] == model.edge_policy_rows[0].policy_id
    assert model.edge_policy_rows[1].edge_role == "daylight_hinge"
    assert model.edge_policy_rows[0].edge_family_intent == "lane"
    assert model.edge_policy_rows[0].source_method == "subassembly_default"
    assert model.edge_policy_rows[0].approval_status == "draft"
    assert "edge_family_approval_pending" in model.edge_policy_rows[0].diagnostic_rows
    assert model.edge_policy_rows[1].edge_family_intent == "side_slope"
    assert model.edge_policy_rows[1].subassembly_kind == "side_slope"
    assert len(model.lane_connection_rows) == 2
    assert model.lane_connection_rows[0].source_method == "preset_default"
    assert model.lane_connection_rows[0].approval_status == "draft"
    assert "lane_connection_approval_pending" in model.lane_connection_rows[0].diagnostic_rows
    assert model.grading_policy_rows[0].source_method == "preset_default"
    assert model.grading_policy_rows[0].approval_status == "draft"
    assert model.grading_policy_rows[0].crown_behavior == "flatten"
    assert "grading_policy_approval_pending" in model.grading_policy_rows[0].diagnostic_rows
    assert model.drainage_policy_rows[0].capture_mode == "review_low_points"
    assert model.drainage_policy_rows[0].intent_status == "hint_only"
    assert model.drainage_policy_rows[0].approval_status == "draft"
    assert "drainage_policy_hint_only" in model.drainage_policy_rows[0].diagnostic_rows
    assert model.drainage_policy_rows[0].policy_id in intersection.policy_refs



def test_intersection_edge_network_exposes_curb_return_contact_stations() -> None:
    doc, project = _new_project_doc()
    try:
        create_starter_intersection_sources(doc, "t_intersection", project=project)
        alignments = list_v1_alignment_choices(doc)
        control_regions = list_intersection_control_region_choices(doc, intersection_ref_for_kind("t_intersection"))
        model = build_intersection_model_from_sources(
            intersection_kind="t_intersection",
            source_mode="Create Starter Sources",
            primary_alignment_ref=alignments[0][0],
            secondary_alignment_ref=alignments[1][0],
            control_region_choices=control_regions,
        )

        edge_network = IntersectionEvaluationService().evaluate_edge_network(model)
        curb_edges = [row for row in edge_network.edge_rows if row.edge_family == "curb_return"]

        assert curb_edges
        for row in curb_edges:
            assert row.contact_station_refs
            assert alignments[0][0] in row.contact_station_refs
            assert alignments[1][0] in row.contact_station_refs
            assert len(row.contact_station_refs[alignments[0][0]]) >= 3
            assert len(row.contact_station_refs[alignments[1][0]]) >= 3
    finally:
        App.closeDocument(doc.Name)
