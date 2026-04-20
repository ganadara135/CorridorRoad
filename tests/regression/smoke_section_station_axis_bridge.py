# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
SectionSet station-axis bridge smoke test for meter-native projects.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_section_station_axis_bridge.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _assert_station_values(actual, expected, msg):
    got = [round(float(v), 3) for v in list(actual or [])]
    want = [round(float(v), 3) for v in list(expected or [])]
    _assert(got == want, f"{msg}: got={got}, want={want}")


def run():
    doc = App.newDocument("CRSectionStationAxisBridge")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)

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

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ss.StructureIds = ["CULV_A"]
        ss.StructureTypes = ["culvert"]
        ss.StartStations = [20.0]
        ss.EndStations = [30.0]
        ss.CenterStations = [25.0]
        ss.Sides = ["both"]
        ss.Widths = [6.0]
        ss.Heights = [2.5]

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
        sec.UseStructureSet = True
        sec.StructureSet = ss
        sec.IncludeStructureStartEnd = True
        sec.IncludeStructureCenters = True
        sec.IncludeStructureTransitionStations = False
        sec.CreateStructureTaggedChildren = True
        sec.CreateChildSections = True
        sec.AutoRebuildChildren = True

        doc.recompute()

        _assert(abs(float(getattr(aln, "TotalLength", 0.0) or 0.0) - 60.0) < 1.0e-6, "Alignment total length should publish meters")
        _assert_station_values(sec.StationValues, [0.0, 20.0, 25.0, 30.0, 40.0, 60.0], "SectionSet station values should publish meters")
        _assert(int(getattr(sec, "ResolvedStructureCount", 0) or 0) == 3, "Structure key station count mismatch")

        metadata = SectionSet.resolve_structure_metadata(sec, [25.0])
        _assert(len(metadata) == 1 and bool(metadata[0].get("HasStructure", False)), "Structure metadata should resolve on meter station input")
        _assert(metadata[0].get("StructureIds", []) == ["CULV_A"], "Structure metadata should resolve the structure id")
        _assert("active" in list(metadata[0].get("StructureRoles", []) or []), "Structure metadata should mark active role")

        print("[PASS] SectionSet station-axis bridge smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
