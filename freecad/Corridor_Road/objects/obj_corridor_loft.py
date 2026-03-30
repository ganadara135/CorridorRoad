# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_corridor_loft.py
import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_section_set import (
    SectionSet,
    _display_only_status_token,
    _earthwork_status_token,
    _external_shape_display_count,
    _external_shape_proxy_count,
    _resolve_structure_source,
    _status_join,
)
from freecad.Corridor_Road.objects.obj_structure_set import (
    StructureSet as StructureSetSource,
    _build_structure_solid as _structure_record_solid,
    _record_transition_distance,
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


def _report_row(kind: str, **fields) -> str:
    parts = [str(kind or "").strip() or "row"]
    for key, value in fields.items():
        parts.append(f"{str(key)}={value}")
    return "|".join(parts)


def _corridor_rule_status_token(split_count: int, corridor_mode_summary, skipped_station_rows, corridor_warning_rows) -> str:
    if (
        int(split_count or 0) >= 2
        or str(corridor_mode_summary or "-") != "-"
        or bool(list(skipped_station_rows or []))
        or bool(list(corridor_warning_rows or []))
    ):
        return "corridorRule=structure_aware"
    return "corridorRule=full"


def _notch_schema_name() -> str:
    return "notch_v1_8pt"


def _resolve_corridor_record_at_station(src, rec, station: float):
    try:
        ss = _resolve_structure_source(src)
        if ss is None:
            return dict(rec or {})
        resolved = StructureSetSource.resolve_profile_at_station(ss, rec, float(station))
        return dict(resolved or rec or {})
    except Exception:
        return dict(rec or {})


def _resolve_corridor_record_span(src, rec, station_from: float, station_to: float):
    try:
        ss = _resolve_structure_source(src)
        if ss is None:
            return []
        return list(StructureSetSource.resolve_profile_span(ss, rec, float(station_from), float(station_to)) or [])
    except Exception:
        return []


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
    # Surface-only policy.
    try:
        obj.OutputType = ["Surface"]
        obj.OutputType = "Surface"
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

    if not hasattr(obj, "AutoUseRuledForTypicalSection"):
        obj.addProperty(
            "App::PropertyBool",
            "AutoUseRuledForTypicalSection",
            "Corridor",
            "Automatically prefer ruled loft when Typical Section profiles include richer edge breaks",
        )
        obj.AutoUseRuledForTypicalSection = True

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

    if not hasattr(obj, "ResolvedStructureCorridorRanges"):
        obj.addProperty("App::PropertyStringList", "ResolvedStructureCorridorRanges", "Result", "Resolved per-structure corridor span diagnostics")
        obj.ResolvedStructureCorridorRanges = []

    if not hasattr(obj, "ResolvedStructureCorridorWarnings"):
        obj.addProperty("App::PropertyStringList", "ResolvedStructureCorridorWarnings", "Result", "Warnings detected while resolving structure corridor spans")
        obj.ResolvedStructureCorridorWarnings = []

    if not hasattr(obj, "ResolvedStructureCorridorModeSummary"):
        obj.addProperty("App::PropertyString", "ResolvedStructureCorridorModeSummary", "Result", "Resolved structure corridor mode summary")
        obj.ResolvedStructureCorridorModeSummary = "-"

    if not hasattr(obj, "ResolvedSkipBoundaryBehavior"):
        obj.addProperty("App::PropertyString", "ResolvedSkipBoundaryBehavior", "Result", "Resolved skip-zone boundary behavior summary")
        obj.ResolvedSkipBoundaryBehavior = "-"

    if not hasattr(obj, "ResolvedSkipBoundaryStates"):
        obj.addProperty("App::PropertyStringList", "ResolvedSkipBoundaryStates", "Result", "Resolved skip-zone boundary states")
        obj.ResolvedSkipBoundaryStates = []

    if not hasattr(obj, "ResolvedSkipBoundaryCapCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedSkipBoundaryCapCount", "Result", "Resolved skip-zone cap count")
        obj.ResolvedSkipBoundaryCapCount = 0

    if not hasattr(obj, "ResolvedStructureNotchCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedStructureNotchCount", "Result", "Number of structure notch cuts applied")
        obj.ResolvedStructureNotchCount = 0

    if not hasattr(obj, "ResolvedNotchStationCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedNotchStationCount", "Result", "Number of stations using the notch-aware profile schema")
        obj.ResolvedNotchStationCount = 0

    if not hasattr(obj, "ResolvedNotchSchemaName"):
        obj.addProperty("App::PropertyString", "ResolvedNotchSchemaName", "Result", "Resolved notch-aware closed-profile schema name")
        obj.ResolvedNotchSchemaName = "-"

    if not hasattr(obj, "ResolvedNotchProfileSummary"):
        obj.addProperty("App::PropertyString", "ResolvedNotchProfileSummary", "Result", "Resolved notch profile summary")
        obj.ResolvedNotchProfileSummary = "-"

    if not hasattr(obj, "ResolvedNotchProfileRows"):
        obj.addProperty("App::PropertyStringList", "ResolvedNotchProfileRows", "Result", "Resolved per-station notch profile diagnostics")
        obj.ResolvedNotchProfileRows = []

    if not hasattr(obj, "ResolvedNotchStructureIds"):
        obj.addProperty("App::PropertyStringList", "ResolvedNotchStructureIds", "Result", "Resolved structure IDs contributing to notch-aware profiles")
        obj.ResolvedNotchStructureIds = []

    if not hasattr(obj, "ResolvedNotchBuildMode"):
        obj.addProperty("App::PropertyString", "ResolvedNotchBuildMode", "Result", "Resolved notch build strategy")
        obj.ResolvedNotchBuildMode = "-"

    if not hasattr(obj, "ResolvedNotchCutterCount"):
        obj.addProperty("App::PropertyInteger", "ResolvedNotchCutterCount", "Result", "Resolved number of notch cutters applied in fallback mode")
        obj.ResolvedNotchCutterCount = 0

    if not hasattr(obj, "ClosedProfileSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "ClosedProfileSchemaVersion", "Result", "Legacy loft-profile schema version used for corridor generation")
        obj.ClosedProfileSchemaVersion = 0

    if not hasattr(obj, "SkipMarkerCount"):
        obj.addProperty("App::PropertyInteger", "SkipMarkerCount", "Result", "Number of skip-zone boundary markers")
        obj.SkipMarkerCount = 0

    if not hasattr(obj, "NotchTransitionScale"):
        obj.addProperty(
            "App::PropertyFloat",
            "NotchTransitionScale",
            "Corridor",
            "Scale factor applied to structure transition distance when deriving notch ramps",
        )
        obj.NotchTransitionScale = 1.0

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"

    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "ResolvedHeightLeft"):
        obj.addProperty("App::PropertyFloat", "ResolvedHeightLeft", "Result", "Legacy resolved left depth (unused in surface mode)")
        obj.ResolvedHeightLeft = 0.0

    if not hasattr(obj, "ResolvedHeightRight"):
        obj.addProperty("App::PropertyFloat", "ResolvedHeightRight", "Result", "Legacy resolved right depth (unused in surface mode)")
        obj.ResolvedHeightRight = 0.0

    if not hasattr(obj, "ResolvedRuledMode"):
        obj.addProperty("App::PropertyString", "ResolvedRuledMode", "Result", "Resolved ruled-loft mode")
        obj.ResolvedRuledMode = "off"

    if not hasattr(obj, "TopProfileEdgeSummary"):
        obj.addProperty("App::PropertyString", "TopProfileEdgeSummary", "Result", "Outermost top-profile edge component summary")
        obj.TopProfileEdgeSummary = "-"
    if not hasattr(obj, "SubassemblySchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SubassemblySchemaVersion", "Result", "Practical subassembly schema version")
        obj.SubassemblySchemaVersion = 0
    if not hasattr(obj, "PracticalSectionMode"):
        obj.addProperty("App::PropertyString", "PracticalSectionMode", "Result", "Practical section mode summary")
        obj.PracticalSectionMode = "simple"
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
    if not hasattr(obj, "PavementScheduleRows"):
        obj.addProperty("App::PropertyStringList", "PavementScheduleRows", "Result", "Structured pavement schedule rows")
        obj.PavementScheduleRows = []
    if not hasattr(obj, "StructureInteractionSummaryRows"):
        obj.addProperty("App::PropertyStringList", "StructureInteractionSummaryRows", "Result", "Structured structure-interaction summary rows")
        obj.StructureInteractionSummaryRows = []
    if not hasattr(obj, "ExportSummaryRows"):
        obj.addProperty("App::PropertyStringList", "ExportSummaryRows", "Result", "Structured export-ready summary rows")
        obj.ExportSummaryRows = []

    try:
        if hasattr(obj, "OutputType"):
            obj.setEditorMode("OutputType", 2)
        if hasattr(obj, "HeightLeft"):
            obj.setEditorMode("HeightLeft", 2)
        if hasattr(obj, "HeightRight"):
            obj.setEditorMode("HeightRight", 2)
    except Exception:
        pass


class CorridorLoft:
    """
    Corridor loft from SectionSet (surface-first).
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
    def _lerp_point(a, b, t: float):
        tt = max(0.0, min(1.0, float(t)))
        return App.Vector(
            float(a.x) + (float(b.x) - float(a.x)) * tt,
            float(a.y) + (float(b.y) - float(a.y)) * tt,
            float(a.z) + (float(b.z) - float(a.z)) * tt,
        )

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
    def _typical_edge_types(src):
        try:
            if src is None or not bool(getattr(src, "UseTypicalSectionTemplate", False)):
                return []
            typ = getattr(src, "TypicalSectionTemplate", None)
            if typ is None:
                return []
            out = []
            for v in (
                getattr(typ, "LeftEdgeComponentType", ""),
                getattr(typ, "RightEdgeComponentType", ""),
            ):
                s = str(v or "").strip().lower()
                if s:
                    out.append(s)
            return out
        except Exception:
            return []

    @staticmethod
    def _resolve_ruled_mode(obj, src, pt_count: int):
        manual = bool(getattr(obj, "UseRuled", False))
        if manual:
            return True, "manual"

        if not bool(getattr(obj, "AutoUseRuledForTypicalSection", True)):
            return False, "off"

        if str(getattr(src, "TopProfileSource", "assembly_simple") or "assembly_simple") != "typical_section":
            return False, "off"

        edge_types = set(CorridorLoft._typical_edge_types(src))
        rich_edges = bool(edge_types.intersection({"curb", "ditch", "berm", "gutter"}))
        if rich_edges:
            return True, "auto:typical_edges"
        if int(pt_count) >= 7:
            return True, "auto:point_count"
        return False, "off"

    @staticmethod
    def _should_retry_with_ruled(src, ruled: bool):
        if bool(ruled):
            return False
        return str(getattr(src, "TopProfileSource", "assembly_simple") or "assembly_simple") == "typical_section"

    @staticmethod
    def _loft_with_retry(wires, stations, ranges, ruled: bool, src, solid: bool = True):
        retry_used = False
        if ranges:
            try:
                shape, failed_ranges = CorridorLoft._loft_by_ranges(wires, stations, ranges, ruled=ruled, solid=solid)
                return shape, failed_ranges, retry_used
            except Exception:
                if CorridorLoft._should_retry_with_ruled(src, ruled):
                    shape, failed_ranges = CorridorLoft._loft_by_ranges(wires, stations, ranges, ruled=True, solid=solid)
                    return shape, failed_ranges, True
                raise
        try:
            shape = CorridorLoft._loft(wires, ruled=ruled, solid=solid)
            return shape, [], retry_used
        except Exception:
            if CorridorLoft._should_retry_with_ruled(src, ruled):
                shape = CorridorLoft._loft(wires, ruled=True, solid=solid)
                return shape, [], True
            raise

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
        _detail_rows, _warning_rows, _mode_summary, spans = CorridorLoft._describe_structure_corridor_records(rows)
        return spans

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
            return [], [], []

        skip_mask = [False] * n
        skip_runs = []
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

        if not any(skip_mask):
            return [], [], []

        keep_ranges = []
        skipped_rows = []
        i = 0
        while i < n:
            if skip_mask[i]:
                j = i
                while j + 1 < n and skip_mask[j + 1]:
                    j += 1
                skipped_rows.append(f"{float(stations[i]):.3f}-{float(stations[j]):.3f}")
                skip_runs.append((int(i), int(j)))
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
        return dedup, skipped_rows, skip_runs

    @staticmethod
    def _skip_zone_boundary_summary(stations, skip_runs):
        vals = list(stations or [])
        n = len(vals)
        if n < 1:
            return "-", [], 0

        rows = []
        labels = []
        for i0, i1 in list(skip_runs or []):
            lo = float(vals[max(0, min(n - 1, int(i0)))])
            hi = float(vals[max(0, min(n - 1, int(i1)))])
            span_txt = CorridorLoft._format_station_span(lo, hi)
            if int(i0) <= 0:
                rows.append(f"open_start:{span_txt}")
                if "open_start" not in labels:
                    labels.append("open_start")
            if int(i1) >= (n - 1):
                rows.append(f"open_end:{span_txt}")
                if "open_end" not in labels:
                    labels.append("open_end")

        if rows:
            return "caps_deferred", rows, 0
        if skip_runs:
            return "internal_only", [], 0
        return "-", [], 0

    @staticmethod
    def _corridor_record_ref(rec) -> str:
        rid = str(rec.get("Id", "") or "").strip()
        if rid:
            return rid
        idx = rec.get("Index", None)
        try:
            return f"#{int(idx) + 1}"
        except Exception:
            return "#?"

    @staticmethod
    def _format_station_span(lo: float, hi: float, tol: float = 1e-6) -> str:
        a = float(min(lo, hi))
        b = float(max(lo, hi))
        if abs(b - a) <= tol:
            return f"{a:.3f}"
        return f"{a:.3f}-{b:.3f}"

    @staticmethod
    def _describe_structure_corridor_records(corridor_records):
        detail_rows = []
        warning_rows = []
        spans = []
        mode_counts = {}
        mode_order = {"split_only": 0, "skip_zone": 1, "notch": 2, "boolean_cut": 3}

        for rec in list(corridor_records or []):
            mode = str(rec.get("ResolvedCorridorMode", "") or "").strip().lower()
            if mode in ("", "none"):
                continue
            rid = CorridorLoft._corridor_record_ref(rec)
            typ = str(rec.get("Type", "") or "structure").strip().lower() or "structure"
            s0 = float(rec.get("ResolvedStartStation", 0.0) or 0.0)
            s1 = float(rec.get("ResolvedEndStation", 0.0) or 0.0)
            mg = max(0.0, float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0))
            lo = min(s0, s1) - mg
            hi = max(s0, s1) + mg
            source = str(rec.get("ResolvedStationSource", "") or "").strip()
            extras = []
            if mg > 1e-9:
                extras.append(f"margin={mg:.3f}")
            if source and source != "start_end":
                extras.append(f"source={source}")
            row = f"{rid}:{typ}:{mode}:{CorridorLoft._format_station_span(lo, hi)}"
            if extras:
                row += f" ({', '.join(extras)})"
            detail_rows.append(row)
            mode_counts[mode] = int(mode_counts.get(mode, 0) or 0) + 1
            if mode not in ("", "none", "split_only"):
                spans.append((lo, hi, mode))
            for note in list(rec.get("ResolvedCorridorWarnings", []) or []):
                txt = str(note or "").strip()
                if txt:
                    warning_rows.append(f"{rid}:{txt}")

        summary_parts = []
        for mode, count in sorted(mode_counts.items(), key=lambda it: (mode_order.get(it[0], 99), it[0])):
            summary_parts.append(f"{mode}={int(count)}")
        return detail_rows, warning_rows, (", ".join(summary_parts) if summary_parts else "-"), _merge_station_spans(spans)

    @staticmethod
    def _clear_skip_markers(obj):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return
        for ch in list(getattr(doc, "Objects", []) or []):
            try:
                if not str(getattr(ch, "Name", "") or "").startswith("CorridorSkipMarker"):
                    continue
                if getattr(ch, "ParentCorridorLoft", None) != obj:
                    continue
                doc.removeObject(ch.Name)
            except Exception:
                pass

    @staticmethod
    def _make_skip_marker_face(profile_wire):
        try:
            if profile_wire is None or profile_wire.isNull():
                return None
            return Part.Face(profile_wire)
        except Exception:
            return profile_wire

    @staticmethod
    def _create_skip_markers(obj, stations, loft_wires, skip_runs):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return 0
        CorridorLoft._clear_skip_markers(obj)
        count = 0
        scale = get_length_scale(doc, default=1.0)
        for run_idx, (i0, i1) in enumerate(list(skip_runs or []), start=1):
            for role, idx in (("SKIP_START", int(i0)), ("SKIP_END", int(i1))):
                if idx < 0 or idx >= len(loft_wires):
                    continue
                shp = CorridorLoft._make_skip_marker_face(loft_wires[idx])
                if shp is None or shp.isNull():
                    continue
                try:
                    mk = doc.addObject("Part::Feature", "CorridorSkipMarker")
                    mk.Label = f"STA {float(stations[idx]):.3f} [{role}]"
                    if not hasattr(mk, "ParentCorridorLoft"):
                        mk.addProperty("App::PropertyLink", "ParentCorridorLoft", "Corridor", "Owning CorridorLoft")
                    mk.ParentCorridorLoft = obj
                    if not hasattr(mk, "Station"):
                        mk.addProperty("App::PropertyFloat", "Station", "Corridor", "Boundary station")
                    mk.Station = float(stations[idx])
                    if not hasattr(mk, "MarkerRole"):
                        mk.addProperty("App::PropertyString", "MarkerRole", "Corridor", "Skip boundary role")
                    mk.MarkerRole = str(role)
                    if not hasattr(mk, "SkipRunIndex"):
                        mk.addProperty("App::PropertyInteger", "SkipRunIndex", "Corridor", "Skip run index")
                    mk.SkipRunIndex = int(run_idx)
                    mk.Shape = shp
                    vobj = getattr(mk, "ViewObject", None)
                    if vobj is not None:
                        vobj.DisplayMode = "Flat Lines"
                        vobj.ShapeColor = (0.96, 0.42, 0.14) if role == "SKIP_START" else (0.90, 0.18, 0.18)
                        vobj.LineColor = (0.85, 0.32, 0.10) if role == "SKIP_START" else (0.72, 0.12, 0.12)
                        vobj.Transparency = 55
                        vobj.LineWidth = max(2, int(round(2.0 * scale)))
                    count += 1
                except Exception:
                    pass
        return int(count)

    @staticmethod
    def _structure_notch_spec(rec, scale: float):
        typ = str(rec.get("Type", "") or "").strip().lower()
        width = max(0.50 * scale, abs(float(rec.get("Width", 0.0) or 0.0)))
        height = max(0.50 * scale, abs(float(rec.get("Height", 0.0) or 0.0)))
        bottom = float(rec.get("BottomElevation", 0.0) or 0.0)
        cover = abs(float(rec.get("Cover", 0.0) or 0.0))
        profile_mode = str(rec.get("ResolvedProfileMode", "base_row") or "base_row")

        if typ == "culvert":
            return {
                "Enabled": True,
                "TypeLabel": "culvert",
                "Width": width * 1.35,
                "Height": height * 1.40,
                "LongPad": max(0.75 * scale, 0.20 * width),
                "BottomExtra": 0.15 * height,
                "BottomMode": ("bottom_elevation" if abs(bottom) > 1e-9 else ("cover_offset" if cover > 1e-9 else "relative_depth")),
                "ProfileMode": profile_mode,
            }
        if typ == "crossing":
            return {
                "Enabled": True,
                "TypeLabel": "crossing",
                "Width": width * 1.20,
                "Height": height * 1.25,
                "LongPad": max(0.50 * scale, 0.15 * width),
                "BottomExtra": 0.10 * height,
                "BottomMode": ("bottom_elevation" if abs(bottom) > 1e-9 else ("cover_offset" if cover > 1e-9 else "relative_depth")),
                "ProfileMode": profile_mode,
            }
        if typ == "retaining_wall":
            return {
                "Enabled": False,
                "Reason": "retaining_wall should use split_only rather than notch",
            }
        if typ in ("bridge_zone", "abutment_zone"):
            return {
                "Enabled": False,
                "Reason": f"{typ} should prefer skip_zone rather than notch",
            }
        return {
            "Enabled": False,
            "Reason": f"{typ or 'generic'} notch support is limited to culvert/crossing in the first notch sprint",
        }

    @staticmethod
    def _notch_profile_spec_rows(src, stations, fallback_mode: str, notch_transition_scale: float):
        recs = CorridorLoft._resolve_structure_corridor_records(src, fallback_mode=fallback_mode)
        if not recs:
            return [], []

        scale = get_length_scale(getattr(src, "Document", None), default=1.0)
        eligible = []
        notes = []
        for rec in list(recs or []):
            mode = str(rec.get("ResolvedCorridorMode", "") or "").strip().lower()
            if mode != "notch":
                continue
            rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
            midpoint_station = 0.5 * (
                float(rec.get("ResolvedStartStation", rec.get("StartStation", 0.0)) or 0.0)
                + float(rec.get("ResolvedEndStation", rec.get("EndStation", 0.0)) or 0.0)
            )
            resolved_mid = _resolve_corridor_record_at_station(src, rec, midpoint_station)
            spec = CorridorLoft._structure_notch_spec(resolved_mid, scale)
            if not bool(spec.get("Enabled", False)):
                notes.append(f"{rid}: {str(spec.get('Reason', 'notch disabled'))}")
                continue
            trans = _record_transition_distance(
                src,
                rec,
                auto_transition=bool(getattr(src, "AutoStructureTransitionDistance", True)),
                transition=float(getattr(src, "StructureTransitionDistance", 0.0) or 0.0),
            )
            trans = max(0.0, float(trans) * max(0.01, float(notch_transition_scale)))
            local = dict(resolved_mid)
            local["ResolvedStartStation"] = float(rec.get("ResolvedStartStation", rec.get("StartStation", 0.0)) or 0.0)
            local["ResolvedEndStation"] = float(rec.get("ResolvedEndStation", rec.get("EndStation", 0.0)) or 0.0)
            local["ResolvedCorridorMode"] = str(rec.get("ResolvedCorridorMode", "") or "")
            local["ResolvedCorridorMargin"] = float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0)
            local["_notch_spec"] = spec
            local["_transition"] = trans
            eligible.append(local)

        if not eligible:
            return [], notes

        rows = []
        tol = 1e-6
        tiny_ramp = 0.004
        for s in list(stations or []):
            ss = float(s)
            best = None
            best_ramp = -1.0
            for rec in eligible:
                s0 = float(rec.get("ResolvedStartStation", rec.get("StartStation", 0.0)) or 0.0)
                s1 = float(rec.get("ResolvedEndStation", rec.get("EndStation", 0.0)) or 0.0)
                lo = min(s0, s1)
                hi = max(s0, s1)
                tt = max(0.0, float(rec.get("_transition", 0.0) or 0.0))
                if ss < (lo - tt - tol) or ss > (hi + tt + tol):
                    continue
                if ss >= lo - tol and ss <= hi + tol:
                    if tt <= tol:
                        ramp = 1.0
                    else:
                        left_ratio = max(0.0, min(1.0, (ss - lo) / tt))
                        right_ratio = max(0.0, min(1.0, (hi - ss) / tt))
                        inner_ratio = min(left_ratio, right_ratio)
                        if abs(ss - lo) <= tol or abs(ss - hi) <= tol:
                            ramp = max(0.35, inner_ratio)
                        else:
                            ramp = max(0.35, min(1.0, max(inner_ratio, 1.0)))
                elif tt <= tol:
                    ramp = 0.0
                elif ss < lo:
                    ramp = max(0.0, min(1.0, (ss - (lo - tt)) / tt))
                else:
                    ramp = max(0.0, min(1.0, ((hi + tt) - ss) / tt))
                if ramp > best_ramp + 1e-9 or (best is None and ramp >= -1e-9):
                    best_ramp = float(ramp)
                    best = rec
            if best is None:
                rows.append({"Mode": "default", "Ramp": 0.0, "Record": None})
            else:
                resolved_best = _resolve_corridor_record_at_station(src, best, ss)
                resolved_best["ResolvedStartStation"] = float(best.get("ResolvedStartStation", best.get("StartStation", 0.0)) or 0.0)
                resolved_best["ResolvedEndStation"] = float(best.get("ResolvedEndStation", best.get("EndStation", 0.0)) or 0.0)
                resolved_best["ResolvedCorridorMode"] = str(best.get("ResolvedCorridorMode", "") or "")
                resolved_best["ResolvedCorridorMargin"] = float(best.get("ResolvedCorridorMargin", 0.0) or 0.0)
                resolved_best["_transition"] = float(best.get("_transition", 0.0) or 0.0)
                resolved_best["_notch_spec"] = CorridorLoft._structure_notch_spec(resolved_best, scale)
                roles = []
                start_sta = float(best.get("ResolvedStartStation", best.get("StartStation", 0.0)) or 0.0)
                end_sta = float(best.get("ResolvedEndStation", best.get("EndStation", 0.0)) or 0.0)
                trans_sta = float(best.get("_transition", 0.0) or 0.0)
                if abs(ss - start_sta) <= tol:
                    roles.append("start")
                if abs(ss - end_sta) <= tol:
                    roles.append("end")
                if trans_sta > tol and abs(ss - (start_sta - trans_sta)) <= tol:
                    roles.append("transition_before")
                if trans_sta > tol and abs(ss - (end_sta + trans_sta)) <= tol:
                    roles.append("transition_after")
                if best_ramp >= 1.0 - 1e-6:
                    roles.append("active")
                elif "start" in roles or "end" in roles:
                    roles.append("active")
                elif ss < start_sta:
                    roles.append("transition_before")
                else:
                    roles.append("transition_after")
                dedup_roles = []
                for role in roles:
                    if role and role not in dedup_roles:
                        dedup_roles.append(role)
                rows.append(
                    {
                        "Mode": "notch",
                        "Ramp": max(tiny_ramp, float(best_ramp)),
                        "Record": resolved_best,
                        "Roles": dedup_roles,
                    }
                )
        return rows, notes

    @staticmethod
    def _describe_notch_profile_rows(rows):
        diag_rows = []
        ids = []
        mode_counts = {}
        active_count = 0
        transition_count = 0
        for row in list(rows or []):
            if str(row.get("Mode", "default") or "default") != "notch":
                continue
            rec = dict(row.get("Record", {}) or {})
            rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
            if rid and rid not in ids:
                ids.append(rid)
            profile_mode = str(rec.get("ResolvedProfileMode", "base_row") or "base_row")
            mode_counts[profile_mode] = int(mode_counts.get(profile_mode, 0)) + 1
            roles = [str(v or "").strip().lower() for v in list(row.get("Roles", []) or []) if str(v or "").strip()]
            if "active" in roles:
                active_count += 1
            else:
                transition_count += 1
            spec = dict(rec.get("_notch_spec", {}) or {})
            diag_rows.append(
                f"{rid}@{float(rec.get('ResolvedProfileStation', 0.0) or 0.0):.3f}: "
                f"type={str(spec.get('TypeLabel', rec.get('Type', '')) or rec.get('Type', '')).strip() or '-'} "
                f"profile={profile_mode} "
                f"points={int(rec.get('ResolvedProfilePointCount', 0) or 0)} "
                f"ramp={float(row.get('Ramp', 0.0) or 0.0):.3f} "
                f"roles={','.join(roles) if roles else '-'} "
                f"width={float(spec.get('Width', rec.get('Width', 0.0) or 0.0) or 0.0):.3f} "
                f"height={float(spec.get('Height', rec.get('Height', 0.0) or 0.0) or 0.0):.3f} "
                f"bottomMode={str(spec.get('BottomMode', '-') or '-')}"
            )
        if not diag_rows:
            return "-", [], []
        parts = [f"schema={_notch_schema_name()}", f"structures={len(ids)}", f"active={int(active_count)}", f"transition={int(transition_count)}"]
        for key in sorted(mode_counts):
            parts.append(f"{key}={int(mode_counts[key])}")
        return " ".join(parts), diag_rows, ids

    @staticmethod
    def _make_notch_profile_for_surface(open_wire, row, scale: float):
        pts = CorridorLoft._wire_points(open_wire)
        if len(pts) < 2:
            raise Exception("Section has insufficient points for notch-aware surface profile.")

        left_outer = pts[0]
        right_outer = pts[-1]
        left_car = pts[1] if len(pts) >= 4 else CorridorLoft._lerp_point(left_outer, right_outer, 0.25)
        right_car = pts[-2] if len(pts) >= 4 else CorridorLoft._lerp_point(left_outer, right_outer, 0.75)
        axis = right_car - left_car
        axis_len = float(axis.Length)
        if axis_len <= 1e-9:
            axis = right_outer - left_outer
            axis_len = float(axis.Length)
        if axis_len <= 1e-9:
            raise Exception("Section carriage span is degenerate for notch profile.")

        rec = dict(row.get("Record", {}) or {})
        spec = dict(rec.get("_notch_spec", {}) or {})
        mode = str(row.get("Mode", "default") or "default").strip().lower()
        ramp = max(0.0, min(1.0, float(row.get("Ramp", 0.0) or 0.0)))
        min_width = max(0.002 * scale, 1e-4)
        min_depth = max(0.005 * scale, 1e-4)
        if mode != "notch":
            eff_width = 0.0
            eff_depth = 0.0
        else:
            eff_width = min(
                axis_len * 0.88,
                max(min_width, float(spec.get("Width", 0.20 * scale) or (0.20 * scale)) * ramp),
            )
            eff_depth = min(
                max(0.20 * scale, 0.45 * axis_len),
                max(min_depth, float(spec.get("Height", 0.10 * scale) or (0.10 * scale)) * 0.70 * (ramp ** 0.85)),
            )

        center_shift = 0.0
        try:
            center_shift = float(rec.get("Offset", 0.0) or 0.0)
        except Exception:
            center_shift = 0.0
        center_t = 0.5 + (center_shift / max(axis_len, 1e-9))
        center_t = max(0.20, min(0.80, center_t))
        if eff_width <= 1e-9 or eff_depth <= 1e-9:
            notch_ls = App.Vector(float(left_car.x), float(left_car.y), float(left_car.z))
            notch_lb = App.Vector(float(left_car.x), float(left_car.y), float(left_car.z))
            notch_rb = App.Vector(float(right_car.x), float(right_car.y), float(right_car.z))
            notch_rs = App.Vector(float(right_car.x), float(right_car.y), float(right_car.z))
        else:
            half_t = 0.5 * eff_width / max(axis_len, 1e-9)
            left_t = max(0.02, min(center_t - half_t, 0.48))
            right_t = min(0.98, max(center_t + half_t, 0.52))
            if right_t <= left_t + 1e-4:
                mid = 0.5 * (left_t + right_t)
                left_t = max(0.02, mid - 5e-4)
                right_t = min(0.98, mid + 5e-4)

            notch_lt = CorridorLoft._lerp_point(left_car, right_car, left_t)
            notch_rt = CorridorLoft._lerp_point(left_car, right_car, right_t)
            notch_lb = App.Vector(float(notch_lt.x), float(notch_lt.y), float(notch_lt.z) - eff_depth)
            notch_rb = App.Vector(float(notch_rt.x), float(notch_rt.y), float(notch_rt.z) - eff_depth)
            shoulder_t = min(0.10, max(0.01, 0.22 * half_t))
            left_shoulder_t = max(0.0, left_t - shoulder_t)
            right_shoulder_t = min(1.0, right_t + shoulder_t)
            notch_ls = CorridorLoft._lerp_point(left_car, right_car, left_shoulder_t)
            notch_rs = CorridorLoft._lerp_point(left_car, right_car, right_shoulder_t)
            shoulder_drop = max(0.0, eff_depth * 0.45)
            notch_ls = App.Vector(float(notch_ls.x), float(notch_ls.y), float(notch_ls.z) - shoulder_drop)
            notch_rs = App.Vector(float(notch_rs.x), float(notch_rs.y), float(notch_rs.z) - shoulder_drop)
        wire_pts = [
            left_outer,
            left_car,
            notch_ls,
            notch_lb,
            notch_rb,
            notch_rs,
            right_car,
            right_outer,
        ]
        return CorridorLoft._make_wire(_dedupe_consecutive_points(wire_pts))

    @staticmethod
    def _make_profiles_with_notch_schema(open_wires, stations, src, fallback_mode: str, notch_transition_scale: float):
        rows, notes = CorridorLoft._notch_profile_spec_rows(
            src,
            stations,
            fallback_mode=fallback_mode,
            notch_transition_scale=notch_transition_scale,
        )
        if not rows or len(rows) != len(open_wires):
            return None, 0, notes, {"schema_name": "-", "summary": "-", "rows": [], "ids": [], "spec_rows": []}

        scale = get_length_scale(getattr(src, "Document", None), default=1.0)
        out = []
        notch_station_count = 0
        for w, row in zip(list(open_wires or []), list(rows or [])):
            if str(row.get("Mode", "default") or "default") == "notch":
                notch_station_count += 1
            out.append(CorridorLoft._make_notch_profile_for_surface(w, row, scale))
        summary, diag_rows, ids = CorridorLoft._describe_notch_profile_rows(rows)
        schema_name = _notch_schema_name() if int(notch_station_count) > 0 else "-"
        return out, int(notch_station_count), notes, {"schema_name": schema_name, "summary": summary, "rows": diag_rows, "ids": ids, "spec_rows": rows}

    @staticmethod
    def _notch_split_candidates(rows):
        candidates = []
        split_station_rows = []
        if not rows or len(rows) < 2:
            return candidates, split_station_rows
        prev_mode = str(rows[0].get("Mode", "default") or "default").strip().lower()
        prev_roles = {str(v or "").strip().lower() for v in list(rows[0].get("Roles", []) or [])}
        for i in range(1, len(rows)):
            curr = rows[i]
            curr_mode = str(curr.get("Mode", "default") or "default").strip().lower()
            curr_roles = {str(v or "").strip().lower() for v in list(curr.get("Roles", []) or [])}
            split_here = False
            if curr_mode != prev_mode:
                split_here = True
            elif "start" in curr_roles or "transition_before" in curr_roles:
                split_here = True
            elif "end" in prev_roles or "transition_after" in prev_roles:
                split_here = True
            if split_here:
                candidates.append(int(i))
                rec = dict(curr.get("Record", {}) or {})
                if not rec:
                    rec = dict(rows[i - 1].get("Record", {}) or {})
                if rec:
                    split_station_rows.append(f"{float(rec.get('ResolvedProfileStation', 0.0) or 0.0):.3f}")
            prev_mode = curr_mode
            prev_roles = curr_roles
        dedup_idx = []
        dedup_sta = []
        seen = set()
        for idx, sta in zip(candidates, split_station_rows):
            key = (int(idx), str(sta))
            if key in seen:
                continue
            seen.add(key)
            dedup_idx.append(int(idx))
            dedup_sta.append(str(sta))
        return dedup_idx, dedup_sta

    @staticmethod
    def _build_notch_cutters(src, corridor_records):
        aln = _resolve_structure_alignment(src)
        if aln is None or getattr(aln, "Shape", None) is None:
            return [], []
        total = float(getattr(aln.Shape, "Length", 0.0) or 0.0)
        scale = get_length_scale(getattr(src, "Document", None), default=1.0)
        cutters = []
        notes = []
        for rec in list(corridor_records or []):
            mode = str(rec.get("ResolvedCorridorMode", "") or "").strip().lower()
            if mode != "notch":
                continue
            try:
                local = dict(rec)
                spec = CorridorLoft._structure_notch_spec(local, scale)
                rid = str(rec.get("Id", "") or f"#{int(rec.get('Index', 0)) + 1}")
                if not bool(spec.get("Enabled", False)):
                    notes.append(f"{rid}: {str(spec.get('Reason', 'notch disabled'))}")
                    continue
                mg = max(0.0, float(rec.get("ResolvedCorridorMargin", 0.0) or 0.0))
                base_s0 = float(rec.get("ResolvedStartStation", 0.0) or 0.0)
                base_s1 = float(rec.get("ResolvedEndStation", 0.0) or 0.0)
                span_rows = _resolve_corridor_record_span(src, rec, base_s0, base_s1)
                if len(span_rows) < 2:
                    span_rows = [
                        _resolve_corridor_record_at_station(src, rec, base_s0),
                        _resolve_corridor_record_at_station(src, rec, base_s1),
                    ]
                built = 0
                for i in range(max(0, len(span_rows) - 1)):
                    a = span_rows[i]
                    b = span_rows[i + 1]
                    ss0 = float(a.get("ResolvedProfileStation", base_s0) or base_s0)
                    ss1 = float(b.get("ResolvedProfileStation", base_s1) or base_s1)
                    if ss1 < ss0:
                        ss0, ss1 = ss1, ss0
                    if ss1 <= ss0 + 1e-9:
                        continue
                    sm = 0.5 * (ss0 + ss1)
                    local_seg = _resolve_corridor_record_at_station(src, rec, sm)
                    seg_spec = CorridorLoft._structure_notch_spec(local_seg, scale)
                    if not bool(seg_spec.get("Enabled", False)):
                        continue
                    long_pad = max(0.0, float(seg_spec.get("LongPad", 0.0) or 0.0))
                    seg_s0 = ss0
                    seg_s1 = ss1
                    if i == 0:
                        seg_s0 = max(0.0, seg_s0 - mg - long_pad)
                    if i == (len(span_rows) - 2):
                        seg_s1 = min(total, seg_s1 + mg + long_pad)
                    local_seg["Width"] = float(seg_spec.get("Width", local_seg.get("Width", 0.0) or 0.0) or 0.0)
                    local_seg["Height"] = float(seg_spec.get("Height", local_seg.get("Height", 0.0) or 0.0) or 0.0)
                    local_seg["StartStation"] = float(seg_s0)
                    local_seg["EndStation"] = float(seg_s1)
                    local_seg["CenterStation"] = float(0.5 * (seg_s0 + seg_s1))
                    if abs(float(local_seg.get("BottomElevation", 0.0) or 0.0)) > 1e-9:
                        local_seg["BottomElevation"] = float(local_seg.get("BottomElevation", 0.0) or 0.0) - float(seg_spec.get("BottomExtra", 0.0) or 0.0)
                    sta = max(0.0, min(total, float(local_seg["CenterStation"])))
                    p = _resolve_structure_station_point(src, sta, aln=aln)
                    try:
                        from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment

                        t = HorizontalAlignment.tangent_at_station(aln, sta)
                        n = HorizontalAlignment.normal_at_station(aln, sta)
                    except Exception:
                        t = App.Vector(1, 0, 0)
                        n = App.Vector(0, 1, 0)
                    for off in _structure_side_offsets(local_seg):
                        solid = _structure_record_solid(p + (n * float(off)), t, n, local_seg)
                        if solid is not None and not solid.isNull():
                            cutters.append(solid)
                            built += 1
                if built <= 0:
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
                CorridorLoft._clear_skip_markers(obj)
                obj.Shape = Part.Shape()
                obj.SectionCount = 0
                obj.PointCountPerSection = 0
                obj.AutoFixedSectionCount = 0
                obj.SchemaVersion = 0
                obj.FailedRanges = []
                obj.StructureSegmentCount = 0
                obj.StructureSplitStations = []
                obj.SkippedStationRanges = []
                obj.ResolvedStructureCorridorRanges = []
                obj.ResolvedStructureCorridorWarnings = []
                obj.ResolvedStructureCorridorModeSummary = "-"
                obj.ResolvedSkipBoundaryBehavior = "-"
                obj.ResolvedSkipBoundaryStates = []
                obj.ResolvedSkipBoundaryCapCount = 0
                obj.ResolvedStructureNotchCount = 0
                obj.ResolvedNotchStationCount = 0
                obj.ResolvedNotchSchemaName = "-"
                obj.ResolvedNotchProfileSummary = "-"
                obj.ResolvedNotchProfileRows = []
                obj.ResolvedNotchStructureIds = []
                obj.ResolvedNotchBuildMode = "-"
                obj.ResolvedNotchCutterCount = 0
                obj.ClosedProfileSchemaVersion = 0
                obj.SkipMarkerCount = 0
                obj.ResolvedHeightLeft = 0.0
                obj.ResolvedHeightRight = 0.0
                obj.ResolvedRuledMode = "off"
                obj.TopProfileEdgeSummary = "-"
                obj.SubassemblySchemaVersion = 0
                obj.PracticalSectionMode = "simple"
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
                obj.PavementScheduleRows = []
                obj.StructureInteractionSummaryRows = []
                obj.ExportSummaryRows = []
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
            h_left = 0.0
            h_right = 0.0
            height_source = "surface_only"
            loft_wires = list(norm_wires)
            ruled, ruled_mode = CorridorLoft._resolve_ruled_mode(obj, src, pt_count)
            obj.TopProfileEdgeSummary = str(getattr(src, "TopProfileEdgeSummary", "-") or "-")
            obj.SubassemblySchemaVersion = int(getattr(src, "SubassemblySchemaVersion", 0) or 0)
            obj.PracticalSectionMode = str(getattr(src, "PracticalSectionMode", "simple") or "simple")
            obj.TypicalSectionAdvancedComponentCount = int(getattr(src, "TypicalSectionAdvancedComponentCount", 0) or 0)
            obj.PavementLayerCount = int(getattr(src, "PavementLayerCount", 0) or 0)
            obj.EnabledPavementLayerCount = int(getattr(src, "EnabledPavementLayerCount", 0) or 0)
            obj.PavementTotalThickness = float(getattr(src, "PavementTotalThickness", 0.0) or 0.0)
            obj.PavementLayerSummaryRows = list(getattr(src, "PavementLayerSummaryRows", []) or [])
            obj.SubassemblyContractRows = list(getattr(src, "SubassemblyContractRows", []) or [])
            obj.SubassemblyValidationRows = list(getattr(src, "SubassemblyValidationRows", []) or [])
            obj.RoadsideLibraryRows = list(getattr(src, "RoadsideLibraryRows", []) or [])
            obj.RoadsideLibrarySummary = str(getattr(src, "RoadsideLibrarySummary", "-") or "-")
            obj.ReportSchemaVersion = int(getattr(src, "ReportSchemaVersion", 1) or 1)
            obj.SectionComponentSummaryRows = list(getattr(src, "SectionComponentSummaryRows", []) or [])
            obj.PavementScheduleRows = list(getattr(src, "PavementScheduleRows", []) or [])
            obj.StructureInteractionSummaryRows = list(getattr(src, "StructureInteractionSummaryRows", []) or [])
            closed_profile_schema = 0
            split_count = 0
            split_station_rows = []
            structure_ranges = []
            skipped_station_rows = []
            skip_runs = []
            skip_boundary_behavior = "-"
            skip_boundary_rows = []
            skip_boundary_cap_count = 0
            notch_count = 0
            notch_schema_name = "-"
            notch_profile_summary = "-"
            notch_profile_rows = []
            notch_structure_ids = []
            notch_spec_rows = []
            notch_build_mode = "-"
            notch_cutter_count = 0
            fallback_mode = str(getattr(obj, "DefaultStructureCorridorMode", "split_only") or "split_only").strip().lower()
            corridor_records = CorridorLoft._resolve_structure_corridor_records(src, fallback_mode=fallback_mode)
            corridor_range_rows, corridor_warning_rows, corridor_mode_summary, structure_spans = CorridorLoft._describe_structure_corridor_records(
                corridor_records
            )
            notch_station_count = 0
            notch_failures = []
            loft_retry_count = 0
            if bool(getattr(obj, "UseStructureCorridorModes", True)):
                notch_wires, notch_station_count, notch_notes, notch_meta = CorridorLoft._make_profiles_with_notch_schema(
                    norm_wires,
                    stations,
                    src,
                    fallback_mode=fallback_mode,
                    notch_transition_scale=float(getattr(obj, "NotchTransitionScale", 1.0) or 1.0),
                )
                notch_schema_name = str(notch_meta.get("schema_name", "-") or "-")
                notch_profile_summary = str(notch_meta.get("summary", "-") or "-")
                notch_profile_rows = list(notch_meta.get("rows", []) or [])
                notch_structure_ids = [str(v or "") for v in list(notch_meta.get("ids", []) or []) if str(v or "")]
                notch_spec_rows = list(notch_meta.get("spec_rows", []) or [])
                if notch_notes:
                    notch_failures.extend(list(notch_notes))
                if notch_wires:
                    loft_wires = list(notch_wires)
                    closed_profile_schema = 2
                    if notch_station_count > 0:
                        notch_count = max(1, len(notch_structure_ids), int(notch_count))
                        notch_build_mode = "schema_profiles"
            if closed_profile_schema > 1 and (not bool(ruled)):
                ruled = True
                ruled_mode = "auto:notch_schema"
            use_segmented_ranges = False
            if bool(getattr(obj, "SplitAtStructureZones", True)):
                split_idx, split_station_rows = CorridorLoft._structure_split_candidates(src, stations)
                if closed_profile_schema > 1 and notch_spec_rows:
                    notch_split_idx, notch_split_rows = CorridorLoft._notch_split_candidates(notch_spec_rows)
                    split_idx = list(split_idx or []) + list(notch_split_idx or [])
                    split_station_rows = list(split_station_rows or []) + list(notch_split_rows or [])
                dedup_split_rows = []
                seen_split_rows = set()
                for row in list(split_station_rows or []):
                    txt = str(row or "").strip()
                    if not txt or txt in seen_split_rows:
                        continue
                    seen_split_rows.add(txt)
                    dedup_split_rows.append(txt)
                split_station_rows = dedup_split_rows
                structure_ranges = CorridorLoft._segment_ranges(len(stations), split_idx)
                split_count = len(structure_ranges) if structure_ranges else 0
                use_segmented_ranges = bool(structure_ranges and len(structure_ranges) >= 2)
            if bool(getattr(obj, "UseStructureCorridorModes", True)):
                skip_ranges, skipped_station_rows, skip_runs = CorridorLoft._skip_zone_keep_ranges(stations, structure_spans)
                skip_boundary_behavior, skip_boundary_rows, skip_boundary_cap_count = CorridorLoft._skip_zone_boundary_summary(stations, skip_runs)
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
            skip_marker_count = 0
            struct_src = _resolve_structure_source(src) if bool(getattr(src, "UseStructureSet", False)) else None
            ext_count = _external_shape_display_count(struct_src)
            ext_proxy_count = _external_shape_proxy_count(struct_src)

            def _build_status(head: str):
                tokens = [
                    "output=surface",
                    f"minSpacing={float(min_spacing):.3f}",
                    f"used={len(stations)}",
                    f"dropped={int(dropped)}",
                    f"autoFixed={int(fixed_count)}",
                    f"ruled={ruled_mode}",
                    _corridor_rule_status_token(split_count, corridor_mode_summary, skipped_station_rows, corridor_warning_rows),
                    _earthwork_status_token(
                        struct_src=struct_src,
                        resolved_count=int(getattr(src, "ResolvedStructureCount", 0) or 0),
                        ext_count=ext_count,
                        proxy_count=ext_proxy_count,
                        overrides_enabled=bool(getattr(src, "ApplyStructureOverrides", False)),
                    ),
                ]
                if split_count >= 2:
                    tokens.append(f"structureSegs={int(split_count)}")
                if str(corridor_mode_summary or "-") != "-":
                    tokens.append(f"corridorModes={corridor_mode_summary}")
                if skipped_station_rows:
                    tokens.append(f"skipZones={len(skipped_station_rows)}")
                if skip_marker_count > 0:
                    tokens.append(f"skipMarkers={int(skip_marker_count)}")
                if str(skip_boundary_behavior or "-") == "caps_deferred":
                    tokens.append("skipCaps=deferred")
                if skip_boundary_rows:
                    tags = []
                    for row in skip_boundary_rows:
                        tag = str(row).split(":", 1)[0]
                        if tag not in tags:
                            tags.append(tag)
                    tokens.append(f"skipBoundary={','.join(tags)}")
                if corridor_warning_rows:
                    tokens.append(f"corridorWarn={len(corridor_warning_rows)}")
                if notch_count > 0:
                    tokens.append(f"notches={int(notch_count)}")
                if notch_station_count > 0:
                    tokens.append(f"notchStations={int(notch_station_count)}")
                if closed_profile_schema > 1:
                    tokens.append(f"profileSchema={int(closed_profile_schema)}")
                if str(notch_schema_name or "-") != "-":
                    tokens.append(f"notchSchema={notch_schema_name}")
                if str(notch_profile_summary or "-") != "-":
                    tokens.append(f"notchProfile={notch_profile_summary}")
                if str(notch_build_mode or "-") != "-":
                    tokens.append(f"notchBuild={notch_build_mode}")
                if int(notch_cutter_count or 0) > 0:
                    tokens.append(f"notchCutters={int(notch_cutter_count)}")
                if int(loft_retry_count or 0) > 0:
                    tokens.append(f"loftRetry={int(loft_retry_count)}")
                tokens.append(f"srcSchema={int(schema)}")
                tokens.append(f"topProfile={str(getattr(src, 'TopProfileSource', 'assembly_simple') or 'assembly_simple')}")
                tokens.append(f"topEdges={str(getattr(src, 'TopProfileEdgeSummary', '-') or '-')}")
                if int(getattr(src, "SubassemblySchemaVersion", 0) or 0) > 0:
                    tokens.append(f"subSchema={int(getattr(src, 'SubassemblySchemaVersion', 0) or 0)}")
                    tokens.append(f"practical={str(getattr(src, 'PracticalSectionMode', 'simple') or 'simple')}")
                if str(getattr(src, "RoadsideLibrarySummary", "-") or "-") != "-":
                    tokens.append(f"roadside={str(getattr(src, 'RoadsideLibrarySummary', '-') or '-')}")
                if len(list(getattr(src, "SubassemblyValidationRows", []) or [])) > 0:
                    tokens.append(f"subWarn={len(list(getattr(src, 'SubassemblyValidationRows', []) or []))}")
                if int(getattr(src, "TypicalSectionAdvancedComponentCount", 0) or 0) > 0:
                    tokens.append(f"typicalAdvanced={int(getattr(src, 'TypicalSectionAdvancedComponentCount', 0) or 0)}")
                if float(getattr(src, "PavementTotalThickness", 0.0) or 0.0) > 1e-9:
                    tokens.append(f"pavement={float(getattr(src, 'PavementTotalThickness', 0.0) or 0.0):.3f}m")
                if int(getattr(src, "PavementLayerCount", 0) or 0) > 0:
                    tokens.append(
                        f"pavLayers={int(getattr(src, 'EnabledPavementLayerCount', 0) or 0)}/{int(getattr(src, 'PavementLayerCount', 0) or 0)}"
                    )
                if ext_count > 0:
                    tokens.append(_display_only_status_token(ext_count))
                    tokens.append(f"externalShapeDisplayOnly={int(ext_count)}")
                if ext_proxy_count > 0:
                    tokens.append(f"externalShapeProxy={int(ext_proxy_count)}")
                if notch_failures:
                    tokens.append(f"notchWarn={len(notch_failures)}")
                return _status_join(head, *tokens)

            try:
                shape, failed_ranges, retry_used = CorridorLoft._loft_with_retry(
                    loft_wires,
                    stations,
                    structure_ranges if use_segmented_ranges else [],
                    ruled=ruled,
                    src=src,
                    solid=False,
                )
                if retry_used and str(ruled_mode or "off") == "off":
                    ruled_mode = "retry:typical_section"
                elif retry_used:
                    ruled_mode = f"{ruled_mode}+retry"
                try:
                    skip_marker_count = CorridorLoft._create_skip_markers(obj, stations, loft_wires, skip_runs)
                except Exception as marker_ex:
                    skip_marker_count = 0
                    notch_failures.append(f"skipMarkers: {marker_ex}")
                if failed_ranges:
                    if str(notch_build_mode or "-") == "schema_profiles":
                        notch_build_mode = "schema_profiles+adaptive_loft"
                    status = _build_status(
                        f"WARN (Surface): structure-aware segmented fallback used ({len(failed_ranges)} failed ranges)"
                    )
                else:
                    status = _build_status("OK (Surface)")
            except Exception as ex:
                if use_segmented_ranges:
                    shape, failed_ranges, retry_used = CorridorLoft._loft_with_retry(
                        loft_wires,
                        stations,
                        structure_ranges,
                        ruled=ruled,
                        src=src,
                        solid=False,
                    )
                else:
                    shape, failed_ranges = CorridorLoft._loft_adaptive(
                        loft_wires,
                        stations,
                        ruled=(True if CorridorLoft._should_retry_with_ruled(src, ruled) else ruled),
                        solid=False,
                    )
                    retry_used = CorridorLoft._should_retry_with_ruled(src, ruled) and not bool(ruled)
                if retry_used and str(ruled_mode or "off") == "off":
                    ruled_mode = "retry:typical_section"
                elif retry_used:
                    ruled_mode = f"{ruled_mode}+retry"
                try:
                    skip_marker_count = CorridorLoft._create_skip_markers(obj, stations, loft_wires, skip_runs)
                except Exception as marker_ex:
                    skip_marker_count = 0
                    notch_failures.append(f"skipMarkers: {marker_ex}")
                loft_retry_count = 1
                if use_segmented_ranges and not failed_ranges:
                    status = _build_status(f"OK (Surface): recovered after loft retry ({ex})")
                else:
                    if str(notch_build_mode or "-") == "schema_profiles":
                        notch_build_mode = "schema_profiles+adaptive_loft"
                    status = _build_status(
                        f"WARN (Surface): full loft failed, adaptive fallback used ({len(failed_ranges)} failed ranges): {ex}"
                    )

            obj.Shape = shape
            obj.SectionCount = len(stations)
            obj.PointCountPerSection = int(pt_count)
            obj.AutoFixedSectionCount = int(fixed_count)
            obj.SchemaVersion = int(schema)
            obj.FailedRanges = list(failed_ranges)
            obj.StructureSegmentCount = int(split_count)
            obj.StructureSplitStations = list(split_station_rows)
            obj.SkippedStationRanges = list(skipped_station_rows)
            obj.ResolvedStructureCorridorRanges = list(corridor_range_rows)
            obj.ResolvedStructureCorridorWarnings = list(corridor_warning_rows)
            obj.ResolvedStructureCorridorModeSummary = str(corridor_mode_summary or "-")
            obj.ResolvedSkipBoundaryBehavior = str(skip_boundary_behavior or "-")
            obj.ResolvedSkipBoundaryStates = list(skip_boundary_rows)
            obj.ResolvedSkipBoundaryCapCount = int(skip_boundary_cap_count)
            obj.ResolvedStructureNotchCount = int(notch_count)
            obj.ResolvedNotchStationCount = int(notch_station_count)
            obj.ResolvedNotchSchemaName = str(notch_schema_name or "-")
            obj.ResolvedNotchProfileSummary = str(notch_profile_summary or "-")
            obj.ResolvedNotchProfileRows = list(notch_profile_rows)
            obj.ResolvedNotchStructureIds = list(notch_structure_ids)
            obj.ResolvedNotchBuildMode = str(notch_build_mode or "-")
            obj.ResolvedNotchCutterCount = int(notch_cutter_count)
            obj.ClosedProfileSchemaVersion = int(closed_profile_schema)
            obj.SkipMarkerCount = int(skip_marker_count)
            obj.ResolvedHeightLeft = 0.0
            obj.ResolvedHeightRight = 0.0
            obj.ResolvedRuledMode = str(ruled_mode)
            obj.ExportSummaryRows = [
                _report_row(
                    "export",
                    target="corridor_loft",
                    reportSchema=int(getattr(obj, "ReportSchemaVersion", 1) or 1),
                    output="surface",
                    sectionSchema=int(schema or 0),
                    practical=str(getattr(obj, "PracticalSectionMode", "simple") or "simple"),
                    sections=int(len(stations)),
                    splitSegments=int(split_count or 0),
                    skipped=int(len(skipped_station_rows)),
                    notchCount=int(notch_count or 0),
                    ruled=str(ruled_mode or "off"),
                    roadside=str(getattr(obj, "RoadsideLibrarySummary", "-") or "-"),
                )
            ]
            obj.Status = status
            _mark_recompute_flag(obj, False)

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False

        except Exception as ex:
            CorridorLoft._clear_skip_markers(obj)
            obj.Shape = Part.Shape()
            obj.SectionCount = 0
            obj.PointCountPerSection = 0
            obj.AutoFixedSectionCount = 0
            obj.SchemaVersion = 0
            obj.FailedRanges = []
            obj.StructureSegmentCount = 0
            obj.StructureSplitStations = []
            obj.SkippedStationRanges = []
            obj.ResolvedStructureCorridorRanges = []
            obj.ResolvedStructureCorridorWarnings = []
            obj.ResolvedStructureCorridorModeSummary = "-"
            obj.ResolvedSkipBoundaryBehavior = "-"
            obj.ResolvedSkipBoundaryStates = []
            obj.ResolvedSkipBoundaryCapCount = 0
            obj.ResolvedStructureNotchCount = 0
            obj.ResolvedNotchStationCount = 0
            obj.ResolvedNotchSchemaName = "-"
            obj.ResolvedNotchProfileSummary = "-"
            obj.ResolvedNotchProfileRows = []
            obj.ResolvedNotchStructureIds = []
            obj.ResolvedNotchBuildMode = "-"
            obj.ResolvedNotchCutterCount = 0
            obj.ClosedProfileSchemaVersion = 0
            obj.SkipMarkerCount = 0
            obj.ResolvedHeightLeft = 0.0
            obj.ResolvedHeightRight = 0.0
            obj.ResolvedRuledMode = "off"
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
            obj.PavementScheduleRows = []
            obj.StructureInteractionSummaryRows = []
            obj.ExportSummaryRows = []
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
            "NotchTransitionScale",
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
