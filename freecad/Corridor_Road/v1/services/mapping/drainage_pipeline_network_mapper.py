"""Drainage pipeline network output mapping for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.drainage_output import (
    DrainagePipelineGeometryOutputRow,
    DrainagePipelineJunctionOutputRow,
    DrainagePipelineNetworkOutputRow,
    DrainagePipelineSegmentOutputRow,
    DrainagePipelineSolidOutputRow,
)
from ...models.source.structure_model import StructureModel


def build_drainage_pipeline_network_rows(
    geometry_rows: list[DrainagePipelineGeometryOutputRow],
    solid_rows: list[DrainagePipelineSolidOutputRow],
) -> list[DrainagePipelineNetworkOutputRow]:
    """Group ready Drainage pipe solid candidates into one first-slice network row."""

    solids = list(solid_rows or [])
    if not solids:
        return []
    geometry_by_id = {
        str(getattr(row, "geometry_row_id", "") or ""): row
        for row in list(geometry_rows or [])
        if str(getattr(row, "geometry_row_id", "") or "")
    }
    ready_solids = [row for row in solids if str(getattr(row, "status", "") or "") == "ready"]
    active_solids = ready_solids or solids
    active_geometry_rows = [
        geometry_by_id.get(str(getattr(row, "geometry_row_ref", "") or ""))
        for row in active_solids
    ]
    active_geometry_rows = [row for row in active_geometry_rows if row is not None]
    segment_refs = _unique_refs([str(getattr(row, "pipeline_segment_id", "") or "") for row in active_solids])
    flow_route_refs = _unique_refs([str(getattr(row, "flow_route_ref", "") or "") for row in active_solids])
    solid_refs = _unique_refs([str(getattr(row, "solid_row_id", "") or "") for row in active_solids])
    coordinate_modes = _unique_refs([str(getattr(row, "coordinate_mode", "") or "") for row in active_solids])
    ready_count = len(ready_solids)
    status = "ready"
    if ready_count <= 0:
        status = "blocked"
    elif ready_count < len(solids):
        status = "warning"
    junction_count, terminal_count = _junction_and_terminal_counts(active_geometry_rows)
    length = sum(float(getattr(row, "length", 0.0) or 0.0) for row in active_solids)
    volume = sum(float(getattr(row, "volume", 0.0) or 0.0) for row in active_solids)
    return [
        DrainagePipelineNetworkOutputRow(
            network_row_id="pipeline-network:main",
            network_id="drainage-pipeline-network:main",
            pipeline_segment_refs=segment_refs,
            flow_route_refs=flow_route_refs,
            solid_row_refs=solid_refs,
            segment_count=len(segment_refs),
            junction_count=junction_count,
            length=length,
            volume=volume,
            coordinate_mode=coordinate_modes[0] if len(coordinate_modes) == 1 else "mixed",
            validation_status=status,
            notes=(
                f"solid_count={len(active_solids)};"
                f"ready_solid_count={ready_count};"
                f"terminal_count={terminal_count};"
                "fuse_mode=compound_first_slice"
            ),
        )
    ]


def build_drainage_pipeline_junction_rows(
    geometry_rows: list[DrainagePipelineGeometryOutputRow],
    solid_rows: list[DrainagePipelineSolidOutputRow],
    segment_rows: list[DrainagePipelineSegmentOutputRow] | None = None,
    *,
    network_ref: str = "drainage-pipeline-network:main",
    structure_model: StructureModel | None = None,
) -> list[DrainagePipelineJunctionOutputRow]:
    """Build endpoint junction rows for a Drainage pipeline network."""

    solids = list(solid_rows or [])
    if not solids:
        return []
    geometry_by_id = {
        str(getattr(row, "geometry_row_id", "") or ""): row
        for row in list(geometry_rows or [])
        if str(getattr(row, "geometry_row_id", "") or "")
    }
    ready_solids = [row for row in solids if str(getattr(row, "status", "") or "") == "ready"]
    active_solids = ready_solids or solids
    segment_by_id = {
        str(getattr(row, "pipeline_segment_id", "") or ""): row
        for row in list(segment_rows or [])
        if str(getattr(row, "pipeline_segment_id", "") or "")
    }
    structure_ref_by_connection_point = {
        str(getattr(row, "connection_point_id", "") or ""): str(getattr(row, "structure_ref", "") or "")
        for row in list(getattr(structure_model, "connection_point_rows", []) or [])
        if str(getattr(row, "connection_point_id", "") or "")
    } if structure_model is not None else {}
    endpoint_data: dict[tuple[float, float, float], dict[str, object]] = {}
    for solid in active_solids:
        geometry = geometry_by_id.get(str(getattr(solid, "geometry_row_ref", "") or ""))
        if geometry is None:
            continue
        points = _points(geometry)
        if len(points) < 2:
            continue
        segment_ref = str(getattr(solid, "pipeline_segment_id", "") or "")
        flow_route_ref = str(getattr(solid, "flow_route_ref", "") or "")
        segment = segment_by_id.get(segment_ref)
        for endpoint_index, point in enumerate((points[0], points[-1])):
            key = (round(point[0], 6), round(point[1], 6), round(point[2], 6))
            data = endpoint_data.setdefault(
                key,
                {
                    "point": point,
                    "segment_refs": [],
                    "flow_route_refs": [],
                    "connection_point_refs": [],
                    "structure_refs": [],
                    "coordinate_modes": [],
                    "endpoint_indexes": [],
                },
            )
            data["segment_refs"].append(segment_ref)
            data["flow_route_refs"].append(flow_route_ref)
            connection_point_ref = _segment_endpoint_connection_point_ref(segment, endpoint_index)
            if connection_point_ref:
                data["connection_point_refs"].append(connection_point_ref)
                structure_ref = structure_ref_by_connection_point.get(connection_point_ref, "")
                if structure_ref:
                    data["structure_refs"].append(structure_ref)
            data["coordinate_modes"].append(str(getattr(solid, "coordinate_mode", "") or ""))
            data["endpoint_indexes"].append(endpoint_index)
    rows: list[DrainagePipelineJunctionOutputRow] = []
    for index, key in enumerate(sorted(endpoint_data), start=1):
        data = endpoint_data[key]
        segment_refs = _unique_refs(list(data.get("segment_refs", []) or []))
        flow_route_refs = _unique_refs(list(data.get("flow_route_refs", []) or []))
        connection_point_refs = _unique_refs(list(data.get("connection_point_refs", []) or []))
        structure_refs = _unique_refs(list(data.get("structure_refs", []) or []))
        coordinate_modes = _unique_refs(list(data.get("coordinate_modes", []) or []))
        degree = len(segment_refs)
        junction_kind = "junction" if degree > 1 else "terminal"
        point = data.get("point", key)
        rows.append(
            DrainagePipelineJunctionOutputRow(
                junction_row_id=f"pipeline-junction:{index}",
                network_ref=str(network_ref or "drainage-pipeline-network:main"),
                junction_kind=junction_kind,
                degree=degree,
                point=(float(point[0]), float(point[1]), float(point[2])),
                pipeline_segment_refs=segment_refs,
                flow_route_refs=flow_route_refs,
                coordinate_mode=coordinate_modes[0] if len(coordinate_modes) == 1 else "mixed",
                status="ready",
                notes=";".join(
                    value for value in [
                        f"endpoint_count={len(list(data.get('endpoint_indexes', []) or []))}",
                        f"connection_point_refs={','.join(connection_point_refs)}" if connection_point_refs else "",
                        f"structure_refs={','.join(structure_refs)}" if structure_refs else "",
                        "trim_status=pending",
                        "structure_connector_status=pending" if connection_point_refs else "",
                    ] if value
                ),
            )
        )
    return rows


def _segment_endpoint_connection_point_ref(segment: DrainagePipelineSegmentOutputRow | None, endpoint_index: int) -> str:
    if segment is None:
        return ""
    if int(endpoint_index or 0) == 0:
        return str(getattr(segment, "from_connection_point_ref", "") or "")
    return str(getattr(segment, "to_connection_point_ref", "") or "")


def _junction_and_terminal_counts(rows: list[DrainagePipelineGeometryOutputRow]) -> tuple[int, int]:
    endpoint_degree: dict[tuple[float, float, float], int] = {}
    for row in list(rows or []):
        points = _points(row)
        if len(points) < 2:
            continue
        for point in (points[0], points[-1]):
            key = (round(point[0], 6), round(point[1], 6), round(point[2], 6))
            endpoint_degree[key] = endpoint_degree.get(key, 0) + 1
    junction_count = sum(1 for degree in endpoint_degree.values() if degree > 1)
    terminal_count = sum(1 for degree in endpoint_degree.values() if degree == 1)
    return junction_count, terminal_count


def _points(row: DrainagePipelineGeometryOutputRow) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    for point in list(getattr(row, "centerline_points", []) or []):
        if len(point) < 3:
            continue
        try:
            output.append((float(point[0]), float(point[1]), float(point[2])))
        except Exception:
            continue
    return output


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
