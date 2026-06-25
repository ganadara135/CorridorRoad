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
    # Segment order: X1, Y1, X2, Y2. Used for first-slice contact edge diagnostics.
    edge_xy_segments: list[tuple[float, float, float, float]] = field(default_factory=list)
    subassembly_refs: list[str] = field(default_factory=list)
    structure_refs: list[str] = field(default_factory=list)
    flow_route_refs: list[str] = field(default_factory=list)
    material_refs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WatertightSimulationQaBuildRequest:
    """Input bundle for building a simulation-readiness QA summary."""

    project_id: str = "corridorroad-v1"
    output_refs: list[str] = field(default_factory=list)
    solid_inputs: list[WatertightSimulationQaSolidInput] = field(default_factory=list)
    terrain_ready: bool = False
    terrain_bound_box: tuple[float, float, float, float, float, float] | None = None
    intersection_trim: dict[str, object] = field(default_factory=dict)
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
        road_ready = "road_body_envelope" in family_set or "region_body" in family_set or "intersection_patch_body" in family_set
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
        traceability_diagnostics = _traceability_diagnostics(inputs)
        traceability_error_count = sum(1 for row in traceability_diagnostics if str(getattr(row, "severity", "") or "") == "error")
        traceability_ok = traceability_error_count == 0
        intersection_trim = dict(getattr(request, "intersection_trim", {}) or {})
        intersection_trim_status = _trim_text(intersection_trim, "status", "not_available")
        intersection_trim_fuse_status = _trim_text(intersection_trim, "fuse_status", "not_available")
        intersection_trim_ready_pair_count = _trim_int(intersection_trim, "ready_pair_count")
        intersection_trim_blocked_pair_count = _trim_int(intersection_trim, "blocked_pair_count")
        intersection_trim_max_gap = _intersection_trim_max_gap(intersection_trim)
        intersection_trim_handoff_status = resolve_intersection_trim_handoff_status(
            status=intersection_trim_status,
            fuse_status=intersection_trim_fuse_status,
            ready_pair_count=intersection_trim_ready_pair_count,
            blocked_pair_count=intersection_trim_blocked_pair_count,
        )
        geometry_contact_status = "ok" if contact_check_applied and contact_ok else "check" if contact_diagnostics else "not_checked"
        terrain_domain_status = "ok" if terrain_check_applied and terrain_domain_ok else "check" if terrain_diagnostics else "not_checked"
        port_connection_status = "ok" if port_check_applied and port_connection_ok else "check" if port_diagnostics else "not_checked"
        simulation_ready = bool(inputs and road_ready and terrain_ready and drainage_ready and solid_validity_ok and contact_ok and terrain_domain_ok and port_connection_ok and traceability_ok)
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
        diagnostics.extend(traceability_diagnostics)
        diagnostics.extend(_intersection_trim_diagnostics(intersection_trim, handoff_status=intersection_trim_handoff_status))
        return SimulationQaOutput(
            schema_version=1,
            project_id=str(getattr(request, "project_id", "") or "corridorroad-v1"),
            simulation_qa_output_id=str(getattr(request, "simulation_qa_output_id", "") or "simulation-qa:watertight-solids"),
            source_refs=_simulation_source_refs(
                getattr(request, "output_refs", []) or [],
                inputs,
            ),
            output_count=len(inputs),
            road_body_status="ready" if road_ready else "missing",
            terrain_status="ready" if terrain_ready else "missing",
            drainage_status="ready" if drainage_ready else "missing",
            structure_status="ready" if structure_ready else "missing",
            solid_validity_status="ok" if solid_validity_ok else "check",
            geometry_contact_status=geometry_contact_status,
            terrain_domain_status=terrain_domain_status,
            port_connection_status=port_connection_status,
            intersection_trim_status=intersection_trim_status,
            intersection_trim_fuse_status=intersection_trim_fuse_status,
            intersection_trim_handoff_status=intersection_trim_handoff_status,
            simulation_ready=simulation_ready,
            invalid_output_count=invalid_count,
            zero_volume_output_count=zero_volume_count,
            contact_issue_count=contact_issue_count,
            terrain_issue_count=terrain_issue_count,
            port_issue_count=port_issue_count,
            intersection_trim_ready_pair_count=intersection_trim_ready_pair_count,
            intersection_trim_blocked_pair_count=intersection_trim_blocked_pair_count,
            intersection_trim_max_gap=intersection_trim_max_gap,
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


def resolve_intersection_trim_handoff_status(
    *,
    status: str,
    fuse_status: str,
    ready_pair_count: int,
    blocked_pair_count: int,
) -> str:
    if status in {"", "not_available"}:
        return "not_available"
    if ready_pair_count <= 0:
        return "blocked"
    if blocked_pair_count > 0:
        return "check"
    if fuse_status == "fused":
        return "accepted"
    if fuse_status in {"compound_candidate", "fuse_failed_compound"}:
        return "fallback"
    return "check"


def _intersection_trim_diagnostics(values: dict[str, object], *, handoff_status: str) -> list[SimulationQaDiagnosticRow]:
    if not values or handoff_status == "not_available":
        return []
    status = _trim_text(values, "status", "not_available")
    result_ref = _trim_text(values, "result_ref", "")
    ready_count = _trim_int(values, "ready_pair_count")
    blocked_count = _trim_int(values, "blocked_pair_count")
    fuse_status = _trim_text(values, "fuse_status", "not_available")
    max_gap = _intersection_trim_max_gap(values)
    notes = (
        f"status={status}; ready_pairs={ready_count}; blocked_pairs={blocked_count}; "
        f"max_gap={max_gap:.3f}; fuse_status={fuse_status}; handoff={handoff_status}"
    )
    if handoff_status == "accepted":
        return [
            _diagnostic(
                "info",
                "intersection_trim_handoff_accepted",
                "Intersection trim/fuse handoff has an accepted fused candidate.",
                source_ref=result_ref,
                notes=notes,
            )
        ]
    if handoff_status == "fallback":
        return [
            _diagnostic(
                "warning",
                "intersection_trim_handoff_fallback",
                "Intersection trim/fuse handoff uses a fallback or compound candidate.",
                source_ref=result_ref,
                notes=notes,
            )
        ]
    return [
        _diagnostic(
            "warning",
            "intersection_trim_handoff_check",
            "Intersection trim/fuse handoff needs review before final simulation handoff.",
            source_ref=result_ref,
            notes=notes,
        )
    ]


def _traceability_diagnostics(inputs: list[WatertightSimulationQaSolidInput]) -> list[SimulationQaDiagnosticRow]:
    rows: list[SimulationQaDiagnosticRow] = []
    for row in list(inputs or []):
        output_ref = str(getattr(row, "output_ref", "") or "")
        families = _unique_refs(getattr(row, "target_families", []) or [])
        if not families:
            rows.append(
                _diagnostic(
                    "error",
                    "solid_output_missing_target_family",
                    f"Watertight Solid output {output_ref or '-'} has no target family contract; target_families is required for Digital Twin traceability.",
                    source_ref=output_ref,
                )
            )
        source_refs = _unique_refs(
            list(getattr(row, "subassembly_refs", []) or [])
            + list(getattr(row, "structure_refs", []) or [])
            + list(getattr(row, "flow_route_refs", []) or [])
            + list(getattr(row, "source_refs", []) or [])
        )
        if families and not source_refs:
            rows.append(
                _diagnostic(
                    "warning",
                    "solid_output_missing_source_refs",
                    f"Watertight Solid output {output_ref or '-'} has target family contract but no source/result refs for Digital Twin traceability.",
                    source_ref=output_ref,
                )
            )
    return rows


def _simulation_source_refs(output_refs: object, inputs: list[WatertightSimulationQaSolidInput]) -> list[str]:
    refs: list[str] = [str(ref or "") for ref in list(output_refs or [])]
    for row in list(inputs or []):
        refs.extend(str(ref or "") for ref in list(getattr(row, "subassembly_refs", []) or []))
        refs.extend(str(ref or "") for ref in list(getattr(row, "structure_refs", []) or []))
        refs.extend(str(ref or "") for ref in list(getattr(row, "flow_route_refs", []) or []))
        refs.extend(str(ref or "") for ref in list(getattr(row, "source_refs", []) or []))
    return _unique_refs(refs)


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
        elif _has_family(row, {"intersection_patch_body"}):
            nearest_gap = _nearest_xy_gap_to_road(row, road_rows)
            nearest_edge_gap = _nearest_edge_xy_gap_to_road(row, road_rows)
            trim_candidate_count = _nearby_edge_pair_count(row, road_rows, tolerance=0.05)
            if not _touches_any_road(row, road_rows):
                rows.append(
                    _diagnostic(
                        "error",
                        "intersection_patch_disconnected_from_road_body",
                        (
                            f"Intersection patch solid {row.output_ref} does not overlap or touch any road body bounding box; "
                            f"{_nearest_xy_gap_message(nearest_gap)}, {_nearest_edge_xy_gap_message(nearest_edge_gap)}."
                        ),
                        source_ref=str(getattr(row, "output_ref", "") or ""),
                    )
                )
            elif nearest_edge_gap is not None and nearest_edge_gap > 0.05:
                rows.append(
                    _diagnostic(
                        "warning",
                        "intersection_patch_edge_pair_gap",
                        (
                            f"Intersection patch solid {row.output_ref} overlaps/touches a road body bounding box, "
                            f"but the nearest patch/road edge pair has {_nearest_edge_xy_gap_message(nearest_edge_gap)}."
                        ),
                        source_ref=str(getattr(row, "output_ref", "") or ""),
                    )
                )
            elif trim_candidate_count > 0:
                rows.append(
                    _diagnostic(
                        "info",
                        "intersection_patch_trim_candidate",
                        (
                            f"Intersection patch solid {row.output_ref} has candidate patch/road edge pair(s) for future clip/trim; "
                            f"candidate_edge_pairs={trim_candidate_count}, {_nearest_edge_xy_gap_message(nearest_edge_gap)}, tolerance=0.050."
                        ),
                        source_ref=str(getattr(row, "output_ref", "") or ""),
                    )
                )
            if not _intersection_patch_shares_road_region_context(row, road_rows):
                patch_regions = _source_region_refs(getattr(row, "source_refs", []) or [])
                road_regions = _road_region_refs(road_rows)
                rows.append(
                    _diagnostic(
                        "error",
                        "intersection_patch_region_context_mismatch",
                        (
                            f"Intersection patch solid {row.output_ref} does not share any control Region source ref with built road/region body outputs; "
                            f"patch_regions={_ref_list_message(patch_regions)}, road_regions={_ref_list_message(road_regions)}, "
                            f"{_nearest_xy_gap_message(nearest_gap)}, {_nearest_edge_xy_gap_message(nearest_edge_gap)}."
                        ),
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
        _has_family(row, {"drainage_pipeline_body", "drainage_pipeline_network_body", "lined_ditch_body", "intersection_patch_body", "structure_body"})
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
        if not _has_family(row, {"road_body_envelope", "region_body", "intersection_patch_body", "drainage_pipeline_body", "drainage_pipeline_network_body", "lined_ditch_body"}):
            continue
        bbox = getattr(row, "bound_box", None)
        if bbox is None:
            continue
        if _bbox_xy_overlaps(bbox, terrain_bound_box, tolerance=0.05):
            continue
        severity = "error" if _has_family(row, {"road_body_envelope", "region_body", "intersection_patch_body"}) else "warning"
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


def _nearest_xy_gap_to_road(
    row: WatertightSimulationQaSolidInput,
    road_rows: list[WatertightSimulationQaSolidInput],
) -> float | None:
    bbox = getattr(row, "bound_box", None)
    if bbox is None:
        return None
    gaps = [
        _bbox_xy_gap(bbox, getattr(road_row, "bound_box", None))
        for road_row in road_rows
        if getattr(road_row, "bound_box", None) is not None
    ]
    if not gaps:
        return None
    return min(gaps)


def _nearest_edge_xy_gap_to_road(
    row: WatertightSimulationQaSolidInput,
    road_rows: list[WatertightSimulationQaSolidInput],
) -> float | None:
    patch_segments = _edge_xy_segments(row)
    if not patch_segments:
        return None
    road_segments: list[tuple[float, float, float, float]] = []
    for road_row in road_rows:
        road_segments.extend(_edge_xy_segments(road_row))
    if not road_segments:
        return None
    min_gap: float | None = None
    for patch_segment in patch_segments:
        for road_segment in road_segments:
            gap = _segment_xy_distance(patch_segment, road_segment)
            if min_gap is None or gap < min_gap:
                min_gap = gap
                if min_gap <= 0.0:
                    return 0.0
    return min_gap


def _nearby_edge_pair_count(
    row: WatertightSimulationQaSolidInput,
    road_rows: list[WatertightSimulationQaSolidInput],
    *,
    tolerance: float,
) -> int:
    patch_segments = _edge_xy_segments(row)
    if not patch_segments:
        return 0
    road_segments: list[tuple[float, float, float, float]] = []
    for road_row in road_rows:
        road_segments.extend(_edge_xy_segments(road_row))
    if not road_segments:
        return 0
    tol = max(float(tolerance or 0.0), 0.0)
    count = 0
    for patch_segment in patch_segments:
        for road_segment in road_segments:
            if _segment_xy_distance(patch_segment, road_segment) <= tol:
                count += 1
    return count


def _edge_xy_segments(row: WatertightSimulationQaSolidInput) -> list[tuple[float, float, float, float]]:
    segments: list[tuple[float, float, float, float]] = []
    for value in list(getattr(row, "edge_xy_segments", []) or []):
        try:
            x1, y1, x2, y2 = [float(part) for part in value]
        except Exception:
            continue
        if (x1, y1) == (x2, y2):
            continue
        segments.append((x1, y1, x2, y2))
    return segments


def _intersection_patch_shares_road_region_context(
    row: WatertightSimulationQaSolidInput,
    road_rows: list[WatertightSimulationQaSolidInput],
) -> bool:
    patch_regions = _source_region_refs(getattr(row, "source_refs", []) or [])
    road_regions = _road_region_refs(road_rows)
    if not patch_regions or not road_regions:
        return True
    return bool(patch_regions & road_regions)


def _road_region_refs(road_rows: list[WatertightSimulationQaSolidInput]) -> set[str]:
    road_regions: set[str] = set()
    for road in road_rows:
        road_regions.update(_source_region_refs(getattr(road, "source_refs", []) or []))
    return road_regions


def _source_region_refs(values) -> set[str]:
    return {
        ref for ref in _input_ref_values(values)
        if ref.startswith("region:")
    }


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


def _bbox_xy_gap(
    left: tuple[float, float, float, float, float, float] | None,
    right: tuple[float, float, float, float, float, float] | None,
) -> float | None:
    if left is None or right is None:
        return None
    lx_min, lx_max, ly_min, ly_max, _lz_min, _lz_max = [float(value) for value in left]
    rx_min, rx_max, ry_min, ry_max, _rz_min, _rz_max = [float(value) for value in right]
    dx = max(rx_min - lx_max, lx_min - rx_max, 0.0)
    dy = max(ry_min - ly_max, ly_min - ry_max, 0.0)
    return (dx * dx + dy * dy) ** 0.5


def _nearest_xy_gap_message(gap: float | None) -> str:
    if gap is None:
        return "nearest_xy_gap=unknown"
    return f"nearest_xy_gap={gap:.3f}"


def _nearest_edge_xy_gap_message(gap: float | None) -> str:
    if gap is None:
        return "nearest_edge_xy_gap=unknown"
    return f"nearest_edge_xy_gap={gap:.3f}"


def _segment_xy_distance(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    ax, ay, bx, by = [float(value) for value in left]
    cx, cy, dx, dy = [float(value) for value in right]
    if _segments_xy_intersect((ax, ay), (bx, by), (cx, cy), (dx, dy)):
        return 0.0
    return min(
        _point_to_segment_xy_distance((ax, ay), (cx, cy), (dx, dy)),
        _point_to_segment_xy_distance((bx, by), (cx, cy), (dx, dy)),
        _point_to_segment_xy_distance((cx, cy), (ax, ay), (bx, by)),
        _point_to_segment_xy_distance((dx, dy), (ax, ay), (bx, by)),
    )


def _segments_xy_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    def orient(p, q, r) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p, q, r) -> bool:
        return (
            min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9
            and min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9
        )

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    if (o1 > 0.0) != (o2 > 0.0) and (o3 > 0.0) != (o4 > 0.0):
        return True
    if abs(o1) <= 1e-9 and on_segment(a, c, b):
        return True
    if abs(o2) <= 1e-9 and on_segment(a, d, b):
        return True
    if abs(o3) <= 1e-9 and on_segment(c, a, d):
        return True
    if abs(o4) <= 1e-9 and on_segment(c, b, d):
        return True
    return False


def _point_to_segment_xy_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    nx = sx + t * dx
    ny = sy + t * dy
    return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5


def _ref_list_message(values: set[str]) -> str:
    refs = sorted(str(value or "").strip() for value in values if str(value or "").strip())
    return ",".join(refs) if refs else "-"


def _trim_text(values: dict[str, object], key: str, default: str = "") -> str:
    return str(values.get(key, default) or default)


def _trim_int(values: dict[str, object], key: str) -> int:
    try:
        return int(values.get(key, 0) or 0)
    except Exception:
        return 0


def _intersection_trim_max_gap(values: dict[str, object]) -> float:
    gaps: list[float] = []
    for row in list(values.get("pair_rows", []) or []):
        if not isinstance(row, dict):
            continue
        try:
            gaps.append(float(row.get("distance_xy", 0.0) or 0.0))
        except Exception:
            continue
    return max(gaps) if gaps else 0.0


def _diagnostic(severity: str, kind: str, message: str, *, source_ref: str = "", notes: str = "") -> SimulationQaDiagnosticRow:
    return SimulationQaDiagnosticRow(
        diagnostic_id=f"simulation-qa:{kind}",
        severity=severity,
        kind=kind,
        source_ref=str(source_ref or ""),
        message=message,
        notes=str(notes or ""),
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
