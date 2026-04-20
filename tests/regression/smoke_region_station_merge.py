# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region-driven station merge smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_station_merge.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


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
    doc = App.newDocument("CRRegionStationMerge")

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

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    reg.RegionIds = ["BASE_A", "BASE_B", "BASE_C", "OVR_DITCH"]
    reg.RegionTypes = ["roadway", "widening", "bridge_approach", "ditch_override"]
    reg.Layers = ["base", "base", "base", "overlay"]
    reg.StartStations = [0.0, 35.0, 70.0, 48.0]
    reg.EndStations = [35.0, 70.0, 100.0, 52.0]
    reg.Priorities = [0, 0, 0, 10]
    reg.TransitionIns = [0.0, 5.0, 0.0, 2.0]
    reg.TransitionOuts = [0.0, 3.0, 0.0, 1.0]
    reg.EnabledFlags = ["true", "true", "true", "true"]

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
    sec.UseRegionPlan = True
    sec.RegionPlan = reg
    sec.IncludeRegionBoundaries = True
    sec.IncludeRegionTransitions = True
    sec.CreateChildSections = True
    sec.AutoRebuildChildren = True

    doc.recompute()

    expected_stations = [0.0, 20.0, 30.0, 35.0, 40.0, 46.0, 48.0, 52.0, 53.0, 60.0, 70.0, 73.0, 80.0, 100.0]
    _assert_station_values(sec.StationValues, expected_stations, "Merged station values mismatch")
    _assert(int(getattr(sec, "ResolvedRegionCount", 0) or 0) == 10, "Resolved region count mismatch")
    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert("regions=10" in str(getattr(sec, "Status", "") or ""), "SectionSet status missing region count")

    summary_rows = list(getattr(sec, "ResolvedRegionTags", []) or [])
    _assert(any("30.000:REG_TRANSITION [BASE_B]" in row for row in summary_rows), "Missing transition summary row for BASE_B")
    _assert(any("48.000:REG_START [OVR_DITCH]" in row for row in summary_rows), "Missing start summary row for overlay")
    _assert(any("53.000:REG_TRANSITION [OVR_DITCH]" in row for row in summary_rows), "Missing transition summary row for overlay")

    slice_35 = _find_group_section(sec, 35.0)
    slice_48 = _find_group_section(sec, 48.0)
    _assert(slice_35 is not None, "Missing child section at 35.0")
    _assert(slice_48 is not None, "Missing child section at 48.0")
    _assert("REG_START" in str(getattr(slice_35, "Label", "") or ""), "35.0 child label missing REG_START tag")
    _assert(set(list(getattr(slice_48, "RegionIds", []) or [])) == {"BASE_B", "OVR_DITCH"}, "48.0 child region IDs mismatch")
    _assert(str(getattr(slice_48, "BaseRegionId", "") or "") == "BASE_B", "48.0 child base region mismatch")
    _assert({"active", "start"}.issubset(set(list(getattr(slice_48, "RegionRoles", []) or []))), "48.0 child region roles mismatch")
    _assert(bool(getattr(slice_48, "HasRegion", False)), "48.0 child should be region-aware")

    payload = SectionSet.resolve_viewer_payload(sec, station=48.0, include_structure_overlay=False)
    _assert(bool(payload.get("has_region", False)), "Viewer payload should report region awareness")
    _assert(str(payload.get("base_region_id", "") or "") == "BASE_B", "Viewer payload base region mismatch")
    _assert(set(list(payload.get("overlay_region_ids", []) or [])) == {"OVR_DITCH"}, "Viewer payload overlay region mismatch")

    App.closeDocument(doc.Name)
    print("[PASS] Region-driven station merge smoke test completed.")


if __name__ == "__main__":
    run()
