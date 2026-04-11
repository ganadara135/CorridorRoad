# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Profile editor display-unit boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_profile_editor_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_profile_editor import ProfileEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRProfileEditorUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"
        prj.LinearUnitImportDefault = "mm"

        bundle = doc.addObject("Part::FeaturePython", "ProfileBundle")
        ProfileBundle(bundle)
        bundle.Stations = [20.0, 40.0]
        bundle.ElevEG = [100.0, 102.0]
        bundle.ElevFG = [101.0, 103.0]
        bundle.WireZOffset = 0.5

        panel = ProfileEditorTaskPanel()
        _assert("Display unit: mm" in str(panel.lbl_info.text() or ""), "Profile editor info should report display unit")
        _assert(panel.spin_eg_zoff.suffix().strip() == "mm", "EG Z offset suffix should follow display unit")
        _assert(panel.table.horizontalHeaderItem(0).text().strip() == "Station (mm)", "Station header should include display unit")
        _assert(panel.table.horizontalHeaderItem(1).text().strip() == "EG (mm)", "EG header should include display unit")
        _assert(abs(float(panel.spin_eg_zoff.value()) - 500.0) < 1.0e-6, "Stored 0.5 m Z offset should display as 500 mm")
        _assert(panel._get_cell_text(0, 0).strip() == "20000.000", "Station table should display millimeters")
        _assert(panel._get_cell_text(0, 1).strip() == "100000.000", "EG table should display millimeters")
        _assert(abs(float(panel._get_cell_float(0, 0)) - 20.0) < 1.0e-6, "Displayed station should read back as meters")

        panel._set_cell_text(0, 0, "25500.000")
        panel._set_cell_text(0, 1, "100250.000")
        panel._set_cell_text(0, 2, "101000.000")
        panel._set_cell_text(1, 0, "40000.000")
        panel._set_cell_text(1, 1, "102000.000")
        panel._set_cell_text(1, 2, "103000.000")
        panel.spin_eg_zoff.setValue(750.0)
        panel._save_to_document()

        _assert(abs(float(bundle.Stations[0]) - 25.5) < 1.0e-6, "Edited 25500 mm station should save as 25.5 m")
        _assert(abs(float(bundle.ElevEG[0]) - 100.25) < 1.0e-6, "Edited 100250 mm EG should save as 100.25 m")
        _assert(abs(float(bundle.WireZOffset) - 0.75) < 1.0e-6, "Edited 750 mm Z offset should save as 0.75 m")

        print("[PASS] Profile editor unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
