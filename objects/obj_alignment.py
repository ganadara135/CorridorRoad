import FreeCAD as App
import Part
import math

from objects.obj_project import get_length_scale

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _left_normal_2d(v: App.Vector) -> App.Vector:
    return App.Vector(-float(v.y), float(v.x), 0.0)


def _rotate_2d(v: App.Vector, ang: float) -> App.Vector:
    ca = math.cos(ang)
    sa = math.sin(ang)
    return App.Vector(float(v.x) * ca - float(v.y) * sa, float(v.x) * sa + float(v.y) * ca, 0.0)


def _line_intersection_2d(p1: App.Vector, d1: App.Vector, p2: App.Vector, d2: App.Vector):
    a11 = float(d1.x)
    a12 = -float(d2.x)
    a21 = float(d1.y)
    a22 = -float(d2.y)
    b1 = float(p2.x - p1.x)
    b2 = float(p2.y - p1.y)

    det = a11 * a22 - a12 * a21
    if abs(det) < 1e-12:
        return None

    t = (b1 * a22 - b2 * a12) / det
    return App.Vector(float(p1.x + t * d1.x), float(p1.y + t * d1.y), float(p1.z))


def _dedupe_points(points, tol: float = 1e-6):
    out = []
    for p in points:
        if not out:
            out.append(p)
            continue
        if (p - out[-1]).Length > tol:
            out.append(p)
    return out


def _tangent_needed(r: float, ls: float, theta: float) -> float:
    if r <= 1e-9:
        return 0.0
    tan_half = math.tan(0.5 * theta)
    if ls <= 1e-9:
        return r * tan_half
    p = (ls * ls) / (24.0 * r)
    return (r + p) * tan_half + 0.5 * ls


def _spiral_xy(s: float, r: float, ls: float):
    """
    Local clothoid coordinates using standard series expansion.
    Start tangent at s=0, curvature ramps linearly to 1/r at s=ls.
    """
    if r <= 1e-9 or ls <= 1e-9:
        return float(s), 0.0

    a2 = r * ls
    s2 = s * s
    s3 = s2 * s
    s5 = s3 * s2
    s7 = s5 * s2
    s9 = s7 * s2
    s11 = s9 * s2

    x = s - (s5 / (40.0 * a2 * a2)) + (s9 / (3456.0 * a2 * a2 * a2 * a2))
    y = (s3 / (6.0 * a2)) - (s7 / (336.0 * a2 * a2 * a2)) + (s11 / (42240.0 * a2 * a2 * a2 * a2 * a2))
    return float(x), float(y)


def _polyline_edges(points, tol: float = 1e-7):
    edges = []
    for i in range(len(points) - 1):
        if (points[i + 1] - points[i]).Length > tol:
            edges.append(Part.makeLine(points[i], points[i + 1]))
    return edges


def ensure_alignment_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "IPPoints"):
        obj.addProperty("App::PropertyVectorList", "IPPoints", "Alignment", "Intersection points (IP)")
    if not hasattr(obj, "CurveRadii"):
        obj.addProperty("App::PropertyFloatList", "CurveRadii", "Alignment", "Circular curve radii at each IP (m), end points ignored")
    if not hasattr(obj, "TransitionLengths"):
        obj.addProperty("App::PropertyFloatList", "TransitionLengths", "Alignment", "Transition length (m) at each IP, end points ignored")
    if not hasattr(obj, "UseTransitionCurves"):
        obj.addProperty("App::PropertyBool", "UseTransitionCurves", "Alignment", "Enable transition curves (S-C-S) for corners")
        obj.UseTransitionCurves = True
    if not hasattr(obj, "SpiralSegments"):
        obj.addProperty("App::PropertyInteger", "SpiralSegments", "Alignment", "Polyline segments per transition curve")
        obj.SpiralSegments = 16
    if not hasattr(obj, "Closed"):
        obj.addProperty("App::PropertyBool", "Closed", "Alignment", "Close the wire")
        obj.Closed = False

    if not hasattr(obj, "DesignSpeedKph"):
        obj.addProperty("App::PropertyFloat", "DesignSpeedKph", "Criteria", "Design speed (km/h)")
        obj.DesignSpeedKph = 60.0
    if not hasattr(obj, "SuperelevationPct"):
        obj.addProperty("App::PropertyFloat", "SuperelevationPct", "Criteria", "Superelevation e (%) for radius check")
        obj.SuperelevationPct = 8.0
    if not hasattr(obj, "SideFriction"):
        obj.addProperty("App::PropertyFloat", "SideFriction", "Criteria", "Side friction f for radius check")
        obj.SideFriction = 0.15
    if not hasattr(obj, "MinRadius"):
        obj.addProperty("App::PropertyFloat", "MinRadius", "Criteria", "Minimum radius (m); <=0 means auto from speed/e/f")
        obj.MinRadius = 0.0
    if not hasattr(obj, "MinTangentLength"):
        obj.addProperty("App::PropertyFloat", "MinTangentLength", "Criteria", "Minimum tangent length between curves (m)")
        obj.MinTangentLength = 20.0 * scale
    if not hasattr(obj, "MinTransitionLength"):
        obj.addProperty("App::PropertyFloat", "MinTransitionLength", "Criteria", "Minimum transition length (m)")
        obj.MinTransitionLength = 20.0 * scale
    if not hasattr(obj, "CriteriaMessages"):
        obj.addProperty("App::PropertyStringList", "CriteriaMessages", "Criteria", "Criteria check messages")
        obj.CriteriaMessages = []
    if not hasattr(obj, "CriteriaStatus"):
        obj.addProperty("App::PropertyString", "CriteriaStatus", "Criteria", "Criteria check status")
        obj.CriteriaStatus = "OK"

    if not hasattr(obj, "TotalLength"):
        obj.addProperty("App::PropertyFloat", "TotalLength", "Alignment", "Computed length")
        obj.TotalLength = 0.0


