# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
TypicalSectionTemplate unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_typical_section_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.objects.obj_typical_section_template import (
    TypicalSectionTemplate,
    ensure_typical_section_template_properties,
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


def run():
    doc = App.newDocument("CRTypicalSectionUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "m"

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)

        _assert(abs(float(list(getattr(typ, "ComponentWidths", []) or [0.0])[0]) - 3.5) < 1.0e-9, "New default widths should be stored in meters")
        _assert(abs(float(list(getattr(typ, "PavementLayerThicknesses", []) or [0.0])[0]) - 0.05) < 1.0e-9, "New pavement defaults should be stored in meters")

        typ.ComponentWidths = [3.5, 1.5, 3.5, 1.5]
        typ.ComponentHeights = [0.0, 0.0, 0.0, 0.0]
        typ.ComponentExtraWidths = [0.0, 0.0, 0.0, 0.0]
        typ.ComponentOffsets = [0.0, 0.0, 0.0, 0.0]
        typ.PavementLayerThicknesses = [0.05, 0.07, 0.20, 0.25]
        typ.LengthSchemaVersion = 0

        ensure_typical_section_template_properties(typ)
        doc.recompute()

        widths = list(getattr(typ, "ComponentWidths", []) or [])
        pavements = list(getattr(typ, "PavementLayerThicknesses", []) or [])
        _assert(abs(float(widths[0]) - 3.5) < 1.0e-9, "Component widths should remain meter-native after schema refresh")
        _assert(abs(float(widths[1]) - 1.5) < 1.0e-9, "Shoulder width should remain meter-native after schema refresh")
        _assert(abs(float(pavements[0]) - 0.05) < 1.0e-9, "Pavement thickness should remain meter-native after schema refresh")
        _assert(int(getattr(typ, "LengthSchemaVersion", 0) or 0) == 1, "Typical-section length schema should migrate to version 1")
        _assert(_shape_ok(typ), "TypicalSectionTemplate should still generate preview geometry after migration")
        _assert(abs(float(getattr(typ.Shape.BoundBox, "XLength", 0.0) or 0.0) - 10.0) < 1.0e-3, "Preview geometry should stay meter-native after schema refresh")
        _assert(abs(float(getattr(typ, "PavementTotalThickness", 0.0) or 0.0) - 0.57) < 1.0e-9, "Reported pavement thickness should stay meter-native")

        print("[PASS] Typical-section unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
