# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_centerline3d_display.py
import Part

from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_project import find_region_plan_objects
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet
from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment


def _unique_sorted(values, tol: float = 1e-6):
    vals = sorted([float(v) for v in values])
    out = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _alignment_edge_boundaries(aln):
    if aln is None or aln.Shape is None or aln.Shape.isNull():
        return []

    vals = [0.0]
    acc = 0.0
    for e in list(aln.Shape.Edges):
        acc += float(e.Length)
        vals.append(_units.meters_from_model_length(getattr(aln, "Document", None), float(acc)))
    return vals


def _vertical_key_stations(va):
    if va is None:
        return []

    vals = []
    try:
        pvis, _grades, curves = VerticalAlignment._solve_curves(va)
        if pvis:
            vals.append(float(pvis[0][0]))
            vals.append(float(pvis[-1][0]))
        for c in curves:
            vals.append(float(c["bvc"]))
            vals.append(float(c["evc"]))
    except Exception:
        return []
    return vals


def _horizontal_key_rows(aln):
    if aln is None:
        return []
    rows = []

    def _append_many(values, source):
        for value in list(values or []):
            try:
                rows.append((float(value), str(source)))
            except Exception:
                pass

    _append_many(getattr(aln, "IPKeyStations", []), "ip_key")
    _append_many(getattr(aln, "TSKeyStations", []), "ts_key")
    _append_many(getattr(aln, "SCKeyStations", []), "sc_key")
    _append_many(getattr(aln, "CSKeyStations", []), "cs_key")
    _append_many(getattr(aln, "STKeyStations", []), "st_key")
    return rows


def _vertical_key_rows(va):
    if va is None:
        return []
    rows = []
    try:
        pvis, _grades, curves = VerticalAlignment._solve_curves(va)
        if pvis:
            rows.append((float(pvis[0][0]), "vertical_pvi"))
            rows.append((float(pvis[-1][0]), "vertical_pvi"))
        for c in curves:
            rows.append((float(c["bvc"]), "vertical_bvc"))
            rows.append((float(c["evc"]), "vertical_evc"))
    except Exception:
        return []
    return rows


def _format_station_text(value):
    return f"{float(value):.3f}"


def _count_summary(rows, key):
    counts = {}
    for row in list(rows or []):
        token = str(row.get(key, "") or "").strip()
        if not token:
            continue
        counts[token] = int(counts.get(token, 0)) + 1
    if not counts:
        return "-"
    order = sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
    return ", ".join(f"{name}:{count}" for name, count in order)


_DISPLAY_QUALITY_PRESETS = ("Fast", "Normal", "Fine", "Ultra")
_DISPLAY_QUALITY_FACTORS = {
    "Fast": {"err": 2.0, "min": 2.0, "max": 1.6},
    "Normal": {"err": 1.0, "min": 1.0, "max": 1.0},
    "Fine": {"err": 0.5, "min": 0.5, "max": 0.65},
    "Ultra": {"err": 0.25, "min": 0.25, "max": 0.45},
}
_SEGMENT_KIND_FACTORS = {
    "base": {"err": 1.0, "min": 1.2, "max": 1.2},
    "horizontal_ip": {"err": 0.7, "min": 0.8, "max": 0.85},
    "horizontal_transition": {"err": 0.5, "min": 0.6, "max": 0.7},
    "vertical_curve": {"err": 0.5, "min": 0.6, "max": 0.7},
    "region_boundary": {"err": 0.6, "min": 0.75, "max": 0.85},
    "region_transition": {"err": 0.45, "min": 0.55, "max": 0.65},
    "structure_zone": {"err": 0.55, "min": 0.65, "max": 0.75},
    "structure_transition": {"err": 0.4, "min": 0.5, "max": 0.6},
    "mixed": {"err": 0.35, "min": 0.5, "max": 0.6},
}


