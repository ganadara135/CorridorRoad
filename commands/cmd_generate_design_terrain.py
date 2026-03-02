# CorridorRoad/commands/cmd_generate_design_terrain.py
import FreeCAD as App
import FreeCADGui as Gui

from objects.obj_design_terrain import DesignTerrain, ViewProviderDesignTerrain
from objects.obj_project import CorridorRoadProject, ensure_project_properties


def _is_mesh_object(obj):
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _is_shape_object(obj):
    try:
        return hasattr(obj, "Shape") and obj.Shape is not None and (not obj.Shape.isNull())
    except Exception:
        return False


def _find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _find_design_grading_surface(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignGradingSurface":
            return o
        if o.Name.startswith("DesignGradingSurface"):
            return o
    return None


def _find_design_terrain(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignTerrain":
            return o
        if o.Name.startswith("DesignTerrain"):
            return o
    return None


def _find_terrain_candidate(doc):
    if doc is None:
        return None
    # 1) Prefer explicit terrain-like names.
    for o in doc.Objects:
        try:
            nm = str(getattr(o, "Name", "") or "").lower()
            lb = str(getattr(o, "Label", "") or "").lower()
            if ("terrain" in nm or "terrain" in lb) and (_is_mesh_object(o) or _is_shape_object(o)):
                return o
        except Exception:
            continue
    # 2) Prefer mesh fallback.
    for o in doc.Objects:
        if _is_mesh_object(o):
            return o
    # 3) Last fallback: surface-like shape names.
    for o in doc.Objects:
        try:
            nm = str(getattr(o, "Name", "") or "").lower()
            lb = str(getattr(o, "Label", "") or "").lower()
            if ("surface" in nm or "surface" in lb or "eg" in nm or "existing" in nm) and _is_shape_object(o):
                return o
        except Exception:
            continue
    return None


class CmdGenerateDesignTerrain:
    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Design Terrain",
            "ToolTip": "Create/update composite design terrain from DesignGradingSurface and Existing Terrain",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            raise Exception("No active document.")

        dsg = _find_design_grading_surface(doc)
        if dsg is None:
            raise Exception("No DesignGradingSurface found. Run Generate Design Grading Surface first.")

        prj = _find_project(doc)
        eg = getattr(prj, "Terrain", None) if prj is not None else None
        if eg is None:
            eg = _find_terrain_candidate(doc)
        if eg is None:
            raise Exception("Existing terrain source is missing (Project.Terrain or terrain object in document).")

        dtm = _find_design_terrain(doc)
        if dtm is None:
            dtm = doc.addObject("Part::FeaturePython", "DesignTerrain")
            DesignTerrain(dtm)
            ViewProviderDesignTerrain(dtm.ViewObject)
            dtm.Label = "Design Terrain"

        dtm.SourceDesignSurface = dsg
        dtm.ExistingTerrain = eg
        dtm.AutoUpdate = True
        dtm.touch()

        if prj is not None:
            ensure_project_properties(prj)
            if hasattr(prj, "Terrain") and getattr(prj, "Terrain", None) is None:
                prj.Terrain = eg
            if hasattr(prj, "DesignGradingSurface"):
                prj.DesignGradingSurface = dsg
            if hasattr(prj, "DesignTerrain"):
                prj.DesignTerrain = dtm
            CorridorRoadProject.adopt(prj, dsg)
            CorridorRoadProject.adopt(prj, dtm)

        doc.recompute()
        try:
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass


Gui.addCommand("CorridorRoad_GenerateDesignTerrain", CmdGenerateDesignTerrain())
