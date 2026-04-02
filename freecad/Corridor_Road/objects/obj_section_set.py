# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_section_set.py
import re
import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet as StructureSetSource
from freecad.Corridor_Road.objects.obj_typical_section_template import build_top_profile as _build_typical_top_profile
from freecad.Corridor_Road.objects.obj_assembly_template import _collect_side_bench_rows, _resolve_side_bench_profile
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


def _clamp(value: float, lo: float, hi: float):
    return max(float(lo), min(float(hi), float(value)))


def _resolve_side_bench_segments(total_w: float, side_slope_pct: float, use_bench: bool, bench_drop: float, bench_width: float, bench_slope_pct: float, post_bench_slope_pct: float):
    total = max(0.0, float(total_w))
    side_slope = float(side_slope_pct)
    out = {
        "active": False,
        "pre_width": 0.0,
        "bench_width": 0.0,
        "post_width": total,
        "pre_slope": side_slope,
        "bench_slope": float(bench_slope_pct),
        "post_slope": side_slope,
    }
    if (not bool(use_bench)) or total <= 1e-9:
        return out

    bench_w = max(0.0, float(bench_width))
    if bench_w <= 1e-9:
        return out

    drop = max(0.0, float(bench_drop))
    pre_w = 0.0
    if drop > 1e-9 and abs(side_slope) > 1e-9:
        pre_w = min(total, drop * 100.0 / abs(side_slope))

    remain = max(0.0, total - pre_w)
    bench_w = min(remain, bench_w)
    if bench_w <= 1e-9:
        return out

    post_w = max(0.0, total - pre_w - bench_w)
    post_slope = float(post_bench_slope_pct)
    if post_w > 1e-9 and abs(post_slope) <= 1e-9:
        post_slope = side_slope

    out.update(
        {
            "active": True,
            "pre_width": float(pre_w),
            "bench_width": float(bench_w),
            "post_width": float(post_w),
            "pre_slope": side_slope,
            "bench_slope": float(bench_slope_pct),
            "post_slope": float(post_slope),
        }
    )
    return out


def _profile_segments(profile):
    return list(profile.get("segments", []) or [])


def _append_side_segment_points(points, edge_p: App.Vector, dir_n: App.Vector, z: App.Vector, profile):
    cur = App.Vector(float(edge_p.x), float(edge_p.y), float(edge_p.z))
    out_pts = []
    total_w = 0.0

    for seg in _profile_segments(profile):
        seg_w = float(seg.get("width", 0.0) or 0.0)
        if seg_w <= 1e-9:
            continue
        seg_s = float(seg.get("slope", 0.0) or 0.0)
        cur = cur + dir_n * seg_w + z * (-seg_w * seg_s / 100.0)
        out_pts.append(cur)
        total_w += seg_w

    points.extend(out_pts)
    return cur, float(total_w)


def _point_on_side_segments(edge_p: App.Vector, outward_n: App.Vector, up_z: App.Vector, profile, total_w: float):
    cur = App.Vector(float(edge_p.x), float(edge_p.y), float(edge_p.z))
    rem = max(0.0, float(total_w))

    for seg in _profile_segments(profile):
        seg_w = min(rem, float(seg.get("width", 0.0) or 0.0))
        if seg_w > 1e-9:
            seg_s = float(seg.get("slope", 0.0) or 0.0)
            cur = cur + outward_n * seg_w + up_z * (-seg_w * seg_s / 100.0)
            rem -= seg_w
        if rem <= 1e-9:
            break

    return cur


def _profile_total_width(profile) -> float:
    return float(sum(max(0.0, float(seg.get("width", 0.0) or 0.0)) for seg in _profile_segments(profile)))


def _resolve_daylight_bench_spec(edge_p, outward_n, up_z, profile, sampler, step: float, search_post_w: float, prev_total_w, max_delta: float):
    base_segments = [dict(seg) for seg in _profile_segments(profile)]
    base_total = _profile_total_width({"segments": base_segments})
    total_search = _profile_total_width({"segments": base_segments})
    out = dict(profile)
    work_segments = [dict(seg) for seg in base_segments]
    if work_segments:
        last = dict(work_segments[-1])
        if str(last.get("kind", "") or "") == "slope":
            last["width"] = max(float(last.get("width", 0.0) or 0.0), float(search_post_w))
            work_segments[-1] = last
        else:
            work_segments.append({"kind": "slope", "width": float(search_post_w), "slope": float(last.get("slope", 0.0) or 0.0)})
    total_search = _profile_total_width({"segments": work_segments})
    out["daylightAdjusted"] = False
    out["daylightSkipped"] = False
    out["benchVisible"] = any(str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > 1e-9 for seg in base_segments)
    out["daylightMode"] = "fixed"

    if sampler is None or total_search <= 1e-9:
        out["segments"] = base_segments
        out["bench_count"] = int(sum(1 for seg in base_segments if str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > 1e-9))
        return out, _profile_total_width(out)

    st = max(0.2, float(step))
    if st > total_search:
        st = total_search
    if st <= 1e-12:
        out["segments"] = base_segments
        out["bench_count"] = int(sum(1 for seg in base_segments if str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > 1e-9))
        return out, base_total

    max_iter = 5000
    est_iter = int(math.ceil(total_search / st)) + 1
    if est_iter > max_iter:
        st = max(st, float(total_search) / float(max_iter))

    def f_at(w):
        q = _point_on_side_segments(edge_p, outward_n, up_z, {"segments": work_segments}, float(w))
        zt = SectionSet._terrain_z_at(sampler, q.x, q.y)
        if zt is None:
            return None
        return float(q.z - zt)

    had_sample = False
    prev_w = None
    prev_f = None
    best_w = None
    best_abs_f = None
    hit = False
    resolved_total = total_search
    w = 0.0
    while w <= total_search + 1e-9:
        fv = f_at(w)
        if fv is not None:
            had_sample = True
            af = abs(float(fv))
            if best_abs_f is None or af < best_abs_f:
                best_abs_f = af
                best_w = float(w)
            if prev_f is not None and (prev_f == 0.0 or fv == 0.0 or (prev_f > 0.0 and fv < 0.0) or (prev_f < 0.0 and fv > 0.0)):
                if prev_w is None:
                    resolved_total = float(w)
                else:
                    den = (fv - prev_f)
                    if abs(den) <= 1e-12:
                        resolved_total = float(w)
                    else:
                        t = -prev_f / den
                        resolved_total = max(0.0, min(total_search, prev_w + (w - prev_w) * t))
                hit = True
                break
            prev_w = w
            prev_f = fv
        w += st

    if not hit:
        if not had_sample:
            resolved_total = base_total
        elif best_w is not None:
            resolved_total = float(best_w)
            hit = True
        else:
            resolved_total = base_total

    resolved_total = SectionSet._stabilize_daylight_width(
        resolved_total,
        prev_total_w,
        max_delta,
        0.01 if total_search > 1e-9 else 0.0,
        total_search,
    )

    tol = 1e-6
    kept_segments = []
    rem = max(0.0, float(resolved_total))
    for seg in work_segments:
        base_w = max(0.0, float(seg.get("width", 0.0) or 0.0))
        if base_w <= 1e-9 and rem <= 1e-9:
            kept_segments.append(dict(seg))
            continue
        take = min(rem, base_w)
        row = dict(seg)
        row["width"] = float(max(0.0, take))
        kept_segments.append(row)
        rem -= take
    if len(kept_segments) > len(base_segments):
        kept_segments = kept_segments[: len(base_segments)]
    elif len(kept_segments) < len(base_segments):
        for seg in base_segments[len(kept_segments):]:
            row = dict(seg)
            row["width"] = 0.0
            kept_segments.append(row)

    base_bench_count = int(sum(1 for seg in base_segments if str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > tol))
    visible_bench_count = int(sum(1 for seg in kept_segments if str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > tol))
    out["segments"] = kept_segments
    out["benchVisible"] = bool(visible_bench_count > 0)
    out["bench_count"] = int(visible_bench_count)
    out["daylightSkipped"] = bool(base_bench_count > 0 and visible_bench_count < base_bench_count)
    out["daylightAdjusted"] = bool(hit or abs(_profile_total_width({"segments": kept_segments}) - _profile_total_width({"segments": base_segments})) > tol)
    out["daylightMode"] = "hit" if hit else "search"
    return out, _profile_total_width(out)


def _preserve_bench_point_contract(profile, min_seg: float):
    eps = max(1e-4, float(min_seg))
    out = dict(profile)
    segments = [dict(seg) for seg in _profile_segments(profile)]
    if not segments:
        out["segments"] = [{"kind": "slope", "width": eps, "slope": 0.0}]
        return out
    adjusted = []
    for seg in segments:
        row = dict(seg)
        row["width"] = max(eps, float(seg.get("width", 0.0) or 0.0))
        adjusted.append(row)
    out["segments"] = adjusted
    return out


def _report_row(kind: str, **fields) -> str:
    parts = [str(kind or "").strip() or "row"]
    for key, value in fields.items():
        parts.append(f"{str(key)}={value}")
    return "|".join(parts)


def _parse_report_row(text: str):
    raw = str(text or "").strip()
    if not raw:
        return {}
    parts = [str(p or "").strip() for p in raw.split("|")]
    out = {"kind": parts[0] if parts else "row", "raw": raw}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[str(key or "").strip()] = str(value or "").strip()
    return out


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _typical_edge_anchors(segment_rows):
    anchors = {}
    for row_txt in list(segment_rows or []):
        row = row_txt if isinstance(row_txt, dict) else _parse_report_row(row_txt)
        if str(row.get("kind", "") or "").strip().lower() != "component_segment":
            continue
        if str(row.get("scope", "") or "").strip().lower() != "typical":
            continue
        try:
            station_value = float(row.get("station", 0.0) or 0.0)
        except Exception:
            continue
        side_name = str(row.get("side", "") or "").strip().lower()
        x0 = _safe_float(row.get("x0", 0.0), 0.0)
        x1 = _safe_float(row.get("x1", 0.0), 0.0)
        slot = anchors.setdefault(round(float(station_value), 6), {"left": None, "right": None})
        if side_name in ("left", "center", "both"):
            slot["left"] = x0 if slot["left"] is None else min(float(slot["left"]), x0)
        if side_name in ("right", "center", "both"):
            slot["right"] = x1 if slot["right"] is None else max(float(slot["right"]), x1)
    return anchors


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


def _resolve_structure_source(obj):
    ss = getattr(obj, "StructureSet", None) if hasattr(obj, "StructureSet") else None
    if ss is not None:
        return ss
    doc = getattr(obj, "Document", None)
    prj = _find_project(doc)
    if prj is not None and hasattr(prj, "StructureSet"):
        return getattr(prj, "StructureSet", None)
    return None


def _status_join(head: str, *tokens):
    parts = []
    for tok in list(tokens or []):
        txt = str(tok or "").strip()
        if txt:
            parts.append(txt)
    if not parts:
        return str(head or "").strip()
    base = str(head or "").strip()
    if not base:
        return " | ".join(parts)
    return f"{base} | " + " | ".join(parts)


def _external_shape_total_count(struct_src) -> int:
    if struct_src is None:
        return 0
    try:
        return sum(
            1
            for rec in list(StructureSetSource.records(struct_src) or [])
            if str(rec.get("GeometryMode", "") or "").strip().lower() == "external_shape"
        )
    except Exception:
        return 0


def _external_shape_proxy_count(struct_src) -> int:
    if struct_src is None:
        return 0
    try:
        return int(getattr(struct_src, "ResolvedEarthworkProxyCount", 0) or 0)
    except Exception:
        return 0


def _external_shape_display_count(struct_src) -> int:
    total = int(_external_shape_total_count(struct_src) or 0)
    proxy = int(_external_shape_proxy_count(struct_src) or 0)
    if total <= 0:
        return 0
    return max(0, total - proxy)


def _display_only_status_token(ext_count: int) -> str:
    count = int(ext_count or 0)
    if count <= 0:
        return ""
    return f"displayOnly=external_shape:{count}"


def _earthwork_status_token(struct_src=None, resolved_count: int = 0, ext_count: int = 0, proxy_count: int = 0, overrides_enabled: bool = False) -> str:
    if int(proxy_count or 0) > 0:
        return "earthwork=external_shape_proxy"
    if int(ext_count or 0) > 0:
        return "earthwork=simplified_type_driven"
    if struct_src is not None or int(resolved_count or 0) > 0 or bool(overrides_enabled):
        return "earthwork=simplified_type_driven"
    return "earthwork=full"


def _structure_overlay_offsets(rec):
    side = str(rec.get("Side", "") or "").strip().lower()
    off = float(rec.get("Offset", 0.0) or 0.0)
    width = abs(float(rec.get("Width", 0.0) or 0.0))
    sep = max(abs(off), 0.5 * width, 0.5)
    if side == "left":
        return [off if abs(off) > 1e-9 else sep]
    if side == "right":
        return [off if abs(off) > 1e-9 else -sep]
    if side == "both":
        return [-sep, sep]
    return [off]


def _primary_structure_role(meta) -> str:
    roles = [str(v or "").strip().lower() for v in list(meta.get("StructureRoles", []) or [])]
    for key in ("center", "start", "end", "transition_before", "transition_after", "active"):
        if key in roles:
            return key
    return roles[0] if roles else ""


def _overlay_signed_side_factor(rec) -> float:
    side = str(rec.get("Side", "") or "").strip().lower()
    if side == "left":
        return 1.0
    if side == "right":
        return -1.0
    off = float(rec.get("Offset", 0.0) or 0.0)
    if off < -1e-9:
        return -1.0
    return 1.0


def _overlay_rect_wire(center, nvec, zvec, width: float, height: float):
    half_w = 0.5 * max(1e-6, float(width))
    p1 = center - (nvec * half_w)
    p2 = center + (nvec * half_w)
    p3 = p2 + (zvec * max(1e-6, float(height)))
    p4 = p1 + (zvec * max(1e-6, float(height)))
    return Part.makePolygon([p1, p2, p3, p4, p1])


def _overlay_profile_wire(origin, nvec, zvec, coords_nz):
    pts = []
    for nn, zz in list(coords_nz or []):
        pts.append(origin + (nvec * float(nn)) + (zvec * float(zz)))
    if not pts:
        return None
    if (pts[0] - pts[-1]).Length > 1e-9:
        pts.append(pts[0])
    return Part.makePolygon(pts)


def _overlay_geometry_mode(rec) -> str:
    mode = str(rec.get("GeometryMode", "") or "").strip().lower()
    if mode in ("box", "template"):
        return mode
    if str(rec.get("TemplateName", "") or "").strip():
        return "template"
    return "box"


def _overlay_template_name(rec) -> str:
    name = str(rec.get("TemplateName", "") or "").strip().lower()
    if name:
        return name
    typ = str(rec.get("Type", "") or "").strip().lower()
    if typ == "culvert":
        return "box_culvert"
    if typ == "crossing":
        return "utility_crossing"
    if typ == "retaining_wall":
        return "retaining_wall"
    if typ == "abutment_zone":
        return "abutment_block"
    return ""


def _structure_overlay_label(station: float, meta) -> str:
    types = [str(v or "").strip() for v in list(meta.get("StructureTypes", []) or []) if str(v or "").strip()]
    ids = [str(v or "").strip() for v in list(meta.get("StructureIds", []) or []) if str(v or "").strip()]
    role = _primary_structure_role(meta)

    parts = []
    if types:
        t0 = types[0].replace("_", " ").upper()
        if len(types) > 1:
            t0 = f"{t0}+{len(types)-1}"
        parts.append(t0)
    else:
        parts.append("STRUCTURE")

    if ids:
        i0 = ids[0]
        if len(ids) > 1:
            i0 = f"{i0}+{len(ids)-1}"
        parts.append(i0)

    if role and role != "active":
        parts.append(role.replace("_", " ").upper())

    return f"STA {float(station):.3f} [{' | '.join(parts)}]"


