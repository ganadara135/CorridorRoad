"""Quantity builder service for CorridorRoad v1."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ...common.identity import new_entity_id
from ...models.result.applied_section import AppliedSection
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.quantity_model import (
    QuantityAggregate,
    QuantityFragment,
    QuantityGroupingRow,
    QuantityModel,
)
from ..evaluation import SectionEarthworkVolumeService


@dataclass(frozen=True)
class QuantityBuildRequest:
    """Input contract for building grouped quantity results."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    quantity_model_id: str


class QuantityBuildService:
    """Build quantity fragments and aggregates from applied sections."""

    def build(self, request: QuantityBuildRequest) -> QuantityModel:
        """Create a minimal quantity model from one applied section set."""

        fragment_rows: list[QuantityFragment] = []

        for section in request.applied_section_set.sections:
            fragment_rows.extend(self._fragment_rows_for_section(section))
        fragment_rows.extend(
            SectionEarthworkVolumeService().build(
                fragment_rows,
                station_values=self._station_values(request.applied_section_set),
                fragment_id_prefix=f"{request.quantity_model_id}:section-earthwork-volume",
            ).rows
        )

        grouping_row = QuantityGroupingRow(
            grouping_id=f"{request.quantity_model_id}:corridor-total",
            grouping_kind="corridor_total",
            grouping_key=request.corridor.corridor_id,
            station_start=self._min_station(request.applied_section_set),
            station_end=self._max_station(request.applied_section_set),
        )

        aggregate_rows = self._build_aggregate_rows(
            grouping_id=grouping_row.grouping_id,
            fragment_rows=fragment_rows,
        )

        return QuantityModel(
            schema_version=1,
            project_id=request.project_id,
            quantity_model_id=request.quantity_model_id,
            corridor_id=request.corridor.corridor_id,
            label=request.corridor.label or "Corridor Quantity",
            unit_context=request.corridor.unit_context,
            coordinate_context=request.corridor.coordinate_context,
            source_refs=[
                request.corridor.corridor_id,
                request.applied_section_set.applied_section_set_id,
            ],
            fragment_rows=fragment_rows,
            aggregate_rows=aggregate_rows,
            grouping_rows=[grouping_row],
            comparison_rows=[],
        )

    def _fragment_rows_for_section(self, section: AppliedSection) -> list[QuantityFragment]:
        """Create minimal quantity fragments for one applied section."""

        if section.quantity_rows:
            return [
                QuantityFragment(
                    fragment_id=row.fragment_id,
                    quantity_kind=row.quantity_kind,
                    measurement_kind="station_fragment",
                    value=row.value,
                    unit=row.unit,
                    station_start=section.station,
                    station_end=section.station,
                    component_ref=row.component_id,
                    region_ref=section.region_id,
                    structure_ref=",".join(self._structure_refs_for_component(section, row.component_id)),
                )
                for row in section.quantity_rows
            ]

        return [
            QuantityFragment(
                fragment_id=new_entity_id("quantity_fragment"),
                quantity_kind=f"{component.kind}_count",
                measurement_kind="count",
                value=1.0,
                unit="ea",
                station_start=section.station,
                station_end=section.station,
                component_ref=component.component_id,
                region_ref=section.region_id,
                structure_ref=",".join(component.structure_ids),
            )
            for component in section.component_rows
        ]

    def _structure_refs_for_component(
        self,
        section: AppliedSection,
        component_id: str,
    ) -> list[str]:
        """Resolve structure refs for one quantity fragment."""

        for component in section.component_rows:
            if component.component_id == component_id:
                return list(component.structure_ids)
        return []

    def _build_aggregate_rows(
        self,
        grouping_id: str,
        fragment_rows: list[QuantityFragment],
    ) -> list[QuantityAggregate]:
        """Create simple aggregates grouped by quantity kind and unit."""

        totals: dict[tuple[str, str], dict[str, object]] = defaultdict(
            lambda: {"value": 0.0, "fragment_refs": []}
        )

        for row in fragment_rows:
            key = (row.quantity_kind, row.unit)
            totals[key]["value"] += row.value
            totals[key]["fragment_refs"].append(row.fragment_id)

        aggregate_rows: list[QuantityAggregate] = []
        for (quantity_kind, unit), payload in sorted(totals.items()):
            aggregate_rows.append(
                QuantityAggregate(
                    aggregate_id=new_entity_id("quantity_aggregate"),
                    aggregate_kind=quantity_kind,
                    grouping_ref=grouping_id,
                    value=float(payload["value"]),
                    unit=unit,
                    fragment_refs=list(payload["fragment_refs"]),
                )
            )

        return aggregate_rows

    def _min_station(self, applied_section_set: AppliedSectionSet) -> float | None:
        """Find the lowest sampled station in one section set."""

        if not applied_section_set.station_rows:
            return None
        return min(row.station for row in applied_section_set.station_rows)

    def _max_station(self, applied_section_set: AppliedSectionSet) -> float | None:
        """Find the highest sampled station in one section set."""

        if not applied_section_set.station_rows:
            return None
        return max(row.station for row in applied_section_set.station_rows)

    def _station_values(self, applied_section_set: AppliedSectionSet) -> list[float]:
        """Return sorted station values for average-end-area volume windows."""

        return sorted(float(row.station) for row in applied_section_set.station_rows)
