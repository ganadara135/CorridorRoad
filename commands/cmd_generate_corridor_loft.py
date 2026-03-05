# CorridorRoad/commands/cmd_generate_corridor_loft.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.doc_query import find_first, find_project
from objects.obj_corridor_loft import CorridorLoft, ViewProviderCorridorLoft
from objects.project_links import link_project


def _find_section_set(doc):
    return find_first(doc, proxy_type="SectionSet", name_prefixes=("SectionSet",))


def _find_corridor_loft(doc):
    return find_first(doc, proxy_type="CorridorLoft", name_prefixes=("CorridorLoft",))


class CmdGenerateCorridorLoft:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Corridor Loft",
            "ToolTip": "Create/update corridor loft from SectionSet",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        sec = _find_section_set(doc)
        if sec is None:
            raise Exception("No SectionSet found. Run Generate Sections first.")

        cor = _find_corridor_loft(doc)
        if cor is None:
            cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
            CorridorLoft(cor)
            ViewProviderCorridorLoft(cor.ViewObject)
            cor.Label = "Corridor Loft"

        cor.SourceSectionSet = sec
        try:
            if hasattr(cor, "OutputType"):
                cor.OutputType = "Solid"
        except Exception:
            pass
        cor.AutoUpdate = True
        cor.touch()

        prj = find_project(doc)
        if prj is not None:
            link_project(
                prj,
                links={"CorridorLoft": cor},
                links_if_empty={"SectionSet": sec},
                adopt_extra=[cor, sec],
            )

        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateCorridorLoft", CmdGenerateCorridorLoft())
