"""Plan/profile viewer command bridge for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ..models.source.alignment_model import AlignmentElement, AlignmentModel
from ..models.output.plan_output import PlanStationRow
from ..models.output.profile_output import ProfileLineRow
from ..models.result.tin_surface import TINSurface
from ..models.source.profile_model import ProfileControlPoint, ProfileModel
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_profile import find_v1_profile, to_profile_model
from ..objects.obj_stationing import find_v1_stationing, station_value_rows
from ..services.evaluation import (
    AlignmentEvaluationService,
    AlignmentStationSamplingService,
    LegacyDocumentAdapter,
    ProfileEarthworkAreaHintService,
    ProfileEarthworkHintService,
    ProfileEvaluationService,
    ProfileTinSamplingService,
)
from ..services.mapping import PlanOutputMapper, ProfileOutputMapper
from ..ui.common import clear_ui_context, get_ui_context
from ..ui.viewers import PlanProfileViewerTaskPanel
from .cmd_earthwork_balance import build_document_earthwork_report
from .selection_context import selected_alignment_profile_target


DEFAULT_STATION_INTERVAL = 20.0


def _build_navigation_station_rows(
    station_values: list[tuple[float, str]] | None,
    *,
    current_station: float | None,
    alignment_model: AlignmentModel | None = None,
    profile_model: ProfileModel | None = None,
) -> list[dict[str, object]]:
    """Build the station-navigation payload for the plan/profile viewer."""

    raw_rows = []
    for station, label in list(station_values or []):
        try:
            station_value = float(station)
        except Exception:
            continue
        raw_rows.append((station_value, str(label or f"STA {station_value:.3f}").strip()))
    if not raw_rows:
        return []

    unique_rows: list[tuple[float, str]] = []
    seen_stations: set[float] = set()
    for station_value, label in sorted(raw_rows, key=lambda row: row[0]):
        rounded = round(station_value, 9)
        if rounded in seen_stations:
            continue
        seen_stations.add(rounded)
        unique_rows.append((station_value, label))

    if current_station is None:
        current_index = 0
    else:
        current_index = min(
            range(len(unique_rows)),
            key=lambda idx: abs(unique_rows[idx][0] - float(current_station)),
        )

    result = []
    for output_index, row_index in enumerate(range(len(unique_rows))):
        station_value, label = unique_rows[row_index]
        if row_index == 0:
            navigation_kind = "first"
        elif row_index == len(unique_rows) - 1:
            navigation_kind = "last"
        elif row_index == current_index:
            navigation_kind = "current"
        elif row_index < current_index:
            navigation_kind = "previous"
        else:
            navigation_kind = "next"
        result.append(
            {
                "index": row_index,
                "station": station_value,
                "label": label or f"STA {station_value:.3f}",
                "navigation_kind": navigation_kind,
                "navigation_reason": _station_navigation_reason(
                    navigation_kind,
                    is_current=bool(row_index == current_index),
                ),
                "is_current": bool(row_index == current_index),
                "navigation_order": output_index,
            }
        )
    enriched = _enrich_station_rows_with_alignment_frame(result, alignment_model)
    return _enrich_station_rows_with_profile_frame(enriched, profile_model)


def _station_navigation_reason(navigation_kind: str, *, is_current: bool = False) -> str:
    """Return a user-facing reason for one review navigation station."""

    if is_current:
        return "Current review focus station"
    return {
        "first": "Start of station range",
        "last": "End of station range",
        "previous": "Station before the current focus",
        "next": "Station after the current focus",
        "current": "Current review focus station",
    }.get(str(navigation_kind or "").strip(), "Review navigation station")


def _enrich_station_rows_with_alignment_frame(
    rows: list[dict[str, object]],
    alignment_model: AlignmentModel | None,
) -> list[dict[str, object]]:
    """Attach evaluated alignment frame data to station rows when possible."""

    if alignment_model is None:
        return rows
    service = AlignmentEvaluationService()
    enriched_rows = []
    for row in rows:
        item = dict(row)
        result = service.evaluate_station(
            alignment_model,
            float(item.get("station", 0.0) or 0.0),
        )
        item["alignment_eval_status"] = result.status
        if result.status == "ok":
            item["x"] = result.x
            item["y"] = result.y
            item["tangent_direction_deg"] = result.tangent_direction_deg
            item["active_element_id"] = result.active_element_id
            item["active_element_kind"] = result.active_element_kind
        else:
            item["alignment_eval_notes"] = result.notes
        enriched_rows.append(item)
    return enriched_rows


def _enrich_station_rows_with_profile_frame(
    rows: list[dict[str, object]],
    profile_model: ProfileModel | None,
) -> list[dict[str, object]]:
    """Attach evaluated finished-grade data to station rows when possible."""

    if profile_model is None:
        return rows
    service = ProfileEvaluationService()
    enriched_rows = []
    for row in rows:
        item = dict(row)
        result = service.evaluate_station(
            profile_model,
            float(item.get("station", 0.0) or 0.0),
        )
        item["profile_eval_status"] = result.status
        item["profile_elevation"] = result.elevation
        item["profile_grade"] = result.grade
        item["active_profile_control_id"] = result.active_control_point_id
        item["active_profile_control_kind"] = result.active_control_kind
        item["active_profile_segment_start_id"] = result.active_segment_start_id
        item["active_profile_segment_end_id"] = result.active_segment_end_id
        item["active_vertical_curve_id"] = result.active_vertical_curve_id
        if result.notes:
            item["profile_eval_notes"] = result.notes
        enriched_rows.append(item)
    return enriched_rows


def _station_values_from_alignment_sampling(
    alignment_model: AlignmentModel | None,
    *,
    interval: float = 20.0,
    extra_stations: list[float] | None = None,
) -> list[tuple[float, str]]:
    """Build station values from the shared alignment range sampler."""

    if alignment_model is None:
        return []
    result = AlignmentStationSamplingService().sample_alignment(
        alignment=alignment_model,
        interval=interval,
        extra_stations=extra_stations,
    )
    if not result.rows:
        return []
    return [(row.station, row.station_label) for row in result.rows]


def _apply_v1_stationing_to_plan_output(plan_output, stationing) -> None:
    """Replace plan station rows with explicit V1Stationing rows when available."""

    if plan_output is None or stationing is None:
        return
    stations = list(getattr(stationing, "StationValues", []) or [])
    if not stations:
        return
    labels = list(getattr(stationing, "StationLabels", []) or [])
    x_values = list(getattr(stationing, "XValues", []) or [])
    y_values = list(getattr(stationing, "YValues", []) or [])
    reasons = list(getattr(stationing, "SourceReasons", []) or [])
    rows = []
    for index, station in enumerate(stations):
        rows.append(
            PlanStationRow(
                station_row_id=f"{getattr(plan_output, 'plan_output_id', 'plan')}:v1-station:{index + 1}",
                station=float(station),
                station_label=(
                    str(labels[index])
                    if index < len(labels) and labels[index]
                    else f"STA {float(station):.3f}"
                ),
                x=float(x_values[index]) if index < len(x_values) else 0.0,
                y=float(y_values[index]) if index < len(y_values) else 0.0,
                kind=str(reasons[index]) if index < len(reasons) and reasons[index] else "v1_stationing",
            )
        )
    plan_output.station_rows = rows


def _apply_tin_existing_ground_profile(preview: dict[str, object], *, interval: float = 20.0) -> None:
    """Attach an existing-ground line row sampled from TIN when available."""

    alignment_model = preview.get("alignment_model", None)
    plan_output = preview.get("plan_output", None)
    profile_output = preview.get("profile_output", None)
    surface = preview.get("tin_surface", None)
    if alignment_model is None or profile_output is None or not isinstance(surface, TINSurface):
        return

    extra_stations = [
        float(row.get("station", 0.0) or 0.0)
        for row in list(preview.get("station_rows", []) or [])
    ]
    for row in list(getattr(plan_output, "station_rows", []) or []):
        try:
            extra_stations.append(float(getattr(row, "station", 0.0) or 0.0))
        except Exception:
            continue
    result = ProfileTinSamplingService().sample_alignment(
        alignment=alignment_model,
        surface=surface,
        interval=interval,
        extra_stations=extra_stations,
    )
    preview["profile_tin_sample_result"] = result

    existing_rows = [
        row
        for row in list(getattr(profile_output, "line_rows", []) or [])
        if str(getattr(row, "kind", "") or "") != "existing_ground_line"
    ]
    profile_output.line_rows = existing_rows + _existing_ground_profile_line_rows(result)


def _apply_profile_earthwork_hints(preview: dict[str, object]) -> None:
    """Attach profile-level EG/FG cut/fill depth hints."""

    profile_output = preview.get("profile_output", None)
    if profile_output is None:
        return
    service = ProfileEarthworkHintService()
    result = service.build(profile_output)
    preview["profile_earthwork_hint_result"] = result
    if result.status != "ok":
        return

    existing_rows = [
        row
        for row in list(getattr(profile_output, "earthwork_rows", []) or [])
        if not str(getattr(row, "kind", "") or "").startswith("profile_")
    ]
    row_id_prefix = str(getattr(profile_output, "profile_output_id", "") or "profile")
    profile_output.earthwork_rows = existing_rows + service.to_profile_earthwork_rows(
        result,
        row_id_prefix=row_id_prefix,
    )


def _apply_profile_earthwork_area_hints(preview: dict[str, object]) -> None:
    """Attach profile-level rectangular-equivalent cut/fill area hints."""

    profile_output = preview.get("profile_output", None)
    if profile_output is None:
        return
    service = ProfileEarthworkAreaHintService()
    result = service.build(
        profile_output,
        section_width=_profile_area_hint_width(preview),
    )
    preview["profile_earthwork_area_hint_result"] = result
    if result.status != "ok":
        return

    area_kinds = service.area_kinds()
    existing_rows = [
        row
        for row in list(getattr(profile_output, "earthwork_rows", []) or [])
        if str(getattr(row, "kind", "") or "") not in area_kinds
    ]
    row_id_prefix = str(getattr(profile_output, "profile_output_id", "") or "profile")
    profile_output.earthwork_rows = existing_rows + service.to_profile_earthwork_rows(
        result,
        row_id_prefix=row_id_prefix,
    )


def _profile_area_hint_width(preview: dict[str, object]) -> float | None:
    """Resolve an explicit section width for early profile area hints."""

    candidates = [
        preview.get("earthwork_area_width", None),
        preview.get("profile_earthwork_area_width", None),
    ]
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    candidates.extend(
        [
            viewer_context.get("earthwork_area_width", None),
            viewer_context.get("profile_earthwork_area_width", None),
            viewer_context.get("section_width", None),
        ]
    )
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            width = float(candidate)
        except Exception:
            continue
        if width > 0.0:
            return width
    return None


def resolve_station_interval(
    context: dict[str, object] | None = None,
    *,
    default: float = DEFAULT_STATION_INTERVAL,
) -> float:
    """Resolve a safe plan/profile station sampling interval from context."""

    payload = dict(context or {})
    viewer_context = dict(payload.get("viewer_context", {}) or {})
    candidates = [
        payload.get("station_interval", None),
        payload.get("plan_profile_station_interval", None),
        viewer_context.get("station_interval", None),
        viewer_context.get("plan_profile_station_interval", None),
    ]
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            value = float(candidate)
        except Exception:
            continue
        if value > 0.0:
            return value
    return float(default)


def _existing_ground_profile_line_rows(result) -> list[ProfileLineRow]:
    segments: list[list[object]] = []
    current: list[object] = []
    for row in list(getattr(result, "rows", []) or []):
        if bool(getattr(row, "found", False)):
            current.append(row)
            continue
        if current:
            segments.append(current)
            current = []
    if current:
        segments.append(current)

    line_rows = []
    for index, segment in enumerate(segments, start=1):
        if len(segment) < 2:
            continue
        line_rows.append(
            ProfileLineRow(
                line_row_id=f"{result.alignment_id}:eg:{index}",
                kind="existing_ground_line",
                station_values=[float(row.station) for row in segment],
                elevation_values=[float(row.elevation) for row in segment if row.elevation is not None],
                style_role="existing_ground",
                source_ref=str(getattr(result, "surface_ref", "") or ""),
            )
        )
    return line_rows


def build_alignment_profile_bridge_diagnostics(preview: dict[str, object]) -> list[dict[str, str]]:
    """Build visible diagnostics for the v0 document to v1 alignment/profile bridge."""

    source_kind = str(preview.get("preview_source_kind", "") or "").strip() or "unknown"
    alignment_model = preview.get("alignment_model", None)
    profile_model = preview.get("profile_model", None)
    legacy_objects = dict(preview.get("legacy_objects", {}) or {})

    rows: list[dict[str, str]] = [
        _bridge_diagnostic_row(
            "preview_source",
            "ok" if source_kind == "document" else "warning",
            f"Preview source is {source_kind}.",
            "document means the viewer is reading the active FreeCAD document; demo means fallback sample data.",
        )
    ]

    rows.append(_alignment_model_diagnostic_row(alignment_model))
    rows.append(_profile_model_diagnostic_row(profile_model))
    rows.append(_legacy_object_diagnostic_row("legacy_alignment_object", legacy_objects.get("alignment"), source_kind))
    rows.append(_legacy_object_diagnostic_row("legacy_profile_object", legacy_objects.get("profile"), source_kind))
    rows.append(_alignment_profile_link_diagnostic_row(alignment_model, profile_model))
    rows.append(_profile_station_range_diagnostic_row(alignment_model, profile_model, preview))
    return rows


def _bridge_diagnostic_row(kind: str, status: str, message: str, notes: str = "") -> dict[str, str]:
    return {
        "kind": kind,
        "status": status,
        "message": message,
        "notes": notes,
    }


def _alignment_model_diagnostic_row(alignment_model) -> dict[str, str]:
    if alignment_model is None:
        return _bridge_diagnostic_row(
            "alignment_model",
            "error",
            "No v1 AlignmentModel was built.",
            "The document needs a HorizontalAlignment object or an explicit preferred alignment.",
        )
    element_count = len(list(getattr(alignment_model, "geometry_sequence", []) or []))
    if element_count <= 0:
        return _bridge_diagnostic_row(
            "alignment_model",
            "warning",
            "AlignmentModel exists but has no geometry elements.",
            f"alignment_id={getattr(alignment_model, 'alignment_id', '')}",
        )
    return _bridge_diagnostic_row(
        "alignment_model",
        "ok",
        f"AlignmentModel built with {element_count} geometry element(s).",
        f"alignment_id={getattr(alignment_model, 'alignment_id', '')}",
    )


def _profile_model_diagnostic_row(profile_model) -> dict[str, str]:
    if profile_model is None:
        return _bridge_diagnostic_row(
            "profile_model",
            "error",
            "No v1 ProfileModel was built.",
            "The document needs a VerticalAlignment object or an explicit preferred profile.",
        )
    control_count = len(list(getattr(profile_model, "control_rows", []) or []))
    if control_count < 2:
        return _bridge_diagnostic_row(
            "profile_model",
            "warning",
            f"ProfileModel has only {control_count} control point(s).",
            f"profile_id={getattr(profile_model, 'profile_id', '')}",
        )
    return _bridge_diagnostic_row(
        "profile_model",
        "ok",
        f"ProfileModel built with {control_count} control point(s).",
        f"profile_id={getattr(profile_model, 'profile_id', '')}",
    )


def _legacy_object_diagnostic_row(kind: str, obj, source_kind: str) -> dict[str, str]:
    if source_kind != "document":
        return _bridge_diagnostic_row(
            kind,
            "not_applicable",
            "Legacy object check skipped for demo preview.",
            "",
        )
    if obj is None:
        return _bridge_diagnostic_row(
            kind,
            "error",
            "Legacy source object was not resolved.",
            "The bridge could not find the expected v0 object in the active document.",
        )
    name = str(getattr(obj, "Name", "") or getattr(obj, "Label", "") or "").strip()
    return _bridge_diagnostic_row(
        kind,
        "ok",
        "Legacy source object resolved.",
        name,
    )


def _alignment_profile_link_diagnostic_row(alignment_model, profile_model) -> dict[str, str]:
    if alignment_model is None or profile_model is None:
        return _bridge_diagnostic_row(
            "alignment_profile_link",
            "error",
            "Alignment/Profile link cannot be checked because one side is missing.",
            "",
        )
    alignment_id = str(getattr(alignment_model, "alignment_id", "") or "").strip()
    profile_alignment_id = str(getattr(profile_model, "alignment_id", "") or "").strip()
    if not profile_alignment_id:
        return _bridge_diagnostic_row(
            "alignment_profile_link",
            "warning",
            "ProfileModel does not reference an alignment_id.",
            f"alignment_id={alignment_id}",
        )
    if alignment_id != profile_alignment_id:
        return _bridge_diagnostic_row(
            "alignment_profile_link",
            "warning",
            "ProfileModel references a different alignment_id.",
            f"alignment={alignment_id}; profile.alignment_id={profile_alignment_id}",
        )
    return _bridge_diagnostic_row(
        "alignment_profile_link",
        "ok",
        "ProfileModel is linked to the active AlignmentModel.",
        f"alignment_id={alignment_id}",
    )


def _profile_station_range_diagnostic_row(alignment_model, profile_model, preview: dict[str, object]) -> dict[str, str]:
    if alignment_model is None or profile_model is None:
        return _bridge_diagnostic_row(
            "profile_station_range",
            "error",
            "Profile station range cannot be checked because alignment or profile is missing.",
            "",
        )
    alignment_extent = _alignment_station_extent(alignment_model, preview)
    profile_stations = _profile_station_values(profile_model)
    if not profile_stations:
        return _bridge_diagnostic_row(
            "profile_station_range",
            "warning",
            "ProfileModel has no station control values to check.",
            "",
        )
    if alignment_extent is None:
        return _bridge_diagnostic_row(
            "profile_station_range",
            "warning",
            "Alignment station range is unavailable.",
            f"profile={min(profile_stations):.3f}->{max(profile_stations):.3f}",
        )
    station_start, station_end = alignment_extent
    outside = [
        station
        for station in profile_stations
        if station < station_start - 1.0e-6 or station > station_end + 1.0e-6
    ]
    if outside:
        return _bridge_diagnostic_row(
            "profile_station_range",
            "warning",
            f"{len(outside)} profile station(s) fall outside the alignment station range.",
            f"alignment={station_start:.3f}->{station_end:.3f}; profile={min(profile_stations):.3f}->{max(profile_stations):.3f}",
        )
    return _bridge_diagnostic_row(
        "profile_station_range",
        "ok",
        "Profile control stations fit within the alignment station range.",
        f"alignment={station_start:.3f}->{station_end:.3f}; profile={min(profile_stations):.3f}->{max(profile_stations):.3f}",
    )


def _alignment_station_extent(alignment_model, preview: dict[str, object]) -> tuple[float, float] | None:
    values: list[float] = []
    for element in list(getattr(alignment_model, "geometry_sequence", []) or []):
        for attr in ("station_start", "station_end"):
            try:
                values.append(float(getattr(element, attr)))
            except Exception:
                pass
    if not values:
        plan_output = preview.get("plan_output", None)
        for row in list(getattr(plan_output, "station_rows", []) or []):
            try:
                values.append(float(getattr(row, "station")))
            except Exception:
                pass
    if not values:
        return None
    return min(values), max(values)


def _profile_station_values(profile_model) -> list[float]:
    values: list[float] = []
    for row in list(getattr(profile_model, "control_rows", []) or []):
        try:
            values.append(float(getattr(row, "station")))
        except Exception:
            pass
    for row in list(getattr(profile_model, "vertical_curve_rows", []) or []):
        for attr in ("station_start", "station_end"):
            try:
                values.append(float(getattr(row, attr)))
            except Exception:
                pass
    return values


def _bridge_diagnostic_counts(preview: dict[str, object]) -> dict[str, int]:
    counts = {"ok": 0, "warning": 0, "error": 0, "not_applicable": 0}
    for row in list(preview.get("bridge_diagnostic_rows", []) or []):
        status = str(dict(row or {}).get("status", "") or "").strip()
        counts[status] = counts.get(status, 0) + 1
    return counts


def _resolve_document_tin_surface(document, *, gui_module=Gui) -> TINSurface | None:
    """Resolve a document TIN surface for profile EG sampling when available."""

    if document is None:
        return None
    try:
        from .cmd_review_tin import build_document_tin_review

        preview = build_document_tin_review(document, gui_module=gui_module)
        surface = (preview or {}).get("tin_surface", None)
        return surface if isinstance(surface, TINSurface) else None
    except Exception:
        return None


def build_document_plan_profile_preview(
    document,
    *,
    preferred_alignment=None,
    preferred_profile=None,
    station_interval: float = DEFAULT_STATION_INTERVAL,
) -> dict[str, object] | None:
    """Build a v1 plan/profile viewer payload from a FreeCAD document."""

    adapter = LegacyDocumentAdapter()
    project = adapter._find_project(document)
    v1_alignment_object = find_v1_alignment(document, preferred_alignment=preferred_alignment)
    alignment_model = to_alignment_model(v1_alignment_object) if v1_alignment_object is not None else None
    if alignment_model is None:
        alignment_model = adapter.build_alignment_model(
            document,
            preferred_alignment=preferred_alignment,
        )
    v1_profile_object = find_v1_profile(document, preferred_profile=preferred_profile)
    profile_model = to_profile_model(v1_profile_object) if v1_profile_object is not None else None
    if profile_model is None:
        profile_model = adapter.build_profile_model(
            document,
            preferred_profile=preferred_profile,
            preferred_alignment=preferred_alignment,
        )
    alignment_object = v1_alignment_object or adapter._resolve_alignment_object(
        project,
        document,
        preferred_alignment=preferred_alignment,
    )
    profile_object = v1_profile_object or adapter._resolve_vertical_alignment_object(
        project,
        document,
        preferred_profile=preferred_profile,
    )
    v1_stationing_object = find_v1_stationing(document)
    if alignment_model is None and profile_model is None:
        return None

    earthwork_model = None
    try:
        report = build_document_earthwork_report(document)
        if report is not None:
            earthwork_model = report.get("earthwork_model")
    except Exception:
        earthwork_model = None

    plan_output = (
        PlanOutputMapper().map_alignment_model(
            alignment_model,
            station_interval=station_interval,
        )
        if alignment_model is not None
        else None
    )
    profile_output = (
        ProfileOutputMapper().map_profile_model(
            profile_model,
            earthwork_model,
            station_interval=station_interval,
        )
        if profile_model is not None
        else None
    )
    tin_surface = _resolve_document_tin_surface(document)
    _apply_v1_stationing_to_plan_output(plan_output, v1_stationing_object)
    current_station = None
    station_values: list[tuple[float, str]] = []
    profile_station_values: list[float] = []
    stationing_values = station_value_rows(v1_stationing_object)
    if profile_output is not None:
        for row in list(getattr(profile_output, "pvi_rows", []) or []):
            profile_station_values.append(float(getattr(row, "station", 0.0) or 0.0))
    if stationing_values:
        station_values.extend(stationing_values)
        for station in profile_station_values:
            station_values.append((station, f"STA {station:.3f}"))
    else:
        if profile_output is not None:
            for row in list(getattr(profile_output, "pvi_rows", []) or []):
                station_values.append(
                    (
                        float(getattr(row, "station", 0.0) or 0.0),
                        str(getattr(row, "label", "") or f"STA {float(getattr(row, 'station', 0.0) or 0.0):.3f}"),
                    )
                )
        station_values.extend(
            _station_values_from_alignment_sampling(
                alignment_model,
                interval=station_interval,
                extra_stations=profile_station_values,
            )
        )
    if not station_values and plan_output is not None:
        for row in list(getattr(plan_output, "station_rows", []) or []):
            station_values.append(
                (
                    float(getattr(row, "station", 0.0) or 0.0),
                    str(getattr(row, "station_label", "") or f"STA {float(getattr(row, 'station', 0.0) or 0.0):.3f}"),
                )
            )
    if profile_output is not None and getattr(profile_output, "pvi_rows", None):
        current_station = float(getattr(profile_output.pvi_rows[0], "station", 0.0) or 0.0)
    elif plan_output is not None and getattr(plan_output, "station_rows", None):
        current_station = float(getattr(plan_output.station_rows[0], "station", 0.0) or 0.0)
    preview = {
        "preview_source_kind": "document",
        "alignment_model": alignment_model,
        "profile_model": profile_model,
        "plan_output": plan_output,
        "profile_output": profile_output,
        "earthwork_model": earthwork_model,
        "tin_surface": tin_surface,
        "station_interval": float(station_interval),
        "station_rows": _build_navigation_station_rows(
            station_values,
            current_station=current_station,
            alignment_model=alignment_model,
            profile_model=profile_model,
        ),
        "legacy_objects": {
            "project": project,
            "alignment": alignment_object,
            "profile": profile_object,
            "stationing": v1_stationing_object,
        },
    }
    preview["bridge_diagnostic_rows"] = build_alignment_profile_bridge_diagnostics(preview)
    return preview


def build_demo_plan_profile_preview(
    document_label: str = "",
    *,
    station_interval: float = DEFAULT_STATION_INTERVAL,
) -> dict[str, object]:
    """Build a minimal in-memory plan/profile viewer payload."""

    alignment_model = AlignmentModel(
        schema_version=1,
        project_id="corridorroad-v1-demo",
        alignment_id="alignment:v1-demo",
        label=document_label or "CorridorRoad v1 Demo Alignment",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:v1-demo:1",
                kind="tangent",
                station_start=0.0,
                station_end=40.0,
                length=40.0,
                geometry_payload={
                    "x_values": [1000.0, 1040.0],
                    "y_values": [2000.0, 2000.0],
                },
            ),
            AlignmentElement(
                element_id="alignment:v1-demo:2",
                kind="transition_curve",
                station_start=40.0,
                station_end=80.0,
                length=40.0,
                geometry_payload={
                    "x_values": [1040.0, 1070.0, 1080.0],
                    "y_values": [2000.0, 2010.0, 2040.0],
                },
            ),
        ],
    )
    profile_model = ProfileModel(
        schema_version=1,
        project_id="corridorroad-v1-demo",
        profile_id="profile:v1-demo",
        alignment_id=alignment_model.alignment_id,
        label=document_label or "CorridorRoad v1 Demo Profile",
        control_rows=[
            ProfileControlPoint(
                control_point_id="profile:v1-demo:pvi:1",
                station=0.0,
                elevation=12.0,
                kind="grade_break",
            ),
            ProfileControlPoint(
                control_point_id="profile:v1-demo:pvi:2",
                station=40.0,
                elevation=13.5,
                kind="pvi",
            ),
            ProfileControlPoint(
                control_point_id="profile:v1-demo:pvi:3",
                station=80.0,
                elevation=12.8,
                kind="grade_break",
            ),
        ],
    )

    plan_output = PlanOutputMapper().map_alignment_model(
        alignment_model,
        station_interval=station_interval,
    )
    profile_output = ProfileOutputMapper().map_profile_model(
        profile_model,
        station_interval=station_interval,
    )
    preview = {
        "preview_source_kind": "demo",
        "alignment_model": alignment_model,
        "profile_model": profile_model,
        "plan_output": plan_output,
        "profile_output": profile_output,
        "earthwork_model": None,
        "station_rows": _build_navigation_station_rows(
            _station_values_from_alignment_sampling(
                alignment_model,
                interval=station_interval,
                extra_stations=[0.0, 40.0, 80.0],
            ),
            current_station=0.0,
            alignment_model=alignment_model,
            profile_model=profile_model,
        ),
        "station_interval": float(station_interval),
        "legacy_objects": {},
    }
    preview["bridge_diagnostic_rows"] = build_alignment_profile_bridge_diagnostics(preview)
    return preview


def format_plan_profile_preview(preview: dict[str, object]) -> str:
    """Format a concise human-readable plan/profile viewer summary."""

    alignment_model = preview.get("alignment_model")
    profile_model = preview.get("profile_model")
    plan_output = preview.get("plan_output")
    profile_output = preview.get("profile_output")
    viewer_context = dict(preview.get("viewer_context", {}) or {})

    lines = [
        "CorridorRoad v1 Plan/Profile Connection Review",
        f"Preview source: {str(preview.get('preview_source_kind', '') or 'unknown')}",
        f"Alignment: {getattr(alignment_model, 'label', '') or '(missing)'}",
        f"Alignment elements: {len(list(getattr(plan_output, 'geometry_rows', []) or []))}",
        f"Plan stations: {len(list(getattr(plan_output, 'station_rows', []) or []))}",
        f"Profile: {getattr(profile_model, 'label', '') or '(missing)'}",
        f"Profile controls: {len(list(getattr(profile_output, 'pvi_rows', []) or []))}",
        f"Profile lines: {len(list(getattr(profile_output, 'line_rows', []) or []))}",
        f"Earthwork attachments: {len(list(getattr(profile_output, 'earthwork_rows', []) or []))}",
        f"Navigation stations: {len(list(preview.get('station_rows', []) or []))}",
    ]
    bridge_counts = _bridge_diagnostic_counts(preview)
    if bridge_counts:
        lines.append(
            "Bridge diagnostics: "
            f"ok={bridge_counts.get('ok', 0)}, "
            f"warning={bridge_counts.get('warning', 0)}, "
            f"error={bridge_counts.get('error', 0)}"
        )
        first_issue = next(
            (
                dict(row or {})
                for row in list(preview.get("bridge_diagnostic_rows", []) or [])
                if str(dict(row or {}).get("status", "") or "") not in {"", "ok", "not_applicable"}
            ),
            None,
        )
        if first_issue is not None:
            lines.append(
                "Bridge first issue: "
                f"{first_issue.get('kind', '')} - {first_issue.get('message', '')}"
            )
    area_width = _profile_area_hint_width(preview)
    if area_width is not None:
        lines.append(f"Earthwork area width: {area_width:.3f} m")
    area_result = preview.get("profile_earthwork_area_hint_result", None)
    area_status = str(getattr(area_result, "status", "") or "").strip()
    if area_status and (area_width is not None or area_status == "ok"):
        lines.append(f"Earthwork area status: {area_status}")
    eg_result = preview.get("profile_tin_sample_result", None)
    if eg_result is not None:
        eg_rows = list(getattr(eg_result, "rows", []) or [])
        lines.append(
            "EG sampling: "
            f"{str(getattr(eg_result, 'status', '') or 'unknown')} "
            f"({int(getattr(eg_result, 'hit_count', 0) or 0)}/{len(eg_rows)} hits)"
        )
    evaluated_station_count = sum(
        1
        for row in list(preview.get("station_rows", []) or [])
        if str(row.get("alignment_eval_status", "") or "") == "ok"
    )
    if evaluated_station_count:
        lines.append(f"Evaluated alignment stations: {evaluated_station_count}")
    evaluated_profile_station_count = sum(
        1
        for row in list(preview.get("station_rows", []) or [])
        if str(row.get("profile_eval_status", "") or "") == "ok"
    )
    if evaluated_profile_station_count:
        lines.append(f"Evaluated profile stations: {evaluated_profile_station_count}")
    source_panel = str(viewer_context.get("source_panel", "") or "").strip()
    focus_station_label = str(viewer_context.get("focus_station_label", "") or "").strip()
    selected_row = str(viewer_context.get("selected_row_label", "") or "").strip()
    if source_panel:
        lines.append(f"Context Source: {source_panel}")
    if focus_station_label:
        lines.append(f"Focus Station: {focus_station_label}")
    if selected_row:
        lines.append(f"Selected Row: {selected_row}")
    return "\n".join(lines)


def show_v1_plan_profile_preview(
    *,
    document=None,
    preferred_alignment=None,
    preferred_profile=None,
    extra_context: dict[str, object] | None = None,
    app_module=None,
    gui_module=None,
) -> dict[str, object]:
    """Build and show one v1 plan/profile viewer for a given document context."""

    app = App if app_module is None else app_module
    gui = Gui if gui_module is None else gui_module
    active_document = document
    if active_document is None and app is not None:
        active_document = getattr(app, "ActiveDocument", None)

    document_label = ""
    if active_document is not None:
        document_label = str(getattr(active_document, "Label", "") or "")
    preview = None
    if active_document is not None:
        station_interval = resolve_station_interval(extra_context)
        preview = build_document_plan_profile_preview(
            active_document,
            preferred_alignment=preferred_alignment,
            preferred_profile=preferred_profile,
            station_interval=station_interval,
        )
    if preview is None:
        station_interval = resolve_station_interval(extra_context)
        preview = build_demo_plan_profile_preview(
            document_label=document_label,
            station_interval=station_interval,
        )
    if extra_context:
        preview.update(dict(extra_context))
    station_interval = resolve_station_interval(preview)
    preview["station_interval"] = station_interval
    viewer_context = dict(preview.get("viewer_context", {}) or {})
    viewer_context["station_interval"] = station_interval
    preview["viewer_context"] = viewer_context
    preview["station_rows"] = list(preview.get("station_rows", []) or [])
    preview["bridge_diagnostic_rows"] = build_alignment_profile_bridge_diagnostics(preview)
    _apply_tin_existing_ground_profile(preview, interval=station_interval)
    _apply_profile_earthwork_hints(preview)
    _apply_profile_earthwork_area_hints(preview)
    summary_text = format_plan_profile_preview(preview)

    if app is not None:
        app.Console.PrintMessage(summary_text + "\n")

    if gui is not None and hasattr(gui, "Control"):  # pragma: no branch - GUI path only in FreeCAD.
        try:
            gui.Control.showDialog(PlanProfileViewerTaskPanel(preview))
        except Exception:
            try:  # pragma: no cover - GUI fallback not available in tests.
                from PySide import QtGui

                QtGui.QMessageBox.information(
                    None,
                    "CorridorRoad v1 Plan/Profile Connection Review",
                    summary_text,
                )
            except Exception:
                pass

    return preview


def run_v1_plan_profile_preview_command() -> dict[str, object]:
    """Execute the minimal v1 plan/profile viewer bridge and show a summary."""

    preferred_alignment = None
    preferred_profile = None
    extra_context = None
    ui_context = get_ui_context()
    clear_ui_context()
    if App is not None and getattr(App, "ActiveDocument", None) is not None:
        preferred_alignment, preferred_profile = selected_alignment_profile_target(Gui, App.ActiveDocument)
        if preferred_alignment is None:
            object_name = str(ui_context.get("preferred_alignment_name", "") or "").strip()
            if object_name:
                try:
                    preferred_alignment = App.ActiveDocument.getObject(object_name)
                except Exception:
                    preferred_alignment = None
        if preferred_profile is None:
            object_name = str(ui_context.get("preferred_profile_name", "") or "").strip()
            if object_name:
                try:
                    preferred_profile = App.ActiveDocument.getObject(object_name)
                except Exception:
                    preferred_profile = None
        extra_context = {}
        for key in (
            "viewer_context",
            "station_row",
            "source",
            "station_interval",
            "plan_profile_station_interval",
        ):
            if key in ui_context:
                extra_context[key] = ui_context[key]
        if extra_context.get("viewer_context", None):
            viewer_context = dict(extra_context.get("viewer_context", {}) or {})
            if ui_context.get("preferred_station", None) is not None:
                try:
                    viewer_context["focus_station"] = float(ui_context.get("preferred_station"))
                except Exception:
                    pass
            extra_context["viewer_context"] = viewer_context
        if not extra_context:
            extra_context = None

    return show_v1_plan_profile_preview(
        document=getattr(App, "ActiveDocument", None) if App is not None else None,
        preferred_alignment=preferred_alignment,
        preferred_profile=preferred_profile,
        extra_context=extra_context,
        app_module=App,
        gui_module=Gui,
    )


class CmdV1ReviewPlanProfile:
    """Standalone v1 plan/profile viewer command."""

    def GetResources(self):
        from freecad.Corridor_Road.misc.resources import icon_path

        return {
            "Pixmap": icon_path("alignment.svg"),
            "MenuText": "Plan/Profile Connection Review",
            "ToolTip": "Review Alignment, Stations, Profile, and TIN EG connectivity on one station grid",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_plan_profile_preview_command()


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1ReviewPlanProfile", CmdV1ReviewPlanProfile())
