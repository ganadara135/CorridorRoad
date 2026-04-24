"""Override resolution service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.source.override_model import OverrideModel, OverrideRow


@dataclass(frozen=True)
class OverrideResolutionResult:
    """Minimal resolved override context for a station."""

    station: float
    active_override_ids: list[str] = field(default_factory=list)


class OverrideResolutionService:
    """Resolve active override rows from an override source model."""

    def resolve_station(
        self,
        override_model: OverrideModel,
        station: float,
        *,
        region_id: str = "",
    ) -> OverrideResolutionResult:
        """Resolve all active overrides that apply at a station."""

        rows = [
            row.override_id
            for row in override_model.override_rows
            if self._applies_to_station(row, station, region_id=region_id)
        ]
        return OverrideResolutionResult(
            station=station,
            active_override_ids=rows,
        )

    @staticmethod
    def _applies_to_station(
        row: OverrideRow,
        station: float,
        *,
        region_id: str,
    ) -> bool:
        if row.activation_state != "active":
            return False

        scope = row.scope
        if scope.region_ref and region_id and scope.region_ref != region_id:
            return False

        if scope.station_start is not None and station < scope.station_start:
            return False
        if scope.station_end is not None and station > scope.station_end:
            return False

        return True
