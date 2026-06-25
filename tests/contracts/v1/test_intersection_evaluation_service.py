from dataclasses import fields, replace

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
from freecad.Corridor_Road.v1.models.result.intersection_corridor_clipping import IntersectionCorridorClipRow
from freecad.Corridor_Road.v1.models.result.intersection_drainage_hint import IntersectionDrainageHintRow
from freecad.Corridor_Road.v1.models.result.intersection_edge_network import IntersectionEdgeNetworkRow
from freecad.Corridor_Road.v1.models.result.intersection_grading_context import IntersectionGradingContextRow
from freecad.Corridor_Road.v1.models.result.intersection_slope_face_loop import IntersectionSlopeFaceLoopRow
from freecad.Corridor_Road.v1.models.result.intersection_surface_zone import IntersectionSurfaceZoneRow
from freecad.Corridor_Road.v1.models.result.intersection_topology import (
    IntersectionTopologyAnchorRow,
    IntersectionTopologyControlAreaRow,
    IntersectionTopologyLaneConnectionRow,
    IntersectionTopologyLegSpanRow,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
)


def test_intersection_core_result_rows_expose_source_status_contract() -> None:
    """Core evaluated result rows must preserve source lineage for review/output consumers."""

    row_types = (
        IntersectionTopologyAnchorRow,
        IntersectionTopologyLegSpanRow,
        IntersectionTopologyControlAreaRow,
        IntersectionTopologyLaneConnectionRow,
        IntersectionEdgeNetworkRow,
        IntersectionSurfaceZoneRow,
        IntersectionCorridorClipRow,
        IntersectionGradingContextRow,
        IntersectionDrainageHintRow,
        IntersectionSlopeFaceLoopRow,
    )

    for row_type in row_types:
        field_names = {field.name for field in fields(row_type)}
        assert "source_status" in field_names, row_type.__name__
        assert "source_diagnostic_rows" in field_names, row_type.__name__


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
                        edge_policy_refs=(
                            "edge-policy:t-01:primary-before:pavement",
                            "edge-policy:t-01:primary-before:daylight",
                        ),
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
                        edge_policy_refs=(
                            "edge-policy:t-01:primary-after:pavement",
                            "edge-policy:t-01:primary-after:daylight",
                        ),
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
                        edge_policy_refs=(
                            "edge-policy:t-01:side:pavement",
                            "edge-policy:t-01:side:daylight",
                        ),
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
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                "edge-policy:t-01:primary-before:pavement",
                "intersection:t-01",
                "intersection:t-01:leg-main-before",
                edge_family_intent="lane",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="lane",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:t-01:primary-before:daylight",
                "intersection:t-01",
                "intersection:t-01:leg-main-before",
                edge_role="daylight_hinge",
                edge_family_intent="side_slope",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="side_slope",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:t-01:primary-after:pavement",
                "intersection:t-01",
                "intersection:t-01:leg-main-after",
                edge_family_intent="lane",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="lane",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:t-01:primary-after:daylight",
                "intersection:t-01",
                "intersection:t-01:leg-main-after",
                edge_role="daylight_hinge",
                edge_family_intent="side_slope",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="side_slope",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:t-01:side:pavement",
                "intersection:t-01",
                "intersection:t-01:leg-side",
                edge_family_intent="lane",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="lane",
            ),
            IntersectionEdgePolicyRow(
                "edge-policy:t-01:side:daylight",
                "intersection:t-01",
                "intersection:t-01:leg-side",
                edge_role="daylight_hinge",
                edge_family_intent="side_slope",
                source_method="subassembly_derived",
                approval_status="locked",
                subassembly_kind="side_slope",
            ),
        ],
        lane_connection_rows=[
            IntersectionLaneConnectionRow(
                connection_id="lane-connection:intersection:t-01:through-main",
                intersection_id="intersection:t-01",
                movement_type="through",
                from_leg_ref="intersection:t-01:leg-main-before",
                to_leg_ref="intersection:t-01:leg-main-after",
                from_edge_policy_ref="edge-policy:t-01:primary-before:pavement",
                to_edge_policy_ref="edge-policy:t-01:primary-after:pavement",
                source_method="manual",
                approval_status="locked",
            ),
            IntersectionLaneConnectionRow(
                connection_id="lane-connection:intersection:t-01:turn-side",
                intersection_id="intersection:t-01",
                movement_type="turn",
                from_leg_ref="intersection:t-01:leg-side",
                to_leg_ref="intersection:t-01:leg-main-after",
                from_edge_policy_ref="edge-policy:t-01:side:pavement",
                to_edge_policy_ref="edge-policy:t-01:primary-after:pavement",
                source_method="manual",
                approval_status="locked",
            ),
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


def test_intersection_topology_evaluation_returns_leg_spans_control_areas_and_diagnostics() -> None:
    result = IntersectionEvaluationService().evaluate_topology(_sample_intersection_model())

    assert result.status == "warning"
    assert result.intersection_id == "intersection:t-01"
    assert result.intersection_kind == "t_intersection"
    assert result.participating_alignment_count == 2
    assert result.control_region_count == 2
    assert result.anchor_count == 1
    assert result.leg_span_count == 3
    assert result.control_area_count == 2
    assert result.lane_connection_count == 2
    assert any(row.startswith("warning:source_leg_profile_ref_missing:") for row in result.diagnostic_rows)
    assert result.anchor_rows[0].source_anchor_ref == "anchor:intersection:t-01:main"
    assert result.anchor_rows[0].primary_alignment_ref == "alignment:main"
    assert result.anchor_rows[0].primary_station == 520.0
    assert result.anchor_rows[0].secondary_station_refs == (("alignment:side", 60.0),)
    assert result.anchor_rows[0].point_xyz == (10.0, 20.0, 30.0)
    assert result.anchor_rows[0].tolerance == 0.05
    assert result.anchor_rows[0].source_status == "accepted"
    assert result.anchor_rows[0].station_lineage_status == "accepted"
    assert result.anchor_rows[0].handoff_target == "intersection-source-stage:anchor:anchor-intersection-t-01-main"
    assert result.leg_span_rows[0].leg_ref == "intersection:t-01:leg-main-before"
    assert result.leg_span_rows[0].station_start == 480.0
    assert result.leg_span_rows[0].station_end == 520.0
    assert result.leg_span_rows[0].control_area_ref == "intersection:t-01:control-main"
    assert result.leg_span_rows[0].edge_policy_refs == (
        "edge-policy:t-01:primary-before:pavement",
        "edge-policy:t-01:primary-before:daylight",
    )
    assert result.control_area_rows[1].alignment_ref == "alignment:side"
    assert result.control_area_rows[1].station_ranges == ((0.0, 120.0),)
    assert result.control_area_rows[1].control_area_result_id == "intersection:t-01:control-area-result:02"
    assert result.control_area_rows[1].source_control_area_ref == "intersection:t-01:control-side"
    assert result.control_area_rows[1].result_region_refs == ("region:side-intersection",)
    assert result.control_area_rows[1].region_lineage_status == "result_only"
    assert result.control_area_rows[1].clipping_boundary_ref == "intersection-control-boundary:intersection-t-01-control-side"
    assert result.control_area_rows[1].region_handoff_status == "review_required"
    assert result.control_area_rows[1].clipping_handoff_status == "review_required"
    assert result.control_area_rows[1].handoff_target == "intersection-source-stage:control_areas:intersection-t-01-control-side"
    assert result.control_area_rows[1].surface_zone_scope == "intersection_control_area"
    assert result.control_area_rows[1].source_status == "warning"
    assert result.lane_connection_rows[0].movement_type == "through"
    assert result.lane_connection_rows[0].lane_connection_result_id == "intersection:t-01:lane-connection-result:01"
    assert result.lane_connection_rows[0].source_lane_connection_ref == "lane-connection:intersection:t-01:through-main"
    assert result.lane_connection_rows[0].from_leg_source_status == "warning"
    assert result.lane_connection_rows[0].to_leg_source_status == "warning"
    assert result.lane_connection_rows[0].from_edge_family_intent == "lane"
    assert result.lane_connection_rows[0].to_edge_family_intent == "lane"
    assert result.lane_connection_rows[0].from_edge_source_status == "accepted"
    assert result.lane_connection_rows[0].to_edge_source_status == "accepted"
    assert result.lane_connection_rows[0].movement_lineage_status == "warning"
    assert result.lane_connection_rows[0].leg_handoff_status == "review_required"
    assert result.lane_connection_rows[0].edge_handoff_status == "accepted"
    assert result.lane_connection_rows[0].handoff_scope == "lane_connection"
    assert result.lane_connection_rows[0].handoff_target == "intersection-source-stage:lane_connections:lane-connection-intersection-t-01-through-main"
    assert result.lane_connection_rows[0].source_status == "warning"
    assert "source_lane_connection_from_leg_status:warning" in result.lane_connection_rows[0].source_diagnostic_rows


def test_intersection_topology_evaluation_warns_about_unresolved_policy_refs() -> None:
    model = _sample_intersection_model()
    model = IntersectionModel(
        schema_version=model.schema_version,
        project_id=model.project_id,
        intersection_model_id=model.intersection_model_id,
        intersection_rows=model.intersection_rows,
        anchor_rows=model.anchor_rows,
        control_area_rows=model.control_area_rows,
    )

    result = IntersectionEvaluationService().evaluate_topology(model)

    assert result.status == "warning"
    assert "warning:leg_arm_policy_ref_unresolved:intersection:t-01:leg-main-before:arm-policy:t-01:primary-before" in result.diagnostic_rows
    assert "warning:leg_edge_policy_ref_unresolved:intersection:t-01:leg-side:edge-policy:t-01:side:pavement" in result.diagnostic_rows
    assert result.leg_span_rows[0].status == "warning"


def test_intersection_topology_evaluation_errors_when_control_area_is_missing() -> None:
    model = _sample_intersection_model()
    model = IntersectionModel(
        schema_version=model.schema_version,
        project_id=model.project_id,
        intersection_model_id=model.intersection_model_id,
        intersection_rows=model.intersection_rows,
    )

    result = IntersectionEvaluationService().evaluate_topology(model)

    assert result.status == "error"
    assert "error:intersection_control_area_rows_missing" in result.diagnostic_rows


def test_intersection_edge_network_evaluation_creates_leg_and_curb_return_edges() -> None:
    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(_sample_intersection_model())
    result = service.evaluate_edge_network(_sample_intersection_model(), topology)

    assert result.status == "warning"
    assert result.intersection_id == "intersection:t-01"
    assert result.edge_count == 8
    assert result.leg_edge_count == 6
    assert result.daylight_edge_count == 3
    assert result.curb_return_edge_count == 2
    assert any(row.startswith("warning:source_leg_profile_ref_missing:") for row in result.diagnostic_rows)
    assert result.edge_rows[0].edge_role == "pavement_edge"
    assert result.edge_rows[0].edge_family == "leg_edge"
    assert result.edge_rows[0].leg_ref == "intersection:t-01:leg-main-before"
    assert result.edge_rows[0].station_start == 480.0
    assert result.edge_rows[0].station_end == 520.0
    curb_edges = [row for row in result.edge_rows if row.edge_family == "curb_return"]
    assert [row.side for row in curb_edges] == ["left", "right"]
    assert [row.source_corner_ref for row in curb_edges] == [
        "corner:intersection:t-01:left",
        "corner:intersection:t-01:right",
    ]
    assert curb_edges[0].edge_role == "curb_return_edge"
    assert curb_edges[0].radius == 12.0
    assert "leg-side" in curb_edges[0].leg_ref


def test_intersection_edge_network_evaluation_stops_when_topology_has_errors() -> None:
    service = IntersectionEvaluationService()
    model = IntersectionModel(schema_version=1, project_id="project:demo", intersection_model_id="intersection-model:main")
    topology = service.evaluate_topology(model)
    result = service.evaluate_edge_network(model, topology)

    assert topology.status == "error"
    assert result.status == "error"
    assert result.edge_count == 0
    assert "error:intersection_row_not_found" in result.diagnostic_rows


def test_intersection_surface_zone_evaluation_creates_zone_contracts_without_triangulation() -> None:
    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(_sample_intersection_model())
    edge_network = service.evaluate_edge_network(_sample_intersection_model(), topology)
    result = service.evaluate_surface_zones(_sample_intersection_model(), edge_network)

    assert result.status == "warning"
    assert result.intersection_id == "intersection:t-01"
    assert result.zone_count == 9
    assert result.design_zone_count == 6
    assert result.pavement_zone_count == 6
    assert result.main_pavement_zone_count == 2
    assert result.side_pavement_zone_count == 1
    assert result.central_pavement_zone_count == 1
    assert result.curb_return_zone_count == 2
    assert result.slope_zone_count == 3
    assert result.slope_zone_ready_count == 3
    assert result.slope_zone_warning_count == 0
    assert any(row.startswith("warning:source_leg_profile_ref_missing:") for row in result.diagnostic_rows)
    assert result.zone_rows[0].zone_role == "central_junction"
    assert result.zone_rows[0].zone_family == "pavement"
    assert result.zone_rows[0].design_zone_role == "central_pavement"
    assert result.zone_rows[0].alignment_refs == ("alignment:main", "alignment:side")
    assert result.zone_rows[0].triangulation_method == "pending_structured_zone"
    assert result.zone_rows[0].status == "candidate"
    assert "leg-main-before" in result.zone_rows[0].leg_refs[0]
    leg_zones = [row for row in result.zone_rows if row.zone_role == "leg_pavement"]
    assert [row.design_zone_role for row in leg_zones] == ["main_pavement", "main_pavement", "side_pavement"]
    curb_zones = [row for row in result.zone_rows if row.zone_family == "curb_return"]
    assert len(curb_zones) == 2
    assert curb_zones[0].design_zone_role == "curb_return_pavement"
    assert curb_zones[0].alignment_refs == ("alignment:main", "alignment:side")
    assert curb_zones[0].control_area_refs == ("intersection:t-01:control-main", "intersection:t-01:control-side")
    assert curb_zones[0].triangulation_method == "pending_curb_return_fan"
    slope_zones = [row for row in result.zone_rows if row.zone_family == "slope"]
    assert len(slope_zones) == 3
    assert slope_zones[0].surface_role == "slope_face"
    assert slope_zones[0].status == "ready"
    assert slope_zones[0].outer_edge_refs == ("intersection-edge:intersection-t-01:leg-01:daylight-hinge-both-02",)
    assert slope_zones[0].inner_edge_refs == ("intersection-edge:intersection-t-01:leg-01:pavement-edge-both-01",)
    assert len(slope_zones[0].tie_edge_refs) == 2
    assert slope_zones[0].boundary_edge_refs == (
        *slope_zones[0].outer_edge_refs,
        *slope_zones[0].inner_edge_refs,
        *slope_zones[0].tie_edge_refs,
    )


def test_intersection_surface_zone_evaluation_warns_when_slope_zone_lacks_pavement_or_curb_tie_edges() -> None:
    model = _sample_intersection_model()
    intersection_row = model.intersection_rows[0]
    daylight_only_legs = []
    for leg in intersection_row.leg_rows:
        daylight_only_legs.append(
            replace(
                leg,
                edge_policy_refs=tuple(ref for ref in leg.edge_policy_refs if "daylight" in str(ref)),
            )
        )
    intersection_rows = [
        replace(
            intersection_row,
            leg_rows=daylight_only_legs,
            policy_refs=[ref for ref in intersection_row.policy_refs if "daylight" in str(ref)],
        )
    ]
    model = IntersectionModel(
        schema_version=model.schema_version,
        project_id=model.project_id,
        intersection_model_id=model.intersection_model_id,
        intersection_rows=intersection_rows,
        control_area_rows=model.control_area_rows,
        arm_policy_rows=model.arm_policy_rows,
        edge_policy_rows=[
            row for row in model.edge_policy_rows if row.edge_role == "daylight_hinge"
        ],
        grading_policy_rows=model.grading_policy_rows,
    )
    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)
    result = service.evaluate_surface_zones(model, edge_network)

    assert result.status == "warning"
    assert result.slope_zone_count == 3
    assert result.slope_zone_ready_count == 0
    assert result.slope_zone_warning_count == 3
    assert any("warning:surface_zone_central_junction_requires_two_pavement_alignments" in row for row in result.diagnostic_rows)
    assert any("warning:surface_zone_curb_return_edges_missing" in row for row in result.diagnostic_rows)
    assert any("warning:slope_zone_matching_pavement_edge_missing" in row for row in result.diagnostic_rows)


