"""Detect station mappings between two v1 Alignment centerlines."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.alignment_model import AlignmentModel


@dataclass(frozen=True)
class AlignmentIntersectionDetectionResult:
    """Detected XY and station relationship between two Alignments."""

    status: str
    primary_alignment_ref: str = ""
    secondary_alignment_ref: str = ""
    x: float = 0.0
    y: float = 0.0
    primary_station: float = 0.0
    secondary_station: float = 0.0
    distance: float = 0.0
    notes: str = ""


@dataclass(frozen=True)
class _Segment:
    x0: float
    y0: float
    sta0: float
    x1: float
    y1: float
    sta1: float


class AlignmentIntersectionDetectionService:
    """Detect crossing or nearest approach between two sampled Alignment paths."""

    def detect(
        self,
        primary_alignment: AlignmentModel,
        secondary_alignment: AlignmentModel,
    ) -> AlignmentIntersectionDetectionResult:
        """Return intersection station mapping for two Alignment models."""

        primary_segments = _alignment_segments(primary_alignment)
        secondary_segments = _alignment_segments(secondary_alignment)
        primary_ref = str(getattr(primary_alignment, "alignment_id", "") or "")
        secondary_ref = str(getattr(secondary_alignment, "alignment_id", "") or "")
        if not primary_segments or not secondary_segments:
            return AlignmentIntersectionDetectionResult(
                status="error",
                primary_alignment_ref=primary_ref,
                secondary_alignment_ref=secondary_ref,
                notes="Both Alignments must contain usable sampled XY geometry.",
            )

        for primary in primary_segments:
            for secondary in secondary_segments:
                intersection = _segment_intersection(primary, secondary)
                if intersection is None:
                    continue
                x, y, primary_t, secondary_t = intersection
                return AlignmentIntersectionDetectionResult(
                    status="intersection",
                    primary_alignment_ref=primary_ref,
                    secondary_alignment_ref=secondary_ref,
                    x=x,
                    y=y,
                    primary_station=_station_at_t(primary, primary_t),
                    secondary_station=_station_at_t(secondary, secondary_t),
                    distance=0.0,
                    notes="Alignment paths cross in plan view.",
                )

        nearest = None
        for primary in primary_segments:
            for secondary in secondary_segments:
                candidate = _nearest_segment_pair(primary, secondary)
                if nearest is None or candidate[-1] < nearest[-1]:
                    nearest = candidate
        if nearest is None:
            return AlignmentIntersectionDetectionResult(
                status="error",
                primary_alignment_ref=primary_ref,
                secondary_alignment_ref=secondary_ref,
                notes="No segment pair could be compared.",
            )

        primary_x, primary_y, primary_t, secondary_x, secondary_y, secondary_t, distance = nearest
        return AlignmentIntersectionDetectionResult(
            status="nearest",
            primary_alignment_ref=primary_ref,
            secondary_alignment_ref=secondary_ref,
            x=(primary_x + secondary_x) * 0.5,
            y=(primary_y + secondary_y) * 0.5,
            primary_station=_station_at_t(primary, primary_t),
            secondary_station=_station_at_t(secondary, secondary_t),
            distance=distance,
            notes="Alignment paths do not cross; nearest approach was detected.",
        )


def _alignment_segments(alignment: AlignmentModel) -> list[_Segment]:
    segments: list[_Segment] = []
    for element in list(getattr(alignment, "geometry_sequence", []) or []):
        x_values = _numeric_values(element.geometry_payload.get("x_values", []))
        y_values = _numeric_values(element.geometry_payload.get("y_values", []))
        points = list(zip(x_values, y_values))
        if len(points) < 2:
            continue
        distances = [0.0]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            distances.append(distances[-1] + _distance(x0, y0, x1, y1))
        geometry_length = distances[-1]
        station_start = float(element.station_start)
        station_end = float(element.station_end)
        station_span = station_end - station_start
        for index, ((x0, y0), (x1, y1)) in enumerate(zip(points, points[1:])):
            if _distance(x0, y0, x1, y1) <= 1.0e-12:
                continue
            if geometry_length > 1.0e-12:
                sta0 = station_start + station_span * (distances[index] / geometry_length)
                sta1 = station_start + station_span * (distances[index + 1] / geometry_length)
            else:
                ratio0 = index / max(len(points) - 1, 1)
                ratio1 = (index + 1) / max(len(points) - 1, 1)
                sta0 = station_start + station_span * ratio0
                sta1 = station_start + station_span * ratio1
            segments.append(_Segment(float(x0), float(y0), float(sta0), float(x1), float(y1), float(sta1)))
    return segments


def _segment_intersection(a: _Segment, b: _Segment) -> tuple[float, float, float, float] | None:
    ax = a.x1 - a.x0
    ay = a.y1 - a.y0
    bx = b.x1 - b.x0
    by = b.y1 - b.y0
    den = ax * by - ay * bx
    if abs(den) <= 1.0e-12:
        return None
    dx = b.x0 - a.x0
    dy = b.y0 - a.y0
    t = (dx * by - dy * bx) / den
    u = (dx * ay - dy * ax) / den
    if -1.0e-9 <= t <= 1.0 + 1.0e-9 and -1.0e-9 <= u <= 1.0 + 1.0e-9:
        t = min(max(t, 0.0), 1.0)
        u = min(max(u, 0.0), 1.0)
        return a.x0 + ax * t, a.y0 + ay * t, t, u
    return None


def _nearest_segment_pair(a: _Segment, b: _Segment) -> tuple[float, float, float, float, float, float, float]:
    candidates = [
        (*_project_point_to_segment(a.x0, a.y0, b), a.x0, a.y0, 0.0, "b"),
        (*_project_point_to_segment(a.x1, a.y1, b), a.x1, a.y1, 1.0, "b"),
        (*_project_point_to_segment(b.x0, b.y0, a), b.x0, b.y0, 0.0, "a"),
        (*_project_point_to_segment(b.x1, b.y1, a), b.x1, b.y1, 1.0, "a"),
    ]
    best = min(candidates, key=lambda row: row[3])
    proj_x, proj_y, proj_t, dist, point_x, point_y, point_t, owner = best
    if owner == "b":
        return point_x, point_y, point_t, proj_x, proj_y, proj_t, dist
    return proj_x, proj_y, proj_t, point_x, point_y, point_t, dist


def _project_point_to_segment(x: float, y: float, segment: _Segment) -> tuple[float, float, float, float]:
    dx = segment.x1 - segment.x0
    dy = segment.y1 - segment.y0
    length_sq = dx * dx + dy * dy
    if length_sq <= 1.0e-12:
        return segment.x0, segment.y0, 0.0, _distance(x, y, segment.x0, segment.y0)
    t = ((x - segment.x0) * dx + (y - segment.y0) * dy) / length_sq
    t = min(max(t, 0.0), 1.0)
    px = segment.x0 + dx * t
    py = segment.y0 + dy * t
    return px, py, t, _distance(x, y, px, py)


def _station_at_t(segment: _Segment, t: float) -> float:
    return float(segment.sta0) + (float(segment.sta1) - float(segment.sta0)) * min(max(float(t), 0.0), 1.0)


def _numeric_values(values) -> list[float]:
    rows: list[float] = []
    for value in list(values or []):
        try:
            rows.append(float(value))
        except Exception:
            continue
    return rows


def _distance(x0: float, y0: float, x1: float, y1: float) -> float:
    return ((float(x1) - float(x0)) ** 2 + (float(y1) - float(y0)) ** 2) ** 0.5
