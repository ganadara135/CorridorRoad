# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Skip-zone boundary behavior smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_skip_zone_boundary_behavior.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
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
    doc = App.newDocument("CRSkipZoneBoundary")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(40.0, 0.0, 0.0)]
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
    ss.StructureIds = ["START_SKIP", "END_SKIP"]
    ss.StructureTypes = ["bridge_zone", "bridge_zone"]
    ss.StartStations = [0.0, 30.0]
    ss.EndStations = [10.0, 40.0]
    ss.CenterStations = [5.0, 35.0]
    ss.Sides = ["both", "both"]
    ss.Widths = [8.0, 8.0]
    ss.Heights = [4.0, 4.0]
    ss.CorridorModes = ["skip_zone", "skip_zone"]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 40.0
    sec.Interval = 10.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = False
    sec.IncludeStructureTransitionStations = False
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    _assert(list(getattr(cor, "SkippedStationRanges", []) or []) == ["0.000-10.000", "30.000-40.000"], "Skipped ranges mismatch")
    _assert(str(getattr(cor, "ResolvedSkipBoundaryBehavior", "") or "") == "caps_deferred", "Skip boundary behavior mismatch")
    _assert(list(getattr(cor, "ResolvedSkipBoundaryStates", []) or []) == ["open_start:0.000-10.000", "open_end:30.000-40.000"], "Skip boundary states mismatch")
    _assert(int(getattr(cor, "ResolvedSkipBoundaryCapCount", 0)) == 0, "Skip boundary cap count should stay deferred/zero")
    package_rows = list(getattr(cor, "SegmentPackageRows", []) or [])
    _assert(len(package_rows) == 1, "Skip-boundary corridor should produce one kept package")
    _assert("start=10.000" in package_rows[0] and "end=30.000" in package_rows[0], "Kept package should retain boundary sections at 10.000 and 30.000")
    status = str(getattr(cor, "Status", "") or "")
    _assert("corridorRule=structure_aware" in status, "Corridor status missing structure-aware corridor token")
    _assert("earthwork=simplified_type_driven" in status, "Corridor status missing simplified earthwork token")
    _assert("skipCaps=deferred" in status, "Corridor status missing deferred cap summary")
    _assert("skipBoundary=open_start,open_end" in status, "Corridor status missing boundary summary")

    App.closeDocument(doc.Name)
    print("[PASS] Skip-zone boundary behavior smoke test completed.")


if __name__ == "__main__":
    run()
