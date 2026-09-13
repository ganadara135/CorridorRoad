"""Presentation rows for the Build Corridor Results tab review."""

from __future__ import annotations

from typing import Callable

from .review_text import join_review_notes as _join_review_notes
from .review_text import unique_text_values as _unique_text_values
from .review_text import display_source_id as _display_source_id
from .review_text import display_source_ref as _display_source_ref
from .review_text import format_count_summary as _format_count_summary
from .shared_breakline_audit_presentation import _normalize_corridor_build_review_status


def roundabout_build_review_rows(
    intersection_obj,
    *,
    apron_obj,
    subgrade_obj,
    slope_face_obj,
) -> list[dict[str, object]]:
    """Return roundabout-specific Results tab rows from generated output contracts."""

    rows: list[dict[str, object]] = []

    rows.append(
        _corridor_roundabout_review_row(
            role="roundabout_circulatory",
            title="Roundabout Circulatory Surface",
            object_name="V1CorridorIntersectionSurfacePreview",
            obj=intersection_obj,
            notes=_join_review_notes(
                "roundabout annular circulatory surface",
                f"boundary={getattr(intersection_obj, 'PatchSurfaceBoundaryStrategy', '')}",
                f"triangulation={getattr(intersection_obj, 'PatchTriangulationMode', '')}",
            ),
        )
    )
    connector_obj = None
    if apron_obj is not None:
        rows.append(
            _corridor_roundabout_review_row(
                role="roundabout_apron",
                title="Roundabout Apron Surface",
                object_name="V1CorridorRoundaboutApronSurfacePreview",
                obj=apron_obj,
                notes=_join_review_notes(
                    "roundabout annular apron surface",
                    f"boundary={getattr(apron_obj, 'PatchSurfaceBoundaryStrategy', '')}",
                    f"triangulation={getattr(apron_obj, 'PatchTriangulationMode', '')}",
                ),
            )
        )
    if subgrade_obj is not None:
        rows.append(
            _corridor_roundabout_review_row(
                role="roundabout_subgrade",
                title="Roundabout Subgrade Surface",
                object_name="V1CorridorRoundaboutSubgradeSurfacePreview",
                obj=subgrade_obj,
                notes=_join_review_notes(
                    "roundabout dedicated subgrade surface",
                    f"boundary={getattr(subgrade_obj, 'PatchSurfaceBoundaryStrategy', '')}",
                    f"triangulation={getattr(subgrade_obj, 'PatchTriangulationMode', '')}",
                ),
            )
        )
    breakline_status = "ready"
    if any(
        int(getattr(candidate, "SharedBreaklineGeometryMismatchCount", 0) or 0)
        or int(getattr(candidate, "SharedBreaklineMeshMismatchCount", 0) or 0)
        or int(getattr(candidate, "SharedBreaklineMissingConsumerCount", 0) or 0)
        for candidate in (connector_obj, apron_obj, subgrade_obj, slope_face_obj)
        if candidate is not None
    ):
        breakline_status = "warning"
    if apron_obj is None or subgrade_obj is None or slope_face_obj is None:
        breakline_status = "missing"
    rows.append(
        {
            "role": "roundabout_breakline_readiness",
            "result": "Roundabout Breakline Readiness",
            "object_name": str(getattr(slope_face_obj, "Name", "") or ""),
            "object_label": str(getattr(slope_face_obj, "Label", "") or ""),
            "status": breakline_status,
            "vertex_count": "",
            "triangle_or_point_count": "",
            "output_path": "roundabout_shared_breakline_contract",
            "notes": _join_review_notes(
                f"apron={getattr(apron_obj, 'SharedBreaklineAuditStatus', '')}" if apron_obj is not None else "apron=missing",
                f"subgrade={getattr(subgrade_obj, 'SharedBreaklineAuditStatus', '')}" if subgrade_obj is not None else "subgrade=missing",
                f"slope_face={getattr(slope_face_obj, 'SharedBreaklineAuditStatus', '')}" if slope_face_obj is not None else "slope_face=missing",
                "entry/exit connector, splitter-island, transitional entry/exit, and generic tie-slope outputs are disabled for roundabout generalization",
                "Recommended Action: Review roundabout source policy and rebuild if any roundabout output is missing.",
            ),
        }
    )
    return rows


def _corridor_roundabout_review_row(
    *,
    role: str,
    title: str,
    object_name: str,
    obj,
    notes: str,
) -> dict[str, object]:
    vertex_count = int(getattr(obj, "VertexCount", 0) or 0) if obj is not None else 0
    triangle_count = int(getattr(obj, "TriangleCount", 0) or 0) if obj is not None else 0
    status = "ready" if vertex_count > 0 and triangle_count > 0 else "missing"
    return {
        "role": role,
        "result": title,
        "object_name": str(getattr(obj, "Name", "") or object_name),
        "object_label": str(getattr(obj, "Label", "") or ""),
        "status": status,
        "vertex_count": vertex_count if obj is not None else "",
        "triangle_or_point_count": triangle_count if obj is not None else "",
        "output_path": "roundabout_output_contract" if obj is not None else "",
        "notes": notes or ("Roundabout output has not been built yet." if obj is None else ""),
    }


def _corridor_surface_role_contract_review_note(obj) -> str:
    status = str(getattr(obj, "ResultContractExpectedSurfaceRoleStatus", "") or "")
    expected = [str(value or "") for value in list(getattr(obj, "ResultContractExpectedSurfaceRoles", []) or []) if str(value or "")]
    matched = [str(value or "") for value in list(getattr(obj, "ResultContractMatchedSurfaceRoles", []) or []) if str(value or "")]
    consumed = [str(value or "") for value in list(getattr(obj, "ConsumedSurfaceRoleCounts", []) or []) if str(value or "")]
    if not status and not expected and not consumed:
        return ""
    parts = [f"surface role contract={status or 'unknown'}"]
    if expected:
        parts.append(f"expected={','.join(expected)}")
    if matched:
        parts.append(f"matched={','.join(matched)}")
    elif consumed:
        parts.append(f"consumed={','.join(consumed)}")
    return "; ".join(parts)


def _corridor_region_contract_review_note(obj) -> str:
    region_refs = [
        str(value or "")
        for value in list(getattr(obj, "ConsumedRegionRefs", []) or [])
        if str(value or "")
    ]
    control_refs = [
        str(value or "")
        for value in list(getattr(obj, "ConsumedIntersectionControlRegionRefs", []) or [])
        if str(value or "")
    ]
    if not region_refs and not control_refs:
        return ""
    parts = [f"region contract: regions={len(region_refs)}"]
    if region_refs:
        parts.append(f"refs={','.join(region_refs)}")
    if control_refs:
        parts.append(f"intersection_control_regions={len(control_refs)}")
        parts.append(f"control_refs={','.join(control_refs)}")
    return "; ".join(parts)


def _corridor_watertight_solid_review_note(obj) -> str:
    status = str(getattr(obj, "WatertightSolidReadinessStatus", "") or "")
    if not status:
        return ""
    physical_body_count = int(getattr(obj, "WatertightSolidPhysicalBodyTargetCount", 0) or 0)
    physical_body_readiness = str(getattr(obj, "WatertightSolidPhysicalBodyReadinessStatus", "") or "")
    digital_twin_readiness = str(getattr(obj, "WatertightSolidDigitalTwinReadinessStatus", "") or "")
    surface_like_count = int(getattr(obj, "WatertightSolidSurfaceLikeTargetCount", 0) or 0)
    envelope_count = int(getattr(obj, "WatertightSolidEnvelopeTargetCount", 0) or 0)
    station_span_count = int(getattr(obj, "WatertightSolidStationSpanCount", 0) or 0)
    missing_count = int(getattr(obj, "WatertightSolidMissingPrerequisiteCount", 0) or 0)
    blocked_count = int(getattr(obj, "WatertightSolidBlockedTargetCount", 0) or 0)
    parts = [
        f"watertight solid readiness={status}",
        f"digital_twin_readiness={digital_twin_readiness or 'unknown'}",
        f"physical_body_targets={physical_body_count}",
        f"physical_body_readiness={physical_body_readiness or 'unknown'}",
        f"surface_like_targets={surface_like_count}",
        f"envelope_targets={envelope_count}",
        f"station_spans={station_span_count}",
    ]
    if missing_count:
        parts.append(f"missing_prerequisites={missing_count}")
    if blocked_count:
        parts.append(f"blocked_targets={blocked_count}")
    return "; ".join(parts)


