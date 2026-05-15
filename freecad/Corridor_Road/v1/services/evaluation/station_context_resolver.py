"""Shared station context resolver for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.result.region_context import RegionContextSummary
from ...models.source.drainage_model import DrainageElementRow, DrainageModel
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
    active_drainage_elements: list[DrainageElementRow] = field(default_factory=list)
    active_drainage_refs: list[str] = field(default_factory=list)
    active_drainage_refs_by_side: dict[str, list[str]] = field(default_factory=dict)
    active_flow_route_refs: list[str] = field(default_factory=list)


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
        active_drainage_elements = _active_drainage_elements(
            drainage_model,
            station=station_value,
            region_id=region_id,
        )
        active_drainage_refs = _drainage_element_refs(active_drainage_elements)
        return StationContext(
            station=station_value,
            region_context=region_context,
            structure_result=structure_result,
            active_drainage_elements=active_drainage_elements,
            active_drainage_refs=active_drainage_refs,
            active_drainage_refs_by_side=_drainage_refs_by_side(active_drainage_elements),
            active_flow_route_refs=_flow_route_refs_for_drainage_refs(
                drainage_model,
                active_drainage_refs=active_drainage_refs,
            ),
        )


def _active_drainage_elements(
    drainage_model: DrainageModel | None,
    *,
    station: float,
    region_id: str,
) -> list[DrainageElementRow]:
    if drainage_model is None:
        return []
    active_region = str(region_id or "").strip()
    station_value = float(station)
    rows: list[DrainageElementRow] = []
    for row in list(getattr(drainage_model, "element_rows", []) or []):
        if active_region and str(getattr(row, "region_ref", "") or "").strip() != active_region:
            continue
        try:
            station_start = float(getattr(row, "station_start", 0.0) or 0.0)
            station_end = float(getattr(row, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        lower = min(station_start, station_end)
        upper = max(station_start, station_end)
        if lower <= station_value <= upper:
            rows.append(row)
    return rows


def _drainage_element_refs(rows: list[DrainageElementRow]) -> list[str]:
    return _unique_refs([str(getattr(row, "drainage_element_id", "") or "") for row in list(rows or [])])


def _drainage_refs_by_side(rows: list[DrainageElementRow]) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for row in list(rows or []):
        ref = str(getattr(row, "drainage_element_id", "") or "").strip()
        if not ref:
            continue
        side = str(getattr(row, "side", "") or "").strip().lower()
        if not side:
            continue
        if side == "both":
            for label in ("left", "right"):
                output.setdefault(label, []).append(ref)
            continue
        output.setdefault(side, []).append(ref)
    return {side: _unique_refs(refs) for side, refs in output.items()}


def _flow_route_refs_for_drainage_refs(
    drainage_model: DrainageModel | None,
    *,
    active_drainage_refs: list[str],
) -> list[str]:
    if drainage_model is None:
        return []
    active = {str(value or "").strip() for value in list(active_drainage_refs or []) if str(value or "").strip()}
    if not active:
        return []
    refs: list[str] = []
    for row in list(getattr(drainage_model, "flow_route_rows", []) or []):
        route_id = str(getattr(row, "flow_route_id", "") or "").strip()
        if not route_id:
            continue
        route_refs = {
            str(getattr(row, "from_element_ref", "") or "").strip(),
            str(getattr(row, "to_element_ref", "") or "").strip(),
            str(getattr(row, "outlet_ref", "") or "").strip(),
        }
        if active.intersection(route_refs):
            refs.append(route_id)
    return _unique_refs(refs)


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
