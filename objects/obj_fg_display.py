# CorridorRoad/objects/obj_fg_display.py
import FreeCAD as App
import Part

from objects.obj_vertical_alignment import VerticalAlignment


def _intersect_tangent_lines(P0: App.Vector, g1: float, P2: App.Vector, g2: float):
    # L0: P0 + t*(1, g1)
    # L2: P2 - u*(1, g2)
    if abs(g1 - g2) < 1e-12:
        return None

    x0, y0 = float(P0.x), float(P0.y)
    x2, y2 = float(P2.x), float(P2.y)

    t = ((y2 - y0) - g2 * (x2 - x0)) / (g1 - g2)
    x1 = x0 + t
    y1 = y0 + g1 * t
    return App.Vector(x1, y1, float(P0.z))


def _make_quadratic_bezier(P0: App.Vector, P1: App.Vector, P2: App.Vector):
    c = Part.BezierCurve()
    c.setPoles([P0, P1, P2])
    return c.toShape()


class FGDisplay:
    """
    Display-only object for Finished Grade (FG).

    - SourceVA: link to VerticalAlignment
    - ShowWire: show/hide FG
    - CurvesOnly: if True, show only vertical curve segments (Bezier), no tangents
    - ZOffset: profile view layering
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "FGDisplay"

        obj.addProperty("App::PropertyLink", "SourceVA", "FG", "VerticalAlignment source")
        obj.addProperty("App::PropertyBool", "ShowWire", "FG", "Show FG wire")
        obj.ShowWire = True

        obj.addProperty("App::PropertyBool", "CurvesOnly", "FG", "Show only vertical curve segments")
        obj.CurvesOnly = False

        obj.addProperty("App::PropertyFloat", "ZOffset", "FG", "Z offset for FG wire")
        obj.ZOffset = 0.0

    def execute(self, obj):
        if not bool(getattr(obj, "ShowWire", True)):
            obj.Shape = Part.Shape()

            return

        va = getattr(obj, "SourceVA", None)
        if va is None:
            obj.Shape = Part.Shape()

            return

        zoff = float(getattr(obj, "ZOffset", 0.0))
        curves_only = bool(getattr(obj, "CurvesOnly", False))

        # Use VA engine to solve curves (clamp/min tangent applied inside)
        pvis, grades, curves = VerticalAlignment._solve_curves(va)

        # Build edges for display
        edges = []

        curve_by_bvc = {c["bvc"]: c for c in curves}

        # key stations: start/end + each BVC/EVC
        key_s = set([pvis[0][0], pvis[-1][0]])
        for c in curves:
            key_s.add(float(c["bvc"]))
            key_s.add(float(c["evc"]))

        keys = sorted(key_s)

        for i in range(len(keys) - 1):
            a = float(keys[i])
            b = float(keys[i + 1])

            # Curve interval? (a==BVC and b==EVC)
            if a in curve_by_bvc:
                c = curve_by_bvc[a]
                if abs(float(c["evc"]) - b) < 1e-9:
                    bvc = float(c["bvc"])
                    evc = float(c["evc"])
                    L = float(c["L"])

                    z_bvc = float(c["z_bvc"])
                    z_evc = float(VerticalAlignment.elevation_at_station(va, evc))

                    P0 = App.Vector(bvc, z_bvc, zoff)
                    P2 = App.Vector(evc, z_evc, zoff)

                    g1 = float(c["g1"])
                    g2 = float(c["g2"])

                    P1 = _intersect_tangent_lines(P0, g1, P2, g2)
                    if P1 is None:
                        edges.append(Part.makeLine(P0, P2))
                    else:
                        edges.append(_make_quadratic_bezier(P0, P1, P2))

                    continue

            # Tangent segment
            if not curves_only:
                za = float(VerticalAlignment.elevation_at_station(va, a))
                zb = float(VerticalAlignment.elevation_at_station(va, b))
                Pa = App.Vector(a, za, zoff)
                Pb = App.Vector(b, zb, zoff)
                edges.append(Part.makeLine(Pa, Pb))

        if not edges:
            obj.Shape = Part.Shape()

            return

        # CurvesOnly => edges can be disconnected, so Compound is safer
        if curves_only:
            obj.Shape = Part.Compound(edges)

            return

        try:
            obj.Shape = Part.Wire(edges)
        except Exception:
            obj.Shape = Part.Compound(edges)

    def onChanged(self, obj, prop):
        # Make property editor changes immediately visible
        if prop in ("SourceVA", "ShowWire", "CurvesOnly", "ZOffset"):
            try:
                obj.touch()
                if obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderFGDisplay:
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

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines"]

    def getDefaultDisplayMode(self):
        return "Wireframe"

    def setDisplayMode(self, mode):
        return mode