# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_generate_cut_fill_calc.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_cut_fill_calc import CutFillCalcTaskPanel


class CmdGenerateCutFillCalc:
    def GetResources(self):
        return {
            "Pixmap": icon_path("cut_fill.svg"),
            "MenuText": "Cut-Fill Calc",
            "ToolTip": "Calculate cut and fill from existing vs design surfaces",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CutFillCalcTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateCutFillCalc", CmdGenerateCutFillCalc())
