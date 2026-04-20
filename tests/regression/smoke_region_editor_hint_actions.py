# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor hint action smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_hint_actions.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorHintActions")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 40.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base A"},
                {"Id": "HINT_ACCEPT", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 20.0, "EndStation": 30.0, "Priority": 10, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "typical:ditch_edge:left", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": False, "Notes": "Seeded left ditch hint", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Detected ditch roadside pattern on the left side."},
                {"Id": "HINT_IGNORE", "RegionType": "retaining_wall_zone", "Layer": "overlay", "StartStation": 50.0, "EndStation": 60.0, "Priority": 20, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "typical:urban_edge:right", "SidePolicy": "", "DaylightPolicy": "right:off", "CorridorPolicy": "", "Enabled": False, "Notes": "Seeded right urban hint", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Detected urban edge roadside pattern on the right side."},
            ]
        )

        _assert(panel.tbl_hint.rowCount() == 2, f"Expected two hint rows, got {panel.tbl_hint.rowCount()}")

        panel.tbl_hint.setCurrentCell(0, 0)
        panel._accept_selected_hint()

        rows_after_accept = panel._read_rows()
        accept_row = next(row for row in rows_after_accept if str(row.get("Id", "") or "") == "HINT_ACCEPT")
        _assert(str(accept_row.get("Enabled", "") or "").lower() == "true", "Accepted hint should become enabled")
        _assert(str(accept_row.get("HintStatus", "") or "").lower() == "accepted", "Accepted hint should update explicit hint status")
        _assert(panel.tbl_override.rowCount() == 1, f"Accepted hint should move to overrides, got {panel.tbl_override.rowCount()}")
        _assert(panel.tbl_hint.rowCount() == 1, f"Hint table should shrink after accept, got {panel.tbl_hint.rowCount()}")

        panel.tbl_hint.setCurrentCell(0, 0)
        panel._ignore_selected_hint()

        rows_after_ignore = panel._read_rows()
        ignore_row = next(row for row in rows_after_ignore if str(row.get("Id", "") or "") == "HINT_IGNORE")
        _assert(str(ignore_row.get("Enabled", "") or "").lower() == "false", "Ignored hint should stay disabled")
        _assert(str(ignore_row.get("HintStatus", "") or "").lower() == "ignored", "Ignored hint should update explicit hint status")
        _assert(panel.tbl_hint.rowCount() == 1, "Ignored hint should remain in hint table")
        _assert(str(panel.tbl_hint.item(0, 1).text() or "") == "Typical Section / Urban Edge", "Hint source should show source and family")
        _assert("High" in str(panel.tbl_hint.item(0, 4).text() or ""), "Hint confidence should stay visible")
        _assert(str(panel.tbl_hint.item(0, 5).text() or "") == "Ignored", "Hint summary should show ignored status")
        _assert("urban edge roadside pattern" in str(panel.tbl_hint.item(0, 6).text() or "").lower(), "Hint reason should remain visible")

        panel.tbl_hint.setCurrentCell(0, 0)
        panel._accept_and_edit_selected_hint()
        rows_after_edit = panel._read_rows()
        edit_row = next(row for row in rows_after_edit if str(row.get("Id", "") or "") == "HINT_IGNORE")
        _assert(str(edit_row.get("Enabled", "") or "").lower() == "true", "Accept and edit should enable the selected hint")
        _assert(str(edit_row.get("HintStatus", "") or "").lower() == "accepted", "Accept and edit should promote the hint status")
        _assert(panel.tabs.currentIndex() == 0, "Accept and edit should stay in Workflow tab")
        _assert(panel.tbl_override.rowCount() == 2, "Accepted hint should move into override summary")
        _assert(str(panel.cmb_override_kind.currentText() or "") == "Urban Edge", "Workflow override editor should load accepted hint kind")
        _assert(str(panel.cmb_override_scope.currentText() or "") == "Right", "Workflow override editor should load accepted hint scope")
        _assert(str(panel.cmb_override_action.currentText() or "") == "Daylight Off", "Workflow override editor should load accepted hint action")

        print("[PASS] Region editor hint action smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
