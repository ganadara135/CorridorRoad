# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_design_terrain.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_design_terrain import DesignTerrainTaskPanel


class CmdGenerateDesignTerrain:
    def GetResources(self):
        return {
            "Pixmap": icon_path("design_terrain.svg"),
            "MenuText": "Build Design Terrain",
            "ToolTip": "Merge the design grading surface with existing terrain",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = DesignTerrainTaskPanel()
        Gui.Control.showDialog(panel)


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_GenerateDesignTerrain", CmdGenerateDesignTerrain())
