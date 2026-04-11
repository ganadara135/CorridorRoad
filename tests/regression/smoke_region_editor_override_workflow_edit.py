# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor override workflow edit smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_override_workflow_edit.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorOverrideWorkflowEdit")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 100.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base A"},
                {"Id": "OVR_A", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 20.0, "EndStation": 30.0, "Priority": 10, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Override A"},
            ]
        )

        panel.tbl_override.setCurrentCell(0, 0)
        panel._load_selected_override_into_editor()

        _assert(str(panel.cmb_override_kind.currentText() or "") == "Ditch / Berm", "Override editor should load current kind")
        _assert(str(panel.cmb_override_scope.currentText() or "") == "Left", "Override editor should load current scope")
        _assert(str(panel.cmb_override_action.currentText() or "") == "Berm", "Override editor should load current action")

        panel._set_combo_value(panel.cmb_override_kind, "Corridor Zone")
        panel._set_combo_value(panel.cmb_override_scope, "Both")
        panel._set_combo_value(panel.cmb_override_action, "Skip Corridor")
        panel.txt_override_start.setText("22.500")
        panel.txt_override_end.setText("32.500")
        panel._apply_override_editor()

        rows = panel._read_rows()
        override = next(row for row in rows if str(row.get("Id", "") or "") == "OVR_A")
        _assert(str(override.get("RegionType", "") or "") == "other", "Workflow edit should remap override type")
        _assert(str(override.get("SidePolicy", "") or "") == "", "Workflow edit should clear side policy for corridor zone")
        _assert(str(override.get("CorridorPolicy", "") or "") == "skip_zone", "Workflow edit should set skip corridor policy")
        _assert(abs(float(override.get("StartStation", 0.0) or 0.0) - 22.5) < 1e-6, "Workflow edit should update start station")
        _assert(abs(float(override.get("EndStation", 0.0) or 0.0) - 32.5) < 1e-6, "Workflow edit should update end station")

        _assert(str(panel.tbl_override.item(0, 1).text() or "") == "Corridor Zone", "Override summary should refresh kind")
        _assert(str(panel.tbl_override.item(0, 2).text() or "") == "Both", "Override summary should refresh scope")
        _assert(str(panel.tbl_override.item(0, 4).text() or "") == "Skip Corridor", "Override summary should refresh action")

        print("[PASS] Region editor override workflow edit smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
