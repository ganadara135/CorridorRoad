# CorridorRoad/objects/obj_corridor_loft.py
import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_section_set import SectionSet, _resolve_structure_source
from freecad.Corridor_Road.objects.obj_structure_set import (
    StructureSet as StructureSetSource,
    _build_structure_solid as _structure_record_solid,
    _resolve_alignment as _resolve_structure_alignment,
    _resolve_station_point as _resolve_structure_station_point,
    _side_offsets as _structure_side_offsets,
)
from freecad.Corridor_Road.objects.obj_project import get_length_scale

_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_finite(x: float) -> bool:
    return math.isfinite(float(x))


def _dedupe_consecutive_points(points, tol: float = 1e-9):
    out = []
    for p in points:
        if not out:
            out.append(p)
            continue
        if (p - out[-1]).Length > tol:
            out.append(p)
    return out


def _merge_station_spans(spans, tol: float = 1e-6):
    rows = sorted(
        [(float(a), float(b), str(m or "")) for (a, b, m) in list(spans or []) if float(b) >= float(a)],
        key=lambda it: (it[0], it[1], it[2]),
    )
    out = []
    for s0, s1, mode in rows:
        if not out:
            out.append([s0, s1, mode])
            continue
        prev = out[-1]
        if str(prev[2]) == str(mode) and s0 <= float(prev[1]) + tol:
            prev[1] = max(float(prev[1]), float(s1))
        else:
            out.append([s0, s1, mode])
    return [(float(a), float(b), str(m)) for a, b, m in out]


def _mark_recompute_flag(obj, needed: bool):
    try:
        if hasattr(obj, "NeedsRecompute"):
            obj.NeedsRecompute = bool(needed)
    except Exception:
        pass

    try:
        label = str(getattr(obj, "Label", "") or "")
        if bool(needed):
            if _RECOMP_LABEL_SUFFIX not in label:
                obj.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
        else:
            if _RECOMP_LABEL_SUFFIX in label:
                obj.Label = label.replace(_RECOMP_LABEL_SUFFIX, "")
    except Exception:
        pass


