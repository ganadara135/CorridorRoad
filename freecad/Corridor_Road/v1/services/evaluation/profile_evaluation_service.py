"""Profile evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.profile_model import ProfileControlPoint, ProfileModel


@dataclass(frozen=True)
class ProfileStationResult:
    """Minimal station evaluation result for vertical profile."""

    station: float
    elevation: float = 0.0
    active_control_point_id: str = ""
    active_control_kind: str = ""


class ProfileEvaluationService:
    """Evaluate station-based profile context from a profile source model."""

    def evaluate_station(
        self,
        profile: ProfileModel,
        station: float,
    ) -> ProfileStationResult:
        """Resolve the nearest applicable profile control point at a station."""

        control = self._find_active_control(profile.control_rows, station)
        if control is None:
            return ProfileStationResult(station=station)

        return ProfileStationResult(
            station=station,
            elevation=control.elevation,
            active_control_point_id=control.control_point_id,
            active_control_kind=control.kind,
        )

    @staticmethod
    def _find_active_control(
        controls: list[ProfileControlPoint],
        station: float,
    ) -> ProfileControlPoint | None:
        if not controls:
            return None

        ordered_controls = sorted(controls, key=lambda row: row.station)
        active = ordered_controls[0]
        for control in ordered_controls:
            if control.station > station:
                break
            active = control
        return active
