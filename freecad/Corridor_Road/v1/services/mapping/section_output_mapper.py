"""Section output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.section_output import (
    SectionComponentRow,
    SectionOutput,
    SectionQuantityRow,
    SectionSummaryRow,
)
from ...models.result.applied_section import AppliedSection


class SectionOutputMapper:
    """Map applied-section results into section output payloads."""

    def map_applied_section(self, applied_section: AppliedSection) -> SectionOutput:
        """Create a normalized section output from one applied section."""

        component_rows = [
            SectionComponentRow(
                component_row_id=f"{applied_section.applied_section_id}:{index}",
                component_id=row.component_id,
                kind=row.kind,
                template_ref=row.source_template_id,
                region_ref=row.region_id,
            )
            for index, row in enumerate(applied_section.component_rows, start=1)
        ]

        quantity_rows = [
            SectionQuantityRow(
                quantity_row_id=fragment.fragment_id,
                quantity_kind=fragment.quantity_kind,
                value=fragment.value,
                unit=fragment.unit,
                component_ref=fragment.component_id,
            )
            for fragment in applied_section.quantity_rows
        ]

        summary_rows = [
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:component-count",
                kind="component_count",
                label="Component Count",
                value=len(component_rows),
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:quantity-count",
                kind="quantity_count",
                label="Quantity Count",
                value=len(quantity_rows),
            ),
        ]

        return SectionOutput(
            schema_version=1,
            project_id=applied_section.project_id,
            section_output_id=applied_section.applied_section_id,
            alignment_id=applied_section.alignment_id,
            station=applied_section.station,
            label=applied_section.label,
            unit_context=applied_section.unit_context,
            coordinate_context=applied_section.coordinate_context,
            selection_scope={"scope_kind": "single_station", "station": applied_section.station},
            source_refs=list(applied_section.source_refs),
            result_refs=[applied_section.applied_section_id],
            component_rows=component_rows,
            quantity_rows=quantity_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(applied_section.diagnostic_rows),
        )
