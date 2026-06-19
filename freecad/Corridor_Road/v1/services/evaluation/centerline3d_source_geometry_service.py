"""Source-geometry station resolver for v1 3D Centerline frames."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...models.source.alignment_model import AlignmentModel
from ...models.source.profile_model import ProfileModel
from .alignment_evaluation_service import AlignmentEvaluationService
from .profile_evaluation_service import ProfileEvaluationService


ARC_FIT_ABSOLUTE_TOLERANCE = 0.05
ARC_FIT_RELATIVE_TOLERANCE = 0.001


@dataclass(frozen=True)
class Centerline3DSourceStationResult:
    """Resolved station on Alignment/Profile source geometry."""

    station: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    tangent_direction_deg: float = 0.0
    grade: float = 0.0
    status: str = "not_found"
    source_mode: str = "centerline3d_source_geometry"
    diagnostic_rows: tuple[str, ...] = field(default_factory=tuple)


class Centerline3DSourceGeometryService:
    """Resolve station frames directly from AlignmentModel and ProfileModel source geometry."""

    def __init__(
        self,
        *,
        alignment_service: AlignmentEvaluationService | None = None,
        profile_service: ProfileEvaluationService | None = None,
    ) -> None:
        self.alignment_service = alignment_service or AlignmentEvaluationService()
        self.profile_service = profile_service or ProfileEvaluationService()

    def evaluate_station(
        self,
        alignment: AlignmentModel | None,
        profile: ProfileModel | None,
        station: float,
        *,
        arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
        arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    ) -> Centerline3DSourceStationResult:
        """Return a station frame evaluated from source geometry."""

        active_station = float(station)
        if alignment is None:
            return _blocked_result(active_station, "missing_alignment_source", "AlignmentModel is required.")
        if profile is None:
            return _blocked_result(active_station, "missing_profile_source", "ProfileModel is required.")
        xy = _horizontal_source_point(
            alignment,
            self.alignment_service,
            active_station,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        )
        profile_result = self.profile_service.evaluate_station(profile, active_station)
        if xy is None:
            return _blocked_result(active_station, "alignment_source_not_resolved", "Station could not be resolved from Alignment source geometry.")
        if str(getattr(profile_result, "status", "") or "") != "ok":
            return _blocked_result(active_station, "profile_source_not_resolved", str(getattr(profile_result, "notes", "") or "Station could not be resolved from Profile source geometry."))
        tangent = _horizontal_source_tangent_deg(
            alignment,
            self.alignment_service,
            active_station,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        )
        diagnostics = (
            f"info|centerline3d_source_geometry_frame|{active_station:.3f}|Frame resolved from Alignment/Profile source geometry.",
        )
        return Centerline3DSourceStationResult(
            station=active_station,
            x=float(xy[0]),
            y=float(xy[1]),
            z=float(getattr(profile_result, "elevation", 0.0) or 0.0),
            tangent_direction_deg=float(tangent),
            grade=float(getattr(profile_result, "grade", 0.0) or 0.0),
            status="ok",
            diagnostic_rows=diagnostics,
        )


def _blocked_result(station: float, code: str, message: str) -> Centerline3DSourceStationResult:
    return Centerline3DSourceStationResult(
        station=float(station),
        status="blocked",
        diagnostic_rows=(f"error|{code}|{float(station):.3f}|{message}",),
    )


def _horizontal_source_point(
    alignment,
    alignment_service: AlignmentEvaluationService,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> tuple[float, float] | None:
    arc_xy = _arc_xy_from_source_element(
        alignment,
        station,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    if arc_xy is not None:
        return arc_xy
    result = alignment_service.evaluate_station(alignment, station)
    if str(getattr(result, "status", "") or "") != "ok":
        return None
    return float(getattr(result, "x", 0.0) or 0.0), float(getattr(result, "y", 0.0) or 0.0)


def _horizontal_source_tangent_deg(
    alignment,
    alignment_service: AlignmentEvaluationService,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> float:
    tangent = _arc_tangent_from_source_element(
        alignment,
        station,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    if tangent is not None:
        return tangent
    result = alignment_service.evaluate_station(alignment, station)
    return float(getattr(result, "tangent_direction_deg", 0.0) or 0.0)


def _arc_xy_from_source_element(
    alignment,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> tuple[float, float] | None:
    arc_eval = _arc_eval_from_source_element(
        alignment,
        station,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    if arc_eval is None:
        return None
    center_x, center_y, radius, angle, _sweep_angle = arc_eval
    return center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)


def _arc_tangent_from_source_element(
    alignment,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> float | None:
    arc_eval = _arc_eval_from_source_element(
        alignment,
        station,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    if arc_eval is None:
        return None
    _center_x, _center_y, _radius, angle, sweep_angle = arc_eval
    tangent_angle = angle + (math.pi * 0.5 if float(sweep_angle) >= 0.0 else -math.pi * 0.5)
    return math.degrees(tangent_angle)


def _arc_eval_from_source_element(
    alignment,
    station: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> tuple[float, float, float, float, float] | None:
    element = _active_alignment_element(alignment, station)
    if element is None or not _element_is_curve(element):
        return None
    payload = getattr(element, "geometry_payload", {}) or {}
    if not isinstance(payload, dict):
        return None
    points = list(zip(_numeric_source_values(payload.get("x_values", [])), _numeric_source_values(payload.get("y_values", []))))
    quality = _arc_fit_quality_from_points(
        points,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    if not bool(quality.get("accepted", False)):
        return None
    arc = quality.get("arc")
    if arc is None:
        return None
    center_x, center_y, radius, start_angle, sweep_angle = arc
    station_start = float(getattr(element, "station_start", 0.0) or 0.0)
    station_end = float(getattr(element, "station_end", 0.0) or 0.0)
    span = station_end - station_start
    if abs(span) <= 1.0e-9 or radius <= 1.0e-9:
        return None
    ratio = min(max((float(station) - station_start) / span, 0.0), 1.0)
    angle = start_angle + sweep_angle * ratio
    return center_x, center_y, radius, angle, sweep_angle


def _active_alignment_element(alignment, station: float):
    for element in list(getattr(alignment, "geometry_sequence", []) or []):
        station_start = float(getattr(element, "station_start", 0.0) or 0.0)
        station_end = float(getattr(element, "station_end", 0.0) or 0.0)
        if station_end < station_start:
            station_start, station_end = station_end, station_start
        if station_start - 1.0e-9 <= float(station) <= station_end + 1.0e-9:
            return element
    return None


def _element_is_curve(element) -> bool:
    kind = str(getattr(element, "kind", "") or "").lower()
    payload = getattr(element, "geometry_payload", {}) or {}
    x_values = list(payload.get("x_values", []) or []) if isinstance(payload, dict) else []
    y_values = list(payload.get("y_values", []) or []) if isinstance(payload, dict) else []
    return "curve" in kind or "arc" in kind or min(len(x_values), len(y_values)) > 2


def _arc_fit_quality_from_points(
    points: list[tuple[float, float]],
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> dict[str, object]:
    arc = _fit_plan_arc_from_points(points)
    if arc is None:
        return {"accepted": False, "arc": None, "radial_error": 0.0, "tolerance": 0.0}
    center_x, center_y, radius, _start_angle, _sweep_angle = arc
    radial_error = _arc_fit_max_radial_error(points, center_x, center_y, radius)
    tolerance = _arc_fit_tolerance(
        radius,
        arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
        arc_fit_relative_tolerance=arc_fit_relative_tolerance,
    )
    return {
        "accepted": radial_error <= tolerance,
        "arc": arc,
        "radial_error": radial_error,
        "tolerance": tolerance,
    }


def _fit_plan_arc_from_points(points: list[tuple[float, float]]) -> tuple[float, float, float, float, float] | None:
    clean = _clean_xy_pairs(points)
    if len(clean) < 3:
        return None
    first = clean[0]
    last = clean[-1]
    middle = max(clean[1:-1], key=lambda point: _point_line_distance(point, first, last))
    center = _circle_center_from_three_points(first, middle, last)
    if center is None:
        return None
    center_x, center_y = center
    radius = _distance2d(center_x, center_y, first[0], first[1])
    if radius <= 1.0e-9:
        return None
    start_angle = math.atan2(first[1] - center_y, first[0] - center_x)
    middle_angle = math.atan2(middle[1] - center_y, middle[0] - center_x)
    end_angle = math.atan2(last[1] - center_y, last[0] - center_x)
    ccw_total = _positive_angle_delta(start_angle, end_angle)
    ccw_mid = _positive_angle_delta(start_angle, middle_angle)
    sweep = ccw_total if ccw_mid <= ccw_total + 1.0e-9 else -_positive_angle_delta(end_angle, start_angle)
    if abs(sweep) <= 1.0e-9:
        return None
    return center_x, center_y, radius, start_angle, sweep


def _circle_center_from_three_points(
    first: tuple[float, float],
    middle: tuple[float, float],
    last: tuple[float, float],
) -> tuple[float, float] | None:
    ax, ay = first
    bx, by = middle
    cx, cy = last
    determinant = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(determinant) <= 1.0e-9:
        return None
    a_sq = ax * ax + ay * ay
    b_sq = bx * bx + by * by
    c_sq = cx * cx + cy * cy
    center_x = (a_sq * (by - cy) + b_sq * (cy - ay) + c_sq * (ay - by)) / determinant
    center_y = (a_sq * (cx - bx) + b_sq * (ax - cx) + c_sq * (bx - ax)) / determinant
    return center_x, center_y


def _positive_angle_delta(start: float, end: float) -> float:
    return (float(end) - float(start)) % (2.0 * math.pi)


def _point_line_distance(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    denominator = math.hypot(dx, dy)
    if denominator <= 1.0e-12:
        return _distance2d(px, py, ax, ay)
    return abs(dy * px - dx * py + bx * ay - by * ax) / denominator


def _clean_xy_pairs(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    clean = []
    previous_key = None
    for x, y in list(points or []):
        key = (round(float(x), 9), round(float(y), 9))
        if key == previous_key:
            continue
        clean.append((float(x), float(y)))
        previous_key = key
    return clean


def _numeric_source_values(values) -> list[float]:
    output = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            continue
    return output


def _distance2d(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.hypot(float(x1) - float(x0), float(y1) - float(y0))


def _arc_fit_max_radial_error(points: list[tuple[float, float]], center_x: float, center_y: float, radius: float) -> float:
    errors = [abs(_distance2d(center_x, center_y, float(x), float(y)) - float(radius)) for x, y in _clean_xy_pairs(points)]
    return max(errors) if errors else 0.0


def _arc_fit_tolerance(
    radius: float,
    *,
    arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
    arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
) -> float:
    absolute, relative = _normalized_arc_fit_tolerances(arc_fit_absolute_tolerance, arc_fit_relative_tolerance)
    return max(absolute, abs(float(radius)) * relative)


def _normalized_arc_fit_tolerances(absolute: float, relative: float) -> tuple[float, float]:
    try:
        absolute_value = max(0.0, float(absolute))
    except Exception:
        absolute_value = float(ARC_FIT_ABSOLUTE_TOLERANCE)
    try:
        relative_value = max(0.0, float(relative))
    except Exception:
        relative_value = float(ARC_FIT_RELATIVE_TOLERANCE)
    return absolute_value, relative_value
