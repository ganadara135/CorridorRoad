# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan repeat-bench slope contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_repeat_bench_slope_contract.py', encoding='utf-8').read())"
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


def _leftmost_point(payload):
    polylines = list(payload.get("section_polylines", []) or [])
    pts = []
    for poly in polylines:
        pts.extend(list(poly or []))
    if not pts:
        return None
    return min(pts, key=lambda pt: float(pt[0]))


def run():
    doc = App.newDocument("CRRepeatBenchSlopeContract")

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
                "Id": "EDIT_REPEAT_BENCH_SLOPE",
                "Enabled": True,
                "Scope": "station",
                "StartStation": 50.0,
                "EndStation": 50.0,
                "TargetId": "L10",
                "TargetSide": "left",
                "TargetType": "side_slope",
                "Parameter": "slope_pct",
                "Value": 5.0,
                "Unit": "pct",
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
    _assert(len(set(counts)) == 1, f"Repeat-bench slope override should keep a stable point count: {counts}")
    _assert(int(point_count) == counts[0], "Section profile point-count summary mismatch")
    _assert(_shape_ok(cor), "Corridor should build after repeat-bench slope override")
    _assert(str(getattr(cor, "ConnectivityDiagnostic", "-") or "-") == "ok|clean", "Corridor connectivity should stay clean")

    _stations, _wires, _terrain_found, _sampler_ok, bench_info = SectionSet.build_section_wires(sec)
    row_50 = _station_profile(bench_info, 50.0)
    left_segments = list(row_50.get("left_segments", []) or [])
    left_slopes = [float(seg.get("slope", 0.0) or 0.0) for seg in left_segments if str(seg.get("kind", "") or "") == "slope"]
    _assert(left_slopes, "Edited station should expose left slope segments")
    _assert(any(abs(val - 5.0) < 1.0e-6 for val in left_slopes), f"Edited station should retain the 5.0% slope override: {left_slopes}")

    payload_20 = SectionSet.resolve_viewer_payload(sec, station=20.0, include_structure_overlay=False)
    payload_50 = SectionSet.resolve_viewer_payload(sec, station=50.0, include_structure_overlay=False)
    left_20 = _leftmost_point(payload_20)
    left_50 = _leftmost_point(payload_50)
    _assert(left_20 is not None and left_50 is not None, "Viewer payload should expose section polylines")
    _assert(abs(float(left_20[1]) - float(left_50[1])) > 1.0e-3, f"Edited station left-side geometry should visibly change: {left_20} vs {left_50}")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan repeat-bench slope contract smoke test completed.")


if __name__ == "__main__":
    run()
