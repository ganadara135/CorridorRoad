"""Orchestrate authoritative Intersection boundary-loop evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.intersection_boundary_loop_evaluation_chain import (
    IntersectionBoundaryLoopEvaluationChainResult,
)
from .intersection_evaluation_service import IntersectionEvaluationService


@dataclass(frozen=True)
class IntersectionBoundaryLoopEvaluationRequest:
    applied_section_set: object
    prerequisite: object
    intersection_model: object | None = None


class IntersectionBoundaryLoopEvaluationService:
    """Run the source-driven boundary-loop evaluation chain in order."""

    def __init__(self, *, evaluation_service=None) -> None:
        self.evaluation_service = evaluation_service or IntersectionEvaluationService()

    def evaluate(
        self,
        request: IntersectionBoundaryLoopEvaluationRequest,
    ) -> IntersectionBoundaryLoopEvaluationChainResult:
        intersection_id = str(
            getattr(request.prerequisite, "intersection_id", "") or ""
        )
        if request.intersection_model is None:
            return IntersectionBoundaryLoopEvaluationChainResult(
                status="missing",
                intersection_id=intersection_id,
                failed_stage="input_validation",
                diagnostic_rows=("intersection_boundary_loop_model_missing",),
                error_message="Intersection model is required.",
            )

        completed = []
        topology_result = None
        edge_network_result = None
        surface_zone_result = None
        slope_face_loop_result = None
        boundary_loop_result = None
        stage = "topology"
        try:
            topology_result = self.evaluation_service.evaluate_topology(
                request.intersection_model
            )
            completed.append(stage)
            stage = "edge_network"
            edge_network_result = self.evaluation_service.evaluate_edge_network(
                request.intersection_model,
                topology_result,
            )
            completed.append(stage)
            stage = "surface_zones"
            surface_zone_result = self.evaluation_service.evaluate_surface_zones(
                request.intersection_model,
                edge_network_result,
            )
            completed.append(stage)
            stage = "slope_face_loops"
            slope_face_loop_result = (
                self.evaluation_service.evaluate_slope_face_loops(
                    request.intersection_model,
                    surface_zone_result,
                    edge_network_result,
                    request.applied_section_set,
                )
            )
            completed.append(stage)
            stage = "boundary_loops"
            boundary_loop_result = self.evaluation_service.evaluate_boundary_loops(
                request.intersection_model,
                surface_zone_result=surface_zone_result,
                edge_network_result=edge_network_result,
                slope_face_loop_result=slope_face_loop_result,
                applied_section_set=request.applied_section_set,
                intersection_id=intersection_id,
            )
            completed.append(stage)
        except Exception as exc:
            diagnostic = f"intersection_boundary_loop_evaluation_failed:{exc}"
            return IntersectionBoundaryLoopEvaluationChainResult(
                status="error",
                intersection_id=intersection_id,
                topology_result=topology_result,
                edge_network_result=edge_network_result,
                surface_zone_result=surface_zone_result,
                slope_face_loop_result=slope_face_loop_result,
                boundary_loop_result=boundary_loop_result,
                completed_stages=tuple(completed),
                failed_stage=stage,
                diagnostic_rows=(diagnostic,),
                error_message=str(exc),
            )
        return IntersectionBoundaryLoopEvaluationChainResult(
            status="ready" if boundary_loop_result is not None else "missing",
            intersection_id=intersection_id,
            topology_result=topology_result,
            edge_network_result=edge_network_result,
            surface_zone_result=surface_zone_result,
            slope_face_loop_result=slope_face_loop_result,
            boundary_loop_result=boundary_loop_result,
            completed_stages=tuple(completed),
        )

    def evaluate_context(
        self,
        applied_section_set,
        *,
        prerequisite,
        intersection_model,
        diagnostics: list[str],
    ):
        """Adapt the boundary-context evaluator signature to the typed request."""

        result = self.evaluate(
            IntersectionBoundaryLoopEvaluationRequest(
                applied_section_set=applied_section_set,
                prerequisite=prerequisite,
                intersection_model=intersection_model,
            )
        )
        diagnostics.extend(result.diagnostic_rows)
        return result.boundary_loop_result
