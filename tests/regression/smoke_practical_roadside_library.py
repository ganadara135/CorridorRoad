# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Practical roadside-library smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_practical_roadside_library.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_typical_section_template import (
    TypicalSectionTemplate,
    expand_roadside_library_bundle,
    roadside_library_rows,
    roadside_library_summary,
)


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


def _assign_component_rows(obj, rows):
    obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
    obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
    obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
    obj.ComponentWidths = [float(r.get("Width", 0.0) or 0.0) for r in rows]
    obj.ComponentCrossSlopes = [float(r.get("CrossSlopePct", 0.0) or 0.0) for r in rows]
    obj.ComponentHeights = [float(r.get("Height", 0.0) or 0.0) for r in rows]
    obj.ComponentExtraWidths = [float(r.get("ExtraWidth", 0.0) or 0.0) for r in rows]
    obj.ComponentBackSlopes = [float(r.get("BackSlopePct", 0.0) or 0.0) for r in rows]
    obj.ComponentOffsets = [float(r.get("Offset", 0.0) or 0.0) for r in rows]
    obj.ComponentOrders = [int(r.get("Order", idx + 1) or (idx + 1)) for idx, r in enumerate(rows)]
    obj.ComponentEnabled = [1 if bool(r.get("Enabled", True)) else 0 for r in rows]


def run():
    doc = App.newDocument("CRPracticalRoadsideLibrary")
    try:
        both_ditch = expand_roadside_library_bundle("ditch_edge", "Both")
        _assert(len(both_ditch) == 6, "ditch_edge both-side bundle should expand to 6 rows")
        _assert(
            [str(r.get("Side", "") or "") for r in both_ditch] == ["left", "left", "left", "right", "right", "right"],
            "ditch_edge both-side bundle side order mismatch",
        )
        _assert(
            all(str(r.get("Id", "") or "").endswith("-L") for r in both_ditch[:3]) and
            all(str(r.get("Id", "") or "").endswith("-R") for r in both_ditch[3:]),
            "ditch_edge both-side bundle ids should be mirrored with side suffixes",
        )
        _assert(expand_roadside_library_bundle("ditch_edge", "Center Only") == [], "ditch_edge should not expand to center-only mode")

        median_bundle = expand_roadside_library_bundle("median_core", "Both")
        _assert(len(median_bundle) == 1, "median_core bundle should stay single-row")
        _assert(str(median_bundle[0].get("Side", "") or "") == "center", "median_core bundle should stay center-side")

        rows = [
            {"Id": "LANE-L", "Type": "lane", "Side": "left", "Width": 3.50, "CrossSlopePct": 2.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 10, "Enabled": True},
            {"Id": "LANE-R", "Type": "lane", "Side": "right", "Width": 3.50, "CrossSlopePct": 2.0, "Height": 0.0, "ExtraWidth": 0.0, "BackSlopePct": 0.0, "Offset": 0.0, "Order": 10, "Enabled": True},
        ]
        for bundle_rows in (
            expand_roadside_library_bundle("urban_edge", "Left Only"),
            expand_roadside_library_bundle("ditch_edge", "Right Only"),
            median_bundle,
        ):
            rows.extend(bundle_rows)
        for idx, row in enumerate(rows):
            row["Order"] = int((idx + 1) * 10)

        expected_rows = ["ditch_edge:right", "urban_edge:left", "median_core:center"]
        expected_summary = "ditch_edge:1,median_core:1,urban_edge:1"
        _assert(roadside_library_rows(rows) == expected_rows, "roadside library rows mismatch before object execution")
        _assert(roadside_library_summary(rows) == expected_summary, "roadside library summary mismatch before object execution")

        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(80.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
        Centerline3DDisplay(disp)
        disp.Alignment = aln
        disp.ElevationSource = "FlatZero"
        disp.UseStationing = False

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.UseSideSlopes = True
        asm.LeftSideWidth = 3.0
        asm.RightSideWidth = 3.0
        asm.ShowTemplateWire = True

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        _assign_component_rows(typ, rows)

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        sec.SourceCenterlineDisplay = disp
        sec.AssemblyTemplate = asm
        sec.TypicalSectionTemplate = typ
        sec.UseTypicalSectionTemplate = True
        sec.Mode = "Range"
        sec.StartStation = 0.0
        sec.EndStation = 80.0
        sec.Interval = 20.0
        sec.CreateChildSections = False

        cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)
        cor.SourceSectionSet = sec

        dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
        DesignGradingSurface(dgs)
        dgs.SourceSectionSet = sec

        doc.recompute()

        _assert(_shape_ok(typ), "TypicalSectionTemplate did not generate geometry")
        _assert(str(getattr(typ, "RoadsideLibrarySummary", "") or "") == expected_summary, "TypicalSectionTemplate roadside summary mismatch")
        _assert(list(getattr(typ, "RoadsideLibraryRows", []) or []) == expected_rows, "TypicalSectionTemplate roadside rows mismatch")
        typ_status = str(getattr(typ, "Status", "") or "")
        _assert(f"roadside={expected_summary}" in typ_status, "TypicalSectionTemplate status missing roadside summary")

        _assert(_shape_ok(sec), "SectionSet did not generate geometry")
        _assert(_shape_ok(cor), "Corridor did not generate geometry")
        _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh")

        for obj in (sec, cor, dgs):
            name = str(getattr(obj, "Name", "Object") or "Object")
            _assert(str(getattr(obj, "RoadsideLibrarySummary", "") or "") == expected_summary, f"{name} roadside summary mismatch")
            _assert(list(getattr(obj, "RoadsideLibraryRows", []) or []) == expected_rows, f"{name} roadside rows mismatch")
            status = str(getattr(obj, "Status", "") or "")
            _assert(f"roadside={expected_summary}" in status, f"{name} status missing roadside summary")
            _assert("practical=advanced" in status, f"{name} status missing practical mode summary")

        App.closeDocument(doc.Name)
        print("[PASS] Practical roadside-library smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
