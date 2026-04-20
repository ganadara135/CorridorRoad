# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor grouped-model smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_grouped_model.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorGroupedModel")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "OVR_B", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 20.0, "EndStation": 30.0, "Priority": 10, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Override B"},
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 40.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base A"},
                {"Id": "HINT_A", "RegionType": "retaining_wall_zone", "Layer": "overlay", "StartStation": 60.0, "EndStation": 70.0, "Priority": 20, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "typical:urban_edge:right", "SidePolicy": "", "DaylightPolicy": "right:off", "CorridorPolicy": "", "Enabled": False, "Notes": "Hint A", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Detected urban edge roadside pattern on the right side."},
                {"Id": "BASE_B", "RegionType": "bridge_approach", "Layer": "base", "StartStation": 40.0, "EndStation": 80.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "bridge_tpl", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base B"},
            ]
        )

        grouped = panel._group_rows()
        _assert([row.get("Id", "") for row in grouped.get("base_rows", [])] == ["BASE_A", "BASE_B"], "Grouped base order mismatch")
        _assert([row.get("Id", "") for row in grouped.get("override_rows", [])] == ["OVR_B"], "Grouped override order mismatch")
        _assert([row.get("Id", "") for row in grouped.get("hint_rows", [])] == ["HINT_A"], "Grouped hint order mismatch")

        flattened = panel._flatten_group_rows(grouped)
        _assert([row.get("Id", "") for row in flattened] == ["BASE_A", "BASE_B", "OVR_B", "HINT_A"], "Flattened grouped order mismatch")

        print("[PASS] Region editor grouped-model smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
