"""Simulation-readiness QA service for Watertight Solid outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.output.simulation_qa_output import (
    SimulationQaDiagnosticRow,
    SimulationQaFamilyRow,
    SimulationQaOutput,
)


@dataclass(frozen=True)
class WatertightSimulationQaSolidInput:
    """Shape/output summary consumed by the simulation QA service."""

    output_ref: str
    target_families: list[str] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)
    valid_solid_statuses: list[bool] = field(default_factory=list)
    shape_valid: bool = False
    # FreeCAD BoundBox order: XMin, XMax, YMin, YMax, ZMin, ZMax.
    bound_box: tuple[float, float, float, float, float, float] | None = None
    structure_refs: list[str] = field(default_factory=list)
    flow_route_refs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WatertightSimulationQaBuildRequest:
    """Input bundle for building a simulation-readiness QA summary."""

    project_id: str = "corridorroad-v1"
    output_refs: list[str] = field(default_factory=list)
    solid_inputs: list[WatertightSimulationQaSolidInput] = field(default_factory=list)
    terrain_ready: bool = False
    terrain_bound_box: tuple[float, float, float, float, float, float] | None = None
    simulation_qa_output_id: str = "simulation-qa:watertight-solids"


class WatertightSimulationQaService:
    """Build first-slice simulation-readiness coverage and validity reports."""

    def build(self, request: WatertightSimulationQaBuildRequest) -> SimulationQaOutput:
        inputs = list(getattr(request, "solid_inputs", []) or [])
        families: dict[str, dict[str, float | int]] = {}
        invalid_count = 0
        zero_volume_count = 0
        total_volume = 0.0
        contact_diagnostics: list[SimulationQaDiagnosticRow] = []
        for row in inputs:
            row_families = _unique_refs(getattr(row, "target_families", []) or [])
            volumes = [float(value or 0.0) for value in list(getattr(row, "volumes", []) or [])]
            if not volumes:
                volumes = [0.0]
            row_volume = sum(max(value, 0.0) for value in volumes)
            total_volume += row_volume
            if any(value <= 0.0 for value in volumes):
                zero_volume_count += 1
            valid_flags = list(getattr(row, "valid_solid_statuses", []) or [])
            if (valid_flags and not all(bool(value) for value in valid_flags)) or not bool(getattr(row, "shape_valid", False)):
                invalid_count += 1
            for family in row_families:
                bucket = families.setdefault(family, {"output_count": 0, "total_volume": 0.0})
                bucket["output_count"] = int(bucket["output_count"]) + 1
                bucket["total_volume"] = float(bucket["total_volume"]) + row_volume

        family_set = set(families)
        road_ready = "road_body_envelope" in family_set or "region_body" in family_set
        drainage_ready = any(family in family_set for family in {"lined_ditch_body", "drainage_pipeline_body", "drainage_pipeline_network_body"})
        structure_ready = "structure_body" in family_set
        terrain_ready = bool(getattr(request, "terrain_ready", False))
        solid_validity_ok = invalid_count == 0 and zero_volume_count == 0
        contact_diagnostics = _contact_diagnostics(inputs)
        contact_check_applied = _contact_check_applied(inputs)
        terrain_diagnostics = _terrain_domain_diagnostics(inputs, getattr(request, "terrain_bound_box", None))
        terrain_check_applied = terrain_ready and getattr(request, "terrain_bound_box", None) is not None
        port_diagnostics = _port_connection_diagnostics(inputs)
        port_check_applied = _port_check_applied(inputs)
        contact_error_count = sum(1 for row in contact_diagnostics if str(getattr(row, "severity", "") or "") == "error")
        contact_issue_count = len(contact_diagnostics)
        contact_ok = contact_error_count == 0
        terrain_error_count = sum(1 for row in terrain_diagnostics if str(getattr(row, "severity", "") or "") == "error")
        terrain_issue_count = len(terrain_diagnostics)
        terrain_domain_ok = terrain_error_count == 0
        port_error_count = sum(1 for row in port_diagnostics if str(getattr(row, "severity", "") or "") == "error")
        port_issue_count = len(port_diagnostics)
        port_connection_ok = port_error_count == 0
        geometry_contact_status = "ok" if contact_check_applied and contact_ok else "check" if contact_diagnostics else "not_checked"
        terrain_domain_status = "ok" if terrain_check_applied and terrain_domain_ok else "check" if terrain_diagnostics else "not_checked"
        port_connection_status = "ok" if port_check_applied and port_connection_ok else "check" if port_diagnostics else "not_checked"
        simulation_ready = bool(inputs and road_ready and terrain_ready and drainage_ready and solid_validity_ok and contact_ok and terrain_domain_ok and port_connection_ok)
        missing_contexts = []
        if not road_ready:
            missing_contexts.append("road_body")
        if not terrain_ready:
            missing_contexts.append("terrain")
        if not drainage_ready:
            missing_contexts.append("drainage")
        if not structure_ready:
            missing_contexts.append("structure")

        diagnostics = _diagnostics(
            missing_contexts=missing_contexts,
            invalid_count=invalid_count,
            zero_volume_count=zero_volume_count,
            output_count=len(inputs),
        )
        diagnostics.extend(contact_diagnostics)
        diagnostics.extend(terrain_diagnostics)
        diagnostics.extend(port_diagnostics)
        return SimulationQaOutput(
            schema_version=1,
            project_id=str(getattr(request, "project_id", "") or "corridorroad-v1"),
            simulation_qa_output_id=str(getattr(request, "simulation_qa_output_id", "") or "simulation-qa:watertight-solids"),
            source_refs=_unique_refs(getattr(request, "output_refs", []) or []),
            output_count=len(inputs),
            road_body_status="ready" if road_ready else "missing",
            terrain_status="ready" if terrain_ready else "missing",
            drainage_status="ready" if drainage_ready else "missing",
            structure_status="ready" if structure_ready else "missing",
            solid_validity_status="ok" if solid_validity_ok else "check",
            geometry_contact_status=geometry_contact_status,
            terrain_domain_status=terrain_domain_status,
            port_connection_status=port_connection_status,
            simulation_ready=simulation_ready,
            invalid_output_count=invalid_count,
            zero_volume_output_count=zero_volume_count,
            contact_issue_count=contact_issue_count,
            terrain_issue_count=terrain_issue_count,
            port_issue_count=port_issue_count,
            total_volume=total_volume,
            missing_contexts=missing_contexts,
            family_rows=[
                SimulationQaFamilyRow(
                    family=family,
                    status="ready",
                    output_count=int(values["output_count"]),
                    total_volume=float(values["total_volume"]),
                )
                for family, values in sorted(families.items())
            ],
            diagnostic_rows=diagnostics,
        )


def _diagnostics(*, missing_contexts: list[str], invalid_count: int, zero_volume_count: int, output_count: int) -> list[SimulationQaDiagnosticRow]:
    rows: list[SimulationQaDiagnosticRow] = []
    if output_count <= 0:
        rows.append(_diagnostic("error", "missing_watertight_outputs", "No Watertight Solid output objects exist."))
    for context in missing_contexts:
        severity = "warning" if context == "structure" else "error"
        rows.append(_diagnostic(severity, f"missing_{context}", f"Simulation QA is missing {context} context."))
    if invalid_count > 0:
        rows.append(_diagnostic("error", "invalid_solid_outputs", f"{invalid_count} Watertight Solid output object(s) are not valid solids."))
    if zero_volume_count > 0:
        rows.append(_diagnostic("error", "zero_volume_solid_outputs", f"{zero_volume_count} Watertight Solid output object(s) have zero volume."))
    return rows


def _contact_diagnostics(inputs: list[WatertightSimulationQaSolidInput]) -> list[SimulationQaDiagnosticRow]:
    road_rows = [
        row for row in inputs
        if _has_family(row, {"road_body_envelope", "region_body"}) and getattr(row, "bound_box", None) is not None
    ]
    if not road_rows:
        return []
    rows: list[SimulationQaDiagnosticRow] = []
    for row in inputs:
        if _has_family(row, {"drainage_pipeline_body", "drainage_pipeline_network_body", "lined_ditch_body"}):
            if not _touches_any_road(row, road_rows):
                rows.append(
                    _diagnostic(
                        "error",
                        "drainage_body_disconnected_from_road_body",
                        f"Drainage solid {row.output_ref} does not overlap or touch any road body bounding box.",
                        source_ref=str(getattr(row, "output_ref", "") or ""),
                    )
                )
        elif _has_family(row, {"structure_body"}):
            if not _touches_any_road(row, road_rows):
                rows.append(
                    _diagnostic(
                        "warning",
                        "structure_body_disconnected_from_road_body",
                        f"Structure solid {row.output_ref} does not overlap or touch any road body bounding box.",
                        source_ref=str(getattr(row, "output_ref", "") or ""),
                    )
                )
    return rows


def _contact_check_applied(inputs: list[WatertightSimulationQaSolidInput]) -> bool:
    road_has_bbox = any(_has_family(row, {"road_body_envelope", "region_body"}) and getattr(row, "bound_box", None) is not None for row in inputs)
    subject_has_bbox = any(
        _has_family(row, {"drainage_pipeline_body", "drainage_pipeline_network_body", "lined_ditch_body", "structure_body"})
        and getattr(row, "bound_box", None) is not None
        for row in inputs
    )
    return bool(road_has_bbox and subject_has_bbox)


def _terrain_domain_diagnostics(
    inputs: list[WatertightSimulationQaSolidInput],
    terrain_bound_box: tuple[float, float, float, float, float, float] | None,
) -> list[SimulationQaDiagnosticRow]:
    if terrain_bound_box is None:
        return []
    rows: list[SimulationQaDiagnosticRow] = []
    for row in inputs:
        if not _has_family(row, {"road_body_envelope", "region_body", "drainage_pipeline_body", "drainage_pipeline_network_body", "lined_ditch_body"}):
            continue
        bbox = getattr(row, "bound_box", None)
        if bbox is None:
            continue
        if _bbox_xy_overlaps(bbox, terrain_bound_box, tolerance=0.05):
            continue
        severity = "error" if _has_family(row, {"road_body_envelope", "region_body"}) else "warning"
        rows.append(
            _diagnostic(
                severity,
                "solid_outside_terrain_domain",
                f"Solid {row.output_ref} does not overlap the terrain domain bounding box in XY.",
                source_ref=str(getattr(row, "output_ref", "") or ""),
            )
        )
    return rows


def _port_connection_diagnostics(inputs: list[WatertightSimulationQaSolidInput]) -> list[SimulationQaDiagnosticRow]:
    structure_body_refs = set()
    for row in inputs:
        if _has_family(row, {"structure_body"}):
            structure_body_refs.update(_input_ref_values(getattr(row, "structure_refs", []) or []))
    rows: list[SimulationQaDiagnosticRow] = []
    for row in inputs:
        if not _has_family(row, {"drainage_pipeline_body", "drainage_pipeline_network_body"}):
            continue
        drainage_structure_refs = _input_ref_values(getattr(row, "structure_refs", []) or [])
        if not drainage_structure_refs:
            continue
        connection_refs = [
            ref for ref in _input_ref_values(getattr(row, "source_refs", []) or [])
            if ref.startswith("connection:") or ref.startswith("structure-connection:")
        ]
        if not connection_refs:
            rows.append(
                _diagnostic(
                    "error",
                    "drainage_port_connection_points_missing",
                    f"Drainage solid {row.output_ref} references Structure ports but has no connection point provenance.",
                    source_ref=str(getattr(row, "output_ref", "") or ""),
                )
            )
        missing_structure_refs = [ref for ref in drainage_structure_refs if ref not in structure_body_refs]
        if missing_structure_refs:
            rows.append(
                _diagnostic(
                    "error",
                    "drainage_structure_body_missing_for_port",
                    f"Drainage solid {row.output_ref} references Structure body ports without built structure_body outputs: {','.join(missing_structure_refs)}.",
                    source_ref=str(getattr(row, "output_ref", "") or ""),
                )
            )
    return rows


def _port_check_applied(inputs: list[WatertightSimulationQaSolidInput]) -> bool:
    return any(
        _has_family(row, {"drainage_pipeline_body", "drainage_pipeline_network_body"})
        and bool(_input_ref_values(getattr(row, "structure_refs", []) or []))
        for row in inputs
    )


def _has_family(row: WatertightSimulationQaSolidInput, families: set[str]) -> bool:
    return bool({str(value or "").strip() for value in list(getattr(row, "target_families", []) or [])} & families)


def _touches_any_road(row: WatertightSimulationQaSolidInput, road_rows: list[WatertightSimulationQaSolidInput]) -> bool:
    bbox = getattr(row, "bound_box", None)
    if bbox is None:
        return True
    return any(_bbox_overlaps(bbox, getattr(road_row, "bound_box", None), tolerance=0.05) for road_row in road_rows)


def _bbox_overlaps(
    left: tuple[float, float, float, float, float, float] | None,
    right: tuple[float, float, float, float, float, float] | None,
    *,
    tolerance: float,
) -> bool:
    if left is None or right is None:
        return True
    lx_min, lx_max, ly_min, ly_max, lz_min, lz_max = [float(value) for value in left]
    rx_min, rx_max, ry_min, ry_max, rz_min, rz_max = [float(value) for value in right]
    tol = max(float(tolerance or 0.0), 0.0)
    return (
        lx_min <= rx_max + tol and lx_max + tol >= rx_min
        and ly_min <= ry_max + tol and ly_max + tol >= ry_min
        and lz_min <= rz_max + tol and lz_max + tol >= rz_min
    )


def _bbox_xy_overlaps(
    left: tuple[float, float, float, float, float, float] | None,
    right: tuple[float, float, float, float, float, float] | None,
    *,
    tolerance: float,
) -> bool:
    if left is None or right is None:
        return True
    lx_min, lx_max, ly_min, ly_max, _lz_min, _lz_max = [float(value) for value in left]
    rx_min, rx_max, ry_min, ry_max, _rz_min, _rz_max = [float(value) for value in right]
    tol = max(float(tolerance or 0.0), 0.0)
    return lx_min <= rx_max + tol and lx_max + tol >= rx_min and ly_min <= ry_max + tol and ly_max + tol >= ry_min


def _diagnostic(severity: str, kind: str, message: str, *, source_ref: str = "") -> SimulationQaDiagnosticRow:
    return SimulationQaDiagnosticRow(
        diagnostic_id=f"simulation-qa:{kind}",
        severity=severity,
        kind=kind,
        source_ref=str(source_ref or ""),
        message=message,
    )


def _unique_refs(values) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _input_ref_values(values) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        for part in str(value or "").replace("|", ",").split(","):
            text = part.strip()
            if not text or text in seen:
                continue
            seen.add(text)
            refs.append(text)
    return refs