class HorizontalAlignment:
    """
    Practical horizontal alignment core:
      - Tangent + circular curves
      - Optional transition curves (S-C-S, Euler spiral approximation)
      - Built-in criteria checks
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "HorizontalAlignment"
        ensure_alignment_properties(obj)

    def execute(self, obj):
        ensure_alignment_properties(obj)

        try:
            shape, total_len, messages = self._build_shape_and_checks(obj)
            obj.Shape = shape
            obj.TotalLength = float(total_len)
            obj.CriteriaMessages = messages
            obj.CriteriaStatus = "OK" if not messages else f"WARN ({len(messages)})"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.TotalLength = 0.0
            obj.CriteriaMessages = [f"[error] {ex}"]
            obj.CriteriaStatus = "ERROR"

    def _build_shape_and_checks(self, obj):
        pts = _dedupe_points(list(getattr(obj, "IPPoints", []) or []))
        if len(pts) < 2:
            return Part.Shape(), 0.0, ["Need at least 2 IP points."]

        poly_pts = list(pts)
        if bool(getattr(obj, "Closed", False)):
            poly_pts.append(pts[0])
            wire = Part.makePolygon(poly_pts)
            return wire, float(wire.Length), []

        n = len(pts)
        radii = list(getattr(obj, "CurveRadii", []) or [])
        if len(radii) < n:
            radii = radii + [0.0] * (n - len(radii))
        else:
            radii = radii[:n]

        trans = list(getattr(obj, "TransitionLengths", []) or [])
        if len(trans) < n:
            trans = trans + [0.0] * (n - len(trans))
        else:
            trans = trans[:n]

        use_transitions = bool(getattr(obj, "UseTransitionCurves", True))
        spiral_segments = max(4, int(getattr(obj, "SpiralSegments", 16)))

        seg_dir = []
        seg_len = []
        for i in range(n - 1):
            v = pts[i + 1] - pts[i]
            L = float(v.Length)
            if L < 1e-9:
                raise Exception("Consecutive IP points are duplicated.")
            seg_len.append(L)
            seg_dir.append(v * (1.0 / L))

        corners = [None] * n
        for i in range(1, n - 1):
            corners[i] = self._solve_corner(
                ip=pts[i],
                u_in=seg_dir[i - 1],
                u_out=seg_dir[i],
                len_in=seg_len[i - 1],
                len_out=seg_len[i],
                radius_req=max(0.0, float(radii[i])),
                ls_req=max(0.0, float(trans[i])) if use_transitions else 0.0,
                spiral_segments=spiral_segments,
            )

        edges = []
        for i in range(n - 1):
            p_start = pts[i]
            p_end = pts[i + 1]

            if i >= 1 and corners[i] is not None:
                p_start = corners[i]["exit"]
            if (i + 1) <= (n - 2) and corners[i + 1] is not None:
                p_end = corners[i + 1]["entry"]

            if (p_end - p_start).Length > 1e-7:
                edges.append(Part.makeLine(p_start, p_end))

            if (i + 1) <= (n - 2) and corners[i + 1] is not None:
                edges.extend(corners[i + 1]["edges"])

        if not edges:
            shape = Part.makePolygon(pts)
        else:
            try:
                shape = Part.Wire(edges)
            except Exception:
                shape = Part.Compound(edges)

        messages = self._run_criteria(obj, pts, seg_len, corners)
        return shape, float(shape.Length), messages

    def _solve_corner(self, ip, u_in, u_out, len_in, len_out, radius_req, ls_req, spiral_segments):
        if radius_req <= 1e-9:
            return None

        dot = _clamp(float(u_in.x * u_out.x + u_in.y * u_out.y), -1.0, 1.0)
        theta = math.acos(dot)
        cross = float(u_in.x * u_out.y - u_in.y * u_out.x)
        if theta < 1e-6 or abs(math.pi - theta) < 1e-6 or abs(cross) < 1e-12:
            return None

        turn_sign = 1.0 if cross > 0.0 else -1.0
        r_eff = float(radius_req)
        ls_eff = max(0.0, float(ls_req))
        if ls_eff > 0.0:
            ls_limit = max(0.0, 0.95 * theta * r_eff)
            if ls_eff > ls_limit:
                ls_eff = ls_limit

        t_req = _tangent_needed(r_eff, ls_eff, theta)
        t_max = 0.49 * min(float(len_in), float(len_out))
        t_use = min(t_req, t_max)

        if t_use < t_req - 1e-6:
            if ls_eff > 1e-6:
                lo = 0.0
                hi = ls_eff
                for _ in range(32):
                    mid = 0.5 * (lo + hi)
                    if _tangent_needed(r_eff, mid, theta) <= t_max:
                        lo = mid
                    else:
                        hi = mid
                ls_eff = lo
                t_req = _tangent_needed(r_eff, ls_eff, theta)
                t_use = min(t_req, t_max)

            if t_use < t_req - 1e-6:
                ls_eff = 0.0
                tan_half = math.tan(0.5 * theta)
                if abs(tan_half) < 1e-12:
                    return None
                r_eff = max(1e-6, t_use / tan_half)

        entry = ip - u_in * t_use
        exitp = ip + u_out * t_use

        if ls_eff <= 1e-6:
            n1 = _left_normal_2d(u_in) * turn_sign
            n2 = _left_normal_2d(u_out) * turn_sign
            center = _line_intersection_2d(entry, n1, exitp, n2)
            if center is None:
                return None

            arc = self._make_arc_edge(center, r_eff, entry, exitp, turn_sign)
            if arc is None:
                return None

            return {
                "entry": entry,
                "exit": exitp,
                "edges": [arc],
                "radius_req": float(radius_req),
                "radius_eff": float(r_eff),
                "ls_req": float(ls_req),
                "ls_eff": 0.0,
                "theta": float(theta),
                "trim": float(t_use),
            }

        n_in = _left_normal_2d(u_in) * turn_sign
        n_out = _left_normal_2d(u_out) * turn_sign

        x_s, y_s = _spiral_xy(ls_eff, r_eff, ls_eff)
        sc = entry + u_in * x_s + n_in * y_s
        csp = exitp - u_out * x_s + n_out * y_s

        phi = ls_eff / (2.0 * r_eff)
        t_sc = _rotate_2d(u_in, turn_sign * phi)
        t_cs = _rotate_2d(u_out, -turn_sign * phi)

        c1 = _line_intersection_2d(sc, _left_normal_2d(t_sc) * turn_sign, csp, _left_normal_2d(t_cs) * turn_sign)
        if c1 is None:
            return None

        pts_sp1 = []
        for k in range(spiral_segments + 1):
            s = ls_eff * float(k) / float(spiral_segments)
            xk, yk = _spiral_xy(s, r_eff, ls_eff)
            pts_sp1.append(entry + u_in * xk + n_in * yk)

        pts_sp2 = []
        for k in range(spiral_segments + 1):
            s = ls_eff * float(k) / float(spiral_segments)
            u = ls_eff - s
            xk, yk = _spiral_xy(u, r_eff, ls_eff)
            pts_sp2.append(exitp - u_out * xk + n_out * yk)

        edges = []
        edges.extend(_polyline_edges(pts_sp1))

        arc = self._make_arc_edge(c1, r_eff, sc, csp, turn_sign)
        if arc is not None:
            edges.append(arc)

        edges.extend(_polyline_edges(pts_sp2))

        if not edges:
            return None

        return {
            "entry": entry,
            "exit": exitp,
            "edges": edges,
            "radius_req": float(radius_req),
            "radius_eff": float(r_eff),
            "ls_req": float(ls_req),
            "ls_eff": float(ls_eff),
            "theta": float(theta),
            "trim": float(t_use),
        }

    @staticmethod
    def _make_arc_edge(center: App.Vector, radius: float, ts: App.Vector, st: App.Vector, turn_sign: float):
        if radius <= 1e-9:
            return None

        a0 = math.atan2(float(ts.y - center.y), float(ts.x - center.x))
        a1 = math.atan2(float(st.y - center.y), float(st.x - center.x))

        delta = a1 - a0
        while delta <= -math.pi:
            delta += 2.0 * math.pi
        while delta > math.pi:
            delta -= 2.0 * math.pi

        if turn_sign > 0.0 and delta <= 0.0:
            delta += 2.0 * math.pi
        if turn_sign < 0.0 and delta >= 0.0:
            delta -= 2.0 * math.pi

        amid = a0 + 0.5 * delta
        pm = App.Vector(
            float(center.x + radius * math.cos(amid)),
            float(center.y + radius * math.sin(amid)),
            float(ts.z),
        )

        try:
            return Part.Arc(ts, pm, st).toShape()
        except Exception:
            try:
                circle = Part.Circle(center, App.Vector(0, 0, 1), radius)
                return Part.ArcOfCircle(circle, ts, pm, st).toShape()
            except Exception:
                return None

    def _run_criteria(self, obj, pts, seg_len, corners):
        msgs = []

        v = max(0.0, float(getattr(obj, "DesignSpeedKph", 60.0)))
        e = max(0.0, float(getattr(obj, "SuperelevationPct", 8.0))) / 100.0
        f = max(0.01, float(getattr(obj, "SideFriction", 0.15)))
        min_radius_user = float(getattr(obj, "MinRadius", 0.0))
        if min_radius_user > 0.0:
            min_radius = min_radius_user
        else:
            denom = 127.0 * (e + f)
            min_radius = (v * v / denom) if denom > 1e-9 else 0.0

        min_tangent = max(0.0, float(getattr(obj, "MinTangentLength", 0.0)))
        min_transition = max(0.0, float(getattr(obj, "MinTransitionLength", 0.0)))

        for i in range(1, len(pts) - 1):
            c = corners[i]
            if c is None:
                continue
            if c["radius_eff"] < min_radius - 1e-6:
                msgs.append(
                    f"[RADIUS] IP#{i} R={c['radius_eff']:.2f}m < min {min_radius:.2f}m (V={v:.1f}km/h)"
                )
            if c["ls_eff"] > 1e-6 and c["ls_eff"] < min_transition - 1e-6:
                msgs.append(
                    f"[TRANSITION] IP#{i} Ls={c['ls_eff']:.2f}m < min {min_transition:.2f}m"
                )
            if c["radius_eff"] < c["radius_req"] - 1e-6:
                msgs.append(
                    f"[CLAMP] IP#{i} R reduced {c['radius_req']:.2f} -> {c['radius_eff']:.2f}m by geometric limits"
                )
            if c["ls_eff"] < c["ls_req"] - 1e-6:
                msgs.append(
                    f"[CLAMP] IP#{i} Ls reduced {c['ls_req']:.2f} -> {c['ls_eff']:.2f}m by geometric limits"
                )

        for i in range(len(seg_len)):
            left_trim = corners[i]["trim"] if (i >= 1 and corners[i] is not None) else 0.0
            right_trim = corners[i + 1]["trim"] if ((i + 1) <= (len(seg_len) - 1) and corners[i + 1] is not None) else 0.0
            residual = float(seg_len[i]) - left_trim - right_trim
            if residual < min_tangent - 1e-6:
                msgs.append(
                    f"[TANGENT] Segment {i}-{i+1} residual tangent {residual:.2f}m < min {min_tangent:.2f}m"
                )

                # Actionable guidance:
                # compute the segment length required to satisfy current criteria assumptions.
                left_req = left_trim
                right_req = right_trim

                if i >= 1 and corners[i] is not None and min_radius > 1e-9:
                    ls_for_left = max(corners[i]["ls_eff"], min_transition) if corners[i]["ls_eff"] > 1e-9 else 0.0
                    left_req = max(
                        left_req,
                        _tangent_needed(min_radius, ls_for_left, float(corners[i]["theta"]))
                    )

                if (i + 1) <= (len(seg_len) - 1) and corners[i + 1] is not None and min_radius > 1e-9:
                    ls_for_right = max(corners[i + 1]["ls_eff"], min_transition) if corners[i + 1]["ls_eff"] > 1e-9 else 0.0
                    right_req = max(
                        right_req,
                        _tangent_needed(min_radius, ls_for_right, float(corners[i + 1]["theta"]))
                    )

                required_len = left_req + right_req + min_tangent
                add_len = required_len - float(seg_len[i])
                if add_len > 1e-6:
                    msgs.append(
                        f"[ACTION] Segment {i}-{i+1}: current IP layout cannot satisfy the criteria together. "
                        f"Required L >= {required_len:.2f}m, current L={float(seg_len[i]):.2f}m -> extend by about {add_len:.2f}m "
                        f"(or relax speed/radius/transition criteria)."
                    )

        return msgs

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
    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = None

    def attach(self, vobj):
        self.Object = vobj.Object
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
