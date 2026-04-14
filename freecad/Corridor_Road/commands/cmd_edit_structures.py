# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.ui.task_structure_editor import StructureEditorTaskPanel


class CmdEditStructures:
    def GetResources(self):
        return {
            "Pixmap": icon_path("edit_structures.svg"),
            "MenuText": "Edit Structures",
            "ToolTip": "Edit structures used during section generation",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        panel = StructureEditorTaskPanel()
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_EditStructures", CmdEditStructures())

