# CorridorRoad/commands/cmd_generate_corridor_loft.py
import FreeCAD as App
import FreeCADGui as Gui

from ui.task_corridor_loft import CorridorLoftTaskPanel


class CmdGenerateCorridorLoft:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Corridor Loft",
            "ToolTip": "Create/update corridor loft from SectionSet",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = CorridorLoftTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateCorridorLoft", CmdGenerateCorridorLoft())
