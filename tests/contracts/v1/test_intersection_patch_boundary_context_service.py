from __future__ import annotations

from types import SimpleNamespace

import pytest

from freecad.Corridor_Road.v1.models.result import (
    IntersectionPatchBoundaryContextResult,
)
from freecad.Corridor_Road.v1.services.builders import (
    IntersectionPatchBoundaryContextRequest,
    IntersectionPatchBoundaryContextService,
)


def _request():
    return IntersectionPatchBoundaryContextRequest(
        applied_section_set=SimpleNamespace(applied_section_set_id="sections:test"),
        prerequisite=SimpleNamespace(intersection_id="intersection:test"),
        intersection_model=SimpleNamespace(intersection_model_id="intersections:test"),
    )


def _evaluators(*, fail_stage: str = "", calls: list | None = None):
    records = calls if calls is not None else []
    results = {
        "tie_in_edges": SimpleNamespace(result_id="tie-in:test"),
        "boundary_segments": SimpleNamespace(result_id="segments:test"),
        "ordered_patch_boundary": SimpleNamespace(result_id="patch:test"),
        "authoritative_boundary_loops": SimpleNamespace(result_id="loops:test"),
        "shared_breaklines": SimpleNamespace(result_id="breaklines:test"),
    }

    def finish(stage, args, kwargs):
        records.append((stage, args, kwargs))
        if fail_stage == stage:
            raise RuntimeError(f"{stage} exploded")
        return results[stage]

    def tie_in(*args, **kwargs):
        return finish("tie_in_edges", args, kwargs)

    def segments(*args, **kwargs):
        return finish("boundary_segments", args, kwargs)

    def patch(*args, **kwargs):
        return finish("ordered_patch_boundary", args, kwargs)

    def loops(*args, **kwargs):
        kwargs["diagnostics"].append("loop-review-note")
        return finish("authoritative_boundary_loops", args, kwargs)

    def shared(*args, **kwargs):
        return finish("shared_breaklines", args, kwargs)

    return (
        {
            "tie_in_evaluator": tie_in,
            "boundary_segment_evaluator": segments,
            "patch_boundary_evaluator": patch,
            "boundary_loop_evaluator": loops,
            "shared_breakline_evaluator": shared,
        },
        results,
    )


def test_boundary_context_runs_ordered_chain_with_exact_inputs() -> None:
    calls = []
    evaluators, results = _evaluators(calls=calls)
    request = _request()

    result = IntersectionPatchBoundaryContextService(**evaluators).evaluate(request)

    assert isinstance(result, IntersectionPatchBoundaryContextResult)
    assert result.status == "ready"
    assert result.intersection_id == "intersection:test"
    assert result.tie_in_result is results["tie_in_edges"]
    assert result.boundary_segment_result is results["boundary_segments"]
    assert result.patch_boundary_result is results["ordered_patch_boundary"]
    assert result.boundary_loop_result is results["authoritative_boundary_loops"]
    assert result.shared_breakline_result is results["shared_breaklines"]
    assert result.completed_stages == (
        "tie_in_edges",
        "boundary_segments",
        "ordered_patch_boundary",
        "authoritative_boundary_loops",
        "shared_breaklines",
    )
    assert result.boundary_evaluation_failed is False
    assert result.boundary_loop_diagnostic_rows == ("loop-review-note",)
    assert result.diagnostic_rows == ("loop-review-note",)
    assert [row[0] for row in calls] == list(result.completed_stages)
    assert calls[0][1] == (request.applied_section_set,)
    assert calls[0][2] == {
        "prerequisite": request.prerequisite,
        "intersection_model": request.intersection_model,
    }
    assert calls[1][1] == (results["tie_in_edges"],)
    assert calls[2][1] == (results["boundary_segments"],)
    assert calls[3][1] == (request.applied_section_set,)
    assert calls[4][2]["patch_boundary_result"] is results[
        "ordered_patch_boundary"
    ]
    assert calls[4][2]["boundary_segment_result"] is results[
        "boundary_segments"
    ]
    assert calls[4][2]["boundary_loop_result"] is results[
        "authoritative_boundary_loops"
    ]


@pytest.mark.parametrize(
    ("failed_stage", "completed_stages"),
    [
        ("tie_in_edges", ()),
        ("boundary_segments", ("tie_in_edges",)),
        (
            "ordered_patch_boundary",
            ("tie_in_edges", "boundary_segments"),
        ),
        (
            "authoritative_boundary_loops",
            ("tie_in_edges", "boundary_segments", "ordered_patch_boundary"),
        ),
        (
            "shared_breaklines",
            (
                "tie_in_edges",
                "boundary_segments",
                "ordered_patch_boundary",
                "authoritative_boundary_loops",
            ),
        ),
    ],
)
def test_boundary_context_preserves_partial_results_and_failed_stage(
    failed_stage,
    completed_stages,
) -> None:
    evaluators, results = _evaluators(fail_stage=failed_stage)

    result = IntersectionPatchBoundaryContextService(**evaluators).evaluate(
        _request()
    )

    assert result.status == "error"
    assert result.failed_stage == failed_stage
    assert result.completed_stages == completed_stages
    assert result.boundary_evaluation_failed is True
    assert result.error_message == f"{failed_stage} exploded"
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_context_failed:"
        f"{failed_stage}:RuntimeError:{failed_stage} exploded",
    )
    result_by_stage = {
        "tie_in_edges": result.tie_in_result,
        "boundary_segments": result.boundary_segment_result,
        "ordered_patch_boundary": result.patch_boundary_result,
        "authoritative_boundary_loops": result.boundary_loop_result,
        "shared_breaklines": result.shared_breakline_result,
    }
    for stage in completed_stages:
        assert result_by_stage[stage] is results[stage]
    assert result_by_stage[failed_stage] is None
    if failed_stage == "shared_breaklines":
        assert result.boundary_loop_diagnostic_rows == ("loop-review-note",)


def test_boundary_context_reports_all_missing_evaluators() -> None:
    result = IntersectionPatchBoundaryContextService().evaluate(_request())

    assert result.status == "unsupported"
    assert result.failed_stage == "tie_in_edges"
    assert result.boundary_evaluation_failed is True
    assert result.completed_stages == ()
    assert result.diagnostic_rows == (
        "intersection_patch_boundary_context_evaluator_missing:"
        "tie_in_edges,boundary_segments,ordered_patch_boundary,"
        "authoritative_boundary_loops,shared_breaklines",
    )
    assert "tie_in_edges" in result.error_message
    assert "shared_breaklines" in result.error_message
