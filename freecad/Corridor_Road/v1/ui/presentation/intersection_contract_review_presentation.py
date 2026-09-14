"""Presentation rows for the intersection contract review table."""

from __future__ import annotations

from typing import Callable

from .shared_breakline_audit_presentation import (
    _parse_intersection_shared_boundary_graph_audit_row,
    _parse_intersection_slope_face_cell_audit_row,
)
from .review_text import join_review_notes as _join_review_notes
from .review_text import unique_text_values as _unique_text_values


def _roundabout_boundary_readiness_contract_review_row(approach_legs, boundary_loops) -> dict[str, object] | None:
    """Expose roundabout approach clip/handoff boundary readiness in the Intersections tab."""

    if approach_legs is None or str(getattr(approach_legs, "intersection_kind", "") or "").lower() != "roundabout":
        return None
    approach_rows = list(getattr(approach_legs, "approach_leg_rows", []) or [])
    accepted_rows = [
        row
        for row in approach_rows
        if str(getattr(row, "status", "") or "").strip().lower() in {"ready", "accepted"}
    ]
    expected_count = max(4, len(accepted_rows))
    required_roles = (
        "roundabout_approach_clip_boundary",
        "roundabout_subgrade_clip_boundary",
        "roundabout_slope_handoff_boundary",
    )
    loop_rows = list(getattr(boundary_loops, "loop_rows", []) or [])
    loops_by_role: dict[str, list[object]] = {role: [] for role in required_roles}
    for row in loop_rows:
        role = str(getattr(row, "loop_role", "") or "")
        if role in loops_by_role:
            loops_by_role[role].append(row)

    missing_roles: list[str] = []
    warning_roles: list[str] = []
    error_roles: list[str] = []
    for role in required_roles:
        role_rows = loops_by_role.get(role, [])
        ready_count = len([row for row in role_rows if str(getattr(row, "status", "") or "") == "ready"])
        if ready_count < expected_count:
            missing_roles.append(f"{role}:{ready_count}/{expected_count}")
        if any(str(getattr(row, "status", "") or "") == "warning" for row in role_rows):
            warning_roles.append(role)
        if any(str(getattr(row, "status", "") or "") == "error" for row in role_rows):
            error_roles.append(role)

    role_attr_map = {
        "roundabout_approach_clip_boundary": "corridor_clip_boundary_role",
        "roundabout_subgrade_clip_boundary": "subgrade_handoff_boundary_role",
        "roundabout_slope_handoff_boundary": "slope_handoff_boundary_role",
    }
    missing_leg_role_attrs: list[str] = []
    for approach in approach_rows:
        approach_id = str(getattr(approach, "approach_leg_id", "") or "")
        for role, attr in role_attr_map.items():
            if str(getattr(approach, attr, "") or "") != role:
                missing_leg_role_attrs.append(f"{approach_id}:{role}")

    diagnostics = _unique_text_values(
        [
            *(
                ["error:roundabout_approach_leg_rows_missing"]
                if not approach_rows
                else []
            ),
            *(
                [f"warning:roundabout_approach_leg_count_below_four:{len(accepted_rows)}"]
                if len(accepted_rows) < 4
                else []
            ),
            *[f"warning:roundabout_boundary_role_missing:{value}" for value in missing_roles],
            *[f"warning:roundabout_boundary_role_warning:{value}" for value in warning_roles],
            *[f"error:roundabout_boundary_role_error:{value}" for value in error_roles],
            *[f"error:roundabout_approach_leg_boundary_role_missing:{value}" for value in missing_leg_role_attrs],
        ]
    )
    status = "error" if any(str(value).startswith("error:") for value in diagnostics) else (
        "warning" if missing_roles or warning_roles or any(str(value).startswith("warning:") for value in diagnostics) else "ready"
    )
    source_status = "error" if status == "error" else ("warning" if status == "warning" else "accepted")
    role_summary = ", ".join(
        f"{role}={len([row for row in loops_by_role.get(role, []) if str(getattr(row, 'status', '') or '') == 'ready'])}/{expected_count}"
        for role in required_roles
    )
    approach_roles = _unique_text_values(
        [str(getattr(row, "approach_role", "") or "") for row in approach_rows]
    )
    source_refs = _unique_text_values(
        [
            str(getattr(approach_legs, "approach_leg_result_id", "") or ""),
            *[str(getattr(row, "approach_leg_id", "") or "") for row in approach_rows],
        ]
    )
    boundary_refs = _unique_text_values(
        [
            str(getattr(row, "loop_id", "") or "")
            for role in required_roles
            for row in loops_by_role.get(role, [])
        ]
    )
    return {
        "contract_family": "roundabout_boundary_readiness",
        "status": status,
        "row_id": f"roundabout-boundary-readiness:{str(getattr(approach_legs, 'intersection_id', '') or 'main')}",
        "role": "approach_clip_and_slope_handoff",
        "source_refs": ", ".join(source_refs),
        "boundary_refs": ", ".join(boundary_refs),
        "source_status": source_status,
        "source_diagnostics": "; ".join(diagnostics),
        "focus_object": "",
        "notes": _join_review_notes(
            f"approach_legs={len(accepted_rows)}/{expected_count}",
            f"approach_roles={','.join(approach_roles) if approach_roles else 'none'}",
            role_summary,
            f"boundary_result={str(getattr(boundary_loops, 'boundary_loop_result_id', '') or '')}",
            f"missing_roles={','.join(missing_roles)}" if missing_roles else "",
            "Roundabout ordinary-surface clip and slope handoff boundaries are ready."
            if status == "ready"
            else "Repair missing roundabout approach boundary roles before ordinary surface clipping.",
        ),
        "output_path": "roundabout_boundary_readiness",
    }


