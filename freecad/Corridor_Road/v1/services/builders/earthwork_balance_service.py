"""Earthwork balance builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...common.identity import new_entity_id
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.earthwork_balance_model import (
    EarthworkBalanceModel,
    EarthworkBalanceRow,
    EarthworkMaterialRow,
    EarthworkZoneRow,
)
from ...models.result.quantity_model import QuantityFragment, QuantityModel


@dataclass(frozen=True)
class EarthworkBalanceBuildRequest:
    """Input contract for building earthwork balance results."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    quantity_model: QuantityModel
    earthwork_balance_id: str
    usable_cut_ratio: float = 0.85


class EarthworkBalanceService:
    """Build station-based earthwork balance rows from quantity results."""

    def build(self, request: EarthworkBalanceBuildRequest) -> EarthworkBalanceModel:
        """Create a minimal earthwork balance model."""

        windows = self._station_windows(request.applied_section_set)
        balance_rows: list[EarthworkBalanceRow] = []
        zone_rows: list[EarthworkZoneRow] = []

        for station_start, station_end in windows:
            cut_value = self._sum_quantity(
                request.quantity_model.fragment_rows,
                station_start,
                station_end,
                {"cut", "earthwork_cut"},
            )
            fill_value = self._sum_quantity(
                request.quantity_model.fragment_rows,
                station_start,
                station_end,
                {"fill", "earthwork_fill"},
            )
            usable_cut_value = self._sum_quantity(
                request.quantity_model.fragment_rows,
                station_start,
                station_end,
                {"usable_cut"},
            )
            unusable_cut_value = self._sum_quantity(
                request.quantity_model.fragment_rows,
                station_start,
                station_end,
                {"unusable_cut"},
            )

            if cut_value > 0.0 and usable_cut_value == 0.0 and unusable_cut_value == 0.0:
                usable_cut_value = cut_value * request.usable_cut_ratio
                unusable_cut_value = cut_value - usable_cut_value

            balance_ratio = usable_cut_value / fill_value if fill_value > 0.0 else 0.0
            balance_row_id = new_entity_id("earthwork_balance_row")
            balance_rows.append(
                EarthworkBalanceRow(
                    balance_row_id=balance_row_id,
                    station_start=station_start,
                    station_end=station_end,
                    cut_value=cut_value,
                    fill_value=fill_value,
                    usable_cut_value=usable_cut_value,
                    unusable_cut_value=unusable_cut_value,
                    balance_ratio=balance_ratio,
                )
            )

            delta_value = usable_cut_value - fill_value
            zone_rows.append(
                EarthworkZoneRow(
                    zone_row_id=new_entity_id("earthwork_zone_row"),
                    kind=self._zone_kind(delta_value),
                    station_start=station_start,
                    station_end=station_end,
                    value=abs(delta_value),
                )
            )

        material_rows = self._build_material_rows(balance_rows)

        return EarthworkBalanceModel(
            schema_version=1,
            project_id=request.project_id,
            earthwork_balance_id=request.earthwork_balance_id,
            corridor_id=request.corridor.corridor_id,
            label=request.corridor.label or "Earthwork Balance",
            unit_context=request.corridor.unit_context,
            coordinate_context=request.corridor.coordinate_context,
            source_refs=[
                request.corridor.corridor_id,
                request.applied_section_set.applied_section_set_id,
                request.quantity_model.quantity_model_id,
            ],
            balance_rows=balance_rows,
            material_rows=material_rows,
            zone_rows=zone_rows,
        )

    def _station_windows(self, applied_section_set: AppliedSectionSet) -> list[tuple[float, float]]:
        """Create station windows from one applied section set."""

        station_values = sorted(row.station for row in applied_section_set.station_rows)
        if not station_values:
            return []
        if len(station_values) == 1:
            return [(station_values[0], station_values[0])]

        return list(zip(station_values[:-1], station_values[1:]))

    def _sum_quantity(
        self,
        fragment_rows: list[QuantityFragment],
        station_start: float,
        station_end: float,
        recognized_kinds: set[str],
    ) -> float:
        """Sum quantity fragments that match one station window and kind set."""

        total = 0.0
        for row in fragment_rows:
            if row.quantity_kind not in recognized_kinds:
                continue
            if not self._fragment_matches_window(row, station_start, station_end):
                continue
            total += row.value
        return total

    def _fragment_matches_window(
        self,
        row: QuantityFragment,
        station_start: float,
        station_end: float,
    ) -> bool:
        """Check whether one fragment belongs to one station window."""

        row_start = row.station_start if row.station_start is not None else station_start
        row_end = row.station_end if row.station_end is not None else row_start
        if row_start == row_end:
            return row_start == station_start
        return row_start == station_start and row_end == station_end

    def _zone_kind(self, delta_value: float) -> str:
        """Classify one earthwork window by usable-cut delta."""

        if delta_value > 0.0:
            return "surplus_zone"
        if delta_value < 0.0:
            return "deficit_zone"
        return "balanced_zone"

    def _build_material_rows(
        self,
        balance_rows: list[EarthworkBalanceRow],
    ) -> list[EarthworkMaterialRow]:
        """Create simple corridor-total material interpretation rows."""

        total_usable_cut = sum(row.usable_cut_value for row in balance_rows)
        total_fill = sum(row.fill_value for row in balance_rows)
        borrow_value = max(total_fill - total_usable_cut, 0.0)
        waste_value = max(total_usable_cut - total_fill, 0.0)

        return [
            EarthworkMaterialRow(
                material_row_id=new_entity_id("earthwork_material_row"),
                kind="usable_cut_total",
                value=total_usable_cut,
                unit="m3",
            ),
            EarthworkMaterialRow(
                material_row_id=new_entity_id("earthwork_material_row"),
                kind="fill_total",
                value=total_fill,
                unit="m3",
            ),
            EarthworkMaterialRow(
                material_row_id=new_entity_id("earthwork_material_row"),
                kind="borrow_total",
                value=borrow_value,
                unit="m3",
            ),
            EarthworkMaterialRow(
                material_row_id=new_entity_id("earthwork_material_row"),
                kind="waste_total",
                value=waste_value,
                unit="m3",
            ),
        ]
