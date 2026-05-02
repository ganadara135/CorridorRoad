# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_centerline3d.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_centerline3d import Centerline3DTaskPanel


class CmdGenerateCenterline3D:
    def GetResources(self):
        return {
            "Pixmap": icon_path("centerline3d.svg"),
            "MenuText": "3D Centerline Utility",
            "ToolTip": "Open the 3D centerline utility for display and diagnostic support",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        Gui.Control.showDialog(Centerline3DTaskPanel())


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_GenerateCenterline3D", CmdGenerateCenterline3D())
