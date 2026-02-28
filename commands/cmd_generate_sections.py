# CorridorRoad/commands/cmd_generate_sections.py
import FreeCAD as App
import FreeCADGui as Gui

from ui.task_section_generator import SectionGeneratorTaskPanel


class CmdGenerateSections:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Generate Sections",
            "ToolTip": "Generate section set from assembly template (range/manual stations)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = SectionGeneratorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_GenerateSections", CmdGenerateSections())
