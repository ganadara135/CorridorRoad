"""v1 profile source editor command."""

from __future__ import annotations

import csv
import math
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

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets  # noqa: F401 - runtime-injected UI collaborator

from ..ui.editors.profile_editor import (  # noqa: F401 - runtime-injected UI collaborator
    _ProfileCurvePreviewWidget,
    V1ProfileEditorTaskPanel,
    configure_profile_editor_task_panel_runtime,
)
from ..services.editing import (
    prepare_profile_control_rows,
    prepare_profile_vertical_curve_rows,
)

from ...misc.resources import icon_path
from ...objects.obj_project import (  # noqa: F401 - runtime-injected UI collaborator
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
    get_design_standard,
)
from ...objects import design_standards as _ds
from ...objects.project_links import link_project
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_profile import (
    V1ProfileObject,
    ViewProviderV1Profile,
    ensure_v1_profile_properties,
    find_v1_profile,
)
from ..objects.obj_stationing import find_v1_stationing, station_value_rows  # noqa: F401 - runtime-injected UI collaborator
from ..models.source.profile_model import ProfileControlPoint, ProfileModel, VerticalCurveRow
from ..models.result.tin_surface import TINSurface
from ..services.evaluation import (  # noqa: F401 - runtime-injected UI collaborator
    AlignmentEvaluationService,
    ProfileCurvePreviewRequest,
    ProfileCurvePreviewService,
    ProfileEvaluationService,
    ProfileTinSamplingService,
)
from ..ui.common import run_legacy_command  # noqa: F401 - runtime-injected UI collaborator
from ..ui.common.styles import apply_clickable_tab_style  # noqa: F401 - runtime-injected UI collaborator
from .selection_context import selected_alignment_profile_target
from freecad.Corridor_Road.v1.objects.project_document_adapter import route_object_to_project_tree


