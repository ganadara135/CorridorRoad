# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_region_editor import RegionEditorTaskPanel


class CmdEditRegions:
    def GetResources(self):
        return {
            "Pixmap": icon_path("edit_regions.svg"),
            "MenuText": "Manage Regions",
            "ToolTip": "Edit region spans for sections and corridor behavior",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = RegionEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditRegions", CmdEditRegions())