def _intersection_contract_display_status(status: str) -> str:
    text = str(status or "").strip().lower()
    if text == "candidate":
        return "ready"
    if text == "warn":
        return "warning"
    return text or "missing"


def _intersection_upper_slope_face_panel_contract_review_row_from_preview(obj) -> dict[str, object] | None:
    """Expose accepted upper rectangular panel readiness in the Intersections tab."""

    if obj is None:
        return None
    candidate_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelCandidateCount", 0) or 0)
    accepted_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelAcceptedCount", 0) or 0)
    generated_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0)
    triangle_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelTriangleCount", 0) or 0)
    suppressed_count = int(getattr(obj, "IntersectionSlopeFaceSuppressedUpperCellCount", 0) or 0)
    if not any((candidate_count, accepted_count, generated_count, triangle_count, suppressed_count)):
        return None
    panel_refs = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionUpperSlopeFacePanelRefs", []) or [])
        if str(value or "").strip()
    ]
    boundary_refs = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionUpperSlopeFacePanelBoundaryRefs", []) or [])
        if str(value or "").strip()
    ]
    suppressed_refs = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionSlopeFaceSuppressedUpperCellRefs", []) or [])
        if str(value or "").strip()
    ]
    generation_mode = str(getattr(obj, "IntersectionUpperSlopeFacePanelGenerationMode", "") or "")
    source_mode = str(getattr(obj, "IntersectionUpperSlopeFacePanelSourceMode", "") or "")
    coverage_status = str(getattr(obj, "IntersectionUpperSlopeFacePanelCoverageStatus", "") or "")
    coverage_summary = str(getattr(obj, "IntersectionUpperSlopeFacePanelCoverageSummary", "") or "")
    expected_group_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelExpectedGroupCount", 0) or 0)
    diagnostic = str(getattr(obj, "IntersectionUpperSlopeFacePanelDiagnostic", "") or "")
    status = "ready" if generated_count > 0 and triangle_count == generated_count * 2 else "warning"
    return {
        "contract_family": "intersection_upper_slope_face_panel",
        "status": status,
        "row_id": "intersection-upper-slope-face-panel",
        "role": "upper_rectangular_panel",
        "source_refs": ", ".join(panel_refs),
        "boundary_refs": ", ".join(boundary_refs),
        "source_status": "accepted" if status == "ready" else "warning",
        "source_diagnostics": diagnostic,
        "focus_object": "V1CorridorIntersectionSlopeFaceSurfacePreview",
        "notes": _join_review_notes(
            f"candidates={candidate_count}",
            f"accepted={accepted_count}",
            f"generated={generated_count}",
            f"triangles={triangle_count}",
            f"suppressed_legacy_upper_cells={suppressed_count}",
            f"mode={generation_mode}" if generation_mode else "",
            f"source={source_mode}" if source_mode else "",
            f"coverage={coverage_status}" if coverage_status else "",
            f"expected_groups={expected_group_count}" if expected_group_count else "",
            coverage_summary,
            f"suppressed_refs={len(suppressed_refs)}",
            diagnostic,
        ),
        "output_path": "intersection_upper_slope_face_panel",
    }