def _roundabout_ownership_intrusion_review_note(obj) -> str:
    status = str(getattr(obj, "RoundaboutOwnershipIntrusionStatus", "") or "")
    if not status or status == "not_applicable":
        return ""
    count = int(getattr(obj, "RoundaboutOwnershipIntrusionTriangleCount", 0) or 0)
    tested = int(getattr(obj, "RoundaboutOwnershipTestedTriangleCount", 0) or 0)
    clipped = int(getattr(obj, "RoundaboutOwnershipClippedTriangleCount", 0) or 0)
    clip_tested = int(getattr(obj, "RoundaboutOwnershipClipTestedTriangleCount", 0) or 0)
    radius = float(getattr(obj, "RoundaboutOwnershipRadius", 0.0) or 0.0)
    action = str(getattr(obj, "RoundaboutOwnershipRecommendedAction", "") or "")
    return _join_review_notes(
        f"roundabout_ownership={status}",
        f"intrusion_triangles={count}/{tested}",
        f"clipped_triangles={clipped}/{clip_tested}" if clipped or clip_tested else "",
        f"clip_boundary={str(getattr(obj, 'RoundaboutClipBoundaryRole', '') or '')}:{str(getattr(obj, 'RoundaboutClipBoundaryStatus', '') or '')}"
        if str(getattr(obj, "RoundaboutClipBoundaryRole", "") or "")
        else "",
        f"radius={radius:.3f}m" if radius else "",
        f"Recommended Action: {action}" if action and status == "warning" else "",
    )


def _corridor_build_review_row(
    role: str,
    title: str,
    object_name: str,
    obj,
    *,
    diagnostic=None,
    absent_note_for_role: Callable[[str], str] | None = None,
) -> dict[str, object]:
    if obj is None:
        notes = str(getattr(diagnostic, "PreviewDiagnostic", "") or "")
        if not notes and str(role or "") == "intersection_slope":
            notes = absent_note_for_role(role) if absent_note_for_role is not None else ""
        if not notes and str(role or "") == "intersection_tie_slope":
            notes = absent_note_for_role(role) if absent_note_for_role is not None else ""
        if not notes:
            notes = "Not built yet."
        status = _normalize_corridor_build_review_status(getattr(diagnostic, "PreviewStatus", "") or "missing")
        return {
            "role": role,
            "result": title,
            "object_name": object_name,
            "object_label": "",
            "status": status,
            "vertex_count": "",
            "triangle_or_point_count": "",
            "output_path": "",
            "notes": notes,
        }
    if role == "centerline":
        point_count = int(getattr(obj, "PointCount", 0) or 0)
        curve_kind = str(getattr(obj, "DisplayCurveKind", "") or "")
        preview_source = str(getattr(obj, "PreviewSource", "") or "")
        source_note = f"; source={preview_source}" if preview_source else ""
        watertight_note = _corridor_watertight_solid_review_note(obj)
        notes = f"Curve: {curve_kind or 'unknown'}{source_note}"
        if watertight_note:
            notes = f"{notes} | {watertight_note}"
        return _with_corridor_consumer_hardening_warning({
            "role": role,
            "result": title,
            "object_name": str(getattr(obj, "Name", "") or object_name),
            "object_label": str(getattr(obj, "Label", "") or object_name),
            "status": "ready",
            "vertex_count": "",
            "triangle_or_point_count": point_count,
            "output_path": _corridor_build_review_output_path(role, obj),
            "notes": notes,
        }, obj)
    vertex_count = int(getattr(obj, "VertexCount", 0) or 0)
    triangle_count = int(getattr(obj, "TriangleCount", 0) or 0)
    notes = str(getattr(obj, "SlopeFaceDiagnosticSummary", "") or "")
    issue_stations = str(getattr(obj, "SlopeFaceIssueStations", "") or "")
    if notes and issue_stations:
        notes = f"{notes} | issues: {issue_stations}"
    applied_section_diagnostics = str(getattr(obj, "AppliedSectionDiagnosticSummary", "") or "")
    if applied_section_diagnostics and applied_section_diagnostics != "diagnostics=0":
        notes = f"{notes} | applied sections: {applied_section_diagnostics}" if notes else f"applied sections: {applied_section_diagnostics}"
    applied_section_clip_review = str(getattr(obj, "AppliedSectionClipReviewSummary", "") or "")
    if applied_section_clip_review and applied_section_clip_review != "clip_rows=0":
        notes = f"{notes} | clipping: {applied_section_clip_review}" if notes else f"clipping: {applied_section_clip_review}"
    surface_role_contract = _corridor_surface_role_contract_review_note(obj)
    if surface_role_contract:
        notes = f"{notes} | {surface_role_contract}" if notes else surface_role_contract
    region_contract = _corridor_region_contract_review_note(obj)
    if region_contract:
        notes = f"{notes} | {region_contract}" if notes else region_contract
    watertight_note = _corridor_watertight_solid_review_note(obj)
    if watertight_note:
        notes = f"{notes} | {watertight_note}" if notes else watertight_note
    slope_boundary_note = _intersection_slope_face_boundary_review_note(obj)
    if slope_boundary_note:
        notes = f"{notes} | {slope_boundary_note}" if notes else slope_boundary_note
    if role == "intersection":
        notes = _intersection_surface_review_notes(obj)
    elif role == "intersection_slope":
        ready_loops = int(getattr(obj, "ReadyLoopCount", 0) or 0)
        skipped_loops = int(getattr(obj, "SkippedLoopCount", 0) or 0)
        source_refs = list(getattr(obj, "SourceLoopRefs", []) or [])
        perimeter_count = int(getattr(obj, "CurbReturnSlopeFacePerimeterCount", 0) or 0)
        perimeter_triangles = int(getattr(obj, "CurbReturnSlopeFacePerimeterTriangleCount", 0) or 0)
        perimeter_mode = str(getattr(obj, "CurbReturnSlopeFacePerimeterGenerationMode", "") or "")
        consumed_contract_summary = str(getattr(obj, "ConsumedIntersectionContractSummary", "") or "")
        consumed_diagnostics = int(getattr(obj, "ConsumedIntersectionContractDiagnosticCount", 0) or 0)
        notes = "Intersection-owned Slope Face output"
        if perimeter_count or perimeter_triangles:
            notes = (
                f"{notes}; curb_return_perimeters={perimeter_count}; "
                f"perimeter_triangles={perimeter_triangles}; mode={perimeter_mode or 'unknown'}"
            )
        notes = f"{notes}; ready_loops={ready_loops}; skipped_loops={skipped_loops}; source_loops={len(source_refs)}"
        if consumed_contract_summary and not perimeter_count:
            notes = f"{notes}; consumed_contracts={consumed_contract_summary}"
        if consumed_diagnostics:
            notes = f"{notes}; consumed_contract_diagnostics={consumed_diagnostics}"
        cell_note = _intersection_slope_face_cell_review_note(obj)
        if cell_note:
            notes = f"{notes}; {cell_note}"
        upper_panel_note = _intersection_slope_face_upper_panel_review_note(obj)
        if upper_panel_note:
            notes = f"{notes}; {upper_panel_note}"
        owner_fill_readiness = str(getattr(obj, "IntersectionSlopeFaceOwnerFillReadinessStatus", "") or "")
        owner_fill_summary = str(getattr(obj, "IntersectionSlopeFaceOwnerFillReadinessSummary", "") or "")
        if owner_fill_readiness:
            notes = f"{notes}; owner_fill={owner_fill_readiness}"
            if owner_fill_summary:
                notes = f"{notes}; {owner_fill_summary}"
    elif role == "intersection_tie_slope":
        notes = _intersection_tie_slope_surface_review_note(obj)
    elif role in {"design", "daylight"}:
        clipped = int(getattr(obj, "IntersectionExclusionClippedTriangleCount", 0) or 0)
        kept = int(getattr(obj, "IntersectionExclusionKeptTriangleCount", 0) or 0)
        exclusion_status = str(getattr(obj, "IntersectionExclusionClipStatus", "") or "")
        if exclusion_status:
            boundary_strategy = str(getattr(obj, "IntersectionExclusionBoundaryStrategy", "") or "")
            aligned = int(getattr(obj, "IntersectionExclusionPracticalBoundaryAligned", 0) or 0)
            suffix_parts = [
                f"intersection exclusion={exclusion_status}",
                f"clipped={clipped}",
                f"kept={kept}",
            ]
            if boundary_strategy:
                suffix_parts.append(f"boundary={boundary_strategy}")
            if aligned:
                suffix_parts.append("aligned=practical")
            height_status = str(getattr(obj, "IntersectionHeightClipStatus", "") or "")
            if height_status:
                height_suppressed = int(getattr(obj, "IntersectionHeightClipSuppressedTriangleCount", 0) or 0)
                height_tested = int(getattr(obj, "IntersectionHeightClipTestedTriangleCount", 0) or 0)
                suffix_parts.append(f"height_clip={height_status} suppressed={height_suppressed}/{height_tested}")
            loop_status = str(getattr(obj, "IntersectionSlopeLoopSuppressStatus", "") or "")
            if loop_status:
                loop_suppressed = int(getattr(obj, "IntersectionSlopeLoopSuppressSuppressedTriangleCount", 0) or 0)
                loop_tested = int(getattr(obj, "IntersectionSlopeLoopSuppressTestedTriangleCount", 0) or 0)
                loop_ready = int(getattr(obj, "IntersectionSlopeLoopSuppressReadyLoopCount", 0) or 0)
                suffix_parts.append(f"loop_suppress={loop_status} suppressed={loop_suppressed}/{loop_tested} ready_loops={loop_ready}")
            suffix = "; ".join(suffix_parts)
            notes = f"{notes} | {suffix}" if notes else suffix
    shared_breakline_note = _shared_breakline_review_note(obj)
    if shared_breakline_note:
        notes = f"{notes} | {shared_breakline_note}" if notes else shared_breakline_note
    roundabout_ownership_note = _roundabout_ownership_intrusion_review_note(obj)
    if roundabout_ownership_note:
        notes = f"{notes} | {roundabout_ownership_note}" if notes else roundabout_ownership_note
    if not notes:
        surface_kind = str(getattr(obj, "SurfaceKind", "") or "")
        notes = f"Surface kind: {surface_kind or 'unknown'}"
    status = "ready" if vertex_count > 0 and triangle_count > 0 else "empty"
    if str(getattr(obj, "RoundaboutOwnershipIntrusionStatus", "") or "") == "warning":
        status = "warning"
    return _with_corridor_consumer_hardening_warning({
        "role": role,
        "result": title,
        "object_name": str(getattr(obj, "Name", "") or object_name),
        "object_label": str(getattr(obj, "Label", "") or object_name),
        "status": status,
        "vertex_count": vertex_count,
        "triangle_or_point_count": triangle_count,
        "output_path": _corridor_build_review_output_path(role, obj),
        "notes": notes,
    }, obj)


