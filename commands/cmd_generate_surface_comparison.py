# CorridorRoad/commands/cmd_generate_surface_comparison.py
import FreeCAD as App
import FreeCADGui as Gui

from ui.task_surface_comparison import SurfaceComparisonTaskPanel


class CmdGenerateSurfaceComparison:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Surface Comparison",
            "ToolTip": "Compare Existing(Mesh) and Design(Corridor top surface) for cut/fill",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = SurfaceComparisonTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateSurfaceComparison", CmdGenerateSurfaceComparison())
