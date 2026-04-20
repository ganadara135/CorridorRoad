# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Typical-section pavement display/report propagation smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_typical_section_pavement_report.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionPavementDisplay, TypicalSectionTemplate


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
    doc = App.newDocument("CRTypicalSectionPavementReport")
    try:
        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(80.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
        Centerline3DDisplay(disp)
        disp.Alignment = aln
        disp.ElevationSource = "FlatZero"
        disp.UseStationing = False

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.UseSideSlopes = False

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        typ.ComponentIds = ["LANE-L", "CURB-L", "LANE-R", "DITCH-R", "BERM-R"]
        typ.ComponentTypes = ["lane", "curb", "lane", "ditch", "berm"]
        typ.ComponentSides = ["left", "left", "right", "right", "right"]
        typ.ComponentWidths = [3.50, 0.18, 3.50, 2.40, 1.20]
        typ.ComponentCrossSlopes = [2.0, 0.0, 2.0, 2.0, 0.0]
        typ.ComponentHeights = [0.0, 0.15, 0.0, 1.00, 0.0]
        typ.ComponentExtraWidths = [0.0, 0.06, 0.0, 0.80, 0.60]
        typ.ComponentBackSlopes = [0.0, 1.0, 0.0, -10.0, 6.0]
        typ.ComponentOffsets = [0.0, 0.0, 0.0, 0.0, 0.0]
        typ.ComponentOrders = [10, 20, 10, 20, 30]
        typ.ComponentEnabled = [1, 1, 1, 1, 1]
        typ.PavementLayerIds = ["SURF", "BASE"]
        typ.PavementLayerTypes = ["surface", "base"]
        typ.PavementLayerThicknesses = [0.05, 0.18]
        typ.PavementLayerEnabled = [1, 1]

        pav = doc.addObject("Part::FeaturePython", "TypicalSectionPavementDisplay")
        TypicalSectionPavementDisplay(pav)
        pav.SourceTypicalSection = typ

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        sec.SourceCenterlineDisplay = disp
        sec.AssemblyTemplate = asm
        sec.TypicalSectionTemplate = typ
        sec.UseTypicalSectionTemplate = True
        sec.Mode = "Range"
        sec.StartStation = 0.0
        sec.EndStation = 80.0
        sec.Interval = 20.0
        sec.CreateChildSections = False

        cor = doc.addObject("Part::FeaturePython", "Corridor")
        Corridor(cor)
        cor.SourceSectionSet = sec

        dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
        DesignGradingSurface(dgs)
        dgs.SourceSectionSet = sec

        doc.recompute()

        _assert(_shape_ok(typ), "TypicalSectionTemplate did not generate preview geometry")
        _assert(int(getattr(typ, "AdvancedComponentCount", 0) or 0) >= 3, "TypicalSectionTemplate advanced component count missing")
        _assert(list(getattr(typ, "PavementLayerSummaryRows", []) or []) == ["SURF:surface:0.050m", "BASE:base:0.180m"], "Unexpected template pavement layer report rows")
        _assert("advanced=" in str(getattr(typ, "Status", "") or ""), "TypicalSectionTemplate status missing advanced summary")

        _assert(_shape_ok(pav), "TypicalSectionPavementDisplay did not generate geometry")
        _assert(int(getattr(pav, "LayerCount", 0) or 0) == 2, "Pavement display layer count mismatch")
        _assert(abs(float(getattr(pav, "TotalThickness", 0.0) or 0.0) - 0.23) <= 1e-6, "Pavement display thickness mismatch")
        _assert(list(getattr(pav, "LayerIds", []) or []) == ["SURF", "BASE"], "Pavement display ids mismatch")
        _assert(list(getattr(pav, "LayerSummaryRows", []) or []) == ["SURF:surface:0.050m", "BASE:base:0.180m"], "Pavement display summary rows mismatch")
        typ_bb = getattr(getattr(typ, "Shape", None), "BoundBox", None)
        pav_bb = getattr(getattr(pav, "Shape", None), "BoundBox", None)
        _assert(typ_bb is not None and pav_bb is not None, "Expected bound boxes for template and pavement display")
        _assert(float(pav_bb.XMin) > float(typ_bb.XMin) + 1.0, "Pavement display should stop before ditch/berm components on the right side")
        _assert(abs(float(pav_bb.XMax) - float(typ_bb.XMax)) <= 1.0e-6, "Pavement display should still follow the paved left-side edge")

        _assert(_shape_ok(cor), "Corridor did not generate geometry")
        _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh")

        for obj in (sec, cor, dgs):
            name = str(getattr(obj, "Name", "Object") or "Object")
            _assert(int(getattr(obj, "TypicalSectionAdvancedComponentCount", 0) or 0) >= 3, f"{name} advanced component count missing")
            _assert(list(getattr(obj, "PavementLayerSummaryRows", []) or []) == ["SURF:surface:0.050m", "BASE:base:0.180m"], f"{name} pavement report rows mismatch")
            status = str(getattr(obj, "Status", "") or "")
            _assert("typicalAdvanced=" in status, f"{name} status missing advanced summary")
            _assert("pavLayers=2/2" in status, f"{name} status missing pavement layer summary")

        App.closeDocument(doc.Name)
        print("[PASS] Typical-section pavement/report smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
