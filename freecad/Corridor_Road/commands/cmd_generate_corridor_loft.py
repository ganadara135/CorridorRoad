# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_corridor_loft.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_corridor_loft import CorridorLoftTaskPanel


class CmdGenerateCorridor:
    def GetResources(self):
        return {
            "Pixmap": icon_path("corridor.svg"),
            "MenuText": "Corridor",
            "ToolTip": "Generate corridor surface from SectionSet",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CorridorLoftTaskPanel()
        Gui.Control.showDialog(panel)


_CMD = CmdGenerateCorridor()

# Preferred user-facing command id.
Gui.addCommand("CorridorRoad_GenerateCorridor", _CMD)
# Compatibility alias kept for older workbench layouts/macros.
Gui.addCommand("CorridorRoad_GenerateCorridorLoft", _CMD)
