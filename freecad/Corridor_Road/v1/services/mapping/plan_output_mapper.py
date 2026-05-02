"""Plan output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.plan_output import (
    PlanGeometryRow,
    PlanOutput,
    PlanStationRow,
    PlanSummaryRow,
)
from ...models.source.alignment_model import AlignmentModel
from ..evaluation.alignment_station_sampling_service import AlignmentStationSamplingService


class PlanOutputMapper:
    """Map alignment sources into plan output payloads."""

    def map_alignment_model(
        self,
        alignment_model: AlignmentModel,
        *,
        station_interval: float = 20.0,
    ) -> PlanOutput:
        """Create a normalized plan output from one alignment model."""

        geometry_rows = [
            PlanGeometryRow(
                row_id=element.element_id,
                kind=element.kind,
                x_values=list(element.geometry_payload.get("x_values", [])),
                y_values=list(element.geometry_payload.get("y_values", [])),
                closed=bool(element.geometry_payload.get("closed", False)),
                style_role=str(element.geometry_payload.get("style_role", element.kind)),
                source_ref=element.element_id,
            )
            for element in alignment_model.geometry_sequence
        ]

        station_rows = self._station_rows(alignment_model, station_interval=station_interval)

        summary_rows = [
            PlanSummaryRow(
                summary_id=f"{alignment_model.alignment_id}:element-count",
                kind="element_count",
                label="Element Count",
                value=len(alignment_model.geometry_sequence),
            ),
            PlanSummaryRow(
                summary_id=f"{alignment_model.alignment_id}:station-count",
                kind="station_marker_count",
                label="Station Marker Count",
                value=len(station_rows),
            ),
        ]

        return PlanOutput(
            schema_version=1,
            project_id=alignment_model.project_id,
            plan_output_id=alignment_model.alignment_id,
            alignment_id=alignment_model.alignment_id,
            label=alignment_model.label,
            unit_context=alignment_model.unit_context,
            coordinate_context=alignment_model.coordinate_context,
            selection_scope={
                "scope_kind": "alignment_plan",
                "alignment_id": alignment_model.alignment_id,
            },
            source_refs=[alignment_model.alignment_id],
            result_refs=[],
            geometry_rows=geometry_rows,
            station_rows=station_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(alignment_model.diagnostic_rows),
        )

    def _format_station(self, station: float) -> str:
        """Format one station value for a minimal plan marker label."""

        return f"{station:.3f}"

    def _first_value(self, values: list[object], fallback: float) -> float:
        """Return the first numeric value from a payload list or a fallback."""

        if not values:
            return fallback
        first_value = values[0]
        if isinstance(first_value, (int, float)):
            return float(first_value)
        return fallback

    def _station_rows(
        self,
        alignment_model: AlignmentModel,
        *,
        station_interval: float = 20.0,
    ) -> list[PlanStationRow]:
        """Build sampled plan station rows from the shared alignment sampler."""

        result = AlignmentStationSamplingService().sample_alignment(
            alignment=alignment_model,
            interval=station_interval,
            extra_stations=[
                float(element.station_start)
                for element in list(alignment_model.geometry_sequence or [])
            ],
        )
        if result.rows:
            return [
                PlanStationRow(
                    station_row_id=f"{alignment_model.alignment_id}:station:{index}",
                    station=row.station,
                    station_label=row.station_label,
                    x=row.x,
                    y=row.y,
                    kind=row.source_reason,
                )
                for index, row in enumerate(result.rows, start=1)
                if row.status == "ok"
            ]

        return [
            PlanStationRow(
                station_row_id=f"{alignment_model.alignment_id}:station:{index}",
                station=element.station_start,
                station_label=self._format_station(element.station_start),
                x=self._first_value(element.geometry_payload.get("x_values", []), element.station_start),
                y=self._first_value(element.geometry_payload.get("y_values", []), 0.0),
                kind="element_start_station",
            )
            for index, element in enumerate(alignment_model.geometry_sequence, start=1)
        ]
