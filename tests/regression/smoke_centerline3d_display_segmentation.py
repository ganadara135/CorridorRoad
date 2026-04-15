# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
3D centerline display semantic segmentation smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_centerline3d_display_segmentation.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
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


def _boundary_children(doc, parent):
    out = []
    for obj in list(getattr(doc, "Objects", []) or []):
        try:
            if not str(getattr(obj, "Name", "") or "").startswith("CenterlineBoundaryMarker"):
                continue
            if getattr(obj, "ParentCenterline3DDisplay", None) != parent:
                continue
            out.append(obj)
        except Exception:
            continue
    return out


def _editor_mode(obj, prop):
    try:
        return list(obj.getEditorMode(prop) or [])
    except Exception:
        return None


def run():
    doc = App.newDocument("CRCenterlineDisplaySeg")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    reg.RegionIds = ["BASE_MAIN", "OVR_DITCH"]
    reg.RegionTypes = ["roadway", "ditch_override"]
    reg.Layers = ["base", "overlay"]
    reg.StartStations = [0.0, 40.0]
    reg.EndStations = [100.0, 60.0]
    reg.Priorities = [0, 10]
    reg.TransitionIns = [0.0, 5.0]
    reg.TransitionOuts = [0.0, 3.0]
    reg.EnabledFlags = ["true", "true"]

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["CULV_A"]
    ss.StructureTypes = ["culvert"]
    ss.StartStations = [48.0]
    ss.EndStations = [54.0]
    ss.CenterStations = [51.0]
    ss.Sides = ["both"]
    ss.Widths = [6.0]
    ss.Heights = [2.5]
    ss.BehaviorModes = ["section_overlay"]
    ss.CorridorModes = ["skip_zone"]

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.RegionPlanSource = reg
    disp.StructureSetSource = ss
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False
    disp.UseKeyStations = False
    disp.SegmentByRegions = True
    disp.SegmentByStructures = True

    doc.recompute()

    _assert(_shape_ok(disp), "Centerline3DDisplay did not generate geometry")
    _assert(str(getattr(disp, "Status", "") or "") == "OK", "Centerline3DDisplay status should be OK")
    _assert(str(getattr(disp, "DisplayWireMode", "") or "") == "SmoothSpline", "Expected default display wire mode to be SmoothSpline")
    _assert(str(getattr(disp, "ActiveWireDisplayMode", "") or "") == "SmoothSpline", "Expected resolved active wire mode to be SmoothSpline")
    _assert(int(getattr(disp, "SegmentCount", 0) or 0) >= 6, "Expected semantic display segmentation")
    _assert(int(getattr(disp, "BoundaryMarkerCount", 0) or 0) >= 4, "Expected boundary marker child objects")
    _assert("Hidden" in _editor_mode(disp, "MaxChordError"), "MaxChordError should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "MinStep"), "MinStep should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "MaxStep"), "MaxStep should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "DisplayQuality"), "DisplayQuality should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "DisplayStations"), "DisplayStations should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "DisplayPoints"), "DisplayPoints should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "DisplayPointCount"), "DisplayPointCount should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "DisplayPolicySummary"), "DisplayPolicySummary should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "MostDetailedSegmentSummary"), "MostDetailedSegmentSummary should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "SegmentRows"), "SegmentRows should be hidden from normal property editing")
    _assert("Hidden" in _editor_mode(disp, "BoundaryMarkerRows"), "BoundaryMarkerRows should be hidden from normal property editing")
    _assert(int(getattr(disp, "DisplayPointCount", 0) or 0) > 0, "DisplayPointCount should be populated")
    _assert(not hasattr(disp, "SampledStations"), "Legacy SampledStations should be removed")
    _assert(not hasattr(disp, "SampledPoints"), "Legacy SampledPoints should be removed")
    _assert(not hasattr(disp, "SampleCount"), "Legacy SampleCount should be removed")
    _assert(not hasattr(disp, "SamplingPolicySummary"), "Legacy SamplingPolicySummary should be removed")
    _assert(not hasattr(disp, "DensestSegmentSummary"), "Legacy DensestSegmentSummary should be removed")
    _assert(len(_boundary_children(doc, disp)) == int(getattr(disp, "BoundaryMarkerCount", 0) or 0), "Boundary marker child count mismatch")
    _assert(str(getattr(disp, "BoundaryMarkerKindSummary", "") or "") != "-", "Boundary marker kind summary should be populated")

    split_summary = str(getattr(disp, "SegmentSplitSourceSummary", "") or "")
    _assert("region_base_start" in split_summary, "Missing base-region split source")
    _assert("region_overlay_transition" in split_summary, "Missing overlay transition split source")
    _assert("structure_boundary" in split_summary, "Missing structure boundary split source")
    _assert("structure_transition" in split_summary, "Missing structure transition split source")
    _assert("stationing" not in split_summary, "Display should not include stationing sources when UseKeyStations is off")

    kind_summary = str(getattr(disp, "SegmentKindSummary", "") or "")
    _assert("region_transition" in kind_summary, "Missing region-transition segment classification")
    _assert("structure_transition" in kind_summary or "structure_zone" in kind_summary, "Missing structure segment classification")

    rows = list(getattr(disp, "SegmentRows", []) or [])
    marker_rows = list(getattr(disp, "BoundaryMarkerRows", []) or [])
    _assert(any("points=" in row for row in rows), "Segment diagnostic rows should report display-point counts")
    _assert(any("kind=region_transition" in row for row in rows), "Expected at least one region-transition segment row")
    _assert(any("kind=structure_transition" in row or "kind=structure_zone" in row for row in rows), "Expected at least one structure-aware segment row")
    _assert(any("kind=region_transition" in row for row in marker_rows), "Expected at least one region-transition boundary marker row")
    _assert(any("kind=structure_transition" in row or "kind=structure_zone" in row for row in marker_rows), "Expected at least one structure-aware boundary marker row")
    _assert(not any("kind=endpoint" in row for row in marker_rows), "Endpoint markers should be hidden by default")

    disp.IncludeEndpointBoundaryMarkers = True
    doc.recompute()
    marker_rows_with_endpoints = list(getattr(disp, "BoundaryMarkerRows", []) or [])
    _assert(any("kind=endpoint" in row for row in marker_rows_with_endpoints), "Endpoint markers should appear when enabled")
    _assert(int(getattr(disp, "BoundaryMarkerCount", 0) or 0) >= len(marker_rows) + 2, "Endpoint marker toggle should increase marker count")

    disp.DisplayWireMode = "Polyline"
    doc.recompute()
    _assert(str(getattr(disp, "ActiveWireDisplayMode", "") or "") == "Polyline", "Expected Polyline mode after explicit toggle")

    App.closeDocument(doc.Name)
    print("[PASS] 3D centerline display semantic segmentation smoke test completed.")


if __name__ == "__main__":
    run()
