# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan repeat-bench width contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_repeat_bench_width_contract.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _shape_ok(obj) -> bool:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False


def _station_profile(bench_info, station: float, tol: float = 1.0e-6):
    for row in list((bench_info or {}).get("stationProfiles", []) or []):
        if abs(float(row.get("station", 0.0) or 0.0) - float(station)) <= tol:
            return dict(row or {})
    return {}


def _segment_sum(profile_row, side: str):
    segs = list(dict(profile_row or {}).get(f"{side}_segments", []) or [])
    return sum(max(0.0, float(seg.get("width", 0.0) or 0.0)) for seg in segs)


def run():
    doc = App.newDocument("CRRepeatBenchWidthContract")

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
    asm.LeftSideWidth = 8.0
    asm.RightSideWidth = 8.0
    asm.LeftSideSlopePct = -33.0
    asm.RightSideSlopePct = 33.0
    asm.UseLeftBench = True
    asm.LeftBenchDrop = 0.8
    asm.LeftBenchWidth = 1.2
    asm.LeftBenchSlopePct = 0.0
    asm.LeftPostBenchSlopePct = -40.0
    asm.LeftBenchRepeatToDaylight = True
    asm.UseRightBench = True
    asm.RightBenchDrop = 0.8
    asm.RightBenchWidth = 1.2
    asm.RightBenchSlopePct = 0.0
    asm.RightPostBenchSlopePct = 40.0
    asm.RightBenchRepeatToDaylight = True

    typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
    TypicalSectionTemplate(typ)

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_REPEAT_BENCH_WIDTH",
                "Enabled": True,
                "Scope": "station",
                "StartStation": 50.0,
                "EndStation": 50.0,
                "TargetId": "L10",
                "TargetSide": "left",
                "TargetType": "side_slope",
                "Parameter": "width",
                "Value": 10.0,
                "Unit": "m",
                "SourceScope": "side_slope",
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

    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    cor.SourceSectionSet = sec

    doc.recompute()

    profiles, _rows, point_count = SectionSet.resolve_section_profiles(sec)
    counts = [len(list(profile.get("points", []) or [])) for profile in profiles]
    _assert(len(counts) == 3, f"Expected 3 section profiles, got {counts}")
    _assert(len(set(counts)) == 1, f"Repeat-bench width override should keep a stable point count: {counts}")
    _assert(int(point_count) == counts[0], "Section profile point-count summary mismatch")
    _assert(_shape_ok(cor), "Corridor should build after repeat-bench width override")
    _assert(str(getattr(cor, "ConnectivityDiagnostic", "-") or "-") == "ok|clean", "Corridor connectivity should stay clean")

    _stations, _wires, _terrain_found, _sampler_ok, bench_info = SectionSet.build_section_wires(sec)
    row_20 = _station_profile(bench_info, 20.0)
    row_50 = _station_profile(bench_info, 50.0)
    _assert(_segment_sum(row_20, "left") < _segment_sum(row_50, "left"), "Edited station should widen the left repeat-bench profile")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan repeat-bench width contract smoke test completed.")


if __name__ == "__main__":
    run()
