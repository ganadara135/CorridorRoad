import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.ui.task_typical_section_editor import TypicalSectionEditorTaskPanel


class CmdEditTypicalSection:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Typical Section",
            "ToolTip": "Create or edit a component-based typical road cross section",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = TypicalSectionEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditTypicalSection", CmdEditTypicalSection())

