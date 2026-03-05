# CorridorRoad/commands/cmd_generate_stations.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.doc_query import find_first, find_project
from objects.project_links import link_project
from objects.obj_stationing import Stationing, ViewProviderStationing
from objects.obj_project import get_length_scale


def _find_alignment(doc):
    return find_first(doc, name_prefixes=("HorizontalAlignment",))


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
        prj = find_project(doc)
        if prj is not None:
            link_project(
                prj,
                links={"Stationing": st},
                links_if_empty={"Alignment": aln},
                adopt_extra=[st],
            )

        doc.recompute()
        
        Gui.ActiveDocument.ActiveView.fitAll()


Gui.addCommand("CorridorRoad_GenerateStations", CmdGenerateStations())
