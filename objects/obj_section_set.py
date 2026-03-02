# CorridorRoad/objects/obj_section_set.py
import re
import math

import FreeCAD as App
import Part

from objects.obj_centerline3d import Centerline3D

_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_mesh_object(obj) -> bool:
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _is_shape_object(obj) -> bool:
    try:
        return hasattr(obj, "Shape") and obj.Shape is not None and (not obj.Shape.isNull())
    except Exception:
        return False


def _find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _find_terrain_candidate(doc):
    if doc is None:
        return None
    # 1) Prefer explicit terrain-like names.
    for o in doc.Objects:
        try:
            nm = str(getattr(o, "Name", "") or "").lower()
            lb = str(getattr(o, "Label", "") or "").lower()
            if ("terrain" in nm or "terrain" in lb) and (_is_mesh_object(o) or _is_shape_object(o)):
                return o
        except Exception:
            continue
    # 2) Fallback to first mesh object only (safer than arbitrary shape).
    for o in doc.Objects:
        if _is_mesh_object(o):
            return o
    # 3) Last fallback: terrain/surface-like shape names only.
    for o in doc.Objects:
        try:
            nm = str(getattr(o, "Name", "") or "").lower()
            lb = str(getattr(o, "Label", "") or "").lower()
            if ("surface" in nm or "surface" in lb or "eg" in nm or "existing" in nm) and _is_shape_object(o):
                return o
        except Exception:
            continue
    return None


def _unique_sorted(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in values])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _parse_station_text(text: str):
    if not text:
        return []
    tokens = re.split(r"[,\s;]+", str(text).strip())
    out = []
    for t in tokens:
        if not t:
            continue
        try:
            out.append(float(t))
        except Exception:
            continue
    return out


def _mark_corridor_needs_recompute(obj_corridor):
    try:
        if hasattr(obj_corridor, "NeedsRecompute"):
            obj_corridor.NeedsRecompute = True
    except Exception:
        pass

    try:
        st = str(getattr(obj_corridor, "Status", "") or "")
        if "NEEDS_RECOMPUTE" not in st:
            obj_corridor.Status = "NEEDS_RECOMPUTE: Source SectionSet changed."
    except Exception:
        pass

    try:
        label = str(getattr(obj_corridor, "Label", "") or "")
        if _RECOMP_LABEL_SUFFIX not in label:
            obj_corridor.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
    except Exception:
        pass


def ensure_section_set_properties(obj):
    if not hasattr(obj, "Group"):
        obj.addProperty("App::PropertyLinkList", "Group", "Sections", "Child section objects")

    if not hasattr(obj, "SourceCenterlineDisplay"):
        obj.addProperty("App::PropertyLink", "SourceCenterlineDisplay", "Sections", "Centerline3DDisplay source link")
    if not hasattr(obj, "AssemblyTemplate"):
        obj.addProperty("App::PropertyLink", "AssemblyTemplate", "Sections", "AssemblyTemplate link")
    if not hasattr(obj, "TerrainMesh"):
        obj.addProperty("App::PropertyLink", "TerrainMesh", "Sections", "Optional terrain source link for daylight (Mesh/Shape)")

    if not hasattr(obj, "Mode"):
        obj.addProperty("App::PropertyEnumeration", "Mode", "Sections", "Station selection mode")
        obj.Mode = ["Range", "Manual"]
        obj.Mode = "Range"

    if not hasattr(obj, "StartStation"):
        obj.addProperty("App::PropertyFloat", "StartStation", "Sections", "Start station (m)")
        obj.StartStation = 0.0
    if not hasattr(obj, "EndStation"):
        obj.addProperty("App::PropertyFloat", "EndStation", "Sections", "End station (m)")
        obj.EndStation = 100.0
    if not hasattr(obj, "Interval"):
        obj.addProperty("App::PropertyFloat", "Interval", "Sections", "Interval for range mode (m)")
        obj.Interval = 20.0
    if not hasattr(obj, "StationText"):
        obj.addProperty("App::PropertyString", "StationText", "Sections", "Manual station list text")
        obj.StationText = ""

    if not hasattr(obj, "StationValues"):
        obj.addProperty("App::PropertyFloatList", "StationValues", "Result", "Resolved stations for sections (m)")
    if not hasattr(obj, "SectionSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SectionSchemaVersion", "Result", "Section schema version")
        obj.SectionSchemaVersion = 1
    if not hasattr(obj, "SectionCount"):
        obj.addProperty("App::PropertyInteger", "SectionCount", "Result", "Section count")
        obj.SectionCount = 0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"

    if not hasattr(obj, "CreateChildSections"):
        obj.addProperty("App::PropertyBool", "CreateChildSections", "Sections", "Create child section objects in tree")
        obj.CreateChildSections = True
    if not hasattr(obj, "AutoRebuildChildren"):
        obj.addProperty("App::PropertyBool", "AutoRebuildChildren", "Sections", "Auto rebuild child sections on recompute")
        obj.AutoRebuildChildren = True
    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "Sections", "Set True to force child section rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "ShowSectionWires"):
        obj.addProperty("App::PropertyBool", "ShowSectionWires", "Display", "Show section wires as set shape")
        obj.ShowSectionWires = True


