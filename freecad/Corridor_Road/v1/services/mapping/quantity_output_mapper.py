"""Quantity output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.quantity_output import (
    QuantityAggregateRow,
    QuantityComparisonOutputRow,
    QuantityFragmentRow,
    QuantityOutput,
    QuantitySummaryRow,
)
from ...models.output.watertight_solid_output import WatertightSolidOutput
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
                subassembly_ref=getattr(row, "subassembly_ref", ""),
                assembly_ref=getattr(row, "assembly_ref", ""),
                region_ref=row.region_ref,
                structure_ref=row.structure_ref,
                drainage_ref=getattr(row, "drainage_ref", ""),
                flow_route_ref=getattr(row, "flow_route_ref", ""),
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

    def map_watertight_solid_output(self, watertight_solid_output: WatertightSolidOutput) -> QuantityOutput:
        """Create volume quantity fragments from accepted watertight solid outputs."""

        accepted_rows = [
            row
            for row in list(getattr(watertight_solid_output, "solid_rows", []) or [])
            if bool(getattr(row, "is_watertight", False))
            and bool(getattr(row, "is_valid_solid", False))
            and str(getattr(row, "validation_status", "") or "") == "ok"
            and float(getattr(row, "volume", 0.0) or 0.0) > 0.0
        ]
        fragment_rows = [
            QuantityFragmentRow(
                fragment_row_id=f"{row.output_object_id}:quantity:volume",
                fragment_id=f"{row.output_object_id}:volume",
                quantity_kind="watertight_solid_volume",
                measurement_kind="part_solid_volume",
                value=float(row.volume),
                unit="m3",
                station_start=float(row.station_start),
                station_end=float(row.station_end),
                subassembly_ref=str(getattr(row, "subassembly_ref", "") or ""),
                assembly_ref=str(getattr(row, "assembly_ref", "") or ""),
                region_ref=str(getattr(row, "region_ref", "") or ""),
                structure_ref=str(getattr(row, "structure_ref", "") or ""),
                drainage_ref=str(getattr(row, "drainage_ref", "") or ""),
                flow_route_ref=str(getattr(row, "flow_route_ref", "") or ""),
            )
            for row in accepted_rows
        ]
        total_volume = sum(float(row.value) for row in fragment_rows)
        aggregate_rows = []
        if fragment_rows:
            aggregate_rows.append(
                QuantityAggregateRow(
                    aggregate_row_id=f"{watertight_solid_output.watertight_solid_output_id}:quantity:total-volume",
                    aggregate_id=f"{watertight_solid_output.watertight_solid_output_id}:total-volume",
                    aggregate_kind="watertight_solid_total_volume",
                    grouping_ref=str(getattr(watertight_solid_output, "watertight_solid_output_id", "") or ""),
                    value=total_volume,
                    unit="m3",
                    fragment_refs=[row.fragment_id for row in fragment_rows],
                )
            )
        summary_rows = [
            QuantitySummaryRow(
                summary_id=f"{watertight_solid_output.watertight_solid_output_id}:accepted-solid-count",
                kind="accepted_watertight_solid_count",
                label="Accepted Watertight Solid Count",
                value=len(fragment_rows),
            ),
            QuantitySummaryRow(
                summary_id=f"{watertight_solid_output.watertight_solid_output_id}:total-volume",
                kind="accepted_watertight_solid_volume",
                label="Accepted Watertight Solid Volume",
                value=total_volume,
                unit="m3",
            ),
        ]
        return QuantityOutput(
            schema_version=1,
            project_id=watertight_solid_output.project_id,
            quantity_output_id=f"{watertight_solid_output.watertight_solid_output_id}:quantities",
            corridor_id=watertight_solid_output.corridor_id,
            label=f"{watertight_solid_output.label or 'Watertight Solids'} Quantities",
            unit_context=watertight_solid_output.unit_context,
            coordinate_context=watertight_solid_output.coordinate_context,
            selection_scope={
                "scope_kind": "watertight_solid_quantities",
                "source_output_id": watertight_solid_output.watertight_solid_output_id,
            },
            source_refs=list(watertight_solid_output.source_refs),
            result_refs=[watertight_solid_output.watertight_solid_output_id],
            fragment_rows=fragment_rows,
            aggregate_rows=aggregate_rows,
            comparison_rows=[],
            summary_rows=summary_rows,
            diagnostic_rows=list(watertight_solid_output.diagnostic_rows),
        )
