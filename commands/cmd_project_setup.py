import FreeCAD as App
import FreeCADGui as Gui

from ui.task_project_setup import ProjectSetupTaskPanel


class CmdProjectSetup:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Project Setup",
            "ToolTip": "Set project coordinate system (CRS/origin/rotation/datum)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = ProjectSetupTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_ProjectSetup", CmdProjectSetup())
