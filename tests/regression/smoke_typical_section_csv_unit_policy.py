# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Typical-section CSV unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_typical_section_csv_unit_policy.py
"""

import os

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_typical_section_editor import TypicalSectionEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRTypicalSectionCsvUnitPolicy")
    comp_csv = os.path.join(os.getcwd(), f"_tmp_typical_components_{os.getpid()}.csv")
    pav_csv = os.path.join(os.getcwd(), f"_tmp_typical_pavement_{os.getpid()}.csv")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"
        prj.LinearUnitImportDefault = "mm"

        with open(comp_csv, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("Id,Type,Side,Width,CrossSlopePct,Height,ExtraWidth,BackSlopePct,Offset,Order,Enabled\n")
            fh.write("LANE-L,lane,left,3500,2,0,0,0,0,10,true\n")
            fh.write("CURB-L,curb,left,180,0,150,50,1,0,20,true\n")

        with open(pav_csv, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("# CorridorRoadUnits,linear=m\n")
            fh.write("Id,Type,Thickness,Enabled\n")
            fh.write("SURF,surface,0.05,true\n")
            fh.write("BASE,base,0.20,true\n")

        panel = TypicalSectionEditorTaskPanel()
        panel.txt_csv.setText(comp_csv)
        panel._load_csv()
        rows = [row for row in panel._read_rows() if str(row.get("Type", "") or "").strip()]
        _assert(len(rows) == 2, "Typical-section component CSV should load two rows")
        _assert(abs(float(rows[0]["Width"]) - 3.5) < 1.0e-6, "Component width should use project import default mm")
        _assert(abs(float(rows[1]["Height"]) - 0.15) < 1.0e-6, "Component height should use project import default mm")
        _assert("linear=mm" in str(panel.lbl_status.text() or ""), "Status should report resolved component CSV unit")
        _assert(panel._get_cell_text(0, 4) == "3500.000", "Component width cell should display project display unit")
        _assert(panel._get_cell_text(1, 6) == "150.000", "Component height cell should display project display unit")
        _assert(panel._get_cell_text(1, 7) == "50.000", "Component extra width cell should display project display unit")
        _assert(panel.lbl_info.text().lower().find("display unit: mm") >= 0, "Panel info should report display unit")

        panel.txt_pavement_csv.setText(pav_csv)
        panel._load_pavement_csv()
        pav_rows = [row for row in panel._read_pavement_rows() if str(row.get("Type", "") or "").strip()]
        _assert(len(pav_rows) == 2, "Pavement CSV should load two rows")
        _assert(abs(float(pav_rows[0]["Thickness"]) - 0.05) < 1.0e-6, "Pavement metadata linear=m should preserve meters")
        _assert("linear=m" in str(panel.lbl_status.text() or ""), "Status should report resolved pavement CSV unit")
        _assert(panel._get_pavement_cell_text(0, 2) == "50.000", "Pavement thickness cell should display project display unit")
        _assert("3730.000 mm" in str(panel.lbl_summary_width.text() or ""), "Summary top width should display project display unit")
        _assert("250.000 mm" in str(panel.lbl_summary_pavement.text() or ""), "Summary pavement thickness should display project display unit")

        print("[PASS] Typical-section CSV unit-policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass
        for path in (comp_csv, pav_csv):
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == "__main__":
    run()
