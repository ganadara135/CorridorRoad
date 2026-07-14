"""Evaluate result-only low-point and boundary flow review metrics."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.intersection_patch_drainage_review import (
    IntersectionPatchDrainageReviewResult,
)


@dataclass(frozen=True)
class IntersectionPatchDrainageReviewRequest:
    boundary_vertices: tuple[object, ...]
    all_vertices: tuple[object, ...]
    low_point_tolerance: float = 0.001


class IntersectionPatchDrainageReviewService:
    """Calculate review hints without creating accepted Drainage source intent."""

    def evaluate(
        self,
        request: IntersectionPatchDrainageReviewRequest,
    ) -> IntersectionPatchDrainageReviewResult:
        tolerance = max(float(request.low_point_tolerance), 0.0)
        vertices = tuple(
            vertex for vertex in tuple(request.all_vertices or ())
            if vertex is not None
        )
        if not vertices:
            return IntersectionPatchDrainageReviewResult(
                status="empty",
                low_point_tolerance=tolerance,
                flow_hint_summary="no intersection patch vertices",
                diagnostic_rows=(
                    "intersection_patch_drainage_review_no_vertices",
                ),
            )
        low_z = min(_coordinate(vertex, "z") for vertex in vertices)
        low_points = tuple(
            vertex for vertex in vertices
            if abs(_coordinate(vertex, "z") - low_z) <= tolerance
        )
        low_point = low_points[0]
        low_x = _coordinate(low_point, "x")
        low_y = _coordinate(low_point, "y")
        boundary = tuple(
            vertex for vertex in tuple(request.boundary_vertices or ())
            if vertex is not None
        )
        flow_sources = tuple(
            vertex for vertex in boundary
            if _coordinate(vertex, "z") > low_z + tolerance
        )
        if flow_sources:
            average_dx = sum(
                low_x - _coordinate(vertex, "x") for vertex in flow_sources
            ) / len(flow_sources)
            average_dy = sum(
                low_y - _coordinate(vertex, "y") for vertex in flow_sources
            ) / len(flow_sources)
            summary = (
                f"boundary_to_low count={len(flow_sources)}; "
                f"avg_vector=({average_dx:.3f},{average_dy:.3f})"
            )
        else:
            average_dx = 0.0
            average_dy = 0.0
            summary = (
                "boundary_to_low count=0; patch appears flat at low-point "
                "tolerance"
            )
        return IntersectionPatchDrainageReviewResult(
            status="ready",
            low_point_tolerance=tolerance,
            low_point_candidate_count=len(low_points),
            low_point_x=low_x,
            low_point_y=low_y,
            low_point_z=low_z,
            low_point_source_ref=str(
                getattr(low_point, "source_point_ref", "") or ""
            ),
            flow_hint_count=len(flow_sources),
            average_flow_dx=average_dx,
            average_flow_dy=average_dy,
            flow_hint_summary=summary,
        )


def _coordinate(vertex: object, name: str) -> float:
    return float(getattr(vertex, name, 0.0) or 0.0)
