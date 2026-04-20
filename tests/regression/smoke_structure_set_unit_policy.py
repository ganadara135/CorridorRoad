# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Structure-set unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_structure_set_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet, ensure_structure_set_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_structure_editor import StructureEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRStructureSetUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"
        prj.LinearUnitImportDefault = "mm"

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        ensure_structure_set_properties(ss)

        ss.StructureIds = ["CULV-01"]
        ss.StructureTypes = ["culvert"]
        ss.StartStations = [20.0]
        ss.EndStations = [26.0]
        ss.CenterStations = [23.0]
        ss.Sides = ["center"]
        ss.Offsets = [0.0]
        ss.Widths = [6.0]
        ss.Heights = [2.5]
        ss.BottomElevations = [0.0]
        ss.Covers = [1.0]
        ss.WallThicknesses = [0.3]
        ss.FootingWidths = [0.0]
        ss.FootingThicknesses = [0.0]
        ss.CapHeights = [0.0]
        ss.CorridorMargins = [1.5]
        ss.ProfileStructureIds = ["CULV-01", "CULV-01"]
        ss.ProfileStations = [20.0, 26.0]
        ss.ProfileWidths = [5.0, 7.0]
        ss.ProfileHeights = [2.2, 2.8]
        ss.LengthSchemaVersion = 0
        ensure_structure_set_properties(ss)

        recs = StructureSet.records(ss)
        _assert(len(recs) == 1, "StructureSet should expose one migrated record")
        rec = recs[0]
        _assert(abs(float(rec["StartStation"]) - 20.0) < 1.0e-6, "StartStation should remain meter-native after schema refresh")
        _assert(abs(float(rec["EndStation"]) - 26.0) < 1.0e-6, "EndStation should remain meter-native after schema refresh")
        _assert(abs(float(rec["Width"]) - 6.0) < 1.0e-6, "Width should remain meter-native after schema refresh")
        _assert(abs(float(rec["Height"]) - 2.5) < 1.0e-6, "Height should remain meter-native after schema refresh")
        _assert(abs(float(rec["Cover"]) - 1.0) < 1.0e-6, "Cover should remain meter-native after schema refresh")
        _assert(abs(float(rec["CorridorMargin"]) - 1.5) < 1.0e-6, "CorridorMargin should remain meter-native after schema refresh")
        _assert(int(getattr(ss, "LengthSchemaVersion", 0) or 0) == 1, "StructureSet length schema should migrate to version 1")

        pts = StructureSet.profile_points(ss, "CULV-01")
        _assert(len(pts) == 2, "Profile points should remain available after migration")
        _assert(abs(float(pts[0]["Station"]) - 20.0) < 1.0e-6, "Profile station should remain meter-native after schema refresh")
        _assert(abs(float(pts[1]["Width"]) - 7.0) < 1.0e-6, "Profile width should remain meter-native after schema refresh")

        panel = StructureEditorTaskPanel()
        panel._populate_structure_table(recs)
        _assert(panel._get_cell_text(0, 2).strip() == "20000.000", "Structure table should display station in millimeters")
        _assert(panel._get_cell_text(0, 7).strip() == "6000.000", "Structure table should display width in millimeters")

        panel._set_cell_text(0, 2, "21000.000")
        panel._set_cell_text(0, 3, "27000.000")
        panel._set_cell_text(0, 7, "6500.000")
        rows = panel._read_rows()
        _assert(abs(float(rows[0]["StartStation"]) - 21.0) < 1.0e-6, "Displayed 21000 mm start station should read back as 21 m")
        _assert(abs(float(rows[0]["EndStation"]) - 27.0) < 1.0e-6, "Displayed 27000 mm end station should read back as 27 m")
        _assert(abs(float(rows[0]["Width"]) - 6.5) < 1.0e-6, "Displayed 6500 mm width should read back as 6.5 m")

        panel._set_profile_rows(list(pts))
        panel._set_profile_table_rows(pts, structure_id="CULV-01")
        _assert(panel.profile_table.item(0, 1).text().strip() == "20000.000", "Profile table should display station in millimeters")
        panel.profile_table.item(0, 1).setText("25000.000")
        panel.profile_table.item(0, 3).setText("6800.000")
        panel._active_profile_structure_id = "CULV-01"
        panel._sync_profile_table_to_store()
        synced = [row for row in list(panel._profile_rows or []) if str(row.get("StructureId", "")) == "CULV-01"]
        _assert(abs(float(synced[0]["Station"]) - 25.0) < 1.0e-6, "Displayed 25000 mm profile station should store as 25 m")
        _assert(abs(float(synced[0]["Width"]) - 6.8) < 1.0e-6, "Displayed 6800 mm profile width should store as 6.8 m")

        print("[PASS] Structure-set unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
