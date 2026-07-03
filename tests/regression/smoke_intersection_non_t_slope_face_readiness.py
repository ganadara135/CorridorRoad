# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Non-T intersection Slope Face Surface readiness smoke test.

This smoke intentionally does not claim non-T dedicated Intersection Slope Face
Surface completion.  It keeps the broader preset limitation traceable while
ensuring Cross, Skewed, and Y starter presets do not regress into build errors
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
    corridor_intersection_contract_review_rows,
    create_corridor_daylight_surface_preview,
    create_corridor_intersection_surface_preview,
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
    "Skewed Intersection - Basic",
    "Y Intersection - Basic",
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
        review_rows = corridor_build_review_rows(doc)
        contract_rows = corridor_intersection_contract_review_rows(doc)
        slope_rows = [row for row in review_rows if row["role"] == "intersection_slope"]
        boundary_loop_rows = [row for row in contract_rows if row.get("contract_family") == "boundary_loop"]

        _assert(len(applied.sections) > 0, f"{preset_label} should build Applied Sections.")
        _assert(intersection_preview is not None, f"{preset_label} should create an Intersection Surface preview.")
        _assert(daylight_preview is not None, f"{preset_label} should create an ordinary Slope Face Surface preview.")
        _assert(slope_rows, f"{preset_label} should expose the Intersection Slope Face Surface Results row.")
        _assert(boundary_loop_rows, f"{preset_label} should expose an authoritative boundary_loop row.")
        _assert(
            any(row.get("status") == "ready" and row.get("role") == "outer_intersection_boundary" for row in boundary_loop_rows),
            f"{preset_label} should expose a ready outer_intersection_boundary row.",
        )
        _assert(
            any("closed=yes" in str(row.get("notes", "") or "") for row in boundary_loop_rows),
            f"{preset_label} boundary loop row should report a closed perimeter.",
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
        return "ready"
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


def run():
    outcomes = {}
    for preset_label in NON_T_PRESETS:
        outcomes[preset_label] = _run_one_preset(preset_label)
    print("[PASS] Non-T intersection slope-face readiness smoke completed: " + str(outcomes))


if __name__ == "__main__":
    run()
