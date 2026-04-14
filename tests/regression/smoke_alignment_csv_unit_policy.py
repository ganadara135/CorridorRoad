# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Alignment CSV unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_alignment_csv_unit_policy.py
"""

import os

import FreeCAD as App

from freecad.Corridor_Road.objects.csv_alignment_import import inspect_alignment_csv, read_alignment_csv, write_alignment_csv
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def run():
    doc = App.newDocument("CRAlignmentCsvUnitPolicy")
    tmp_root = os.getcwd()
    suffix = str(os.getpid())
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "m"
        prj.LinearUnitImportDefault = "mm"
        prj.LinearUnitExportDefault = "mm"

        csv_no_meta = os.path.join(tmp_root, f"_tmp_alignment_no_meta_{suffix}.csv")
        with open(csv_no_meta, "w", encoding="utf-8-sig", newline="") as handle:
            handle.write("X,Y,Radius,TransitionLs,STA\n")
            handle.write("0,0,18000,8000,0\n")
            handle.write("100,0,0,0,100000\n")

        info = inspect_alignment_csv(csv_no_meta, doc_or_project=prj)
        _assert(str(info.get("linear_unit", "")) == "mm", "Inspect should resolve missing metadata from project import default")

        loaded = read_alignment_csv(csv_no_meta, doc_or_project=prj, has_header="yes", sort_mode="sta")
        rows = list(loaded.get("rows", []) or [])
        _assert(len(rows) == 2, "CSV without metadata should still load two rows")
        _assert(abs(float(rows[0][2]) - 18.0) < 1.0e-6, "18000 mm radius should import as 18 m")
        _assert(abs(float(rows[0][3]) - 8.0) < 1.0e-6, "8000 mm transition should import as 8 m")
        _assert(str(loaded.get("linear_unit", "")) == "mm", "Read should report resolved mm import unit")

        csv_meta_m = os.path.join(tmp_root, f"_tmp_alignment_meta_m_{suffix}.csv")
        with open(csv_meta_m, "w", encoding="utf-8-sig", newline="") as handle:
            handle.write("# CorridorRoadUnits,linear=m\n")
            handle.write("X,Y,Radius,TransitionLs,STA\n")
            handle.write("0,0,18,8,0\n")
            handle.write("100,0,0,0,100\n")

        loaded_meta = read_alignment_csv(csv_meta_m, doc_or_project=prj, has_header="yes", sort_mode="sta")
        rows_meta = list(loaded_meta.get("rows", []) or [])
        _assert(abs(float(rows_meta[0][2]) - 18.0) < 1.0e-6, "Metadata linear=m should preserve 18 m radius")
        _assert(abs(float(rows_meta[0][3]) - 8.0) < 1.0e-6, "Metadata linear=m should preserve 8 m transition")
        _assert(str(loaded_meta.get("linear_unit", "")) == "m", "Metadata should override project import default")

        csv_export = os.path.join(tmp_root, f"_tmp_alignment_export_{suffix}.csv")
        write_info = write_alignment_csv(
            csv_export,
            [(0.0, 0.0, 18.0, 8.0), (100.0, 0.0, 0.0, 0.0)],
            doc_or_project=prj,
            include_header=True,
        )
        text = _read_text(csv_export)
        _assert("linear=mm" in text, "Export should write linear unit metadata using project export default")
        _assert("18000.0,8000.0" in text, "Export should convert meter-native radius/transition back to mm")
        _assert(str(write_info.get("linear_unit", "")) == "mm", "Write should report resolved export unit")

        print("[PASS] Alignment CSV unit-policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass
        for path in (locals().get("csv_no_meta"), locals().get("csv_meta_m"), locals().get("csv_export")):
            try:
                if path:
                    os.remove(path)
            except Exception:
                pass


if __name__ == "__main__":
    run()
