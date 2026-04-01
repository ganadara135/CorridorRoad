# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Typical-section pipeline smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_typical_section_pipeline.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
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


def _make_alignment(doc, length=100.0):
    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(float(length), 0.0, 0.0)]
    aln.UseTransitionCurves = False
    return aln


def _make_display(doc, aln):
    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False
    disp.ShowWire = True
    return disp


def _make_assembly(doc):
    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False
    asm.HeightLeft = 0.40
    asm.HeightRight = 0.35
    return asm


def _make_typical(doc, richer=False):
    typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
    TypicalSectionTemplate(typ)
    if richer:
        typ.ComponentIds = ["LANE-L", "DITCH-L", "LANE-R", "BERM-R"]
        typ.ComponentTypes = ["lane", "ditch", "lane", "berm"]
        typ.ComponentSides = ["left", "left", "right", "right"]
        typ.ComponentWidths = [3.50, 2.00, 3.50, 1.50]
        typ.ComponentCrossSlopes = [2.0, 4.0, 2.0, 0.0]
        typ.ComponentHeights = [0.0, 0.80, 0.0, 0.20]
        typ.ComponentExtraWidths = [0.0, 0.60, 0.0, 0.80]
        typ.ComponentBackSlopes = [0.0, -8.0, 0.0, 6.0]
        typ.ComponentOffsets = [0.0, 0.0, 0.0, 0.0]
        typ.ComponentOrders = [10, 20, 10, 20]
        typ.ComponentEnabled = [1, 1, 1, 1]
    return typ


def _make_section_set(doc, name, disp, asm, typ):
    sec = doc.addObject("Part::FeaturePython", name)
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
    return sec


def _make_corridor(doc, sec):
    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    return cor


def _assert_basic_pipeline(sec, cor):
    _assert(_shape_ok(sec), f"{sec.Name} did not generate section geometry")
    _assert(_shape_ok(cor), f"{cor.Name} did not generate corridor geometry")
    _assert(int(getattr(sec, "SectionSchemaVersion", 0) or 0) == 2, f"{sec.Name} schema should be 2")
    _assert(str(getattr(sec, "TopProfileSource", "") or "") == "typical_section", f"{sec.Name} top profile source mismatch")
    _assert(int(getattr(sec, "SectionCount", 0) or 0) == 5, f"{sec.Name} section count mismatch")
    _assert(float(getattr(sec, "PavementTotalThickness", 0.0) or 0.0) > 1e-9, f"{sec.Name} pavement thickness missing")
    _assert("schema=2" in str(getattr(sec, "Status", "") or ""), f"{sec.Name} status missing schema summary")
    sec_status = str(getattr(sec, "Status", "") or "")
    _assert("topProfile=typical_section" in sec_status, f"{sec.Name} status missing typical-section summary")
    _assert("earthwork=full" in sec_status, f"{sec.Name} status missing full earthwork summary")

    _assert(int(getattr(cor, "SchemaVersion", 0) or 0) == 2, f"{cor.Name} source schema should be 2")
    _assert(int(getattr(cor, "PointCountPerSection", 0) or 0) >= 5, f"{cor.Name} point count per section is too low")
    _assert(len(list(getattr(getattr(cor, "Shape", None), "Solids", []) or [])) == 0, f"{cor.Name} should not generate corridor solids")
    cor_status = str(getattr(cor, "Status", "") or "")
    _assert(cor_status.startswith("OK (Surface)") or cor_status.startswith("WARN (Surface)"), f"{cor.Name} should report surface output status")
    _assert("output=surface" in cor_status, f"{cor.Name} status missing surface-output token")
    _assert("topProfile=typical_section" in cor_status, f"{cor.Name} status missing typical-section summary")
    _assert("srcSchema=2" in cor_status, f"{cor.Name} status missing source schema summary")
    _assert("pavement=" in cor_status, f"{cor.Name} status missing pavement summary")
    _assert("pavLayers=" in cor_status, f"{cor.Name} status missing pavement layer summary")
    _assert("corridorRule=full" in cor_status, f"{cor.Name} status missing full corridor summary")
    _assert("earthwork=full" in cor_status, f"{cor.Name} status missing full earthwork summary")


