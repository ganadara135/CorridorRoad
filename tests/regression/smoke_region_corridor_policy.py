# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region-driven corridor policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_corridor_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
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


def run():
    doc = App.newDocument("CRRegionCorridorPolicy")

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
    reg.RegionIds = ["BASE_A", "BASE_SPLIT", "BASE_SKIP"]
    reg.RegionTypes = ["roadway", "bridge_approach", "earthwork_zone"]
    reg.Layers = ["base", "base", "base"]
    reg.StartStations = [0.0, 30.0, 70.0]
    reg.EndStations = [30.0, 70.0, 90.0]
    reg.Priorities = [0, 0, 0]
    reg.CorridorPolicies = ["", "split_only", "skip_zone"]
    reg.EnabledFlags = ["true", "true", "true"]

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
    sec.UseRegionPlan = True
    sec.RegionPlan = reg
    sec.IncludeRegionBoundaries = True
    sec.IncludeRegionTransitions = False
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = False
    cor.UseRegionCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "CorridorLoft did not generate geometry")
    _assert(int(getattr(cor, "StructureSegmentCount", 0) or 0) == 2, "Corridor segment count mismatch for region-driven split/skip")
    _assert(list(getattr(cor, "SkippedStationRanges", []) or []) == ["70.000-90.000"], "Region skip-zone ranges mismatch")

    region_mode_summary = str(getattr(cor, "ResolvedRegionCorridorModeSummary", "-") or "-")
    combined_mode_summary = str(getattr(cor, "ResolvedCombinedCorridorModeSummary", "-") or "-")
    _assert("split_only=1" in region_mode_summary, "Region mode summary missing split_only")
    _assert("skip_zone=1" in region_mode_summary, "Region mode summary missing skip_zone")
    _assert(combined_mode_summary.startswith("region|"), "Combined mode summary should report region source")
    _assert("split_only=1" in combined_mode_summary, "Combined mode summary missing split_only")
    _assert("skip_zone=1" in combined_mode_summary, "Combined mode summary missing skip_zone")

    region_ranges = list(getattr(cor, "ResolvedRegionCorridorRanges", []) or [])
    combined_ranges = list(getattr(cor, "ResolvedCombinedCorridorRanges", []) or [])
    _assert(any("BASE_SPLIT:region:split_only:30.000-60.000" in row for row in region_ranges), "Missing split_only region detail row")
    _assert(any("BASE_SKIP:region:skip_zone:70.000-90.000" in row for row in region_ranges), "Missing skip_zone region detail row")
    _assert(any("BASE_SPLIT:region:split_only:30.000-60.000" in row for row in combined_ranges), "Missing split_only combined row")
    _assert(any("BASE_SKIP:region:skip_zone:70.000-90.000" in row for row in combined_ranges), "Missing skip_zone combined row")
    _assert(len(list(getattr(cor, "ResolvedCombinedCorridorWarnings", []) or [])) == 0, "Region-only combined warnings should stay empty")

    status = str(getattr(cor, "Status", "") or "")
    _assert("corridorRule=region_aware" in status, "CorridorLoft status missing region-aware token")
    _assert("corridorModes=region|" in status, "CorridorLoft status missing combined region mode summary")
    _assert("regionCorridorModes=split_only=1, skip_zone=1" in status, "CorridorLoft status missing region mode summary")
    _assert("skipZones=1" in status, "CorridorLoft status missing skip-zone summary")

    App.closeDocument(doc.Name)
    print("[PASS] Region-driven corridor policy smoke test completed.")


if __name__ == "__main__":
    run()
