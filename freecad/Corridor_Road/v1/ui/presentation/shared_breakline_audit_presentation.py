"""Presentation mapping for typed shared-breakline audit results."""

from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Mapping
from .review_text import join_review_notes as _join_review_notes
from .review_text import unique_text_values as _unique_text_values


@dataclass(frozen=True)
class SharedBreaklineAuditPresentation:
    status: str
    missing_consumer_count: int
    mismatch_count: int
    geometry_match_count: int
    geometry_mismatch_count: int
    mesh_match_count: int
    mesh_mismatch_count: int
    reversed_edge_count: int
    solid_readiness_status: str
    solid_open_end_count: int
    solid_duplicate_edge_count: int
    solid_reversed_edge_count: int
    solid_non_manifold_node_count: int
    solid_readiness_notes: str
    notes: str
    summary: str
    note_rows: tuple[str, ...]


class SharedBreaklineAuditPresentationMapper:
    """Map typed or compatibility audit results into stable display fields."""

    def map(self, audit: object) -> SharedBreaklineAuditPresentation:
        status = str(_value(audit, "status", "") or "")
        geometry_match = int(_value(audit, "geometry_match_count", 0) or 0)
        geometry_mismatch = int(
            _value(audit, "geometry_mismatch_count", 0) or 0
        )
        mesh_match = int(_value(audit, "mesh_match_count", 0) or 0)
        mesh_mismatch = int(_value(audit, "mesh_mismatch_count", 0) or 0)
        missing = int(_value(audit, "missing_consumer_count", 0) or 0)
        mismatch = int(_value(audit, "mismatch_count", 0) or 0)
        reversed_count = int(_value(audit, "reversed_edge_count", 0) or 0)
        notes = str(_value(audit, "notes", "") or "")
        summary = (
            f"audit={status or 'unknown'} "
            f"geometry={geometry_match}/{geometry_match + geometry_mismatch} "
            f"mesh={mesh_match}/{mesh_match + mesh_mismatch} "
            f"missing={missing} mismatch={mismatch} reversed={reversed_count}"
        )
        return SharedBreaklineAuditPresentation(
            status=status,
            missing_consumer_count=missing,
            mismatch_count=mismatch,
            geometry_match_count=geometry_match,
            geometry_mismatch_count=geometry_mismatch,
            mesh_match_count=mesh_match,
            mesh_mismatch_count=mesh_mismatch,
            reversed_edge_count=reversed_count,
            solid_readiness_status=str(
                _value(audit, "solid_readiness_status", "") or ""
            ),
            solid_open_end_count=int(
                _value(audit, "solid_open_end_count", 0) or 0
            ),
            solid_duplicate_edge_count=int(
                _value(audit, "solid_duplicate_edge_count", 0) or 0
            ),
            solid_reversed_edge_count=int(
                _value(audit, "solid_reversed_edge_count", 0) or 0
            ),
            solid_non_manifold_node_count=int(
                _value(audit, "solid_non_manifold_node_count", 0) or 0
            ),
            solid_readiness_notes=str(
                _value(audit, "solid_readiness_notes", "") or ""
            ),
            notes=notes,
            summary=summary,
            note_rows=tuple(
                value.strip() for value in notes.split(";") if value.strip()
            ),
        )


def _value(source: object, name: str, default: object) -> object:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


# Moved from cmd_build_corridor by M5: panel display rows for the
# shared-breakline audit table. The command module keeps the document read
# and imports these back.

INTERSECTION_TIE_SLOPE_WINDOW_GENERIC_BREAKLINE_ROLES = (
    "intersection_tie_slope_window_outer",
    "intersection_tie_slope_window_inner",
    "intersection_tie_slope_window_start_cap",
    "intersection_tie_slope_window_end_cap",
)

INTERSECTION_TIE_SLOPE_WINDOW_APPROACH_BREAKLINE_ROLES = (
    "intersection_tie_slope_approach_outer",
    "intersection_tie_slope_to_curb_return_approach",
    "intersection_tie_slope_approach_start_cap",
    "intersection_tie_slope_approach_end_cap",
)

INTERSECTION_TIE_SLOPE_WINDOW_SUPPLEMENTAL_BREAKLINE_ROLES = (
    "intersection_tie_slope_supplemental_outer",
    "intersection_tie_slope_supplemental_inner",
    "intersection_tie_slope_supplemental_start_cap",
    "intersection_tie_slope_supplemental_end_cap",
)

INTERSECTION_TIE_SLOPE_WINDOW_ENDPOINT_BREAKLINE_ROLES = (
    "intersection_tie_slope_supplemental_outer",
    "intersection_tie_slope_supplemental_endpoint",
    "intersection_tie_slope_supplemental_start_cap",
    "intersection_tie_slope_supplemental_end_cap",
)

INTERSECTION_TIE_SLOPE_WINDOW_BREAKLINE_ROLES = (
    *INTERSECTION_TIE_SLOPE_WINDOW_GENERIC_BREAKLINE_ROLES,
    *INTERSECTION_TIE_SLOPE_WINDOW_APPROACH_BREAKLINE_ROLES,
    *INTERSECTION_TIE_SLOPE_WINDOW_SUPPLEMENTAL_BREAKLINE_ROLES,
    *INTERSECTION_TIE_SLOPE_WINDOW_ENDPOINT_BREAKLINE_ROLES,
)

INTERSECTION_SHARED_BOUNDARY_EXPECTED_CONSUMERS = {
    "patch_to_design_surface": ("intersection_surface", "design_surface", "intersection_slope_face_surface"),
    "patch_to_intersection_slope_face": ("intersection_surface", "intersection_slope_face_surface"),
    "intersection_slope_face_to_design_surface": ("intersection_slope_face_surface", "design_surface"),
    "intersection_slope_face_to_corridor_slope_face": ("intersection_slope_face_surface", "slope_face_surface"),
    "main_road_tie": ("intersection_surface", "design_surface", "intersection_slope_face_surface"),
    "side_road_tie": ("intersection_surface", "design_surface", "intersection_slope_face_surface"),
    "main_side_slope_face_tie": ("intersection_slope_face_surface",),
    "curb_return_to_intersection_slope_face": ("intersection_surface", "intersection_slope_face_surface"),
    "curb_return_bridge_to_intersection_slope_face": ("intersection_slope_face_surface", "intersection_slope_face_cell_result"),
    "intersection_tie_slope_transition_inner": ("intersection_tie_slope_surface", "intersection_slope_face_surface", "intersection_surface"),
    "intersection_tie_slope_transition_outer": ("intersection_tie_slope_surface", "slope_face_surface"),
    "intersection_tie_slope_start_cap": ("intersection_tie_slope_surface",),
    "intersection_tie_slope_end_cap": ("intersection_tie_slope_surface",),
    "roundabout_island_to_circulatory": ("intersection_surface", "roundabout_central_island", "roundabout_circulatory_surface"),
    "roundabout_circulatory_to_apron": ("intersection_surface", "roundabout_circulatory_surface", "roundabout_apron_surface"),
    "roundabout_apron_to_slope_face": ("roundabout_apron_surface", "roundabout_slope_face_surface"),
    "roundabout_entry_exit_connector_boundary": ("roundabout_entry_exit_connector", "design_surface", "roundabout_circulatory_surface"),
    "roundabout_approach_clip_to_design_surface": ("design_surface",),
    "roundabout_subgrade_clip_to_subgrade_surface": ("subgrade_surface", "roundabout_subgrade_surface"),
    "roundabout_subgrade_to_approach_subgrade": ("subgrade_surface", "roundabout_subgrade_surface"),
    "roundabout_slope_handoff_to_slope_face_surface": ("slope_face_surface",),
    "roundabout_slope_to_corridor_slope_face": ("slope_face_surface",),
    "roundabout_central_island_boundary": ("intersection_surface", "roundabout_central_island", "roundabout_circulatory_surface"),
    "roundabout_circulatory_outer_boundary": ("intersection_surface", "roundabout_circulatory_surface", "roundabout_apron_surface"),
    "roundabout_outer_ownership_boundary": ("roundabout_apron_surface", "roundabout_slope_face_surface"),
    "intersection_upper_slope_face_panel_inner": ("intersection_upper_slope_face_panel_handoff",),
    "intersection_upper_slope_face_panel_outer": ("intersection_upper_slope_face_panel_handoff",),
    "intersection_upper_slope_face_panel_left_cap": ("intersection_upper_slope_face_panel_handoff",),
    "intersection_upper_slope_face_panel_right_cap": ("intersection_upper_slope_face_panel_handoff",),
    "upper_transition_internal_seam": ("intersection_slope_face_surface",),
    "cell_closure_internal_seam": ("intersection_slope_face_surface",),
}


