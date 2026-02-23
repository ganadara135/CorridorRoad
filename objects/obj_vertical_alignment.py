# CorridorRoad/objects/obj_vertical_alignment.py
import FreeCAD as App
import Part
import FreeCADGui as Gui


def _intersect_tangent_lines(P0: App.Vector, g1: float, P2: App.Vector, g2: float):
    """
    Find intersection point P1 of two tangent lines:
      L0: P0 + t*(1, g1)
      L2: P2 - u*(1, g2)
    Returns App.Vector or None if parallel (g1 == g2).
    """
    if abs(g1 - g2) < 1e-12:
        return None

    x0, y0 = float(P0.x), float(P0.y)
    x2, y2 = float(P2.x), float(P2.y)

    t = ((y2 - y0) - g2 * (x2 - x0)) / (g1 - g2)
    x1 = x0 + t
    y1 = y0 + g1 * t
    return App.Vector(x1, y1, float(P0.z))


def _make_quadratic_bezier(P0: App.Vector, P1: App.Vector, P2: App.Vector):
    """
    Quadratic Bezier curve (3 poles) => exact 2nd-degree conic curve.
    """
    c = Part.BezierCurve()
    c.setPoles([P0, P1, P2])
    return c.toShape()


class VerticalAlignment:
    """
    Vertical Alignment based on PVI + vertical curve length L (symmetric).

    This object can:
      - Evaluate FG elevation at any station (parabolic VC)
      - Build a FG display wire as: Line edges + Quadratic Bezier edges

    Notes:
      - CurveLengths[i] applies to PVI i (end PVIs should be 0)
      - Overlap handling:
          ClampOverlaps True  -> auto reduce lengths
          ClampOverlaps False -> raise Exception
      - MinTangent: minimum tangent length between adjacent curves
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "VerticalAlignment"

        obj.addProperty("App::PropertyFloatList", "PVIStations", "PVI", "PVI stations (m)")
        obj.addProperty("App::PropertyFloatList", "PVIElevations", "PVI", "PVI elevations (m)")
        obj.addProperty("App::PropertyFloatList", "CurveLengths", "PVI", "Vertical curve length L at each PVI (m)")

        obj.addProperty("App::PropertyBool", "ClampOverlaps", "PVI", "Auto-adjust curve lengths to avoid overlaps")
        obj.ClampOverlaps = True

        obj.addProperty("App::PropertyFloat", "MinTangent", "PVI", "Minimum tangent length between adjacent vertical curves (m)")
        obj.MinTangent = 0.0

        obj.addProperty("App::PropertyBool", "ShowPVIWire", "Display", "Show PVI polyline (station-elev)")
        obj.ShowPVIWire = True

        # obj.addProperty("App::PropertyBool", "ShowFGWire", "Display", "Show FG (tangent+parabolic) wire")
        # obj.ShowFGWire = True
        # obj.addProperty(
        #     "App::PropertyBool",
        #     "FGCurvesOnly",
        #     "Display",
        #     "If True, show only vertical curve segments (no tangent lines)"
        # )
        # obj.FGCurvesOnly = False

        # obj.addProperty("App::PropertyFloat", "FGWireZOffset", "Display", "Z offset for FG wire (profile view layering)")
        # obj.FGWireZOffset = 0.0

    

    def execute(self, obj):
        shapes = []

        if obj.ShowPVIWire:
            pvi_wire = self._build_pvi_wire(obj)
            if pvi_wire is not None:
                shapes.append(pvi_wire)

        if not shapes:
            obj.Shape = Part.Shape()
            return

        obj.Shape = shapes[0]
    
    
    def onChanged(self, obj, prop):
        """
        Make Property Editor toggles immediately reflect on shape + keep UX consistent.

        Requested UX:
        - When FGCurvesOnly becomes False:
            ShowFGWire = True
            ShowPVIWire = False
        (We also keep the previously added behavior for curves-only mode to avoid straight-looking PVI polyline.)
        """
        # try:
        #     if prop == "FGCurvesOnly":
        #         curves_only = bool(getattr(obj, "FGCurvesOnly", False))

        #         if curves_only:
        #             # 곡선만 표시 모드에서는 직선처럼 보이는 PVI polyline이 혼동을 주므로 기본적으로 숨김
        #             obj.ShowPVIWire = False
        #             # FG는 보여야 "곡선만"을 볼 수 있으니 켜줌 (원치 않으면 이 줄 제거 가능)
        #             obj.ShowFGWire = True

        #         else:
        #             # 사용자 요구: FGCurvesOnly=False 로 바꾸면 아래 상태를 자동으로 맞춤
        #             obj.ShowFGWire = True
        #             obj.ShowPVIWire = False
        # except Exception:
        #     pass

        # 속성 변경 시 Shape 갱신 강제
        if prop in (
            # "ShowFGWire",
            # "FGCurvesOnly",
            # "FGWireZOffset",
            "ShowPVIWire",
            "PVIStations",
            "PVIElevations",
            "CurveLengths",
            "ClampOverlaps",
            "MinTangent",
        ):
            try:
                obj.touch()
                if obj.Document is not None:
                    obj.Document.recompute()

                # View refresh (일부 환경에서 recompute만으로 화면이 안 바뀌는 케이스 대비)
                try:
                    if hasattr(obj, "ViewObject") and obj.ViewObject:
                        obj.ViewObject.update()
                except Exception:
                    pass

                try:
                    Gui.updateGui()
                except Exception:
                    pass
            except Exception:
                pass


    # -------------------------
    # Public API (static-ish)
    # -------------------------
    @staticmethod
    def elevation_at_station(v_align_obj, s: float) -> float:
        """
        Elevation from PVI + symmetric parabolic vertical curves.
        Same engine used for FG wire generation.
        """
        pvis, grades, curves = VerticalAlignment._solve_curves(v_align_obj)

        if s <= pvis[0][0]:
            return pvis[0][1]

        if s >= pvis[-1][0]:
            return pvis[-1][1]

        for c in curves:
            if c["bvc"] <= s <= c["evc"]:
                x = float(s - c["bvc"])
                L = float(c["L"])
                g1 = float(c["g1"])
                dg = float(c["g2"] - c["g1"])
                z = float(c["z_bvc"]) + g1 * x + (dg / (2.0 * L)) * (x * x)
                return z

        # tangent region: linear between PVI points (simple)
        for i in range(len(pvis) - 1):
            s1, z1, _ = pvis[i]
            s2, z2, _ = pvis[i + 1]
            if s1 <= s <= s2:
                if abs(s2 - s1) < 1e-12:
                    return z1

                g = (z2 - z1) / (s2 - s1)
                return z1 + g * (s - s1)

        return pvis[-1][1]

    # -------------------------
    # Internal: Build wires
    # -------------------------
    def _build_pvi_wire(self, obj):
        st = list(obj.PVIStations or [])
        el = list(obj.PVIElevations or [])
        n = min(len(st), len(el))
        if n < 2:
            return None

        pairs = sorted([(float(st[i]), float(el[i])) for i in range(n)], key=lambda x: x[0])
        pts = [App.Vector(s, z, 0.0) for s, z in pairs]
        return Part.makePolygon(pts)

    def _build_fg_wire(self, obj, zoff: float):
        pvis, grades, curves = VerticalAlignment._solve_curves(obj)

        curves_only = bool(getattr(obj, "FGCurvesOnly", False))

        # If there is no curve, just return a grade polyline as wire of line edges
        # But we still build line edges between PVIs to keep it analytic.
        edges = []

        # Build helper arrays for curve endpoints
        # curves list contains dict: bvc, evc, L, g1,g2,z_bvc
        # We'll create Bezier edges for each curve and connect with line edges in-between.
        # First, build "events" in order: BVC/EVC markers for each curve.
        curve_by_bvc = {c["bvc"]: c for c in curves}
        curve_by_evc = {c["evc"]: c for c in curves}

        # Collect all key stations: start PVI, each BVC, each EVC, end PVI
        key_s = set([pvis[0][0], pvis[-1][0]])
        for c in curves:
            key_s.add(float(c["bvc"]))
            key_s.add(float(c["evc"]))

        keys = sorted(key_s)

        # Function to get tangent grade at station s:
        # If inside a curve, use g1 + dg/L * x
        # Else use grade segment based on PVIs.
        def grade_at(sq: float) -> float:
            for c in curves:
                if c["bvc"] <= sq <= c["evc"]:
                    x = float(sq - c["bvc"])
                    dg = float(c["g2"] - c["g1"])
                    L = float(c["L"])
                    return float(c["g1"] + (dg / L) * x)

            # tangent region: find bracketing PVIs
            for i in range(len(pvis) - 1):
                s1, z1, _ = pvis[i]
                s2, z2, _ = pvis[i + 1]
                if s1 <= sq <= s2:
                    if abs(s2 - s1) < 1e-12:
                        return 0.0

                    return float((z2 - z1) / (s2 - s1))

            return 0.0

        # Build edges between consecutive keys:
        # If [k0,k1] corresponds to a curve interval, make Bezier edge.
        # Otherwise, make a straight line edge.
        for i in range(len(keys) - 1):
            a = float(keys[i])
            b = float(keys[i + 1])

            # Curve interval?
            # We detect if a is a BVC and b is its EVC.
            if a in curve_by_bvc:
                c = curve_by_bvc[a]
                if abs(float(c["evc"]) - b) < 1e-9:
                    # Build curve Bezier (exact quadratic conic)
                    bvc = float(c["bvc"])
                    evc = float(c["evc"])
                    L = float(c["L"])

                    z_bvc = float(c["z_bvc"])
                    z_evc = float(VerticalAlignment.elevation_at_station(obj, evc))

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

            # Otherwise: straight tangent segment (line)            
            if not curves_only:
                za = float(VerticalAlignment.elevation_at_station(obj, a))
                zb = float(VerticalAlignment.elevation_at_station(obj, b))
                Pa = App.Vector(a, za, zoff)
                Pb = App.Vector(b, zb, zoff)
                edges.append(Part.makeLine(Pa, Pb))                            


        App.Console.PrintMessage(f"[VA] curves_only={curves_only}, edges={len(edges)}, curves={len(curves)}\n")

        # Build a Wire
        if not edges:
            return None
        
        # curves-only: edges may be disconnected -> Compound is safer
        if curves_only:
            return Part.Compound(edges)

        try:
            return Part.Wire(edges)
        except Exception:
            # fallback if something is slightly disconnected
            return Part.Compound(edges)

    # -------------------------
    # Internal: Solve curves with clamp/min tangent
    # -------------------------
    @staticmethod
    def _solve_curves(v_align_obj):
        st = list(getattr(v_align_obj, "PVIStations", []) or [])
        el = list(getattr(v_align_obj, "PVIElevations", []) or [])
        Ls = list(getattr(v_align_obj, "CurveLengths", []) or [])

        n = min(len(st), len(el))
        if n < 2:
            raise Exception("Need at least 2 PVI points")

        if len(Ls) < n:
            Ls = list(Ls) + [0.0] * (n - len(Ls))
        else:
            Ls = Ls[:n]

        pvis = sorted([(float(st[i]), float(el[i]), float(Ls[i])) for i in range(n)], key=lambda x: x[0])

        # grades between PVIs
        grades = []
        for i in range(len(pvis) - 1):
            s1, z1, _ = pvis[i]
            s2, z2, _ = pvis[i + 1]
            if abs(s2 - s1) < 1e-12:
                grades.append(0.0)
            else:
                grades.append((z2 - z1) / (s2 - s1))

        clamp = bool(getattr(v_align_obj, "ClampOverlaps", True))
        min_tan = float(getattr(v_align_obj, "MinTangent", 0.0))
        if min_tan < 0.0:
            min_tan = 0.0

        # desired half-lengths
        half = [0.0] * len(pvis)
        for i in range(1, len(pvis) - 1):
            L = float(pvis[i][2])
            half[i] = 0.5 * max(0.0, L)

        # clamp to neighbor PVIs with min tangent
        for i in range(1, len(pvis) - 1):
            si = pvis[i][0]
            s_prev = pvis[i - 1][0]
            s_next = pvis[i + 1][0]

            max_half_prev = max(0.0, (si - s_prev) - min_tan)
            max_half_next = max(0.0, (s_next - si) - min_tan)
            max_half = min(max_half_prev, max_half_next)

            if half[i] > max_half:
                if clamp:
                    half[i] = max_half
                else:
                    raise Exception(
                        f"Vertical curve at PVI {si:.3f}m too long: requested L={2*half[i]:.3f}m "
                        f"exceeds limit {2*max_half:.3f}m (reduce L or enable ClampOverlaps)."
                    )

        # enforce separation between adjacent curves: EVC_i + min_tan <= BVC_{i+1}
        for i in range(1, len(pvis) - 2):
            si = pvis[i][0]
            sj = pvis[i + 1][0]
            gap = (sj - si)

            if half[i] <= 0.0 or half[i + 1] <= 0.0:
                continue

            allowed_sum = max(0.0, gap - min_tan)
            current_sum = half[i] + half[i + 1]

            if current_sum > allowed_sum + 1e-12:
                if not clamp:
                    raise Exception(
                        f"Adjacent vertical curves overlap between {si:.3f}m and {sj:.3f}m "
                        f"(half sum {current_sum:.3f} > allowed {allowed_sum:.3f})."
                    )

                # proportional reduce to preserve ratio
                if current_sum <= 1e-12:
                    half[i] = 0.0
                    half[i + 1] = 0.0
                else:
                    scale = allowed_sum / current_sum
                    half[i] *= scale
                    half[i + 1] *= scale

        # build curve dicts
        curves = []
        for i in range(1, len(pvis) - 1):
            si, zi, _ = pvis[i]
            hi = float(half[i])
            if hi <= 0.0:
                continue

            bvc = si - hi
            evc = si + hi
            L = max(1e-9, 2.0 * hi)

            g1 = float(grades[i - 1])
            g2 = float(grades[i])

            z_bvc = float(zi - g1 * (0.5 * L))

            curves.append({
                "bvc": float(bvc),
                "evc": float(evc),
                "L": float(L),
                "g1": float(g1),
                "g2": float(g2),
                "z_bvc": float(z_bvc),
            })

        return pvis, grades, curves


class ViewProviderVerticalAlignment:
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