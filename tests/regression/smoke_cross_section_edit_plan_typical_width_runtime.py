# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan typical-width runtime override smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_typical_width_runtime.py', encoding='utf-8').read())"
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


def run():
    doc = App.newDocument("CRCrossSectionEditPlanTypicalWidthRuntime")

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
                "Id": "EDIT_TYP_LANE_L",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 40.0,
                "EndStation": 60.0,
                "TransitionIn": 0.0,
                "TransitionOut": 0.0,
                "TargetId": "LANE-L",
                "TargetSide": "left",
                "TargetType": "lane",
                "Parameter": "width",
                "Value": 4.0,
                "Unit": "m",
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

    stations, _wires, _terrain_found, _sampler_ok, _bench_info = SectionSet.build_section_wires(sec)
    got = [round(float(v), 3) for v in list(stations or [])]
    _assert(got == [20.0, 40.0, 50.0, 60.0, 80.0], f"Station values mismatch: {got}")

    payload_20 = SectionSet.resolve_viewer_payload(sec, station=20.0, include_structure_overlay=False)
    payload_50 = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
    lane_20 = _find_component(payload_20.get("component_rows", []), "LANE-L", "left")
    lane_50 = _find_component(payload_50.get("component_rows", []), "LANE-L", "left")

    _assert(lane_20, "Base station should expose LANE-L component row")
    _assert(lane_50, "Edited station should expose LANE-L component row")
    _assert(abs(float(lane_20.get("width", 0.0) or 0.0) - 3.5) < 1.0e-6, "Base station lane width should remain 3.5 m")
    _assert(abs(float(lane_50.get("width", 0.0) or 0.0) - 4.0) < 1.0e-6, "Edited station lane width should be 4.0 m")
    _assert(str(lane_20.get("source", "") or "") == "typical_summary", "Base station lane should keep typical_summary source")
    _assert(str(lane_50.get("source", "") or "") == "cross_section_edit", "Edited station lane should report cross_section_edit source")
    _assert("EDIT_TYP_LANE_L" in str(lane_50.get("editId", "") or ""), "Edited station lane should expose edit id")

    _assert(int(getattr(sec, "CrossSectionEditOverrideHitCount", 0) or 0) >= 2, "Typical-width override should contribute active edit hits")
    status = str(getattr(sec, "Status", "") or "")
    _assert("editPlan=1" in status, "SectionSet status missing editPlan count")
    _assert("editPlanActive=" in status, "SectionSet status missing active edit-plan count")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan typical-width runtime override smoke test completed.")


if __name__ == "__main__":
    run()