def shared_breakline_audit_display_rows(rows: list[dict[str, object]], *, include_internal: bool = False) -> list[dict[str, object]]:
    """Return panel-friendly shared breakline audit rows.

    The default panel view is intentionally compact. It keeps the audited
    surface rows and hides implementation detail rows such as graph edges,
    graph cells, role expansions, and slope-face cell internals. Tests and
    developer diagnostics can opt into those rows with ``include_internal``.
    """

    output: list[dict[str, object]] = []
    for row in list(rows or []):
        surface_row = dict(row)
        surface_row["row_kind"] = "surface"
        output.append(surface_row)
        if not include_internal:
            continue
        for role, count in _shared_breakline_summary_count_items(str(row.get("role_summary", "") or "")):
            detail = dict(row)
            detail["row_kind"] = "role"
            detail["surface"] = f"  Role: {role}"
            detail["consumed"] = count
            detail["total"] = count
            detail["material_summary"] = str(row.get("material_summary", "") or "")
            detail["role_summary"] = f"{role}={count}"
            detail["breakline_role_filter"] = role
            detail["recommended_action"] = _shared_breakline_recommended_action_from_notes(role) or str(row.get("recommended_action", "") or "")
            output.append(detail)
        tie_slope_window_counts = _intersection_tie_slope_window_role_counts_from_audit_row(row)
        if tie_slope_window_counts:
            consumed = sum(tie_slope_window_counts.values())
            required_roles: list[str] = []
            if any(int(tie_slope_window_counts.get(role, 0) or 0) > 0 for role in INTERSECTION_TIE_SLOPE_WINDOW_GENERIC_BREAKLINE_ROLES):
                required_roles.extend(INTERSECTION_TIE_SLOPE_WINDOW_GENERIC_BREAKLINE_ROLES)
            if any(int(tie_slope_window_counts.get(role, 0) or 0) > 0 for role in INTERSECTION_TIE_SLOPE_WINDOW_APPROACH_BREAKLINE_ROLES):
                required_roles.extend(INTERSECTION_TIE_SLOPE_WINDOW_APPROACH_BREAKLINE_ROLES)
            if not required_roles:
                required_roles = list(INTERSECTION_TIE_SLOPE_WINDOW_BREAKLINE_ROLES)
            missing_roles = [
                role for role in required_roles
                if int(tie_slope_window_counts.get(role, 0) or 0) <= 0
            ]
            detail = dict(row)
            detail["row_kind"] = "intersection_tie_slope_window"
            detail["surface"] = "  Intersection Tie Slope Window Handoff"
            detail["status"] = "warning" if missing_roles else "ready"
            detail["consumed"] = consumed
            detail["total"] = max(consumed, len(required_roles))
            detail["material_summary"] = "intersection_tie_slope_window"
            detail["role_summary"] = ", ".join(
                f"{role}={int(tie_slope_window_counts.get(role, 0) or 0)}"
                for role in INTERSECTION_TIE_SLOPE_WINDOW_BREAKLINE_ROLES
            )
            detail["breakline_role_filter"] = "intersection_tie_slope_window"
            detail["recommended_action"] = (
                "Review Applied Section window candidates, then rebuild Tie Slope"
                if missing_roles
                else "No action needed"
            )
            detail["notes"] = _join_review_notes(
                str(detail.get("notes", "") or ""),
                (
                    "intersection_tie_slope_window_handoff="
                    f"roles={len(tie_slope_window_counts)}; consumed={consumed}; "
                    f"missing_roles={','.join(missing_roles) if missing_roles else 'none'}; "
                    "source=applied_section_context_transition_window"
                ),
            )
            output.append(detail)
        boundary_loop_ref_count = int(row.get("boundary_loop_ref_count", 0) or 0)
        boundary_loop_constraint_segments = int(row.get("boundary_loop_constraint_segment_count", 0) or 0)
        boundary_loop_constraint_edges = int(row.get("boundary_loop_constraint_edge_count", 0) or 0)
        exclusion_tested_triangles = int(row.get("intersection_exclusion_tested_triangle_count", 0) or 0)
        exclusion_clipped_triangles = int(row.get("intersection_exclusion_clipped_triangle_count", 0) or 0)
        exclusion_boundary_crossings = int(row.get("intersection_exclusion_boundary_crossing_triangle_count", 0) or 0)
        exclusion_near_boundary_kept = int(row.get("intersection_exclusion_near_boundary_kept_triangle_count", 0) or 0)
        exclusion_clip_ratio = float(row.get("intersection_exclusion_clip_ratio", 0.0) or 0.0)
        boundary_loop_near_kept_warning = bool(row.get("boundary_loop_near_kept_warning", False))
        if boundary_loop_ref_count or boundary_loop_constraint_segments or boundary_loop_constraint_edges:
            detail = dict(row)
            detail["row_kind"] = "boundary_loop_handoff"
            detail["surface"] = "  Boundary Loop Handoff"
            ownership_status = str(row.get("boundary_loop_ownership_status", "") or "")
            detail["status"] = (
                "warning"
                if boundary_loop_ref_count and not boundary_loop_constraint_edges
                or boundary_loop_near_kept_warning
                else ownership_status
                if ownership_status and ownership_status != "missing"
                else "ready"
            )
            detail["consumed"] = boundary_loop_constraint_edges
            detail["total"] = max(boundary_loop_ref_count, boundary_loop_constraint_segments, boundary_loop_constraint_edges)
            detail["material_summary"] = "intersection_boundary_loop"
            detail["role_summary"] = (
                f"refs={boundary_loop_ref_count}, "
                f"constraint_segments={boundary_loop_constraint_segments}, "
                f"constraint_edges={boundary_loop_constraint_edges}, "
                f"ownership={ownership_status or 'not_checked'}, "
                f"clip={exclusion_clipped_triangles}/{exclusion_tested_triangles}, "
                f"crossing={exclusion_boundary_crossings}, near_kept={exclusion_near_boundary_kept}, "
                f"ratio={exclusion_clip_ratio:.3f}"
            )
            detail["breakline_role_filter"] = "intersection_boundary_loop"
            detail["graph_edge_refs"] = _shared_boundary_graph_edge_refs_from_audit_row(
                row,
                source_ref_filter="intersection-boundary-loop",
            )
            if boundary_loop_near_kept_warning:
                detail["recommended_action"] = "Review boundary-loop clipping residuals, then rebuild constrained surfaces"
            elif str(detail["status"]) == "warning":
                detail["recommended_action"] = "Rebuild boundary-loop constrained surfaces"
            else:
                detail["recommended_action"] = "No action needed"
            detail["notes"] = _join_review_notes(
                str(detail.get("notes", "") or ""),
                (
                    "boundary_loop_handoff="
                    f"refs={boundary_loop_ref_count}; "
                    f"constraint_segments={boundary_loop_constraint_segments}; "
                    f"constraint_edges={boundary_loop_constraint_edges}"
                ),
                str(row.get("boundary_loop_ownership_notes", "") or ""),
            )
            output.append(detail)
        roundabout_clip_boundary_role = str(row.get("roundabout_clip_boundary_role", "") or "")
        roundabout_clip_boundary_status = str(row.get("roundabout_clip_boundary_status", "") or "")
        roundabout_actual_clip_boundary_roles = [
            str(value or "").strip()
            for value in list(row.get("roundabout_actual_clip_boundary_roles", []) or [])
            if str(value or "").strip()
        ]
        roundabout_clip_boundary_is_diagnostic_only = bool(
            roundabout_clip_boundary_role
            and roundabout_actual_clip_boundary_roles
            and roundabout_clip_boundary_role not in set(roundabout_actual_clip_boundary_roles)
        )
        roundabout_clip_mode = str(row.get("roundabout_clip_mode", "") or "")
        roundabout_clip_reason_summary = str(row.get("roundabout_clip_reason_summary", "") or "")
        roundabout_clip_boundary_loop_count = int(row.get("roundabout_clip_boundary_loop_count", 0) or 0)
        roundabout_clip_boundary_segment_count = int(row.get("roundabout_clip_boundary_segment_count", 0) or 0)
        roundabout_clip_boundary_approach_leg_count = int(row.get("roundabout_clip_boundary_approach_leg_count", 0) or 0)
        roundabout_clip_boundary_approach_leg_roles = [
            str(value or "")
            for value in list(row.get("roundabout_clip_boundary_approach_leg_roles", []) or [])
            if str(value or "")
        ]
        roundabout_clip_boundary_approach_leg_source = str(row.get("roundabout_clip_boundary_approach_leg_source", "") or "")
        if roundabout_clip_boundary_role or roundabout_clip_boundary_status:
            consumer_pairs = _roundabout_clip_boundary_consumer_pairs(
                str(row.get("role", "") or ""),
                roundabout_clip_boundary_role,
            )
            detail = dict(row)
            detail["row_kind"] = (
                "roundabout_clip_boundary_diagnostic"
                if roundabout_clip_boundary_is_diagnostic_only
                else "roundabout_clip_boundary"
            )
            detail["surface"] = (
                "  Roundabout Diagnostic Boundary"
                if roundabout_clip_boundary_is_diagnostic_only
                else "  Roundabout Clip Boundary"
            )
            detail["status"] = roundabout_clip_boundary_status or "missing"
            detail["consumed"] = roundabout_clip_boundary_segment_count
            detail["total"] = max(roundabout_clip_boundary_segment_count, roundabout_clip_boundary_loop_count)
            detail["material_summary"] = (
                "roundabout_diagnostic_boundary"
                if roundabout_clip_boundary_is_diagnostic_only
                else "roundabout_clip_boundary"
            )
            detail["role_summary"] = (
                f"role={roundabout_clip_boundary_role or 'missing'}, "
                f"loops={roundabout_clip_boundary_loop_count}, "
                f"segments={roundabout_clip_boundary_segment_count}, "
                f"approach_legs={roundabout_clip_boundary_approach_leg_count}, "
                f"approach_roles={','.join(roundabout_clip_boundary_approach_leg_roles) if roundabout_clip_boundary_approach_leg_roles else 'none'}, "
                f"mode={roundabout_clip_mode or 'missing'}, "
                f"actual_clip_roles={','.join(roundabout_actual_clip_boundary_roles) if roundabout_actual_clip_boundary_roles else 'none'}, "
                f"reasons={roundabout_clip_reason_summary or 'none'}, "
                f"consumer_pairs={' | '.join(consumer_pairs)}"
            )
            detail["breakline_role_filter"] = (
                ""
                if roundabout_clip_boundary_is_diagnostic_only
                else roundabout_clip_boundary_role or "roundabout_clip_boundary"
            )
            detail["graph_edge_refs"] = (
                []
                if roundabout_clip_boundary_is_diagnostic_only
                else list(row.get("roundabout_clip_boundary_segment_refs", []) or [])
            )
            detail["recommended_action"] = (
                "No action needed - diagnostic handoff boundary is not used for ordinary surface clipping"
                if roundabout_clip_boundary_is_diagnostic_only
                else
                "Review roundabout clip boundary loops, then rebuild ordinary surfaces"
                if str(detail["status"]) != "ready"
                else "No action needed"
            )
            detail["notes"] = _join_review_notes(
                str(detail.get("notes", "") or ""),
                (
                    "roundabout_clip_boundary_handoff="
                    f"result={str(row.get('roundabout_clip_boundary_result_id', '') or '')}; "
                    f"role={roundabout_clip_boundary_role or 'missing'}; "
                    f"status={roundabout_clip_boundary_status or 'missing'}; "
                    f"loops={roundabout_clip_boundary_loop_count}; "
                    f"segments={roundabout_clip_boundary_segment_count}; "
                    f"approach_legs={roundabout_clip_boundary_approach_leg_count}; "
                    f"approach_roles={','.join(roundabout_clip_boundary_approach_leg_roles) if roundabout_clip_boundary_approach_leg_roles else 'none'}; "
                    f"approach_source={roundabout_clip_boundary_approach_leg_source or 'missing'}; "
                    f"mode={roundabout_clip_mode or 'missing'}; "
                    f"actual_clip_roles={','.join(roundabout_actual_clip_boundary_roles) if roundabout_actual_clip_boundary_roles else 'none'}; "
                    f"diagnostic_only={'yes' if roundabout_clip_boundary_is_diagnostic_only else 'no'}; "
                    f"reasons={roundabout_clip_reason_summary or 'none'}; "
                    f"consumer_pairs={' | '.join(consumer_pairs)}"
                ),
            )
            output.append(detail)
            if roundabout_clip_boundary_is_diagnostic_only:
                continue
            leg_roles = roundabout_clip_boundary_approach_leg_roles or ["unassigned"]
            per_leg_total = (
                max(1, roundabout_clip_boundary_segment_count // len(leg_roles))
                if leg_roles
                else roundabout_clip_boundary_segment_count
            )
            for approach_role in leg_roles:
                leg_detail = dict(row)
                leg_detail["row_kind"] = "roundabout_clip_boundary_leg"
                leg_detail["surface"] = f"  Roundabout Clip Boundary - {approach_role}"
                leg_status = roundabout_clip_boundary_status or "missing"
                if (
                    int(row.get("geometry_mismatch_count", 0) or 0)
                    or int(row.get("mesh_mismatch_count", 0) or 0)
                    or int(row.get("missing_consumer_count", 0) or 0)
                ):
                    leg_status = "warning"
                leg_detail["status"] = leg_status
                leg_detail["consumed"] = per_leg_total if leg_status == "ready" else 0
                leg_detail["total"] = max(1, per_leg_total)
                leg_detail["material_summary"] = "roundabout_clip_boundary_leg"
                leg_detail["role_summary"] = (
                    f"role={roundabout_clip_boundary_role or 'missing'}, "
                    f"approach_role={approach_role}, "
                    f"mode={roundabout_clip_mode or 'missing'}, "
                    f"consumer_pairs={' | '.join(consumer_pairs)}"
                )
                leg_detail["breakline_role_filter"] = f"{roundabout_clip_boundary_role or 'roundabout_clip_boundary'}:{approach_role}"
                leg_detail["graph_edge_refs"] = _roundabout_clip_boundary_leg_segment_refs(
                    row.get("roundabout_clip_boundary_segment_refs", []),
                    approach_role,
                )
                leg_detail["recommended_action"] = (
                    "Review this roundabout approach clip boundary, then rebuild ordinary surfaces"
                    if str(leg_detail["status"]) != "ready"
                    else "No action needed"
                )
                leg_detail["notes"] = _join_review_notes(
                    str(leg_detail.get("notes", "") or ""),
                    (
                        "roundabout_clip_boundary_leg_handoff="
                        f"result={str(row.get('roundabout_clip_boundary_result_id', '') or '')}; "
                        f"role={roundabout_clip_boundary_role or 'missing'}; "
                        f"approach_role={approach_role}; "
                        f"status={roundabout_clip_boundary_status or 'missing'}; "
                        f"segments={per_leg_total}; "
                        f"approach_source={roundabout_clip_boundary_approach_leg_source or 'missing'}; "
                        f"consumer_pairs={' | '.join(consumer_pairs)}"
                    ),
                )
                output.append(leg_detail)
        graph_edge_count = int(row.get("graph_edge_count", 0) or 0)
        graph_cell_count = int(row.get("graph_cell_count", 0) or 0)
        if graph_edge_count or graph_cell_count or str(row.get("graph_status", "") or ""):
            detail = dict(row)
            detail["row_kind"] = "graph"
            detail["surface"] = "  Shared Boundary Graph"
            detail["status"] = (
                "warning"
                if int(row.get("graph_duplicate_edge_count", 0) or 0)
                or int(row.get("graph_missing_consumer_count", 0) or 0)
                or int(row.get("graph_open_cell_count", 0) or 0)
                or int(row.get("graph_endpoint_mismatch_count", 0) or 0)
                or int(row.get("graph_not_snapped_count", 0) or 0)
                or int(row.get("graph_foreign_edge_count", 0) or 0)
                or int(row.get("graph_pair_missing_count", 0) or 0)
                else str(row.get("graph_status", "") or "ready")
            )
            detail["consumed"] = int(row.get("graph_consumed_edge_count", 0) or graph_edge_count)
            detail["total"] = graph_edge_count
            detail["material_summary"] = "intersection_shared_boundary_graph"
            detail["graph_edge_refs"] = _shared_boundary_graph_edge_refs_from_audit_row(row)
            detail["role_summary"] = (
                f"nodes={int(row.get('graph_node_count', 0) or 0)}, "
                f"edges={graph_edge_count}, consumed_edges={int(row.get('graph_consumed_edge_count', 0) or 0)}, cells={graph_cell_count}, "
                f"duplicate_edges={int(row.get('graph_duplicate_edge_count', 0) or 0)}, "
                f"missing_consumers={int(row.get('graph_missing_consumer_count', 0) or 0)}, "
                f"open_cells={int(row.get('graph_open_cell_count', 0) or 0)}, "
                f"endpoint_mismatch={int(row.get('graph_endpoint_mismatch_count', 0) or 0)}, "
                f"not_snapped={int(row.get('graph_not_snapped_count', 0) or 0)}, "
                f"foreign_edges={int(row.get('graph_foreign_edge_count', 0) or 0)}, "
                f"pair_missing={int(row.get('graph_pair_missing_count', 0) or 0)}"
            )
            detail["breakline_role_filter"] = "intersection_shared_boundary_graph"
            detail["recommended_action"] = (
                "Review Shared Boundary Graph, then rebuild surfaces"
                if str(detail["status"]) == "warning"
                else "No action needed"
            )
            if str(row.get("graph_pair_notes", "") or ""):
                detail["notes"] = _join_review_notes(
                    str(detail.get("notes", "") or ""),
                    f"graph_pair_audit={row.get('graph_pair_notes', '')}",
                )
            if str(row.get("graph_foreign_edge_notes", "") or ""):
                detail["notes"] = _join_review_notes(
                    str(detail.get("notes", "") or ""),
                    str(row.get("graph_foreign_edge_notes", "") or ""),
                    )
            output.append(detail)
            output.extend(_boundary_loop_owner_summary_display_rows(row))
            for pair_note in _parse_shared_boundary_graph_pair_notes(str(row.get("graph_pair_notes", "") or "")):
                pair_detail = dict(row)
                pair_detail["row_kind"] = "graph_pair"
                pair_detail["surface"] = f"    Graph Pair: {pair_note['edge_role']}"
                pair_detail["status"] = "warning" if pair_note["status"] == "missing" else "ready"
                pair_detail["consumed"] = int(pair_note.get("match_count", 0) or 0)
                pair_detail["total"] = 1
                pair_detail["material_summary"] = "intersection_shared_boundary_graph_pair"
                pair_detail["role_summary"] = f"{pair_note['first_role']}<->{pair_note['second_role']}"
                pair_detail["breakline_role_filter"] = "intersection_shared_boundary_graph_pair"
                pair_detail["graph_edge_refs"] = _shared_boundary_graph_edge_refs_from_audit_row(
                    row,
                    role_filter=str(pair_note.get("edge_role", "") or ""),
                )
                pair_detail["recommended_action"] = (
                    "Review this graph consumer pair, then rebuild surfaces"
                    if pair_note["status"] == "missing"
                    else "No action needed"
                )
                pair_detail["notes"] = _join_review_notes(
                    f"edge_role={pair_note['edge_role']}",
                    f"surface_pair={pair_note['first_role']}<->{pair_note['second_role']}",
                    f"status={pair_note['status']}",
                )
                output.append(pair_detail)
        for raw_graph in list(row.get("graph_audit_rows", []) or []):
            parsed = _parse_intersection_shared_boundary_graph_audit_row(raw_graph)
            if parsed is None:
                continue
            is_internal_seam = (
                str(parsed.get("row_kind", "") or "") == "edge"
                and _intersection_shared_boundary_graph_edge_role_is_internal_seam(str(parsed.get("role", "") or ""))
            )
            if (
                str(parsed.get("row_kind", "") or "") == "edge"
                and _intersection_boundary_loop_source_refs(str(parsed.get("source_refs", "") or ""))
            ):
                owner_refs = _intersection_boundary_owner_source_refs(str(parsed.get("source_refs", "") or ""))
                owner_consumers = _intersection_boundary_owner_consumer_summary(
                    owner_refs,
                    str(parsed.get("refs", "") or ""),
                )
                owner_missing_consumers = _intersection_boundary_owner_missing_consumer_summary(
                    owner_refs,
                    str(parsed.get("role", "") or ""),
                    str(parsed.get("refs", "") or ""),
                )
                boundary_detail = dict(row)
                boundary_detail["row_kind"] = "graph_boundary_loop"
                boundary_detail["surface"] = f"    Boundary Loop Edge: {parsed['role']}"
                boundary_detail["status"] = (
                    "warning"
                    if str(parsed.get("diagnostics", "") or "") or owner_missing_consumers
                    else "ready"
                )
                boundary_detail["consumed"] = 0 if str(boundary_detail["status"]) == "warning" else 1
                boundary_detail["total"] = 1
                boundary_detail["material_summary"] = "intersection_boundary_loop"
                boundary_detail["role_summary"] = str(parsed.get("refs", "") or "")
                boundary_detail["breakline_role_filter"] = "intersection_boundary_loop"
                boundary_detail["graph_edge_refs"] = [str(parsed.get("row_id", "") or "")]
                boundary_detail["recommended_action"] = (
                    "Review boundary-loop shared consumers, then rebuild surfaces"
                    if str(boundary_detail["status"]) == "warning"
                    else "No action needed"
                )
                boundary_detail["notes"] = _join_review_notes(
                    f"edge_id={parsed.get('row_id', '')}",
                    f"edge_role={parsed.get('role', '')}",
                    f"source_refs={parsed.get('source_refs', '')}",
                    f"owner_refs={','.join(owner_refs)}" if owner_refs else "",
                    f"owner_consumers={owner_consumers}" if owner_consumers else "",
                    f"owner_missing_consumers={owner_missing_consumers}" if owner_missing_consumers else "",
                    f"consumers={parsed.get('refs', '')}",
                    f"diagnostics={parsed.get('diagnostics', '')}" if parsed.get("diagnostics", "") else "",
                )
                output.append(boundary_detail)
            if is_internal_seam:
                seam_detail = dict(row)
                seam_detail["row_kind"] = "graph_internal_seam"
                seam_detail["surface"] = f"    Internal Seam: {parsed['role']}"
                seam_detail["status"] = "warning" if str(parsed.get("diagnostics", "") or "") else "ready"
                seam_detail["consumed"] = 0 if str(seam_detail["status"]) == "warning" else 1
                seam_detail["total"] = 1
                seam_detail["material_summary"] = "intersection_shared_boundary_graph_internal_seam"
                seam_detail["role_summary"] = str(parsed.get("refs", "") or "")
                seam_detail["breakline_role_filter"] = "intersection_shared_boundary_graph_internal_seam"
                seam_detail["graph_edge_refs"] = [str(parsed.get("row_id", "") or "")]
                seam_detail["recommended_action"] = (
                    "Review internal cell closure seam, then rebuild surfaces"
                    if str(seam_detail["status"]) == "warning"
                    else "No action needed"
                )
                seam_detail["notes"] = _join_review_notes(
                    f"edge_id={parsed.get('row_id', '')}",
                    f"edge_role={parsed.get('role', '')}",
                    f"consumers={parsed.get('refs', '')}",
                    f"diagnostics={parsed.get('diagnostics', '')}" if parsed.get("diagnostics", "") else "",
                )
                output.append(seam_detail)
            graph_detail = dict(row)
            graph_detail["row_kind"] = f"graph_{parsed['row_kind']}"
            graph_detail["surface"] = f"    Graph {parsed['row_kind']}: {parsed['role']}"
            graph_detail["status"] = "warning" if str(parsed.get("diagnostics", "") or "") or int(parsed.get("open_count", 0) or 0) else "ready"
            graph_detail["consumed"] = 0 if str(graph_detail["status"]) == "warning" else 1
            graph_detail["total"] = 1
            graph_detail["material_summary"] = "intersection_shared_boundary_graph"
            graph_detail["role_summary"] = str(parsed.get("refs", "") or "")
            graph_detail["breakline_role_filter"] = "intersection_shared_boundary_graph"
            if str(parsed.get("row_kind", "") or "") == "edge":
                graph_detail["graph_edge_refs"] = [str(parsed.get("row_id", "") or "")]
            elif str(parsed.get("row_kind", "") or "") == "cell":
                graph_detail["graph_edge_refs"] = [
                    value.strip()
                    for value in str(parsed.get("refs", "") or "").split(",")
                    if value.strip()
                ]
            graph_detail["recommended_action"] = (
                "Review this graph boundary, then rebuild surfaces"
                if str(graph_detail["status"]) == "warning"
                else "No action needed"
            )
            graph_detail["notes"] = _join_review_notes(
                f"id={parsed.get('row_id', '')}",
                f"refs={parsed.get('refs', '')}" if parsed.get("refs", "") else "",
                f"diagnostics={parsed.get('diagnostics', '')}" if parsed.get("diagnostics", "") else "",
            )
            output.append(graph_detail)
        cell_count = int(row.get("cell_count", 0) or 0)
        if cell_count:
            detail = dict(row)
            detail["row_kind"] = "cell"
            detail["surface"] = "  Cell Audit: Intersection Slope Face"
            detail["consumed"] = int(row.get("cell_ready_count", 0) or 0)
            detail["total"] = cell_count
            detail["material_summary"] = "intersection_slope_face_cell"
            detail["role_summary"] = (
                f"ready={int(row.get('cell_ready_count', 0) or 0)}, "
                f"open={int(row.get('cell_open_count', 0) or 0)}, "
                f"missing_edge={int(row.get('cell_missing_edge_count', 0) or 0)}, "
                f"triangles={int(row.get('cell_triangle_count', 0) or 0)}"
            )
            detail["breakline_role_filter"] = "intersection_slope_face_cell"
            detail["recommended_action"] = (
                "Review Intersection Slope Face cells, then rebuild"
                if int(row.get("cell_open_count", 0) or 0) or int(row.get("cell_missing_edge_count", 0) or 0)
                else "No action needed"
            )
            output.append(detail)
            for raw_cell in list(row.get("cell_audit_rows", []) or []):
                parsed = _parse_intersection_slope_face_cell_audit_row(raw_cell)
                if parsed is None:
                    continue
                cell_detail = dict(row)
                cell_detail["row_kind"] = "cell_detail"
                cell_detail["surface"] = f"    Cell: {parsed['cell_role']}"
                cell_detail["status"] = "warning" if int(parsed.get("open_count", 0) or 0) or int(parsed.get("missing_edge_count", 0) or 0) else str(parsed.get("status", "") or "ready")
                cell_detail["consumed"] = 0 if str(cell_detail["status"]) == "warning" else 1
                cell_detail["total"] = 1
                cell_detail["material_summary"] = "intersection_slope_face_cell"
                cell_detail["role_summary"] = str(parsed.get("boundary_refs", "") or "")
                cell_detail["breakline_role_filter"] = "intersection_slope_face_cell"
                cell_detail["recommended_action"] = (
                    "Review this cell boundary refs, then rebuild"
                    if str(cell_detail["status"]) == "warning"
                    else "No action needed"
                )
                cell_detail["notes"] = _join_review_notes(
                    f"cell_id={parsed.get('cell_id', '')}",
                    f"open={parsed.get('open_count', 0)}",
                    f"missing_edge={parsed.get('missing_edge_count', 0)}",
                    f"points={parsed.get('point_count', 0)}",
                    f"diagnostics={parsed.get('diagnostics', '')}" if parsed.get("diagnostics", "") else "",
                )
                output.append(cell_detail)
    return output


def _boundary_loop_owner_summary_display_rows(row: dict[str, object]) -> list[dict[str, object]]:
    owner_rows: dict[str, dict[str, object]] = {}
    for raw_graph in list(row.get("graph_audit_rows", []) or []):
        parsed = _parse_intersection_shared_boundary_graph_audit_row(raw_graph)
        if (
            parsed is None
            or str(parsed.get("row_kind", "") or "") != "edge"
            or not _intersection_boundary_loop_source_refs(str(parsed.get("source_refs", "") or ""))
        ):
            continue
        owner_refs = _intersection_boundary_owner_source_refs(str(parsed.get("source_refs", "") or ""))
        if not owner_refs:
            continue
        consumers = {
            str(value or "").strip()
            for value in str(parsed.get("refs", "") or "").split(",")
            if str(value or "").strip()
        }
        missing_summary = _intersection_boundary_owner_missing_consumer_summary(
            owner_refs,
            str(parsed.get("role", "") or ""),
            str(parsed.get("refs", "") or ""),
        )
        for owner_ref in owner_refs:
            owner = owner_rows.setdefault(
                owner_ref,
                {"edge_count": 0, "consumers": set(), "missing": [], "roles": set(), "edge_refs": []},
            )
            owner["edge_count"] = int(owner.get("edge_count", 0) or 0) + 1
            owner["consumers"].update(consumers)
            owner["roles"].add(str(parsed.get("role", "") or ""))
            owner["edge_refs"].append(str(parsed.get("row_id", "") or ""))
            if missing_summary:
                owner["missing"].append(missing_summary)
    output: list[dict[str, object]] = []
    for owner_ref in sorted(owner_rows):
        owner = owner_rows[owner_ref]
        missing = _unique_text_values([str(value or "") for value in list(owner.get("missing", []) or []) if str(value or "")])
        consumers = sorted(str(value or "") for value in owner.get("consumers", set()) if str(value or ""))
        roles = sorted(str(value or "") for value in owner.get("roles", set()) if str(value or ""))
        edge_refs = _unique_text_values([str(value or "") for value in list(owner.get("edge_refs", []) or []) if str(value or "")])
        detail = dict(row)
        detail["row_kind"] = "graph_boundary_owner"
        detail["surface"] = f"    Boundary Owner: {owner_ref}"
        detail["status"] = "warning" if missing else "ready"
        detail["consumed"] = int(owner.get("edge_count", 0) or 0)
        detail["total"] = int(owner.get("edge_count", 0) or 0)
        detail["material_summary"] = "intersection_boundary_owner"
        detail["role_summary"] = (
            f"edges={int(owner.get('edge_count', 0) or 0)}, "
            f"roles={','.join(roles)}, consumers={'+'.join(consumers) if consumers else 'none'}"
        )
        detail["breakline_role_filter"] = "intersection_boundary_owner"
        detail["graph_edge_refs"] = edge_refs
        detail["recommended_action"] = (
            "Review owner boundary-loop consumers, then rebuild surfaces"
            if missing
            else "No action needed"
        )
        detail["notes"] = _join_review_notes(
            f"owner_ref={owner_ref}",
            f"edge_refs={','.join(edge_refs)}",
            f"roles={','.join(roles)}",
            f"consumers={'+'.join(consumers) if consumers else 'none'}",
            f"owner_missing_consumers={';'.join(missing)}" if missing else "",
        )
        output.append(detail)
    return output


def _shared_breakline_recommended_action_from_notes(notes: str) -> str:
    text = str(notes or "")
    if not text:
        return ""
    if "patch-to-slope-face" in text or "patch_to_slope_face" in text:
        return "Rebuild Intersection and Slope Face constraints"
    if "curb_return_to_slope_face" in text or "curb-return-to-slope-face" in text:
        return "Rebuild Intersection and Slope Face constraints"
    if "patch-to-design" in text or "patch_to_design" in text:
        return "Rebuild Intersection and Design constraints"
    if "curb_return_to_pavement" in text or "curb-return-to-pavement" in text:
        return "Rebuild Intersection and Design constraints"
    if "curb_return_to_shoulder" in text or "curb-return-to-shoulder" in text:
        return "Rebuild Intersection and Design constraints"
    if "patch-to-shoulder" in text or "patch_to_shoulder" in text:
        return "Rebuild Intersection and Design constraints"
    if "shoulder-to-slope-face" in text or "shoulder_to_slope_face" in text:
        return "Rebuild Applied Sections, then constrained surfaces"
    if "curb_return_inner" in text or "curb-return-inner" in text or "curb_return_outer" in text or "curb-return-outer" in text:
        return "Rebuild Intersection curb-return constraints"
    if (
        "region-transition" in text
        or "region_start_boundary" in text
        or "region_end_boundary" in text
        or "assembly_change_boundary" in text
        or "surface_transition_boundary" in text
    ):
        return "Review Region spans, then Build Parametric"
    if (
        "control_area_entry" in text
        or "control-area-entry" in text
        or "control_area_exit" in text
        or "control-area-exit" in text
        or "region_to_intersection_control" in text
        or "region-to-intersection-control" in text
    ):
        return "Review Intersection control areas and Region spans, then Build Parametric"
    if (
        "lane_to_lane" in text
        or "lane_to_shoulder" in text
        or "shoulder_edge" in text
        or "shoulder_to_side_slope" in text
        or "side_slope_to_daylight" in text
    ):
        return "Rebuild Applied Sections, then constrained surfaces"
    if (
        "intersection_gutter_handoff" in text
        or "intersection-gutter-handoff" in text
        or "intersection_ditch_handoff" in text
        or "intersection-ditch-handoff" in text
        or "low_point_flow_split" in text
        or "low-point-flow-split" in text
        or "drainage_capture_edge" in text
        or "drainage-capture-edge" in text
    ):
        return "Review Intersection Drainage source, then rebuild Intersection"
    if (
        "corridor_gutter_handoff" in text
        or "corridor-ditch-handoff" in text
        or "corridor_ditch_handoff" in text
        or "corridor-gutter-handoff" in text
    ):
        return "Review Drainage source, then rebuild Applied Sections"
    return ""


def _parse_intersection_shared_boundary_graph_audit_row(raw: object) -> dict[str, object] | None:
    parts = str(raw or "").split("|")
    if len(parts) < 7:
        return None
    row_kind = parts[0] or ""
    if row_kind == "edge":
        return {
            "row_kind": "edge",
            "row_id": parts[1],
            "role": parts[2],
            "from_node_ref": parts[3],
            "to_node_ref": parts[4],
            "refs": parts[5],
            "diagnostics": parts[6],
            "source_refs": parts[7] if len(parts) > 7 else "",
            "open_count": 0,
        }
    if row_kind == "cell":
        closed = str(parts[3] or "") == "1"
        return {
            "row_kind": "cell",
            "row_id": parts[1],
            "role": parts[2],
            "closed": closed,
            "owner_surface_ref": parts[4],
            "refs": parts[5],
            "diagnostics": parts[6],
            "source_refs": parts[7] if len(parts) > 7 else "",
            "open_count": 0 if closed else 1,
        }
    if row_kind == "graph":
        return {
            "row_kind": "graph",
            "row_id": parts[1],
            "role": "shared_boundary_graph",
            "refs": "",
            "diagnostics": parts[1],
            "source_refs": "",
            "open_count": 0,
        }
    return None


def _parse_shared_boundary_graph_pair_notes(notes: str) -> list[dict[str, object]]:
    """Parse graph pair audit notes into panel detail rows."""

    rows: list[dict[str, object]] = []
    for raw in str(notes or "").split(";"):
        text = str(raw or "").strip()
        if not text:
            continue
        parts = text.split(":")
        if len(parts) < 3 or parts[0] not in {"pair_match", "pair_missing"}:
            continue
        pair_parts = parts[2].split("<->", 1)
        if len(pair_parts) != 2:
            continue
        match_count = 0
        if parts[0] == "pair_match" and len(parts) >= 4:
            try:
                match_count = int(parts[3] or 0)
            except Exception:
                match_count = 0
        rows.append(
            {
                "status": "ready" if parts[0] == "pair_match" else "missing",
                "edge_role": parts[1],
                "first_role": pair_parts[0],
                "second_role": pair_parts[1],
                "match_count": match_count,
            }
        )
    return rows


def _parse_intersection_slope_face_cell_audit_row(raw: object) -> dict[str, object] | None:
    parts = str(raw or "").split("|")
    if len(parts) < 8:
        return None
    try:
        open_count = int(parts[3] or 0)
    except Exception:
        open_count = 0
    try:
        missing_edge_count = int(parts[4] or 0)
    except Exception:
        missing_edge_count = 0
    try:
        point_count = int(parts[5] or 0)
    except Exception:
        point_count = 0
    return {
        "cell_id": parts[0],
        "cell_role": parts[1],
        "status": parts[2] or "missing",
        "open_count": open_count,
        "missing_edge_count": missing_edge_count,
        "point_count": point_count,
        "boundary_refs": parts[6],
        "diagnostics": parts[7],
    }


def _shared_boundary_graph_edge_refs_from_audit_row(
    row: dict[str, object],
    *,
    role_filter: str = "",
    source_ref_filter: str = "",
) -> list[str]:
    refs: list[str] = []
    role_text = str(role_filter or "").strip()
    source_text = str(source_ref_filter or "").strip()
    for raw_graph in list(row.get("graph_audit_rows", []) or []):
        parsed = _parse_intersection_shared_boundary_graph_audit_row(raw_graph)
        if parsed is None or str(parsed.get("row_kind", "") or "") != "edge":
            continue
        if role_text and str(parsed.get("role", "") or "") != role_text:
            continue
        if source_text and source_text not in str(parsed.get("source_refs", "") or ""):
            continue
        edge_id = str(parsed.get("row_id", "") or "").strip()
        if edge_id:
            refs.append(edge_id)
    return _unique_text_values(refs)


def _roundabout_clip_boundary_consumer_pairs(surface_role: str, boundary_role: str) -> list[str]:
    role = str(surface_role or "").strip().lower()
    boundary = str(boundary_role or "").strip().lower()
    if role == "design" or boundary == "roundabout_approach_clip_boundary":
        return [
            "Design Surface <-> Roundabout Circulatory Surface",
            "Design Surface <-> Roundabout Apron Surface",
            "Approach Shoulder Review <-> Roundabout Apron Surface",
        ]
    if role == "subgrade" or boundary == "roundabout_subgrade_clip_boundary":
        return ["Subgrade Surface <-> Roundabout Subgrade Surface"]
    if role == "daylight" or boundary == "roundabout_slope_handoff_boundary":
        return [
            "Slope Face Surface <-> Roundabout Slope Face Surface",
            "Side Slope Review <-> Roundabout Slope Face Surface",
        ]
    return ["Roundabout Clip Boundary <-> Ordinary Surface"]


def _shared_breakline_summary_count_items(summary: str) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for part in str(summary or "").split(","):
        text = str(part or "").strip()
        if not text or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        try:
            count = int(str(value or "0").strip() or 0)
        except Exception:
            count = 0
        if key:
            items.append((key, count))
    return items


def _intersection_boundary_owner_missing_consumer_summary(owner_refs: list[str], role: str, consumers: str) -> str:
    owners = [str(value or "").strip() for value in list(owner_refs or []) if str(value or "").strip()]
    expected = INTERSECTION_SHARED_BOUNDARY_EXPECTED_CONSUMERS.get(str(role or ""), ())
    if not owners or not expected:
        return ""
    consumer_refs = {
        str(value or "").strip()
        for value in str(consumers or "").split(",")
        if str(value or "").strip()
    }
    missing = [str(value or "") for value in tuple(expected or ()) if str(value or "") and str(value or "") not in consumer_refs]
    if not missing:
        return ""
    missing_text = "+".join(_unique_text_values(missing))
    return ",".join(f"{owner}->{missing_text}" for owner in _unique_text_values(owners))


def _roundabout_clip_boundary_leg_segment_refs(segment_refs: object, approach_role: str) -> list[str]:
    refs = [str(value or "") for value in list(segment_refs or []) if str(value or "")]
    role = str(approach_role or "").strip()
    if not role:
        return refs
    tokens = {
        role,
        role.replace("-", "_"),
        role.replace("_", "-"),
    }
    filtered = [ref for ref in refs if any(token and token in ref for token in tokens)]
    return filtered or refs


def _intersection_boundary_owner_consumer_summary(owner_refs: list[str], consumers: str) -> str:
    owners = [str(value or "").strip() for value in list(owner_refs or []) if str(value or "").strip()]
    consumer_refs = [
        str(value or "").strip()
        for value in str(consumers or "").split(",")
        if str(value or "").strip()
    ]
    if not owners or not consumer_refs:
        return ""
    consumer_text = "+".join(_unique_text_values(consumer_refs))
    return ",".join(f"{owner}->{consumer_text}" for owner in _unique_text_values(owners))


def _intersection_boundary_loop_source_refs(source_refs: str) -> list[str]:
    return [
        value.strip()
        for value in str(source_refs or "").split(",")
        if value.strip()
        and (
            "intersection-boundary-loop" in value.strip()
            or "intersection-boundary-loops" in value.strip()
        )
    ]


def _intersection_tie_slope_window_role_counts_from_audit_row(row: dict[str, object]) -> dict[str, int]:
    role_counts = {
        role: count
        for role, count in _shared_breakline_summary_count_items(str(row.get("role_summary", "") or ""))
        if role in INTERSECTION_TIE_SLOPE_WINDOW_BREAKLINE_ROLES
    }
    return role_counts


def _intersection_boundary_owner_source_refs(source_refs: str) -> list[str]:
    return [
        value.strip()
        for value in str(source_refs or "").split(",")
        if value.strip().startswith("intersection-boundary-owner:")
    ]


def _intersection_shared_boundary_graph_edge_role_is_internal_seam(role: str) -> bool:
    return str(role or "") in {"upper_transition_internal_seam", "cell_closure_internal_seam"}


CORRIDOR_BUILD_REVIEW_STATUS_VALUES = ("ready", "warning", "missing", "empty", "error")


def _normalize_corridor_build_review_status(status: str, *, default: str = "missing") -> str:
    value = str(status or "").strip().lower()
    if value == "warn":
        value = "warning"
    if value == "not_built":
        value = "missing"
    if value in CORRIDOR_BUILD_REVIEW_STATUS_VALUES:
        return value
    return str(default or "missing")


def _boundary_loop_near_kept_warning_threshold(tested_triangle_count: int) -> int:
    return max(30, int(math.ceil(float(tested_triangle_count or 0) * 0.50)))


def _boundary_loop_near_kept_warning(role: str, *, near_kept_count: int, tested_triangle_count: int) -> bool:
    if str(role or "") not in {"design", "daylight"}:
        return False
    if int(tested_triangle_count or 0) <= 0:
        return False
    return int(near_kept_count or 0) >= _boundary_loop_near_kept_warning_threshold(tested_triangle_count)


def _shared_breakline_recommended_action(
    *,
    geometry_mismatch_count: int,
    missing_consumer_count: int,
    mismatch_count: int,
    reversed_edge_count: int,
    mesh_mismatch_count: int = 0,
    cell_open_count: int = 0,
    cell_missing_edge_count: int = 0,
    graph_duplicate_edge_count: int = 0,
    graph_missing_consumer_count: int = 0,
    graph_source_segment_split_count: int = 0,
    graph_open_cell_count: int = 0,
    graph_not_snapped_count: int = 0,
    graph_endpoint_mismatch_count: int = 0,
    graph_foreign_edge_count: int = 0,
    graph_pair_missing_count: int = 0,
    notes: str = "",
) -> str:
    if int(graph_pair_missing_count or 0) > 0:
        return "Review Shared Boundary Graph consumer pairs, then rebuild surfaces"
    if int(graph_foreign_edge_count or 0) > 0:
        return "Review Shared Boundary Graph consumer ownership, then rebuild surfaces"
    if int(graph_endpoint_mismatch_count or 0) > 0 or int(graph_not_snapped_count or 0) > 0:
        return "Rebuild Shared Boundary Graph from canonical source edges"
    if int(graph_source_segment_split_count or 0) > 0:
        return "Unify shared boundary source segments, then rebuild surfaces"
    if int(graph_duplicate_edge_count or 0) > 0 or int(graph_missing_consumer_count or 0) > 0 or int(graph_open_cell_count or 0) > 0:
        return "Review Shared Boundary Graph, then rebuild surfaces"
    if int(cell_open_count or 0) > 0 or int(cell_missing_edge_count or 0) > 0:
        return "Review Intersection Slope Face cells, then rebuild"
    if int(mismatch_count or 0) > 0:
        return "Review Intersection Source"
    if int(missing_consumer_count or 0) > 0:
        return "Rebuild Build Parametric"
    role_action = _shared_breakline_recommended_action_from_notes(notes)
    if role_action:
        return role_action
    if int(mesh_mismatch_count or 0) > 0:
        return "Rebuild constrained surface mesh"
    if int(geometry_mismatch_count or 0) > 0:
        return "Rebuild Applied Sections, then Build Parametric"
    if int(reversed_edge_count or 0) > 0:
        return "Monitor; check Watertight normals if needed"
    return "No action needed"


def _shared_boundary_graph_consumer_audit_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Mark graph refs that are not owned by the surface consumer represented by a row."""

    if not rows:
        return []
    consumer_by_role = {
        "design": "design_surface",
        "intersection": "intersection_surface",
        "daylight": "slope_face_surface",
        "intersection_slope": "intersection_slope_face_surface",
    }
    edge_consumers: dict[str, set[str]] = {}
    for row in rows:
        for raw in list(row.get("graph_audit_rows", []) or []):
            parsed = _parse_intersection_shared_boundary_graph_audit_row(raw)
            if not parsed or str(parsed.get("row_kind", "") or "") != "edge":
                continue
            edge_id = str(parsed.get("row_id", "") or "")
            consumers = {
                str(value or "").strip()
                for value in str(parsed.get("refs", "") or "").split(",")
                if str(value or "").strip()
            }
            if edge_id:
                edge_consumers.setdefault(edge_id, set()).update(consumers)
    output: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        role = str(row.get("role", "") or "")
        consumer_ref = consumer_by_role.get(role, "")
        graph_refs = {str(value or "") for value in list(row.get("graph_refs", []) or []) if str(value or "")}
        foreign_refs = []
        if consumer_ref:
            for edge_ref in sorted(graph_refs):
                consumers = edge_consumers.get(edge_ref)
                if not consumers or consumer_ref not in consumers:
                    foreign_refs.append(edge_ref)
        updated["graph_foreign_edge_count"] = len(foreign_refs)
        updated["graph_foreign_edge_notes"] = "; ".join(
            f"shared_boundary_surface_owns_foreign_edge:{role}:{edge_ref}"
            for edge_ref in foreign_refs
        )
        if foreign_refs:
            updated["status"] = "warning"
            updated["recommended_action"] = "Review Shared Boundary Graph consumer ownership, then rebuild surfaces"
            updated["notes"] = _join_review_notes(
                str(updated.get("notes", "") or ""),
                str(updated.get("graph_foreign_edge_notes", "") or ""),
            )
        output.append(updated)
    return output


def _shared_boundary_graph_pair_audit_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Mark whether adjacent surfaces consume the same canonical graph edge ids."""

    if not rows:
        return []
    rows_by_role = {str(row.get("role", "") or ""): row for row in rows}
    role_edge_ids: dict[str, set[str]] = {}
    for row in rows:
        for raw in list(row.get("graph_audit_rows", []) or []):
            parsed = _parse_intersection_shared_boundary_graph_audit_row(raw)
            if not parsed or str(parsed.get("row_kind", "") or "") != "edge":
                continue
            role = str(parsed.get("role", "") or "")
            edge_id = str(parsed.get("row_id", "") or "")
            if role and edge_id:
                role_edge_ids.setdefault(role, set()).add(edge_id)
    expected_pairs = (
        ("patch_to_design_surface", "intersection", "design"),
        ("patch_to_intersection_slope_face", "intersection", "intersection_slope"),
        ("curb_return_to_intersection_slope_face", "intersection", "intersection_slope"),
        ("intersection_slope_face_to_design_surface", "design", "intersection_slope"),
        ("intersection_slope_face_to_corridor_slope_face", "daylight", "intersection_slope"),
        ("main_road_tie", "intersection", "intersection_slope"),
    )
    pair_notes_by_role: dict[str, list[str]] = {}
    pair_match_by_role: dict[str, int] = {}
    pair_missing_by_role: dict[str, int] = {}
    for edge_role, first_role, second_role in expected_pairs:
        first = rows_by_role.get(first_role)
        second = rows_by_role.get(second_role)
        edge_ids = role_edge_ids.get(edge_role, set())
        if first is None or second is None or not edge_ids:
            continue
        first_refs = {str(value or "") for value in list(first.get("graph_refs", []) or []) if str(value or "")}
        second_refs = {str(value or "") for value in list(second.get("graph_refs", []) or []) if str(value or "")}
        shared = edge_ids.intersection(first_refs).intersection(second_refs)
        target_roles = (first_role, second_role)
        if shared:
            for role in target_roles:
                pair_match_by_role[role] = int(pair_match_by_role.get(role, 0) or 0) + len(shared)
                pair_notes_by_role.setdefault(role, []).append(f"pair_match:{edge_role}:{first_role}<->{second_role}:{len(shared)}")
        else:
            for role in target_roles:
                pair_missing_by_role[role] = int(pair_missing_by_role.get(role, 0) or 0) + 1
                pair_notes_by_role.setdefault(role, []).append(f"pair_missing:{edge_role}:{first_role}<->{second_role}")
    output: list[dict[str, object]] = []
    for row in rows:
        role = str(row.get("role", "") or "")
        updated = dict(row)
        pair_match = int(pair_match_by_role.get(role, 0) or 0)
        pair_missing = int(pair_missing_by_role.get(role, 0) or 0)
        pair_notes = "; ".join(pair_notes_by_role.get(role, []))
        updated["graph_pair_match_count"] = pair_match
        updated["graph_pair_missing_count"] = pair_missing
        updated["graph_pair_notes"] = pair_notes
        if pair_notes:
            updated["notes"] = _join_review_notes(str(updated.get("notes", "") or ""), f"graph_pair_audit={pair_notes}")
        if pair_missing:
            updated["status"] = "warning"
            updated["recommended_action"] = "Review Shared Boundary Graph consumer pairs, then rebuild surfaces"
        output.append(updated)
    return output


def shared_breakline_audit_rows_from_preview_objects(preview_entries) -> list[dict[str, object]]:
    """Return panel-friendly shared breakline audit rows from built preview objects."""

    rows: list[dict[str, object]] = []
    for role, title, object_name, obj in preview_entries:
        result_id = str(getattr(obj, "SharedBreaklineResultId", "") or "")
        audit_status = str(getattr(obj, "SharedBreaklineAuditStatus", "") or "")
        has_roundabout_clip_boundary = bool(
            str(getattr(obj, "RoundaboutClipBoundaryStatus", "") or "")
            or str(getattr(obj, "RoundaboutClipBoundaryRole", "") or "")
        )
        if not result_id and not audit_status and not has_roundabout_clip_boundary:
            continue
        geometry_match = int(getattr(obj, "SharedBreaklineGeometryMatchCount", 0) or 0)
        geometry_mismatch = int(getattr(obj, "SharedBreaklineGeometryMismatchCount", 0) or 0)
        mesh_match = int(getattr(obj, "SharedBreaklineMeshMatchCount", 0) or 0)
        mesh_mismatch = int(getattr(obj, "SharedBreaklineMeshMismatchCount", 0) or 0)
        missing = int(getattr(obj, "SharedBreaklineMissingConsumerCount", 0) or 0)
        mismatch = int(getattr(obj, "SharedBreaklineMismatchCount", 0) or 0)
        reversed_count = int(getattr(obj, "SharedBreaklineReversedEdgeCount", 0) or 0)
        consumed = int(getattr(obj, "SharedBreaklineConsumedCount", 0) or 0)
        total = int(getattr(obj, "SharedBreaklineCount", 0) or 0)
        boundary_loop_ref_count = int(getattr(obj, "SharedBreaklineBoundaryLoopRefCount", 0) or 0)
        boundary_loop_constraint_segments = int(getattr(obj, "SharedBreaklineBoundaryLoopConstraintSegmentCount", 0) or 0)
        boundary_loop_constraint_edges = int(getattr(obj, "SharedBreaklineBoundaryLoopConstraintEdgeCount", 0) or 0)
        boundary_loop_constraint_refs = [
            str(value or "")
            for value in list(getattr(obj, "SharedBreaklineBoundaryLoopConstraintRefs", []) or [])
            if str(value or "")
        ]
        boundary_loop_constraint_role_summary = str(
            getattr(obj, "SharedBreaklineBoundaryLoopConstraintRoleSummary", "") or ""
        )
        boundary_loop_ownership_status = str(getattr(obj, "IntersectionBoundaryLoopOwnershipStatus", "") or "")
        boundary_loop_ownership_notes = str(getattr(obj, "IntersectionBoundaryLoopOwnershipNotes", "") or "")
        exclusion_tested_triangles = int(getattr(obj, "IntersectionExclusionTestedTriangleCount", 0) or 0)
        exclusion_clipped_triangles = int(getattr(obj, "IntersectionExclusionClippedTriangleCount", 0) or 0)
        exclusion_boundary_crossings = int(getattr(obj, "IntersectionExclusionBoundaryCrossingTriangleCount", 0) or 0)
        exclusion_near_boundary_kept = int(getattr(obj, "IntersectionExclusionNearBoundaryKeptTriangleCount", 0) or 0)
        exclusion_max_kept_boundary_distance = float(getattr(obj, "IntersectionExclusionMaxKeptBoundaryDistance", 0.0) or 0.0)
        exclusion_clip_ratio = float(getattr(obj, "IntersectionExclusionClipRatio", 0.0) or 0.0)
        boundary_loop_near_kept_warning = _boundary_loop_near_kept_warning(
            role,
            near_kept_count=exclusion_near_boundary_kept,
            tested_triangle_count=exclusion_tested_triangles,
        )
        cell_count = int(getattr(obj, "IntersectionSlopeFaceCellCount", 0) or 0)
        cell_ready = int(getattr(obj, "IntersectionSlopeFaceCellReadyCount", 0) or 0)
        cell_open = int(getattr(obj, "IntersectionSlopeFaceCellOpenCount", 0) or 0)
        cell_missing_edge = int(getattr(obj, "IntersectionSlopeFaceCellMissingEdgeCount", 0) or 0)
        cell_triangles = int(getattr(obj, "IntersectionSlopeFaceCellTriangleCount", 0) or 0)
        graph_status = str(getattr(obj, "IntersectionSharedBoundaryGraphStatus", "") or "")
        graph_nodes = int(getattr(obj, "IntersectionSharedBoundaryGraphNodeCount", 0) or 0)
        graph_edges = int(getattr(obj, "IntersectionSharedBoundaryGraphEdgeCount", 0) or 0)
        graph_cells = int(getattr(obj, "IntersectionSharedBoundaryGraphCellCount", 0) or 0)
        graph_consumed_edges = int(getattr(obj, "IntersectionSharedBoundaryGraphConsumedEdgeCount", 0) or 0)
        graph_duplicate_edges = int(getattr(obj, "IntersectionSharedBoundaryGraphDuplicateEdgeCount", 0) or 0)
        graph_missing_consumers = int(getattr(obj, "IntersectionSharedBoundaryGraphMissingConsumerCount", 0) or 0)
        graph_source_segment_splits = int(getattr(obj, "IntersectionSharedBoundaryGraphSourceSegmentSplitCount", 0) or 0)
        graph_open_cells = int(getattr(obj, "IntersectionSharedBoundaryGraphOpenCellCount", 0) or 0)
        graph_not_snapped = int(getattr(obj, "IntersectionSharedBoundaryGraphNotSnappedCount", 0) or 0)
        graph_endpoint_mismatches = int(getattr(obj, "IntersectionSharedBoundaryGraphEndpointMismatchCount", 0) or 0)
        transition_qa_status = str(getattr(obj, "IntersectionBoundaryLoopTransitionQAStatus", "") or "")
        transition_qa_notes = str(getattr(obj, "IntersectionBoundaryLoopTransitionQANotes", "") or "")
        roundabout_clip_boundary_status = str(getattr(obj, "RoundaboutClipBoundaryStatus", "") or "")
        roundabout_clip_boundary_role = str(getattr(obj, "RoundaboutClipBoundaryRole", "") or "")
        raw_roundabout_actual_clip_roles = getattr(obj, "RoundaboutActualClipBoundaryRoles", "")
        if isinstance(raw_roundabout_actual_clip_roles, str):
            roundabout_actual_clip_boundary_roles = [
                value.strip()
                for value in raw_roundabout_actual_clip_roles.split(",")
                if value.strip()
            ]
        else:
            roundabout_actual_clip_boundary_roles = [
                str(value or "").strip()
                for value in list(raw_roundabout_actual_clip_roles or [])
                if str(value or "").strip()
            ]
        roundabout_clip_boundary_result_id = str(getattr(obj, "RoundaboutClipBoundaryResultId", "") or "")
        roundabout_clip_mode = str(getattr(obj, "RoundaboutOwnershipClipMode", "") or "")
        roundabout_clip_reason_summary = str(getattr(obj, "RoundaboutOwnershipClipReasonSummary", "") or "")
        roundabout_clip_boundary_loop_count = int(getattr(obj, "RoundaboutClipBoundaryLoopCount", 0) or 0)
        roundabout_clip_boundary_segment_count = int(getattr(obj, "RoundaboutClipBoundarySegmentCount", 0) or 0)
        roundabout_clip_boundary_approach_leg_count = int(getattr(obj, "RoundaboutClipBoundaryApproachLegCount", 0) or 0)
        roundabout_clip_boundary_approach_leg_roles = [
            str(value or "")
            for value in list(getattr(obj, "RoundaboutClipBoundaryApproachLegRoles", []) or [])
            if str(value or "")
        ]
        roundabout_clip_boundary_approach_leg_source = str(getattr(obj, "RoundaboutClipBoundaryApproachLegSource", "") or "")
        roundabout_clip_boundary_loop_refs = [
            str(value or "")
            for value in list(getattr(obj, "RoundaboutClipBoundaryLoopRefs", []) or [])
            if str(value or "")
        ]
        roundabout_clip_boundary_segment_refs = [
            str(value or "")
            for value in list(getattr(obj, "RoundaboutClipBoundarySegmentRefs", []) or [])
            if str(value or "")
        ]
        roundabout_clip_boundary_diagnostics = [
            str(value or "")
            for value in list(getattr(obj, "RoundaboutClipBoundaryDiagnostics", []) or [])
            if str(value or "")
        ]
        cell_audit_rows = [
            str(value or "")
            for value in list(getattr(obj, "IntersectionSlopeFaceCellAuditRows", []) or [])
            if str(value or "")
        ]
        graph_audit_rows = [
            str(value or "")
            for value in list(getattr(obj, "IntersectionSharedBoundaryGraphAuditRows", []) or [])
            if str(value or "")
        ]
        graph_refs = [
            str(value or "")
            for value in list(getattr(obj, "IntersectionSharedBoundaryGraphRefs", []) or [])
            if str(value or "")
        ]
        notes = "; ".join(str(value or "") for value in list(getattr(obj, "SharedBreaklineAuditNotes", []) or []) if str(value or ""))
        if not notes:
            notes = str(getattr(obj, "SharedBreaklineAuditSummary", "") or "")
        if cell_count or cell_open or cell_missing_edge:
            cell_note = (
                f"cell_audit=count={cell_count}; ready={cell_ready}; open={cell_open}; "
                f"missing_edge={cell_missing_edge}; triangles={cell_triangles}"
            )
            notes = _join_review_notes(notes, cell_note)
        if graph_status or graph_nodes or graph_edges or graph_cells:
            graph_note = (
                f"shared_boundary_graph=status={graph_status or 'missing'}; nodes={graph_nodes}; "
                f"edges={graph_edges}; consumed_edges={graph_consumed_edges}; cells={graph_cells}; duplicate_edges={graph_duplicate_edges}; "
                f"missing_consumers={graph_missing_consumers}; source_segment_splits={graph_source_segment_splits}; open_cells={graph_open_cells}; "
                f"endpoint_mismatches={graph_endpoint_mismatches}; not_snapped={graph_not_snapped}"
            )
            notes = _join_review_notes(notes, graph_note)
        if boundary_loop_ref_count or boundary_loop_constraint_segments or boundary_loop_constraint_edges:
            notes = _join_review_notes(
                notes,
                (
                    "boundary_loop_handoff="
                    f"refs={boundary_loop_ref_count}; "
                    f"constraint_segments={boundary_loop_constraint_segments}; "
                    f"constraint_edges={boundary_loop_constraint_edges}"
                ),
            )
            if boundary_loop_constraint_role_summary:
                notes = _join_review_notes(
                    notes,
                    f"boundary_loop_constraint_roles={boundary_loop_constraint_role_summary}",
                )
        if boundary_loop_ownership_status:
            notes = _join_review_notes(
                notes,
                f"boundary_loop_ownership={boundary_loop_ownership_status}; {boundary_loop_ownership_notes}",
            )
        if boundary_loop_near_kept_warning:
            notes = _join_review_notes(
                notes,
                (
                    "boundary_loop_near_kept_warning="
                    f"near_kept={exclusion_near_boundary_kept}; "
                    f"tested={exclusion_tested_triangles}; "
                    f"threshold={_boundary_loop_near_kept_warning_threshold(exclusion_tested_triangles)}"
                ),
            )
        if transition_qa_status:
            notes = _join_review_notes(
                notes,
                f"boundary_loop_transition_qa={transition_qa_status}; {transition_qa_notes}",
            )
        if roundabout_clip_boundary_role or roundabout_clip_boundary_status:
            notes = _join_review_notes(
                notes,
                (
                    "roundabout_clip_boundary="
                    f"{roundabout_clip_boundary_role or 'missing'}:{roundabout_clip_boundary_status or 'missing'}; "
                    f"loops={roundabout_clip_boundary_loop_count}; "
                    f"segments={roundabout_clip_boundary_segment_count}; "
                    f"approach_legs={roundabout_clip_boundary_approach_leg_count}; "
                    f"approach_roles={','.join(roundabout_clip_boundary_approach_leg_roles) if roundabout_clip_boundary_approach_leg_roles else 'none'}; "
                    f"mode={roundabout_clip_mode or 'missing'}; "
                    f"actual_clip_roles={','.join(roundabout_actual_clip_boundary_roles) if roundabout_actual_clip_boundary_roles else 'none'}; "
                    f"reasons={roundabout_clip_reason_summary or 'none'}; "
                    f"diagnostics={','.join(roundabout_clip_boundary_diagnostics) if roundabout_clip_boundary_diagnostics else 'none'}"
                ),
            )
        status = _normalize_corridor_build_review_status(audit_status or str(getattr(obj, "SharedBreaklineStatus", "") or "missing"), default="missing")
        substantive_warning = bool(
            geometry_mismatch
            or mesh_mismatch
            or missing
            or mismatch
            or reversed_count
            or cell_open
            or cell_missing_edge
            or graph_duplicate_edges
            or graph_missing_consumers
            or graph_source_segment_splits
            or graph_open_cells
            or graph_not_snapped
            or graph_endpoint_mismatches
        )
        if substantive_warning:
            status = "warning"
        if boundary_loop_ref_count and not boundary_loop_constraint_edges:
            substantive_warning = True
            status = "warning"
        if boundary_loop_near_kept_warning:
            substantive_warning = True
            status = "warning"
        if not substantive_warning and status == "warning":
            status = "ready"
        action = _shared_breakline_recommended_action(
            geometry_mismatch_count=geometry_mismatch,
            mesh_mismatch_count=mesh_mismatch,
            missing_consumer_count=missing,
            mismatch_count=mismatch,
            reversed_edge_count=reversed_count,
            cell_open_count=cell_open,
            cell_missing_edge_count=cell_missing_edge,
            graph_duplicate_edge_count=graph_duplicate_edges,
            graph_missing_consumer_count=graph_missing_consumers,
            graph_source_segment_split_count=graph_source_segment_splits,
            graph_open_cell_count=graph_open_cells,
            graph_not_snapped_count=graph_not_snapped,
            graph_endpoint_mismatch_count=graph_endpoint_mismatches,
            graph_foreign_edge_count=0,
            graph_pair_missing_count=0,
            notes=notes,
        )
        rows.append(
            {
                "role": role,
                "surface": title,
                "object_name": str(getattr(obj, "Name", "") or object_name),
                "object_label": str(getattr(obj, "Label", "") or object_name),
                "status": status,
                "result_id": result_id,
                "material_summary": str(getattr(obj, "SharedBreaklineMaterialSummary", "") or ""),
                "role_summary": str(getattr(obj, "SharedBreaklineRoleSummary", "") or ""),
                "consumed": consumed,
                "total": total,
                "geometry_match_count": geometry_match,
                "geometry_mismatch_count": geometry_mismatch,
                "mesh_match_count": mesh_match,
                "mesh_mismatch_count": mesh_mismatch,
                "missing_consumer_count": missing,
                "mismatch_count": mismatch,
                "reversed_edge_count": reversed_count,
                "boundary_loop_ref_count": boundary_loop_ref_count,
                "boundary_loop_constraint_segment_count": boundary_loop_constraint_segments,
                "boundary_loop_constraint_edge_count": boundary_loop_constraint_edges,
                "boundary_loop_constraint_refs": boundary_loop_constraint_refs,
                "boundary_loop_ownership_status": boundary_loop_ownership_status,
                "boundary_loop_ownership_notes": boundary_loop_ownership_notes,
                "roundabout_clip_boundary_status": roundabout_clip_boundary_status,
                "roundabout_clip_boundary_role": roundabout_clip_boundary_role,
                "roundabout_actual_clip_boundary_roles": roundabout_actual_clip_boundary_roles,
                "roundabout_clip_boundary_result_id": roundabout_clip_boundary_result_id,
                "roundabout_clip_mode": roundabout_clip_mode,
                "roundabout_clip_reason_summary": roundabout_clip_reason_summary,
                "roundabout_clip_boundary_loop_count": roundabout_clip_boundary_loop_count,
                "roundabout_clip_boundary_segment_count": roundabout_clip_boundary_segment_count,
                "roundabout_clip_boundary_approach_leg_count": roundabout_clip_boundary_approach_leg_count,
                "roundabout_clip_boundary_approach_leg_roles": roundabout_clip_boundary_approach_leg_roles,
                "roundabout_clip_boundary_approach_leg_source": roundabout_clip_boundary_approach_leg_source,
                "roundabout_clip_boundary_loop_refs": roundabout_clip_boundary_loop_refs,
                "roundabout_clip_boundary_segment_refs": roundabout_clip_boundary_segment_refs,
                "roundabout_clip_boundary_diagnostics": roundabout_clip_boundary_diagnostics,
                "intersection_exclusion_tested_triangle_count": exclusion_tested_triangles,
                "intersection_exclusion_clipped_triangle_count": exclusion_clipped_triangles,
                "intersection_exclusion_boundary_crossing_triangle_count": exclusion_boundary_crossings,
                "intersection_exclusion_near_boundary_kept_triangle_count": exclusion_near_boundary_kept,
                "intersection_exclusion_max_kept_boundary_distance": exclusion_max_kept_boundary_distance,
                "intersection_exclusion_clip_ratio": exclusion_clip_ratio,
                "boundary_loop_near_kept_warning": boundary_loop_near_kept_warning,
                "cell_count": cell_count,
                "cell_ready_count": cell_ready,
                "cell_open_count": cell_open,
                "cell_missing_edge_count": cell_missing_edge,
                "cell_triangle_count": cell_triangles,
                "cell_audit_rows": cell_audit_rows,
                "graph_status": graph_status,
                "graph_node_count": graph_nodes,
                "graph_edge_count": graph_edges,
                "graph_consumed_edge_count": graph_consumed_edges,
                "graph_cell_count": graph_cells,
                "graph_duplicate_edge_count": graph_duplicate_edges,
                "graph_missing_consumer_count": graph_missing_consumers,
                "graph_source_segment_split_count": graph_source_segment_splits,
                "graph_open_cell_count": graph_open_cells,
                "graph_not_snapped_count": graph_not_snapped,
                "graph_endpoint_mismatch_count": graph_endpoint_mismatches,
                "graph_audit_rows": graph_audit_rows,
                "graph_refs": graph_refs,
                "graph_foreign_edge_count": 0,
                "graph_foreign_edge_notes": "",
                "graph_pair_match_count": 0,
                "graph_pair_missing_count": 0,
                "graph_pair_notes": "",
                "solid_readiness_status": str(getattr(obj, "SharedBreaklineSolidReadinessStatus", "") or ""),
                "solid_open_end_count": int(getattr(obj, "SharedBreaklineSolidOpenEndCount", 0) or 0),
                "solid_duplicate_edge_count": int(getattr(obj, "SharedBreaklineSolidDuplicateEdgeCount", 0) or 0),
                "solid_non_manifold_node_count": int(getattr(obj, "SharedBreaklineSolidNonManifoldNodeCount", 0) or 0),
                "recommended_action": action,
                "notes": notes,
            }
        )
    return _shared_boundary_graph_pair_audit_rows(_shared_boundary_graph_consumer_audit_rows(rows))
