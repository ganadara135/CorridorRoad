# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import Part
import math

from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_project import get_design_standard


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


def _unique_sorted_floats(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in values])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
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


def _spline_edge(points, start_tangent=None, end_tangent=None, tol: float = 1e-7):
    pts = _dedupe_points(list(points or []), tol=tol)
    if len(pts) < 2:
        return None
    if len(pts) == 2:
        return Part.makeLine(pts[0], pts[1])

    def _norm_vec(vec):
        if vec is None or getattr(vec, "Length", 0.0) <= 1.0e-12:
            return None
        vv = App.Vector(float(vec.x), float(vec.y), float(vec.z))
        if vv.Length <= 1.0e-12:
            return None
        return vv.normalize()

    try:
        curve = Part.BSplineCurve()
        st = _norm_vec(start_tangent)
        et = _norm_vec(end_tangent)
        if st is not None and et is not None:
            try:
                curve.interpolate(pts, InitialTangent=st, FinalTangent=et)
            except TypeError:
                curve.interpolate(pts)
        else:
            curve.interpolate(pts)
        return curve.toShape()
    except Exception:
        return None


def _model_length_from_meters(obj, meters: float) -> float:
    return _units.model_length_from_meters(getattr(obj, "Document", None), meters)


def _meters_from_model_length(obj, value: float) -> float:
    return _units.meters_from_model_length(getattr(obj, "Document", None), value)


def _edge_curve_kind(edge) -> str:
    curve = getattr(edge, "Curve", None)
    cname = str(type(curve).__name__ if curve is not None else "")
    if "Line" in cname:
        return "line"
    if "BSpline" in cname or "Bezier" in cname:
        return "spline"
    if "Circle" in cname:
        return "arc"
    return "other"


def _alignment_total_length_m(obj) -> float:
    try:
        total = float(getattr(obj, "TotalLength", 0.0) or 0.0)
        if total > 1e-9:
            return total
    except Exception:
        pass
    try:
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            return _meters_from_model_length(obj, float(shape.Length))
    except Exception:
        pass
    return 0.0


_ALIGNMENT_LENGTH_SCHEMA_TARGET = 2
_ALIGNMENT_METER_FLOAT_PROPS = (
    "MinRadius",
    "MinTangentLength",
    "MinTransitionLength",
    "TotalLength",
)
_ALIGNMENT_METER_FLOATLIST_PROPS = (
    "CurveRadii",
    "TransitionLengths",
)


def _migrate_alignment_length_schema(obj, had_existing_props: bool):
    if obj is None or (not hasattr(obj, "LengthSchemaVersion")):
        return
    try:
        schema = int(getattr(obj, "LengthSchemaVersion", 0) or 0)
    except Exception:
        schema = 0
    if schema >= _ALIGNMENT_LENGTH_SCHEMA_TARGET:
        return
    if not had_existing_props:
        try:
            obj.LengthSchemaVersion = _ALIGNMENT_LENGTH_SCHEMA_TARGET
        except Exception:
            pass
        return

    try:
        obj.LengthSchemaVersion = _ALIGNMENT_LENGTH_SCHEMA_TARGET
    except Exception:
        pass


