# CorridorRoad/objects/obj_project.py
import FreeCAD as App


def _find_first(doc, name_prefix: str):
    for o in doc.Objects:
        if o.Name.startswith(name_prefix):
            return o

    return None


def ensure_project_properties(obj):
    if not hasattr(obj, "Group"):
        obj.addProperty("App::PropertyLinkList", "Group", "CorridorRoad", "Contained objects")

    if not hasattr(obj, "Version"):
        obj.addProperty("App::PropertyString", "Version", "CorridorRoad", "Project schema version")
        obj.Version = "0.3"

    if not hasattr(obj, "Terrain"):
        obj.addProperty("App::PropertyLink", "Terrain", "CorridorRoad", "Link to EG terrain object")
    if not hasattr(obj, "Alignment"):
        obj.addProperty("App::PropertyLink", "Alignment", "CorridorRoad", "Link to horizontal alignment object")
    if not hasattr(obj, "Stationing"):
        obj.addProperty("App::PropertyLink", "Stationing", "CorridorRoad", "Link to stationing object")
    if not hasattr(obj, "ProfileEG"):
        obj.addProperty("App::PropertyLink", "ProfileEG", "CorridorRoad", "Link to existing ground profile object")
    if not hasattr(obj, "Centerline3D"):
        obj.addProperty("App::PropertyLink", "Centerline3D", "CorridorRoad", "Link to 3D centerline object")
    if not hasattr(obj, "Centerline3DDisplay"):
        obj.addProperty("App::PropertyLink", "Centerline3DDisplay", "CorridorRoad", "Link to 3D centerline display object")
    if not hasattr(obj, "AssemblyTemplate"):
        obj.addProperty("App::PropertyLink", "AssemblyTemplate", "CorridorRoad", "Link to assembly template object")
    if not hasattr(obj, "SectionSet"):
        obj.addProperty("App::PropertyLink", "SectionSet", "CorridorRoad", "Link to section set object")


class CorridorRoadProject:
    """
    Project container:
    - stores Links to key objects
    - optionally groups child objects via Group property (DocumentObjectGroup)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CorridorRoadProject"
        ensure_project_properties(obj)

    def execute(self, obj):
        ensure_project_properties(obj)
        # Container does not generate shape.
        return

    @staticmethod
    def adopt(obj_project, child):
        """Put child into project.Group if not already there."""
        if child is None:
            return

        group = list(getattr(obj_project, "Group", []) or [])
        if child not in group:
            group.append(child)
            obj_project.Group = group

    @staticmethod
    def auto_link(doc, obj_project):
        """Try to auto-detect first alignment/stationing/profile and link them."""
        if doc is None:
            return

        if obj_project.Alignment is None:
            a = _find_first(doc, "HorizontalAlignment")
            if a is not None:
                obj_project.Alignment = a

        if obj_project.Stationing is None:
            s = _find_first(doc, "Stationing")
            if s is not None:
                obj_project.Stationing = s

        if obj_project.ProfileEG is None:
            p = _find_first(doc, "ProfileEG")
            if p is not None:
                obj_project.ProfileEG = p

        if hasattr(obj_project, "Centerline3D") and obj_project.Centerline3D is None:
            c = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3D":
                    c = o
                    break
                if o.Name.startswith("Centerline3D") and (not o.Name.startswith("Centerline3DDisplay")):
                    c = o
                    break
            if c is not None:
                obj_project.Centerline3D = c

        if hasattr(obj_project, "Centerline3DDisplay") and obj_project.Centerline3DDisplay is None:
            d = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3DDisplay":
                    d = o
                    break
                if o.Name.startswith("Centerline3DDisplay"):
                    d = o
                    break
            if d is not None:
                obj_project.Centerline3DDisplay = d

        if hasattr(obj_project, "AssemblyTemplate") and obj_project.AssemblyTemplate is None:
            a = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "AssemblyTemplate":
                    a = o
                    break
                if o.Name.startswith("AssemblyTemplate"):
                    a = o
                    break
            if a is not None:
                obj_project.AssemblyTemplate = a

        if hasattr(obj_project, "SectionSet") and obj_project.SectionSet is None:
            s = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "SectionSet":
                    s = o
                    break
                if o.Name.startswith("SectionSet"):
                    s = o
                    break
            if s is not None:
                obj_project.SectionSet = s
