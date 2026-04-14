# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
PointCloud CSV comment/unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_pointcloud_csv_comment_policy.py
"""

import os

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_pointcloud_dem import PointCloudDEM
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRPointCloudCsvCommentPolicy")
    csv_path = os.path.join(os.getcwd(), f"_tmp_pointcloud_comment_{os.getpid()}.csv")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitImportDefault = "mm"

        dem = doc.addObject("Mesh::FeaturePython", "PointCloudDEM")
        proxy = PointCloudDEM(dem)

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("# CorridorRoadUnits,linear=mm\n")
            fh.write("# comment line should be ignored\n")
            fh.write("easting,northing,elevation\n")
            fh.write("10,20,100\n")
            fh.write("15,25,101\n")

        pts, raw_count, skipped = proxy._read_points(dem, csv_path, "Auto", True, "World", "World")
        _assert(raw_count == 2, "PointCloud CSV reader should ignore comment rows when counting data rows")
        _assert(skipped == 0, "PointCloud CSV reader should not skip valid data rows after comment lines")
        _assert(len(pts) == 2, "PointCloud CSV reader should parse both data points")
        _assert(abs(float(pts[0][0]) - 10.0) < 1.0e-9, "PointCloud easting should remain raw file value")
        _assert(abs(float(pts[0][2]) - 100.0) < 1.0e-9, "PointCloud elevation should not be rescaled by project unit defaults")

        print("[PASS] PointCloud CSV comment/unit-policy smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass
        try:
            os.remove(csv_path)
        except Exception:
            pass


if __name__ == "__main__":
    run()
