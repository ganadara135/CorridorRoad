"""Alignment evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.alignment_model import AlignmentElement, AlignmentModel


@dataclass(frozen=True)
class AlignmentStationResult:
    """Minimal station evaluation result for horizontal alignment."""

    station: float
    active_element_id: str = ""
    active_element_kind: str = ""
    x: float = 0.0
    y: float = 0.0
    tangent_direction_deg: float = 0.0


class AlignmentEvaluationService:
    """Evaluate station-based alignment context from an alignment source model."""

    def evaluate_station(
        self,
        alignment: AlignmentModel,
        station: float,
    ) -> AlignmentStationResult:
        """Resolve the active alignment element at a station."""

        element = self._find_active_element(alignment.geometry_sequence, station)
        if element is None:
            return AlignmentStationResult(station=station)

        return AlignmentStationResult(
            station=station,
            active_element_id=element.element_id,
            active_element_kind=element.kind,
        )

    @staticmethod
    def _find_active_element(
        elements: list[AlignmentElement],
        station: float,
    ) -> AlignmentElement | None:
        for element in elements:
            if element.station_start <= station <= element.station_end:
                return element
        return None
