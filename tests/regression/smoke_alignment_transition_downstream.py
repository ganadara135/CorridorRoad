# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
HorizontalAlignment transition downstream stability smoke test.

This locks the contract that:
1. transition-enabled alignments prefer spline source edges
2. station round-trip and frame evaluation remain stable
3. SectionSet / StructureSet downstream station consumers still behave correctly

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_alignment_transition_downstream.py', 'r', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
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


def _unique_sorted(values, digits=3):
    out = []
    seen = set()
    for value in list(values or []):
        key = round(float(value), digits)
        if key in seen:
            continue
        seen.add(key)
        out.append(float(key))
    return sorted(out)


def run():
    doc = App.newDocument("CRAlignTransitionDownstream")
    try:
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

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.UseSideSlopes = False

        doc.recompute()

        _assert(_shape_ok(aln), "HorizontalAlignment did not generate geometry")
        _assert(_shape_ok(disp), "Centerline3DDisplay did not generate geometry")
        _assert(str(getattr(aln, "TransitionGeometryMode", "") or "") == "BSplineSpiral", "Expected BSpline spiral source geometry")
        _assert(str(getattr(disp, "ActiveWireDisplayMode", "") or "") == "SmoothSpline", "Expected SmoothSpline display mode")

        ts_vals = list(getattr(aln, "TSKeyStations", []) or [])
        sc_vals = list(getattr(aln, "SCKeyStations", []) or [])
        cs_vals = list(getattr(aln, "CSKeyStations", []) or [])
        st_vals = list(getattr(aln, "STKeyStations", []) or [])
        _assert(len(ts_vals) >= 1 and len(sc_vals) >= 1 and len(cs_vals) >= 1 and len(st_vals) >= 1, "Expected transition key stations")

        ts = float(ts_vals[0])
        sc = float(sc_vals[0])
        cs = float(cs_vals[0])
        st = float(st_vals[0])
        total = float(getattr(aln, "TotalLength", 0.0) or 0.0)
        _assert(0.0 < ts < sc < cs < st < total, "Transition key stations should be monotonic")

        probe_stations = [ts, sc, 0.5 * (sc + cs), cs, st]
        for station in probe_stations:
            p = HorizontalAlignment.point_at_station(aln, station)
            back = float(HorizontalAlignment.station_at_xy(aln, float(p.x), float(p.y), samples_per_edge=256))
            _assert(abs(back - station) <= 1.0, f"Station round-trip drift too large at {station:.3f}: {back:.3f}")

            t = HorizontalAlignment.tangent_at_station(aln, station)
            _assert(float(getattr(t, "Length", 0.0) or 0.0) > 0.99, f"Horizontal tangent length invalid at {station:.3f}")

            frame = Centerline3D.frame_at_station(disp, station)
            _assert(float(getattr(frame.get('T'), 'Length', 0.0) or 0.0) > 0.99, f"3D frame tangent invalid at {station:.3f}")
            _assert(float(getattr(frame.get('N'), 'Length', 0.0) or 0.0) > 0.99, f"3D frame normal invalid at {station:.3f}")

        struct_start = round(sc + 5.0, 3)
        struct_end = round(cs - 5.0, 3)
        struct_center = round(0.5 * (struct_start + struct_end), 3)
        _assert(struct_start < struct_center < struct_end, "Structure probe stations should be monotonic")

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ss.StructureIds = ["CURVE_BOX"]
        ss.StructureTypes = ["culvert"]
        ss.StartStations = [struct_start]
        ss.EndStations = [struct_end]
        ss.CenterStations = [struct_center]
        ss.Sides = ["both"]
        ss.Widths = [6.0]
        ss.Heights = [2.5]

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        sec.SourceCenterlineDisplay = disp
        sec.AssemblyTemplate = asm
        sec.Mode = "Range"
        sec.StartStation = 0.0
        sec.EndStation = total
        sec.Interval = total
        sec.IncludeAlignmentIPStations = False
        sec.IncludeAlignmentSCCSStations = True
        sec.UseStructureSet = True
        sec.StructureSet = ss
        sec.IncludeStructureStartEnd = True
        sec.IncludeStructureCenters = True
        sec.IncludeStructureTransitionStations = False
        sec.CreateChildSections = False
        sec.AutoRebuildChildren = False

        doc.recompute()

        _assert(_shape_ok(sec), "SectionSet did not generate geometry")
        expected_stations = _unique_sorted([0.0, total, ts, sc, cs, st, struct_start, struct_center, struct_end])
        actual_stations = _unique_sorted(list(getattr(sec, "StationValues", []) or []))
        _assert(actual_stations == expected_stations, f"SectionSet merged station values mismatch: got={actual_stations}, want={expected_stations}")
        _assert(int(getattr(sec, "ResolvedStructureCount", 0) or 0) == 3, "SectionSet resolved structure station count mismatch")

        metadata = SectionSet.resolve_structure_metadata(sec, [struct_center])
        _assert(len(metadata) == 1 and bool(metadata[0].get("HasStructure", False)), "Structure metadata should resolve at structure center")
        _assert(metadata[0].get("StructureIds", []) == ["CURVE_BOX"], "Structure metadata should resolve structure id")

        stations, wires, _terrain_found, _sampler_ok, _bench_info = SectionSet.build_section_wires(sec)
        built_stations = _unique_sorted(stations)
        _assert(built_stations == expected_stations, f"Built section-wire stations mismatch: got={built_stations}, want={expected_stations}")
        _assert(len(list(wires or [])) == len(expected_stations), "Expected one section wire per resolved station")

        print("[PASS] HorizontalAlignment transition downstream stability smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
