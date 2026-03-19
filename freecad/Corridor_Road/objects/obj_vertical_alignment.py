# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import Part
import FreeCADGui as Gui


class VerticalAlignment:
    """
    Vertical Alignment based on PVI + vertical curve length L (symmetric).

    Role:
      - Data/engine for vertical geometry
      - Optional PVI polyline display only
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

    def execute(self, obj):
        if obj.ShowPVIWire:
            pvi_wire = self._build_pvi_wire(obj)
            if pvi_wire is not None:
                obj.Shape = pvi_wire
                return

        obj.Shape = Part.Shape()

    def onChanged(self, obj, prop):
        if prop in (
            "ShowPVIWire",
            "PVIStations",
            "PVIElevations",
            "CurveLengths",
            "ClampOverlaps",
            "MinTangent",
        ):
            try:
                obj.touch()

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

    @staticmethod
    def elevation_at_station(v_align_obj, s: float) -> float:
        """
        Elevation from PVI + symmetric parabolic vertical curves.
        Shared engine used by FGDisplay.
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

        for i in range(len(pvis) - 1):
            s1, z1, _ = pvis[i]
            s2, z2, _ = pvis[i + 1]
            if s1 <= s <= s2:
                if abs(s2 - s1) < 1e-12:
                    return z1

                g = (z2 - z1) / (s2 - s1)
                return z1 + g * (s - s1)

        return pvis[-1][1]

    def _build_pvi_wire(self, obj):
        st = list(obj.PVIStations or [])
        el = list(obj.PVIElevations or [])
        n = min(len(st), len(el))
        if n < 2:
            return None

        pairs = sorted([(float(st[i]), float(el[i])) for i in range(n)], key=lambda x: x[0])
        pts = [App.Vector(s, z, 0.0) for s, z in pairs]
        return Part.makePolygon(pts)

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

        half = [0.0] * len(pvis)
        for i in range(1, len(pvis) - 1):
            L = float(pvis[i][2])
            half[i] = 0.5 * max(0.0, L)

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

                if current_sum <= 1e-12:
                    half[i] = 0.0
                    half[i + 1] = 0.0
                else:
                    scale = allowed_sum / current_sum
                    half[i] *= scale
                    half[i + 1] *= scale

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