def ensure_corridor_loft_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    # Hard-remove legacy thickness properties.
    for legacy_prop in ("PavementThickness", "SolidThickness", "ResolvedPavementThickness"):
        try:
            if hasattr(obj, legacy_prop):
                obj.removeProperty(legacy_prop)
        except Exception:
            pass

    if not hasattr(obj, "SourceSectionSet"):
        obj.addProperty("App::PropertyLink", "SourceSectionSet", "Corridor", "SectionSet source")

    if not hasattr(obj, "OutputType"):
        obj.addProperty("App::PropertyEnumeration", "OutputType", "Corridor", "Output type")
    # Solid-only policy.
    try:
        obj.OutputType = ["Solid"]
        obj.OutputType = "Solid"
    except Exception:
        pass

    if not hasattr(obj, "HeightLeft"):
        obj.addProperty("App::PropertyFloat", "HeightLeft", "Corridor", "Fallback left depth (m, downward)")
        obj.HeightLeft = 0.30

    if not hasattr(obj, "HeightRight"):
        obj.addProperty("App::PropertyFloat", "HeightRight", "Corridor", "Fallback right depth (m, downward)")
        obj.HeightRight = 0.30

    if not hasattr(obj, "UseRuled"):
        obj.addProperty("App::PropertyBool", "UseRuled", "Corridor", "Use ruled loft")
        obj.UseRuled = False

    if not hasattr(obj, "MinSectionSpacing"):
        obj.addProperty("App::PropertyFloat", "MinSectionSpacing", "Corridor", "Minimum station spacing for loft input (m)")
        obj.MinSectionSpacing = 0.50 * scale

    if not hasattr(obj, "AutoFixSectionOrientation"):
        obj.addProperty(
            "App::PropertyBool",
            "AutoFixSectionOrientation",
            "Corridor",
            "Auto-fix flipped section orientation against neighboring section input",
        )
        obj.AutoFixSectionOrientation = True

    if not hasattr(obj, "SplitAtStructureZones"):
        obj.addProperty(
            "App::PropertyBool",
            "SplitAtStructureZones",
            "Corridor",
            "Split loft into segments at structure-zone boundaries when StructureSet-driven sections are used",
        )
        obj.SplitAtStructureZones = True

    if not hasattr(obj, "UseStructureCorridorModes"):
        obj.addProperty(
            "App::PropertyBool",
            "UseStructureCorridorModes",
            "Corridor",
            "Use structure corridor modes such as skip_zone when StructureSet data is available",
        )
        obj.UseStructureCorridorModes = True

    if not hasattr(obj, "DefaultStructureCorridorMode"):
        obj.addProperty(
            "App::PropertyEnumeration",
            "DefaultStructureCorridorMode",
            "Corridor",
            "Fallback corridor mode when a structure record does not specify one",
        )
        obj.DefaultStructureCorridorMode = ["none", "split_only", "skip_zone"]
        obj.DefaultStructureCorridorMode = "split_only"

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "Corridor", "Auto update from source changes")
        obj.AutoUpdate = True

    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "Corridor", "Set True to force rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "SectionCount"):
        obj.addProperty("App::PropertyInteger", "SectionCount", "Result", "Used section count")
        obj.SectionCount = 0

    if not hasattr(obj, "PointCountPerSection"):
        obj.addProperty("App::PropertyInteger", "PointCountPerSection", "Result", "Point count per section")
        obj.PointCountPerSection = 0

    if not hasattr(obj, "AutoFixedSectionCount"):
        obj.addProperty("App::PropertyInteger", "AutoFixedSectionCount", "Result", "Auto-fixed section count")
        obj.AutoFixedSectionCount = 0

    if not hasattr(obj, "SchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SchemaVersion", "Result", "Section schema version used")
        obj.SchemaVersion = 0

    if not hasattr(obj, "FailedRanges"):
        obj.addProperty("App::PropertyStringList", "FailedRanges", "Result", "Failed ranges during segmented fallback")
        obj.FailedRanges = []

    if not hasattr(obj, "StructureSegmentCount"):
        obj.addProperty("App::PropertyInteger", "StructureSegmentCount", "Result", "Number of structure-aware loft segments used")
        obj.StructureSegmentCount = 0

    if not hasattr(obj, "StructureSplitStations"):
        obj.addProperty("App::PropertyStringList", "StructureSplitStations", "Result", "Stations used as structure-aware split boundaries")
        obj.StructureSplitStations = []

    if not hasattr(obj, "SkippedStationRanges"):
        obj.addProperty("App::PropertyStringList", "SkippedStationRanges", "Result", "Station spans skipped by structure corridor modes")
        obj.SkippedStationRanges = []

    if not hasattr(obj, "ResolvedStructureNotchCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedStructureNotchCount", "Result", "Number of structure notch cuts applied")
        obj.ResolvedStructureNotchCount = 0

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"

    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "ResolvedHeightLeft"):
        obj.addProperty("App::PropertyFloat", "ResolvedHeightLeft", "Result", "Resolved left depth used for solid")
        obj.ResolvedHeightLeft = 0.0

    if not hasattr(obj, "ResolvedHeightRight"):
        obj.addProperty("App::PropertyFloat", "ResolvedHeightRight", "Result", "Resolved right depth used for solid")
        obj.ResolvedHeightRight = 0.0

    try:
        if hasattr(obj, "OutputType"):
            obj.setEditorMode("OutputType", 2)
    except Exception:
        pass


