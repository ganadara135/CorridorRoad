# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Mixed region/structure corridor precedence smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_structure_corridor_precedence.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
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


def run():
    doc = App.newDocument("CRRegionStructureCorridorPrecedence")

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
    reg.RegionIds = ["BASE_A", "BASE_SKIP", "BASE_B"]
    reg.RegionTypes = ["roadway", "earthwork_zone", "roadway"]
    reg.Layers = ["base", "base", "base"]
    reg.StartStations = [0.0, 40.0, 80.0]
    reg.EndStations = [40.0, 80.0, 100.0]
    reg.Priorities = [0, 0, 0]
    reg.CorridorPolicies = ["", "skip_zone", ""]
    reg.EnabledFlags = ["true", "true", "true"]

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["STR_SPLIT"]
    ss.StructureTypes = ["bridge_zone"]
    ss.StartStations = [60.0]
    ss.EndStations = [70.0]
    ss.CenterStations = [65.0]
    ss.Sides = ["both"]
    ss.Widths = [8.0]
    ss.Heights = [4.0]
    ss.CorridorModes = ["split_only"]

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
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = False
    sec.IncludeStructureTransitionStations = False
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.UseRegionCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "CorridorLoft did not generate geometry")
    _assert(int(getattr(cor, "StructureSegmentCount", 0) or 0) == 2, "Mixed corridor segment count mismatch")
    _assert(list(getattr(cor, "SkippedStationRanges", []) or []) == ["40.000-60.000"], "Mixed skipped ranges mismatch")

    structure_mode_summary = str(getattr(cor, "ResolvedStructureCorridorModeSummary", "-") or "-")
    region_mode_summary = str(getattr(cor, "ResolvedRegionCorridorModeSummary", "-") or "-")
    combined_mode_summary = str(getattr(cor, "ResolvedCombinedCorridorModeSummary", "-") or "-")
    _assert(structure_mode_summary == "split_only=1", "Structure mode summary mismatch")
    _assert(region_mode_summary == "skip_zone=1", "Region mode summary mismatch")
    _assert(combined_mode_summary.startswith("mixed|"), "Combined mode summary should report mixed precedence")
    _assert("split_only=1" in combined_mode_summary, "Combined mode summary missing split_only")
    _assert("skip_zone=1" in combined_mode_summary, "Combined mode summary missing skip_zone")

    structure_ranges = list(getattr(cor, "ResolvedStructureCorridorRanges", []) or [])
    region_ranges = list(getattr(cor, "ResolvedRegionCorridorRanges", []) or [])
    combined_ranges = list(getattr(cor, "ResolvedCombinedCorridorRanges", []) or [])
    _assert(structure_ranges == ["STR_SPLIT:bridge_zone:split_only:60.000-70.000"], "Structure range diagnostics mismatch")
    _assert(region_ranges == ["BASE_SKIP:region:skip_zone:40.000-70.000 (source=section_regions)"], "Region range diagnostics mismatch")
    _assert(
        combined_ranges == [
            "BASE_SKIP:region:skip_zone:40.000-60.000 (source=region)",
            "STR_SPLIT:structure:split_only:60.000-70.000 (source=structure)",
        ],
        f"Combined range diagnostics mismatch: {combined_ranges}",
    )

    combined_warnings = list(getattr(cor, "ResolvedCombinedCorridorWarnings", []) or [])
    _assert(
        combined_warnings == ["BASE_SKIP: overridden by structure corridor mode 'split_only' from STR_SPLIT"],
        f"Combined warnings mismatch: {combined_warnings}",
    )

    status = str(getattr(cor, "Status", "") or "")
    _assert("corridorRule=mixed" in status, "CorridorLoft status missing mixed corridor token")
    _assert("corridorModes=mixed|" in status, "CorridorLoft status missing mixed combined mode summary")
    _assert("regionCorridorModes=skip_zone=1" in status, "CorridorLoft status missing region corridor summary")
    _assert("structCorridorModes=split_only=1" in status, "CorridorLoft status missing structure corridor summary")
    _assert("corridorWarn=1" in status, "CorridorLoft status missing mixed warning count")

    App.closeDocument(doc.Name)
    print("[PASS] Mixed region/structure corridor precedence smoke test completed.")


if __name__ == "__main__":
    run()
