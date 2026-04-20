# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor combo/id behavior smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_combo_ids.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorComboIds")
    try:
        panel = RegionEditorTaskPanel()
        panel.chk_auto_seed_project.setChecked(False)
        panel._on_target_changed()

        region_type_combo = panel.table.cellWidget(0, 1)
        _assert(isinstance(region_type_combo, QtWidgets.QComboBox), "RegionType column should use a combo box")
        combo_items = [str(region_type_combo.itemText(i) or "") for i in range(region_type_combo.count())]
        _assert("roadway" in combo_items, "RegionType combo missing roadway")
        _assert("ditch_override" in combo_items, "RegionType combo missing ditch_override")
        _assert("culvert" in combo_items, "RegionType combo missing culvert for structure-derived seeds")

        rows = panel._read_rows()
        _assert(len(rows) == 1, "Default editor state should seed one row when auto-seed is off")
        _assert(str(rows[0].get("Id", "") or "") == "BASE_01", "Default base row id mismatch")

        panel._add_row()
        new_row = panel.table.rowCount() - 1
        _assert(str(panel._get_cell_text(new_row, 0) or "") == "OVR_OTHER_01", "New overlay row should receive generated id")
        _assert(str(panel._get_cell_text(new_row, 1) or "") == "other", "New overlay row should default RegionType to other")

        combo = panel.table.cellWidget(new_row, 1)
        combo.setCurrentText("ditch_override")
        _assert(str(panel._get_cell_text(new_row, 0) or "") == "OVR_DITCH_OVERRIDE_01", "Changing RegionType should regenerate auto id")

        panel._set_cell_text(new_row, 2, "base")
        _assert(str(panel._get_cell_text(new_row, 0) or "") == "BASE_DITCH_OVERRIDE_01", "Changing Layer should regenerate auto id")

        panel._set_cell_text(new_row, 0, "")
        panel._refresh_validation_status()
        _assert(str(panel._get_cell_text(new_row, 0) or "") == "BASE_DITCH_OVERRIDE_01", "Blank ids should be materialized consistently")

        print("[PASS] Region editor combo/id smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
