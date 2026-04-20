# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Side-slope bench + daylight smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_side_slope_bench_daylight.py
"""

import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
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


def _mesh_ok(obj) -> bool:
    mesh = getattr(obj, "Mesh", None)
    if mesh is None:
        return False
    try:
        return int(getattr(mesh, "CountFacets", 0) or 0) > 0
    except Exception:
        return False


def _make_alignment(doc, length=20.0):
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
    asm.LeftSlopePct = -2.0
    asm.RightSlopePct = 2.0
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 6.0
    asm.RightSideWidth = 0.0
    asm.LeftSideSlopePct = 50.0
    asm.RightSideSlopePct = 50.0
    asm.UseLeftBench = True
    asm.LeftBenchDrop = 1.0
    asm.LeftBenchWidth = 1.5
    asm.LeftBenchSlopePct = 0.0
    asm.LeftPostBenchSlopePct = 60.0
    return asm


def _plane_z(x: float, y: float) -> float:
    return 0.2 + 0.1 * float(y) + 0.05 * float(x)


def _make_mesh_feature(doc, name):
    obj = doc.addObject("Mesh::Feature", name)
    mesh = Mesh.Mesh()
    p00 = App.Vector(0.0, 0.0, _plane_z(0.0, 0.0))
    p10 = App.Vector(20.0, 0.0, _plane_z(20.0, 0.0))
    p01 = App.Vector(0.0, 20.0, _plane_z(0.0, 20.0))
    p11 = App.Vector(20.0, 20.0, _plane_z(20.0, 20.0))
    mesh.addFacet(p00, p10, p11)
    mesh.addFacet(p00, p11, p01)
    obj.Mesh = mesh
    if not hasattr(obj, "OutputCoords"):
        obj.addProperty("App::PropertyString", "OutputCoords", "Source", "Terrain coordinate mode")
    obj.OutputCoords = "Local"
    return obj


def _make_section_set(doc, disp, asm, terrain):
    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 2.0
    sec.EndStation = 18.0
    sec.Interval = 16.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.DaylightAuto = True
    sec.TerrainMesh = terrain
    sec.TerrainMeshCoords = "Local"
    sec.CreateChildSections = False
    return sec


def run():
    doc = App.newDocument("CRBenchDaylight")

    aln = _make_alignment(doc, length=20.0)
    disp = _make_display(doc, aln)
    asm = _make_assembly(doc)
    terrain = _make_mesh_feature(doc, "TerrainMesh")
    sec = _make_section_set(doc, disp, asm, terrain)
    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
    DesignGradingSurface(dgs)
    dgs.SourceSectionSet = sec

    doc.recompute()

    _assert(_shape_ok(sec), "Bench+daylight SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Bench+daylight Corridor did not generate geometry")
    _assert(_mesh_ok(dgs), "Bench+daylight DesignGradingSurface did not generate mesh")
    _assert(int(getattr(sec, "BenchAppliedSectionCount", 0) or 0) == 1, "Exactly one section should retain a visible bench")
    _assert(int(getattr(sec, "BenchDaylightAdjustedSectionCount", 0) or 0) == 2, "Both sections should be daylight-adjusted")
    _assert(int(getattr(sec, "BenchDaylightSkippedSectionCount", 0) or 0) == 1, "One section should lose the bench before it starts")
    rows = list(getattr(sec, "BenchSummaryRows", []) or [])
    _assert(len(rows) == 1, "Bench summary should contain one left-side row")
    _assert("daylightAdjusted=2" in rows[0], "Bench summary row missing daylight-adjusted count")
    _assert("daylightSkipped=1" in rows[0], "Bench summary row missing daylight-skipped count")

    sec_status = str(getattr(sec, "Status", "") or "")
    _assert("daylight=terrain:local" in sec_status, "SectionSet status missing daylight terrain token")
    _assert("bench=left" in sec_status, "SectionSet status missing bench side token")
    _assert("benchSections=1" in sec_status, "SectionSet status missing visible bench count")
    _assert("benchDayAdj=2" in sec_status, "SectionSet status missing bench daylight-adjusted count")
    _assert("benchDaySkip=1" in sec_status, "SectionSet status missing bench daylight-skipped count")

    cor_status = str(getattr(cor, "Status", "") or "")
    _assert("bench=left" in cor_status, "Corridor status missing bench side token")
    _assert("benchSections=1" in cor_status, "Corridor status missing visible bench count")
    _assert("benchDayAdj=2" in cor_status, "Corridor status missing bench daylight-adjusted count")
    _assert("benchDaySkip=1" in cor_status, "Corridor status missing bench daylight-skipped count")
    _assert("ruled=auto:bench_profile" in cor_status, "Corridor should auto-enable ruled mode for bench profiles")

    dgs_status = str(getattr(dgs, "Status", "") or "")
    _assert("bench=left" in dgs_status, "DesignGradingSurface status missing bench side token")
    _assert("benchSections=1" in dgs_status, "DesignGradingSurface status missing visible bench count")
    _assert("benchDayAdj=2" in dgs_status, "DesignGradingSurface status missing bench daylight-adjusted count")
    _assert("benchDaySkip=1" in dgs_status, "DesignGradingSurface status missing bench daylight-skipped count")

    App.closeDocument(doc.Name)
    print("[PASS] Side-slope bench + daylight smoke test completed.")


if __name__ == "__main__":
    run()
