# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Side-slope bench profile smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_side_slope_bench_profile.py
"""

import FreeCAD as App

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


def _vertex_count(obj) -> int:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return 0
    try:
        return int(len(list(getattr(shp, "Vertexes", []) or [])))
    except Exception:
        return 0


def _mesh_ok(obj) -> bool:
    mesh = getattr(obj, "Mesh", None)
    if mesh is None:
        return False
    try:
        return int(getattr(mesh, "CountFacets", 0) or 0) > 0
    except Exception:
        return False
        return 0


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


def _make_assembly(doc, name, use_left_bench=False):
    asm = doc.addObject("Part::FeaturePython", name)
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
    asm.UseLeftBench = bool(use_left_bench)
    asm.LeftBenchDrop = 1.0
    asm.LeftBenchWidth = 1.5
    asm.LeftBenchSlopePct = 0.0
    asm.LeftPostBenchSlopePct = 60.0
    return asm


def _make_section_set(doc, name, disp, asm):
    sec = doc.addObject("Part::FeaturePython", name)
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 20.0
    sec.Interval = 20.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.DaylightAuto = False
    sec.CreateChildSections = False
    return sec


def _make_corridor(doc, name, sec):
    cor = doc.addObject("Part::FeaturePython", name)
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    return cor


def _make_grading(doc, name, sec):
    dgs = doc.addObject("Mesh::FeaturePython", name)
    DesignGradingSurface(dgs)
    dgs.SourceSectionSet = sec
    return dgs


def run():
    doc = App.newDocument("CRBenchSlopeProfile")

    aln = _make_alignment(doc, length=20.0)
    disp = _make_display(doc, aln)
    asm_base = _make_assembly(doc, "AssemblyBase", use_left_bench=False)
    asm_bench = _make_assembly(doc, "AssemblyBench", use_left_bench=True)
    sec_base = _make_section_set(doc, "SectionSetBase", disp, asm_base)
    sec_bench = _make_section_set(doc, "SectionSetBench", disp, asm_bench)
    cor_bench = _make_corridor(doc, "CorridorBench", sec_bench)
    dgs_bench = _make_grading(doc, "GradingBench", sec_bench)

    doc.recompute()

    _assert(_shape_ok(sec_base), "Baseline section set did not generate geometry")
    _assert(_shape_ok(sec_bench), "Bench-enabled section set did not generate geometry")
    _assert(_shape_ok(cor_bench), "Bench-enabled corridor did not generate geometry")
    _assert(_mesh_ok(dgs_bench), "Bench-enabled grading surface did not generate mesh")
    _assert(_vertex_count(sec_bench) > _vertex_count(sec_base), "Bench-enabled section did not add extra break points")
    _assert(int(getattr(sec_bench, "BenchAppliedSectionCount", 0) or 0) == 2, "Bench section count should be 2")
    _assert(str(getattr(sec_bench, "BenchSummary", "") or "").startswith("mode=left"), "Bench summary should report left bench")
    _assert(len(list(getattr(sec_bench, "BenchSummaryRows", []) or [])) == 1, "Bench summary rows should include one left-side row")
    sec_status = str(getattr(sec_bench, "Status", "") or "")
    _assert("bench=left" in sec_status, "Bench status token missing")
    _assert("benchSections=2" in sec_status, "Bench section-count token missing")
    _assert("daylight=off" in sec_status, "Bench smoke should stay in fixed-width mode")
    cor_status = str(getattr(cor_bench, "Status", "") or "")
    _assert("bench=left" in cor_status, "Corridor status should propagate bench summary")
    _assert("benchSections=2" in cor_status, "Corridor status should propagate bench section count")
    _assert("ruled=auto:bench_profile" in cor_status, "Corridor should auto-enable the ruled fallback for bench profiles")
    _assert(int(getattr(cor_bench, "AutoFixedSectionCount", 0) or 0) == 0, "Bench corridor should keep SectionSet point order without auto-flip")
    _assert(
        len(list(getattr(getattr(cor_bench, "Shape", None), "Faces", []) or []))
        == int(getattr(dgs_bench, "FaceCount", 0) or 0),
        "Bench corridor face count should match grading strip contract",
    )
    dgs_status = str(getattr(dgs_bench, "Status", "") or "")
    _assert("bench=left" in dgs_status, "Design grading surface status should propagate bench summary")
    _assert("benchSections=2" in dgs_status, "Design grading surface status should propagate bench section count")

    App.closeDocument(doc.Name)
    print("[PASS] Side-slope bench profile smoke test completed.")


if __name__ == "__main__":
    run()
