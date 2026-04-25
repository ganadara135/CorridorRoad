"""FreeCAD source/result object for v1 stationing rows."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from ..services.evaluation import AlignmentStationSamplingService
from .obj_alignment import find_v1_alignment, to_alignment_model


class V1StationingObject:
    """Document object proxy that stores evaluated v1 station rows."""

    Type = "V1Stationing"

    def __init__(self, obj):
        obj.Proxy = self
        ensure_v1_stationing_properties(obj)

    def execute(self, obj):
        ensure_v1_stationing_properties(obj)
        try:
            obj.Shape = build_v1_stationing_shape(obj)
        except Exception:
            if Part is not None:
                try:
                    obj.Shape = Part.Shape()
                except Exception:
                    pass
        return


class ViewProviderV1Stationing:
    """Simple display provider for v1 station ticks."""

    Type = "ViewProviderV1Stationing"

    def __init__(self, vobj):
        vobj.Proxy = self
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineColor = (1.0, 0.74, 0.18)
            vobj.LineWidth = 2.0
        except Exception:
            pass

    def getIcon(self):
        try:
            from ...misc.resources import icon_path

            return icon_path("stations.svg")
        except Exception:
            return ""


def ensure_v1_stationing_properties(obj) -> None:
    """Ensure the FreeCAD object has the minimal v1 stationing properties."""

    if obj is None:
        return
    _add_property(obj, "App::PropertyString", "V1ObjectType", "CorridorRoad", "v1 object type")
    _add_property(obj, "App::PropertyInteger", "SchemaVersion", "CorridorRoad", "v1 schema version")
    _add_property(obj, "App::PropertyString", "ProjectId", "CorridorRoad", "v1 project id")
    _add_property(obj, "App::PropertyString", "StationingId", "CorridorRoad", "v1 stationing id")
    _add_property(obj, "App::PropertyString", "AlignmentId", "CorridorRoad", "linked v1 alignment id")
    _add_property(obj, "App::PropertyFloat", "Interval", "Stations", "station sampling interval")
    _add_property(obj, "App::PropertyFloat", "MajorInterval", "Stations", "major station interval")
    _add_property(obj, "App::PropertyFloat", "StationStartOffset", "Stations", "display station offset")
    _add_property(obj, "App::PropertyString", "StationLabelFormat", "Stations", "station label format")
    _add_property(obj, "App::PropertyFloat", "MinorTickLength", "Display", "minor station tick length")
    _add_property(obj, "App::PropertyFloat", "MajorTickLength", "Display", "major station tick length")
    _add_property(obj, "App::PropertyBool", "ShowTicks", "Display", "show station ticks as shape")
    _add_property(obj, "App::PropertyFloatList", "StationValues", "Stations", "sampled stations")
    _add_property(obj, "App::PropertyStringList", "StationLabels", "Stations", "station labels")
    _add_property(obj, "App::PropertyStringList", "StationKinds", "Stations", "major/minor/key station kinds")
    _add_property(obj, "App::PropertyFloatList", "XValues", "Stations", "sampled x coordinates")
    _add_property(obj, "App::PropertyFloatList", "YValues", "Stations", "sampled y coordinates")
    _add_property(obj, "App::PropertyFloatList", "TangentDirections", "Stations", "sampled tangent directions")
    _add_property(obj, "App::PropertyStringList", "ActiveElementIds", "Stations", "active alignment element ids")
    _add_property(obj, "App::PropertyStringList", "ActiveElementKinds", "Stations", "active alignment element kinds")
    _add_property(obj, "App::PropertyStringList", "SourceReasons", "Stations", "station source reasons")
    _add_property(obj, "App::PropertyStringList", "ReviewRows", "Stations", "station review summary rows")
    _add_property(obj, "App::PropertyString", "SourceAlignmentLabel", "Source", "linked v1 alignment label")
    _add_property(obj, "App::PropertyInteger", "SourceGeometryElementCount", "Source", "source alignment geometry element count")
    _add_property(obj, "App::PropertyString", "SourceGeometrySignature", "Source", "source alignment geometry signature")
    _add_property(obj, "App::PropertyString", "ActiveElementKindSummary", "Diagnostics", "active element kind summary")
    _add_property(obj, "App::PropertyInteger", "TangentStationCount", "Diagnostics", "sampled tangent station count")
    _add_property(obj, "App::PropertyInteger", "CurveStationCount", "Diagnostics", "sampled curve station count")
    _add_property(obj, "App::PropertyInteger", "TransitionStationCount", "Diagnostics", "sampled transition station count")
    _add_property(obj, "App::PropertyInteger", "MajorStationCount", "Diagnostics", "sampled major station count")
    _add_property(obj, "App::PropertyInteger", "MinorStationCount", "Diagnostics", "sampled minor station count")
    _add_property(obj, "App::PropertyInteger", "KeyStationCount", "Diagnostics", "sampled key station count")
    _add_property(obj, "App::PropertyInteger", "DisplayTickCount", "Diagnostics", "display tick edge count")
    _add_property(obj, "App::PropertyString", "DisplayStatus", "Diagnostics", "station tick display status")
    _add_property(obj, "App::PropertyString", "Status", "Diagnostics", "stationing build status")
    _add_property(obj, "App::PropertyString", "Notes", "Diagnostics", "stationing build notes")
    _add_property(obj, "Part::PropertyPartShape", "Shape", "Display", "station tick display shape")

    if not str(getattr(obj, "V1ObjectType", "") or ""):
        obj.V1ObjectType = "V1Stationing"
    if int(getattr(obj, "SchemaVersion", 0) or 0) <= 0:
        obj.SchemaVersion = 1
    if not str(getattr(obj, "ProjectId", "") or ""):
        obj.ProjectId = "corridorroad-v1"
    if not str(getattr(obj, "StationingId", "") or ""):
        obj.StationingId = f"stationing:{str(getattr(obj, 'Name', '') or 'v1-stationing')}"
    if float(getattr(obj, "Interval", 0.0) or 0.0) <= 0.0:
        obj.Interval = 20.0
    if float(getattr(obj, "MajorInterval", 0.0) or 0.0) <= 0.0:
        obj.MajorInterval = max(float(getattr(obj, "Interval", 20.0) or 20.0) * 5.0, 1.0)
    if not str(getattr(obj, "StationLabelFormat", "") or ""):
        obj.StationLabelFormat = "STA_DECIMAL"
    if float(getattr(obj, "MinorTickLength", 0.0) or 0.0) <= 0.0:
        obj.MinorTickLength = 2.0
    if float(getattr(obj, "MajorTickLength", 0.0) or 0.0) <= 0.0:
        obj.MajorTickLength = 4.0
    try:
        if not hasattr(obj, "ShowTicks") or getattr(obj, "ShowTicks") is None:
            obj.ShowTicks = True
    except Exception:
        pass
    if not str(getattr(obj, "DisplayStatus", "") or ""):
        obj.DisplayStatus = "pending"
    if not str(getattr(obj, "Status", "") or ""):
        obj.Status = "empty"


def create_v1_stationing(
    document=None,
    *,
    project=None,
    alignment=None,
    interval: float = 20.0,
    label: str = "Stations",
):
    """Create one v1 stationing object by sampling a v1 alignment."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 stationing creation.")

    alignment_obj = alignment or find_v1_alignment(doc)
    alignment_model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    if alignment_model is None:
        raise RuntimeError("A V1Alignment is required before generating v1 stations.")

    try:
        obj = doc.addObject("Part::FeaturePython", "V1Stationing")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "V1Stationing")
    V1StationingObject(obj)
    try:
        ViewProviderV1Stationing(obj.ViewObject)
    except Exception:
        pass
    obj.Label = label
    obj.ProjectId = _project_id(project)
    obj.StationingId = f"stationing:{str(getattr(obj, 'Name', '') or 'stations')}"
    obj.AlignmentId = alignment_model.alignment_id
    obj.ShowTicks = True
    update_v1_stationing_from_alignment(obj, alignment_model, interval=interval)

    if project is not None:
        try:
            from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

            route_to_v1_tree(project, obj)
        except Exception:
            pass
    return obj


