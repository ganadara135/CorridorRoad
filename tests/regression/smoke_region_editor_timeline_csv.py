# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor timeline and CSV smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_timeline_csv.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorTimelineCsv")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 40.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base A"},
                {"Id": "OVR_A", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 20.0, "EndStation": 30.0, "Priority": 10, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Override A"},
                {"Id": "HINT_A", "RegionType": "retaining_wall_zone", "Layer": "overlay", "StartStation": 50.0, "EndStation": 60.0, "Priority": 20, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "typical:urban_edge:right", "SidePolicy": "", "DaylightPolicy": "right:off", "CorridorPolicy": "", "Enabled": False, "Notes": "Pending hint", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Detected urban edge roadside pattern on the right side."},
            ]
        )

        _assert(panel.tbl_timeline.rowCount() == 3, "Timeline should show three rows")

        panel.tbl_timeline.setCurrentCell(1, 0)
        _assert(panel.tbl_override.currentRow() == 0, "Timeline selection should sync to override summary")
        _assert(str(panel.cmb_override_kind.currentText() or "") == "Ditch / Berm", "Override editor should load from timeline selection")

        panel.txt_timeline_start.setText("22.000")
        panel.txt_timeline_end.setText("32.000")
        panel._apply_timeline_span_edit()
        rows_after_span = panel._read_rows()
        override_row = next(row for row in rows_after_span if str(row.get("Id", "") or "") == "OVR_A")
        _assert(str(override_row.get("StartStation", "") or "") == "22.000", "Timeline span edit should update start station")
        _assert(str(override_row.get("EndStation", "") or "") == "32.000", "Timeline span edit should update end station")

        panel.tbl_timeline.setCurrentCell(0, 0)
        panel._split_selected_timeline_base()
        _assert(panel.tbl_base.rowCount() == 2, f"Split from timeline should create two base rows, got {panel.tbl_base.rowCount()}")

        flat_rows = panel._flatten_group_rows(panel._group_rows())
        csv_text = panel._rows_to_csv_text(flat_rows)
        imported_rows = panel._rows_from_csv_text(csv_text)
        _assert(len(imported_rows) == len(flat_rows), "CSV round-trip should preserve row count")
        imported_hint = next(row for row in imported_rows if str(row.get("HintStatus", "") or "").strip().lower() == "pending")
        _assert(str(imported_hint.get("HintSource", "") or "") == "typical", "CSV round-trip should preserve hint source")
        _assert("urban edge roadside pattern" in str(imported_hint.get("HintReason", "") or "").lower(), "CSV round-trip should preserve hint reason")

        panel._populate_table(imported_rows)
        _assert(panel.tbl_timeline.rowCount() == len(imported_rows), "Imported rows should rebuild timeline table")

        print("[PASS] Region editor timeline and CSV smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
