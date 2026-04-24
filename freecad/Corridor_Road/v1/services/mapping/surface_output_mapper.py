"""Surface output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.surface_output import (
    SurfaceComparisonOutputRow,
    SurfaceOutput,
    SurfaceRowOutput,
    SurfaceSummaryRow,
)
from ...models.result.surface_model import SurfaceModel


class SurfaceOutputMapper:
    """Map surface results into surface output payloads."""

    def map_surface_model(self, surface_model: SurfaceModel) -> SurfaceOutput:
        """Create a normalized surface output from one surface result family."""

        surface_rows = [
            SurfaceRowOutput(
                surface_row_id=row.surface_id,
                surface_id=row.surface_id,
                surface_kind=row.surface_kind,
                tin_ref=row.tin_ref,
                status=row.status,
                parent_surface_ref=row.parent_surface_ref,
            )
            for row in surface_model.surface_rows
        ]

        comparison_rows = [
            SurfaceComparisonOutputRow(
                comparison_row_id=row.comparison_id,
                comparison_id=row.comparison_id,
                comparison_kind=row.comparison_kind,
                base_surface_ref=row.base_surface_ref,
                compare_surface_ref=row.compare_surface_ref,
                result_surface_ref=row.result_surface_ref,
            )
            for row in surface_model.comparison_rows
        ]

        summary_rows = [
            SurfaceSummaryRow(
                summary_id=f"{surface_model.surface_model_id}:surface-count",
                kind="surface_count",
                label="Surface Count",
                value=len(surface_rows),
            ),
            SurfaceSummaryRow(
                summary_id=f"{surface_model.surface_model_id}:comparison-count",
                kind="comparison_count",
                label="Comparison Count",
                value=len(comparison_rows),
            ),
        ]

        return SurfaceOutput(
            schema_version=1,
            project_id=surface_model.project_id,
            surface_output_id=surface_model.surface_model_id,
            corridor_id=surface_model.corridor_id,
            label=surface_model.label,
            unit_context=surface_model.unit_context,
            coordinate_context=surface_model.coordinate_context,
            selection_scope={"scope_kind": "corridor_surface_set", "corridor_id": surface_model.corridor_id},
            source_refs=list(surface_model.source_refs),
            result_refs=[row.surface_id for row in surface_model.surface_rows],
            surface_rows=surface_rows,
            comparison_rows=comparison_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(surface_model.diagnostic_rows),
        )
