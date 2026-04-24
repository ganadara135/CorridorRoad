"""Structure interaction service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.source.structure_model import StructureModel, StructureRow


@dataclass(frozen=True)
class StructureResolutionResult:
    """Minimal resolved structure context for a station."""

    station: float
    active_structure_ids: list[str] = field(default_factory=list)
    active_rule_ids: list[str] = field(default_factory=list)
    active_influence_zone_ids: list[str] = field(default_factory=list)


class StructureInteractionService:
    """Resolve active structures and interaction rules for a station."""

    def resolve_station(
        self,
        structure_model: StructureModel,
        station: float,
    ) -> StructureResolutionResult:
        """Resolve active structures, rules, and influence zones at a station."""

        active_structures = self._active_structures(structure_model.structure_rows, station)
        active_structure_ids = [row.structure_id for row in active_structures]

        active_zone_ids = [
            row.influence_zone_id
            for row in structure_model.influence_zone_rows
            if self._covers_station(row.station_start, row.station_end, station)
            and row.structure_ref in active_structure_ids
        ]

        active_rule_ids = [
            row.interaction_rule_id
            for row in structure_model.interaction_rule_rows
            if row.structure_ref in active_structure_ids
        ]

        return StructureResolutionResult(
            station=station,
            active_structure_ids=active_structure_ids,
            active_rule_ids=active_rule_ids,
            active_influence_zone_ids=active_zone_ids,
        )

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