class CorridorLoft:
    """
    Corridor loft from SectionSet (Solid-only).
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CorridorLoft"
        ensure_corridor_loft_properties(obj)

    @staticmethod
    def _wire_points(wire):
        edges = list(getattr(wire, "Edges", []) or [])
        if not edges:
            return []
        pts = [edges[0].valueAt(edges[0].FirstParameter)]
        for e in edges:
            pts.append(e.valueAt(e.LastParameter))
        return _dedupe_consecutive_points(pts)

    @staticmethod
    def _make_wire(points):
        return Part.makePolygon(points)

    @staticmethod
    def _should_flip_points(prev_pts, pts):
        if prev_pts is None or len(prev_pts) != len(pts):
            return False

        rev_pts = list(reversed(pts))
        direct_score = sum((pts[i] - prev_pts[i]).Length for i in range(len(pts)))
        flip_score = sum((rev_pts[i] - prev_pts[i]).Length for i in range(len(pts)))

        axis_prev = prev_pts[-1] - prev_pts[0]
        axis_curr = pts[-1] - pts[0]
        if axis_prev.Length > 1e-9 and axis_curr.Length > 1e-9:
            axis_prev = axis_prev.normalize()
            axis_curr = axis_curr.normalize()
            if axis_prev.dot(axis_curr) < 0.0 and flip_score <= (direct_score * 1.02 + 1e-6):
                return True

        return flip_score + 1e-6 < (direct_score * 0.85)

    @staticmethod
    def _validate_and_normalize(stations, wires, schema_version: int, auto_fix_orientation: bool):
        if len(stations) < 2 or len(wires) < 2:
            raise Exception("Need at least 2 sections for loft.")
        if len(stations) != len(wires):
            raise Exception("Stations/wires size mismatch.")

        st = [float(s) for s in stations]
        for i, s in enumerate(st):
            if not _is_finite(s):
                raise Exception(f"Station[{i}] is not finite.")
            if i >= 1 and s <= st[i - 1] + 1e-9:
                raise Exception("Station values must be strictly increasing.")

        pt_lists = []
        for i, w in enumerate(wires):
            pts = CorridorLoft._wire_points(w)
            if len(pts) < 2:
                raise Exception(f"Section[{i}] has insufficient points.")
            for j, p in enumerate(pts):
                if not (_is_finite(p.x) and _is_finite(p.y) and _is_finite(p.z)):
                    raise Exception(f"Section[{i}] point[{j}] is not finite.")
            for j in range(len(pts) - 1):
                if (pts[j + 1] - pts[j]).Length <= 1e-12:
                    raise Exception(f"Section[{i}] has duplicate critical points.")
            pt_lists.append(pts)

        ref_n = len(pt_lists[0])
        for i, pts in enumerate(pt_lists):
            if len(pts) != ref_n:
                raise Exception(
                    f"Section point count mismatch at index {i}: {len(pts)} != {ref_n}. "
                    "Loft stopped by section contract."
                )

        if int(schema_version) == 1 and ref_n != 3:
            raise Exception(
                f"SchemaVersion=1 requires 3 points (Left->Center->Right), but got {ref_n}."
            )

        out_wires = []
        prev_pts = None
        fixed_count = 0
        for i, pts in enumerate(pt_lists):
            if bool(auto_fix_orientation) and CorridorLoft._should_flip_points(prev_pts, pts):
                pts = list(reversed(pts))
                fixed_count += 1
            axis = pts[0] - pts[-1]
            if axis.Length <= 1e-12:
                raise Exception(f"Section[{i}] left/right axis is degenerate.")
            out_wires.append(CorridorLoft._make_wire(pts))
            prev_pts = pts

        return out_wires, ref_n, fixed_count

    @staticmethod
    def _filter_close_sections(stations, wires, min_spacing: float):
        if len(stations) != len(wires):
            raise Exception("Stations/wires size mismatch.")
        if len(stations) <= 2:
            return list(stations), list(wires), 0

        dmin = max(0.0, float(min_spacing))
        if dmin <= 1e-9:
            return list(stations), list(wires), 0

        out_st = [float(stations[0])]
        out_wr = [wires[0]]
        dropped = 0

        for i in range(1, len(stations)):
            s = float(stations[i])
            if (s - float(out_st[-1])) < dmin:
                dropped += 1
                continue
            out_st.append(s)
            out_wr.append(wires[i])

        # Keep at least 2 sections for loft contract.
        if len(out_st) < 2 and len(stations) >= 2:
            return [float(stations[0]), float(stations[-1])], [wires[0], wires[-1]], max(0, len(stations) - 2)
        return out_st, out_wr, dropped

    @staticmethod
    def _valid_heights(h_left: float, h_right: float):
        if not (_is_finite(h_left) and _is_finite(h_right)):
            return False
        if h_left < -1e-9 or h_right < -1e-9:
            return False
        return max(float(h_left), float(h_right)) > 1e-6

    @staticmethod
    def _make_closed_profiles_for_solid(open_wires, h_left: float, h_right: float):
        hl = float(h_left)
        hr = float(h_right)
        if not CorridorLoft._valid_heights(hl, hr):
            raise Exception("HeightLeft/HeightRight must be finite, non-negative, and at least one > 0.")

        closed = []
        for i, w in enumerate(open_wires):
            up = CorridorLoft._wire_points(w)
            if len(up) < 2:
                raise Exception(f"Section[{i}] has insufficient points for solid profile.")

            n = len(up)
            dn = []
            for j, p in enumerate(up):
                alpha = float(j) / float(n - 1) if n > 1 else 0.5
                h = (1.0 - alpha) * hl + alpha * hr
                dn.append(App.Vector(p.x, p.y, p.z - h))

            poly = list(up) + list(reversed(dn))
            poly.append(poly[0])
            closed.append(Part.makePolygon(poly))
        return closed

    @staticmethod
    def _resolve_heights(obj, src):
        asm = getattr(src, "AssemblyTemplate", None) if src is not None else None
        if asm is not None:
            try:
                hl = float(getattr(asm, "HeightLeft"))
                hr = float(getattr(asm, "HeightRight"))
                if CorridorLoft._valid_heights(hl, hr):
                    return hl, hr, "AssemblyTemplate.HeightLeft/HeightRight"
            except Exception:
                pass

        try:
            hl = float(getattr(obj, "HeightLeft"))
            hr = float(getattr(obj, "HeightRight"))
            if CorridorLoft._valid_heights(hl, hr):
                return hl, hr, "CorridorLoft.HeightLeft/HeightRight"
        except Exception:
            pass

        raise Exception("Valid HeightLeft/HeightRight are required for Solid output.")

    @staticmethod
    def _loft(wires, ruled: bool, solid: bool = True):
        return Part.makeLoft(wires, bool(solid), bool(ruled), False)

    @staticmethod
    def _loft_adaptive(wires, stations, ruled: bool, solid: bool = True):
        parts = []
        failed = []

        def _run(i0: int, i1: int):
            try:
                seg = CorridorLoft._loft(wires[i0 : i1 + 1], ruled=ruled, solid=solid)
                parts.append((i0, seg))
            except Exception as ex:
                if (i1 - i0) <= 1:
                    failed.append(f"{float(stations[i0]):.3f}-{float(stations[i1]):.3f}: {ex}")
                    return
                mid = (i0 + i1) // 2
                if mid <= i0 or mid >= i1:
                    failed.append(f"{float(stations[i0]):.3f}-{float(stations[i1]):.3f}: {ex}")
                    return
                _run(i0, mid)
                _run(mid, i1)

        _run(0, len(wires) - 1)

        if not parts:
            raise Exception("Adaptive segmented loft failed for all ranges.")

        parts.sort(key=lambda it: int(it[0]))
        shapes = [it[1] for it in parts]
        shape = shapes[0] if len(shapes) == 1 else Part.Compound(shapes)
        return shape, failed

    @staticmethod
    def _structure_split_candidates(src, stations):
        try:
            if not bool(getattr(src, "UseStructureSet", False)):
                return [], []
            meta = SectionSet.resolve_structure_metadata(src, stations)
        except Exception:
            return [], []

        if not meta or len(meta) != len(stations):
            return [], []

        candidates = []
        split_station_rows = []
        prev_has = bool(meta[0].get("HasStructure", False)) if meta else False
        for i in range(1, len(stations)):
            curr_meta = meta[i]
            prev_meta = meta[i - 1]
            curr_has = bool(curr_meta.get("HasStructure", False))
            prev_roles = {str(v or "").strip().lower() for v in list(prev_meta.get("StructureRoles", []) or [])}
            curr_roles = {str(v or "").strip().lower() for v in list(curr_meta.get("StructureRoles", []) or [])}

            split_here = False
            if curr_has != prev_has:
                split_here = True
            elif ("start" in curr_roles) or ("transition_before" in curr_roles):
                split_here = True
            elif ("end" in prev_roles) or ("transition_after" in prev_roles):
                split_here = True

            if split_here:
                candidates.append(i)
                split_station_rows.append(f"{float(stations[i]):.3f}")
            prev_has = curr_has

        # Deduplicate while preserving order.
        dedup_idx = []
        dedup_sta = []
        seen = set()
        for idx, sta in zip(candidates, split_station_rows):
            if idx in seen:
                continue
            seen.add(idx)
            dedup_idx.append(int(idx))
            dedup_sta.append(str(sta))
        return dedup_idx, dedup_sta

    @staticmethod
    def _resolve_structure_corridor_spans(src, fallback_mode: str = "split_only"):
        try:
            if not bool(getattr(src, "UseStructureSet", False)):
                return []
            ss = _resolve_structure_source(src)
            if ss is None:
                return []
            rows = StructureSetSource.corridor_zone_records(ss, fallback_mode=fallback_mode)
        except Exception:
            return []

        spans = []
        for rec in rows:
            mode = str(rec.get("ResolvedCorridorMode", "") or "").strip().lower()
            if mode in ("", "none", "split_only"):
                continue
            s0 = float(rec.get("ResolvedStartStation", 0.0) or 0.0)
            s1 = float(rec.get("ResolvedEndStation", 0.0) or 0.0)
            mg = max(0.0, float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0))
            lo = min(s0, s1) - mg
            hi = max(s0, s1) + mg
            spans.append((lo, hi, mode))
        return _merge_station_spans(spans)

    @staticmethod
    def _resolve_structure_corridor_records(src, fallback_mode: str = "split_only"):
        try:
            if not bool(getattr(src, "UseStructureSet", False)):
                return []
            ss = _resolve_structure_source(src)
            if ss is None:
                return []
            return StructureSetSource.corridor_zone_records(ss, fallback_mode=fallback_mode)
        except Exception:
            return []

    @staticmethod
    def _skip_zone_keep_ranges(stations, skip_spans):
        n = len(list(stations or []))
        if n < 2 or not skip_spans:
            return [], []

        skip_mask = [False] * n
        tol = 1e-6
        for s0, s1, mode in list(skip_spans or []):
            if str(mode or "").strip().lower() != "skip_zone":
                continue
            lo = float(min(s0, s1))
            hi = float(max(s0, s1))
            for i, s in enumerate(stations):
                ss = float(s)
                if ss >= lo - tol and ss <= hi + tol:
                    skip_mask[i] = True

        keep_ranges = []
        skipped_rows = []
        i = 0
        while i < n:
            if skip_mask[i]:
                j = i
                while j + 1 < n and skip_mask[j + 1]:
                    j += 1
                skipped_rows.append(f"{float(stations[i]):.3f}-{float(stations[j]):.3f}")
                i = j + 1
            else:
                i += 1

        # Build keep ranges from non-skipped runs, including boundary stations shared at gaps.
        keep_ranges = []
        start = 0
        while start < n:
            while start < n and skip_mask[start]:
                start += 1
            if start >= n:
                break
            end = start
            while end + 1 < n and not skip_mask[end + 1]:
                end += 1
            if start > 0:
                start = start - 1
            if end < (n - 1):
                end = end + 1
            if (end - start + 1) >= 2:
                if not keep_ranges or keep_ranges[-1] != (start, end):
                    keep_ranges.append((start, end))
            start = end + 1

        dedup = []
        seen = set()
        for i0, i1 in keep_ranges:
            key = (int(i0), int(i1))
            if key in seen:
                continue
            seen.add(key)
            dedup.append(key)

        dedup = [(int(a), int(b)) for a, b in dedup if (int(b) - int(a) + 1) >= 2]
        return dedup, skipped_rows

    @staticmethod
    def _build_notch_cutters(src, corridor_records):
        aln = _resolve_structure_alignment(src)
        if aln is None or getattr(aln, "Shape", None) is None:
            return [], []
        total = float(getattr(aln.Shape, "Length", 0.0) or 0.0)
        cutters = []
        notes = []
        for rec in list(corridor_records or []):
            mode = str(rec.get("ResolvedCorridorMode", "") or "").strip().lower()
            if mode != "notch":
                continue
            try:
                local = dict(rec)
                mg = max(0.0, float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0))
                local["StartStation"] = max(0.0, float(rec.get("ResolvedStartStation", 0.0) or 0.0) - mg)
                local["EndStation"] = min(total, float(rec.get("ResolvedEndStation", 0.0) or 0.0) + mg)
                if float(local["EndStation"]) < float(local["StartStation"]):
                    local["StartStation"], local["EndStation"] = local["EndStation"], local["StartStation"]
                sta = max(0.0, min(total, 0.5 * (float(local["StartStation"]) + float(local["EndStation"]))))
                p = _resolve_structure_station_point(src, sta, aln=aln)
                try:
                    from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment

                    t = HorizontalAlignment.tangent_at_station(aln, sta)
                    n = HorizontalAlignment.normal_at_station(aln, sta)
                except Exception:
                    t = App.Vector(1, 0, 0)
                    n = App.Vector(0, 1, 0)
                built = 0
                for off in _structure_side_offsets(local):
                    solid = _structure_record_solid(p + (n * float(off)), t, n, local)
                    if solid is not None and not solid.isNull():
                        cutters.append(solid)
                        built += 1
                if built <= 0:
                    rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                    notes.append(f"{rid}: notch cutter skipped")
            except Exception as ex:
                rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                notes.append(f"{rid}: notch cutter failed ({ex})")
        return cutters, notes

    @staticmethod
    def _apply_notch_cuts(shape, cutters):
        if shape is None or getattr(shape, "isNull", lambda: True)():
            return shape, 0, []
        if not cutters:
            return shape, 0, []
        out = shape
        count = 0
        failed = []
        for i, cutter in enumerate(list(cutters or [])):
            try:
                if cutter is None or cutter.isNull():
                    continue
                out = out.cut(cutter)
                count += 1
            except Exception as ex:
                failed.append(f"notch[{i}]: {ex}")
        return out, count, failed

    @staticmethod
    def _segment_ranges(count: int, boundaries):
        if count < 2:
            return []
        ranges = []
        start = 0
        for b in sorted({int(v) for v in list(boundaries or []) if int(v) > 0 and int(v) < count}):
            # Keep the split station shared by both neighboring segments so the
            # corridor skin remains continuous across the structure boundary.
            if (b - start + 1) < 2:
                continue
            if (count - b) < 2:
                continue
            ranges.append((start, b))
            start = b
        ranges.append((start, count - 1))
        return [(i0, i1) for (i0, i1) in ranges if (i1 - i0 + 1) >= 2]

    @staticmethod
    def _loft_by_ranges(wires, stations, ranges, ruled: bool, solid: bool = True):
        if not ranges:
            return CorridorLoft._loft(wires, ruled=ruled, solid=solid), []

        shapes = []
        failed_ranges = []
        for i0, i1 in ranges:
            seg_wires = list(wires[i0 : i1 + 1])
            seg_sta = list(stations[i0 : i1 + 1])
            try:
                shp = CorridorLoft._loft(seg_wires, ruled=ruled, solid=solid)
            except Exception as ex:
                shp, failed = CorridorLoft._loft_adaptive(seg_wires, seg_sta, ruled=ruled, solid=solid)
                if failed:
                    failed_ranges.extend(list(failed))
                else:
                    failed_ranges.append(f"{float(seg_sta[0]):.3f}-{float(seg_sta[-1]):.3f}: {ex}")
            shapes.append(shp)

        if not shapes:
            raise Exception("Structure-aware segmented loft failed for all ranges.")
        return (shapes[0] if len(shapes) == 1 else Part.Compound(shapes)), failed_ranges

    def execute(self, obj):
        ensure_corridor_loft_properties(obj)
        try:
            src = getattr(obj, "SourceSectionSet", None)
            if src is None:
                obj.Shape = Part.Shape()
                obj.SectionCount = 0
                obj.PointCountPerSection = 0
                obj.AutoFixedSectionCount = 0
                obj.SchemaVersion = 0
                obj.FailedRanges = []
                obj.StructureSegmentCount = 0
                obj.StructureSplitStations = []
                obj.SkippedStationRanges = []
                obj.ResolvedStructureNotchCount = 0
                obj.ResolvedHeightLeft = 0.0
                obj.ResolvedHeightRight = 0.0
                obj.Status = "Missing SourceSectionSet"
                _mark_recompute_flag(obj, False)
                return

            stations, wires, _tf, _so = SectionSet.build_section_wires(src)
            min_spacing = max(0.0, float(getattr(obj, "MinSectionSpacing", 0.0)))
            stations, wires, dropped = CorridorLoft._filter_close_sections(stations, wires, min_spacing)
            schema = int(getattr(src, "SectionSchemaVersion", 1))

            auto_fix_orientation = bool(getattr(obj, "AutoFixSectionOrientation", True))
            norm_wires, pt_count, fixed_count = CorridorLoft._validate_and_normalize(
                stations,
                wires,
                schema,
                auto_fix_orientation,
            )
            ruled = bool(getattr(obj, "UseRuled", False))
            h_left, h_right, height_source = CorridorLoft._resolve_heights(obj, src)
            loft_wires = CorridorLoft._make_closed_profiles_for_solid(norm_wires, h_left, h_right)
            split_count = 0
            split_station_rows = []
            structure_ranges = []
            skipped_station_rows = []
            fallback_mode = str(getattr(obj, "DefaultStructureCorridorMode", "split_only") or "split_only").strip().lower()
            corridor_records = CorridorLoft._resolve_structure_corridor_records(src, fallback_mode=fallback_mode)
            use_segmented_ranges = False
            if bool(getattr(obj, "SplitAtStructureZones", True)):
                split_idx, split_station_rows = CorridorLoft._structure_split_candidates(src, stations)
                structure_ranges = CorridorLoft._segment_ranges(len(stations), split_idx)
                split_count = len(structure_ranges) if structure_ranges else 0
                use_segmented_ranges = bool(structure_ranges and len(structure_ranges) >= 2)
            if bool(getattr(obj, "UseStructureCorridorModes", True)):
                structure_spans = _merge_station_spans(
                    [
                        (
                            float(rec.get("ResolvedStartStation", 0.0) or 0.0) - max(0.0, float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0)),
                            float(rec.get("ResolvedEndStation", 0.0) or 0.0) + max(0.0, float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0)),
                            str(rec.get("ResolvedCorridorMode", "") or ""),
                        )
                        for rec in list(corridor_records or [])
                    ]
                )
                skip_ranges, skipped_station_rows = CorridorLoft._skip_zone_keep_ranges(stations, structure_spans)
                if skip_ranges:
                    structure_ranges = list(skip_ranges)
                    split_count = len(structure_ranges) if structure_ranges else 0
                    use_segmented_ranges = bool(
                        structure_ranges
                        and not (len(structure_ranges) == 1 and structure_ranges[0] == (0, len(stations) - 1))
                    )
                elif skipped_station_rows:
                    raise Exception("All corridor sections fall inside skip_zone structure spans.")

            failed_ranges = []
            notch_count = 0
            notch_failures = []
            try:
                if use_segmented_ranges:
                    shape, failed_ranges = CorridorLoft._loft_by_ranges(
                        loft_wires, stations, structure_ranges, ruled=ruled, solid=True
                    )
                else:
                    shape = CorridorLoft._loft(loft_wires, ruled=ruled, solid=True)
                if bool(getattr(obj, "UseStructureCorridorModes", True)):
                    notch_cutters, notch_notes = CorridorLoft._build_notch_cutters(src, corridor_records)
                    if notch_notes:
                        notch_failures.extend(list(notch_notes))
                    shape, notch_count, notch_failed = CorridorLoft._apply_notch_cuts(shape, notch_cutters)
                    if notch_failed:
                        notch_failures.extend(list(notch_failed))
                if failed_ranges:
                    status = (
                        "WARN (Solid): structure-aware segmented fallback used "
                        f"({len(failed_ranges)} failed ranges) | "
                        f"hL={float(h_left):.3f}m hR={float(h_right):.3f}m from {height_source} | "
                        f"minSpacing={float(min_spacing):.3f} used={len(stations)} dropped={int(dropped)} "
                        f"autoFixed={int(fixed_count)}"
                    )
                else:
                    status = (
                        "OK (Solid) "
                        f"hL={float(h_left):.3f}m hR={float(h_right):.3f}m from {height_source} | "
                        f"minSpacing={float(min_spacing):.3f} used={len(stations)} dropped={int(dropped)} "
                        f"autoFixed={int(fixed_count)}"
                    )
                if split_count >= 2:
                    status += f" structureSegs={int(split_count)}"
                if skipped_station_rows:
                    status += f" skipZones={len(skipped_station_rows)}"
                if notch_count > 0:
                    status += f" notches={int(notch_count)}"
                if notch_failures:
                    status += f" notchWarn={len(notch_failures)}"
            except Exception as ex:
                if use_segmented_ranges:
                    shape, failed_ranges = CorridorLoft._loft_by_ranges(
                        loft_wires, stations, structure_ranges, ruled=ruled, solid=True
                    )
                else:
                    shape, failed_ranges = CorridorLoft._loft_adaptive(
                        loft_wires, stations, ruled=ruled, solid=True
                    )
                if bool(getattr(obj, "UseStructureCorridorModes", True)):
                    notch_cutters, notch_notes = CorridorLoft._build_notch_cutters(src, corridor_records)
                    if notch_notes:
                        notch_failures.extend(list(notch_notes))
                    shape, notch_count, notch_failed = CorridorLoft._apply_notch_cuts(shape, notch_cutters)
                    if notch_failed:
                        notch_failures.extend(list(notch_failed))
                status = (
                    "WARN (Solid): full loft failed, adaptive fallback used "
                    f"({len(failed_ranges)} failed ranges): {ex} | "
                    f"hL={float(h_left):.3f}m hR={float(h_right):.3f}m from {height_source} | "
                    f"minSpacing={float(min_spacing):.3f} used={len(stations)} dropped={int(dropped)} "
                    f"autoFixed={int(fixed_count)}"
                )
                if split_count >= 2:
                    status += f" structureSegs={int(split_count)}"
                if skipped_station_rows:
                    status += f" skipZones={len(skipped_station_rows)}"
                if notch_count > 0:
                    status += f" notches={int(notch_count)}"
                if notch_failures:
                    status += f" notchWarn={len(notch_failures)}"

            obj.Shape = shape
            obj.SectionCount = len(stations)
            obj.PointCountPerSection = int(pt_count)
            obj.AutoFixedSectionCount = int(fixed_count)
            obj.SchemaVersion = int(schema)
            obj.FailedRanges = list(failed_ranges)
            obj.StructureSegmentCount = int(split_count)
            obj.StructureSplitStations = list(split_station_rows)
            obj.SkippedStationRanges = list(skipped_station_rows)
            obj.ResolvedStructureNotchCount = int(notch_count)
            obj.ResolvedHeightLeft = float(h_left)
            obj.ResolvedHeightRight = float(h_right)
            obj.Status = status
            _mark_recompute_flag(obj, False)

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SectionCount = 0
            obj.PointCountPerSection = 0
            obj.AutoFixedSectionCount = 0
            obj.SchemaVersion = 0
            obj.FailedRanges = []
            obj.StructureSegmentCount = 0
            obj.StructureSplitStations = []
            obj.SkippedStationRanges = []
            obj.ResolvedStructureNotchCount = 0
            obj.ResolvedHeightLeft = 0.0
            obj.ResolvedHeightRight = 0.0
            obj.Status = f"ERROR: {ex}"
            _mark_recompute_flag(obj, False)

    def onChanged(self, obj, prop):
        if prop in (
            "SourceSectionSet",
            "OutputType",
            "HeightLeft",
            "HeightRight",
            "UseRuled",
            "MinSectionSpacing",
            "AutoFixSectionOrientation",
            "SplitAtStructureZones",
            "UseStructureCorridorModes",
            "DefaultStructureCorridorMode",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                obj.touch()
                # Avoid forced recompute on every property-editor keystroke.
                # FreeCAD will recompute on confirmed edit; only force when user
                # explicitly requests rebuild.
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)):
                    if obj.Document is not None:
                        obj.Document.recompute()
            except Exception:
                pass


class ViewProviderCorridorLoft:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Flat Lines"
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
        return ["Wireframe", "Flat Lines", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode
