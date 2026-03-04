# CorridorRoad/commands/cmd_generate_design_grading_surface.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_design_grading_surface import DesignGradingSurface, ViewProviderDesignGradingSurface
from objects.obj_project import CorridorRoadProject, ensure_project_properties


def _find_project(doc):
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _find_section_set(doc):
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "SectionSet":
            return o
        if o.Name.startswith("SectionSet"):
            return o
    return None


def _find_design_grading_surface(doc):
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignGradingSurface":
            return o
        if o.Name.startswith("DesignGradingSurface"):
            return o
    return None


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

        prj = _find_project(doc)
        if prj is not None:
            ensure_project_properties(prj)
            if hasattr(prj, "DesignGradingSurface"):
                prj.DesignGradingSurface = surf
            if hasattr(prj, "SectionSet") and getattr(prj, "SectionSet", None) is None:
                prj.SectionSet = sec
            CorridorRoadProject.adopt(prj, surf)
            CorridorRoadProject.adopt(prj, sec)

        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateDesignGradingSurface", CmdGenerateDesignGradingSurface())
