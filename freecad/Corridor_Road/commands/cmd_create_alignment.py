# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/commands/cmd_create_alignment.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
    get_coordinate_setup,
)
from freecad.Corridor_Road.objects.project_links import link_project


class CmdCreateAlignment:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Sample Alignment",
            "ToolTip": "Create a sample Horizontal Alignment (tangent + S-C-S transition curves)",
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
        obj = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(obj)
        ViewProviderHorizontalAlignment(obj.ViewObject)

        cst = get_coordinate_setup(prj)
        x0 = float(cst.get("LocalOriginX", 0.0))
        y0 = float(cst.get("LocalOriginY", 0.0))
        model_len = lambda meters: float(_units.model_length_from_meters(prj, float(meters)))
        delta_x = model_len(60.0)
        obj.IPPoints = [
            App.Vector(x0 + (0.0 - delta_x), y0 + 0.0, 0.0),
            App.Vector(x0 + (model_len(48.0) - delta_x), y0 + 0.0, 0.0),
            App.Vector(x0 + (model_len(66.0) - delta_x), y0 + model_len(24.0), 0.0),
            App.Vector(x0 + (model_len(108.0) - delta_x), y0 + model_len(24.0), 0.0),
        ]
        obj.CurveRadii = [0.0, 18.0, 18.0, 0.0]
        obj.TransitionLengths = [0.0, 8.0, 8.0, 0.0]
        obj.UseTransitionCurves = True
        obj.SpiralSegments = 20
        obj.Label = "Sample Alignment"

        link_project(prj, links={"Alignment": obj}, adopt_extra=[obj])

        obj.touch()
        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_CreateAlignment", CmdCreateAlignment())
