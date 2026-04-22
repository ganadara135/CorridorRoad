# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan typical cross-slope runtime override smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_typical_slope_runtime.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _find_component(rows, target_id, side):
    target_id = str(target_id or "").strip().upper()
    side = str(side or "").strip().lower()
    for row in list(rows or []):
        if str(row.get("id", "") or "").strip().upper() != target_id:
            continue
        if str(row.get("side", "") or "").strip().lower() != side:
            continue
        return dict(row or {})
    return {}


def _leftmost_y(payload):
    polylines = list(payload.get("section_polylines", []) or [])
    pts = []
    for poly in polylines:
        pts.extend(list(poly or []))
    if not pts:
        return None
    leftmost = min(pts, key=lambda pt: float(pt[0]))
    return float(leftmost[1])


def run():
    doc = App.newDocument("CRCrossSectionEditPlanTypicalSlopeRuntime")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False

    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False

    typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
    TypicalSectionTemplate(typ)

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_TYP_SLOPE_L",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 40.0,
                "EndStation": 60.0,
                "TargetId": "LANE-L",
                "TargetSide": "left",
                "TargetType": "lane",
                "Parameter": "cross_slope_pct",
                "Value": 4.0,
                "Unit": "pct",
                "SourceScope": "typical",
            }
        ],
    )

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.TypicalSectionTemplate = typ
    sec.UseTypicalSectionTemplate = True
    sec.Mode = "Manual"
    sec.StationText = "20, 50, 80"
    sec.DaylightAuto = False
    sec.UseCrossSectionEditPlan = True
    sec.CrossSectionEditPlan = plan
    sec.CreateChildSections = False

    doc.recompute()

    payload_20 = SectionSet.resolve_viewer_payload(sec, station=20.0, include_structure_overlay=False)
    payload_50 = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
    lane_20 = _find_component(payload_20.get("component_rows", []), "LANE-L", "left")
    lane_50 = _find_component(payload_50.get("component_rows", []), "LANE-L", "left")

    _assert(lane_20 and lane_50, "Typical slope smoke requires LANE-L rows")
    _assert(abs(float(lane_20.get("slope", 0.0) or 0.0) - 2.0) < 1.0e-6, "Base station lane slope should remain 2.0%")
    _assert(abs(float(lane_50.get("slope", 0.0) or 0.0) - 4.0) < 1.0e-6, "Edited station lane slope should be 4.0%")
    _assert(str(lane_50.get("source", "") or "") == "cross_section_edit", "Edited typical slope row should report cross_section_edit source")
    _assert("EDIT_TYP_SLOPE_L" in str(lane_50.get("editId", "") or ""), "Edited typical slope row should expose edit id")

    y20 = _leftmost_y(payload_20)
    y50 = _leftmost_y(payload_50)
    _assert(y20 is not None and y50 is not None, "Section payload should expose local section polyline coordinates")
    _assert(y50 < y20 - 1.0e-3, f"Edited station should have steeper left falloff: y20={y20}, y50={y50}")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan typical cross-slope runtime override smoke test completed.")


if __name__ == "__main__":
    run()
