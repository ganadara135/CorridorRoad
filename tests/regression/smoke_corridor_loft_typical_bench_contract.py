# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CorridorLoft typical-section + bench strip contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_loft_typical_bench_contract.py
"""

import FreeCAD as App

from freecad.Corridor_Road.corridor_compat import CORRIDOR_CHILD_LINK_PROPERTY
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
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


def _mesh_ok(obj) -> bool:
    mesh = getattr(obj, "Mesh", None)
    if mesh is None:
        return False
    try:
        return int(getattr(mesh, "CountFacets", 0) or 0) > 0
    except Exception:
        return False


def run():
    doc = App.newDocument("CRCorridorTypicalBenchContract")

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
    asm.UseRightBench = True
    asm.RightBenchDrop = 0.8
    asm.RightBenchWidth = 1.2
    asm.RightBenchSlopePct = 0.0
    asm.RightPostBenchSlopePct = 40.0

    typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
    TypicalSectionTemplate(typ)
    typ.ComponentIds = ["BERM-L", "LANE-L", "LANE-R", "BERM-R"]
    typ.ComponentTypes = ["berm", "lane", "lane", "berm"]
    typ.ComponentShapes = ["", "", "", ""]
    typ.ComponentSides = ["left", "left", "right", "right"]
    typ.ComponentWidths = [1.5, 3.5, 3.5, 1.5]
    typ.ComponentCrossSlopes = [0.0, 2.0, 2.0, 0.0]
    typ.ComponentHeights = [0.0, 0.0, 0.0, 0.0]
    typ.ComponentExtraWidths = [0.8, 0.0, 0.0, 0.8]
    typ.ComponentBackSlopes = [6.0, 0.0, 0.0, 6.0]
    typ.ComponentOffsets = [0.0, 0.0, 0.0, 0.0]
    typ.ComponentOrders = [20, 10, 10, 20]
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

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec

    dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
    DesignGradingSurface(dgs)
    dgs.SourceSectionSet = sec

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh")
    _assert(str(getattr(sec, "TopProfileSource", "") or "") == "typical_section", "Top profile should be typical_section")
    _assert(str(getattr(sec, "TopProfileEdgeSummary", "") or "") == "berm/berm", "Top edge summary should stay berm/berm")
    _assert(int(getattr(cor, "AutoFixedSectionCount", 0) or 0) == 0, "Typical+bench corridor should keep SectionSet point order")
    _assert(str(getattr(cor, "ProfileContractSource", "-") or "-") == "section_profiles", "Typical+bench corridor should report section_profiles contract source")
    _assert(str(getattr(cor, "SegmentProfileContractSummary", "-") or "-") == "section_profiles=1", "Typical+bench corridor should summarize section_profiles package contract")

    cor_faces = len(list(getattr(getattr(cor, "Shape", None), "Faces", []) or []))
    dgs_faces = int(getattr(dgs, "FaceCount", 0) or 0)
    _assert(cor_faces == dgs_faces, f"CorridorLoft faces should match grading strip faces: {cor_faces} != {dgs_faces}")

    package_rows = list(getattr(cor, "SegmentPackageRows", []) or [])
    _assert(len(package_rows) >= 1, "Typical+bench corridor should expose at least one segment package row")
    _assert(all("profileContract=section_profiles" in row for row in package_rows), "Typical+bench segment packages should carry the section_profiles contract source")

    segment_objs = [
        o
        for o in list(getattr(doc, "Objects", []) or [])
        if str(getattr(o, "Name", "") or "").startswith("CorridorSegment")
        and getattr(o, CORRIDOR_CHILD_LINK_PROPERTY, None) == cor
    ]
    _assert(len(segment_objs) >= 1, "Typical+bench corridor should create at least one CorridorSegment child")
    _assert(all(str(getattr(o, "ProfileContractSource", "-") or "-") == "section_profiles" for o in segment_objs), "Typical+bench CorridorSegment children should carry the section_profiles contract source")
    _assert(all("[section_profiles]" in str(getattr(o, "Label", "") or "") for o in segment_objs), "Typical+bench CorridorSegment labels should expose the contract source")
    _assert(all("|contract=section_profiles" in str(getattr(o, "SegmentSummary", "") or "") for o in segment_objs), "Typical+bench CorridorSegment summaries should expose the contract source")

    App.closeDocument(doc.Name)
    print("[PASS] CorridorLoft typical-section + bench strip contract smoke test completed.")


if __name__ == "__main__":
    run()
