import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    build_intersection_model_from_sources,
    create_starter_intersection_sources,
    intersection_ref_for_kind,
    list_intersection_control_region_choices,
    list_v1_alignment_choices,
    show_intersection_edge_network_preview,
)
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionEdgePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    create_or_update_v1_intersection_model_object,
    to_intersection_model,
)


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
                            arm_policy_ref="arm-policy:intersection:t-01:leg-01",
                            edge_policy_refs=[
                                "edge-policy:intersection:t-01:leg-01:pavement",
                                "edge-policy:intersection:t-01:leg-01:daylight",
                            ],
                            grading_policy_ref="grading:intersection:t-01:default",
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
                )
            ],
            edge_policy_rows=[
                IntersectionEdgePolicyRow(
                    policy_id="edge-policy:intersection:t-01:leg-01:pavement",
                    intersection_id="intersection:t-01",
                    leg_ref="intersection:t-01:leg-01",
                    edge_role="pavement_edge",
                    offset_rule="lane_width_from_arm_policy",
                )
            ],
            grading_policy_rows=[
                IntersectionGradingPolicyRow(
                    policy_id="grading:intersection:t-01:default",
                    intersection_id="intersection:t-01",
                    mode="flatten_intersection",
                    primary_alignment_ref="alignment:main",
                )
            ],
            drainage_policy_rows=[
                IntersectionDrainagePolicyRow(
                    policy_id="drainage-policy:intersection:t-01:default",
                    intersection_id="intersection:t-01",
                    gutter_edge_refs=["edge-policy:intersection:t-01:leg-01:pavement"],
                )
            ],
        )

        obj = create_or_update_v1_intersection_model_object(doc, intersection_model=model, project=project)
        restored = to_intersection_model(obj)

        assert obj.ArmPolicyCount == 1
        assert obj.EdgePolicyCount == 1
        assert obj.DrainagePolicyCount == 1
        assert restored is not None
        assert restored.intersection_rows[0].leg_rows[0].arm_policy_ref == "arm-policy:intersection:t-01:leg-01"
        assert restored.intersection_rows[0].leg_rows[0].edge_policy_refs == [
            "edge-policy:intersection:t-01:leg-01:pavement",
            "edge-policy:intersection:t-01:leg-01:daylight",
        ]
        assert restored.arm_policy_rows[0].lane_width == 3.6
        assert restored.curb_return_policy_rows[0].long_edge_factor == 3.0
        assert restored.curb_return_policy_rows[0].max_boundary_edge_length == 2.0
        assert restored.edge_policy_rows[0].offset_rule == "lane_width_from_arm_policy"
        assert restored.drainage_policy_rows[0].gutter_edge_refs == [
            "edge-policy:intersection:t-01:leg-01:pavement"
        ]
    finally:
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
    assert len(model.arm_policy_rows) == 2
    assert len(model.edge_policy_rows) == 4
    assert len(model.drainage_policy_rows) == 1
    assert intersection.leg_rows[0].arm_policy_ref == model.arm_policy_rows[0].policy_id
    assert intersection.leg_rows[0].edge_policy_refs[0] == model.edge_policy_rows[0].policy_id
    assert model.edge_policy_rows[1].edge_role == "daylight_hinge"
    assert model.drainage_policy_rows[0].capture_mode == "review_low_points"
    assert model.drainage_policy_rows[0].policy_id in intersection.policy_refs


def test_intersection_edge_network_preview_object_uses_source_edge_rows() -> None:
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

        obj = show_intersection_edge_network_preview(doc, intersection_model=model, project=project)

        assert obj.Label == "Intersection Edge Network Preview"
        assert obj.CRRecordKind == "v1_intersection_edge_network_preview"
        assert obj.V1ObjectType == "V1IntersectionEdgeNetworkPreview"
        assert obj.EdgeNetworkStatus == "ready"
        assert obj.EdgeCount == 6
        assert obj.LegEdgeCount == 4
        assert obj.DaylightEdgeCount == 2
        assert obj.CurbReturnEdgeCount == 2
        assert len(list(obj.EdgeIds)) == 6
        assert obj.ShapePartCount > 0
    finally:
        App.closeDocument(doc.Name)
