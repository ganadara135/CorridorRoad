# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
HorizontalAlignment transition-geometry diagnostics smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_alignment_transition_geometry.py', 'r', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay


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
    doc = App.newDocument("CRAlignTransitionDiag")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [
        App.Vector(0.0, 0.0, 0.0),
        App.Vector(300.0, 0.0, 0.0),
        App.Vector(520.0, 180.0, 0.0),
    ]
    aln.CurveRadii = [0.0, 120.0, 0.0]
    aln.TransitionLengths = [0.0, 60.0, 0.0]
    aln.UseTransitionCurves = True
    aln.SpiralSegments = 16

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False
    disp.UseKeyStations = False
    disp.SegmentByRegions = False
    disp.SegmentByStructures = False

    doc.recompute()

    _assert(_shape_ok(aln), "HorizontalAlignment did not generate geometry")
    _assert(_shape_ok(disp), "Centerline3DDisplay did not generate geometry")
    _assert(str(getattr(aln, "TransitionGeometryMode", "") or "") == "BSplineSpiral", "Expected BSpline spiral transition diagnostics")
    _assert(int(getattr(aln, "TransitionCornerCount", 0) or 0) >= 1, "Expected at least one transition corner")
    _assert(int(getattr(aln, "TransitionSplineEdgeCount", 0) or 0) >= 2, "Expected spline edges in transition diagnostics")
    _assert(int(getattr(aln, "TransitionPolylineEdgeCount", 0) or 0) == 0, "Expected no polyline-edge fallback in transition diagnostics")
    _assert(int(getattr(aln, "ArcEdgeCount", 0) or 0) > 0, "Expected at least one arc edge in alignment diagnostics")
    _assert(int(getattr(aln, "SplineEdgeCount", 0) or 0) >= 2, "Expected spline edges in overall alignment diagnostics")

    edge_summary = str(getattr(aln, "EdgeTypeSummary", "") or "")
    _assert("transition_spline:" in edge_summary, "Missing transition spline summary token")
    _assert("spline:" in edge_summary, "Missing spline summary token")
    _assert("arc:" in edge_summary, "Missing arc summary token")

    _assert(str(getattr(disp, "DisplayWireMode", "") or "") == "SmoothSpline", "Expected default requested wire mode to be SmoothSpline")
    _assert(str(getattr(disp, "ActiveWireDisplayMode", "") or "") == "SmoothSpline", "Expected current display mode diagnostics to report SmoothSpline")
    _assert(str(getattr(disp, "SourceTransitionGeometry", "") or "") == "BSplineSpiral", "Expected display to expose source transition geometry mode")
    _assert("transition_spline:" in str(getattr(disp, "SourceEdgeTypeSummary", "") or ""), "Expected display to expose source edge summary")

    disp.DisplayWireMode = "Polyline"
    doc.recompute()
    _assert(str(getattr(disp, "ActiveWireDisplayMode", "") or "") == "Polyline", "Expected Polyline mode after explicit toggle")

    App.closeDocument(doc.Name)
    print("[PASS] HorizontalAlignment transition-geometry diagnostics smoke test completed.")


if __name__ == "__main__":
    run()
