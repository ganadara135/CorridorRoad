# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_create_alignment.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment


class CmdCreateAlignment:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Sample Alignment (v1)",
            "ToolTip": "Create a sample v1 Alignment source object",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        prj = find_project(doc)

        if prj is None:
            try:
                prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
            except Exception:
                prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
            CorridorRoadProject(prj)
            prj.Label = "CorridorRoad Project"

        ensure_project_properties(prj)
        ensure_project_tree(prj, include_references=False)
        obj = create_sample_v1_alignment(doc, project=prj, label="Main Alignment")

        link_project(prj, adopt_extra=[obj])

        obj.touch()
        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_CreateAlignment", CmdCreateAlignment())