def update_v1_stationing_from_alignment(stationing, alignment_model, *, interval: float = 20.0):
    """Rebuild station rows on an existing V1Stationing object."""

    ensure_v1_stationing_properties(stationing)
    geometry_sequence = list(getattr(alignment_model, "geometry_sequence", []) or [])
    result = AlignmentStationSamplingService().sample_alignment(
        alignment=alignment_model,
        interval=interval,
        extra_stations=_alignment_key_stations(geometry_sequence),
    )
    rows = list(result.rows or [])
    stationing.AlignmentId = str(getattr(alignment_model, "alignment_id", "") or "")
    stationing.SourceAlignmentLabel = str(getattr(alignment_model, "label", "") or "")
    stationing.SourceGeometryElementCount = int(len(geometry_sequence))
    stationing.SourceGeometrySignature = _alignment_geometry_signature(alignment_model)
    stationing.Interval = float(interval)
    stationing.StationValues = [float(row.station) for row in rows]
    stationing.StationKinds = _station_kinds(
        rows,
        station_start_offset=float(getattr(stationing, "StationStartOffset", 0.0) or 0.0),
        major_interval=float(getattr(stationing, "MajorInterval", 0.0) or 0.0),
    )
    stationing.StationLabels = [
        _format_station_label(
            row.station,
            station_start_offset=float(getattr(stationing, "StationStartOffset", 0.0) or 0.0),
            label_format=str(getattr(stationing, "StationLabelFormat", "") or "STA_DECIMAL"),
        )
        for row in rows
    ]
    stationing.XValues = [float(row.x) for row in rows]
    stationing.YValues = [float(row.y) for row in rows]
    stationing.TangentDirections = [float(row.tangent_direction_deg) for row in rows]
    stationing.ActiveElementIds = [str(row.active_element_id) for row in rows]
    stationing.ActiveElementKinds = [str(row.active_element_kind) for row in rows]
    stationing.SourceReasons = [str(row.source_reason) for row in rows]
    stationing.ReviewRows = station_review_rows(stationing)
    kind_counts = _active_element_kind_counts(rows)
    station_kind_counts = _station_kind_counts(stationing.StationKinds)
    stationing.TangentStationCount = int(kind_counts.get("tangent", 0))
    stationing.CurveStationCount = int(
        kind_counts.get("sampled_curve", 0)
        + kind_counts.get("circular_curve", 0)
    )
    stationing.TransitionStationCount = int(kind_counts.get("transition_curve", 0))
    stationing.MajorStationCount = int(station_kind_counts.get("major", 0))
    stationing.MinorStationCount = int(station_kind_counts.get("minor", 0))
    stationing.KeyStationCount = int(station_kind_counts.get("key", 0))
    stationing.ActiveElementKindSummary = _format_kind_summary(kind_counts)
    stationing.Status = str(result.status)
    stationing.Notes = _stationing_notes(result.notes, stationing)
    try:
        stationing.touch()
    except Exception:
        pass
    return stationing


