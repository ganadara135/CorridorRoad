# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Structure-driven station merge and tagging smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_structure_station_merge.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet


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


def _find_group_section(sec, station: float, tol: float = 1e-6):
    for child in list(getattr(sec, "Group", []) or []):
        if str(getattr(child, "Name", "") or "").startswith("SectionSlice"):
            if abs(float(getattr(child, "Station", 0.0) or 0.0) - float(station)) <= tol:
                return child
    return None


def _assert_station_values(actual, expected, msg):
    got = [round(float(v), 3) for v in list(actual or [])]
    want = [round(float(v), 3) for v in list(expected or [])]
    _assert(got == want, f"{msg}: got={got}, want={want}")


def run():
    doc = App.newDocument("CRStructureStationMerge")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(50.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False

    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["OVL_A", "OVL_B", "OVL_C"]
    ss.StructureTypes = ["culvert", "bridge_zone", "retaining_wall"]
    ss.StartStations = [20.0, 28.0, 36.0]
    ss.EndStations = [30.0, 35.0, 37.0]
    ss.CenterStations = [25.0, 31.5, 36.5]
    ss.Sides = ["both", "both", "left"]
    ss.Widths = [6.0, 8.0, 3.0]
    ss.Heights = [3.0, 4.0, 2.5]
    ss.BehaviorModes = ["section_overlay", "section_overlay", "assembly_override"]
    ss.CorridorModes = ["skip_zone", "skip_zone", "split_only"]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 50.0
    sec.Interval = 20.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = True
    sec.IncludeStructureTransitionStations = True
    sec.AutoStructureTransitionDistance = False
    sec.StructureTransitionDistance = 2.0
    sec.CreateStructureTaggedChildren = True
    sec.ApplyStructureOverrides = True
    sec.CreateChildSections = True
    sec.AutoRebuildChildren = True

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    expected_stations = [
        0.0, 18.0, 20.0, 25.0, 26.0, 28.0, 30.0, 31.5, 32.0, 34.0,
        35.0, 36.0, 36.5, 37.0, 39.0, 40.0, 50.0,
    ]
    _assert_station_values(sec.StationValues, expected_stations, "Merged station values mismatch")
    _assert(int(getattr(sec, "ResolvedStructureCount", 0) or 0) == 14, "Resolved structure count mismatch")
    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert("structures=14" in str(getattr(sec, "Status", "") or ""), "SectionSet status missing structure count")

    summary_rows = list(getattr(sec, "ResolvedStructureTags", []) or [])
    _assert(any("34.000:TRANSITION [OVL_C]" in row for row in summary_rows), "Missing transition summary row for OVL_C")
    _assert(any("28.000:STR_START [OVL_B]" in row for row in summary_rows), "Missing start summary row for OVL_B")
    _assert(any("37.000:STR_END [OVL_C]" in row for row in summary_rows), "Missing end summary row for OVL_C")

    slice_20 = _find_group_section(sec, 20.0)
    slice_28 = _find_group_section(sec, 28.0)
    slice_34 = _find_group_section(sec, 34.0)
    _assert(slice_20 is not None, "Missing child section at 20.0")
    _assert(slice_28 is not None, "Missing child section at 28.0")
    _assert(slice_34 is not None, "Missing child section at 34.0")
    _assert("STR_START" in str(getattr(slice_20, "Label", "") or ""), "20.0 child label missing STR_START tag")
    _assert("STR" in str(getattr(slice_20, "Label", "") or ""), "20.0 child label missing active STR tag")
    _assert(set(list(getattr(slice_28, "StructureIds", []) or [])) == {"OVL_A", "OVL_B"}, "28.0 child structure IDs mismatch")
    _assert(set(list(getattr(slice_28, "StructureRoles", []) or [])) == {"active", "start"}, "28.0 child roles mismatch")
    _assert(set(list(getattr(slice_34, "StructureRoles", []) or [])) == {"active", "transition_before"}, "34.0 child roles mismatch")
    _assert(int(getattr(slice_28, "StructureOverlayCount", 0) or 0) >= 1, "28.0 child missing structure overlay count")

    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    _assert(int(getattr(cor, "StructureSegmentCount", 0) or 0) >= 2, "Corridor should split across structure ranges")
    _assert(len(list(getattr(cor, "SkippedStationRanges", []) or [])) >= 1, "CorridorLoft missing skipped station ranges")
    mode_summary = str(getattr(cor, "ResolvedStructureCorridorModeSummary", "") or "")
    _assert("skip_zone=2" in mode_summary, "Corridor mode summary missing skip_zone count")
    _assert("split_only=1" in mode_summary, "Corridor mode summary missing split_only count")
    cor_status = str(getattr(cor, "Status", "") or "")
    _assert("corridorModes=" in cor_status, "Corridor status missing corridor mode summary")
    _assert("skip_zone=2" in cor_status, "Corridor status missing skip_zone count")
    _assert("split_only=1" in cor_status, "Corridor status missing split_only count")
    _assert("skipZones=" in cor_status, "Corridor status missing skip-zone summary")

    App.closeDocument(doc.Name)
    print("[PASS] Structure station merge smoke test completed.")


if __name__ == "__main__":
    run()
