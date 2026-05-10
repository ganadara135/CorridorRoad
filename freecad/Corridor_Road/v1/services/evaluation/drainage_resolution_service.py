"""Drainage resolution service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.source.drainage_model import (
    DrainageElementRow,
    DrainageFlowRoute,
    DrainageModel,
)
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel


STATION_BOUNDARY_TOLERANCE = 1.0e-3


@dataclass(frozen=True)
class DrainageValidationResult:
    """Validation result for a DrainageModel."""

    status: str
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


@dataclass(frozen=True)
class DrainageResolutionResult:
    """Minimal resolved drainage context for a station."""

    station: float
    active_element_id: str = ""
    active_element_kind: str = ""
    active_policy_set_ref: str = ""
    active_flow_route_id: str = ""
    flow_route_risk_level: str = ""


class DrainageValidationService:
    """Validate v1 drainage source rows without mutating them."""

    def validate(
        self,
        drainage_model: DrainageModel,
        *,
        region_model: RegionModel | None = None,
        structure_model: StructureModel | None = None,
    ) -> DrainageValidationResult:
        diagnostics: list[DiagnosticMessage] = []
        element_rows = list(getattr(drainage_model, "element_rows", []) or [])
        policy_rows = list(getattr(drainage_model, "policy_rows", []) or [])
        flow_route_rows = list(getattr(drainage_model, "flow_route_rows", []) or [])
        policy_ids = _policy_id_set(policy_rows)
        region_ranges = None if region_model is None else _region_station_ranges(region_model)
        structure_ids = None if structure_model is None else _structure_id_set(structure_model)

        diagnostics.extend(_duplicate_id_diagnostics(policy_rows, "policy_set_id", "duplicate_policy_set_id", "Drainage policy id is duplicated."))
        diagnostics.extend(
            _duplicate_id_diagnostics(
                element_rows,
                "drainage_element_id",
                "duplicate_drainage_element_id",
                "Drainage element id is duplicated.",
            )
        )
        diagnostics.extend(
            _duplicate_id_diagnostics(
                flow_route_rows,
                "flow_route_id",
                "duplicate_flow_route_id",
                "Drainage flow route id is duplicated.",
            )
        )

        for index, row in enumerate(element_rows, start=1):
            element_id = str(getattr(row, "drainage_element_id", "") or "").strip()
            source_ref = element_id or f"drainage-element:{index}"
            if not element_id:
                diagnostics.append(_diagnostic("error", "missing_drainage_element_id", source_ref, "Drainage element id is required."))
            element_kind = str(getattr(row, "element_kind", "") or "").strip()
            if not element_kind:
                diagnostics.append(_diagnostic("warning", "missing_drainage_element_kind", source_ref, "Drainage element kind is not set."))
            side = str(getattr(row, "side", "") or "").strip().lower()
            if side and side not in {"left", "right", "both", "center"}:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "unsupported_drainage_side",
                        source_ref,
                        f"Drainage element side should be left, right, both, or center: {side}.",
                    )
                )
            station_diagnostic = _station_range_diagnostic(
                row,
                source_ref=source_ref,
                kind="invalid_drainage_element_station_range",
                label="Drainage element",
            )
            if station_diagnostic is not None:
                diagnostics.append(station_diagnostic)
            region_diagnostic = _element_region_station_diagnostic(row, source_ref=source_ref, region_ranges=region_ranges)
            if region_diagnostic is not None:
                diagnostics.append(region_diagnostic)
            structure_diagnostic = _element_structure_ref_diagnostic(row, source_ref=source_ref, structure_ids=structure_ids)
            if structure_diagnostic is not None:
                diagnostics.append(structure_diagnostic)
            policy_ref = str(getattr(row, "policy_set_ref", "") or "").strip()
            if not policy_ref:
                diagnostics.append(_diagnostic("warning", "missing_policy_ref", source_ref, "Drainage element has no policy_set_ref."))
            elif policy_ref not in policy_ids:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_policy_set_ref",
                        source_ref,
                        f"Drainage element references missing policy_set_ref {policy_ref}.",
                    )
                )

        for index, row in enumerate(policy_rows, start=1):
            policy_id = str(getattr(row, "policy_set_id", "") or "").strip()
            source_ref = policy_id or f"drainage-policy:{index}"
            if not policy_id:
                diagnostics.append(_diagnostic("error", "missing_policy_set_id", source_ref, "Drainage policy id is required."))
            if not str(getattr(row, "flow_intent", "") or "").strip():
                diagnostics.append(_diagnostic("warning", "missing_flow_intent", source_ref, "Drainage policy flow_intent is not set."))

        for index, row in enumerate(flow_route_rows, start=1):
            route_id = str(getattr(row, "flow_route_id", "") or "").strip()
            source_ref = route_id or f"flow-route:{index}"
            if not route_id:
                diagnostics.append(_diagnostic("error", "missing_flow_route_id", source_ref, "Drainage flow route id is required."))
        diagnostics.extend(_flow_route_graph_diagnostics(flow_route_rows, element_rows))

        status = "error" if any(row.severity == "error" for row in diagnostics) else "warning" if diagnostics else "ok"
        return DrainageValidationResult(status=status, diagnostic_rows=diagnostics)


class DrainageResolutionService:
    """Resolve drainage element and flow-route context for a station."""

    def __init__(self, *, validation_service: DrainageValidationService | None = None) -> None:
        self.validation_service = validation_service or DrainageValidationService()

    def validate(
        self,
        drainage_model: DrainageModel,
        *,
        region_model: RegionModel | None = None,
        structure_model: StructureModel | None = None,
    ) -> DrainageValidationResult:
        """Validate a DrainageModel using the shared validation service."""

        return self.validation_service.validate(drainage_model, region_model=region_model, structure_model=structure_model)

    def resolve_station(
        self,
        drainage_model: DrainageModel,
        station: float,
    ) -> DrainageResolutionResult:
        """Resolve the active drainage context covering the station."""

        element = self._find_active_element(drainage_model.element_rows, station)
        route = self._find_active_flow_route(getattr(drainage_model, "flow_route_rows", []) or [], element)

        return DrainageResolutionResult(
            station=station,
            active_element_id="" if element is None else element.drainage_element_id,
            active_element_kind="" if element is None else element.element_kind,
            active_policy_set_ref="" if element is None else element.policy_set_ref,
            active_flow_route_id="" if route is None else route.flow_route_id,
            flow_route_risk_level="" if route is None else route.risk_level,
        )

    @staticmethod
    def _find_active_element(
        element_rows: list[DrainageElementRow],
        station: float,
    ) -> DrainageElementRow | None:
        for row in element_rows:
            if row.station_start <= station <= row.station_end:
                return row
        return None

    @staticmethod
    def _find_active_flow_route(
        route_rows: list[DrainageFlowRoute],
        element: DrainageElementRow | None,
    ) -> DrainageFlowRoute | None:
        if element is None:
            return None
        element_id = str(getattr(element, "drainage_element_id", "") or "")
        for row in route_rows:
            if str(getattr(row, "from_element_ref", "") or "") == element_id:
                return row
        return None


def _policy_id_set(policy_rows: list[DrainagePolicySet]) -> set[str]:
    return {str(getattr(row, "policy_set_id", "") or "").strip() for row in list(policy_rows or []) if str(getattr(row, "policy_set_id", "") or "").strip()}


def _structure_id_set(structure_model: StructureModel | None) -> set[str]:
    if structure_model is None:
        return set()
    return {
        str(getattr(row, "structure_id", "") or "").strip()
        for row in list(getattr(structure_model, "structure_rows", []) or [])
        if str(getattr(row, "structure_id", "") or "").strip()
    }


def _duplicate_id_diagnostics(rows: list[object], id_attr: str, kind: str, message: str) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    seen: set[str] = set()
    for index, row in enumerate(list(rows or []), start=1):
        row_id = str(getattr(row, id_attr, "") or "").strip()
        if not row_id:
            continue
        if row_id in seen:
            diagnostics.append(_diagnostic("error", kind, row_id, message, notes=f"row_index={index}"))
        seen.add(row_id)
    return diagnostics


def _flow_route_graph_diagnostics(
    flow_route_rows: list[DrainageFlowRoute],
    element_rows: list[DrainageElementRow],
) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    element_by_id = {
        str(getattr(row, "drainage_element_id", "") or "").strip(): row
        for row in list(element_rows or [])
        if str(getattr(row, "drainage_element_id", "") or "").strip()
    }
    element_ids = set(element_by_id)
    structure_refs = {
        str(getattr(row, "structure_ref", "") or "").strip()
        for row in list(element_rows or [])
        if str(getattr(row, "structure_ref", "") or "").strip()
    }
    adjacency: dict[str, list[tuple[str, str]]] = {}

    for index, row in enumerate(list(flow_route_rows or []), start=1):
        route_id = str(getattr(row, "flow_route_id", "") or "").strip()
        source_ref = route_id or f"flow-route:{index}"
        from_ref = str(getattr(row, "from_element_ref", "") or "").strip()
        to_ref = str(getattr(row, "to_element_ref", "") or "").strip()
        outlet_ref = str(getattr(row, "outlet_ref", "") or "").strip()

        if not from_ref:
            diagnostics.append(_diagnostic("error", "missing_flow_route_from_element_ref", source_ref, "Flow Route From Element is required."))
        elif from_ref not in element_ids:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_flow_route_from_element",
                    source_ref,
                    f"Flow Route From Element does not exist: {from_ref}.",
                    notes=f"from_element_ref={from_ref}",
                )
            )

        if not to_ref:
            diagnostics.append(_diagnostic("error", "missing_flow_route_to_element_ref", source_ref, "Flow Route To Element is required."))
        elif to_ref not in element_ids:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_flow_route_to_element",
                    source_ref,
                    f"Flow Route To Element does not exist: {to_ref}.",
                    notes=f"to_element_ref={to_ref}",
                )
            )

        if from_ref and to_ref and from_ref == to_ref:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "flow_route_self_loop",
                    source_ref,
                    f"Flow Route cannot connect an Element to itself: {from_ref}.",
                    notes=f"from_element_ref={from_ref};to_element_ref={to_ref}",
                )
            )

        if from_ref in element_ids and to_ref in element_ids and from_ref != to_ref:
            from_region = str(getattr(element_by_id.get(from_ref), "region_ref", "") or "").strip()
            to_region = str(getattr(element_by_id.get(to_ref), "region_ref", "") or "").strip()
            if from_region and to_region and from_region != to_region:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "flow_route_cross_region",
                        source_ref,
                        "Flow Route connects Drainage Elements assigned to different Regions.",
                        notes=f"from_element_ref={from_ref};from_region_ref={from_region};to_element_ref={to_ref};to_region_ref={to_region}",
                    )
                )

        if outlet_ref and not _known_outlet_ref(outlet_ref, element_ids=element_ids, structure_refs=structure_refs):
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_flow_route_outlet_ref",
                    source_ref,
                    f"Flow Route Outlet does not exist or is not a named external outlet: {outlet_ref}.",
                    notes=f"outlet_ref={outlet_ref}",
                )
            )

        if from_ref and to_ref and from_ref in element_ids and to_ref in element_ids and from_ref != to_ref:
            adjacency.setdefault(from_ref, []).append((to_ref, source_ref))
            to_kind = str(getattr(element_by_id.get(to_ref), "element_kind", "") or "").strip().lower()
            if not outlet_ref and to_kind != "outfall_reference":
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "flow_route_missing_outlet",
                        source_ref,
                        "Flow Route has no final Outlet context and does not end at an outfall_reference Element.",
                        notes=f"to_element_ref={to_ref};to_element_kind={to_kind}",
                    )
                )

    diagnostics.extend(_cycle_diagnostics(adjacency))
    return diagnostics


def _known_outlet_ref(outlet_ref: str, *, element_ids: set[str], structure_refs: set[str]) -> bool:
    if outlet_ref in element_ids or outlet_ref in structure_refs:
        return True
    return outlet_ref.startswith(("outfall:", "outlet:", "structure:"))


def _cycle_diagnostics(adjacency: dict[str, list[tuple[str, str]]]) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    reported: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycle_nodes = stack[stack.index(node) :] + [node] if node in stack else [node]
            key = tuple(cycle_nodes)
            if key not in reported:
                reported.add(key)
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "flow_route_cycle",
                        node,
                        "Flow Route graph contains a cycle.",
                        notes=f"chain={' -> '.join(cycle_nodes)}",
                    )
                )
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for next_node, _route_id in list(adjacency.get(node, []) or []):
            visit(next_node)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(adjacency):
        visit(node)
    return diagnostics


def _station_range_diagnostic(row: object, *, source_ref: str, kind: str, label: str) -> DiagnosticMessage | None:
    try:
        station_start = float(getattr(row, "station_start", 0.0) or 0.0)
        station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    except Exception:
        return _diagnostic("error", kind, source_ref, f"{label} station_start/station_end must be numeric.")
    if station_start >= station_end:
        return _diagnostic(
            "error",
            kind,
            source_ref,
            f"{label} station_start must be lower than station_end: {station_start:g} >= {station_end:g}.",
        )
    return None


def _region_station_ranges(region_model: RegionModel | None) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    if region_model is None:
        return ranges
    for row in list(getattr(region_model, "region_rows", []) or []):
        region_id = str(getattr(row, "region_id", "") or "").strip()
        if not region_id:
            continue
        try:
            station_start = float(getattr(row, "station_start", 0.0) or 0.0)
            station_end = float(getattr(row, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        ranges[region_id] = (min(station_start, station_end), max(station_start, station_end))
    return ranges


def _element_region_station_diagnostic(
    row: object,
    *,
    source_ref: str,
    region_ranges: dict[str, tuple[float, float]] | None,
) -> DiagnosticMessage | None:
    region_ref = str(getattr(row, "region_ref", "") or "").strip()
    if not region_ref or region_ranges is None:
        return None
    region_range = region_ranges.get(region_ref)
    if region_range is None:
        return _diagnostic(
            "warning",
            "missing_drainage_element_region_ref",
            source_ref,
            f"Drainage element references missing Region {region_ref}.",
            notes=f"region_ref={region_ref}",
        )
    try:
        station_start = float(getattr(row, "station_start", 0.0) or 0.0)
        station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    except Exception:
        return None
    lower, upper = region_range
    if station_start < lower - STATION_BOUNDARY_TOLERANCE or station_end > upper + STATION_BOUNDARY_TOLERANCE:
        return _diagnostic(
            "error",
            "drainage_element_outside_region_station_range",
            source_ref,
            (
                "Drainage element Start STA and End STA must stay inside the referenced Region boundary: "
                f"{station_start:g}-{station_end:g} outside {region_ref} {lower:g}-{upper:g}."
            ),
            notes=f"region_ref={region_ref};region_start={lower:g};region_end={upper:g};element_start={station_start:g};element_end={station_end:g}",
        )
    return None


def _element_structure_ref_diagnostic(
    row: object,
    *,
    source_ref: str,
    structure_ids: set[str] | None,
) -> DiagnosticMessage | None:
    if structure_ids is None:
        return None
    structure_ref = str(getattr(row, "structure_ref", "") or "").strip()
    if not structure_ref:
        return None
    if structure_ref not in structure_ids:
        return _diagnostic(
            "error",
            "missing_drainage_structure_ref",
            source_ref,
            f"Drainage element references missing Structure {structure_ref}.",
            notes=f"structure_ref={structure_ref}",
        )
    return None


def _diagnostic(severity: str, kind: str, source_ref: str, message: str, notes: str = "") -> DiagnosticMessage:
    note_values = [f"source_ref={str(source_ref or '')}"]
    if str(notes or ""):
        note_values.append(str(notes or ""))
    return DiagnosticMessage(
        severity=str(severity or "info"),
        kind=str(kind or "info"),
        message=str(message or ""),
        notes=";".join(note_values),
    )
