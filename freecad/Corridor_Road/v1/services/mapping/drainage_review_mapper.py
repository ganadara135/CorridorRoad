"""Drainage review output mapping for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.drainage_output import (
    DrainageElementOutputRow,
    DrainageOutput,
    DrainagePipelineGeometryOutputRow,
    DrainagePipelineJunctionOutputRow,
    DrainagePipelineNetworkOutputRow,
    DrainagePipelineSegmentOutputRow,
    DrainagePipelineSolidOutputRow,
    DrainageSummaryRow,
)
from ...models.result.drainage_pipeline import DrainagePipelineResult
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.quantity_model import QuantityModel
from ...models.source.alignment_model import AlignmentModel
from ...models.source.drainage_model import DrainageModel
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel
from ..evaluation.drainage_resolution_service import build_drainage_pipeline_result, build_drainage_pipeline_segment_candidates
from .drainage_pipeline_geometry_mapper import build_drainage_pipeline_geometry_rows
from .drainage_pipeline_network_mapper import build_drainage_pipeline_junction_rows, build_drainage_pipeline_network_rows
from .drainage_pipeline_solid_mapper import build_drainage_pipeline_solid_rows


class DrainageReviewMapper:
    """Build a read-only drainage review payload from source and result contracts."""

    def map(
        self,
        *,
        drainage_model: DrainageModel | None = None,
        alignment_model: AlignmentModel | None = None,
        station_offset_to_xy=None,
        coordinate_mode: str = "",
        region_model: RegionModel | None = None,
        structure_model: StructureModel | None = None,
        applied_section_set: AppliedSectionSet | None = None,
        quantity_model: QuantityModel | None = None,
        project_id: str = "corridorroad-v1",
    ) -> DrainageOutput:
        rows: list[DrainageElementOutputRow] = []
        rows.extend(_drainage_element_rows(drainage_model))
        pipeline_result = build_drainage_pipeline_result(drainage_model, structure_model, project_id=project_id)
        pipeline_segment_rows = _pipeline_segment_output_rows(pipeline_result)
        pipeline_geometry_rows = _pipeline_geometry_output_rows(
            pipeline_segment_rows,
            alignment_model,
            station_offset_to_xy=station_offset_to_xy,
            coordinate_mode=coordinate_mode,
        )
        pipeline_solid_rows = _pipeline_solid_output_rows(pipeline_geometry_rows)
        pipeline_network_rows = _pipeline_network_output_rows(pipeline_geometry_rows, pipeline_solid_rows)
        pipeline_junction_rows = _pipeline_junction_output_rows(pipeline_geometry_rows, pipeline_solid_rows, pipeline_segment_rows, structure_model)
        flow_route_rows = _flow_route_rows(drainage_model, pipeline_solid_rows)
        rows.extend(flow_route_rows)
        pipeline_candidate_rows = _pipeline_segment_candidate_rows(drainage_model, structure_model)
        rows.extend(pipeline_candidate_rows)
        region_rows, region_assignment_issue_count = _region_assignment_rows(drainage_model, region_model)
        rows.extend(region_rows)
        applied_rows, ditch_point_count, ditch_point_with_ref_count = _applied_section_rows(applied_section_set)
        rows.extend(applied_rows)
        quantity_rows, ditch_length, flowline_length = _quantity_rows(quantity_model)
        rows.extend(quantity_rows)
        summary_rows = [
            DrainageSummaryRow("summary:drainage-elements", "count", "Drainage elements", len(_drainage_element_ids(drainage_model)), "count"),
            DrainageSummaryRow("summary:flow-routes", "count", "Flow Routes", len(flow_route_rows), "count"),
            DrainageSummaryRow("summary:pipeline-segment-candidates", "count", "Pipeline segment candidates", len(pipeline_candidate_rows), "count"),
            DrainageSummaryRow("summary:pipeline-segments", "count", "Pipeline segments", len(pipeline_segment_rows), "count"),
            DrainageSummaryRow("summary:pipeline-geometries", "count", "Pipeline geometry rows", len(pipeline_geometry_rows), "count"),
            DrainageSummaryRow("summary:pipeline-solid-candidates", "count", "Pipeline solid candidates", len(pipeline_solid_rows), "count"),
            DrainageSummaryRow("summary:pipeline-solid-length", "length", "Pipeline solid length", _pipeline_solid_length(pipeline_solid_rows), "m"),
            DrainageSummaryRow("summary:pipeline-networks", "count", "Pipeline networks", len(pipeline_network_rows), "count"),
            DrainageSummaryRow("summary:pipeline-network-length", "length", "Pipeline network length", _pipeline_network_length(pipeline_network_rows), "m"),
            DrainageSummaryRow("summary:pipeline-junctions", "count", "Pipeline junctions", _pipeline_junction_count(pipeline_junction_rows), "count"),
            DrainageSummaryRow("summary:pipeline-terminals", "count", "Pipeline terminals", _pipeline_terminal_count(pipeline_junction_rows), "count"),
            DrainageSummaryRow("summary:region-assignments", "count", "Drainage Element Region assignments", len(region_rows), "count"),
            DrainageSummaryRow("summary:region-assignment-issues", "count", "Drainage Element Region assignment issues", region_assignment_issue_count, "count"),
            DrainageSummaryRow("summary:applied-sections", "count", "Applied Sections", _section_count(applied_section_set), "count"),
            DrainageSummaryRow("summary:ditch-surface-points", "count", "Ditch surface points", ditch_point_count, "count"),
            DrainageSummaryRow(
                "summary:ditch-surface-points-with-drainage",
                "count",
                "Ditch surface points with Drainage ref",
                ditch_point_with_ref_count,
                "count",
            ),
            DrainageSummaryRow("summary:drainage-ditch-length", "length", "Drainage ditch length", ditch_length, "m"),
            DrainageSummaryRow("summary:drainage-flowline-length", "length", "Drainage flowline length", flowline_length, "m"),
        ]
        return DrainageOutput(
            schema_version=1,
            project_id=str(project_id or getattr(drainage_model, "project_id", "") or "corridorroad-v1"),
            drainage_output_id="drainage-review:main",
            alignment_id=str(getattr(alignment_model, "alignment_id", "") or ""),
            drainage_model_id=str(getattr(drainage_model, "drainage_model_id", "") or ""),
            label="Drainage Review",
            element_rows=rows,
            pipeline_segment_rows=pipeline_segment_rows,
            pipeline_geometry_rows=pipeline_geometry_rows,
            pipeline_solid_rows=pipeline_solid_rows,
            pipeline_network_rows=pipeline_network_rows,
            pipeline_junction_rows=pipeline_junction_rows,
            summary_rows=summary_rows,
            source_refs=_source_refs(drainage_model, alignment_model, region_model, applied_section_set, quantity_model, structure_model),
            result_refs=_result_refs(pipeline_result),
        )


def _drainage_element_ids(drainage_model: DrainageModel | None) -> set[str]:
    return {
        str(getattr(row, "drainage_element_id", "") or "").strip()
        for row in list(getattr(drainage_model, "element_rows", []) or []) if str(getattr(row, "drainage_element_id", "") or "").strip()
    }


def _drainage_element_rows(drainage_model: DrainageModel | None) -> list[DrainageElementOutputRow]:
    rows: list[DrainageElementOutputRow] = []
    for row in list(getattr(drainage_model, "element_rows", []) or []):
        element_id = str(getattr(row, "drainage_element_id", "") or "").strip()
        if not element_id:
            continue
        rows.append(
            DrainageElementOutputRow(
                row_id=f"element:{_safe_id(element_id)}",
                kind="drainage_element",
                station_start=float(getattr(row, "station_start", 0.0) or 0.0),
                station_end=float(getattr(row, "station_end", 0.0) or 0.0),
                label=element_id,
                source_ref=element_id,
                notes=";".join(
                    value for value in [
                        f"kind={str(getattr(row, 'element_kind', '') or '')}",
                        f"side={str(getattr(row, 'side', '') or '')}",
                        f"region_ref={str(getattr(row, 'region_ref', '') or '')}",
                        f"assembly_component_ref={str(getattr(row, 'assembly_component_ref', '') or '')}",
                        f"policy_set_ref={str(getattr(row, 'policy_set_ref', '') or '')}",
                    ] if value.split("=", 1)[-1]
                ),
            )
        )
    return rows


def _flow_route_rows(
    drainage_model: DrainageModel | None,
    pipeline_solid_rows: list[DrainagePipelineSolidOutputRow] | None = None,
) -> list[DrainageElementOutputRow]:
    rows: list[DrainageElementOutputRow] = []
    element_by_id = {
        str(getattr(row, "drainage_element_id", "") or "").strip(): row
        for row in list(getattr(drainage_model, "element_rows", []) or [])
        if str(getattr(row, "drainage_element_id", "") or "").strip()
    }
    for index, route in enumerate(list(getattr(drainage_model, "flow_route_rows", []) or []), start=1):
        route_id = str(getattr(route, "flow_route_id", "") or "").strip() or f"flow-route:{index}"
        from_ref = str(getattr(route, "from_element_ref", "") or "").strip()
        to_ref = str(getattr(route, "to_element_ref", "") or "").strip()
        outlet_ref = str(getattr(route, "outlet_ref", "") or "").strip()
        from_element = element_by_id.get(from_ref)
        to_element = element_by_id.get(to_ref)
        chain = _route_chain_text(from_ref, to_ref, outlet_ref)
        pipeline_solid = _pipeline_solid_for_flow_route(pipeline_solid_rows, route_id)
        rows.append(
            DrainageElementOutputRow(
                row_id=f"flow-route:{_safe_id(route_id)}",
                kind="flow_route",
                station_start=_route_station_start(from_element, to_element),
                station_end=_route_station_end(from_element, to_element),
                label=route_id,
                source_ref=route_id,
                notes=";".join(
                    value
                    for value in [
                        f"from_element_ref={from_ref}",
                        f"to_element_ref={to_ref}",
                        f"outlet_ref={outlet_ref}",
                        f"risk_level={str(getattr(route, 'risk_level', '') or '')}",
                        f"direction={str(getattr(route, 'direction', '') or '')}",
                        f"chain={chain}",
                        f"from_region_ref={str(getattr(from_element, 'region_ref', '') or '')}",
                        f"to_region_ref={str(getattr(to_element, 'region_ref', '') or '')}",
                        f"from_policy_set_ref={str(getattr(from_element, 'policy_set_ref', '') or '')}",
                        f"to_policy_set_ref={str(getattr(to_element, 'policy_set_ref', '') or '')}",
                        f"pipeline_solid_status={str(getattr(pipeline_solid, 'status', '') or '')}" if pipeline_solid is not None else "",
                        f"pipeline_solid_length={float(getattr(pipeline_solid, 'length', 0.0) or 0.0):.3f}" if pipeline_solid is not None else "",
                        f"pipeline_solid_caps={int(getattr(pipeline_solid, 'cap_count', 0) or 0)}" if pipeline_solid is not None else "",
                    ]
                    if value.split("=", 1)[-1]
                ),
            )
        )
    return rows


def _pipeline_solid_for_flow_route(
    pipeline_solid_rows: list[DrainagePipelineSolidOutputRow] | None,
    flow_route_ref: str,
) -> DrainagePipelineSolidOutputRow | None:
    active_ref = str(flow_route_ref or "").strip()
    if not active_ref:
        return None
    for row in list(pipeline_solid_rows or []):
        if str(getattr(row, "flow_route_ref", "") or "").strip() == active_ref:
            return row
    return None


def _pipeline_segment_candidate_rows(
    drainage_model: DrainageModel | None,
    structure_model: StructureModel | None,
) -> list[DrainageElementOutputRow]:
    rows: list[DrainageElementOutputRow] = []
    for segment in build_drainage_pipeline_segment_candidates(drainage_model, structure_model):
        rows.append(
            DrainageElementOutputRow(
                row_id=str(getattr(segment, "segment_id", "") or ""),
                kind="pipeline_segment_candidate",
                station_start=float(getattr(segment, "station_start", 0.0) or 0.0),
                station_end=float(getattr(segment, "station_end", 0.0) or 0.0),
                label=str(getattr(segment, "flow_route_ref", "") or ""),
                source_ref=str(getattr(segment, "flow_route_ref", "") or ""),
                notes=";".join(
                    value
                    for value in [
                        f"status={str(getattr(segment, 'status', '') or '')}",
                        f"from_element_ref={str(getattr(segment, 'from_element_ref', '') or '')}",
                        f"to_element_ref={str(getattr(segment, 'to_element_ref', '') or '')}",
                        f"from_connection_point_ref={str(getattr(segment, 'from_connection_point_ref', '') or '')}",
                        f"to_connection_point_ref={str(getattr(segment, 'to_connection_point_ref', '') or '')}",
                        f"from_offset={float(getattr(segment, 'from_offset', 0.0) or 0.0):.3f}",
                        f"to_offset={float(getattr(segment, 'to_offset', 0.0) or 0.0):.3f}",
                        _optional_note("invert_start", getattr(segment, "invert_start", None)),
                        _optional_note("invert_end", getattr(segment, "invert_end", None)),
                        f"diameter={float(getattr(segment, 'diameter', 0.0) or 0.0):.3f}",
                        f"shape_kind={str(getattr(segment, 'shape_kind', '') or '')}",
                        str(getattr(segment, "notes", "") or ""),
                    ]
                    if value and value.split("=", 1)[-1]
                ),
            )
        )
    return rows


def _pipeline_segment_output_rows(pipeline_result: DrainagePipelineResult | None) -> list[DrainagePipelineSegmentOutputRow]:
    rows: list[DrainagePipelineSegmentOutputRow] = []
    for segment in list(getattr(pipeline_result, "segment_rows", []) or []):
        rows.append(
            DrainagePipelineSegmentOutputRow(
                pipeline_segment_id=str(getattr(segment, "pipeline_segment_id", "") or ""),
                flow_route_ref=str(getattr(segment, "flow_route_ref", "") or ""),
                from_element_ref=str(getattr(segment, "from_element_ref", "") or ""),
                to_element_ref=str(getattr(segment, "to_element_ref", "") or ""),
                from_connection_point_ref=str(getattr(segment, "from_connection_point_ref", "") or ""),
                to_connection_point_ref=str(getattr(segment, "to_connection_point_ref", "") or ""),
                station_start=float(getattr(segment, "station_start", 0.0) or 0.0),
                station_end=float(getattr(segment, "station_end", 0.0) or 0.0),
                from_offset=float(getattr(segment, "from_offset", 0.0) or 0.0),
                to_offset=float(getattr(segment, "to_offset", 0.0) or 0.0),
                invert_start=getattr(segment, "invert_start", None),
                invert_end=getattr(segment, "invert_end", None),
                diameter=float(getattr(segment, "diameter", 0.0) or 0.0),
                shape_kind=str(getattr(segment, "shape_kind", "") or ""),
                status=str(getattr(segment, "status", "") or ""),
                notes=str(getattr(segment, "notes", "") or ""),
            )
        )
    return rows


def _pipeline_geometry_output_rows(
    pipeline_segment_rows: list[DrainagePipelineSegmentOutputRow],
    alignment_model: AlignmentModel | None,
    *,
    station_offset_to_xy=None,
    coordinate_mode: str = "",
) -> list[DrainagePipelineGeometryOutputRow]:
    return build_drainage_pipeline_geometry_rows(
        pipeline_segment_rows,
        alignment_model=alignment_model,
        station_offset_to_xy=station_offset_to_xy,
        coordinate_mode=coordinate_mode,
    )


def _pipeline_solid_output_rows(
    pipeline_geometry_rows: list[DrainagePipelineGeometryOutputRow],
) -> list[DrainagePipelineSolidOutputRow]:
    return build_drainage_pipeline_solid_rows(pipeline_geometry_rows)


def _pipeline_network_output_rows(
    pipeline_geometry_rows: list[DrainagePipelineGeometryOutputRow],
    pipeline_solid_rows: list[DrainagePipelineSolidOutputRow],
) -> list[DrainagePipelineNetworkOutputRow]:
    return build_drainage_pipeline_network_rows(pipeline_geometry_rows, pipeline_solid_rows)


def _pipeline_junction_output_rows(
    pipeline_geometry_rows: list[DrainagePipelineGeometryOutputRow],
    pipeline_solid_rows: list[DrainagePipelineSolidOutputRow],
    pipeline_segment_rows: list[DrainagePipelineSegmentOutputRow],
    structure_model: StructureModel | None,
) -> list[DrainagePipelineJunctionOutputRow]:
    return build_drainage_pipeline_junction_rows(
        pipeline_geometry_rows,
        pipeline_solid_rows,
        pipeline_segment_rows,
        structure_model=structure_model,
    )


def _pipeline_solid_length(rows: list[DrainagePipelineSolidOutputRow]) -> float:
    return sum(float(getattr(row, "length", 0.0) or 0.0) for row in list(rows or []))


def _pipeline_network_length(rows: list[DrainagePipelineNetworkOutputRow]) -> float:
    return sum(float(getattr(row, "length", 0.0) or 0.0) for row in list(rows or []))


def _pipeline_junction_count(rows: list[DrainagePipelineJunctionOutputRow]) -> int:
    return sum(1 for row in list(rows or []) if str(getattr(row, "junction_kind", "") or "") == "junction")


def _pipeline_terminal_count(rows: list[DrainagePipelineJunctionOutputRow]) -> int:
    return sum(1 for row in list(rows or []) if str(getattr(row, "junction_kind", "") or "") == "terminal")


def _route_chain_text(from_ref: str, to_ref: str, outlet_ref: str) -> str:
    chain = [ref for ref in [from_ref, to_ref] if ref]
    if outlet_ref and outlet_ref not in chain:
        chain.append(outlet_ref)
    return " -> ".join(chain)


def _route_station_start(from_element: object | None, to_element: object | None) -> float:
    values = [
        float(getattr(row, "station_start", 0.0) or 0.0)
        for row in [from_element, to_element]
        if row is not None
    ]
    return min(values) if values else 0.0


def _route_station_end(from_element: object | None, to_element: object | None) -> float:
    values = [
        float(getattr(row, "station_end", 0.0) or 0.0)
        for row in [from_element, to_element]
        if row is not None
    ]
    return max(values) if values else 0.0


def _region_assignment_rows(
    drainage_model: DrainageModel | None,
    region_model: RegionModel | None,
) -> tuple[list[DrainageElementOutputRow], int]:
    rows: list[DrainageElementOutputRow] = []
    issue_count = 0
    known_regions = {
        str(getattr(region, "region_id", "") or "").strip(): region
        for region in list(getattr(region_model, "region_rows", []) or [])
        if str(getattr(region, "region_id", "") or "").strip()
    }
    for element in list(getattr(drainage_model, "element_rows", []) or []):
        element_id = str(getattr(element, "drainage_element_id", "") or "").strip()
        if not element_id:
            continue
        region_ref = str(getattr(element, "region_ref", "") or "").strip()
        region = known_regions.get(region_ref)
        status = "ok"
        if not region_ref:
            status = "missing_region"
        elif region_model is not None and region is None:
            status = "unknown_region"
        if status != "ok":
            issue_count += 1
        rows.append(
            DrainageElementOutputRow(
                row_id=f"region-assignment:{_safe_id(element_id)}",
                kind="region_assignment",
                station_start=float(getattr(element, "station_start", 0.0) or 0.0),
                station_end=float(getattr(element, "station_end", 0.0) or 0.0),
                label=region_ref,
                source_ref=element_id,
                notes=";".join(
                    value
                    for value in [
                        f"element_ref={element_id}",
                        f"region_ref={region_ref}",
                        f"status={status}",
                        f"region_start={float(getattr(region, 'station_start', 0.0) or 0.0):.3f}" if region is not None else "",
                        f"region_end={float(getattr(region, 'station_end', 0.0) or 0.0):.3f}" if region is not None else "",
                    ]
                    if value
                ),
            )
        )
    return rows, issue_count


def _applied_section_rows(applied_section_set: AppliedSectionSet | None) -> tuple[list[DrainageElementOutputRow], int, int]:
    rows: list[DrainageElementOutputRow] = []
    ditch_point_count = 0
    ditch_point_with_ref_count = 0
    for section in list(getattr(applied_section_set, "sections", []) or []):
        points = [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "") == "ditch_surface"
        ]
        if not points:
            continue
        refs = _unique_refs([str(getattr(point, "drainage_ref", "") or "") for point in points])
        component_refs = _unique_refs([str(getattr(point, "component_ref", "") or "") for point in points])
        sides = _unique_refs([str(getattr(point, "side", "") or "") for point in points])
        ditch_point_count += len(points)
        ditch_point_with_ref_count += sum(1 for point in points if str(getattr(point, "drainage_ref", "") or "").strip())
        station = float(getattr(section, "station", 0.0) or 0.0)
        rows.append(
            DrainageElementOutputRow(
                row_id=f"applied-section:{_safe_id(str(getattr(section, 'applied_section_id', '') or station))}",
                kind="applied_section_ditch_context",
                station_start=station,
                station_end=station,
                label=f"STA {station:.3f}",
                source_ref=str(getattr(section, "applied_section_id", "") or ""),
                notes=(
                    f"ditch_points={len(points)};"
                    f"drainage_refs={','.join(refs)};"
                    f"component_refs={','.join(component_refs)};"
                    f"sides={','.join(sides)}"
                ),
            )
        )
    return rows, ditch_point_count, ditch_point_with_ref_count


def _quantity_rows(quantity_model: QuantityModel | None) -> tuple[list[DrainageElementOutputRow], float, float]:
    rows: list[DrainageElementOutputRow] = []
    ditch_length = 0.0
    flowline_length = 0.0
    for row in list(getattr(quantity_model, "fragment_rows", []) or []):
        drainage_ref = str(getattr(row, "drainage_ref", "") or "").strip()
        if not drainage_ref:
            continue
        quantity_kind = str(getattr(row, "quantity_kind", "") or "")
        if quantity_kind not in {"drainage_ditch_length", "drainage_flowline_length"}:
            continue
        value = float(getattr(row, "value", 0.0) or 0.0)
        if quantity_kind == "drainage_ditch_length":
            ditch_length += value
        if quantity_kind == "drainage_flowline_length":
            flowline_length += value
        rows.append(
            DrainageElementOutputRow(
                row_id=f"quantity:{_safe_id(str(getattr(row, 'fragment_id', '') or drainage_ref))}",
                kind="drainage_quantity",
                station_start=float(getattr(row, "station_start", 0.0) or 0.0),
                station_end=float(getattr(row, "station_end", 0.0) or 0.0),
                label=quantity_kind,
                source_ref=drainage_ref,
                notes=(
                    f"quantity_kind={quantity_kind};"
                    f"value={value:.6g};"
                    f"unit={str(getattr(row, 'unit', '') or '')};"
                    f"component_ref={str(getattr(row, 'component_ref', '') or '')};"
                    f"flow_route_ref={str(getattr(row, 'flow_route_ref', '') or '')}"
                ),
            )
        )
    return rows, ditch_length, flowline_length


def _section_count(applied_section_set: AppliedSectionSet | None) -> int:
    return len(list(getattr(applied_section_set, "sections", []) or []))


def _source_refs(
    drainage_model: DrainageModel | None,
    alignment_model: AlignmentModel | None,
    region_model: RegionModel | None,
    applied_section_set: AppliedSectionSet | None,
    quantity_model: QuantityModel | None = None,
    structure_model: StructureModel | None = None,
) -> list[str]:
    return _unique_refs(
        [
            str(getattr(drainage_model, "drainage_model_id", "") or ""),
            str(getattr(alignment_model, "alignment_id", "") or ""),
            str(getattr(region_model, "region_model_id", "") or ""),
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            str(getattr(quantity_model, "quantity_model_id", "") or ""),
            str(getattr(structure_model, "structure_model_id", "") or ""),
        ]
    )


def _result_refs(pipeline_result: DrainagePipelineResult | None) -> list[str]:
    return _unique_refs([str(getattr(pipeline_result, "drainage_pipeline_result_id", "") or "")])


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


def _safe_id(value: str) -> str:
    return str(value or "").strip().replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "-") or "unknown"


def _optional_note(key: str, value: object) -> str:
    if value is None:
        return ""
    try:
        return f"{key}={float(value):.3f}"
    except Exception:
        return ""
