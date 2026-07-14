from __future__ import annotations

from types import SimpleNamespace

from freecad.Corridor_Road.v1.models.result import (
    IntersectionSharedBreaklineContributionResult,
)
from freecad.Corridor_Road.v1.models.result.shared_breakline import (
    SharedBreaklineRow,
)
from freecad.Corridor_Road.v1.services.evaluation import (
    IntersectionSharedBreaklineAssemblyRequest,
    IntersectionSharedBreaklineContributionRequest,
    IntersectionSharedBreaklineService,
)


def _boundary_loop_result():
    return SimpleNamespace(
        boundary_loop_result_id="boundary-loops:test",
        loop_rows=(
            SimpleNamespace(
                loop_role="outer_intersection_boundary",
                status="ready",
                closed=True,
                segment_refs=("segment:1",),
            ),
        ),
        segment_rows=(
            SimpleNamespace(
                segment_id="segment:1",
                intersection_id="intersection:test",
                segment_role="curb_return_envelope_arc",
                from_xyz=(0.0, 0.0, 10.0),
                to_xyz=(5.0, 0.0, 10.0),
                from_point_ref="source:p1",
                to_point_ref="source:p2",
                loop_ref="loop:outer",
                source_refs=("zone:test",),
                shared_breakline_ref="shared:segment:1",
                source_status="accepted",
                diagnostics=(),
            ),
        ),
    )


def _request(*, contributors):
    boundary = SimpleNamespace(
        boundary_segment_result_id="boundary-segments:test",
        segment_rows=(
            SimpleNamespace(
                boundary_segment_id="tie:primary:left",
                segment_kind="tie_in",
                segment_role="pavement_edge",
                alignment_ref="alignment:primary",
                side="left",
                start_xyz=(0.0, 0.0, 10.0),
                end_xyz=(10.0, 0.0, 10.0),
                status="candidate",
            ),
        ),
    )
    patch = SimpleNamespace(
        patch_boundary_result_id="patch:test",
        status="ready",
        diagnostic_rows=(),
        point_rows=(),
    )
    model = SimpleNamespace(
        intersection_rows=(
            SimpleNamespace(
                intersection_id="intersection:test",
                primary_alignment_ref="alignment:primary",
            ),
        )
    )
    return IntersectionSharedBreaklineContributionRequest(
        result_id="shared-breakline:intersection:intersection:test",
        intersection_id="intersection:test",
        boundary_loop_result=_boundary_loop_result(),
        patch_boundary_result=patch,
        boundary_segment_result=boundary,
        intersection_model=model,
        boundary_loop_ready=True,
        contributor_names=contributors,
    )


def test_boundary_loop_contributor_preserves_identity_sources_and_consumers() -> None:
    result = IntersectionSharedBreaklineService().evaluate_core(
        _request(contributors=("boundary_loops",))
    )

    assert isinstance(result, IntersectionSharedBreaklineContributionResult)
    assert result.status == "ready"
    assert result.completed_contributors == ("boundary_loops",)
    assert len(result.breakline_rows) == 1
    row = result.breakline_rows[0]
    assert row.breakline_id == "shared:segment:1"
    assert row.breakline_role == "curb_return_to_intersection_slope_face"
    assert row.source_contract_refs == (
        "boundary-loops:test",
        "loop:outer",
        "segment:1",
        "zone:test",
    )
    assert row.consumer_refs == (
        "intersection_surface",
        "intersection_slope_face_surface",
    )
    assert row.source_status == "accepted"
    assert row.point_refs == ("shared:segment:1:p1", "shared:segment:1:p2")
    assert [point.source_point_ref for point in result.point_rows] == [
        "source:p1",
        "source:p2",
    ]


def test_patch_contributor_preserves_primary_contact_role_and_traceability() -> None:
    result = IntersectionSharedBreaklineService().evaluate_core(
        _request(contributors=("patch_to_design",))
    )

    assert result.completed_contributors == ("patch_to_design",)
    assert len(result.breakline_rows) == 1
    row = result.breakline_rows[0]
    assert row.breakline_role == "patch_to_design_pavement_tie_in"
    assert row.alignment_ref == "alignment:primary"
    assert row.source_contract_refs == (
        "patch:test",
        "boundary-segments:test",
        "tie:primary:left",
    )
    assert row.consumer_refs == ("intersection_surface", "design_surface")
    assert row.handoff_target == "intersection_patch_to_design"
    assert len(result.point_rows) == 2


def test_boundary_contributor_deduplicates_reversed_segment_geometry() -> None:
    source = _boundary_loop_result()
    duplicate = SimpleNamespace(
        **{
            **vars(source.segment_rows[0]),
            "segment_id": "segment:2",
            "from_xyz": (5.0, 0.0, 10.0),
            "to_xyz": (0.0, 0.0, 10.0),
            "shared_breakline_ref": "shared:segment:2",
        }
    )
    source.loop_rows[0].segment_refs = ("segment:1", "segment:2")
    source.segment_rows = (*source.segment_rows, duplicate)
    request = _request(contributors=("boundary_loops",))
    request = IntersectionSharedBreaklineContributionRequest(
        **{**vars(request), "boundary_loop_result": source}
    )

    result = IntersectionSharedBreaklineService().evaluate_core(request)

    assert len(result.breakline_rows) == 1
    assert len(result.point_rows) == 2


