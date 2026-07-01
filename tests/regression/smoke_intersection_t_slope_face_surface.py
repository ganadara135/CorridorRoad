# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
T intersection dedicated Slope Face Surface smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_intersection_t_slope_face_surface.py', 'r', encoding='utf-8').read())"
"""

import FreeCAD as App
from dataclasses import replace

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    build_document_corridor_model,
    build_document_corridor_surface_model,
    corridor_build_preview_visibility_note,
    corridor_build_review_rows,
    corridor_shared_breakline_audit_rows,
    corridor_intersection_contract_review_rows,
    create_corridor_design_surface_preview,
    create_corridor_daylight_surface_preview,
    create_corridor_intersection_surface_preview,
    focus_corridor_intersection_contract_review_row,
    _parse_intersection_exclusion_near_boundary_kept_triangle_row,
    shared_breakline_audit_display_rows,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import create_intersection_preset_sources
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
    update_v1_intersection_model_object,
)


def _assert(condition, message):
    if not condition:
        raise Exception(message)


def _shape_bbox_xy(obj):
    bbox = None
    for attr_name in ("Shape", "Mesh"):
        geometry = getattr(obj, attr_name, None)
        candidate = getattr(geometry, "BoundBox", None)
        if candidate is not None:
            bbox = candidate
            break
    if bbox is None:
        return None
    return {
        "xmin": float(getattr(bbox, "XMin", 0.0) or 0.0),
        "ymin": float(getattr(bbox, "YMin", 0.0) or 0.0),
        "xmax": float(getattr(bbox, "XMax", 0.0) or 0.0),
        "ymax": float(getattr(bbox, "YMax", 0.0) or 0.0),
        "xlen": float(getattr(bbox, "XLength", 0.0) or 0.0),
        "ylen": float(getattr(bbox, "YLength", 0.0) or 0.0),
    }


def _bbox_area_xy(bbox):
    if not bbox:
        return 0.0
    return max(0.0, float(bbox["xlen"] or 0.0)) * max(0.0, float(bbox["ylen"] or 0.0))


def _bbox_overlap_area_xy(first, second):
    if not first or not second:
        return 0.0
    x_overlap = max(0.0, min(first["xmax"], second["xmax"]) - max(first["xmin"], second["xmin"]))
    y_overlap = max(0.0, min(first["ymax"], second["ymax"]) - max(first["ymin"], second["ymin"]))
    return x_overlap * y_overlap


def _shape_area(obj):
    shape = getattr(obj, "Shape", None)
    try:
        return float(getattr(shape, "Area", 0.0) or 0.0)
    except Exception:
        return 0.0


def _graph_edge_rows(source_obj):
    rows = []
    for raw in list(getattr(source_obj, "IntersectionSharedBoundaryGraphAuditRows", []) or []):
        parts = str(raw or "").split("|")
        if len(parts) >= 7 and parts[0] == "edge":
            rows.append(
                {
                    "edge_id": parts[1],
                    "role": parts[2],
                    "from_node_ref": parts[3],
                    "to_node_ref": parts[4],
                    "consumers": {value.strip() for value in parts[5].split(",") if value.strip()},
                    "diagnostics": parts[6],
                }
            )
    return rows


def _graph_cell_rows(source_obj):
    rows = []
    for raw in list(getattr(source_obj, "IntersectionSharedBoundaryGraphAuditRows", []) or []):
        parts = str(raw or "").split("|")
        if len(parts) >= 7 and parts[0] == "cell":
            rows.append(
                {
                    "cell_id": parts[1],
                    "role": parts[2],
                    "closed": parts[3] == "1",
                    "owner": parts[4],
                    "edge_refs": [value.strip() for value in parts[5].split(",") if value.strip()],
                    "diagnostics": parts[6],
                }
            )
    return rows


def _parent_group_labels(doc, obj):
    labels = []
    for owner in list(getattr(doc, "Objects", []) or []):
        try:
            if obj in list(getattr(owner, "Group", []) or []):
                labels.append(str(getattr(owner, "Label", "") or getattr(owner, "Name", "") or ""))
        except Exception:
            continue
    return labels


def _boundary_loop_handoff_rows(doc):
    return [
        row
        for row in shared_breakline_audit_display_rows(corridor_shared_breakline_audit_rows(doc), include_internal=True)
        if row.get("row_kind") == "boundary_loop_handoff"
    ]


def _note_int(notes, key):
    prefix = f"{key}="
    for part in str(notes or "").replace(";", " ").split():
        if part.startswith(prefix):
            try:
                return int(part[len(prefix):])
            except Exception:
                return 0
    return 0


def _accept_t_intersection_preset_prerequisites(doc):
    """Mark preset source rows as reviewed for the smoke's complete-prerequisite scenario."""

    obj = find_v1_intersection_model(doc)
    model = to_intersection_model(obj)
    _assert(obj is not None and model is not None, "T preset did not create an IntersectionModel.")
    intersection_rows = []
    for intersection in list(model.intersection_rows or []):
        accepted_legs = [
            replace(
                leg,
                approval_status="accepted",
                span_source="explicit",
                approach_station_start=float(leg.approach_station_start or 96.0),
                approach_station_end=float(leg.approach_station_end or 120.0),
                profile_ref=str(leg.profile_ref or f"profile:{leg.alignment_ref or leg.leg_id}"),
                centerline3d_ref=str(leg.centerline3d_ref or f"centerline3d:{leg.alignment_ref or leg.leg_id}"),
                diagnostic_rows=[],
            )
            for leg in list(intersection.leg_rows or [])
        ]
        intersection_rows.append(replace(intersection, leg_rows=accepted_legs))
    model.intersection_rows = intersection_rows
    model.anchor_rows = [
        replace(row, approval_status="accepted", tolerance=float(row.tolerance or 0.01), diagnostic_rows=[])
        for row in list(model.anchor_rows or [])
    ]
    model.control_area_rows = [
        replace(
            row,
            approval_status="accepted",
            intent_status="intersection_owned",
            station_ranges=list(row.station_ranges or [(96.0, 120.0)]),
            influence_ranges=list(row.influence_ranges or [(96.0, 120.0)]),
            diagnostic_rows=[],
        )
        for row in list(model.control_area_rows or [])
    ]
    model.corner_rows = [
        replace(row, approval_status="accepted", diagnostic_rows=[])
        for row in list(model.corner_rows or [])
    ]
    model.edge_policy_rows = [
        replace(
            row,
            approval_status="accepted",
            source_method="subassembly_derived",
            diagnostic_rows=[],
        )
        for row in list(model.edge_policy_rows or [])
    ]
    model.lane_connection_rows = [
        replace(row, approval_status="accepted", diagnostic_rows=[])
        for row in list(model.lane_connection_rows or [])
    ]
    model.grading_policy_rows = [
        replace(row, approval_status="accepted", diagnostic_rows=[])
        for row in list(model.grading_policy_rows or [])
    ]
    model.drainage_policy_rows = [
        replace(row, approval_status="accepted", intent_status="accepted_drainage", diagnostic_rows=[])
        for row in list(model.drainage_policy_rows or [])
    ]
    update_v1_intersection_model_object(obj, model, label=str(getattr(obj, "Label", "") or "Intersections"))
    return model


