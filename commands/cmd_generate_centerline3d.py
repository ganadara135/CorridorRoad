# CorridorRoad/commands/cmd_generate_centerline3d.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_centerline3d_display import (
    Centerline3DDisplay,
    ViewProviderCenterline3DDisplay,
    ensure_centerline3d_display_properties,
)
from objects.obj_project import CorridorRoadProject, ensure_project_properties


def _find_project(doc):
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _find_alignment(doc):
    for o in doc.Objects:
        if o.Name.startswith("HorizontalAlignment"):
            return o
    return None


def _find_stationing(doc):
    for o in doc.Objects:
        if o.Name.startswith("Stationing"):
            return o
    return None


def _find_vertical_alignment(doc):
    for o in doc.Objects:
        if o.Name.startswith("VerticalAlignment"):
            return o
    return None


def _find_profile_bundle(doc):
    for o in doc.Objects:
        if o.Name.startswith("ProfileBundle"):
            return o
    return None


def _find_centerline3d(doc):
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3D":
            return o
        if o.Name.startswith("Centerline3D") and (not o.Name.startswith("Centerline3DDisplay")):
            return o
    return None


def _find_centerline3d_display(doc):
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3DDisplay":
            return o
        if o.Name.startswith("Centerline3DDisplay"):
            return o
    return None


class CmdGenerateCenterline3D:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Generate 3D Centerline",
            "ToolTip": "Create/update 3D centerline display from horizontal + vertical sources",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        aln = _find_alignment(doc)
        if aln is None:
            raise Exception("No HorizontalAlignment found. Create/Edit alignment first.")

        st = _find_stationing(doc)
        va = _find_vertical_alignment(doc)
        pb = _find_profile_bundle(doc)

        disp = _find_centerline3d_display(doc)
        if disp is None:
            disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
            Centerline3DDisplay(disp)
            ViewProviderCenterline3DDisplay(disp.ViewObject)
            disp.Label = "3D Centerline (H+V)"

        ensure_centerline3d_display_properties(disp)
        disp.Alignment = aln
        disp.Stationing = st
        disp.VerticalAlignment = va
        disp.ProfileBundle = pb
        disp.UseStationing = (st is not None)
        if va is None and pb is None:
            disp.ElevationSource = "FlatZero"
        else:
            disp.ElevationSource = "Auto"
        # Prefer direct source mode so display updates immediately by its own sampling props.
        disp.SourceCenterline = None
        disp.ShowWire = True
        disp.touch()

        # Cleanup legacy engine object if it exists from older workflow.
        cl = _find_centerline3d(doc)
        if cl is not None:
            if hasattr(disp, "SourceCenterline") and getattr(disp, "SourceCenterline", None) == cl:
                disp.SourceCenterline = None
            prj = _find_project(doc)
            if prj is not None and hasattr(prj, "Centerline3D") and getattr(prj, "Centerline3D", None) == cl:
                prj.Centerline3D = None
            try:
                doc.removeObject(cl.Name)
            except Exception:
                pass

        prj = _find_project(doc)
        if prj is not None:
            ensure_project_properties(prj)
            if hasattr(prj, "Centerline3DDisplay"):
                prj.Centerline3DDisplay = disp
            CorridorRoadProject.adopt(prj, disp)

            if getattr(prj, "Alignment", None) is None:
                prj.Alignment = aln
                CorridorRoadProject.adopt(prj, aln)

            if getattr(prj, "Stationing", None) is None and st is not None:
                prj.Stationing = st
                CorridorRoadProject.adopt(prj, st)

        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateCenterline3D", CmdGenerateCenterline3D())
