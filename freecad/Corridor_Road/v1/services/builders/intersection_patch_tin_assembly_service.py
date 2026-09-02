"""Assemble the final non-roundabout Intersection patch TIN contract."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.intersection_patch_tin_assembly import (
    IntersectionPatchTinAssemblyResult,
)
from ...models.result.tin_surface import (
    TINProvenanceRow,
    TINQualityRow,
    TINSurface,
)


@dataclass(frozen=True)
class IntersectionPatchTinAssemblyRequest:
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
    boundary_vertex_count: int
    vertex_rows: tuple[object, ...]
    triangle_rows: tuple[object, ...]
    boundary_selection: object
    triangulation: object
    constraint_build: object
    grading_result: object
    superelevation_context: object
    drainage_review: object
    shape_quality: object


class IntersectionPatchTinAssemblyService:
    """Build final TIN identity, quality, and provenance from typed results."""

    def build(
        self,
        request: IntersectionPatchTinAssemblyRequest,
    ) -> IntersectionPatchTinAssemblyResult:
        try:
            surface = self._assemble(request)
        except Exception as exc:
            return IntersectionPatchTinAssemblyResult(
                status="error",
                surface_id=request.surface_id,
                intersection_id=request.intersection_id,
                diagnostic_rows=(
                    "intersection_patch_tin_assembly_failed:"
                    f"{type(exc).__name__}:{exc}",
                ),
                error_message=str(exc),
            )
        return IntersectionPatchTinAssemblyResult(
            status="ready",
            surface_id=request.surface_id,
            intersection_id=request.intersection_id,
            tin_surface=surface,
            quality_row_count=len(surface.quality_rows),
            provenance_row_count=len(surface.provenance_rows),
        )

    def _assemble(self, request: IntersectionPatchTinAssemblyRequest) -> TINSurface:
        surface_id = request.surface_id
        boundary = request.boundary_selection
        triangulation = request.triangulation
        constraint = request.constraint_build
        grading = request.grading_result
        superelevation = request.superelevation_context
        drainage = request.drainage_review
        quality = request.shape_quality

        def row(kind: str, value, unit: str = "") -> TINQualityRow:
            return TINQualityRow(f"{surface_id}:{kind}", kind, value, unit)

        quality_rows = [
            row("patch_boundary_point_count", request.boundary_vertex_count, "count"),
            row("patch_boundary_source", boundary.boundary_source),
            row("participating_alignment_count", request.participating_alignment_count, "count"),
            row("control_region_count", request.control_region_count, "count"),
            row("tie_in_edge_count", request.tie_in_edge_count, "count"),
            row("patch_triangle_count", len(request.triangle_rows), "count"),
            row("patch_degenerate_triangle_count", triangulation.degenerate_count, "count"),
            row("patch_boundary_edge_max_length", triangulation.max_edge_length, "m"),
            row("patch_boundary_edge_long_count", triangulation.long_edge_count, "count"),
            row("patch_boundary_edge_long_factor", triangulation.long_edge_factor, "factor"),
            row("patch_boundary_edge_long_limit", triangulation.long_edge_limit, "m"),
            row("patch_boundary_edge_max_length_policy", triangulation.max_boundary_edge_length_policy, "m"),
            row("patch_triangulation_mode", quality.triangulation_mode),
            row("patch_surface_boundary_strategy", triangulation.boundary_strategy),
            row("patch_structured_strip_count", triangulation.structured_strip_count, "count"),
            row("patch_curb_return_surface_edge_count", triangulation.curb_return_surface_edge_count, "count"),
            row("patch_curb_return_arc_count", triangulation.curb_return_arc_count, "count"),
            row("patch_curb_return_arc_sample_count", triangulation.curb_return_arc_sample_count, "count"),
            row("patch_curb_return_arc_segment_count", triangulation.curb_return_arc_segment_count, "count"),
            row("patch_edge_blend_face_count", triangulation.edge_blend_face_count, "count"),
            row("patch_boundary_role_summary", triangulation.boundary_role_summary),
            row("patch_boundary_pavement_tie_in_edge_count", triangulation.pavement_tie_in_edge_count, "count"),
            row("patch_boundary_stem_tie_in_edge_count", triangulation.stem_tie_in_edge_count, "count"),
            row("patch_boundary_overlap_cut_edge_count", triangulation.overlap_cut_edge_count, "count"),
            row("patch_boundary_curb_return_edge_count", triangulation.curb_return_edge_count, "count"),
            row("shared_breakline_constraint_mode", constraint.mode),
            row("shared_breakline_constraint_segment_count", constraint.segment_count, "count"),
            row("shared_breakline_constraint_edge_count", constraint.edge_count, "count"),
            row("shared_breakline_constraint_vertex_count", constraint.inserted_vertex_count, "count"),
            row("shared_breakline_boundary_loop_constraint_segment_count", constraint.boundary_loop_segment_count, "count"),
            row("shared_breakline_boundary_loop_constraint_edge_count", constraint.boundary_loop_edge_count, "count"),
            row("shared_breakline_boundary_loop_constraint_refs", ",".join(_unique_text_values(constraint.boundary_loop_refs))),
            row("shared_breakline_boundary_loop_constraint_role_summary", constraint.boundary_loop_role_summary),
            row("shared_breakline_constraint_snap_count", constraint.snap_count, "count"),
            row("shared_breakline_constraint_snap_max_distance", constraint.snap_max_distance, "m"),
            row("shared_breakline_constraint_snap_diagnostics", "; ".join(constraint.snap_diagnostic_rows)),
            row("patch_boundary_bbox_x", quality.bbox_x, "m"),
            row("patch_boundary_bbox_y", quality.bbox_y, "m"),
            row("patch_boundary_bbox_aspect_ratio", quality.bbox_aspect_ratio, "ratio"),
            row("patch_triangle_min_quality", quality.triangle_min_quality, "ratio"),
            row("patch_triangle_skinny_count", quality.skinny_triangle_count, "count"),
            row("ordered_patch_boundary_point_count", boundary.patch_boundary_point_count, "count"),
            row("ordered_patch_boundary_source_segment_count", boundary.patch_boundary_source_segment_count, "count"),
            row("ordered_patch_boundary_closed", 1 if boundary.patch_boundary_closed else 0, "boolean"),
            row("ordered_patch_boundary_diagnostic_count", boundary.patch_boundary_diagnostic_count, "count"),
            row("ordered_patch_boundary_polygon_area", boundary.patch_boundary_polygon_area, "m2"),
            row("ordered_patch_boundary_self_crossing", 1 if boundary.patch_boundary_self_crossing else 0, "boolean"),
            row("ordered_patch_boundary_ring_count", boundary.patch_boundary_ring_count, "count"),
            row("ordered_patch_boundary_hole_ring_count", boundary.patch_boundary_hole_ring_count, "count"),
            row("ordered_patch_boundary_island_ring_count", boundary.patch_boundary_island_ring_count, "count"),
            row("authoritative_boundary_loop_source", boundary.boundary_loop_source),
            row("authoritative_boundary_loop_point_count", boundary.boundary_loop_point_count, "count"),
            row("authoritative_boundary_loop_segment_count", boundary.boundary_loop_segment_count, "count"),
            row("intersection_grading_mode", grading.grading_mode),
            row("intersection_grading_z_delta_max", grading.max_z_delta, "m"),
            row("intersection_superelevation_source_count", int(superelevation.source_count), "count"),
            row("intersection_superelevation_transition_count", int(superelevation.transition_count), "count"),
            row("intersection_superelevation_left_min", float(superelevation.left_min), "%"),
            row("intersection_superelevation_left_max", float(superelevation.left_max), "%"),
            row("intersection_superelevation_right_min", float(superelevation.right_min), "%"),
            row("intersection_superelevation_right_max", float(superelevation.right_max), "%"),
            row("intersection_superelevation_context", str(superelevation.summary)),
            row("intersection_low_point_candidate_count", drainage.low_point_candidate_count, "count"),
            row("intersection_low_point_x", drainage.low_point_x, "m"),
            row("intersection_low_point_y", drainage.low_point_y, "m"),
            row("intersection_low_point_z", drainage.low_point_z, "m"),
            row("intersection_low_point_source_ref", drainage.low_point_source_ref),
            row("intersection_boundary_to_low_flow_hint_count", drainage.flow_hint_count, "count"),
            row("intersection_boundary_to_low_flow_hint_summary", drainage.flow_hint_summary),
        ]
        return TINSurface(
            schema_version=1,
            project_id=request.project_id,
            surface_id=surface_id,
            surface_kind="intersection_surface",
            label=(
                "Intersection Surface - "
                f"{request.intersection_id or request.corridor_id}"
            ),
            source_refs=[
                request.applied_section_set_id,
                request.intersection_id,
                *list(request.source_control_region_refs),
            ],
            vertex_rows=list(request.vertex_rows),
            triangle_rows=list(request.triangle_rows),
            boundary_refs=[f"{surface_id}:boundary"],
            quality_rows=quality_rows,
            provenance_rows=[
                TINProvenanceRow(
                    provenance_id=(
                        f"{surface_id}:provenance:applied-sections"
                    ),
                    source_kind="intersection_applied_section_fg_surface",
                    source_ref=request.applied_section_set_id,
                    notes=(
                        f"intersection={request.intersection_id}; "
                        "control_regions="
                        f"{','.join(sorted(request.evaluated_control_region_refs))}"
                    ),
                )
            ],
        )


def _unique_text_values(values) -> list[str]:
    output = []
    seen = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output
