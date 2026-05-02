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
    resolve_project_corridor,
)
from freecad.Corridor_Road.ui.task_project_setup import ProjectSetupTaskPanel


def create_corridorroad_project(doc):
    """Create the v1 project root and adopt any compatible existing design objects."""
    if doc is None:
        raise Exception("No active document.")

    try:
        obj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(obj)
    ensure_project_properties(obj)
    ensure_project_tree(obj, include_references=False)
    obj.Label = "CorridorRoad Project"

    CorridorRoadProject.auto_link(doc, obj)

    if obj.Alignment is not None:
        CorridorRoadProject.adopt(obj, obj.Alignment)

    if obj.Stationing is not None:
        CorridorRoadProject.adopt(obj, obj.Stationing)

    if hasattr(obj, "Centerline3D") and obj.Centerline3D is not None:
        CorridorRoadProject.adopt(obj, obj.Centerline3D)
    if hasattr(obj, "Centerline3DDisplay") and obj.Centerline3DDisplay is not None:
        CorridorRoadProject.adopt(obj, obj.Centerline3DDisplay)
    if hasattr(obj, "AssemblyTemplate") and obj.AssemblyTemplate is not None:
        CorridorRoadProject.adopt(obj, obj.AssemblyTemplate)
    if hasattr(obj, "SectionSet") and obj.SectionSet is not None:
        CorridorRoadProject.adopt(obj, obj.SectionSet)
    corridor_obj = resolve_project_corridor(obj)
    if corridor_obj is not None:
        CorridorRoadProject.adopt(obj, corridor_obj)
    if hasattr(obj, "DesignGradingSurface") and obj.DesignGradingSurface is not None:
        CorridorRoadProject.adopt(obj, obj.DesignGradingSurface)
    if hasattr(obj, "DesignTerrain") and obj.DesignTerrain is not None:
        CorridorRoadProject.adopt(obj, obj.DesignTerrain)
    if hasattr(obj, "CutFillCalc") and obj.CutFillCalc is not None:
        CorridorRoadProject.adopt(obj, obj.CutFillCalc)

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
            Gui.Control.showDialog(ProjectSetupTaskPanel(preferred_project=obj))
        except Exception:
            pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_NewProject", CmdNewProject())
