# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Surface-object length-schema smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_surface_length_schema.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_design_terrain import DesignTerrain, ensure_design_terrain_properties
from freecad.Corridor_Road.objects.obj_pointcloud_dem import PointCloudDEM, ensure_pointcloud_dem_properties
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRSurfaceLengthSchema")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)

        dtm = doc.addObject("Mesh::FeaturePython", "DesignTerrain")
        DesignTerrain(dtm)
        dtm.LengthSchemaVersion = 0
        dtm.CellSize = 1.0
        dtm.DomainMargin = 2.5
        ensure_design_terrain_properties(dtm)

        _assert(abs(float(dtm.CellSize) - 1.0) < 1.0e-9, "DesignTerrain cell size should remain meter-native")
        _assert(abs(float(dtm.DomainMargin) - 2.5) < 1.0e-9, "DesignTerrain domain margin should remain meter-native")
        _assert(int(getattr(dtm, "LengthSchemaVersion", 0) or 0) >= 1, "DesignTerrain length schema version should update")

        dem = doc.addObject("Mesh::FeaturePython", "PointCloudDEM")
        PointCloudDEM(dem)
        dem.LengthSchemaVersion = 0
        dem.CellSize = 4.0
        ensure_pointcloud_dem_properties(dem)

        _assert(abs(float(dem.CellSize) - 4.0) < 1.0e-9, "PointCloudDEM cell size should remain meter-native")
        _assert(int(getattr(dem, "LengthSchemaVersion", 0) or 0) >= 1, "PointCloudDEM length schema version should update")

        print("[PASS] Surface-object length-schema smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
