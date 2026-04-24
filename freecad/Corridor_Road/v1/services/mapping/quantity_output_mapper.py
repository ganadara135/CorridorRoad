"""Quantity output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.quantity_output import (
    QuantityAggregateRow,
    QuantityComparisonOutputRow,
    QuantityFragmentRow,
    QuantityOutput,
    QuantitySummaryRow,
)
from ...models.result.quantity_model import QuantityModel


class QuantityOutputMapper:
    """Map quantity results into quantity output payloads."""

    def map_quantity_model(self, quantity_model: QuantityModel) -> QuantityOutput:
        """Create a normalized quantity output from one quantity result family."""

        fragment_rows = [
            QuantityFragmentRow(
                fragment_row_id=row.fragment_id,
                fragment_id=row.fragment_id,
                quantity_kind=row.quantity_kind,
                measurement_kind=row.measurement_kind,
                value=row.value,
                unit=row.unit,
                station_start=row.station_start,
                station_end=row.station_end,
                component_ref=row.component_ref,
                region_ref=row.region_ref,
            )
            for row in quantity_model.fragment_rows
        ]

        aggregate_rows = [
            QuantityAggregateRow(
                aggregate_row_id=row.aggregate_id,
                aggregate_id=row.aggregate_id,
                aggregate_kind=row.aggregate_kind,
                grouping_ref=row.grouping_ref,
                value=row.value,
                unit=row.unit,
                fragment_refs=list(row.fragment_refs),
            )
            for row in quantity_model.aggregate_rows
        ]

        comparison_rows = [
            QuantityComparisonOutputRow(
                comparison_row_id=row.comparison_id,
                comparison_id=row.comparison_id,
                comparison_kind=row.comparison_kind,
                base_ref=row.base_ref,
                compare_ref=row.compare_ref,
                delta_value=row.delta_value,
                unit=row.unit,
            )
            for row in quantity_model.comparison_rows
        ]

        summary_rows = [
            QuantitySummaryRow(
                summary_id=f"{quantity_model.quantity_model_id}:fragment-count",
                kind="fragment_count",
                label="Fragment Count",
                value=len(fragment_rows),
            ),
            QuantitySummaryRow(
                summary_id=f"{quantity_model.quantity_model_id}:aggregate-count",
                kind="aggregate_count",
                label="Aggregate Count",
                value=len(aggregate_rows),
            ),
        ]

        return QuantityOutput(
            schema_version=1,
            project_id=quantity_model.project_id,
            quantity_output_id=quantity_model.quantity_model_id,
            corridor_id=quantity_model.corridor_id,
            label=quantity_model.label,
            unit_context=quantity_model.unit_context,
            coordinate_context=quantity_model.coordinate_context,
            selection_scope={"scope_kind": "corridor_total", "corridor_id": quantity_model.corridor_id},
            source_refs=list(quantity_model.source_refs),
            result_refs=[quantity_model.quantity_model_id],
            fragment_rows=fragment_rows,
            aggregate_rows=aggregate_rows,
            comparison_rows=comparison_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(quantity_model.diagnostic_rows),
        )
