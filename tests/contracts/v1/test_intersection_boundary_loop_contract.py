"""Contract tests for source-driven intersection boundary loops."""

from __future__ import annotations

from freecad.Corridor_Road.v1.models.source.intersection_model import IntersectionModel
from freecad.Corridor_Road.v1.models.result.intersection_edge_network import (
    IntersectionEdgeNetworkResult,
    IntersectionEdgeNetworkRow,
)
from freecad.Corridor_Road.v1.models.result.intersection_surface_zone import (
    IntersectionSurfaceZoneResult,
    IntersectionSurfaceZoneRow,
)
from freecad.Corridor_Road.v1.models.result.intersection_slope_face_loop import (
    IntersectionSlopeFaceLoopResult,
    IntersectionSlopeFaceLoopRow,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import IntersectionEvaluationService


def _edge(
    edge_id: str,
    start,
    end,
    role: str = "boundary",
    family: str = "leg_edge",
    leg_ref: str = "leg:main",
    arc_points=(),
):
    return IntersectionEdgeNetworkRow(
        edge_id=edge_id,
        intersection_id="starter-t_intersection",
        edge_role=role,
        edge_family=family,
        source_policy_ref=f"source-policy:{edge_id}",
        leg_ref=leg_ref,
        control_area_ref="control:main",
        start_xyz=start,
        end_xyz=end,
        arc_points_xyz=tuple(arc_points or ()),
        source_status="accepted",
        status="ready",
    )


def _manual_edge_network() -> IntersectionEdgeNetworkResult:
    edges = [
        _edge("e:bottom", (0.0, 0.0, 0.0), (4.0, 0.0, 0.0)),
        _edge("e:right", (4.0, 0.0, 0.0), (4.0, 3.0, 0.0)),
        _edge("e:top", (4.0, 3.0, 0.0), (0.0, 3.0, 0.0)),
        _edge("e:left", (0.0, 3.0, 0.0), (0.0, 0.0, 0.0)),
        _edge("e:internal", (1.0, 1.0, 0.0), (3.0, 2.0, 0.0), role="internal"),
        _edge("e:shortcut", (0.0, 0.0, 0.0), (4.0, 3.0, 0.0), role="boundary_shortcut"),
    ]
    return IntersectionEdgeNetworkResult(
        schema_version=1,
        project_id="project:test",
        edge_network_result_id="intersection-edge-network:test",
        intersection_id="starter-t_intersection",
        intersection_kind="t_intersection",
        status="ready",
        edge_count=len(edges),
        edge_rows=edges,
    )


def _manual_surface_zones() -> IntersectionSurfaceZoneResult:
    return IntersectionSurfaceZoneResult(
        schema_version=1,
        project_id="project:test",
        surface_zone_result_id="intersection-surface-zones:test",
        intersection_id="starter-t_intersection",
        intersection_kind="t_intersection",
        status="ready",
        zone_count=1,
        zone_rows=[
            IntersectionSurfaceZoneRow(
                zone_id="zone:outer",
                intersection_id="starter-t_intersection",
                zone_role="outer_boundary",
                zone_family="boundary",
                surface_role="design",
                boundary_edge_refs=("e:bottom", "e:right", "e:top", "e:left", "e:internal", "e:shortcut"),
                source_edge_refs=("e:bottom", "e:right", "e:top", "e:left", "e:internal", "e:shortcut"),
                status="ready",
            )
        ],
    )


def test_intersection_boundary_loop_contract_builds_closed_outer_loop_from_result_edges():
    service = IntersectionEvaluationService()
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        surface_zone_result=_manual_surface_zones(),
        edge_network_result=_manual_edge_network(),
    )

    assert result.status in {"ready", "warning"}
    assert result.loop_count == 1
    assert result.ready_count == 1
    assert result.segment_count >= 4
    loop = result.loop_rows[0]
    assert loop.loop_role == "outer_intersection_boundary"
    assert loop.closed is True
    assert loop.point_count >= 4
    assert loop.area_xy > 0.0
    assert loop.loop_points_xyz[0] == loop.loop_points_xyz[-1]
    assert "intersection_surface" in loop.consumer_roles
    assert "intersection_slope_face_surface" in loop.consumer_roles
    assert "design_surface" in loop.consumer_roles
    assert "slope_face_surface" in loop.consumer_roles
    assert all(row.shared_breakline_ref for row in result.segment_rows)
    assert all(row.graph_edge_ref for row in result.segment_rows)
    assert any(
        "intersection_slope_face_surface" in row.expected_consumers
        for row in result.segment_rows
    )
    assert any("candidate_segments_excluded:shortcut:1" in row for row in result.diagnostic_rows)
    assert any("intersection_boundary_candidate_graph:" in row for row in result.diagnostic_rows)
    assert not any("e:shortcut" in row.source_refs for row in result.segment_rows)


