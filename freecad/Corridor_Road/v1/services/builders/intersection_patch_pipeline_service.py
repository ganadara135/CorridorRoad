"""Orchestrate the typed non-roundabout Intersection patch result pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ...models.result.intersection_patch_pipeline import (
    IntersectionPatchPipelineResult,
)
from ...models.result.tin_surface import TINVertex
from ..evaluation.intersection_patch_drainage_review_service import (
    IntersectionPatchDrainageReviewRequest,
    IntersectionPatchDrainageReviewService,
)
from ..evaluation.intersection_patch_shape_quality_service import (
    IntersectionPatchShapeQualityRequest,
    IntersectionPatchShapeQualityService,
)
from .intersection_patch_boundary_selection_service import (
    IntersectionPatchBoundarySelectionRequest,
    IntersectionPatchBoundarySelectionService,
)
from .intersection_patch_constraint_build_service import (
    IntersectionPatchConstraintBuildRequest,
    IntersectionPatchConstraintBuildService,
)
from .intersection_patch_tin_assembly_service import (
    IntersectionPatchTinAssemblyRequest,
    IntersectionPatchTinAssemblyService,
)
from .intersection_patch_triangulation_service import (
    IntersectionPatchTriangulationRequest,
    IntersectionPatchTriangulationService,
)


@dataclass(frozen=True)
class IntersectionPatchPipelineRequest:
    project_id: str
    surface_id: str
    intersection_id: str
    corridor_id: str
    applied_section_set_id: str
    source_control_region_refs: tuple[str, ...]
    evaluated_control_region_refs: tuple[str, ...]
    participating_alignment_count: int
    control_region_count: int
    tie_in_edge_count: int
    graded_vertices: tuple[object, ...]
    grading_plane: tuple[float, float, float] | None
    grading_result: object
    superelevation_context: object
    boundary_context: object
    intersection_model: object | None = None
    triangulation_policy: Mapping[str, float] | None = None


class IntersectionPatchPipelineService:
    """Run typed post-context stages without document or presentation access."""

    def __init__(
        self,
        *,
        boundary_selection_service=None,
        drainage_review_service=None,
        triangulation_service=None,
        constraint_service=None,
        shape_quality_service=None,
        assembly_service=None,
    ) -> None:
        self.boundary_selection_service = (
            boundary_selection_service or IntersectionPatchBoundarySelectionService()
        )
        self.drainage_review_service = (
            drainage_review_service or IntersectionPatchDrainageReviewService()
        )
        self.triangulation_service = (
            triangulation_service or IntersectionPatchTriangulationService()
        )
        self.constraint_service = (
            constraint_service or IntersectionPatchConstraintBuildService()
        )
        self.shape_quality_service = (
            shape_quality_service or IntersectionPatchShapeQualityService()
        )
        self.assembly_service = assembly_service or IntersectionPatchTinAssemblyService()

    def build(
        self,
        request: IntersectionPatchPipelineRequest,
    ) -> IntersectionPatchPipelineResult:
        completed = []
        diagnostics = []
        boundary_selection = None
        center = None
        drainage = None
        triangulation = None
        constraint = None
        quality = None
        assembly = None
        stage = "boundary_selection"
        try:
            boundary_selection = self.boundary_selection_service.select(
                IntersectionPatchBoundarySelectionRequest(
                    source_vertices=tuple(request.graded_vertices),
                    patch_boundary_result=request.boundary_context.patch_boundary_result,
                    boundary_loop_result=request.boundary_context.boundary_loop_result,
                    grading_plane=request.grading_plane,
                    grading_mode=str(
                        getattr(request.grading_result, "grading_mode", "") or ""
                    ),
                    boundary_evaluation_failed=(
                        bool(request.boundary_context.boundary_evaluation_failed)
                        and request.boundary_context.patch_boundary_result is None
                    ),
                )
            )
            diagnostics.extend(boundary_selection.diagnostic_rows)
            if boundary_selection.status != "ready":
                return self._failure(
                    request,
                    stage,
                    boundary_selection.error_message,
                    diagnostics,
                    boundary_selection=boundary_selection,
                )
            completed.append(stage)
            vertices = list(boundary_selection.vertex_rows)
            stage = "centroid"
            center = _centroid_vertex(vertices, request.surface_id)
            completed.append(stage)
            stage = "drainage_review"
            drainage = self.drainage_review_service.evaluate(
                IntersectionPatchDrainageReviewRequest(
                    boundary_vertices=tuple(vertices),
                    all_vertices=tuple([*vertices, center]),
                )
            )
            diagnostics.extend(drainage.diagnostic_rows)
            completed.append(stage)
            stage = "triangulation"
            triangulation = self.triangulation_service.triangulate(
                IntersectionPatchTriangulationRequest(
                    boundary_source=boundary_selection.boundary_source,
                    boundary_vertices=tuple(vertices),
                    center_vertex=center,
                    intersection_id=request.intersection_id,
                    policy=request.triangulation_policy,
                    tie_in_result=request.boundary_context.tie_in_result,
                    intersection_model=request.intersection_model,
                    boundary_segment_result=(
                        request.boundary_context.boundary_segment_result
                    ),
                )
            )
            diagnostics.extend(triangulation.diagnostic_rows)
            if triangulation.status != "ready":
                return self._failure(
                    request,
                    stage,
                    triangulation.error_message,
                    diagnostics,
                    completed=completed,
                    boundary_selection=boundary_selection,
                    center=center,
                    drainage=drainage,
                    triangulation=triangulation,
                )
            completed.append(stage)
            stage = "shared_breakline_constraints"
            constraint = self.constraint_service.build(
                IntersectionPatchConstraintBuildRequest(
                    surface_id=request.surface_id,
                    vertices=tuple(triangulation.vertex_rows),
                    triangles=tuple(triangulation.triangle_rows),
                    shared_breakline_result=(
                        request.boundary_context.shared_breakline_result
                    ),
                )
            )
            diagnostics.extend(constraint.diagnostic_rows)
            if constraint.status != "ready":
                return self._failure(
                    request,
                    stage,
                    constraint.error_message,
                    diagnostics,
                    completed=completed,
                    boundary_selection=boundary_selection,
                    center=center,
                    drainage=drainage,
                    triangulation=triangulation,
                    constraint=constraint,
                )
            completed.append(stage)
            stage = "shape_quality"
            quality = self.shape_quality_service.evaluate(
                IntersectionPatchShapeQualityRequest(
                    vertices=tuple(constraint.vertex_rows),
                    triangles=tuple(constraint.triangle_rows),
                )
            )
            diagnostics.extend(quality.diagnostic_rows)
            completed.append(stage)
            stage = "tin_assembly"
            assembly = self.assembly_service.build(
                IntersectionPatchTinAssemblyRequest(
                    project_id=request.project_id,
                    surface_id=request.surface_id,
                    intersection_id=request.intersection_id,
                    corridor_id=request.corridor_id,
                    applied_section_set_id=request.applied_section_set_id,
                    source_control_region_refs=request.source_control_region_refs,
                    evaluated_control_region_refs=(
                        request.evaluated_control_region_refs
                    ),
                    participating_alignment_count=(
                        request.participating_alignment_count
                    ),
                    control_region_count=request.control_region_count,
                    tie_in_edge_count=request.tie_in_edge_count,
                    boundary_vertex_count=len(vertices),
                    vertex_rows=tuple(constraint.vertex_rows),
                    triangle_rows=tuple(constraint.triangle_rows),
                    boundary_selection=boundary_selection,
                    triangulation=triangulation,
                    constraint_build=constraint,
                    grading_result=request.grading_result,
                    superelevation_context=request.superelevation_context,
                    drainage_review=drainage,
                    shape_quality=quality,
                )
            )
            diagnostics.extend(assembly.diagnostic_rows)
            if assembly.status != "ready" or assembly.tin_surface is None:
                return self._failure(
                    request,
                    stage,
                    assembly.error_message,
                    diagnostics,
                    completed=completed,
                    boundary_selection=boundary_selection,
                    center=center,
                    drainage=drainage,
                    triangulation=triangulation,
                    constraint=constraint,
                    quality=quality,
                    assembly=assembly,
                )
            completed.append(stage)
        except Exception as exc:
            diagnostics.append(
                f"intersection_patch_pipeline_failed:{stage}:"
                f"{type(exc).__name__}:{exc}"
            )
            return self._failure(
                request,
                stage,
                str(exc),
                diagnostics,
                completed=completed,
                boundary_selection=boundary_selection,
                center=center,
                drainage=drainage,
                triangulation=triangulation,
                constraint=constraint,
                quality=quality,
                assembly=assembly,
            )
        return IntersectionPatchPipelineResult(
            status="ready",
            surface_id=request.surface_id,
            intersection_id=request.intersection_id,
            tin_surface=assembly.tin_surface,
            boundary_selection=boundary_selection,
            center_vertex=center,
            drainage_review=drainage,
            triangulation=triangulation,
            constraint_build=constraint,
            shape_quality=quality,
            assembly=assembly,
            completed_stages=tuple(completed),
            diagnostic_rows=tuple(diagnostics),
        )

    @staticmethod
    def _failure(
        request,
        stage,
        message,
        diagnostics,
        *,
        completed=(),
        boundary_selection=None,
        center=None,
        drainage=None,
        triangulation=None,
        constraint=None,
        quality=None,
        assembly=None,
    ):
        return IntersectionPatchPipelineResult(
            status="error",
            surface_id=request.surface_id,
            intersection_id=request.intersection_id,
            boundary_selection=boundary_selection,
            center_vertex=center,
            drainage_review=drainage,
            triangulation=triangulation,
            constraint_build=constraint,
            shape_quality=quality,
            assembly=assembly,
            completed_stages=tuple(completed),
            failed_stage=stage,
            diagnostic_rows=tuple(diagnostics),
            error_message=str(message or ""),
        )


def _centroid_vertex(vertices, surface_id: str) -> TINVertex:
    count = len(vertices)
    return TINVertex(
        vertex_id="v:center",
        x=sum(float(getattr(vertex, "x", 0.0) or 0.0) for vertex in vertices)
        / count,
        y=sum(float(getattr(vertex, "y", 0.0) or 0.0) for vertex in vertices)
        / count,
        z=sum(float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices)
        / count,
        source_point_ref=f"{surface_id}:centroid",
        notes="intersection patch centroid",
    )
