import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.ui.task_alignment_editor import AlignmentEditorTaskPanel


class CmdEditAlignment:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Alignment",
            "ToolTip": "Edit alignment IP/radius/transition and run criteria checks",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = AlignmentEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditAlignment", CmdEditAlignment())
