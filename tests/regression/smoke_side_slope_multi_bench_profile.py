# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Side-slope multi-bench profile smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_side_slope_multi_bench_profile.py
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


def _make_alignment(doc, length=24.0):
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


def _make_assembly(doc, name, extra_rows=None):
    asm = doc.addObject("Part::FeaturePython", name)
    AssemblyTemplate(asm)
    asm.LeftWidth = 4.0
    asm.RightWidth = 4.0
    asm.LeftSlopePct = -2.0
    asm.RightSlopePct = 2.0
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 10.0
    asm.RightSideWidth = 0.0
    asm.LeftSideSlopePct = 50.0
    asm.RightSideSlopePct = 50.0
    asm.UseLeftBench = True
    asm.LeftBenchDrop = 1.0
    asm.LeftBenchWidth = 1.5
    asm.LeftBenchSlopePct = 0.0
    asm.LeftPostBenchSlopePct = 60.0
    asm.LeftBenchRows = list(extra_rows or [])
    return asm


def _make_section_set(doc, name, disp, asm):
    sec = doc.addObject("Part::FeaturePython", name)
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 24.0
    sec.Interval = 24.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.DaylightAuto = False
    sec.CreateChildSections = False
    return sec


def run():
    doc = App.newDocument("CRMultiBenchProfile")

    aln = _make_alignment(doc)
    disp = _make_display(doc, aln)
    asm_single = _make_assembly(doc, "AssemblySingleBench", [])
    asm_multi = _make_assembly(
        doc,
        "AssemblyMultiBench",
        [
            "drop=0.8|width=1.0|slope=0|post=55",
            "drop=0.6|width=0.8|slope=0|post=70",
        ],
    )
    sec_single = _make_section_set(doc, "SectionSetSingleBench", disp, asm_single)
    sec_multi = _make_section_set(doc, "SectionSetMultiBench", disp, asm_multi)
    cor_multi = doc.addObject("Part::FeaturePython", "CorridorMultiBench")
    CorridorLoft(cor_multi)
    cor_multi.SourceSectionSet = sec_multi
    dgs_multi = doc.addObject("Mesh::FeaturePython", "GradingMultiBench")
    DesignGradingSurface(dgs_multi)
    dgs_multi.SourceSectionSet = sec_multi

    doc.recompute()

    _assert(_shape_ok(sec_single), "Single-bench section set did not generate geometry")
    _assert(_shape_ok(sec_multi), "Multi-bench section set did not generate geometry")
    _assert(_shape_ok(cor_multi), "Multi-bench corridor did not generate geometry")
    _assert(_mesh_ok(dgs_multi), "Multi-bench grading surface did not generate mesh")
    _assert(_vertex_count(sec_multi) > _vertex_count(sec_single), "Multi-bench section should add more break points than single bench")

    asm_status = str(getattr(asm_multi, "Status", "") or "")
    _assert("bench=left(3)" in asm_status, "AssemblyTemplate should report three configured left benches")

    _assert(int(getattr(sec_multi, "BenchAppliedSectionCount", 0) or 0) == 2, "Multi-bench section count should be 2")
    sec_summary = str(getattr(sec_multi, "BenchSummary", "") or "")
    _assert("mode=left" in sec_summary, "Bench summary should report left-side benching")
    _assert("left=2/3" in sec_summary, "Bench summary should report visible/configured left bench counts")
    rows = list(getattr(sec_multi, "BenchSummaryRows", []) or [])
    _assert(len(rows) == 1, "Bench summary rows should include one left-side row")
    _assert("mode=multi" in rows[0], "Bench summary row should report multi-bench mode")
    _assert("benches=3" in rows[0], "Bench summary row should report three configured benches")

    sec_status = str(getattr(sec_multi, "Status", "") or "")
    _assert("bench=left" in sec_status, "SectionSet status missing bench side token")
    _assert("benchSections=2" in sec_status, "SectionSet status missing bench section count")
    cor_status = str(getattr(cor_multi, "Status", "") or "")
    _assert("bench=left" in cor_status, "Corridor status should propagate multi-bench summary")
    _assert("benchSections=2" in cor_status, "Corridor status should propagate multi-bench section count")
    _assert("ruled=auto:bench_profile" in cor_status, "Corridor should auto-enable ruled loft for multi-bench profiles")
    dgs_status = str(getattr(dgs_multi, "Status", "") or "")
    _assert("bench=left" in dgs_status, "Design grading surface status should propagate multi-bench summary")
    _assert("benchSections=2" in dgs_status, "Design grading surface status should propagate multi-bench section count")

    App.closeDocument(doc.Name)
    print("[PASS] Side-slope multi-bench profile smoke test completed.")


if __name__ == "__main__":
    run()
