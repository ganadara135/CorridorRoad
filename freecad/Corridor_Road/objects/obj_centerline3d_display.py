# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App

# CorridorRoad/objects/obj_centerline3d_display.py
import Part

from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_centerline3d import Centerline3D
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, find_region_plan_objects
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


def _kind_display_name(kind: str) -> str:
    token = str(kind or "").strip().lower()
    mapping = {
        "base": "Base",
        "horizontal_ip": "Horizontal IP",
        "horizontal_transition": "Horizontal Transition",
        "vertical_curve": "Vertical Curve",
        "region_boundary": "Region Boundary",
        "region_transition": "Region Transition",
        "structure_zone": "Structure Zone",
        "structure_transition": "Structure Transition",
        "mixed": "Mixed",
        "endpoint": "Endpoint",
        "boundary": "Boundary",
    }
    return mapping.get(token, token.replace("_", " ").title() if token else "Boundary")


def _marker_kind_color(kind: str):
    token = str(kind or "").strip().lower()
    mapping = {
        "region_boundary": (0.35, 0.82, 0.56),
        "region_transition": (1.00, 0.68, 0.18),
        "structure_zone": (0.94, 0.38, 0.38),
        "structure_transition": (1.00, 0.35, 0.35),
        "mixed": (0.86, 0.54, 0.98),
        "endpoint": (0.70, 0.70, 0.70),
    }
    return mapping.get(token, (0.95, 0.80, 0.30))


_DISPLAY_QUALITY_PRESETS = ("Fast", "Normal", "Fine", "Ultra")
_DISPLAY_WIRE_MODES = ("SmoothSpline", "Polyline")
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
_HIDDEN_PROPERTY_NAMES = (
    "SourceCenterline",
    "MaxChordError",
    "MinStep",
    "MaxStep",
    "UseKeyStations",
    "DisplayQuality",
    "DisplayStations",
    "DisplayPoints",
    "DisplayPointCount",
    "DisplayPolicySummary",
    "MostDetailedSegmentSummary",
    "SegmentRows",
    "BoundaryMarkerRows",
    "SegmentBoundaryStations",
    "LengthSchemaVersion",
)


