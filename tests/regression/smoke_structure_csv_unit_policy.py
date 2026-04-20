# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Structure CSV unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_structure_csv_unit_policy.py
"""

import os

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_structure_editor import StructureEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _write_text(path, text):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        handle.write(text)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRStructureCsvUnitPolicy")
    suffix = str(os.getpid())
    base_csv = os.path.join(os.getcwd(), f"_tmp_structure_base_{suffix}.csv")
    profile_csv = os.path.join(os.getcwd(), f"_tmp_structure_profile_{suffix}.csv")
    profile_meta_csv = os.path.join(os.getcwd(), f"_tmp_structure_profile_meta_{suffix}.csv")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"
        prj.LinearUnitImportDefault = "mm"

        _write_text(
            base_csv,
            "Id,Type,StartStation,EndStation,CenterStation,Width,Height,CorridorMargin\n"
            "CULV-01,culvert,20000,26000,23000,6000,2500,1500\n",
        )
        _write_text(
            profile_csv,
            "StructureId,Station,Width,Height\n"
            "CULV-01,20000,5000,2200\n"
            "CULV-01,26000,7000,2800\n",
        )
        _write_text(
            profile_meta_csv,
            "# CorridorRoadUnits,linear=m\n"
            "StructureId,Station,Width,Height\n"
            "CULV-01,20,5,2.2\n"
            "CULV-01,26,7,2.8\n",
        )

        panel = StructureEditorTaskPanel()
        panel.ed_csv.setText(base_csv)
        panel._on_load_csv()
        rows = panel._read_rows()
        _assert(len(rows) == 1, "Base structure CSV should load one row")
        _assert(abs(float(rows[0]["StartStation"]) - 20.0) < 1.0e-6, "StartStation should use project import default mm")
        _assert(abs(float(rows[0]["Width"]) - 6.0) < 1.0e-6, "Width should use project import default mm")
        _assert("linear=mm" in str(panel.lbl_status.text() or ""), "Status should report resolved import unit")

        panel.ed_profile_csv.setText(profile_csv)
        panel._on_load_profile_csv()
        profile_rows = list(panel._profile_rows or [])
        _assert(len(profile_rows) == 2, "Profile CSV should load two rows")
        _assert(abs(float(profile_rows[0]["Station"]) - 20.0) < 1.0e-6, "Profile station should use project import default mm")
        _assert(abs(float(profile_rows[1]["Width"]) - 7.0) < 1.0e-6, "Profile width should use project import default mm")

        panel.ed_profile_csv.setText(profile_meta_csv)
        panel._on_load_profile_csv()
        profile_rows_meta = list(panel._profile_rows or [])
        _assert(abs(float(profile_rows_meta[0]["Station"]) - 20.0) < 1.0e-6, "Metadata linear=m should preserve station meters")
        _assert(abs(float(profile_rows_meta[1]["Height"]) - 2.8) < 1.0e-6, "Metadata linear=m should preserve height meters")
        _assert("linear=m" in str(panel.lbl_status.text() or ""), "Status should report metadata override unit")

        print("[PASS] Structure CSV unit-policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass
        for path in (base_csv, profile_csv, profile_meta_csv):
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == "__main__":
    run()
