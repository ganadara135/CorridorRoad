# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
PVI starter-defaults smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_pvi_starter_defaults.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle
from freecad.Corridor_Road.objects.obj_stationing import Stationing
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_pvi_editor import PviEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRPviStarterDefaults")
    try:
        st = doc.addObject("Part::FeaturePython", "Stationing")
        Stationing(st)
        st.StationValues = [0.0, 50.0, 100.0, 150.0, 200.0]

        bundle = doc.addObject("Part::FeaturePython", "ProfileBundle")
        ProfileBundle(bundle)
        bundle.Stations = list(st.StationValues)
        bundle.ElevEG = [100.0, 102.0, 104.0, 106.0, 108.0]
        bundle.ElevFG = [0.0, 0.0, 0.0, 0.0, 0.0]

        panel = PviEditorTaskPanel()
        rows = panel._read_pvi()
        _assert(len(rows) == 3, "Starter PVI should auto-fill three rows from the resolved station range")
        _assert(abs(rows[0][0] - 0.0) < 1e-6 and abs(rows[2][0] - 200.0) < 1e-6, "Starter PVI should use start/end stations")
        _assert(abs(rows[1][0] - 100.0) < 1e-6, "Starter PVI should use the midpoint station when available")
        _assert(abs(rows[0][1] - 100.0) < 1e-6 and abs(rows[1][1] - 104.0) < 1e-6, "Starter PVI should seed elevations from ProfileBundle EG")
        _assert(abs(rows[1][2] - 20.0) < 1e-6, "Starter interior vertical-curve length should use the default starter value")
        _assert(panel._starter_source_name == "ProfileBundle EG", "Starter PVI source should report ProfileBundle EG")

        panel._clear_to_blank()
        _assert(len(panel._read_pvi()) == 0, "Clear to Blank should remove valid PVI rows")

        ok = panel._load_starter_pvi(show_message=False)
        _assert(ok, "Load Starter PVI should succeed when station/profile data exists")
        rows = panel._read_pvi()
        _assert(len(rows) == 3, "Load Starter PVI should restore starter rows after clearing")

        print("[PASS] PVI starter-defaults smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
