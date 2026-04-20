# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Notch workflow with neighboring corridor modes smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_notch_neighbor_modes.py
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


def run():
    doc = App.newDocument("CRNotchNeighborModes")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(120.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False

    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False
    asm.LeftWidth = 5.0
    asm.RightWidth = 5.0
    asm.HeightLeft = 4.0
    asm.HeightRight = 4.0

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["SKIP_ZONE", "NOTCH_MAIN", "WALL_SPLIT"]
    ss.StructureTypes = ["culvert", "culvert", "retaining_wall"]
    ss.StartStations = [20.0, 50.0, 82.0]
    ss.EndStations = [30.0, 70.0, 92.0]
    ss.CenterStations = [25.0, 60.0, 87.0]
    ss.Sides = ["both", "both", "left"]
    ss.Widths = [4.0, 4.0, 3.0]
    ss.Heights = [2.0, 2.0, 4.0]
    ss.CorridorModes = ["skip_zone", "notch", "split_only"]

    ss.ProfileStructureIds = ["NOTCH_MAIN", "NOTCH_MAIN", "NOTCH_MAIN"]
    ss.ProfileStations = [50.0, 60.0, 70.0]
    ss.ProfileWidths = [4.0, 8.0, 6.0]
    ss.ProfileHeights = [2.0, 3.0, 2.5]
    ss.ProfileBottomElevations = [1.0, 1.2, 1.1]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 100.0
    sec.Interval = 20.0
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = True
    sec.IncludeStructureTransitionStations = True
    sec.AutoStructureTransitionDistance = False
    sec.StructureTransitionDistance = 5.0
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.SplitAtStructureZones = True
    cor.DefaultStructureCorridorMode = "split_only"
    cor.NotchTransitionScale = 1.0

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    _assert(int(getattr(cor, "StructureSegmentCount", 0) or 0) == 2, "Expected mixed structure segmentation to preserve two kept ranges around skip-zone gaps")
    _assert(int(getattr(cor, "ResolvedStructureNotchCount", 0) or 0) == 1, "Expected exactly one notch structure")
    _assert(int(getattr(cor, "ResolvedNotchStationCount", 0) or 0) == 5, "Unexpected notch station count in mixed-mode case")
    _assert(str(getattr(cor, "ResolvedNotchBuildMode", "") or "") == "schema_profiles", "Mixed corridor modes should keep schema-profile notch build in surface mode")

    mode_summary = str(getattr(cor, "ResolvedStructureCorridorModeSummary", "") or "")
    _assert("split_only=1" in mode_summary, "Mode summary missing split_only count")
    _assert("skip_zone=1" in mode_summary, "Mode summary missing skip_zone count")
    _assert("notch=1" in mode_summary, "Mode summary missing notch count")

    skipped_ranges = list(getattr(cor, "SkippedStationRanges", []) or [])
    _assert(skipped_ranges == ["20.000-30.000"], "Unexpected skip-zone station ranges in mixed-mode case")

    status = str(getattr(cor, "Status", "") or "")
    _assert(len(list(getattr(getattr(cor, "Shape", None), "Solids", []) or [])) == 0, "Mixed-mode corridor should stay surface-only")
    _assert(status.startswith("OK (Surface)"), "Mixed-mode corridor should report successful surface build")
    _assert("output=surface" in status, "Status missing surface-output token")
    _assert("structureSegs=2" in status, "Status missing structure segmentation token")
    _assert("corridorModes=structure|split_only=1, skip_zone=1, notch=1" in status, "Status missing mixed corridor mode summary")
    _assert("skipMarkers=2" in status, "Status missing skip-marker token")
    _assert("notchBuild=schema_profiles" in status, "Status missing notch build token")
    _assert("skipZones=" in status, "Status missing skip-zone token")

    App.closeDocument(doc.Name)
    print("[PASS] Notch neighbor-modes smoke test completed.")


if __name__ == "__main__":
    run()
