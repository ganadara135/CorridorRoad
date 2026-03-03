# CorridorRoad/commands/cmd_generate_stations.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_stationing import Stationing, ViewProviderStationing
from objects.obj_project import CorridorRoadProject, get_length_scale


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


class CmdGenerateStations:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Stations",
            "ToolTip": "Create Stationing object and generate station ticks along alignment",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        aln = _find_alignment(doc)
        if aln is None:
            raise Exception("No HorizontalAlignment found. Run Sample Alignment first.")

        st = doc.addObject("Part::FeaturePython", "Stationing")
        Stationing(st)
        ViewProviderStationing(st.ViewObject)
        st.Alignment = aln
        scale = get_length_scale(doc, default=1.0)
        st.Interval = 20.0 * scale
        st.TickLength = 2.0 * scale
        st.ShowTicks = True
        st.Label = "Stations"

        # Project auto-link/adopt
        prj = _find_project(doc)
        if prj is not None:
            prj.Stationing = st
            CorridorRoadProject.adopt(prj, st)

            if prj.Alignment is None:
                prj.Alignment = aln
                CorridorRoadProject.adopt(prj, aln)

        doc.recompute()
        
        Gui.ActiveDocument.ActiveView.fitAll()


Gui.addCommand("CorridorRoad_GenerateStations", CmdGenerateStations())
