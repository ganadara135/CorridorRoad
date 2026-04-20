# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region editor dark theme color contrast smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_editor_dark_theme_colors.py
"""

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtGui, QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _set_dark_palette(app):
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#2b2f3a"))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#f2f4f8"))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#1f232c"))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#2b2f3a"))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#f2f4f8"))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#313640"))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#f2f4f8"))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#4d6f91"))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#f2f4f8"))
    app.setPalette(palette)


def _check_item_dark_contrast(item, label: str):
    _assert(item is not None, f"{label}: missing table item")
    bg = item.background().color()
    fg = item.foreground().color()
    _assert(bg.isValid(), f"{label}: invalid background color")
    _assert(fg.isValid(), f"{label}: invalid foreground color")
    _assert(bg.lightness() < 140, f"{label}: background should stay dark in dark theme")
    _assert(fg.lightness() > bg.lightness(), f"{label}: foreground should be lighter than background")


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    old_palette = app.palette()
    _set_dark_palette(app)
    doc = App.newDocument("CRRegionEditorDarkTheme")
    try:
        panel = RegionEditorTaskPanel()
        panel._populate_table(
            [
                {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 40.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": ""},
                {"Id": "OVR_A", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 20.0, "EndStation": 30.0, "Priority": 10, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "left:berm", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": ""},
                {"Id": "HINT_A", "RegionType": "retaining_wall_zone", "Layer": "overlay", "StartStation": 50.0, "EndStation": 60.0, "Priority": 20, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "typical:urban_edge:right", "SidePolicy": "", "DaylightPolicy": "right:off", "CorridorPolicy": "", "Enabled": False, "Notes": "", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Pending review"},
            ]
        )

        _check_item_dark_contrast(panel.tbl_base.item(0, 0), "base summary")
        _check_item_dark_contrast(panel.tbl_override.item(0, 0), "override summary")
        _check_item_dark_contrast(panel.tbl_hint.item(0, 0), "hint summary")
        _check_item_dark_contrast(panel.tbl_timeline.item(0, 0), "timeline base")
        _check_item_dark_contrast(panel.tbl_timeline.item(1, 0), "timeline override")
        _check_item_dark_contrast(panel.tbl_timeline.item(2, 0), "timeline hint")

        print("[PASS] Region editor dark theme color smoke test completed.")
    finally:
        app.setPalette(old_palette)
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