def _intersection_slope_face_cell_contract_review_rows_from_preview(obj) -> list[dict[str, object]]:
    """Expose generated Intersection Slope Face cell contracts in the Intersections tab."""

    if obj is None:
        return []
    raw_rows = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionSlopeFaceCellAuditRows", []) or [])
        if str(value or "").strip()
    ]
    if not raw_rows:
        return []
    result_id = str(getattr(obj, "IntersectionSlopeFaceCellResultId", "") or "").strip()
    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        parsed = _parse_intersection_slope_face_cell_audit_row(raw)
        if not parsed:
            continue
        open_count = int(parsed.get("open_count", 0) or 0)
        missing_edge_count = int(parsed.get("missing_edge_count", 0) or 0)
        status = _intersection_contract_display_status(str(parsed.get("status", "") or "missing"))
        if open_count or missing_edge_count:
            status = "warning"
        diagnostics = str(parsed.get("diagnostics", "") or "")
        boundary_refs = str(parsed.get("boundary_refs", "") or "")
        rows.append(
            {
                "contract_family": "slope_face_cell",
                "status": status,
                "row_id": str(parsed.get("cell_id", "") or ""),
                "role": str(parsed.get("cell_role", "") or ""),
                "source_refs": result_id,
                "boundary_refs": boundary_refs,
                "source_status": "warning" if diagnostics or open_count or missing_edge_count else "accepted",
                "source_diagnostics": diagnostics,
                "focus_object": "V1CorridorIntersectionSlopeFaceSurfacePreview",
                "notes": _join_review_notes(
                    f"points={int(parsed.get('point_count', 0) or 0)}",
                    f"open={open_count}",
                    f"missing_edges={missing_edge_count}",
                    f"boundary_refs={boundary_refs}" if boundary_refs else "",
                    diagnostics,
                ),
                "output_path": "intersection_slope_face_cell_result",
            }
        )
    return rows


def _intersection_shared_boundary_graph_contract_review_rows_from_preview(obj) -> list[dict[str, object]]:
    """Expose canonical shared-boundary graph contracts in the Intersections tab."""

    if obj is None:
        return []
    raw_rows = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionSharedBoundaryGraphAuditRows", []) or [])
        if str(value or "").strip()
    ]
    if not raw_rows:
        return []
    result_id = str(getattr(obj, "IntersectionSharedBoundaryGraphResultId", "") or "").strip()
    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        parsed = _parse_intersection_shared_boundary_graph_audit_row(raw)
        if not parsed:
            continue
        diagnostics = str(parsed.get("diagnostics", "") or "")
        open_count = int(parsed.get("open_count", 0) or 0)
        status = "warning" if diagnostics or open_count else "ready"
        rows.append(
            {
                "contract_family": "shared_boundary_graph",
                "status": status,
                "row_id": str(parsed.get("row_id", "") or ""),
                "role": f"{parsed.get('row_kind', '')}:{parsed.get('role', '')}",
                "source_refs": result_id,
                "boundary_refs": str(parsed.get("refs", "") or ""),
                "source_status": "warning" if status == "warning" else "accepted",
                "source_diagnostics": diagnostics,
                "focus_object": "V1CorridorIntersectionSlopeFaceSurfacePreview",
                "notes": _join_review_notes(
                    f"kind={parsed.get('row_kind', '')}",
                    f"refs={parsed.get('refs', '')}" if parsed.get("refs", "") else "",
                    f"open={open_count}" if open_count else "",
                    diagnostics,
                ),
                "output_path": "intersection_shared_boundary_graph_result",
            }
        )
    return rows


