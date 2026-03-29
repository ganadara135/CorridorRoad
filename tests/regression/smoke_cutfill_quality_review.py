# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CutFill quality / trust smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_cutfill_quality_review.py
"""

import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_cut_fill_calc import CutFillCalc
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _base_setup(doc_name: str):
    doc = App.newDocument(doc_name)
    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(40.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False

    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.LeftWidth = 5.0
    asm.RightWidth = 5.0
    asm.HeightLeft = 1.0
    asm.HeightRight = 1.0
    asm.UseSideSlopes = False

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 40.0
    sec.Interval = 20.0
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec

    existing = doc.addObject("Mesh::Feature", "ExistingSurface")
    mesh = Mesh.Mesh()
    p00 = App.Vector(0.0, -5.0, -0.5)
    p10 = App.Vector(40.0, -5.0, -0.5)
    p01 = App.Vector(0.0, 5.0, -0.5)
    p11 = App.Vector(40.0, 5.0, -0.5)
    mesh.addFacet(p00, p10, p11)
    mesh.addFacet(p00, p11, p01)
    existing.Mesh = mesh

    cfc = doc.addObject("Part::FeaturePython", "CutFillCalc")
    CutFillCalc(cfc)
    cfc.SourceCorridor = cor
    cfc.ExistingSurface = existing
    cfc.CellSize = 5.0
    cfc.MaxSamples = 2000
    cfc.MinMeshFacets = 1
    cfc.ShowDeltaMap = False
    cfc.StationBinSize = 20.0
    return doc, cfc


def _assert_row_contains(rows, text, msg):
    _assert(any(text in row for row in list(rows or [])), msg)


def run():
    doc, cfc = _base_setup("CRCutFillQualityWarn")
    try:
        cfc.ExistingSurfaceCoords = "World"
        cfc.UseCorridorBounds = False
        cfc.DomainCoords = "World"
        cfc.XMin = 0.0
        cfc.XMax = 40.0
        cfc.YMin = -5.0
        cfc.YMax = 5.0

        doc.recompute()

        _assert(str(getattr(cfc, "TrustLevel", "") or "") == "review_with_warnings", "Expected review_with_warnings trust level")
        _assert(int(getattr(cfc, "TrustBlockerCount", 0) or 0) == 0, "Unexpected trust blocker count in warning scenario")
        _assert(int(getattr(cfc, "CoordinateTransformCount", 0) or 0) == 2, "Expected both existing/world and manual/world transforms")
        _assert(int(getattr(cfc, "FallbackEventCount", 0) or 0) == 0, "Unexpected fallback events in warning scenario")
        _assert(str(getattr(cfc, "AnalysisDomainMode", "") or "") == "manual_bounds_world", "Unexpected domain mode in warning scenario")
        _assert_row_contains(getattr(cfc, "QualitySummaryRows", []), "quality|metric=trust|value=review_with_warnings|state=warn|blockers=0|", "Missing trust quality row for warning scenario")
        _assert_row_contains(getattr(cfc, "QualitySummaryRows", []), "quality|metric=fallbacks|fallbackEvents=0|coordinateTransforms=2", "Missing transform quality row")
        _assert_row_contains(getattr(cfc, "ExportSummaryRows", []), "export|target=cut_fill_calc|schema=1|source=corridor_top_vs_existing_mesh|trust=review_with_warnings|", "Missing warning export row")
        status = str(getattr(cfc, "Status", "") or "")
        _assert("trust=review_with_warnings" in status, "Status missing warning trust token")
        _assert("coordXf=2" in status, "Status missing coordinate-transform count")

        App.closeDocument(doc.Name)
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass

    doc2, cfc2 = _base_setup("CRCutFillQualityBlock")
    try:
        cfc2.UseCorridorBounds = False
        cfc2.DomainCoords = "Local"
        cfc2.XMin = 0.0
        cfc2.XMax = 40.0
        cfc2.YMin = -10.0
        cfc2.YMax = 10.0
        cfc2.NoDataWarnRatio = 0.05

        doc2.recompute()

        _assert(str(getattr(cfc2, "TrustLevel", "") or "") == "low_confidence", "Expected low_confidence trust level")
        _assert(int(getattr(cfc2, "TrustBlockerCount", 0) or 0) >= 1, "Expected at least one trust blocker")
        _assert(float(getattr(cfc2, "NoDataRatio", 0.0) or 0.0) > 0.05, "Expected elevated no-data ratio")
        _assert_row_contains(getattr(cfc2, "QualitySummaryRows", []), "quality|metric=trust|value=low_confidence|state=block|", "Missing trust quality row for blocker scenario")
        _assert_row_contains(getattr(cfc2, "ReviewSummaryRows", []), "review|metric=coverage|noDataRatio=", "Missing review coverage row")
        status2 = str(getattr(cfc2, "Status", "") or "")
        _assert(status2.startswith("WARN: trust=low_confidence"), "Status should escalate to warning for blocker scenario")

        App.closeDocument(doc2.Name)
        print("[PASS] CutFill quality-review smoke test completed.")
    finally:
        try:
            App.closeDocument(doc2.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
