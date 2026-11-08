"""Structure interaction service for CorridorRoad v1: which structures are active at a station."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.source.structure_model import StructureModel, StructureRow


@dataclass(frozen=True)
class StructureResolutionResult:
    """Minimal resolved structure context for a station."""

    station: float
    active_structure_ids: list[str] = field(default_factory=list)


class StructureInteractionService:
    """Resolve the structures whose placement covers a station."""

    def resolve_station(
        self,
        structure_model: StructureModel,
        station: float,
        *,
        active_structure_ref: str = "",
        active_region_ref: str = "",
    ) -> StructureResolutionResult:
        """Resolve the active structures at a station."""

        active_structures = self._active_structures(structure_model.structure_rows, station)
        active_region_ref = str(active_region_ref or "").strip()
        if active_region_ref:
            active_structures = [
                row
                for row in active_structures
                if str(getattr(getattr(row, "placement", None), "region_ref", "") or "") == active_region_ref
            ]
        active_structure_ref = str(active_structure_ref or "").strip()
        if active_structure_ref:
            active_structures = [
                row for row in active_structures if str(getattr(row, "structure_id", "") or "") == active_structure_ref
            ]
        active_structure_ids = [row.structure_id for row in active_structures]

        return StructureResolutionResult(station=station, active_structure_ids=active_structure_ids)

    @staticmethod
    def _active_structures(
        structure_rows: list[StructureRow],
        station: float,
    ) -> list[StructureRow]:
        return [
            row
            for row in structure_rows
            if StructureInteractionService._covers_station(
                row.placement.station_start,
                row.placement.station_end,
                station,
            )
        ]

    @staticmethod
    def _covers_station(
        station_start: float,
        station_end: float,
        station: float,
    ) -> bool:
        return station_start <= station <= station_end
