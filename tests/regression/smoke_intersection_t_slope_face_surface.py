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
    corridor_intersection_patch_prerequisite_result,
    corridor_shared_breakline_audit_rows,
    corridor_intersection_contract_review_rows,
    create_corridor_design_surface_preview,
    create_corridor_daylight_surface_preview,
    create_corridor_intersection_surface_preview,
    focus_corridor_intersection_contract_review_row,
    _intersection_tie_slope_applied_section_window_rows,
    _parse_intersection_exclusion_near_boundary_kept_triangle_row,
    _intersection_tie_slope_oriented_ring_points,
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


def _bbox_gap_xy(first, second):
    if not first or not second:
        return float("inf")
    x_gap = max(0.0, max(first["xmin"], second["xmin"]) - min(first["xmax"], second["xmax"]))
    y_gap = max(0.0, max(first["ymin"], second["ymin"]) - min(first["ymax"], second["ymax"]))
    return max(x_gap, y_gap)


def _ring_area_xy(points):
    point_list = [(float(point[0]), float(point[1])) for point in list(points or [])]
    if len(point_list) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(point_list):
        next_point = point_list[(index + 1) % len(point_list)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return area / 2.0


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


def _graph_cell_diagnostics_are_informational(text):
    diagnostics = [
        value.strip()
        for value in str(text or "").replace(";", ",").split(",")
        if value.strip()
    ]
    return not diagnostics


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


def _upper_panel_candidate_fields(row):
    parts = str(row or "").split("|")
    output = {
        "candidate_id": parts[0] if len(parts) > 0 else "",
        "status": parts[1] if len(parts) > 1 else "",
        "alignment_ref": parts[2] if len(parts) > 2 else "",
        "side": parts[3] if len(parts) > 3 else "",
        "loop_area": 0.0,
        "inner_ref": parts[5] if len(parts) > 5 else "",
        "outer_ref": parts[6] if len(parts) > 6 else "",
        "left_cap_ref": parts[7] if len(parts) > 7 else "",
        "right_cap_ref": parts[8] if len(parts) > 8 else "",
        "diagnostics": parts[16] if len(parts) > 16 else "",
    }
    try:
        output["loop_area"] = float(parts[4]) if len(parts) > 4 else 0.0
    except Exception:
        output["loop_area"] = 0.0
    for part in parts[9:16]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "caps":
            cap_parts = value.split("/", 1)
            try:
                output["left_cap_len"] = float(cap_parts[0])
            except Exception:
                output["left_cap_len"] = 0.0
            try:
                output["right_cap_len"] = float(cap_parts[1]) if len(cap_parts) > 1 else 0.0
            except Exception:
                output["right_cap_len"] = 0.0
            continue
        try:
            output[key] = float(value)
        except Exception:
            output[key] = 0.0
    return output


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
    clockwise_tie_slope_loop = [
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (2.0, 1.0, 0.0),
        (2.0, 0.0, 0.0),
    ]
    oriented_tie_slope_loop = _intersection_tie_slope_oriented_ring_points(clockwise_tie_slope_loop)
    _assert(
        _ring_area_xy(oriented_tie_slope_loop) > 0.0,
        "Intersection Tie Slope loops should be normalized to a consistent top-facing winding before triangulation.",
    )
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
        tie_slope_preview = doc.getObject("V1CorridorIntersectionTieSlopeSurfacePreview")
        review_rows = corridor_build_review_rows(doc)
        slope_rows = [row for row in review_rows if row["role"] == "intersection_slope"]
        prerequisite = corridor_intersection_patch_prerequisite_result(doc)
        intersection_model = to_intersection_model(find_v1_intersection_model(doc))
        tie_slope_window_rows = _intersection_tie_slope_applied_section_window_rows(
            applied,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
        accepted_tie_slope_rows = [
            row for row in tie_slope_window_rows
            if str(row.get("status", "") or "") == "accepted"
        ]

        _assert(len(applied.sections) > 0, "T preset smoke should build Applied Sections.")
        _assert(intersection_preview is not None, "Intersection Surface preview was not created.")
        _assert(design_preview is not None, "Design Surface preview was not created.")
        _assert(daylight_preview is not None, "Ordinary Slope Face Surface preview was not created.")
        _assert(slope_face_preview is not None, "Dedicated Intersection Slope Face Surface preview was not created.")
        _assert(
            tie_slope_preview is not None,
            "Intersection Tie Slope preview should be created from accepted Applied Section window rows.",
        )
        _assert(
            "Intersections" in _parent_group_labels(doc, tie_slope_preview),
            "Intersection Tie Slope preview should be routed under Parametric Model > Intersections.",
        )
        _assert(
            str(getattr(tie_slope_preview, "IntersectionTieSlopeGeometrySource", "") or "") == "accepted_applied_section_window_rows",
            "Intersection Tie Slope preview must use accepted Applied Section window rows as its geometry source.",
        )
        _assert(
            int(getattr(tie_slope_preview, "IntersectionTieSlopeTriangleCount", 0) or 0) > 0,
            "Intersection Tie Slope preview should contain visible triangles from accepted window rows.",
        )
        _assert(
            int(getattr(tie_slope_preview, "IntersectionTieSlopeAppliedSectionWindowAcceptedCount", 0) or 0) > 0,
            "Intersection Tie Slope preview should report accepted Applied Section window rows.",
        )
        _assert(
            accepted_tie_slope_rows,
            "T Intersection should still create accepted legacy Intersection Tie Slope window rows.",
        )
        _assert(
            all(str(row.get("outer_edge_source_mode", "") or "") == "legacy_slope_breakline" for row in accepted_tie_slope_rows)
            and all(str(row.get("inner_edge_source_mode", "") or "") == "legacy_slope_breakline" for row in accepted_tie_slope_rows),
            (
                "T Intersection Tie Slope should remain on the pre-Cross legacy window edge path; "
                f"rows={accepted_tie_slope_rows}."
            ),
        )
        _assert(
            not any(str(row.get("outer_edge_source_mode", "") or "") == "applied_section_side_slope_edge" for row in accepted_tie_slope_rows)
            and not any(str(row.get("inner_edge_source_mode", "") or "") == "applied_section_side_slope_edge" for row in accepted_tie_slope_rows),
            (
                "Cross-only Applied Section side-slope edge selection must not affect T Intersection Tie Slope; "
                f"rows={accepted_tie_slope_rows}."
            ),
        )
        _assert(
            doc.getObject("ReviewIntersectionTieSlopeTransitionGapHighlight") is None
            and not str(getattr(intersection_preview, "IntersectionTieSlopeTransitionGapHighlightRef", "") or ""),
            "Intersection Tie Slope transition gap highlight should no longer be generated once the surface output is available.",
        )
        tie_slope_preview_bbox = _shape_bbox_xy(tie_slope_preview)
        tie_slope_preview_area = _bbox_area_xy(tie_slope_preview_bbox)
        _assert(
            tie_slope_preview_bbox is not None
            and tie_slope_preview_area > 0.0,
            f"Intersection Tie Slope surface should expose a measurable local surface bbox: "
            f"preview={tie_slope_preview_bbox}, area={tie_slope_preview_area:.3f}.",
        )
        _assert(
            int(getattr(tie_slope_preview, "IntersectionTieSlopeTriangleCount", 0) or 0)
            == int(getattr(tie_slope_preview, "IntersectionTieSlopeAppliedSectionWindowAcceptedCount", 0) or 0) * 2,
            "Intersection Tie Slope preview should triangulate each accepted four-edge window as exactly two triangles.",
        )
        _assert(
            any(row["role"] == "intersection_tie_slope" for row in review_rows),
            "Results rows should expose source-owned Intersection Tie Slope diagnostics while STA-separated generation is pending.",
        )
        tie_slope_review_rows = [row for row in review_rows if row.get("role") == "intersection_tie_slope"]
        _assert(
            tie_slope_review_rows[0].get("status") == "ready",
            f"Intersection Tie Slope Results row should be ready when accepted Applied Section window rows generate triangles: {tie_slope_review_rows[0]}",
        )
        tie_slope_review_notes = str(tie_slope_review_rows[0].get("notes", "") or "")
        _assert(
            "ready=0" in tie_slope_review_notes
            and "sta_separation_required" in tie_slope_review_notes
            and "transition_spans=" in tie_slope_review_notes
            and "preferred_breakline_ready=" in tie_slope_review_notes
            and "preferred_breakline_roles=intersection_tie_slope_transition_inner,intersection_tie_slope_transition_outer,intersection_tie_slope_start_cap,intersection_tie_slope_end_cap" in tie_slope_review_notes
            and "Recommended Action: Build separated Region/control-area to Applied Section intersection STA transition" in tie_slope_review_notes,
            f"Intersection Tie Slope Results row should retain legacy diagnostic context while window rows provide visible geometry: {tie_slope_review_notes}",
        )
        _assert(
            "Applied Section window candidates:" in tie_slope_review_notes
            and "accepted=" in tie_slope_review_notes
            and "source=applied_section_context_transition_window" in tie_slope_review_notes,
            f"Intersection Tie Slope Results row should expose Applied Section window candidate readiness: {tie_slope_review_notes}",
        )
        _assert(
            int(getattr(intersection_preview, "SharedBreaklineBoundaryLoopRefCount", 0) or 0) > 0,
            "Intersection Surface should consume boundary-loop shared breakline refs.",
        )
        _assert(
            int(getattr(intersection_preview, "SharedBreaklineConstraintSegmentCount", 0) or 0) > 0,
            "Intersection Surface should expose consumed shared breakline segments for boundary-loop handoff.",
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
            int(getattr(design_preview, "SharedBreaklineConstraintSegmentCount", 0) or 0) > 0,
            "Design Surface should expose consumed shared breakline segments for boundary-loop handoff.",
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
            int(getattr(daylight_preview, "SharedBreaklineConstraintSegmentCount", 0) or 0) > 0,
            "Ordinary Slope Face Surface should expose consumed shared breakline segments for boundary-loop handoff.",
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
        breakline_notes = " ".join(
            " ".join(str(value or "") for value in row.values())
            for row in breakline_display_rows
        )
        for role_name in (
            "intersection_tie_slope_inner",
            "intersection_tie_slope_outer",
            "intersection_tie_slope_transition_inner",
            "intersection_tie_slope_transition_outer",
            "intersection_tie_slope_start_cap",
            "intersection_tie_slope_end_cap",
        ):
            _assert(
                role_name not in breakline_notes,
                f"Legacy Intersection Tie Slope shared breakline role should stay disabled until separated STA transitions are built: {role_name}.",
            )
        for role_name in (
            "intersection_tie_slope_window_outer",
            "intersection_tie_slope_window_inner",
            "intersection_tie_slope_window_start_cap",
            "intersection_tie_slope_window_end_cap",
        ):
            _assert(
                role_name in breakline_notes,
                f"Breakline Audit should expose Applied Section window Tie Slope shared breakline role: {role_name}.",
            )
        supplemental_role_counts = {}
        for audit_row in breakline_display_rows:
            for token in str(audit_row.get("role_summary", "") or "").split(","):
                token = token.strip()
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                try:
                    count = int(value.strip() or 0)
                except Exception:
                    continue
                supplemental_role_counts[key.strip()] = max(supplemental_role_counts.get(key.strip(), 0), count)
        for role_name in (
            "intersection_tie_slope_supplemental_outer",
            "intersection_tie_slope_supplemental_inner",
            "intersection_tie_slope_supplemental_endpoint",
        ):
            _assert(
                int(supplemental_role_counts.get(role_name, 0) or 0) == 0,
                (
                    f"T Intersection Tie Slope should not emit Cross supplemental shared breakline role: {role_name}; "
                    f"counts={supplemental_role_counts}."
                ),
            )
        tie_slope_window_handoff_rows = [
            row for row in breakline_display_rows
            if row.get("row_kind") == "intersection_tie_slope_window"
        ]
        _assert(
            tie_slope_window_handoff_rows,
            "Breakline Audit should expose a compact Intersection Tie Slope Window Handoff row.",
        )
        tie_slope_window_handoff = next(
            (
                row for row in tie_slope_window_handoff_rows
                if row.get("status") == "ready"
                and "missing_roles=none" in str(row.get("notes", "") or "")
            ),
            tie_slope_window_handoff_rows[0],
        )
        _assert(
            tie_slope_window_handoff.get("status") == "ready",
            f"Intersection Tie Slope Window Handoff should be ready: {tie_slope_window_handoff}",
        )
        _assert(
            "source=applied_section_context_transition_window" in str(tie_slope_window_handoff.get("notes", "") or "")
            and "missing_roles=none" in str(tie_slope_window_handoff.get("notes", "") or ""),
            f"Intersection Tie Slope Window Handoff should explain source and completeness: {tie_slope_window_handoff}",
        )
        tie_slope_shared_refs = " ".join(
            str(value or "")
            for value in list(getattr(tie_slope_preview, "IntersectionTieSlopeSharedBreaklineRefs", []) or [])
        )
        _assert(
            int(getattr(tie_slope_preview, "IntersectionTieSlopeSharedBreaklineCount", 0) or 0) > 0,
            "Intersection Tie Slope preview should consume window shared breaklines.",
        )
        for role_name in (
            "intersection-tie-slope-window-outer",
            "intersection-tie-slope-window-inner",
            "intersection-tie-slope-window-start-cap",
            "intersection-tie-slope-window-end-cap",
        ):
            _assert(
                role_name in tie_slope_shared_refs,
                f"Intersection Tie Slope preview should record shared breakline ref for {role_name}: {tie_slope_shared_refs}",
            )
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
            not any(row.get("row_kind") in {"control_area_transition_caps", "control_area_transition_cell"} for row in breakline_display_rows),
            "Removed control-area transition experiments should not appear in Breakline Audit.",
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
        bbox_gap = _bbox_gap_xy(intersection_bbox, slope_face_bbox)
        intersection_area = _shape_area(intersection_preview)
        slope_face_area = _shape_area(slope_face_preview)
        _assert(
            intersection_bbox_area > 0.0 and slope_face_bbox_area > 0.0,
            f"Dedicated Intersection Slope Face Surface should expose measurable bbox coverage; "
            f"intersection_bbox={intersection_bbox}, slope_face_bbox={slope_face_bbox}.",
        )
        _assert(
            bbox_overlap_area > 0.0 or bbox_gap <= 12.0,
            f"Dedicated Intersection Slope Face Surface bbox should stay near the intersection patch vicinity; "
            f"overlap={bbox_overlap_area:.3f}, intersection_bbox_area={intersection_bbox_area:.3f}, "
            f"slope_face_bbox_area={slope_face_bbox_area:.3f}, bbox_gap={bbox_gap:.3f}.",
        )
        _assert(
            slope_face_bbox_area / intersection_bbox_area <= 3.00,
            f"Dedicated Intersection Slope Face Surface bbox should stay within local intersection transition coverage; "
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
            "Dedicated Intersection Slope Face Surface should have ready upper/control-area transition cells.",
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
            int(getattr(slope_face_preview, "IntersectionSlopeFaceCellTriangleCount", 0) or 0) <= 10,
            "Dedicated Intersection Slope Face Surface should limit generated cell triangles to local transition cells.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceUpperTransitionTriangleCount", 0) or 0) == 0,
            "Dedicated Intersection Slope Face Surface should suppress legacy upper transition cell triangles once rectangular panels are accepted.",
        )
        upper_cell_refs = [
            str(ref or "")
            for ref in list(getattr(slope_face_preview, "IntersectionSlopeFaceUpperCellRefs", []) or [])
        ]
        _assert(
            upper_cell_refs,
            "Dedicated Intersection Slope Face Surface should expose upper transition cell refs for rectangular-panel replacement diagnostics.",
        )
        suppressed_upper_cell_refs = [
            str(ref or "")
            for ref in list(getattr(slope_face_preview, "IntersectionSlopeFaceSuppressedUpperCellRefs", []) or [])
        ]
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceSuppressedUpperCellCount", 0) or 0) > 0
            and suppressed_upper_cell_refs,
            "Accepted rectangular panels should suppress overlapping legacy upper transition cells while retaining their refs.",
        )
        cell_role_summary = str(getattr(slope_face_preview, "IntersectionSlopeFaceCellRoleSummary", "") or "")
        if cell_role_summary:
            _assert(
                "upper_" not in cell_role_summary,
                f"Generated cell role summary should not include suppressed legacy upper cells; summary={cell_role_summary!r}.",
            )
        _assert(
            str(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelSourceMode", "") or "")
            == "accepted_upper_rectangular_panel_boundary",
            "Dedicated Intersection Slope Face Surface should expose source-boundary upper rectangular panel candidates.",
        )
        upper_panel_candidate_rows = [
            str(row or "")
            for row in list(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelCandidateRows", []) or [])
        ]
        _assert(
            int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelCandidateCount", 0) or 0) > 0
            and upper_panel_candidate_rows,
            "Dedicated Intersection Slope Face Surface should expose upper rectangular panel candidate rows.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelAcceptedCount", 0) or 0) > 0
            and any("|accepted|" in row for row in upper_panel_candidate_rows),
            f"Upper rectangular panel candidates should include accepted source-boundary rows: {upper_panel_candidate_rows}",
        )
        upper_panel_accepted_rows = [
            _upper_panel_candidate_fields(row)
            for row in upper_panel_candidate_rows
            if "|accepted|" in row
        ]
        upper_panel_accepted_count = int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelAcceptedCount", 0) or 0)
        _assert(
            str(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelGenerationMode", "") or "")
            == "upper_rectangular_panel",
            "Accepted upper rectangular panel candidates should generate dedicated panel triangles.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0) > 0,
            "Dedicated Intersection Slope Face Surface should report generated upper rectangular panels.",
        )
        _assert(
            len(upper_panel_accepted_rows) == upper_panel_accepted_count
            and int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0) == upper_panel_accepted_count,
            (
                "Upper rectangular panel generation should be one-to-one with accepted source candidates; "
                f"accepted_rows={len(upper_panel_accepted_rows)} accepted_count={upper_panel_accepted_count} "
                f"generated={getattr(slope_face_preview, 'IntersectionUpperSlopeFacePanelGeneratedCount', 0)}."
            ),
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelTriangleCount", 0) or 0)
            == int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0) * 2,
            "Each upper rectangular panel should triangulate as two triangles, not a center fan.",
        )
        for accepted_row in upper_panel_accepted_rows:
            _assert(
                float(accepted_row.get("loop_area", 0.0) or 0.0) > 0.0
                and float(accepted_row.get("inner_len", 0.0) or 0.0) > 0.0
                and float(accepted_row.get("outer_len", 0.0) or 0.0) > 0.0
                and float(accepted_row.get("left_cap_len", 0.0) or 0.0) > 0.0
                and float(accepted_row.get("right_cap_len", 0.0) or 0.0) > 0.0,
                f"Accepted upper panel candidate should have a closed non-zero rectangular loop: {accepted_row}",
            )
            _assert(
                float(accepted_row.get("bbox_aspect", 0.0) or 0.0) <= 8.0
                and float(accepted_row.get("bbox_fill", 0.0) or 0.0) >= 0.05
                and "remote_fan_risk" not in str(accepted_row.get("diagnostics", "") or ""),
                f"Accepted upper panel candidate should not be a broad/remote fan: {accepted_row}",
            )
        _assert(
            list(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelRefs", []) or [])
            and list(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelBoundaryRefs", []) or []),
            "Generated upper rectangular panels should expose source panel refs and boundary refs.",
        )
        _assert(
            len(list(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelRefs", []) or []))
            == upper_panel_accepted_count,
            "Generated upper rectangular panel refs should match the accepted candidate count.",
        )
        upper_panel_result_rows = [
            row for row in review_rows
            if row.get("role") == "intersection_upper_slope_face_panel"
        ]
        _assert(
            upper_panel_result_rows and upper_panel_result_rows[0].get("status") == "ready",
            "Results tab should expose a ready Intersection Upper Slope Face Panel row.",
        )
        upper_panel_result_notes = str(upper_panel_result_rows[0].get("notes", "") or "")
        for token in (
            "intersection_upper_slope_face_panel",
            "upper_panels=",
            "triangles=",
            "suppressed_legacy_upper_cells=",
            "mode=upper_rectangular_panel",
            "source=accepted_upper_rectangular_panel_boundary",
            "expected_groups=",
        ):
            _assert(
                token in upper_panel_result_notes,
                f"Results tab upper panel row should include {token}: {upper_panel_result_notes}",
            )
        _assert(
            all("patch-to-intersection-slope-face" in row and "intersection-slope-face-to-corridor-slope-face" in row for row in upper_panel_candidate_rows),
            f"Upper rectangular panel candidates should be derived from inner/outer shared breaklines: {upper_panel_candidate_rows}",
        )
        for metric_token in ("inner_len=", "outer_len=", "caps=", "bbox_diag=", "bbox_aspect=", "bbox_fill="):
            _assert(
                all(metric_token in row for row in upper_panel_candidate_rows),
                f"Upper rectangular panel candidate diagnostics should include {metric_token}: {upper_panel_candidate_rows}",
            )
        _assert(
            not any(
                "|accepted|" in row
                and (
                    "edge_missing" in row
                    or "cap_missing" in row
                    or "open_loop" in row
                    or "self_crossing" in row
                    or "zero_area" in row
                    or "remote_fan_risk" in row
                )
                for row in upper_panel_candidate_rows
            ),
            f"Upper rectangular panel candidates with blocking diagnostics must not be accepted: {upper_panel_candidate_rows}",
        )
        upper_panel_role_summary = str(getattr(slope_face_preview, "SharedBreaklineRoleSummary", "") or "")
        for role_name in (
            "intersection_upper_slope_face_panel_inner",
            "intersection_upper_slope_face_panel_outer",
            "intersection_upper_slope_face_panel_left_cap",
            "intersection_upper_slope_face_panel_right_cap",
        ):
            _assert(
                role_name in upper_panel_role_summary,
                f"Breakline Audit should expose upper rectangular panel handoff role {role_name}; summary={upper_panel_role_summary!r}.",
            )
        _assert(
            doc.getObject("ReviewIntersectionUpperSlopeFacePanelHighlight") is None
            and not str(getattr(intersection_preview, "IntersectionUpperSlopeFacePanelHighlightRef", "") or ""),
            "Intersection Upper Slope Face Panel Highlight should no longer be generated once panel metadata and surface output are available.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceMainSideTieTriangleCount", 0) or 0) == 0,
            "Main/side tie cells should remain metadata-only until curb-return side/leg context is unambiguous.",
        )
        _assert(
            int(getattr(slope_face_preview, "IntersectionSlopeFaceMainSideTieTriangleCount", 0) or 0) == 0,
            "Main/side tie candidates should not emit visible triangles until Intersection Tie Slope owns the connection.",
        )
        _assert(
            not any(
                "curb-return-bridge" in str(ref or "")
                for ref in list(getattr(slope_face_preview, "IntersectionSlopeFaceCellRefs", []) or [])
            ),
            "Diagnostic curb-return bridge candidates should not be visible cell refs.",
        )
        cell_diagnostic = str(getattr(slope_face_preview, "IntersectionSlopeFaceCellDiagnostic", "") or "")
        _assert(
            "control_area_transition" not in cell_diagnostic and "main_cap_transition" not in cell_diagnostic,
            "Removed control-area/main-cap transition experiments should not appear in active diagnostics.",
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
            not any("control_area_transition_candidate" in row or "|main_cap_" in row for row in cell_audit_rows),
            "Removed transition experiments should not expose active cell audit rows.",
        )
        _assert(
            any("|upper_" in row and "|ready|" in row for row in cell_audit_rows),
            "Dedicated Intersection Slope Face Surface should expose a ready upper transition cell.",
        )
        _assert(
            any(
                "|main_to_side_" in row
                for row in cell_audit_rows
            ),
            "Main/side tie cells should remain traceable as metadata until the new Intersection Tie Slope result owns them.",
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
            graph_cell_rows
            and all(
                row["closed"]
                and (not row["diagnostics"] or _graph_cell_diagnostics_are_informational(row["diagnostics"]))
                for row in graph_cell_rows
            ),
            "All dedicated slope-face graph cell rows should be closed and free of blocking diagnostics.",
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
        upper_panel_contract_rows = [
            row for row in contract_rows
            if row.get("contract_family") == "intersection_upper_slope_face_panel"
        ]
        _assert(
            upper_panel_contract_rows and upper_panel_contract_rows[0].get("status") == "ready",
            "Intersections tab should expose upper rectangular panel readiness.",
        )
        _assert(
            upper_panel_contract_rows[0].get("focus_object") == "V1CorridorIntersectionSlopeFaceSurfacePreview",
            "Upper rectangular panel contract row should focus the dedicated Intersection Slope Face Surface preview.",
        )
        upper_panel_contract_notes = str(upper_panel_contract_rows[0].get("notes", "") or "")
        for token in (
            "candidates=",
            "accepted=",
            "generated=",
            "triangles=",
            "suppressed_legacy_upper_cells=",
            "mode=upper_rectangular_panel",
            "source=accepted_upper_rectangular_panel_boundary",
            "expected_groups=",
        ):
            _assert(
                token in upper_panel_contract_notes,
                f"Intersections tab upper panel row should include {token}: {upper_panel_contract_notes}",
            )
        upper_panel_contract_refs = (
            str(upper_panel_contract_rows[0].get("source_refs", "") or "")
            + " "
            + str(upper_panel_contract_rows[0].get("boundary_refs", "") or "")
        )
        for accepted_row in upper_panel_accepted_rows:
            _assert(
                str(accepted_row.get("candidate_id", "") or "") in upper_panel_contract_refs
                and str(accepted_row.get("inner_ref", "") or "") in upper_panel_contract_refs
                and str(accepted_row.get("outer_ref", "") or "") in upper_panel_contract_refs,
                f"Intersections tab upper panel row should preserve source candidate and boundary refs: {accepted_row}",
            )
        intersection_tie_slope_rows = [
            row for row in contract_rows
            if row.get("contract_family") == "intersection_tie_slope"
        ]
        _assert(
            not intersection_tie_slope_rows,
            "Intersections tab should hide legacy Intersection Tie Slope gap-cell contracts once the window handoff and surface output are available.",
        )
        intersection_tie_slope_window_rows = [
            row for row in contract_rows
            if row.get("contract_family") == "intersection_tie_slope_window"
        ]
        _assert(
            intersection_tie_slope_window_rows,
            "Intersections tab should expose Applied Section window candidate readiness for Intersection Tie Slope.",
        )
        tie_slope_window_notes = " ".join(str(row.get("notes", "") or "") for row in intersection_tie_slope_window_rows)
        for window_token in (
            "Applied Section window candidates:",
            "accepted=",
            "transition_pair=",
            "intersection_adjacent_pair=",
            "source=applied_section_context_transition_window",
        ):
            _assert(
                window_token in tie_slope_window_notes,
                f"Intersection Tie Slope window contract should include {window_token}: {tie_slope_window_notes}",
            )
        tie_slope_window_index = next(
            index for index, row in enumerate(contract_rows)
            if row.get("contract_family") == "intersection_tie_slope_window"
        )
        tie_slope_focus = focus_corridor_intersection_contract_review_row(doc, tie_slope_window_index)
        _assert(
            str(getattr(tie_slope_focus, "Name", "") or "") == str(getattr(tie_slope_preview, "Name", "") or ""),
            "Double-click/focus on the Intersection Tie Slope window row should focus the generated surface preview.",
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
        topology_rows = [row for row in contract_rows if row.get("contract_family") == "topology"]
        boundary_loop_rows = [row for row in contract_rows if row.get("contract_family") == "boundary_loop"]
        _assert(topology_rows, "Intersections tab should expose the topology row.")
        topology_notes = str(topology_rows[0].get("notes", "") or "")
        for token in ("kind=", "legs=", "corners=", "curb_return_arcs=", "leg_graph=", "corner_graph="):
            _assert(
                token in topology_notes,
                f"Intersections tab topology row should include {token}: {topology_notes}",
            )
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
        for token in ("kind=", "surface_boundary_mode=", "surface_boundary_loop="):
            _assert(
                token in ready_boundary_notes,
                f"Boundary loop row notes should include {token}: {ready_boundary_notes}",
            )
        _assert(
            _note_int(ready_boundary_notes, "points") >= 8 and _note_int(ready_boundary_notes, "segments") >= 8,
            "T preset boundary loop should expose a non-trivial source perimeter, not a simple bbox or convex hull.",
        )
        _assert(
            "convex_hull_fallback" not in ready_boundary_notes and "not_accepted_from_convex_hull" not in ready_boundary_notes,
            "T preset boundary loop should not be accepted from convex-hull fallback.",
        )
        boundary_loop_index = next(index for index, row in enumerate(contract_rows) if row.get("contract_family") == "boundary_loop")
        boundary_focus = focus_corridor_intersection_contract_review_row(doc, boundary_loop_index)
        _assert(
            str(getattr(boundary_focus, "Name", "") or "") == "V1CorridorIntersectionSurfacePreview",
            "Boundary loop focus should use the built Intersection Surface preview, not create detached raw-loop geometry.",
        )
        _assert(
            doc.getObject("ReviewIntersectionContractHighlight") is None,
            "Boundary loop focus should not create a separate contract highlight object away from the intersection.",
        )
        _assert(
            str(getattr(boundary_focus, "PatchBoundarySource", "") or "") == "authoritative_boundary_loop",
            "Boundary loop focus should land on the preview that consumed the authoritative boundary loop.",
        )
        boundary_bbox = _shape_bbox_xy(boundary_focus)
        _assert(
            boundary_bbox is not None
            and float(boundary_bbox["xmin"]) <= 0.0 <= float(boundary_bbox["xmax"])
            and float(boundary_bbox["ymin"]) <= 0.0 <= float(boundary_bbox["ymax"]),
            f"Boundary loop focus should show the accepted outer loop around the intersection anchor: {boundary_bbox}.",
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
        cell_focus = focus_corridor_intersection_contract_review_row(doc, first_cell_index, include_internal=True)
        _assert(
            str(getattr(cell_focus, "Name", "") or "") == "V1CorridorIntersectionSlopeFaceSurfacePreview",
            "Internal slope_face_cell focus should select the generated Intersection Slope Face Surface preview.",
        )
        _assert(
            doc.getObject("ReviewIntersectionContractHighlight") is None,
            "Internal slope_face_cell rows should not create legacy contract highlight geometry.",
        )
        first_graph_edge_index = next(
            index
            for index, row in enumerate(internal_contract_rows)
            if row.get("contract_family") == "shared_boundary_graph" and str(row.get("role", "") or "").startswith("edge:")
        )
        graph_edge_focus = focus_corridor_intersection_contract_review_row(doc, first_graph_edge_index, include_internal=True)
        _assert(
            str(getattr(graph_edge_focus, "Name", "") or "") == "ReviewIntersectionContractHighlight"
            and str(getattr(graph_edge_focus, "HighlightGeometrySource", "") or "") == "intersection_shared_boundary_graph_result"
            and int(getattr(graph_edge_focus, "HighlightedShapeCount", 0) or 0) > 0,
            "Internal shared_boundary_graph edge focus should create a local result-contract highlight.",
        )
        _assert(
            str(getattr(graph_edge_focus, "ContractFamily", "") or "") == "shared_boundary_graph",
            "Internal shared_boundary_graph edge focus should preserve its result-contract family.",
        )
        first_graph_cell_index = next(
            index
            for index, row in enumerate(internal_contract_rows)
            if row.get("contract_family") == "shared_boundary_graph" and str(row.get("role", "") or "").startswith("cell:")
        )
        graph_cell_focus = focus_corridor_intersection_contract_review_row(doc, first_graph_cell_index, include_internal=True)
        _assert(
            str(getattr(graph_cell_focus, "Name", "") or "") == "ReviewIntersectionContractHighlight"
            and str(getattr(graph_cell_focus, "HighlightGeometrySource", "") or "") == "intersection_shared_boundary_graph_result"
            and int(getattr(graph_cell_focus, "HighlightedShapeCount", 0) or 0) > 0,
            "Internal shared_boundary_graph cell focus should create a local result-contract highlight.",
        )
        _assert(
            str(getattr(graph_cell_focus, "ContractFamily", "") or "") == "shared_boundary_graph",
            "Internal shared_boundary_graph cell focus should preserve its result-contract family.",
        )
        _assert(
            int(getattr(slope_face_preview, "TriangleCount", 0) or 0)
            == int(getattr(slope_face_preview, "CurbReturnSlopeFacePerimeterTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionSlopeFaceBoundaryStripTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphSurfaceTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionBoundaryLoopTransitionTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelTriangleCount", 0) or 0)
            + int(getattr(slope_face_preview, "IntersectionSlopeFaceCellTriangleCount", 0) or 0),
            "Dedicated Intersection Slope Face Surface should be composed from explicit perimeter, boundary-loop transition, upper-panel, boundary-strip, graph-cell, and cell triangles in this preset.",
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
