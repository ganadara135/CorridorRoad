"""Drainage pipeline geometry output mapping for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.drainage_output import DrainagePipelineGeometryOutputRow, DrainagePipelineSegmentOutputRow
from ...models.source.alignment_model import AlignmentModel
from ..evaluation.alignment_evaluation_service import AlignmentEvaluationService


def build_drainage_pipeline_geometry_rows(
    segment_rows: list[DrainagePipelineSegmentOutputRow],
    *,
    alignment_model: AlignmentModel | None = None,
    station_offset_to_xy=None,
    coordinate_mode: str = "",
    sample_spacing: float = 10.0,
) -> list[DrainagePipelineGeometryOutputRow]:
    """Build output-only centerline geometry rows for resolved pipeline segments."""

    adapter = None
    requested_coordinate_mode = str(coordinate_mode or "")
    coordinate_mode = "station_offset_fallback"
    if station_offset_to_xy is not None:
        adapter = station_offset_to_xy
        coordinate_mode = requested_coordinate_mode or "station_offset_adapter"
    elif alignment_model is not None:
        try:
            adapter = AlignmentEvaluationService().station_offset_adapter(alignment_model)
            coordinate_mode = "alignment_station_offset"
        except Exception:
            adapter = None
            coordinate_mode = "station_offset_fallback"

    rows: list[DrainagePipelineGeometryOutputRow] = []
    for segment in list(segment_rows or []):
        points, mode = _segment_centerline_points(segment, adapter=adapter, coordinate_mode=coordinate_mode, sample_spacing=sample_spacing)
        segment_id = str(getattr(segment, "pipeline_segment_id", "") or "")
        rows.append(
            DrainagePipelineGeometryOutputRow(
                geometry_row_id=f"pipeline-geometry:{_safe_id(segment_id)}",
                pipeline_segment_id=segment_id,
                flow_route_ref=str(getattr(segment, "flow_route_ref", "") or ""),
                geometry_kind="centerline_polyline",
                coordinate_mode=mode,
                centerline_points=points,
                diameter=float(getattr(segment, "diameter", 0.0) or 0.0),
                shape_kind=str(getattr(segment, "shape_kind", "") or ""),
                status="ready" if len(points) >= 2 else "empty",
                notes=(
                    f"point_count={len(points)};"
                    f"station_start={float(getattr(segment, 'station_start', 0.0) or 0.0):.3f};"
                    f"station_end={float(getattr(segment, 'station_end', 0.0) or 0.0):.3f}"
                ),
            )
        )
    return rows


def _segment_centerline_points(
    segment: DrainagePipelineSegmentOutputRow,
    *,
    adapter,
    coordinate_mode: str,
    sample_spacing: float,
) -> tuple[list[tuple[float, float, float]], str]:
    station_start = float(getattr(segment, "station_start", 0.0) or 0.0)
    station_end = float(getattr(segment, "station_end", station_start) or station_start)
    from_offset = float(getattr(segment, "from_offset", 0.0) or 0.0)
    to_offset = float(getattr(segment, "to_offset", from_offset) or from_offset)
    start_x, start_y, baseline_start_z, start_mode = _station_offset_xyz(
        station_start,
        from_offset,
        adapter=adapter,
        coordinate_mode=coordinate_mode,
    )
    end_x, end_y, baseline_end_z, end_mode = _station_offset_xyz(
        station_end,
        to_offset,
        adapter=adapter,
        coordinate_mode=coordinate_mode,
    )
    if start_mode != coordinate_mode:
        coordinate_mode = start_mode
    if end_mode != coordinate_mode:
        coordinate_mode = end_mode
    explicit_start = _optional_float(getattr(segment, "invert_start", None))
    explicit_end = _optional_float(getattr(segment, "invert_end", None))
    invert_start = baseline_start_z if explicit_start is None else explicit_start
    invert_end = baseline_end_z if explicit_end is None else explicit_end
    if _is_structure_connection_segment(segment):
        return [(start_x, start_y, invert_start), (end_x, end_y, invert_end)], coordinate_mode
    stations = _sample_stations(station_start, station_end, sample_spacing)
    points: list[tuple[float, float, float]] = []
    mode = coordinate_mode
    for station in stations:
        ratio = _station_ratio(station, station_start, station_end)
        offset = from_offset + (to_offset - from_offset) * ratio
        x, y, baseline_z, resolved_mode = _station_offset_xyz(station, offset, adapter=adapter, coordinate_mode=coordinate_mode)
        z = baseline_z if explicit_start is None and explicit_end is None else invert_start + (invert_end - invert_start) * ratio
        if resolved_mode != coordinate_mode:
            mode = resolved_mode
        points.append((x, y, z))
    return points, mode


def _is_structure_connection_segment(segment: DrainagePipelineSegmentOutputRow) -> bool:
    return bool(
        str(getattr(segment, "from_connection_point_ref", "") or "").strip()
        and str(getattr(segment, "to_connection_point_ref", "") or "").strip()
    )


def _sample_stations(station_start: float, station_end: float, sample_spacing: float) -> list[float]:
    start = float(station_start)
    end = float(station_end)
    direction = 1.0 if end >= start else -1.0
    span = abs(end - start)
    if span <= 1.0e-9:
        return [start]
    spacing = max(float(sample_spacing or 0.0), 0.1)
    interior_count = max(0, int(span // spacing))
    values = [start]
    for index in range(1, interior_count + 1):
        value = start + direction * spacing * index
        if min(start, end) < value < max(start, end):
            values.append(value)
    values.append(end)
    output: list[float] = []
    seen: set[float] = set()
    for value in values:
        key = round(value, 9)
        if key in seen:
            continue
        seen.add(key)
        output.append(key)
    return output


def _station_ratio(station: float, station_start: float, station_end: float) -> float:
    span = float(station_end) - float(station_start)
    if abs(span) <= 1.0e-12:
        return 0.0
    return min(max((float(station) - float(station_start)) / span, 0.0), 1.0)


def _station_offset_xyz(station: float, offset: float, *, adapter, coordinate_mode: str) -> tuple[float, float, float, str]:
    if adapter is not None:
        try:
            values = adapter(float(station), float(offset))
            x, y = values[0], values[1]
            z = values[2] if len(values) >= 3 else 0.0
            return float(x), float(y), float(z), str(coordinate_mode or "station_offset_adapter")
        except Exception:
            pass
    return float(station), float(offset), 0.0, "station_offset_fallback"


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_id(value: str) -> str:
    return str(value or "").strip().replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "-") or "unknown"
