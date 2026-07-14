# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Non-T intersection Slope Face Surface readiness smoke test.

This smoke intentionally does not claim non-T dedicated Intersection Slope Face
Surface completion.  It keeps the broader preset limitation traceable while
ensuring the remaining non-T starter presets do not regress into build errors
or misleading ready states.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_intersection_non_t_slope_face_readiness.py', 'r', encoding='utf-8').read())"
"""

from dataclasses import replace

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    build_document_corridor_model,
    build_document_corridor_surface_model,
    corridor_build_review_rows,
    corridor_shared_breakline_audit_rows,
    corridor_intersection_patch_prerequisite_result,
    corridor_intersection_contract_review_rows,
    corridor_intersection_shared_breakline_result,
    create_corridor_daylight_surface_preview,
    create_corridor_intersection_surface_preview,
    _intersection_tie_slope_applied_section_window_rows,
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


NON_T_PRESETS = (
    "Cross Intersection - Basic",
    "Roundabout - Single Lane",
)


def _assert(condition, message):
    if not condition:
        raise Exception(message)


def _accept_preset_prerequisites(doc):
    """Accept review-required starter rows so the smoke reaches result readiness."""

    obj = find_v1_intersection_model(doc)
    model = to_intersection_model(obj)
    _assert(obj is not None and model is not None, "Preset did not create an IntersectionModel.")

    intersection_rows = []
    for intersection in list(model.intersection_rows or []):
        accepted_legs = []
        for leg in list(intersection.leg_rows or []):
            start = float(leg.approach_station_start or 96.0)
            end = float(leg.approach_station_end or max(start + 24.0, 120.0))
            accepted_legs.append(
                replace(
                    leg,
                    approval_status="accepted",
                    span_source="explicit",
                    approach_station_start=start,
                    approach_station_end=end,
                    profile_ref=str(leg.profile_ref or f"profile:{leg.alignment_ref or leg.leg_id}"),
                    centerline3d_ref=str(leg.centerline3d_ref or f"centerline3d:{leg.alignment_ref or leg.leg_id}"),
                    diagnostic_rows=[],
                )
            )
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
        replace(row, approval_status="accepted", source_method="subassembly_derived", diagnostic_rows=[])
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


def _run_one_preset(preset_label):
    doc = App.newDocument("CRV1NonTIntersectionSlopeFaceReadiness")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label=preset_label,
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
        _accept_preset_prerequisites(doc)
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
        daylight_preview = create_corridor_daylight_surface_preview(
            document=doc,
            project=project,
            corridor_model=corridor_model,
            surface_model=surface_model,
        )
        slope_face_preview = doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
        tie_slope_preview = doc.getObject("V1CorridorIntersectionTieSlopeSurfacePreview")
        review_rows = corridor_build_review_rows(doc)
        contract_rows = corridor_intersection_contract_review_rows(doc)
        slope_rows = [row for row in review_rows if row["role"] == "intersection_slope"]
        topology_rows = [row for row in contract_rows if row.get("contract_family") == "topology"]
        boundary_loop_rows = [row for row in contract_rows if row.get("contract_family") == "boundary_loop"]

        _assert(len(applied.sections) > 0, f"{preset_label} should build Applied Sections.")
        _assert(intersection_preview is not None, f"{preset_label} should create an Intersection Surface preview.")
        if preset_label == "Cross Intersection - Basic":
            _assert(
                str(getattr(intersection_preview, "PatchBoundarySource", "") or "") == "authoritative_boundary_loop",
                (
                    "Cross Intersection Surface should consume the authoritative curb-return boundary loop; "
                    f"source={getattr(intersection_preview, 'PatchBoundarySource', '')!r}."
                ),
            )
            _assert(
                str(getattr(intersection_preview, "PatchSurfaceBoundaryStrategy", "") or "") == "ordered_polygon",
                (
                    "Cross Intersection Surface should triangulate from the authoritative outer loop, "
                    f"not the rectangular structured strip; strategy={getattr(intersection_preview, 'PatchSurfaceBoundaryStrategy', '')!r}."
                ),
            )
            intersection_model = to_intersection_model(find_v1_intersection_model(doc))
            prerequisite = corridor_intersection_patch_prerequisite_result(doc)
            tie_slope_rows = _intersection_tie_slope_applied_section_window_rows(
                applied,
                prerequisite=prerequisite,
                intersection_model=intersection_model,
            )
            _assert(
                any(str(row.get("cell_role", "") or "") == "curb_return_approach_pair" for row in tie_slope_rows),
                "Cross Intersection should create curb_return_approach_pair Tie Slope rows.",
            )
            accepted_approach_rows = [
                row for row in tie_slope_rows
                if str(row.get("cell_role", "") or "") == "curb_return_approach_pair"
                and str(row.get("status", "") or "") == "accepted"
            ]
            _assert(
                accepted_approach_rows
                and all(str(row.get("ownership_class", "") or "") == "tie_slope_candidate" for row in accepted_approach_rows),
                (
                    "Accepted Cross curb-return approach windows should be owned by Intersection Tie Slope; "
                    f"rows={accepted_approach_rows}."
                ),
            )
            _assert(
                all(str(row.get("outer_edge_source_mode", "") or "") == "legacy_slope_breakline" for row in accepted_approach_rows)
                and all(str(row.get("inner_edge_source_mode", "") or "") == "legacy_slope_breakline" for row in accepted_approach_rows),
                (
                    "Cross Intersection Tie Slope should remain on the restored legacy window edge path; "
                    f"rows={accepted_approach_rows}."
                ),
            )
            _assert(
                not [
                    row for row in contract_rows
                    if row.get("contract_family") == "intersection_tie_slope_target_edge"
                ],
                "Cross Intersection contracts should not expose the removed temporary Tie Slope target edge row.",
            )
            secondary_approach_groups = {
                (
                    str(row.get("gap_role", "") or ""),
                    str(row.get("side", "") or ""),
                )
                for row in tie_slope_rows
                if str(row.get("cell_role", "") or "") == "curb_return_approach_pair"
                and str(row.get("road_role", "") or "") == "secondary"
                and str(row.get("status", "") or "") == "accepted"
            }
            primary_approach_groups = {
                (
                    str(row.get("gap_role", "") or ""),
                    str(row.get("side", "") or ""),
                )
                for row in tie_slope_rows
                if str(row.get("cell_role", "") or "") == "curb_return_approach_pair"
                and str(row.get("road_role", "") or "") == "primary"
                and str(row.get("status", "") or "") == "accepted"
            }
            _assert(
                {("entry", "left"), ("entry", "right"), ("exit", "left"), ("exit", "right")}.issubset(primary_approach_groups),
                (
                    "Cross primary road should generate Tie Slope on entry/exit and both sides; "
                    f"groups={sorted(primary_approach_groups)}."
                ),
            )
            _assert(
                {("entry", "left"), ("entry", "right"), ("exit", "left"), ("exit", "right")}.issubset(secondary_approach_groups),
                (
                    "Cross secondary road should mirror primary Tie Slope generation on entry/exit and both sides; "
                    f"groups={sorted(secondary_approach_groups)}."
                ),
            )
            supplemental_endpoint_rows = [
                row for row in tie_slope_rows
                if str(row.get("supplemental_extent_role", "") or "") == "supplemental_endpoint_pair"
            ]
            supplemental_pair_rows = [
                row for row in tie_slope_rows
                if str(row.get("supplemental_extent_role", "") or "") == "intersection_supplemental_pair"
            ]
            _assert(
                supplemental_endpoint_rows,
                "Cross Intersection Tie Slope rows should expose selected supplemental endpoint candidate rows.",
            )
            _assert(
                supplemental_pair_rows,
                "Cross Intersection Tie Slope should expose intermediate supplemental Applied Section pair rows.",
            )
            endpoint_groups_by_road = {
                str(row.get("road_role", "") or ""): {
                    (
                        str(candidate.get("gap_role", "") or ""),
                        str(candidate.get("side", "") or ""),
                    )
                    for candidate in supplemental_endpoint_rows
                    if str(candidate.get("road_role", "") or "") == str(row.get("road_role", "") or "")
                    and str(candidate.get("status", "") or "") == "accepted"
                }
                for row in supplemental_endpoint_rows
            }
            expected_endpoint_groups = {("entry", "left"), ("entry", "right"), ("exit", "left"), ("exit", "right")}
            for road_role in ("primary", "secondary"):
                _assert(
                    expected_endpoint_groups.issubset(endpoint_groups_by_road.get(road_role, set())),
                    (
                        f"Cross {road_role} Tie Slope should reach supplemental endpoints on entry/exit and both sides; "
                        f"groups={sorted(endpoint_groups_by_road.get(road_role, set()))}."
                    ),
                )
            _assert(
                all(str(row.get("supplemental_endpoint_ref", "") or "") for row in supplemental_endpoint_rows),
                (
                    "Cross Intersection Tie Slope endpoint rows should record selected supplemental endpoint refs; "
                    f"rows={supplemental_endpoint_rows}."
                ),
            )
            _assert(
                all(bool(row.get("inner_is_supplemental", False)) for row in supplemental_endpoint_rows),
                (
                    "Cross Intersection Tie Slope endpoint rows should stop on supplemental Applied Sections; "
                    f"rows={supplemental_endpoint_rows}."
                ),
            )
            _assert(
                any(
                    "info:intersection_tie_slope_supplemental_endpoint_selected" in ";".join(
                        str(value or "") for value in tuple(row.get("diagnostics", ()) or ())
                    )
                    for row in supplemental_endpoint_rows
                ),
                "Cross Intersection Tie Slope diagnostics should report selected supplemental endpoint sections.",
            )
            secondary_window_kinds = {
                str(row.get("transition_window_kind", "") or "")
                for row in tie_slope_rows
                if str(row.get("road_role", "") or "") == "secondary"
            }
            _assert(
                "secondary_region_start_to_intersection_start" in secondary_window_kinds
                and "secondary_intersection_end_to_region_end" in secondary_window_kinds,
                (
                    "Cross secondary road should expose entry and exit transition window kinds separately; "
                    f"kinds={sorted(secondary_window_kinds)}."
                ),
            )
            _assert(
                not any(str(row.get("cell_role", "") or "") == "intersection_adjacent_pair" for row in tie_slope_rows),
                "Cross Intersection should not restore internal intersection_adjacent_pair Tie Slope rows.",
            )
            shared_breaklines = corridor_intersection_shared_breakline_result(
                applied,
                prerequisite=prerequisite,
                intersection_model=intersection_model,
                tie_slope_window_rows=tie_slope_rows,
            )
            shared_roles = [
                str(getattr(row, "breakline_role", "") or "")
                for row in list(getattr(shared_breaklines, "breakline_rows", []) or [])
            ]
            for role in (
                "intersection_tie_slope_supplemental_outer",
                "intersection_tie_slope_supplemental_inner",
                "intersection_tie_slope_supplemental_endpoint",
                "intersection_tie_slope_supplemental_start_cap",
                "intersection_tie_slope_supplemental_end_cap",
            ):
                _assert(role in shared_roles, f"Cross Tie Slope supplemental shared breaklines should include {role}.")
            _assert(
                tie_slope_preview is not None,
                "Cross manual QA proxy should create a dedicated Intersection Tie Slope preview.",
            )
            _assert(
                str(getattr(tie_slope_preview, "IntersectionTieSlopeGeometrySource", "") or "")
                == "accepted_applied_section_window_rows",
                "Cross Tie Slope should remain sourced from accepted Applied Section window rows.",
            )
            accepted_windows = int(getattr(tie_slope_preview, "IntersectionTieSlopeAppliedSectionWindowAcceptedCount", 0) or 0)
            tie_slope_triangles = int(getattr(tie_slope_preview, "IntersectionTieSlopeTriangleCount", 0) or 0)
            supplemental_endpoint_count = int(getattr(tie_slope_preview, "IntersectionTieSlopeSupplementalEndpointCount", 0) or 0)
            supplemental_inner_count = int(getattr(tie_slope_preview, "IntersectionTieSlopeSupplementalInnerCount", 0) or 0)
            ownership_summary = str(getattr(tie_slope_preview, "IntersectionTieSlopeWindowOwnershipSummary", "") or "")
            endpoint_by_road = str(getattr(tie_slope_preview, "IntersectionTieSlopeSupplementalEndpointByRoad", "") or "")
            _assert(
                accepted_windows > 0 and tie_slope_triangles == accepted_windows * 2,
                (
                    "Cross Tie Slope should triangulate each accepted Applied Section window as two triangles; "
                    f"accepted={accepted_windows}, triangles={tie_slope_triangles}."
                ),
            )
            _assert(
                supplemental_endpoint_count > 0 and supplemental_inner_count >= supplemental_endpoint_count,
                (
                    "Cross Tie Slope surface should consume supplemental endpoint window rows; "
                    f"endpoints={supplemental_endpoint_count}, supplemental_inner={supplemental_inner_count}, "
                    f"rows={[(row.get('inner_applied_section_ref'), row.get('inner_is_supplemental'), row.get('supplemental_endpoint_ref')) for row in supplemental_endpoint_rows]}."
                ),
            )
            _assert(
                "tie_slope_candidate=" in ownership_summary,
                f"Cross Tie Slope should expose Applied Section ownership classification: {ownership_summary!r}.",
            )
            _assert(
                "primary=4" in endpoint_by_road and "secondary=4" in endpoint_by_road,
                (
                    "Cross Tie Slope should pass supplemental endpoint windows for primary and secondary roads; "
                    f"summary={endpoint_by_road!r}."
                ),
            )
        _assert(daylight_preview is not None, f"{preset_label} should create an ordinary Slope Face Surface preview.")
        _assert(slope_rows, f"{preset_label} should expose the Intersection Slope Face Surface Results row.")
        _assert(topology_rows, f"{preset_label} should expose a topology row.")
        topology_notes = str(topology_rows[0].get("notes", "") or "")
        for token in ("kind=", "legs=", "corners=", "curb_return_arcs=", "leg_graph=", "corner_graph="):
            _assert(
                token in topology_notes,
                f"{preset_label} topology row should include {token}: {topology_notes}",
            )
        _assert(boundary_loop_rows, f"{preset_label} should expose an authoritative boundary_loop row.")
        expected_boundary_role = (
            "roundabout_outer_ownership_boundary"
            if preset_label == "Roundabout - Single Lane"
            else "outer_intersection_boundary"
        )
        _assert(
            any(row.get("status") == "ready" and row.get("role") == expected_boundary_role for row in boundary_loop_rows),
            f"{preset_label} should expose a ready {expected_boundary_role} row.",
        )
        _assert(
            any("closed=yes" in str(row.get("notes", "") or "") for row in boundary_loop_rows),
            f"{preset_label} boundary loop row should report a closed perimeter.",
        )
        ready_boundary_notes = str(
            next(
                row.get("notes", "") or ""
                for row in boundary_loop_rows
                if row.get("status") == "ready" and row.get("role") == expected_boundary_role
            )
        )
        for token in ("kind=", "surface_boundary_mode=", "surface_boundary_loop="):
            _assert(
                token in ready_boundary_notes,
                f"{preset_label} boundary loop row should include {token}: {ready_boundary_notes}",
            )

        if slope_face_preview is None:
            _assert(
                slope_rows[0]["status"] in {"missing", "warning"},
                f"{preset_label} should not report dedicated Intersection Slope Face Surface ready when no object exists.",
            )
            _assert(
                "missing" in str(slope_rows[0]["status"] or "")
                or "Intersection Slope Face Surface" in str(slope_rows[0].get("object", "") or ""),
                f"{preset_label} missing dedicated surface should stay visible in Results metadata.",
            )
            return "missing"

        _assert(
            int(getattr(slope_face_preview, "TriangleCount", 0) or 0) > 0,
            f"{preset_label} dedicated Intersection Slope Face Surface exists but has no triangles.",
        )
        _assert(
            list(getattr(slope_face_preview, "SourceLoopRefs", []) or [])
            or list(getattr(slope_face_preview, "IntersectionSharedBoundaryGraphRefs", []) or []),
            f"{preset_label} dedicated Intersection Slope Face Surface should preserve source loop or graph refs.",
        )
        _assert(
            slope_rows[0]["status"] == "ready",
            f"{preset_label} Results row should be ready when the dedicated preview object exists.",
        )
        if preset_label == "Cross Intersection - Basic":
            _assert(
                str(getattr(daylight_preview, "Name", "") or "")
                not in {
                    str(getattr(tie_slope_preview, "Name", "") or ""),
                    str(getattr(slope_face_preview, "Name", "") or ""),
                },
                "Cross manual QA proxy should keep ordinary Slope Face, Intersection Slope Face, and Tie Slope as separate objects.",
            )
            audit_rows = corridor_shared_breakline_audit_rows(doc)
            _assert(audit_rows, "Cross manual QA proxy should expose Breakline Audit rows.")
            geometry_mismatch = sum(int(row.get("geometry_mismatch_count", 0) or 0) for row in audit_rows)
            mesh_mismatch = sum(int(row.get("mesh_mismatch_count", 0) or 0) for row in audit_rows)
            missing_consumer = sum(int(row.get("missing_consumer_count", 0) or 0) for row in audit_rows)
            _assert(
                geometry_mismatch == 0 and mesh_mismatch == 0 and missing_consumer == 0,
                (
                    "Cross manual QA proxy should keep shared breakline geometry, mesh, and consumer mismatch at zero; "
                    f"geometry={geometry_mismatch}, mesh={mesh_mismatch}, missing={missing_consumer}."
                ),
            )
            coverage_summary = str(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelCoverageSummary", "") or "")
            source_mode = str(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelSourceMode", "") or "")
            generation_mode = str(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelGenerationMode", "") or "")
            generated_count = int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelGeneratedCount", 0) or 0)
            triangle_count = int(getattr(slope_face_preview, "IntersectionUpperSlopeFacePanelTriangleCount", 0) or 0)
            _assert(
                "suppressed_for_intersection_kind:cross_intersection" in coverage_summary
                and source_mode == "suppressed_non_t_intersection"
                and generation_mode == "suppressed_non_t_intersection"
                and generated_count == 0
                and triangle_count == 0,
                (
                    "Cross Intersection should suppress T-oriented upper Intersection Slope Face panels; "
                    f"summary={coverage_summary!r}, source={source_mode!r}, generation={generation_mode!r}, "
                    f"generated={generated_count}, triangles={triangle_count}."
                ),
            )
        return "ready"
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


def _run_cross_preset_without_manual_acceptance():
    doc = App.newDocument("CRV1CrossIntersectionBoundaryNoAcceptance")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="Cross Intersection - Basic",
            grading_policy="blend_primary_side",
            drainage_mode="outside_gutter",
        )
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
        contract_rows = corridor_intersection_contract_review_rows(doc)
        topology_row = next(row for row in contract_rows if row.get("contract_family") == "topology")
        topology_notes = str(topology_row.get("notes", "") or "")

        _assert(intersection_preview is not None, "Cross preset should create an Intersection Surface without manual acceptance.")
        for token in ("legs=4", "corners=4", "curb_return_arcs=4"):
            _assert(token in topology_notes, f"Cross preset topology should expose {token}: {topology_notes}")
        _assert(
            str(getattr(intersection_preview, "PatchBoundarySource", "") or "") == "authoritative_boundary_loop",
            (
                "Cross preset Intersection Surface should use the source-driven curb-return envelope without "
                f"manual acceptance; source={getattr(intersection_preview, 'PatchBoundarySource', '')!r}."
            ),
        )
        _assert(
            str(getattr(intersection_preview, "IntersectionSurfaceBoundaryMode", "") or "") == "curb_return_envelope",
            (
                "Cross preset Intersection Surface should report curb_return_envelope boundary mode; "
                f"mode={getattr(intersection_preview, 'IntersectionSurfaceBoundaryMode', '')!r}."
            ),
        )
        _assert(
            int(getattr(intersection_preview, "PatchBoundaryPointCount", 0) or 0) > 8,
            "Cross preset curb-return envelope should have more than the rectangular four-point boundary.",
        )
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


def run():
    outcomes = {}
    _run_cross_preset_without_manual_acceptance()
    for preset_label in NON_T_PRESETS:
        outcomes[preset_label] = _run_one_preset(preset_label)
    print("[PASS] Non-T intersection slope-face readiness smoke completed: " + str(outcomes))


if __name__ == "__main__":
    run()