def station_review_rows(obj) -> list[str]:
    """Return compact station review rows for UI/diagnostics."""

    ensure_v1_stationing_properties(obj)
    stations = _float_list(getattr(obj, "StationValues", []) or [])
    labels = list(getattr(obj, "StationLabels", []) or [])
    xs = _float_list(getattr(obj, "XValues", []) or [])
    ys = _float_list(getattr(obj, "YValues", []) or [])
    tangents = _float_list(getattr(obj, "TangentDirections", []) or [])
    kinds = list(getattr(obj, "ActiveElementKinds", []) or [])
    station_kinds = list(getattr(obj, "StationKinds", []) or [])
    reasons = list(getattr(obj, "SourceReasons", []) or [])
    rows = []
    for index, station in enumerate(stations):
        label = str(labels[index]) if index < len(labels) and labels[index] else f"STA {station:.3f}"
        x = xs[index] if index < len(xs) else 0.0
        y = ys[index] if index < len(ys) else 0.0
        tangent = tangents[index] if index < len(tangents) else 0.0
        kind = str(kinds[index]) if index < len(kinds) and kinds[index] else "-"
        station_kind = str(station_kinds[index]) if index < len(station_kinds) and station_kinds[index] else "-"
        reason = str(reasons[index]) if index < len(reasons) and reasons[index] else "-"
        rows.append(
            f"{label} | kind={station_kind} | XY=({x:.3f}, {y:.3f}) | tangent={tangent:.3f} deg | element={kind} | reason={reason}"
        )
    return rows


