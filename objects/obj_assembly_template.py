# CorridorRoad/objects/obj_assembly_template.py
import FreeCAD as App
import Part


def ensure_assembly_template_properties(obj):
    if not hasattr(obj, "LeftWidth"):
        obj.addProperty("App::PropertyFloat", "LeftWidth", "Assembly", "Width to left side from centerline (m)")
        obj.LeftWidth = 4.0
    if not hasattr(obj, "RightWidth"):
        obj.addProperty("App::PropertyFloat", "RightWidth", "Assembly", "Width to right side from centerline (m)")
        obj.RightWidth = 4.0

    if not hasattr(obj, "LeftSlopePct"):
        obj.addProperty("App::PropertyFloat", "LeftSlopePct", "Assembly", "Cross slope (%) on left side (downward)")
        obj.LeftSlopePct = 2.0
    if not hasattr(obj, "RightSlopePct"):
        obj.addProperty("App::PropertyFloat", "RightSlopePct", "Assembly", "Cross slope (%) on right side (downward)")
        obj.RightSlopePct = 2.0

    if not hasattr(obj, "ShowTemplateWire"):
        obj.addProperty("App::PropertyBool", "ShowTemplateWire", "Display", "Show template wire (local profile view)")
        obj.ShowTemplateWire = True

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class AssemblyTemplate:
    """
    Cross-section template parameters for section generation.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "AssemblyTemplate"
        ensure_assembly_template_properties(obj)

    def execute(self, obj):
        ensure_assembly_template_properties(obj)
        try:
            if not bool(getattr(obj, "ShowTemplateWire", True)):
                obj.Shape = Part.Shape()
                obj.Status = "Hidden"
                return

            lw = max(0.0, float(getattr(obj, "LeftWidth", 0.0)))
            rw = max(0.0, float(getattr(obj, "RightWidth", 0.0)))
            ls = float(getattr(obj, "LeftSlopePct", 0.0))
            rs = float(getattr(obj, "RightSlopePct", 0.0))

            dz_l = -lw * ls / 100.0
            dz_r = -rw * rs / 100.0

            p_l = App.Vector(+lw, dz_l, 0.0)
            p_c = App.Vector(0.0, 0.0, 0.0)
            p_r = App.Vector(-rw, dz_r, 0.0)
            obj.Shape = Part.makePolygon([p_l, p_c, p_r])
            obj.Status = "OK"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if prop in ("LeftWidth", "RightWidth", "LeftSlopePct", "RightSlopePct", "ShowTemplateWire"):
            try:
                obj.touch()
                if obj.Document is not None:
                    # Propagate template edits to linked SectionSet objects.
                    for o in list(obj.Document.Objects):
                        try:
                            if getattr(o, "AssemblyTemplate", None) == obj:
                                o.touch()
                        except Exception:
                            pass
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderAssemblyTemplate:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 2
        except Exception:
            pass

    def getIcon(self):
        return ""

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines"]

    def getDefaultDisplayMode(self):
        return "Wireframe"

    def setDisplayMode(self, mode):
        return mode
