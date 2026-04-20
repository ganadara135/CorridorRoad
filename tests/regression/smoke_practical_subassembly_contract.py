# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Practical subassembly contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_practical_subassembly_contract.py
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
    doc = App.newDocument("CRPracticalSubassemblyContract")
    try:
        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(60.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
        Centerline3DDisplay(disp)
        disp.Alignment = aln
        disp.ElevationSource = "FlatZero"
        disp.UseStationing = False

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.UseSideSlopes = True
        asm.LeftSideWidth = 3.0
        asm.RightSideWidth = 3.0
        asm.ShowTemplateWire = True

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        typ.ComponentIds = ["LANE-L", "DITCH-L", "LANE-R", "BERM-R"]
        typ.ComponentTypes = ["lane", "ditch", "lane", "berm"]
        typ.ComponentSides = ["left", "left", "right", "right"]
        typ.ComponentWidths = [3.50, 2.20, 3.50, 1.20]
        typ.ComponentCrossSlopes = [2.0, 4.0, 2.0, 0.0]
        typ.ComponentHeights = [0.0, 0.90, 0.0, 0.00]
        typ.ComponentExtraWidths = [0.0, 0.60, 0.0, 0.80]
        typ.ComponentBackSlopes = [0.0, 4.0, 0.0, 0.0]
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
        sec.EndStation = 60.0
        sec.Interval = 20.0
        sec.CreateChildSections = False

        cor = doc.addObject("Part::FeaturePython", "Corridor")
        Corridor(cor)
        cor.SourceSectionSet = sec

        dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
        DesignGradingSurface(dgs)
        dgs.SourceSectionSet = sec

        doc.recompute()

        _assert(_shape_ok(asm), "AssemblyTemplate did not generate geometry")
        _assert(str(getattr(asm, "PracticalRole", "") or "") == "assembly_core", "AssemblyTemplate role mismatch")
        _assert("role=assembly_core" in str(getattr(asm, "Status", "") or ""), "AssemblyTemplate status missing role summary")

        _assert(_shape_ok(typ), "TypicalSectionTemplate did not generate geometry")
        _assert(int(getattr(typ, "SubassemblySchemaVersion", 0) or 0) == 1, "TypicalSectionTemplate subassembly schema mismatch")
        _assert(str(getattr(typ, "PracticalRole", "") or "") == "top_profile_subassembly", "TypicalSectionTemplate role mismatch")
        _assert(str(getattr(typ, "PracticalSectionMode", "") or "") == "advanced", "TypicalSectionTemplate practical mode mismatch")
        _assert(len(list(getattr(typ, "SubassemblyContractRows", []) or [])) == 4, "TypicalSectionTemplate contract rows mismatch")
        _assert(len(list(getattr(typ, "SubassemblyValidationRows", []) or [])) >= 2, "TypicalSectionTemplate validation rows missing")
        typ_status = str(getattr(typ, "Status", "") or "")
        _assert("role=top_profile_subassembly" in typ_status, "TypicalSectionTemplate status missing role summary")
        _assert("practical=advanced" in typ_status, "TypicalSectionTemplate status missing practical-mode summary")
        _assert("subSchema=1" in typ_status, "TypicalSectionTemplate status missing subassembly schema summary")

        _assert(_shape_ok(sec), "SectionSet did not generate geometry")
        _assert(_shape_ok(cor), "Corridor did not generate geometry")
        _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh")

        for obj in (sec, cor, dgs):
            name = str(getattr(obj, "Name", "Object") or "Object")
            _assert(int(getattr(obj, "SubassemblySchemaVersion", 0) or 0) == 1, f"{name} subassembly schema mismatch")
            _assert(str(getattr(obj, "PracticalSectionMode", "") or "") == "advanced", f"{name} practical mode mismatch")
            _assert(len(list(getattr(obj, "SubassemblyContractRows", []) or [])) == 4, f"{name} contract rows mismatch")
            _assert(len(list(getattr(obj, "SubassemblyValidationRows", []) or [])) >= 2, f"{name} validation rows missing")
            status = str(getattr(obj, "Status", "") or "")
            _assert("subSchema=1" in status, f"{name} status missing subassembly schema summary")
            _assert("practical=advanced" in status, f"{name} status missing practical mode summary")
            _assert("subWarn=" in status, f"{name} status missing subassembly warning summary")

        App.closeDocument(doc.Name)
        print("[PASS] Practical subassembly contract smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
