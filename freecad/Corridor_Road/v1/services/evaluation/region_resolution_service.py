"""Region resolution service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.region_model import RegionModel, RegionRow


@dataclass(frozen=True)
class RegionResolutionResult:
    """Minimal resolved region context for a station."""

    station: float
    active_region_id: str = ""
    active_template_ref: str = ""
    active_superelevation_ref: str = ""


class RegionResolutionService:
    """Resolve active region policy rows from a region source model."""

    def resolve_station(
        self,
        region_model: RegionModel,
        station: float,
    ) -> RegionResolutionResult:
        """Resolve the highest-priority region covering the station."""

        region = self._find_active_region(region_model.region_rows, station)
        if region is None:
            return RegionResolutionResult(station=station)

        return RegionResolutionResult(
            station=station,
            active_region_id=region.region_id,
            active_template_ref=region.template_ref,
            active_superelevation_ref=region.superelevation_ref,
        )

    @staticmethod
    def _find_active_region(
        region_rows: list[RegionRow],
        station: float,
    ) -> RegionRow | None:
        matches = [
            row
            for row in region_rows
            if row.station_start <= station <= row.station_end
        ]
        if not matches:
            return None

        matches.sort(
            key=lambda row: (row.priority, -(row.station_end - row.station_start)),
            reverse=True,
        )
        return matches[0]
