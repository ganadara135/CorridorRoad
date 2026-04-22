# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan typical advanced-parameter runtime override smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_typical_advanced_runtime.py', encoding='utf-8').read())"
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


def _rightmost_point(payload):
    polylines = list(payload.get("section_polylines", []) or [])
    pts = []
    for poly in polylines:
        pts.extend(list(poly or []))
    if not pts:
        return None
    return max(pts, key=lambda pt: float(pt[0]))


def run():
    doc = App.newDocument("CRCrossSectionEditPlanTypicalAdvancedRuntime")

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
    typ.ComponentIds = ["LANE-L", "LANE-R", "BERM-R"]
    typ.ComponentTypes = ["lane", "lane", "berm"]
    typ.ComponentShapes = ["", "", ""]
    typ.ComponentSides = ["left", "right", "right"]
    typ.ComponentWidths = [3.5, 3.5, 1.5]
    typ.ComponentCrossSlopes = [2.0, 2.0, 0.0]
    typ.ComponentHeights = [0.0, 0.0, 0.0]
    typ.ComponentExtraWidths = [0.0, 0.0, 0.8]
    typ.ComponentBackSlopes = [0.0, 0.0, 6.0]
    typ.ComponentOffsets = [0.0, 0.0, 0.0]
    typ.ComponentOrders = [10, 10, 20]
    typ.ComponentEnabled = [1, 1, 1]

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_TYP_HEIGHT_L",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 40.0,
                "EndStation": 60.0,
                "TargetId": "LANE-L",
                "TargetSide": "left",
                "TargetType": "lane",
                "Parameter": "height",
                "Value": 0.2,
                "Unit": "m",
                "SourceScope": "typical",
            },
            {
                "Id": "EDIT_TYP_EXTRA_R",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 40.0,
                "EndStation": 60.0,
                "TargetId": "BERM-R",
                "TargetSide": "right",
                "TargetType": "berm",
                "Parameter": "extra_width",
                "Value": 1.5,
                "Unit": "m",
                "SourceScope": "typical",
            },
            {
                "Id": "EDIT_TYP_BACK_R",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 40.0,
                "EndStation": 60.0,
                "TargetId": "BERM-R",
                "TargetSide": "right",
                "TargetType": "berm",
                "Parameter": "back_slope_pct",
                "Value": 12.0,
                "Unit": "pct",
                "SourceScope": "typical",
            },
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
    berm_20 = _find_component(payload_20.get("component_rows", []), "BERM-R", "right")
    berm_50 = _find_component(payload_50.get("component_rows", []), "BERM-R", "right")

    _assert(lane_20 and lane_50 and berm_20 and berm_50, "Advanced typical runtime smoke requires LANE-L and BERM-R rows")
    _assert(abs(float(lane_20.get("height", 0.0) or 0.0) - 0.0) < 1.0e-6, "Base station lane height should remain 0.0 m")
    _assert(abs(float(lane_50.get("height", 0.0) or 0.0) - 0.2) < 1.0e-6, "Edited station lane height should be 0.2 m")
    _assert(abs(float(berm_20.get("extraWidth", 0.0) or 0.0) - 0.8) < 1.0e-6, "Base station berm extra width should remain 0.8 m")
    _assert(abs(float(berm_50.get("extraWidth", 0.0) or 0.0) - 1.5) < 1.0e-6, "Edited station berm extra width should be 1.5 m")
    _assert(abs(float(berm_50.get("backSlopePct", 0.0) or 0.0) - 12.0) < 1.0e-6, "Edited station berm back slope should be 12.0%")
    _assert(str(lane_50.get("source", "") or "") == "cross_section_edit", "Edited lane row should report cross_section_edit source")
    _assert(str(berm_50.get("source", "") or "") == "cross_section_edit", "Edited berm row should report cross_section_edit source")

    y20 = _leftmost_y(payload_20)
    y50 = _leftmost_y(payload_50)
    _assert(y20 is not None and y50 is not None, "Section payload should expose left-side section coordinates")
    _assert(abs(y50 - y20) > 1.0e-3, f"Lane height edit should move the left-side section geometry: y20={y20}, y50={y50}")

    right_20 = _rightmost_point(payload_20)
    right_50 = _rightmost_point(payload_50)
    _assert(right_20 is not None and right_50 is not None, "Section payload should expose right-side section coordinates")
    _assert(abs(float(right_50[0]) - float(right_20[0])) > 1.0e-3 or abs(float(right_50[1]) - float(right_20[1])) > 1.0e-3, f"Berm advanced edits should move the right-side geometry: {right_20} vs {right_50}")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan typical advanced-parameter runtime override smoke test completed.")


if __name__ == "__main__":
    run()
