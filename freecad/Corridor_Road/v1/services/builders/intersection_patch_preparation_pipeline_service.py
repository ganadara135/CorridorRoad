"""Prepare and build a typed non-roundabout Intersection surface patch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ...models.result.intersection_patch_preparation_pipeline import (
    IntersectionPatchPreparationPipelineResult,
)
from ..evaluation.intersection_patch_grading_service import (
    IntersectionPatchGradingRequest,
    IntersectionPatchGradingService,
)
from .intersection_patch_boundary_context_service import (
    IntersectionPatchBoundaryContextRequest,
    IntersectionPatchBoundaryContextService,
)
from .intersection_patch_input_preparation_service import (
    IntersectionPatchInputPreparationRequest,
    IntersectionPatchInputPreparationService,
)
from .intersection_patch_pipeline_service import (
    IntersectionPatchPipelineRequest,
    IntersectionPatchPipelineService,
)


@dataclass(frozen=True)
class IntersectionPatchPreparationPipelineRequest:
    project_id: str
    surface_id: str
    corridor_id: str
    applied_section_set: object
    prerequisite: object
    intersection_model: object | None = None
    triangulation_policy: Mapping[str, float] | None = None


class IntersectionPatchPreparationPipelineService:
    """Orchestrate accepted inputs through the existing patch pipeline."""

    def __init__(
        self,
        *,
        input_preparation_service=None,
        grading_service=None,
        boundary_context_service=None,
        patch_pipeline_service=None,
    ) -> None:
        self.input_preparation_service = (
            input_preparation_service or IntersectionPatchInputPreparationService()
        )
        self.grading_service = grading_service or IntersectionPatchGradingService()
        self.boundary_context_service = (
            boundary_context_service or IntersectionPatchBoundaryContextService()
        )
        self.patch_pipeline_service = (
            patch_pipeline_service or IntersectionPatchPipelineService()
        )

    def build(
        self,
        request: IntersectionPatchPreparationPipelineRequest,
    ) -> IntersectionPatchPreparationPipelineResult:
        intersection_id = str(
            getattr(request.prerequisite, "intersection_id", "") or ""
        )
        completed = []
        diagnostics = []
        prepared_input = None
        grading_result = None
        boundary_context = None
        patch_pipeline = None
        stage = "input_preparation"
        try:
            prepared_input = self.input_preparation_service.prepare(
                IntersectionPatchInputPreparationRequest(
                    applied_section_set=request.applied_section_set,
                    prerequisite=request.prerequisite,
                    intersection_model=request.intersection_model,
                )
            )
            diagnostics.extend(prepared_input.diagnostic_rows)
            if prepared_input.status != "ready":
                return self._failure(
                    request,
                    intersection_id,
                    stage,
                    prepared_input.error_message,
                    diagnostics,
                    prepared_input=prepared_input,
                )
            completed.append(stage)

            stage = "grading"
            grading_result = self.grading_service.evaluate(
                IntersectionPatchGradingRequest(
                    vertices=tuple(prepared_input.vertex_rows),
                    intersection_model=request.intersection_model,
                    intersection_id=intersection_id,
                )
            )
            diagnostics.extend(grading_result.diagnostic_rows)
            if grading_result.status != "ready":
                return self._failure(
                    request,
                    intersection_id,
                    stage,
                    getattr(grading_result, "error_message", ""),
                    diagnostics,
                    completed=completed,
                    prepared_input=prepared_input,
                    grading_result=grading_result,
                )
            completed.append(stage)

            stage = "boundary_context"
            boundary_context = self.boundary_context_service.evaluate(
                IntersectionPatchBoundaryContextRequest(
                    applied_section_set=request.applied_section_set,
                    prerequisite=request.prerequisite,
                    intersection_model=request.intersection_model,
                )
            )
            diagnostics.extend(boundary_context.diagnostic_rows)
            completed.append(stage)

            stage = "patch_pipeline"
            patch_pipeline = self.patch_pipeline_service.build(
                IntersectionPatchPipelineRequest(
                    project_id=request.project_id,
                    surface_id=request.surface_id,
                    intersection_id=intersection_id,
                    corridor_id=request.corridor_id,
                    applied_section_set_id=str(
                        getattr(
                            request.applied_section_set,
                            "applied_section_set_id",
                            "",
                        )
                        or ""
                    ),
                    source_control_region_refs=tuple(
                        getattr(request.prerequisite, "control_region_refs", ())
                        or ()
                    ),
                    evaluated_control_region_refs=tuple(
                        prepared_input.control_region_refs
                    ),
                    participating_alignment_count=int(
                        getattr(
                            request.prerequisite,
                            "participating_alignment_count",
                            0,
                        )
                        or 0
                    ),
                    control_region_count=int(
                        getattr(request.prerequisite, "control_region_count", 0)
                        or 0
                    ),
                    tie_in_edge_count=int(
                        getattr(request.prerequisite, "tie_in_edge_count", 0) or 0
                    ),
                    graded_vertices=tuple(grading_result.vertex_rows),
                    grading_plane=grading_result.grading_plane,
                    grading_result=grading_result,
                    superelevation_context=(
                        prepared_input.superelevation_context
                    ),
                    boundary_context=boundary_context,
                    intersection_model=request.intersection_model,
                    triangulation_policy=request.triangulation_policy,
                )
            )
            diagnostics.extend(patch_pipeline.diagnostic_rows)
            if patch_pipeline.status != "ready" or patch_pipeline.tin_surface is None:
                return self._failure(
                    request,
                    intersection_id,
                    stage,
                    patch_pipeline.error_message,
                    diagnostics,
                    completed=completed,
                    prepared_input=prepared_input,
                    grading_result=grading_result,
                    boundary_context=boundary_context,
                    patch_pipeline=patch_pipeline,
                )
            completed.append(stage)
        except Exception as exc:
            diagnostics.append(
                f"intersection_patch_preparation_pipeline_failed:{stage}:"
                f"{type(exc).__name__}:{exc}"
            )
            return self._failure(
                request,
                intersection_id,
                stage,
                str(exc),
                diagnostics,
                completed=completed,
                prepared_input=prepared_input,
                grading_result=grading_result,
                boundary_context=boundary_context,
                patch_pipeline=patch_pipeline,
            )
        return IntersectionPatchPreparationPipelineResult(
            status="ready",
            surface_id=request.surface_id,
            intersection_id=intersection_id,
            tin_surface=patch_pipeline.tin_surface,
            prepared_input=prepared_input,
            grading_result=grading_result,
            boundary_context=boundary_context,
            patch_pipeline=patch_pipeline,
            completed_stages=tuple(completed),
            diagnostic_rows=tuple(diagnostics),
        )

    @staticmethod
    def _failure(
        request,
        intersection_id,
        stage,
        message,
        diagnostics,
        *,
        completed=(),
        prepared_input=None,
        grading_result=None,
        boundary_context=None,
        patch_pipeline=None,
    ):
        return IntersectionPatchPreparationPipelineResult(
            status="error",
            surface_id=request.surface_id,
            intersection_id=intersection_id,
            prepared_input=prepared_input,
            grading_result=grading_result,
            boundary_context=boundary_context,
            patch_pipeline=patch_pipeline,
            completed_stages=tuple(completed),
            failed_stage=stage,
            diagnostic_rows=tuple(diagnostics),
            error_message=str(message or ""),
        )
