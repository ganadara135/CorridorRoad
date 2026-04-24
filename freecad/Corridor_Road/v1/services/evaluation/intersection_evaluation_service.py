"""Intersection evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.intersection_model import (
    IntersectionControlArea,
    IntersectionModel,
)


@dataclass(frozen=True)
class IntersectionEvaluationResult:
    """Minimal resolved intersection context for a station."""

    station: float
    active_intersection_id: str = ""
    active_control_area_id: str = ""
    turn_lane_policy_ref: str = ""
    drainage_policy_ref: str = ""


class IntersectionEvaluationService:
    """Resolve intersection control-area context from an intersection source model."""

    def resolve_station(
        self,
        intersection_model: IntersectionModel,
        station: float,
    ) -> IntersectionEvaluationResult:
        """Resolve the active control area covering the station."""

        control_area = self._find_active_control_area(
            intersection_model.control_area_rows,
            station,
        )
        if control_area is None:
            return IntersectionEvaluationResult(station=station)

        return IntersectionEvaluationResult(
            station=station,
            active_intersection_id=control_area.intersection_id,
            active_control_area_id=control_area.control_area_id,
            turn_lane_policy_ref=control_area.turn_lane_policy_ref,
            drainage_policy_ref=control_area.drainage_policy_ref,
        )

    @staticmethod
    def _find_active_control_area(
        control_areas: list[IntersectionControlArea],
        station: float,
    ) -> IntersectionControlArea | None:
        for row in control_areas:
            for station_start, station_end in row.station_ranges:
                if station_start <= station <= station_end:
                    return row
            for station_start, station_end in row.influence_ranges:
                if station_start <= station <= station_end:
                    return row
        return None
