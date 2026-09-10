"""Presentation rows for the intersection contract review table."""

from __future__ import annotations

from .shared_breakline_audit_presentation import (
    _parse_intersection_shared_boundary_graph_audit_row,
    _parse_intersection_slope_face_cell_audit_row,
)


def _unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _join_review_notes(*parts: str) -> str:
    return "; ".join(str(part or "").strip() for part in parts if str(part or "").strip())


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
