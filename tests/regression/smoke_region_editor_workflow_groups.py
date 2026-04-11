# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor workflow grouping smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_workflow_groups.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorWorkflow")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 40.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base A"},
                {"Id": "OVR_A", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 20.0, "EndStation": 30.0, "Priority": 10, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Override A"},
                {"Id": "HINT_A", "RegionType": "retaining_wall_zone", "Layer": "overlay", "StartStation": 50.0, "EndStation": 60.0, "Priority": 20, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "typical:urban_edge:right", "SidePolicy": "", "DaylightPolicy": "right:off", "CorridorPolicy": "", "Enabled": False, "Notes": "Pending hint", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Detected urban edge roadside pattern on the right side."},
            ]
        )

        _assert(panel.tabs.count() >= 2, "Expected workflow and advanced tabs")
        _assert(panel.tabs.tabText(0) == "Workflow", "First tab should be Workflow")
        _assert(panel.tabs.tabText(1) == "Advanced", "Second tab should be Advanced")
        _assert(bool(panel.chk_enable_advanced_edit.isEnabled()), "Advanced legacy editing should stay available while creating a new plan")
        _assert(not bool(panel.chk_enable_advanced_edit.isChecked()), "Advanced legacy editing should default to off")
        _assert(not bool(panel.btn_add.isEnabled()), "Advanced add button should be disabled in preview mode")
        _assert("Flat runtime preview | Base=1 | Override=1 | Hint=1" in str(panel.lbl_advanced_preview.text() or ""), "Advanced preview summary mismatch")
        diag = str(panel.txt_advanced_diagnostics.toPlainText() or "")
        _assert("Mode: new-plan authoring" in diag, "Advanced diagnostics should describe new-plan authoring mode")
        _assert("Grouped Model: Base=1 | Override=1 | Hint=1" in diag, "Advanced diagnostics grouped counts mismatch")
        _assert("Preview Order: BASE_A, OVR_A, HINT_A" in diag, "Advanced diagnostics preview order mismatch")
        _assert(panel.tbl_base.rowCount() == 1, f"Base group row count mismatch: {panel.tbl_base.rowCount()}")
        _assert(panel.tbl_override.rowCount() == 1, f"Override group row count mismatch: {panel.tbl_override.rowCount()}")
        _assert(panel.tbl_hint.rowCount() == 1, f"Hint group row count mismatch: {panel.tbl_hint.rowCount()}")
        _assert(str(panel._workflow_group_boxes["base"].title() or "") == "Base Regions (1)", "Base group title should include count")
        _assert(str(panel._workflow_group_boxes["override"].title() or "") == "Overrides (1)", "Override group title should include count")
        _assert(str(panel._workflow_group_boxes["hint"].title() or "") == "Hints (1)", "Hint group title should include count")
        _assert(not bool(panel._workflow_action_buttons["base"]["Split Selected"].isEnabled()), "Base split should stay disabled until a base row is selected")
        _assert(not bool(panel._workflow_action_buttons["hint"]["Accept"].isEnabled()), "Hint accept should stay disabled until a hint row is selected")
        _assert(not bool(panel.btn_apply_override_editor.isEnabled()), "Override editor apply should stay disabled until an override row is selected")
        _assert(str(panel.tbl_base.item(0, 0).text() or "") == "BASE_A", "Base summary id mismatch")
        _assert(str(panel.tbl_override.item(0, 0).text() or "") == "OVR_A", "Override summary id mismatch")
        _assert(str(panel.tbl_override.item(0, 1).text() or "") == "Ditch / Berm", "Override kind should be structured")
        _assert(str(panel.tbl_override.item(0, 2).text() or "") == "Left", "Override scope should show Left")
        _assert(str(panel.tbl_override.item(0, 4).text() or "") == "Berm", "Override action should show Berm")
        _assert(str(panel.tbl_hint.item(0, 0).text() or "") == "HINT_A", "Hint summary id mismatch")
        _assert(str(panel.tbl_hint.item(0, 1).text() or "") == "Typical Section / Urban Edge", "Hint source should show source and family")
        _assert("High" in str(panel.tbl_hint.item(0, 4).text() or ""), "Hint confidence should show High for urban roadside hints")
        _assert(str(panel.tbl_hint.item(0, 5).text() or "") == "Pending", "Hint status should show Pending")
        _assert(panel.tbl_timeline.rowCount() == 3, f"Timeline row count mismatch: {panel.tbl_timeline.rowCount()}")
        _assert(str(panel.tbl_timeline.item(0, 0).text() or "") == "Base", "Timeline should show base rows first")
        _assert(str(panel.tbl_timeline.item(1, 0).text() or "") == "Override", "Timeline should show override rows after base rows")
        _assert(str(panel.tbl_timeline.item(2, 0).text() or "") == "Hint", "Timeline should show hint rows after overrides")
        timeline = str(panel.txt_timeline_summary.toPlainText() or "")
        _assert("Base=1 | Override=1 | Hint=1" in timeline, "Timeline summary counts mismatch")
        _assert("BASE_A" in timeline and "OVR_A" in timeline and "HINT_A" in timeline, "Timeline summary should list all workflow rows")

        panel.tbl_base.setCurrentCell(0, 0)
        _assert(bool(panel._workflow_action_buttons["base"]["Split Selected"].isEnabled()), "Base split should enable for selected base rows")
        _assert(not bool(panel._workflow_action_buttons["base"]["Merge Selected"].isEnabled()), "Base merge should stay disabled when no adjacent merge partner exists")
        panel.tbl_override.setCurrentCell(0, 0)
        _assert(bool(panel.btn_apply_override_editor.isEnabled()), "Override editor apply should enable for a selected override")
        panel.tbl_hint.setCurrentCell(0, 0)
        _assert(bool(panel._workflow_action_buttons["hint"]["Accept"].isEnabled()), "Hint accept should enable for a selected hint")

        panel.chk_enable_advanced_edit.setChecked(True)
        _assert(bool(panel.btn_add.isEnabled()), "Advanced add button should enable when legacy editing is turned on")
        _assert("Legacy flat-row editing enabled" in str(panel.lbl_advanced_preview.text() or ""), "Advanced preview label should reflect legacy edit mode")
        _assert("Legacy Editing: enabled" in str(panel.txt_advanced_diagnostics.toPlainText() or ""), "Advanced diagnostics should reflect enabled legacy edit mode")
        panel._add_base_row()
        _assert(panel.tabs.currentIndex() == 1, "Adding from workflow should jump to Advanced tab")
        _assert(panel.table.rowCount() >= 4, "Advanced table should grow when adding a workflow row")

        print("[PASS] Region editor workflow grouping smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
