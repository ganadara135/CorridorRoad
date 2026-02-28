# CorridorRoad/commands/cmd_generate_corridor_loft.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_corridor_loft import CorridorLoft, ViewProviderCorridorLoft
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


def _find_corridor_loft(doc):
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "CorridorLoft":
            return o
        if o.Name.startswith("CorridorLoft"):
            return o
    return None


class CmdGenerateCorridorLoft:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Generate Corridor Loft",
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

        prj = _find_project(doc)
        if prj is not None:
            ensure_project_properties(prj)
            if hasattr(prj, "CorridorLoft"):
                prj.CorridorLoft = cor
            if hasattr(prj, "SectionSet") and getattr(prj, "SectionSet", None) is None:
                prj.SectionSet = sec
            CorridorRoadProject.adopt(prj, cor)
            CorridorRoadProject.adopt(prj, sec)

        doc.recompute()

        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateCorridorLoft", CmdGenerateCorridorLoft())
