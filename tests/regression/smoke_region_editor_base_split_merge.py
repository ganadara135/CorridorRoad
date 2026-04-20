# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor base split/merge smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_base_split_merge.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _find(rows, row_id):
    for row in list(rows or []):
        if str(row.get("Id", "") or "") == str(row_id or ""):
            return row
    return None


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorBaseSplitMerge")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_MAIN", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 100.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "ASM_A", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Main base"},
            ]
        )

        panel.tbl_base.setCurrentCell(0, 0)
        panel._split_selected_base_row()

        rows_after_split = panel._read_rows()
        left = _find(rows_after_split, "BASE_MAIN_A")
        right = _find(rows_after_split, "BASE_MAIN_B")
        _assert(left is not None and right is not None, "Split should create _A and _B base rows")
        _assert(abs(float(left.get("EndStation", 0.0) or 0.0) - 50.0) < 1e-6, "Left split end should be midpoint")
        _assert(abs(float(right.get("StartStation", 0.0) or 0.0) - 50.0) < 1e-6, "Right split start should be midpoint")
        _assert(panel.tbl_base.rowCount() == 2, f"Expected two base rows after split, got {panel.tbl_base.rowCount()}")

        panel.tbl_base.setCurrentCell(0, 0)
        panel._merge_selected_base_row()

        rows_after_merge = panel._read_rows()
        merged = _find(rows_after_merge, "BASE_MAIN_A")
        _assert(len(rows_after_merge) == 1, f"Merge should collapse back to one row, got {len(rows_after_merge)}")
        _assert(merged is not None, "Merged row should keep the selected manual id")
        _assert(abs(float(merged.get("StartStation", 0.0) or 0.0) - 0.0) < 1e-6, "Merged row start mismatch")
        _assert(abs(float(merged.get("EndStation", 0.0) or 0.0) - 100.0) < 1e-6, "Merged row end mismatch")

        print("[PASS] Region editor base split/merge smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
