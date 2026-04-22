# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan runtime override smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_runtime_override.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _find_station_profile(bench_info, station: float, tol: float = 1e-6):
    for row in list((bench_info or {}).get("stationProfiles", []) or []):
        if abs(float(row.get("station", 0.0) or 0.0) - float(station)) <= tol:
            return dict(row)
    return {}


def _segment_sum(profile_row, side: str):
    segs = list(dict(profile_row or {}).get(f"{side}_segments", []) or [])
    return sum(max(0.0, float(seg.get("width", 0.0) or 0.0)) for seg in segs)


def run():
    doc = App.newDocument("CRCrossSectionEditPlanRuntime")

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
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 6.0
    asm.RightSideWidth = 6.0
    asm.LeftSideSlopePct = 30.0
    asm.RightSideSlopePct = 30.0
    asm.UseLeftBench = False
    asm.UseRightBench = False

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_RANGE_WIDTH",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 40.0,
                "EndStation": 60.0,
                "TargetId": "L10",
                "TargetSide": "left",
                "TargetType": "side_slope",
                "Parameter": "width",
                "Value": 8.0,
                "Unit": "m",
                "SourceScope": "side_slope",
            },
            {
                "Id": "EDIT_STATION_SLOPE",
                "Enabled": True,
                "Scope": "station",
                "StartStation": 80.0,
                "EndStation": 80.0,
                "TargetId": "R10",
                "TargetSide": "right",
                "TargetType": "side_slope",
                "Parameter": "slope_pct",
                "Value": 45.0,
                "Unit": "pct",
                "SourceScope": "side_slope",
            },
        ],
    )

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Manual"
    sec.StationText = "20, 50, 80"
    sec.DaylightAuto = False
    sec.UseCrossSectionEditPlan = True
    sec.CrossSectionEditPlan = plan
    sec.CreateChildSections = False

    doc.recompute()

    stations, _wires, _terrain_found, _sampler_ok, bench_info = SectionSet.build_section_wires(sec)
    got = [round(float(v), 3) for v in list(stations or [])]
    _assert(got == [20.0, 40.0, 50.0, 60.0, 80.0], f"Station values mismatch: {got}")

    profile_20 = _find_station_profile(bench_info, 20.0)
    profile_50 = _find_station_profile(bench_info, 50.0)
    profile_80 = _find_station_profile(bench_info, 80.0)
    _assert(abs(_segment_sum(profile_20, "left") - 6.0) < 1e-6, "Baseline left width at 20.0 should remain 6.0")
    _assert(abs(_segment_sum(profile_50, "left") - 8.0) < 1e-6, "Edit-plan left width at 50.0 should be overridden to 8.0")
    right_80 = list(profile_80.get("right_segments", []) or [])
    _assert(len(right_80) >= 1 and abs(float(right_80[0].get("slope", 0.0) or 0.0) - 45.0) < 1e-6, "Right slope at 80.0 should be overridden to 45.0")

    payload = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
    comp_rows = list(payload.get("component_rows", []) or [])
    edited = [row for row in comp_rows if str(row.get("side", "") or "") == "left" and str(row.get("source", "") or "") == "cross_section_edit"]
    _assert(len(edited) >= 1, "Viewer payload should expose cross_section_edit source rows at edited station")
    _assert(any("EDIT_RANGE_WIDTH" in str(row.get("editId", "") or "") for row in edited), "Viewer payload editId missing for edited row")

    _assert(int(getattr(sec, "CrossSectionEditOverrideHitCount", 0) or 0) >= 2, "CrossSectionEditOverrideHitCount should report active runtime overrides")
    status = str(getattr(sec, "Status", "") or "")
    _assert("editPlan=2" in status, "SectionSet status missing editPlan count")
    _assert("editPlanActive=" in status, "SectionSet status missing active edit-plan count")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan runtime override smoke test completed.")


if __name__ == "__main__":
    run()
