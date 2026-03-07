# CorridorRoad/commands/cmd_create_alignment.py
import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets

from objects.obj_alignment import HorizontalAlignment, ViewProviderHorizontalAlignment
from objects.obj_project import (
    CorridorRoadProject,
    ALIGNMENT_HORIZONTAL,
    ensure_alignment_tree,
    ensure_project_tree,
    ensure_project_properties,
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

        # Sample uses 120 m total length with user/project scale.
        s = float(scale)
        cst = get_coordinate_setup(prj)
        x0 = float(cst.get("LocalOriginX", 0.0))
        y0 = float(cst.get("LocalOriginY", 0.0))
        deltaX = 60.0 * s
        obj.IPPoints = [
            App.Vector(x0 + (0 - deltaX), y0 + 0.0, 0),
            App.Vector(x0 + (48.0 * s - deltaX), y0 + 0.0, 0),
            App.Vector(x0 + (66.0 * s - deltaX), y0 + (24.0 * s), 0),
            App.Vector(x0 + (108.0 * s - deltaX), y0 + (24.0 * s), 0),
        ]
        # Keep sample geometry feasible so S-C-S transitions are preserved (not clamped to zero).
        obj.CurveRadii = [0.0, 18.0 * s, 18.0 * s, 0.0]
        obj.TransitionLengths = [0.0, 8.0 * s, 8.0 * s, 0.0]
        obj.UseTransitionCurves = True
        obj.SpiralSegments = 20
        obj.Label = "Sample Alignment"

        link_project(prj, links={"Alignment": obj}, adopt_extra=[obj])

        # Force immediate placement under ALN_<name>/Horizontal for this command path.
        try:
            aln_tree = ensure_alignment_tree(prj, alignment_obj=obj)
            horizontal = aln_tree.get(ALIGNMENT_HORIZONTAL, None)
            if horizontal is not None:
                try:
                    horizontal.addObject(obj)
                except Exception:
                    cur = list(getattr(horizontal, "Group", []) or [])
                    if obj not in cur:
                        cur.append(obj)
                        horizontal.Group = cur
            # Keep root project group clean (folders only).
            try:
                root_children = list(getattr(prj, "Group", []) or [])
                if obj in root_children:
                    prj.Group = [ch for ch in root_children if ch != obj]
            except Exception:
                pass
        except Exception:
            pass

        obj.touch()
        doc.recompute()

        Gui.ActiveDocument.ActiveView.fitAll()


Gui.addCommand("CorridorRoad_CreateAlignment", CmdCreateAlignment())
