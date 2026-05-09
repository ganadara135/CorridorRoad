"""Drainage review output mapping for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.drainage_output import DrainageElementOutputRow, DrainageOutput, DrainageSummaryRow
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.quantity_model import QuantityModel
from ...models.source.drainage_model import DrainageModel
from ...models.source.region_model import RegionModel


class DrainageReviewMapper:
    """Build a read-only drainage review payload from source and result contracts."""

    def map(
        self,
        *,
        drainage_model: DrainageModel | None = None,
        region_model: RegionModel | None = None,
        applied_section_set: AppliedSectionSet | None = None,
        quantity_model: QuantityModel | None = None,
        project_id: str = "corridorroad-v1",
    ) -> DrainageOutput:
        drainage_ids = _drainage_element_ids(drainage_model)
        rows: list[DrainageElementOutputRow] = []
        rows.extend(_drainage_element_rows(drainage_model))
        flow_route_rows = _flow_route_rows(drainage_model)
        rows.extend(flow_route_rows)
        region_rows, missing_region_ref_count = _region_handoff_rows(region_model, drainage_ids)
        rows.extend(region_rows)
        applied_rows, ditch_point_count, ditch_point_with_ref_count = _applied_section_rows(applied_section_set)
        rows.extend(applied_rows)
        quantity_rows, ditch_length, flowline_length = _quantity_rows(quantity_model)
        rows.extend(quantity_rows)
        summary_rows = [
            DrainageSummaryRow("summary:drainage-elements", "count", "Drainage elements", len(drainage_ids), "count"),
            DrainageSummaryRow("summary:flow-routes", "count", "Flow Routes", len(flow_route_rows), "count"),
            DrainageSummaryRow("summary:region-handoffs", "count", "Region drainage handoffs", len(region_rows), "count"),
            DrainageSummaryRow("summary:missing-region-refs", "count", "Missing Region drainage refs", missing_region_ref_count, "count"),
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
            drainage_model_id=str(getattr(drainage_model, "drainage_model_id", "") or ""),
            label="Drainage Review",
            element_rows=rows,
            summary_rows=summary_rows,
            source_refs=_source_refs(drainage_model, region_model, applied_section_set, quantity_model),
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


def _flow_route_rows(drainage_model: DrainageModel | None) -> list[DrainageElementOutputRow]:
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
                    ]
                    if value.split("=", 1)[-1]
                ),
            )
        )
    return rows


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


def _region_handoff_rows(region_model: RegionModel | None, drainage_ids: set[str]) -> tuple[list[DrainageElementOutputRow], int]:
    rows: list[DrainageElementOutputRow] = []
    missing_count = 0
    for region in list(getattr(region_model, "region_rows", []) or []):
        region_id = str(getattr(region, "region_id", "") or "").strip()
        for drainage_ref in list(getattr(region, "drainage_refs", []) or []):
            ref = str(drainage_ref or "").strip()
            if not ref:
                continue
            status = "ok" if ref in drainage_ids else "missing"
            if status == "missing":
                missing_count += 1
            rows.append(
                DrainageElementOutputRow(
                    row_id=f"region-handoff:{_safe_id(region_id)}:{_safe_id(ref)}",
                    kind="region_handoff",
                    station_start=float(getattr(region, "station_start", 0.0) or 0.0),
                    station_end=float(getattr(region, "station_end", 0.0) or 0.0),
                    label=region_id,
                    source_ref=region_id,
                    notes=f"drainage_ref={ref};status={status}",
                )
            )
    return rows, missing_count


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
    region_model: RegionModel | None,
    applied_section_set: AppliedSectionSet | None,
    quantity_model: QuantityModel | None = None,
) -> list[str]:
    return _unique_refs(
        [
            str(getattr(drainage_model, "drainage_model_id", "") or ""),
            str(getattr(region_model, "region_model_id", "") or ""),
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            str(getattr(quantity_model, "quantity_model_id", "") or ""),
        ]
    )


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