def test_intersection_corridor_clipping_evaluation_creates_control_area_clip_contracts() -> None:
    service = IntersectionEvaluationService()
    model = _sample_intersection_model()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)
    surface_zones = service.evaluate_surface_zones(model, edge_network)
    result = service.evaluate_corridor_clipping(model, topology, surface_zones)

    assert result.status == "warning"
    assert result.intersection_id == "intersection:t-01"
    assert result.clip_row_count == 4
    assert result.design_clip_count == 2
    assert result.slope_clip_count == 2
    assert result.ready_clip_count == 4
    assert result.warning_clip_count == 0
    assert any(row.startswith("warning:source_leg_profile_ref_missing:") for row in result.diagnostic_rows)
    assert result.clip_rows[0].clip_boundary_source == "intersection_control_area"
    assert result.clip_rows[0].clip_timing == "before_surface_merge"
    assert result.clip_rows[0].clip_method == "station_control_area_boundary"
    assert result.clip_rows[0].surface_role == "design"
    assert result.clip_rows[0].control_area_ref == "intersection:t-01:control-main"
    assert result.clip_rows[0].source_control_area_ref == "intersection:t-01:control-main"
    assert result.clip_rows[0].control_area_intent_status == "intersection_owned"
    assert result.clip_rows[0].control_area_source_method == "manual"
    assert result.clip_rows[0].control_area_approval_status == "accepted"
    assert result.clip_rows[0].alignment_ref == "alignment:main"
    assert result.clip_rows[0].station_ranges == ((480.0, 560.0),)
    assert result.clip_rows[0].control_region_refs == ("region:main-intersection",)
    assert result.clip_rows[0].result_region_refs == ("region:main-intersection",)
    assert result.clip_rows[0].region_lineage_status == "result_only"
    assert result.clip_rows[0].source_status == "accepted"
    assert "central-junction" in result.clip_rows[0].protected_zone_refs[0]


