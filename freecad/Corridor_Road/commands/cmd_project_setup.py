# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.commands.cmd_new_project import create_corridorroad_project
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree
from freecad.Corridor_Road.ui.task_project_setup import ProjectSetupTaskPanel


def _find_preferred_project(doc):
    if doc is None:
        return None
    try:
        sel = list(Gui.Selection.getSelection() or [])
        for obj in sel:
            if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject"):
                return obj
    except Exception:
        pass
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject"):
            return obj
    return None


class CmdProjectSetup:
    def GetResources(self):
        return {
            "Pixmap": icon_path("project_setup.svg"),
            "MenuText": "New/Project Setup",
            "ToolTip": "Create or configure a CorridorRoad project, CRS, origin, rotation, and datum",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        preferred = _find_preferred_project(doc)
        if preferred is None:
            preferred = create_corridorroad_project(doc)
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


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_ProjectSetup", CmdProjectSetup())
