# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor section-strip surface smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_loft_section_strip_surface.py
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
    doc = App.newDocument("CRCorridorStripSurface")

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
    cor.UseStructureCorridorModes = False
    cor.SplitAtStructureZones = False

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")

    section_count = int(getattr(cor, "SectionCount", 0) or 0)
    point_count = int(getattr(cor, "PointCountPerSection", 0) or 0)
    expected_faces = 2 * max(0, section_count - 1) * max(0, point_count - 1)
    face_count = len(list(getattr(getattr(cor, "Shape", None), "Faces", []) or []))

    _assert(section_count == 4, "Unexpected simple corridor section count")
    _assert(point_count == 3, "Unexpected simple corridor point count")
    _assert(face_count == expected_faces, f"Corridor strip face count mismatch: {face_count} != {expected_faces}")
    _assert(len(list(getattr(getattr(cor, "Shape", None), "Solids", []) or [])) == 0, "Corridor should stay surface-only")

    App.closeDocument(doc.Name)
    print("[PASS] Corridor section-strip surface smoke test completed.")


if __name__ == "__main__":
    run()