def test_intersection_boundary_loop_contract_reports_missing_points():
    service = IntersectionEvaluationService()
    edge_network = IntersectionEdgeNetworkResult(
        schema_version=1,
        project_id="project:test",
        edge_network_result_id="intersection-edge-network:broken",
        intersection_id="starter-t_intersection",
        intersection_kind="t_intersection",
        status="warning",
        edge_rows=[
            _edge("e:only", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        ],
    )
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=edge_network,
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
    )

    assert result.status == "error"
    assert "error:intersection_boundary_loop_point_count_too_low" in result.diagnostic_rows


def test_intersection_boundary_loop_contract_does_not_accept_convex_hull_fallback():
    service = IntersectionEvaluationService()
    slope_loops = IntersectionSlopeFaceLoopResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="starter-t_intersection",
        status="ready",
        loop_rows=[
            IntersectionSlopeFaceLoopRow(
                loop_id="slope-loop:test",
                intersection_id="starter-t_intersection",
                loop_family="diagnostic_fallback",
                status="ready",
                loop_points_xyz=(
                    (0.0, 0.0, 0.0),
                    (4.0, 0.0, 0.0),
                    (2.0, 2.0, 0.0),
                    (0.0, 0.0, 0.0),
                ),
                source_surface_zone_refs=("zone:slope",),
            )
        ],
    )
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:disconnected",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
            edge_rows=[
                _edge("e:a", (0.0, 0.0, 0.0), (4.0, 0.0, 0.0)),
                _edge("e:b", (5.0, 0.0, 0.0), (6.0, 2.0, 0.0)),
                _edge("e:c", (2.0, 3.0, 0.0), (0.0, 1.0, 0.0)),
            ],
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
        slope_face_loop_result=slope_loops,
    )

    assert result.status == "warning"
    assert result.ready_count == 0
    assert result.loop_rows[0].status == "warning"
    assert result.loop_rows[0].source_status == "fallback_warning"
    assert "warning:intersection_boundary_convex_hull_fallback" in result.diagnostic_rows
    assert "warning:intersection_boundary_convex_hull_fallback" in result.loop_rows[0].diagnostics


def test_intersection_boundary_loop_contract_ignores_slope_face_loop_as_outer_source():
    service = IntersectionEvaluationService()
    slope_loops = IntersectionSlopeFaceLoopResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="starter-t_intersection",
        status="ready",
        loop_rows=[
            IntersectionSlopeFaceLoopRow(
                loop_id="slope-loop:outer",
                intersection_id="starter-t_intersection",
                loop_family="source_boundary",
                status="ready",
                closed_xy=True,
                loop_points_xyz=(
                    (0.0, 0.0, 0.0),
                    (4.0, 0.0, 0.0),
                    (4.0, 3.0, 0.0),
                    (0.0, 3.0, 0.0),
                    (0.0, 0.0, 0.0),
                ),
                source_applied_section_refs=("section:a",),
                source_surface_zone_refs=("zone:slope",),
            )
        ],
    )
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:empty",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
            edge_rows=[],
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
        slope_face_loop_result=slope_loops,
    )

    assert result.status == "error"
    assert result.ready_count == 0
    assert result.segment_count == 0
    assert result.loop_rows == []
    assert "error:intersection_boundary_loop_point_count_too_low" in result.diagnostic_rows
    assert any("slope_face_candidates_ignored" in row for row in result.diagnostic_rows)
    assert any("reason=slope_face_loop_is_consumer_not_outer_boundary_source" in row for row in result.diagnostic_rows)
    assert not any("convex_hull_fallback" in row for row in result.diagnostic_rows)


