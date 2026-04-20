# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
SectionProfile export contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_section_profile_contract.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _mesh_ok(obj) -> bool:
    mesh = getattr(obj, "Mesh", None)
    if mesh is None:
        return False
    try:
        return int(getattr(mesh, "CountFacets", 0) or 0) > 0
    except Exception:
        return False


def _shape_ok(obj) -> bool:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False


def run():
    doc = App.newDocument("CRSectionProfileContract")

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

    typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
    TypicalSectionTemplate(typ)
    typ.ComponentIds = ["LANE-L", "DITCH-L", "LANE-R", "BERM-R"]
    typ.ComponentTypes = ["lane", "ditch", "lane", "berm"]
    typ.ComponentShapes = ["", "trapezoid", "", ""]
    typ.ComponentSides = ["left", "left", "right", "right"]
    typ.ComponentWidths = [3.50, 2.00, 3.50, 1.50]
    typ.ComponentCrossSlopes = [2.0, 4.0, 2.0, 0.0]
    typ.ComponentHeights = [0.0, 0.80, 0.0, 0.20]
    typ.ComponentExtraWidths = [0.0, 0.60, 0.0, 0.80]
    typ.ComponentBackSlopes = [0.0, -8.0, 0.0, 6.0]
    typ.ComponentOffsets = [0.0, 0.0, 0.0, 0.0]
    typ.ComponentOrders = [10, 20, 10, 20]
    typ.ComponentEnabled = [1, 1, 1, 1]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.TypicalSectionTemplate = typ
    sec.UseTypicalSectionTemplate = True
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 100.0
    sec.Interval = 25.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.CreateChildSections = False
    sec.DaylightAuto = False

    dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
    DesignGradingSurface(dgs)
    dgs.SourceSectionSet = sec
    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    cor.SourceSectionSet = sec

    doc.recompute()

    rows = list(getattr(sec, "SectionProfileRows", []) or [])
    _assert(int(getattr(sec, "SectionProfileCount", 0) or 0) == int(getattr(sec, "SectionCount", 0) or 0), "SectionProfileCount should match SectionCount")
    _assert(len(rows) == int(getattr(sec, "SectionCount", 0) or 0), "SectionProfileRows should exist per section")
    _assert(all("section_profile|" in str(row or "") for row in rows), "SectionProfileRows should use section_profile rows")

    profiles, _rows, point_count = SectionSet.resolve_section_profiles(sec)
    _assert(len(profiles) == int(getattr(sec, "SectionCount", 0) or 0), "resolve_section_profiles should return one profile per section")
    _assert(int(point_count) >= 5, "Richer typical section should export expanded profile points")
    _assert(all(len(list(profile.get("points", []) or [])) == int(point_count) for profile in profiles), "All section profiles should keep a stable point count")
    _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh")
    _assert(_shape_ok(cor), "Corridor did not generate geometry from exported SectionProfile contract")
    _assert(int(getattr(dgs, "PointCountPerSection", 0) or 0) == int(point_count), "DesignGradingSurface should consume exported SectionProfile contract")
    _assert(int(getattr(cor, "PointCountPerSection", 0) or 0) == int(point_count), "Corridor should consume exported SectionProfile contract")
    _assert(str(getattr(cor, "ProfileContractSource", "-") or "-") == "section_profiles", "Corridor should report section_profiles contract source")
    _assert("profileContract=section_profiles" in str(getattr(cor, "Status", "") or ""), "Corridor status should expose profile contract source")
    cor_export = list(getattr(cor, "ExportSummaryRows", []) or [])
    _assert(len(cor_export) == 1 and "profileContract=section_profiles" in cor_export[0], "Corridor export summary should expose profile contract source")

    App.closeDocument(doc.Name)
    print("[PASS] SectionProfile export contract smoke test completed.")


if __name__ == "__main__":
    run()
