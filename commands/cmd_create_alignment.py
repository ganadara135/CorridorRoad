# CorridorRoad/commands/cmd_create_alignment.py
import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets

from objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment
from objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
    get_coordinate_setup,
    get_length_scale,
)
from objects.project_links import link_project


def _ask_length_scale(default_value: float):
    val, ok = QtWidgets.QInputDialog.getDouble(
        None,
        "Sample Alignment Scale",
        "Length scale (internal units per meter)\n1 = meter, 1000 = millimeter-like",
        float(default_value),
        1e-6,
        1e9,
        6,
    )
    if not ok:
        return None
    return float(val)


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
        default_scale = get_length_scale(prj if prj is not None else doc, default=1.0)
        scale = _ask_length_scale(default_scale)
        if scale is None:
            return

        if prj is None:
            try:
                prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
            except Exception:
                prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
            CorridorRoadProject(prj)
            prj.Label = "CorridorRoad Project"

        ensure_project_properties(prj)
        ensure_project_tree(prj, include_references=False)
        prj.LengthScale = float(scale)

        obj = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(obj)
        ViewProviderHorizontalAlignment(obj.ViewObject)

        s = float(scale)
        cst = get_coordinate_setup(prj)
        x0 = float(cst.get("LocalOriginX", 0.0))
        y0 = float(cst.get("LocalOriginY", 0.0))
        delta_x = 60.0 * s
        obj.IPPoints = [
            App.Vector(x0 + (0.0 - delta_x), y0 + 0.0, 0.0),
            App.Vector(x0 + (48.0 * s - delta_x), y0 + 0.0, 0.0),
            App.Vector(x0 + (66.0 * s - delta_x), y0 + (24.0 * s), 0.0),
            App.Vector(x0 + (108.0 * s - delta_x), y0 + (24.0 * s), 0.0),
        ]
        obj.CurveRadii = [0.0, 18.0 * s, 18.0 * s, 0.0]
        obj.TransitionLengths = [0.0, 8.0 * s, 8.0 * s, 0.0]
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
