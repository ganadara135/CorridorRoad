import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_typical_section_editor import TypicalSectionEditorTaskPanel


class CmdEditTypicalSection:
    def GetResources(self):
        return {
            "Pixmap": icon_path("typical_section.svg"),
            "MenuText": "Typical Section",
            "ToolTip": "Edit the component-based typical section",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = TypicalSectionEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditTypicalSection", CmdEditTypicalSection())