def test_intersection_boundary_loop_contract_builds_t_source_perimeter_from_edge_envelopes():
    service = IntersectionEvaluationService()
    edges = [
        _edge(
            "intersection-edge:starter-t:leg-01:pavement",
            (-24.0, 4.5, 0.0),
            (24.0, 4.5, 0.0),
            role="pavement_edge",
            leg_ref="leg:01",
        ),
        _edge(
            "intersection-edge:starter-t:leg-01:daylight",
            (-24.0, 9.0, 0.0),
            (24.0, 9.0, 0.0),
            role="daylight_hinge",
            leg_ref="leg:01",
        ),
        _edge(
            "intersection-edge:starter-t:leg-02:pavement",
            (-4.5, -35.0, 0.0),
            (-4.5, 0.0, 0.0),
            role="pavement_edge",
            leg_ref="leg:02",
        ),
        _edge(
            "intersection-edge:starter-t:leg-02:daylight",
            (-9.0, -35.0, 0.0),
            (-9.0, 0.0, 0.0),
            role="daylight_hinge",
            leg_ref="leg:02",
        ),
        _edge(
            "intersection-edge:starter-t:curb-return:01",
            (-12.0, 0.0, 0.0),
            (0.0, 12.0, 0.0),
            role="curb_return",
            family="curb_return",
            arc_points=((-12.0, 0.0, 0.0), (-6.0, 2.5, 0.0), (-2.5, 6.0, 0.0), (0.0, 12.0, 0.0)),
        ),
    ]
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:t-source",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="ready",
            edge_rows=edges,
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
    )

    assert result.status in {"ready", "warning"}
    assert result.ready_count == 1
    assert result.loop_rows[0].source_status == "accepted"
    assert result.loop_rows[0].bbox_xy == (-24.0, -35.0, 24.0, 12.0)
    assert result.loop_rows[0].area_xy < (48.0 * 47.0)
    assert any("curb_arc_span_candidates" in row for row in result.diagnostic_rows)
    assert any("curb_arc_bridge_required" in row for row in result.diagnostic_rows)
    assert any("curb_arc_bridge_promotion_blocked" in row for row in result.diagnostic_rows)
    assert any("curb_arc_pure_span_missing" in row for row in result.diagnostic_rows)
    assert any("curb_arc_span_mixed_ownership" in row for row in result.diagnostic_rows)
    assert not any("curb_arc_replacement_bbox_changed" in row for row in result.diagnostic_rows)
    assert any("rectilinear_edge_network_envelope" in row for row in result.diagnostic_rows)
    assert not any("convex_hull_fallback" in row for row in result.diagnostic_rows)
    owner_refs = {
        ref
        for row in result.segment_rows
        for ref in row.source_refs
        if str(ref).startswith("intersection-boundary-owner:")
    }
    assert "intersection-boundary-owner:leg:01:north" in owner_refs
    assert "intersection-boundary-owner:leg:01:south" in owner_refs
    assert "intersection-boundary-owner:leg:02:south" in owner_refs
    side_tie_rows = [row for row in result.segment_rows if row.segment_role == "side_road_tie"]
    assert side_tie_rows
    assert any("intersection-boundary-owner:leg:02:south" in row.source_refs for row in side_tie_rows)


def test_intersection_boundary_loop_contract_does_not_let_slope_loop_override_source_perimeter():
    service = IntersectionEvaluationService()
    edges = [
        _edge(
            "intersection-edge:starter-t:leg-01:pavement",
            (-24.0, 4.5, 0.0),
            (24.0, 4.5, 0.0),
            role="pavement_edge",
            leg_ref="leg:01",
        ),
        _edge(
            "intersection-edge:starter-t:leg-01:daylight",
            (-24.0, 9.0, 0.0),
            (24.0, 9.0, 0.0),
            role="daylight_hinge",
            leg_ref="leg:01",
        ),
        _edge(
            "intersection-edge:starter-t:leg-02:pavement",
            (-4.5, -35.0, 0.0),
            (-4.5, 0.0, 0.0),
            role="pavement_edge",
            leg_ref="leg:02",
        ),
        _edge(
            "intersection-edge:starter-t:leg-02:daylight",
            (-9.0, -35.0, 0.0),
            (-9.0, 0.0, 0.0),
            role="daylight_hinge",
            leg_ref="leg:02",
        ),
    ]
    remote_slope_loop = IntersectionSlopeFaceLoopResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="starter-t_intersection",
        status="ready",
        loop_rows=[
            IntersectionSlopeFaceLoopRow(
                loop_id="slope-loop:remote-alignment-side",
                intersection_id="starter-t_intersection",
                loop_family="source_boundary",
                status="ready",
                closed_xy=True,
                loop_points_xyz=(
                    (100.0, 100.0, 0.0),
                    (110.0, 100.0, 0.0),
                    (110.0, 106.0, 0.0),
                    (100.0, 106.0, 0.0),
                    (100.0, 100.0, 0.0),
                ),
                source_applied_section_refs=("section:remote",),
            )
        ],
    )
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:t-source",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="ready",
            edge_rows=edges,
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
        slope_face_loop_result=remote_slope_loop,
    )

    assert result.loop_count == 1
    assert result.loop_rows[0].bbox_xy == (-24.0, -35.0, 24.0, 9.0)
    assert not any("section:remote" in row.source_refs for row in result.segment_rows)
    assert any("slope_face_candidates_ignored" in row for row in result.diagnostic_rows)


