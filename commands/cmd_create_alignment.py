# CorridorRoad/commands/cmd_create_alignment.py
import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets

from objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment
from objects.obj_project import CorridorRoadProject, ensure_project_properties, find_project, get_length_scale


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
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
            CorridorRoadProject(prj)
            prj.Label = "CorridorRoad Project"
        ensure_project_properties(prj)
        prj.LengthScale = float(scale)

        obj = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(obj)
        ViewProviderHorizontalAlignment(obj.ViewObject)

        # Sample uses 120 m total length with user/project scale.
        s = float(scale)
        deltaX = 60.0 * s
        obj.IPPoints = [
            App.Vector(0 - deltaX, 0, 0),
            App.Vector(48.0 * s - deltaX, 0, 0),
            App.Vector(66.0 * s - deltaX, 24.0 * s, 0),
            App.Vector(108.0 * s - deltaX, 24.0 * s, 0),
        ]
        # Keep sample geometry feasible so S-C-S transitions are preserved (not clamped to zero).
        obj.CurveRadii = [0.0, 18.0 * s, 18.0 * s, 0.0]
        obj.TransitionLengths = [0.0, 8.0 * s, 8.0 * s, 0.0]
        obj.UseTransitionCurves = True
        obj.SpiralSegments = 20
        obj.Label = "Sample Alignment"

        if hasattr(prj, "Alignment"):
            prj.Alignment = obj
        CorridorRoadProject.adopt(prj, obj)

        obj.touch()
        doc.recompute()

        Gui.ActiveDocument.ActiveView.fitAll()


Gui.addCommand("CorridorRoad_CreateAlignment", CmdCreateAlignment())
