"""Earthwork quantity builder for CorridorRoad v1."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...common.identity import new_entity_id
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.quantity_model import (
    QuantityAggregate,
    QuantityFragment,
    QuantityGroupingRow,
    QuantityModel,
)
from ..evaluation import SectionEarthworkVolumeService
from .earthwork_analysis_service import EarthworkAnalysisResult


@dataclass(frozen=True)
class EarthworkQuantityBuildRequest:
    """Input contract for building earthwork quantity rows."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    earthwork_analysis_result: EarthworkAnalysisResult
    quantity_model_id: str


class EarthworkQuantityService:
    """Build a QuantityModel from v1 earthwork area analysis results."""

    def __init__(self, *, volume_service: SectionEarthworkVolumeService | None = None) -> None:
        self.volume_service = volume_service or SectionEarthworkVolumeService()

    def build(self, request: EarthworkQuantityBuildRequest) -> QuantityModel:
        """Create earthwork area and average-end-area volume quantity fragments."""

        area_rows = list(getattr(request.earthwork_analysis_result, "area_fragment_rows", []) or [])
        station_values = self._station_values(request.applied_section_set)
        diagnostics = list(getattr(request.earthwork_analysis_result, "diagnostic_rows", []) or [])

        volume_result = self.volume_service.build(
            area_rows,
            station_values=station_values,
            fragment_id_prefix=f"{request.quantity_model_id}:earthwork-volume",
        )
        if volume_result.status != "ok":
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind=f"earthwork_volume_{volume_result.status}",
                    message=volume_result.notes or "Earthwork volume fragments were not generated.",
                    notes=request.earthwork_analysis_result.analysis_id,
                )
            )

        fragment_rows = area_rows + list(volume_result.rows or [])
        grouping_row = QuantityGroupingRow(
            grouping_id=f"{request.quantity_model_id}:earthwork-total",
            grouping_kind="earthwork_total",
            grouping_key=request.corridor.corridor_id,
            station_start=self._min_station(station_values),
            station_end=self._max_station(station_values),
        )

        return QuantityModel(
            schema_version=1,
            project_id=request.project_id,
            quantity_model_id=request.quantity_model_id,
            corridor_id=request.corridor.corridor_id,
            label=request.corridor.label or "Earthwork Quantity",
            unit_context=request.corridor.unit_context,
            coordinate_context=request.corridor.coordinate_context,
            source_refs=[
                ref
                for ref in [
                    request.corridor.corridor_id,
                    request.applied_section_set.applied_section_set_id,
                    request.earthwork_analysis_result.analysis_id,
                ]
                if ref
            ],
            diagnostic_rows=diagnostics,
            fragment_rows=fragment_rows,
            aggregate_rows=self._aggregate_rows(
                grouping_id=grouping_row.grouping_id,
                fragment_rows=fragment_rows,
            ),
            grouping_rows=[grouping_row],
            comparison_rows=[],
        )

    @staticmethod
    def _station_values(applied_section_set: AppliedSectionSet) -> list[float]:
        values = []
        seen: set[float] = set()
        for row in list(getattr(applied_section_set, "station_rows", []) or []):
            try:
                station = float(getattr(row, "station", 0.0) or 0.0)
            except Exception:
                continue
            rounded = round(station, 9)
            if rounded in seen:
                continue
            seen.add(rounded)
            values.append(station)
        return sorted(values)

    @staticmethod
    def _min_station(station_values: list[float]) -> float | None:
        return min(station_values) if station_values else None

    @staticmethod
    def _max_station(station_values: list[float]) -> float | None:
        return max(station_values) if station_values else None

    @staticmethod
    def _aggregate_rows(
        *,
        grouping_id: str,
        fragment_rows: list[QuantityFragment],
    ) -> list[QuantityAggregate]:
        totals: dict[tuple[str, str], dict[str, object]] = defaultdict(
            lambda: {"value": 0.0, "fragment_refs": []}
        )
        for row in list(fragment_rows or []):
            key = (str(row.quantity_kind), str(row.unit))
            totals[key]["value"] += float(row.value)
            totals[key]["fragment_refs"].append(row.fragment_id)

        rows: list[QuantityAggregate] = []
        for (quantity_kind, unit), payload in sorted(totals.items()):
            rows.append(
                QuantityAggregate(
                    aggregate_id=new_entity_id("earthwork_quantity_aggregate"),
                    aggregate_kind=quantity_kind,
                    grouping_ref=grouping_id,
                    value=float(payload["value"]),
                    unit=unit,
                    fragment_refs=list(payload["fragment_refs"]),
                )
            )
        return rows