def test_intersection_boundary_loop_contract_rejects_defaulted_edge_network_as_source():
    service = IntersectionEvaluationService()
    warning_edges = [
        IntersectionEdgeNetworkRow(
            edge_id=f"edge:defaulted:{index}",
            intersection_id="starter-t_intersection",
            edge_role="pavement_edge",
            edge_family="leg_edge",
            source_policy_ref=f"edge-policy:defaulted:{index}",
            start_xyz=start,
            end_xyz=end,
            source_status="warning",
            source_diagnostic_rows=(
                "edge_family_subassembly_defaulted",
                "source_edge_family_approval_pending",
                "preset_edge_family_review_required",
            ),
            status="warning",
        )
        for index, (start, end) in enumerate(
            (
                ((0.0, 0.0, 0.0), (4.0, 0.0, 0.0)),
                ((4.0, 0.0, 0.0), (4.0, 3.0, 0.0)),
                ((4.0, 3.0, 0.0), (0.0, 3.0, 0.0)),
                ((0.0, 3.0, 0.0), (0.0, 0.0, 0.0)),
            ),
            start=1,
        )
    ]
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:defaulted",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
            edge_rows=warning_edges,
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
    )

    assert result.status == "error"
    assert result.ready_count == 0
    assert result.loop_rows == []
    assert "error:intersection_boundary_authoritative_source_edges_missing" in result.diagnostic_rows
    assert any("candidate_edges_excluded:source_status_warning:4" in row for row in result.diagnostic_rows)


def test_intersection_boundary_loop_contract_consumes_curb_return_arc_points_as_segments():
    service = IntersectionEvaluationService()
    edges = [
        _edge(
            "intersection-edge:arc:curb-return",
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            role="curb_return_edge",
            family="curb_return",
            arc_points=((0.0, 0.0, 0.0), (0.5, 0.2, 0.0), (1.0, 1.0, 0.0)),
        ),
        _edge("intersection-edge:arc:top", (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
        _edge("intersection-edge:arc:left", (0.0, 1.0, 0.0), (0.0, 0.0, 0.0)),
    ]
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:arc-source",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="ready",
            edge_rows=edges,
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
    )

    assert result.status in {"ready", "warning"}
    assert result.ready_count == 1
    assert result.loop_rows[0].status == "ready"
    assert result.loop_rows[0].point_count == 4
    assert result.segment_count == 4
    assert any((0.5, 0.2, 0.0) == point for point in result.loop_rows[0].loop_points_xyz)
    arc_segments = [
        row
        for row in result.segment_rows
        if "intersection-edge:arc:curb-return" in row.source_refs
    ]
    assert len(arc_segments) == 2
    assert all(row.segment_role == "curb_return_to_intersection_slope_face" for row in arc_segments)
    assert any("curb_return_arc_segments" in row for row in result.diagnostic_rows)
    assert not any("convex_hull_fallback" in row for row in result.diagnostic_rows)


def test_intersection_boundary_loop_contract_builds_leg_frame_source_perimeter_for_skew_edges():
    service = IntersectionEvaluationService()
    edges = [
        _edge(
            "intersection-edge:skew:leg-01:pavement",
            (-10.0, -1.0, 0.0),
            (10.0, 1.0, 0.0),
            role="pavement_edge",
            leg_ref="leg:01",
        ),
        _edge(
            "intersection-edge:skew:leg-01:daylight",
            (-10.0, 1.0, 0.0),
            (10.0, 3.0, 0.0),
            role="daylight_hinge",
            leg_ref="leg:01",
        ),
        _edge(
            "intersection-edge:skew:leg-02:pavement",
            (-1.0, -10.0, 0.0),
            (1.0, 10.0, 0.0),
            role="pavement_edge",
            leg_ref="leg:02",
        ),
        _edge(
            "intersection-edge:skew:leg-02:daylight",
            (-3.0, -10.0, 0.0),
            (-1.0, 10.0, 0.0),
            role="daylight_hinge",
            leg_ref="leg:02",
        ),
    ]
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:skew-source",
            intersection_id="starter-t_intersection",
            intersection_kind="skewed_intersection",
            status="ready",
            edge_rows=edges,
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="skewed_intersection",
            status="warning",
        ),
    )

    assert result.status in {"ready", "warning"}
    assert result.ready_count == 1
    assert result.loop_rows[0].status == "ready"
    assert result.loop_rows[0].source_status == "accepted"
    assert result.loop_rows[0].area_xy > 0.0
    assert any("leg_frame_source_polygon_envelope" in row for row in result.diagnostic_rows)
    assert not any("convex_hull_fallback" in row for row in result.diagnostic_rows)


