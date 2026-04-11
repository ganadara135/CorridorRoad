# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Profile FG CSV unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_profile_fg_csv_unit_policy.py
"""

import os

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_profile_editor import ProfileEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRProfileFGCsvUnitPolicy")
    csv_mm = os.path.join(os.getcwd(), f"_tmp_fg_mm_{os.getpid()}.csv")
    csv_m = os.path.join(os.getcwd(), f"_tmp_fg_m_{os.getpid()}.csv")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitImportDefault = "mm"

        with open(csv_mm, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("Station,FG\n")
            fh.write("10000,150000\n")
            fh.write("30000,175500\n")

        with open(csv_m, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("# CorridorRoadUnits,linear=m\n")
            fh.write("Station,FG\n")
            fh.write("10,150\n")
            fh.write("30,175.5\n")

        panel = ProfileEditorTaskPanel()
        rows_mm, linear_mm = panel._parse_fg_import_file(csv_mm, doc_or_project=panel._unit_context())
        _assert(rows_mm == [(10.0, 150.0), (30.0, 175.5)], "FG CSV without metadata should use project import default mm")
        _assert(linear_mm == "mm", "FG CSV should report resolved project import unit")

        rows_m, linear_m = panel._parse_fg_import_file(csv_m, doc_or_project=panel._unit_context())
        _assert(rows_m == [(10.0, 150.0), (30.0, 175.5)], "FG CSV metadata linear=m should preserve meter values")
        _assert(linear_m == "m", "FG CSV metadata should override project import default")

        print("[PASS] Profile FG CSV unit-policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass
        for path in (csv_mm, csv_m):
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == "__main__":
    run()
