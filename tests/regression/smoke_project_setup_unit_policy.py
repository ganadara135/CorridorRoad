# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Project Setup unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_project_setup_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_project_setup import ProjectSetupTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    _ = app
    doc = App.newDocument("CRProjectSetupUnits")
    original_info = QtWidgets.QMessageBox.information
    original_warn = QtWidgets.QMessageBox.warning
    try:
        QtWidgets.QMessageBox.information = staticmethod(lambda *args, **kwargs: 0)
        QtWidgets.QMessageBox.warning = staticmethod(lambda *args, **kwargs: 0)

        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        _assert(not hasattr(prj, "LengthScale"), "New project should no longer auto-create LengthScale")
        panel = ProjectSetupTaskPanel(preferred_project=prj)

        _assert(panel.cmb_linear_display.currentText() == "m", "New project should load meter display unit")
        _assert(panel.cmb_linear_import.currentText() == "m", "New project should load meter import unit")
        _assert(panel.cmb_linear_export.currentText() == "m", "New project should load meter export unit")
        _assert("Stored geometry stays meter-native" in str(panel.lbl_info.text() or ""), "Project info should explain meter-native storage")
        _assert("Stored geometry stays in meters" in str(panel.lbl_unit_policy_info.text() or ""), "Unit policy help should explain meter-native storage")

        panel.cmb_linear_display.setCurrentText("mm")
        panel.cmb_linear_import.setCurrentText("custom")
        panel.cmb_linear_export.setCurrentText("mm")
        panel.sp_custom_linear_scale.setValue(0.0025)
        _assert("meter(s) / custom-unit" in str(panel.sp_custom_linear_scale.suffix() or ""), "Custom scale suffix should describe custom-unit conversion")
        panel._apply()

        _assert(str(prj.LinearUnitDisplay) == "mm", "Apply should store display unit")
        _assert(str(prj.LinearUnitImportDefault) == "custom", "Apply should store import unit")
        _assert(str(prj.LinearUnitExportDefault) == "mm", "Apply should store export unit")
        _assert(abs(float(prj.CustomLinearUnitScale) - 0.0025) < 1.0e-9, "Apply should store custom unit scale")
        _assert("CompatibilityScale" not in str(panel.lbl_result.text() or ""), "Apply result should no longer expose compatibility scale text")
        _assert("CustomScale=0.002500000" in str(panel.lbl_result.text() or ""), "Apply result should report the explicit custom scale")

        print("[PASS] Project Setup unit-policy smoke test completed.")
    finally:
        QtWidgets.QMessageBox.information = original_info
        QtWidgets.QMessageBox.warning = original_warn
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
