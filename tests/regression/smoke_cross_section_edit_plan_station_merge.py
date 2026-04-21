# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan station merge smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_station_merge.py', encoding='utf-8').read())"
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


def _assert_station_values(actual, expected, msg):
    got = [round(float(v), 3) for v in list(actual or [])]
    want = [round(float(v), 3) for v in list(expected or [])]
    _assert(got == want, f"{msg}: got={got}, want={want}")


def run():
    doc = App.newDocument("CRCrossSectionEditPlanStationMerge")

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

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_RANGE_001",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 35.0,
                "EndStation": 55.0,
                "TransitionIn": 5.0,
                "TransitionOut": 3.0,
                "TargetId": "L10",
                "TargetSide": "left",
                "TargetType": "side_slope",
                "Parameter": "width",
                "Value": 7.0,
                "Unit": "m",
                "SourceScope": "side_slope",
            },
            {
                "Id": "EDIT_STATION_001",
                "Enabled": True,
                "Scope": "station",
                "StartStation": 90.0,
                "EndStation": 90.0,
                "TransitionIn": 2.0,
                "TransitionOut": 4.0,
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
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 100.0
    sec.Interval = 20.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.UseStructureSet = False
    sec.UseRegionPlan = False
    sec.CrossSectionEditPlan = plan
    sec.UseCrossSectionEditPlan = True
    sec.CreateChildSections = False

    doc.recompute()

    expected_stations = [0.0, 20.0, 30.0, 35.0, 40.0, 55.0, 58.0, 60.0, 80.0, 88.0, 90.0, 94.0, 100.0]
    _assert_station_values(sec.StationValues, expected_stations, "CrossSectionEditPlan merged station values mismatch")
    _assert(int(getattr(sec, "ResolvedCrossSectionEditCount", 0) or 0) == 2, "Resolved edit-plan count mismatch")
    _assert("editPlan=2" in str(getattr(sec, "Status", "") or ""), "SectionSet status missing editPlan count")
    summary = list(getattr(sec, "ResolvedCrossSectionEditSummaryRows", []) or [])
    _assert(any("edits=2" in row and "boundaries=7" in row for row in summary), f"Edit-plan summary mismatch: {summary}")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan station merge smoke test completed.")


if __name__ == "__main__":
    run()