def _intersection_slope_face_cell_review_note(obj) -> str:
    cell_count = int(getattr(obj, "IntersectionSlopeFaceCellCount", 0) or 0)
    cell_ready = int(getattr(obj, "IntersectionSlopeFaceCellReadyCount", 0) or 0)
    cell_open = int(getattr(obj, "IntersectionSlopeFaceCellOpenCount", 0) or 0)
    cell_missing_edge = int(getattr(obj, "IntersectionSlopeFaceCellMissingEdgeCount", 0) or 0)
    cell_triangles = int(getattr(obj, "IntersectionSlopeFaceCellTriangleCount", 0) or 0)
    if not any((cell_count, cell_ready, cell_open, cell_missing_edge, cell_triangles)):
        return ""
    status = str(getattr(obj, "IntersectionSlopeFaceCellStatus", "") or "").strip()
    parts = [
        f"cells={cell_count}",
        f"ready={cell_ready}",
        f"open={cell_open}",
        f"missing_edges={cell_missing_edge}",
        f"cell_triangles={cell_triangles}",
    ]
    if status:
        parts.insert(0, f"cell_status={status}")
    return "intersection_slope_face_cell " + " ".join(parts)


def _intersection_slope_face_upper_panel_review_note(obj) -> str:
    candidate_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelCandidateCount", 0) or 0)
    accepted_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelAcceptedCount", 0) or 0)
    generated_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0)
    triangle_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelTriangleCount", 0) or 0)
    suppressed_count = int(getattr(obj, "IntersectionSlopeFaceSuppressedUpperCellCount", 0) or 0)
    if not any((candidate_count, accepted_count, generated_count, triangle_count, suppressed_count)):
        return ""
    mode = str(getattr(obj, "IntersectionUpperSlopeFacePanelGenerationMode", "") or "")
    source_mode = str(getattr(obj, "IntersectionUpperSlopeFacePanelSourceMode", "") or "")
    coverage_status = str(getattr(obj, "IntersectionUpperSlopeFacePanelCoverageStatus", "") or "")
    coverage_summary = str(getattr(obj, "IntersectionUpperSlopeFacePanelCoverageSummary", "") or "")
    expected_group_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelExpectedGroupCount", 0) or 0)
    missing_groups = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionUpperSlopeFacePanelMissingGroups", []) or [])
        if str(value or "")
    ]
    parts = [
        f"upper_panels={generated_count}/{accepted_count}",
        f"candidates={candidate_count}",
        f"triangles={triangle_count}",
        f"suppressed_legacy_upper_cells={suppressed_count}",
    ]
    if mode:
        parts.append(f"mode={mode}")
    if source_mode:
        parts.append(f"source={source_mode}")
    if coverage_status:
        parts.append(f"coverage={coverage_status}")
    if expected_group_count:
        parts.append(f"expected_groups={expected_group_count}")
    if coverage_summary:
        parts.append(coverage_summary)
    if missing_groups:
        parts.append(f"missing_groups={','.join(missing_groups[:8])}")
    return "intersection_upper_slope_face_panel " + " ".join(parts)


def _intersection_tie_slope_surface_review_note(obj) -> str:
    status = str(getattr(obj, "IntersectionTieSlopeStatus", "") or "").strip()
    coverage_status = str(getattr(obj, "IntersectionTieSlopeCoverageStatus", "") or "").strip()
    coverage_summary = str(getattr(obj, "IntersectionTieSlopeCoverageSummary", "") or "").strip()
    count = int(getattr(obj, "IntersectionTieSlopeCount", 0) or 0)
    ready = int(getattr(obj, "IntersectionTieSlopeReadyCount", 0) or 0)
    warning = int(getattr(obj, "IntersectionTieSlopeWarningCount", 0) or 0)
    error = int(getattr(obj, "IntersectionTieSlopeErrorCount", 0) or 0)
    triangles = int(getattr(obj, "IntersectionTieSlopeTriangleCount", 0) or getattr(obj, "TriangleCount", 0) or 0)
    consumed = int(getattr(obj, "IntersectionTieSlopeConsumedRowCount", 0) or 0)
    rejected = int(getattr(obj, "IntersectionTieSlopeRejectedRowCount", 0) or 0)
    shared = int(getattr(obj, "IntersectionTieSlopeSharedBreaklineCount", 0) or 0)
    window_rows = int(getattr(obj, "IntersectionTieSlopeAppliedSectionWindowRowCount", 0) or 0)
    window_accepted = int(getattr(obj, "IntersectionTieSlopeAppliedSectionWindowAcceptedCount", 0) or 0)
    window_suppressed = int(getattr(obj, "IntersectionTieSlopeAppliedSectionWindowSuppressedCount", 0) or 0)
    geometry_source = str(getattr(obj, "IntersectionTieSlopeGeometrySource", "") or "").strip()
    summary = str(getattr(obj, "IntersectionTieSlopeReadinessSummary", "") or "").strip()
    action = str(getattr(obj, "IntersectionTieSlopeRecommendedAction", "") or "").strip()
    diagnostics = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionTieSlopeDiagnostics", []) or [])
        if str(value or "")
    ]
    parts = [
        "Intersection Tie Slope output",
        f"status={status or 'unknown'}",
        f"ready={ready}/{count}",
        f"triangles={triangles}",
        f"consumed={consumed}",
        f"rejected={rejected}",
        f"shared_breaklines={shared}",
    ]
    if warning or error:
        parts.append(f"warnings={warning}")
        parts.append(f"errors={error}")
    if coverage_status:
        parts.append(f"coverage={coverage_status}")
    if coverage_summary:
        parts.append(coverage_summary)
    if window_rows:
        parts.append(
            "Applied Section window candidates: "
            f"rows={window_rows}; accepted={window_accepted}; suppressed={window_suppressed}; "
            "source=applied_section_context_transition_window"
            + (f"; geometry_source={geometry_source}" if geometry_source else "")
        )
    if summary:
        parts.append(summary)
    if diagnostics:
        parts.append("diagnostics=" + "; ".join(_unique_text_values(diagnostics)[:3]))
    if action:
        parts.append("Recommended Action: " + action)
    return "; ".join(part for part in parts if str(part or "").strip())


