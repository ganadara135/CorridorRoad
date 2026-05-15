"""Drainage resolution service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ...common.diagnostics import DiagnosticMessage
from ...models.result.drainage_pipeline import DrainagePipelineResult, DrainagePipelineSegment
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


@dataclass(frozen=True)
class DrainagePipelineSegmentCandidate:
    """Physical pipeline segment candidate resolved from a Flow Route and Structure connection points."""

    segment_id: str
    flow_route_ref: str
    from_element_ref: str = ""
    to_element_ref: str = ""
    from_connection_point_ref: str = ""
    to_connection_point_ref: str = ""
    status: str = "missing_connection_point_ref"
    station_start: float = 0.0
    station_end: float = 0.0
    from_offset: float = 0.0
    to_offset: float = 0.0
    invert_start: float | None = None
    invert_end: float | None = None
    diameter: float = 0.0
    shape_kind: str = ""
    notes: str = ""


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
        connection_point_refs = None if structure_model is None else _connection_point_ref_set(structure_model)
        connection_point_structure_refs = None if structure_model is None else _connection_point_structure_ref_map(structure_model)

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
            connection_point_diagnostic = _element_connection_point_ref_diagnostic(
                row,
                source_ref=source_ref,
                connection_point_refs=connection_point_refs,
                connection_point_structure_refs=connection_point_structure_refs,
            )
            if connection_point_diagnostic is not None:
                diagnostics.append(connection_point_diagnostic)
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


def build_drainage_pipeline_segment_candidates(
    drainage_model: DrainageModel | None,
    structure_model: StructureModel | None,
) -> list[DrainagePipelineSegmentCandidate]:
    """Resolve Flow Route rows into first-slice physical pipeline segment candidates."""

    if drainage_model is None or structure_model is None:
        return []
    element_by_id = {
        str(getattr(row, "drainage_element_id", "") or "").strip(): row
        for row in list(getattr(drainage_model, "element_rows", []) or [])
        if str(getattr(row, "drainage_element_id", "") or "").strip()
    }
    point_by_id = {
        str(getattr(row, "connection_point_id", "") or "").strip(): row
        for row in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(row, "connection_point_id", "") or "").strip()
    } if structure_model is not None else {}
    structure_by_id = {
        str(getattr(row, "structure_id", "") or "").strip(): row
        for row in list(getattr(structure_model, "structure_rows", []) or [])
        if str(getattr(row, "structure_id", "") or "").strip()
    } if structure_model is not None else {}
    points_by_structure: dict[str, list[object]] = {}
    if structure_model is not None:
        for point in list(getattr(structure_model, "connection_point_rows", []) or []):
            structure_ref = str(getattr(point, "structure_ref", "") or "").strip()
            if structure_ref:
                points_by_structure.setdefault(structure_ref, []).append(point)
    output: list[DrainagePipelineSegmentCandidate] = []
    for index, route in enumerate(list(getattr(drainage_model, "flow_route_rows", []) or []), start=1):
        route_id = str(getattr(route, "flow_route_id", "") or "").strip() or f"flow-route:{index}"
        from_ref = str(getattr(route, "from_element_ref", "") or "").strip()
        to_ref = str(getattr(route, "to_element_ref", "") or "").strip()
        segment_id = f"pipeline-segment-candidate:{_safe_ref_id(route_id)}"
        from_element = element_by_id.get(from_ref)
        to_element = element_by_id.get(to_ref)
        if from_element is None or to_element is None:
            output.append(
                DrainagePipelineSegmentCandidate(
                    segment_id=segment_id,
                    flow_route_ref=route_id,
                    from_element_ref=from_ref,
                    to_element_ref=to_ref,
                    status="missing_element",
                    notes=f"from_element_found={from_element is not None};to_element_found={to_element is not None}",
                )
            )
            continue
        if _is_capture_only_flow_route(from_element, to_element):
            output.append(
                DrainagePipelineSegmentCandidate(
                    segment_id=segment_id,
                    flow_route_ref=route_id,
                    from_element_ref=from_ref,
                    to_element_ref=to_ref,
                    status="capture_only",
                    station_start=float(getattr(from_element, "station_start", 0.0) or 0.0),
                    station_end=float(getattr(to_element, "station_end", getattr(to_element, "station_start", 0.0)) or 0.0),
                    notes=(
                        "flow_relationship=capture;"
                        f"from_kind={str(getattr(from_element, 'element_kind', '') or '')};"
                        f"to_kind={str(getattr(to_element, 'element_kind', '') or '')};"
                        "reason=ditch_to_inlet_open_channel_capture"
                    ),
                )
            )
            continue
        from_point = _element_connection_point_for_direction(
            from_element,
            point_by_id=point_by_id,
            points_by_structure=points_by_structure,
            structure_by_id=structure_by_id,
            direction="out",
        )
        to_point = _element_connection_point_for_direction(
            to_element,
            point_by_id=point_by_id,
            points_by_structure=points_by_structure,
            structure_by_id=structure_by_id,
            direction="in",
        )
        from_point_ref = str(getattr(from_point, "connection_point_id", "") or "").strip()
        to_point_ref = str(getattr(to_point, "connection_point_id", "") or "").strip()
        if not from_point_ref or not to_point_ref:
            output.append(
                DrainagePipelineSegmentCandidate(
                    segment_id=segment_id,
                    flow_route_ref=route_id,
                    from_element_ref=from_ref,
                    to_element_ref=to_ref,
                    from_connection_point_ref=from_point_ref,
                    to_connection_point_ref=to_point_ref,
                    status="missing_connection_point_ref",
                    notes=f"from_connection_point_ref={from_point_ref};to_connection_point_ref={to_point_ref}",
                )
            )
            continue
        if from_point is None or to_point is None:
            output.append(
                DrainagePipelineSegmentCandidate(
                    segment_id=segment_id,
                    flow_route_ref=route_id,
                    from_element_ref=from_ref,
                    to_element_ref=to_ref,
                    from_connection_point_ref=from_point_ref,
                    to_connection_point_ref=to_point_ref,
                    status="missing_connection_point",
                    notes=f"from_point_found={from_point is not None};to_point_found={to_point is not None}",
                )
            )
            continue
        from_station = float(getattr(from_point, "station", 0.0) or 0.0)
        to_station = float(getattr(to_point, "station", 0.0) or 0.0)
        from_diameter = float(getattr(from_point, "diameter", 0.0) or 0.0)
        to_diameter = float(getattr(to_point, "diameter", 0.0) or 0.0)
        from_shape = str(getattr(from_point, "shape_kind", "") or "").strip()
        to_shape = str(getattr(to_point, "shape_kind", "") or "").strip()
        output.append(
            DrainagePipelineSegmentCandidate(
                segment_id=segment_id,
                flow_route_ref=route_id,
                from_element_ref=from_ref,
                to_element_ref=to_ref,
                from_connection_point_ref=from_point_ref,
                to_connection_point_ref=to_point_ref,
                status="ready",
                station_start=from_station,
                station_end=to_station,
                from_offset=float(getattr(from_point, "offset", 0.0) or 0.0),
                to_offset=float(getattr(to_point, "offset", 0.0) or 0.0),
                invert_start=_optional_float(getattr(from_point, "invert_elevation", None)),
                invert_end=_optional_float(getattr(to_point, "invert_elevation", None)),
                diameter=max(from_diameter, to_diameter),
                shape_kind=from_shape or to_shape,
                notes=(
                    f"from_role={str(getattr(from_point, 'point_role', '') or '')};"
                    f"to_role={str(getattr(to_point, 'point_role', '') or '')}"
                ),
            )
        )
    return output


def build_drainage_pipeline_result(
    drainage_model: DrainageModel | None,
    structure_model: StructureModel | None,
    *,
    project_id: str = "corridorroad-v1",
) -> DrainagePipelineResult:
    """Promote ready Flow Route connection candidates into pipeline result segments."""

    candidates = build_drainage_pipeline_segment_candidates(drainage_model, structure_model)
    segment_rows: list[DrainagePipelineSegment] = []
    diagnostics: list[DiagnosticMessage] = []
    for candidate in candidates:
        status = str(getattr(candidate, "status", "") or "")
        flow_route_ref = str(getattr(candidate, "flow_route_ref", "") or "")
        if status == "capture_only":
            continue
        if status != "ready":
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "drainage_pipeline_segment_not_ready",
                    flow_route_ref,
                    "Drainage Flow Route could not be promoted into a pipeline segment.",
                    notes=f"status={status};{str(getattr(candidate, 'notes', '') or '')}",
                )
            )
            continue
        pipeline_segment_id = f"pipeline-segment:{_safe_ref_id(flow_route_ref)}"
        segment_rows.append(
            DrainagePipelineSegment(
                pipeline_segment_id=pipeline_segment_id,
                flow_route_ref=flow_route_ref,
                from_element_ref=str(getattr(candidate, "from_element_ref", "") or ""),
                to_element_ref=str(getattr(candidate, "to_element_ref", "") or ""),
                from_connection_point_ref=str(getattr(candidate, "from_connection_point_ref", "") or ""),
                to_connection_point_ref=str(getattr(candidate, "to_connection_point_ref", "") or ""),
                station_start=float(getattr(candidate, "station_start", 0.0) or 0.0),
                station_end=float(getattr(candidate, "station_end", 0.0) or 0.0),
                from_offset=float(getattr(candidate, "from_offset", 0.0) or 0.0),
                to_offset=float(getattr(candidate, "to_offset", 0.0) or 0.0),
                invert_start=_optional_float(getattr(candidate, "invert_start", None)),
                invert_end=_optional_float(getattr(candidate, "invert_end", None)),
                diameter=float(getattr(candidate, "diameter", 0.0) or 0.0),
                shape_kind=str(getattr(candidate, "shape_kind", "") or ""),
                status="ready",
                notes=str(getattr(candidate, "notes", "") or ""),
            )
        )
    return DrainagePipelineResult(
        schema_version=1,
        project_id=str(project_id or getattr(drainage_model, "project_id", "") or getattr(structure_model, "project_id", "") or "corridorroad-v1"),
        drainage_pipeline_result_id="drainage-pipeline:main",
        drainage_model_id=str(getattr(drainage_model, "drainage_model_id", "") or ""),
        structure_model_id=str(getattr(structure_model, "structure_model_id", "") or ""),
        label="Drainage Pipeline",
        segment_rows=segment_rows,
        source_refs=_unique_refs(
            [
                str(getattr(drainage_model, "drainage_model_id", "") or ""),
                str(getattr(structure_model, "structure_model_id", "") or ""),
            ]
        ),
        diagnostic_rows=diagnostics,
    )


def _is_capture_only_flow_route(from_element, to_element) -> bool:
    """Return true for open-channel capture rows that should not create pipe geometry."""

    from_kind = str(getattr(from_element, "element_kind", "") or "").strip().lower()
    to_kind = str(getattr(to_element, "element_kind", "") or "").strip().lower()
    if from_kind not in {"ditch", "gutter", "swale", "channel", "lined_ditch", "lined-ditch"}:
        return False
    if to_kind not in {"inlet", "inlet_reference", "catch_basin", "catch-basin"}:
        return False
    return True


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


def _connection_point_ref_set(structure_model: StructureModel | None) -> set[str]:
    if structure_model is None:
        return set()
    return {
        str(getattr(row, "connection_point_id", "") or "").strip()
        for row in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(row, "connection_point_id", "") or "").strip()
    }


def _connection_point_structure_ref_map(structure_model: StructureModel | None) -> dict[str, str]:
    if structure_model is None:
        return {}
    return {
        str(getattr(row, "connection_point_id", "") or "").strip(): str(getattr(row, "structure_ref", "") or "").strip()
        for row in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(row, "connection_point_id", "") or "").strip()
    }


def _element_connection_point_for_direction(
    element,
    *,
    point_by_id: dict[str, object],
    points_by_structure: dict[str, list[object]],
    structure_by_id: dict[str, object],
    direction: str,
):
    structure_ref = str(getattr(element, "structure_ref", "") or "").strip()
    explicit_ref = str(getattr(element, "connection_point_ref", "") or "").strip()
    explicit_point = point_by_id.get(explicit_ref) if explicit_ref else None
    preferred = _preferred_structure_connection_point(structure_ref, points_by_structure, direction=direction)
    structure = structure_by_id.get(structure_ref)
    if explicit_point is None:
        return _normalized_structure_endpoint_connection_point(preferred, structure=structure, direction=direction)
    if preferred is None:
        return _normalized_structure_endpoint_connection_point(explicit_point, structure=structure, direction=direction)
    if _connection_point_matches_direction(explicit_point, direction):
        return _normalized_structure_endpoint_connection_point(explicit_point, structure=structure, direction=direction)
    return _normalized_structure_endpoint_connection_point(preferred, structure=structure, direction=direction)


def _preferred_structure_connection_point(
    structure_ref: str,
    points_by_structure: dict[str, list[object]],
    *,
    direction: str,
):
    points = list(points_by_structure.get(str(structure_ref or ""), []) or [])
    if not points:
        return None
    priority = (
        ["pipe_out", "downstream", "outlet", "discharge", "pipe_junction", "pipe", "upstream", "pipe_in", "inlet"]
        if direction == "out"
        else ["pipe_in", "upstream", "inlet", "pipe_junction", "pipe", "pipe_out", "downstream", "outlet", "discharge"]
    )
    by_role: dict[str, object] = {}
    for point in points:
        role = str(getattr(point, "point_role", "") or "").strip().lower()
        if role and role not in by_role:
            by_role[role] = point
    for role in priority:
        if role in by_role:
            return by_role[role]
    return sorted(points, key=lambda point: int(getattr(point, "connection_order", 0) or 0))[0]


def _connection_point_matches_direction(point, direction: str) -> bool:
    role = str(getattr(point, "point_role", "") or "").strip().lower()
    if not role:
        return True
    if direction == "out":
        return role in {"pipe_out", "downstream", "outlet", "discharge", "pipe_junction", "pipe"}
    return role in {"pipe_in", "upstream", "inlet", "pipe_junction", "pipe"}


def _normalized_structure_endpoint_connection_point(point, *, structure, direction: str):
    if point is None or structure is None:
        return point
    if not _is_default_culvert_endpoint_point(point, structure):
        return point
    placement = getattr(structure, "placement", None)
    if placement is None:
        return point
    start = float(getattr(placement, "station_start", 0.0) or 0.0)
    end = float(getattr(placement, "station_end", start) or start)
    station = min(start, end) if direction == "in" else max(start, end)
    offset = float(getattr(placement, "offset", getattr(point, "offset", 0.0)) or 0.0)
    try:
        return replace(point, station=station, offset=offset)
    except Exception:
        return point


def _is_default_culvert_endpoint_point(point, structure) -> bool:
    kind = str(getattr(structure, "structure_kind", "") or "").strip().lower()
    native_type = str(getattr(structure, "native_type", "") or "").strip().lower()
    if kind != "culvert" and native_type not in {"box_culvert", "pipe_culvert"}:
        return False
    structure_ref = str(getattr(structure, "structure_id", "") or "").strip()
    base_id = structure_ref.split(":")[-1]
    point_id = str(getattr(point, "connection_point_id", "") or "").strip().lower()
    role = str(getattr(point, "point_role", "") or "").strip().lower()
    default_suffixes = {"pipe-in", "pipe_out", "pipe-out", "pipe_in", "upstream", "downstream"}
    has_default_id = any(point_id == f"connection:{base_id}:{suffix}".lower() for suffix in default_suffixes)
    return role in {"pipe_in", "pipe_out", "upstream", "downstream"} or has_default_id


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


def _element_connection_point_ref_diagnostic(
    row: object,
    *,
    source_ref: str,
    connection_point_refs: set[str] | None,
    connection_point_structure_refs: dict[str, str] | None,
) -> DiagnosticMessage | None:
    if connection_point_refs is None:
        return None
    connection_point_ref = str(getattr(row, "connection_point_ref", "") or "").strip()
    if not connection_point_ref:
        return None
    if connection_point_ref not in connection_point_refs:
        return _diagnostic(
            "error",
            "missing_drainage_connection_point_ref",
            source_ref,
            f"Drainage element references missing Structure connection point {connection_point_ref}.",
            notes=f"connection_point_ref={connection_point_ref}",
        )
    structure_ref = str(getattr(row, "structure_ref", "") or "").strip()
    point_structure_ref = (connection_point_structure_refs or {}).get(connection_point_ref, "")
    if structure_ref and point_structure_ref and structure_ref != point_structure_ref:
        return _diagnostic(
            "error",
            "drainage_connection_point_structure_mismatch",
            source_ref,
            "Drainage element Structure Ref and Connection Point Ref point to different Structures.",
            notes=f"structure_ref={structure_ref};connection_point_ref={connection_point_ref};connection_point_structure_ref={point_structure_ref}",
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


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_ref_id(value: str) -> str:
    return str(value or "").strip().replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "-") or "unknown"


def _unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output
