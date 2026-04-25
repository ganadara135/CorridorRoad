"""v1 profile source editor command."""

from __future__ import annotations

import csv
import os

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None
try:
    import Part
except Exception:  # pragma: no cover - Part is not available in plain Python.
    Part = None

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

from ...misc.resources import icon_path
from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ...objects.project_links import link_project
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_profile import (
    V1ProfileObject,
    ViewProviderV1Profile,
    ensure_v1_profile_properties,
    find_v1_profile,
)
from ..objects.obj_stationing import find_v1_stationing, station_value_rows
from ..models.source.profile_model import ProfileControlPoint, ProfileModel, VerticalCurveRow
from ..models.result.tin_surface import TINSurface
from ..services.evaluation import AlignmentEvaluationService, ProfileEvaluationService, ProfileTinSamplingService
from ..ui.common import run_legacy_command
from .selection_context import selected_alignment_profile_target


PROFILE_PRESET_ROWS = {
    "Starter Road": [
        {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
        {"station": 90.0, "elevation": 15.0, "kind": "pvi"},
        {"station": 180.0, "elevation": 13.5, "kind": "grade_break"},
    ],
    "Rolling Terrain": [
        {"station": 0.0, "elevation": 18.0, "kind": "grade_break"},
        {"station": 60.0, "elevation": 23.5, "kind": "pvi"},
        {"station": 140.0, "elevation": 16.5, "kind": "pvi"},
        {"station": 220.0, "elevation": 21.0, "kind": "grade_break"},
    ],
    "Valley Crossing": [
        {"station": 0.0, "elevation": 30.0, "kind": "grade_break"},
        {"station": 80.0, "elevation": 21.0, "kind": "pvi"},
        {"station": 160.0, "elevation": 20.0, "kind": "pvi"},
        {"station": 260.0, "elevation": 31.5, "kind": "grade_break"},
    ],
}


def profile_control_rows(profile) -> list[dict[str, object]]:
    """Return editable PVI rows from a V1Profile object."""

    if profile is None:
        return []
    ensure_v1_profile_properties(profile)
    ids = list(getattr(profile, "ControlPointIds", []) or [])
    stations = _float_list(getattr(profile, "ControlStations", []) or [])
    elevations = _float_list(getattr(profile, "ControlElevations", []) or [])
    kinds = list(getattr(profile, "ControlKinds", []) or [])
    count = max(len(stations), len(elevations), len(ids), len(kinds))
    rows: list[dict[str, object]] = []
    profile_id = str(getattr(profile, "ProfileId", "") or getattr(profile, "Name", "") or "profile:v1")
    for index in range(count):
        rows.append(
            {
                "control_point_id": (
                    str(ids[index])
                    if index < len(ids) and str(ids[index] or "").strip()
                    else f"{profile_id}:pvi:{index + 1}"
                ),
                "station": float(stations[index]) if index < len(stations) else 0.0,
                "elevation": float(elevations[index]) if index < len(elevations) else 0.0,
                "kind": str(kinds[index] if index < len(kinds) and kinds[index] else "pvi"),
            }
        )
    return rows


def profile_model_from_editor_rows(
    rows: list[dict[str, object]],
    curve_rows: list[dict[str, object]] | None = None,
    *,
    profile_id: str = "profile:show-preview",
    alignment_id: str = "",
    label: str = "Profile Show Preview",
) -> ProfileModel:
    """Build a transient ProfileModel from current editor table rows."""

    normalized = _normalized_control_rows(None, rows)
    normalized_curves = _normalized_vertical_curve_rows(None, list(curve_rows or []), min_rows=0)
    return ProfileModel(
        schema_version=1,
        project_id="corridorroad-v1",
        profile_id=str(profile_id or "profile:show-preview"),
        alignment_id=str(alignment_id or ""),
        label=str(label or "Profile Show Preview"),
        profile_kind="finished_grade",
        source_refs=["profile-editor-current-table"],
        control_rows=[
            ProfileControlPoint(
                control_point_id=str(row.get("control_point_id", "") or f"{profile_id}:pvi:{index + 1}"),
                station=float(row["station"]),
                elevation=float(row["elevation"]),
                kind=str(row.get("kind", "") or "pvi"),
            )
            for index, row in enumerate(normalized)
        ],
        vertical_curve_rows=[
            VerticalCurveRow(
                vertical_curve_id=str(row.get("curve_id", "") or f"{profile_id}:curve:{index + 1}"),
                kind=str(row.get("kind", "") or "parabolic_vertical_curve"),
                station_start=float(row["station_start"]),
                station_end=float(row["station_end"]),
                curve_length=float(row.get("length", 0.0) or 0.0),
                curve_parameter=float(row.get("parameter", 0.0) or 0.0),
            )
            for index, row in enumerate(normalized_curves)
        ],
    )


def build_profile_preview_shape(
    profile_model: ProfileModel,
    alignment,
    *,
    sample_interval: float = 10.0,
) -> tuple[object, int]:
    """Build a framed X-Z profile preview shape for a transient profile model."""

    preview = build_profile_sheet_preview(
        profile_model,
        alignment,
        sample_interval=sample_interval,
    )
    shapes = [
        preview.get("frame_shape"),
        preview.get("grid_shape"),
        preview.get("fg_shape"),
        preview.get("eg_shape"),
    ]
    valid_shapes = [shape for shape in shapes if shape is not None and not shape.isNull()]
    return Part.Compound(valid_shapes) if valid_shapes else Part.Shape(), int(preview.get("fg_point_count", 0) or 0)


def build_profile_sheet_preview(
    profile_model: ProfileModel,
    alignment,
    *,
    document=None,
    sample_interval: float = 10.0,
    surface_obj=None,
) -> dict[str, object]:
    """Build framed profile-sheet geometry in an isolated X-Z drafting plane."""

    if App is None or Part is None:
        raise RuntimeError("FreeCAD Part workbench is required to build a profile preview shape.")
    alignment_model = to_alignment_model(alignment)
    if alignment_model is None:
        raise ValueError("A V1Alignment is required before showing a profile preview.")

    fg_rows = _profile_preview_fg_rows(profile_model, alignment_model, sample_interval)
    if len(fg_rows) < 2:
        raise ValueError("Profile preview needs at least two station/elevation rows.")
    station_values = [float(row[0]) for row in fg_rows]
    eg_rows, eg_status = _profile_preview_eg_rows(
        document,
        alignment_model,
        station_values,
        sample_interval,
        surface_obj=surface_obj,
    )
    all_elevations = [float(row[1]) for row in fg_rows] + [float(row[1]) for row in eg_rows]
    station_min = min(station_values)
    station_max = max(station_values)
    elevation_min = min(all_elevations)
    elevation_max = max(all_elevations)
    elevation_span = max(1.0, elevation_max - elevation_min)
    station_span = max(1.0, station_max - station_min)
    elevation_pad = max(1.0, elevation_span * 0.12)
    elevation_min -= elevation_pad
    elevation_max += elevation_pad

    plot_width = max(240.0, station_span)
    plot_height = 120.0
    origin_x, origin_y, origin_z = _profile_preview_origin(document, plot_width, plot_height)
    x_scale = plot_width / station_span
    z_scale = plot_height / max(1.0, elevation_max - elevation_min)

    def to_sheet_point(station: float, elevation: float):
        return App.Vector(
            origin_x + (float(station) - station_min) * x_scale,
            origin_y,
            origin_z + (float(elevation) - elevation_min) * z_scale,
        )

    fg_points = [to_sheet_point(station, elevation) for station, elevation in fg_rows]
    eg_points = [to_sheet_point(station, elevation) for station, elevation in eg_rows]
    frame_shape = _profile_sheet_frame_shape(origin_x, origin_y, origin_z, plot_width, plot_height)
    grid_shape, station_ticks, elevation_ticks = _profile_sheet_grid_shape(
        station_min,
        station_max,
        elevation_min,
        elevation_max,
        origin_x,
        origin_y,
        origin_z,
        plot_width,
        plot_height,
        x_scale,
        z_scale,
    )
    return {
        "frame_shape": frame_shape,
        "grid_shape": grid_shape,
        "fg_shape": _make_profile_polyline(fg_points),
        "eg_shape": _make_profile_polyline(eg_points),
        "fg_point_count": len(fg_points),
        "eg_point_count": len(eg_points),
        "origin": (origin_x, origin_y, origin_z),
        "plot_width": plot_width,
        "plot_height": plot_height,
        "station_range": (station_min, station_max),
        "elevation_range": (elevation_min, elevation_max),
        "station_ticks": station_ticks,
        "elevation_ticks": elevation_ticks,
        "eg_status": eg_status,
    }


def show_profile_preview_object(
    document,
    profile_model: ProfileModel,
    alignment,
    *,
    sample_interval: float = 10.0,
    surface_obj=None,
):
    """Create or update the reusable framed Profile preview objects."""

    if document is None:
        raise RuntimeError("No active document is available for Profile preview.")
    preview = build_profile_sheet_preview(
        profile_model,
        alignment,
        document=document,
        sample_interval=sample_interval,
        surface_obj=surface_obj,
    )
    frame_obj = _set_preview_part_object(
        document,
        "FinishedGradeFG_ShowPreview_Frame",
        "Profile Show Preview - Frame",
        preview.get("frame_shape"),
        color=(0.82, 0.86, 0.90),
        line_width=2.0,
    )
    grid_obj = _set_preview_part_object(
        document,
        "FinishedGradeFG_ShowPreview_Grid",
        "Profile Show Preview - Grid",
        preview.get("grid_shape"),
        color=(0.38, 0.44, 0.50),
        line_width=1.0,
    )
    fg_obj = _set_preview_part_object(
        document,
        "FinishedGradeFG_ShowPreview",
        "Profile Show Preview - FG",
        preview.get("fg_shape"),
        color=(1.0, 0.48, 0.12),
        line_width=5.0,
    )
    eg_obj = _set_preview_part_object(
        document,
        "FinishedGradeFG_ShowPreview_EG",
        "Profile Show Preview - EG",
        preview.get("eg_shape"),
        color=(0.24, 0.82, 0.42),
        line_width=4.0,
    )
    for obj in (frame_obj, grid_obj, fg_obj, eg_obj):
        _set_preview_string_property(obj, "CRRecordKind", "profile_show_preview")
        _set_preview_string_property(obj, "ProfileId", str(getattr(profile_model, "profile_id", "") or "profile:show-preview"))
        _set_preview_integer_property(obj, "DisplayPointCount", int(preview.get("fg_point_count", 0) or 0))
        _set_preview_integer_property(obj, "ExistingGroundPointCount", int(preview.get("eg_point_count", 0) or 0))
        _set_preview_string_property(obj, "DisplayStatus", "ok")
        _set_preview_string_property(obj, "ExistingGroundStatus", str(preview.get("eg_status", "") or "unavailable"))
    _update_profile_sheet_labels(document, preview)
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        project = find_project(document)
        if project is not None:
            for obj in (frame_obj, grid_obj, fg_obj, eg_obj):
                route_to_v1_tree(project, obj)
    except Exception:
        pass
    return fg_obj


def profile_rows_from_stationing(stationing) -> list[dict[str, object]]:
    """Build starter profile rows from generated v1 station values."""

    if stationing is None:
        return []
    stations = _float_list(getattr(stationing, "StationValues", []) or [])
    if not stations:
        return []
    rows: list[dict[str, object]] = []
    last_index = len(stations) - 1
    for index, station in enumerate(stations):
        rows.append(
            {
                "station": float(station),
                "elevation": None,
                "kind": "grade_break" if index in {0, last_index} else "pvi",
            }
        )
    return rows


def apply_profile_control_rows(profile, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate, sort, and write PVI rows back to a V1Profile object."""

    if profile is None:
        raise ValueError("No V1Profile object is available.")
    ensure_v1_profile_properties(profile)
    normalized = _normalized_control_rows(profile, rows)
    profile.ControlPointIds = [str(row["control_point_id"]) for row in normalized]
    profile.ControlStations = [float(row["station"]) for row in normalized]
    profile.ControlElevations = [float(row["elevation"]) for row in normalized]
    profile.ControlKinds = [str(row["kind"]) for row in normalized]
    try:
        profile.touch()
    except Exception:
        pass
    return normalized


def apply_profile_vertical_curve_rows(profile, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate, sort, and write vertical curve rows back to a V1Profile object."""

    if profile is None:
        raise ValueError("No V1Profile object is available.")
    ensure_v1_profile_properties(profile)
    normalized = _normalized_vertical_curve_rows(profile, rows)
    profile.VerticalCurveIds = [str(row["curve_id"]) for row in normalized]
    profile.VerticalCurveKinds = [str(row["kind"]) for row in normalized]
    profile.VerticalCurveStationStarts = [float(row["station_start"]) for row in normalized]
    profile.VerticalCurveStationEnds = [float(row["station_end"]) for row in normalized]
    profile.VerticalCurveLengths = [float(row["length"]) for row in normalized]
    profile.VerticalCurveParameters = [float(row["parameter"]) for row in normalized]
    try:
        profile.touch()
    except Exception:
        pass
    return normalized


def generate_profile_vertical_curve_rows_from_controls(
    control_rows: list[dict[str, object]],
    *,
    default_length: float = 30.0,
    tangent_clearance_ratio: float = 0.45,
) -> list[dict[str, object]]:
    """Build practical symmetric vertical-curve rows centered on interior PVI rows."""

    controls = _normalized_control_rows(None, control_rows)
    if len(controls) < 3:
        return []
    desired_half_length = max(0.0, float(default_length or 0.0)) * 0.5
    clearance = max(0.05, min(0.49, float(tangent_clearance_ratio or 0.45)))
    rows: list[dict[str, object]] = []
    for index in range(1, len(controls) - 1):
        previous_row = controls[index - 1]
        pvi_row = controls[index]
        next_row = controls[index + 1]
        kind = str(pvi_row.get("kind", "") or "pvi").strip().lower()
        if kind in {"grade_break", "break", "no_curve", "fixed"}:
            continue
        left_gap = float(pvi_row["station"]) - float(previous_row["station"])
        right_gap = float(next_row["station"]) - float(pvi_row["station"])
        if left_gap <= 1.0e-9 or right_gap <= 1.0e-9:
            continue
        half_length = min(desired_half_length, left_gap * clearance, right_gap * clearance)
        if half_length <= 1.0e-9:
            continue
        grade_in = (float(pvi_row["elevation"]) - float(previous_row["elevation"])) / left_gap
        grade_out = (float(next_row["elevation"]) - float(pvi_row["elevation"])) / right_gap
        rows.append(
            {
                "kind": "parabolic_vertical_curve",
                "station_start": float(pvi_row["station"]) - half_length,
                "station_end": float(pvi_row["station"]) + half_length,
                "length": 2.0 * half_length,
                "parameter": grade_out - grade_in,
            }
        )
    return _normalized_vertical_curve_rows(None, rows, min_rows=0)


def profile_preset_names() -> list[str]:
    """Return available v1 Profile preset data names."""

    return list(PROFILE_PRESET_ROWS.keys())


def profile_preset_rows(name: str) -> list[dict[str, object]]:
    """Return a copy of preset PVI/control rows for a named profile shape."""

    key = str(name or "").strip()
    rows = PROFILE_PRESET_ROWS.get(key)
    if rows is None:
        raise ValueError(f"Unknown Profile preset: {key}")
    return [dict(row) for row in rows]


def import_profile_control_rows_from_csv(path: str) -> list[dict[str, object]]:
    """Import v1 Profile PVI/control rows from CSV.

    Accepted columns include station aliases plus elevation/FG aliases. If a
    kind column is absent, rows default to ``pvi``.
    """

    if not path or not os.path.isfile(path):
        raise ValueError("Profile CSV import file was not found.")

    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        lines = list(handle.readlines())
    data_lines = [line for line in lines if not str(line or "").lstrip().startswith("#")]
    sample = "".join(data_lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except Exception:
        class _SimpleDialect(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL

        dialect = _SimpleDialect

    raw_rows = []
    for row in csv.reader(data_lines, dialect):
        values = [str(value).strip() for value in list(row or [])]
        if values and not all(value == "" for value in values):
            raw_rows.append(values)
    if not raw_rows:
        raise ValueError("Profile CSV import file has no usable rows.")

    first = list(raw_rows[0] or [])
    has_header = _optional_float(first[0] if len(first) > 0 else None) is None
    station_idx = 0
    elevation_idx = 1
    kind_idx = -1
    rows = list(raw_rows)
    if has_header:
        header = [_normalize_profile_csv_header(value) for value in first]
        station_idx = _first_matching_header_index(header, {"station", "sta", "chainage", "pk", "kp", "distance", "dist"})
        elevation_idx = _first_matching_header_index(
            header,
            {
                "elevation",
                "elev",
                "fg",
                "finishedgrade",
                "finishedelevation",
                "fgelevation",
                "elevfg",
                "designgrade",
                "designelevation",
                "grade",
                "z",
            },
        )
        kind_idx = _first_matching_header_index(header, {"kind", "type", "controlkind", "pvikind"})
        if station_idx < 0 and len(header) >= 1:
            station_idx = 0
        if elevation_idx < 0 and len(header) >= 2:
            elevation_idx = 1 if station_idx != 1 else (2 if len(header) >= 3 else -1)
        rows = rows[1:]

    if station_idx < 0 or elevation_idx < 0:
        raise ValueError("Profile CSV must include station and elevation columns.")

    by_station: dict[float, dict[str, object]] = {}
    for row in rows:
        if max(station_idx, elevation_idx) >= len(row):
            continue
        station = _optional_float(row[station_idx])
        elevation = _optional_float(row[elevation_idx])
        if station is None or elevation is None:
            continue
        kind = "pvi"
        if kind_idx >= 0 and kind_idx < len(row):
            kind = str(row[kind_idx] or "").strip() or "pvi"
        key = round(float(station), 6)
        by_station[key] = {"station": float(station), "elevation": float(elevation), "kind": kind}

    parsed = [by_station[key] for key in sorted(by_station)]
    if not parsed:
        raise ValueError("Profile CSV import did not yield any valid station/elevation rows.")
    return _normalized_control_rows(None, parsed)


def export_profile_control_rows_to_csv(path: str, rows: list[dict[str, object]]) -> int:
    """Export v1 Profile PVI/control rows to CSV."""

    if not path:
        raise ValueError("Profile CSV export path is empty.")
    normalized = _normalized_control_rows(None, rows)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["station", "elevation", "kind"])
        for row in normalized:
            writer.writerow([
                _format_float(row.get("station", 0.0)),
                _format_float(row.get("elevation", 0.0)),
                str(row.get("kind", "") or "pvi"),
            ])
    return len(normalized)


def create_blank_v1_profile(
    *,
    document=None,
    project=None,
    alignment=None,
    label: str = "Finished Grade Profile",
):
    """Create an empty v1 profile source object for Apply-time authoring."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document is available for v1 profile creation.")

    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"

    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    alignment_obj = alignment or find_v1_alignment(doc)
    try:
        obj = doc.addObject("Part::FeaturePython", "V1Profile")
    except Exception:
        obj = doc.addObject("App::FeaturePython", "V1Profile")
    V1ProfileObject(obj)
    try:
        ViewProviderV1Profile(obj.ViewObject)
    except Exception:
        pass
    obj.Label = label
    obj.ProjectId = str(getattr(prj, "ProjectId", "") or "corridorroad-v1")
    obj.ProfileId = f"profile:{str(getattr(obj, 'Name', '') or 'fg')}"
    obj.AlignmentId = str(getattr(alignment_obj, "AlignmentId", "") or "")
    obj.ProfileKind = "finished_grade"
    link_project(prj, links={"Profile": obj}, links_if_empty={"Alignment": alignment_obj}, adopt_extra=[obj])
    return obj


def build_profile_editor_handoff_context(profile, *, selected_row: dict[str, object] | None = None) -> dict[str, object]:
    """Build Plan/Profile Review context after editing a v1 profile."""

    row = dict(selected_row or {})
    station = _optional_float(row.get("station", None))
    station_label = f"STA {station:.3f}" if station is not None else ""
    return {
        "source": "v1_profile_editor",
        "preferred_station": station,
        "preferred_profile_name": str(getattr(profile, "Name", "") or ""),
        "viewer_context": {
            "source_panel": "v1 Profile Editor",
            "focus_station": station,
            "focus_station_label": station_label,
            "selected_row_label": _selected_row_label(row),
        },
    }


def profile_vertical_curve_rows(profile) -> list[dict[str, object]]:
    """Return table-friendly vertical curve rows from a V1Profile object."""

    if profile is None:
        return []
    ensure_v1_profile_properties(profile)
    ids = list(getattr(profile, "VerticalCurveIds", []) or [])
    kinds = list(getattr(profile, "VerticalCurveKinds", []) or [])
    starts = _float_list(getattr(profile, "VerticalCurveStationStarts", []) or [])
    ends = _float_list(getattr(profile, "VerticalCurveStationEnds", []) or [])
    lengths = _float_list(getattr(profile, "VerticalCurveLengths", []) or [])
    parameters = _float_list(getattr(profile, "VerticalCurveParameters", []) or [])
    count = max(len(ids), len(kinds), len(starts), len(ends), len(lengths), len(parameters))
    rows = []
    profile_id = str(getattr(profile, "ProfileId", "") or getattr(profile, "Name", "") or "profile:v1")
    for index in range(count):
        start = starts[index] if index < len(starts) else 0.0
        end = ends[index] if index < len(ends) else start
        rows.append(
            {
                "curve_id": str(ids[index]) if index < len(ids) and ids[index] else f"{profile_id}:curve:{index + 1}",
                "kind": str(kinds[index]) if index < len(kinds) and kinds[index] else "parabolic_vertical_curve",
                "station_start": float(start),
                "station_end": float(end),
                "length": float(lengths[index]) if index < len(lengths) else max(0.0, float(end) - float(start)),
                "parameter": float(parameters[index]) if index < len(parameters) else 0.0,
            }
        )
    return rows


def profile_station_check_lines(profile, alignment) -> list[str]:
    """Return compact station-link diagnostics for the profile editor."""

    lines = []
    if profile is None:
        lines.append("Profile: not created yet. Apply will create the V1Profile source object.")
    else:
        ensure_v1_profile_properties(profile)
        lines.append(f"Profile: {str(getattr(profile, 'Label', '') or getattr(profile, 'Name', '') or '')}")
        lines.append(f"ProfileId: {str(getattr(profile, 'ProfileId', '') or '')}")
        lines.append(f"Profile alignment id: {str(getattr(profile, 'AlignmentId', '') or '')}")

    alignment_model = to_alignment_model(alignment) if alignment is not None else None
    if alignment_model is None:
        lines.append("Alignment: not available.")
    else:
        lines.append(f"Alignment: {alignment_model.label}")
        lines.append(f"AlignmentId: {alignment_model.alignment_id}")

    rows = profile_control_rows(profile) if profile is not None else []
    stations = [float(row.get("station", 0.0) or 0.0) for row in rows]
    if stations:
        lines.append(f"Profile station range: {_format_float(min(stations))} - {_format_float(max(stations))} m")
        lines.append(f"PVI/control count: {len(stations)}")
    else:
        lines.append("Profile station range: no PVI/control rows.")

    if alignment_model is not None and stations:
        elements = list(getattr(alignment_model, "geometry_sequence", []) or [])
        if elements:
            start = min(float(getattr(row, "station_start", 0.0) or 0.0) for row in elements)
            end = max(float(getattr(row, "station_end", 0.0) or 0.0) for row in elements)
            outside = [station for station in stations if station < start - 1.0e-9 or station > end + 1.0e-9]
            lines.append(f"Alignment station range: {_format_float(start)} - {_format_float(end)} m")
            if outside:
                lines.append(f"Station check: warning - {len(outside)} profile station(s) outside alignment range.")
            else:
                lines.append("Station check: ok - profile stations fit alignment range.")
        else:
            lines.append("Station check: alignment has no geometry rows.")
    return lines


def profile_station_check_rows(
    rows: list[dict[str, object]],
    alignment,
    stationing,
    *,
    station_tolerance: float = 1.0e-6,
) -> list[dict[str, object]]:
    """Return per-profile-station link checks against alignment and stationing."""

    alignment_model = to_alignment_model(alignment) if alignment is not None else None
    alignment_start = None
    alignment_end = None
    if alignment_model is not None:
        elements = list(getattr(alignment_model, "geometry_sequence", []) or [])
        if elements:
            alignment_start = min(float(getattr(row, "station_start", 0.0) or 0.0) for row in elements)
            alignment_end = max(float(getattr(row, "station_end", 0.0) or 0.0) for row in elements)
    stationing_values = [float(value) for value, _label in station_value_rows(stationing)]

    output = []
    for index, row in enumerate(list(rows or []), start=1):
        station = _optional_float(row.get("station", None))
        kind = str(row.get("kind", "") or "pvi")
        if station is None:
            output.append(
                {
                    "station": "",
                    "kind": kind,
                    "in_alignment": "no",
                    "in_stationing": "no",
                    "status": "ERROR",
                    "notes": f"Row {index} station is empty or invalid.",
                }
            )
            continue
        in_alignment = (
            alignment_start is not None
            and alignment_end is not None
            and alignment_start - station_tolerance <= float(station) <= alignment_end + station_tolerance
        )
        in_stationing = any(abs(float(station) - value) <= station_tolerance for value in stationing_values)
        if alignment_start is None or alignment_end is None:
            status = "ERROR"
            notes = "No compiled V1Alignment range is available."
        elif not in_alignment:
            status = "ERROR"
            notes = f"Station is outside alignment range {_format_float(alignment_start)} - {_format_float(alignment_end)}."
        elif not stationing_values:
            status = "WARN"
            notes = "No V1Stationing object is available for station-grid membership check."
        elif not in_stationing:
            status = "WARN"
            notes = "Station is in alignment range but not in generated Stations grid."
        else:
            status = "OK"
            notes = "Station is covered by alignment and generated Stations."
        output.append(
            {
                "station": float(station),
                "kind": kind,
                "in_alignment": "yes" if in_alignment else "no",
                "in_stationing": "yes" if in_stationing else "no",
                "status": status,
                "notes": notes,
            }
        )
    return output


def profile_eg_reference_lines(document, profile, alignment) -> list[str]:
    """Return EG reference status lines for the profile editor."""

    lines = ["EG reference source: TIN-first existing ground profile."]
    if document is None:
        return lines + ["Status: no active document."]
    try:
        from .cmd_review_plan_profile import build_document_plan_profile_preview

        preview = build_document_plan_profile_preview(document)
        profile_output = preview.get("profile_output") if isinstance(preview, dict) else None
        line_rows = list(getattr(profile_output, "line_rows", []) or [])
        eg_rows = [row for row in line_rows if str(getattr(row, "kind", "") or "") == "existing_ground_line"]
        if not eg_rows:
            return lines + ["Status: no EG line is currently attached. Build or select an Existing Ground TIN first."]
        sample_count = sum(len(list(getattr(row, "station_values", []) or [])) for row in eg_rows)
        elevation_count = sum(len(list(getattr(row, "elevation_values", []) or [])) for row in eg_rows)
        lines.append(f"Status: EG line available from Plan/Profile Review context.")
        lines.append(f"EG line rows: {len(eg_rows)}")
        lines.append(f"EG station samples: {sample_count}")
        lines.append(f"EG elevation samples: {elevation_count}")
        return lines
    except Exception as exc:
        return lines + [f"Status: EG reference check unavailable - {exc}"]


def profile_eg_sample_rows(
    document,
    alignment,
    profile_rows: list[dict[str, object]],
    *,
    interval: float = 20.0,
    surface_obj=None,
) -> tuple[list[dict[str, object]], str]:
    """Sample EG rows for the current profile station range from a selected/document TIN."""

    alignment_model = to_alignment_model(alignment) if alignment is not None else None
    if alignment_model is None:
        return [], "no_alignment"
    stations = [_optional_float(row.get("station", None)) for row in list(profile_rows or [])]
    stations = [float(station) for station in stations if station is not None]
    if len(stations) < 2:
        return [], "not_enough_profile_stations"
    surface = _tin_surface_from_candidate(surface_obj) if surface_obj is not None else _resolve_profile_preview_tin_surface(document)
    if not isinstance(surface, TINSurface):
        return [], "no_tin"
    station_min = min(stations)
    station_max = max(stations)
    try:
        result = ProfileTinSamplingService().sample_alignment(
            alignment=alignment_model,
            surface=surface,
            interval=max(1.0, float(interval or 20.0)),
            extra_stations=stations,
        )
    except Exception as exc:
        return [], f"eg_error: {exc}"
    rows = []
    for row in list(getattr(result, "rows", []) or []):
        station = float(getattr(row, "station", 0.0) or 0.0)
        if station < station_min - 1.0e-9 or station > station_max + 1.0e-9:
            continue
        rows.append(
            {
                "station": station,
                "x": float(getattr(row, "x", 0.0) or 0.0),
                "y": float(getattr(row, "y", 0.0) or 0.0),
                "elevation": getattr(row, "elevation", None),
                "status": str(getattr(row, "status", "") or ""),
                "face_id": str(getattr(row, "face_id", "") or ""),
                "notes": str(getattr(row, "notes", "") or ""),
            }
        )
    return rows, str(getattr(result, "status", "") or "unknown")


def _make_profile_table_compact(table, column_widths: list[int]) -> None:
    """Let Profile task-panel tables shrink and use horizontal scrolling."""

    try:
        table.setMinimumWidth(0)
        table.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setWordWrap(False)
    except Exception:
        pass
    try:
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(36)
        header.setDefaultSectionSize(76)
        resize_mode = getattr(QtWidgets.QHeaderView, "Interactive", None)
        for col, width in enumerate(list(column_widths or [])):
            if resize_mode is not None and hasattr(header, "setSectionResizeMode"):
                header.setSectionResizeMode(col, resize_mode)
            elif resize_mode is not None and hasattr(header, "setResizeMode"):
                header.setResizeMode(col, resize_mode)
            table.setColumnWidth(col, int(width))
    except Exception:
        pass
    try:
        table.verticalHeader().setDefaultSectionSize(30)
        table.verticalHeader().setMinimumSectionSize(24)
    except Exception:
        pass


class V1ProfileEditorTaskPanel:
    """Tabbed editor for v1 profile source rows and references."""

    def __init__(self, *, profile=None, document=None, preferred_alignment=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.profile = profile or find_v1_profile(self.document)
        self.preferred_alignment = preferred_alignment
        self._needs_stationing_notice = False
        self._stationing_loaded_rows = 0
        self.form = self._build_ui()
        if self._needs_stationing_notice:
            self._show_message(
                "Profile",
                "Stations have not been generated yet.\nOpen `Stations`, click Apply, then reopen Profile.",
            )

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._apply(close_after=True)

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Profile Editor")
        try:
            widget.setMinimumWidth(320)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        except Exception:
            pass

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        try:
            layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        except Exception:
            pass

        title = QtWidgets.QLabel("Profile Editor")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self._profile_label = QtWidgets.QLabel(self._profile_summary_text())
        self._profile_label.setStyleSheet("color: #dfe8ff; background: #263142; padding: 6px;")
        layout.addWidget(self._profile_label)

        hint = QtWidgets.QLabel(
            "Edit station/elevation PVI rows. Apply creates or updates the V1Profile source object."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        data_row = QtWidgets.QHBoxLayout()
        data_row.addWidget(QtWidgets.QLabel("Profile data:"))
        preset_button = QtWidgets.QPushButton("Preset Data")
        preset_button.clicked.connect(self._apply_preset_data)
        data_row.addWidget(preset_button)
        import_button = QtWidgets.QPushButton("Import CSV")
        import_button.clicked.connect(self._import_profile_csv)
        data_row.addWidget(import_button)
        export_button = QtWidgets.QPushButton("Export CSV")
        export_button.clicked.connect(self._export_profile_csv)
        data_row.addWidget(export_button)
        data_row.addStretch(1)
        layout.addLayout(data_row)

        self._tabs = QtWidgets.QTabWidget()
        try:
            self._tabs.setMinimumWidth(0)
        except Exception:
            pass
        self._tabs.addTab(self._build_fg_profile_tab(), "FG Profile")
        self._tabs.addTab(self._build_vertical_curves_tab(), "Vertical Curves")
        self._tabs.addTab(self._build_eg_reference_tab(), "EG Reference")
        self._tabs.addTab(self._build_station_check_tab(), "Station Check")
        layout.addWidget(self._tabs, 1)

        self._refresh_reference_tabs()

        button_grid = QtWidgets.QGridLayout()
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(6)
        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(lambda: self._apply(close_after=False))
        button_grid.addWidget(apply_button, 0, 0)
        show_button = QtWidgets.QPushButton("Show")
        show_button.clicked.connect(self._show_current_profile)
        button_grid.addWidget(show_button, 0, 1)
        open_review_button = QtWidgets.QPushButton("Review Plan/Profile")
        open_review_button.clicked.connect(self._open_review)
        button_grid.addWidget(open_review_button, 1, 0, 1, 2)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_grid.addWidget(close_button, 0, 2)
        button_grid.setColumnStretch(3, 1)
        layout.addLayout(button_grid)

        return widget

    def _build_fg_profile_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        note = QtWidgets.QLabel("Finished-grade PVI/control rows. These rows are the editable v1 profile source.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._table = QtWidgets.QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Station", "Elevation", "Kind"])
        self._table.setMinimumHeight(190)
        _make_profile_table_compact(self._table, [82, 86, 120])
        layout.addWidget(self._table)
        self._load_rows()

        edit_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add PVI")
        add_button.clicked.connect(self._add_row)
        edit_row.addWidget(add_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_rows)
        edit_row.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Station")
        sort_button.clicked.connect(self._sort_table_rows)
        edit_row.addWidget(sort_button)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)
        return tab

    def _build_vertical_curves_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel("Vertical curve rows stored on the V1Profile source object.")
        note.setWordWrap(True)
        layout.addWidget(note)

        settings_row = QtWidgets.QHBoxLayout()
        settings_row.addWidget(QtWidgets.QLabel("Auto curve length:"))
        self._curve_default_length_spin = QtWidgets.QDoubleSpinBox()
        self._curve_default_length_spin.setRange(1.0, 1000000.0)
        self._curve_default_length_spin.setDecimals(3)
        self._curve_default_length_spin.setValue(30.0)
        self._curve_default_length_spin.setSuffix(" m")
        self._curve_default_length_spin.setToolTip("Default full curve length used by Auto from PVI.")
        settings_row.addWidget(self._curve_default_length_spin)
        settings_row.addStretch(1)
        layout.addLayout(settings_row)

        self._curve_table = QtWidgets.QTableWidget(0, 5)
        self._curve_table.setHorizontalHeaderLabels(["Kind", "Start STA", "End STA", "Length", "Parameter"])
        self._curve_table.setMinimumHeight(190)
        _make_profile_table_compact(self._curve_table, [92, 78, 78, 70, 78])
        layout.addWidget(self._curve_table, 1)

        curve_buttons = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Curve")
        add_button.clicked.connect(self._add_curve_row)
        curve_buttons.addWidget(add_button)
        auto_button = QtWidgets.QPushButton("Auto from PVI")
        auto_button.clicked.connect(self._auto_curve_rows_from_pvi)
        curve_buttons.addWidget(auto_button)
        delete_button = QtWidgets.QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_selected_curve_rows)
        curve_buttons.addWidget(delete_button)
        sort_button = QtWidgets.QPushButton("Sort by Start")
        sort_button.clicked.connect(self._sort_curve_rows)
        curve_buttons.addWidget(sort_button)
        curve_buttons.addStretch(1)
        layout.addLayout(curve_buttons)
        return tab

    def _build_eg_reference_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel("Existing ground is treated as a TIN-derived reference, not as editable FG source data.")
        note.setWordWrap(True)
        layout.addWidget(note)

        source_row = QtWidgets.QHBoxLayout()
        self._eg_surface_combo = QtWidgets.QComboBox()
        self._eg_surface_combo.setMinimumWidth(120)
        refresh_sources_button = QtWidgets.QPushButton("Refresh Sources")
        refresh_sources_button.clicked.connect(lambda _checked=False: self._refresh_tin_candidates(refresh_eg=False))
        use_selected_button = QtWidgets.QPushButton("Use Selected")
        use_selected_button.clicked.connect(self._use_selected_eg_surface)
        source_row.addWidget(QtWidgets.QLabel("TIN:"))
        source_row.addWidget(self._eg_surface_combo, 1)
        layout.addLayout(source_row)

        source_button_row = QtWidgets.QHBoxLayout()
        source_button_row.addWidget(refresh_sources_button)
        source_button_row.addWidget(use_selected_button)
        source_button_row.addStretch(1)
        layout.addLayout(source_button_row)

        sample_row = QtWidgets.QHBoxLayout()
        self._eg_interval_spin = QtWidgets.QDoubleSpinBox()
        self._eg_interval_spin.setRange(1.0, 1000000.0)
        self._eg_interval_spin.setDecimals(3)
        self._eg_interval_spin.setValue(20.0)
        self._eg_interval_spin.setSuffix(" m")
        refresh_eg_button = QtWidgets.QPushButton("Refresh EG")
        refresh_eg_button.clicked.connect(self._refresh_eg_reference)
        sample_row.addWidget(QtWidgets.QLabel("Interval:"))
        sample_row.addWidget(self._eg_interval_spin)
        sample_row.addWidget(refresh_eg_button)
        sample_row.addStretch(1)
        layout.addLayout(sample_row)

        self._eg_reference_status = QtWidgets.QLabel("")
        self._eg_reference_status.setWordWrap(True)
        layout.addWidget(self._eg_reference_status)

        self._eg_reference_table = QtWidgets.QTableWidget(0, 7)
        self._eg_reference_table.setHorizontalHeaderLabels(["Station", "X", "Y", "EG Elev.", "Status", "Face", "Notes"])
        self._eg_reference_table.setMinimumHeight(190)
        _make_profile_table_compact(self._eg_reference_table, [72, 82, 82, 74, 70, 54, 160])
        try:
            self._eg_reference_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        except Exception:
            pass
        layout.addWidget(self._eg_reference_table, 1)
        self._refresh_tin_candidates(refresh_eg=False)
        return tab

    def _build_station_check_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        note = QtWidgets.QLabel("Checks whether profile station rows are linked to the active v1 alignment station range.")
        note.setWordWrap(True)
        layout.addWidget(note)

        control_row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh Check")
        refresh_button.clicked.connect(self._refresh_station_check)
        control_row.addWidget(refresh_button)
        control_row.addStretch(1)
        layout.addLayout(control_row)

        self._station_check_status = QtWidgets.QLabel("")
        self._station_check_status.setWordWrap(True)
        layout.addWidget(self._station_check_status)

        self._station_check_table = QtWidgets.QTableWidget(0, 6)
        self._station_check_table.setHorizontalHeaderLabels(["Station", "Kind", "In Alignment", "In Stations", "Status", "Notes"])
        self._station_check_table.setMinimumHeight(190)
        _make_profile_table_compact(self._station_check_table, [72, 86, 92, 88, 66, 170])
        try:
            self._station_check_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        except Exception:
            pass
        layout.addWidget(self._station_check_table, 1)
        return tab

    def _load_rows(self) -> None:
        rows = profile_control_rows(self.profile)
        if not rows:
            rows = profile_rows_from_stationing(find_v1_stationing(self.document))
            self._stationing_loaded_rows = len(rows)
        else:
            self._stationing_loaded_rows = 0
        if not rows:
            self._needs_stationing_notice = True
        self._table.setRowCount(0)
        for row in rows:
            self._append_table_row(row)
        if self.profile is None and self._stationing_loaded_rows > 0:
            self._set_status("Station rows are loaded from V1Stationing. Fill elevations, then Apply to create the v1 profile.", ok=True)
        elif self.profile is None:
            self._set_status("No station rows are available. Generate Stations before creating a Profile.", ok=False)

    def _refresh_reference_tabs(self) -> None:
        self._load_vertical_curve_rows()
        if hasattr(self, "_eg_surface_combo"):
            self._refresh_tin_candidates(refresh_eg=False)
        if hasattr(self, "_station_check_table"):
            self._refresh_station_check()

    def _refresh_tin_candidates(self, *, refresh_eg: bool = False) -> None:
        if not hasattr(self, "_eg_surface_combo"):
            return
        current_name = ""
        current = self._current_eg_surface_object()
        if current is not None:
            current_name = str(getattr(current, "Name", "") or "")
        self._eg_surface_candidates = self._tin_candidate_objects()
        self._eg_surface_combo.clear()
        for obj in self._eg_surface_candidates:
            label = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "TIN")
            name = str(getattr(obj, "Name", "") or "")
            self._eg_surface_combo.addItem(f"{label} ({name})")
        if current_name:
            for index, obj in enumerate(self._eg_surface_candidates):
                if str(getattr(obj, "Name", "") or "") == current_name:
                    self._eg_surface_combo.setCurrentIndex(index)
                    break
        if refresh_eg:
            self._refresh_eg_reference()
        else:
            self._set_eg_reference_idle_status()

    def _tin_candidate_objects(self) -> list[object]:
        candidates = []
        project = find_project(self.document)
        if project is not None:
            try:
                terrain = getattr(project, "Terrain", None)
                if terrain is not None:
                    candidates.append(terrain)
            except Exception:
                pass
        if Gui is not None:
            try:
                candidates.extend(list(Gui.Selection.getSelection() or []))
            except Exception:
                pass
        candidates.extend(list(getattr(self.document, "Objects", []) or []))
        result = []
        seen = set()
        for obj in candidates:
            name = str(getattr(obj, "Name", "") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            if _looks_like_tin_candidate(obj):
                result.append(obj)
        return result

    def _set_eg_reference_idle_status(self) -> None:
        if not hasattr(self, "_eg_reference_status"):
            return
        candidate = self._current_eg_surface_object()
        candidate_label = str(getattr(candidate, "Label", "") or getattr(candidate, "Name", "") or "(none)")
        count = len(list(getattr(self, "_eg_surface_candidates", []) or []))
        self._eg_reference_status.setText(
            f"TIN sources: {count} | Selected: {candidate_label} | Click Refresh EG to sample existing ground."
        )

    def _current_eg_surface_object(self):
        candidates = list(getattr(self, "_eg_surface_candidates", []) or [])
        if not candidates or not hasattr(self, "_eg_surface_combo"):
            return None
        index = int(self._eg_surface_combo.currentIndex())
        if index < 0 or index >= len(candidates):
            return None
        return candidates[index]

    def _use_selected_eg_surface(self) -> None:
        selected = []
        if Gui is not None:
            try:
                selected = list(Gui.Selection.getSelection() or [])
            except Exception:
                selected = []
        selected_surface = None
        for obj in selected:
            if _tin_surface_from_candidate(obj) is not None:
                selected_surface = obj
                break
        if selected_surface is None:
            self._set_status("No selected TIN-capable Mesh/Shape object was found.", ok=False)
            return
        self._refresh_tin_candidates(refresh_eg=False)
        target_name = str(getattr(selected_surface, "Name", "") or "")
        for index, obj in enumerate(list(getattr(self, "_eg_surface_candidates", []) or [])):
            if str(getattr(obj, "Name", "") or "") == target_name:
                self._eg_surface_combo.setCurrentIndex(index)
                break
        self._refresh_eg_reference()

    def _refresh_eg_reference(self) -> None:
        if not hasattr(self, "_eg_reference_table"):
            return
        alignment = self.preferred_alignment or find_v1_alignment(self.document)
        interval = float(self._eg_interval_spin.value()) if hasattr(self, "_eg_interval_spin") else 20.0
        rows, status = profile_eg_sample_rows(
            self.document,
            alignment,
            self._profile_rows_for_reference(),
            interval=interval,
            surface_obj=self._current_eg_surface_object(),
        )
        self._eg_reference_table.setRowCount(0)
        for row in rows:
            row_index = self._eg_reference_table.rowCount()
            self._eg_reference_table.insertRow(row_index)
            values = [
                _format_float(row.get("station", 0.0)),
                _format_float(row.get("x", 0.0)),
                _format_float(row.get("y", 0.0)),
                _format_optional_float(row.get("elevation", None)),
                str(row.get("status", "") or ""),
                str(row.get("face_id", "") or ""),
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._eg_reference_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
        candidate = self._current_eg_surface_object()
        candidate_label = str(getattr(candidate, "Label", "") or getattr(candidate, "Name", "") or "(none)")
        if hasattr(self, "_eg_reference_status"):
            self._eg_reference_status.setText(
                f"TIN: {candidate_label} | Status: {status} | EG rows: {len(rows)} | Interval: {_format_float(interval)} m"
            )

    def _refresh_station_check(self) -> None:
        if not hasattr(self, "_station_check_table"):
            return
        alignment = self.preferred_alignment or find_v1_alignment(self.document)
        stationing = find_v1_stationing(self.document)
        rows = profile_station_check_rows(
            self._profile_rows_for_reference(),
            alignment,
            stationing,
        )
        self._station_check_table.setRowCount(0)
        counts = {"OK": 0, "WARN": 0, "ERROR": 0}
        for row in rows:
            status = str(row.get("status", "") or "")
            counts[status] = counts.get(status, 0) + 1
            row_index = self._station_check_table.rowCount()
            self._station_check_table.insertRow(row_index)
            values = [
                _format_optional_float(row.get("station", None)),
                str(row.get("kind", "") or ""),
                str(row.get("in_alignment", "") or ""),
                str(row.get("in_stationing", "") or ""),
                status,
                str(row.get("notes", "") or ""),
            ]
            for col, value in enumerate(values):
                self._station_check_table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))
        if hasattr(self, "_station_check_status"):
            self._station_check_status.setText(
                f"Rows: {len(rows)} | OK: {counts.get('OK', 0)} | WARN: {counts.get('WARN', 0)} | ERROR: {counts.get('ERROR', 0)}"
            )

    def _profile_rows_for_reference(self) -> list[dict[str, object]]:
        rows = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            kind_text = self._item_text(row_index, 2) or "pvi"
            station = _optional_float(station_text)
            if station is None and not station_text:
                continue
            rows.append({"station": station, "kind": kind_text.strip() or "pvi"})
        return rows

    def _load_vertical_curve_rows(self) -> None:
        if not hasattr(self, "_curve_table"):
            return
        self._curve_table.setRowCount(0)
        for row in profile_vertical_curve_rows(self.profile):
            self._append_vertical_curve_row(row)

    def _append_vertical_curve_row(self, row: dict[str, object]) -> None:
        row_index = self._curve_table.rowCount()
        self._curve_table.insertRow(row_index)
        kind_combo = QtWidgets.QComboBox()
        kind_combo.addItems(["Parabolic", "Crest", "Sag"])
        kind_combo.setCurrentText(_curve_kind_label(row.get("kind", "") or "parabolic_vertical_curve"))
        kind_combo.currentTextChanged.connect(lambda text, combo=kind_combo: self._on_curve_kind_changed(combo, text))
        self._curve_table.setCellWidget(row_index, 0, kind_combo)
        values = [
            _format_optional_float(row.get("station_start", None)),
            _format_optional_float(row.get("station_end", None)),
            _format_optional_float(row.get("length", None)),
            _format_float(row.get("parameter", 0.0)),
        ]
        for offset, value in enumerate(values, start=1):
            item = QtWidgets.QTableWidgetItem(value)
            self._curve_table.setItem(row_index, offset, item)

    def _on_curve_kind_changed(self, combo, text: str) -> None:
        label = str(text or "").strip()
        if label in {"Crest", "Sag"}:
            self._show_message("Profile", f"{label} vertical curve type is in progress.\nKind will be set back to Parabolic.")
            try:
                combo.blockSignals(True)
                combo.setCurrentText("Parabolic")
            finally:
                combo.blockSignals(False)
            self._set_status(f"{label} curve type is not available yet. Reverted to Parabolic.", ok=False)

    def _append_table_row(self, row: dict[str, object]) -> None:
        row_index = self._table.rowCount()
        self._table.insertRow(row_index)
        values = [
            _format_float(row.get("station", 0.0)),
            _format_optional_float(row.get("elevation", None)),
            str(row.get("kind", "") or "pvi"),
        ]
        for col, value in enumerate(values):
            self._table.setItem(row_index, col, QtWidgets.QTableWidgetItem(value))

    def _replace_table_rows(self, rows: list[dict[str, object]]) -> None:
        normalized = _normalized_control_rows(self.profile, rows)
        self._table.setRowCount(0)
        for row in normalized:
            self._append_table_row(row)

    def _apply_preset_data(self) -> None:
        names = profile_preset_names()
        if not names:
            self._show_message("Profile", "No Profile preset data is available.")
            return
        try:
            name, ok = QtWidgets.QInputDialog.getItem(
                self.form,
                "Profile Preset Data",
                "Preset:",
                names,
                0,
                False,
            )
        except Exception:
            name, ok = names[0], True
        if not ok or not name:
            return
        try:
            rows = profile_preset_rows(str(name))
            self._replace_table_rows(rows)
            self._set_status(f"Loaded Profile preset data: {name}. Apply when ready.", ok=True)
            self._show_message("Profile", f"Preset data loaded: {name}\nRows: {len(rows)}\nClick Apply to update the V1Profile.")
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Preset data was not loaded.\n{exc}")

    def _import_profile_csv(self) -> None:
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self.form,
            "Import Profile CSV",
            "",
            "CSV Files (*.csv *.txt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            rows = import_profile_control_rows_from_csv(path)
            self._replace_table_rows(rows)
            self._set_status(f"Imported {len(rows)} Profile row(s) from CSV. Apply when ready.", ok=True)
            self._show_message(
                "Profile",
                f"Profile CSV imported.\nFile: {os.path.basename(str(path))}\nRows: {len(rows)}\nClick Apply to update the V1Profile.",
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile CSV import failed.\n{exc}")

    def _export_profile_csv(self) -> None:
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            self.form,
            "Export Profile CSV",
            "profile.csv",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        try:
            count = export_profile_control_rows_to_csv(path, self._table_rows(allow_empty=False))
            self._set_status(f"Exported {count} Profile row(s) to CSV.", ok=True)
            self._show_message("Profile", f"Profile CSV exported.\nFile: {os.path.basename(str(path))}\nRows: {count}")
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile CSV export failed.\n{exc}")

    def _add_row(self) -> None:
        rows = self._table_rows(allow_empty=False)
        if rows:
            last = rows[-1]
            station = float(last["station"]) + 20.0
            elevation = float(last["elevation"])
        else:
            station = 0.0
            elevation = 0.0
        self._append_table_row({"station": station, "elevation": elevation, "kind": "pvi"})
        self._set_status("Added a new PVI row. Apply when ready.", ok=True)

    def _delete_selected_rows(self) -> None:
        selected = sorted({item.row() for item in list(self._table.selectedItems() or [])}, reverse=True)
        if not selected and self._table.currentRow() >= 0:
            selected = [self._table.currentRow()]
        for row_index in selected:
            self._table.removeRow(row_index)
        self._set_status(f"Deleted {len(selected)} row(s). Apply when ready.", ok=True)

    def _sort_table_rows(self) -> None:
        try:
            rows = _normalized_control_rows(self.profile, self._table_rows(allow_empty=False), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            return
        self._table.setRowCount(0)
        for row in rows:
            self._append_table_row(row)
        self._set_status("Rows sorted by station. Apply when ready.", ok=True)

    def _add_curve_row(self) -> None:
        self._append_vertical_curve_row(
            {
                "kind": "parabolic_vertical_curve",
                "station_start": None,
                "station_end": None,
                "length": None,
                "parameter": 0.0,
            }
        )
        self._set_status("Added a blank vertical curve row. Enter Start/End/Length, then Apply.", ok=True)

    def _auto_curve_rows_from_pvi(self) -> None:
        try:
            pvi_rows = self._profile_rows_for_auto_curves()
            curve_rows = generate_profile_vertical_curve_rows_from_controls(
                pvi_rows,
                default_length=self._curve_default_length(),
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Vertical curves were not generated from PVI rows.\n{exc}")
            return
        self._curve_table.setRowCount(0)
        for row in curve_rows:
            self._append_vertical_curve_row(row)
        self._set_status(f"Generated {len(curve_rows)} vertical curve row(s) from PVI rows. Apply when ready.", ok=True)
        self._show_message(
            "Profile",
            f"Generated {len(curve_rows)} vertical curve row(s) from PVI rows.\nClick Apply to update the V1Profile.",
        )

    def _profile_rows_for_auto_curves(self) -> list[dict[str, object]]:
        missing_rows = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            elevation_text = self._item_text(row_index, 1)
            if station_text and not elevation_text:
                missing_rows.append(row_index + 1)
        if missing_rows:
            raise ValueError(
                "Auto from PVI requires FG elevation values first. "
                "Enter elevations in the FG Profile tab, or use Preset Data / Import CSV before running Auto from PVI."
            )
        return self._table_rows(allow_empty=False)

    def _curve_default_length(self) -> float:
        try:
            return float(self._curve_default_length_spin.value())
        except Exception:
            return 30.0

    def _delete_selected_curve_rows(self) -> None:
        selected = sorted({item.row() for item in list(self._curve_table.selectedItems() or [])}, reverse=True)
        if not selected and self._curve_table.currentRow() >= 0:
            selected = [self._curve_table.currentRow()]
        for row_index in selected:
            self._curve_table.removeRow(row_index)
        self._set_status(f"Deleted {len(selected)} vertical curve row(s). Apply when ready.", ok=True)

    def _sort_curve_rows(self) -> None:
        try:
            rows = _normalized_vertical_curve_rows(self.profile, self._curve_table_rows(allow_empty=True), min_rows=0)
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Vertical curve rows were not sorted.\n{exc}")
            return
        self._curve_table.setRowCount(0)
        for row in rows:
            self._append_vertical_curve_row(row)
        self._set_status("Vertical curve rows sorted by start station. Apply when ready.", ok=True)

    def _apply(self, *, close_after: bool = False) -> bool:
        try:
            input_rows = self._table_rows(allow_empty=False)
            curve_rows = self._curve_table_rows(allow_empty=True)
            _normalized_control_rows(self.profile, input_rows)
            _normalized_vertical_curve_rows(self.profile, curve_rows, min_rows=0)
            if self.profile is None:
                self.profile = create_blank_v1_profile(
                    document=self.document,
                    alignment=self.preferred_alignment or find_v1_alignment(self.document),
                )
            normalized = apply_profile_control_rows(self.profile, input_rows)
            normalized_curves = apply_profile_vertical_curve_rows(self.profile, curve_rows)
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            self._set_status(f"Applied {len(normalized)} PVI row(s) to V1Profile.", ok=True)
            self._profile_label.setText(self._profile_summary_text())
            self._refresh_reference_tabs()
            self._show_apply_complete_message(len(normalized), len(normalized_curves))
            if close_after and Gui is not None:
                Gui.Control.closeDialog()
            return True
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile was not applied.\n{exc}")
            return False

    def _show_current_profile(self) -> None:
        try:
            input_rows = self._table_rows(allow_empty=False)
            curve_rows = self._curve_table_rows(allow_empty=True)
            alignment = self.preferred_alignment or find_v1_alignment(self.document)
            alignment_id = str(getattr(alignment, "AlignmentId", "") or "")
            profile_model = profile_model_from_editor_rows(
                input_rows,
                curve_rows,
                alignment_id=alignment_id,
            )
            preview = show_profile_preview_object(
                self.document,
                profile_model,
                alignment,
                sample_interval=10.0,
                surface_obj=self._current_eg_surface_object() if hasattr(self, "_eg_surface_combo") else None,
            )
            if self.document is not None:
                try:
                    self.document.recompute()
                except Exception:
                    pass
            if Gui is not None:
                _force_profile_preview_visibility(self.document)
                try:
                    Gui.Selection.clearSelection()
                    for name in (
                        "FinishedGradeFG_ShowPreview_Frame",
                        "FinishedGradeFG_ShowPreview_Grid",
                        "FinishedGradeFG_ShowPreview",
                        "FinishedGradeFG_ShowPreview_EG",
                    ):
                        obj = self.document.getObject(name) if self.document is not None else None
                        if obj is not None:
                            Gui.Selection.addSelection(obj)
                    if hasattr(Gui, "updateGui"):
                        Gui.updateGui()
                except Exception:
                    pass
                try:
                    view = Gui.ActiveDocument.ActiveView
                    if hasattr(view, "viewFront"):
                        view.viewFront()
                    else:
                        Gui.SendMsgToActiveView("ViewFront")
                except Exception:
                    try:
                        Gui.SendMsgToActiveView("ViewFront")
                    except Exception:
                        pass
                try:
                    if hasattr(Gui, "updateGui"):
                        Gui.updateGui()
                    view = Gui.ActiveDocument.ActiveView
                    if hasattr(view, "fitSelection"):
                        view.fitSelection()
                    else:
                        Gui.SendMsgToActiveView("ViewSelection")
                except Exception:
                    try:
                        Gui.SendMsgToActiveView("ViewSelection")
                    except Exception:
                        try:
                            Gui.SendMsgToActiveView("ViewFit")
                        except Exception:
                            pass
                try:
                    if hasattr(Gui, "updateGui"):
                        Gui.updateGui()
                except Exception:
                    pass
            self._set_status(
                f"Profile preview shown in 3D View ({int(getattr(preview, 'DisplayPointCount', 0) or 0)} points).",
                ok=True,
            )
        except Exception as exc:
            self._set_status(str(exc), ok=False)
            self._show_message("Profile", f"Profile preview was not shown.\n{exc}")

    def _show_apply_complete_message(self, row_count: int, curve_count: int) -> None:
        try:
            QtWidgets.QMessageBox.information(
                self.form,
                "Profile",
                f"Profile has been applied successfully.\nPVI rows: {int(row_count)}\nVertical curve rows: {int(curve_count)}",
            )
        except Exception:
            pass

    def _open_review(self) -> None:
        if self.profile is None:
            self._set_status("Apply the profile before opening Plan/Profile Review.", ok=False)
            self._show_message("Profile", "Apply the profile before opening Plan/Profile Review.")
            return
        context = build_profile_editor_handoff_context(
            self.profile,
            selected_row=self._selected_or_first_row(),
        )
        success, message = run_legacy_command(
            "CorridorRoad_V1ReviewPlanProfile",
            gui_module=Gui,
            objects_to_select=[self.profile],
            context_payload=context,
        )
        self._set_status(message, ok=success)

    def _table_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._table.rowCount()):
            station_text = self._item_text(row_index, 0)
            elevation_text = self._item_text(row_index, 1)
            kind_text = self._item_text(row_index, 2) or "pvi"
            if not station_text and not elevation_text and allow_empty:
                continue
            rows.append(
                {
                    "control_point_id": _existing_control_id(self.profile, row_index),
                    "station": _required_float(station_text, f"Row {row_index + 1} station"),
                    "elevation": _required_float(elevation_text, f"Row {row_index + 1} elevation"),
                    "kind": kind_text.strip() or "pvi",
                }
            )
        return rows

    def _table_station_values(self) -> list[float]:
        stations: list[float] = []
        for row_index in range(self._table.rowCount()):
            station = _optional_float(self._item_text(row_index, 0))
            if station is not None:
                stations.append(float(station))
        return stations

    def _curve_table_rows(self, *, allow_empty: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row_index in range(self._curve_table.rowCount()):
            raw_kind_text = self._curve_item_text(row_index, 0)
            start_text = self._curve_item_text(row_index, 1)
            end_text = self._curve_item_text(row_index, 2)
            length_text = self._curve_item_text(row_index, 3)
            parameter_text = self._curve_item_text(row_index, 4)
            if allow_empty and not start_text and not end_text and not length_text:
                continue
            kind_text = _curve_kind_value(raw_kind_text or "Parabolic")
            rows.append(
                {
                    "curve_id": _existing_curve_id(self.profile, row_index),
                    "kind": kind_text,
                    "station_start": _required_float(start_text, f"Curve row {row_index + 1} start station"),
                    "station_end": _required_float(end_text, f"Curve row {row_index + 1} end station"),
                    "length": _optional_float(length_text),
                    "parameter": _optional_float(parameter_text) or 0.0,
                }
            )
        return rows

    def _selected_or_first_row(self) -> dict[str, object]:
        rows = self._table_rows(allow_empty=True)
        if not rows:
            return {}
        row_index = self._table.currentRow()
        if row_index < 0:
            return rows[0]
        if row_index >= len(rows):
            return rows[0]
        return rows[row_index]

    def _item_text(self, row_index: int, col_index: int) -> str:
        item = self._table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _curve_item_text(self, row_index: int, col_index: int) -> str:
        widget = self._curve_table.cellWidget(row_index, col_index)
        if widget is not None and hasattr(widget, "currentText"):
            return str(widget.currentText() or "").strip()
        item = self._curve_table.item(row_index, col_index)
        if item is None:
            return ""
        return str(item.text() or "").strip()

    def _profile_summary_text(self) -> str:
        if self.profile is None:
            return "No V1Profile is available."
        return (
            f"Profile: {str(getattr(self.profile, 'Label', '') or getattr(self.profile, 'Name', '') or '')} | "
            f"ProfileId: {str(getattr(self.profile, 'ProfileId', '') or '')} | "
            f"AlignmentId: {str(getattr(self.profile, 'AlignmentId', '') or '')}"
        )

    def _set_status(self, message: str, *, ok: bool) -> None:
        return

    def _show_message(self, title: str, message: str) -> None:
        try:
            QtWidgets.QMessageBox.information(self.form, title, message)
        except Exception:
            pass


def run_v1_profile_editor_command():
    """Open the v1 profile editor without creating sample data on open."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    preferred_alignment, preferred_profile = selected_alignment_profile_target(Gui, document)
    profile = find_v1_profile(document, preferred_profile=preferred_profile)
    preferred_alignment = find_v1_alignment(document, preferred_alignment=preferred_alignment)
    if Gui is not None and hasattr(Gui, "Control"):
        if profile is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(profile)
            except Exception:
                pass
        Gui.Control.showDialog(
            V1ProfileEditorTaskPanel(
                profile=profile,
                document=document,
                preferred_alignment=preferred_alignment,
            )
        )
    return profile


class CmdV1ProfileEditor:
    """Open the v1 profile source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("profiles.svg"),
            "MenuText": "Profile",
            "ToolTip": "Edit v1 profile PVI source rows and review the result",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_profile_editor_command()


def _normalized_control_rows(
    profile,
    rows: list[dict[str, object]],
    *,
    min_rows: int = 2,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    seen_stations: set[float] = set()
    profile_id = str(getattr(profile, "ProfileId", "") or getattr(profile, "Name", "") or "profile:v1")
    for index, row in enumerate(rows):
        station = _required_float(row.get("station", None), f"Row {index + 1} station")
        elevation = _required_float(row.get("elevation", None), f"Row {index + 1} elevation")
        station_key = round(station, 6)
        if station_key in seen_stations:
            raise ValueError(f"Duplicate station is not allowed: {station:.3f}")
        seen_stations.add(station_key)
        kind = str(row.get("kind", "") or "pvi").strip() or "pvi"
        control_id = str(row.get("control_point_id", "") or "").strip()
        if not control_id:
            control_id = f"{profile_id}:pvi:{index + 1}"
        normalized.append(
            {
                "control_point_id": control_id,
                "station": station,
                "elevation": elevation,
                "kind": kind,
            }
        )
    if len(normalized) < min_rows:
        raise ValueError(f"Profile needs at least {min_rows} PVI/control rows.")
    normalized.sort(key=lambda item: float(item["station"]))
    return normalized


def _normalized_vertical_curve_rows(
    profile,
    rows: list[dict[str, object]],
    *,
    min_rows: int = 0,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    profile_id = str(getattr(profile, "ProfileId", "") or getattr(profile, "Name", "") or "profile:v1")
    for index, row in enumerate(rows):
        start = _required_float(row.get("station_start", None), f"Curve row {index + 1} start station")
        end = _required_float(row.get("station_end", None), f"Curve row {index + 1} end station")
        if end <= start:
            raise ValueError(f"Curve row {index + 1} end station must be greater than start station.")
        length = _optional_float(row.get("length", None))
        if length is None:
            length = max(0.0, end - start)
        if length < 0.0:
            raise ValueError(f"Curve row {index + 1} length must be non-negative.")
        kind = _curve_kind_value(row.get("kind", "") or "Parabolic")
        curve_id = str(row.get("curve_id", "") or "").strip()
        if not curve_id:
            curve_id = f"{profile_id}:curve:{index + 1}"
        normalized.append(
            {
                "curve_id": curve_id,
                "kind": kind,
                "station_start": float(start),
                "station_end": float(end),
                "length": float(length),
                "parameter": _optional_float(row.get("parameter", 0.0)) or 0.0,
            }
        )
    if len(normalized) < min_rows:
        raise ValueError(f"Profile needs at least {min_rows} vertical curve row(s).")
    normalized.sort(key=lambda item: (float(item["station_start"]), float(item["station_end"])))
    previous_end = None
    for index, row in enumerate(normalized):
        start = float(row["station_start"])
        end = float(row["station_end"])
        if previous_end is not None and start < previous_end - 1.0e-9:
            raise ValueError(f"Curve row {index + 1} overlaps the previous vertical curve row.")
        previous_end = end
    return normalized


def _existing_control_id(profile, row_index: int) -> str:
    ids = list(getattr(profile, "ControlPointIds", []) or []) if profile is not None else []
    if row_index < len(ids):
        return str(ids[row_index] or "")
    return ""


def _existing_curve_id(profile, row_index: int) -> str:
    ids = list(getattr(profile, "VerticalCurveIds", []) or []) if profile is not None else []
    if row_index < len(ids):
        return str(ids[row_index] or "")
    return ""


def _float_list(values) -> list[float]:
    result = []
    for value in list(values or []):
        result.append(_optional_float(value) or 0.0)
    return result


def _required_float(value, label: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{label} must be a number.") from None


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def _normalize_profile_csv_header(value: object) -> str:
    raw = str(value or "").strip().lower()
    return "".join(ch for ch in raw if ch.isalnum())


def _first_matching_header_index(header: list[str], aliases: set[str]) -> int:
    for index, key in enumerate(list(header or [])):
        if str(key or "") in aliases:
            return int(index)
    return -1


def _profile_preview_station_values(profile: ProfileModel, interval: float) -> list[float]:
    controls = sorted(list(getattr(profile, "control_rows", []) or []), key=lambda row: float(row.station))
    if len(controls) < 2:
        return []
    start = float(controls[0].station)
    end = float(controls[-1].station)
    step = max(0.1, float(interval or 10.0))
    stations = {round(start, 6), round(end, 6)}
    current = start
    while current < end - 1.0e-9:
        current += step
        stations.add(round(min(current, end), 6))
    for control in controls:
        stations.add(round(float(control.station), 6))
    for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
        stations.add(round(float(curve.station_start), 6))
        stations.add(round(float(curve.station_end), 6))
        stations.add(round(0.5 * (float(curve.station_start) + float(curve.station_end)), 6))
    return [station for station in sorted(stations) if start - 1.0e-9 <= station <= end + 1.0e-9]


def _profile_preview_fg_rows(
    profile: ProfileModel,
    alignment_model,
    interval: float,
) -> list[tuple[float, float]]:
    stations = _profile_preview_station_values(profile, interval)
    alignment_service = AlignmentEvaluationService()
    profile_service = ProfileEvaluationService()
    rows: list[tuple[float, float]] = []
    for station in stations:
        alignment_result = alignment_service.evaluate_station(alignment_model, float(station))
        profile_result = profile_service.evaluate_station(profile, float(station))
        if alignment_result.status != "ok" or profile_result.status != "ok":
            continue
        rows.append((float(station), float(profile_result.elevation)))
    return rows


def _profile_preview_eg_rows(
    document,
    alignment_model,
    station_values: list[float],
    interval: float,
    *,
    surface_obj=None,
) -> tuple[list[tuple[float, float]], str]:
    if document is None:
        return [], "no_document"
    surface = _tin_surface_from_candidate(surface_obj) if surface_obj is not None else _resolve_profile_preview_tin_surface(document)
    if not isinstance(surface, TINSurface):
        return [], "no_tin"
    try:
        station_min = min(float(value) for value in station_values)
        station_max = max(float(value) for value in station_values)
        result = ProfileTinSamplingService().sample_alignment(
            alignment=alignment_model,
            surface=surface,
            interval=max(1.0, float(interval or 10.0)),
            extra_stations=station_values,
        )
        rows = [
            (float(row.station), float(row.elevation))
            for row in list(getattr(result, "rows", []) or [])
            if bool(getattr(row, "found", False))
            and station_min - 1.0e-9 <= float(row.station) <= station_max + 1.0e-9
            and getattr(row, "elevation", None) is not None
        ]
        by_station = {round(station, 6): (station, elevation) for station, elevation in rows}
        return [by_station[key] for key in sorted(by_station)], str(getattr(result, "status", "") or "unknown")
    except Exception as exc:
        return [], f"eg_error: {exc}"


def _resolve_profile_preview_tin_surface(document) -> TINSurface | None:
    """Resolve a terrain TIN for Profile Show without being trapped by alignment/profile shapes."""

    if document is None:
        return None
    try:
        from .cmd_review_tin import _tin_surface_from_object
    except Exception:
        return None

    candidates = []
    project = find_project(document)
    if project is not None:
        try:
            terrain = getattr(project, "Terrain", None)
            if terrain is not None:
                candidates.append(terrain)
        except Exception:
            pass
    if Gui is not None:
        try:
            candidates.extend(list(Gui.Selection.getSelection() or []))
        except Exception:
            pass
    candidates.extend(list(getattr(document, "Objects", []) or []))

    seen = set()
    for obj in candidates:
        if obj is None:
            continue
        name = str(getattr(obj, "Name", "") or "")
        if name in seen:
            continue
        seen.add(name)
        if _skip_profile_preview_tin_candidate(obj):
            continue
        surface = _tin_surface_from_candidate(obj)
        if isinstance(surface, TINSurface):
            return surface
    return None


def _tin_surface_from_candidate(obj) -> TINSurface | None:
    if obj is None or _skip_profile_preview_tin_candidate(obj):
        return None
    try:
        from .cmd_review_tin import _tin_surface_from_object

        surface = _tin_surface_from_object(obj, max_triangles=250000)
    except Exception:
        surface = None
    return surface if isinstance(surface, TINSurface) else None


def _looks_like_tin_candidate(obj) -> bool:
    """Lightweight TIN candidate check used while opening the Profile panel."""

    if obj is None or _skip_profile_preview_tin_candidate(obj):
        return False
    try:
        from ...objects import surface_sampling_core as _ssc

        return bool(_ssc.is_mesh_object(obj) or _ssc.is_shape_object(obj))
    except Exception:
        return False


def _skip_profile_preview_tin_candidate(obj) -> bool:
    name = str(getattr(obj, "Name", "") or "")
    if name.startswith("FinishedGradeFG_ShowPreview"):
        return True
    v1_type = str(getattr(obj, "V1ObjectType", "") or "")
    if v1_type in {"V1Alignment", "V1Profile", "V1Stationing"}:
        return True
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    if record_kind.startswith("profile_show_preview"):
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    if proxy_type in {"V1Alignment", "V1Profile", "V1Stationing"}:
        return True
    return False


def _profile_preview_origin(document, plot_width: float, plot_height: float = 120.0) -> tuple[float, float, float]:
    if document is None:
        return -0.5 * float(plot_width), 0.0, 0.0
    x_min = 0.0
    x_max = 0.0
    y_max = 0.0
    z_max = 0.0
    found = False
    for obj in list(getattr(document, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if name.startswith("FinishedGradeFG_ShowPreview"):
            continue
        try:
            if hasattr(obj, "Shape") and obj.Shape is not None and not obj.Shape.isNull():
                box = obj.Shape.BoundBox
            elif hasattr(obj, "Mesh") and obj.Mesh is not None:
                box = obj.Mesh.BoundBox
            else:
                continue
            if not found:
                x_min = float(box.XMin)
                x_max = float(box.XMax)
                y_max = float(box.YMax)
                z_max = float(box.ZMax)
                found = True
                continue
            x_min = min(x_min, float(box.XMin))
            x_max = max(x_max, float(box.XMax))
            y_max = max(y_max, float(box.YMax))
            z_max = max(z_max, float(box.ZMax))
        except Exception:
            continue
    if not found:
        return -0.5 * float(plot_width), 0.0, 0.0
    center_x = 0.5 * (float(x_min) + float(x_max))
    origin_x = center_x - 0.5 * float(plot_width)
    origin_y = float(y_max) + max(40.0, float(plot_width) * 0.10)
    origin_z = float(z_max) + max(40.0, float(plot_height) * 0.35)
    return origin_x, origin_y, origin_z


def _profile_sheet_frame_shape(
    origin_x: float,
    origin_y: float,
    origin_z: float,
    width: float,
    height: float,
):
    p0 = App.Vector(origin_x, origin_y, origin_z)
    p1 = App.Vector(origin_x + width, origin_y, origin_z)
    p2 = App.Vector(origin_x + width, origin_y, origin_z + height)
    p3 = App.Vector(origin_x, origin_y, origin_z + height)
    return _make_profile_edges([(p0, p1), (p1, p2), (p2, p3), (p3, p0)])


def _profile_sheet_grid_shape(
    station_min: float,
    station_max: float,
    elevation_min: float,
    elevation_max: float,
    origin_x: float,
    origin_y: float,
    origin_z: float,
    width: float,
    height: float,
    x_scale: float,
    z_scale: float,
):
    station_ticks = _linear_tick_values(station_min, station_max, 6)
    elevation_ticks = _linear_tick_values(elevation_min, elevation_max, 6)
    edges = []
    for station in station_ticks:
        x = origin_x + (float(station) - station_min) * x_scale
        edges.append((App.Vector(x, origin_y, origin_z - 4.0), App.Vector(x, origin_y, origin_z + height)))
    for elevation in elevation_ticks:
        z = origin_z + (float(elevation) - elevation_min) * z_scale
        edges.append((App.Vector(origin_x - 4.0, origin_y, z), App.Vector(origin_x + width, origin_y, z)))
    station_rows = [
        {
            "value": float(station),
            "label": f"{float(station):.0f}",
            "position": (origin_x + (float(station) - station_min) * x_scale, origin_y, origin_z - 16.0),
        }
        for station in station_ticks
    ]
    elevation_rows = [
        {
            "value": float(elevation),
            "label": f"{float(elevation):.1f}",
            "position": (origin_x - 34.0, origin_y, origin_z + (float(elevation) - elevation_min) * z_scale),
        }
        for elevation in elevation_ticks
    ]
    return _make_profile_edges(edges), station_rows, elevation_rows


def _linear_tick_values(start: float, end: float, count: int) -> list[float]:
    if count <= 1 or abs(float(end) - float(start)) <= 1.0e-9:
        return [float(start)]
    step = (float(end) - float(start)) / float(count - 1)
    return [float(start) + step * index for index in range(count)]


def _make_profile_polyline(points):
    pts = list(points or [])
    if Part is None:
        return None
    if len(pts) < 2:
        return Part.Shape()
    try:
        return Part.makePolygon(pts)
    except Exception:
        return _make_profile_edges(list(zip(pts, pts[1:])))


def _make_profile_edges(edges):
    if Part is None:
        return None
    edge_shapes = []
    for start, end in list(edges or []):
        try:
            if (end - start).Length > 1.0e-9:
                edge_shapes.append(Part.makeLine(start, end))
        except Exception:
            continue
    return Part.Compound(edge_shapes) if edge_shapes else Part.Shape()


def _set_preview_part_object(
    document,
    name: str,
    label: str,
    shape,
    *,
    color: tuple[float, float, float],
    line_width: float,
):
    obj = document.getObject(name)
    if obj is None:
        obj = document.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape if shape is not None else Part.Shape()
    _style_profile_preview_object(obj, color=color, line_width=line_width)
    return obj


def _style_profile_preview_object(
    obj,
    *,
    color: tuple[float, float, float],
    line_width: float,
) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        vobj.Visibility = True
        vobj.DisplayMode = "Wireframe"
        vobj.ShapeColor = color
        vobj.LineColor = color
        vobj.PointColor = color
        vobj.LineWidth = float(line_width)
        vobj.PointSize = max(4.0, float(line_width) + 2.0)
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = 0
    except Exception:
        pass


def _force_profile_preview_visibility(document) -> None:
    if document is None:
        return
    styles = {
        "FinishedGradeFG_ShowPreview_Frame": ((0.82, 0.86, 0.90), 3.0),
        "FinishedGradeFG_ShowPreview_Grid": ((0.52, 0.60, 0.68), 2.0),
        "FinishedGradeFG_ShowPreview": ((1.0, 0.48, 0.12), 6.0),
        "FinishedGradeFG_ShowPreview_EG": ((0.24, 0.82, 0.42), 5.0),
    }
    for name, (color, line_width) in styles.items():
        obj = document.getObject(name)
        if obj is not None:
            _style_profile_preview_object(obj, color=color, line_width=line_width)


def _update_profile_sheet_labels(document, preview: dict[str, object]) -> None:
    origin_x, origin_y, origin_z = preview.get("origin", (0.0, 0.0, 0.0))
    plot_width = float(preview.get("plot_width", 0.0) or 0.0)
    plot_height = float(preview.get("plot_height", 0.0) or 0.0)
    for index, row in enumerate(list(preview.get("station_ticks", []) or []), start=1):
        x, y, z = row.get("position", (origin_x, origin_y, origin_z))
        _set_profile_annotation(
            document,
            f"FinishedGradeFG_ShowPreview_StationLabel_{index}",
            str(row.get("label", "") or ""),
            App.Vector(float(x) - 8.0, float(y), float(z)),
        )
    for index, row in enumerate(list(preview.get("elevation_ticks", []) or []), start=1):
        x, y, z = row.get("position", (origin_x, origin_y, origin_z))
        _set_profile_annotation(
            document,
            f"FinishedGradeFG_ShowPreview_ElevationLabel_{index}",
            str(row.get("label", "") or ""),
            App.Vector(float(x), float(y), float(z) - 2.0),
        )
    _set_profile_annotation(
        document,
        "FinishedGradeFG_ShowPreview_Title",
        "Profile Show Preview",
        App.Vector(origin_x, origin_y, origin_z + plot_height + 14.0),
    )
    _set_profile_annotation(
        document,
        "FinishedGradeFG_ShowPreview_XAxisLabel",
        "Distance / Station",
        App.Vector(origin_x + plot_width * 0.42, origin_y, origin_z - 32.0),
    )
    _set_profile_annotation(
        document,
        "FinishedGradeFG_ShowPreview_YAxisLabel",
        "Elevation",
        App.Vector(origin_x - 42.0, origin_y, origin_z + plot_height + 4.0),
    )
    eg_status = str(preview.get("eg_status", "") or "no_tin")
    legend = "FG: orange"
    legend += " | EG: green" if int(preview.get("eg_point_count", 0) or 0) >= 2 else f" | EG: unavailable ({eg_status})"
    _set_profile_annotation(
        document,
        "FinishedGradeFG_ShowPreview_Legend",
        legend,
        App.Vector(origin_x + plot_width * 0.55, origin_y, origin_z + plot_height + 14.0),
    )


def _set_profile_annotation(document, name: str, text: str, position) -> None:
    obj = document.getObject(name)
    if obj is None:
        obj = document.addObject("App::Annotation", name)
    obj.Label = name.replace("FinishedGradeFG_ShowPreview_", "Profile ")
    obj.LabelText = str(text or "")
    obj.Position = position
    _set_preview_string_property(obj, "CRRecordKind", "profile_show_preview_label")
    try:
        obj.ViewObject.Visibility = True
        obj.ViewObject.TextColor = (0.9, 0.94, 1.0)
        obj.ViewObject.FontSize = 10.0
    except Exception:
        pass


def _set_preview_string_property(obj, name: str, value: str) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
    setattr(obj, name, str(value or ""))


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
    setattr(obj, name, int(value or 0))


def _curve_kind_label(kind: object) -> str:
    key = str(kind or "").strip().lower()
    if key in {"crest", "crest_curve"}:
        return "Crest"
    if key in {"sag", "sag_curve"}:
        return "Sag"
    return "Parabolic"


def _curve_kind_value(label: object) -> str:
    key = str(label or "").strip().lower()
    if key == "crest":
        return "crest_curve"
    if key == "sag":
        return "sag_curve"
    return "parabolic_vertical_curve"


def _format_float(value) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _format_optional_float(value) -> str:
    numeric = _optional_float(value)
    if numeric is None:
        return ""
    return _format_float(numeric)


def _selected_row_label(row: dict[str, object]) -> str:
    if not row:
        return ""
    station = _optional_float(row.get("station", None))
    elevation = _optional_float(row.get("elevation", None))
    kind = str(row.get("kind", "") or "pvi")
    parts = []
    if station is not None:
        parts.append(f"STA {station:.3f}")
    if elevation is not None:
        parts.append(f"FG {elevation:.3f}")
    parts.append(kind)
    return " | ".join(parts)


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditProfile", CmdV1ProfileEditor())