def ensure_alignment_properties(obj):
    had_existing_props = any(
        hasattr(obj, prop)
        for prop in (_ALIGNMENT_METER_FLOAT_PROPS + _ALIGNMENT_METER_FLOATLIST_PROPS)
    )
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
        obj.addProperty("App::PropertyInteger", "SpiralSegments", "Alignment", "Control points per transition curve approximation")
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
        obj.MinTangentLength = 20.0
    if not hasattr(obj, "MinTransitionLength"):
        obj.addProperty("App::PropertyFloat", "MinTransitionLength", "Criteria", "Minimum transition length (m)")
        obj.MinTransitionLength = 20.0
    if not hasattr(obj, "CriteriaMessages"):
        obj.addProperty("App::PropertyStringList", "CriteriaMessages", "Criteria", "Criteria check messages")
        obj.CriteriaMessages = []
    if not hasattr(obj, "CriteriaStatus"):
        obj.addProperty("App::PropertyString", "CriteriaStatus", "Criteria", "Criteria check status")
        obj.CriteriaStatus = "OK"
    if not hasattr(obj, "CriteriaStandard"):
        obj.addProperty("App::PropertyString", "CriteriaStandard", "Criteria", "Applied design standard")
        obj.CriteriaStandard = _ds.DEFAULT_STANDARD

    if not hasattr(obj, "TotalLength"):
        obj.addProperty("App::PropertyFloat", "TotalLength", "Alignment", "Computed length")
        obj.TotalLength = 0.0
    if not hasattr(obj, "IPKeyStations"):
        obj.addProperty("App::PropertyFloatList", "IPKeyStations", "Result", "Approx station at each IP")
    if not hasattr(obj, "TSKeyStations"):
        obj.addProperty("App::PropertyFloatList", "TSKeyStations", "Result", "Approx station at transition TS points")
    if not hasattr(obj, "SCKeyStations"):
        obj.addProperty("App::PropertyFloatList", "SCKeyStations", "Result", "Approx station at transition SC points")
    if not hasattr(obj, "CSKeyStations"):
        obj.addProperty("App::PropertyFloatList", "CSKeyStations", "Result", "Approx station at transition CS points")
    if not hasattr(obj, "STKeyStations"):
        obj.addProperty("App::PropertyFloatList", "STKeyStations", "Result", "Approx station at transition ST points")
    if not hasattr(obj, "TransitionGeometryMode"):
        obj.addProperty("App::PropertyString", "TransitionGeometryMode", "Result", "Transition geometry mode summary")
        obj.TransitionGeometryMode = "-"
    if not hasattr(obj, "EdgeTypeSummary"):
        obj.addProperty("App::PropertyString", "EdgeTypeSummary", "Result", "Edge makeup summary")
        obj.EdgeTypeSummary = "-"
    if not hasattr(obj, "LineEdgeCount"):
        obj.addProperty("App::PropertyInteger", "LineEdgeCount", "Result", "Resolved line-edge count")
        obj.LineEdgeCount = 0
    if not hasattr(obj, "ArcEdgeCount"):
        obj.addProperty("App::PropertyInteger", "ArcEdgeCount", "Result", "Resolved arc-edge count")
        obj.ArcEdgeCount = 0
    if not hasattr(obj, "SplineEdgeCount"):
        obj.addProperty("App::PropertyInteger", "SplineEdgeCount", "Result", "Resolved spline-edge count")
        obj.SplineEdgeCount = 0
    if not hasattr(obj, "OtherEdgeCount"):
        obj.addProperty("App::PropertyInteger", "OtherEdgeCount", "Result", "Resolved other-edge count")
        obj.OtherEdgeCount = 0
    if not hasattr(obj, "TransitionCornerCount"):
        obj.addProperty("App::PropertyInteger", "TransitionCornerCount", "Result", "Transition corner count")
        obj.TransitionCornerCount = 0
    if not hasattr(obj, "TransitionSplineEdgeCount"):
        obj.addProperty("App::PropertyInteger", "TransitionSplineEdgeCount", "Result", "Spline edge count used by transition spirals")
        obj.TransitionSplineEdgeCount = 0
    if not hasattr(obj, "TransitionPolylineEdgeCount"):
        obj.addProperty("App::PropertyInteger", "TransitionPolylineEdgeCount", "Result", "Polyline edge count used by transition spirals")
        obj.TransitionPolylineEdgeCount = 0
    if not hasattr(obj, "LengthSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "LengthSchemaVersion", "Alignment", "Alignment scalar length storage schema")
        obj.LengthSchemaVersion = _ALIGNMENT_LENGTH_SCHEMA_TARGET

    _migrate_alignment_length_schema(obj, had_existing_props=had_existing_props)


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
            shape, total_len, messages, geometry_diag = self._build_shape_and_checks(obj)
            obj.Shape = shape
            obj.TotalLength = _meters_from_model_length(obj, float(total_len))
            obj.CriteriaMessages = messages
            obj.CriteriaStatus = "OK" if not messages else f"WARN ({len(messages)})"
            obj.TransitionGeometryMode = str(geometry_diag.get("transition_geometry_mode", "-") or "-")
            obj.EdgeTypeSummary = str(geometry_diag.get("edge_type_summary", "-") or "-")
            obj.LineEdgeCount = int(geometry_diag.get("line_edge_count", 0) or 0)
            obj.ArcEdgeCount = int(geometry_diag.get("arc_edge_count", 0) or 0)
            obj.SplineEdgeCount = int(geometry_diag.get("spline_edge_count", 0) or 0)
            obj.OtherEdgeCount = int(geometry_diag.get("other_edge_count", 0) or 0)
            obj.TransitionCornerCount = int(geometry_diag.get("transition_corner_count", 0) or 0)
            obj.TransitionSplineEdgeCount = int(geometry_diag.get("transition_spline_edge_count", 0) or 0)
            obj.TransitionPolylineEdgeCount = int(geometry_diag.get("transition_polyline_edge_count", 0) or 0)
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.TotalLength = 0.0
            obj.CriteriaMessages = [f"[error] {ex}"]
            obj.CriteriaStatus = "ERROR"
            obj.IPKeyStations = []
            obj.TSKeyStations = []
            obj.SCKeyStations = []
            obj.CSKeyStations = []
            obj.STKeyStations = []
            obj.TransitionGeometryMode = "-"
            obj.EdgeTypeSummary = "-"
            obj.LineEdgeCount = 0
            obj.ArcEdgeCount = 0
            obj.SplineEdgeCount = 0
            obj.OtherEdgeCount = 0
            obj.TransitionCornerCount = 0
            obj.TransitionSplineEdgeCount = 0
            obj.TransitionPolylineEdgeCount = 0

    def _build_shape_and_checks(self, obj):
        obj.IPKeyStations = []
        obj.TSKeyStations = []
        obj.SCKeyStations = []
        obj.CSKeyStations = []
        obj.STKeyStations = []

        pts = _dedupe_points(list(getattr(obj, "IPPoints", []) or []))
        if len(pts) < 2:
            return Part.Shape(), 0.0, ["Need at least 2 IP points."], self._build_geometry_diagnostics([], [], use_transitions=False)

        poly_pts = list(pts)
        if bool(getattr(obj, "Closed", False)):
            poly_pts.append(pts[0])
            wire = Part.makePolygon(poly_pts)
            try:
                edges0 = list(wire.Edges)
                total0 = float(wire.Length)
                if edges0 and total0 > 1e-9:
                    vals = []
                    for p in pts:
                        station_model = HorizontalAlignment._station_at_xy_on_edges(
                            edges0, total0, float(p.x), float(p.y), samples_per_edge=48
                        )
                        vals.append(_meters_from_model_length(obj, station_model))
                    obj.IPKeyStations = _unique_sorted_floats(vals)
            except Exception:
                pass
            diag = self._build_geometry_diagnostics(list(getattr(wire, "Edges", []) or []), [], use_transitions=False)
            return wire, float(wire.Length), [], diag

        n = len(pts)
        radii_m = list(getattr(obj, "CurveRadii", []) or [])
        if len(radii_m) < n:
            radii_m = radii_m + [0.0] * (n - len(radii_m))
        else:
            radii_m = radii_m[:n]
        radii = [_model_length_from_meters(obj, float(v or 0.0)) for v in radii_m]

        trans_m = list(getattr(obj, "TransitionLengths", []) or [])
        if len(trans_m) < n:
            trans_m = trans_m + [0.0] * (n - len(trans_m))
        else:
            trans_m = trans_m[:n]
        trans = [_model_length_from_meters(obj, float(v or 0.0)) for v in trans_m]

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
                # Retry with topological sorting to keep station traversal stable.
                try:
                    chains = Part.sortEdges(edges)
                    if chains:
                        chain = max(chains, key=lambda ch: sum(float(e.Length) for e in ch))
                        shape = Part.Wire(chain)
                    else:
                        shape = Part.Compound(edges)
                except Exception:
                    shape = Part.Compound(edges)

        # Publish key stations for downstream tools (sections/labels).
        try:
            edges1 = list(shape.Edges)
            total1 = float(shape.Length)
            if edges1 and total1 > 1e-9:
                ip_vals = []
                ts_vals = []
                sc_vals = []
                cs_vals = []
                st_vals = []
                for p in pts:
                    station_model = HorizontalAlignment._station_at_xy_on_edges(
                        edges1, total1, float(p.x), float(p.y), samples_per_edge=48
                    )
                    ip_vals.append(_meters_from_model_length(obj, station_model))
                for c in corners:
                    if c is None:
                        continue
                    p_ts = c.get("ts", None)
                    p_sc = c.get("sc", None)
                    p_cs = c.get("cs", None)
                    p_st = c.get("st", None)
                    if p_ts is not None:
                        station_model = HorizontalAlignment._station_at_xy_on_edges(
                            edges1, total1, float(p_ts.x), float(p_ts.y), samples_per_edge=64
                        )
                        ts_vals.append(_meters_from_model_length(obj, station_model))
                    if p_sc is not None:
                        station_model = HorizontalAlignment._station_at_xy_on_edges(
                            edges1, total1, float(p_sc.x), float(p_sc.y), samples_per_edge=64
                        )
                        sc_vals.append(_meters_from_model_length(obj, station_model))
                    if p_cs is not None:
                        station_model = HorizontalAlignment._station_at_xy_on_edges(
                            edges1, total1, float(p_cs.x), float(p_cs.y), samples_per_edge=64
                        )
                        cs_vals.append(_meters_from_model_length(obj, station_model))
                    if p_st is not None:
                        station_model = HorizontalAlignment._station_at_xy_on_edges(
                            edges1, total1, float(p_st.x), float(p_st.y), samples_per_edge=64
                        )
                        st_vals.append(_meters_from_model_length(obj, station_model))
                obj.IPKeyStations = _unique_sorted_floats(ip_vals)
                obj.TSKeyStations = _unique_sorted_floats(ts_vals)
                obj.SCKeyStations = _unique_sorted_floats(sc_vals)
                obj.CSKeyStations = _unique_sorted_floats(cs_vals)
                obj.STKeyStations = _unique_sorted_floats(st_vals)
        except Exception:
            obj.IPKeyStations = []
            obj.TSKeyStations = []
            obj.SCKeyStations = []
            obj.CSKeyStations = []
            obj.STKeyStations = []

        messages = self._run_criteria(obj, pts, seg_len, corners)
        diag = self._build_geometry_diagnostics(list(getattr(shape, "Edges", []) or []), corners, use_transitions=use_transitions)
        return shape, float(shape.Length), messages, diag

    @staticmethod
    def _build_geometry_diagnostics(edges, corners, use_transitions: bool):
        line_count = 0
        arc_count = 0
        spline_count = 0
        other_count = 0
        for edge in list(edges or []):
            kind = _edge_curve_kind(edge)
            if kind == "line":
                line_count += 1
            elif kind == "arc":
                arc_count += 1
            elif kind == "spline":
                spline_count += 1
            else:
                other_count += 1

        transition_corner_count = 0
        transition_spline_edge_count = 0
        transition_polyline_edge_count = 0
        for corner in list(corners or []):
            if not corner:
                continue
            if float(corner.get("ls_eff", 0.0) or 0.0) <= 1.0e-9:
                continue
            transition_corner_count += 1
            if str(corner.get("spiral_in_mode", "") or "") == "spline":
                transition_spline_edge_count += int(corner.get("spiral_in_edge_count", 0) or 0)
            else:
                transition_polyline_edge_count += int(corner.get("spiral_in_edge_count", 0) or 0)
            if str(corner.get("spiral_out_mode", "") or "") == "spline":
                transition_spline_edge_count += int(corner.get("spiral_out_edge_count", 0) or 0)
            else:
                transition_polyline_edge_count += int(corner.get("spiral_out_edge_count", 0) or 0)

        if transition_spline_edge_count > 0 and transition_polyline_edge_count <= 0:
            transition_geometry_mode = "BSplineSpiral"
        elif transition_spline_edge_count > 0 and transition_polyline_edge_count > 0:
            transition_geometry_mode = "HybridSpiral"
        elif transition_polyline_edge_count > 0:
            transition_geometry_mode = "PolylineSpiral"
        elif arc_count > 0:
            transition_geometry_mode = "ArcOnly"
        elif use_transitions:
            transition_geometry_mode = "NoEffectiveTransition"
        else:
            transition_geometry_mode = "NoTransition"

        parts = [f"line:{line_count}", f"arc:{arc_count}", f"spline:{spline_count}", f"other:{other_count}"]
        if transition_spline_edge_count > 0:
            parts.append(f"transition_spline:{transition_spline_edge_count}")
        if transition_polyline_edge_count > 0:
            parts.append(f"transition_polyline:{transition_polyline_edge_count}")
        if transition_corner_count > 0:
            parts.append(f"transition_corners:{transition_corner_count}")

        return {
            "transition_geometry_mode": transition_geometry_mode,
            "edge_type_summary": ", ".join(parts) if parts else "-",
            "line_edge_count": int(line_count),
            "arc_edge_count": int(arc_count),
            "spline_edge_count": int(spline_count),
            "other_edge_count": int(other_count),
            "transition_corner_count": int(transition_corner_count),
            "transition_spline_edge_count": int(transition_spline_edge_count),
            "transition_polyline_edge_count": int(transition_polyline_edge_count),
        }

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

        t_max = 0.49 * min(float(len_in), float(len_out))
        if t_max <= 1e-6:
            return None
        t_req = _tangent_needed(r_eff, ls_eff, theta)
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
                "ts": None,
                "sc": entry,
                "cs": exitp,
                "st": None,
                "radius_req": float(radius_req),
                "radius_eff": float(r_eff),
                "ls_req": float(ls_req),
                "ls_eff": 0.0,
                "theta": float(theta),
                "trim": float(t_use),
                "turn_sign": float(turn_sign),
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

        spiral_in_edge = _spline_edge(pts_sp1, start_tangent=u_in, end_tangent=t_sc)
        if spiral_in_edge is not None:
            spiral_in_edges = [spiral_in_edge]
            spiral_in_mode = "spline"
        else:
            spiral_in_edges = _polyline_edges(pts_sp1)
            spiral_in_mode = "polyline"
        edges = []
        edges.extend(spiral_in_edges)

        arc = self._make_arc_edge(c1, r_eff, sc, csp, turn_sign)
        if arc is not None:
            edges.append(arc)

        spiral_out_edge = _spline_edge(pts_sp2, start_tangent=t_cs, end_tangent=u_out)
        if spiral_out_edge is not None:
            spiral_out_edges = [spiral_out_edge]
            spiral_out_mode = "spline"
        else:
            spiral_out_edges = _polyline_edges(pts_sp2)
            spiral_out_mode = "polyline"
        edges.extend(spiral_out_edges)

        if not edges:
            return None

        return {
            "entry": entry,
            "exit": exitp,
            "edges": edges,
            "ts": entry,
            "sc": sc,
            "cs": csp,
            "st": exitp,
            "radius_req": float(radius_req),
            "radius_eff": float(r_eff),
            "ls_req": float(ls_req),
            "ls_eff": float(ls_eff),
            "theta": float(theta),
            "trim": float(t_use),
            "turn_sign": float(turn_sign),
            "spiral_in_mode": str(spiral_in_mode),
            "spiral_in_edge_count": int(len(spiral_in_edges)),
            "spiral_out_mode": str(spiral_out_mode),
            "spiral_out_edge_count": int(len(spiral_out_edges)),
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
        std = get_design_standard(obj, default=_ds.DEFAULT_STANDARD)
        std_spec = _ds.criteria_defaults(std, v, scale=1.0)
        obj.CriteriaStandard = std
        std_tag = f"[{std}]"

        e = max(0.0, float(getattr(obj, "SuperelevationPct", 8.0))) / 100.0
        f = max(0.01, float(getattr(obj, "SideFriction", 0.15)))
        min_radius_user = float(getattr(obj, "MinRadius", 0.0))
        if min_radius_user > 0.0:
            min_radius = min_radius_user
        else:
            denom = 127.0 * (e + f)
            r_ef = (v * v / denom) if denom > 1e-9 else 0.0
            min_radius = max(float(std_spec.get("min_radius", 0.0)), float(r_ef))

        min_tangent_user = max(0.0, float(getattr(obj, "MinTangentLength", 0.0)))
        min_transition_user = max(0.0, float(getattr(obj, "MinTransitionLength", 0.0)))
        min_tangent = max(min_tangent_user, float(std_spec.get("min_tangent", 0.0)))
        min_transition = max(min_transition_user, float(std_spec.get("min_transition", 0.0)))
        reverse_min_tangent = max(min_tangent, float(std_spec.get("reverse_min_tangent", 0.0)))
        reverse_min_transition = max(min_transition, float(std_spec.get("reverse_min_transition", 0.0)))
        seg_len_m = [_meters_from_model_length(obj, float(length or 0.0)) for length in list(seg_len or [])]

        for i in range(1, len(pts) - 1):
            c = corners[i]
            if c is None:
                continue
            radius_eff = _meters_from_model_length(obj, float(c.get("radius_eff", 0.0) or 0.0))
            radius_req = _meters_from_model_length(obj, float(c.get("radius_req", 0.0) or 0.0))
            ls_eff = _meters_from_model_length(obj, float(c.get("ls_eff", 0.0) or 0.0))
            ls_req = _meters_from_model_length(obj, float(c.get("ls_req", 0.0) or 0.0))
            if radius_eff < min_radius - 1e-6:
                msgs.append(
                    f"{std_tag} [RADIUS] IP#{i} R={radius_eff:.2f}m < min {min_radius:.2f}m (V={v:.1f}km/h)"
                )
            if ls_eff > 1e-6 and ls_eff < min_transition - 1e-6:
                msgs.append(
                    f"{std_tag} [TRANSITION] IP#{i} Ls={ls_eff:.2f}m < min {min_transition:.2f}m"
                )
            if radius_eff < radius_req - 1e-6:
                msgs.append(
                    f"{std_tag} [CLAMP] IP#{i} R reduced {radius_req:.2f} -> {radius_eff:.2f}m by geometric limits"
                )
            if ls_eff < ls_req - 1e-6:
                msgs.append(
                    f"{std_tag} [CLAMP] IP#{i} Ls reduced {ls_req:.2f} -> {ls_eff:.2f}m by geometric limits"
                )

        for i in range(len(seg_len_m)):
            left_trim = _meters_from_model_length(obj, float(corners[i]["trim"])) if (i >= 1 and corners[i] is not None) else 0.0
            right_trim = (
                _meters_from_model_length(obj, float(corners[i + 1]["trim"]))
                if ((i + 1) <= (len(seg_len_m) - 1) and corners[i + 1] is not None)
                else 0.0
            )
            residual = float(seg_len_m[i]) - left_trim - right_trim
            if residual < min_tangent - 1e-6:
                msgs.append(
                    f"{std_tag} [TANGENT] Segment {i}-{i+1} residual tangent {residual:.2f}m < min {min_tangent:.2f}m"
                )

                # Actionable guidance:
                # compute the segment length required to satisfy current criteria assumptions.
                left_req = left_trim
                right_req = right_trim

                if i >= 1 and corners[i] is not None and min_radius > 1e-9:
                    ls_for_left_raw = _meters_from_model_length(obj, float(corners[i]["ls_eff"]))
                    ls_for_left = max(ls_for_left_raw, min_transition) if ls_for_left_raw > 1e-9 else 0.0
                    left_req = max(
                        left_req,
                        _tangent_needed(min_radius, ls_for_left, float(corners[i]["theta"]))
                    )

                if (i + 1) <= (len(seg_len_m) - 1) and corners[i + 1] is not None and min_radius > 1e-9:
                    ls_for_right_raw = _meters_from_model_length(obj, float(corners[i + 1]["ls_eff"]))
                    ls_for_right = max(ls_for_right_raw, min_transition) if ls_for_right_raw > 1e-9 else 0.0
                    right_req = max(
                        right_req,
                        _tangent_needed(min_radius, ls_for_right, float(corners[i + 1]["theta"]))
                    )

                required_len = left_req + right_req + min_tangent
                add_len = required_len - float(seg_len_m[i])
                if add_len > 1e-6:
                    msgs.append(
                        f"{std_tag} [ACTION] Segment {i}-{i+1}: current IP layout cannot satisfy the criteria together. "
                        f"Required L >= {required_len:.2f}m, current L={float(seg_len_m[i]):.2f}m -> extend by about {add_len:.2f}m "
                        f"(or relax speed/radius/transition criteria)."
                    )

        # Reverse-curve check: consecutive curved corners with opposite turning direction.
        for i in range(1, len(pts) - 2):
            c0 = corners[i]
            c1 = corners[i + 1]
            if c0 is None or c1 is None:
                continue
            if _meters_from_model_length(obj, float(c0.get("radius_eff", 0.0) or 0.0)) <= 1e-9:
                continue
            if _meters_from_model_length(obj, float(c1.get("radius_eff", 0.0) or 0.0)) <= 1e-9:
                continue
            s0 = float(c0.get("turn_sign", 0.0))
            s1 = float(c1.get("turn_sign", 0.0))
            if s0 * s1 >= 0.0:
                continue

            left_trim = _meters_from_model_length(obj, float(c0.get("trim", 0.0) or 0.0))
            right_trim = _meters_from_model_length(obj, float(c1.get("trim", 0.0) or 0.0))
            residual = float(seg_len_m[i]) - left_trim - right_trim
            if residual <= 1e-6:
                msgs.append(
                    f"{std_tag} [REVERSE] IP#{i}->IP#{i+1}: reverse curve detected with no tangent between curves."
                )
            else:
                msgs.append(
                    f"{std_tag} [REVERSE] IP#{i}->IP#{i+1}: reverse curve detected (intermediate tangent {residual:.2f}m)."
                )
            if residual < reverse_min_tangent - 1e-6:
                msgs.append(
                    f"{std_tag} [REVERSE-TANGENT] IP#{i}->IP#{i+1}: intermediate tangent {residual:.2f}m < "
                    f"required {reverse_min_tangent:.2f}m."
                )

            ls0 = _meters_from_model_length(obj, float(c0.get("ls_eff", 0.0) or 0.0))
            ls1 = _meters_from_model_length(obj, float(c1.get("ls_eff", 0.0) or 0.0))
            if ls0 < reverse_min_transition - 1e-6:
                msgs.append(
                    f"{std_tag} [REVERSE-TRANSITION] IP#{i}: Ls={ls0:.2f}m < required {reverse_min_transition:.2f}m."
                )
            if ls1 < reverse_min_transition - 1e-6:
                msgs.append(
                    f"{std_tag} [REVERSE-TRANSITION] IP#{i+1}: Ls={ls1:.2f}m < required {reverse_min_transition:.2f}m."
                )

        return msgs

    # ----- helpers for stationing -----
    @staticmethod
    def _resolve_edges(alignment_obj):
        shape = getattr(alignment_obj, "Shape", None)
        if shape is None or shape.isNull():
            raise ValueError("Alignment shape is empty")
        edges = list(shape.Edges)
        if not edges:
            raise ValueError("No edges in alignment")
        return edges

    @staticmethod
    def _station_to_edge(alignment_obj, s: float):
        edges = HorizontalAlignment._resolve_edges(alignment_obj)
        lengths = [float(e.Length) for e in edges]
        total_model = float(sum(lengths))
        if total_model <= 1e-12:
            raise ValueError("Alignment length is zero")
        total = _alignment_total_length_m(alignment_obj)
        if total <= 1e-12:
            total = _meters_from_model_length(alignment_obj, total_model)

        ss = _clamp(float(s), 0.0, total)
        ss_model = _model_length_from_meters(alignment_obj, ss)
        acc = 0.0
        last_i = len(edges) - 1
        for i, e in enumerate(edges):
            L = lengths[i]
            next_acc = acc + L
            if i == last_i or ss_model <= next_acc + 1e-9:
                local = _clamp(ss_model - acc, 0.0, L)
                return {
                    "edge": e,
                    "edge_len": L,
                    "local_len": local,
                    "total_len": total,
                    "station": ss,
                }
            acc = next_acc

        # Numerical fallback.
        e = edges[-1]
        L = lengths[-1]
        return {
            "edge": e,
            "edge_len": L,
            "local_len": L,
            "total_len": total,
            "station": total,
        }

    @staticmethod
    def _edge_param_by_length(edge, local_len: float, edge_len: float):
        fp = float(edge.FirstParameter)
        lp = float(edge.LastParameter)

        if edge_len <= 1e-12:
            return fp

        ll = _clamp(float(local_len), 0.0, edge_len)
        if ll <= 1e-12:
            return fp
        if ll >= edge_len - 1e-12:
            return lp

        try:
            return float(edge.getParameterByLength(ll))
        except Exception:
            return float(fp + (lp - fp) * (ll / edge_len))

    @staticmethod
    def _station_at_xy_on_edges(edges, total_len: float, x: float, y: float, samples_per_edge: int = 64) -> float:
        target = App.Vector(float(x), float(y), 0.0)
        samples = max(8, min(256, int(samples_per_edge)))

        best_s = 0.0
        best_d2 = float("inf")
        acc = 0.0

        for e in edges:
            L = float(e.Length)
            if L <= 1e-12:
                continue

            try:
                pts = list(e.discretize(Number=samples + 1))
            except Exception:
                pts = [
                    e.valueAt(float(e.FirstParameter)),
                    e.valueAt(float(e.LastParameter)),
                ]

            if len(pts) < 2:
                acc += L
                continue

            seg_acc = 0.0
            for i in range(len(pts) - 1):
                a = pts[i]
                b = pts[i + 1]
                abx = float(b.x - a.x)
                aby = float(b.y - a.y)
                seg_len = float((b - a).Length)
                den = abx * abx + aby * aby
                if den <= 1e-16:
                    seg_acc += seg_len
                    continue

                apx = float(target.x - a.x)
                apy = float(target.y - a.y)
                t = _clamp((apx * abx + apy * aby) / den, 0.0, 1.0)

                qx = float(a.x + t * abx)
                qy = float(a.y + t * aby)
                dx = float(target.x - qx)
                dy = float(target.y - qy)
                d2 = dx * dx + dy * dy

                if d2 < best_d2:
                    best_d2 = d2
                    best_s = acc + seg_acc + seg_len * t

                seg_acc += seg_len

            acc += L

        return _clamp(best_s, 0.0, max(0.0, float(total_len)))

    @staticmethod
    def point_at_station(alignment_obj, s: float) -> App.Vector:
        hit = HorizontalAlignment._station_to_edge(alignment_obj, float(s))
        e = hit["edge"]
        L = hit["edge_len"]
        p = HorizontalAlignment._edge_param_by_length(e, hit["local_len"], L)
        return e.valueAt(p)

    @staticmethod
    def tangent_at_station(alignment_obj, s: float) -> App.Vector:
        hit = HorizontalAlignment._station_to_edge(alignment_obj, float(s))
        e = hit["edge"]
        L = hit["edge_len"]
        p = HorizontalAlignment._edge_param_by_length(e, hit["local_len"], L)

        try:
            t = e.tangentAt(p)
            if isinstance(t, (tuple, list)):
                t = t[0]
            if getattr(t, "Length", 0.0) > 1e-12:
                return t.normalize()
        except Exception:
            pass

        total = hit["total_len"]
        ss = hit["station"]
        eps = max(1e-4, min(1.0, 0.01 * total))
        s0 = max(0.0, ss - eps)
        s1 = min(total, ss + eps)
        if s1 <= s0 + 1e-9:
            s0 = max(0.0, ss - 0.5 * eps)
            s1 = min(total, ss + 0.5 * eps)

        p0 = HorizontalAlignment.point_at_station(alignment_obj, s0)
        p1 = HorizontalAlignment.point_at_station(alignment_obj, s1)
        v = p1 - p0
        if v.Length < 1e-9:
            return App.Vector(1, 0, 0)
        return v.normalize()

    @staticmethod
    def normal_at_station(alignment_obj, s: float) -> App.Vector:
        t = HorizontalAlignment.tangent_at_station(alignment_obj, float(s))
        n = App.Vector(-float(t.y), float(t.x), 0.0)
        if n.Length < 1e-9:
            return App.Vector(0, 1, 0)
        return n.normalize()

    @staticmethod
    def station_at_xy(alignment_obj, x: float, y: float, samples_per_edge: int = 64) -> float:
        """
        Approximate inverse map XY->station by polyline projection over each edge.
        """
        edges = HorizontalAlignment._resolve_edges(alignment_obj)
        total_model = float(getattr(alignment_obj.Shape, "Length", 0.0))
        station_model = HorizontalAlignment._station_at_xy_on_edges(edges, total_model, float(x), float(y), samples_per_edge=samples_per_edge)
        return _meters_from_model_length(alignment_obj, station_model)


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