def test_intersection_corridor_clipping_evaluation_warns_when_control_area_region_context_is_missing() -> None:
    model = _sample_intersection_model()
    control_areas = [
        replace(model.control_area_rows[0], control_region_refs=[]),
        model.control_area_rows[1],
    ]
    model = IntersectionModel(
        schema_version=model.schema_version,
        project_id=model.project_id,
        intersection_model_id=model.intersection_model_id,
        intersection_rows=model.intersection_rows,
        control_area_rows=control_areas,
        arm_policy_rows=model.arm_policy_rows,
        curb_return_policy_rows=model.curb_return_policy_rows,
        edge_policy_rows=model.edge_policy_rows,
        grading_policy_rows=model.grading_policy_rows,
        drainage_policy_rows=model.drainage_policy_rows,
    )
    service = IntersectionEvaluationService()
    result = service.evaluate_corridor_clipping(model)

    assert result.status == "warning"
    assert result.clip_row_count == 4
    assert result.ready_clip_count == 2
    assert result.warning_clip_count == 2
    assert any("warning:clip_control_area_region_refs_missing" in row for row in result.diagnostic_rows)
    assert result.clip_rows[0].source_status == "warning"
    assert "warning:clip_control_area_region_refs_missing" in result.clip_rows[0].source_diagnostic_rows


