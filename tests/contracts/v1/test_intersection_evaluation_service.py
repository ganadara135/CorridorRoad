
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCornerRow,
    IntersectionCurbReturnPolicyRow,
    IntersectionDrainagePolicyRow,
    IntersectionGradingPolicyRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
)


def _sample_intersection_model() -> IntersectionModel:
    return IntersectionModel(
        schema_version=1,
        project_id="project:demo",
        intersection_model_id="intersection-model:main",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                leg_rows=[
                    IntersectionLegRow(
                        "intersection:t-01:leg-main-before",
                        "primary_before",
                        "alignment:main",
                        intersection_id="intersection:t-01",
                        region_ref="region:main-intersection",
                        approach_station_start=480.0,
                        approach_station_end=520.0,
                        arm_policy_ref="arm-policy:t-01:primary-before",
                        grading_policy_ref="policy:grading-main",
                        priority=1,
                    ),
                    IntersectionLegRow(
                        "intersection:t-01:leg-main-after",
                        "primary_after",
                        "alignment:main",
                        intersection_id="intersection:t-01",
                        region_ref="region:main-intersection",
                        approach_station_start=520.0,
                        approach_station_end=560.0,
                        arm_policy_ref="arm-policy:t-01:primary-after",
                        grading_policy_ref="policy:grading-main",
                        priority=2,
                    ),
                    IntersectionLegRow(
                        "intersection:t-01:leg-side",
                        "side_approach",
                        "alignment:side",
                        intersection_id="intersection:t-01",
                        region_ref="region:side-intersection",
                        approach_station_start=0.0,
                        approach_station_end=120.0,
                        arm_policy_ref="arm-policy:t-01:side",
                        grading_policy_ref="policy:grading-side",
                        priority=1,
                    ),
                ],
                policy_refs=[
                    "arm-policy:t-01:primary-before",
                    "arm-policy:t-01:primary-after",
                    "arm-policy:t-01:side",
                    "edge-policy:t-01:primary-before:pavement",
                    "edge-policy:t-01:primary-before:daylight",
                    "edge-policy:t-01:primary-after:pavement",
                    "edge-policy:t-01:primary-after:daylight",
                    "edge-policy:t-01:side:pavement",
                    "edge-policy:t-01:side:daylight",
                    "policy:curb-return-main",
                    "policy:grading-main",
                    "policy:grading-side",
                    "policy:drainage-main",
                ],
            )
        ],
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:intersection:t-01:main",
                intersection_id="intersection:t-01",
                source_method="manual",
                approval_status="locked",
                primary_alignment_ref="alignment:main",
                primary_station=520.0,
                secondary_station_refs={"alignment:side": 60.0},
                point_x=10.0,
                point_y=20.0,
                point_z=30.0,
                tolerance=0.05,
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="intersection:t-01:control-main",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:main",
                station_ranges=[(480.0, 560.0)],
                influence_ranges=[(460.0, 580.0)],
                control_region_refs=["region:main-intersection"],
                curb_return_policy_ref="policy:curb-return-main",
                turn_lane_policy_ref="policy:turn-lane-main",
                grading_policy_ref="policy:grading-main",
                drainage_policy_ref="policy:drainage-main",
            ),
            IntersectionControlArea(
                control_area_id="intersection:t-01:control-side",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:side",
                station_ranges=[(0.0, 120.0)],
                influence_ranges=[(0.0, 140.0)],
                control_region_refs=["region:side-intersection"],
                curb_return_policy_ref="policy:curb-return-side",
                turn_lane_policy_ref="policy:turn-lane-side",
                grading_policy_ref="policy:grading-side",
                drainage_policy_ref="policy:drainage-side",
            ),
        ],
        corner_rows=[
            IntersectionCornerRow(
                corner_id="corner:intersection:t-01:left",
                intersection_id="intersection:t-01",
                control_area_ref="intersection:t-01:control-main",
                from_leg_ref="intersection:t-01:leg-main-before",
                to_leg_ref="intersection:t-01:leg-side",
                side="left",
                quadrant="left",
                curb_return_policy_ref="policy:curb-return-main",
                source_method="manual",
                approval_status="locked",
            ),
            IntersectionCornerRow(
                corner_id="corner:intersection:t-01:right",
                intersection_id="intersection:t-01",
                control_area_ref="intersection:t-01:control-main",
                from_leg_ref="intersection:t-01:leg-side",
                to_leg_ref="intersection:t-01:leg-main-after",
                side="right",
                quadrant="right",
                curb_return_policy_ref="policy:curb-return-main",
                source_method="manual",
                approval_status="locked",
            ),
        ],
        arm_policy_rows=[
            IntersectionArmPolicyRow("arm-policy:t-01:primary-before", "intersection:t-01", "intersection:t-01:leg-main-before"),
            IntersectionArmPolicyRow("arm-policy:t-01:primary-after", "intersection:t-01", "intersection:t-01:leg-main-after"),
            IntersectionArmPolicyRow("arm-policy:t-01:side", "intersection:t-01", "intersection:t-01:leg-side"),
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                "policy:curb-return-main",
                "intersection:t-01",
                radius=12.0,
                side="all",
                approach_leg_refs=[
                    "intersection:t-01:leg-main-before",
                    "intersection:t-01:leg-main-after",
                    "intersection:t-01:leg-side",
                ],
                corner_refs=[
                    "corner:intersection:t-01:left",
                    "corner:intersection:t-01:right",
                ],
            )
        ],
        grading_policy_rows=[
            IntersectionGradingPolicyRow(
                "policy:grading-main",
                "intersection:t-01",
                primary_alignment_ref="alignment:main",
                controlling_profile_ref="profile:main",
                crown_behavior="preserve_primary_crown",
                tie_in_rule="tie_to_primary_profile",
                crossfall_transition="linear",
                low_point_strategy="review_low_points",
                approval_status="locked",
            ),
            IntersectionGradingPolicyRow(
                "policy:grading-side",
                "intersection:t-01",
                primary_alignment_ref="alignment:side",
                controlling_profile_ref="profile:side",
                crown_behavior="blend_primary_side_crowns",
                tie_in_rule="blend_to_leg_profiles",
                crossfall_transition="linear",
                low_point_strategy="review_low_points",
                approval_status="locked",
            ),
        ],
        drainage_policy_rows=[
            IntersectionDrainagePolicyRow(
                "policy:drainage-main",
                "intersection:t-01",
                drainage_element_refs=["drainage:inlet-main"],
                flow_route_refs=["flow-route:main"],
                inlet_candidate_refs=["inlet-candidate:main"],
                low_point_refs=["low-point:central"],
                intent_status="accepted",
                approval_status="locked",
            ),
        ],
    )