def _shared_breakline_review_note(obj) -> str:
    status = str(getattr(obj, "SharedBreaklineStatus", "") or "")
    result_id = str(getattr(obj, "SharedBreaklineResultId", "") or "")
    if not status and not result_id:
        return ""
    count = int(getattr(obj, "SharedBreaklineCount", 0) or 0)
    consumed = int(getattr(obj, "SharedBreaklineConsumedCount", 0) or 0)
    warnings = int(getattr(obj, "SharedBreaklineWarningCount", 0) or 0)
    errors = int(getattr(obj, "SharedBreaklineErrorCount", 0) or 0)
    parts = [
        f"shared_breakline={status or 'unknown'} "
        f"consumed={consumed}/{count} warnings={warnings} errors={errors}"
    ]
    audit_status = str(getattr(obj, "SharedBreaklineAuditStatus", "") or "")
    if audit_status:
        geometry_match = int(getattr(obj, "SharedBreaklineGeometryMatchCount", 0) or 0)
        geometry_mismatch = int(getattr(obj, "SharedBreaklineGeometryMismatchCount", 0) or 0)
        mesh_match = int(getattr(obj, "SharedBreaklineMeshMatchCount", 0) or 0)
        mesh_mismatch = int(getattr(obj, "SharedBreaklineMeshMismatchCount", 0) or 0)
        missing = int(getattr(obj, "SharedBreaklineMissingConsumerCount", 0) or 0)
        mismatch = int(getattr(obj, "SharedBreaklineMismatchCount", 0) or 0)
        reversed_count = int(getattr(obj, "SharedBreaklineReversedEdgeCount", 0) or 0)
        parts.append(
            f"audit={audit_status} geometry={geometry_match}/{geometry_match + geometry_mismatch} "
            f"mesh={mesh_match}/{mesh_match + mesh_mismatch} "
            f"missing={missing} mismatch={mismatch} reversed={reversed_count}"
        )
    solid_status = str(getattr(obj, "SharedBreaklineSolidReadinessStatus", "") or "")
    if solid_status:
        open_end_count = int(getattr(obj, "SharedBreaklineSolidOpenEndCount", 0) or 0)
        duplicate_edge_count = int(getattr(obj, "SharedBreaklineSolidDuplicateEdgeCount", 0) or 0)
        solid_reversed_count = int(getattr(obj, "SharedBreaklineSolidReversedEdgeCount", 0) or 0)
        non_manifold_count = int(getattr(obj, "SharedBreaklineSolidNonManifoldNodeCount", 0) or 0)
        parts.append(
            f"solid_readiness={solid_status} open={open_end_count} "
            f"duplicate={duplicate_edge_count} reversed={solid_reversed_count} non_manifold={non_manifold_count}"
        )
    return "; ".join(parts)


def _corridor_build_review_output_path(role: str, obj) -> str:
    """Label whether a Build Parametric result consumed a v1 contract or fallback output."""

    if obj is None:
        return ""
    explicit = str(getattr(obj, "IntersectionOutputPath", "") or "").strip()
    if explicit:
        return explicit
    role_text = str(role or "")
    implementation_mode = str(getattr(obj, "IntersectionImplementationMode", "") or "")
    if role_text == "intersection":
        if not implementation_mode or implementation_mode == "legacy_patch_frozen":
            return "legacy_output"
        return "contract_consumed"
    if role_text == "intersection_slope":
        contract_refs = [str(value or "") for value in list(getattr(obj, "ConsumedIntersectionContractRefs", []) or []) if str(value or "")]
        if contract_refs:
            return "contract_consumed"
        ready_loops = int(getattr(obj, "ReadyLoopCount", 0) or 0)
        source_refs = [str(value or "") for value in list(getattr(obj, "SourceLoopRefs", []) or []) if str(value or "")]
        return "contract_consumed" if ready_loops and source_refs else "inferred_fallback"
    source_mode = str(getattr(obj, "ConsumedCenterlineSourceMode", "") or getattr(obj, "PreviewSource", "") or "")
    centerline_fallback = bool(int(getattr(obj, "CenterlineConsumerFallbackActive", 0) or 0))
    supplemental_fallback = bool(int(getattr(obj, "SupplementalCompatibilityFallbackActive", 0) or 0))
    result_contract_fallback = bool(int(getattr(obj, "ResultContractCompatibilityFallbackActive", 0) or 0))
    if centerline_fallback or supplemental_fallback or result_contract_fallback:
        return "inferred_fallback"
    if source_mode and source_mode != "centerline3d_source_geometry":
        return "inferred_fallback"
    return "contract_consumed"


def _intersection_slope_face_boundary_review_note(obj) -> str:
    result_id = str(getattr(obj, "IntersectionSlopeFaceBoundaryResultId", "") or "")
    summary = str(getattr(obj, "IntersectionSlopeFaceBoundarySummary", "") or "")
    strip_generation_mode = str(getattr(obj, "IntersectionSlopeFaceBoundaryStripGenerationMode", "") or "")
    strip_output_path = str(getattr(obj, "IntersectionSlopeFaceBoundaryStripOutputPath", "") or "")
    strip_diagnostic = str(getattr(obj, "IntersectionSlopeFaceBoundaryStripDiagnostic", "") or "")
    strip_count = int(getattr(obj, "IntersectionSlopeFaceBoundaryStripCount", 0) or 0)
    strip_triangles = int(getattr(obj, "IntersectionSlopeFaceBoundaryStripTriangleCount", 0) or 0)
    strip_note_parts: list[str] = []
    if strip_generation_mode:
        strip_note_parts.append(f"strip_generation={strip_generation_mode}")
    if strip_output_path:
        strip_note_parts.append(f"strip_output={strip_output_path}")
    if strip_count or strip_triangles:
        strip_note_parts.append(f"strips={strip_count}, triangles={strip_triangles}")
    if strip_diagnostic:
        strip_note_parts.append(f"strip_diagnostic={strip_diagnostic}")
    strip_note = f"; {'; '.join(strip_note_parts)}" if strip_note_parts else ""
    if not result_id and not summary:
        return strip_note.lstrip("; ")
    if summary:
        return f"slope_face_boundary={summary}{strip_note}"
    status = str(getattr(obj, "IntersectionSlopeFaceBoundaryStatus", "") or "")
    ready = int(getattr(obj, "IntersectionSlopeFaceBoundaryReadyCount", 0) or 0)
    count = int(getattr(obj, "IntersectionSlopeFaceBoundaryCount", 0) or 0)
    warnings = int(getattr(obj, "IntersectionSlopeFaceBoundaryWarningCount", 0) or 0)
    return f"slope_face_boundary=boundary_result={result_id}; status={status}; ready={ready}/{count}; warnings={warnings}{strip_note}"


def _with_corridor_consumer_hardening_warning(row: dict[str, object], obj) -> dict[str, object]:
    """Warn when Build Corridor consumed a fallback instead of the preferred v1 result path."""

    if obj is None:
        return row
    source_mode = str(getattr(obj, "ConsumedCenterlineSourceMode", "") or getattr(obj, "PreviewSource", "") or "")
    centerline_fallback = bool(int(getattr(obj, "CenterlineConsumerFallbackActive", 0) or 0))
    supplemental_fallback = bool(int(getattr(obj, "SupplementalCompatibilityFallbackActive", 0) or 0))
    result_contract_fallback = bool(int(getattr(obj, "ResultContractCompatibilityFallbackActive", 0) or 0))
    row_role = str(row.get("role", "") or "")
    warnings: list[str] = []
    if centerline_fallback or (source_mode and source_mode != "centerline3d_source_geometry"):
        warnings.append(
            f"warning:centerline source fallback={source_mode or 'unknown'}; expected=centerline3d_source_geometry"
        )
    if supplemental_fallback:
        warnings.append("warning:supplemental compatibility fallback active; rebuild Applied Sections")
    if result_contract_fallback and row_role != "centerline":
        reason = str(getattr(obj, "ResultContractCompatibilityReason", "") or "missing Subassembly link result contract")
        warnings.append(f"warning:result contract fallback active; {reason}")
    surface_role_status = str(getattr(obj, "ResultContractExpectedSurfaceRoleStatus", "") or "")
    if surface_role_status == "missing":
        expected = [
            str(value or "")
            for value in list(getattr(obj, "ResultContractExpectedSurfaceRoles", []) or [])
            if str(value or "")
        ]
        warnings.append(f"warning:expected surface role missing={','.join(expected) or 'unknown'}")
    watertight_status = str(getattr(obj, "WatertightSolidReadinessStatus", "") or "")
    if watertight_status in {"blocked", "partial"}:
        missing_count = int(getattr(obj, "WatertightSolidMissingPrerequisiteCount", 0) or 0)
        blocked_count = int(getattr(obj, "WatertightSolidBlockedTargetCount", 0) or 0)
        warnings.append(
            f"warning:watertight solid readiness={watertight_status}; "
            f"missing_prerequisites={missing_count}; blocked_targets={blocked_count}"
        )
    physical_body_readiness = str(getattr(obj, "WatertightSolidPhysicalBodyReadinessStatus", "") or "")
    if physical_body_readiness == "blocked":
        reason = str(getattr(obj, "WatertightSolidPhysicalBodyReadinessReason", "") or "missing physical-body targets")
        warnings.append(f"warning:physical-body watertight readiness=blocked; {reason}")
    if not warnings:
        return row
    output = dict(row)
    existing_notes = str(output.get("notes", "") or "").strip()
    output["notes"] = f"{existing_notes} | {' | '.join(warnings)}" if existing_notes else " | ".join(warnings)
    if str(output.get("output_path", "") or "") != "legacy_output":
        output["output_path"] = "inferred_fallback"
    if str(output.get("status", "") or "") == "ready":
        output["status"] = "warning"
    return output


