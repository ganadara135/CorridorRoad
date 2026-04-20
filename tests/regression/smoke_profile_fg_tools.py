# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Profile FG tools smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_profile_fg_tools.py
"""

import os

import FreeCAD as App
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_profile_editor import ProfileEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _fg_values(panel):
    out = []
    for r in range(panel.table.rowCount()):
        sta = panel._get_cell_float(r, 0)
        if sta is None:
            continue
        out.append((float(sta), panel._get_cell_float(r, 1), panel._get_cell_float(r, 2)))
    return out


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRProfileFGTools")
    csv_path = None

    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"
        prj.LinearUnitImportDefault = "m"

        panel = ProfileEditorTaskPanel()
        panel.chk_fg_from_va.setChecked(False)
        panel.table.setRowCount(0)
        panel._set_rows(3)
        panel._set_cell_float(0, 0, 0.0)
        panel._set_cell_float(1, 0, 10.0)
        panel._set_cell_float(2, 0, 20.0)
        panel._set_cell_float(0, 1, 100.0)
        panel._set_cell_float(1, 1, 101.0)
        panel._set_cell_float(2, 1, 102.0)

        updated, skipped = panel._apply_fg_wizard_values("eg_offset", 0.0, 20.0, 1.5, 0.0)
        _assert(updated == 3, "Constant-offset FG wizard should update all rows")
        _assert(skipped == 0, "Constant-offset FG wizard should not skip EG-ready rows")
        vals = _fg_values(panel)
        _assert(abs(float(vals[0][2]) - 101.5) < 1e-6, "Station 0 FG mismatch after constant-offset wizard")
        _assert(abs(float(vals[1][2]) - 102.5) < 1e-6, "Station 10 FG mismatch after constant-offset wizard")
        _assert(abs(float(vals[2][2]) - 103.5) < 1e-6, "Station 20 FG mismatch after constant-offset wizard")

        updated, skipped = panel._apply_fg_wizard_values("eg_offset_ramp", 0.0, 20.0, 0.0, 2.0)
        _assert(updated == 3, "Ramp-offset FG wizard should update all rows")
        _assert(skipped == 0, "Ramp-offset FG wizard should not skip EG-ready rows")
        vals = _fg_values(panel)
        _assert(abs(float(vals[0][2]) - 100.0) < 1e-6, "Station 0 FG mismatch after ramp-offset wizard")
        _assert(abs(float(vals[1][2]) - 102.0) < 1e-6, "Station 10 FG mismatch after ramp-offset wizard")
        _assert(abs(float(vals[2][2]) - 104.0) < 1e-6, "Station 20 FG mismatch after ramp-offset wizard")

        updated, skipped = panel._apply_fg_wizard_values("absolute_interp", 0.0, 20.0, 200.0, 210.0)
        _assert(updated == 3, "Absolute-interpolation FG wizard should update all rows")
        _assert(skipped == 0, "Absolute-interpolation FG wizard should not skip rows")
        vals = _fg_values(panel)
        _assert(abs(float(vals[0][2]) - 200.0) < 1e-6, "Station 0 FG mismatch after absolute interpolation")
        _assert(abs(float(vals[1][2]) - 205.0) < 1e-6, "Station 10 FG mismatch after absolute interpolation")
        _assert(abs(float(vals[2][2]) - 210.0) < 1e-6, "Station 20 FG mismatch after absolute interpolation")

        csv_path = os.path.join(os.getcwd(), f"_tmp_fg_import_{os.getpid()}.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("Station,FG\n")
            fh.write("10,150.0\n")
            fh.write("30,175.5\n")
        imported, linear_unit = panel._parse_fg_import_file(csv_path, doc_or_project=panel._unit_context())
        _assert(imported == [(10.0, 150.0), (30.0, 175.5)], "FG import parser returned unexpected rows")
        _assert(linear_unit == "m", "FG import parser should default to meter units without project override")
        updated, appended = panel._apply_imported_fg_rows(imported)
        _assert(updated == 1, "FG import should update one existing station")
        _assert(appended == 1, "FG import should append one new station")

        vals = _fg_values(panel)
        _assert(any(abs(sta - 10.0) < 1e-6 and abs(float(fg or 0.0) - 150.0) < 1e-6 for sta, _eg, fg in vals), "Imported FG should overwrite station 10")
        _assert(any(abs(sta - 30.0) < 1e-6 and abs(float(fg or 0.0) - 175.5) < 1e-6 for sta, _eg, fg in vals), "Imported FG should append station 30")

        import_summary = panel._fg_import_summary_text(csv_path, len(imported), updated, appended, linear_unit)
        _assert("Display unit: mm" in import_summary, "FG import summary should report active display unit")
        _assert("CSV linear values: m" in import_summary, "FG import summary should report CSV linear unit")

        wizard_summary = panel._fg_wizard_summary_text(3, 1)
        _assert("Display unit: mm" in wizard_summary, "FG wizard summary should report active display unit")
        _assert("Skipped rows missing EG: 1" in wizard_summary, "FG wizard summary should report skipped EG rows")

        panel._save_to_document()
        bundle = panel.bundle
        _assert(bundle is not None, "ProfileBundle should be created during save")
        _assert(len(list(getattr(bundle, "Stations", []) or [])) == 4, "ProfileBundle station count mismatch after FG tool save")
        _assert(any(abs(float(v) - 175.5) < 1e-6 for v in list(getattr(bundle, "ElevFG", []) or [])), "Saved bundle is missing imported FG value")

        print("[PASS] Profile FG tools smoke test completed.")
    finally:
        if csv_path:
            try:
                os.remove(csv_path)
            except Exception:
                pass
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
