# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_import_pointcloud_dem.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.ui.task_pointcloud_dem import PointCloudDEMTaskPanel


class CmdImportPointCloudDEM:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Import PointCloud DEM",
            "ToolTip": "Import UTM CSV point cloud (E/N/Z) and build DEM mesh terrain",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = PointCloudDEMTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_ImportPointCloudDEM", CmdImportPointCloudDEM())
