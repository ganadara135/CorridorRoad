"""Presentation rows for the Drainage Flow review table."""

from __future__ import annotations

from typing import Callable

from .review_text import display_source_ref as _display_source_ref
from .review_text import unique_text_values as _unique_text_values

DRAINAGE_FLOW_REVIEW_MISSING_MODEL_NOTE = "DrainageModel is required before Drainage Flow review."
DRAINAGE_FLOW_REVIEW_PRESET_MODEL_NOTE = (
    "Intersection preset drainage is source-stage handoff metadata, not a Drainage Flow highlight source."
)
DRAINAGE_FLOW_REVIEW_NO_ROUTES_NOTE = "No Drainage Flow Route rows."


def drainage_flow_review_placeholder_row(notes: str) -> dict[str, object]:
    """Return the single row shown when there is no Flow Route to review."""

    return {
        "flow_route_id": "",
        "status": "missing",
        "from_element": "",
        "to_element": "",
        "outlet": "",
        "structure_refs": "",
        "station_start": "",
        "station_end": "",
        "notes": notes,
    }


def drainage_flow_review_rows(
    drainage_model,
    structure_model,
    *,
    highlight_mode_for_route: Callable[[str], str],
) -> list[dict[str, object]]:
    """Return one review row per Flow Route; empty when the model has none."""

    element_by_id = {
        str(getattr(row, "drainage_element_id", "") or ""): row
        for row in list(getattr(drainage_model, "element_rows", []) or [])
    }
    structure_by_id = {
        str(getattr(row, "structure_id", "") or ""): row
        for row in list(getattr(structure_model, "structure_rows", []) or [])
    } if structure_model is not None else {}
    rows: list[dict[str, object]] = []
    for flow_row in list(getattr(drainage_model, "flow_route_rows", []) or []):
        connected_elements = _drainage_flow_connected_elements(flow_row, element_by_id)
        structure_refs = _drainage_flow_structure_refs(flow_row, connected_elements)
        station_range = _drainage_flow_station_range(flow_row, connected_elements, structure_by_id)
        route_id = str(getattr(flow_row, "flow_route_id", "") or "")
        from_ref = str(getattr(flow_row, "from_element_ref", "") or "")
        to_ref = str(getattr(flow_row, "to_element_ref", "") or "")
        outlet_ref = str(getattr(flow_row, "outlet_ref", "") or "")
        chain_values = [value for value in (from_ref, to_ref, outlet_ref) if value]
        missing_refs = [
            ref
            for ref in (from_ref, to_ref)
            if ref and ref.startswith("drainage:") and ref not in element_by_id
        ]
        if missing_refs:
            status = "missing"
            notes = "Broken Flow Route element refs: " + ", ".join(_display_source_ref(ref) for ref in missing_refs)
        elif not chain_values:
            status = "missing"
            notes = "Flow Route has no From, To, or Outlet refs."
        elif not structure_refs:
            status = "warn"
            notes = f"Route {' -> '.join(_display_source_ref(value) for value in chain_values)} has no linked Structure ref."
        else:
            status = "ready"
            notes = (
                f"Route {' -> '.join(_display_source_ref(value) for value in chain_values)}; "
                f"structures={', '.join(_display_source_ref(ref) for ref in structure_refs)}"
            )
        rows.append(
            {
                "flow_route_id": route_id,
                "status": status,
                "from_element": from_ref,
                "to_element": to_ref,
                "outlet": outlet_ref,
                "structure_refs": ", ".join(structure_refs),
                "station_start": "" if station_range is None else station_range[0],
                "station_end": "" if station_range is None else station_range[1],
                "highlight_mode": highlight_mode_for_route(route_id),
                "notes": notes,
            }
        )
    return rows


def _drainage_flow_connected_elements(flow_row, element_by_id: dict[str, object]) -> list[object]:
    elements: list[object] = []
    seen: set[str] = set()
    for ref in (
        str(getattr(flow_row, "from_element_ref", "") or ""),
        str(getattr(flow_row, "to_element_ref", "") or ""),
        str(getattr(flow_row, "outlet_ref", "") or ""),
    ):
        if not ref or ref in seen:
            continue
        seen.add(ref)
        element = element_by_id.get(ref)
        if element is not None:
            elements.append(element)
    return elements


def _drainage_flow_structure_refs(flow_row, connected_elements: list[object]) -> list[str]:
    refs: list[str] = []
    for element in list(connected_elements or []):
        ref = str(getattr(element, "structure_ref", "") or "").strip()
        if ref:
            refs.append(ref)
    outlet_ref = str(getattr(flow_row, "outlet_ref", "") or "").strip()
    if outlet_ref.startswith("structure:"):
        refs.append(outlet_ref)
    return _unique_text_values(refs)


def _drainage_flow_station_range(
    flow_row,
    connected_elements: list[object],
    structure_by_id: dict[str, object],
) -> tuple[float, float] | None:
    stations: list[float] = []
    for element in list(connected_elements or []):
        stations.extend(
            [
                float(getattr(element, "station_start", 0.0) or 0.0),
                float(getattr(element, "station_end", 0.0) or 0.0),
            ]
        )
    for ref in _drainage_flow_structure_refs(flow_row, connected_elements):
        structure = structure_by_id.get(ref)
        placement = getattr(structure, "placement", None)
        if placement is None:
            continue
        stations.extend(
            [
                float(getattr(placement, "station_start", 0.0) or 0.0),
                float(getattr(placement, "station_end", 0.0) or 0.0),
            ]
        )
    if not stations:
        return None
    return min(stations), max(stations)
