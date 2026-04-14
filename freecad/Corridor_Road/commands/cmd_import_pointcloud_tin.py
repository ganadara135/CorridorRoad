# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets


class CmdImportPointCloudTIN:
    def GetResources(self):
        return {
            "Pixmap": icon_path("pointcloud_tin.svg"),
            "MenuText": "PointCloud TIN",
            "ToolTip": "Point cloud to TIN workflow (work in progress)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        QtWidgets.QMessageBox.information(None, "PointCloud TIN", "작업중입니다")


Gui.addCommand("CorridorRoad_ImportPointCloudTIN", CmdImportPointCloudTIN())
