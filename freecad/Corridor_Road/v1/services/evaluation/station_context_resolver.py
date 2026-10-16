"""Shared station context resolver for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.result.region_context import RegionContextSummary
from ...models.source.drainage_model import DitchRun, DrainageModel, ditch_run_covers
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel
from .region_resolution_service import RegionResolutionService
from .structure_interaction_service import StructureInteractionService


@dataclass(frozen=True)
class StationContext:
    """Resolved source context for one corridor station."""

    station: float
    region_context: RegionContextSummary
    structure_result: object | None = None
    # the Drainage Ditch Runs covering the station on this road, and their ids
    active_ditch_runs: list[DitchRun] = field(default_factory=list)
    active_drainage_refs: list[str] = field(default_factory=list)
    active_drainage_refs_by_side: dict[str, list[str]] = field(default_factory=dict)


class StationContextResolver:
    """Resolve Region, Structure, and Drainage context at a station."""

    def __init__(
        self,
        *,
        region_service: RegionResolutionService | None = None,
        structure_service: StructureInteractionService | None = None,
    ) -> None:
        self.region_service = region_service or RegionResolutionService()
        self.structure_service = structure_service or StructureInteractionService()

    def resolve(
        self,
        *,
        region_model: RegionModel,
        station: float,
        structure_model: StructureModel | None = None,
        drainage_model: DrainageModel | None = None,
    ) -> StationContext:
        """Resolve shared station context without mutating source models."""

        station_value = float(station)
        region_context = self.region_service.resolve_handoff(region_model, station_value)
        region_id = str(getattr(region_context, "region_id", "") or "")
        structure_result = (
            self.structure_service.resolve_station(
                structure_model,
                station_value,
                active_region_ref=region_id,
            )
            if structure_model is not None
            else None
        )
        ditch_runs = _active_ditch_runs(
            drainage_model,
            station=station_value,
            alignment_ref=str(getattr(region_model, "alignment_id", "") or ""),
        )
        return StationContext(
            station=station_value,
            region_context=region_context,
            structure_result=structure_result,
            active_ditch_runs=ditch_runs,
            active_drainage_refs=_unique_refs([run.ditch_run_id for run in ditch_runs]),
            active_drainage_refs_by_side=_ditch_run_refs_by_side(ditch_runs),
        )


def _active_ditch_runs(drainage_model: DrainageModel | None, *, station: float, alignment_ref: str) -> list[DitchRun]:
    if drainage_model is None:
        return []
    return [
        run
        for run in list(getattr(drainage_model, "ditch_run_rows", []) or [])
        if ditch_run_covers(run, station, alignment_ref=alignment_ref)
    ]


def _ditch_run_refs_by_side(runs: list[DitchRun]) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for run in list(runs or []):
        output.setdefault(str(run.side), []).append(str(run.ditch_run_id))
    return {side: _unique_refs(refs) for side, refs in output.items()}


def _unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output
