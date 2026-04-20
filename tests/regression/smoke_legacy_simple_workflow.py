# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Legacy/simple workflow smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_legacy_simple_workflow.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
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
    doc = App.newDocument("CRLegacySimpleWorkflow")

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
    asm.UseSideSlopes = False
    asm.LeftWidth = 4.0
    asm.RightWidth = 4.0

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 60.0
    sec.Interval = 20.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.UseStructureSet = False
    sec.UseTypicalSectionTemplate = False
    sec.DaylightAuto = False
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True

    doc.recompute()

    _assert(_shape_ok(sec), "Simple SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Simple Corridor did not generate geometry")
    _assert(int(getattr(sec, "SectionSchemaVersion", 0) or 0) == 1, "Legacy simple workflow should stay on schema 1")
    _assert(str(getattr(sec, "TopProfileSource", "") or "") == "assembly_simple", "Legacy simple workflow top profile mismatch")
    sec_status = str(getattr(sec, "Status", "") or "")
    _assert(sec_status.startswith("OK"), "Legacy simple workflow section status should stay OK")
    _assert("daylight=off" in sec_status, "Simple section status missing daylight=off token")
    _assert("earthwork=full" in sec_status, "Simple section status missing full earthwork token")
    _assert("topProfile=assembly_simple" in sec_status, "Simple section status missing top-profile summary")
    _assert("structures=" not in sec_status, "Simple section status should not report structure diagnostics")
    cor_status = str(getattr(cor, "Status", "") or "")
    _assert(cor_status.startswith("OK"), "Legacy simple workflow corridor status should stay OK")
    _assert("corridorRule=full" in cor_status, "Simple corridor status missing full corridor token")
    _assert("earthwork=full" in cor_status, "Simple corridor status missing full earthwork token")
    _assert("corridorModes=" not in cor_status, "Simple corridor status should not report structure corridor modes")
    _assert("skipCaps=" not in cor_status, "Simple corridor status should not report skip boundary caps")
    _assert(str(getattr(cor, "ResolvedSkipBoundaryBehavior", "") or "") == "-", "Simple corridor skip boundary behavior should stay empty")
    _assert(list(getattr(cor, "ResolvedSkipBoundaryStates", []) or []) == [], "Simple corridor skip boundary states should stay empty")

    App.closeDocument(doc.Name)
    print("[PASS] Legacy/simple workflow smoke test completed.")


if __name__ == "__main__":
    run()