def _slope_sign(value: float, fallback: float = 1.0) -> float:
    v = float(value)
    if v > 1e-9:
        return 1.0
    if v < -1e-9:
        return -1.0
    return 1.0 if float(fallback) >= 0.0 else -1.0


def _structure_side_override_spec(rec, side_key: str, scale: float):
    typ = str(rec.get("Type", "") or "").strip().lower()
    side = str(rec.get("Side", "") or "").strip().lower()
    width = max(0.0, abs(float(rec.get("Width", 0.0) or 0.0)))
    height = max(0.0, abs(float(rec.get("Height", 0.0) or 0.0)))

    applies = False
    if typ in ("culvert", "crossing", "bridge_zone", "abutment_zone"):
        applies = True
    elif side_key == "left" and side in ("left", "both", "center"):
        applies = True
    elif side_key == "right" and side in ("right", "both", "center"):
        applies = True
    if not applies:
        return None

    if typ in ("culvert", "crossing"):
        return {
            "Action": "berm",
            "TargetWidth": max(1.0 * scale, min(4.0 * scale, 0.35 * width + 0.50 * height)),
            "SlopeMode": "flat",
            "DisableDaylight": True,
            "Priority": 20,
        }
    if typ == "retaining_wall":
        return {
            "Action": "wall",
            "TargetWidth": max(0.35 * scale, min(2.0 * scale, 0.15 * width + 0.25 * height)),
            "SlopeMode": "steep",
            "SteepSlopePct": max(250.0, 60.0 * max(1.0, height / max(scale, 1e-9))),
            "DisableDaylight": True,
            "Priority": 30,
        }
    if typ in ("bridge_zone", "abutment_zone"):
        return {
            "Action": "trim",
            "TargetWidth": max(1.0 * scale, min(6.0 * scale, 0.20 * width + 0.50 * height)),
            "SlopeMode": "same",
            "DisableDaylight": True,
            "Priority": 15,
        }
    return {
        "Action": "stub",
        "TargetWidth": max(0.25 * scale, min(2.0 * scale, 0.15 * width + 0.25 * height)),
        "SlopeMode": "flat",
        "DisableDaylight": True,
        "Priority": 10,
    }


