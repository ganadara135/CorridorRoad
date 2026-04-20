# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
AssemblyTemplate unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_assembly_template_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate, ensure_assembly_template_properties
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


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
    doc = App.newDocument("CRAssemblyTemplateUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "m"

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        ensure_assembly_template_properties(asm)

        _assert(abs(float(getattr(asm, "LeftWidth", 0.0) or 0.0) - 4.0) < 1.0e-9, "New default left width should be stored in meters")
        _assert(abs(float(getattr(asm, "DaylightSearchStep", 0.0) or 0.0) - 1.0) < 1.0e-9, "New daylight step should be stored in meters")

        asm.LeftWidth = 4.0
        asm.RightWidth = 4.0
        asm.LeftSideWidth = 6.0
        asm.RightSideWidth = 6.0
        asm.LeftBenchDrop = 1.0
        asm.LeftBenchWidth = 1.5
        asm.LeftBenchRows = ["drop=1.000000|width=1.500000|slope=0.000000|post=50.000000"]
        asm.DaylightSearchStep = 1.0
        asm.DaylightMaxSearchWidth = 200.0
        asm.HeightLeft = 0.3
        asm.HeightRight = 0.3
        asm.LengthSchemaVersion = 0

        ensure_assembly_template_properties(asm)
        doc.recompute()

        _assert(abs(float(getattr(asm, "LeftWidth", 0.0) or 0.0) - 4.0) < 1.0e-9, "Assembly width should remain meter-native after schema refresh")
        _assert(abs(float(getattr(asm, "LeftSideWidth", 0.0) or 0.0) - 6.0) < 1.0e-9, "Assembly side width should remain meter-native after schema refresh")
        _assert(abs(float(getattr(asm, "LeftBenchDrop", 0.0) or 0.0) - 1.0) < 1.0e-9, "Assembly bench drop should remain meter-native after schema refresh")
        _assert(abs(float(getattr(asm, "DaylightSearchStep", 0.0) or 0.0) - 1.0) < 1.0e-9, "Assembly daylight step should remain meter-native after schema refresh")
        _assert(abs(float(getattr(asm, "HeightLeft", 0.0) or 0.0) - 0.3) < 1.0e-9, "Assembly height should remain meter-native after schema refresh")
        _assert(int(getattr(asm, "LengthSchemaVersion", 0) or 0) == 1, "Assembly length schema should migrate to version 1")
        _assert(_shape_ok(asm), "AssemblyTemplate should still generate preview geometry after migration")
        _assert(abs(float(getattr(asm.Shape.BoundBox, "XLength", 0.0) or 0.0) - 8.0) < 1.0e-3, "Preview geometry should stay meter-native after schema refresh")

        print("[PASS] Assembly-template unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