def find_v1_stationing(document, preferred_stationing=None):
    """Find a v1 stationing object in a document, honoring an explicit preferred object."""

    if _is_v1_stationing(preferred_stationing):
        return preferred_stationing
    if document is None:
        return None
    for obj in list(getattr(document, "Objects", []) or []):
        if _is_v1_stationing(obj):
            return obj
    return None


def station_value_rows(obj) -> list[tuple[float, str]]:
    """Return station-label tuples from one V1Stationing object."""

    if not _is_v1_stationing(obj):
        return []
    ensure_v1_stationing_properties(obj)
    stations = _float_list(getattr(obj, "StationValues", []) or [])
    labels = list(getattr(obj, "StationLabels", []) or [])
    rows = []
    for index, station in enumerate(stations):
        label = str(labels[index]) if index < len(labels) and labels[index] else f"STA {station:.3f}"
        rows.append((float(station), label))
    return rows


def build_v1_stationing_shape(obj):
    """Build station tick display shape from sampled station rows."""

    if Part is None or App is None:
        return None
    ensure_v1_stationing_properties(obj)
    if not bool(getattr(obj, "ShowTicks", True)):
        try:
            obj.DisplayTickCount = 0
            obj.DisplayStatus = "hidden"
        except Exception:
            pass
        return Part.Shape()

    xs = _float_list(getattr(obj, "XValues", []) or [])
    ys = _float_list(getattr(obj, "YValues", []) or [])
    tangents = _float_list(getattr(obj, "TangentDirections", []) or [])
    station_kinds = list(getattr(obj, "StationKinds", []) or [])
    count = min(len(xs), len(ys), len(tangents))
    edges = []
    for index in range(count):
        kind = str(station_kinds[index]) if index < len(station_kinds) and station_kinds[index] else "minor"
        tick_length = float(getattr(obj, "MajorTickLength", 4.0) or 4.0) if kind in {"major", "key"} else float(getattr(obj, "MinorTickLength", 2.0) or 2.0)
        if tick_length <= 0.0:
            continue
        tangent_rad = _math_radians(float(tangents[index]))
        normal_x = -_math_sin(tangent_rad)
        normal_y = _math_cos(tangent_rad)
        half = 0.5 * tick_length
        center = App.Vector(float(xs[index]), float(ys[index]), 0.0)
        a = App.Vector(center.x - normal_x * half, center.y - normal_y * half, 0.0)
        b = App.Vector(center.x + normal_x * half, center.y + normal_y * half, 0.0)
        if (b - a).Length > 1.0e-9:
            edges.append(Part.makeLine(a, b))
    try:
        obj.DisplayTickCount = int(len(edges))
        obj.DisplayStatus = "ok" if edges else "empty"
    except Exception:
        pass
    if not edges:
        return Part.Shape()
    if len(edges) == 1:
        return edges[0]
    return Part.Compound(edges)


def _alignment_key_stations(elements) -> list[float]:
    """Include element starts/ends and curve midpoints so stationing exposes curve zones."""

    values: list[float] = []
    for element in list(elements or []):
        try:
            start = float(element.station_start)
            end = float(element.station_end)
        except Exception:
            continue
        values.extend([start, end])
        kind = str(getattr(element, "kind", "") or "")
        if kind in {"sampled_curve", "circular_curve", "transition_curve"}:
            values.append(0.5 * (start + end))
    return values