def ensure_centerline3d_display_properties(obj):
    # Hard-remove legacy display compatibility properties.
    for legacy_prop in (
        "SamplingInterval",
        "SampledStations",
        "SampledPoints",
        "SampleCount",
        "DensestSegmentSummary",
        "SamplingPolicySummary",
    ):
        try:
            if hasattr(obj, legacy_prop):
                obj.removeProperty(legacy_prop)
        except Exception:
            pass

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

    if not hasattr(obj, "ElevationSource"):
        obj.addProperty("App::PropertyEnumeration", "ElevationSource", "Source", "Elevation source mode")
        obj.ElevationSource = ["Auto", "VerticalAlignment", "ProfileBundleFG", "FlatZero"]
        obj.ElevationSource = "Auto"

    if not hasattr(obj, "ShowWire"):
        obj.addProperty("App::PropertyBool", "ShowWire", "Display", "Show 3D centerline wire")
        obj.ShowWire = True
    if not hasattr(obj, "DisplayWireMode"):
        obj.addProperty("App::PropertyEnumeration", "DisplayWireMode", "Display", "Visible 3D wire display mode")
        obj.DisplayWireMode = list(_DISPLAY_WIRE_MODES)
        obj.DisplayWireMode = "SmoothSpline"
    if not hasattr(obj, "ShowBoundaryMarkers"):
        obj.addProperty("App::PropertyBool", "ShowBoundaryMarkers", "Display", "Show semantic boundary marker child objects")
        obj.ShowBoundaryMarkers = True
    if not hasattr(obj, "BoundaryMarkerLength"):
        obj.addProperty("App::PropertyFloat", "BoundaryMarkerLength", "Display", "Boundary marker line length (m)")
        obj.BoundaryMarkerLength = 4.0
    if not hasattr(obj, "IncludeEndpointBoundaryMarkers"):
        obj.addProperty("App::PropertyBool", "IncludeEndpointBoundaryMarkers", "Display", "Include start/end boundary markers")
        obj.IncludeEndpointBoundaryMarkers = False

    if not hasattr(obj, "MaxChordError"):
        obj.addProperty("App::PropertyFloat", "MaxChordError", "Internal", "Internal maximum display chord error (m)")
        obj.MaxChordError = 0.02
    else:
        try:
            obj.setGroupOfProperty("MaxChordError", "Internal")
        except Exception:
            pass

    if not hasattr(obj, "MinStep"):
        obj.addProperty("App::PropertyFloat", "MinStep", "Internal", "Internal minimum display station step (m)")
        obj.MinStep = 0.5
    else:
        try:
            obj.setGroupOfProperty("MinStep", "Internal")
        except Exception:
            pass

    if not hasattr(obj, "MaxStep"):
        obj.addProperty("App::PropertyFloat", "MaxStep", "Internal", "Internal maximum display station step (m)")
        obj.MaxStep = 10.0
    else:
        try:
            obj.setGroupOfProperty("MaxStep", "Internal")
        except Exception:
            pass

    if not hasattr(obj, "UseKeyStations"):
        obj.addProperty("App::PropertyBool", "UseKeyStations", "Internal", "Internal toggle to always include key stations (edge bounds, BVC/EVC)")
        obj.UseKeyStations = True
    else:
        try:
            obj.setGroupOfProperty("UseKeyStations", "Internal")
        except Exception:
            pass
    if not hasattr(obj, "SegmentByRegions"):
        obj.addProperty("App::PropertyBool", "SegmentByRegions", "Display", "Split visible display at RegionPlan boundaries and transitions")
        obj.SegmentByRegions = True
    else:
        try:
            obj.setGroupOfProperty("SegmentByRegions", "Display")
        except Exception:
            pass
    if not hasattr(obj, "SegmentByStructures"):
        obj.addProperty("App::PropertyBool", "SegmentByStructures", "Display", "Split visible display at StructureSet boundaries and transitions")
        obj.SegmentByStructures = True
    else:
        try:
            obj.setGroupOfProperty("SegmentByStructures", "Display")
        except Exception:
            pass
    if not hasattr(obj, "DisplayQuality"):
        obj.addProperty("App::PropertyEnumeration", "DisplayQuality", "Internal", "Internal display-point generation quality preset")
        obj.DisplayQuality = list(_DISPLAY_QUALITY_PRESETS)
        obj.DisplayQuality = "Normal"
    else:
        try:
            obj.setGroupOfProperty("DisplayQuality", "Internal")
        except Exception:
            pass

    if not hasattr(obj, "DisplayStations"):
        obj.addProperty("App::PropertyFloatList", "DisplayStations", "Result", "Visible display station values (m)")
    if not hasattr(obj, "DisplayPoints"):
        obj.addProperty("App::PropertyVectorList", "DisplayPoints", "Result", "Visible 3D display points")
    if not hasattr(obj, "DisplayPointCount"):
        obj.addProperty("App::PropertyInteger", "DisplayPointCount", "Result", "Display point count")
        obj.DisplayPointCount = 0
    if not hasattr(obj, "DisplayPolicySummary"):
        obj.addProperty("App::PropertyString", "DisplayPolicySummary", "Result", "Applied display-point generation summary")
        obj.DisplayPolicySummary = "-"
    if not hasattr(obj, "MostDetailedSegmentSummary"):
        obj.addProperty("App::PropertyString", "MostDetailedSegmentSummary", "Result", "Most detailed planned display segment")
        obj.MostDetailedSegmentSummary = "-"
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
    if not hasattr(obj, "BoundaryMarkerRows"):
        obj.addProperty("App::PropertyStringList", "BoundaryMarkerRows", "Result", "Structured boundary marker rows")
        obj.BoundaryMarkerRows = []
    if not hasattr(obj, "BoundaryMarkerCount"):
        obj.addProperty("App::PropertyInteger", "BoundaryMarkerCount", "Result", "Generated boundary marker object count")
        obj.BoundaryMarkerCount = 0
    if not hasattr(obj, "BoundaryMarkerKindSummary"):
        obj.addProperty("App::PropertyString", "BoundaryMarkerKindSummary", "Result", "Boundary marker kind summary")
        obj.BoundaryMarkerKindSummary = "-"
    if not hasattr(obj, "ActiveWireDisplayMode"):
        obj.addProperty("App::PropertyString", "ActiveWireDisplayMode", "Result", "Resolved display wire mode")
        obj.ActiveWireDisplayMode = "SmoothSpline"
    if not hasattr(obj, "SourceTransitionGeometry"):
        obj.addProperty("App::PropertyString", "SourceTransitionGeometry", "Result", "Resolved source transition geometry mode")
        obj.SourceTransitionGeometry = "-"
    if not hasattr(obj, "SourceEdgeTypeSummary"):
        obj.addProperty("App::PropertyString", "SourceEdgeTypeSummary", "Result", "Resolved source edge makeup summary")
        obj.SourceEdgeTypeSummary = "-"
    if not hasattr(obj, "SegmentBoundaryStations"):
        obj.addProperty("App::PropertyStringList", "SegmentBoundaryStations", "Result", "Segment boundary station list with source labels")
        obj.SegmentBoundaryStations = []

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
    for internal_prop in _HIDDEN_PROPERTY_NAMES:
        try:
            obj.setEditorMode(internal_prop, 2)
        except Exception:
            pass


