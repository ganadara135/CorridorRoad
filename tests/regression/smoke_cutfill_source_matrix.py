# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CutFill source-matrix / domain / station-bin smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_cutfill_source_matrix.py
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


def _shape_ok(obj) -> bool:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False


def run():
    doc = App.newDocument("CRCutFillSourceMatrix")
    try:
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
        cfc.ExistingSurfaceCoords = "Local"
        cfc.CellSize = 5.0
        cfc.DomainMargin = 0.0
        cfc.UseCorridorBounds = True
        cfc.MaxSamples = 1000
        cfc.MinMeshFacets = 1
        cfc.ShowDeltaMap = False
        cfc.StationBinSize = 20.0

        doc.recompute()

        _assert(_shape_ok(cor), "Corridor did not generate geometry")
        _assert(_shape_ok(cfc), "CutFillCalc did not generate output shape")

        _assert(int(getattr(cfc, "ComparisonSchemaVersion", 0) or 0) == 1, "Comparison schema mismatch")
        _assert(str(getattr(cfc, "ComparisonSourceMode", "") or "") == "corridor_top_vs_existing_mesh", "Comparison source mode mismatch")
        _assert(str(getattr(cfc, "ComparisonSourceSupport", "") or "") == "supported", "Comparison source support mismatch")
        _assert(
            list(getattr(cfc, "ComparisonSourceSummaryRows", []) or []) == [
                "source|design=corridor_top|existing=mesh|existingCoords=Local|mode=corridor_top_vs_existing_mesh|support=supported"
            ],
            "Comparison source summary rows mismatch",
        )

        _assert(str(getattr(cfc, "AnalysisDomainMode", "") or "") == "corridor_bounds", "Analysis domain mode mismatch")
        domain_rows = list(getattr(cfc, "DomainSummaryRows", []) or [])
        _assert(len(domain_rows) == 1, "Expected one domain summary row")
        _assert("domain|mode=corridor_bounds|coords=Local|" in domain_rows[0], "Domain summary row missing mode")
        _assert("excludedArea=0.000" in domain_rows[0], "Domain summary row missing excluded area")

        _assert(int(getattr(cfc, "SampleCount", 0) or 0) == 16, "Unexpected sample count")
        _assert(int(getattr(cfc, "ValidCount", 0) or 0) == 16, "Unexpected valid count")
        _assert(int(getattr(cfc, "ComparedCellCount", 0) or 0) == 16, "Unexpected compared cell count")
        _assert(int(getattr(cfc, "ExcludedCellCount", 0) or 0) == 0, "Unexpected excluded cell count")
        _assert(abs(float(getattr(cfc, "CutVolume", 0.0) or 0.0)) <= 1e-9, "Cut volume should be zero")
        _assert(abs(float(getattr(cfc, "FillVolume", 0.0) or 0.0) - 180.0) < 1e-6, "Unexpected fill volume")
        _assert(abs(float(getattr(cfc, "DeltaMean", 0.0) or 0.0) - 0.45) < 1e-9, "Unexpected delta mean")
        _assert(str(getattr(cfc, "TrustLevel", "") or "") == "review_ready", "Unexpected trust level")
        _assert(int(getattr(cfc, "TrustBlockerCount", 0) or 0) == 0, "Unexpected trust blocker count")
        _assert(int(getattr(cfc, "FallbackEventCount", 0) or 0) == 0, "Unexpected fallback event count")
        _assert(int(getattr(cfc, "CoordinateTransformCount", 0) or 0) == 0, "Unexpected coordinate-transform count")

        bin_rows = list(getattr(cfc, "StationBinnedSummaryRows", []) or [])
        _assert(len(bin_rows) == 6, "Expected 6 station-binned summary rows")
        _assert(any("stationBin|fromStation=0.000|toStation=20.000|side=all|samples=8|valid=8|" in row and "fill=90.000" in row for row in bin_rows), "Missing first all-side station bin")
        _assert(any("stationBin|fromStation=20.000|toStation=40.000|side=all|samples=8|valid=8|" in row and "fill=90.000" in row for row in bin_rows), "Missing second all-side station bin")
        _assert(any("side=left|samples=4|valid=4|" in row and "fill=45.000" in row for row in bin_rows), "Missing left-side station bin summary")
        _assert(any("side=right|samples=4|valid=4|" in row and "fill=45.000" in row for row in bin_rows), "Missing right-side station bin summary")

        quality_rows = list(getattr(cfc, "QualitySummaryRows", []) or [])
        _assert(any("quality|metric=trust|value=review_ready|state=ok|blockers=0|" in row for row in quality_rows), "Missing trust quality row")
        _assert(any("quality|metric=coverage|comparedCells=16|excludedCells=0|noDataRatio=0.000000" in row for row in quality_rows), "Missing coverage quality row")
        review_rows = list(getattr(cfc, "ReviewSummaryRows", []) or [])
        _assert(any("review|metric=overall|trust=review_ready|cut=0.000|fill=180.000|" in row for row in review_rows), "Missing overall review row")
        _assert(any("review|metric=max_fill_bin|side=all|fromStation=0.000|toStation=20.000|fill=90.000" in row for row in review_rows), "Missing max-fill review row")
        export_rows = list(getattr(cfc, "ExportSummaryRows", []) or [])
        _assert(export_rows == ["export|target=cut_fill_calc|schema=1|source=corridor_top_vs_existing_mesh|trust=review_ready|comparedCells=16|noDataRatio=0.000000|cut=0.000|fill=180.000|bins=6"], "Unexpected export summary rows")

        status = str(getattr(cfc, "Status", "") or "")
        _assert("trust=review_ready" in status, "Status missing trust token")
        _assert("sourceMatrix=corridor_top_vs_existing_mesh:supported" in status, "Status missing source matrix token")
        _assert("domain=corridor_bounds" in status, "Status missing domain token")
        _assert("bins=6" in status, "Status missing station-bin count")

        App.closeDocument(doc.Name)
        print("[PASS] CutFill source-matrix smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
