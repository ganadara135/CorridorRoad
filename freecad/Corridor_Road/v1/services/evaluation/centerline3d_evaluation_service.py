"""3D Centerline evaluation service for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from ...models.source.alignment_model import AlignmentModel
from ...models.source.profile_model import ProfileModel
from .alignment_evaluation_service import AlignmentEvaluationService
from .profile_evaluation_service import ProfileEvaluationService


@dataclass(frozen=True)
class Centerline3DEvaluationRequest:
    """Inputs needed to evaluate a shared 3D centerline baseline."""

    project_id: str = "corridorroad-v1"
    alignment_model: AlignmentModel | None = None
    profile_model: ProfileModel | None = None
    station_values: tuple[float, ...] = ()
    stationing_id: str = ""
    source_refs: tuple[str, ...] = ()


class Centerline3DEvaluationService:
    """Evaluate Alignment XY and Profile Z over the accepted station grid."""

    CURVE_SAMPLE_MAX_SPACING = 1.0
    MAX_CURVE_SAMPLES_PER_SPAN = 512

    def __init__(self) -> None:
        self._alignment_service = AlignmentEvaluationService()
        self._profile_service = ProfileEvaluationService()

    def evaluate(self, request: Centerline3DEvaluationRequest) -> Centerline3DResult:
        diagnostics: list[str] = []
        alignment = request.alignment_model
        profile = request.profile_model
        source_stations = tuple(float(value) for value in list(request.station_values or ()))
        if alignment is None:
            diagnostics.append("error|missing_alignment|centerline3d_result|AlignmentModel is required.")
        if profile is None:
            diagnostics.append("error|missing_profile|centerline3d_result|ProfileModel is required.")
        if not source_stations:
            diagnostics.append("error|missing_stationing|centerline3d_result|Stationing values are required.")
        if diagnostics:
            return Centerline3DResult(
                project_id=str(request.project_id or "corridorroad-v1"),
                alignment_id=str(getattr(alignment, "alignment_id", "") or ""),
                profile_id=str(getattr(profile, "profile_id", "") or ""),
                stationing_id=str(request.stationing_id or ""),
                diagnostic_rows=tuple(diagnostics),
                status="blocked",
                source_refs=tuple(request.source_refs or ()),
            )

        stations = self._expanded_station_values(source_stations, alignment, profile)
        if len(stations) > len(set(float(value) for value in source_stations)):
            diagnostics.append(
                "info|centerline3d_curve_station_expansion|centerline3d_result|"
                f"Expanded station samples from {len(set(float(value) for value in source_stations))} to {len(stations)} "
                "for curved 3D Centerline evaluation."
            )
        elif _profile_has_internal_pvis(profile):
            diagnostics.append(
                "warning|centerline3d_profile_curve_rows_missing|centerline3d_result|"
                "Profile has internal PVI rows but no usable vertical curve rows were sampled; 3D Centerline may display as broken tangent segments."
            )
        point_rows: list[Centerline3DPointRow] = []
        assert alignment is not None
        assert profile is not None
        for station in stations:
            alignment_result = self._alignment_service.evaluate_station(alignment, station)
            profile_result = self._profile_service.evaluate_station(profile, station)
            row_diagnostics: list[str] = []
            alignment_status = str(getattr(alignment_result, "status", "") or "")
            profile_status = str(getattr(profile_result, "status", "") or "")
            if alignment_status != "ok":
                row_diagnostics.append(f"warning|alignment_station|{station:.3f}|Alignment evaluation status is {alignment_status}.")
            if profile_status != "ok":
                row_diagnostics.append(f"warning|profile_station|{station:.3f}|Profile evaluation status is {profile_status}.")
            diagnostics.extend(row_diagnostics)
            if alignment_status == "ok" and profile_status == "ok":
                point_rows.append(
                    Centerline3DPointRow(
                        station=station,
                        x=float(getattr(alignment_result, "x", 0.0) or 0.0),
                        y=float(getattr(alignment_result, "y", 0.0) or 0.0),
                        z=float(getattr(profile_result, "elevation", 0.0) or 0.0),
                        grade=float(getattr(profile_result, "grade", 0.0) or 0.0),
                        source_alignment_ref=str(getattr(alignment, "alignment_id", "") or ""),
                        source_profile_ref=str(getattr(profile, "profile_id", "") or ""),
                        source_station_ref=str(request.stationing_id or ""),
                        status="ok",
                    )
                )
        status = "ready" if len(point_rows) >= 2 else "blocked"
        if len(point_rows) < 2:
            diagnostics.append("error|not_enough_points|centerline3d_result|At least two evaluated 3D centerline points are required.")
        return Centerline3DResult(
            project_id=str(request.project_id or "corridorroad-v1"),
            alignment_id=str(getattr(alignment, "alignment_id", "") or ""),
            profile_id=str(getattr(profile, "profile_id", "") or ""),
            stationing_id=str(request.stationing_id or ""),
            point_rows=tuple(point_rows),
            diagnostic_rows=tuple(diagnostics),
            status=status,
            source_refs=tuple(value for value in list(request.source_refs or ()) if str(value or "")),
        )

    def _expanded_station_values(
        self,
        source_stations: tuple[float, ...],
        alignment: AlignmentModel | None,
        profile: ProfileModel | None,
    ) -> tuple[float, ...]:
        stations = _unique_stations(source_stations)
        if len(stations) < 2:
            return tuple(stations)
        additions: set[float] = set(stations)
        for index in range(len(stations) - 1):
            start = float(stations[index])
            end = float(stations[index + 1])
            if end <= start:
                continue
            for station in self._profile_curve_sample_stations(start, end, profile):
                additions.add(station)
            if not self._span_needs_curve_sampling(start, end, alignment, profile):
                continue
            span = end - start
            sample_count = min(
                max(1, int(math.ceil(span / self.CURVE_SAMPLE_MAX_SPACING)) - 1),
                self.MAX_CURVE_SAMPLES_PER_SPAN,
            )
            for sample_index in range(1, sample_count + 1):
                additions.add(start + span * (float(sample_index) / float(sample_count + 1)))
        return tuple(_unique_stations(additions))

    def _profile_curve_sample_stations(
        self,
        start: float,
        end: float,
        profile: ProfileModel | None,
    ) -> list[float]:
        if profile is None:
            return []
        output: set[float] = set()
        for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
            curve_start = float(getattr(curve, "station_start", 0.0) or 0.0)
            curve_end = float(getattr(curve, "station_end", 0.0) or 0.0)
            if curve_end < curve_start:
                curve_start, curve_end = curve_end, curve_start
            clipped_start = max(float(start), curve_start)
            clipped_end = min(float(end), curve_end)
            if clipped_end < clipped_start:
                continue
            output.add(clipped_start)
            output.add(clipped_end)
            output.add(0.5 * (clipped_start + clipped_end))
            span = clipped_end - clipped_start
            if span <= 1.0e-9:
                continue
            sample_count = min(
                max(1, int(math.ceil(span / self.CURVE_SAMPLE_MAX_SPACING)) - 1),
                self.MAX_CURVE_SAMPLES_PER_SPAN,
            )
            for sample_index in range(1, sample_count + 1):
                output.add(clipped_start + span * (float(sample_index) / float(sample_count + 1)))
        return sorted(output)

    def _span_needs_curve_sampling(
        self,
        start: float,
        end: float,
        alignment: AlignmentModel | None,
        profile: ProfileModel | None,
    ) -> bool:
        return self._span_overlaps_vertical_curve(start, end, profile) or self._span_overlaps_horizontal_curve(start, end, alignment)

    @staticmethod
    def _span_overlaps_vertical_curve(start: float, end: float, profile: ProfileModel | None) -> bool:
        if profile is None:
            return False
        for curve in list(getattr(profile, "vertical_curve_rows", []) or []):
            curve_start = float(getattr(curve, "station_start", 0.0) or 0.0)
            curve_end = float(getattr(curve, "station_end", 0.0) or 0.0)
            if curve_end < curve_start:
                curve_start, curve_end = curve_end, curve_start
            if curve_end >= float(start) and curve_start <= float(end):
                return True
        return False

    @staticmethod
    def _span_overlaps_horizontal_curve(start: float, end: float, alignment: AlignmentModel | None) -> bool:
        if alignment is None:
            return False
        for element in list(getattr(alignment, "geometry_sequence", []) or []):
            element_start = float(getattr(element, "station_start", 0.0) or 0.0)
            element_end = float(getattr(element, "station_end", 0.0) or 0.0)
            if element_end < element_start:
                element_start, element_end = element_end, element_start
            if element_end < float(start) or element_start > float(end):
                continue
            kind = str(getattr(element, "kind", "") or "").lower()
            payload = getattr(element, "geometry_payload", {}) or {}
            x_values = list(payload.get("x_values", []) or []) if isinstance(payload, dict) else []
            y_values = list(payload.get("y_values", []) or []) if isinstance(payload, dict) else []
            if "curve" in kind or "arc" in kind or min(len(x_values), len(y_values)) > 2:
                return True
        return False


def _unique_stations(values) -> list[float]:
    output: list[float] = []
    seen: set[float] = set()
    for value in list(values or []):
        try:
            station = round(float(value), 9)
        except Exception:
            continue
        if station in seen:
            continue
        seen.add(station)
        output.append(float(value))
    return sorted(output)


def _profile_has_internal_pvis(profile: ProfileModel | None) -> bool:
    if profile is None:
        return False
    controls = sorted(list(getattr(profile, "control_rows", []) or []), key=lambda row: float(getattr(row, "station", 0.0) or 0.0))
    if len(controls) < 3:
        return False
    return not bool(list(getattr(profile, "vertical_curve_rows", []) or []))