def run():
    doc = App.newDocument("CRTypicalSectionPipeline")

    aln = _make_alignment(doc, length=100.0)
    disp = _make_display(doc, aln)
    asm = _make_assembly(doc)

    typ_simple = _make_typical(doc, richer=False)
    sec_simple = _make_section_set(doc, "SectionSetSimple", disp, asm, typ_simple)
    cor_simple = _make_corridor(doc, sec_simple)

    typ_rich = _make_typical(doc, richer=True)
    sec_rich = _make_section_set(doc, "SectionSetRich", disp, asm, typ_rich)
    cor_rich = _make_corridor(doc, sec_rich)

    doc.recompute()

    _assert(_shape_ok(aln), "Alignment shape was not built")
    _assert(abs(float(getattr(aln.Shape, "Length", 0.0) or 0.0) - 100.0) < 1e-6, "Alignment length mismatch")
    _assert(int(getattr(typ_simple, "AdvancedComponentCount", 0) or 0) == 0, "Simple template should not report advanced components")
    _assert(str(getattr(typ_simple, "LeftEdgeComponentType", "") or "") == "shoulder", "Simple template left edge mismatch")
    _assert(str(getattr(typ_simple, "RightEdgeComponentType", "") or "") == "shoulder", "Simple template right edge mismatch")
    _assert_basic_pipeline(sec_simple, cor_simple)
    _assert(str(getattr(sec_simple, "TopProfileEdgeSummary", "") or "") == "shoulder/shoulder", "Simple section edge summary mismatch")
    _assert(int(getattr(sec_simple, "TypicalSectionAdvancedComponentCount", 0) or 0) == 0, "Simple section should not report advanced components")

    _assert(str(getattr(typ_rich, "LeftEdgeComponentType", "") or "") == "ditch", "Rich template left edge mismatch")
    _assert(str(getattr(typ_rich, "RightEdgeComponentType", "") or "") == "berm", "Rich template right edge mismatch")
    _assert(int(getattr(typ_rich, "AdvancedComponentCount", 0) or 0) >= 2, "Rich template should report advanced components")
    _assert(len(list(getattr(typ_rich, "PavementLayerSummaryRows", []) or [])) >= 1, "Rich template pavement report rows missing")
    _assert_basic_pipeline(sec_rich, cor_rich)
    _assert(str(getattr(sec_rich, "TopProfileEdgeSummary", "") or "") == "ditch/berm", "Rich section edge summary mismatch")
    _assert(int(getattr(sec_rich, "TypicalSectionAdvancedComponentCount", 0) or 0) >= 2, "Rich section should report advanced components")
    _assert("typicalAdvanced=" in str(getattr(sec_rich, "Status", "") or ""), "Rich section status missing advanced component summary")
    _assert(len(list(getattr(sec_rich, "PavementLayerSummaryRows", []) or [])) >= 1, "Rich section pavement report rows missing")
    _assert(int(getattr(cor_rich, "PointCountPerSection", 0) or 0) >= 6, "Rich corridor should have expanded point count")
    _assert("topEdges=ditch/berm" in str(getattr(cor_rich, "Status", "") or ""), "Rich corridor status missing edge summary")
    _assert("typicalAdvanced=" in str(getattr(cor_rich, "Status", "") or ""), "Rich corridor status missing advanced component summary")
    _assert(len(list(getattr(cor_rich, "PavementLayerSummaryRows", []) or [])) >= 1, "Rich corridor pavement report rows missing")

    App.closeDocument(doc.Name)
    print("[PASS] Typical-section pipeline smoke test completed.")


if __name__ == "__main__":
    run()
