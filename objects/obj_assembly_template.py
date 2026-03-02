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

    if not hasattr(obj, "UseSideSlopes"):
        obj.addProperty("App::PropertyBool", "UseSideSlopes", "Assembly", "Enable side slope wings")
        obj.UseSideSlopes = False
    if not hasattr(obj, "LeftSideWidth"):
        obj.addProperty("App::PropertyFloat", "LeftSideWidth", "Assembly", "Left side slope horizontal width (m)")
        obj.LeftSideWidth = 0.0
    if not hasattr(obj, "RightSideWidth"):
        obj.addProperty("App::PropertyFloat", "RightSideWidth", "Assembly", "Right side slope horizontal width (m)")
        obj.RightSideWidth = 0.0
    if not hasattr(obj, "LeftSideSlopePct"):
        obj.addProperty("App::PropertyFloat", "LeftSideSlopePct", "Assembly", "Left side slope (%) downward outward")
        obj.LeftSideSlopePct = 50.0
    if not hasattr(obj, "RightSideSlopePct"):
        obj.addProperty("App::PropertyFloat", "RightSideSlopePct", "Assembly", "Right side slope (%) downward outward")
        obj.RightSideSlopePct = 50.0
    if not hasattr(obj, "UseDaylightToTerrain"):
        obj.addProperty("App::PropertyBool", "UseDaylightToTerrain", "Assembly", "Use terrain-daylight for side slopes")
        obj.UseDaylightToTerrain = False
    if not hasattr(obj, "DaylightSearchStep"):
        obj.addProperty("App::PropertyFloat", "DaylightSearchStep", "Assembly", "Search step for terrain-daylight (m)")
        obj.DaylightSearchStep = 1.0
    if not hasattr(obj, "DaylightMaxTriangles"):
        obj.addProperty("App::PropertyInteger", "DaylightMaxTriangles", "Assembly", "Max triangles used for daylight sampler")
        obj.DaylightMaxTriangles = 300000

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
        self._suspend_recompute = False
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
            use_ss = bool(getattr(obj, "UseSideSlopes", False))
            lsw = max(0.0, float(getattr(obj, "LeftSideWidth", 0.0)))
            rsw = max(0.0, float(getattr(obj, "RightSideWidth", 0.0)))
            lss = float(getattr(obj, "LeftSideSlopePct", 0.0))
            rss = float(getattr(obj, "RightSideSlopePct", 0.0))

            dz_l = -lw * ls / 100.0
            dz_r = -rw * rs / 100.0

            p_l = App.Vector(+lw, dz_l, 0.0)
            p_c = App.Vector(0.0, 0.0, 0.0)
            p_r = App.Vector(-rw, dz_r, 0.0)

            top_pts = [p_l, p_c, p_r]
            if use_ss and (lsw > 1e-9):
                p_lt = App.Vector(+lw + lsw, dz_l - lsw * lss / 100.0, 0.0)
                top_pts = [p_lt] + top_pts
            if use_ss and (rsw > 1e-9):
                p_rt = App.Vector(-(rw + rsw), dz_r - rsw * rss / 100.0, 0.0)
                top_pts = top_pts + [p_rt]

            # Display both crown line and solid-depth envelope so HeightLeft/Right
            # edits are visible immediately in 3D view.
            if max(hl, hr) <= 1e-9:
                obj.Shape = Part.makePolygon(top_pts)
            else:
                n_top = len(top_pts)
                q_pts = []
                for i, tp in enumerate(top_pts):
                    if n_top <= 1:
                        alpha = 0.5
                    else:
                        alpha = float(i) / float(n_top - 1)
                    h = (1.0 - alpha) * hl + alpha * hr
                    q_pts.append(App.Vector(tp.x, tp.y - h, tp.z))
                obj.Shape = Part.makePolygon(list(top_pts) + list(reversed(q_pts)) + [top_pts[0]])
            obj.Status = "OK"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "LeftWidth",
            "RightWidth",
            "LeftSlopePct",
            "RightSlopePct",
            "UseSideSlopes",
            "LeftSideWidth",
            "RightSideWidth",
            "LeftSideSlopePct",
            "RightSideSlopePct",
            "UseDaylightToTerrain",
            "DaylightSearchStep",
            "DaylightMaxTriangles",
            "HeightLeft",
            "HeightRight",
            "ShowTemplateWire",
        ):
            try:
                if prop == "UseSideSlopes" and bool(getattr(obj, "UseSideSlopes", False)):
                    # Keep side-slope preview visible by seeding practical defaults
                    # when user enables side slopes with zero widths.
                    lsw = max(0.0, float(getattr(obj, "LeftSideWidth", 0.0)))
                    rsw = max(0.0, float(getattr(obj, "RightSideWidth", 0.0)))
                    if lsw <= 1e-9:
                        obj.LeftSideWidth = max(2.0, 0.5 * max(0.0, float(getattr(obj, "LeftWidth", 0.0))))
                    if rsw <= 1e-9:
                        obj.RightSideWidth = max(2.0, 0.5 * max(0.0, float(getattr(obj, "RightWidth", 0.0))))
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
