# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_corridor.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.corridor_compat import PREFERRED_COMMAND_ID
from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_corridor import CorridorTaskPanel


class CmdGenerateCorridor:
    def GetResources(self):
        return {
            "Pixmap": icon_path("corridor.svg"),
            "MenuText": "Build Corridor",
            "ToolTip": "Build corridor results from the current section set",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CorridorTaskPanel()
        Gui.Control.showDialog(panel)


_CMD = CmdGenerateCorridor()

if hasattr(Gui, "addCommand"):
    Gui.addCommand(PREFERRED_COMMAND_ID, _CMD)
