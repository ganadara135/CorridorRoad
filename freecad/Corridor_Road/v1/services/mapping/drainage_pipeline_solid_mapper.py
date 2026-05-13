"""Drainage pipeline solid output mapping for CorridorRoad v1."""

from __future__ import annotations

from math import pi

from ...models.output.drainage_output import DrainagePipelineGeometryOutputRow, DrainagePipelineSolidOutputRow


def build_drainage_pipeline_solid_rows(
    geometry_rows: list[DrainagePipelineGeometryOutputRow],
) -> list[DrainagePipelineSolidOutputRow]:
    """Build output metadata rows for capped pipe solid candidates."""

    output: list[DrainagePipelineSolidOutputRow] = []
    for row in list(geometry_rows or []):
        points = _points(row)
        length = _polyline_length(points)
        diameter = max(float(getattr(row, "diameter", 0.0) or 0.0), 0.0)
        capped = len(points) >= 2 and diameter > 0.0
        volume = pi * (diameter / 2.0) ** 2 * length if capped else 0.0
        geometry_id = str(getattr(row, "geometry_row_id", "") or "")
        segment_id = str(getattr(row, "pipeline_segment_id", "") or "")
        output.append(
            DrainagePipelineSolidOutputRow(
                solid_row_id=f"pipeline-solid:{_safe_id(segment_id)}",
                pipeline_segment_id=segment_id,
                flow_route_ref=str(getattr(row, "flow_route_ref", "") or ""),
                solid_kind="pipe_solid_candidate",
                station_start=_note_float(getattr(row, "notes", ""), "station_start"),
                station_end=_note_float(getattr(row, "notes", ""), "station_end"),
                length=length,
                diameter=diameter,
                volume=volume,
                cap_count=2 if capped else 0,
                is_capped=capped,
                coordinate_mode=str(getattr(row, "coordinate_mode", "") or "station_offset_fallback"),
                geometry_row_ref=geometry_id,
                status="ready" if capped else "blocked",
                notes=f"geometry_row_ref={geometry_id};point_count={len(points)};shape_kind={str(getattr(row, 'shape_kind', '') or '')}",
            )
        )
    return output


def _points(row: DrainagePipelineGeometryOutputRow) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    for point in list(getattr(row, "centerline_points", []) or []):
        if len(point) < 3:
            continue
        try:
            output.append((float(point[0]), float(point[1]), float(point[2])))
        except Exception:
            continue
    return output


def _polyline_length(points: list[tuple[float, float, float]]) -> float:
    total = 0.0
    for first, second in zip(points, points[1:]):
        total += (
            (second[0] - first[0]) ** 2
            + (second[1] - first[1]) ** 2
            + (second[2] - first[2]) ** 2
        ) ** 0.5
    return total


def _note_float(notes: str, key: str) -> float:
    prefix = str(key or "") + "="
    for token in str(notes or "").split(";"):
        if token.startswith(prefix):
            try:
                return float(token[len(prefix) :])
            except Exception:
                return 0.0
    return 0.0


def _safe_id(value: str) -> str:
    return str(value or "").strip().replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "-") or "unknown"
