"""Corridor model builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel, CorridorSamplingPolicy, CorridorStationRow


@dataclass(frozen=True)
class CorridorModelBuildRequest:
    """Input bundle used to build one v1 CorridorModel result."""

    project_id: str
    corridor_id: str
    applied_section_set: AppliedSectionSet
    station_interval: float = 0.0
    region_model_ref: str = ""


class CorridorModelService:
    """Build a v1 CorridorModel orchestration result from applied sections."""

    def build(self, request: CorridorModelBuildRequest) -> CorridorModel:
        """Build a corridor orchestration model without generating solids."""

        station_rows = [
            CorridorStationRow(
                station_row_id=f"{request.corridor_id}:station:{index}",
                station=float(row.station),
                kind=str(getattr(row, "kind", "") or "regular_sample"),
                source_reason=str(getattr(row, "applied_section_id", "") or ""),
            )
            for index, row in enumerate(list(request.applied_section_set.station_rows or []), start=1)
        ]
        station_interval = float(request.station_interval or _infer_station_interval(station_rows))
        return CorridorModel(
            schema_version=1,
            project_id=request.project_id,
            corridor_id=request.corridor_id,
            alignment_id=str(getattr(request.applied_section_set, "alignment_id", "") or ""),
            region_model_ref=str(request.region_model_ref or ""),
            sampling_policy=CorridorSamplingPolicy(
                sampling_policy_id=f"{request.corridor_id}:sampling",
                station_interval=station_interval,
            ),
            station_rows=station_rows,
            applied_section_set_ref=str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
            label=f"Corridor {request.corridor_id}",
            source_refs=[
                ref
                for ref in [
                    str(getattr(request.applied_section_set, "applied_section_set_id", "") or ""),
                    str(request.region_model_ref or ""),
                ]
                if ref
            ],
        )


def _infer_station_interval(rows: list[CorridorStationRow]) -> float:
    stations = sorted({round(float(row.station), 9) for row in list(rows or [])})
    deltas = [stations[index] - stations[index - 1] for index in range(1, len(stations))]
    positive = [delta for delta in deltas if delta > 1.0e-9]
    return float(min(positive)) if positive else 0.0
