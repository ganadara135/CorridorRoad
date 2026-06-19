"""Profile curve preview evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...common.diagnostics import DiagnosticMessage
from ...models.result.profile_curve_preview import (
    ProfileCurvePreviewAnnotationRow,
    ProfileCurvePreviewCurveRow,
    ProfileCurvePreviewPointRow,
    ProfileCurvePreviewResult,
)
from ...models.source.profile_model import ProfileControlPoint, ProfileModel, VerticalCurveRow
from .profile_evaluation_service import ProfileEvaluationService


@dataclass(frozen=True)
class ProfileCurvePreviewRequest:
    """Inputs for read-only Profile curve preview evaluation."""

    profile: ProfileModel | None = None
    sample_interval: float = 5.0


class ProfileCurvePreviewService:
    """Build preview rows for Profile panel curve review."""

    def __init__(self, *, profile_service: ProfileEvaluationService | None = None) -> None:
        self.profile_service = profile_service or ProfileEvaluationService()

    def evaluate(self, request: ProfileCurvePreviewRequest) -> ProfileCurvePreviewResult:
        profile = request.profile
        interval = max(float(getattr(request, "sample_interval", 5.0) or 5.0), 0.1)
        if profile is None:
            return ProfileCurvePreviewResult(
                schema_version=1,
                project_id="corridorroad-v1",
                status="blocked",
                diagnostic_rows=[
                    DiagnosticMessage("error", "profile_curve_preview_missing_profile", "ProfileModel is required.")
                ],
            )
        controls = _ordered_controls(profile)
        if len(controls) < 2:
            return ProfileCurvePreviewResult(
                schema_version=1,
                project_id=str(getattr(profile, "project_id", "") or "corridorroad-v1"),
                profile_id=str(getattr(profile, "profile_id", "") or ""),
                status="blocked",
                source_refs=list(getattr(profile, "source_refs", []) or []),
                diagnostic_rows=[
                    DiagnosticMessage(
                        "error",
                        "profile_curve_preview_not_enough_controls",
                        "At least two profile control rows are required.",
                    )
                ],
            )

        start = float(controls[0].station)
        end = float(controls[-1].station)
        stations = _preview_station_values(profile, interval)
        point_rows = self._point_rows(profile, controls, stations)
        curve_rows: list[ProfileCurvePreviewCurveRow] = []
        annotation_rows: list[ProfileCurvePreviewAnnotationRow] = []
        diagnostics: list[DiagnosticMessage] = [
            DiagnosticMessage("info", "profile_curve_preview_ok", "Profile curve preview was evaluated.")
        ]

        for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
            curve_row, curve_annotations, curve_diagnostics = self._curve_preview_rows(profile, controls, curve, interval)
            curve_rows.append(curve_row)
            annotation_rows.extend(curve_annotations)
            diagnostics.extend(curve_diagnostics)

        if not curve_rows:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "profile_vertical_curve_linear_fallback",
                    "No vertical curve rows were found; preview shows source tangent interpolation only.",
                )
            )

        return ProfileCurvePreviewResult(
            schema_version=1,
            project_id=str(getattr(profile, "project_id", "") or "corridorroad-v1"),
            profile_id=str(getattr(profile, "profile_id", "") or ""),
            station_start=start,
            station_end=end,
            sample_interval=interval,
            status="ready",
            point_rows=point_rows,
            annotation_rows=annotation_rows,
            curve_rows=curve_rows,
            source_refs=list(getattr(profile, "source_refs", []) or []),
            diagnostic_rows=diagnostics,
        )

    def _point_rows(
        self,
        profile: ProfileModel,
        controls: list[ProfileControlPoint],
        stations: list[float],
    ) -> list[ProfileCurvePreviewPointRow]:
        output: list[ProfileCurvePreviewPointRow] = []
        for index, station in enumerate(stations, start=1):
            result = self.profile_service.evaluate_station(profile, station)
            if str(getattr(result, "status", "") or "") not in {"ok", "warning"}:
                continue
            output.append(
                ProfileCurvePreviewPointRow(
                    point_id=f"profile-preview:evaluated:{index}",
                    station=float(station),
                    elevation=float(getattr(result, "elevation", 0.0) or 0.0),
                    grade=float(getattr(result, "grade", 0.0) or 0.0),
                    role="evaluated_curve",
                    curve_ref=str(getattr(result, "active_vertical_curve_id", "") or ""),
                    source_ref=str(getattr(profile, "profile_id", "") or ""),
                    notes=str(getattr(result, "notes", "") or ""),
                )
            )
            tangent_elevation, tangent_grade = _linear_control_elevation(controls, station)
            output.append(
                ProfileCurvePreviewPointRow(
                    point_id=f"profile-preview:tangent:{index}",
                    station=float(station),
                    elevation=tangent_elevation,
                    grade=tangent_grade,
                    role="source_tangent",
                    source_ref=str(getattr(profile, "profile_id", "") or ""),
                    notes="Source PVI tangent/chord elevation.",
                )
            )
        return output

    def _curve_preview_rows(
        self,
        profile: ProfileModel,
        controls: list[ProfileControlPoint],
        curve: VerticalCurveRow,
        interval: float,
    ) -> tuple[ProfileCurvePreviewCurveRow, list[ProfileCurvePreviewAnnotationRow], list[DiagnosticMessage]]:
        curve_id = str(getattr(curve, "vertical_curve_id", "") or "vertical-curve")
        curve_start, curve_end = _curve_station_range(curve)
        pvi = _pvi_control_for_curve(controls, curve_start, curve_end)
        curve_start, curve_end = _effective_symmetric_curve_range(curve_start, curve_end, pvi)
        length = max(float(curve_end) - float(curve_start), 0.0)
        bvc = self.profile_service.evaluate_station(profile, curve_start)
        evc = self.profile_service.evaluate_station(profile, curve_end)
        mid_station = 0.5 * (curve_start + curve_end)
        mid = self.profile_service.evaluate_station(profile, mid_station)
        grade_in = float(getattr(bvc, "grade", 0.0) or 0.0)
        grade_out = float(getattr(evc, "grade", 0.0) or 0.0)
        algebraic = grade_out - grade_in
        k_value = length / abs(algebraic) if abs(algebraic) > 1.0e-12 else 0.0
        high_low_kind, high_low_station, high_low_elevation = self._high_low_point(profile, curve_start, curve_end, grade_in, algebraic)
        max_deviation = self._max_chord_deviation(profile, curve_start, curve_end, interval)
        mid_notes = str(getattr(mid, "notes", "") or "").lower()
        parabolic = mid_notes.startswith("station resolved by parabolic vertical-curve evaluation")
        status = "ok" if parabolic and pvi is not None else "warning"
        notes = "Parabolic vertical curve evaluated." if parabolic else "Vertical curve fell back to linear interpolation."

        curve_row = ProfileCurvePreviewCurveRow(
            curve_id=curve_id,
            kind=str(getattr(curve, "kind", "") or ""),
            station_start=curve_start,
            station_end=curve_end,
            length=length,
            bvc_station=curve_start,
            bvc_elevation=float(getattr(bvc, "elevation", 0.0) or 0.0),
            pvi_station=float(getattr(pvi, "station", mid_station) if pvi is not None else mid_station),
            pvi_elevation=float(getattr(pvi, "elevation", getattr(mid, "elevation", 0.0)) if pvi is not None else getattr(mid, "elevation", 0.0)),
            evc_station=curve_end,
            evc_elevation=float(getattr(evc, "elevation", 0.0) or 0.0),
            grade_in=grade_in,
            grade_out=grade_out,
            algebraic_grade_difference=algebraic,
            k_value=k_value,
            high_low_kind=high_low_kind,
            high_low_station=high_low_station,
            high_low_elevation=high_low_elevation,
            max_chord_deviation=max_deviation,
            status=status,
            notes=notes,
        )
        annotations = _profile_curve_annotations(curve_row)
        diagnostics = [
            DiagnosticMessage("info", "profile_vertical_curve_bvc_evc_labeled", f"BVC/EVC labels resolved for {curve_id}.")
        ]
        if parabolic:
            diagnostics.append(
                DiagnosticMessage("info", "profile_vertical_curve_parabolic_evaluated", f"Vertical curve {curve_id} was evaluated as parabolic.")
            )
        else:
            diagnostics.append(
                DiagnosticMessage("warning", "profile_vertical_curve_linear_fallback", f"Vertical curve {curve_id} fell back to linear interpolation.")
            )
        if pvi is None:
            diagnostics.append(
                DiagnosticMessage("warning", "profile_vertical_curve_missing_pvi", f"Vertical curve {curve_id} has no usable PVI control.")
            )
        if high_low_kind:
            diagnostics.append(
                DiagnosticMessage("info", "profile_vertical_curve_high_low_point", f"{high_low_kind} point resolved for {curve_id}.")
            )
        elif abs(algebraic) > 1.0e-12:
            diagnostics.append(
                DiagnosticMessage("warning", "profile_vertical_curve_high_low_point_outside", f"Computed high/low point falls outside {curve_id}.")
            )
        return curve_row, annotations, diagnostics

    def _high_low_point(
        self,
        profile: ProfileModel,
        curve_start: float,
        curve_end: float,
        grade_in: float,
        algebraic_grade_difference: float,
    ) -> tuple[str, float, float]:
        length = curve_end - curve_start
        if length <= 1.0e-12 or abs(algebraic_grade_difference) <= 1.0e-12:
            return "", 0.0, 0.0
        x = -float(grade_in) * length / float(algebraic_grade_difference)
        station = curve_start + x
        if station < curve_start - 1.0e-9 or station > curve_end + 1.0e-9:
            return "", 0.0, 0.0
        result = self.profile_service.evaluate_station(profile, station)
        kind = "LP" if algebraic_grade_difference > 0.0 else "HP"
        return kind, station, float(getattr(result, "elevation", 0.0) or 0.0)

    def _max_chord_deviation(self, profile: ProfileModel, curve_start: float, curve_end: float, interval: float) -> float:
        start = self.profile_service.evaluate_station(profile, curve_start)
        end = self.profile_service.evaluate_station(profile, curve_end)
        start_z = float(getattr(start, "elevation", 0.0) or 0.0)
        end_z = float(getattr(end, "elevation", 0.0) or 0.0)
        span = curve_end - curve_start
        if span <= 1.0e-12:
            return 0.0
        max_deviation = 0.0
        for station in _station_range(curve_start, curve_end, interval):
            ratio = (station - curve_start) / span
            chord_z = start_z + (end_z - start_z) * ratio
            result = self.profile_service.evaluate_station(profile, station)
            max_deviation = max(max_deviation, abs(float(getattr(result, "elevation", 0.0) or 0.0) - chord_z))
        return max_deviation


def _profile_curve_annotations(curve: ProfileCurvePreviewCurveRow) -> list[ProfileCurvePreviewAnnotationRow]:
    curve_id = curve.curve_id
    rows = [
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:bvc", "BVC", "BVC", curve.bvc_station, curve.bvc_elevation, curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:pvi", "PVI", "PVI", curve.pvi_station, curve.pvi_elevation, curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:evc", "EVC", "EVC", curve.evc_station, curve.evc_elevation, curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:length", "L", "L", curve.pvi_station, curve.pvi_elevation, value=f"{curve.length:.3f}", curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:g1", "g1", "g1", curve.bvc_station, curve.bvc_elevation, value=f"{curve.grade_in:.6f}", curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:g2", "g2", "g2", curve.evc_station, curve.evc_elevation, value=f"{curve.grade_out:.6f}", curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:a", "A", "A", curve.pvi_station, curve.pvi_elevation, value=f"{curve.algebraic_grade_difference:.6f}", curve_ref=curve_id),
        ProfileCurvePreviewAnnotationRow(f"{curve_id}:max-deviation", "Max deviation", "Max deviation", curve.pvi_station, curve.pvi_elevation, value=f"{curve.max_chord_deviation:.3f}", curve_ref=curve_id),
    ]
    if curve.k_value > 0.0:
        rows.append(
            ProfileCurvePreviewAnnotationRow(f"{curve_id}:k", "K", "K", curve.pvi_station, curve.pvi_elevation, value=f"{curve.k_value:.3f}", curve_ref=curve_id)
        )
    if curve.high_low_kind:
        rows.append(
            ProfileCurvePreviewAnnotationRow(
                f"{curve_id}:high-low",
                curve.high_low_kind,
                curve.high_low_kind,
                curve.high_low_station,
                curve.high_low_elevation,
                curve_ref=curve_id,
            )
        )
    return rows


def _preview_station_values(profile: ProfileModel, interval: float) -> list[float]:
    controls = _ordered_controls(profile)
    if len(controls) < 2:
        return []
    stations: set[float] = set()
    start = float(controls[0].station)
    end = float(controls[-1].station)
    for station in _station_range(start, end, interval):
        stations.add(station)
    for control in controls:
        stations.add(float(control.station))
    for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
        curve_start, curve_end = _curve_station_range(curve)
        stations.update(_station_range(curve_start, curve_end, interval))
        stations.add(curve_start)
        stations.add(0.5 * (curve_start + curve_end))
        stations.add(curve_end)
    return sorted(stations)


def _station_range(start: float, end: float, interval: float) -> list[float]:
    if end < start:
        start, end = end, start
    output = [float(start)]
    span = float(end) - float(start)
    if span <= 1.0e-12:
        return output
    count = max(1, int(math.ceil(span / max(float(interval), 0.1))))
    for index in range(1, count):
        output.append(float(start) + span * (float(index) / float(count)))
    output.append(float(end))
    return sorted({round(value, 9): value for value in output}.values())


def _curve_station_range(curve: VerticalCurveRow) -> tuple[float, float]:
    start = float(getattr(curve, "station_start", 0.0) or 0.0)
    end = float(getattr(curve, "station_end", 0.0) or 0.0)
    return (start, end) if start <= end else (end, start)


def _effective_symmetric_curve_range(
    curve_start: float,
    curve_end: float,
    pvi: ProfileControlPoint | None,
) -> tuple[float, float]:
    if pvi is None:
        return curve_start, curve_end
    length = abs(float(curve_end) - float(curve_start))
    center = float(getattr(pvi, "station", 0.0) or 0.0)
    half = 0.5 * length
    return center - half, center + half


def _ordered_controls(profile: ProfileModel) -> list[ProfileControlPoint]:
    return sorted(list(getattr(profile, "control_rows", []) or []), key=lambda row: float(getattr(row, "station", 0.0) or 0.0))


def _pvi_control_for_curve(controls: list[ProfileControlPoint], curve_start: float, curve_end: float) -> ProfileControlPoint | None:
    candidates = [
        control
        for control in controls
        if curve_start + 1.0e-6 < float(control.station) < curve_end - 1.0e-6
    ]
    if not candidates:
        return None
    pvis = [control for control in candidates if "pvi" in str(getattr(control, "kind", "") or "").lower()]
    search = pvis or candidates
    center = 0.5 * (curve_start + curve_end)
    return min(search, key=lambda control: abs(float(control.station) - center))


def _linear_control_elevation(controls: list[ProfileControlPoint], station: float) -> tuple[float, float]:
    if not controls:
        return 0.0, 0.0
    if station <= float(controls[0].station):
        return float(controls[0].elevation), 0.0
    if station >= float(controls[-1].station):
        return float(controls[-1].elevation), 0.0
    for left, right in zip(controls, controls[1:]):
        if float(left.station) <= float(station) <= float(right.station):
            span = float(right.station) - float(left.station)
            if abs(span) <= 1.0e-12:
                return float(left.elevation), 0.0
            ratio = (float(station) - float(left.station)) / span
            grade = (float(right.elevation) - float(left.elevation)) / span
            return float(left.elevation) + (float(right.elevation) - float(left.elevation)) * ratio, grade
    return float(controls[-1].elevation), 0.0
