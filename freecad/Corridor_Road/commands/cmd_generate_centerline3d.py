# CorridorRoad/commands/cmd_generate_centerline3d.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.project_links import link_project
from freecad.Corridor_Road.objects.obj_centerline3d_display import (
    Centerline3DDisplay,
    ViewProviderCenterline3DDisplay,
    ensure_centerline3d_display_properties,
)


def _find_alignment(doc):
    return find_first(doc, name_prefixes=("HorizontalAlignment",))


def _find_stationing(doc):
    return find_first(doc, name_prefixes=("Stationing",))


def _find_vertical_alignment(doc):
    return find_first(doc, name_prefixes=("VerticalAlignment",))


def _find_profile_bundle(doc):
    return find_first(doc, name_prefixes=("ProfileBundle",))


def _find_centerline3d(doc):
    return find_first(
        doc,
        proxy_type="Centerline3D",
        name_prefixes=("Centerline3D",),
        predicate=lambda o: not str(getattr(o, "Name", "")).startswith("Centerline3DDisplay"),
    )


def _find_centerline3d_display(doc):
    return find_first(doc, proxy_type="Centerline3DDisplay", name_prefixes=("Centerline3DDisplay",))


class CmdGenerateCenterline3D:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "3D Centerline",
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
            prj = find_project(doc)
            if prj is not None and hasattr(prj, "Centerline3D") and getattr(prj, "Centerline3D", None) == cl:
                prj.Centerline3D = None
            try:
                doc.removeObject(cl.Name)
            except Exception:
                pass

        prj = find_project(doc)
        if prj is not None:
            link_project(
                prj,
                links={"Centerline3DDisplay": disp},
                links_if_empty={"Alignment": aln, "Stationing": st},
                adopt_extra=[disp],
            )

        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateCenterline3D", CmdGenerateCenterline3D())
