# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor override starter smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_override_starters.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionEditorOverrideStarters")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 100.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "roadway_default", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "Base A"},
            ]
        )

        panel._add_override_ditch_left()
        panel._add_override_urban_right()
        panel._add_override_split_zone()
        panel._add_override_skip_zone()

        rows = panel._read_rows()
        override_rows = [row for row in rows if str(row.get("Layer", "") or "").strip().lower() == "overlay"]
        _assert(len(override_rows) == 4, f"Expected four override starter rows, got {len(override_rows)}")

        ditch = next(row for row in override_rows if str(row.get("SidePolicy", "") or "") == "left:berm")
        urban = next(row for row in override_rows if str(row.get("DaylightPolicy", "") or "") == "right:off")
        split = next(row for row in override_rows if str(row.get("CorridorPolicy", "") or "") == "split_only")
        skip = next(row for row in override_rows if str(row.get("CorridorPolicy", "") or "") == "skip_zone")

        _assert(str(ditch.get("RegionType", "") or "") == "ditch_override", "Ditch starter should use ditch_override")
        _assert(str(urban.get("RegionType", "") or "") == "retaining_wall_zone", "Urban starter should use retaining_wall_zone")
        _assert(str(split.get("RegionType", "") or "") == "other", "Split starter should use generic region type")
        _assert(str(skip.get("RegionType", "") or "") == "other", "Skip starter should use generic region type")

        _assert(panel.tbl_override.rowCount() == 4, f"Override summary should show four rows, got {panel.tbl_override.rowCount()}")
        _assert(any(str(panel.tbl_override.item(i, 1).text() or "") == "Urban Edge" for i in range(panel.tbl_override.rowCount())), "Override summary should expose Urban Edge kind")
        _assert(any(str(panel.tbl_override.item(i, 4).text() or "") == "Split Corridor" for i in range(panel.tbl_override.rowCount())), "Override summary should expose Split Corridor action")
        _assert(any(str(panel.tbl_override.item(i, 4).text() or "") == "Skip Corridor" for i in range(panel.tbl_override.rowCount())), "Override summary should expose Skip Corridor action")

        print("[PASS] Region editor override starter smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