def test_intersection_grading_context_exposes_vertical_source_lineage() -> None:
    service = IntersectionEvaluationService()
    model = _sample_intersection_model()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)
    surface_zones = service.evaluate_surface_zones(model, edge_network)
    result = service.evaluate_grading_context(model, surface_zones)

    assert result.status == "warning"
    rows_by_role = {row.design_zone_role if hasattr(row, "design_zone_role") else row.zone_role: row for row in result.context_rows}
    central = rows_by_role["central_pavement"]
    assert central.source_grading_policy_ref == "policy:grading-main"
    assert central.controlling_profile_ref == "profile:main"
    assert central.profile_lineage_status == "explicit"
    assert central.profile_handoff_status == "accepted"
    assert central.superelevation_source_ref == ""
    assert central.superelevation_source_status == "intersection_policy_override"
    assert central.superelevation_handoff_status == "overridden"
    assert central.vertical_handoff_status == "ready"
    assert central.handoff_target.startswith("intersection-preview-stage:grading:")
    assert central.grading_source_scope == "intersection_policy"
    assert central.fallback_status == "none"
    assert central.source_status == "accepted"

    slope = rows_by_role["exterior_slope_face"]
    assert slope.crossfall_context == "normal_superelevation"
    assert slope.superelevation_source_status == "normal_superelevation_context"
    assert slope.superelevation_handoff_status == "inherited"
    assert slope.grading_source_scope == "normal_superelevation"
    assert slope.fallback_status == "none"


