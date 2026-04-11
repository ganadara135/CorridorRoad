# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region CSV unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_csv_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRRegionCsvUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"
        prj.LinearUnitImportDefault = "mm"
        prj.LinearUnitExportDefault = "mm"

        panel = RegionEditorTaskPanel()
        csv_mm = (
            "Id,RegionType,Layer,StartStation,EndStation,Priority,TransitionIn,TransitionOut,TemplateName,AssemblyName,RuleSet,SidePolicy,DaylightPolicy,CorridorPolicy,Enabled,Notes,HintSource,HintStatus,HintReason,HintConfidence\n"
            "BASE_01,roadway,base,20000,60000,0,5000,8000,roadway_default,,,,,true,Base zone,,,,0\n"
        )
        rows_mm = panel._rows_from_csv_text(csv_mm)
        _assert(len(rows_mm) == 1, "Region CSV without metadata should import one row")
        _assert(abs(float(rows_mm[0]["StartStation"]) - 20.0) < 1.0e-6, "StartStation should use project import default mm")
        _assert(abs(float(rows_mm[0]["TransitionOut"]) - 8.0) < 1.0e-6, "TransitionOut should use project import default mm")

        csv_m = (
            "# CorridorRoadUnits,linear=m\n"
            "Id,RegionType,Layer,StartStation,EndStation,Priority,TransitionIn,TransitionOut,TemplateName,AssemblyName,RuleSet,SidePolicy,DaylightPolicy,CorridorPolicy,Enabled,Notes,HintSource,HintStatus,HintReason,HintConfidence\n"
            "BASE_02,roadway,base,20,60,0,5,8,roadway_default,,,,,true,Base zone,,,,0\n"
        )
        rows_m = panel._rows_from_csv_text(csv_m)
        _assert(abs(float(rows_m[0]["StartStation"]) - 20.0) < 1.0e-6, "Metadata linear=m should preserve start station meters")
        _assert(abs(float(rows_m[0]["TransitionIn"]) - 5.0) < 1.0e-6, "Metadata linear=m should preserve transition meters")

        exported = panel._rows_to_csv_text(rows_m)
        _assert("linear=mm" in exported, "Region CSV export should use project export default")
        _assert("20000.000" in exported and "8000.000" in exported, "Region CSV export should convert meter-native values to export unit")

        panel._populate_table(rows_m)
        _assert(panel._get_cell_text(0, 3) == "20000.000", "Region table should display start station in display unit")
        _assert(panel._get_cell_text(0, 4) == "60000.000", "Region table should display end station in display unit")
        _assert(panel._get_cell_text(0, 6) == "5000.000", "Region table should display transition-in in display unit")
        _assert(panel._get_cell_text(0, 7) == "8000.000", "Region table should display transition-out in display unit")

        rows_roundtrip = panel._read_rows()
        _assert(abs(float(rows_roundtrip[0]["StartStation"]) - 20.0) < 1.0e-6, "Region table read-back should convert display unit back to meters")
        _assert(abs(float(rows_roundtrip[0]["TransitionOut"]) - 8.0) < 1.0e-6, "Region table transition read-back should convert display unit back to meters")

        alignment = doc.addObject("App::FeaturePython", "HorizontalAlignment")
        alignment.addProperty("App::PropertyFloat", "DesignSpeedKph", "CorridorRoad", "Design speed")
        alignment.DesignSpeedKph = 60.0
        hint_rows = panel._project_standard_seed_rows(prj, alignment, 0.0, 100.0)
        _assert(len(hint_rows) >= 1, "Project standard seed should create at least one hint row")
        hint_reason = str(hint_rows[0].get("HintReason", "") or "")
        _assert(" mm" in hint_reason, "Project standard hint should describe criteria in display unit")
        _assert(" m)" not in hint_reason, "Project standard hint should not keep hard-coded meter suffix")

        print("[PASS] Region CSV unit-policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
