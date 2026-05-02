"""Drainage resolution service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.drainage_model import (
    DrainageCollectionRegion,
    DrainageElementRow,
    DrainageModel,
)


@dataclass(frozen=True)
class DrainageResolutionResult:
    """Minimal resolved drainage context for a station."""

    station: float
    active_element_id: str = ""
    active_element_kind: str = ""
    active_policy_set_ref: str = ""
    active_collection_region_id: str = ""
    collection_risk_level: str = ""


class DrainageResolutionService:
    """Resolve drainage element and collection-region context for a station."""

    def resolve_station(
        self,
        drainage_model: DrainageModel,
        station: float,
    ) -> DrainageResolutionResult:
        """Resolve the active drainage context covering the station."""

        element = self._find_active_element(drainage_model.element_rows, station)
        region = self._find_active_region(drainage_model.collection_region_rows, station)

        return DrainageResolutionResult(
            station=station,
            active_element_id="" if element is None else element.drainage_element_id,
            active_element_kind="" if element is None else element.element_kind,
            active_policy_set_ref="" if element is None else element.policy_set_ref,
            active_collection_region_id="" if region is None else region.collection_region_id,
            collection_risk_level="" if region is None else region.risk_level,
        )

    @staticmethod
    def _find_active_element(
        element_rows: list[DrainageElementRow],
        station: float,
    ) -> DrainageElementRow | None:
        for row in element_rows:
            if row.station_start <= station <= row.station_end:
                return row
        return None

    @staticmethod
    def _find_active_region(
        region_rows: list[DrainageCollectionRegion],
        station: float,
    ) -> DrainageCollectionRegion | None:
        for row in region_rows:
            if row.station_start <= station <= row.station_end:
                return row
        return None