def test_intersection_drainage_hint_evaluation_generates_low_point_and_inlet_recommendations() -> None:
    service = IntersectionEvaluationService()
    model = _sample_intersection_model()
    topology = service.evaluate_topology(model)
    edge_network = service.evaluate_edge_network(model, topology)
    surface_zones = service.evaluate_surface_zones(model, edge_network)
    result = service.evaluate_drainage_hints(model, surface_zones)

    assert result.status == "warning"
    assert result.intersection_id == "intersection:t-01"
    assert result.low_point_hint_count == 1
    assert result.inlet_recommendation_count == 5
    assert result.hint_row_count == 6
    assert result.accepted_handoff_count == 6
    assert result.hint_only_count == 0
    assert result.review_required_count == 0
    assert result.ready_hint_count == 5
    assert result.warning_hint_count == 1
    assert "warning:intersection_drainage_hint_rows_require_review" in result.diagnostic_rows
    assert result.hint_rows[0].hint_kind == "low_point_candidate"
    assert result.hint_rows[0].recommended_element_kind == "low_point_review"
    assert result.hint_rows[0].drainage_policy_ref == "policy:drainage-main"
    assert result.hint_rows[0].source_drainage_policy_ref == "policy:drainage-main"
    assert result.hint_rows[0].drainage_intent_status == "accepted"
    assert result.hint_rows[0].drainage_element_refs == ("drainage:inlet-main",)
    assert result.hint_rows[0].flow_route_refs == ("flow-route:main",)
    assert result.hint_rows[0].drainage_handoff_status == "accepted_handoff"
    assert result.hint_rows[0].drainage_source_scope == "source_owned"
    assert result.hint_rows[0].accepted_drainage_ref == "drainage:inlet-main"
    assert result.hint_rows[0].drainage_review_status == "accepted"
    assert result.hint_rows[0].source_lineage_status == "accepted_source"
    assert result.hint_rows[0].handoff_target == "intersection-source-stage:drainage:policy-drainage-main"
    assert result.hint_rows[0].source_status == "accepted"
    assert any(row.hint_kind == "inlet_recommendation" and row.recommended_element_kind == "inlet" for row in result.hint_rows)


