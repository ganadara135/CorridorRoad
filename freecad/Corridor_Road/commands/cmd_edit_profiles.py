# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_edit_profiles.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_profile_editor import ProfileEditorTaskPanel


class CmdEditProfiles:
    def GetResources(self):
        return {
            "Pixmap": icon_path("edit_profiles.svg"),
            "MenuText": "Edit Profiles (Data/EG)",
            "ToolTip": "Edit Data/EG profiles and FG sources",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = ProfileEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditProfiles", CmdEditProfiles())
