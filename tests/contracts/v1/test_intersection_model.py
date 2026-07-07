from freecad.Corridor_Road.v1.models.source.intersection_model import (
    INTERSECTION_KIND_PRESETS,
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
    IntersectionSlopeFacePolicyRow,
    intersection_kind_from_label,
    intersection_preset_labels,
    intersection_row_from_kind,
)


def test_intersection_type_presets_are_user_selectable() -> None:
    labels = intersection_preset_labels()

    assert labels == ["T Intersection", "Cross Intersection", "Y Intersection"]
    assert intersection_kind_from_label("T Intersection") == "t_intersection"
    assert intersection_kind_from_label("Cross Intersection") == "cross_intersection"
    assert intersection_kind_from_label("Y Intersection") == "y_intersection"
    assert set(INTERSECTION_KIND_PRESETS) == {"t_intersection", "cross_intersection", "y_intersection"}


def test_intersection_row_preserves_alignment_refs_control_regions_and_legs() -> None:
    row = intersection_row_from_kind(
        intersection_id="intersection:t-01",
        intersection_kind="t_intersection",
        primary_alignment_ref="alignment:main-road",
        secondary_alignment_refs=["alignment:side-road-01"],
        control_region_refs=["region:main-intersection-01", "region:side-intersection-01"],
    )

    assert row.is_supported_kind is True
    assert row.primary_alignment_ref == "alignment:main-road"
    assert row.secondary_alignment_refs == ["alignment:side-road-01"]
    assert row.control_region_refs == ["region:main-intersection-01", "region:side-intersection-01"]
    assert row.control_area_ref == "intersection:t-01:control-area"
    assert [leg.leg_role for leg in row.leg_rows] == ["primary_before", "primary_after", "side_approach"]
    assert row.leg_rows[0].alignment_ref == "alignment:main-road"
    assert row.leg_rows[-1].alignment_ref == "alignment:side-road-01"
    assert row.leg_rows[0].arm_policy_ref == "arm-policy:intersection:t-01:leg-01"
    assert row.leg_rows[0].edge_policy_refs == [
        "edge-policy:intersection:t-01:leg-01:pavement",
        "edge-policy:intersection:t-01:leg-01:daylight",
    ]
    assert "slope-face:intersection:t-01:default" in row.policy_refs
    assert "drainage-policy:intersection:t-01:default" in row.policy_refs