PROFILE_PRESET_ROWS = {
    "Vertical Curve Showcase": [
        {"station": 0.0, "elevation": 70.0, "kind": "grade_break"},
        {"station": 80.0, "elevation": 118.0, "kind": "pvi"},
        {"station": 160.0, "elevation": 48.0, "kind": "pvi"},
        {"station": 240.0, "elevation": 108.0, "kind": "pvi"},
        {"station": 320.0, "elevation": 72.0, "kind": "grade_break"},
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

PROFILE_PRESET_VERTICAL_CURVE_ROWS = {
    "Vertical Curve Showcase": [
        {
            "kind": "parabolic_vertical_curve",
            "pvi_station": 80.0,
            "length": 48.0,
            "parameter": 0.0,
        },
        {
            "kind": "parabolic_vertical_curve",
            "pvi_station": 160.0,
            "length": 48.0,
            "parameter": 0.0,
        },
        {
            "kind": "parabolic_vertical_curve",
            "pvi_station": 240.0,
            "length": 48.0,
            "parameter": 0.0,
        },
    ],
}

PROFILE_VERTICAL_CURVE_K_VALUE_DEFAULTS = {
    40: {"crest": 7.0, "sag": 8.0},
    50: {"crest": 12.0, "sag": 13.0},
    60: {"crest": 18.0, "sag": 18.0},
    70: {"crest": 28.0, "sag": 24.0},
    80: {"crest": 44.0, "sag": 32.0},
    90: {"crest": 60.0, "sag": 40.0},
    100: {"crest": 84.0, "sag": 52.0},
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
        "fg_shape": _make_profile_polyline(fg_points, stroke_width=3.0),
        "eg_shape": _make_profile_polyline(eg_points, stroke_width=2.8),
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
        project = find_project(document)
        if project is not None:
            for obj in (frame_obj, grid_obj, fg_obj, eg_obj):
                route_object_to_project_tree(project, obj)
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


def auto_interpolate_profile_elevation_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Fill blank profile elevations by linear interpolation between entered controls."""

    parsed: list[dict[str, object]] = []
    seen_stations: set[float] = set()
    for index, row in enumerate(list(rows or [])):
        station = _required_float(row.get("station", None), f"Row {index + 1} station")
        station_key = round(station, 6)
        if station_key in seen_stations:
            raise ValueError(f"Duplicate station is not allowed: {station:.3f}")
        seen_stations.add(station_key)
        parsed.append(
            {
                "control_point_id": str(row.get("control_point_id", "") or ""),
                "station": float(station),
                "elevation": _optional_float(row.get("elevation", None)),
                "kind": str(row.get("kind", "") or "pvi").strip() or "pvi",
            }
        )
    if len(parsed) < 2:
        raise ValueError("Auto Interpolate Elevations requires at least two station rows.")

    parsed.sort(key=lambda item: float(item["station"]))
    control_indices = [index for index, row in enumerate(parsed) if row.get("elevation", None) is not None]
    if len(control_indices) < 2:
        raise ValueError("Auto Interpolate Elevations requires at least two entered elevation values.")
    if control_indices[0] != 0 or control_indices[-1] != len(parsed) - 1:
        first_station = float(parsed[0]["station"])
        last_station = float(parsed[-1]["station"])
        raise ValueError(
            "Enter elevation values for the first and last station before using Auto Interpolate Elevations.\n"
            f"First station: {first_station:.3f}\n"
            f"Last station: {last_station:.3f}"
        )

    for left_index, right_index in zip(control_indices, control_indices[1:]):
        left = parsed[left_index]
        right = parsed[right_index]
        left_station = float(left["station"])
        right_station = float(right["station"])
        if right_station <= left_station:
            raise ValueError("Profile stations must increase for auto interpolation.")
        left_elevation = float(left["elevation"])
        right_elevation = float(right["elevation"])
        grade = (right_elevation - left_elevation) / (right_station - left_station)
        for row_index in range(left_index + 1, right_index):
            station = float(parsed[row_index]["station"])
            parsed[row_index]["elevation"] = left_elevation + grade * (station - left_station)

    return parsed


def apply_profile_control_rows(profile, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate, sort, and write PVI rows back to a V1Profile object."""

    if profile is None:
        raise ValueError("No V1Profile object is available.")
    ensure_v1_profile_properties(profile)
    normalized = prepare_profile_control_rows(_normalized_control_rows(profile, rows))
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
    normalized = prepare_profile_vertical_curve_rows(_normalized_vertical_curve_rows(profile, rows))
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
    design_speed_kph: float = 60.0,
    design_standard: str = "KDS",
    min_length: float | None = None,
    max_length: float = 300.0,
    method: str = "k_value",
    return_diagnostics: bool = False,
):
    """Build practical symmetric vertical-curve rows centered on interior PVI rows."""

    controls = _normalized_control_rows(None, control_rows)
    if len(controls) < 3:
        return ([], _vertical_curve_auto_summary([], [])) if return_diagnostics else []
    min_curve_length = max(0.0, float(default_length if min_length is None else min_length) or 0.0)
    max_curve_length = max(min_curve_length, float(max_length or min_curve_length or 0.0))
    use_k_value = str(method or "k_value").strip().lower() in {"k_value", "k-value", "design", "k_value_design"}
    desired_length = max(0.0, float(default_length or min_curve_length or 0.0))
    clearance = max(0.05, min(0.49, float(tangent_clearance_ratio or 0.45)))
    rows: list[dict[str, object]] = []
    diagnostics: list[str] = []
    for index in range(1, len(controls) - 1):
        previous_row = controls[index - 1]
        pvi_row = controls[index]
        next_row = controls[index + 1]
        pvi_station = float(pvi_row["station"])
        kind = str(pvi_row.get("kind", "") or "pvi").strip().lower()
        if kind in {"grade_break", "break", "no_curve", "fixed"}:
            diagnostics.append(f"[PVI STA {pvi_station:.3f}] Skipped: row kind is {kind}.")
            continue
        left_gap = pvi_station - float(previous_row["station"])
        right_gap = float(next_row["station"]) - pvi_station
        if left_gap <= 1.0e-9 or right_gap <= 1.0e-9:
            diagnostics.append(f"[PVI STA {pvi_station:.3f}] Skipped: adjacent station spacing is invalid.")
            continue
        grade_in = (float(pvi_row["elevation"]) - float(previous_row["elevation"])) / left_gap
        grade_out = (float(next_row["elevation"]) - float(pvi_row["elevation"])) / right_gap
        algebraic = grade_out - grade_in
        if abs(algebraic) <= 1.0e-9:
            diagnostics.append(f"[PVI STA {pvi_station:.3f}] Skipped: grade difference below threshold.")
            continue
        curve_type = "crest" if algebraic < 0.0 else "sag"
        if use_k_value:
            k_value = profile_vertical_curve_k_value(float(design_speed_kph or 60.0), curve_type, standard=design_standard)
            required_length = max(min_curve_length, k_value * abs(algebraic * 100.0))
        else:
            k_value = 0.0
            required_length = max(min_curve_length, desired_length)
        spacing_limit = 2.0 * min(left_gap * clearance, right_gap * clearance)
        final_length = min(required_length, max_curve_length, spacing_limit)
        if final_length < min_curve_length and spacing_limit >= min_curve_length:
            final_length = min_curve_length
        if final_length <= 1.0e-9:
            diagnostics.append(f"[PVI STA {pvi_station:.3f}] Skipped: available spacing cannot fit a vertical curve.")
            continue
        clamp_reasons = []
        if final_length < required_length - 1.0e-6:
            if spacing_limit <= required_length + 1.0e-6:
                clamp_reasons.append("adjacent PVI spacing")
            if max_curve_length <= required_length + 1.0e-6:
                clamp_reasons.append("max length")
        if final_length < min_curve_length - 1.0e-6:
            clamp_reasons.append("spacing below min length")
        if clamp_reasons:
            diagnostics.append(
                f"[PVI STA {pvi_station:.3f}] {curve_type.title()} required L={required_length:.3f}m, "
                f"clamped to {final_length:.3f}m by {', '.join(clamp_reasons)}."
            )
        else:
            diagnostics.append(
                f"[PVI STA {pvi_station:.3f}] {curve_type.title()} generated L={final_length:.3f}m"
                + (f" from K={k_value:.3f}." if use_k_value else ".")
            )
        half_length = 0.5 * final_length
        rows.append(
            {
                "kind": "parabolic_vertical_curve",
                "station_start": pvi_station - half_length,
                "station_end": pvi_station + half_length,
                "length": final_length,
                "parameter": algebraic,
            }
        )
    normalized = _normalized_vertical_curve_rows(None, rows, min_rows=0)
    return (normalized, _vertical_curve_auto_summary(normalized, diagnostics)) if return_diagnostics else normalized


def profile_vertical_curve_k_value(design_speed_kph: float, curve_type: str, *, standard: str = "KDS") -> float:
    """Return placeholder required K value for a vertical curve type and design speed."""

    try:
        return float(_ds.vertical_curve_k_value(standard, design_speed_kph, curve_type))
    except Exception:
        speeds = sorted(PROFILE_VERTICAL_CURVE_K_VALUE_DEFAULTS)
        speed = float(design_speed_kph or 60.0)
        nearest = min(speeds, key=lambda value: abs(float(value) - speed))
        kind = "crest" if str(curve_type or "").strip().lower() == "crest" else "sag"
        return float(PROFILE_VERTICAL_CURVE_K_VALUE_DEFAULTS[nearest][kind])


def _vertical_curve_auto_summary(rows: list[dict[str, object]], diagnostics: list[str]) -> dict[str, object]:
    crest = 0
    sag = 0
    clamped = 0
    skipped = 0
    for message in list(diagnostics or []):
        text = str(message)
        if " Crest " in text:
            crest += 1
        if " Sag " in text:
            sag += 1
        if "clamped" in text:
            clamped += 1
        if "Skipped" in text:
            skipped += 1
    return {
        "generated": len(list(rows or [])),
        "crest": crest,
        "sag": sag,
        "clamped": clamped,
        "skipped": skipped,
        "diagnostics": list(diagnostics or []),
    }


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


def profile_preset_rows_for_station_rows(name: str, station_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sample a Profile preset shape onto the current station rows."""

    target_rows = _station_kind_rows(station_rows)
    if not target_rows:
        return profile_preset_rows(name)
    preset_rows = _normalized_control_rows(None, profile_preset_rows(name))
    if len(preset_rows) < 2:
        return profile_preset_rows(name)
    source_start = float(preset_rows[0]["station"])
    source_end = float(preset_rows[-1]["station"])
    target_start = float(target_rows[0]["station"])
    target_end = float(target_rows[-1]["station"])
    source_span = max(source_end - source_start, 1.0e-9)
    target_span = max(target_end - target_start, 1.0e-9)
    last_index = len(target_rows) - 1
    sampled: list[dict[str, object]] = []
    for index, row in enumerate(target_rows):
        station = float(row["station"])
        ratio = (station - target_start) / target_span
        source_station = source_start + source_span * ratio
        kind = str(row.get("kind", "") or "").strip()
        if not kind:
            kind = "grade_break" if index in {0, last_index} else "pvi"
        sampled.append(
            {
                "control_point_id": str(row.get("control_point_id", "") or ""),
                "station": station,
                "elevation": _interpolated_preset_elevation(preset_rows, source_station),
                "kind": kind,
            }
        )
    return sampled


def profile_preset_vertical_curve_rows(name: str) -> list[dict[str, object]]:
    """Return a copy of preset vertical-curve rows for a named profile shape."""

    out = []
    for row in list(PROFILE_PRESET_VERTICAL_CURVE_ROWS.get(str(name or "").strip(), []) or []):
        copy = dict(row)
        pvi_station = _optional_float(copy.get("pvi_station", None))
        length = _optional_float(copy.get("length", None)) or 0.0
        if pvi_station is not None and length > 0.0:
            copy["station_start"] = float(pvi_station) - 0.5 * float(length)
            copy["station_end"] = float(pvi_station) + 0.5 * float(length)
        out.append(copy)
    return out


def profile_preset_vertical_curve_rows_for_station_rows(name: str, station_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Scale preset vertical-curve rows onto the current station range."""

    curve_rows = profile_preset_vertical_curve_rows(name)
    if not curve_rows:
        return []
    target_rows = _station_kind_rows(station_rows)
    if not target_rows:
        return curve_rows
    preset_rows = _normalized_control_rows(None, profile_preset_rows(name))
    if len(preset_rows) < 2:
        return curve_rows
    source_start = float(preset_rows[0]["station"])
    source_end = float(preset_rows[-1]["station"])
    target_start = float(target_rows[0]["station"])
    target_end = float(target_rows[-1]["station"])
    source_span = max(source_end - source_start, 1.0e-9)
    target_span = max(target_end - target_start, 1.0e-9)

    def _scale_station(station: float) -> float:
        ratio = (float(station) - source_start) / source_span
        return target_start + target_span * ratio

    scaled = []
    for row in curve_rows:
        pvi_station = _optional_float(row.get("pvi_station", None))
        length = _optional_float(row.get("length", None))
        if pvi_station is not None and length is not None:
            center = _scale_station(float(pvi_station))
            scaled_length = abs(float(length) * target_span / source_span)
            start = center - 0.5 * scaled_length
            end = center + 0.5 * scaled_length
        else:
            start = _scale_station(float(row.get("station_start", 0.0) or 0.0))
            end = _scale_station(float(row.get("station_end", start) or start))
        scaled.append(
            {
                "kind": str(row.get("kind", "") or "parabolic_vertical_curve"),
                "station_start": start,
                "station_end": end,
                "length": abs(end - start),
                "parameter": float(row.get("parameter", 0.0) or 0.0),
            }
        )
    return _normalized_vertical_curve_rows(None, scaled, min_rows=0)


def _station_kind_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    seen: set[float] = set()
    for index, row in enumerate(list(rows or [])):
        station = _required_float(row.get("station", None), f"Preset target row {index + 1} station")
        key = round(station, 6)
        if key in seen:
            continue
        seen.add(key)
        parsed.append(
            {
                "control_point_id": str(row.get("control_point_id", "") or ""),
                "station": station,
                "kind": str(row.get("kind", "") or ""),
            }
        )
    parsed.sort(key=lambda item: float(item["station"]))
    return parsed


def _interpolated_preset_elevation(preset_rows: list[dict[str, object]], station: float) -> float:
    if not preset_rows:
        return 0.0
    if station <= float(preset_rows[0]["station"]):
        return float(preset_rows[0]["elevation"])
    if station >= float(preset_rows[-1]["station"]):
        return float(preset_rows[-1]["elevation"])
    for left, right in zip(preset_rows[:-1], preset_rows[1:]):
        left_station = float(left["station"])
        right_station = float(right["station"])
        if not (left_station <= station <= right_station):
            continue
        span = max(right_station - left_station, 1.0e-9)
        ratio = (station - left_station) / span
        return float(left["elevation"]) + (float(right["elevation"]) - float(left["elevation"])) * ratio
    return float(preset_rows[-1]["elevation"])


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
        prj.Label = "Parametric Road Project"

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
    station_tolerance: float = 1.0e-3,
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
        lines.append("Status: EG line available from Plan/Profile Review context.")
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
        kind = "parabolic_vertical_curve"
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
        from .cmd_review_tin import _tin_surface_from_object  # noqa: F401 - runtime-injected UI collaborator
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
    for obj in sorted(candidates, key=_profile_tin_candidate_sort_key):
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
        from .cmd_review_tin import _tin_surface_from_object, resolve_document_tin_max_triangles

        surface = _tin_surface_from_object(
            obj,
            max_triangles=resolve_document_tin_max_triangles(surface_obj=obj),
        )
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


def _profile_tin_candidate_sort_key(obj) -> tuple[int, str]:
    try:
        from .cmd_review_tin import _tin_surface_candidate_sort_key

        return _tin_surface_candidate_sort_key(obj)
    except Exception:
        role = str(getattr(obj, "SurfaceRole", "") or "").lower()
        record_kind = str(getattr(obj, "CRRecordKind", "") or "")
        label = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "")
        if role == "edited":
            return (0, label)
        if record_kind == "tin_mesh_preview":
            return (1, label)
        return (2, label)


def _skip_profile_preview_tin_candidate(obj) -> bool:
    name = str(getattr(obj, "Name", "") or "")
    if name.startswith("FinishedGradeFG_ShowPreview"):
        return True
    if name.startswith("ReviewIssue"):
        return True
    v1_type = str(getattr(obj, "V1ObjectType", "") or "")
    if v1_type in {"V1Alignment", "V1Profile", "V1Stationing", "ReviewIssue"}:
        return True
    record_kind = str(getattr(obj, "CRRecordKind", "") or "")
    if record_kind == "v1_review_issue":
        return True
    if record_kind.startswith("profile_show_preview"):
        return True
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
    if proxy_type in {"V1Alignment", "V1Profile", "V1Stationing", "ReviewIssue"}:
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
    return _make_profile_edges([(p0, p1), (p1, p2), (p2, p3), (p3, p0)], stroke_width=2.0)


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
    return _make_profile_edges(edges, stroke_width=1.2), station_rows, elevation_rows


def _linear_tick_values(start: float, end: float, count: int) -> list[float]:
    if count <= 1 or abs(float(end) - float(start)) <= 1.0e-9:
        return [float(start)]
    step = (float(end) - float(start)) / float(count - 1)
    return [float(start) + step * index for index in range(count)]


def _make_profile_polyline(points, *, stroke_width: float = 0.0):
    pts = list(points or [])
    if Part is None:
        return None
    if len(pts) < 2:
        return Part.Shape()
    spline_shape = _make_profile_spline(pts)
    if float(stroke_width or 0.0) > 0.0:
        return _make_profile_stroked_curve(spline_shape, pts, stroke_width=stroke_width)
    if spline_shape is not None:
        return spline_shape
    try:
        return Part.makePolygon(pts)
    except Exception:
        return _make_profile_edges(list(zip(pts, pts[1:])))


def _make_profile_spline(points):
    pts = _profile_unique_points(points)
    if Part is None or len(pts) < 2:
        return None
    if len(pts) == 2:
        try:
            return Part.makeLine(pts[0], pts[1])
        except Exception:
            return None
    try:
        curve = Part.BSplineCurve()
        curve.interpolate(pts)
        return curve.toShape()
    except Exception:
        return None


def _make_profile_stroked_curve(spline_shape, fallback_points, *, stroke_width: float):
    points = _profile_curve_sample_points(spline_shape, fallback_points)
    return _make_profile_edges(list(zip(points, points[1:])), stroke_width=stroke_width)


def _profile_curve_sample_points(shape, fallback_points, *, sample_count: int = 96):
    fallback = _profile_unique_points(fallback_points)
    edge = None
    try:
        edges = list(getattr(shape, "Edges", []) or [])
        edge = edges[0] if edges else None
    except Exception:
        edge = None
    if edge is None:
        return fallback
    try:
        points = list(edge.discretize(Number=max(2, int(sample_count))) or [])
        return _profile_unique_points(points) or fallback
    except Exception:
        return fallback


def _profile_unique_points(points):
    clean = []
    for point in list(points or []):
        if clean and (point - clean[-1]).Length <= 1.0e-9:
            continue
        clean.append(point)
    return clean


def _make_profile_edges(edges, *, stroke_width: float = 0.0):
    if Part is None:
        return None
    edge_shapes = []
    for start, end in list(edges or []):
        try:
            if (end - start).Length > 1.0e-9:
                stroke = _make_profile_segment_stroke(start, end, stroke_width)
                edge_shapes.append(stroke if stroke is not None else Part.makeLine(start, end))
        except Exception:
            continue
    return Part.Compound(edge_shapes) if edge_shapes else Part.Shape()


def _make_profile_segment_stroke(start, end, stroke_width: float):
    """Build a shallow X-Z ribbon solid so profile lines remain visible in Front view."""

    width = float(stroke_width or 0.0)
    if width <= 0.0 or Part is None:
        return None
    try:
        dx = float(end.x) - float(start.x)
        dz = float(end.z) - float(start.z)
        length = math.hypot(dx, dz)
        if length <= 1.0e-9:
            return None
        half = width * 0.5
        nx = -dz / length * half
        nz = dx / length * half
        points = [
            App.Vector(float(start.x) + nx, float(start.y), float(start.z) + nz),
            App.Vector(float(end.x) + nx, float(end.y), float(end.z) + nz),
            App.Vector(float(end.x) - nx, float(end.y), float(end.z) - nz),
            App.Vector(float(start.x) - nx, float(start.y), float(start.z) - nz),
            App.Vector(float(start.x) + nx, float(start.y), float(start.z) + nz),
        ]
        front_face = Part.Face(Part.makePolygon(points))
        try:
            depth = max(0.8, width * 0.25)
            return front_face.extrude(App.Vector(0.0, -depth, 0.0))
        except Exception:
            reversed_face = Part.Face(Part.makePolygon(list(reversed(points))))
            return Part.Compound([front_face, reversed_face])
    except Exception:
        return None


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
        vobj.DisplayMode = "Flat Lines"
        vobj.ShapeColor = color
        vobj.LineColor = color
        vobj.PointColor = color
        vobj.LineWidth = float(line_width)
        vobj.PointSize = max(4.0, float(line_width) + 2.0)
        if hasattr(vobj, "DrawStyle"):
            vobj.DrawStyle = "Solid"
        if hasattr(vobj, "Lighting"):
            try:
                vobj.Lighting = "Two side"
            except Exception:
                pass
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


configure_profile_editor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditProfile", CmdV1ProfileEditor())
