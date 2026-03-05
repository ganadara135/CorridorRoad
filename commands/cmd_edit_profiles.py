# CorridorRoad/commands/cmd_edit_profiles.py
import FreeCAD as App
import FreeCADGui as Gui

from ui.task_profile_editor import ProfileEditorTaskPanel


class CmdEditProfiles:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Edit Profiles (Data/EG)",
            "ToolTip": "Edit profile data (Data/EG) and FG display/source settings by station",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = ProfileEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditProfiles", CmdEditProfiles())
