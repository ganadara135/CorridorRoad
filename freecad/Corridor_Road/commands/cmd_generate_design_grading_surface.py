# CorridorRoad/commands/cmd_generate_design_grading_surface.py
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface, ViewProviderDesignGradingSurface
from freecad.Corridor_Road.objects.project_links import link_project


def _find_section_set(doc):
    return find_first(doc, proxy_type="SectionSet", name_prefixes=("SectionSet",))


def _find_design_grading_surface(doc):
    return find_first(doc, proxy_type="DesignGradingSurface", name_prefixes=("DesignGradingSurface",))


class CmdGenerateDesignGradingSurface:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Design Grading Surface",
            "ToolTip": "Create/update design grading surface (road + side slopes) from SectionSet",
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

        surf = _find_design_grading_surface(doc)
        if surf is None:
            surf = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
            DesignGradingSurface(surf)
            ViewProviderDesignGradingSurface(surf.ViewObject)
            surf.Label = "Design Grading Surface"

        surf.SourceSectionSet = sec
        surf.AutoUpdate = True
        surf.touch()

        prj = find_project(doc)
        if prj is not None:
            link_project(
                prj,
                links={"DesignGradingSurface": surf},
                links_if_empty={"SectionSet": sec},
                adopt_extra=[surf, sec],
            )

        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateDesignGradingSurface", CmdGenerateDesignGradingSurface())