class Centerline3DDisplay:
    """
    Display-only object for Centerline3D.
    Uses internal display-point generation to represent curved 3D geometry.
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
        obj.BoundaryMarkerRows = []
        obj.BoundaryMarkerCount = 0
        obj.BoundaryMarkerKindSummary = "-"
        obj.SegmentKindSummary = "-"
        obj.SegmentSplitSourceSummary = "-"
        obj.MostDetailedSegmentSummary = "-"
        obj.DisplayPolicySummary = "-"

    @staticmethod
    def _clear_display_outputs(obj):
        obj.DisplayStations = []
        obj.DisplayPoints = []
        obj.DisplayPointCount = 0

    @staticmethod
    def _set_display_outputs(obj, display_stations, display_points):
        obj.DisplayStations = list(display_stations or [])
        obj.DisplayPoints = list(display_points or [])
        obj.DisplayPointCount = len(list(display_points or []))

    @staticmethod
    def _publish_segment_diagnostics(obj, segment_rows, merged_markers, display_stations):
        obj.SegmentCount = len(list(segment_rows or []))
        obj.SegmentRows = Centerline3DDisplay._segment_rows_to_strings(segment_rows)
        obj.SegmentBoundaryStations = Centerline3DDisplay._marker_rows_to_strings(merged_markers)
        obj.SegmentKindSummary = _count_summary(segment_rows, "kind")
        obj.SegmentSplitSourceSummary = _count_summary(
            [{"source": src0} for row in list(merged_markers or []) for src0 in list(row.get("sources", []) or [])],
            "source",
        )
        obj.MostDetailedSegmentSummary = Centerline3DDisplay._most_detailed_segment_summary(segment_rows, display_stations)
        obj.DisplayPolicySummary = Centerline3DDisplay._display_policy_summary(obj, segment_rows)

    @staticmethod
    def _boundary_marker_objects(obj):
        doc = getattr(obj, "Document", None)
        if doc is None:
            return []
        out = []
        for ch in list(getattr(doc, "Objects", []) or []):
            try:
                if not str(getattr(ch, "Name", "") or "").startswith("CenterlineBoundaryMarker"):
                    continue
                if getattr(ch, "ParentCenterline3DDisplay", None) != obj:
                    continue
                out.append(ch)
            except Exception:
                continue
        out.sort(key=lambda item: float(getattr(item, "MarkerStation", 0.0) or 0.0))
        return out

    @staticmethod
    def _ensure_boundary_marker_properties(obj):
        if not hasattr(obj, "ParentCenterline3DDisplay"):
            obj.addProperty("App::PropertyLink", "ParentCenterline3DDisplay", "Centerline", "Owning Centerline3DDisplay")
        if not hasattr(obj, "MarkerStation"):
            obj.addProperty("App::PropertyFloat", "MarkerStation", "Centerline", "Boundary marker station (m)")
            obj.MarkerStation = 0.0
        if not hasattr(obj, "MarkerKind"):
            obj.addProperty("App::PropertyString", "MarkerKind", "Centerline", "Boundary marker kind")
            obj.MarkerKind = "-"
        if not hasattr(obj, "MarkerSources"):
            obj.addProperty("App::PropertyStringList", "MarkerSources", "Centerline", "Boundary marker sources")
            obj.MarkerSources = []
        try:
            obj.setEditorMode("ParentCenterline3DDisplay", 2)
        except Exception:
            pass

    @staticmethod
    def _filtered_boundary_marker_rows(merged_markers):
        out = []
        for row in list(merged_markers or []):
            sources = [str(v or "").strip() for v in list(row.get("sources", []) or []) if str(v or "").strip()]
            if not sources:
                continue
            internal_sources = [src for src in sources if src not in ("start", "end")]
            if not internal_sources:
                continue
            out.append({"station": float(row.get("station", 0.0) or 0.0), "sources": list(internal_sources)})
        return out

    @staticmethod
    def _filtered_boundary_marker_rows_for_display(display_obj, merged_markers):
        include_endpoints = bool(getattr(display_obj, "IncludeEndpointBoundaryMarkers", False))
        out = []
        for row in list(merged_markers or []):
            sources = [str(v or "").strip() for v in list(row.get("sources", []) or []) if str(v or "").strip()]
            if not sources:
                continue
            non_endpoints = [src for src in sources if src not in ("start", "end")]
            if non_endpoints:
                out.append({"station": float(row.get("station", 0.0) or 0.0), "sources": list(non_endpoints)})
            if include_endpoints and any(src in ("start", "end") for src in sources):
                out.append({"station": float(row.get("station", 0.0) or 0.0), "sources": ["endpoint"]})
        return out

    @staticmethod
    def _boundary_marker_kind(row):
        sources = list(row.get("sources", []) or [])
        if not sources:
            return "boundary"
        if sources == ["endpoint"]:
            return "endpoint"
        return Centerline3DDisplay._classify_segment_kind(sources)

    @staticmethod
    def _boundary_marker_shape(src_obj, station: float, marker_length_m: float, z_provider=None):
        frame = Centerline3D.frame_at_station(src_obj, float(station), z_provider=z_provider)
        p = frame.get("point", App.Vector(0.0, 0.0, 0.0))
        n = frame.get("N", App.Vector(0.0, 1.0, 0.0))
        z = frame.get("Z", App.Vector(0.0, 0.0, 1.0))
        if getattr(n, "Length", 0.0) <= 1e-9:
            n = App.Vector(0.0, 1.0, 0.0)
        else:
            n = n.normalize()
        half = max(0.05, 0.5 * float(marker_length_m))
        half_model = _units.model_length_from_meters(getattr(src_obj, "Document", None), half)
        z_offset = _units.model_length_from_meters(getattr(src_obj, "Document", None), 0.02)
        p0 = p - (n * half_model) + (z * z_offset)
        p1 = p + (n * half_model) + (z * z_offset)
        return Part.makeLine(p0, p1)

    @staticmethod
    def _boundary_marker_rows_to_strings(rows):
        out = []
        for row in list(rows or []):
            out.append(
                "station={station}|kind={kind}|sources={sources}".format(
                    station=_format_station_text(row.get("station", 0.0)),
                    kind=str(row.get("kind", "-") or "-"),
                    sources=",".join(list(row.get("sources", []) or [])) or "-",
                )
            )
        return out

    @staticmethod
    def _sync_boundary_marker_children(display_obj, src_obj, merged_markers, z_provider=None):
        rows = []
        if bool(getattr(display_obj, "ShowBoundaryMarkers", True)):
            for row in list(Centerline3DDisplay._filtered_boundary_marker_rows_for_display(display_obj, merged_markers) or []):
                row_copy = dict(row)
                row_copy["kind"] = Centerline3DDisplay._boundary_marker_kind(row)
                rows.append(row_copy)

        existing = Centerline3DDisplay._boundary_marker_objects(display_obj)
        doc = getattr(display_obj, "Document", None)
        if doc is None:
            display_obj.BoundaryMarkerRows = Centerline3DDisplay._boundary_marker_rows_to_strings(rows)
            display_obj.BoundaryMarkerCount = len(rows)
            return []

        created_or_kept = []
        prj = find_project(doc)
        marker_length_m = max(0.10, float(getattr(display_obj, "BoundaryMarkerLength", 4.0) or 4.0))
        for idx, row in enumerate(rows):
            if idx < len(existing):
                mk = existing[idx]
            else:
                mk = doc.addObject("Part::Feature", "CenterlineBoundaryMarker")
                Centerline3DDisplay._ensure_boundary_marker_properties(mk)
            Centerline3DDisplay._ensure_boundary_marker_properties(mk)
            mk.ParentCenterline3DDisplay = display_obj
            mk.MarkerStation = float(row.get("station", 0.0) or 0.0)
            mk.MarkerKind = str(row.get("kind", "-") or "-")
            mk.MarkerSources = list(row.get("sources", []) or [])
            mk.Label = f"Boundary [{_kind_display_name(mk.MarkerKind)}] @STA {_format_station_text(mk.MarkerStation)}"
            mk.Shape = Centerline3DDisplay._boundary_marker_shape(src_obj, mk.MarkerStation, marker_length_m, z_provider=z_provider)
            try:
                vobj = getattr(mk, "ViewObject", None)
                if vobj is not None:
                    vobj.Visibility = True
                    vobj.DisplayMode = "Wireframe"
                    vobj.LineWidth = 2
                    vobj.LineColor = _marker_kind_color(mk.MarkerKind)
                mk.setEditorMode("Placement", 2)
            except Exception:
                pass
            if prj is not None:
                try:
                    CorridorRoadProject.unadopt(prj, mk)
                except Exception:
                    pass
            created_or_kept.append(mk)

        for mk in list(existing[len(rows):] or []):
            try:
                doc.removeObject(mk.Name)
            except Exception:
                pass

        display_obj.BoundaryMarkerRows = Centerline3DDisplay._boundary_marker_rows_to_strings(rows)
        display_obj.BoundaryMarkerCount = len(rows)
        display_obj.BoundaryMarkerKindSummary = _count_summary(rows, "kind")
        return created_or_kept

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
                "idx={idx}|start={start}|end={end}|len={length}|kind={kind}|sources={sources}|points={points}|err={err}|min={min_step}|max={max_step}".format(
                    idx=int(row.get("index", 0) or 0),
                    start=_format_station_text(row.get("start", 0.0)),
                    end=_format_station_text(row.get("end", 0.0)),
                    length=_format_station_text(row.get("length", 0.0)),
                    kind=str(row.get("kind", "base") or "base"),
                    sources=",".join(list(row.get("boundary_sources", []) or [])) or "-",
                    points=int(row.get("display_point_count", 0) or 0),
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
    def _display_point_count_for_range(display_stations, s0: float, s1: float, tol: float = 1.0e-6):
        count = 0
        for value in list(display_stations or []):
            try:
                station = float(value)
            except Exception:
                continue
            if (float(s0) - tol) <= station <= (float(s1) + tol):
                count += 1
        return int(count)

    @staticmethod
    def _most_detailed_segment_summary(segment_rows, display_stations):
        best = None
        best_count = -1
        for row in list(segment_rows or []):
            count = int(row.get("display_point_count", 0) or 0)
            if count <= 0:
                count = Centerline3DDisplay._display_point_count_for_range(
                    display_stations,
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
            f" ({int(best_count)} points)"
        )

    @staticmethod
    def _display_quality_name(obj):
        raw = str(getattr(obj, "DisplayQuality", "Normal") or "Normal").strip()
        return raw if raw in _DISPLAY_QUALITY_FACTORS else "Normal"

    @staticmethod
    def _segment_display_policy(obj, row, max_err: float, min_step: float, max_step: float):
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
    def _display_policy_summary(obj, segment_rows):
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
    def _segment_display_stations(src_obj, z_provider, s0: float, s1: float, max_err: float, min_step: float, max_step: float):
        stations = [float(s0)]
        if float(s1) > float(s0) + 1.0e-9:
            Centerline3DDisplay._append_display_adaptive_stations(
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
        display_station_values = []
        planned_rows = []
        for row in list(segment_rows or []):
            policy = Centerline3DDisplay._segment_display_policy(display_obj, row, max_err, min_step, max_step)
            display_stations_seg = Centerline3DDisplay._segment_display_stations(
                src_obj,
                z_provider,
                row.get("start", 0.0),
                row.get("end", 0.0),
                max_err=policy["max_err"],
                min_step=policy["min_step"],
                max_step=policy["max_step"],
            )
            display_points_seg = [Centerline3D.point3d_at_station(src_obj, s, z_provider=z_provider) for s in display_stations_seg]
            row_copy = dict(row)
            row_copy["quality"] = str(policy.get("quality", "Normal"))
            row_copy["max_err"] = float(policy.get("max_err", max_err))
            row_copy["min_step"] = float(policy.get("min_step", min_step))
            row_copy["max_step"] = float(policy.get("max_step", max_step))
            row_copy["display_point_count"] = int(len(display_points_seg))
            planned_rows.append(row_copy)
            display_station_values.extend(display_stations_seg)

        display_stations = _unique_sorted(display_station_values)
        display_points = [Centerline3D.point3d_at_station(src_obj, s, z_provider=z_provider) for s in display_stations]
        if len(display_points) < 2:
            return Part.Shape(), display_stations, display_points, planned_rows
        shape = Centerline3DDisplay._build_display_shape(display_obj, display_points)
        return shape, display_stations, display_points, planned_rows

    @staticmethod
    def _safe_display_params(obj):
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
    def _requested_wire_mode(obj) -> str:
        raw = str(getattr(obj, "DisplayWireMode", "SmoothSpline") or "SmoothSpline").strip()
        return raw if raw in _DISPLAY_WIRE_MODES else "SmoothSpline"

    @staticmethod
    def _build_display_shape(obj, points):
        pts = list(points or [])
        requested = Centerline3DDisplay._requested_wire_mode(obj)
        if len(pts) < 2:
            obj.ActiveWireDisplayMode = requested
            return Part.Shape()
        if requested == "SmoothSpline" and len(pts) >= 3:
            try:
                curve = Part.BSplineCurve()
                curve.interpolate(pts)
                obj.ActiveWireDisplayMode = "SmoothSpline"
                return curve.toShape()
            except Exception:
                pass
        obj.ActiveWireDisplayMode = "Polyline"
        return Part.makePolygon(pts)

    @staticmethod
    def _publish_source_geometry_diagnostics(obj, alignment_obj):
        if not str(getattr(obj, "ActiveWireDisplayMode", "") or "").strip():
            obj.ActiveWireDisplayMode = Centerline3DDisplay._requested_wire_mode(obj)
        if alignment_obj is None:
            obj.SourceTransitionGeometry = "-"
            obj.SourceEdgeTypeSummary = "-"
            return
        obj.SourceTransitionGeometry = str(getattr(alignment_obj, "TransitionGeometryMode", "-") or "-")
        obj.SourceEdgeTypeSummary = str(getattr(alignment_obj, "EdgeTypeSummary", "-") or "-")

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
    def _append_display_adaptive_stations(src_obj, z_provider, out_stations, s0: float, s1: float, max_err: float, min_step: float, max_step: float, depth: int):
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
            Centerline3DDisplay._append_display_adaptive_stations(src_obj, z_provider, out_stations, s0, sm, max_err, min_step, max_step, depth + 1)
            Centerline3DDisplay._append_display_adaptive_stations(src_obj, z_provider, out_stations, sm, s1, max_err, min_step, max_step, depth + 1)
            return

        out_stations.append(float(s1))

    def execute(self, obj):
        ensure_centerline3d_display_properties(obj)
        obj.ActiveWireDisplayMode = Centerline3DDisplay._requested_wire_mode(obj)
        try:
            if not bool(getattr(obj, "ShowWire", True)):
                obj.Shape = Part.Shape()
                Centerline3DDisplay._clear_display_outputs(obj)
                Centerline3DDisplay._sync_boundary_marker_children(obj, obj, [], z_provider=None)
                Centerline3DDisplay._reset_segment_diagnostics(obj)
                Centerline3DDisplay._publish_source_geometry_diagnostics(obj, getattr(obj, "Alignment", None))
                obj.Status = "Hidden"
                return

            src = getattr(obj, "SourceCenterline", None)
            if src is None:
                # Preferred mode: display uses its own source links and internal display settings.
                src = obj

            aln = getattr(src, "Alignment", None)
            if aln is None or aln.Shape is None or aln.Shape.isNull():
                obj.Shape = Part.Shape()
                Centerline3DDisplay._clear_display_outputs(obj)
                Centerline3DDisplay._sync_boundary_marker_children(obj, obj, [], z_provider=None)
                Centerline3DDisplay._reset_segment_diagnostics(obj)
                Centerline3DDisplay._publish_source_geometry_diagnostics(obj, None)
                obj.Status = "Source alignment is missing"
                obj.ResolvedElevationSource = "N/A"
                return

            Centerline3DDisplay._publish_source_geometry_diagnostics(obj, aln)

            total = float(getattr(aln, "TotalLength", 0.0) or 0.0)
            if total <= 1.0e-9:
                total = _units.meters_from_model_length(getattr(obj, "Document", None), float(getattr(aln.Shape, "Length", 0.0) or 0.0))
            if total <= 1e-9:
                obj.Shape = Part.Shape()
                Centerline3DDisplay._clear_display_outputs(obj)
                Centerline3DDisplay._sync_boundary_marker_children(obj, obj, [], z_provider=None)
                Centerline3DDisplay._reset_segment_diagnostics(obj)
                Centerline3DDisplay._publish_source_geometry_diagnostics(obj, aln)
                obj.Status = "Source alignment length is zero"
                obj.ResolvedElevationSource = "N/A"
                return

            source_name, z_provider = Centerline3D._resolve_z_provider(src)
            max_err, min_step, max_step = Centerline3DDisplay._safe_display_params(obj)

            merged_markers = Centerline3DDisplay._merge_split_markers(
                Centerline3DDisplay._collect_split_markers(obj, src, total)
            )
            segment_rows = Centerline3DDisplay._build_segment_rows(merged_markers)

            shape, display_stations, display_points, planned_rows = Centerline3DDisplay._build_segmented_display(
                obj,
                src,
                segment_rows,
                z_provider,
                max_err=max_err,
                min_step=min_step,
                max_step=max_step,
            )
            if len(display_points) < 2:
                obj.Shape = Part.Shape()
                Centerline3DDisplay._set_display_outputs(obj, display_stations, display_points)
                Centerline3DDisplay._publish_segment_diagnostics(obj, planned_rows, merged_markers, display_stations)
                Centerline3DDisplay._publish_source_geometry_diagnostics(obj, aln)
                obj.Status = "Insufficient display points"
                obj.ResolvedElevationSource = source_name
                return

            obj.Shape = shape
            Centerline3DDisplay._set_display_outputs(obj, display_stations, display_points)
            Centerline3DDisplay._publish_segment_diagnostics(obj, planned_rows, merged_markers, display_stations)
            Centerline3DDisplay._sync_boundary_marker_children(obj, src, merged_markers, z_provider=z_provider)
            obj.Status = "OK"
            obj.ResolvedElevationSource = source_name

        except Exception as ex:
            obj.Shape = Part.Shape()
            Centerline3DDisplay._clear_display_outputs(obj)
            Centerline3DDisplay._sync_boundary_marker_children(obj, obj, [], z_provider=None)
            Centerline3DDisplay._reset_segment_diagnostics(obj)
            Centerline3DDisplay._publish_source_geometry_diagnostics(obj, getattr(obj, "Alignment", None))
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
            "ElevationSource",
            "ShowWire",
            "DisplayWireMode",
            "ShowBoundaryMarkers",
            "BoundaryMarkerLength",
            "IncludeEndpointBoundaryMarkers",
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
            self.Object = getattr(vobj, "Object", None)
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

    def claimChildren(self):
        try:
            obj = getattr(self, "Object", None)
            return Centerline3DDisplay._boundary_marker_objects(obj) if obj is not None else []
        except Exception:
            return []

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines"]

    def getDefaultDisplayMode(self):
        return "Wireframe"

    def setDisplayMode(self, mode):
        return mode
