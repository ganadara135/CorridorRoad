"""Surface output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.surface_output import (
    SurfaceComparisonOutputRow,
    SurfaceOutput,
    SurfaceRowOutput,
    SurfaceSpanOutputRow,
    SurfaceSummaryRow,
)
from ...common.diagnostics import DiagnosticMessage
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

        span_rows = [
            SurfaceSpanOutputRow(
                span_row_id=row.span_id,
                surface_ref=row.surface_ref,
                station_start=row.station_start,
                station_end=row.station_end,
                from_region_ref=row.from_region_ref,
                to_region_ref=row.to_region_ref,
                span_kind=row.span_kind,
                transition_ref=row.transition_ref,
                continuity_status=row.continuity_status,
                diagnostic_refs=list(row.diagnostic_refs),
                notes=row.notes,
            )
            for row in list(getattr(surface_model, "span_rows", []) or [])
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
            SurfaceSummaryRow(
                summary_id=f"{surface_model.surface_model_id}:span-count",
                kind="span_count",
                label="Surface Span Count",
                value=len(span_rows),
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
            span_rows=span_rows,
            comparison_rows=comparison_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(surface_model.diagnostic_rows) + _surface_span_diagnostic_rows(span_rows),
        )


def _surface_span_diagnostic_rows(span_rows: list[SurfaceSpanOutputRow]) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for row in list(span_rows or []):
        for diagnostic_ref in list(getattr(row, "diagnostic_refs", []) or []):
            kind = str(diagnostic_ref or "")
            if not kind:
                continue
            severity = "warning" if kind in {"surface_transition_applied", "region_context_change"} else "info"
            diagnostics.append(
                DiagnosticMessage(
                    severity=severity,
                    kind=kind,
                    message=_surface_span_diagnostic_message(row, kind),
                    notes=(
                        f"surface_ref={row.surface_ref}; span={float(row.station_start):.3f}->{float(row.station_end):.3f}; "
                        f"from_region_ref={row.from_region_ref}; to_region_ref={row.to_region_ref}; "
                        f"transition_ref={row.transition_ref}"
                    ),
                )
            )
    return diagnostics


def _surface_span_diagnostic_message(row: SurfaceSpanOutputRow, kind: str) -> str:
    if kind == "surface_transition_applied":
        return f"Surface span uses Transition Surface range {row.transition_ref}."
    if kind == "region_context_change":
        return f"Surface span crosses Region boundary {row.from_region_ref} -> {row.to_region_ref}."
    return f"Surface span diagnostic: {kind}."