def _intersection_surface_review_notes(obj) -> str:
    parts: list[str] = []
    tie_in_count = int(getattr(obj, "TieInEdgeCount", 0) or 0)
    boundary_count = int(getattr(obj, "PatchBoundaryPointCount", 0) or 0)
    grading_policy_ref = str(getattr(obj, "IntersectionGradingPolicyRef", "") or "")
    grading_mode = str(getattr(obj, "IntersectionGradingMode", "") or "")
    target_crossfall = str(getattr(obj, "IntersectionTargetCrossfallPercent", "") or "")
    grading_z_delta = float(getattr(obj, "IntersectionGradingZDeltaMax", 0.0) or 0.0)
    drainage_status = str(getattr(obj, "IntersectionDrainageCoverageStatus", "") or "")
    tie_in_preview_ref = str(getattr(obj, "TieInEdgePreviewRef", "") or "")
    tie_in_preview_status = str(getattr(obj, "TieInEdgePreviewStatus", "") or "")
    tie_in_diagnostic_count = int(getattr(obj, "TieInEdgeDiagnosticCount", 0) or 0)
    intersection_diagnostic_count = int(getattr(obj, "IntersectionDiagnosticCount", 0) or 0)
    boundary_status = str(getattr(obj, "IntersectionBoundaryStatus", "") or "")
    boundary_segment_count = int(getattr(obj, "IntersectionBoundarySegmentCount", 0) or 0)
    boundary_arc_count = int(getattr(obj, "IntersectionBoundaryArcSegmentCount", 0) or 0)
    boundary_preview_ref = str(getattr(obj, "IntersectionBoundaryPreviewRef", "") or "")
    boundary_diagnostic_count = int(getattr(obj, "IntersectionBoundaryDiagnosticCount", 0) or 0)
    patch_boundary_status = str(getattr(obj, "IntersectionPatchBoundaryStatus", "") or "")
    patch_boundary_point_count = int(getattr(obj, "IntersectionPatchBoundaryOrderedPointCount", 0) or 0)
    patch_boundary_closed = str(getattr(obj, "IntersectionPatchBoundaryClosed", "") or "")
    patch_boundary_self_crossing = str(getattr(obj, "IntersectionPatchBoundarySelfCrossing", "") or "")
    patch_boundary_diagnostic_count = int(getattr(obj, "IntersectionPatchBoundaryDiagnosticCount", 0) or 0)
    patch_boundary_diagnostics = [str(value or "") for value in list(getattr(obj, "IntersectionPatchBoundaryDiagnostics", []) or []) if str(value or "")]
    patch_boundary_hole_count = int(getattr(obj, "IntersectionPatchBoundaryHoleRingCount", 0) or 0)
    patch_boundary_island_count = int(getattr(obj, "IntersectionPatchBoundaryIslandRingCount", 0) or 0)
    superelevation_context = str(getattr(obj, "IntersectionSuperelevationContext", "") or "")
    low_point_count = int(getattr(obj, "IntersectionTINLowPointCandidateCount", 0) or 0)
    low_point_z = float(getattr(obj, "IntersectionTINLowPointZ", 0.0) or 0.0)
    flow_hint_summary = str(getattr(obj, "IntersectionBoundaryToLowFlowHintSummary", "") or "")
    patch_degenerate_count = int(getattr(obj, "PatchDegenerateTriangleCount", 0) or 0)
    patch_long_edge_count = int(getattr(obj, "PatchBoundaryLongEdgeCount", 0) or 0)
    patch_triangulation_mode = str(getattr(obj, "PatchTriangulationMode", "") or "")
    patch_boundary_strategy = str(getattr(obj, "PatchSurfaceBoundaryStrategy", "") or "")
    patch_boundary_role_summary = str(getattr(obj, "PatchBoundaryRoleSummary", "") or "")
    patch_skinny_triangle_count = int(getattr(obj, "PatchTriangleSkinnyCount", 0) or 0)
    implementation_mode = str(getattr(obj, "IntersectionImplementationMode", "") or "")
    redesign_path = str(getattr(obj, "IntersectionRedesignPath", "") or "")
    output_path = str(getattr(obj, "IntersectionOutputPath", "") or "")
    contract_summary = str(getattr(obj, "ConsumedIntersectionContractSummary", "") or "")
    surface_patch_summary = str(getattr(obj, "IntersectionSurfacePatchSummary", "") or "")
    surface_patch_footprint_summary = str(getattr(obj, "IntersectionSurfacePatchFootprintSummary", "") or "")
    surface_patch_result_id = str(getattr(obj, "IntersectionSurfacePatchResultId", "") or "")
    surface_boundary_mode = str(getattr(obj, "IntersectionSurfaceBoundaryMode", "") or "")
    surface_boundary_loop = str(getattr(obj, "IntersectionSurfaceBoundaryLoopKind", "") or "")
    surface_boundary_fallback = str(getattr(obj, "IntersectionSurfaceBoundaryFallbackReason", "") or "")
    surface_boundary_summary = str(getattr(obj, "IntersectionSurfaceBoundaryDiagnosticSummary", "") or "")
    surface_zone_output_summary = str(getattr(obj, "IntersectionSurfaceZoneOutputSummary", "") or "")
    surface_zone_output_contract_status = str(getattr(obj, "IntersectionSurfaceZoneOutputContractStatus", "") or "")
    surface_zone_output_handoff = str(getattr(obj, "IntersectionSurfaceZoneOutputDigitalTwinHandoff", "") or "")
    surface_replacement_summary = str(getattr(obj, "IntersectionSurfaceReplacementSummary", "") or "")
    surface_replacement_gate = str(getattr(obj, "IntersectionSurfaceReplacementGateStatus", "") or "")
    surface_patch_contract_status = str(getattr(obj, "IntersectionSurfacePatchOutputContractStatus", "") or "")
    surface_patch_handoff = str(getattr(obj, "IntersectionSurfacePatchDigitalTwinHandoff", "") or "")
    surface_patch_transitional_reason = str(getattr(obj, "IntersectionSurfacePatchTransitionalReason", "") or "")
    surface_patch_replacement_path = str(getattr(obj, "IntersectionSurfacePatchReplacementPath", "") or "")
    legacy_patch_audit_summary = str(getattr(obj, "IntersectionLegacyPatchCompatibilityAuditSummary", "") or "")
    surface_patch_row_statuses = _surface_patch_review_status_note(obj)
    surface_patch_row_diagnostics = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionSurfacePatchRowDiagnostics", []) or [])
        if str(value or "")
    ]
    normalized_surface_patch_available = bool(surface_patch_result_id or surface_patch_summary or surface_patch_row_statuses)
    if tie_in_count:
        parts.append(f"tie-in edges={tie_in_count}")
    if boundary_count and not normalized_surface_patch_available:
        parts.append(f"boundary points={boundary_count}")
    if grading_policy_ref:
        parts.append(f"grading policy={_display_source_id(grading_policy_ref, 'grading:')}")
    if grading_mode:
        parts.append(f"grading={grading_mode}")
    if target_crossfall:
        parts.append(f"target crossfall={target_crossfall}%")
    if grading_z_delta:
        parts.append(f"max z adjustment={grading_z_delta:.3f}m")
    if drainage_status:
        parts.append(f"drainage={drainage_status}")
    if superelevation_context:
        parts.append(f"superelevation={superelevation_context}")
    if low_point_count:
        parts.append(f"low-point candidates={low_point_count}, z={low_point_z:.3f}")
    if flow_hint_summary:
        parts.append(f"flow hint={flow_hint_summary}")
    if tie_in_preview_ref:
        parts.append(f"tie-in preview={tie_in_preview_ref}")
    if tie_in_preview_status:
        parts.append(f"tie-in status={tie_in_preview_status}")
    if tie_in_diagnostic_count:
        parts.append(f"tie-in diagnostics={tie_in_diagnostic_count}")
    if intersection_diagnostic_count:
        parts.append(f"intersection diagnostics={intersection_diagnostic_count}")
    if boundary_status:
        parts.append(f"boundary={boundary_status}")
    if boundary_segment_count:
        parts.append(f"boundary segments={boundary_segment_count}")
    if boundary_arc_count:
        parts.append(f"boundary arcs={boundary_arc_count}")
    if boundary_preview_ref:
        parts.append(f"boundary preview={boundary_preview_ref}")
    if boundary_diagnostic_count:
        parts.append(f"boundary diagnostics={boundary_diagnostic_count}")
    if normalized_surface_patch_available:
        parts.append("legacy_patch_review=metadata_only")
    if legacy_patch_audit_summary:
        parts.append(f"legacy_patch_audit={legacy_patch_audit_summary}")
    if patch_boundary_status and not normalized_surface_patch_available:
        parts.append(f"patch boundary={patch_boundary_status}")
    if patch_boundary_point_count and not normalized_surface_patch_available:
        parts.append(f"patch boundary points={patch_boundary_point_count}")
    if patch_boundary_closed and not normalized_surface_patch_available:
        parts.append(f"patch boundary closed={patch_boundary_closed}")
    if patch_boundary_self_crossing == "Yes" and not normalized_surface_patch_available:
        parts.append("patch boundary self-crossing=Yes")
    if patch_boundary_hole_count and not normalized_surface_patch_available:
        parts.append(f"patch boundary holes={patch_boundary_hole_count}")
    if patch_boundary_island_count and not normalized_surface_patch_available:
        parts.append(f"patch boundary islands={patch_boundary_island_count}")
    if patch_boundary_diagnostic_count and not normalized_surface_patch_available:
        parts.append(f"patch boundary diagnostics={patch_boundary_diagnostic_count}")
        if patch_boundary_diagnostics:
            parts.append(f"patch boundary first diagnostic={patch_boundary_diagnostics[0]}")
    if patch_degenerate_count and not normalized_surface_patch_available:
        parts.append(f"degenerate triangles={patch_degenerate_count}")
    if patch_long_edge_count and not normalized_surface_patch_available:
        parts.append(f"long boundary edges={patch_long_edge_count}")
    if patch_triangulation_mode and not normalized_surface_patch_available:
        parts.append(f"triangulation={patch_triangulation_mode}")
    if patch_boundary_strategy and not normalized_surface_patch_available:
        parts.append(f"surface boundary={patch_boundary_strategy}")
    if patch_boundary_role_summary and not normalized_surface_patch_available:
        parts.append(f"boundary roles={patch_boundary_role_summary}")
    if patch_skinny_triangle_count and not normalized_surface_patch_available:
        parts.append(f"skinny triangles={patch_skinny_triangle_count}")
    if implementation_mode:
        parts.append(f"implementation={implementation_mode}")
    if redesign_path:
        parts.append(f"next={redesign_path}")
    if output_path:
        parts.append(f"output_path={output_path}")
    if contract_summary:
        parts.append(f"consumed_contracts={contract_summary}")
    if surface_patch_result_id:
        parts.append(f"surface_patch_result={surface_patch_result_id}")
    if surface_patch_summary:
        parts.append(f"surface_patch={surface_patch_summary}")
    if surface_patch_footprint_summary:
        parts.append(f"surface_patch_footprint={surface_patch_footprint_summary}")
    if surface_boundary_mode:
        parts.append(f"surface_boundary_mode={surface_boundary_mode}")
    if surface_boundary_loop:
        parts.append(f"surface_boundary_loop={surface_boundary_loop}")
    if surface_boundary_fallback:
        parts.append(f"surface_boundary_fallback={surface_boundary_fallback}")
    if surface_boundary_summary:
        parts.append(f"surface_boundary_review={surface_boundary_summary}")
    if surface_zone_output_summary:
        parts.append(f"surface_zone_output={surface_zone_output_summary}")
    if surface_zone_output_contract_status:
        parts.append(f"surface_zone_output_contract={surface_zone_output_contract_status}")
    if surface_zone_output_handoff:
        parts.append(f"surface_zone_output_handoff={surface_zone_output_handoff}")
    if surface_replacement_summary:
        parts.append(f"surface_replacement={surface_replacement_summary}")
    if surface_replacement_gate:
        parts.append(f"surface_replacement_gate={surface_replacement_gate}")
    if surface_patch_contract_status:
        parts.append(f"surface_patch_contract={surface_patch_contract_status}")
    if surface_patch_handoff:
        parts.append(f"surface_patch_handoff={surface_patch_handoff}")
    if surface_patch_transitional_reason:
        parts.append(f"surface_patch_transitional_reason={surface_patch_transitional_reason}")
    if surface_patch_replacement_path:
        parts.append(f"surface_patch_replacement={surface_patch_replacement_path}")
    if surface_patch_row_statuses:
        parts.append(f"surface_patch_rows={surface_patch_row_statuses}")
    if surface_patch_row_diagnostics:
        parts.append(f"surface_patch_row_diagnostics={len(surface_patch_row_diagnostics)}")
    return "; ".join(parts)


