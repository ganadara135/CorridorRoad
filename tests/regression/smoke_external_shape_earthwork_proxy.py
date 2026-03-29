# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
External-shape indirect earthwork proxy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_external_shape_earthwork_proxy.py
"""

import os
import shutil

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
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


def _write_brep_box(path: str, x_len: float, y_len: float, z_len: float):
    shp = Part.makeBox(float(x_len), float(y_len), float(z_len))
    try:
        shp.exportBrep(path)
        return
    except Exception:
        pass
    txt = shp.exportBrepToString()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(txt)


def run():
    temp_dir = os.path.join(os.getcwd(), "tests", "regression", ".tmp_external_shape_proxy")
    os.makedirs(temp_dir, exist_ok=True)
    shape_path = os.path.join(temp_dir, "proxy_shape.brep")
    doc = None
    try:
        _write_brep_box(shape_path, 12.0, 7.0, 3.0)

        doc = App.newDocument("CRExternalShapeEarthworkProxy")

        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
        Centerline3DDisplay(disp)
        disp.Alignment = aln
        disp.ElevationSource = "FlatZero"
        disp.UseStationing = False

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.UseSideSlopes = True
        asm.LeftWidth = 4.0
        asm.RightWidth = 4.0
        asm.HeightLeft = 4.0
        asm.HeightRight = 4.0
        asm.LeftSideWidth = 3.0
        asm.RightSideWidth = 3.0
        asm.LeftSideSlopePct = 100.0
        asm.RightSideSlopePct = 100.0

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ss.StructureIds = ["EXT_PROXY"]
        ss.StructureTypes = ["culvert"]
        ss.StartStations = [20.0]
        ss.EndStations = [40.0]
        ss.CenterStations = [30.0]
        ss.Sides = ["both"]
        ss.Widths = [1.0]
        ss.Heights = [1.0]
        ss.BehaviorModes = ["assembly_override"]
        ss.GeometryModes = ["external_shape"]
        ss.ShapeSourcePaths = [shape_path]
        ss.ScaleFactors = [1.0]
        ss.PlacementModes = ["center_on_station"]
        ss.UseSourceBaseAsBottoms = ["true"]

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        sec.SourceCenterlineDisplay = disp
        sec.AssemblyTemplate = asm
        sec.Mode = "Range"
        sec.StartStation = 0.0
        sec.EndStation = 60.0
        sec.Interval = 20.0
        sec.UseStructureSet = True
        sec.StructureSet = ss
        sec.ApplyStructureOverrides = True
        sec.IncludeStructureStartEnd = True
        sec.IncludeStructureCenters = True
        sec.CreateChildSections = False

        cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)
        cor.SourceSectionSet = sec
        cor.UseStructureCorridorModes = True
        cor.SplitAtStructureZones = True

        dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
        DesignGradingSurface(dgs)
        dgs.SourceSectionSet = sec

        doc.recompute()

        _assert(_shape_ok(ss), "StructureSet did not generate display geometry")
        _assert(_shape_ok(cor), "CorridorLoft did not generate geometry")
        _assert(int(getattr(ss, "ResolvedEarthworkProxyCount", 0) or 0) == 1, "Expected one external-shape proxy record")
        _assert(list(getattr(ss, "ResolvedEarthworkProxyIds", []) or []) == ["EXT_PROXY"], "Unexpected proxy structure ids")

        ss_status = str(getattr(ss, "Status", "") or "")
        _assert("externalShapeProxy=1" in ss_status, "StructureSet status missing proxy count")
        _assert("externalShapeDisplayOnly=" not in ss_status, "Valid proxy case should not remain display-only")

        resolved = StructureSet.resolve_profile_at_station(ss, "EXT_PROXY", 30.0)
        _assert(str(resolved.get("ResolvedEarthworkProxyMode", "") or "") == "external_shape_bbox", "Resolved record missing proxy mode")
        _assert(abs(float(resolved.get("Width", 0.0) or 0.0) - 7.0) <= 1e-6, "Resolved width should come from external-shape bbox")
        _assert(abs(float(resolved.get("Height", 0.0) or 0.0) - 3.0) <= 1e-6, "Resolved height should come from external-shape bbox")

        sec_status = str(getattr(sec, "Status", "") or "")
        _assert("earthwork=external_shape_proxy" in sec_status, "SectionSet status missing proxy earthwork token")
        _assert("externalShapeProxy=1" in sec_status, "SectionSet status missing proxy count")
        _assert("displayOnly=external_shape" not in sec_status, "SectionSet status should not advertise display-only when proxy is active")

        cor_status = str(getattr(cor, "Status", "") or "")
        _assert("earthwork=external_shape_proxy" in cor_status, "CorridorLoft status missing proxy earthwork token")
        _assert("externalShapeProxy=1" in cor_status, "CorridorLoft status missing proxy count")
        _assert("displayOnly=external_shape" not in cor_status, "CorridorLoft status should not advertise display-only when proxy is active")

        dgs_status = str(getattr(dgs, "Status", "") or "")
        _assert("earthwork=external_shape_proxy" in dgs_status, "DesignGradingSurface status missing proxy earthwork token")
        _assert("externalShapeProxy=1" in dgs_status, "DesignGradingSurface status missing proxy count")
        _assert("displayOnly=external_shape" not in dgs_status, "DesignGradingSurface status should not advertise display-only when proxy is active")

        App.closeDocument(doc.Name)
        doc = None
        print("[PASS] External-shape earthwork proxy smoke test completed.")
    finally:
        if doc is not None:
            try:
                App.closeDocument(doc.Name)
            except Exception:
                pass
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run()