def test_intersection_evaluation_resolves_by_alignment_and_station() -> None:
    result = IntersectionEvaluationService().resolve_station(
        _sample_intersection_model(),
        90.0,
        alignment_ref="alignment:side",
    )

    assert result.active_intersection_id == "intersection:t-01"
    assert result.active_control_area_id == "intersection:t-01:control-side"
    assert result.active_leg_id == "intersection:t-01:leg-side"
    assert result.leg_role == "side_approach"
    assert result.control_region_refs == ("region:side-intersection",)
    assert result.curb_return_policy_ref == "policy:curb-return-side"
    assert result.turn_lane_policy_ref == "policy:turn-lane-side"
    assert result.grading_policy_ref == "policy:grading-side"
    assert result.drainage_policy_ref == "policy:drainage-side"
    assert result.diagnostic_rows == ()


def test_intersection_evaluation_preserves_station_only_compatibility() -> None:
    result = IntersectionEvaluationService().resolve_station(_sample_intersection_model(), 500.0)

    assert result.active_intersection_id == "intersection:t-01"
    assert result.active_control_area_id == "intersection:t-01:control-main"
    assert result.active_leg_id == "intersection:t-01:leg-main-before"


def test_intersection_evaluation_does_not_cross_match_other_alignment() -> None:
    result = IntersectionEvaluationService().resolve_station(
        _sample_intersection_model(),
        90.0,
        alignment_ref="alignment:main",
    )

    assert result.active_intersection_id == ""
    assert result.diagnostic_rows == ("intersection_context_not_found_for_alignment_station",)


def test_intersection_evaluation_reports_missing_leg_when_control_area_matches() -> None:
    model = _sample_intersection_model()
    result = IntersectionEvaluationService().resolve_station(
        model,
        130.0,
        alignment_ref="alignment:side",
    )

    assert result.active_control_area_id == "intersection:t-01:control-side"
    assert result.active_leg_id == ""
    assert result.diagnostic_rows == ("intersection_leg_not_found_for_alignment_station",)
