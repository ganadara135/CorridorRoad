# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Boolean-cut scope guard smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_boolean_cut_scope_guard.py
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
    doc = App.newDocument("CRBooleanCutScopeGuard")

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

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["CUT_FUTURE"]
    ss.StructureTypes = ["culvert"]
    ss.StartStations = [30.0]
    ss.EndStations = [50.0]
    ss.CenterStations = [40.0]
    ss.Sides = ["both"]
    ss.Widths = [6.0]
    ss.Heights = [3.0]
    ss.CorridorModes = ["boolean_cut"]

    issues = list(StructureSet.validate(ss) or [])
    _assert(any("boolean_cut remains later opt-in scope" in row for row in issues), "Missing boolean_cut future-scope validation warning")

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 80.0
    sec.Interval = 20.0
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = True
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    status = str(getattr(cor, "Status", "") or "")
    _assert("corridorModes=boolean_cut=1" in status, "Corridor status missing boolean_cut mode summary")
    _assert("notchSchema=" not in status, "Boolean-cut workflow should not imply notch schema usage")
    _assert("notchBuild=" not in status, "Boolean-cut workflow should not imply notch build mode")
    _assert(str(getattr(cor, "ResolvedNotchSchemaName", "") or "") == "-", "Boolean-cut workflow should keep notch schema empty")
    _assert(str(getattr(cor, "ResolvedNotchBuildMode", "") or "") == "-", "Boolean-cut workflow should keep notch build mode empty")

    App.closeDocument(doc.Name)
    print("[PASS] Boolean-cut scope guard smoke test completed.")


if __name__ == "__main__":
    run()
