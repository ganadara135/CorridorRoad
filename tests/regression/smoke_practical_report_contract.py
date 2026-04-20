# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Practical report-contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_practical_report_contract.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate


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


def run():
    doc = App.newDocument("CRPracticalReportContract")
    try:
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
        asm.UseSideSlopes = True
        asm.LeftSideWidth = 2.5
        asm.RightSideWidth = 2.5

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        typ.ComponentIds = ["LANE-L", "CURB-L", "LANE-R", "SHL-R"]
        typ.ComponentTypes = ["lane", "curb", "lane", "shoulder"]
        typ.ComponentSides = ["left", "left", "right", "right"]
        typ.ComponentWidths = [3.500, 0.180, 3.500, 1.500]
        typ.ComponentCrossSlopes = [2.0, 0.0, 2.0, 4.0]
        typ.ComponentHeights = [0.0, 0.150, 0.0, 0.0]
        typ.ComponentExtraWidths = [0.0, 0.060, 0.0, 0.0]
        typ.ComponentBackSlopes = [0.0, 1.000, 0.0, 0.0]
        typ.ComponentOffsets = [0.0, 0.0, 0.0, 0.0]
        typ.ComponentOrders = [10, 20, 10, 20]
        typ.ComponentEnabled = [1, 1, 1, 1]
        typ.PavementLayerIds = ["SURF", "BASE"]
        typ.PavementLayerTypes = ["surface", "base"]
        typ.PavementLayerThicknesses = [0.050, 0.180]
        typ.PavementLayerEnabled = [1, 1]

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
        ss.BehaviorModes = ["section_overlay"]
        ss.CorridorModes = ["split_only"]

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        sec.SourceCenterlineDisplay = disp
        sec.AssemblyTemplate = asm
        sec.TypicalSectionTemplate = typ
        sec.UseTypicalSectionTemplate = True
        sec.Mode = "Range"
        sec.StartStation = 0.0
        sec.EndStation = 60.0
        sec.Interval = 20.0
        sec.CreateChildSections = False
        sec.UseStructureSet = True
        sec.StructureSet = ss
        sec.IncludeStructureStartEnd = True
        sec.IncludeStructureCenters = True
        sec.IncludeStructureTransitionStations = False

        cor = doc.addObject("Part::FeaturePython", "Corridor")
        Corridor(cor)
        cor.SourceSectionSet = sec
        cor.UseStructureCorridorModes = True
        cor.SplitAtStructureZones = True

        dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
        DesignGradingSurface(dgs)
        dgs.SourceSectionSet = sec

        doc.recompute()

        _assert(_shape_ok(typ), "TypicalSectionTemplate did not generate geometry")
        _assert(_shape_ok(sec), "SectionSet did not generate geometry")
        _assert(_shape_ok(cor), "Corridor did not generate geometry")
        _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh")

        expected_component_rows = [
            "component|id=LANE-L|type=lane|shape=-|side=left|width=3.500|crossSlopePct=2.000|height=0.000|extraWidth=0.000|backSlopePct=0.000|offset=0.000|order=10",
            "component|id=CURB-L|type=curb|shape=-|side=left|width=0.180|crossSlopePct=0.000|height=0.150|extraWidth=0.060|backSlopePct=1.000|offset=0.000|order=20",
            "component|id=LANE-R|type=lane|shape=-|side=right|width=3.500|crossSlopePct=2.000|height=0.000|extraWidth=0.000|backSlopePct=0.000|offset=0.000|order=10",
            "component|id=SHL-R|type=shoulder|shape=-|side=right|width=1.500|crossSlopePct=4.000|height=0.000|extraWidth=0.000|backSlopePct=0.000|offset=0.000|order=20",
        ]
        expected_pavement_rows = [
            "pavement|id=SURF|type=surface|thickness=0.050",
            "pavement|id=BASE|type=base|thickness=0.180",
        ]
        expected_typ_export = [
            "export|target=typical_section|reportSchema=1|practical=advanced|components=4|advanced=1|pavementLayers=2|pavementTotal=0.230|roadside=shoulder_edge:1|validation=0"
        ]
        expected_structure_rows = [
            "structure|source=structure_set|stations=3|tags=3"
        ]
        expected_sec_export = [
            "export|target=section_set|reportSchema=1|sectionSchema=2|topProfile=typical_section|practical=advanced|sections=6|structures=3|benchSections=0|benchMode=-|benchAdjusted=0|benchSkipped=0|pavementLayers=2|roadside=shoulder_edge:1"
        ]

        _assert(int(getattr(typ, "ReportSchemaVersion", 0) or 0) == 1, "TypicalSectionTemplate report schema mismatch")
        _assert(list(getattr(typ, "SectionComponentSummaryRows", []) or []) == expected_component_rows, "TypicalSectionTemplate component report rows mismatch")
        _assert(list(getattr(typ, "PavementScheduleRows", []) or []) == expected_pavement_rows, "TypicalSectionTemplate pavement schedule rows mismatch")
        _assert(list(getattr(typ, "StructureInteractionSummaryRows", []) or []) == [], "TypicalSectionTemplate should not have structure interaction rows")
        _assert(list(getattr(typ, "ExportSummaryRows", []) or []) == expected_typ_export, "TypicalSectionTemplate export summary mismatch")

        _assert(int(getattr(sec, "ReportSchemaVersion", 0) or 0) == 1, "SectionSet report schema mismatch")
        _assert(list(getattr(sec, "SectionComponentSummaryRows", []) or []) == expected_component_rows, "SectionSet component report rows mismatch")
        _assert(list(getattr(sec, "PavementScheduleRows", []) or []) == expected_pavement_rows, "SectionSet pavement schedule rows mismatch")
        _assert(list(getattr(sec, "StructureInteractionSummaryRows", []) or []) == expected_structure_rows, "SectionSet structure interaction rows mismatch")
        _assert(list(getattr(sec, "ExportSummaryRows", []) or []) == expected_sec_export, "SectionSet export summary mismatch")

        cor_export = list(getattr(cor, "ExportSummaryRows", []) or [])
        _assert(len(cor_export) == 1, "Corridor export summary row missing")
        _assert("export|target=corridor_loft|" in cor_export[0], "Corridor export summary target mismatch")
        _assert("reportSchema=1" in cor_export[0], "Corridor export summary schema mismatch")
        _assert("practical=advanced" in cor_export[0], "Corridor export summary practical mode mismatch")
        _assert("roadside=shoulder_edge:1" in cor_export[0], "Corridor export summary roadside mismatch")
        _assert(list(getattr(cor, "SectionComponentSummaryRows", []) or []) == expected_component_rows, "Corridor component report rows mismatch")
        _assert(list(getattr(cor, "PavementScheduleRows", []) or []) == expected_pavement_rows, "Corridor pavement schedule rows mismatch")
        _assert(list(getattr(cor, "StructureInteractionSummaryRows", []) or []) == expected_structure_rows, "Corridor structure interaction rows mismatch")

        dgs_export = list(getattr(dgs, "ExportSummaryRows", []) or [])
        _assert(len(dgs_export) == 1, "DesignGradingSurface export summary row missing")
        _assert("export|target=design_grading_surface|" in dgs_export[0], "DesignGradingSurface export summary target mismatch")
        _assert("reportSchema=1" in dgs_export[0], "DesignGradingSurface export summary schema mismatch")
        _assert("practical=advanced" in dgs_export[0], "DesignGradingSurface export summary practical mode mismatch")
        _assert("roadside=shoulder_edge:1" in dgs_export[0], "DesignGradingSurface export summary roadside mismatch")
        _assert(list(getattr(dgs, "SectionComponentSummaryRows", []) or []) == expected_component_rows, "DesignGradingSurface component report rows mismatch")
        _assert(list(getattr(dgs, "PavementScheduleRows", []) or []) == expected_pavement_rows, "DesignGradingSurface pavement schedule rows mismatch")
        _assert(list(getattr(dgs, "StructureInteractionSummaryRows", []) or []) == expected_structure_rows, "DesignGradingSurface structure interaction rows mismatch")

        App.closeDocument(doc.Name)
        print("[PASS] Practical report-contract smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
