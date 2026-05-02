"""Ramp evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.ramp_model import RampModel, RampRow


@dataclass(frozen=True)
class RampEvaluationResult:
    """Minimal resolved ramp context for a station."""

    station: float
    active_ramp_id: str = ""
    active_ramp_kind: str = ""
    parent_alignment_ref: str = ""
    intersection_ref: str = ""


class RampEvaluationService:
    """Resolve ramp context rows from a ramp source model."""

    def resolve_station(
        self,
        ramp_model: RampModel,
        station: float,
    ) -> RampEvaluationResult:
        """Resolve the active ramp covering the station."""

        ramp = self._find_active_ramp(ramp_model.ramp_rows, station)
        if ramp is None:
            return RampEvaluationResult(station=station)

        return RampEvaluationResult(
            station=station,
            active_ramp_id=ramp.ramp_id,
            active_ramp_kind=ramp.ramp_kind,
            parent_alignment_ref=ramp.parent_alignment_ref,
            intersection_ref=ramp.intersection_ref,
        )

    @staticmethod
    def _find_active_ramp(
        ramp_rows: list[RampRow],
        station: float,
    ) -> RampRow | None:
        for row in ramp_rows:
            if row.station_start <= station <= row.station_end:
                return row
        return None