def run():
    doc = App.newDocument("CRV1IntersectionTSlopeFaceSurfaceSmoke")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        _accept_t_intersection_preset_prerequisites(doc)
        project = find_project(doc)
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        corridor_model = build_document_corridor_model(doc, project=project)
        surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)

        intersection_preview = create_corridor_intersection_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        design_preview = create_corridor_design_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        daylight_preview = create_corridor_daylight_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_face_preview = doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
        review_rows = corridor_build_review_rows(doc)
        slope_rows = [row for row in review_rows if row["role"] == "intersection_slope"]

        _assert(len(applied.sections) > 0, "T preset smoke should build Applied Sections.")
        _assert(intersection_preview is not None, "Intersection Surface preview was not created.")
        _assert(design_preview is not None, "Design Surface preview was not created.")
        _assert(daylight_preview is not None, "Ordinary Slope Face Surface preview was not created.")
        _assert(slope_face_preview is not None, "Dedicated Intersection Slope Face Surface preview was not created.")
        _assert(
            int(getattr(intersection_preview, "SharedBreaklineBoundaryLoopRefCount", 0) or 0) > 0,
            "Intersection Surface should consume boundary-loop shared breakline refs.",
        )
        _assert(
            int(getattr(intersection_preview, "SharedBreaklineConstraintEdgeCount", 0) or 0) > 0,
            "Intersection Surface should expose shared breakline constraint edges for boundary-loop handoff.",
        )
        _assert(
            int(getattr(intersection_preview, "SharedBreaklineBoundaryLoopConstraintEdgeCount", 0) or 0) > 0,
            "Intersection Surface should preserve boundary-loop constraint edges.",
        )
        _assert(
            int(getattr(design_preview, "SharedBreaklineBoundaryLoopRefCount", 0) or 0) > 0,
            "Design Surface should consume boundary-loop shared breakline refs.",
        )
        _assert(
            int(getattr(design_preview, "SharedBreaklineConstraintEdgeCount", 0) or 0) > 0,
            "Design Surface should expose shared breakline constraint edges for boundary-loop handoff.",
        )
        _assert(
            int(getattr(design_preview, "SharedBreaklineBoundaryLoopConstraintEdgeCount", 0) or 0) > 0,
            "Design Surface should preserve boundary-loop constraint edges.",
        )
        _assert(
            str(getattr(design_preview, "IntersectionExclusionBoundarySource", "") or "") == "intersection_boundary_loop",
            "Design Surface should use the authoritative boundary loop as the intersection exclusion source.",
        )
        _assert(
            int(getattr(design_preview, "IntersectionExclusionBoundaryLoopPointCount", 0) or 0) >= 3,
            "Design Surface should expose the boundary-loop exclusion point count.",
        )
        _assert(
            str(getattr(design_preview, "IntersectionBoundaryLoopOwnershipStatus", "") or "") == "ready",
            f"Design Surface should report ready boundary-loop ownership: "
            f"{getattr(design_preview, 'IntersectionBoundaryLoopOwnershipNotes', '')}",
        )
        _assert(
            int(getattr(design_preview, "IntersectionExclusionTestedTriangleCount", 0) or 0)
            == int(getattr(design_preview, "IntersectionExclusionClippedTriangleCount", 0) or 0)
            + int(getattr(design_preview, "IntersectionExclusionKeptTriangleCount", 0) or 0),
            "Design Surface should expose consistent intersection exclusion tested/clipped/kept counts.",
        )
        _assert(
            0.0 <= float(getattr(design_preview, "IntersectionExclusionClipRatio", 0.0) or 0.0) <= 1.0,
            "Design Surface should expose a bounded intersection exclusion clip ratio.",
        )
        _assert(
            hasattr(design_preview, "IntersectionExclusionNearBoundaryKeptTriangleCount"),
            "Design Surface should expose near-boundary kept triangle diagnostics.",
        )
        _assert(
            float(getattr(design_preview, "IntersectionExclusionMaxKeptBoundaryDistance", 0.0) or 0.0) >= 0.0,
            "Design Surface should expose a non-negative max kept-boundary distance.",
        )
        _assert(
            int(getattr(daylight_preview, "SharedBreaklineBoundaryLoopRefCount", 0) or 0) > 0,
            "Ordinary Slope Face Surface should consume boundary-loop shared breakline refs.",
        )
        _assert(
            int(getattr(daylight_preview, "SharedBreaklineConstraintEdgeCount", 0) or 0) > 0,
            "Ordinary Slope Face Surface should expose shared breakline constraint edges for boundary-loop handoff.",
        )
        _assert(
            int(getattr(daylight_preview, "SharedBreaklineBoundaryLoopConstraintEdgeCount", 0) or 0) > 0,
            "Ordinary Slope Face Surface should preserve boundary-loop constraint edges.",
        )
        _assert(
            str(getattr(daylight_preview, "IntersectionExclusionBoundarySource", "") or "") == "intersection_boundary_loop",
            "Ordinary Slope Face Surface should use the authoritative boundary loop as the intersection exclusion source.",
        )
        _assert(
            int(getattr(daylight_preview, "IntersectionExclusionBoundaryLoopPointCount", 0) or 0) >= 3,
            "Ordinary Slope Face Surface should expose the boundary-loop exclusion point count.",
        )
        _assert(
            str(getattr(daylight_preview, "IntersectionBoundaryLoopOwnershipStatus", "") or "") == "ready",
            f"Ordinary Slope Face Surface should report ready boundary-loop ownership: "
            f"{getattr(daylight_preview, 'IntersectionBoundaryLoopOwnershipNotes', '')}",
        )
        _assert(
            int(getattr(daylight_preview, "IntersectionExclusionTestedTriangleCount", 0) or 0)
            == int(getattr(daylight_preview, "IntersectionExclusionClippedTriangleCount", 0) or 0)
            + int(getattr(daylight_preview, "IntersectionExclusionKeptTriangleCount", 0) or 0),
            "Ordinary Slope Face Surface should expose consistent intersection exclusion tested/clipped/kept counts.",
        )
        _assert(
            0.0 <= float(getattr(daylight_preview, "IntersectionExclusionClipRatio", 0.0) or 0.0) <= 1.0,
            "Ordinary Slope Face Surface should expose a bounded intersection exclusion clip ratio.",
        )
        _assert(
            hasattr(daylight_preview, "IntersectionExclusionNearBoundaryKeptTriangleCount"),
            "Ordinary Slope Face Surface should expose near-boundary kept triangle diagnostics.",
        )
        _assert(
            float(getattr(daylight_preview, "IntersectionExclusionMaxKeptBoundaryDistance", 0.0) or 0.0) >= 0.0,
            "Ordinary Slope Face Surface should expose a non-negative max kept-boundary distance.",
        )
        near_kept_count = int(getattr(daylight_preview, "IntersectionExclusionNearBoundaryKeptTriangleCount", 0) or 0)
        if near_kept_count > 0:
            near_kept_rows = list(getattr(daylight_preview, "IntersectionExclusionNearBoundaryKeptTriangleRows", []) or [])
            _assert(
                near_kept_rows,
                "Ordinary Slope Face Surface should expose near-boundary kept triangle centroid rows when count is non-zero.",
            )
            _assert(
                _parse_intersection_exclusion_near_boundary_kept_triangle_row(near_kept_rows[0]) is not None,
                "Near-boundary kept triangle centroid rows should be parseable.",
            )
        boundary_handoff_rows = _boundary_loop_handoff_rows(doc)
        handoff_by_role = {str(row.get("role", "") or ""): row for row in boundary_handoff_rows}
        for role_name in ("intersection", "design", "daylight"):
            _assert(
                role_name in handoff_by_role,
                f"Breakline Audit should expose a Boundary Loop Handoff row for {role_name}.",
            )
            _assert(
                handoff_by_role[role_name].get("status") == "ready",
                f"Boundary Loop Handoff row for {role_name} should be ready: {handoff_by_role[role_name]}",
            )
            if role_name in {"design", "daylight"}:
                _assert(
                    handoff_by_role[role_name].get("boundary_loop_ownership_status") == "ready",
                    f"Boundary Loop Handoff row for {role_name} should expose ready ownership status.",
                )
            _assert(
                int(handoff_by_role[role_name].get("boundary_loop_constraint_edge_count", 0) or 0) > 0,
                f"Boundary Loop Handoff row for {role_name} should report preserved constraint edges.",
            )
            _assert(
                "boundary_loop_handoff=refs=" in str(handoff_by_role[role_name].get("notes", "") or ""),
                f"Boundary Loop Handoff row for {role_name} should expose handoff notes.",
            )
            _assert(
                list(handoff_by_role[role_name].get("graph_edge_refs", []) or []),
                f"Boundary Loop Handoff row for {role_name} should expose graph edge refs for focused highlight.",
            )
        breakline_display_rows = shared_breakline_audit_display_rows(
            corridor_shared_breakline_audit_rows(doc),
            include_internal=True,
        )
        graph_summary_rows = [row for row in breakline_display_rows if row.get("row_kind") == "graph"]
        _assert(graph_summary_rows, "Breakline Audit should expose Shared Boundary Graph summary rows.")
        _assert(
            all(list(row.get("graph_edge_refs", []) or []) for row in graph_summary_rows),
            "Shared Boundary Graph summary rows should focus canonical graph edges, not shared-breakline fallback geometry.",
        )
        graph_pair_rows = [row for row in breakline_display_rows if row.get("row_kind") == "graph_pair"]
        _assert(graph_pair_rows, "Breakline Audit should expose Shared Boundary Graph pair rows.")
        _assert(
            all(list(row.get("graph_edge_refs", []) or []) for row in graph_pair_rows),
            "Shared Boundary Graph pair rows should focus matching canonical graph edges.",
        )
        _assert(
            int(getattr(slope_face_preview, "TriangleCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface has no triangles.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryLoopSharedBreaklineCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should preserve boundary-loop shared breakline refs.",
        )
        _assert(
            list(getattr(slope_face_preview, "IntersectionBoundaryLoopSharedBreaklineRefs", []) or []),
            "Dedicated Intersection Slope Face Surface should expose boundary-loop shared breakline refs.",
        )
        _assert(
            str(getattr(slope_face_preview, "IntersectionBoundaryOwnerStatus", "") or "") == "ready",
            f"Dedicated Intersection Slope Face Surface should expose ready boundary-owner handoff metadata; "
            f"{getattr(slope_face_preview, 'IntersectionBoundaryOwnerSummary', '')}",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryOwnerCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should expose boundary-owner coverage rows.",
        )
        boundary_owner_refs = list(getattr(slope_face_preview, "IntersectionBoundaryOwnerRefs", []) or [])
        _assert(
            any(
                "intersection-boundary-owner:leg:01:" in str(value)
                or "intersection-boundary-owner:leg-01:" in str(value)
                for value in boundary_owner_refs
            )
            and any(
                "intersection-boundary-owner:leg:02:" in str(value)
                or "intersection-boundary-owner:leg-02:" in str(value)
                for value in boundary_owner_refs
            ),
            f"Dedicated Intersection Slope Face Surface should expose main and side-road boundary owner refs; "
            f"{boundary_owner_refs}",
        )
        _assert(
            str(getattr(slope_face_preview, "IntersectionSlopeFaceOwnerFillReadinessStatus", "") or "") == "ready",
            f"Dedicated Intersection Slope Face Surface should report ready owner/fill readiness; "
            f"{getattr(slope_face_preview, 'IntersectionSlopeFaceOwnerFillReadinessSummary', '')}",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceOwnerFillComponentTriangleCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should report owner/fill component triangles.",
        )
        _assert(
            str(getattr(slope_face_preview, "IntersectionSlopeFaceOwnerGraphFillLinkStatus", "") or "")
            in ("ready", "not_applicable", "not_evaluated"),
            f"Dedicated Intersection Slope Face Surface should expose truthful graph-fill owner link status; "
            f"{getattr(slope_face_preview, 'IntersectionSlopeFaceOwnerFillReadinessSummary', '')}",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceOwnerGraphFillBoundaryRefCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should report graph-fill boundary ref count.",
        )
        _assert(
            list(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphSurfaceBoundaryRefs", []) or []),
            "Dedicated Intersection Slope Face Surface should expose graph surface boundary refs for fill diagnostics.",
        )
        intersection_bbox = _shape_bbox_xy(intersection_preview)
        slope_face_bbox = _shape_bbox_xy(slope_face_preview)
        intersection_bbox_area = _bbox_area_xy(intersection_bbox)
        slope_face_bbox_area = _bbox_area_xy(slope_face_bbox)
        bbox_overlap_area = _bbox_overlap_area_xy(intersection_bbox, slope_face_bbox)
        intersection_area = _shape_area(intersection_preview)
        slope_face_area = _shape_area(slope_face_preview)
        _assert(
            intersection_bbox_area > 0.0 and slope_face_bbox_area > 0.0,
            f"Dedicated Intersection Slope Face Surface should expose measurable bbox coverage; "
            f"intersection_bbox={intersection_bbox}, slope_face_bbox={slope_face_bbox}.",
        )
        _assert(
            bbox_overlap_area / min(intersection_bbox_area, slope_face_bbox_area) >= 0.20,
            f"Dedicated Intersection Slope Face Surface bbox should overlap the intersection patch vicinity; "
            f"overlap={bbox_overlap_area:.3f}, intersection_bbox_area={intersection_bbox_area:.3f}, "
            f"slope_face_bbox_area={slope_face_bbox_area:.3f}.",
        )
        _assert(
            slope_face_bbox_area / intersection_bbox_area <= 0.25,
            f"Dedicated Intersection Slope Face Surface bbox should not expand into broad alignment-side coverage; "
            f"intersection_bbox_area={intersection_bbox_area:.3f}, slope_face_bbox_area={slope_face_bbox_area:.3f}.",
        )
        _assert(
            int(getattr(slope_face_preview, "CurbReturnSlopeFacePerimeterTriangleCount", 0) or 0) == 0,
            "Curb-return perimeter should not use remote Applied Section candidates to emit alignment-direction triangles.",
        )
        _assert(
            str(getattr(slope_face_preview, "CurbReturnSlopeFacePerimeterGenerationMode", "") or "")
            == "no_curb_return_perimeter_strip",
            "Dedicated Intersection Slope Face Surface should suppress curb-return perimeter strips when only remote candidates are available.",
        )
        _assert(
            "outer_point_missing" in str(getattr(slope_face_preview, "CurbReturnSlopeFacePerimeterDiagnostic", "") or ""),
            "Suppressed curb-return perimeter strips should expose a diagnostic instead of silently creating remote geometry.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceBoundaryStripTriangleCount", 0) or 0) == 0,
            "Dedicated Intersection Slope Face Surface should suppress broad boundary-strip triangles when ready cells exist.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceBoundaryStripCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should keep boundary strip rows as metadata.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceBoundaryStripCount", 0) or 0) == 1,
            "Dedicated Intersection Slope Face Surface should suppress lower/side temporary boundary strips in the T preset.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceTransitionStripCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should report transition strip rows as compatibility metadata.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceTransitionStripTriangleCount", 0) or 0) == 0,
            "Dedicated Intersection Slope Face Surface should not generate broad transition strip triangles when ready cells exist.",
        )
        _assert(
            str(getattr(slope_face_preview, "IntersectionSlopeFaceBoundaryStripGenerationMode", "") or "")
            == "metadata_only",
            "Dedicated Intersection Slope Face Surface should keep broad boundary strip generation metadata-only when cells exist.",
        )
        _assert(
            hasattr(slope_face_preview, "SuppressedAppliedBoundaryLoopCount"),
            "Applied Section completion loop suppression diagnostics should remain exposed.",
        )
        _assert(
            hasattr(slope_face_preview, "SuppressedPreferredComponentLoopFanCount"),
            "Dedicated Intersection Slope Face Surface should expose raw loop-fan suppression diagnostics.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceCellCount", 0) or 0) >= 3,
            "Dedicated Intersection Slope Face Surface should report cell-based slope-face candidates.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceCellReadyCount", 0) or 0) >= 3,
            "Dedicated Intersection Slope Face Surface should have ready upper and main/side tie cells.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceCellOpenCount", 0) or 0) == 0,
            "Dedicated Intersection Slope Face Surface should not report open ready-cell loops.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceCellMissingEdgeCount", 0) or 0) == 0,
            "Dedicated Intersection Slope Face Surface should not report missing cell edges.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceCellTriangleCount", 0) or 0) <= 2,
            "Dedicated Intersection Slope Face Surface should not generate broad main/side tie cell triangles.",
        )
        _assert(
            any(
                "main-side" in str(ref or "")
                for ref in list(getattr(slope_face_preview, "IntersectionSlopeFaceCellRefs", []) or [])
            ),
            "Dedicated Intersection Slope Face Surface should preserve main/side tie cell refs.",
        )
        _assert(
            any(
                "curb-return-bridge" in str(ref or "")
                for ref in list(getattr(slope_face_preview, "IntersectionSlopeFaceCellRefs", []) or [])
            ),
            "Dedicated Intersection Slope Face Surface should preserve curb-return bridge cell refs.",
        )
        _assert(
            any(
                "main_to_side" in str(row or "")
                for row in list(getattr(slope_face_preview, "IntersectionSlopeFaceCellAuditRows", []) or [])
            ),
            "Dedicated Intersection Slope Face Surface should expose cell-level audit rows.",
        )
        cell_audit_rows = [str(row or "") for row in list(getattr(slope_face_preview, "IntersectionSlopeFaceCellAuditRows", []) or [])]
        _assert(
            any("|upper_" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready upper transition cell.",
        )
        _assert(
            any("|curb_return_bridge_cell|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready curb-return bridge cell.",
        )
        _assert(
            any("|upper_left_transition_cell|" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready upper-left transition cell.",
        )
        _assert(
            any("|upper_mid_transition_cell|" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready upper-mid transition cell.",
        )
        _assert(
            any("|upper_right_transition_cell|" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready upper-right transition cell.",
        )
        _assert(
            any("|main_to_side_left_tie_cell|" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready left main/side tie cell.",
        )
        _assert(
            any("|main_to_side_right_tie_cell|" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready right main/side tie cell.",
        )
        shared_role_summary = str(getattr(slope_face_preview, "SharedBreaklineRoleSummary", "") or "")
        for role_name in (
            "patch_to_intersection_slope_face",
            "intersection_slope_face_to_corridor_slope_face",
            "intersection_slope_face_to_design_surface",
            "main_road_tie",
            "main_side_slope_face_tie",
            "curb_return_to_intersection_slope_face",
        ):
            _assert(
                f"{role_name}=" in shared_role_summary,
                f"Dedicated Intersection Slope Face Surface should expose shared breakline role: {role_name}.",
            )
        design_role_summary = str(getattr(design_preview, "SharedBreaklineRoleSummary", "") or "")
        _assert(
            "patch_to_design:" not in design_role_summary,
            "Design Surface should not consume the broad patch_to_design fallback when boundary-loop ownership is available.",
        )
        graph_edge_rows = _graph_edge_rows(slope_face_preview)
        graph_cell_rows = _graph_cell_rows(slope_face_preview)
        graph_roles = {row["role"] for row in graph_edge_rows}
        expected_graph_consumers = {
            "patch_to_intersection_slope_face": {"intersection_surface", "intersection_slope_face_surface"},
            "intersection_slope_face_to_design_surface": {"intersection_slope_face_surface", "design_surface"},
            "intersection_slope_face_to_corridor_slope_face": {"intersection_slope_face_surface", "slope_face_surface"},
            "main_road_tie": {"intersection_surface", "design_surface", "intersection_slope_face_surface"},
            "main_side_slope_face_tie": {"intersection_slope_face_surface"},
            "curb_return_to_intersection_slope_face": {"intersection_surface", "intersection_slope_face_surface"},
        }
        for role_name, expected_consumers in expected_graph_consumers.items():
            _assert(
                role_name in graph_roles,
                f"Shared Boundary Graph should expose canonical edge role: {role_name}.",
            )
            matching_rows = [row for row in graph_edge_rows if row["role"] == role_name]
            _assert(
                any(expected_consumers.issubset(row["consumers"]) for row in matching_rows),
                f"Shared Boundary Graph edge role {role_name} is missing expected consumers {sorted(expected_consumers)}.",
            )
        _assert(
            str(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphStatus", "") or "") == "ready",
            "Dedicated Intersection Slope Face Surface graph status should be ready.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphInternalSeamCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should report graph internal seams separately from outer boundary edges.",
        )
        _assert(
            list(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphInternalSeamRefs", []) or []),
            "Dedicated Intersection Slope Face Surface should expose graph internal seam refs separately.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphDuplicateEdgeCount", 0) or 0) == 0,
            "Shared Boundary Graph should not contain duplicate parallel edges.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphOpenCellCount", 0) or 0) == 0,
            "Dedicated slope-face graph cells should be graph-closed.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphEndpointMismatchCount", 0) or 0) == 0,
            "Shared Boundary Graph should not contain endpoint mismatches.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphNotSnappedCount", 0) or 0) == 0,
            "Shared Boundary Graph should not contain unsnapped duplicate canonical nodes.",
        )
        _assert(
            graph_cell_rows and all(row["closed"] and not row["diagnostics"] for row in graph_cell_rows),
            "All dedicated slope-face graph cell rows should be closed and diagnostic-free.",
        )
        dedicated_graph_refs = {
            str(value or "")
            for value in list(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphRefs", []) or [])
            if str(value or "")
        }
        daylight_graph_refs = {
            str(value or "")
            for value in list(getattr(daylight_preview, "IntersectionSharedBoundaryGraphRefs", []) or [])
            if str(value or "")
        }
        daylight_contact_edges = {
            row["edge_id"]
            for row in graph_edge_rows
            if row["role"] == "intersection_slope_face_to_corridor_slope_face"
        }
        _assert(
            daylight_contact_edges.intersection(dedicated_graph_refs).intersection(daylight_graph_refs),
            "Ordinary and dedicated Slope Face surfaces should consume the same graph edge at their contact boundary.",
        )
        contract_rows = corridor_intersection_contract_review_rows(doc)
        internal_contract_rows = corridor_intersection_contract_review_rows(doc, include_internal=True)
        expected_intersection_edge_refs = (
            "intersection-edge:intersection-starter-t-intersection:leg-01:pavement-edge-both-01",
            "intersection-edge:intersection-starter-t-intersection:leg-01:daylight-hinge-both-02",
            "intersection-edge:intersection-starter-t-intersection:leg-02:pavement-edge-both-01",
            "intersection-edge:intersection-starter-t-intersection:leg-02:daylight-hinge-both-02",
            "intersection-edge:intersection-starter-t-intersection:curb-return-01:curb-return-edge-left-01",
            "intersection-edge:intersection-starter-t-intersection:curb-return-01:curb-return-edge-right-02",
        )
        _assert(
            not any(row.get("contract_family") == "edge_network" for row in contract_rows),
            "Intersections tab should not expose raw edge_network rows; edge refs should be carried by higher-level contracts.",
        )
        downstream_edge_refs = " ".join(
            str(row.get("source_refs", "") or "") + " " + str(row.get("boundary_refs", "") or "")
            for row in contract_rows
        )
        for edge_id in expected_intersection_edge_refs:
            _assert(
                edge_id in downstream_edge_refs,
                f"Downstream intersection contracts should retain source/boundary edge ref {edge_id}.",
            )
        expected_intersection_zone_refs = (
            "intersection-zone:intersection-starter-t-intersection:central-junction",
            "intersection-zone:intersection-starter-t-intersection:leg-pavement-01",
            "intersection-zone:intersection-starter-t-intersection:leg-pavement-02",
            "intersection-zone:intersection-starter-t-intersection:curb-return-01",
            "intersection-zone:intersection-starter-t-intersection:curb-return-02",
            "intersection-zone:intersection-starter-t-intersection:slope-face-01",
            "intersection-zone:intersection-starter-t-intersection:slope-face-02",
        )
        _assert(
            not any(row.get("contract_family") == "surface_zone" for row in contract_rows),
            "Intersections tab should not expose raw surface_zone rows; zone refs should be carried by higher-level contracts.",
        )
        _assert(
            not any(row.get("contract_family") in {"slope_face_loop", "slope_face_cell", "shared_boundary_graph"} for row in contract_rows),
            "Intersections tab should hide internal slope-face loop/cell and shared-boundary graph rows by default.",
        )
        downstream_zone_refs = " ".join(
            str(row.get("source_refs", "") or "") + " " + str(row.get("boundary_refs", "") or "")
            for row in contract_rows
        )
        for zone_id in expected_intersection_zone_refs:
            _assert(
                zone_id in downstream_zone_refs,
                f"Downstream intersection contracts should retain surface-zone ref {zone_id}.",
            )
        boundary_loop_rows = [row for row in contract_rows if row.get("contract_family") == "boundary_loop"]
        _assert(boundary_loop_rows, "Intersections tab should expose the authoritative boundary_loop row.")
        _assert(
            any(row.get("status") == "ready" and row.get("role") == "outer_intersection_boundary" for row in boundary_loop_rows),
            "T preset should expose a ready outer_intersection_boundary row.",
        )
        _assert(
            any("closed=yes" in str(row.get("notes", "") or "") for row in boundary_loop_rows),
            "Boundary loop row should report a closed perimeter.",
        )
        ready_boundary_loop = next(
            row
            for row in boundary_loop_rows
            if row.get("status") == "ready" and row.get("role") == "outer_intersection_boundary"
        )
        ready_boundary_notes = str(ready_boundary_loop.get("notes", "") or "")
        _assert(
            _note_int(ready_boundary_notes, "points") >= 8 and _note_int(ready_boundary_notes, "segments") >= 8,
            "T preset boundary loop should expose a non-trivial source perimeter, not a simple bbox or convex hull.",
        )
        _assert(
            "convex_hull_fallback" not in ready_boundary_notes and "not_accepted_from_convex_hull" not in ready_boundary_notes,
            "T preset boundary loop should not be accepted from convex-hull fallback.",
        )
        boundary_loop_index = next(index for index, row in enumerate(contract_rows) if row.get("contract_family") == "boundary_loop")
        boundary_highlight = focus_corridor_intersection_contract_review_row(doc, boundary_loop_index)
        _assert(
            str(getattr(boundary_highlight, "ContractFamily", "") or "") == "boundary_loop",
            "Double-click/focus should create a boundary_loop contract highlight.",
        )
        _assert(
            int(getattr(boundary_highlight, "HighlightedShapeCount", 0) or 0) >= 1,
            "Boundary loop focus should highlight the authoritative outer perimeter.",
        )
        _assert(
            str(getattr(boundary_highlight, "BoundaryLoopRole", "") or "") == "outer_intersection_boundary",
            "Boundary loop highlight should expose the highlighted loop role.",
        )
        _assert(
            "Issues" in _parent_group_labels(doc, boundary_highlight),
            "Boundary loop highlight should be routed to Review > Issues, not Alignment/Profile containers.",
        )
        boundary_bbox = _shape_bbox_xy(boundary_highlight)
        _assert(
            boundary_bbox is not None
            and float(boundary_bbox["xmin"]) <= 0.0 <= float(boundary_bbox["xmax"])
            and float(boundary_bbox["ymin"]) <= 0.0 <= float(boundary_bbox["ymax"]),
            f"Boundary loop focus should show the accepted outer loop around the intersection anchor: {boundary_bbox}.",
        )
        _assert(
            int(getattr(boundary_highlight, "BoundaryLoopClosed", 0) or 0) == 1,
            "Boundary loop highlight should expose closed-loop metadata.",
        )
        _assert(
            int(getattr(boundary_highlight, "BoundaryLoopPointCount", 0) or 0) >= 8
            and int(getattr(boundary_highlight, "BoundaryLoopSegmentCount", 0) or 0) >= 8,
            "Boundary loop highlight should expose non-trivial point and segment counts.",
        )
        _assert(
            int(getattr(boundary_highlight, "BoundaryLoopSegmentRefCount", 0) or 0)
            == int(getattr(boundary_highlight, "BoundaryLoopSegmentCount", 0) or 0),
            "Boundary loop highlight should preserve one segment ref per boundary segment.",
        )
        _assert(
            int(getattr(boundary_highlight, "BoundaryLoopSharedBreaklineRefCount", 0) or 0) > 0,
            "Boundary loop highlight should expose shared breakline handoff refs.",
        )
        _assert(
            int(getattr(boundary_highlight, "BoundaryLoopGraphEdgeRefCount", 0) or 0) > 0,
            "Boundary loop highlight should expose shared-boundary graph edge refs.",
        )
        _assert(
            "intersection_slope_face_surface=" in str(getattr(boundary_highlight, "BoundaryLoopGraphConsumerSummary", "") or ""),
            "Boundary loop highlight should summarize graph consumers for Intersection Slope Face Surface.",
        )
        boundary_role_summary = str(getattr(boundary_highlight, "BoundaryLoopSegmentRoleSummary", "") or "")
        for expected_role in (
            "patch_to_design_surface",
            "intersection_slope_face_to_corridor_slope_face",
            "main_road_tie",
            "side_road_tie",
        ):
            _assert(
                f"{expected_role}=" in boundary_role_summary,
                f"T preset boundary loop should expose segment role {expected_role}.",
            )
        cell_contract_rows = [row for row in internal_contract_rows if row.get("contract_family") == "slope_face_cell"]
        _assert(
            len(cell_contract_rows) == len(cell_audit_rows),
            "Intersections tab should expose one slope_face_cell row for each cell audit row.",
        )
        _assert(
            all(row.get("status") == "ready" for row in cell_contract_rows),
            "T preset slope_face_cell contract rows should be ready.",
        )
        first_cell_index = next(index for index, row in enumerate(internal_contract_rows) if row.get("contract_family") == "slope_face_cell")
        cell_highlight = focus_corridor_intersection_contract_review_row(doc, first_cell_index, include_internal=True)
        _assert(
            str(getattr(cell_highlight, "ContractFamily", "") or "") == "slope_face_cell",
            "Double-click/focus should create a slope_face_cell contract highlight.",
        )
        _assert(
            int(getattr(cell_highlight, "HighlightedShapeCount", 0) or 0) >= 2,
            "Slope face cell focus should highlight the cell shared breakline boundary segments.",
        )
        cell_bbox = _shape_bbox_xy(cell_highlight)
        _assert(
            cell_bbox is not None and max(float(cell_bbox["xlen"]), float(cell_bbox["ylen"])) <= 24.001,
            f"Slope face cell focus should be clipped to the intersection neighborhood: {cell_bbox}.",
        )
        first_graph_edge_index = next(
            index
            for index, row in enumerate(internal_contract_rows)
            if row.get("contract_family") == "shared_boundary_graph" and str(row.get("role", "") or "").startswith("edge:")
        )
        graph_edge_highlight = focus_corridor_intersection_contract_review_row(doc, first_graph_edge_index, include_internal=True)
        _assert(
            str(getattr(graph_edge_highlight, "ContractFamily", "") or "") == "shared_boundary_graph",
            "Double-click/focus should create a shared_boundary_graph edge highlight.",
        )
        _assert(
            int(getattr(graph_edge_highlight, "HighlightedShapeCount", 0) or 0) == 1,
            "Shared Boundary Graph edge focus should highlight the selected canonical graph edge only.",
        )
        _assert(
            "Issues" in _parent_group_labels(doc, graph_edge_highlight),
            "Shared Boundary Graph edge highlight should be routed to Review > Issues, not Alignment/Profile containers.",
        )
        for graph_index, graph_row in enumerate(internal_contract_rows):
            if graph_row.get("contract_family") != "shared_boundary_graph":
                continue
            if not str(graph_row.get("role", "") or "").startswith("edge:"):
                continue
            graph_highlight = focus_corridor_intersection_contract_review_row(doc, graph_index, include_internal=True)
            graph_bbox = _shape_bbox_xy(graph_highlight)
            _assert(
                graph_bbox is not None and max(float(graph_bbox["xlen"]), float(graph_bbox["ylen"])) <= 24.001,
                f"Shared Boundary Graph focus should be clipped to the intersection neighborhood: "
                f"{graph_row.get('row_id')}; {graph_bbox}.",
            )
        first_graph_cell_index = next(
            index
            for index, row in enumerate(internal_contract_rows)
            if row.get("contract_family") == "shared_boundary_graph" and str(row.get("role", "") or "").startswith("cell:")
        )
        graph_cell_highlight = focus_corridor_intersection_contract_review_row(doc, first_graph_cell_index, include_internal=True)
        _assert(
            str(getattr(graph_cell_highlight, "ContractFamily", "") or "") == "shared_boundary_graph",
            "Double-click/focus should create a shared_boundary_graph cell highlight.",
        )
        _assert(
            int(getattr(graph_cell_highlight, "HighlightedShapeCount", 0) or 0) >= 1,
            "Shared Boundary Graph cell focus should highlight the selected canonical graph cell boundary.",
        )
        _assert(
            "Issues" in _parent_group_labels(doc, graph_cell_highlight),
            "Shared Boundary Graph cell highlight should be routed to Review > Issues, not Alignment/Profile containers.",
        )
        for graph_index, graph_row in enumerate(internal_contract_rows):
            if graph_row.get("contract_family") != "shared_boundary_graph":
                continue
            if not str(graph_row.get("role", "") or "").startswith("cell:"):
                continue
            graph_highlight = focus_corridor_intersection_contract_review_row(doc, graph_index, include_internal=True)
            graph_bbox = _shape_bbox_xy(graph_highlight)
            _assert(
                graph_bbox is not None
                and float(graph_bbox["xmin"]) >= -12.001
                and float(graph_bbox["xmax"]) <= 12.001
                and float(graph_bbox["ymin"]) >= -12.001
                and float(graph_bbox["ymax"]) <= 12.001,
                f"Shared Boundary Graph cell focus should be clipped to the intersection neighborhood: "
                f"{graph_row.get('row_id')}; {graph_bbox}.",
            )
        _assert(
            int(getattr(slope_face_preview, "TriangleCount", 0) or 0)
            == int(getattr(slope_face_preview, "CurbReturnSlopeFacePerimeterTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionSlopeFaceBoundaryStripTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphSurfaceTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionSlopeFaceCellTriangleCount", 0) or 0),
            "Dedicated Intersection Slope Face Surface should be composed from explicit perimeter, boundary-loop transition, boundary-strip, graph-cell, and cell triangles in this preset.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionTriangleCount", 0) or 0) == 0,
            "Boundary-loop transition rows should not emit visible alignment-direction strip triangles.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionCornerFillCount", 0) or 0) == 0,
            "Boundary-loop transition rows should not add visible corner-fill triangles.",
        )
        _assert(
            list(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionRefs", []) or []),
            "Dedicated Intersection Slope Face Surface should expose boundary-loop transition refs.",
        )
        transition_role_summary = str(
            getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionRoleSummary", "") or ""
        )
        _assert(
            transition_role_summary == "",
            "Boundary-loop transition role summary should describe visible strips only.",
        )
        transition_width_summary = str(
            getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionWidthSummary", "") or ""
        )
        _assert(
            transition_width_summary == "",
            "Boundary-loop transition width summary should describe visible strips only.",
        )
        transition_rows = list(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionRows", []) or [])
        _assert(
            any("role=patch_to_design_surface" in str(row or "") for row in transition_rows),
            "Dedicated Intersection Slope Face Surface should preserve patch-to-design transition rows for QA.",
        )
        _assert(
            any("mode=metadata_only" in str(row or "") for row in transition_rows),
            "Long boundary-loop road-tie segments should remain traceable as metadata-only rows.",
        )
        _assert(
            not any(
                "mode=visible_strip" in str(row or "")
                and (
                    "role=main_road_tie" in str(row or "")
                    or "role=side_road_tie" in str(row or "")
                )
                for row in transition_rows
            ),
            "Road-tie boundary-loop edges should not emit visible transition strips along the alignment.",
        )
        slope_face_bbox = _shape_bbox_xy(slope_face_preview)
        _assert(
            slope_face_bbox is not None
            and float(slope_face_bbox.get("xlen", 0.0) or 0.0) <= 55.0
            and float(slope_face_bbox.get("ylen", 0.0) or 0.0) <= 40.0,
            f"Dedicated Intersection Slope Face Surface should stay near the local intersection envelope; bbox={slope_face_bbox}",
        )
        _assert(
            str(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionQAStatus", "") or "") == "ready",
            f"Boundary-loop transition QA should be ready; "
            f"notes={getattr(slope_face_preview, 'IntersectionBoundaryLoopTransitionQANotes', '')}",
        )
        _assert(
            "Inspect dedicated slope-face cell" in str(
                getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionRecommendedAction", "") or ""
            ),
            "Boundary-loop transition QA should guide remaining visual gap triage toward cell and adjacent surface ownership.",
        )
        _assert(
            str(getattr(slope_face_preview, "IntersectionBoundaryLoopGraphCoverageStatus", "") or "") == "ready",
            f"Dedicated Intersection Slope Face Surface should cover all boundary-loop graph edges intended for it; "
            f"missing={list(getattr(slope_face_preview, 'IntersectionBoundaryLoopGraphMissingEdgeRefs', []) or [])}",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryLoopGraphConsumerEdgeCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should report boundary-loop graph consumer edge count.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryLoopGraphConsumerEdgeCount", 0) or 0)
            == int(getattr(slope_face_preview, "IntersectionBoundaryLoopGraphEdgeCount", 0) or 0),
            "Dedicated Intersection Slope Face Surface should consume every authoritative outer boundary-loop graph edge.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionBoundaryLoopGraphNonConsumerEdgeCount", 0) or 0) == 0,
            "Dedicated Intersection Slope Face Surface should not leave outer boundary-loop edges outside its consumer set.",
        )
        non_consumer_edge_rows = list(
            getattr(slope_face_preview, "IntersectionBoundaryLoopGraphNonConsumerEdgeRows", []) or []
        )
        _assert(
            not non_consumer_edge_rows,
            "Dedicated Intersection Slope Face Surface should expose no non-consumer boundary-loop edge rows once outer boundary ownership is complete.",
        )
        _assert(
            int(getattr(slope_face_preview, "SharedBreaklineConsumedCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should consume shared breakline refs.",
        )
        _assert(
            str(getattr(slope_face_preview, "SharedBreaklineAuditStatus", "") or "") == "ready",
            "Dedicated Intersection Slope Face Surface shared breakline audit should be ready.",
        )
        _assert(
            int(getattr(slope_face_preview, "SharedBreaklineMeshMismatchCount", 0) or 0) == 0,
            "Shared breakline audit should not report mesh mismatches when normalized constraint segments cover the breakline.",
        )
        _assert(
            list(getattr(slope_face_preview, "SourceLoopRefs", []) or []),
            "Dedicated Intersection Slope Face Surface did not preserve source perimeter refs.",
        )
        _assert(
            int(getattr(slope_face_preview, "ReadyLoopCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should include Applied Section completed slope-face loops.",
        )
        _assert(
            any(
                str(ref or "").startswith("intersection-slope-face-loop:")
                for ref in list(getattr(slope_face_preview, "SourceLoopRefs", []) or [])
            ),
            "Dedicated Intersection Slope Face Surface should preserve Applied Section slope-face loop refs.",
        )
        _assert(slope_rows, "Results rows are missing the Intersection Slope Face Surface row.")
        _assert(slope_rows[0]["status"] == "ready", "Results row did not mark Intersection Slope Face Surface ready.")
        _assert(
            int(slope_rows[0].get("triangle_or_point_count", 0) or 0) == int(getattr(slope_face_preview, "TriangleCount", 0) or 0),
            "Results row should report the dedicated Intersection Slope Face Surface triangle count.",
        )
        _assert(
            str(getattr(daylight_preview, "IntersectionSlopeLoopSuppressStatus", "") or "") == "ready",
            "Ordinary Slope Face Surface should run intersection slope-face footprint suppression.",
        )
        _assert(
            int(getattr(daylight_preview, "IntersectionSlopeLoopSuppressReferenceTriangleCount", 0) or 0)
            >= int(getattr(slope_face_preview, "CurbReturnSlopeFacePerimeterTriangleCount", 0) or 0),
            "Ordinary Slope Face Surface suppression should include dedicated curb-return perimeter triangles.",
        )
        _assert(
            int(getattr(daylight_preview, "IntersectionSlopeLoopSuppressSuppressedTriangleCount", 0) or 0) > 0
            or int(getattr(daylight_preview, "IntersectionExclusionClippedTriangleCount", 0) or 0) > 0,
            "Ordinary Slope Face Surface should be clipped either by the boundary-loop exclusion or by dedicated slope-face footprint suppression.",
        )
        _assert(
            int(getattr(daylight_preview, "IntersectionExclusionControlSectionClippedTriangleCount", 0) or 0) > 0,
            "Ordinary Slope Face Surface should suppress triangles generated from intersection control sections.",
        )
        _assert(
            "Show or hide" in corridor_build_preview_visibility_note(doc, "intersection_slope"),
            "Visibility note should be enabled when the dedicated preview object exists.",
        )

        print("[PASS] T intersection dedicated Slope Face Surface smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