class SectionSet:
    """
    Section set container with station selection settings and aggregate display.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "SectionSet"
        self._is_rebuilding_children = False
        self._suspend_recompute = False
        ensure_section_set_properties(obj)

    @staticmethod
    def resolve_station_values(obj):
        src = getattr(obj, "SourceCenterlineDisplay", None)
        if src is None:
            return []

        aln = getattr(src, "Alignment", None)
        if aln is None or aln.Shape is None or aln.Shape.isNull():
            return []

        total = float(aln.Shape.Length)
        mode = str(getattr(obj, "Mode", "Range"))

        if mode == "Manual":
            vals = _parse_station_text(getattr(obj, "StationText", ""))
            vals = [min(max(0.0, float(v)), total) for v in vals]
            return _unique_sorted(vals)

        # Range mode
        s0 = float(getattr(obj, "StartStation", 0.0))
        s1 = float(getattr(obj, "EndStation", total))
        if s1 < s0:
            s0, s1 = s1, s0

        s0 = min(max(0.0, s0), total)
        s1 = min(max(0.0, s1), total)
        if s1 < s0 + 1e-9:
            return [s0]

        itv = float(getattr(obj, "Interval", 20.0))
        if itv <= 1e-9:
            itv = 20.0
            obj.Interval = itv

        vals = [s0]
        s = s0 + itv
        while s < s1 - 1e-9:
            vals.append(float(s))
            s += itv
        vals.append(float(s1))
        return _unique_sorted(vals)

    @staticmethod
    def _resolve_terrain_source(obj):
        t = getattr(obj, "TerrainMesh", None)
        if _is_mesh_object(t) or _is_shape_object(t):
            return t

        doc = getattr(obj, "Document", None)
        prj = _find_project(doc)
        if prj is not None:
            pt = getattr(prj, "Terrain", None)
            if _is_mesh_object(pt) or _is_shape_object(pt):
                return pt

        cand = _find_terrain_candidate(doc)
        if cand is not None:
            return cand

        return None

    @staticmethod
    def _triangle_bbox_xy(p0, p1, p2):
        return (
            min(p0.x, p1.x, p2.x),
            max(p0.x, p1.x, p2.x),
            min(p0.y, p1.y, p2.y),
            max(p0.y, p1.y, p2.y),
        )

    @staticmethod
    def _to_vec(p):
        try:
            return App.Vector(float(p.x), float(p.y), float(p.z))
        except Exception:
            pass
        try:
            return App.Vector(float(p[0]), float(p[1]), float(p[2]))
        except Exception:
            pass
        raise Exception("Invalid point format.")

    @staticmethod
    def _mesh_triangles(mesh_obj):
        mesh = getattr(mesh_obj, "Mesh", None)
        if mesh is None:
            return []

        triangles = []
        topo = None
        try:
            topo = mesh.Topology
            if callable(topo):
                topo = topo()
        except Exception:
            topo = None

        if topo is not None and len(topo) == 2:
            pts, faces = topo
            for f in faces:
                try:
                    i0, i1, i2 = int(f[0]), int(f[1]), int(f[2])
                    p0 = SectionSet._to_vec(pts[i0])
                    p1 = SectionSet._to_vec(pts[i1])
                    p2 = SectionSet._to_vec(pts[i2])
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        continue
                    bb = SectionSet._triangle_bbox_xy(p0, p1, p2)
                    triangles.append((p0, p1, p2, bb))
                except Exception:
                    continue
        else:
            for fc in list(getattr(mesh, "Facets", []) or []):
                try:
                    pts = list(getattr(fc, "Points", []) or [])
                    if len(pts) != 3:
                        continue
                    p0, p1, p2 = SectionSet._to_vec(pts[0]), SectionSet._to_vec(pts[1]), SectionSet._to_vec(pts[2])
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        continue
                    bb = SectionSet._triangle_bbox_xy(p0, p1, p2)
                    triangles.append((p0, p1, p2, bb))
                except Exception:
                    continue

        return triangles

    @staticmethod
    def _shape_triangles(shape_obj, deflection: float = 1.0):
        shp = getattr(shape_obj, "Shape", None)
        if shp is None or shp.isNull():
            return []
        triangles = []
        try:
            pts, tri_idx = shp.tessellate(max(0.01, float(deflection)))
        except Exception:
            return []
        for t in tri_idx:
            try:
                i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
                p0 = SectionSet._to_vec(pts[i0])
                p1 = SectionSet._to_vec(pts[i1])
                p2 = SectionSet._to_vec(pts[i2])
                if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                    continue
                bb = SectionSet._triangle_bbox_xy(p0, p1, p2)
                triangles.append((p0, p1, p2, bb))
            except Exception:
                continue
        return triangles

    @staticmethod
    def _surface_triangles(src_obj):
        if _is_mesh_object(src_obj):
            return SectionSet._mesh_triangles(src_obj)
        if _is_shape_object(src_obj):
            return SectionSet._shape_triangles(src_obj, deflection=1.0)
        return []

    @staticmethod
    def _build_xy_buckets(triangles, bucket_size: float, max_cells_per_triangle: int = 20000):
        if bucket_size <= 1e-9:
            bucket_size = 1.0
        buckets = {}
        wide = []
        for idx, tri in enumerate(triangles):
            bb = tri[3]
            ix0 = int(math.floor(bb[0] / bucket_size))
            ix1 = int(math.floor(bb[1] / bucket_size))
            iy0 = int(math.floor(bb[2] / bucket_size))
            iy1 = int(math.floor(bb[3] / bucket_size))
            nx = int(max(0, ix1 - ix0 + 1))
            ny = int(max(0, iy1 - iy0 + 1))
            if int(nx * ny) > int(max(1, max_cells_per_triangle)):
                # Guard against pathological bucket blow-up.
                wide.append(idx)
                continue
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    buckets.setdefault((ix, iy), []).append(idx)
        if len(wide) > 5000:
            stride = int(math.ceil(float(len(wide)) / 5000.0))
            wide = wide[::max(1, stride)]
        return buckets, wide

    @staticmethod
    def _point_in_tri_z(x, y, p0, p1, p2):
        x0, y0 = p0.x, p0.y
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) <= 1e-14:
            return None
        w0 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / den
        w1 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / den
        w2 = 1.0 - w0 - w1
        tol = 1e-9
        if w0 < -tol or w1 < -tol or w2 < -tol:
            return None
        return float(w0 * p0.z + w1 * p1.z + w2 * p2.z)

    @staticmethod
    def _terrain_sampler(src_obj, max_triangles: int = 300000):
        tris = SectionSet._surface_triangles(src_obj)
        if not tris:
            return None

        mt = int(max(1000, int(max_triangles)))
        if len(tris) > mt:
            stride = int(math.ceil(float(len(tris)) / float(mt)))
            tris = tris[::max(1, stride)]

        bucket = 2.0
        try:
            if _is_mesh_object(src_obj):
                bb = src_obj.Mesh.BoundBox
            else:
                bb = src_obj.Shape.BoundBox
            n = max(1, len(tris))
            area = max(1.0, float(bb.XLength) * float(bb.YLength))
            bucket = max(0.5, min(20.0, math.sqrt(area / float(n)) * 2.0))
        except Exception:
            pass
        buckets, wide = SectionSet._build_xy_buckets(tris, bucket)
        return {
            "triangles": tris,
            "bucket_size": bucket,
            "buckets": buckets,
            "wide_indices": wide,
        }

    @staticmethod
    def _terrain_z_at(sampler, x: float, y: float):
        if sampler is None:
            return None
        tris = sampler["triangles"]
        buckets = sampler["buckets"]
        wide = sampler.get("wide_indices", []) or []
        bs = float(sampler["bucket_size"])

        ix = int(math.floor(float(x) / bs))
        iy = int(math.floor(float(y) / bs))
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand.extend(buckets.get((ix + dx, iy + dy), []))
        if wide:
            cand.extend(wide)
        if not cand:
            return None

        z_best = None
        seen = set()
        for idx in cand:
            if idx in seen:
                continue
            seen.add(idx)
            p0, p1, p2, bb = tris[idx]
            if x < bb[0] - 1e-9 or x > bb[1] + 1e-9 or y < bb[2] - 1e-9 or y > bb[3] + 1e-9:
                continue
            z = SectionSet._point_in_tri_z(x, y, p0, p1, p2)
            if z is None:
                continue
            if z_best is None or z > z_best:
                z_best = z
        return z_best

    @staticmethod
    def _solve_daylight_width(edge_p, outward_n, up_z, slope_pct: float, max_w: float, sampler, step: float):
        mw = max(0.0, float(max_w))
        if sampler is None or mw <= 1e-9:
            return mw

        st = max(0.2, float(step))
        if st > mw:
            st = mw

        def f_at(w):
            q = edge_p + outward_n * float(w) + up_z * (-float(w) * float(slope_pct) / 100.0)
            zt = SectionSet._terrain_z_at(sampler, q.x, q.y)
            if zt is None:
                return None
            return float(q.z - zt)

        # Daylight policy:
        # - If a sign-change intersection is found, use that root.
        # - If no intersection exists inside [0, max_w], keep max_w
        #   (do not collapse to near-zero width).
        had_sample = False
        prev_w = None
        prev_f = None
        w = 0.0
        while w <= mw + 1e-9:
            fv = f_at(w)
            if fv is not None:
                had_sample = True
                if prev_f is not None and (prev_f == 0.0 or fv == 0.0 or (prev_f > 0.0 and fv < 0.0) or (prev_f < 0.0 and fv > 0.0)):
                    if prev_w is None:
                        return w
                    den = (fv - prev_f)
                    if abs(den) <= 1e-12:
                        return w
                    t = -prev_f / den
                    return max(0.0, min(mw, prev_w + (w - prev_w) * t))
                prev_w = w
                prev_f = fv
            w += st

        if not had_sample:
            return mw
        return mw

    @staticmethod
    def _daylight_signed_slope(edge_p, slope_pct: float, sampler):
        """
        Resolve cut/fill side-slope direction automatically for daylight:
        - terrain above edge -> cut slope (upward outward)  -> negative slope_pct
        - terrain below edge -> fill slope (downward outward) -> positive slope_pct
        If terrain cannot be sampled, keep user-provided sign.
        """
        s = float(slope_pct)
        mag = abs(s)
        if mag <= 1e-9:
            return 0.0

        sign_user = -1.0 if s < 0.0 else 1.0
        if sampler is None:
            return sign_user * mag

        zt = SectionSet._terrain_z_at(sampler, float(edge_p.x), float(edge_p.y))
        if zt is None:
            return sign_user * mag

        tol = 1e-3
        if float(zt) > float(edge_p.z) + tol:
            # Cut condition: terrain is above road edge -> slope goes upward outward.
            return -mag
        if float(zt) < float(edge_p.z) - tol:
            # Fill condition: terrain is below road edge -> slope goes downward outward.
            return +mag
        return sign_user * mag

    @staticmethod
    def build_section_wire(source_obj, asm_obj, station: float, prev_n: App.Vector = None, terrain_sampler=None):
        frame = Centerline3D.frame_at_station(source_obj, float(station), eps=0.1, prev_n=prev_n)
        p = frame["point"]
        n = frame["N"]
        z = frame["Z"]

        lw = max(0.0, float(getattr(asm_obj, "LeftWidth", 0.0)))
        rw = max(0.0, float(getattr(asm_obj, "RightWidth", 0.0)))
        ls = float(getattr(asm_obj, "LeftSlopePct", 0.0))
        rs = float(getattr(asm_obj, "RightSlopePct", 0.0))
        use_ss = bool(getattr(asm_obj, "UseSideSlopes", False))
        lsw = max(0.0, float(getattr(asm_obj, "LeftSideWidth", 0.0)))
        rsw = max(0.0, float(getattr(asm_obj, "RightSideWidth", 0.0)))
        lss = float(getattr(asm_obj, "LeftSideSlopePct", 0.0))
        rss = float(getattr(asm_obj, "RightSideSlopePct", 0.0))
        use_day = bool(getattr(asm_obj, "UseDaylightToTerrain", False))
        day_step = max(0.2, float(getattr(asm_obj, "DaylightSearchStep", 1.0)))

        dz_l = -lw * ls / 100.0
        dz_r = -rw * rs / 100.0

        p_l = p + n * lw + z * dz_l
        p_r = p - n * rw + z * dz_r

        lss_eff = float(lss)
        rss_eff = float(rss)
        if use_day:
            lss_eff = SectionSet._daylight_signed_slope(p_l, lss, terrain_sampler)
            rss_eff = SectionSet._daylight_signed_slope(p_r, rss, terrain_sampler)

        pts = [p_l, p, p_r]
        if use_ss and lsw > 1e-9:
            w_l = lsw
            if use_day:
                w_l = SectionSet._solve_daylight_width(
                    p_l, n, z, lss_eff, lsw, terrain_sampler, day_step
                )
            w_l = max(0.01 if lsw > 1e-9 else 0.0, min(lsw, w_l))
            p_lt = p_l + n * w_l + z * (-w_l * lss_eff / 100.0)
            pts = [p_lt] + pts
        if use_ss and rsw > 1e-9:
            w_r = rsw
            if use_day:
                w_r = SectionSet._solve_daylight_width(
                    p_r, -n, z, rss_eff, rsw, terrain_sampler, day_step
                )
            w_r = max(0.01 if rsw > 1e-9 else 0.0, min(rsw, w_r))
            p_rt = p_r - n * w_r + z * (-w_r * rss_eff / 100.0)
            pts = pts + [p_rt]

        w = Part.makePolygon(pts)
        return w, n

    @staticmethod
    def build_section_wires(obj):
        src = getattr(obj, "SourceCenterlineDisplay", None)
        asm = getattr(obj, "AssemblyTemplate", None)
        if src is None:
            raise Exception("SourceCenterlineDisplay is missing.")
        if asm is None:
            raise Exception("AssemblyTemplate is missing.")

        stations = list(getattr(obj, "StationValues", []) or [])
        if len(stations) < 1:
            stations = SectionSet.resolve_station_values(obj)
        if len(stations) < 1:
            return [], [], False, False

        terrain_sampler = None
        terrain_found = False
        try:
            if bool(getattr(asm, "UseDaylightToTerrain", False)):
                tsrc = SectionSet._resolve_terrain_source(obj)
                terrain_found = tsrc is not None
                if tsrc is not None:
                    day_max = int(getattr(asm, "DaylightMaxTriangles", 300000))
                    terrain_sampler = SectionSet._terrain_sampler(tsrc, max_triangles=day_max)
        except Exception:
            terrain_sampler = None

        wires = []
        prev_n = None
        for s in stations:
            w, prev_n = SectionSet.build_section_wire(
                src, asm, float(s), prev_n=prev_n, terrain_sampler=terrain_sampler
            )
            wires.append(w)

        return stations, wires, terrain_found, (terrain_sampler is not None)

    @staticmethod
    def clear_child_sections(obj):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return
        group = list(getattr(obj, "Group", []) or [])
        if not group:
            return
        for ch in group:
            try:
                doc.removeObject(ch.Name)
            except Exception:
                pass
        obj.Group = []

    @staticmethod
    def rebuild_child_sections(obj, stations=None, wires=None):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return

        if stations is None or wires is None:
            stations, wires, _tf, _so = SectionSet.build_section_wires(obj)
        if len(stations) != len(wires):
            raise Exception("Child rebuild failed: stations/wires size mismatch.")

        SectionSet.clear_child_sections(obj)
        children = []
        for s, w in zip(stations, wires):
            ch = doc.addObject("Part::Feature", "SectionSlice")
            ch.Label = f"Section @STA {float(s):.3f}"
            try:
                if not hasattr(ch, "Station"):
                    ch.addProperty("App::PropertyFloat", "Station", "Section", "Station (m)")
                ch.Station = float(s)
            except Exception:
                pass
            try:
                if not hasattr(ch, "ParentSectionSet"):
                    ch.addProperty("App::PropertyLink", "ParentSectionSet", "Section", "Owner SectionSet")
                ch.ParentSectionSet = obj
            except Exception:
                pass
            ch.Shape = w
            children.append(ch)
        obj.Group = children

    def execute(self, obj):
        ensure_section_set_properties(obj)
        try:
            asm = getattr(obj, "AssemblyTemplate", None)
            use_ss = bool(getattr(asm, "UseSideSlopes", False)) if asm is not None else False
            left_on = float(getattr(asm, "LeftSideWidth", 0.0)) > 1e-9 if asm is not None else False
            right_on = float(getattr(asm, "RightSideWidth", 0.0)) > 1e-9 if asm is not None else False
            # Schema contract:
            # - v1: 3 points (Left->Center->Right)
            # - v2: side-slope extended profile (>=3 points)
            obj.SectionSchemaVersion = 2 if (use_ss and (left_on or right_on)) else 1
            stations = SectionSet.resolve_station_values(obj)
            obj.StationValues = stations
            obj.SectionCount = len(stations)

            if not bool(getattr(obj, "ShowSectionWires", True)):
                obj.Shape = Part.Shape()
                obj.Status = "Hidden"
                return

            if len(stations) < 1:
                obj.Shape = Part.Shape()
                obj.Status = "No stations"
                return

            _stations, wires, terrain_found, sampler_ok = SectionSet.build_section_wires(obj)
            if len(wires) < 1:
                obj.Shape = Part.Shape()
                obj.Status = "No section wires"
                return

            if len(wires) == 1:
                obj.Shape = wires[0]
            else:
                obj.Shape = Part.Compound(wires)

            # Keep tree child sections consistent with current template/centerline.
            if bool(getattr(obj, "CreateChildSections", True)):
                need_rebuild = bool(getattr(obj, "AutoRebuildChildren", True)) or bool(getattr(obj, "RebuildNow", False))
                if need_rebuild and (not self._is_rebuilding_children):
                    self._is_rebuilding_children = True
                    try:
                        SectionSet.rebuild_child_sections(obj, stations=stations, wires=wires)
                    finally:
                        self._is_rebuilding_children = False
            else:
                if (not self._is_rebuilding_children):
                    self._is_rebuilding_children = True
                    try:
                        SectionSet.clear_child_sections(obj)
                    finally:
                        self._is_rebuilding_children = False

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False
            use_day = bool(getattr(asm, "UseDaylightToTerrain", False)) if asm is not None else False
            if use_day and (not terrain_found):
                obj.Status = "WARN: UseDaylightToTerrain=True but no terrain source found. Fixed side widths used."
            elif use_day and terrain_found and (not sampler_ok):
                obj.Status = "WARN: Terrain source found but daylight sampler failed. Fixed side widths used."
            else:
                obj.Status = "OK"

            # Push parametric updates to linked corridor objects.
            if obj.Document is not None:
                for o in list(obj.Document.Objects):
                    try:
                        if getattr(o, "SourceSectionSet", None) == obj and bool(getattr(o, "AutoUpdate", True)):
                            _mark_corridor_needs_recompute(o)
                    except Exception:
                        pass

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SectionCount = 0
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "SourceCenterlineDisplay",
            "AssemblyTemplate",
            "TerrainMesh",
            "Mode",
            "StartStation",
            "EndStation",
            "Interval",
            "StationText",
            "CreateChildSections",
            "AutoRebuildChildren",
            "RebuildNow",
            "ShowSectionWires",
        ):
            try:
                obj.touch()
                if obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderSectionSet:
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