def _surface_patch_review_status_note(obj) -> str:
    statuses: list[str] = []
    for label, attr in (
        ("boundary", "IntersectionSurfacePatchBoundaryRowStatuses"),
        ("triangulation", "IntersectionSurfacePatchTriangulationRowStatuses"),
        ("quality", "IntersectionSurfacePatchQualityRowStatuses"),
    ):
        values = [str(value or "") for value in list(getattr(obj, attr, []) or []) if str(value or "")]
        if values:
            row_status = values[0].rsplit(":", 1)[-1]
            statuses.append(f"{label}={row_status}")
    return ", ".join(statuses)


def applied_sections_review_summary(applied) -> dict[str, object]:
    """Summarize Applied Sections as the source context for Build Corridor rows."""

    if applied is None:
        return {
            "status": "missing",
            "summary": "Applied Sections: missing",
            "diagnostics": "Run Applied Sections before Build Parametric.",
            "station_count": 0,
            "diagnostic_count": 0,
        }
    station_rows = list(getattr(applied, "station_rows", []) or [])
    sections = list(getattr(applied, "sections", []) or [])
    stations = []
    for row in station_rows:
        try:
            stations.append(float(getattr(row, "station", 0.0) or 0.0))
        except Exception:
            pass
    diagnostic_count = sum(len(list(getattr(section, "diagnostic_rows", []) or [])) for section in sections)
    ditch_point_count = sum(
        1
        for section in sections
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "ditch_surface"
    )
    slope_face_count = sum(
        1
        for section in sections
        if float(getattr(section, "daylight_left_width", 0.0) or 0.0) > 0.0
        or float(getattr(section, "daylight_right_width", 0.0) or 0.0) > 0.0
    )
    region_count = len({str(getattr(section, "region_id", "") or "") for section in sections if str(getattr(section, "region_id", "") or "")})
    assembly_count = len({str(getattr(section, "assembly_id", "") or "") for section in sections if str(getattr(section, "assembly_id", "") or "")})
    structure_refs = {
        ref
        for section in sections
        for ref in [_first_active_structure_ref(section)]
        if ref
    }
    structure_count = len(structure_refs)
    station_range = f"{min(stations):.3f}->{max(stations):.3f}" if stations else "no stations"
    summary = (
        f"{len(station_rows)} STA | {station_range} | "
        f"regions:{region_count} | assemblies:{assembly_count} | structures:{structure_count} | "
        f"ditch_pts:{ditch_point_count} | slope_rows:{slope_face_count}"
    )
    diagnostics = f"{diagnostic_count} diagnostic(s)" if diagnostic_count else "ok"
    return {
        "status": "warn" if diagnostic_count else "ok",
        "summary": summary,
        "diagnostics": diagnostics,
        "station_count": len(station_rows),
        "station_range": station_range,
        "diagnostic_count": diagnostic_count,
        "ditch_point_count": ditch_point_count,
        "slope_face_count": slope_face_count,
        "region_count": region_count,
        "assembly_count": assembly_count,
        "structure_count": structure_count,
        "structure_refs": sorted(structure_refs),
    }


def subassembly_surface_role_review_note(applied, *, surface_role: str) -> str:
    if applied is None:
        return ""
    sections = list(getattr(applied, "sections", []) or [])
    if not sections:
        return ""
    linked_section_count = 0
    link_count = 0
    subassembly_refs: list[str] = []
    preset_refs: list[str] = []
    preset_statuses: list[str] = []
    role = str(surface_role or "").strip()
    for section in sections:
        section_has_role = False
        subassembly_by_id = {
            str(getattr(row, "subassembly_id", "") or "").strip(): row
            for row in list(getattr(section, "subassembly_rows", []) or [])
            if str(getattr(row, "subassembly_id", "") or "").strip()
        }
        for link in list(getattr(section, "subassembly_link_rows", []) or []):
            if str(getattr(link, "surface_role", "") or "").strip() != role:
                continue
            section_has_role = True
            link_count += 1
            subassembly_ref = str(getattr(link, "subassembly_ref", "") or "")
            subassembly_refs.append(subassembly_ref)
            subassembly = subassembly_by_id.get(subassembly_ref.strip())
            if subassembly is not None:
                preset_ref = str(getattr(subassembly, "preset_ref", "") or "").strip()
                preset_status = str(getattr(subassembly, "preset_status", "") or "").strip()
                if preset_ref:
                    preset_refs.append(preset_ref)
                if preset_status:
                    preset_statuses.append(preset_status)
                elif preset_ref:
                    preset_statuses.append("linked")
                else:
                    preset_statuses.append("snapshot")
        if section_has_role:
            linked_section_count += 1
    if not link_count:
        return f"subassembly role={role}: not linked; legacy point-role fallback"
    refs = _unique_refs(subassembly_refs)
    ref_note = f"; refs={','.join(_display_source_ref(ref) for ref in refs[:3])}" if refs else ""
    if len(refs) > 3:
        ref_note += f"; +{len(refs) - 3} more"
    preset_ref_rows = _unique_refs(preset_refs)
    preset_ref_note = f"; preset_refs={','.join(_display_source_ref(ref) for ref in preset_ref_rows[:3])}" if preset_ref_rows else ""
    if len(preset_ref_rows) > 3:
        preset_ref_note += f"; +{len(preset_ref_rows) - 3} more presets"
    preset_status_note = ""
    preset_status_counts = _text_count_map(preset_statuses)
    if preset_status_counts:
        preset_status_note = f"; preset_status={_format_count_summary(preset_status_counts)}"
    coverage = (
        f"subassembly role={role}: linked sections={linked_section_count}/{len(sections)}, "
        f"links={link_count}{ref_note}{preset_ref_note}{preset_status_note}"
    )
    if linked_section_count < len(sections):
        coverage += "; fallback used for unlinked sections"
    return coverage


