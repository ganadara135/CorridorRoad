"""Orchestrate non-roundabout Intersection patch boundary result evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ...models.result.intersection_patch_boundary_context import (
    IntersectionPatchBoundaryContextResult,
)


ContextEvaluator = Callable[..., object]


@dataclass(frozen=True)
class IntersectionPatchBoundaryContextRequest:
    applied_section_set: object
    prerequisite: object
    intersection_model: object | None = None


class IntersectionPatchBoundaryContextService:
    """Run the ordered boundary-result chain and retain partial failures."""

    def __init__(
        self,
        *,
        tie_in_evaluator: ContextEvaluator | None = None,
        boundary_segment_evaluator: ContextEvaluator | None = None,
        patch_boundary_evaluator: ContextEvaluator | None = None,
        boundary_loop_evaluator: ContextEvaluator | None = None,
        shared_breakline_evaluator: ContextEvaluator | None = None,
    ) -> None:
        self.tie_in_evaluator = tie_in_evaluator
        self.boundary_segment_evaluator = boundary_segment_evaluator
        self.patch_boundary_evaluator = patch_boundary_evaluator
        self.boundary_loop_evaluator = boundary_loop_evaluator
        self.shared_breakline_evaluator = shared_breakline_evaluator

    def evaluate(
        self,
        request: IntersectionPatchBoundaryContextRequest,
    ) -> IntersectionPatchBoundaryContextResult:
        intersection_id = str(
            getattr(request.prerequisite, "intersection_id", "") or ""
        )
        missing = self._missing_evaluators()
        if missing:
            message = (
                "Intersection patch boundary context evaluator is not configured: "
                + ", ".join(missing)
            )
            return IntersectionPatchBoundaryContextResult(
                status="unsupported",
                intersection_id=intersection_id,
                failed_stage=missing[0],
                boundary_evaluation_failed=True,
                diagnostic_rows=(
                    "intersection_patch_boundary_context_evaluator_missing:"
                    + ",".join(missing),
                ),
                error_message=message,
            )
        completed = []
        loop_diagnostics: list[str] = []
        tie_in_result = None
        boundary_segment_result = None
        patch_boundary_result = None
        boundary_loop_result = None
        shared_breakline_result = None
        stage = "tie_in_edges"
        try:
            tie_in_result = self.tie_in_evaluator(
                request.applied_section_set,
                prerequisite=request.prerequisite,
                intersection_model=request.intersection_model,
            )
            completed.append(stage)
            stage = "boundary_segments"
            boundary_segment_result = self.boundary_segment_evaluator(
                tie_in_result,
                intersection_model=request.intersection_model,
            )
            completed.append(stage)
            stage = "ordered_patch_boundary"
            patch_boundary_result = self.patch_boundary_evaluator(
                boundary_segment_result
            )
            completed.append(stage)
            stage = "authoritative_boundary_loops"
            boundary_loop_result = self.boundary_loop_evaluator(
                request.applied_section_set,
                prerequisite=request.prerequisite,
                intersection_model=request.intersection_model,
                diagnostics=loop_diagnostics,
            )
            completed.append(stage)
            stage = "shared_breaklines"
            shared_breakline_result = self.shared_breakline_evaluator(
                request.applied_section_set,
                prerequisite=request.prerequisite,
                intersection_model=request.intersection_model,
                patch_boundary_result=patch_boundary_result,
                boundary_segment_result=boundary_segment_result,
                boundary_loop_result=boundary_loop_result,
            )
            completed.append(stage)
        except Exception as exc:
            diagnostic = (
                f"intersection_patch_boundary_context_failed:{stage}:"
                f"{type(exc).__name__}:{exc}"
            )
            return IntersectionPatchBoundaryContextResult(
                status="error",
                intersection_id=intersection_id,
                tie_in_result=tie_in_result,
                boundary_segment_result=boundary_segment_result,
                patch_boundary_result=patch_boundary_result,
                boundary_loop_result=boundary_loop_result,
                shared_breakline_result=shared_breakline_result,
                completed_stages=tuple(completed),
                failed_stage=stage,
                boundary_evaluation_failed=True,
                boundary_loop_diagnostic_rows=tuple(loop_diagnostics),
                diagnostic_rows=(diagnostic,),
                error_message=str(exc),
            )
        return IntersectionPatchBoundaryContextResult(
            status="ready",
            intersection_id=intersection_id,
            tie_in_result=tie_in_result,
            boundary_segment_result=boundary_segment_result,
            patch_boundary_result=patch_boundary_result,
            boundary_loop_result=boundary_loop_result,
            shared_breakline_result=shared_breakline_result,
            completed_stages=tuple(completed),
            boundary_loop_diagnostic_rows=tuple(loop_diagnostics),
            diagnostic_rows=tuple(loop_diagnostics),
        )

    def _missing_evaluators(self) -> list[str]:
        return [
            name
            for name, evaluator in (
                ("tie_in_edges", self.tie_in_evaluator),
                ("boundary_segments", self.boundary_segment_evaluator),
                ("ordered_patch_boundary", self.patch_boundary_evaluator),
                ("authoritative_boundary_loops", self.boundary_loop_evaluator),
                ("shared_breaklines", self.shared_breakline_evaluator),
            )
            if evaluator is None
        ]
