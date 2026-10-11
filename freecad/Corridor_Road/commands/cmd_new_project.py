# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_new_project.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
)


def create_corridorroad_project(doc):
    """Create the v1 project root and place the existing v1 design objects in its tree."""
    if doc is None:
        raise Exception("No active document.")

    try:
        obj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(obj)
    ensure_project_properties(obj)
    ensure_project_tree(obj, include_references=False)
    obj.Label = "Parametric Road Project"

    CorridorRoadProject.auto_link(doc, obj)

    doc.recompute()
    return obj


def _find_existing_project(doc):
    if doc is None:
        return None
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject"):
            return obj
    return None


class CmdNewProject:
    def GetResources(self):
        return {
            "Pixmap": icon_path("project_setup.svg"),
            "MenuText": "New/Project Setup",
            "ToolTip": "Create or configure a CorridorRoad project",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        obj = _find_existing_project(doc) or create_corridorroad_project(doc)
        ensure_project_properties(obj)
        ensure_project_tree(obj, include_references=False)
        CorridorRoadProject.auto_link(doc, obj)
        obj.touch()
        doc.recompute()

        try:
            # imported here: the v1 command imports create_corridorroad_project from this module
            from freecad.Corridor_Road.v1.commands.cmd_project_setup import run_v1_project_setup_command

            # this command has already prepared and recomputed the project
            run_v1_project_setup_command(doc, preferred_project=obj, prepare_project=False)
        except Exception as exc:
            App.Console.PrintError(f"Project Setup panel was not opened: {exc}\n")


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_NewProject", CmdNewProject())
