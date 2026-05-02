"""Mass-haul builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...common.identity import new_entity_id
from ...models.result.corridor_model import CorridorModel
from ...models.result.earthwork_balance_model import EarthworkBalanceModel
from ...models.result.mass_haul_model import (
    BalancePointRow,
    HaulZoneRow,
    MassCurveRow,
    MassHaulModel,
)


@dataclass(frozen=True)
class MassHaulBuildRequest:
    """Input contract for building mass-haul results."""

    project_id: str
    corridor: CorridorModel
    earthwork_balance_model: EarthworkBalanceModel
    mass_haul_id: str


class MassHaulService:
    """Build a minimal cumulative mass-haul result from earthwork balance rows."""

    def build(self, request: MassHaulBuildRequest) -> MassHaulModel:
        """Create one cumulative mass curve and simple haul zones."""

        ordered_rows = sorted(
            request.earthwork_balance_model.balance_rows,
            key=lambda row: (
                row.station_start if row.station_start is not None else 0.0,
                row.station_end if row.station_end is not None else 0.0,
            ),
        )

        station_values: list[float] = []
        cumulative_mass_values: list[float] = []
        balance_point_rows: list[BalancePointRow] = []
        haul_zone_rows: list[HaulZoneRow] = []

        if ordered_rows:
            initial_station = ordered_rows[0].station_start
            initial_station = 0.0 if initial_station is None else initial_station
            station_values.append(initial_station)
            cumulative_mass_values.append(0.0)

        cumulative_mass = 0.0
        previous_cumulative_mass = 0.0
        for row in ordered_rows:
            delta_value = row.usable_cut_value - row.fill_value
            cumulative_mass += delta_value
            station_value = self._row_station_value(row)
            station_values.append(station_value)
            cumulative_mass_values.append(cumulative_mass)

            balance_station = self._balance_station(
                row,
                previous_cumulative_mass=previous_cumulative_mass,
                cumulative_mass=cumulative_mass,
            )
            if balance_station is not None:
                balance_point_rows.append(
                    BalancePointRow(
                        balance_point_row_id=new_entity_id("balance_point_row"),
                        station=balance_station,
                        value=0.0,
                    )
                )

            haul_zone_rows.append(
                HaulZoneRow(
                    haul_zone_row_id=new_entity_id("haul_zone_row"),
                    kind=self._haul_zone_kind(delta_value),
                    station_start=row.station_start if row.station_start is not None else station_value,
                    station_end=row.station_end if row.station_end is not None else station_value,
                    direction="forward",
                    value=abs(delta_value),
                )
            )
            previous_cumulative_mass = cumulative_mass

        curve_rows: list[MassCurveRow] = []
        if station_values:
            curve_rows.append(
                MassCurveRow(
                    curve_row_id=new_entity_id("mass_curve_row"),
                    kind="mass_curve",
                    station_values=station_values,
                    cumulative_mass_values=cumulative_mass_values,
                )
            )

        return MassHaulModel(
            schema_version=1,
            project_id=request.project_id,
            mass_haul_id=request.mass_haul_id,
            corridor_id=request.corridor.corridor_id,
            label=request.corridor.label or "Mass Haul",
            unit_context=request.corridor.unit_context,
            coordinate_context=request.corridor.coordinate_context,
            source_refs=[
                request.corridor.corridor_id,
                request.earthwork_balance_model.earthwork_balance_id,
            ],
            curve_rows=curve_rows,
            balance_point_rows=balance_point_rows,
            haul_zone_rows=haul_zone_rows,
        )

    def _row_station_value(self, row: object) -> float:
        """Resolve the representative station value for one balance row."""

        station_end = getattr(row, "station_end", None)
        if station_end is not None:
            return station_end
        station_start = getattr(row, "station_start", None)
        if station_start is not None:
            return station_start
        return 0.0

    def _haul_zone_kind(self, delta_value: float) -> str:
        """Map one cumulative delta into a minimal haul-zone kind."""

        if delta_value > 0.0:
            return "surplus_haul_zone"
        if delta_value < 0.0:
            return "borrow_haul_zone"
        return "balanced_haul_zone"

    def _balance_station(
        self,
        row: object,
        *,
        previous_cumulative_mass: float,
        cumulative_mass: float,
    ) -> float | None:
        """Resolve an interpolated station where the mass curve crosses zero."""

        if cumulative_mass == 0.0:
            return self._row_station_value(row)
        if not (
            previous_cumulative_mass < 0.0 < cumulative_mass
            or previous_cumulative_mass > 0.0 > cumulative_mass
        ):
            return None

        station_start = getattr(row, "station_start", None)
        station_end = getattr(row, "station_end", None)
        if station_start is None or station_end is None:
            return self._row_station_value(row)
        denominator = cumulative_mass - previous_cumulative_mass
        if abs(denominator) <= 1e-12:
            return self._row_station_value(row)
        ratio = (0.0 - previous_cumulative_mass) / denominator
        return float(station_start) + ratio * (float(station_end) - float(station_start))
