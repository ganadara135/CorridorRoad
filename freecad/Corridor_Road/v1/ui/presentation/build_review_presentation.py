"""Presentation rows for the Build Corridor Results tab review."""

from __future__ import annotations

from typing import Callable

from .review_text import join_review_notes as _join_review_notes
from .review_text import unique_text_values as _unique_text_values
from .review_text import unique_refs as _unique_refs
from .review_text import display_source_ref as _display_source_ref
from .review_text import format_count_summary as _format_count_summary
from .shared_breakline_audit_presentation import _normalize_corridor_build_review_status


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
    radius = float(getattr(obj, "RoundaboutOwnershipRadius", 0.0) or 0.0)
    action = str(getattr(obj, "RoundaboutOwnershipRecommendedAction", "") or "")
    return _join_review_notes(
        f"roundabout_ownership={status}",
        f"intrusion_triangles={count}/{tested}",
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
    role_text = str(role or "")
    if role_text in {"intersection", "intersection_slope"}:
        # the intersection kernel builds both surfaces from the stored spec and the Applied
        # Sections; a surface without its status was built before the kernel (plan phase R7c)
        return "contract_consumed" if str(getattr(obj, "IntersectionKernelStatus", "") or "") else "legacy_output"
    source_mode = str(getattr(obj, "ConsumedCenterlineSourceMode", "") or getattr(obj, "PreviewSource", "") or "")
    centerline_fallback = bool(int(getattr(obj, "CenterlineConsumerFallbackActive", 0) or 0))
    supplemental_fallback = bool(int(getattr(obj, "SupplementalCompatibilityFallbackActive", 0) or 0))
    result_contract_fallback = bool(int(getattr(obj, "ResultContractCompatibilityFallbackActive", 0) or 0))
    if centerline_fallback or supplemental_fallback or result_contract_fallback:
        return "inferred_fallback"
    if source_mode and source_mode != "centerline3d_source_geometry":
        return "inferred_fallback"
    return "contract_consumed"


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
