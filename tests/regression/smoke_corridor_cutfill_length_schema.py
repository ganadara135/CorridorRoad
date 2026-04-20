# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor and Cut/Fill length-schema smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_cutfill_length_schema.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_corridor import Corridor, ensure_corridor_loft_properties
from freecad.Corridor_Road.objects.obj_cut_fill_calc import CutFillCalc, ensure_cut_fill_calc_properties
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRCorridorCutFillLengthSchema")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)

        cor = doc.addObject("Part::FeaturePython", "Corridor")
        Corridor(cor)
        cor.LengthSchemaVersion = 0
        cor.MinSectionSpacing = 0.5
        ensure_corridor_loft_properties(cor)

        _assert(abs(float(cor.MinSectionSpacing) - 0.5) < 1.0e-9, "Corridor min spacing should remain meter-native")
        _assert(int(getattr(cor, "LengthSchemaVersion", 0) or 0) >= 1, "Corridor length schema version should update")

        cmp_obj = doc.addObject("Part::FeaturePython", "CutFillCalc")
        CutFillCalc(cmp_obj)
        cmp_obj.LengthSchemaVersion = 0
        cmp_obj.CellSize = 1.0
        cmp_obj.DomainMargin = 5.0
        cmp_obj.DeltaDeadband = 0.02
        cmp_obj.DeltaClamp = 2.0
        cmp_obj.VisualZOffset = 0.05
        cmp_obj.XMin = 12.0
        cmp_obj.XMax = 34.0
        cmp_obj.YMin = 56.0
        cmp_obj.YMax = 78.0
        ensure_cut_fill_calc_properties(cmp_obj)

        _assert(abs(float(cmp_obj.CellSize) - 1.0) < 1.0e-9, "Cut/Fill cell size should remain meter-native")
        _assert(abs(float(cmp_obj.DomainMargin) - 5.0) < 1.0e-9, "Cut/Fill domain margin should remain meter-native")
        _assert(abs(float(cmp_obj.DeltaDeadband) - 0.02) < 1.0e-9, "Cut/Fill deadband should remain meter-native")
        _assert(abs(float(cmp_obj.DeltaClamp) - 2.0) < 1.0e-9, "Cut/Fill clamp should remain meter-native")
        _assert(abs(float(cmp_obj.VisualZOffset) - 0.05) < 1.0e-9, "Cut/Fill visual offset should remain meter-native")
        _assert(abs(float(cmp_obj.XMin) - 12.0) < 1.0e-9, "Cut/Fill XMin should remain meter-native")
        _assert(abs(float(cmp_obj.XMax) - 34.0) < 1.0e-9, "Cut/Fill XMax should remain meter-native")
        _assert(abs(float(cmp_obj.YMin) - 56.0) < 1.0e-9, "Cut/Fill YMin should remain meter-native")
        _assert(abs(float(cmp_obj.YMax) - 78.0) < 1.0e-9, "Cut/Fill YMax should remain meter-native")
        _assert(int(getattr(cmp_obj, "LengthSchemaVersion", 0) or 0) >= 1, "Cut/Fill length schema version should update")

        print("[PASS] Corridor/CutFill length-schema smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