def _alignment_geometry_signature(alignment_model) -> str:
    """Build a compact signature for detecting stale stationing rows."""

    tokens = []
    for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
        payload = dict(getattr(element, "geometry_payload", {}) or {})
        x_values = payload.get("x_values", [])
        y_values = payload.get("y_values", [])
        tokens.append(
            "|".join(
                [
                    str(getattr(element, "element_id", "") or ""),
                    str(getattr(element, "kind", "") or ""),
                    f"{float(getattr(element, 'station_start', 0.0) or 0.0):.6f}",
                    f"{float(getattr(element, 'station_end', 0.0) or 0.0):.6f}",
                    f"{float(getattr(element, 'length', 0.0) or 0.0):.6f}",
                    str(len(list(x_values or []))),
                    str(len(list(y_values or []))),
                ]
            )
        )
    return ";".join(tokens)


def _active_element_kind_counts(rows) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in list(rows or []):
        kind = str(getattr(row, "active_element_kind", "") or "-")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _station_kinds(rows, *, station_start_offset: float, major_interval: float) -> list[str]:
    kinds = []
    major = max(1.0e-9, float(major_interval))
    for row in list(rows or []):
        reason = str(getattr(row, "source_reason", "") or "")
        display_station = float(getattr(row, "station", 0.0) or 0.0) + float(station_start_offset)
        if reason in {"range_start", "range_end", "extra_station"}:
            kinds.append("key")
        elif _is_multiple(display_station, major):
            kinds.append("major")
        else:
            kinds.append("minor")
    return kinds


def _station_kind_counts(kinds) -> dict[str, int]:
    counts: dict[str, int] = {}
    for kind in list(kinds or []):
        key = str(kind or "-")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _format_station_label(station: float, *, station_start_offset: float, label_format: str) -> str:
    value = float(station) + float(station_start_offset)
    fmt = str(label_format or "STA_DECIMAL").strip().upper()
    if fmt in {"PLUS", "STA_PLUS", "0+000"}:
        sign = "-" if value < 0.0 else ""
        abs_value = abs(value)
        major = int(abs_value // 1000.0)
        minor = abs_value - major * 1000.0
        return f"{sign}{major}+{minor:06.3f}"
    if fmt in {"PLAIN", "DECIMAL"}:
        return f"{value:.3f}"
    return f"STA {value:.3f}"


def _is_multiple(value: float, step: float, tolerance: float = 1.0e-6) -> bool:
    if abs(float(step)) <= 1.0e-12:
        return False
    ratio = float(value) / float(step)
    return abs(ratio - round(ratio)) <= float(tolerance)


def _math_radians(value: float) -> float:
    return math.radians(float(value))


def _math_sin(value: float) -> float:
    return math.sin(float(value))


def _math_cos(value: float) -> float:
    return math.cos(float(value))


def _format_kind_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _stationing_notes(base_notes: str, stationing) -> str:
    parts = [str(base_notes or "").strip()]
    curve_count = int(getattr(stationing, "CurveStationCount", 0) or 0)
    transition_count = int(getattr(stationing, "TransitionStationCount", 0) or 0)
    parts.append(f"curve_stations={curve_count}")
    parts.append(f"transition_stations={transition_count}")
    parts.append(f"source_elements={int(getattr(stationing, 'SourceGeometryElementCount', 0) or 0)}")
    return " | ".join(part for part in parts if part)


def _is_v1_stationing(obj) -> bool:
    if obj is None:
        return False
    if str(getattr(obj, "V1ObjectType", "") or "") == "V1Stationing":
        return True
    proxy = getattr(obj, "Proxy", None)
    if str(getattr(proxy, "Type", "") or "") == "V1Stationing":
        return True
    return str(getattr(obj, "Name", "") or "").startswith("V1Stationing")


def _add_property(obj, type_name: str, name: str, group: str, doc: str) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty(type_name, name, group, doc)
    except Exception:
        pass


def _float_list(values) -> list[float]:
    rows = []
    for value in list(values or []):
        try:
            rows.append(float(value))
        except Exception:
            rows.append(0.0)
    return rows


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "Name", "") or getattr(project, "Label", "") or "corridorroad-v1")
