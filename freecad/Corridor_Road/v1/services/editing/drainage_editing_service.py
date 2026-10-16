"""Drainage editor rules: Ditch Run prefill from the Assembly, choices and checks.

Pure Python: the command reads the document and passes models in; nothing here touches FreeCAD
or Qt. A Ditch Run names one Assembly ditch Subassembly on one side of one road over a station
span; Regions own which Assembly applies where, so the prefill follows the Region spans.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.assembly_model import AssemblySubassemblyModel
from ...models.source.drainage_model import DITCH_RUN_SIDES, LOW_POINT_RULES, DitchRun, DrainagePolicy
from ...models.source.region_model import RegionModel

# Stations closer than this are the same station: Region ends and Stationing values are stored
# rounded, and two Regions meeting at one station must join into one run.
STATION_TOLERANCE_M = 1.0e-6


@dataclass(frozen=True)
class RoadStationSpan:
    """One road's Regions, or its station span when it has none."""

    alignment_id: str
    region_model: RegionModel | None = None
    station_start: float = 0.0
    station_end: float = 0.0


@dataclass(frozen=True)
class DitchChoice:
    """A ditch Subassembly of an Assembly template and the sides it is on."""

    subassembly_ref: str
    sides: tuple[str, ...]


def ditch_run_id(alignment_id: str, side: str, subassembly_ref: str, index: int = 1) -> str:
    road = str(alignment_id or "").strip()
    stem = f"ditch-run:{road}:{side}:{subassembly_ref}" if road else f"ditch-run:{side}:{subassembly_ref}"
    return stem if index <= 1 else f"{stem}:{index}"


def ditch_choices(assembly_models: list[AssemblySubassemblyModel]) -> list[DitchChoice]:
    """Every enabled ditch Subassembly in the Assemblies, once, with its sides."""

    sides_by_ref: dict[str, list[str]] = {}
    for model in list(assembly_models or []):
        for template in list(getattr(model, "template_rows", []) or []):
            for row in _template_ditches(template):
                sides = sides_by_ref.setdefault(str(row.subassembly_id), [])
                sides.extend(side for side in _ditch_sides(row) if side not in sides)
    return [DitchChoice(ref, tuple(side for side in DITCH_RUN_SIDES if side in sides)) for ref, sides in sides_by_ref.items()]


def prefill_ditch_runs(
    roads: list[RoadStationSpan],
    assembly_models: list[AssemblySubassemblyModel],
) -> list[DitchRun]:
    """Ditch Runs for every ditch of the Assembly each Region uses, joined across Regions.

    A road without Regions takes the first Assembly's active template over its whole span.
    """

    runs: list[DitchRun] = []
    for road in list(roads or []):
        open_runs: dict[tuple[str, str], int] = {}
        for start, end, template in _road_templates(road, assembly_models):
            for row in _template_ditches(template):
                for side in _ditch_sides(row):
                    key = (str(row.subassembly_id), side)
                    index = open_runs.get(key)
                    if index is not None and abs(runs[index].station_end - start) <= STATION_TOLERANCE_M:
                        previous = runs[index]
                        runs[index] = DitchRun(
                            previous.ditch_run_id,
                            previous.side,
                            previous.subassembly_ref,
                            previous.station_start,
                            end,
                            alignment_ref=previous.alignment_ref,
                        )
                        continue
                    count = sum(1 for run in runs if (run.alignment_ref, run.subassembly_ref, run.side) == (road.alignment_id, key[0], side))
                    runs.append(
                        DitchRun(
                            ditch_run_id(road.alignment_id, side, key[0], count + 1),
                            side,
                            key[0],
                            start,
                            end,
                            alignment_ref=road.alignment_id,
                        )
                    )
                    open_runs[key] = len(runs) - 1
    return runs