def _merge_side_override_spec(current, incoming):
    if incoming is None:
        return current
    if current is None:
        return dict(incoming)
    cur_pri = int(current.get("Priority", 0) or 0)
    inc_pri = int(incoming.get("Priority", 0) or 0)
    if inc_pri > cur_pri:
        return dict(incoming)
    if inc_pri < cur_pri:
        return current
    cur_w = float(current.get("TargetWidth", 0.0) or 0.0)
    inc_w = float(incoming.get("TargetWidth", 0.0) or 0.0)
    if cur_w <= 1e-9:
        return dict(incoming)
    if inc_w > 1e-9 and inc_w < cur_w:
        return dict(incoming)
    return current


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
    if not hasattr(obj, "TypicalSectionTemplate"):
        obj.addProperty("App::PropertyLink", "TypicalSectionTemplate", "Sections", "TypicalSectionTemplate link")
    if not hasattr(obj, "UseTypicalSectionTemplate"):
        obj.addProperty("App::PropertyBool", "UseTypicalSectionTemplate", "Sections", "Use TypicalSectionTemplate as primary top-profile source")
        obj.UseTypicalSectionTemplate = False
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
    if not hasattr(obj, "StructureSet"):
        obj.addProperty("App::PropertyLink", "StructureSet", "Structures", "Linked StructureSet source")
    if not hasattr(obj, "UseStructureSet"):
        obj.addProperty("App::PropertyBool", "UseStructureSet", "Structures", "Use linked StructureSet for structure-driven station merge")
        obj.UseStructureSet = False
    if not hasattr(obj, "IncludeStructureStartEnd"):
        obj.addProperty("App::PropertyBool", "IncludeStructureStartEnd", "Structures", "Include structure start/end stations from StructureSet")
        obj.IncludeStructureStartEnd = True
    if not hasattr(obj, "IncludeStructureCenters"):
        obj.addProperty("App::PropertyBool", "IncludeStructureCenters", "Structures", "Include structure center stations from StructureSet")
        obj.IncludeStructureCenters = True
    if not hasattr(obj, "IncludeStructureTransitionStations"):
        obj.addProperty("App::PropertyBool", "IncludeStructureTransitionStations", "Structures", "Include transition stations before and after structure zones")
        obj.IncludeStructureTransitionStations = True
    if not hasattr(obj, "AutoStructureTransitionDistance"):
        obj.addProperty("App::PropertyBool", "AutoStructureTransitionDistance", "Structures", "Automatically derive transition distance from structure type and size")
        obj.AutoStructureTransitionDistance = True
    if not hasattr(obj, "StructureTransitionDistance"):
        scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
        obj.addProperty("App::PropertyFloat", "StructureTransitionDistance", "Structures", "Transition distance used before and after structure boundaries")
        obj.StructureTransitionDistance = 5.0 * scale
    if not hasattr(obj, "StructureBufferBefore"):
        obj.addProperty("App::PropertyFloat", "StructureBufferBefore", "Structures", "Additional station before structure start")
        obj.StructureBufferBefore = 0.0
    if not hasattr(obj, "StructureBufferAfter"):
        obj.addProperty("App::PropertyFloat", "StructureBufferAfter", "Structures", "Additional station after structure end")
        obj.StructureBufferAfter = 0.0
    if not hasattr(obj, "CreateStructureTaggedChildren"):
        obj.addProperty("App::PropertyBool", "CreateStructureTaggedChildren", "Structures", "Add structure-derived tags to child section labels")
        obj.CreateStructureTaggedChildren = True
    if not hasattr(obj, "ApplyStructureOverrides"):
        obj.addProperty("App::PropertyBool", "ApplyStructureOverrides", "Structures", "Reserved flag for future structure-based section overrides")
        obj.ApplyStructureOverrides = False

    if not hasattr(obj, "StationValues"):
        obj.addProperty("App::PropertyFloatList", "StationValues", "Result", "Resolved stations for sections (m)")
    if not hasattr(obj, "ResolvedStructureCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedStructureCount", "Result", "Count of merged structure-driven stations")
        obj.ResolvedStructureCount = 0
    if not hasattr(obj, "ResolvedStructureTags"):
        obj.addProperty("App::PropertyStringList", "ResolvedStructureTags", "Result", "Resolved structure station summary")
        obj.ResolvedStructureTags = []
    if not hasattr(obj, "SectionSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SectionSchemaVersion", "Result", "Section schema version")
        obj.SectionSchemaVersion = 1
    if not hasattr(obj, "TopProfileSource"):
        obj.addProperty("App::PropertyString", "TopProfileSource", "Result", "Top-profile source summary")
        obj.TopProfileSource = "assembly_simple"
    if not hasattr(obj, "SubassemblySchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SubassemblySchemaVersion", "Result", "Practical subassembly schema version")
        obj.SubassemblySchemaVersion = 0
    if not hasattr(obj, "PracticalSectionMode"):
        obj.addProperty("App::PropertyString", "PracticalSectionMode", "Result", "Practical section mode summary")
        obj.PracticalSectionMode = "simple"
    if not hasattr(obj, "TopProfileEdgeSummary"):
        obj.addProperty("App::PropertyString", "TopProfileEdgeSummary", "Result", "Outermost top-profile edge component summary")
        obj.TopProfileEdgeSummary = "-"
    if not hasattr(obj, "TypicalSectionAdvancedComponentCount"):
        obj.addProperty("App::PropertyInteger", "TypicalSectionAdvancedComponentCount", "Result", "Advanced typical-section component count")
        obj.TypicalSectionAdvancedComponentCount = 0
    if not hasattr(obj, "PavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "PavementLayerCount", "Result", "Typical-section pavement layer count")
        obj.PavementLayerCount = 0
    if not hasattr(obj, "EnabledPavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "EnabledPavementLayerCount", "Result", "Enabled typical-section pavement layer count")
        obj.EnabledPavementLayerCount = 0
    if not hasattr(obj, "PavementTotalThickness"):
        obj.addProperty("App::PropertyFloat", "PavementTotalThickness", "Result", "Typical-section pavement total thickness")
        obj.PavementTotalThickness = 0.0
    if not hasattr(obj, "PavementLayerSummaryRows"):
        obj.addProperty("App::PropertyStringList", "PavementLayerSummaryRows", "Result", "Enabled pavement layer report rows")
        obj.PavementLayerSummaryRows = []
    if not hasattr(obj, "SubassemblyContractRows"):
        obj.addProperty("App::PropertyStringList", "SubassemblyContractRows", "Result", "Resolved subassembly contract rows")
        obj.SubassemblyContractRows = []
    if not hasattr(obj, "SubassemblyValidationRows"):
        obj.addProperty("App::PropertyStringList", "SubassemblyValidationRows", "Result", "Resolved subassembly validation rows")
        obj.SubassemblyValidationRows = []
    if not hasattr(obj, "RoadsideLibraryRows"):
        obj.addProperty("App::PropertyStringList", "RoadsideLibraryRows", "Result", "Detected reusable roadside-library rows")
        obj.RoadsideLibraryRows = []
    if not hasattr(obj, "RoadsideLibrarySummary"):
        obj.addProperty("App::PropertyString", "RoadsideLibrarySummary", "Result", "Detected reusable roadside-library summary")
        obj.RoadsideLibrarySummary = "-"
    if not hasattr(obj, "ReportSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "ReportSchemaVersion", "Result", "Structured report schema version")
        obj.ReportSchemaVersion = 1
    if not hasattr(obj, "SectionComponentSummaryRows"):
        obj.addProperty("App::PropertyStringList", "SectionComponentSummaryRows", "Result", "Structured section-component summary rows")
        obj.SectionComponentSummaryRows = []
    if not hasattr(obj, "SectionComponentSegmentRows"):
        obj.addProperty("App::PropertyStringList", "SectionComponentSegmentRows", "Result", "Station-specific section-component segment rows")
        obj.SectionComponentSegmentRows = []
    if not hasattr(obj, "PavementScheduleRows"):
        obj.addProperty("App::PropertyStringList", "PavementScheduleRows", "Result", "Structured pavement schedule rows")
        obj.PavementScheduleRows = []
    if not hasattr(obj, "StructureInteractionSummaryRows"):
        obj.addProperty("App::PropertyStringList", "StructureInteractionSummaryRows", "Result", "Structured structure-interaction summary rows")
        obj.StructureInteractionSummaryRows = []
    if not hasattr(obj, "ExportSummaryRows"):
        obj.addProperty("App::PropertyStringList", "ExportSummaryRows", "Result", "Structured export-ready summary rows")
        obj.ExportSummaryRows = []
    if not hasattr(obj, "BenchAppliedSectionCount"):
        obj.addProperty("App::PropertyInteger", "BenchAppliedSectionCount", "Result", "Count of sections using bench-expanded side slopes")
        obj.BenchAppliedSectionCount = 0
    if not hasattr(obj, "BenchSummary"):
        obj.addProperty("App::PropertyString", "BenchSummary", "Result", "Resolved side-bench usage summary")
        obj.BenchSummary = "-"
    if not hasattr(obj, "BenchSummaryRows"):
        obj.addProperty("App::PropertyStringList", "BenchSummaryRows", "Result", "Structured side-bench summary rows")
        obj.BenchSummaryRows = []
    if not hasattr(obj, "BenchDaylightAdjustedSectionCount"):
        obj.addProperty("App::PropertyInteger", "BenchDaylightAdjustedSectionCount", "Result", "Count of bench-enabled sections adjusted by daylight")
        obj.BenchDaylightAdjustedSectionCount = 0
    if not hasattr(obj, "BenchDaylightSkippedSectionCount"):
        obj.addProperty("App::PropertyInteger", "BenchDaylightSkippedSectionCount", "Result", "Count of bench-enabled sections where terrain hit before the bench")
        obj.BenchDaylightSkippedSectionCount = 0
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
    def _resolve_structure_station_items(obj, total: float, mode: str = "", s0: float = None, s1: float = None):
        items = []
        source_kind = ""
        source_obj = None

        if bool(getattr(obj, "UseStructureSet", False)):
            ss = _resolve_structure_source(obj)
            if ss is not None:
                source_obj = ss
                source_kind = "structure_set"
                items = StructureSetSource.structure_key_station_items(
                    ss,
                    include_start_end=bool(getattr(obj, "IncludeStructureStartEnd", True)),
                    include_centers=bool(getattr(obj, "IncludeStructureCenters", True)),
                    include_transition=bool(getattr(obj, "IncludeStructureTransitionStations", True)),
                    auto_transition=bool(getattr(obj, "AutoStructureTransitionDistance", True)),
                    transition=float(getattr(obj, "StructureTransitionDistance", 0.0) or 0.0),
                )

        out = []
        lo = None if s0 is None else float(min(s0, s1))
        hi = None if s1 is None else float(max(s0, s1))
        for it in items:
            st = _clamp(float(it.get("station", 0.0) or 0.0), 0.0, float(total))
            if str(mode or "") == "Range" and lo is not None and hi is not None:
                if st < lo - 1e-9 or st > hi + 1e-9:
                    continue
            rec = dict(it)
            rec["station"] = st
            out.append(rec)
        return out, source_kind, source_obj

    @staticmethod
    def _resolved_structure_summary(items):
        if not items:
            return 0, []
        rows = []
        uniq = set()
        for it in sorted(items, key=lambda x: float(x.get("station", 0.0))):
            sta = float(it.get("station", 0.0))
            tag = str(it.get("tag", "") or "")
            ids = ",".join([str(v) for v in list(it.get("ids", []) or []) if str(v)])
            if tag:
                txt = f"{sta:.3f}:{tag}"
            else:
                txt = f"{sta:.3f}:TRANSITION"
            if ids:
                txt += f" [{ids}]"
            if txt not in uniq:
                rows.append(txt)
                uniq.add(txt)
        count = len(_unique_sorted([float(it.get("station", 0.0)) for it in items]))
        return int(count), rows

    @staticmethod
    def _structure_context_at_station(obj, station: float):
        ctx = {
            "HasStructure": False,
            "ActiveRecords": [],
            "SuppressSideSlopes": False,
            "SuppressDaylight": False,
            "OverlayRecords": [],
            "LeftAction": "keep",
            "RightAction": "keep",
            "LeftDisableDaylight": False,
            "RightDisableDaylight": False,
            "BoundaryRoles": [],
            "IsBoundaryStation": False,
            "LeftOverrideSpec": None,
            "RightOverrideSpec": None,
        }
        if not bool(getattr(obj, "UseStructureSet", False)):
            return ctx
        ss = _resolve_structure_source(obj)
        if ss is None:
            return ctx

        src = getattr(obj, "SourceCenterlineDisplay", None)
        aln = getattr(src, "Alignment", None) if src is not None else None
        total = float(getattr(getattr(aln, "Shape", None), "Length", 0.0) or 0.0)
        tol = max(1e-4, 1e-6 * max(total, 1.0))
        try:
            active = StructureSetSource.active_records_at_station(ss, float(station), tol=tol)
        except Exception:
            active = []
        if not active:
            return ctx

        resolved_active = []
        for rec in list(active or []):
            try:
                resolved = StructureSetSource.resolve_profile_at_station(ss, rec, float(station))
                resolved_active.append(resolved if resolved else rec)
            except Exception:
                resolved_active.append(rec)

        ctx["HasStructure"] = True
        ctx["ActiveRecords"] = list(resolved_active)
        ctx["OverlayRecords"] = list(resolved_active)
        try:
            station_items, _sk, _so = SectionSet._resolve_structure_station_items(
                obj,
                total,
                mode=str(getattr(obj, "Mode", "Range") or "Range"),
                s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                s1=float(getattr(obj, "EndStation", total) or total),
            )
        except Exception:
            station_items = []
        boundary_roles = []
        for it in station_items:
            if abs(float(it.get("station", 0.0) or 0.0) - float(station)) > tol:
                continue
            role = str(it.get("role", "") or "").strip().lower()
            if role and role not in boundary_roles:
                boundary_roles.append(role)
        ctx["BoundaryRoles"] = list(boundary_roles)
        ctx["IsBoundaryStation"] = any(r in ("start", "end", "transition_before", "transition_after") for r in boundary_roles)

        if ctx["IsBoundaryStation"]:
            return ctx

        scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
        for rec in resolved_active:
            mode = str(rec.get("BehaviorMode", "") or "").strip().lower()
            if mode not in ("section_overlay", "assembly_override"):
                continue
            left_spec = _structure_side_override_spec(rec, "left", scale)
            right_spec = _structure_side_override_spec(rec, "right", scale)
            ctx["LeftOverrideSpec"] = _merge_side_override_spec(ctx.get("LeftOverrideSpec"), left_spec)
            ctx["RightOverrideSpec"] = _merge_side_override_spec(ctx.get("RightOverrideSpec"), right_spec)

        if ctx["LeftOverrideSpec"] is not None:
            ctx["LeftAction"] = str(ctx["LeftOverrideSpec"].get("Action", "keep") or "keep").strip().lower()
            ctx["LeftDisableDaylight"] = bool(ctx["LeftOverrideSpec"].get("DisableDaylight", False))
        if ctx["RightOverrideSpec"] is not None:
            ctx["RightAction"] = str(ctx["RightOverrideSpec"].get("Action", "keep") or "keep").strip().lower()
            ctx["RightDisableDaylight"] = bool(ctx["RightOverrideSpec"].get("DisableDaylight", False))

        if ctx["LeftAction"] == "stub" and ctx["RightAction"] == "stub":
            ctx["SuppressSideSlopes"] = True
        if ctx["LeftDisableDaylight"] and ctx["RightDisableDaylight"]:
            ctx["SuppressDaylight"] = True
        return ctx

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

        try:
            struct_items, _skind, _sobj = SectionSet._resolve_structure_station_items(
                obj,
                total,
                mode=mode,
                s0=s0,
                s1=s1,
            )
            vals.extend([float(it.get("station", 0.0)) for it in struct_items])
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
        struct_items = []
        struct_kind = ""
        struct_obj = None
        try:
            struct_items, struct_kind, struct_obj = SectionSet._resolve_structure_station_items(
                obj,
                float(aln.Shape.Length),
                mode=str(getattr(obj, "Mode", "Range") or "Range"),
                s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                s1=float(getattr(obj, "EndStation", float(aln.Shape.Length)) or float(aln.Shape.Length)),
            )
        except Exception:
            struct_items = []
        if struct_items and bool(getattr(obj, "CreateStructureTaggedChildren", True)):
            by_tag = {}
            for it in struct_items:
                tag = str(it.get("tag", "") or "")
                if not tag:
                    continue
                by_tag.setdefault(tag, []).append(float(it.get("station", 0.0)))
            for tag, keys in by_tag.items():
                key_sets.append((tag, _unique_sorted(keys)))

        if not key_sets:
            key_sets = []

        for i, s in enumerate(stations):
            ss = float(s)
            tags = []
            for tag, keys in key_sets:
                if any(abs(ss - float(k)) <= tol for k in keys):
                    tags.append(tag)
            if bool(getattr(obj, "CreateStructureTaggedChildren", True)) and struct_kind == "structure_set" and struct_obj is not None:
                try:
                    active = StructureSetSource.active_records_at_station(struct_obj, ss, tol=tol)
                    if active:
                        tags.append("STR")
                except Exception:
                    pass
            if tags:
                dedup = []
                for tg in tags:
                    if tg not in dedup:
                        dedup.append(tg)
                tags = dedup
            out[i] = tags
        return out

    @staticmethod
    def resolve_structure_metadata(obj, stations):
        out = []
        if not stations:
            return out

        src = getattr(obj, "SourceCenterlineDisplay", None)
        aln = getattr(src, "Alignment", None) if src is not None else None
        total = float(getattr(getattr(aln, "Shape", None), "Length", 0.0) or 0.0)
        tol = max(1e-4, 1e-6 * max(total, 1.0))

        struct_items = []
        struct_kind = ""
        struct_obj = None
        try:
            struct_items, struct_kind, struct_obj = SectionSet._resolve_structure_station_items(
                obj,
                total,
                mode=str(getattr(obj, "Mode", "Range") or "Range"),
                s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                s1=float(getattr(obj, "EndStation", total) or total),
            )
        except Exception:
            struct_items = []

        for s in stations:
            ss = float(s)
            ids = []
            types = []
            roles = []

            if struct_kind == "structure_set" and struct_obj is not None:
                try:
                    active = StructureSetSource.active_records_at_station(struct_obj, ss, tol=tol)
                except Exception:
                    active = []
                for rec in active:
                    rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                    typ = str(rec.get("Type", "") or "").strip()
                    if rid and rid not in ids:
                        ids.append(rid)
                    if typ and typ not in types:
                        types.append(typ)
                if active:
                    roles.append("active")

            for it in struct_items:
                if abs(ss - float(it.get("station", 0.0) or 0.0)) > tol:
                    continue
                role = str(it.get("role", "") or "").strip()
                if role and role not in roles:
                    roles.append(role)
                for rid in list(it.get("ids", []) or []):
                    rid_txt = str(rid or "").strip()
                    if rid_txt and rid_txt not in ids:
                        ids.append(rid_txt)
                for typ in list(it.get("types", []) or []):
                    typ_txt = str(typ or "").strip()
                    if typ_txt and typ_txt not in types:
                        types.append(typ_txt)

            has_structure = bool(ids or roles or types)
            role_summary = ",".join(roles)
            type_summary = ",".join(types)
            id_summary = ",".join(ids)
            out.append(
                {
                    "HasStructure": has_structure,
                    "StructureIds": ids,
                    "StructureTypes": types,
                    "StructureRoles": roles,
                    "StructureRole": role_summary,
                    "StructureSummary": f"{id_summary} | {type_summary} | {role_summary}".strip(" |"),
                }
            )
        return out

    @staticmethod
    def _apply_child_structure_visual(ch, meta):
        try:
            vobj = getattr(ch, "ViewObject", None)
            if vobj is None:
                return
            has_structure = bool(meta.get("HasStructure", False))
            roles = list(meta.get("StructureRoles", []) or [])
            if not has_structure:
                return
            color = (0.95, 0.70, 0.18)
            line_width = 3
            if "center" in roles:
                color = (0.86, 0.28, 0.16)
                line_width = 4
            elif "start" in roles or "end" in roles:
                color = (0.95, 0.52, 0.14)
                line_width = 4
            elif "transition_before" in roles or "transition_after" in roles:
                color = (0.92, 0.82, 0.38)
                line_width = 3
            vobj.LineColor = color
            vobj.PointColor = color
            vobj.ShapeColor = color
            vobj.LineWidth = line_width
            vobj.DisplayMode = "Wireframe"
        except Exception:
            pass

    @staticmethod
    def _record_overlay_wire(section_obj, station: float, rec):
        src = getattr(section_obj, "SourceCenterlineDisplay", None)
        if src is None:
            return None
        struct_src = _resolve_structure_source(section_obj)
        try:
            if struct_src is not None and str(rec.get("Id", "") or "").strip():
                resolved = StructureSetSource.resolve_profile_at_station(struct_src, rec, float(station))
                if resolved:
                    rec = resolved
        except Exception:
            pass
        scale = get_length_scale(getattr(section_obj, "Document", None), default=1.0)
        frame = Centerline3D.frame_at_station(src, float(station), eps=0.1 * scale, prev_n=None)
        p = frame["point"]
        n = frame["N"]
        z = frame["Z"]

        width = max(0.2 * scale, abs(float(rec.get("Width", 0.0) or 0.0)))
        height = max(0.2 * scale, abs(float(rec.get("Height", 0.0) or 0.0)))
        bottom = float(rec.get("BottomElevation", 0.0) or 0.0)
        cover = abs(float(rec.get("Cover", 0.0) or 0.0))
        z_ref = float(getattr(p, "z", 0.0) or 0.0)
        if abs(bottom) > 1e-9:
            z0 = bottom
        elif cover > 1e-9:
            z0 = z_ref - cover - height
        else:
            z0 = z_ref

        wires = []
        geom_mode = _overlay_geometry_mode(rec)
        template_name = _overlay_template_name(rec)
        for off in _structure_overlay_offsets(rec):
            c = App.Vector(float(p.x), float(p.y), float(z0)) + (n * float(off))
            if geom_mode == "template" and template_name == "box_culvert":
                wall = max(0.10 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
                cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
                top_cap = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                total_h = max(0.2 * scale, height + top_cap)
                wires.append(_overlay_rect_wire(c, n, z, width, total_h))
                inner_h = total_h - (2.0 * wall)
                clear_w = width - (2.0 * wall)
                if inner_h > 0.05 * scale and clear_w > 0.05 * scale:
                    gap = wall
                    total_gap = max(0.0, float(cells - 1)) * gap
                    cell_w = (clear_w - total_gap) / float(cells)
                    if cell_w > 0.05 * scale:
                        inner_center = App.Vector(float(c.x), float(c.y), float(z0) + wall)
                        start_center = -0.5 * clear_w + 0.5 * cell_w
                        for i in range(cells):
                            shift = start_center + (float(i) * (cell_w + gap))
                            cell_center = inner_center + (n * shift)
                            wires.append(_overlay_rect_wire(cell_center, n, z, cell_w, inner_h))
            elif geom_mode == "template" and template_name == "utility_crossing":
                wall = max(0.08 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
                cells = max(1, int(round(float(rec.get("CellCount", 1) or 1))))
                top_cap = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                total_h = max(0.2 * scale, height + top_cap)
                wires.append(_overlay_rect_wire(c, n, z, width, total_h))
                clear_w = width - (2.0 * wall)
                duct_h = max(0.10 * scale, min(0.45 * total_h, total_h - (2.0 * wall)))
                if clear_w > 0.05 * scale and duct_h > 0.05 * scale:
                    gap = max(0.10 * scale, 0.60 * wall)
                    total_gap = max(0.0, float(cells - 1)) * gap
                    duct_w = (clear_w - total_gap) / float(cells)
                    if duct_w > 0.05 * scale:
                        z_clear_bottom = max(wall, 0.28 * total_h)
                        z_clear_top = z_clear_bottom + duct_h
                        if z_clear_top >= total_h - wall:
                            z_clear_bottom = max(wall, total_h - wall - duct_h)
                        inner_center = App.Vector(float(c.x), float(c.y), float(z0) + z_clear_bottom)
                        start_center = -0.5 * clear_w + 0.5 * duct_w
                        for i in range(cells):
                            shift = start_center + (float(i) * (duct_w + gap))
                            duct_center = inner_center + (n * shift)
                            wires.append(_overlay_rect_wire(duct_center, n, z, duct_w, duct_h))
            elif geom_mode == "template" and template_name == "retaining_wall":
                wall = max(0.10 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)))
                footing_w = max(wall * 2.0, abs(float(rec.get("FootingWidth", 0.0) or 0.0)), max(width, wall * 3.0))
                footing_h = max(0.10 * scale, abs(float(rec.get("FootingThickness", 0.0) or 0.0)))
                cap_h = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                sign = _overlay_signed_side_factor(rec)
                heel = footing_w * 0.65
                toe = footing_w - heel
                top_wall = max(0.08 * scale, wall * 0.70)
                total_h = footing_h + max(0.2 * scale, height)
                coords = [
                    (-sign * toe, 0.0),
                    (sign * heel, 0.0),
                    (sign * heel, footing_h),
                    (sign * (0.5 * wall), footing_h),
                    (sign * (0.5 * top_wall), total_h),
                    (-sign * (0.5 * top_wall), total_h),
                    (-sign * (0.5 * wall), footing_h),
                    (-sign * toe, footing_h),
                ]
                pw = _overlay_profile_wire(App.Vector(float(c.x), float(c.y), float(z0)), n, z, coords)
                if pw is not None:
                    wires.append(pw)
                if cap_h > 1e-9:
                    cap_center = App.Vector(float(c.x), float(c.y), float(z0) + total_h)
                    cap_center = cap_center + (n * (sign * 0.10 * wall))
                    wires.append(_overlay_rect_wire(cap_center, n, z, max(top_wall * 1.8, wall + 0.20 * scale), cap_h))
            elif geom_mode == "template" and template_name == "abutment_block":
                wall = max(0.20 * scale, abs(float(rec.get("WallThickness", 0.0) or 0.0)), max(0.20 * scale, 0.35 * height))
                footing_h = max(0.20 * scale, abs(float(rec.get("FootingThickness", 0.0) or 0.0)), max(0.20 * scale, 0.18 * height))
                footing_w = max(abs(float(rec.get("FootingWidth", 0.0) or 0.0)), width, wall * 2.5)
                cap_h = max(0.0, abs(float(rec.get("CapHeight", 0.0) or 0.0)))
                stem_w = max(wall * 1.4, min(width * 0.55, footing_w * 0.60))
                seat_w = max(stem_w * 0.55, wall * 1.4)
                total_h = footing_h + max(0.2 * scale, height)
                seat_h0 = footing_h + max(0.30 * scale, 0.60 * height)
                coords = [
                    (-0.5 * footing_w, 0.0),
                    (0.5 * footing_w, 0.0),
                    (0.5 * footing_w, footing_h),
                    (0.5 * stem_w, footing_h),
                    (0.5 * stem_w, seat_h0),
                    (0.5 * seat_w, total_h),
                    (-0.5 * seat_w, total_h),
                    (-0.5 * stem_w, seat_h0),
                    (-0.5 * stem_w, footing_h),
                    (-0.5 * footing_w, footing_h),
                ]
                pw = _overlay_profile_wire(App.Vector(float(c.x), float(c.y), float(z0)), n, z, coords)
                if pw is not None:
                    wires.append(pw)
                if cap_h > 1e-9:
                    cap_center = App.Vector(float(c.x), float(c.y), float(z0) + total_h)
                    wires.append(_overlay_rect_wire(cap_center, n, z, max(seat_w * 1.1, seat_w + 0.20 * scale), cap_h))
            else:
                wires.append(_overlay_rect_wire(c, n, z, width, height))
        if not wires:
            return None
        if len(wires) == 1:
            return wires[0]
        try:
            return Part.Compound(wires)
        except Exception:
            return wires[0]

    @staticmethod
    def _build_child_structure_overlay(section_obj, station: float, meta):
        if not bool(meta.get("HasStructure", False)):
            return None
        if not bool(getattr(section_obj, "CreateStructureTaggedChildren", True)):
            return None
        ctx = SectionSet._structure_context_at_station(section_obj, float(station))
        recs = list(ctx.get("OverlayRecords", []) or [])
        if not recs:
            return None
        overlays = []
        for rec in recs:
            try:
                ow = SectionSet._record_overlay_wire(section_obj, float(station), rec)
                if ow is not None and not ow.isNull():
                    overlays.append(ow)
            except Exception:
                pass
        if not overlays:
            return None
        if len(overlays) == 1:
            return overlays[0]
        try:
            return Part.Compound(overlays)
        except Exception:
            return overlays[0]

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
    def _resolved_terrain_coord_mode(obj, terrain_source=None) -> str:
        terrain_mode = str(getattr(obj, "TerrainMeshCoords", "Local") or "Local")
        tsrc = terrain_source if terrain_source is not None else SectionSet._resolve_terrain_source(obj)
        src_mode = str(getattr(tsrc, "OutputCoords", "") or "")
        if src_mode in ("Local", "World"):
            terrain_mode = src_mode
        if terrain_mode not in ("Local", "World"):
            terrain_mode = "Local"
        return str(terrain_mode)

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
    def _slope_component_type(slope_pct: float):
        slope_pct = float(slope_pct or 0.0)
        if slope_pct < -1e-9:
            return "cut_slope"
        if slope_pct > 1e-9:
            return "fill_slope"
        return "side_slope"

    @staticmethod
    def _assembly_station_side_slope_types(obj, station: float, prev_n=None, terrain_sampler=None, use_daylight: bool = False):
        asm = getattr(obj, "AssemblyTemplate", None)
        src = getattr(obj, "SourceCenterlineDisplay", None)
        if asm is None:
            return {"left": "side_slope", "right": "side_slope"}, prev_n

        lw = max(0.0, float(getattr(asm, "LeftWidth", 0.0) or 0.0))
        rw = max(0.0, float(getattr(asm, "RightWidth", 0.0) or 0.0))
        ls = float(getattr(asm, "LeftSlopePct", 0.0) or 0.0)
        rs = float(getattr(asm, "RightSlopePct", 0.0) or 0.0)
        lsw = max(0.0, float(getattr(asm, "LeftSideWidth", 0.0) or 0.0))
        rsw = max(0.0, float(getattr(asm, "RightSideWidth", 0.0) or 0.0))
        lss = float(getattr(asm, "LeftSideSlopePct", 0.0) or 0.0)
        rss = float(getattr(asm, "RightSideSlopePct", 0.0) or 0.0)

        resolved = {
            "left": SectionSet._slope_component_type(lss),
            "right": SectionSet._slope_component_type(rss),
        }
        if src is None:
            return resolved, prev_n

        scale = get_length_scale(getattr(src, "Document", None), default=1.0)
        frame = Centerline3D.frame_at_station(src, float(station), eps=0.1 * scale, prev_n=prev_n)
        p = frame["point"]
        n = frame["N"]
        z = frame["Z"]

        if bool(use_daylight) and lsw > 1e-9:
            p_l = p + n * lw + z * (-lw * ls / 100.0)
            resolved["left"] = SectionSet._slope_component_type(
                SectionSet._daylight_signed_slope(p_l, lss, terrain_sampler)
            )
        if bool(use_daylight) and rsw > 1e-9:
            p_r = p - n * rw + z * (-rw * rs / 100.0)
            resolved["right"] = SectionSet._slope_component_type(
                SectionSet._daylight_signed_slope(p_r, rss, terrain_sampler)
            )
        return resolved, n

    @staticmethod
    def _stabilize_daylight_width(target_w: float, prev_w, max_delta: float, min_w: float, max_w: float):
        w = _clamp(float(target_w), float(min_w), float(max_w))
        if prev_w is None:
            return w
        md = max(0.0, float(max_delta))
        if md <= 1e-9:
            return w
        lo = max(float(min_w), float(prev_w) - md)
        hi = min(float(max_w), float(prev_w) + md)
        return _clamp(w, lo, hi)

    @staticmethod
    def build_section_wire(
        source_obj,
        asm_obj,
        station: float,
        prev_n: App.Vector = None,
        prev_day_widths=None,
        terrain_sampler=None,
        use_daylight: bool = False,
        structure_context=None,
        apply_structure_overrides: bool = False,
        typical_section_obj=None,
        use_typical_section: bool = False,
    ):
        scale = get_length_scale(getattr(source_obj, "Document", None), default=1.0)
        stub_side_w = max(0.01, 0.01 * scale)
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
        left_has_side = bool(use_ss) and lsw > 1e-9
        right_has_side = bool(use_ss) and rsw > 1e-9
        left_action = "keep"
        right_action = "keep"
        left_spec = None
        right_spec = None
        use_day_left = bool(use_day and left_has_side)
        use_day_right = bool(use_day and right_has_side)
        use_left_bench = bool(getattr(asm_obj, "UseLeftBench", False)) and left_has_side
        use_right_bench = bool(getattr(asm_obj, "UseRightBench", False)) and right_has_side
        if bool(apply_structure_overrides) and structure_context is not None:
            left_action = str(structure_context.get("LeftAction", "keep") or "keep").strip().lower()
            right_action = str(structure_context.get("RightAction", "keep") or "keep").strip().lower()
            left_spec = structure_context.get("LeftOverrideSpec")
            right_spec = structure_context.get("RightOverrideSpec")
            if bool(structure_context.get("SuppressSideSlopes", False)):
                # Preserve the section point contract for loft consumers by keeping
                # side-slope vertices present as short horizontal stubs.
                use_ss = bool(left_has_side or right_has_side)
                if left_has_side:
                    lsw = min(lsw, stub_side_w)
                    lss = 0.0
                else:
                    lsw = 0.0
                if right_has_side:
                    rsw = min(rsw, stub_side_w)
                    rss = 0.0
                else:
                    rsw = 0.0
            if bool(structure_context.get("SuppressDaylight", False)):
                use_day_left = False
                use_day_right = False
            if left_action == "stub" and left_has_side:
                lsw = min(lsw, stub_side_w)
                lss = 0.0
                use_day_left = False
                use_ss = True
            if right_action == "stub" and right_has_side:
                rsw = min(rsw, stub_side_w)
                rss = 0.0
                use_day_right = False
                use_ss = True
            if bool(structure_context.get("LeftDisableDaylight", False)):
                use_day_left = False
            if bool(structure_context.get("RightDisableDaylight", False)):
                use_day_right = False
            if left_action != "keep" or bool(structure_context.get("SuppressSideSlopes", False)):
                use_left_bench = False
            if right_action != "keep" or bool(structure_context.get("SuppressSideSlopes", False)):
                use_right_bench = False

        def _apply_side_override(base_w, base_s, has_side, action, spec, use_day_side):
            if (not has_side) or action == "keep":
                return base_w, base_s, use_day_side

            target_w = 0.0
            slope_mode = "same"
            steep_slope = 0.0
            if spec is not None:
                try:
                    target_w = float(spec.get("TargetWidth", 0.0) or 0.0)
                except Exception:
                    target_w = 0.0
                slope_mode = str(spec.get("SlopeMode", "same") or "same").strip().lower()
                try:
                    steep_slope = float(spec.get("SteepSlopePct", 0.0) or 0.0)
                except Exception:
                    steep_slope = 0.0

            resolved_w = float(base_w)
            resolved_s = float(base_s)
            sign = _slope_sign(base_s, fallback=1.0)

            if action == "stub":
                resolved_w = min(resolved_w, max(stub_side_w, target_w if target_w > 1e-9 else stub_side_w))
                resolved_s = 0.0
                use_day_side = False
            elif action in ("bench", "berm"):
                target = max(1.0 * scale, target_w if target_w > 1e-9 else max(stub_side_w, 0.20 * resolved_w))
                resolved_w = min(resolved_w, target) if resolved_w > 1e-9 else target
                resolved_s = 0.0
                use_day_side = False
            elif action == "trim":
                target = max(stub_side_w, target_w if target_w > 1e-9 else max(0.50 * scale, 0.35 * resolved_w))
                resolved_w = min(resolved_w, target) if resolved_w > 1e-9 else target
                resolved_s = 0.0 if slope_mode == "flat" else float(base_s)
                use_day_side = False
            elif action == "wall":
                target = max(0.20 * scale, target_w if target_w > 1e-9 else max(0.35 * scale, 0.15 * resolved_w))
                resolved_w = min(resolved_w, target) if resolved_w > 1e-9 else target
                steep = max(abs(steep_slope), abs(float(base_s)), 250.0)
                resolved_s = sign * steep
                use_day_side = False

            return resolved_w, resolved_s, use_day_side

        if bool(apply_structure_overrides) and structure_context is not None:
            lsw, lss, use_day_left = _apply_side_override(lsw, lss, left_has_side, left_action, left_spec, use_day_left)
            rsw, rss, use_day_right = _apply_side_override(rsw, rss, right_has_side, right_action, right_spec, use_day_right)
        left_has_side = bool(use_ss) and lsw > 1e-9
        right_has_side = bool(use_ss) and rsw > 1e-9
        use_left_bench = bool(use_left_bench) and left_has_side
        use_right_bench = bool(use_right_bench) and right_has_side
        left_bench_rows = _collect_side_bench_rows(
            use_left_bench,
            float(getattr(asm_obj, "LeftBenchDrop", 0.0) or 0.0),
            float(getattr(asm_obj, "LeftBenchWidth", 0.0) or 0.0),
            float(getattr(asm_obj, "LeftBenchSlopePct", 0.0) or 0.0),
            float(getattr(asm_obj, "LeftPostBenchSlopePct", lss) or lss),
            list(getattr(asm_obj, "LeftBenchRows", []) or []),
        )
        right_bench_rows = _collect_side_bench_rows(
            use_right_bench,
            float(getattr(asm_obj, "RightBenchDrop", 0.0) or 0.0),
            float(getattr(asm_obj, "RightBenchWidth", 0.0) or 0.0),
            float(getattr(asm_obj, "RightBenchSlopePct", 0.0) or 0.0),
            float(getattr(asm_obj, "RightPostBenchSlopePct", rss) or rss),
            list(getattr(asm_obj, "RightBenchRows", []) or []),
        )
        left_bench = _resolve_side_bench_profile(lsw, lss, left_bench_rows)
        right_bench = _resolve_side_bench_profile(rsw, rss, right_bench_rows)
        day_step = max(0.2 * scale, float(getattr(asm_obj, "DaylightSearchStep", 1.0 * scale)))
        day_max_w = max(0.0, float(getattr(asm_obj, "DaylightMaxSearchWidth", 200.0 * scale)))
        day_max_delta = max(0.0, float(getattr(asm_obj, "DaylightMaxWidthDelta", 0.0)))
        prev_left_w = None if prev_day_widths is None else prev_day_widths.get("left")
        prev_right_w = None if prev_day_widths is None else prev_day_widths.get("right")
        prev_left_post_w = None if prev_day_widths is None else prev_day_widths.get("left_post")
        prev_right_post_w = None if prev_day_widths is None else prev_day_widths.get("right_post")

        top_pts = None
        p_l = None
        p_r = None
        if bool(use_typical_section) and typical_section_obj is not None:
            try:
                local_pts = list(_build_typical_top_profile(typical_section_obj) or [])
                if len(local_pts) >= 2:
                    top_pts = [p + n * float(lp.x) + z * float(lp.y) for lp in local_pts]
                    p_l = top_pts[0]
                    p_r = top_pts[-1]
            except Exception:
                top_pts = None
                p_l = None
                p_r = None

        if top_pts is None:
            dz_l = -lw * ls / 100.0
            dz_r = -rw * rs / 100.0
            p_l = p + n * lw + z * dz_l
            p_r = p - n * rw + z * dz_r
            top_pts = [p_l, p, p_r]

        lss_eff = float(lss)
        rss_eff = float(rss)
        if use_day_left:
            lss_eff = SectionSet._daylight_signed_slope(p_l, lss, terrain_sampler)
        if use_day_right:
            rss_eff = SectionSet._daylight_signed_slope(p_r, rss, terrain_sampler)

        pts = list(top_pts)
        resolved_left_w = None
        resolved_right_w = None
        resolved_left_post_w = None
        resolved_right_post_w = None
        bench_left_applied = False
        bench_right_applied = False
        bench_left_adjusted = False
        bench_right_adjusted = False
        bench_left_skipped = False
        bench_right_skipped = False
        if use_ss and lsw > 1e-9:
            if bool(left_bench.get("active", False)):
                spec_l = {"segments": [dict(seg) for seg in _profile_segments(left_bench)], "active": True}
                left_visible_bench_count = int(
                    sum(
                        1
                        for seg in _profile_segments(spec_l)
                        if str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > 1e-9
                    )
                )
                spec_l["bench_count"] = int(left_visible_bench_count)
                spec_l["benchVisible"] = bool(left_visible_bench_count > 0)
                spec_l["daylightAdjusted"] = False
                spec_l["daylightSkipped"] = False
                if use_day_left:
                    segs = []
                    for seg in _profile_segments(spec_l):
                        row = dict(seg)
                        if str(row.get("kind", "") or "") == "slope":
                            row["slope"] = SectionSet._daylight_signed_slope(p_l, float(row.get("slope", 0.0) or 0.0), terrain_sampler)
                        segs.append(row)
                    spec_l["segments"] = segs
                if use_day_left and _profile_total_width(spec_l) > 1e-9:
                    try:
                        search_w_l = max(_profile_total_width(spec_l), day_max_w)
                        spec_l, total_left_w = _resolve_daylight_bench_spec(
                            p_l,
                            n,
                            z,
                            spec_l,
                            terrain_sampler,
                            day_step,
                            search_w_l,
                            prev_left_w,
                            day_max_delta,
                        )
                    except Exception:
                        total_left_w = _profile_total_width(spec_l)
                else:
                    total_left_w = _profile_total_width(spec_l)
                bench_left_applied = bool(spec_l.get("benchVisible", int(spec_l.get("bench_count", 0) or 0) > 0))
                bench_left_adjusted = bool(spec_l.get("daylightAdjusted", False))
                bench_left_skipped = bool(spec_l.get("daylightSkipped", False))
                if use_day_left:
                    spec_l = _preserve_bench_point_contract(spec_l, stub_side_w)
                left_pts = []
                _left_end, total_left_w = _append_side_segment_points(left_pts, p_l, n, z, spec_l)
                resolved_left_w = float(total_left_w)
                left_seg_list = _profile_segments(spec_l)
                resolved_left_post_w = float(left_seg_list[-1].get("width", 0.0) or 0.0) if left_seg_list else 0.0
                pts = list(reversed(left_pts)) + pts
            else:
                w_l = lsw
                if use_day_left:
                    try:
                        search_w_l = max(lsw, day_max_w)
                        w_l_day, hit_l = SectionSet._solve_daylight_width(
                            p_l, n, z, lss_eff, search_w_l, terrain_sampler, day_step
                        )
                        w_l = w_l_day if hit_l else lsw
                        w_l = SectionSet._stabilize_daylight_width(
                            w_l,
                            prev_left_w,
                            day_max_delta,
                            0.01 if lsw > 1e-9 else 0.0,
                            search_w_l,
                        )
                    except Exception:
                        # Fail-safe: never block section creation due to daylight solve failure.
                        w_l = max(0.01 if lsw > 1e-9 else 0.0, lsw)
                else:
                    w_l = max(0.01 if lsw > 1e-9 else 0.0, min(lsw, w_l))
                resolved_left_w = float(w_l)
                resolved_left_post_w = float(w_l)
                p_lt = p_l + n * w_l + z * (-w_l * lss_eff / 100.0)
                pts = [p_lt] + pts
        if use_ss and rsw > 1e-9:
            if bool(right_bench.get("active", False)):
                spec_r = {"segments": [dict(seg) for seg in _profile_segments(right_bench)], "active": True}
                right_visible_bench_count = int(
                    sum(
                        1
                        for seg in _profile_segments(spec_r)
                        if str(seg.get("kind", "") or "") == "bench" and float(seg.get("width", 0.0) or 0.0) > 1e-9
                    )
                )
                spec_r["bench_count"] = int(right_visible_bench_count)
                spec_r["benchVisible"] = bool(right_visible_bench_count > 0)
                spec_r["daylightAdjusted"] = False
                spec_r["daylightSkipped"] = False
                if use_day_right:
                    segs = []
                    for seg in _profile_segments(spec_r):
                        row = dict(seg)
                        if str(row.get("kind", "") or "") == "slope":
                            row["slope"] = SectionSet._daylight_signed_slope(p_r, float(row.get("slope", 0.0) or 0.0), terrain_sampler)
                        segs.append(row)
                    spec_r["segments"] = segs
                if use_day_right and _profile_total_width(spec_r) > 1e-9:
                    try:
                        search_w_r = max(_profile_total_width(spec_r), day_max_w)
                        spec_r, total_right_w = _resolve_daylight_bench_spec(
                            p_r,
                            -n,
                            z,
                            spec_r,
                            terrain_sampler,
                            day_step,
                            search_w_r,
                            prev_right_w,
                            day_max_delta,
                        )
                    except Exception:
                        total_right_w = _profile_total_width(spec_r)
                else:
                    total_right_w = _profile_total_width(spec_r)
                bench_right_applied = bool(spec_r.get("benchVisible", int(spec_r.get("bench_count", 0) or 0) > 0))
                bench_right_adjusted = bool(spec_r.get("daylightAdjusted", False))
                bench_right_skipped = bool(spec_r.get("daylightSkipped", False))
                if use_day_right:
                    spec_r = _preserve_bench_point_contract(spec_r, stub_side_w)
                right_pts = []
                _right_end, total_right_w = _append_side_segment_points(right_pts, p_r, -n, z, spec_r)
                resolved_right_w = float(total_right_w)
                right_seg_list = _profile_segments(spec_r)
                resolved_right_post_w = float(right_seg_list[-1].get("width", 0.0) or 0.0) if right_seg_list else 0.0
                pts = pts + right_pts
            else:
                w_r = rsw
                if use_day_right:
                    try:
                        search_w_r = max(rsw, day_max_w)
                        w_r_day, hit_r = SectionSet._solve_daylight_width(
                            p_r, -n, z, rss_eff, search_w_r, terrain_sampler, day_step
                        )
                        w_r = w_r_day if hit_r else rsw
                        w_r = SectionSet._stabilize_daylight_width(
                            w_r,
                            prev_right_w,
                            day_max_delta,
                            0.01 if rsw > 1e-9 else 0.0,
                            search_w_r,
                        )
                    except Exception:
                        # Fail-safe: never block section creation due to daylight solve failure.
                        w_r = max(0.01 if rsw > 1e-9 else 0.0, rsw)
                else:
                    w_r = max(0.01 if rsw > 1e-9 else 0.0, min(rsw, w_r))
                resolved_right_w = float(w_r)
                resolved_right_post_w = float(w_r)
                p_rt = p_r - n * w_r + z * (-w_r * rss_eff / 100.0)
                pts = pts + [p_rt]

        w = Part.makePolygon(pts)
        return w, n, {
            "left": resolved_left_w,
            "right": resolved_right_w,
            "left_post": resolved_left_post_w,
            "right_post": resolved_right_post_w,
            "bench_left": bool(bench_left_applied),
            "bench_right": bool(bench_right_applied),
            "bench_left_adjusted": bool(bench_left_adjusted),
            "bench_right_adjusted": bool(bench_right_adjusted),
            "bench_left_skipped": bool(bench_left_skipped),
            "bench_right_skipped": bool(bench_right_skipped),
        }

    @staticmethod
    def build_section_wires(obj):
        src = getattr(obj, "SourceCenterlineDisplay", None)
        asm = getattr(obj, "AssemblyTemplate", None)
        typ = getattr(obj, "TypicalSectionTemplate", None) if hasattr(obj, "TypicalSectionTemplate") else None
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
                    terrain_mode = SectionSet._resolved_terrain_coord_mode(obj, terrain_source=tsrc)
                    terrain_sampler = SectionSet._terrain_sampler(
                        tsrc,
                        max_triangles=day_max,
                        coord_context=obj,
                        coord_mode=terrain_mode,
                    )
        except Exception:
            terrain_sampler = None

        left_cfg_count = len(
            _collect_side_bench_rows(
                bool(getattr(asm, "UseLeftBench", False)),
                float(getattr(asm, "LeftBenchDrop", 0.0) or 0.0),
                float(getattr(asm, "LeftBenchWidth", 0.0) or 0.0),
                float(getattr(asm, "LeftBenchSlopePct", 0.0) or 0.0),
                float(getattr(asm, "LeftPostBenchSlopePct", getattr(asm, "LeftSideSlopePct", 0.0)) or getattr(asm, "LeftSideSlopePct", 0.0)),
                list(getattr(asm, "LeftBenchRows", []) or []),
            )
        )
        right_cfg_count = len(
            _collect_side_bench_rows(
                bool(getattr(asm, "UseRightBench", False)),
                float(getattr(asm, "RightBenchDrop", 0.0) or 0.0),
                float(getattr(asm, "RightBenchWidth", 0.0) or 0.0),
                float(getattr(asm, "RightBenchSlopePct", 0.0) or 0.0),
                float(getattr(asm, "RightPostBenchSlopePct", getattr(asm, "RightSideSlopePct", 0.0)) or getattr(asm, "RightSideSlopePct", 0.0)),
                list(getattr(asm, "RightBenchRows", []) or []),
            )
        )
        wires = []
        prev_n = None
        prev_day_widths = {"left": None, "right": None}
        override_hits = 0
        bench_left_hits = 0
        bench_right_hits = 0
        bench_section_hits = 0
        bench_adjusted_hits = 0
        bench_skipped_hits = 0
        use_typ = bool(getattr(obj, "UseTypicalSectionTemplate", False)) and typ is not None
        for s in stations:
            structure_context = None
            if bool(getattr(obj, "ApplyStructureOverrides", False)):
                structure_context = SectionSet._structure_context_at_station(obj, float(s))
                if bool(
                    structure_context.get("SuppressSideSlopes", False)
                    or structure_context.get("SuppressDaylight", False)
                    or str(structure_context.get("LeftAction", "keep") or "keep").strip().lower() != "keep"
                    or str(structure_context.get("RightAction", "keep") or "keep").strip().lower() != "keep"
                ):
                    override_hits += 1
            try:
                w, prev_n, prev_day_widths = SectionSet.build_section_wire(
                    src,
                    asm,
                    float(s),
                    prev_n=prev_n,
                    prev_day_widths=prev_day_widths,
                    terrain_sampler=terrain_sampler,
                    use_daylight=use_day,
                    structure_context=structure_context,
                    apply_structure_overrides=bool(getattr(obj, "ApplyStructureOverrides", False)),
                    typical_section_obj=typ,
                    use_typical_section=use_typ,
                )
            except Exception:
                # Per-station fail-safe: fall back to fixed-width side slopes.
                w, prev_n, prev_day_widths = SectionSet.build_section_wire(
                    src,
                    asm,
                    float(s),
                    prev_n=prev_n,
                    prev_day_widths=prev_day_widths,
                    terrain_sampler=None,
                    use_daylight=False,
                    structure_context=structure_context,
                    apply_structure_overrides=bool(getattr(obj, "ApplyStructureOverrides", False)),
                    typical_section_obj=typ,
                    use_typical_section=use_typ,
                )
            left_bench_here = bool(prev_day_widths.get("bench_left", False))
            right_bench_here = bool(prev_day_widths.get("bench_right", False))
            if bool(prev_day_widths.get("bench_left_adjusted", False)) or bool(prev_day_widths.get("bench_right_adjusted", False)):
                bench_adjusted_hits += 1
            if bool(prev_day_widths.get("bench_left_skipped", False)) or bool(prev_day_widths.get("bench_right_skipped", False)):
                bench_skipped_hits += 1
            if left_bench_here:
                bench_left_hits += 1
            if right_bench_here:
                bench_right_hits += 1
            if left_bench_here or right_bench_here:
                bench_section_hits += 1
            wires.append(w)
        try:
            bench_info = {
                "overrideHits": int(override_hits),
                "benchLeft": int(bench_left_hits),
                "benchRight": int(bench_right_hits),
                "benchSections": int(bench_section_hits),
                "benchAdjusted": int(bench_adjusted_hits),
                "benchSkipped": int(bench_skipped_hits),
                "benchLeftConfigured": int(left_cfg_count),
                "benchRightConfigured": int(right_cfg_count),
            }
        except Exception:
            bench_info = {
                "overrideHits": int(override_hits),
                "benchLeft": 0,
                "benchRight": 0,
                "benchSections": 0,
                "benchAdjusted": 0,
                "benchSkipped": 0,
                "benchLeftConfigured": int(left_cfg_count),
                "benchRightConfigured": int(right_cfg_count),
            }
        return stations, wires, terrain_found, (terrain_sampler is not None), bench_info

    @staticmethod
    def _viewer_polyline_from_wire(wire, origin, nvec, zvec):
        if wire is None:
            return []
        verts = list(getattr(wire, "OrderedVertexes", []) or [])
        if not verts:
            verts = list(getattr(wire, "Vertexes", []) or [])
        pts = []
        for vv in verts:
            try:
                p = vv.Point
            except Exception:
                continue
            rel = p - origin
            # Screen X should match roadway left/right convention:
            # left side drawn on the left, right side on the right.
            x = -float(rel.dot(nvec))
            y = float(rel.dot(zvec))
            pts.append((x, y))
        return pts

    @staticmethod
    def _viewer_polylines_from_shape(shape, origin, nvec, zvec):
        if shape is None:
            return []
        try:
            if shape.isNull():
                return []
        except Exception:
            pass
        polylines = []
        wires = list(getattr(shape, "Wires", []) or [])
        if not wires:
            pts = SectionSet._viewer_polyline_from_wire(shape, origin, nvec, zvec)
            if pts:
                polylines.append(pts)
            return polylines
        for wire in wires:
            pts = SectionSet._viewer_polyline_from_wire(wire, origin, nvec, zvec)
            if pts:
                polylines.append(pts)
        return polylines

    @staticmethod
    def _viewer_bounds(polylines):
        xs = []
        ys = []
        for poly in list(polylines or []):
            for x, y in list(poly or []):
                xs.append(float(x))
                ys.append(float(y))
        if not xs or not ys:
            return {
                "xmin": 0.0,
                "xmax": 0.0,
                "ymin": 0.0,
                "ymax": 0.0,
                "width": 0.0,
                "height": 0.0,
            }
        xmin = min(xs)
        xmax = max(xs)
        ymin = min(ys)
        ymax = max(ys)
        return {
            "xmin": float(xmin),
            "xmax": float(xmax),
            "ymin": float(ymin),
            "ymax": float(ymax),
            "width": float(xmax - xmin),
            "height": float(ymax - ymin),
        }

    @staticmethod
    def _viewer_dimension_rows(payload):
        sec_bounds = dict(payload.get("section_bounds", {}) or {})
        xmin = float(sec_bounds.get("xmin", 0.0) or 0.0)
        xmax = float(sec_bounds.get("xmax", 0.0) or 0.0)
        ymin = float(sec_bounds.get("ymin", 0.0) or 0.0)
        ymax = float(sec_bounds.get("ymax", 0.0) or 0.0)
        width = max(0.0, float(sec_bounds.get("width", 0.0) or 0.0))
        height = max(1.0, float(sec_bounds.get("height", 0.0) or 0.0))
        base_y = ymin - (0.28 * height)
        mid_y = ymin - (0.42 * height)
        dims = []
        if width > 1e-9:
            dims.append(
                {
                    "kind": "overall_width",
                    "label": f"Overall {width:.3f} m",
                    "x0": float(xmin),
                    "x1": float(xmax),
                    "y": float(base_y),
                    "value": float(width),
                }
            )
        component_rows = [
            row for row in list(payload.get("component_rows", []) or [])
            if str(row.get("kind", "") or "") == "component"
        ]

        def _effective_width(row):
            typ = str(row.get("type", "") or "").strip().lower()
            width = max(0.0, float(row.get("width", 0.0) or 0.0))
            extra = max(0.0, float(row.get("extraWidth", 0.0) or 0.0))
            if typ in ("curb", "berm"):
                return width + extra
            return width

        left_rows = sorted(
            [row for row in component_rows if str(row.get("side", "") or "").strip().lower() == "left"],
            key=lambda row: int(float(row.get("order", 0) or 0)),
        )
        right_rows = sorted(
            [row for row in component_rows if str(row.get("side", "") or "").strip().lower() == "right"],
            key=lambda row: int(float(row.get("order", 0) or 0)),
        )
        both_rows = sorted(
            [row for row in component_rows if str(row.get("side", "") or "").strip().lower() == "both"],
            key=lambda row: int(float(row.get("order", 0) or 0)),
        )
        left_rows.extend(dict(row, side="left") for row in both_rows)
        right_rows.extend(dict(row, side="right") for row in both_rows)

        comp_y = ymin - (0.62 * height)
        step_y = 0.14 * height

        cur = 0.0
        for idx, row in enumerate(left_rows):
            seg_w = _effective_width(row)
            if seg_w <= 1e-9:
                continue
            x0 = cur - seg_w
            x1 = cur
            label = f"{str(row.get('id', '-') or '-')} {seg_w:.3f} m"
            dims.append(
                {
                    "kind": "component_left",
                    "label": label,
                    "x0": float(x0),
                    "x1": float(x1),
                    "y": float(comp_y - (idx * step_y)),
                    "value": float(seg_w),
                    "role": str(row.get("type", "") or "").strip().lower(),
                }
            )
            cur = x0

        cur = 0.0
        for idx, row in enumerate(right_rows):
            seg_w = _effective_width(row)
            if seg_w <= 1e-9:
                continue
            x0 = cur
            x1 = cur + seg_w
            label = f"{str(row.get('id', '-') or '-')} {seg_w:.3f} m"
            dims.append(
                {
                    "kind": "component_right",
                    "label": label,
                    "x0": float(x0),
                    "x1": float(x1),
                    "y": float(comp_y - (idx * step_y)),
                    "value": float(seg_w),
                    "role": str(row.get("type", "") or "").strip().lower(),
                }
            )
            cur = x1
        return dims

    @staticmethod
    def _viewer_label_rows(payload):
        bounds = dict(payload.get("bounds", {}) or {})
        xmin = float(bounds.get("xmin", 0.0) or 0.0)
        xmax = float(bounds.get("xmax", 0.0) or 0.0)
        ymax = float(bounds.get("ymax", 0.0) or 0.0)
        dy = max(1.0, float(bounds.get("height", 0.0) or 0.0))
        labels = []

        tag_summary = str(payload.get("tag_summary", "") or "").strip()
        if tag_summary:
            labels.append(
                {
                    "text": f"Tags: {tag_summary}",
                    "x": float(xmin),
                    "y": float(ymax + (0.18 * dy)),
                    "role": "station_tags",
                }
            )

        left_edge = str(payload.get("left_edge_label", "") or "").strip()
        right_edge = str(payload.get("right_edge_label", "") or "").strip()
        if left_edge:
            labels.append(
                {
                    "text": f"L: {left_edge}",
                    "x": float(xmin),
                    "y": float(ymax + (0.05 * dy)),
                    "role": "top_edge_left",
                }
            )
        if right_edge:
            labels.append(
                {
                    "text": f"R: {right_edge}",
                    "x": float(xmax),
                    "y": float(ymax + (0.05 * dy)),
                    "role": "top_edge_right",
                }
            )

        structure_summary = str(payload.get("structure_summary", "") or "").strip()
        if structure_summary:
            labels.append(
                {
                    "text": structure_summary,
                    "x": 0.0,
                    "y": float(ymax + (0.11 * dy)),
                    "role": "structure_summary",
                }
            )

        daylight_note = str(payload.get("daylight_note", "") or "").strip()
        if daylight_note:
            labels.append(
                {
                    "text": daylight_note,
                    "x": float(xmin),
                    "y": float(bounds.get("ymin", 0.0) or 0.0) - (0.14 * dy),
                    "role": "daylight_note",
                }
            )
        return labels

    @staticmethod
    def _viewer_daylight_rows(payload):
        payload = dict(payload or {})
        daylight_note = str(payload.get("daylight_note", "") or "").strip().lower()
        if not daylight_note.startswith("daylight=terrain:"):
            return []
        daylight_mode = daylight_note.split("=", 1)[1] if "=" in daylight_note else daylight_note
        polylines = list(payload.get("section_polylines", []) or [])
        if not polylines:
            return []
        pts = []
        for poly in polylines:
            for pt in list(poly or []):
                if len(pt) < 2:
                    continue
                try:
                    pts.append((float(pt[0]), float(pt[1])))
                except Exception:
                    continue
        if len(pts) < 2:
            return []
        left_pt = min(pts, key=lambda p: p[0])
        right_pt = max(pts, key=lambda p: p[0])
        rows = [
            {
                "kind": "daylight",
                "side": "left",
                "x": float(left_pt[0]),
                "y": float(left_pt[1]),
                "label": "daylight L",
                "scope": "daylight",
                "source": "terrain",
                "mode": daylight_mode,
            }
        ]
        if abs(float(right_pt[0]) - float(left_pt[0])) > 1e-6 or abs(float(right_pt[1]) - float(left_pt[1])) > 1e-6:
            rows.append(
                {
                    "kind": "daylight",
                    "side": "right",
                    "x": float(right_pt[0]),
                    "y": float(right_pt[1]),
                    "label": "daylight R",
                    "scope": "daylight",
                    "source": "terrain",
                    "mode": daylight_mode,
                }
            )
        return rows

    @staticmethod
    def _viewer_fallback_component_rows(obj):
        asm = getattr(obj, "AssemblyTemplate", None)
        if asm is None:
            return []

        rows = []

        def _append(side: str, order: int, typ: str, width: float, extra: float = 0.0, label: str = ""):
            width = max(0.0, float(width or 0.0))
            extra = max(0.0, float(extra or 0.0))
            if (width + extra) <= 1e-9:
                return
            rows.append(
                {
                    "kind": "component",
                    "id": f"{side[:1].upper()}{order}",
                    "type": str(typ or "").strip().lower(),
                    "side": str(side or "").strip().lower(),
                    "width": float(width),
                    "extraWidth": float(extra),
                    "order": int(order),
                    "label": str(label or "").strip(),
                }
            )

        left_width = max(0.0, float(getattr(asm, "LeftWidth", 0.0) or 0.0))
        right_width = max(0.0, float(getattr(asm, "RightWidth", 0.0) or 0.0))
        if left_width > 1e-9:
            _append("left", 1, "carriageway", left_width, label="Left Carriageway")
        if right_width > 1e-9:
            _append("right", 1, "carriageway", right_width, label="Right Carriageway")

        use_side_slopes = bool(getattr(asm, "UseSideSlopes", False))
        if not use_side_slopes:
            return rows

        left_side_width = max(0.0, float(getattr(asm, "LeftSideWidth", 0.0) or 0.0))
        right_side_width = max(0.0, float(getattr(asm, "RightSideWidth", 0.0) or 0.0))
        left_side_slope = float(getattr(asm, "LeftSideSlopePct", 0.0) or 0.0)
        right_side_slope = float(getattr(asm, "RightSideSlopePct", 0.0) or 0.0)

        left_bench_rows = _collect_side_bench_rows(
            bool(getattr(asm, "UseLeftBench", False)),
            float(getattr(asm, "LeftBenchDrop", 0.0) or 0.0),
            float(getattr(asm, "LeftBenchWidth", 0.0) or 0.0),
            float(getattr(asm, "LeftBenchSlopePct", 0.0) or 0.0),
            float(getattr(asm, "LeftPostBenchSlopePct", left_side_slope) or left_side_slope),
            list(getattr(asm, "LeftBenchRows", []) or []),
        )
        right_bench_rows = _collect_side_bench_rows(
            bool(getattr(asm, "UseRightBench", False)),
            float(getattr(asm, "RightBenchDrop", 0.0) or 0.0),
            float(getattr(asm, "RightBenchWidth", 0.0) or 0.0),
            float(getattr(asm, "RightBenchSlopePct", 0.0) or 0.0),
            float(getattr(asm, "RightPostBenchSlopePct", right_side_slope) or right_side_slope),
            list(getattr(asm, "RightBenchRows", []) or []),
        )

        def _append_profile(side: str, start_order: int, total_width: float, side_slope: float, bench_rows):
            profile = _resolve_side_bench_profile(total_width, side_slope, bench_rows)
            order = int(start_order)
            for seg in list(profile.get("segments", []) or []):
                seg_w = max(0.0, float(seg.get("width", 0.0) or 0.0))
                if seg_w <= 1e-9:
                    continue
                seg_kind = str(seg.get("kind", "") or "").strip().lower()
                typ = "bench" if seg_kind == "bench" else "side_slope"
                label = f"{'Left' if side == 'left' else 'Right'} Bench" if typ == "bench" else f"{'Left' if side == 'left' else 'Right'} Side Slope"
                _append(side, order, typ, seg_w, label=label)
                order += 1

        if left_side_width > 1e-9:
            _append_profile("left", 10, left_side_width, left_side_slope, left_bench_rows)
        if right_side_width > 1e-9:
            _append_profile("right", 10, right_side_width, right_side_slope, right_bench_rows)

        return rows

    @staticmethod
    def _component_segment_rows_from_summary_rows(component_rows, stations):
        rows = [
            dict(row)
            for row in list(component_rows or [])
            if str(row.get("kind", "") or "").strip().lower() == "component"
        ]
        stations = [float(sta) for sta in list(stations or [])]
        if not rows or not stations:
            return []

        def _safe_float_text(value, default=0.0):
            try:
                return float(value)
            except Exception:
                return float(default)

        def _sorted_side_rows(side_name: str):
            side_name = str(side_name or "").strip().lower()
            out = [
                dict(row)
                for row in rows
                if str(row.get("side", "") or "").strip().lower() == side_name
            ]
            out.extend(
                dict(row, side=side_name)
                for row in rows
                if str(row.get("side", "") or "").strip().lower() == "both"
            )
            out.sort(key=lambda row: int(_safe_float_text(row.get("order", 0), 0)))
            return out

        left_rows = _sorted_side_rows("left")
        right_rows = _sorted_side_rows("right")
        center_rows = _sorted_side_rows("center")
        out = []
        for station_value in stations:
            cur = 0.0
            for row in left_rows:
                width = max(0.0, _safe_float_text(row.get("width", 0.0), 0.0))
                extra = max(0.0, _safe_float_text(row.get("extraWidth", 0.0), 0.0))
                typ = str(row.get("type", "") or "").strip().lower()
                seg_w = width + extra if typ in ("curb", "berm") else width
                if seg_w <= 1e-9:
                    continue
                x0 = cur - seg_w
                x1 = cur
                out.append(
                    _report_row(
                        "component_segment",
                        station=f"{station_value:.3f}",
                        side="left",
                        id=str(row.get("id", "") or "").strip() or "-",
                        type=typ or "-",
                        label=str(row.get("label", "") or row.get("type", "") or "").strip(),
                        scope="typical",
                        order=int(_safe_float_text(row.get("order", 0), 0)),
                        x0=f"{x0:.3f}",
                        x1=f"{x1:.3f}",
                        width=f"{seg_w:.3f}",
                        source="typical_summary",
                    )
                )
                cur = x0

            cur = 0.0
            for row in right_rows:
                width = max(0.0, _safe_float_text(row.get("width", 0.0), 0.0))
                extra = max(0.0, _safe_float_text(row.get("extraWidth", 0.0), 0.0))
                typ = str(row.get("type", "") or "").strip().lower()
                seg_w = width + extra if typ in ("curb", "berm") else width
                if seg_w <= 1e-9:
                    continue
                x0 = cur
                x1 = cur + seg_w
                out.append(
                    _report_row(
                        "component_segment",
                        station=f"{station_value:.3f}",
                        side="right",
                        id=str(row.get("id", "") or "").strip() or "-",
                        type=typ or "-",
                        label=str(row.get("label", "") or row.get("type", "") or "").strip(),
                        scope="typical",
                        order=int(_safe_float_text(row.get("order", 0), 0)),
                        x0=f"{x0:.3f}",
                        x1=f"{x1:.3f}",
                        width=f"{seg_w:.3f}",
                        source="typical_summary",
                    )
                )
                cur = x1

            for row in center_rows:
                width = max(0.0, _safe_float_text(row.get("width", 0.0), 0.0))
                extra = max(0.0, _safe_float_text(row.get("extraWidth", 0.0), 0.0))
                typ = str(row.get("type", "") or "").strip().lower()
                seg_w = width + extra if typ in ("curb", "berm") else width
                if seg_w <= 1e-9:
                    continue
                x0 = -0.5 * seg_w
                x1 = 0.5 * seg_w
                out.append(
                    _report_row(
                        "component_segment",
                        station=f"{station_value:.3f}",
                        side="center",
                        id=str(row.get("id", "") or "").strip() or "-",
                        type=typ or "-",
                        label=str(row.get("label", "") or row.get("type", "") or "").strip(),
                        scope="typical",
                        order=int(_safe_float_text(row.get("order", 0), 0)),
                        x0=f"{x0:.3f}",
                        x1=f"{x1:.3f}",
                        width=f"{seg_w:.3f}",
                        source="typical_summary",
                    )
                )
        return out

    @staticmethod
    def _component_segment_rows_from_assembly(obj, stations):
        asm = getattr(obj, "AssemblyTemplate", None)
        if asm is None:
            return []
        stations = [float(sta) for sta in list(stations or [])]
        if not stations:
            return []

        left_width = max(0.0, float(getattr(asm, "LeftWidth", 0.0) or 0.0))
        right_width = max(0.0, float(getattr(asm, "RightWidth", 0.0) or 0.0))
        left_side_width = max(0.0, float(getattr(asm, "LeftSideWidth", 0.0) or 0.0))
        right_side_width = max(0.0, float(getattr(asm, "RightSideWidth", 0.0) or 0.0))
        left_side_slope = float(getattr(asm, "LeftSideSlopePct", 0.0) or 0.0)
        right_side_slope = float(getattr(asm, "RightSideSlopePct", 0.0) or 0.0)
        terrain_sampler = None
        use_ss = bool(getattr(asm, "UseSideSlopes", False))
        use_day = bool(getattr(obj, "DaylightAuto", True)) and bool(use_ss) and ((left_side_width > 1e-9) or (right_side_width > 1e-9))
        if use_day:
            try:
                tsrc = SectionSet._resolve_terrain_source(obj)
                if tsrc is not None:
                    day_max = int(getattr(asm, "DaylightMaxTriangles", 300000))
                    terrain_mode = SectionSet._resolved_terrain_coord_mode(obj, terrain_source=tsrc)
                    terrain_sampler = SectionSet._terrain_sampler(
                        tsrc,
                        max_triangles=day_max,
                        coord_context=obj,
                        coord_mode=terrain_mode,
                    )
            except Exception:
                terrain_sampler = None
        left_bench_rows = _collect_side_bench_rows(
            bool(getattr(asm, "UseLeftBench", False)),
            float(getattr(asm, "LeftBenchDrop", 0.0) or 0.0),
            float(getattr(asm, "LeftBenchWidth", 0.0) or 0.0),
            float(getattr(asm, "LeftBenchSlopePct", 0.0) or 0.0),
            float(getattr(asm, "LeftPostBenchSlopePct", left_side_slope) or left_side_slope),
            list(getattr(asm, "LeftBenchRows", []) or []),
        )
        right_bench_rows = _collect_side_bench_rows(
            bool(getattr(asm, "UseRightBench", False)),
            float(getattr(asm, "RightBenchDrop", 0.0) or 0.0),
            float(getattr(asm, "RightBenchWidth", 0.0) or 0.0),
            float(getattr(asm, "RightBenchSlopePct", 0.0) or 0.0),
            float(getattr(asm, "RightPostBenchSlopePct", right_side_slope) or right_side_slope),
            list(getattr(asm, "RightBenchRows", []) or []),
        )
        left_profile = _resolve_side_bench_profile(left_side_width, left_side_slope, left_bench_rows)
        right_profile = _resolve_side_bench_profile(right_side_width, right_side_slope, right_bench_rows)

        def _append_segments(out_rows, station_value: float, side_name: str, start_cursor: float, widths: float, profile: dict, carriageway_width: float, slope_type: str):
            if carriageway_width > 1e-9:
                if side_name == "left":
                    x0 = start_cursor - carriageway_width
                    x1 = start_cursor
                else:
                    x0 = start_cursor
                    x1 = start_cursor + carriageway_width
                out_rows.append(
                    _report_row(
                        "component_segment",
                        station=f"{station_value:.3f}",
                        side=side_name,
                        id=f"{side_name[:1].upper()}RW",
                        type="carriageway",
                        label="carriageway",
                        scope="typical",
                        order=1,
                        x0=f"{x0:.3f}",
                        x1=f"{x1:.3f}",
                        width=f"{carriageway_width:.3f}",
                        source="assembly_template",
                    )
                )
                cursor = x0 if side_name == "left" else x1
            else:
                cursor = start_cursor

            order = 10
            segments = list(dict(profile or {}).get("segments", []) or [])
            for seg in segments:
                seg_w = max(0.0, float(seg.get("width", 0.0) or 0.0))
                if seg_w <= 1e-9:
                    continue
                seg_kind = str(seg.get("kind", "") or "").strip().lower()
                seg_type = "bench" if seg_kind == "bench" else str(slope_type or "side_slope")
                if side_name == "left":
                    x0 = cursor - seg_w
                    x1 = cursor
                    cursor = x0
                else:
                    x0 = cursor
                    x1 = cursor + seg_w
                    cursor = x1
                out_rows.append(
                    _report_row(
                        "component_segment",
                        station=f"{station_value:.3f}",
                        side=side_name,
                        id=f"{side_name[:1].upper()}{order}",
                        type=seg_type,
                        label=seg_type,
                        scope="side_slope",
                        order=order,
                        x0=f"{x0:.3f}",
                        x1=f"{x1:.3f}",
                        width=f"{seg_w:.3f}",
                        source="assembly_template",
                    )
                )
                order += 1

        out = []
        prev_n = None
        for station_value in stations:
            slope_types, prev_n = SectionSet._assembly_station_side_slope_types(
                obj,
                station_value,
                prev_n=prev_n,
                terrain_sampler=terrain_sampler,
                use_daylight=bool(use_day),
            )
            _append_segments(
                out,
                station_value,
                "left",
                0.0,
                left_side_width,
                left_profile,
                left_width,
                str(slope_types.get("left", "side_slope") or "side_slope"),
            )
            _append_segments(
                out,
                station_value,
                "right",
                0.0,
                right_side_width,
                right_profile,
                right_width,
                str(slope_types.get("right", "side_slope") or "side_slope"),
            )
        return out

    @staticmethod
    def _side_slope_segment_rows_from_assembly(obj, stations, typical_segment_rows=None):
        rows = SectionSet._component_segment_rows_from_assembly(obj, stations)
        typical_anchors = _typical_edge_anchors(typical_segment_rows)
        asm = getattr(obj, "AssemblyTemplate", None)
        left_width = max(0.0, float(getattr(asm, "LeftWidth", 0.0) or 0.0)) if asm is not None else 0.0
        right_width = max(0.0, float(getattr(asm, "RightWidth", 0.0) or 0.0)) if asm is not None else 0.0
        out = []
        for row_txt in list(rows or []):
            try:
                row = _parse_report_row(row_txt)
            except Exception:
                row = {}
            if str(row.get("scope", "") or "").strip().lower() == "side_slope":
                station_key = round(_safe_float(row.get("station", 0.0), 0.0), 6)
                side_name = str(row.get("side", "") or "").strip().lower()
                delta = 0.0
                anchor_info = typical_anchors.get(station_key, {})
                if side_name == "left":
                    target_edge = anchor_info.get("left", None)
                    source_edge = -left_width if left_width > 1e-9 else 0.0
                    if target_edge is not None:
                        delta = float(target_edge) - float(source_edge)
                elif side_name == "right":
                    target_edge = anchor_info.get("right", None)
                    source_edge = right_width if right_width > 1e-9 else 0.0
                    if target_edge is not None:
                        delta = float(target_edge) - float(source_edge)
                if abs(delta) > 1e-9:
                    row["x0"] = f"{(_safe_float(row.get('x0', 0.0), 0.0) + delta):.3f}"
                    row["x1"] = f"{(_safe_float(row.get('x1', 0.0), 0.0) + delta):.3f}"
                    kind = str(row.get("kind", "component_segment") or "component_segment")
                    fields = {k: v for k, v in row.items() if k not in ("kind", "raw")}
                    out.append(_report_row(kind, **fields))
                else:
                    out.append(str(row_txt))
        return out

    @staticmethod
    def resolve_viewer_station_rows(obj):
        stations = list(getattr(obj, "StationValues", []) or [])
        if len(stations) < 1:
            stations = SectionSet.resolve_station_values(obj)
        tags = SectionSet.resolve_station_tags(obj, stations) if stations else []
        meta_rows = SectionSet.resolve_structure_metadata(obj, stations) if stations else []
        rows = []
        for idx, station in enumerate(stations):
            tag_list = list(tags[idx] if idx < len(tags) else [] or [])
            meta = dict(meta_rows[idx] if idx < len(meta_rows) else {} or {})
            tag_txt = f" [{' / '.join(tag_list)}]" if tag_list else ""
            struct_count = len(list(meta.get("StructureIds", []) or []))
            struct_txt = ""
            if struct_count > 0:
                struct_txt = f" | structures={struct_count}"
            rows.append(
                {
                    "index": int(idx),
                    "station": float(station),
                    "tags": tag_list,
                    "has_structure": bool(meta.get("HasStructure", False)),
                    "structure_summary": str(meta.get("StructureSummary", "") or ""),
                    "label": f"STA {float(station):.3f}{tag_txt}{struct_txt}",
                }
            )
        return rows

    @staticmethod
    def resolve_viewer_payload(obj, station=None, index=None, include_structure_overlay: bool = True):
        stations, wires, _terrain_found, _sampler_ok, _bench_info = SectionSet.build_section_wires(obj)
        if len(stations) < 1 or len(wires) < 1:
            return {}

        use_index = -1
        if index is not None:
            try:
                idx = int(index)
                if 0 <= idx < len(stations):
                    use_index = idx
            except Exception:
                use_index = -1
        if use_index < 0:
            target = float(station if station is not None else stations[0])
            best_idx = 0
            best_delta = None
            for idx, sta in enumerate(stations):
                delta = abs(float(sta) - target)
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_idx = idx
            use_index = int(best_idx)

        station_value = float(stations[use_index])
        src = getattr(obj, "SourceCenterlineDisplay", None)
        if src is None:
            raise Exception("SourceCenterlineDisplay is missing.")
        scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
        frame = Centerline3D.frame_at_station(src, station_value, eps=0.1 * scale, prev_n=None)
        origin = frame["point"]
        nvec = frame["N"]
        zvec = frame["Z"]

        tags = SectionSet.resolve_station_tags(obj, stations)
        meta_rows = SectionSet.resolve_structure_metadata(obj, stations)
        tag_list = list(tags[use_index] if use_index < len(tags) else [] or [])
        meta = dict(meta_rows[use_index] if use_index < len(meta_rows) else {} or {})
        section_polylines = SectionSet._viewer_polylines_from_shape(wires[use_index], origin, nvec, zvec)

        overlay_polylines = []
        if bool(include_structure_overlay):
            try:
                overlay_shape = SectionSet._build_child_structure_overlay(obj, station_value, meta)
            except Exception:
                overlay_shape = None
            overlay_polylines = SectionSet._viewer_polylines_from_shape(overlay_shape, origin, nvec, zvec)

        section_bounds = SectionSet._viewer_bounds(section_polylines)
        all_polylines = list(section_polylines) + list(overlay_polylines)
        bounds = SectionSet._viewer_bounds(all_polylines)
        top_edges = str(getattr(obj, "TopProfileEdgeSummary", "-") or "-")
        left_edge = ""
        right_edge = ""
        if "/" in top_edges:
            left_edge, right_edge = [str(v or "").strip() for v in top_edges.split("/", 1)]
        elif top_edges not in ("", "-"):
            left_edge = top_edges
            right_edge = top_edges
        status_text = str(getattr(obj, "Status", "") or "")
        status_tokens = [str(tok or "").strip() for tok in status_text.split("|") if str(tok or "").strip()]
        diagnostic_tokens = [
            tok for tok in status_tokens
            if tok.startswith("daylight=")
            or tok.startswith("bench=")
            or tok.startswith("benchDay")
            or tok.startswith("structures=")
            or tok.startswith("topEdges=")
            or tok.startswith("pavement=")
            or tok.startswith("pavLayers=")
        ]
        structure_rows = [_parse_report_row(row) for row in list(getattr(obj, "StructureInteractionSummaryRows", []) or [])]
        bench_rows = [_parse_report_row(row) for row in list(getattr(obj, "BenchSummaryRows", []) or [])]
        segment_rows = [_parse_report_row(row) for row in list(getattr(obj, "SectionComponentSegmentRows", []) or [])]
        component_rows = []
        for row in segment_rows:
            if str(row.get("kind", "") or "").strip().lower() != "component_segment":
                continue
            try:
                row_station = float(row.get("station", 0.0) or 0.0)
            except Exception:
                continue
            if abs(row_station - station_value) > 1e-6:
                continue
            component_rows.append(row)
        pavement_rows = [_parse_report_row(row) for row in list(getattr(obj, "PavementScheduleRows", []) or [])]
        daylight_note = ""
        for tok in diagnostic_tokens:
            if tok.startswith("daylight="):
                daylight_note = tok
                break
        payload = {
            "index": int(use_index),
            "station": station_value,
            "station_label": f"STA {station_value:.3f}",
            "tags": tag_list,
            "tag_summary": "/".join(tag_list) if tag_list else "",
            "section_count": int(len(stations)),
            "section_polylines": list(section_polylines),
            "overlay_polylines": list(overlay_polylines),
            "section_bounds": dict(section_bounds),
            "bounds": dict(bounds),
            "has_structure": bool(meta.get("HasStructure", False)),
            "structure_ids": list(meta.get("StructureIds", []) or []),
            "structure_types": list(meta.get("StructureTypes", []) or []),
            "structure_roles": list(meta.get("StructureRoles", []) or []),
            "structure_summary": str(meta.get("StructureSummary", "") or ""),
            "bench_summary": str(getattr(obj, "BenchSummary", "-") or "-"),
            "top_profile_edge_summary": top_edges,
            "left_edge_label": left_edge,
            "right_edge_label": right_edge,
            "status": status_text,
            "diagnostic_tokens": list(diagnostic_tokens),
            "structure_rows": list(structure_rows),
            "bench_rows": list(bench_rows),
            "component_rows": list(component_rows),
            "pavement_rows": list(pavement_rows),
            "pavement_total_thickness": float(getattr(obj, "PavementTotalThickness", 0.0) or 0.0),
            "pavement_layer_count": int(getattr(obj, "PavementLayerCount", 0) or 0),
            "enabled_pavement_layer_count": int(getattr(obj, "EnabledPavementLayerCount", 0) or 0),
            "daylight_note": daylight_note,
            "daylight_mode": daylight_note.split("=", 1)[1] if "=" in daylight_note else daylight_note,
        }
        payload["dimension_rows"] = SectionSet._viewer_dimension_rows(payload)
        payload["label_rows"] = SectionSet._viewer_label_rows(payload)
        payload["daylight_rows"] = SectionSet._viewer_daylight_rows(payload)
        return payload

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
    def rebuild_child_sections(obj, stations=None, wires=None, station_tags=None, structure_meta=None):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return

        if stations is None or wires is None:
            stations, wires, _tf, _so, _bi = SectionSet.build_section_wires(obj)
        if len(stations) != len(wires):
            raise Exception("Child rebuild failed: stations/wires size mismatch.")
        if station_tags is None or len(station_tags) != len(stations):
            station_tags = SectionSet.resolve_station_tags(obj, stations)
        if structure_meta is None or len(structure_meta) != len(stations):
            structure_meta = SectionSet.resolve_structure_metadata(obj, stations)

        SectionSet.clear_child_sections(obj)
        children = []
        for i, (s, w) in enumerate(zip(stations, wires)):
            ch = doc.addObject("Part::Feature", "SectionSlice")
            tags = station_tags[i] if i < len(station_tags) else []
            meta = structure_meta[i] if i < len(structure_meta) else {}
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
            try:
                if not hasattr(ch, "HasStructure"):
                    ch.addProperty("App::PropertyBool", "HasStructure", "Structure", "Whether this section is structure-aware")
                ch.HasStructure = bool(meta.get("HasStructure", False))
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureIds"):
                    ch.addProperty("App::PropertyStringList", "StructureIds", "Structure", "Resolved structure IDs at this section")
                ch.StructureIds = list(meta.get("StructureIds", []) or [])
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureTypes"):
                    ch.addProperty("App::PropertyStringList", "StructureTypes", "Structure", "Resolved structure types at this section")
                ch.StructureTypes = list(meta.get("StructureTypes", []) or [])
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureRoles"):
                    ch.addProperty("App::PropertyStringList", "StructureRoles", "Structure", "Resolved structure roles at this section")
                ch.StructureRoles = list(meta.get("StructureRoles", []) or [])
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureRole"):
                    ch.addProperty("App::PropertyString", "StructureRole", "Structure", "Primary structure role summary")
                ch.StructureRole = str(meta.get("StructureRole", "") or "")
            except Exception:
                pass
            try:
                if not hasattr(ch, "StructureSummary"):
                    ch.addProperty("App::PropertyString", "StructureSummary", "Structure", "Structure summary text")
                ch.StructureSummary = str(meta.get("StructureSummary", "") or "")
            except Exception:
                pass
            overlay_shape = SectionSet._build_child_structure_overlay(obj, float(s), meta)
            try:
                if not hasattr(ch, "StructureOverlayCount"):
                    ch.addProperty("App::PropertyInteger", "StructureOverlayCount", "Structure", "Overlay wire count generated for this section")
                if overlay_shape is not None:
                    nw = len(list(getattr(overlay_shape, "Wires", []) or []))
                    ch.StructureOverlayCount = int(max(1, nw))
                else:
                    ch.StructureOverlayCount = 0
            except Exception:
                pass
            # Keep the child section shape as the base section wire only.
            # Corridor loft relies on a stable wire point contract, and embedding
            # structure overlay geometry here can change the interpreted point count.
            ch.Shape = w
            SectionSet._apply_child_structure_visual(ch, meta)
            children.append(ch)
            if overlay_shape is not None:
                try:
                    ov = doc.addObject("Part::Feature", "SectionStructureOverlay")
                    ov.Label = _structure_overlay_label(float(s), meta)
                    try:
                        if not hasattr(ov, "Station"):
                            ov.addProperty("App::PropertyFloat", "Station", "Section", "Section station")
                        ov.Station = float(s)
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "ParentSectionSet"):
                            ov.addProperty("App::PropertyLink", "ParentSectionSet", "Section", "Owner SectionSet")
                        ov.ParentSectionSet = obj
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "ParentSectionSlice"):
                            ov.addProperty("App::PropertyLink", "ParentSectionSlice", "Section", "Owner child section")
                        ov.ParentSectionSlice = ch
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "HasStructure"):
                            ov.addProperty("App::PropertyBool", "HasStructure", "Structure", "Whether this overlay represents resolved structure data")
                        ov.HasStructure = bool(meta.get("HasStructure", False))
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureIds"):
                            ov.addProperty("App::PropertyStringList", "StructureIds", "Structure", "Resolved structure IDs at this section")
                        ov.StructureIds = list(meta.get("StructureIds", []) or [])
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureTypes"):
                            ov.addProperty("App::PropertyStringList", "StructureTypes", "Structure", "Resolved structure types at this section")
                        ov.StructureTypes = list(meta.get("StructureTypes", []) or [])
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureRoles"):
                            ov.addProperty("App::PropertyStringList", "StructureRoles", "Structure", "Resolved structure roles at this section")
                        ov.StructureRoles = list(meta.get("StructureRoles", []) or [])
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureRole"):
                            ov.addProperty("App::PropertyString", "StructureRole", "Structure", "Primary structure role summary")
                        ov.StructureRole = str(meta.get("StructureRole", "") or "")
                    except Exception:
                        pass
                    try:
                        if not hasattr(ov, "StructureSummary"):
                            ov.addProperty("App::PropertyString", "StructureSummary", "Structure", "Structure summary text")
                        ov.StructureSummary = str(meta.get("StructureSummary", "") or "")
                    except Exception:
                        pass
                    ov.Shape = overlay_shape
                    try:
                        vov = getattr(ov, "ViewObject", None)
                        if vov is not None:
                            vov.DisplayMode = "Wireframe"
                            vov.LineColor = (0.92, 0.35, 0.20)
                            vov.PointColor = (0.92, 0.35, 0.20)
                            vov.ShapeColor = (0.92, 0.35, 0.20)
                            vov.LineWidth = 4
                            vov.Transparency = 0
                        ov.Label = _structure_overlay_label(float(s), meta)
                    except Exception:
                        pass
                    children.append(ov)
                except Exception:
                    pass
        obj.Group = children
        prj = _find_project(doc)
        if prj is not None:
            try:
                from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject

                for child in children:
                    try:
                        CorridorRoadProject.adopt(prj, child)
                    except Exception:
                        pass
            except Exception:
                pass

    def execute(self, obj):
        ensure_section_set_properties(obj)
        try:
            asm = getattr(obj, "AssemblyTemplate", None)
            use_ss = bool(getattr(asm, "UseSideSlopes", False)) if asm is not None else False
            left_on = float(getattr(asm, "LeftSideWidth", 0.0)) > 1e-9 if asm is not None else False
            right_on = float(getattr(asm, "RightSideWidth", 0.0)) > 1e-9 if asm is not None else False
            use_typ = bool(getattr(obj, "UseTypicalSectionTemplate", False)) and getattr(obj, "TypicalSectionTemplate", None) is not None
            stations = SectionSet.resolve_station_values(obj)
            # Schema contract:
            # - v1: simple 3-point profile (Left->Center->Right)
            # - v2: extended/open profile with additional break points
            obj.SectionSchemaVersion = 2 if (use_typ or (use_ss and (left_on or right_on))) else 1
            obj.TopProfileSource = "typical_section" if use_typ else "assembly_simple"
            if use_typ:
                typ = getattr(obj, "TypicalSectionTemplate", None)
                obj.SubassemblySchemaVersion = int(getattr(typ, "SubassemblySchemaVersion", 1) or 1)
                obj.PracticalSectionMode = str(getattr(typ, "PracticalSectionMode", "simple") or "simple")
                obj.ReportSchemaVersion = int(getattr(typ, "ReportSchemaVersion", 1) or 1)
                left_edge = str(getattr(typ, "LeftEdgeComponentType", "") or "-")
                right_edge = str(getattr(typ, "RightEdgeComponentType", "") or "-")
                obj.TopProfileEdgeSummary = f"{left_edge}/{right_edge}"
                obj.TypicalSectionAdvancedComponentCount = int(getattr(typ, "AdvancedComponentCount", 0) or 0)
                obj.PavementLayerCount = int(getattr(typ, "PavementLayerCount", 0) or 0)
                obj.EnabledPavementLayerCount = int(getattr(typ, "EnabledPavementLayerCount", 0) or 0)
                obj.PavementTotalThickness = float(getattr(typ, "PavementTotalThickness", 0.0) or 0.0)
                obj.PavementLayerSummaryRows = list(getattr(typ, "PavementLayerSummaryRows", []) or [])
                obj.SubassemblyContractRows = list(getattr(typ, "SubassemblyContractRows", []) or [])
                obj.SubassemblyValidationRows = list(getattr(typ, "SubassemblyValidationRows", []) or [])
                obj.RoadsideLibraryRows = list(getattr(typ, "RoadsideLibraryRows", []) or [])
                obj.RoadsideLibrarySummary = str(getattr(typ, "RoadsideLibrarySummary", "-") or "-")
                obj.SectionComponentSummaryRows = list(getattr(typ, "SectionComponentSummaryRows", []) or [])
                typical_segment_rows = SectionSet._component_segment_rows_from_summary_rows(
                    [_parse_report_row(row) for row in list(getattr(typ, "SectionComponentSummaryRows", []) or [])],
                    stations,
                )
                side_slope_segment_rows = SectionSet._side_slope_segment_rows_from_assembly(
                    obj,
                    stations,
                    typical_segment_rows=typical_segment_rows,
                )
                obj.SectionComponentSegmentRows = list(typical_segment_rows) + list(side_slope_segment_rows)
                obj.PavementScheduleRows = list(getattr(typ, "PavementScheduleRows", []) or [])
            else:
                obj.SubassemblySchemaVersion = 0
                obj.PracticalSectionMode = "simple"
                obj.ReportSchemaVersion = 1
                obj.TopProfileEdgeSummary = "-"
                obj.TypicalSectionAdvancedComponentCount = 0
                obj.PavementLayerCount = 0
                obj.EnabledPavementLayerCount = 0
                obj.PavementTotalThickness = 0.0
                obj.PavementLayerSummaryRows = []
                obj.SubassemblyContractRows = []
                obj.SubassemblyValidationRows = []
                obj.RoadsideLibraryRows = []
                obj.RoadsideLibrarySummary = "-"
                obj.SectionComponentSummaryRows = []
                obj.SectionComponentSegmentRows = SectionSet._component_segment_rows_from_assembly(obj, stations)
                obj.PavementScheduleRows = []
            obj.BenchAppliedSectionCount = 0
            obj.BenchSummary = "-"
            obj.BenchSummaryRows = []
            obj.BenchDaylightAdjustedSectionCount = 0
            obj.BenchDaylightSkippedSectionCount = 0
            obj.StationValues = stations
            obj.SectionCount = len(stations)
            try:
                src0 = getattr(obj, "SourceCenterlineDisplay", None)
                aln0 = getattr(src0, "Alignment", None) if src0 is not None else None
                total0 = float(getattr(getattr(aln0, "Shape", None), "Length", 0.0) or 0.0)
                st_items, st_kind, st_obj = SectionSet._resolve_structure_station_items(
                    obj,
                    total0,
                    mode=str(getattr(obj, "Mode", "Range") or "Range"),
                    s0=float(getattr(obj, "StartStation", 0.0) or 0.0),
                    s1=float(getattr(obj, "EndStation", total0) or total0),
                )
                st_count, st_rows = SectionSet._resolved_structure_summary(st_items)
                obj.ResolvedStructureCount = int(st_count)
                obj.ResolvedStructureTags = list(st_rows)
            except Exception:
                obj.ResolvedStructureCount = 0
                obj.ResolvedStructureTags = []
                st_kind = ""
                st_obj = None
            structure_rows = []
            if bool(getattr(obj, "UseStructureSet", False)):
                if st_obj is None:
                    structure_rows.append(_report_row("structure", source="missing", stations=0, tags=0))
                elif int(getattr(obj, "ResolvedStructureCount", 0) or 0) > 0:
                    structure_rows.append(
                        _report_row(
                            "structure",
                            source=str(st_kind or "structure_set"),
                            stations=int(getattr(obj, "ResolvedStructureCount", 0) or 0),
                            tags=len(list(getattr(obj, "ResolvedStructureTags", []) or [])),
                        )
                    )
            obj.StructureInteractionSummaryRows = list(structure_rows)

            if not bool(getattr(obj, "ShowSectionWires", True)):
                obj.Shape = Part.Shape()
                obj.Status = "Hidden"
                return

            if len(stations) < 1:
                obj.Shape = Part.Shape()
                obj.Status = "No stations"
                return

            _stations, wires, terrain_found, sampler_ok, bench_info = SectionSet.build_section_wires(obj)
            if len(wires) < 1:
                obj.Shape = Part.Shape()
                obj.Status = "No section wires"
                return

            bench_left_hits = int((bench_info or {}).get("benchLeft", 0) or 0)
            bench_right_hits = int((bench_info or {}).get("benchRight", 0) or 0)
            bench_section_hits = int((bench_info or {}).get("benchSections", 0) or 0)
            bench_adjusted_hits = int((bench_info or {}).get("benchAdjusted", 0) or 0)
            bench_skipped_hits = int((bench_info or {}).get("benchSkipped", 0) or 0)
            bench_left_cfg = int((bench_info or {}).get("benchLeftConfigured", 0) or 0)
            bench_right_cfg = int((bench_info or {}).get("benchRightConfigured", 0) or 0)
            bench_mode = "-"
            if bench_left_hits > 0 and bench_right_hits > 0:
                bench_mode = "both"
            elif bench_left_hits > 0:
                bench_mode = "left"
            elif bench_right_hits > 0:
                bench_mode = "right"
            obj.BenchAppliedSectionCount = int(bench_section_hits)
            obj.BenchDaylightAdjustedSectionCount = int(bench_adjusted_hits)
            obj.BenchDaylightSkippedSectionCount = int(bench_skipped_hits)
            if bench_mode == "-":
                obj.BenchSummary = "-"
            else:
                obj.BenchSummary = (
                    f"mode={bench_mode},left={bench_left_hits}/{bench_left_cfg},"
                    f"right={bench_right_hits}/{bench_right_cfg}"
                )
            bench_rows = []
            if bench_left_hits > 0:
                bench_rows.append(
                    _report_row(
                        "bench",
                        side="left",
                        sections=bench_left_hits,
                        mode="multi" if bench_left_cfg > 1 else "single",
                        benches=bench_left_cfg,
                        daylightAdjusted=int(bench_adjusted_hits),
                        daylightSkipped=int(bench_skipped_hits),
                    )
                )
            if bench_right_hits > 0:
                bench_rows.append(
                    _report_row(
                        "bench",
                        side="right",
                        sections=bench_right_hits,
                        mode="multi" if bench_right_cfg > 1 else "single",
                        benches=bench_right_cfg,
                        daylightAdjusted=int(bench_adjusted_hits),
                        daylightSkipped=int(bench_skipped_hits),
                    )
                )
            obj.BenchSummaryRows = list(bench_rows)
            obj.ExportSummaryRows = [
                _report_row(
                    "export",
                    target="section_set",
                    reportSchema=int(getattr(obj, "ReportSchemaVersion", 1) or 1),
                    sectionSchema=int(getattr(obj, "SectionSchemaVersion", 1) or 1),
                    topProfile=str(getattr(obj, "TopProfileSource", "assembly_simple") or "assembly_simple"),
                    practical=str(getattr(obj, "PracticalSectionMode", "simple") or "simple"),
                    sections=int(len(stations)),
                    structures=int(getattr(obj, "ResolvedStructureCount", 0) or 0),
                    benchSections=int(bench_section_hits),
                    benchMode=str(bench_mode),
                    benchAdjusted=int(bench_adjusted_hits),
                    benchSkipped=int(bench_skipped_hits),
                    pavementLayers=int(getattr(obj, "EnabledPavementLayerCount", 0) or 0),
                    roadside=str(getattr(obj, "RoadsideLibrarySummary", "-") or "-"),
                )
            ]

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
                        meta = SectionSet.resolve_structure_metadata(obj, stations)
                        SectionSet.rebuild_child_sections(
                            obj,
                            stations=stations,
                            wires=wires,
                            station_tags=tags,
                            structure_meta=meta,
                        )
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
            terrain_mode = SectionSet._resolved_terrain_coord_mode(obj) if use_day else ""
            struct_src = _resolve_structure_source(obj) if bool(getattr(obj, "UseStructureSet", False)) else None
            resolved_structure_count = int(getattr(obj, "ResolvedStructureCount", 0) or 0)
            ext_count = _external_shape_display_count(struct_src)
            ext_proxy_count = _external_shape_proxy_count(struct_src)
            if use_day and (not terrain_found):
                head = "WARN: daylight=no_terrain; fixed side widths used. Add TerrainMesh or disable DaylightAuto."
                daylight_token = "daylight=fallback:no_terrain"
            elif use_day and terrain_found and (not sampler_ok):
                head = "WARN: daylight=sampler_failed; fixed side widths used. Check TerrainMeshCoords or terrain mesh validity."
                daylight_token = "daylight=fallback:sampler_failed"
            else:
                head = "OK"
                if use_day:
                    daylight_token = f"daylight=terrain:{str(terrain_mode or 'Local').lower()}"
                else:
                    daylight_token = "daylight=off"
            status_tokens = [
                daylight_token,
                f"schema={int(getattr(obj, 'SectionSchemaVersion', 1) or 1)}",
                f"topProfile={str(getattr(obj, 'TopProfileSource', 'assembly_simple') or 'assembly_simple')}",
                f"topEdges={str(getattr(obj, 'TopProfileEdgeSummary', '-') or '-')}",
            ]
            if int(getattr(obj, "SubassemblySchemaVersion", 0) or 0) > 0:
                status_tokens.append(f"subSchema={int(getattr(obj, 'SubassemblySchemaVersion', 0) or 0)}")
                status_tokens.append(f"practical={str(getattr(obj, 'PracticalSectionMode', 'simple') or 'simple')}")
            if str(getattr(obj, "RoadsideLibrarySummary", "-") or "-") != "-":
                status_tokens.append(f"roadside={str(getattr(obj, 'RoadsideLibrarySummary', '-') or '-')}")
            if int(getattr(obj, "BenchAppliedSectionCount", 0) or 0) > 0:
                status_tokens.append(f"bench={bench_mode}")
                status_tokens.append(f"benchSections={int(getattr(obj, 'BenchAppliedSectionCount', 0) or 0)}")
                if int(getattr(obj, "BenchDaylightAdjustedSectionCount", 0) or 0) > 0:
                    status_tokens.append(f"benchDayAdj={int(getattr(obj, 'BenchDaylightAdjustedSectionCount', 0) or 0)}")
                if int(getattr(obj, "BenchDaylightSkippedSectionCount", 0) or 0) > 0:
                    status_tokens.append(f"benchDaySkip={int(getattr(obj, 'BenchDaylightSkippedSectionCount', 0) or 0)}")
            if len(list(getattr(obj, "SubassemblyValidationRows", []) or [])) > 0:
                status_tokens.append(f"subWarn={len(list(getattr(obj, 'SubassemblyValidationRows', []) or []))}")
            if int(getattr(obj, "TypicalSectionAdvancedComponentCount", 0) or 0) > 0:
                status_tokens.append(f"typicalAdvanced={int(getattr(obj, 'TypicalSectionAdvancedComponentCount', 0) or 0)}")
            if float(getattr(obj, "PavementTotalThickness", 0.0) or 0.0) > 1e-9:
                status_tokens.append(f"pavement={float(getattr(obj, 'PavementTotalThickness', 0.0) or 0.0):.3f}m")
            if int(getattr(obj, "PavementLayerCount", 0) or 0) > 0:
                status_tokens.append(
                    f"pavLayers={int(getattr(obj, 'EnabledPavementLayerCount', 0) or 0)}/{int(getattr(obj, 'PavementLayerCount', 0) or 0)}"
                )
            status_tokens.append(
                _earthwork_status_token(
                    struct_src=struct_src,
                    resolved_count=resolved_structure_count,
                    ext_count=ext_count,
                    proxy_count=ext_proxy_count,
                    overrides_enabled=bool(getattr(obj, "ApplyStructureOverrides", False)),
                )
            )
            if bool(getattr(obj, "UseStructureSet", False)) and struct_src is None:
                status_tokens.append("StructureSet missing")
            elif resolved_structure_count > 0:
                status_tokens.append(f"structures={resolved_structure_count}")
            if ext_count > 0:
                status_tokens.append(_display_only_status_token(ext_count))
                status_tokens.append(f"externalShapeDisplayOnly={int(ext_count)}")
            if ext_proxy_count > 0:
                status_tokens.append(f"externalShapeProxy={int(ext_proxy_count)}")
            if bool(getattr(obj, "ApplyStructureOverrides", False)):
                ovh = int((bench_info or {}).get("overrideHits", 0) or 0)
                status_tokens.append(f"overrides={ovh}")
            obj.Status = _status_join(head, *status_tokens)

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
            obj.TopProfileEdgeSummary = "-"
            obj.SubassemblySchemaVersion = 0
            obj.PracticalSectionMode = "fallback"
            obj.TypicalSectionAdvancedComponentCount = 0
            obj.PavementLayerCount = 0
            obj.EnabledPavementLayerCount = 0
            obj.PavementTotalThickness = 0.0
            obj.PavementLayerSummaryRows = []
            obj.SubassemblyContractRows = []
            obj.SubassemblyValidationRows = []
            obj.RoadsideLibraryRows = []
            obj.RoadsideLibrarySummary = "-"
            obj.ReportSchemaVersion = 1
            obj.SectionComponentSummaryRows = []
            obj.SectionComponentSegmentRows = []
            obj.PavementScheduleRows = []
            obj.StructureInteractionSummaryRows = []
            obj.ExportSummaryRows = []
            obj.BenchAppliedSectionCount = 0
            obj.BenchSummary = "-"
            obj.BenchSummaryRows = []
            obj.BenchDaylightAdjustedSectionCount = 0
            obj.BenchDaylightSkippedSectionCount = 0
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "SourceCenterlineDisplay",
            "AssemblyTemplate",
            "TypicalSectionTemplate",
            "UseTypicalSectionTemplate",
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
            "StructureSet",
            "UseStructureSet",
            "IncludeStructureStartEnd",
            "IncludeStructureCenters",
            "IncludeStructureTransitionStations",
            "AutoStructureTransitionDistance",
            "StructureTransitionDistance",
            "StructureBufferBefore",
            "StructureBufferAfter",
            "CreateStructureTaggedChildren",
            "ApplyStructureOverrides",
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