def test_intersection_model_round_trips_control_area_and_leg_context() -> None:
    leg = IntersectionLegRow(
        leg_id="intersection:x-01:leg-primary",
        intersection_id="intersection:x-01",
        leg_role="primary_before",
        alignment_ref="alignment:main",
        profile_ref="profile:main",
        centerline3d_ref="centerline3d:main",
        region_ref="region:main-intersection",
        approach_station_start=480.0,
        approach_station_end=520.0,
    )
    row = IntersectionRow(
        intersection_id="intersection:x-01",
        intersection_kind="cross_intersection",
        primary_alignment_ref="alignment:main",
        secondary_alignment_refs=["alignment:cross"],
        intersection_point_x=100.0,
        intersection_point_y=50.0,
        primary_station=500.0,
        secondary_station_refs={"alignment:cross": 80.0},
        control_region_refs=["region:main-intersection", "region:cross-intersection"],
        leg_rows=[leg],
        policy_refs=["policy:curb-return-basic"],
    )
    control = IntersectionControlArea(
        control_area_id="intersection:x-01:control-main",
        intersection_id="intersection:x-01",
        alignment_ref="alignment:main",
        station_ranges=[(480.0, 560.0)],
        influence_ranges=[(460.0, 580.0)],
        control_region_refs=["region:main-intersection"],
        source_method="region_derived",
        approval_status="draft",
        intent_status="region_derived",
        source_region_refs=["region:main-intersection"],
        curb_return_policy_ref="policy:curb-return-basic",
        grading_policy_ref="policy:intersection-grading-basic",
        drainage_policy_ref="policy:intersection-drainage-basic",
        diagnostic_rows=["control_area_region_derived"],
    )
    corner = IntersectionCornerRow(
        corner_id="corner:intersection:x-01:nw",
        intersection_id="intersection:x-01",
        control_area_ref="intersection:x-01:control-main",
        from_leg_ref="intersection:x-01:leg-primary",
        to_leg_ref="intersection:x-01:leg-secondary",
        side="left",
        quadrant="northwest",
        curb_return_policy_ref="policy:curb-return-basic",
        source_method="manual",
        approval_status="locked",
        diagnostic_rows=["corner_locked_by_user"],
    )
    model = IntersectionModel(
        schema_version=1,
        project_id="project:demo",
        intersection_model_id="intersection-model:main",
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:intersection:x-01:main",
                intersection_id="intersection:x-01",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=500.0,
                secondary_station_refs={"alignment:cross": 80.0},
                point_x=100.0,
                point_y=50.0,
                point_z=10.0,
                tolerance=0.05,
                diagnostic_rows=["anchor_locked_by_user"],
            )
        ],
        intersection_rows=[row],
        control_area_rows=[control],
        corner_rows=[corner],
        arm_policy_rows=[
            IntersectionArmPolicyRow(
                policy_id="policy:arm-primary",
                intersection_id="intersection:x-01",
                leg_ref="intersection:x-01:leg-primary",
                arm_role="primary_before",
                design_speed_kph=50.0,
                lane_count=2,
                lane_width=3.6,
                shoulder_width=1.2,
            )
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="policy:curb-return-basic",
                intersection_id="intersection:x-01",
                radius=12.0,
                side="all",
                approach_leg_refs=["intersection:x-01:leg-primary"],
                corner_refs=["corner:intersection:x-01:nw"],
            )
        ],
        grading_policy_rows=[
            IntersectionGradingPolicyRow(
                policy_id="policy:intersection-grading-basic",
                intersection_id="intersection:x-01",
                mode="flatten_intersection",
                target_crossfall_percent=0.0,
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:cross"],
                controlling_profile_ref="profile:main",
                crown_behavior="preserve_primary_crown",
                tie_in_rule="tie_to_primary_profile",
                crossfall_transition="linear",
                low_point_strategy="review_low_points",
                source_method="manual",
                approval_status="locked",
                diagnostic_rows=["grading_locked_by_user"],
            )
        ],
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                policy_id="policy:edge-primary-pavement",
                intersection_id="intersection:x-01",
                leg_ref="intersection:x-01:leg-primary",
                edge_role="pavement_edge",
                side="both",
                offset_rule="lane_width_from_arm_policy",
                elevation_rule="from_grading_policy",
                edge_family_intent="lane",
                source_method="subassembly_derived",
                approval_status="locked",
                assembly_ref="assembly:basic-road",
                template_ref="template:basic-road",
                subassembly_ref="subassembly:lane-left",
                subassembly_kind="lane",
                diagnostic_rows=["edge_family_locked_by_user"],
            )
        ],
        lane_connection_rows=[
            IntersectionLaneConnectionRow(
                connection_id="lane-connection:intersection:x-01:through-01",
                intersection_id="intersection:x-01",
                movement_type="through",
                from_leg_ref="intersection:x-01:leg-primary",
                to_leg_ref="intersection:x-01:leg-secondary",
                from_edge_policy_ref="policy:edge-primary-pavement",
                to_edge_policy_ref="policy:edge-secondary-pavement",
                source_method="manual",
                approval_status="locked",
                diagnostic_rows=["lane_connection_locked_by_user"],
            )
        ],
        drainage_policy_rows=[
            IntersectionDrainagePolicyRow(
                policy_id="policy:intersection-drainage-basic",
                intersection_id="intersection:x-01",
                capture_mode="review_low_points",
                low_point_tolerance=0.04,
                gutter_edge_refs=["policy:edge-primary-pavement"],
                drainage_element_refs=["drainage:inlet-01"],
                flow_route_refs=["flow-route:intersection-main"],
                inlet_candidate_refs=["inlet-candidate:01"],
                low_point_refs=["low-point:central"],
                intent_status="accepted",
                source_method="manual",
                approval_status="locked",
                diagnostic_rows=["drainage_locked_by_user"],
            )
        ],
        slope_face_policy_rows=[
            IntersectionSlopeFacePolicyRow(
                policy_id="policy:intersection-slope-face-basic",
                intersection_id="intersection:x-01",
                policy_name="Locked Slope Face Policy",
                tie_slope_overlap_m=0.75,
                slope_face_width_offset_m=0.25,
                blend_angle_deg=5.0,
                max_panel_extension_m=4.0,
                min_panel_width_m=0.3,
                source_method="manual",
                approval_status="locked",
                diagnostic_rows=["slope_face_policy_locked_by_user"],
            )
        ],
    )

    assert model.intersection_rows[0].intersection_kind == "cross_intersection"
    assert model.anchor_rows[0].approval_status == "locked"
    assert model.anchor_rows[0].secondary_station_refs["alignment:cross"] == 80.0
    assert model.anchor_rows[0].diagnostic_rows == ["anchor_locked_by_user"]
    assert model.intersection_rows[0].secondary_station_refs["alignment:cross"] == 80.0
    assert model.intersection_rows[0].leg_rows[0].centerline3d_ref == "centerline3d:main"
    assert model.control_area_rows[0].control_region_refs == ["region:main-intersection"]
    assert model.control_area_rows[0].source_method == "region_derived"
    assert model.control_area_rows[0].approval_status == "draft"
    assert model.control_area_rows[0].intent_status == "region_derived"
    assert model.control_area_rows[0].source_region_refs == ["region:main-intersection"]
    assert model.control_area_rows[0].diagnostic_rows == ["control_area_region_derived"]
    assert model.corner_rows[0].approval_status == "locked"
    assert model.corner_rows[0].curb_return_policy_ref == "policy:curb-return-basic"
    assert model.corner_rows[0].diagnostic_rows == ["corner_locked_by_user"]
    assert model.arm_policy_rows[0].lane_width == 3.6
    assert model.curb_return_policy_rows[0].radius == 12.0
    assert model.curb_return_policy_rows[0].approach_leg_refs == ["intersection:x-01:leg-primary"]
    assert model.curb_return_policy_rows[0].corner_refs == ["corner:intersection:x-01:nw"]
    assert model.edge_policy_rows[0].elevation_rule == "from_grading_policy"
    assert model.edge_policy_rows[0].edge_family_intent == "lane"
    assert model.edge_policy_rows[0].approval_status == "locked"
    assert model.edge_policy_rows[0].assembly_ref == "assembly:basic-road"
    assert model.edge_policy_rows[0].subassembly_kind == "lane"
    assert model.edge_policy_rows[0].diagnostic_rows == ["edge_family_locked_by_user"]
    assert model.lane_connection_rows[0].movement_type == "through"
    assert model.lane_connection_rows[0].approval_status == "locked"
    assert model.lane_connection_rows[0].diagnostic_rows == ["lane_connection_locked_by_user"]
    assert model.grading_policy_rows[0].mode == "flatten_intersection"
    assert model.grading_policy_rows[0].controlling_profile_ref == "profile:main"
    assert model.grading_policy_rows[0].crown_behavior == "preserve_primary_crown"
    assert model.grading_policy_rows[0].tie_in_rule == "tie_to_primary_profile"
    assert model.grading_policy_rows[0].approval_status == "locked"
    assert model.grading_policy_rows[0].diagnostic_rows == ["grading_locked_by_user"]
    assert model.drainage_policy_rows[0].gutter_edge_refs == ["policy:edge-primary-pavement"]
    assert model.drainage_policy_rows[0].drainage_element_refs == ["drainage:inlet-01"]
    assert model.slope_face_policy_rows[0].tie_slope_overlap_m == 0.75
    assert model.slope_face_policy_rows[0].slope_face_width_offset_m == 0.25
    assert model.slope_face_policy_rows[0].approval_status == "locked"
    assert model.slope_face_policy_rows[0].diagnostic_rows == ["slope_face_policy_locked_by_user"]
    assert model.drainage_policy_rows[0].flow_route_refs == ["flow-route:intersection-main"]
    assert model.drainage_policy_rows[0].intent_status == "accepted"
    assert model.drainage_policy_rows[0].approval_status == "locked"
    assert model.drainage_policy_rows[0].diagnostic_rows == ["drainage_locked_by_user"]


def test_intersection_kind_helper_rejects_unsupported_kind() -> None:
    try:
        intersection_row_from_kind(intersection_id="intersection:bad", intersection_kind="roundabout")
    except ValueError as exc:
        assert "Unsupported intersection kind" in str(exc)
    else:
        raise AssertionError("Unsupported intersection kind should be rejected.")