def ditch_run_diagnostics(runs: list[DitchRun], choices: list[DitchChoice]) -> list[str]:
    """Plain-language problems with the Ditch Runs; empty when they can be applied."""

    messages: list[str] = []
    sides_by_ref = {choice.subassembly_ref: choice.sides for choice in list(choices or [])}
    seen_ids: set[str] = set()
    for run in list(runs or []):
        label = run.ditch_run_id or "(no id)"
        if not run.ditch_run_id:
            messages.append("A Ditch Run has no id.")
        elif run.ditch_run_id in seen_ids:
            messages.append(f"{label}: the id is used twice.")
        seen_ids.add(run.ditch_run_id)
        if run.side not in DITCH_RUN_SIDES:
            messages.append(f"{label}: side must be left or right, not '{run.side}'.")
        if run.subassembly_ref not in sides_by_ref:
            messages.append(f"{label}: '{run.subassembly_ref}' is not a ditch in any Assembly.")
        elif run.side in DITCH_RUN_SIDES and run.side not in sides_by_ref[run.subassembly_ref]:
            messages.append(f"{label}: ditch '{run.subassembly_ref}' has no {run.side} side.")
        if not float(run.station_end) - float(run.station_start) > STATION_TOLERANCE_M:
            messages.append(f"{label}: End STA must be after Start STA.")
    enabled = [run for run in list(runs or []) if run.enabled]
    for index, run in enumerate(enabled):
        for other in enabled[index + 1:]:
            if (run.alignment_ref, run.subassembly_ref, run.side) != (other.alignment_ref, other.subassembly_ref, other.side):
                continue
            overlap = min(run.station_end, other.station_end) - max(run.station_start, other.station_start)
            if overlap > STATION_TOLERANCE_M:
                messages.append(f"{run.ditch_run_id} and {other.ditch_run_id} overlap on the same ditch and side.")
    return messages


def policy_diagnostics(policy: DrainagePolicy) -> list[str]:
    messages: list[str] = []
    if not float(policy.min_grade_percent) > 0.0:
        messages.append("Minimum grade must be above 0 %.")
    if not float(policy.max_inlet_spacing_m) > 0.0:
        messages.append("Maximum inlet spacing must be above 0 m.")
    if policy.low_point_rule not in LOW_POINT_RULES:
        messages.append(f"Low point rule must be one of {', '.join(LOW_POINT_RULES)}.")
    return messages


def _road_templates(road: RoadStationSpan, assembly_models: list[AssemblySubassemblyModel]):
    region_rows = sorted(
        list(getattr(road.region_model, "region_rows", []) or []),
        key=lambda row: float(getattr(row, "station_start", 0.0) or 0.0),
    )
    if not region_rows:
        model = assembly_models[0] if assembly_models else None
        template = _template(model, "")
        return [(float(road.station_start), float(road.station_end), template)] if template is not None else []
    output = []
    for row in region_rows:
        model = _assembly(assembly_models, str(getattr(row, "assembly_ref", "") or ""))
        template = _template(model, str(getattr(row, "template_ref", "") or ""))
        if template is not None:
            output.append((float(row.station_start), float(row.station_end), template))
    return output


def _assembly(assembly_models: list[AssemblySubassemblyModel], assembly_ref: str):
    models = [model for model in list(assembly_models or []) if model is not None]
    for model in models:
        if assembly_ref and str(getattr(model, "assembly_id", "") or "") == assembly_ref:
            return model
    return models[0] if models else None


def _template(model, template_ref: str):
    templates = list(getattr(model, "template_rows", []) or [])
    for wanted in (template_ref, str(getattr(model, "active_template_id", "") or "")):
        for template in templates:
            if wanted and str(getattr(template, "template_id", "") or "") == wanted:
                return template
    return templates[0] if templates else None


def _template_ditches(template) -> list:
    return [
        row
        for row in list(getattr(template, "subassembly_rows", []) or [])
        if bool(getattr(row, "enabled", True)) and str(getattr(row, "kind", "") or "") == "ditch"
    ]


def _ditch_sides(row) -> tuple[str, ...]:
    # The Applied Sections place a "both" or "center" ditch on each side of the road.
    side = str(getattr(row, "side", "") or "center").strip().lower()
    return (side,) if side in DITCH_RUN_SIDES else DITCH_RUN_SIDES