def _with_subassembly_surface_role_review_note(
    row: dict[str, object],
    note_for_surface_role: Callable[[str], str],
) -> dict[str, object]:
    surface_role = _review_surface_role_for_result_role(str(row.get("role", "") or ""))
    if not surface_role:
        return row
    note = note_for_surface_role(surface_role)
    if not note:
        return row
    output = dict(row)
    existing = str(output.get("notes", "") or "").strip()
    output["notes"] = f"{existing} | {note}" if existing else note
    return output


def _with_applied_section_review_summary(row: dict[str, object], summary: dict[str, object]) -> dict[str, object]:
    output = dict(row or {})
    output["applied_section_summary"] = str(summary.get("summary", "") or "")
    output["applied_section_diagnostics"] = str(summary.get("diagnostics", "") or "")
    output["applied_section_status"] = str(summary.get("status", "") or "")
    return output


def _review_surface_role_for_result_role(role: str) -> str:
    if role == "design":
        return "design_surface"
    if role == "subgrade":
        return "subgrade_surface"
    if role == "daylight":
        return "slope_face_surface"
    if role == "drainage":
        return "drainage_surface"
    return ""


def _text_count_map(values: list[str] | tuple[str, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in list(values or []):
        text = str(value or "").strip()
        if not text:
            continue
        counts[text] = counts.get(text, 0) + 1
    return counts


def _first_active_structure_ref(section) -> str:
    for value in _section_structure_refs(section):
        if value:
            return value
    return ""


def _section_structure_refs(section) -> list[str]:
    refs: list[str] = []
    for value in list(getattr(section, "active_structure_ids", []) or []):
        text = str(value or "").strip()
        if text:
            refs.append(text)
    subassembly_rows = list(getattr(section, "subassembly_rows", []) or [])
    for subassembly in subassembly_rows:
        for value in list(getattr(subassembly, "structure_ids", []) or []):
            text = str(value or "").strip()
            if text:
                refs.append(text)
        text = str(getattr(subassembly, "structure_ref", "") or "").strip()
        if text:
            refs.append(text)
    return _unique_text_values(refs)


def _unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def intersection_upper_slope_face_panel_review_row(obj) -> dict[str, object] | None:
    if obj is None:
        return None
    candidate_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelCandidateCount", 0) or 0)
    accepted_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelAcceptedCount", 0) or 0)
    generated_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0)
    triangle_count = int(getattr(obj, "IntersectionUpperSlopeFacePanelTriangleCount", 0) or 0)
    suppressed_count = int(getattr(obj, "IntersectionSlopeFaceSuppressedUpperCellCount", 0) or 0)
    if not any((candidate_count, accepted_count, generated_count, triangle_count, suppressed_count)):
        return None
    status = "ready" if generated_count > 0 and triangle_count == generated_count * 2 else "warning" if candidate_count else "missing"
    refs = list(getattr(obj, "IntersectionUpperSlopeFacePanelRefs", []) or [])
    boundary_refs = list(getattr(obj, "IntersectionUpperSlopeFacePanelBoundaryRefs", []) or [])
    coverage_status = str(getattr(obj, "IntersectionUpperSlopeFacePanelCoverageStatus", "") or "")
    diagnostic = str(getattr(obj, "IntersectionUpperSlopeFacePanelDiagnostic", "") or "")
    notes = _join_review_notes(
        _intersection_slope_face_upper_panel_review_note(obj),
        f"refs={len(refs)}",
        f"boundary_refs={len(boundary_refs)}",
        diagnostic,
    )
    if coverage_status and coverage_status != "ready":
        status = "warning"
    return {
        "role": "intersection_upper_slope_face_panel",
        "result": "Intersection Upper Slope Face Panel",
        "object_name": str(getattr(obj, "Name", "") or "V1CorridorIntersectionSlopeFaceSurfacePreview"),
        "object_label": str(getattr(obj, "Label", "") or "Intersection Slope Face Surface"),
        "status": status,
        "vertex_count": "",
        "triangle_or_point_count": triangle_count,
        "output_path": "intersection_upper_slope_face_panel",
        "notes": notes,
    }


def intersection_surface_replacement_readiness_row(obj) -> dict[str, object] | None:
    if obj is None:
        return None
    gate_status = str(getattr(obj, "IntersectionSurfaceReplacementGateStatus", "") or "")
    if not gate_status:
        return None
    recommendation = str(getattr(obj, "IntersectionSurfaceReplacementGateRecommendation", "") or "")
    patch_triangles = int(getattr(obj, "IntersectionSurfaceComparisonPatchTriangleCount", 0) or 0)
    zone_triangles = int(getattr(obj, "IntersectionSurfaceComparisonZoneTriangleCount", 0) or 0)
    delta = int(getattr(obj, "IntersectionSurfaceComparisonTriangleDelta", 0) or 0)
    ratio = float(getattr(obj, "IntersectionSurfaceComparisonZoneToPatchTriangleRatio", 0.0) or 0.0)
    diagnostics = [str(value or "") for value in list(getattr(obj, "IntersectionSurfaceReplacementDiagnostics", []) or []) if str(value or "")]
    acceptance_diagnostics = [str(value or "") for value in list(getattr(obj, "IntersectionSurfaceReplacementAcceptanceDiagnostics", []) or []) if str(value or "")]
    if gate_status == "ready_to_replace":
        status = "ready"
        readiness = "ready_to_replace"
    elif gate_status == "blocked":
        status = "warning"
        readiness = "blocked"
    else:
        status = "warning"
        readiness = "review_only"
    blocked_note = "; blocked_reason=accepted_zone_surface_not_ready" if readiness == "blocked" else ""
    notes = (
        f"Replacement readiness={readiness}; gate={gate_status}; "
        f"patch_triangles={patch_triangles}; zone_triangles={zone_triangles}; "
        f"delta={delta}; ratio={ratio:.3f}; "
        f"recommendation={recommendation or 'review_required'}; diagnostics={len(diagnostics)}; "
        f"acceptance_evidence={len(acceptance_diagnostics)}"
        f"{blocked_note}"
    )
    return {
        "role": "intersection_replacement_readiness",
        "result": "Intersection Replacement Readiness",
        "object_name": str(getattr(obj, "Name", "") or "V1CorridorIntersectionSurfacePreview"),
        "object_label": "Intersection Replacement Readiness",
        "status": status,
        "vertex_count": "",
        "triangle_or_point_count": zone_triangles,
        "output_path": "review_gate",
        "notes": notes,
    }


def intersection_tie_in_continuity_row(
    obj,
    *,
    station_span_for: Callable[[str], str],
) -> dict[str, object] | None:
    if obj is None:
        return None
    tie_in_count = int(getattr(obj, "PatchPavementTieInEdgeCount", 0) or 0) + int(getattr(obj, "PatchStemTieInEdgeCount", 0) or 0)
    curb_return_count = int(getattr(obj, "PatchCurbReturnEdgeCount", 0) or 0)
    overlap_count = int(getattr(obj, "PatchOverlapCutEdgeCount", 0) or 0)
    boundary_diagnostic_count = int(getattr(obj, "IntersectionPatchBoundaryDiagnosticCount", 0) or 0)
    boundary_diagnostics = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionPatchBoundaryDiagnostics", []) or [])
        if str(value or "")
    ]
    boundary_error_count = len([
        value for value in boundary_diagnostics
        if not str(value).strip().lower().startswith(("warning:", "info:"))
    ])
    if boundary_diagnostic_count and not boundary_diagnostics:
        boundary_error_count = boundary_diagnostic_count
    shared_status = str(getattr(obj, "SharedBreaklineAuditStatus", "") or "")
    geometry_mismatch = int(getattr(obj, "SharedBreaklineGeometryMismatchCount", 0) or 0)
    mesh_mismatch = int(getattr(obj, "SharedBreaklineMeshMismatchCount", 0) or 0)
    missing_consumer = int(getattr(obj, "SharedBreaklineMissingConsumerCount", 0) or 0)
    reversed_count = int(getattr(obj, "SharedBreaklineReversedEdgeCount", 0) or 0)
    if not any([tie_in_count, curb_return_count, overlap_count, boundary_diagnostic_count, shared_status]):
        return None
    if boundary_error_count > 0 or geometry_mismatch > 0 or missing_consumer > 0:
        status = "error"
    elif boundary_diagnostic_count > 0 or mesh_mismatch > 0 or reversed_count > 0 or shared_status in {"warning", "error"}:
        status = "warning"
    else:
        status = "ready"
    station_span = station_span_for(str(getattr(obj, "IntersectionId", "") or ""))
    notes = (
        f"tie-in edges={tie_in_count}; curb_return_edges={curb_return_count}; overlap_cut_edges={overlap_count}; "
        f"boundary_diagnostics={boundary_diagnostic_count}; shared_breakline_audit={shared_status or 'not_available'}; "
        f"geometry_mismatch={geometry_mismatch}; mesh_mismatch={mesh_mismatch}; "
        f"missing_consumer={missing_consumer}; reversed={reversed_count}; "
        f"station_span={station_span or 'unavailable'}"
    )
    qa_summary = str(getattr(obj, "IntersectionManualQASummary", "") or "")
    if qa_summary:
        notes = f"{notes}; {qa_summary}"
    return {
        "role": "intersection_tie_in_continuity",
        "result": "Intersection Tie-In Continuity",
        "object_name": str(getattr(obj, "Name", "") or "V1CorridorIntersectionSurfacePreview"),
        "object_label": "Intersection Tie-In Continuity",
        "status": status,
        "vertex_count": "",
        "triangle_or_point_count": tie_in_count + curb_return_count + overlap_count,
        "output_path": "review_gate",
        "notes": notes,
    }


