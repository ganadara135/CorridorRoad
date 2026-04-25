"""Earthwork output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.earthwork_output import (
    EarthworkBalanceOutput,
    EarthworkBalanceRowOutput,
    EarthworkSummaryRow,
    MassCurveRowOutput,
    MassHaulOutput,
)
from ...models.result.earthwork_balance_model import EarthworkBalanceModel
from ...models.result.mass_haul_model import MassHaulModel


class EarthworkOutputMapper:
    """Map earthwork and mass-haul results into normalized output payloads."""

    def map_earthwork_balance(
        self,
        earthwork_model: EarthworkBalanceModel,
    ) -> EarthworkBalanceOutput:
        """Create a normalized earthwork balance output."""

        balance_rows = [
            EarthworkBalanceRowOutput(
                balance_row_id=row.balance_row_id,
                station_start=row.station_start,
                station_end=row.station_end,
                cut_value=row.cut_value,
                fill_value=row.fill_value,
                usable_cut_value=row.usable_cut_value,
                unusable_cut_value=row.unusable_cut_value,
                balance_ratio=row.balance_ratio,
                unit=row.unit,
            )
            for row in earthwork_model.balance_rows
        ]

        total_cut = sum(row.cut_value for row in earthwork_model.balance_rows)
        total_fill = sum(row.fill_value for row in earthwork_model.balance_rows)

        summary_rows = [
            EarthworkSummaryRow(
                summary_id=f"{earthwork_model.earthwork_balance_id}:total-cut",
                kind="total_cut",
                label="Total Cut",
                value=total_cut,
                unit="m3",
            ),
            EarthworkSummaryRow(
                summary_id=f"{earthwork_model.earthwork_balance_id}:total-fill",
                kind="total_fill",
                label="Total Fill",
                value=total_fill,
                unit="m3",
            ),
        ]

        return EarthworkBalanceOutput(
            schema_version=1,
            project_id=earthwork_model.project_id,
            earthwork_output_id=earthwork_model.earthwork_balance_id,
            corridor_id=earthwork_model.corridor_id,
            label=earthwork_model.label,
            unit_context=earthwork_model.unit_context,
            coordinate_context=earthwork_model.coordinate_context,
            selection_scope={"scope_kind": "corridor_total", "corridor_id": earthwork_model.corridor_id},
            source_refs=list(earthwork_model.source_refs),
            result_refs=[earthwork_model.earthwork_balance_id],
            balance_rows=balance_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(earthwork_model.diagnostic_rows),
        )

    def map_mass_haul(self, mass_haul_model: MassHaulModel) -> MassHaulOutput:
        """Create a normalized mass-haul output."""

        curve_rows = [
            MassCurveRowOutput(
                curve_row_id=row.curve_row_id,
                kind=row.kind,
                station_values=list(row.station_values),
                cumulative_mass_values=list(row.cumulative_mass_values),
                unit=row.unit,
            )
            for row in mass_haul_model.curve_rows
        ]

        summary_rows = [
            EarthworkSummaryRow(
                summary_id=f"{mass_haul_model.mass_haul_id}:curve-count",
                kind="mass_haul_summary",
                label="Curve Count",
                value=len(curve_rows),
            ),
            EarthworkSummaryRow(
                summary_id=f"{mass_haul_model.mass_haul_id}:balance-point-count",
                kind="balance_point_count",
                label="Balance Point Count",
                value=len(mass_haul_model.balance_point_rows),
            ),
        ]
        summary_rows.extend(self._mass_curve_summary_rows(mass_haul_model))

        return MassHaulOutput(
            schema_version=1,
            project_id=mass_haul_model.project_id,
            mass_haul_output_id=mass_haul_model.mass_haul_id,
            corridor_id=mass_haul_model.corridor_id,
            label=mass_haul_model.label,
            unit_context=mass_haul_model.unit_context,
            coordinate_context=mass_haul_model.coordinate_context,
            selection_scope={"scope_kind": "corridor_total", "corridor_id": mass_haul_model.corridor_id},
            source_refs=list(mass_haul_model.source_refs),
            result_refs=[mass_haul_model.mass_haul_id],
            curve_rows=curve_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(mass_haul_model.diagnostic_rows),
        )

    @staticmethod
    def _mass_curve_summary_rows(mass_haul_model: MassHaulModel) -> list[EarthworkSummaryRow]:
        curve_rows = list(getattr(mass_haul_model, "curve_rows", []) or [])
        if not curve_rows:
            return []
        values = list(getattr(curve_rows[0], "cumulative_mass_values", []) or [])
        if not values:
            return []
        return [
            EarthworkSummaryRow(
                summary_id=f"{mass_haul_model.mass_haul_id}:final-cumulative-mass",
                kind="final_cumulative_mass",
                label="Final Cumulative Mass",
                value=float(values[-1]),
                unit="m3",
            ),
            EarthworkSummaryRow(
                summary_id=f"{mass_haul_model.mass_haul_id}:max-surplus-cumulative-mass",
                kind="max_surplus_cumulative_mass",
                label="Max Surplus Cumulative Mass",
                value=float(max(values)),
                unit="m3",
            ),
            EarthworkSummaryRow(
                summary_id=f"{mass_haul_model.mass_haul_id}:max-deficit-cumulative-mass",
                kind="max_deficit_cumulative_mass",
                label="Max Deficit Cumulative Mass",
                value=float(min(values)),
                unit="m3",
            ),
        ]
