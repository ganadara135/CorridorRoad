# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region-driven section rule consumption smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_rule_consumption.py
"""

import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _make_flat_terrain(doc, name: str, z_value: float = -1.0):
    obj = doc.addObject("Mesh::Feature", name)
    mesh = Mesh.Mesh()
    p00 = App.Vector(0.0, -20.0, float(z_value))
    p10 = App.Vector(100.0, -20.0, float(z_value))
    p01 = App.Vector(0.0, 20.0, float(z_value))
    p11 = App.Vector(100.0, 20.0, float(z_value))
    mesh.addFacet(p00, p10, p11)
    mesh.addFacet(p00, p11, p01)
    obj.Mesh = mesh
    if not hasattr(obj, "OutputCoords"):
        obj.addProperty("App::PropertyString", "OutputCoords", "Source", "Terrain coordinate mode")
    obj.OutputCoords = "Local"
    return obj


def _find_group_section(sec, station: float, tol: float = 1e-6):
    for child in list(getattr(sec, "Group", []) or []):
        if str(getattr(child, "Name", "") or "").startswith("SectionSlice"):
            if abs(float(getattr(child, "Station", 0.0) or 0.0) - float(station)) <= tol:
                return child
    return None


def _resolved_side_widths(bench_info):
    out = {}
    for row in list((bench_info or {}).get("stationProfiles", []) or []):
        station = round(float(row.get("station", 0.0) or 0.0), 3)
        left_segments = list(row.get("left_segments", []) or [])
        right_segments = list(row.get("right_segments", []) or [])
        out[station] = {
            "left": sum(max(0.0, float(seg.get("width", 0.0) or 0.0)) for seg in left_segments),
            "right": sum(max(0.0, float(seg.get("width", 0.0) or 0.0)) for seg in right_segments),
        }
    return out


def run():
    doc = App.newDocument("CRRegionRuleConsumption")

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
    asm.LeftWidth = 4.0
    asm.RightWidth = 4.0
    asm.LeftSlopePct = 0.0
    asm.RightSlopePct = 0.0
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 6.0
    asm.RightSideWidth = 6.0
    asm.LeftSideSlopePct = 50.0
    asm.RightSideSlopePct = 50.0
    asm.UseLeftBench = False
    asm.UseRightBench = False

    terrain = _make_flat_terrain(doc, "TerrainMesh", z_value=-1.0)

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    reg.RegionIds = ["BASE_KEEP", "BASE_DAYLIGHT_OFF", "BASE_SIDE_STUB"]
    reg.RegionTypes = ["roadway", "roadway", "ditch_override"]
    reg.Layers = ["base", "base", "base"]
    reg.StartStations = [0.0, 40.0, 70.0]
    reg.EndStations = [40.0, 70.0, 100.0]
    reg.Priorities = [0, 0, 0]
    reg.SidePolicies = ["", "", "stub"]
    reg.DaylightPolicies = ["", "off", ""]
    reg.EnabledFlags = ["true", "true", "true"]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Manual"
    sec.StationText = "20, 50, 80"
    sec.DaylightAuto = True
    sec.TerrainMesh = terrain
    sec.TerrainMeshCoords = "Local"
    sec.UseRegionPlan = True
    sec.RegionPlan = reg
    sec.ApplyRegionOverrides = True
    sec.IncludeRegionBoundaries = False
    sec.IncludeRegionTransitions = False
    sec.CreateChildSections = True
    sec.AutoRebuildChildren = True

    doc.recompute()

    stations, _wires, terrain_found, sampler_ok, bench_info = SectionSet.build_section_wires(sec)
    _assert([round(float(v), 3) for v in list(stations or [])] == [20.0, 50.0, 80.0], "Manual station values mismatch")
    _assert(bool(terrain_found), "Terrain should be detected for region-rule smoke test")
    _assert(bool(sampler_ok), "Terrain sampler should be available for region-rule smoke test")

    widths = _resolved_side_widths(bench_info)
    keep_widths = dict(widths.get(20.0, {}) or {})
    daylight_off_widths = dict(widths.get(50.0, {}) or {})
    stub_widths = dict(widths.get(80.0, {}) or {})
    _assert(abs(float(keep_widths.get("left", 0.0) or 0.0) - 2.0) < 0.25, f"20.0 left daylight width mismatch: {keep_widths}")
    _assert(abs(float(keep_widths.get("right", 0.0) or 0.0) - 2.0) < 0.25, f"20.0 right daylight width mismatch: {keep_widths}")
    _assert(abs(float(daylight_off_widths.get("left", 0.0) or 0.0) - 6.0) < 0.05, f"50.0 left fixed width mismatch: {daylight_off_widths}")
    _assert(abs(float(daylight_off_widths.get("right", 0.0) or 0.0) - 6.0) < 0.05, f"50.0 right fixed width mismatch: {daylight_off_widths}")
    _assert(float(stub_widths.get("left", 0.0) or 0.0) <= 0.05, f"80.0 left stub width mismatch: {stub_widths}")
    _assert(float(stub_widths.get("right", 0.0) or 0.0) <= 0.05, f"80.0 right stub width mismatch: {stub_widths}")

    _assert(int(getattr(sec, "RegionOverrideHitCount", 0) or 0) == 2, "Region override hit count mismatch")
    status = str(getattr(sec, "Status", "") or "")
    _assert("regionOverrides=2" in status, "SectionSet status missing region override hit count")
    _assert("regionSide=1" in status, "SectionSet status missing side-policy hit count")
    _assert("regionDaylight=1" in status, "SectionSet status missing daylight-policy hit count")

    region_rows = list(getattr(sec, "RegionInteractionSummaryRows", []) or [])
    _assert(any("stations=2" in row for row in region_rows), "Region interaction summary missing station count")
    _assert(any("side=1" in row for row in region_rows), "Region interaction summary missing side count")
    _assert(any("daylight=1" in row for row in region_rows), "Region interaction summary missing daylight count")

    slice_50 = _find_group_section(sec, 50.0)
    slice_80 = _find_group_section(sec, 80.0)
    _assert(slice_50 is not None, "Missing child section at 50.0")
    _assert(slice_80 is not None, "Missing child section at 80.0")
    _assert(str(getattr(slice_50, "ResolvedDaylightPolicy", "") or "") == "off", "50.0 child daylight policy mismatch")
    _assert(str(getattr(slice_80, "ResolvedSidePolicy", "") or "") == "stub", "80.0 child side policy mismatch")

    payload = SectionSet.resolve_viewer_payload(sec, station=80.0, include_structure_overlay=False)
    _assert(str(payload.get("resolved_side_policy", "") or "") == "stub", "Viewer payload side policy mismatch")
    _assert(str(payload.get("resolved_daylight_policy", "") or "") == "", "Viewer payload daylight policy mismatch at 80.0")

    App.closeDocument(doc.Name)
    print("[PASS] Region-driven section rule consumption smoke test completed.")


if __name__ == "__main__":
    run()
