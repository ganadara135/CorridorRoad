# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Station generator unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_station_generator_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_station_generator import StationGeneratorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRStationUnitPolicy")
    original_info = QtWidgets.QMessageBox.information
    original_warn = QtWidgets.QMessageBox.warning
    try:
        QtWidgets.QMessageBox.information = staticmethod(lambda *args, **kwargs: 0)
        QtWidgets.QMessageBox.warning = staticmethod(lambda *args, **kwargs: 0)

        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"

        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(60.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        panel = StationGeneratorTaskPanel()
        _assert(panel.spin_interval.suffix().strip() == "mm", "Station generator should display millimeter suffix for legacy mm project")
        _assert(abs(float(panel.spin_interval.value()) - 20000.0) < 1e-6, "Default interval should display as 20000 mm")
        _assert(abs(float(panel.spin_tick.value()) - 2000.0) < 1e-6, "Default tick should display as 2000 mm")
        _assert("Display unit: mm" in str(panel.lbl_info.text() or ""), "Station generator info should report display unit")
        _assert("Interval=20000.000 mm" in str(panel.lbl_status.text() or ""), "New-stationing status should report display-unit interval with unit")
        _assert("tick=2000.000 mm" in str(panel.lbl_status.text() or ""), "New-stationing status should report display-unit tick with unit")

        panel.spin_interval.setValue(25000.0)
        panel.spin_tick.setValue(500.0)
        panel._generate()

        stationings = [o for o in doc.Objects if str(getattr(o, "Name", "") or "").startswith("Stationing")]
        _assert(len(stationings) >= 1, "Station generator should create a Stationing object")
        st = stationings[0]
        _assert(abs(float(getattr(st, "Interval", 0.0)) - 25.0) < 1e-6, "Displayed 25000 mm interval should save as 25 meter-native units")
        _assert(abs(float(getattr(st, "TickLength", 0.0)) - 0.5) < 1e-6, "Displayed 500 mm tick should save as 0.5 meter-native units")
        _assert(abs(float((getattr(st, "StationValues", []) or [0.0, 0.0])[-1]) - 60.0) < 1e-6, "Station values should be published in meters")
        _assert("Interval=25000.000 mm" in str(panel.lbl_status.text() or ""), "Generate status should keep display-unit interval text with unit")
        _assert("tick=500.000 mm" in str(panel.lbl_status.text() or ""), "Generate status should keep display-unit tick text with unit")

        print("[PASS] Station generator unit-policy smoke test completed.")
    finally:
        QtWidgets.QMessageBox.information = original_info
        QtWidgets.QMessageBox.warning = original_warn
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
