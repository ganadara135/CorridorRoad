# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Unit-policy project settings smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_unit_policy_project_settings.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.objects import unit_policy as units


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _make_feature(doc, name: str):
    return doc.addObject("App::FeaturePython", name)


def run():
    doc = App.newDocument("CRUnitPolicy")
    try:
        prj = _make_feature(doc, "CorridorRoadProject")
        ensure_project_properties(prj)
        _assert(str(getattr(prj, "LinearUnitDisplay", "")) == "m", "New project display unit should default to meters")
        _assert(str(getattr(prj, "LinearUnitImportDefault", "")) == "m", "New project import unit should default to meters")
        _assert(str(getattr(prj, "LinearUnitExportDefault", "")) == "m", "New project export unit should default to meters")
        _assert(abs(float(getattr(prj, "CustomLinearUnitScale", 0.0)) - 1.0) < 1.0e-9, "New project custom scale should default to 1 meter per user-unit")
        _assert(not hasattr(prj, "LengthScale"), "New project should not auto-create LengthScale")
        _assert(units.get_linear_display_unit(prj) == "m", "Display helper should read meter default")
        _assert(abs(units.meters_from_user_length(prj, 12.5) - 12.5) < 1.0e-9, "Meter input should stay meter-native")

        custom_project = _make_feature(doc, "CustomUnitProject")
        ensure_project_properties(custom_project)
        custom_project.LinearUnitDisplay = "mm"
        custom_project.LinearUnitImportDefault = "custom"
        custom_project.LinearUnitExportDefault = "custom"
        custom_project.CustomLinearUnitScale = 0.25
        _assert(str(getattr(custom_project, "LinearUnitDisplay", "")) == "mm", "Explicit display-unit settings should persist on the project")
        _assert(str(getattr(custom_project, "LinearUnitImportDefault", "")) == "custom", "Explicit import-unit settings should persist on the project")
        _assert(str(getattr(custom_project, "LinearUnitExportDefault", "")) == "custom", "Explicit export-unit settings should persist on the project")
        _assert(abs(float(getattr(custom_project, "CustomLinearUnitScale", 0.0)) - 0.25) < 1.0e-9, "Explicit custom scale should persist in meters per user-unit")
        _assert(abs(units.meters_from_user_length(custom_project, 2.0) - 0.5) < 1.0e-9, "Custom import unit should convert into meters using the explicit project scale")
        _assert(abs(units.user_length_from_meters(custom_project, 1.0, use_default="export") - 4.0) < 1.0e-9, "Custom export unit should format from meters using the explicit project scale")
        _assert(units.format_length(custom_project, 1.0, digits=3, unit="custom") == "4.000 custom", "Formatted custom unit should reflect the explicit custom scale")

        print("[PASS] Unit-policy project settings smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