def intersection_grading_ownership_row(
    obj,
    *,
    station_span_for: Callable[[str], str],
    profile_refs_for: Callable[[str], list[str]],
) -> dict[str, object] | None:
    if obj is None:
        return None
    grading_policy_ref = str(getattr(obj, "IntersectionGradingPolicyRef", "") or "")
    grading_mode = str(getattr(obj, "IntersectionGradingMode", "") or "")
    target_crossfall = str(getattr(obj, "IntersectionTargetCrossfallPercent", "") or "")
    superelevation_sources = int(getattr(obj, "IntersectionSuperelevationSourceCount", 0) or 0)
    transition_count = int(getattr(obj, "IntersectionSuperelevationTransitionCount", 0) or 0)
    superelevation_context = str(getattr(obj, "IntersectionSuperelevationContext", "") or "")
    consumed_grading_ref = str(getattr(obj, "ConsumedIntersectionGradingContextResultId", "") or "")
    if not any([grading_policy_ref, grading_mode, target_crossfall, superelevation_sources, transition_count, consumed_grading_ref]):
        return None
    left_min = float(getattr(obj, "IntersectionSuperelevationLeftMin", 0.0) or 0.0)
    left_max = float(getattr(obj, "IntersectionSuperelevationLeftMax", 0.0) or 0.0)
    right_min = float(getattr(obj, "IntersectionSuperelevationRightMin", 0.0) or 0.0)
    right_max = float(getattr(obj, "IntersectionSuperelevationRightMax", 0.0) or 0.0)
    left_delta = abs(left_max - left_min)
    right_delta = abs(right_max - right_min)
    max_delta = max(left_delta, right_delta)
    if max_delta > 0.5 or transition_count > 0:
        status = "warning"
    else:
        status = "ready"
    station_span = station_span_for(str(getattr(obj, "IntersectionId", "") or ""))
    controlling_source = "intersection_policy" if grading_policy_ref or grading_mode else "normal_superelevation"
    profile_refs = profile_refs_for(str(getattr(obj, "IntersectionId", "") or ""))
    notes = (
        f"owner={controlling_source}; grading_policy={_display_source_id(grading_policy_ref, 'grading:') or '-'}; "
        f"mode={grading_mode or '-'}; target_crossfall={target_crossfall or '-'}%; "
        f"superelevation_sources={superelevation_sources}; transitions={transition_count}; "
        f"left_crossfall={left_min:.3f}%..{left_max:.3f}%; right_crossfall={right_min:.3f}%..{right_max:.3f}%; "
        f"max_crossfall_delta={max_delta:.3f}%; grading_context={consumed_grading_ref or '-'}; "
        f"profile_refs={','.join(profile_refs) if profile_refs else '-'}; station_span={station_span or 'unavailable'}"
    )
    if superelevation_context:
        notes = f"{notes}; context={superelevation_context}"
    return {
        "role": "intersection_grading_ownership",
        "result": "Intersection Grading Ownership",
        "object_name": str(getattr(obj, "Name", "") or "V1CorridorIntersectionSurfacePreview"),
        "object_label": "Intersection Grading Ownership",
        "status": status,
        "vertex_count": "",
        "triangle_or_point_count": transition_count,
        "output_path": "review_gate",
        "notes": notes,
    }


def intersection_drainage_handoff_gate_row(obj, *, policy_rows, drainage_model) -> dict[str, object] | None:
    intersection_id = str(getattr(obj, "IntersectionId", "") or "").strip()
    hint_ref = str(getattr(obj, "ConsumedIntersectionDrainageHintResultId", "") or "").strip()
    low_point_count = int(getattr(obj, "IntersectionTINLowPointCandidateCount", 0) or 0)
    flow_hint_count = int(getattr(obj, "IntersectionBoundaryToLowFlowHintCount", 0) or 0)
    flow_hint_summary = str(getattr(obj, "IntersectionBoundaryToLowFlowHintSummary", "") or "").strip()
    element_ids = {
        str(getattr(row, "drainage_element_id", "") or "").strip()
        for row in list(getattr(drainage_model, "element_rows", []) or [])
        if str(getattr(row, "drainage_element_id", "") or "").strip()
    } if drainage_model is not None else set()
    route_ids = {
        str(getattr(row, "flow_route_id", "") or "").strip()
        for row in list(getattr(drainage_model, "flow_route_rows", []) or [])
        if str(getattr(row, "flow_route_id", "") or "").strip()
    } if drainage_model is not None else set()
    accepted_policies = [
        row for row in policy_rows
        if str(getattr(row, "intent_status", "") or "").strip().lower() == "accepted"
        or str(getattr(row, "approval_status", "") or "").strip().lower() in {"accepted", "locked"}
    ]
    policy_element_refs = _unique_text_values([
        str(value or "").strip()
        for row in policy_rows
        for value in list(getattr(row, "drainage_element_refs", []) or [])
        if str(value or "").strip()
    ])
    policy_route_refs = _unique_text_values([
        str(value or "").strip()
        for row in policy_rows
        for value in list(getattr(row, "flow_route_refs", []) or [])
        if str(value or "").strip()
    ])
    matched_elements = [ref for ref in policy_element_refs if ref in element_ids]
    matched_routes = [ref for ref in policy_route_refs if ref in route_ids]
    missing_elements = [ref for ref in policy_element_refs if ref and ref not in element_ids]
    missing_routes = [ref for ref in policy_route_refs if ref and ref not in route_ids]
    has_hint = bool(hint_ref or low_point_count or flow_hint_count or flow_hint_summary)
    has_policy = bool(policy_rows)
    if not any([has_hint, has_policy, drainage_model is not None]):
        return None
    if missing_elements or missing_routes:
        status = "error"
        handoff = "accepted_drainage_refs_missing"
        action = "Create or relink the referenced DrainageModel elements and flow routes."
    elif accepted_policies and (matched_elements or matched_routes):
        status = "ready"
        handoff = "accepted_drainage"
        action = "No action needed."
    elif has_hint:
        status = "warning"
        handoff = "hint_only"
        action = "Convert low-point hints into accepted DrainageModel elements and flow routes."
    else:
        status = "missing"
        handoff = "drainage_source_missing"
        action = "Add an Intersection drainage policy and DrainageModel handoff rows."
    notes = (
        f"handoff={handoff}; intersection={intersection_id or '-'}; "
        f"hint_ref={hint_ref or '-'}; low_points={low_point_count}; flow_hints={flow_hint_count}; "
        f"policies={len(policy_rows)}; accepted_policies={len(accepted_policies)}; "
        f"elements={len(matched_elements)}/{len(policy_element_refs)}; routes={len(matched_routes)}/{len(policy_route_refs)}; "
        f"missing_elements={','.join(missing_elements) if missing_elements else '-'}; "
        f"missing_routes={','.join(missing_routes) if missing_routes else '-'}; "
        f"recommended_action={action}"
    )
    if flow_hint_summary:
        notes = f"{notes}; hint_summary={flow_hint_summary}"
    return {
        "role": "intersection_drainage_handoff_gate",
        "result": "Intersection Drainage Handoff Gate",
        "object_name": str(getattr(obj, "Name", "") or "V1CorridorIntersectionSurfacePreview"),
        "object_label": "Intersection Drainage Handoff Gate",
        "status": status,
        "vertex_count": "",
        "triangle_or_point_count": max(low_point_count, len(matched_elements) + len(matched_routes)),
        "output_path": "review_gate",
        "notes": notes,
    }
