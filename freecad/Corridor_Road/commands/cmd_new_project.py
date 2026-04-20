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


class CmdNewProject:
    def GetResources(self):
        return {
            "Pixmap": icon_path("new_project.svg"),
            "MenuText": "New Project",
            "ToolTip": "Create a new CorridorRoad project",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
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

        # Try auto-link and adopt existing objects
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

        try:
            Gui.Control.showDialog(ProjectSetupTaskPanel(preferred_project=obj))
        except Exception:
            pass


Gui.addCommand("CorridorRoad_NewProject", CmdNewProject())
