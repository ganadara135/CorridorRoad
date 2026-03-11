# CorridorRoad/objects/obj_section_set.py
import re
import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_project import get_length_scale
from freecad.Corridor_Road.objects import coord_transform as _ct
from freecad.Corridor_Road.objects import surface_sampling_core as _ssc

_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_mesh_object(obj) -> bool:
    return _ssc.is_mesh_object(obj)


def _is_shape_object(obj) -> bool:
    return _ssc.is_shape_object(obj)


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
            if ("terrain" in nm or "terrain" in lb) and _is_mesh_object(o):
                return o
        except Exception:
            continue
    # 2) Fallback to first mesh object.
    for o in doc.Objects:
        if _is_mesh_object(o):
            return o
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


def _alignment_ip_key_stations(aln):
    if aln is None or getattr(aln, "Shape", None) is None or aln.Shape.isNull():
        return []
    total = float(aln.Shape.Length)
    if total <= 1e-9:
        return [0.0]

    vals = [0.0, total]
    pts = list(getattr(aln, "IPPoints", []) or [])
    for p in pts:
        try:
            s = float(HorizontalAlignment.station_at_xy(aln, float(p.x), float(p.y), samples_per_edge=48))
            vals.append(s)
        except Exception:
            continue
    vals = [min(max(0.0, float(v)), total) for v in vals]
    return _unique_sorted(vals)