def intersection_contract_review_rows(
    *,
    topology,
    tie_slope_result,
    tie_slope_window_rows,
    roundabout_approach_legs,
    boundary_loops,
    slope_loops,
    corridor_clips,
    drainage_hints,
    surface_boundary_mode,
    surface_boundary_loop,
    surface_boundary_fallback,
    intersection_preview_object,
    slope_loop_blocking_reasons_for: Callable[[object], list[str]],
    include_internal: bool = False,
) -> list[dict[str, object]]:
    """Return edge-network-first intersection contract rows for Build Parametric review."""

    rows: list[dict[str, object]] = []
    rows.append(
        {
            "contract_family": "topology",
            "status": topology.status,
            "row_id": topology.topology_result_id,
            "role": "control_area",
            "source_refs": ", ".join(list(getattr(topology, "source_refs", []) or [])),
            "boundary_refs": ", ".join(row.control_area_id for row in list(topology.control_area_rows or [])),
            "source_status": _intersection_contract_source_status(
                [
                    *list(getattr(topology, "anchor_rows", []) or []),
                    *list(getattr(topology, "leg_span_rows", []) or []),
                    *list(getattr(topology, "control_area_rows", []) or []),
                    *list(getattr(topology, "lane_connection_rows", []) or []),
                ]
            ),
            "source_diagnostics": _intersection_contract_source_diagnostics(
                [
                    *list(getattr(topology, "anchor_rows", []) or []),
                    *list(getattr(topology, "leg_span_rows", []) or []),
                    *list(getattr(topology, "control_area_rows", []) or []),
                    *list(getattr(topology, "lane_connection_rows", []) or []),
                ]
            ),
            "focus_object": "V1CorridorIntersectionSurfacePreview",
            "notes": (
                f"kind={getattr(topology, 'intersection_kind', '')}; "
                f"anchors={getattr(topology, 'anchor_count', 0)}; legs={topology.leg_span_count}; "
                f"corners={getattr(topology, 'corner_count', 0)}; curb_return_arcs={getattr(topology, 'curb_return_arc_count', 0)}; "
                f"leg_graph={getattr(topology, 'leg_graph_status', '')}; corner_graph={getattr(topology, 'corner_graph_status', '')}; "
                f"control areas={topology.control_area_count}; "
                f"lane connections={getattr(topology, 'lane_connection_count', 0)}; "
                f"alignments={topology.participating_alignment_count}; diagnostics={len(topology.diagnostic_rows)}"
            ),
        }
    )
    if tie_slope_window_rows:
        rows.append(
            {
                "contract_family": "intersection_tie_slope_window",
                "status": "ready" if all(str(row.get("status", "") or "") == "accepted" for row in tie_slope_window_rows) else "warning",
                "row_id": f"intersection-tie-slope-window:{str(getattr(tie_slope_result, 'intersection_id', '') or 'main')}",
                "role": "applied_section_window",
                "source_refs": ",".join(
                    _unique_text_values(
                        [
                            str(row.get("outer_applied_section_ref", "") or "")
                            for row in tie_slope_window_rows
                        ]
                        + [
                            str(row.get("inner_applied_section_ref", "") or "")
                            for row in tie_slope_window_rows
                        ]
                    )
                ),
                "boundary_refs": "applied_section_side_slope_edges",
                "source_status": "accepted" if all(str(row.get("status", "") or "") == "accepted" for row in tie_slope_window_rows) else "warning",
                "source_diagnostics": "; ".join(_intersection_tie_slope_window_diagnostics(tie_slope_window_rows)[:8]),
                "focus_object": "V1CorridorIntersectionTieSlopeSurfacePreview",
                "notes": _intersection_tie_slope_window_summary_note(tie_slope_window_rows),
                "output_path": "intersection_tie_slope_window_candidates",
            }
        )
    roundabout_boundary_readiness_row = _roundabout_boundary_readiness_contract_review_row(
        roundabout_approach_legs,
        boundary_loops,
    )
    if roundabout_boundary_readiness_row is not None:
        rows.append(roundabout_boundary_readiness_row)
    for row in list(getattr(boundary_loops, "loop_rows", []) or []):
        rows.append(
            {
                "contract_family": "boundary_loop",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or boundary_loops.status)),
                "row_id": str(getattr(row, "loop_id", "") or ""),
                "role": str(getattr(row, "loop_role", "") or ""),
                "source_refs": ", ".join(list(getattr(row, "source_refs", ()) or ())),
                "boundary_refs": ", ".join(list(getattr(row, "segment_refs", ()) or ())),
                "source_status": str(getattr(row, "source_status", "") or "accepted"),
                "source_diagnostics": "; ".join(list(getattr(row, "diagnostics", ()) or ())),
                "focus_object": "V1CorridorIntersectionSurfacePreview",
                "notes": _join_review_notes(
                    f"kind={getattr(boundary_loops, 'intersection_kind', '')}",
                    f"surface_boundary_mode={surface_boundary_mode}" if surface_boundary_mode else "",
                    f"surface_boundary_loop={surface_boundary_loop}" if surface_boundary_loop else "",
                    f"fallback_reason={surface_boundary_fallback}" if surface_boundary_fallback else "",
                    f"closed={'yes' if bool(getattr(row, 'closed', False)) else 'no'}",
                    f"points={int(getattr(row, 'point_count', 0) or 0)}",
                    f"segments={int(getattr(row, 'segment_count', 0) or 0)}",
                    f"area={float(getattr(row, 'area_xy', 0.0) or 0.0):.3f}",
                    "consumers=" + ",".join(list(getattr(row, "consumer_roles", ()) or ())),
                    "; ".join(list(getattr(row, "diagnostics", ()) or ())),
                    str(getattr(row, "recommended_action", "") or ""),
                ),
                "output_path": "intersection_boundary_loop_result",
            }
        )
    for row in list(slope_loops.loop_rows or []):
        blocking_reasons = slope_loop_blocking_reasons_for(row)
        rows.append(
            {
                "contract_family": "slope_face_loop",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or slope_loops.status)),
                "row_id": str(getattr(row, "loop_id", "") or ""),
                "role": str(getattr(row, "loop_family", "") or ""),
                "source_refs": _join_review_notes(
                    ", ".join(list(getattr(row, "source_edge_network_refs", ()) or ())),
                    ", ".join(list(getattr(row, "source_surface_zone_refs", ()) or ())),
                    ", ".join(list(getattr(row, "source_applied_section_refs", ()) or ())),
                ),
                "boundary_refs": ", ".join(list(getattr(row, "boundary_edge_refs", ()) or ())),
                "source_status": str(getattr(row, "source_status", "") or "accepted"),
                "source_diagnostics": "; ".join(
                    _unique_text_values(
                        [
                            *[str(value or "") for value in tuple(getattr(row, "source_diagnostic_rows", ()) or ())],
                            *[str(value or "") for value in tuple(getattr(row, "diagnostics", ()) or ())],
                        ]
                    )
                ),
                "focus_object": "",
                "notes": _join_review_notes(
                    f"alignment={getattr(row, 'alignment_ref', '')}",
                    f"leg={getattr(row, 'leg_ref', '')}",
                    f"side={getattr(row, 'side', '')}",
                    f"points={getattr(row, 'point_count', 0)}",
                    "closed_xy=yes" if bool(getattr(row, "closed_xy", False)) else "closed_xy=no",
                    "self_crossing=yes" if bool(getattr(row, "self_crossing", False)) else "",
                    f"generation={getattr(row, 'surface_generation_role', '')}:{getattr(row, 'surface_generation_status', '')}",
                    "blocking=" + ",".join(blocking_reasons[:4]) if blocking_reasons else "",
                    f"source_lineage={getattr(row, 'source_lineage_status', '')}" if str(getattr(row, "source_lineage_status", "") or "") != "accepted" else "",
                    f"surface_zone_status={getattr(row, 'source_surface_zone_status', '')}" if str(getattr(row, "source_surface_zone_status", "") or "") not in {"", "accepted"} else "",
                    f"edge_network_status={getattr(row, 'source_edge_network_status', '')}" if str(getattr(row, "source_edge_network_status", "") or "") not in {"", "accepted"} else "",
                    "; ".join(list(getattr(row, "source_diagnostic_rows", ()) or ())),
                    "; ".join(list(getattr(row, "diagnostics", ()) or ())),
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    # One lookup for the three presentation row builders below.
    upper_panel_contract_row = _intersection_upper_slope_face_panel_contract_review_row_from_preview(intersection_preview_object)
    if upper_panel_contract_row is not None:
        rows.append(upper_panel_contract_row)
    rows.extend(_intersection_slope_face_cell_contract_review_rows_from_preview(intersection_preview_object))
    rows.extend(_intersection_shared_boundary_graph_contract_review_rows_from_preview(intersection_preview_object))
    for row in list(corridor_clips.clip_rows or []):
        rows.append(
            {
                "contract_family": "corridor_clip",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or corridor_clips.status)),
                "row_id": str(getattr(row, "clip_id", "") or ""),
                "role": str(getattr(row, "surface_role", "") or ""),
                "source_refs": _join_review_notes(
                    str(getattr(row, "source_control_area_ref", "") or getattr(row, "control_area_ref", "") or ""),
                    ", ".join(list(getattr(row, "source_region_refs", ()) or ())),
                ),
                "boundary_refs": ", ".join(list(getattr(row, "protected_zone_refs", ()) or ())),
                "source_status": str(getattr(row, "source_status", "") or "accepted"),
                "source_diagnostics": "; ".join(list(getattr(row, "source_diagnostic_rows", ()) or ())),
                "focus_object": "V1CorridorIntersectionExclusionZonePreview",
                "notes": _join_review_notes(
                    f"alignment={getattr(row, 'alignment_ref', '')}",
                    f"method={getattr(row, 'clip_method', '')}",
                    f"timing={getattr(row, 'clip_timing', '')}",
                    f"intent={getattr(row, 'control_area_intent_status', '')}",
                    f"lineage={getattr(row, 'region_lineage_status', '')}",
                    "; ".join(list(getattr(row, "diagnostic_rows", ()) or ())),
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    for row in list(drainage_hints.hint_rows or []):
        rows.append(
            {
                "contract_family": "drainage_hint",
                "status": _intersection_contract_display_status(str(getattr(row, "status", "") or drainage_hints.status)),
                "row_id": str(getattr(row, "hint_id", "") or ""),
                "role": str(getattr(row, "hint_kind", "") or ""),
                "source_refs": _join_review_notes(
                    str(getattr(row, "source_drainage_policy_ref", "") or getattr(row, "drainage_policy_ref", "") or ""),
                    str(getattr(row, "accepted_drainage_ref", "") or ""),
                    ", ".join(list(getattr(row, "source_edge_refs", ()) or ())),
                ),
                "boundary_refs": _join_review_notes(
                    str(getattr(row, "zone_ref", "") or ""),
                    ", ".join(list(getattr(row, "control_area_refs", ()) or ())),
                ),
                "source_status": str(getattr(row, "source_status", "") or "accepted"),
                "source_diagnostics": "; ".join(list(getattr(row, "source_diagnostic_rows", ()) or ())),
                "focus_object": "V1CorridorIntersectionSurfacePreview",
                "notes": _join_review_notes(
                    f"zone={getattr(row, 'zone_role', '')}",
                    f"surface={getattr(row, 'surface_role', '')}",
                    f"recommend={getattr(row, 'recommended_element_kind', '')}",
                    f"handoff={getattr(row, 'drainage_handoff_status', '')}",
                    f"review={getattr(row, 'drainage_review_status', '')}",
                    "; ".join(list(getattr(row, "diagnostic_rows", ()) or ())),
                    str(getattr(row, "notes", "") or ""),
                ),
            }
        )
    for row in rows:
        row.setdefault("output_path", "contract_consumed")
    if not include_internal:
        internal_families = {
            "edge_network",
            "surface_zone",
            "drainage_hint",
            "slope_face_loop",
            "slope_face_cell",
            "shared_boundary_graph",
        }
        rows = [
            row
            for row in rows
            if str(row.get("contract_family", "") or "") not in internal_families
        ]
    return rows


def _intersection_contract_source_status(rows: list[object]) -> str:
    statuses = [str(getattr(row, "source_status", "") or "") for row in rows]
    statuses = [status for status in statuses if status]
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "warning" for status in statuses):
        return "warning"
    return "accepted"


def _intersection_contract_source_diagnostics(rows: list[object]) -> str:
    diagnostics: list[str] = []
    for row in rows:
        for item in tuple(getattr(row, "source_diagnostic_rows", ()) or ()):
            text = str(item or "").strip()
            if text and text not in diagnostics:
                diagnostics.append(text)
    return "; ".join(diagnostics)


def _intersection_tie_slope_window_summary_note(rows: list[dict[str, object]]) -> str:
    row_list = list(rows or [])
    accepted = [
        row for row in row_list
        if str(row.get("status", "") or "") == "accepted"
    ]
    warnings = [
        row for row in row_list
        if str(row.get("status", "") or "") != "accepted"
    ]
    cell_roles = [
        str(row.get("cell_role", "") or "")
        for row in row_list
        if str(row.get("cell_role", "") or "")
    ]
    alignments = [
        str(row.get("alignment_ref", "") or "")
        for row in row_list
        if str(row.get("alignment_ref", "") or "")
    ]
    sides = [
        str(row.get("side", "") or "")
        for row in row_list
        if str(row.get("side", "") or "")
    ]
    ownership_classes = [
        str(row.get("ownership_class", "") or "")
        for row in row_list
        if str(row.get("ownership_class", "") or "")
    ]
    diagnostics = _intersection_tie_slope_window_diagnostics(row_list)
    role_counts = {
        role: sum(1 for value in cell_roles if value == role)
        for role in _unique_text_values(cell_roles)
    }
    for known_role in ("transition_pair", "intersection_adjacent_pair", "curb_return_approach_pair"):
        role_counts.setdefault(known_role, 0)
    supplemental_endpoint_count = sum(
        1 for row in row_list
        if str(row.get("supplemental_extent_role", "") or "") == "supplemental_endpoint_pair"
    )
    supplemental_inner_count = sum(1 for row in row_list if bool(row.get("inner_is_supplemental", False)))
    control_area_transition_count = sum(
        1 for row in row_list
        if bool(row.get("control_area_transition_allowed", False))
    )
    role_text = ",".join(f"{role}={count}" for role, count in role_counts.items())
    ownership_counts = {
        ownership: sum(1 for value in ownership_classes if value == ownership)
        for ownership in _unique_text_values(ownership_classes)
    }
    ownership_text = ",".join(f"{ownership}={count}" for ownership, count in ownership_counts.items())
    parts = [
        f"Applied Section window candidates: rows={len(row_list)}",
        f"accepted={len(accepted)}",
        f"warnings={len(warnings)}",
        "source=applied_section_context_transition_window",
        f"supplemental_inner={supplemental_inner_count}",
        f"supplemental_endpoints={supplemental_endpoint_count}",
        f"control_area_transitions={control_area_transition_count}",
    ]
    if role_text:
        parts.append(role_text)
    if ownership_text:
        parts.append("ownership=" + ownership_text)
    endpoint_by_road = _intersection_tie_slope_window_endpoint_summary_by_road(row_list)
    if endpoint_by_road and endpoint_by_road != "not_evaluated":
        parts.append("supplemental_endpoint_by_road=" + endpoint_by_road)
    if alignments:
        parts.append("alignments=" + ",".join(_unique_text_values(alignments)))
    if sides:
        parts.append("sides=" + ",".join(_unique_text_values(sides)))
    if diagnostics:
        parts.append("diagnostics=" + "; ".join(diagnostics[:4]))
    return "; ".join(parts)


def _intersection_tie_slope_window_diagnostics(rows: list[dict[str, object]]) -> list[str]:
    diagnostics: list[str] = []
    for row in list(rows or []):
        diagnostics.extend(
            str(value or "")
            for value in tuple(row.get("diagnostics", ()) or ())
            if str(value or "")
        )
    return _unique_text_values(diagnostics)


def _intersection_tie_slope_window_endpoint_summary_by_road(rows: list[dict[str, object]]) -> str:
    """Return accepted supplemental endpoint window counts by road role."""

    accepted_endpoint_rows = [
        row for row in list(rows or [])
        if str(row.get("status", "") or "") == "accepted"
        and str(row.get("ownership_class", "") or "") == "tie_slope_candidate"
        and str(row.get("supplemental_extent_role", "") or "") == "supplemental_endpoint_pair"
    ]
    road_roles = [
        str(row.get("road_role", "") or "")
        for row in accepted_endpoint_rows
        if str(row.get("road_role", "") or "")
    ]
    if not road_roles:
        return "not_evaluated"
    counts = {
        role: sum(1 for row in accepted_endpoint_rows if str(row.get("road_role", "") or "") == role)
        for role in _unique_text_values(road_roles)
    }
    return ",".join(f"{role}={count}" for role, count in counts.items())
