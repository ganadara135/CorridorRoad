"""Presentation notes for the Intersections guided review step."""

from __future__ import annotations

from .build_review_presentation import _surface_patch_review_status_note
from .review_text import display_source_id as _display_source_id


def intersection_patch_boundary_review_notes(obj) -> dict[str, object]:
    if obj is None:
        return {"diagnostic_count": 0, "notes": ""}
    diagnostic_count = int(getattr(obj, "IntersectionPatchBoundaryDiagnosticCount", 0) or 0)
    hole_count = int(getattr(obj, "IntersectionPatchBoundaryHoleRingCount", 0) or 0)
    island_count = int(getattr(obj, "IntersectionPatchBoundaryIslandRingCount", 0) or 0)
    diagnostics = [str(value or "") for value in list(getattr(obj, "IntersectionPatchBoundaryDiagnostics", []) or []) if str(value or "")]
    parts: list[str] = []
    if hole_count or island_count:
        parts.append(f"patch boundary rings: holes={hole_count}, islands={island_count}")
    if diagnostic_count:
        shown = "; ".join(diagnostics[:2]) if diagnostics else f"{diagnostic_count} diagnostic(s)"
        suffix = f"; +{diagnostic_count - 2} more" if diagnostic_count > 2 else ""
        parts.append(f"patch boundary diagnostics: {shown}{suffix}")
    return {"diagnostic_count": diagnostic_count, "notes": "; ".join(parts)}


def intersection_grading_review_notes(obj) -> str:
    if obj is None:
        return ""
    policy_ref = _display_source_id(str(getattr(obj, "IntersectionGradingPolicyRef", "") or ""), "grading:")
    mode = str(getattr(obj, "IntersectionGradingMode", "") or "")
    z_delta = float(getattr(obj, "IntersectionGradingZDeltaMax", 0.0) or 0.0)
    superelevation_sources = int(getattr(obj, "IntersectionSuperelevationSourceCount", 0) or 0)
    superelevation_transitions = int(getattr(obj, "IntersectionSuperelevationTransitionCount", 0) or 0)
    parts: list[str] = []
    if policy_ref or mode:
        label = policy_ref or "default"
        parts.append(f"grading policy={label}, mode={mode or 'use_normal_superelevation'}")
    if z_delta:
        parts.append(f"max z adjustment={z_delta:.3f}m")
    if superelevation_sources or superelevation_transitions:
        parts.append(f"superelevation sources={superelevation_sources}, transitions={superelevation_transitions}")
    return "; ".join(parts)


def intersection_surface_quality_review_notes(obj) -> dict[str, object]:
    if obj is None:
        return {"diagnostic_count": 0, "notes": ""}
    surface_patch_summary = str(getattr(obj, "IntersectionSurfacePatchSummary", "") or "")
    surface_zone_output_summary = str(getattr(obj, "IntersectionSurfaceZoneOutputSummary", "") or "")
    surface_zone_output_contract_status = str(getattr(obj, "IntersectionSurfaceZoneOutputContractStatus", "") or "")
    surface_zone_output_handoff = str(getattr(obj, "IntersectionSurfaceZoneOutputDigitalTwinHandoff", "") or "")
    surface_replacement_summary = str(getattr(obj, "IntersectionSurfaceReplacementSummary", "") or "")
    surface_replacement_gate = str(getattr(obj, "IntersectionSurfaceReplacementGateStatus", "") or "")
    surface_patch_contract_status = str(getattr(obj, "IntersectionSurfacePatchOutputContractStatus", "") or "")
    surface_patch_handoff = str(getattr(obj, "IntersectionSurfacePatchDigitalTwinHandoff", "") or "")
    surface_patch_replacement_path = str(getattr(obj, "IntersectionSurfacePatchReplacementPath", "") or "")
    slope_face_surface_action = str(getattr(obj, "IntersectionSlopeFaceSurfaceRecommendedAction", "") or "")
    surface_patch_row_statuses = _surface_patch_review_status_note(obj)
    surface_patch_row_diagnostics = [
        str(value or "")
        for value in list(getattr(obj, "IntersectionSurfacePatchRowDiagnostics", []) or [])
        if str(value or "")
    ]
    triangulation_mode = str(getattr(obj, "PatchTriangulationMode", "") or "")
    boundary_strategy = str(getattr(obj, "PatchSurfaceBoundaryStrategy", "") or "")
    bbox_ratio = float(getattr(obj, "PatchBoundaryBBoxAspectRatio", 0.0) or 0.0)
    min_quality = float(getattr(obj, "PatchTriangleMinQuality", 0.0) or 0.0)
    skinny_count = int(getattr(obj, "PatchTriangleSkinnyCount", 0) or 0)
    long_edge_count = int(getattr(obj, "PatchBoundaryLongEdgeCount", 0) or 0)
    parts: list[str] = []
    diagnostics = len(surface_patch_row_diagnostics)
    if surface_patch_summary:
        parts.append(f"surface_patch={surface_patch_summary}")
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
    if surface_patch_replacement_path:
        parts.append(f"surface_patch_replacement={surface_patch_replacement_path}")
    if slope_face_surface_action:
        parts.append(f"intersection_slope_face_action={slope_face_surface_action}")
    if surface_patch_row_statuses:
        parts.append(f"surface_patch_rows={surface_patch_row_statuses}")
    if surface_patch_row_diagnostics:
        parts.append(f"surface_patch_row_diagnostics={len(surface_patch_row_diagnostics)}")
    if triangulation_mode:
        if triangulation_mode == "fan_fallback":
            diagnostics += 1
            parts.append(f"warning:patch triangulation={triangulation_mode}; ear clipping failed and fan fallback was used")
        else:
            parts.append(f"patch triangulation={triangulation_mode}")
    if boundary_strategy:
        parts.append(f"surface boundary={boundary_strategy}")
    if bbox_ratio:
        if bbox_ratio >= 8.0:
            diagnostics += 1
            parts.append(f"warning:patch bbox ratio={bbox_ratio:.3f}; boundary is elongated")
        else:
            parts.append(f"patch bbox ratio={bbox_ratio:.3f}")
    if min_quality:
        if min_quality < 0.08:
            diagnostics += 1
            parts.append(f"warning:patch min triangle quality={min_quality:.3f}; skinny triangle risk")
        else:
            parts.append(f"patch min triangle quality={min_quality:.3f}")
    if skinny_count:
        diagnostics += skinny_count
        parts.append(f"warning:skinny triangles={skinny_count}; improve intersection boundary/tie-in shape")
    if long_edge_count:
        parts.append(f"warning:long boundary edges={long_edge_count}; patch boundary needs more local control points")
    return {"diagnostic_count": diagnostics, "notes": "; ".join(parts)}


