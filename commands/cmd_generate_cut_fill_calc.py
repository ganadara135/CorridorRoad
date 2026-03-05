# CorridorRoad/commands/cmd_generate_cut_fill_calc.py
import FreeCAD as App
import FreeCADGui as Gui

from ui.task_cut_fill_calc import CutFillCalcTaskPanel


class CmdGenerateCutFillCalc:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Cut-Fill Calc",
            "ToolTip": "Cut/Fill calculation from Existing(Mesh) vs Design(Corridor top surface)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CutFillCalcTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateCutFillCalc", CmdGenerateCutFillCalc())
