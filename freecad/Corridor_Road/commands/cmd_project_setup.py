# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree
from freecad.Corridor_Road.ui.task_project_setup import ProjectSetupTaskPanel


class CmdProjectSetup:
    def GetResources(self):
        return {
            "Pixmap": icon_path("project_setup.svg"),
            "MenuText": "Project Setup",
            "ToolTip": "Configure project CRS, origin, rotation, and datum",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        preferred = None
        try:
            sel = list(Gui.Selection.getSelection() or [])
            for o in sel:
                if str(getattr(o, "Name", "") or "").startswith("CorridorRoadProject"):
                    preferred = o
                    break
        except Exception:
            preferred = None
        if preferred is not None:
            try:
                ensure_project_properties(preferred)
                ensure_project_tree(preferred, include_references=False)
                CorridorRoadProject.auto_link(preferred.Document, preferred)
                preferred.touch()
                preferred.Document.recompute()
            except Exception:
                pass
        panel = ProjectSetupTaskPanel(preferred_project=preferred)
        Gui.Control.showDialog(panel)


Gui.addCommand("CorridorRoad_ProjectSetup", CmdProjectSetup())
