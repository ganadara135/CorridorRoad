# CorridorRoad/objects/obj_project.py
import FreeCAD as App


def _find_first(doc, name_prefix: str):
    for o in doc.Objects:
        if o.Name.startswith(name_prefix):
            return o

    return None


class CorridorRoadProject:
    """
    Project container:
    - stores Links to key objects
    - optionally groups child objects via Group property (DocumentObjectGroup)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CorridorRoadProject"

        # Group-capable base type is recommended, but App::FeaturePython also works with a Group property.
        # We'll add Group property explicitly.
        if not hasattr(obj, "Group"):
            obj.addProperty("App::PropertyLinkList", "Group", "CorridorRoad", "Contained objects")

        obj.addProperty("App::PropertyString", "Version", "CorridorRoad", "Project schema version")
        obj.Version = "0.2"

        obj.addProperty("App::PropertyLink", "Terrain", "CorridorRoad", "Link to EG terrain object")
        obj.addProperty("App::PropertyLink", "Alignment", "CorridorRoad", "Link to horizontal alignment object")
        obj.addProperty("App::PropertyLink", "Stationing", "CorridorRoad", "Link to stationing object")
        obj.addProperty("App::PropertyLink", "ProfileEG", "CorridorRoad", "Link to existing ground profile object")

    def execute(self, obj):
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
