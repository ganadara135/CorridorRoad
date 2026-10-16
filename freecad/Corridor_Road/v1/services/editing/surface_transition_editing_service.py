"""Surface Transition editing rules, used by the Region editor.

A Surface Transition is a station range, centred on a station, where the corridor surfaces blend
from one Region's sections to the next. The Region editor authors them next to the Region rows:
a user edits the station, half length, sample spacing and enabled state, and these rules turn the
rows into `SurfaceTransitionRange`s whose From and To Regions follow from the Region rows at
Apply time, so a transition keeps its place when Regions are renumbered.

Ranges belong to one road. The document holds one `SurfaceTransitionModel`; a road's editor
replaces only the ranges it owns and keeps the others.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ...models.source.region_model import RegionRow
from ...models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange


DEFAULT_HALF_LENGTH = 5.0
DEFAULT_SAMPLE_INTERVAL = 2.5
MIN_HALF_LENGTH = 0.001
MIN_SAMPLE_INTERVAL = 0.1
DEFAULT_TRANSITION_MODEL_ID = "surface-transitions:main"
# Stations within this distance are the same transition station (they are stored at 3 decimals).
_STATION_TOLERANCE = 5.0e-4


@dataclass(frozen=True)
class TransitionRowDraft:
    """One Surface Transition row as the Region editor shows it. Lengths are meters."""

    station: float
    half_length: float = DEFAULT_HALF_LENGTH
    sample_interval: float = DEFAULT_SAMPLE_INTERVAL
    enabled: bool = True


def surface_transition_id(from_region_ref: object, to_region_ref: object, station: float) -> str:
    """The stable id of the transition at a station between two Regions."""

    return f"surface-transition:{from_region_ref}->{to_region_ref}@{float(station):.3f}"


def region_editor_source_ref(alignment_id: str) -> str:
    """The source_ref that marks a range as authored by one road's Region editor."""

    return f"region-editor:{alignment_id}"


def region_refs_at_station(region_rows: list[RegionRow], station: float) -> tuple[str, str]:
    """The Regions just before and just after a station.

    At a boundary they are the two Regions that meet there; inside a Region both are that Region.
    A station outside every Region gives empty refs.
    """

    rows = sorted(region_rows, key=lambda row: (float(row.station_start), int(row.region_index)))
    before = ""
    after = ""
    for row in rows:
        start = float(row.station_start)
        end = float(row.station_end)
        if start < station <= end + _STATION_TOLERANCE and not before:
            before = row.region_id
        if start - _STATION_TOLERANCE <= station < end and not after:
            after = row.region_id
    return before or after, after or before


def region_boundary_stations(region_rows: list[RegionRow]) -> list[float]:
    """Stations where one Region ends and the next begins."""

    rows = sorted(region_rows, key=lambda row: float(row.station_start))
    return [float(row.station_start) for row in rows[1:]]


def owned_ranges(
    model: SurfaceTransitionModel | None,
    *,
    alignment_id: str,
    single_road: bool,
) -> list[SurfaceTransitionRange]:
    """The ranges one road's Region editor edits.

    In a document with one road every range is that road's, including ranges written before the
    Region editor authored them. With several roads only the ranges the road's editor wrote are.
    """

    rows = list(getattr(model, "transition_ranges", []) or []) if model is not None else []
    if single_road:
        return rows
    owner = region_editor_source_ref(alignment_id)
    return [row for row in rows if str(row.source_ref or "") == owner]


def drafts_from_ranges(ranges: list[SurfaceTransitionRange]) -> list[TransitionRowDraft]:
    """Editor rows for stored ranges, centred on their station, in station order."""

    drafts = [
        TransitionRowDraft(
            station=0.5 * (float(row.station_start) + float(row.station_end)),
            half_length=max(MIN_HALF_LENGTH, 0.5 * (float(row.station_end) - float(row.station_start))),
            sample_interval=float(row.sample_interval),
            enabled=bool(row.enabled),
        )
        for row in ranges
    ]
    return sorted(drafts, key=lambda draft: draft.station)


def merged_transition_model(
    existing: SurfaceTransitionModel | None,
    drafts: list[TransitionRowDraft],
    region_rows: list[RegionRow],
    *,
    alignment_id: str,
    single_road: bool,
    project_id: str,
    corridor_ref: str = "corridor:main",
) -> SurfaceTransitionModel:
    """The document's transitions with this road's ranges replaced by the editor rows.

    A row at a station an existing range already covers keeps that range's mode, target surfaces,
    approval and notes; only its extent, spacing, enabled state and Regions follow the row.
    """

    replaced = owned_ranges(existing, alignment_id=alignment_id, single_road=single_road)
    replaced_ids = {id(row) for row in replaced}
    kept = [row for row in list(getattr(existing, "transition_ranges", []) or []) if id(row) not in replaced_ids]
    previous_by_station = {round(0.5 * (row.station_start + row.station_end), 3): row for row in replaced}
    owner = region_editor_source_ref(alignment_id)
    new_ranges: list[SurfaceTransitionRange] = []
    for draft in drafts:
        station = float(draft.station)
        half = max(MIN_HALF_LENGTH, float(draft.half_length))
        from_ref, to_ref = region_refs_at_station(region_rows, station)
        previous = previous_by_station.get(round(station, 3))
        base = previous or SurfaceTransitionRange(
            transition_id="",
            station_start=0.0,
            station_end=0.0,
            approval_status="active",
            notes="Authored in the Regions panel.",
        )
        new_ranges.append(
            replace(
                base,
                transition_id=surface_transition_id(from_ref, to_ref, station),
                station_start=station - half,
                station_end=station + half,
                from_region_ref=from_ref,
                to_region_ref=to_ref,
                sample_interval=max(MIN_SAMPLE_INTERVAL, float(draft.sample_interval)),
                enabled=bool(draft.enabled),
                source_ref=owner,
            )
        )
    ranges = sorted(kept + new_ranges, key=lambda row: (float(row.station_start), float(row.station_end), str(row.transition_id)))
    if existing is not None:
        return replace(existing, transition_ranges=ranges, diagnostic_rows=[])
    return SurfaceTransitionModel(
        schema_version=1,
        project_id=str(project_id or "corridorroad-v1"),
        label="Surface Transitions",
        transition_model_id=DEFAULT_TRANSITION_MODEL_ID,
        corridor_ref=str(corridor_ref or "corridor:main"),
        transition_ranges=ranges,
    )


def transition_draft_problems(drafts: list[TransitionRowDraft], region_rows: list[RegionRow]) -> list[str]:
    """Rows Apply refuses: outside every Region, or two rows at the same station."""

    problems = []
    seen: set[float] = set()
    for index, draft in enumerate(drafts, start=1):
        key = round(float(draft.station), 3)
        if key in seen:
            problems.append(f"Transition row {index}: another row is at STA {key:.3f}.")
        seen.add(key)
        from_ref, to_ref = region_refs_at_station(region_rows, float(draft.station))
        if not from_ref and not to_ref:
            problems.append(f"Transition row {index}: STA {float(draft.station):.3f} is outside every Region.")
    return problems


__all__ = [
    "DEFAULT_HALF_LENGTH",
    "DEFAULT_SAMPLE_INTERVAL",
    "TransitionRowDraft",
    "drafts_from_ranges",
    "merged_transition_model",
    "owned_ranges",
    "region_boundary_stations",
    "region_editor_source_ref",
    "region_refs_at_station",
    "surface_transition_id",
    "transition_draft_problems",
]
