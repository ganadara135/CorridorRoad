"""Profile evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
    VerticalCurveRow,
)


@dataclass(frozen=True)
class ProfileStationResult:
    """Minimal station evaluation result for vertical profile."""

    station: float
    elevation: float = 0.0
    grade: float = 0.0
    active_control_point_id: str = ""
    active_control_kind: str = ""
    active_segment_start_id: str = ""
    active_segment_end_id: str = ""
    active_vertical_curve_id: str = ""
    offset_on_segment: float = 0.0
    status: str = "not_found"
    notes: str = ""


class ProfileEvaluationService:
    """Evaluate station-based profile context from a profile source model."""

    def evaluate_station(
        self,
        profile: ProfileModel,
        station: float,
    ) -> ProfileStationResult:
        """Resolve finished-grade elevation and grade at a station."""

        ordered_controls = self._ordered_controls(profile.control_rows)
        if not ordered_controls:
            return ProfileStationResult(
                station=station,
                status="no_controls",
                notes="ProfileModel has no control rows.",
            )

        if len(ordered_controls) == 1:
            return self._single_control_result(ordered_controls[0], station)

        if station < ordered_controls[0].station:
            return self._out_of_range_result(
                ordered_controls[0],
                station,
                notes="Station is before the first profile control point.",
            )
        if station > ordered_controls[-1].station:
            return self._out_of_range_result(
                ordered_controls[-1],
                station,
                notes="Station is after the last profile control point.",
            )

        left, right = self._find_active_segment(ordered_controls, station)
        if left is None or right is None:
            return ProfileStationResult(
                station=station,
                status="not_found",
                notes="Station could not be matched to a profile control segment.",
            )

        delta_station = float(right.station) - float(left.station)
        if abs(delta_station) <= 1e-12:
            return ProfileStationResult(
                station=station,
                elevation=float(left.elevation),
                active_control_point_id=left.control_point_id,
                active_control_kind=left.kind,
                status="duplicate_station",
                notes="Profile segment has duplicate station values.",
            )

        active_curve = self._active_vertical_curve(profile.vertical_curve_rows, station)
        curve_result = self._parabolic_vertical_curve_result(
            ordered_controls,
            active_curve,
            station,
        )
        if curve_result is None:
            ratio = (float(station) - float(left.station)) / delta_station
            elevation = float(left.elevation) + (float(right.elevation) - float(left.elevation)) * ratio
            grade = (float(right.elevation) - float(left.elevation)) / delta_station
            notes = "Station resolved by linear interpolation between profile control points."
            if active_curve is not None:
                notes += " Active vertical-curve metadata is attached, but parabolic evaluation was unavailable."
        else:
            elevation, grade, curve_notes = curve_result
            notes = curve_notes
        return ProfileStationResult(
            station=station,
            elevation=elevation,
            grade=grade,
            active_control_point_id=left.control_point_id,
            active_control_kind=left.kind,
            active_segment_start_id=left.control_point_id,
            active_segment_end_id=right.control_point_id,
            active_vertical_curve_id=getattr(active_curve, "vertical_curve_id", "") if active_curve is not None else "",
            offset_on_segment=float(station) - float(left.station),
            status="ok",
            notes=notes,
        )

    @staticmethod
    def _ordered_controls(
        controls: list[ProfileControlPoint],
    ) -> list[ProfileControlPoint]:
        return sorted(list(controls or []), key=lambda row: row.station)

    def _single_control_result(
        self,
        control: ProfileControlPoint,
        station: float,
    ) -> ProfileStationResult:
        status = "ok" if abs(float(station) - float(control.station)) <= 1e-9 else "out_of_range"
        notes = (
            "Station matches the only profile control point."
            if status == "ok"
            else "ProfileModel has only one control point; station interpolation is unavailable."
        )
        return ProfileStationResult(
            station=station,
            elevation=float(control.elevation),
            grade=0.0,
            active_control_point_id=control.control_point_id,
            active_control_kind=control.kind,
            offset_on_segment=0.0,
            status=status,
            notes=notes,
        )

    @staticmethod
    def _out_of_range_result(
        nearest_control: ProfileControlPoint,
        station: float,
        *,
        notes: str,
    ) -> ProfileStationResult:
        return ProfileStationResult(
            station=station,
            elevation=float(nearest_control.elevation),
            active_control_point_id=nearest_control.control_point_id,
            active_control_kind=nearest_control.kind,
            status="out_of_range",
            notes=notes,
        )

    @staticmethod
    def _find_active_segment(
        ordered_controls: list[ProfileControlPoint],
        station: float,
    ) -> tuple[ProfileControlPoint | None, ProfileControlPoint | None]:
        for left, right in zip(ordered_controls, ordered_controls[1:]):
            if left.station <= station <= right.station:
                return left, right
        return None, None

    @staticmethod
    def _active_vertical_curve(
        curve_rows: list[VerticalCurveRow],
        station: float,
    ) -> VerticalCurveRow | None:
        for row in list(curve_rows or []):
            if float(row.station_start) <= float(station) <= float(row.station_end):
                return row
        return None

    def _parabolic_vertical_curve_result(
        self,
        ordered_controls: list[ProfileControlPoint],
        curve: VerticalCurveRow | None,
        station: float,
    ) -> tuple[float, float, str] | None:
        """Evaluate a symmetric parabolic vertical curve when its PVI is known."""

        if curve is None:
            return None
        if "parabolic" not in str(getattr(curve, "kind", "") or "").lower():
            return None

        station_start = float(curve.station_start)
        station_end = float(curve.station_end)
        if station_end < station_start:
            station_start, station_end = station_end, station_start
        curve_length = station_end - station_start
        if curve_length <= 1e-12:
            return None

        pvi_index = self._curve_pvi_index(ordered_controls, station_start, station_end)
        if pvi_index is None:
            return None
        previous_control = ordered_controls[pvi_index - 1]
        pvi_control = ordered_controls[pvi_index]
        next_control = ordered_controls[pvi_index + 1]

        grade_in = self._incoming_grade(previous_control, pvi_control)
        grade_out = self._outgoing_grade(pvi_control, next_control)
        if grade_in is None or grade_out is None:
            return None

        x = float(station) - station_start
        bvc_elevation = float(pvi_control.elevation) - grade_in * (float(pvi_control.station) - station_start)
        algebraic_grade_change = grade_out - grade_in
        elevation = bvc_elevation + grade_in * x + (algebraic_grade_change / (2.0 * curve_length)) * (x * x)
        grade = grade_in + (algebraic_grade_change / curve_length) * x
        notes = (
            "Station resolved by parabolic vertical-curve evaluation "
            "using incoming and outgoing PVI tangent grades."
        )
        return elevation, grade, notes

    @staticmethod
    def _curve_pvi_index(
        ordered_controls: list[ProfileControlPoint],
        station_start: float,
        station_end: float,
    ) -> int | None:
        center_station = 0.5 * (float(station_start) + float(station_end))
        if len(ordered_controls) < 3:
            return None
        best_index = min(
            range(len(ordered_controls)),
            key=lambda index: abs(float(ordered_controls[index].station) - center_station),
        )
        tolerance = max(1e-6, abs(station_end - station_start) * 1e-6)
        if abs(float(ordered_controls[best_index].station) - center_station) > tolerance:
            return None
        if best_index <= 0 or best_index >= len(ordered_controls) - 1:
            return None
        return best_index

    @staticmethod
    def _incoming_grade(
        previous_control: ProfileControlPoint,
        pvi_control: ProfileControlPoint,
    ) -> float | None:
        if pvi_control.grade_in is not None:
            return float(pvi_control.grade_in)
        delta_station = float(pvi_control.station) - float(previous_control.station)
        if abs(delta_station) <= 1e-12:
            return None
        return (float(pvi_control.elevation) - float(previous_control.elevation)) / delta_station

    @staticmethod
    def _outgoing_grade(
        pvi_control: ProfileControlPoint,
        next_control: ProfileControlPoint,
    ) -> float | None:
        if pvi_control.grade_out is not None:
            return float(pvi_control.grade_out)
        delta_station = float(next_control.station) - float(pvi_control.station)
        if abs(delta_station) <= 1e-12:
            return None
        return (float(next_control.elevation) - float(pvi_control.elevation)) / delta_station