def test_intersection_drainage_hint_evaluation_warns_without_drainage_policy() -> None:
    service = IntersectionEvaluationService()
    model = _sample_intersection_model()
    model = IntersectionModel(
        schema_version=model.schema_version,
        project_id=model.project_id,
        intersection_model_id=model.intersection_model_id,
        intersection_rows=model.intersection_rows,
        control_area_rows=model.control_area_rows,
        arm_policy_rows=model.arm_policy_rows,
        curb_return_policy_rows=model.curb_return_policy_rows,
        edge_policy_rows=model.edge_policy_rows,
        grading_policy_rows=model.grading_policy_rows,
        drainage_policy_rows=[],
    )
    result = service.evaluate_drainage_hints(model)

    assert result.status == "warning"
    assert result.hint_row_count == 6
    assert result.accepted_handoff_count == 0
    assert result.hint_only_count == 6
    assert result.review_required_count == 6
    assert result.ready_hint_count == 0
    assert result.warning_hint_count == 6
    assert "warning:intersection_drainage_policy_missing" in result.diagnostic_rows
    assert result.hint_rows[0].drainage_handoff_status == "hint_only"
    assert result.hint_rows[0].drainage_source_scope == "hint"
    assert result.hint_rows[0].drainage_review_status == "review_required"
    assert result.hint_rows[0].source_lineage_status == "hint_only"
    assert result.hint_rows[0].handoff_target == "intersection-source-stage:drainage:intersection-t-01"
    assert result.hint_rows[0].source_status == "warning"
    assert "source_drainage_policy_missing" in result.hint_rows[0].source_diagnostic_rows
    assert any("drainage_policy_missing" in row.diagnostic_rows[0] for row in result.hint_rows if row.diagnostic_rows)


def test_intersection_surface_zone_evaluation_stops_when_edge_network_has_errors() -> None:
    service = IntersectionEvaluationService()
    model = IntersectionModel(schema_version=1, project_id="project:demo", intersection_model_id="intersection-model:main")
    edge_network = service.evaluate_edge_network(model)
    result = service.evaluate_surface_zones(model, edge_network)

    assert edge_network.status == "error"
    assert result.status == "error"
    assert result.zone_count == 0
    assert "error:intersection_row_not_found" in result.diagnostic_rows