def ensure_centerline3d_display_properties(obj):
    # Optional legacy link: if provided, display can read source data from engine object.
    if not hasattr(obj, "SourceCenterline"):
        obj.addProperty("App::PropertyLink", "SourceCenterline", "Display", "Centerline3D engine source")

    # Direct source mode (preferred): display can resolve geometry/elevation on its own.
    if not hasattr(obj, "Alignment"):
        obj.addProperty("App::PropertyLink", "Alignment", "Source", "HorizontalAlignment link")
    if not hasattr(obj, "Stationing"):
        obj.addProperty("App::PropertyLink", "Stationing", "Source", "Stationing link (optional)")
    if not hasattr(obj, "VerticalAlignment"):
        obj.addProperty("App::PropertyLink", "VerticalAlignment", "Source", "VerticalAlignment link (optional)")
    if not hasattr(obj, "ProfileBundle"):
        obj.addProperty("App::PropertyLink", "ProfileBundle", "Source", "ProfileBundle link (optional)")
    if not hasattr(obj, "RegionPlanSource"):
        obj.addProperty("App::PropertyLink", "RegionPlanSource", "Source", "RegionPlan link (optional)")
    if not hasattr(obj, "StructureSetSource"):
        obj.addProperty("App::PropertyLink", "StructureSetSource", "Source", "StructureSet link (optional)")

    if not hasattr(obj, "UseStationing"):
        obj.addProperty("App::PropertyBool", "UseStationing", "Source", "Use Stationing.StationValues when available")
        obj.UseStationing = True

    if not hasattr(obj, "SamplingInterval"):
        obj.addProperty("App::PropertyFloat", "SamplingInterval", "Sampling", "Sampling interval (m) when Stationing is not used")
        obj.SamplingInterval = 5.0
    else:
        # Migrate older objects where SamplingInterval was under "Source"
        try:
            obj.setGroupOfProperty("SamplingInterval", "Sampling")
        except Exception:
            pass

    if not hasattr(obj, "ElevationSource"):
        obj.addProperty("App::PropertyEnumeration", "ElevationSource", "Source", "Elevation source mode")
        obj.ElevationSource = ["Auto", "VerticalAlignment", "ProfileBundleFG", "FlatZero"]
        obj.ElevationSource = "Auto"

    if not hasattr(obj, "ShowWire"):
        obj.addProperty("App::PropertyBool", "ShowWire", "Display", "Show 3D centerline wire")
        obj.ShowWire = True

    if not hasattr(obj, "MaxChordError"):
        obj.addProperty("App::PropertyFloat", "MaxChordError", "Sampling", "Maximum chord error for adaptive sampling (m)")
        obj.MaxChordError = 0.02

    if not hasattr(obj, "MinStep"):
        obj.addProperty("App::PropertyFloat", "MinStep", "Sampling", "Minimum station step for adaptive sampling (m)")
        obj.MinStep = 0.5

    if not hasattr(obj, "MaxStep"):
        obj.addProperty("App::PropertyFloat", "MaxStep", "Sampling", "Maximum station step for adaptive sampling (m)")
        obj.MaxStep = 10.0

    if not hasattr(obj, "UseKeyStations"):
        obj.addProperty("App::PropertyBool", "UseKeyStations", "Sampling", "Always include key stations (edge bounds, BVC/EVC)")
        obj.UseKeyStations = True
    if not hasattr(obj, "SegmentByRegions"):
        obj.addProperty("App::PropertyBool", "SegmentByRegions", "Sampling", "Split display at RegionPlan boundaries and transitions")
        obj.SegmentByRegions = True
    if not hasattr(obj, "SegmentByStructures"):
        obj.addProperty("App::PropertyBool", "SegmentByStructures", "Sampling", "Split display at StructureSet boundaries and transitions")
        obj.SegmentByStructures = True
    if not hasattr(obj, "DisplayQuality"):
        obj.addProperty("App::PropertyEnumeration", "DisplayQuality", "Sampling", "Display sampling quality preset")
        obj.DisplayQuality = list(_DISPLAY_QUALITY_PRESETS)
        obj.DisplayQuality = "Normal"

    if not hasattr(obj, "SampledStations"):
        obj.addProperty("App::PropertyFloatList", "SampledStations", "Result", "Adaptive sampled station values (m)")
    if not hasattr(obj, "SampledPoints"):
        obj.addProperty("App::PropertyVectorList", "SampledPoints", "Result", "Adaptive sampled 3D points")
    if not hasattr(obj, "SampleCount"):
        obj.addProperty("App::PropertyInteger", "SampleCount", "Result", "Sample point count")
        obj.SampleCount = 0
    if not hasattr(obj, "SegmentCount"):
        obj.addProperty("App::PropertyInteger", "SegmentCount", "Result", "Planned display segment count")
        obj.SegmentCount = 0
    if not hasattr(obj, "SegmentKindSummary"):
        obj.addProperty("App::PropertyString", "SegmentKindSummary", "Result", "Planned display segment kind summary")
        obj.SegmentKindSummary = "-"
    if not hasattr(obj, "SegmentSplitSourceSummary"):
        obj.addProperty("App::PropertyString", "SegmentSplitSourceSummary", "Result", "Split-source summary used for display segmentation")
        obj.SegmentSplitSourceSummary = "-"
    if not hasattr(obj, "SegmentRows"):
        obj.addProperty("App::PropertyStringList", "SegmentRows", "Result", "Structured display segment rows")
        obj.SegmentRows = []
    if not hasattr(obj, "SegmentBoundaryStations"):
        obj.addProperty("App::PropertyStringList", "SegmentBoundaryStations", "Result", "Segment boundary station list with source labels")
        obj.SegmentBoundaryStations = []
    if not hasattr(obj, "DensestSegmentSummary"):
        obj.addProperty("App::PropertyString", "DensestSegmentSummary", "Result", "Most densely sampled planned display segment")
        obj.DensestSegmentSummary = "-"
    if not hasattr(obj, "SamplingPolicySummary"):
        obj.addProperty("App::PropertyString", "SamplingPolicySummary", "Result", "Applied display quality and per-segment sampling summary")
        obj.SamplingPolicySummary = "-"

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Display generation status")
        obj.Status = "Idle"
    if not hasattr(obj, "ResolvedElevationSource"):
        obj.addProperty("App::PropertyString", "ResolvedElevationSource", "Result", "Resolved elevation source used at runtime")
        obj.ResolvedElevationSource = "N/A"
    if not hasattr(obj, "LengthSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "LengthSchemaVersion", "Display", "Centerline3DDisplay scalar length storage schema")
        obj.LengthSchemaVersion = 2
    try:
        schema = int(getattr(obj, "LengthSchemaVersion", 0) or 0)
    except Exception:
        schema = 0
    if schema < 2:
        obj.LengthSchemaVersion = 2


class Centerline3DDisplay:
    """
    Display-only object for Centerline3D.
    Uses adaptive sampling to represent curved 3D geometry.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Centerline3DDisplay"
        ensure_centerline3d_display_properties(obj)

    @staticmethod
    def _reset_segment_diagnostics(obj):
        obj.SegmentCount = 0
        obj.SegmentRows = []
        obj.SegmentBoundaryStations = []
        obj.SegmentKindSummary = "-"
        obj.SegmentSplitSourceSummary = "-"
        obj.DensestSegmentSummary = "-"
        obj.SamplingPolicySummary = "-"

    @staticmethod
    def _publish_segment_diagnostics(obj, segment_rows, merged_markers, sampled_stations):
        obj.SegmentCount = len(list(segment_rows or []))
        obj.SegmentRows = Centerline3DDisplay._segment_rows_to_strings(segment_rows)
        obj.SegmentBoundaryStations = Centerline3DDisplay._marker_rows_to_strings(merged_markers)
        obj.SegmentKindSummary = _count_summary(segment_rows, "kind")
        obj.SegmentSplitSourceSummary = _count_summary(
            [{"source": src0} for row in list(merged_markers or []) for src0 in list(row.get("sources", []) or [])],
            "source",
        )
        obj.DensestSegmentSummary = Centerline3DDisplay._densest_segment_summary(segment_rows, sampled_stations)
        obj.SamplingPolicySummary = Centerline3DDisplay._sampling_policy_summary(obj, segment_rows)

    @staticmethod
    def _resolve_region_plan_source(display_obj):
        region_obj = getattr(display_obj, "RegionPlanSource", None)
        if region_obj is not None:
            return region_obj
        prj = find_project(getattr(display_obj, "Document", None))
        if prj is not None and hasattr(prj, "RegionPlan"):
            region_obj = getattr(prj, "RegionPlan", None)
            if region_obj is not None:
                return region_obj
        doc = getattr(display_obj, "Document", None)
        candidates = find_region_plan_objects(doc)
        return candidates[0] if candidates else None

    @staticmethod
    def _resolve_structure_set_source(display_obj):
        struct_obj = getattr(display_obj, "StructureSetSource", None)
        if struct_obj is not None:
            return struct_obj
        prj = find_project(getattr(display_obj, "Document", None))
        if prj is not None and hasattr(prj, "StructureSet"):
            struct_obj = getattr(prj, "StructureSet", None)
            if struct_obj is not None:
                return struct_obj
        return find_first(
            getattr(display_obj, "Document", None),
            proxy_type="StructureSet",
            name_prefixes=("StructureSet",),
        )

    @staticmethod
    def _region_marker_rows(region_obj):
        rows = []
        if region_obj is None:
            return rows
        for item in list(RegionPlan.region_key_station_items(region_obj, include_boundaries=True, include_transitions=True) or []):
            try:
                station = float(item.get("station", 0.0) or 0.0)
            except Exception:
                continue
            layers = [str(v or "").strip().lower() for v in list(item.get("layers", []) or []) if str(v or "").strip()]
            layer = layers[0] if layers else "region"
            role = str(item.get("role", "") or "").strip().lower()
            if role.startswith("transition"):
                source = f"region_{layer}_transition"
            elif role == "start":
                source = f"region_{layer}_start"
            elif role == "end":
                source = f"region_{layer}_end"
            else:
                source = f"region_{layer}_boundary"
            rows.append({"station": station, "source": source})
        return rows

    @staticmethod
    def _structure_marker_rows(struct_obj):
        rows = []
        if struct_obj is None:
            return rows
        items = StructureSet.structure_key_station_items(
            struct_obj,
            include_start_end=True,
            include_centers=True,
            include_transition=True,
            auto_transition=True,
            transition=0.0,
        )
        for item in list(items or []):
            try:
                station = float(item.get("station", 0.0) or 0.0)
            except Exception:
                continue
            role = str(item.get("role", "") or "").strip().lower()
            if role.startswith("transition"):
                source = "structure_transition"
            elif role == "center":
                source = "structure_center"
            elif role in ("start", "end"):
                source = "structure_boundary"
            else:
                source = "structure_zone"
            rows.append({"station": station, "source": source})
        return rows

    @staticmethod
    def _collect_split_markers(display_obj, src_obj, total_len: float):
        total = max(0.0, float(total_len))
        markers = [
            {"station": 0.0, "source": "start"},
            {"station": float(total), "source": "end"},
        ]

        if bool(getattr(display_obj, "UseKeyStations", True)):
            for value in list(getattr(src_obj, "StationValues", []) or []):
                try:
                    markers.append({"station": float(value), "source": "engine_station"})
                except Exception:
                    pass

            if bool(getattr(src_obj, "UseStationing", True)):
                st_obj = getattr(src_obj, "Stationing", None)
                if st_obj is not None and hasattr(st_obj, "StationValues"):
                    for value in list(st_obj.StationValues or []):
                        try:
                            markers.append({"station": float(value), "source": "stationing"})
                        except Exception:
                            pass

            aln = getattr(src_obj, "Alignment", None)
            if aln is not None:
                for value in _alignment_edge_boundaries(aln):
                    markers.append({"station": float(value), "source": "alignment_edge"})
                for value, source in _horizontal_key_rows(aln):
                    markers.append({"station": float(value), "source": source})

            for value, source in _vertical_key_rows(getattr(src_obj, "VerticalAlignment", None)):
                markers.append({"station": float(value), "source": source})

        if bool(getattr(display_obj, "SegmentByRegions", True)):
            markers.extend(
                Centerline3DDisplay._region_marker_rows(
                    Centerline3DDisplay._resolve_region_plan_source(display_obj)
                )
            )
        if bool(getattr(display_obj, "SegmentByStructures", True)):
            markers.extend(
                Centerline3DDisplay._structure_marker_rows(
                    Centerline3DDisplay._resolve_structure_set_source(display_obj)
                )
            )

        out = []
        for row in markers:
            try:
                station = min(max(0.0, float(row.get("station", 0.0) or 0.0)), float(total))
            except Exception:
                continue
            source = str(row.get("source", "") or "").strip()
            if not source:
                continue
            out.append({"station": station, "source": source})
        return out

    @staticmethod
    def _merge_split_markers(marker_rows, tol: float = 1.0e-6):
        vals = sorted(
            list(marker_rows or []),
            key=lambda row: (float(row.get("station", 0.0) or 0.0), str(row.get("source", "") or "")),
        )
        merged = []
        for row in vals:
            station = float(row.get("station", 0.0) or 0.0)
            source = str(row.get("source", "") or "").strip()
            if not merged:
                merged.append({"station": station, "sources": [source]})
                continue
            prev = merged[-1]
            if abs(float(prev["station"]) - station) <= float(tol):
                if source and source not in prev["sources"]:
                    prev["sources"].append(source)
            else:
                merged.append({"station": station, "sources": [source]})
        for row in merged:
            row["sources"] = sorted([str(v) for v in list(row.get("sources", []) or []) if str(v).strip()])
        return merged

    @staticmethod
    def _classify_segment_kind(sources):
        src = {str(v or "").strip().lower() for v in list(sources or [])}
        src.discard("")
        if not src:
            return "base"
        has_vertical = any(v.startswith("vertical_") for v in src)
        has_horizontal_transition = any(v in ("ts_key", "sc_key", "cs_key", "st_key") for v in src)
        has_ip = "ip_key" in src
        has_region = any(v.startswith("region_") for v in src)
        has_region_transition = any(v.startswith("region_") and "transition" in v for v in src)
        has_structure = any(v.startswith("structure_") for v in src)
        has_structure_transition = any(v.startswith("structure_") and "transition" in v for v in src)
        if has_vertical and (has_horizontal_transition or has_region or has_structure):
            return "mixed"
        if has_structure_transition:
            return "structure_transition"
        if has_region_transition:
            return "region_transition"
        if has_structure:
            return "structure_zone"
        if has_region:
            return "region_boundary"
        if has_vertical:
            return "vertical_curve"
        if has_horizontal_transition:
            return "horizontal_transition"
        if has_ip:
            return "horizontal_ip"
        return "base"

    @staticmethod
    def _build_segment_rows(merged_markers):
        rows = []
        vals = list(merged_markers or [])
        for idx in range(len(vals) - 1):
            left = vals[idx]
            right = vals[idx + 1]
            s0 = float(left.get("station", 0.0) or 0.0)
            s1 = float(right.get("station", 0.0) or 0.0)
            if s1 <= s0 + 1.0e-9:
                continue
            boundary_sources = sorted(
                {
                    str(v)
                    for v in (list(left.get("sources", []) or []) + list(right.get("sources", []) or []))
                    if str(v).strip()
                }
            )
            kind = Centerline3DDisplay._classify_segment_kind(boundary_sources)
            rows.append(
                {
                    "index": int(len(rows)),
                    "start": float(s0),
                    "end": float(s1),
                    "length": float(s1 - s0),
                    "kind": str(kind),
                    "boundary_sources": list(boundary_sources),
                    "start_sources": list(left.get("sources", []) or []),
                    "end_sources": list(right.get("sources", []) or []),
                }
            )
        return rows

    @staticmethod
    def _segment_rows_to_strings(rows):
        out = []
        for row in list(rows or []):
            out.append(
                "idx={idx}|start={start}|end={end}|len={length}|kind={kind}|sources={sources}|samples={samples}|err={err}|min={min_step}|max={max_step}".format(
                    idx=int(row.get("index", 0) or 0),
                    start=_format_station_text(row.get("start", 0.0)),
                    end=_format_station_text(row.get("end", 0.0)),
                    length=_format_station_text(row.get("length", 0.0)),
                    kind=str(row.get("kind", "base") or "base"),
                    sources=",".join(list(row.get("boundary_sources", []) or [])) or "-",
                    samples=int(row.get("sample_count", 0) or 0),
                    err=_format_station_text(row.get("max_err", 0.0)),
                    min_step=_format_station_text(row.get("min_step", 0.0)),
                    max_step=_format_station_text(row.get("max_step", 0.0)),
                )
            )
        return out

    @staticmethod
    def _marker_rows_to_strings(rows):
        out = []
        for row in list(rows or []):
            out.append(
                "station={station}|sources={sources}".format(
                    station=_format_station_text(row.get("station", 0.0)),
                    sources=",".join(list(row.get("sources", []) or [])) or "-",
                )
            )
        return out

    @staticmethod
    def _sample_count_for_range(sampled_stations, s0: float, s1: float, tol: float = 1.0e-6):
        count = 0
        for value in list(sampled_stations or []):
            try:
                station = float(value)
            except Exception:
                continue
            if (float(s0) - tol) <= station <= (float(s1) + tol):
                count += 1
        return int(count)

    @staticmethod
    def _densest_segment_summary(segment_rows, sampled_stations):
        best = None
        best_count = -1
        for row in list(segment_rows or []):
            count = int(row.get("sample_count", 0) or 0)
            if count <= 0:
                count = Centerline3DDisplay._sample_count_for_range(
                    sampled_stations,
                    row.get("start", 0.0),
                    row.get("end", 0.0),
                )
            if int(count) > int(best_count):
                best = row
                best_count = int(count)
        if best is None:
            return "-"
        return (
            f"{str(best.get('kind', 'base') or 'base')}:"
            f"{_format_station_text(best.get('start', 0.0))}"
            f"-{_format_station_text(best.get('end', 0.0))}"
            f" ({int(best_count)} samples)"
        )

    @staticmethod
    def _display_quality_name(obj):
        raw = str(getattr(obj, "DisplayQuality", "Normal") or "Normal").strip()
        return raw if raw in _DISPLAY_QUALITY_FACTORS else "Normal"

    @staticmethod
    def _segment_sampling_policy(obj, row, max_err: float, min_step: float, max_step: float):
        quality = Centerline3DDisplay._display_quality_name(obj)
        qf = dict(_DISPLAY_QUALITY_FACTORS.get(quality, _DISPLAY_QUALITY_FACTORS["Normal"]))
        kind = str(row.get("kind", "base") or "base")
        kf = dict(_SEGMENT_KIND_FACTORS.get(kind, _SEGMENT_KIND_FACTORS["base"]))

        err = max(1.0e-6, float(max_err) * float(qf.get("err", 1.0)) * float(kf.get("err", 1.0)))
        seg_min = max(1.0e-3, float(min_step) * float(qf.get("min", 1.0)) * float(kf.get("min", 1.0)))
        seg_max = max(seg_min, float(max_step) * float(qf.get("max", 1.0)) * float(kf.get("max", 1.0)))
        return {
            "quality": str(quality),
            "kind": str(kind),
            "max_err": float(err),
            "min_step": float(seg_min),
            "max_step": float(seg_max),
        }

    @staticmethod
    def _sampling_policy_summary(obj, segment_rows):
        quality = Centerline3DDisplay._display_quality_name(obj)
        if not segment_rows:
            return f"{quality} | no-segments"
        seen = {}
        for row in list(segment_rows or []):
            kind = str(row.get("kind", "base") or "base")
            token = (
                _format_station_text(row.get("max_err", 0.0)),
                _format_station_text(row.get("min_step", 0.0)),
                _format_station_text(row.get("max_step", 0.0)),
            )
            seen[kind] = token
        parts = []
        for kind in sorted(seen):
            err, seg_min, seg_max = seen[kind]
            parts.append(f"{kind}[e={err},min={seg_min},max={seg_max}]")
        return f"{quality} | " + "; ".join(parts)

    @staticmethod
    def _sample_segment_stations(src_obj, z_provider, s0: float, s1: float, max_err: float, min_step: float, max_step: float):
        stations = [float(s0)]
        if float(s1) > float(s0) + 1.0e-9:
            Centerline3DDisplay._append_adaptive(
                src_obj,
                z_provider,
                stations,
                float(s0),
                float(s1),
                max_err=max_err,
                min_step=min_step,
                max_step=max_step,
                depth=0,
            )
        return _unique_sorted(stations)

    @staticmethod
    def _build_segmented_display(display_obj, src_obj, segment_rows, z_provider, max_err: float, min_step: float, max_step: float):
        sampled_all = []
        segment_shapes = []
        planned_rows = []
        for row in list(segment_rows or []):
            policy = Centerline3DDisplay._segment_sampling_policy(display_obj, row, max_err, min_step, max_step)
            sampled_seg = Centerline3DDisplay._sample_segment_stations(
                src_obj,
                z_provider,
                row.get("start", 0.0),
                row.get("end", 0.0),
                max_err=policy["max_err"],
                min_step=policy["min_step"],
                max_step=policy["max_step"],
            )
            pts = [Centerline3D.point3d_at_station(src_obj, s, z_provider=z_provider) for s in sampled_seg]
            row_copy = dict(row)
            row_copy["quality"] = str(policy.get("quality", "Normal"))
            row_copy["max_err"] = float(policy.get("max_err", max_err))
            row_copy["min_step"] = float(policy.get("min_step", min_step))
            row_copy["max_step"] = float(policy.get("max_step", max_step))
            row_copy["sample_count"] = int(len(pts))
            planned_rows.append(row_copy)
            if len(pts) < 2:
                continue
            segment_shapes.append(Part.makePolygon(pts))
            sampled_all.extend(sampled_seg)

        sampled = _unique_sorted(sampled_all)
        points = [Centerline3D.point3d_at_station(src_obj, s, z_provider=z_provider) for s in sampled]
        if not segment_shapes:
            return Part.Shape(), sampled, points, planned_rows
        shape = segment_shapes[0] if len(segment_shapes) == 1 else Part.Compound(segment_shapes)
        return shape, sampled, points, planned_rows

    @staticmethod
    def _safe_sampling_params(obj):
        max_err = float(getattr(obj, "MaxChordError", 0.02))
        if max_err < 1e-6:
            max_err = 1e-6
            obj.MaxChordError = max_err

        min_step = float(getattr(obj, "MinStep", 0.5))
        if min_step < 1e-3:
            min_step = 1e-3
            obj.MinStep = min_step

        max_step = float(getattr(obj, "MaxStep", 10.0))
        if max_step < min_step:
            max_step = min_step
            obj.MaxStep = max_step

        return max_err, min_step, max_step

    @staticmethod
    def _midpoint_dev(src_obj, z_provider, s0: float, s1: float):
        p0 = Centerline3D.point3d_at_station(src_obj, float(s0), z_provider=z_provider)
        p1 = Centerline3D.point3d_at_station(src_obj, float(s1), z_provider=z_provider)
        sm = 0.5 * (float(s0) + float(s1))
        pm = Centerline3D.point3d_at_station(src_obj, float(sm), z_provider=z_provider)

        chord_mid = p0 + (p1 - p0) * 0.5
        dev_model = float((pm - chord_mid).Length)
        return float(_units.meters_from_model_length(getattr(src_obj, "Document", None), dev_model)), float(sm)

    @staticmethod
    def _append_adaptive(src_obj, z_provider, out_stations, s0: float, s1: float, max_err: float, min_step: float, max_step: float, depth: int):
        ds = float(s1 - s0)
        if ds <= min_step + 1e-9:
            out_stations.append(float(s1))
            return

        need_split = False
        if ds > max_step + 1e-9:
            need_split = True
            sm = 0.5 * (float(s0) + float(s1))
        else:
            dev, sm = Centerline3DDisplay._midpoint_dev(src_obj, z_provider, s0, s1)
            if dev > max_err:
                need_split = True

        if need_split and depth < 32:
            Centerline3DDisplay._append_adaptive(src_obj, z_provider, out_stations, s0, sm, max_err, min_step, max_step, depth + 1)
            Centerline3DDisplay._append_adaptive(src_obj, z_provider, out_stations, sm, s1, max_err, min_step, max_step, depth + 1)
            return

        out_stations.append(float(s1))

    def execute(self, obj):
        ensure_centerline3d_display_properties(obj)
        try:
            if not bool(getattr(obj, "ShowWire", True)):
                obj.Shape = Part.Shape()
                obj.SampledStations = []
                obj.SampledPoints = []
                obj.SampleCount = 0
                Centerline3DDisplay._reset_segment_diagnostics(obj)
                obj.Status = "Hidden"
                return

            src = getattr(obj, "SourceCenterline", None)
            if src is None:
                # Preferred mode: display uses its own source links/sampling properties.
                src = obj

            aln = getattr(src, "Alignment", None)
            if aln is None or aln.Shape is None or aln.Shape.isNull():
                obj.Shape = Part.Shape()
                obj.SampledStations = []
                obj.SampledPoints = []
                obj.SampleCount = 0
                Centerline3DDisplay._reset_segment_diagnostics(obj)
                obj.Status = "Source alignment is missing"
                obj.ResolvedElevationSource = "N/A"
                return

            total = float(getattr(aln, "TotalLength", 0.0) or 0.0)
            if total <= 1.0e-9:
                total = _units.meters_from_model_length(getattr(obj, "Document", None), float(getattr(aln.Shape, "Length", 0.0) or 0.0))
            if total <= 1e-9:
                obj.Shape = Part.Shape()
                obj.SampledStations = []
                obj.SampledPoints = []
                obj.SampleCount = 0
                Centerline3DDisplay._reset_segment_diagnostics(obj)
                obj.Status = "Source alignment length is zero"
                obj.ResolvedElevationSource = "N/A"
                return

            source_name, z_provider = Centerline3D._resolve_z_provider(src)
            max_err, min_step, max_step = Centerline3DDisplay._safe_sampling_params(obj)

            merged_markers = Centerline3DDisplay._merge_split_markers(
                Centerline3DDisplay._collect_split_markers(obj, src, total)
            )
            segment_rows = Centerline3DDisplay._build_segment_rows(merged_markers)

            shape, sampled, points, planned_rows = Centerline3DDisplay._build_segmented_display(
                obj,
                src,
                segment_rows,
                z_provider,
                max_err=max_err,
                min_step=min_step,
                max_step=max_step,
            )
            if len(points) < 2:
                obj.Shape = Part.Shape()
                obj.SampledStations = sampled
                obj.SampledPoints = points
                obj.SampleCount = len(points)
                Centerline3DDisplay._publish_segment_diagnostics(obj, planned_rows, merged_markers, sampled)
                obj.Status = "Insufficient sampled points"
                obj.ResolvedElevationSource = source_name
                return

            obj.Shape = shape
            obj.SampledStations = sampled
            obj.SampledPoints = points
            obj.SampleCount = len(points)
            Centerline3DDisplay._publish_segment_diagnostics(obj, planned_rows, merged_markers, sampled)
            obj.Status = "OK"
            obj.ResolvedElevationSource = source_name

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SampledStations = []
            obj.SampledPoints = []
            obj.SampleCount = 0
            Centerline3DDisplay._reset_segment_diagnostics(obj)
            obj.Status = f"ERROR: {ex}"
            obj.ResolvedElevationSource = "N/A"

    def onChanged(self, obj, prop):
        if prop in (
            "SourceCenterline",
            "Alignment",
            "Stationing",
            "VerticalAlignment",
            "ProfileBundle",
            "RegionPlanSource",
            "StructureSetSource",
            "UseStationing",
            "SamplingInterval",
            "ElevationSource",
            "ShowWire",
            "MaxChordError",
            "MinStep",
            "MaxStep",
            "UseKeyStations",
            "SegmentByRegions",
            "SegmentByStructures",
            "DisplayQuality",
        ):
            try:
                obj.touch()
                try:
                    import FreeCADGui as Gui
                    Gui.updateGui()
                except Exception:
                    pass
            except Exception:
                pass


class ViewProviderCenterline3DDisplay:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
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