def test_intersection_boundary_loop_contract_rejects_competing_slope_face_loop_components():
    service = IntersectionEvaluationService()
    slope_loops = IntersectionSlopeFaceLoopResult(
        schema_version=1,
        project_id="project:test",
        intersection_id="starter-t_intersection",
        status="ready",
        loop_rows=[
            IntersectionSlopeFaceLoopRow(
                loop_id="slope-loop:left-strip",
                intersection_id="starter-t_intersection",
                loop_family="source_boundary",
                status="ready",
                closed_xy=True,
                loop_points_xyz=(
                    (0.0, 0.0, 0.0),
                    (4.0, 0.0, 0.0),
                    (4.0, 1.0, 0.0),
                    (0.0, 1.0, 0.0),
                    (0.0, 0.0, 0.0),
                ),
                source_applied_section_refs=("section:left",),
            ),
            IntersectionSlopeFaceLoopRow(
                loop_id="slope-loop:right-strip",
                intersection_id="starter-t_intersection",
                loop_family="source_boundary",
                status="ready",
                closed_xy=True,
                loop_points_xyz=(
                    (6.0, 0.0, 0.0),
                    (10.0, 0.0, 0.0),
                    (10.0, 1.0, 0.0),
                    (6.0, 1.0, 0.0),
                    (6.0, 0.0, 0.0),
                ),
                source_applied_section_refs=("section:right",),
            ),
        ],
    )
    result = service.evaluate_boundary_loops(
        IntersectionModel(schema_version=1, project_id="project:test"),
        edge_network_result=IntersectionEdgeNetworkResult(
            schema_version=1,
            project_id="project:test",
            edge_network_result_id="intersection-edge-network:empty",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
            edge_rows=[],
        ),
        surface_zone_result=IntersectionSurfaceZoneResult(
            schema_version=1,
            project_id="project:test",
            intersection_id="starter-t_intersection",
            intersection_kind="t_intersection",
            status="warning",
        ),
        slope_face_loop_result=slope_loops,
    )

    assert result.status == "error"
    assert result.ready_count == 0
    assert result.loop_rows == []
    assert "error:intersection_boundary_loop_point_count_too_low" in result.diagnostic_rows
    assert any("slope_face_candidates_ignored" in row for row in result.diagnostic_rows)
    assert not any("intersection_boundary_multiple_closed_components" in row for row in result.diagnostic_rows)
    assert not any("convex_hull_fallback" in row for row in result.diagnostic_rows)


def run():
    test_intersection_boundary_loop_contract_builds_closed_outer_loop_from_result_edges()
    test_intersection_boundary_loop_contract_reports_missing_points()
    test_intersection_boundary_loop_contract_does_not_accept_convex_hull_fallback()
    test_intersection_boundary_loop_contract_ignores_slope_face_loop_as_outer_source()
    test_intersection_boundary_loop_contract_builds_t_source_perimeter_from_edge_envelopes()
    test_intersection_boundary_loop_contract_does_not_let_slope_loop_override_source_perimeter()
    test_intersection_boundary_loop_contract_rejects_defaulted_edge_network_as_source()
    test_intersection_boundary_loop_contract_consumes_curb_return_arc_points_as_segments()
    test_intersection_boundary_loop_contract_builds_leg_frame_source_perimeter_for_skew_edges()
    test_intersection_boundary_loop_contract_rejects_competing_slope_face_loop_components()
    print("[PASS] intersection boundary loop contract tests")


if __name__ == "__main__":
    run()
