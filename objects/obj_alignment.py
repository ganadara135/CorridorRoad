# CorridorRoad/objects/obj_alignment.py
import FreeCAD as App
import Part


class HorizontalAlignment:
    """
    IPPoints -> polyline wire
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "HorizontalAlignment"

        obj.addProperty("App::PropertyVectorList", "IPPoints", "Alignment", "Intersection points (IP)")
        obj.addProperty("App::PropertyBool", "Closed", "Alignment", "Close the wire")
        obj.Closed = False

        obj.addProperty("App::PropertyFloat", "TotalLength", "Alignment", "Computed length")
        obj.TotalLength = 0.0

    def execute(self, obj):
        pts = obj.IPPoints
        if not pts or len(pts) < 2:
            obj.Shape = Part.Shape()
            obj.TotalLength = 0.0

            return

        poly_pts = list(pts)
        if obj.Closed:
            poly_pts.append(pts[0])

        wire = Part.makePolygon(poly_pts)
        obj.Shape = wire
        obj.TotalLength = float(wire.Length)

    # ----- helpers for stationing -----
    @staticmethod
    def point_at_station(alignment_obj, s: float) -> App.Vector:
        wire = alignment_obj.Shape
        if wire is None or wire.isNull():
            raise ValueError("Alignment shape is empty")

        if s < 0:
            s = 0.0

        total = float(wire.Length)
        if s > total:
            s = total

        remaining = s
        edges = list(wire.Edges)
        if not edges:
            raise ValueError("No edges in alignment")

        for e in edges:
            L = float(e.Length)
            if remaining <= L:
                fp = float(e.FirstParameter)
                lp = float(e.LastParameter)
                if L <= 1e-9:
                    return e.valueAt(fp)

                t = fp + (lp - fp) * (remaining / L)
                return e.valueAt(t)

            remaining -= L

        last = edges[-1]
        return last.valueAt(last.LastParameter)

    @staticmethod
    def tangent_at_station(alignment_obj, s: float) -> App.Vector:
        eps = 0.01
        p0 = HorizontalAlignment.point_at_station(alignment_obj, max(0.0, s - eps))
        p1 = HorizontalAlignment.point_at_station(alignment_obj, s + eps)
        v = (p1 - p0)
        if v.Length < 1e-9:
            return App.Vector(1, 0, 0)

        return v.normalize()


class ViewProviderHorizontalAlignment:
    """
    Minimal ViewProvider: makes sure the object is actually drawable in 3D view.
    """

    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = None

    def attach(self, vobj):
        self.Object = vobj.Object

        # Force visibility & line style (safe defaults)
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 3
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