def test_assembly_computes_status_and_counts_from_contributed_rows() -> None:
    rows = (
        SharedBreaklineRow("ready", "intersection", "i", "r", source_status="accepted"),
        SharedBreaklineRow("candidate", "intersection", "i", "c", source_status="candidate"),
        SharedBreaklineRow("error", "intersection", "i", "e", source_status="error"),
    )

    result = IntersectionSharedBreaklineService().assemble(
        IntersectionSharedBreaklineAssemblyRequest(
            project_id="project:test",
            result_id="shared:test",
            intersection_id="intersection:test",
            breakline_rows=rows,
            point_rows=(),
            diagnostic_rows=("test:diagnostic",),
        )
    )

    assert result.status == "warning"
    assert result.breakline_count == 3
    assert result.ready_count == 1
    assert result.warning_count == 1
    assert result.error_count == 1
    assert result.diagnostic_rows == ["test:diagnostic"]


def test_tie_slope_contributor_builds_four_source_owned_edges() -> None:
    tie_row = SimpleNamespace(
        tie_slope_id="tie-slope:test",
        status="ready",
        alignment_ref="alignment:side",
        side="left",
        road_role="side",
        source_intersection_boundary_ref="boundary:test",
        source_slope_face_boundary_ref="slope:test",
        source_applied_section_refs=("section:outer", "section:inner"),
        last_applied_section_refs=(),
        inner_intersection_edge_xyz=((0.0, 0.0, 10.0), (1.0, 0.0, 10.0)),
        outer_applied_section_edge_xyz=((0.0, 4.0, 9.0), (1.0, 4.0, 9.0)),
        start_cap_edge_xyz=((0.0, 0.0, 10.0), (0.0, 4.0, 9.0)),
        end_cap_edge_xyz=((1.0, 0.0, 10.0), (1.0, 4.0, 9.0)),
        inner_breakline_ref="",
        outer_breakline_ref="",
        start_cap_breakline_ref="",
        end_cap_breakline_ref="",
        diagnostics=(),
    )
    request = _request(contributors=("tie_slope",))
    request = IntersectionSharedBreaklineContributionRequest(
        **{
            **vars(request),
            "tie_slope_result": SimpleNamespace(
                tie_slope_result_id="tie-slopes:test",
                tie_slope_rows=(tie_row,),
            ),
        }
    )

    result = IntersectionSharedBreaklineService().evaluate_core(request)

    assert result.status == "ready"
    assert len(result.breakline_rows) == 4
    assert {row.breakline_role for row in result.breakline_rows} == {
        "intersection_tie_slope_transition_inner",
        "intersection_tie_slope_transition_outer",
        "intersection_tie_slope_start_cap",
        "intersection_tie_slope_end_cap",
    }
    assert all(row.source_status == "ready" for row in result.breakline_rows)
    assert len(result.point_rows) == 8
    assert result.diagnostic_rows == (
        "intersection_tie_slope_shared_breaklines:4",
    )


def test_tie_slope_window_contributor_preserves_accepted_window_roles() -> None:
    window = {
        "intersection_id": "intersection:test",
        "intersection_kind": "t_intersection",
        "alignment_ref": "alignment:side",
        "gap_role": "approach",
        "side": "left",
        "cell_role": "transition_pair",
        "ownership_class": "tie_slope_candidate",
        "status": "accepted",
        "diagnostics": (),
        "outer_applied_section_ref": "section:outer",
        "inner_applied_section_ref": "section:inner",
        "source_mode": "applied_section_context_transition_window",
        "outer_station": 80.0,
        "inner_station": 100.0,
        "outer_edge_xyz": ((0.0, 4.0, 9.0), (1.0, 4.0, 9.0)),
        "inner_edge_xyz": ((0.0, 0.0, 10.0), (1.0, 0.0, 10.0)),
        "start_cap_edge_xyz": ((0.0, 4.0, 9.0), (0.0, 0.0, 10.0)),
        "end_cap_edge_xyz": ((1.0, 4.0, 9.0), (1.0, 0.0, 10.0)),
    }
    request = _request(contributors=("tie_slope",))
    request = IntersectionSharedBreaklineContributionRequest(
        **{
            **vars(request),
            "tie_slope_result": SimpleNamespace(
                tie_slope_result_id="tie-slopes:test"
            ),
            "tie_slope_window_rows": (window,),
        }
    )

    result = IntersectionSharedBreaklineService().evaluate_core(request)

    assert len(result.breakline_rows) == 4
    assert {row.breakline_role for row in result.breakline_rows} == {
        "intersection_tie_slope_window_outer",
        "intersection_tie_slope_window_inner",
        "intersection_tie_slope_window_start_cap",
        "intersection_tie_slope_window_end_cap",
    }
    assert all(row.source_status == "accepted" for row in result.breakline_rows)
    assert result.diagnostic_rows == (
        "intersection_tie_slope_window_shared_breaklines:4; "
        "accepted_rows=1; suppressed_rows=0",
    )