def intersection_exclusion_review_notes(preview_by_role) -> str:
    items: list[str] = []
    for role, label in (("design", "Design"), ("daylight", "Slope")):
        obj = preview_by_role.get(role)
        if obj is None:
            continue
        status = str(getattr(obj, "IntersectionExclusionClipStatus", "") or "")
        if not status:
            continue
        clipped = int(getattr(obj, "IntersectionExclusionClippedTriangleCount", 0) or 0)
        kept = int(getattr(obj, "IntersectionExclusionKeptTriangleCount", 0) or 0)
        exact_cut_candidates = int(getattr(obj, "IntersectionExclusionExactCutCandidateCount", 0) or 0)
        boundary_strategy = str(getattr(obj, "IntersectionExclusionBoundaryStrategy", "") or "")
        aligned = int(getattr(obj, "IntersectionExclusionPracticalBoundaryAligned", 0) or 0)
        footprint_status = str(getattr(obj, "IntersectionExclusionPracticalFootprintStatus", "") or "")
        footprint_diagnostics = [
            str(value or "")
            for value in list(getattr(obj, "IntersectionExclusionPracticalFootprintDiagnostics", []) or [])
            if str(value or "")
        ]
        action = _intersection_exclusion_practical_footprint_recommended_action(
            footprint_status,
            "; ".join(footprint_diagnostics),
        )
        suffix_parts = []
        if exact_cut_candidates:
            suffix_parts.append(f"exact-cut candidates={exact_cut_candidates}")
        if boundary_strategy:
            suffix_parts.append(f"boundary={boundary_strategy}")
        if aligned:
            suffix_parts.append("aligned=practical")
        if footprint_status and footprint_status not in {"ready", status}:
            suffix_parts.append(f"footprint={footprint_status}")
        if footprint_diagnostics:
            suffix_parts.append(footprint_diagnostics[0])
        if action:
            suffix_parts.append(f"recommended_action={action}")
        suffix = f", {', '.join(suffix_parts)}" if suffix_parts else ""
        items.append(f"{label} exclusion {status}: clipped={clipped}, kept={kept}{suffix}")
    return "; ".join(items)


def _intersection_exclusion_practical_footprint_recommended_action(status: str, diagnostics: str = "") -> str:
    status_text = str(status or "").strip().lower()
    diagnostic_text = str(diagnostics or "").strip().lower()
    if status_text in {"", "ready"}:
        return ""
    if "primary_strip_invalid" in diagnostic_text or "strip_invalid" in diagnostic_text:
        return "Review Intersection tie-in source geometry, then rebuild Applied Sections and Build Parametric"
    if "union_invalid" in diagnostic_text or "zero_area" in diagnostic_text:
        return "Review skew angle and tie-in extents, then rebuild Build Parametric"
    if status_text == "degraded":
        return "Review recovered footprint outline before accepting adjacent surface clipping"
    if status_text == "missing":
        return "Review Intersection source and rebuild before trusting adjacent surface clipping"
    return "Review practical exclusion footprint diagnostics"