def _alignment_transition_key_stations(aln):
    if aln is None or getattr(aln, "Shape", None) is None or aln.Shape.isNull():
        return [], [], [], []
    total = float(aln.Shape.Length)
    if total <= 1e-9:
        return [], [], [], []

    ts = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "TSKeyStations", []) or [])]
    sc = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "SCKeyStations", []) or [])]
    cs = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "CSKeyStations", []) or [])]
    st = [min(max(0.0, float(v)), total) for v in list(getattr(aln, "STKeyStations", []) or [])]
    return _unique_sorted(ts), _unique_sorted(sc), _unique_sorted(cs), _unique_sorted(st)


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
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "Group"):
        obj.addProperty("App::PropertyLinkList", "Group", "Sections", "Child section objects")

    if not hasattr(obj, "SourceCenterlineDisplay"):
        obj.addProperty("App::PropertyLink", "SourceCenterlineDisplay", "Sections", "Centerline3DDisplay source link")
    if not hasattr(obj, "AssemblyTemplate"):
        obj.addProperty("App::PropertyLink", "AssemblyTemplate", "Sections", "AssemblyTemplate link")
    if not hasattr(obj, "TerrainMesh"):
        obj.addProperty("App::PropertyLink", "TerrainMesh", "Sections", "Optional terrain source link for daylight (Mesh only)")
    if not hasattr(obj, "TerrainMeshCoords"):
        obj.addProperty(
            "App::PropertyEnumeration",
            "TerrainMeshCoords",
            "Sections",
            "Coordinate system of daylight terrain source",
        )
        obj.TerrainMeshCoords = ["Local", "World"]
        obj.TerrainMeshCoords = "Local"
    if not hasattr(obj, "DaylightAuto"):
        obj.addProperty("App::PropertyBool", "DaylightAuto", "Sections", "Auto daylight to terrain during section build")
        obj.DaylightAuto = True

    if not hasattr(obj, "Mode"):
        obj.addProperty("App::PropertyEnumeration", "Mode", "Sections", "Station selection mode")
        obj.Mode = ["Range", "Manual"]
        obj.Mode = "Range"

    if not hasattr(obj, "StartStation"):
        obj.addProperty("App::PropertyFloat", "StartStation", "Sections", "Start station (m)")
        obj.StartStation = 0.0
    if not hasattr(obj, "EndStation"):
        obj.addProperty("App::PropertyFloat", "EndStation", "Sections", "End station (m)")
        obj.EndStation = 100.0 * scale
    if not hasattr(obj, "Interval"):
        obj.addProperty("App::PropertyFloat", "Interval", "Sections", "Interval for range mode (m)")
        obj.Interval = 20.0 * scale
    if not hasattr(obj, "StationText"):
        obj.addProperty("App::PropertyString", "StationText", "Sections", "Manual station list text")
        obj.StationText = ""
    if not hasattr(obj, "IncludeAlignmentIPStations"):
        obj.addProperty("App::PropertyBool", "IncludeAlignmentIPStations", "Sections", "In Range mode, always include alignment IP key stations")
        obj.IncludeAlignmentIPStations = True
    if not hasattr(obj, "IncludeAlignmentSCCSStations"):
        obj.addProperty("App::PropertyBool", "IncludeAlignmentSCCSStations", "Sections", "In Range mode, include transition TS/SC/CS/ST key stations")
        obj.IncludeAlignmentSCCSStations = False
    if not hasattr(obj, "IncludeStructureStations"):
        obj.addProperty("App::PropertyBool", "IncludeStructureStations", "Sections", "Include structure/crossing key stations from text list")
        obj.IncludeStructureStations = False
    if not hasattr(obj, "StructureStationText"):
        obj.addProperty("App::PropertyString", "StructureStationText", "Sections", "Structure/crossing key stations list text")
        obj.StructureStationText = ""

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
        vals = []
        s0 = 0.0
        s1 = float(total)

        if mode == "Manual":
            vals = _parse_station_text(getattr(obj, "StationText", ""))
            vals = [min(max(0.0, float(v)), total) for v in vals]
        else:
            # Range mode
            s0 = float(getattr(obj, "StartStation", 0.0))
            s1 = float(getattr(obj, "EndStation", total))
            if s1 < s0:
                s0, s1 = s1, s0

            s0 = min(max(0.0, s0), total)
            s1 = min(max(0.0, s1), total)
            if s1 < s0 + 1e-9:
                vals = [s0]
            else:
                itv = float(getattr(obj, "Interval", 20.0))
                if itv <= 1e-9:
                    itv = 20.0 * get_length_scale(getattr(obj, "Document", None), default=1.0)
                    obj.Interval = itv

                vals = [s0]
                s = s0 + itv
                while s < s1 - 1e-9:
                    vals.append(float(s))
                    s += itv
                vals.append(float(s1))

            if bool(getattr(obj, "IncludeAlignmentIPStations", True)):
                try:
                    keys = _alignment_ip_key_stations(aln)
                    keys = [v for v in keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    vals.extend(keys)
                except Exception:
                    pass
            if bool(getattr(obj, "IncludeAlignmentSCCSStations", False)):
                try:
                    ts_keys, sc_keys, cs_keys, st_keys = _alignment_transition_key_stations(aln)
                    ts_keys = [v for v in ts_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    sc_keys = [v for v in sc_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    cs_keys = [v for v in cs_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    st_keys = [v for v in st_keys if (v >= s0 - 1e-9 and v <= s1 + 1e-9)]
                    vals.extend(ts_keys)
                    vals.extend(sc_keys)
                    vals.extend(cs_keys)
                    vals.extend(st_keys)
                except Exception:
                    pass

        if bool(getattr(obj, "IncludeStructureStations", False)):
            try:
                sk = _parse_station_text(getattr(obj, "StructureStationText", ""))
                if mode == "Range":
                    sk = [float(v) for v in sk if (float(v) >= s0 - 1e-9 and float(v) <= s1 + 1e-9)]
                sk = [min(max(0.0, float(v)), total) for v in sk]
                vals.extend(sk)
            except Exception:
                pass
        return _unique_sorted(vals)

    @staticmethod
    def resolve_station_tags(obj, stations):
        """
        Resolve per-station tag list used by child section labels.
        """
        out = [[] for _ in stations]
        if not stations:
            return out

        src = getattr(obj, "SourceCenterlineDisplay", None)
        aln = getattr(src, "Alignment", None) if src is not None else None
        if aln is None or getattr(aln, "Shape", None) is None or aln.Shape.isNull():
            return out

        tol = max(1e-4, 1e-6 * float(getattr(aln.Shape, "Length", 1.0)))
        key_sets = []

        if bool(getattr(obj, "IncludeAlignmentIPStations", True)):
            try:
                key_sets.append(("PI", _alignment_ip_key_stations(aln)))
            except Exception:
                pass
        if bool(getattr(obj, "IncludeAlignmentSCCSStations", False)):
            try:
                ts_keys, sc_keys, cs_keys, st_keys = _alignment_transition_key_stations(aln)
                key_sets.append(("TS", ts_keys))
                key_sets.append(("SC", sc_keys))
                key_sets.append(("CS", cs_keys))
                key_sets.append(("ST", st_keys))
            except Exception:
                pass
        if bool(getattr(obj, "IncludeStructureStations", False)):
            try:
                stx = _parse_station_text(getattr(obj, "StructureStationText", ""))
                stx = [min(max(0.0, float(v)), float(aln.Shape.Length)) for v in stx]
                key_sets.append(("STR", _unique_sorted(stx)))
            except Exception:
                pass

        if not key_sets:
            return out

        for i, s in enumerate(stations):
            ss = float(s)
            tags = []
            for tag, keys in key_sets:
                if any(abs(ss - float(k)) <= tol for k in keys):
                    tags.append(tag)
            out[i] = tags
        return out

    @staticmethod
    def _resolve_terrain_source(obj):
        t = getattr(obj, "TerrainMesh", None)
        if _is_mesh_object(t):
            return t

        doc = getattr(obj, "Document", None)
        prj = _find_project(doc)
        if prj is not None:
            pt = getattr(prj, "Terrain", None)
            if _is_mesh_object(pt):
                return pt

        cand = _find_terrain_candidate(doc)
        if cand is not None:
            return cand

        return None

    @staticmethod
    def _triangle_bbox_xy(p0, p1, p2):
        return _ssc.triangle_bbox_xy(p0, p1, p2)

    @staticmethod
    def _to_vec(p):
        return _ssc.to_vec(p)

    @staticmethod
    def _mesh_triangles(mesh_obj):
        return _ssc.mesh_triangles(mesh_obj)

    @staticmethod
    def _shape_triangles(shape_obj, deflection: float = 1.0):
        return _ssc.shape_triangles(shape_obj, deflection=deflection)

    @staticmethod
    def _surface_triangles(src_obj):
        if _is_mesh_object(src_obj):
            return SectionSet._mesh_triangles(src_obj)
        return []

    @staticmethod
    def _build_xy_buckets(triangles, bucket_size: float, max_cells_per_triangle: int = 20000):
        return _ssc.build_xy_buckets(
            triangles,
            bucket_size,
            max_cells_per_triangle=max_cells_per_triangle,
            max_wide_items=5000,
        )

    @staticmethod
    def _point_in_tri_z(x, y, p0, p1, p2):
        return _ssc.point_in_tri_z(x, y, p0, p1, p2)

    @staticmethod
    def _terrain_sampler(src_obj, max_triangles: int = 300000, coord_context=None, coord_mode: str = "Local"):
        tris = SectionSet._surface_triangles(src_obj)
        if not tris:
            return None

        if str(coord_mode or "Local") == "World":
            tris = _ct.triangles_world_to_local(
                tris,
                doc_or_obj=(coord_context if coord_context is not None else src_obj),
            )
            if not tris:
                return None

        mt = int(max(1000, int(max_triangles)))
        tris = _ssc.decimate_triangles(tris, mt)

        scale = get_length_scale(getattr(src_obj, "Document", None), default=1.0)
        bucket = 2.0 * scale
        try:
            n = max(1, len(tris))
            xmin, xmax, ymin, ymax = _ct.triangles_bbox_xy(tris)
            xlen = float(xmax - xmin)
            ylen = float(ymax - ymin)
            area = max((1.0 * scale) ** 2, xlen * ylen)
            bucket = max(0.5 * scale, min(20.0 * scale, math.sqrt(area / float(n)) * 2.0))
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
        z0 = _ssc.z_at_xy(float(x), float(y), tris, buckets, bs, wide_indices=wide, max_candidates=None)
        if z0 is not None:
            return z0

        # Fallback for DEM-like meshes with local holes:
        # sample neighboring positions and use nearest available Z.
        step = max(0.2, float(bs))
        dirs = (
            (1.0, 0.0),
            (-1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0),
            (0.7071, 0.7071),
            (0.7071, -0.7071),
            (-0.7071, 0.7071),
            (-0.7071, -0.7071),
        )
        best = None
        best_d2 = None
        for ring in (1, 2, 3):
            r = float(ring) * step
            for dx, dy in dirs:
                qx = float(x) + float(dx) * r
                qy = float(y) + float(dy) * r
                zz = _ssc.z_at_xy(float(qx), float(qy), tris, buckets, bs, wide_indices=wide, max_candidates=None)
                if zz is None:
                    continue
                d2 = float((qx - x) * (qx - x) + (qy - y) * (qy - y))
                if best is None or d2 < best_d2:
                    best = float(zz)
                    best_d2 = d2
            if best is not None:
                return best
        return None

    @staticmethod
    def _solve_daylight_width(edge_p, outward_n, up_z, slope_pct: float, max_w: float, sampler, step: float):
        mw = max(0.0, float(max_w))
        if sampler is None or mw <= 1e-9:
            return mw, False

        st = max(0.2, float(step))
        if st > mw:
            st = mw
        if st <= 1e-12:
            return mw, False
        # Keep runtime bounded even when max width is large or step is tiny.
        max_iter = 5000
        est_iter = int(math.ceil(mw / st)) + 1
        if est_iter > max_iter:
            st = max(st, float(mw) / float(max_iter))

        def f_at(w):
            q = edge_p + outward_n * float(w) + up_z * (-float(w) * float(slope_pct) / 100.0)
            zt = SectionSet._terrain_z_at(sampler, q.x, q.y)
            if zt is None:
                return None
            return float(q.z - zt)

        # Daylight policy:
        # - If a sign-change intersection is found, use that root.
        # - If no intersection exists inside [0, max_w], return max_w with hit=False.
        had_sample = False
        prev_w = None
        prev_f = None
        best_w = None
        best_abs_f = None
        w = 0.0
        while w <= mw + 1e-9:
            fv = f_at(w)
            if fv is not None:
                had_sample = True
                af = abs(float(fv))
                if best_abs_f is None or af < best_abs_f:
                    best_abs_f = af
                    best_w = float(w)
                if prev_f is not None and (prev_f == 0.0 or fv == 0.0 or (prev_f > 0.0 and fv < 0.0) or (prev_f < 0.0 and fv > 0.0)):
                    if prev_w is None:
                        return w, True
                    den = (fv - prev_f)
                    if abs(den) <= 1e-12:
                        return w, True
                    t = -prev_f / den
                    return max(0.0, min(mw, prev_w + (w - prev_w) * t)), True
                prev_w = w
                prev_f = fv
            w += st

        if not had_sample:
            return mw, False
        # If sampled but no explicit sign change was found, use nearest approach.
        if best_w is not None:
            return max(0.0, min(mw, float(best_w))), True
        return mw, False

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
    def build_section_wire(
        source_obj,
        asm_obj,
        station: float,
        prev_n: App.Vector = None,
        terrain_sampler=None,
        use_daylight: bool = False,
    ):
        scale = get_length_scale(getattr(source_obj, "Document", None), default=1.0)
        frame = Centerline3D.frame_at_station(source_obj, float(station), eps=0.1 * scale, prev_n=prev_n)
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
        use_day = bool(use_daylight) and bool(use_ss) and ((lsw > 1e-9) or (rsw > 1e-9))
        day_step = max(0.2 * scale, float(getattr(asm_obj, "DaylightSearchStep", 1.0 * scale)))
        day_max_w = max(0.0, float(getattr(asm_obj, "DaylightMaxSearchWidth", 200.0 * scale)))

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
                try:
                    search_w_l = max(lsw, day_max_w)
                    w_l_day, hit_l = SectionSet._solve_daylight_width(
                        p_l, n, z, lss_eff, search_w_l, terrain_sampler, day_step
                    )
                    w_l = w_l_day if hit_l else lsw
                    w_l = max(0.01 if lsw > 1e-9 else 0.0, min(search_w_l, w_l))
                except Exception:
                    # Fail-safe: never block section creation due to daylight solve failure.
                    w_l = max(0.01 if lsw > 1e-9 else 0.0, lsw)
            else:
                w_l = max(0.01 if lsw > 1e-9 else 0.0, min(lsw, w_l))
            p_lt = p_l + n * w_l + z * (-w_l * lss_eff / 100.0)
            pts = [p_lt] + pts
        if use_ss and rsw > 1e-9:
            w_r = rsw
            if use_day:
                try:
                    search_w_r = max(rsw, day_max_w)
                    w_r_day, hit_r = SectionSet._solve_daylight_width(
                        p_r, -n, z, rss_eff, search_w_r, terrain_sampler, day_step
                    )
                    w_r = w_r_day if hit_r else rsw
                    w_r = max(0.01 if rsw > 1e-9 else 0.0, min(search_w_r, w_r))
                except Exception:
                    # Fail-safe: never block section creation due to daylight solve failure.
                    w_r = max(0.01 if rsw > 1e-9 else 0.0, rsw)
            else:
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
        use_ss = bool(getattr(asm, "UseSideSlopes", False))
        lsw = max(0.0, float(getattr(asm, "LeftSideWidth", 0.0)))
        rsw = max(0.0, float(getattr(asm, "RightSideWidth", 0.0)))
        use_day = bool(getattr(obj, "DaylightAuto", True)) and bool(use_ss) and ((lsw > 1e-9) or (rsw > 1e-9))
        try:
            if use_day:
                tsrc = SectionSet._resolve_terrain_source(obj)
                terrain_found = tsrc is not None
                if tsrc is not None:
                    day_max = int(getattr(asm, "DaylightMaxTriangles", 300000))
                    terrain_mode = str(getattr(obj, "TerrainMeshCoords", "Local") or "Local")
                    # Prefer explicit source declaration when available.
                    src_mode = str(getattr(tsrc, "OutputCoords", "") or "")
                    if src_mode in ("Local", "World"):
                        terrain_mode = src_mode
                    if terrain_mode not in ("Local", "World"):
                        terrain_mode = "Local"
                    terrain_sampler = SectionSet._terrain_sampler(
                        tsrc,
                        max_triangles=day_max,
                        coord_context=obj,
                        coord_mode=terrain_mode,
                    )
        except Exception:
            terrain_sampler = None

        wires = []
        prev_n = None
        for s in stations:
            try:
                w, prev_n = SectionSet.build_section_wire(
                    src,
                    asm,
                    float(s),
                    prev_n=prev_n,
                    terrain_sampler=terrain_sampler,
                    use_daylight=use_day,
                )
            except Exception:
                # Per-station fail-safe: fall back to fixed-width side slopes.
                w, prev_n = SectionSet.build_section_wire(
                    src,
                    asm,
                    float(s),
                    prev_n=prev_n,
                    terrain_sampler=None,
                    use_daylight=False,
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
    def rebuild_child_sections(obj, stations=None, wires=None, station_tags=None):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return

        if stations is None or wires is None:
            stations, wires, _tf, _so = SectionSet.build_section_wires(obj)
        if len(stations) != len(wires):
            raise Exception("Child rebuild failed: stations/wires size mismatch.")
        if station_tags is None or len(station_tags) != len(stations):
            station_tags = SectionSet.resolve_station_tags(obj, stations)

        SectionSet.clear_child_sections(obj)
        children = []
        for i, (s, w) in enumerate(zip(stations, wires)):
            ch = doc.addObject("Part::Feature", "SectionSlice")
            tags = station_tags[i] if i < len(station_tags) else []
            tag_txt = f" [{'/'.join(tags)}]" if tags else ""
            ch.Label = f"STA {float(s):.3f}{tag_txt}"
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
                        tags = SectionSet.resolve_station_tags(obj, stations)
                        SectionSet.rebuild_child_sections(obj, stations=stations, wires=wires, station_tags=tags)
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
            use_day = bool(getattr(obj, "DaylightAuto", True)) and bool(use_ss) and (left_on or right_on)
            if use_day and (not terrain_found):
                obj.Status = "WARN: DaylightAuto=True but no terrain source found. Fixed side widths used."
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
            "TerrainMeshCoords",
            "DaylightAuto",
            "Mode",
            "StartStation",
            "EndStation",
            "Interval",
            "StationText",
            "IncludeAlignmentIPStations",
            "IncludeAlignmentSCCSStations",
            "IncludeStructureStations",
            "StructureStationText",
            "CreateChildSections",
            "AutoRebuildChildren",
            "RebuildNow",
            "ShowSectionWires",
        ):
            try:
                obj.touch()
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)):
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
