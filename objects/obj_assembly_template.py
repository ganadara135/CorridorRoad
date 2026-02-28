# CorridorRoad/objects/obj_assembly_template.py
import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None


def ensure_assembly_template_properties(obj):
    # Hard-remove legacy thickness properties.
    for legacy_prop in ("PavementThickness", "SolidThickness"):
        try:
            if hasattr(obj, legacy_prop):
                obj.removeProperty(legacy_prop)
        except Exception:
            pass

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

    if not hasattr(obj, "HeightLeft"):
        obj.addProperty("App::PropertyFloat", "HeightLeft", "Assembly", "Left depth for corridor solid (m, downward)")
        obj.HeightLeft = 0.30

    if not hasattr(obj, "HeightRight"):
        obj.addProperty("App::PropertyFloat", "HeightRight", "Assembly", "Right depth for corridor solid (m, downward)")
        obj.HeightRight = 0.30

    try:
        obj.setGroupOfProperty("HeightLeft", "Assembly")
        obj.setGroupOfProperty("HeightRight", "Assembly")
    except Exception:
        pass

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
            hl = max(0.0, float(getattr(obj, "HeightLeft", 0.0)))
            hr = max(0.0, float(getattr(obj, "HeightRight", 0.0)))

            dz_l = -lw * ls / 100.0
            dz_r = -rw * rs / 100.0

            p_l = App.Vector(+lw, dz_l, 0.0)
            p_c = App.Vector(0.0, 0.0, 0.0)
            p_r = App.Vector(-rw, dz_r, 0.0)

            # Display both crown line and solid-depth envelope so HeightLeft/Right
            # edits are visible immediately in 3D view.
            if max(hl, hr) <= 1e-9:
                obj.Shape = Part.makePolygon([p_l, p_c, p_r])
            else:
                h_c = 0.5 * (hl + hr)
                q_l = App.Vector(p_l.x, p_l.y - hl, p_l.z)
                q_c = App.Vector(p_c.x, p_c.y - h_c, p_c.z)
                q_r = App.Vector(p_r.x, p_r.y - hr, p_r.z)
                obj.Shape = Part.makePolygon([p_l, p_c, p_r, q_r, q_c, q_l, p_l])
            obj.Status = "OK"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if prop in (
            "LeftWidth",
            "RightWidth",
            "LeftSlopePct",
            "RightSlopePct",
            "HeightLeft",
            "HeightRight",
            "ShowTemplateWire",
        ):
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
                    if Gui is not None:
                        Gui.updateGui()
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
