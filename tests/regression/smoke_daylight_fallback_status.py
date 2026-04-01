# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Daylight fallback status smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_daylight_fallback_status.py
"""

import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
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


def _make_alignment(doc, length=30.0):
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
    return disp


def _make_assembly(doc):
    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.LeftWidth = 4.0
    asm.RightWidth = 4.0
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 5.0
    asm.RightSideWidth = 5.0
    asm.LeftSideSlopePct = 50.0
    asm.RightSideSlopePct = 50.0
    return asm


def _make_section_set(doc, name, disp, asm, terrain=None):
    sec = doc.addObject("Part::FeaturePython", name)
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Manual"
    sec.StationText = "10"
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.DaylightAuto = True
    sec.CreateChildSections = False
    if terrain is not None:
        sec.TerrainMesh = terrain
    return sec


def _make_mesh_feature(doc, name):
    obj = doc.addObject("Mesh::Feature", name)
    mesh = Mesh.Mesh()
    p0 = App.Vector(0.0, 0.0, 100.0)
    p1 = App.Vector(10.0, 0.0, 100.0)
    p2 = App.Vector(0.0, 10.0, 100.0)
    p3 = App.Vector(10.0, 10.0, 100.0)
    mesh.addFacet(p0, p1, p3)
    mesh.addFacet(p0, p3, p2)
    obj.Mesh = mesh
    if not hasattr(obj, "OutputCoords"):
        obj.addProperty("App::PropertyString", "OutputCoords", "Source", "Terrain coordinate mode")
    obj.OutputCoords = "Local"
    return obj


def _run_missing_terrain_case():
    doc = App.newDocument("CRDaylightNoTerrain")
    aln = _make_alignment(doc)
    disp = _make_display(doc, aln)
    asm = _make_assembly(doc)
    sec = _make_section_set(doc, "SectionSetNoTerrain", disp, asm, terrain=None)

    doc.recompute()

    status = str(getattr(sec, "Status", "") or "")
    _assert(_shape_ok(sec), "No-terrain SectionSet did not generate fallback geometry")
    _assert("daylight=fallback:no_terrain" in status, "No-terrain status missing fallback token")
    _assert("Add TerrainMesh or disable DaylightAuto." in status, "No-terrain status missing next-step guidance")
    _assert("earthwork=full" in status, "No-terrain status should report full earthwork")
    App.closeDocument(doc.Name)


def _run_sampler_failure_case():
    doc = App.newDocument("CRDaylightSamplerFail")
    aln = _make_alignment(doc)
    disp = _make_display(doc, aln)
    asm = _make_assembly(doc)
    terrain = _make_mesh_feature(doc, "TerrainMesh")
    sec = _make_section_set(doc, "SectionSetSamplerFail", disp, asm, terrain=terrain)

    orig = SectionSet._terrain_sampler
    try:
        SectionSet._terrain_sampler = staticmethod(lambda *args, **kwargs: None)
        doc.recompute()
    finally:
        SectionSet._terrain_sampler = orig

    status = str(getattr(sec, "Status", "") or "")
    _assert(_shape_ok(sec), "Sampler-failure SectionSet did not generate fallback geometry")
    _assert("daylight=fallback:sampler_failed" in status, "Sampler-failure status missing fallback token")
    _assert("Check TerrainMeshCoords or terrain mesh validity." in status, "Sampler-failure status missing next-step guidance")
    _assert("earthwork=full" in status, "Sampler-failure status should report full earthwork")
    App.closeDocument(doc.Name)


def run():
    _run_missing_terrain_case()
    _run_sampler_failure_case()
    print("[PASS] Daylight fallback status smoke test completed.")


if __name__ == "__main__":
    run()
