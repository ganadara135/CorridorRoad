"""Build typed roundabout TIN surfaces from accepted Intersection contracts."""

from __future__ import annotations

import math

from ...models.result.applied_section_set import AppliedSectionSet
from ...services.geometry import (
    xy_distance,
    xy_polygon_signed_area,
    xyz_point,
)
from ..evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
    IntersectionPatchPrerequisiteResult,
)
from ..evaluation.intersection_patch_shape_quality_service import (
    IntersectionPatchShapeQualityRequest,
    IntersectionPatchShapeQualityService,
)


def _station_ordered_applied_sections(applied_section_set) -> list[object]:
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    output: list[object] = []
    for row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda item: float(getattr(item, "station", 0.0) or 0.0),
    ):
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None:
            output.append(section)
    if output:
        return output
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=lambda section: _section_station(section))


def _section_station(section) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
    except Exception:
        try:
            return float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            return 0.0


def _roundabout_boundary_center_from_loops(boundary_loops) -> tuple[float, float, float]:
    points: list[tuple[float, float, float]] = []
    for row in list(getattr(boundary_loops, "loop_rows", []) or []):
        if str(getattr(row, "loop_role", "") or "") != "roundabout_circulatory_outer_boundary":
            continue
        points.extend(_roundabout_open_loop_points(tuple(getattr(row, "loop_points_xyz", ()) or ())))
    if not points:
        return (0.0, 0.0, 0.0)
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
        sum(point[2] for point in points) / len(points),
    )


def _xyz_tuple(point) -> tuple[float, float, float]:
    return xyz_point(point)


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"


def _intersection_patch_sections(applied_section_set, prerequisite: IntersectionPatchPrerequisiteResult) -> list[object]:
    control_refs = set(str(value or "") for value in list(getattr(prerequisite, "control_region_refs", ()) or ()) if str(value or ""))
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    return [
        section for section in _station_ordered_applied_sections(applied_section_set)
        if (
            (intersection_id and str(getattr(section, "active_intersection_id", "") or "") == intersection_id)
            or (str(getattr(section, "region_id", "") or "") in control_refs)
        )
    ]


def _unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _xy_polygon_area(points: list[tuple[float, float]]) -> float:
    return xy_polygon_signed_area(points)


def build_roundabout_circulatory_surface_tin(
    *,
    project_id: str,
    corridor_model,
    applied_section_set,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    surface_id: str,
):
    """Build a source-policy annular TIN for the roundabout circulatory roadway."""

    from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    service = IntersectionEvaluationService()
    edge_network = service.evaluate_edge_network(intersection_model, intersection_id=intersection_id)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network, intersection_id=intersection_id)
    boundary_loops = service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, intersection_id=intersection_id)
    loop_by_role = {
        str(getattr(row, "loop_role", "") or ""): row
        for row in list(getattr(boundary_loops, "loop_rows", []) or [])
        if str(getattr(row, "loop_role", "") or "")
    }
    inner_loop = loop_by_role.get("roundabout_central_island_boundary")
    outer_loop = loop_by_role.get("roundabout_circulatory_outer_boundary")
    if inner_loop is None or outer_loop is None:
        raise ValueError("roundabout_circulatory_surface_boundary_missing: island and outer loops are required.")
    inner_points = _roundabout_open_loop_points(tuple(getattr(inner_loop, "loop_points_xyz", ()) or ()))
    outer_points = _roundabout_open_loop_points(tuple(getattr(outer_loop, "loop_points_xyz", ()) or ()))
    if len(inner_points) < 3 or len(outer_points) < 3:
        raise ValueError("roundabout_circulatory_surface_boundary_too_few_points: island and outer loops require at least three points.")
    segment_count = min(len(inner_points), len(outer_points))
    inner_points = inner_points[:segment_count]
    outer_points = outer_points[:segment_count]
    if segment_count < 3:
        raise ValueError("roundabout_circulatory_surface_segment_count_too_low: at least three paired radial samples are required.")

    z_value = _roundabout_circulatory_reference_z(applied_section_set, prerequisite)
    vertices: list[TINVertex] = []
    for index, point in enumerate(inner_points, start=1):
        vertices.append(
            TINVertex(
                vertex_id=f"ri{index:02d}",
                x=float(point[0]),
                y=float(point[1]),
                z=z_value,
                source_point_ref=f"{getattr(inner_loop, 'loop_id', '')}:point:{index:02d}",
                notes="roundabout central island boundary",
            )
        )
    for index, point in enumerate(outer_points, start=1):
        vertices.append(
            TINVertex(
                vertex_id=f"ro{index:02d}",
                x=float(point[0]),
                y=float(point[1]),
                z=z_value,
                source_point_ref=f"{getattr(outer_loop, 'loop_id', '')}:point:{index:02d}",
                notes="roundabout circulatory outer boundary",
            )
        )
    triangles: list[TINTriangle] = []
    for index in range(segment_count):
        next_index = (index + 1) % segment_count
        inner_a = f"ri{index + 1:02d}"
        inner_b = f"ri{next_index + 1:02d}"
        outer_a = f"ro{index + 1:02d}"
        outer_b = f"ro{next_index + 1:02d}"
        triangles.append(
            TINTriangle(
                triangle_id=f"rt{len(triangles) + 1:03d}",
                v1=inner_a,
                v2=outer_a,
                v3=outer_b,
                triangle_kind="roundabout_circulatory_surface",
                quality_ref="roundabout_annular_strip",
                notes="roundabout annular radial strip",
            )
        )
        triangles.append(
            TINTriangle(
                triangle_id=f"rt{len(triangles) + 1:03d}",
                v1=inner_a,
                v2=outer_b,
                v3=inner_b,
                triangle_kind="roundabout_circulatory_surface",
                quality_ref="roundabout_annular_strip",
                notes="roundabout annular radial strip",
            )
        )

    shape_quality = _intersection_patch_shape_quality(vertices, triangles)
    inner_area = float(getattr(inner_loop, "area_xy", 0.0) or 0.0)
    outer_area = float(getattr(outer_loop, "area_xy", 0.0) or 0.0)
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        surface_id=surface_id,
        surface_kind="intersection_surface",
        label=f"Roundabout Circulatory Surface - {intersection_id or getattr(corridor_model, 'corridor_id', '')}",
        source_refs=[
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            intersection_id,
            str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
            str(getattr(inner_loop, "loop_id", "") or ""),
            str(getattr(outer_loop, "loop_id", "") or ""),
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=[
            str(getattr(inner_loop, "loop_id", "") or f"{surface_id}:central-island"),
            str(getattr(outer_loop, "loop_id", "") or f"{surface_id}:circulatory-outer"),
        ],
        quality_rows=[
            TINQualityRow(f"{surface_id}:patch_boundary_point_count", "patch_boundary_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_source", "patch_boundary_source", "roundabout_boundary_loop"),
            TINQualityRow(f"{surface_id}:participating_alignment_count", "participating_alignment_count", int(getattr(prerequisite, "participating_alignment_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:control_region_count", "control_region_count", int(getattr(prerequisite, "control_region_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:tie_in_edge_count", "tie_in_edge_count", int(getattr(prerequisite, "tie_in_edge_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:patch_triangle_count", "patch_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:patch_degenerate_triangle_count", "patch_degenerate_triangle_count", 0, "count"),
            TINQualityRow(f"{surface_id}:patch_triangulation_mode", "patch_triangulation_mode", "roundabout_annular_strip"),
            TINQualityRow(f"{surface_id}:patch_surface_boundary_strategy", "patch_surface_boundary_strategy", "roundabout_authoritative_boundary_loops"),
            TINQualityRow(f"{surface_id}:patch_structured_strip_count", "patch_structured_strip_count", segment_count, "count"),
            TINQualityRow(f"{surface_id}:roundabout_central_island_point_count", "roundabout_central_island_point_count", len(inner_points), "count"),
            TINQualityRow(f"{surface_id}:roundabout_circulatory_outer_point_count", "roundabout_circulatory_outer_point_count", len(outer_points), "count"),
            TINQualityRow(f"{surface_id}:roundabout_annular_triangle_count", "roundabout_annular_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_annular_inner_area", "roundabout_annular_inner_area", inner_area, "m2"),
            TINQualityRow(f"{surface_id}:roundabout_annular_outer_area", "roundabout_annular_outer_area", outer_area, "m2"),
            TINQualityRow(f"{surface_id}:roundabout_annular_ring_area", "roundabout_annular_ring_area", max(0.0, outer_area - inner_area), "m2"),
            TINQualityRow(f"{surface_id}:intersection_grading_mode", "intersection_grading_mode", "roundabout_radial_crossfall"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_x", "patch_boundary_bbox_x", float(shape_quality["bbox_x"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_y", "patch_boundary_bbox_y", float(shape_quality["bbox_y"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_aspect_ratio", "patch_boundary_bbox_aspect_ratio", float(shape_quality["bbox_aspect_ratio"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_min_quality", "patch_triangle_min_quality", float(shape_quality["triangle_min_quality"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_skinny_count", "patch_triangle_skinny_count", int(shape_quality["skinny_triangle_count"]), "count"),
            TINQualityRow(f"{surface_id}:authoritative_boundary_loop_source", "authoritative_boundary_loop_source", "roundabout_boundary_loop"),
            TINQualityRow(f"{surface_id}:authoritative_boundary_loop_point_count", "authoritative_boundary_loop_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:authoritative_boundary_loop_segment_count", "authoritative_boundary_loop_segment_count", segment_count * 2, "count"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{surface_id}:provenance:roundabout-boundary-loops",
                source_kind="roundabout_boundary_loop_contract",
                source_ref=str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
                notes=f"intersection={intersection_id}; segments={segment_count}",
            )
        ],
    )


def build_roundabout_apron_surface_tin(
    *,
    project_id: str,
    corridor_model,
    applied_section_set,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    surface_id: str,
):
    """Build a source-policy annular TIN for the roundabout truck apron / outer shoulder band."""

    from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    service = IntersectionEvaluationService()
    edge_network = service.evaluate_edge_network(intersection_model, intersection_id=intersection_id)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network, intersection_id=intersection_id)
    boundary_loops = service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, intersection_id=intersection_id)
    loop_by_role = {
        str(getattr(row, "loop_role", "") or ""): row
        for row in list(getattr(boundary_loops, "loop_rows", []) or [])
        if str(getattr(row, "loop_role", "") or "")
    }
    inner_loop = loop_by_role.get("roundabout_circulatory_outer_boundary")
    outer_loop = loop_by_role.get("roundabout_outer_ownership_boundary")
    if inner_loop is None or outer_loop is None:
        raise ValueError("roundabout_apron_surface_boundary_missing: circulatory outer and ownership outer loops are required.")
    inner_points = _roundabout_open_loop_points(tuple(getattr(inner_loop, "loop_points_xyz", ()) or ()))
    outer_points = _roundabout_open_loop_points(tuple(getattr(outer_loop, "loop_points_xyz", ()) or ()))
    if len(inner_points) < 3 or len(outer_points) < 3:
        raise ValueError("roundabout_apron_surface_boundary_too_few_points: apron loops require at least three points.")
    segment_count = min(len(inner_points), len(outer_points))
    inner_points = inner_points[:segment_count]
    outer_points = outer_points[:segment_count]
    if segment_count < 3:
        raise ValueError("roundabout_apron_surface_segment_count_too_low: at least three paired radial samples are required.")

    z_value = _roundabout_circulatory_reference_z(applied_section_set, prerequisite)
    vertices: list[TINVertex] = []
    for index, point in enumerate(inner_points, start=1):
        vertices.append(
            TINVertex(
                vertex_id=f"rai{index:02d}",
                x=float(point[0]),
                y=float(point[1]),
                z=z_value,
                source_point_ref=f"{getattr(inner_loop, 'loop_id', '')}:point:{index:02d}",
                notes="roundabout apron inner boundary",
            )
        )
    for index, point in enumerate(outer_points, start=1):
        vertices.append(
            TINVertex(
                vertex_id=f"rao{index:02d}",
                x=float(point[0]),
                y=float(point[1]),
                z=z_value,
                source_point_ref=f"{getattr(outer_loop, 'loop_id', '')}:point:{index:02d}",
                notes="roundabout apron outer ownership boundary",
            )
        )
    triangles: list[TINTriangle] = []
    for index in range(segment_count):
        next_index = (index + 1) % segment_count
        inner_a = f"rai{index + 1:02d}"
        inner_b = f"rai{next_index + 1:02d}"
        outer_a = f"rao{index + 1:02d}"
        outer_b = f"rao{next_index + 1:02d}"
        triangles.append(
            TINTriangle(
                triangle_id=f"rat{len(triangles) + 1:03d}",
                v1=inner_a,
                v2=outer_a,
                v3=outer_b,
                triangle_kind="roundabout_apron_surface",
                quality_ref="roundabout_apron_annular_strip",
                notes="roundabout apron annular radial strip",
            )
        )
        triangles.append(
            TINTriangle(
                triangle_id=f"rat{len(triangles) + 1:03d}",
                v1=inner_a,
                v2=outer_b,
                v3=inner_b,
                triangle_kind="roundabout_apron_surface",
                quality_ref="roundabout_apron_annular_strip",
                notes="roundabout apron annular radial strip",
            )
        )

    shape_quality = _intersection_patch_shape_quality(vertices, triangles)
    inner_area = float(getattr(inner_loop, "area_xy", 0.0) or 0.0)
    outer_area = float(getattr(outer_loop, "area_xy", 0.0) or 0.0)
    center = _roundabout_boundary_center_from_loops(boundary_loops)
    sample_count = min(len(inner_points), len(outer_points))
    widths = [
        abs(
            _xy_distance((float(outer_points[index][0]), float(outer_points[index][1])), (float(center[0]), float(center[1])))
            - _xy_distance((float(inner_points[index][0]), float(inner_points[index][1])), (float(center[0]), float(center[1])))
        )
        for index in range(sample_count)
    ]
    apron_width = (sum(widths) / len(widths)) if widths else max(0.0, _roundabout_slope_face_width(intersection_model)[0])
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        surface_id=surface_id,
        surface_kind="roundabout_apron_surface",
        label=f"Roundabout Apron Surface - {intersection_id or getattr(corridor_model, 'corridor_id', '')}",
        source_refs=[
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            intersection_id,
            str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
            str(getattr(inner_loop, "loop_id", "") or ""),
            str(getattr(outer_loop, "loop_id", "") or ""),
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=[
            str(getattr(inner_loop, "loop_id", "") or f"{surface_id}:circulatory-outer"),
            str(getattr(outer_loop, "loop_id", "") or f"{surface_id}:ownership-outer"),
        ],
        quality_rows=[
            TINQualityRow(f"{surface_id}:roundabout_apron_boundary_segment_count", "roundabout_apron_boundary_segment_count", segment_count, "count"),
            TINQualityRow(f"{surface_id}:roundabout_apron_triangle_count", "roundabout_apron_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_apron_width", "roundabout_apron_width", float(apron_width), "m"),
            TINQualityRow(f"{surface_id}:roundabout_apron_geometry_source", "roundabout_apron_geometry_source", "roundabout_circulatory_outer_to_ownership_boundary"),
            TINQualityRow(f"{surface_id}:roundabout_apron_inner_area", "roundabout_apron_inner_area", inner_area, "m2"),
            TINQualityRow(f"{surface_id}:roundabout_apron_outer_area", "roundabout_apron_outer_area", outer_area, "m2"),
            TINQualityRow(f"{surface_id}:roundabout_apron_ring_area", "roundabout_apron_ring_area", max(0.0, outer_area - inner_area), "m2"),
            TINQualityRow(f"{surface_id}:patch_boundary_point_count", "patch_boundary_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_source", "patch_boundary_source", "roundabout_circulatory_outer_to_ownership_boundary"),
            TINQualityRow(f"{surface_id}:patch_triangulation_mode", "patch_triangulation_mode", "roundabout_apron_annular_strip"),
            TINQualityRow(f"{surface_id}:patch_surface_boundary_strategy", "patch_surface_boundary_strategy", "roundabout_authoritative_apron_boundary_loops"),
            TINQualityRow(f"{surface_id}:patch_triangle_count", "patch_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:patch_structured_strip_count", "patch_structured_strip_count", segment_count, "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_x", "patch_boundary_bbox_x", float(shape_quality["bbox_x"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_y", "patch_boundary_bbox_y", float(shape_quality["bbox_y"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_aspect_ratio", "patch_boundary_bbox_aspect_ratio", float(shape_quality["bbox_aspect_ratio"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_min_quality", "patch_triangle_min_quality", float(shape_quality["triangle_min_quality"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_skinny_count", "patch_triangle_skinny_count", int(shape_quality["skinny_triangle_count"]), "count"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{surface_id}:provenance:roundabout-apron-boundary-loops",
                source_kind="roundabout_apron_boundary_loop_contract",
                source_ref=str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
                notes=f"intersection={intersection_id}; segments={segment_count}; width={apron_width:.3f}",
            )
        ],
    )


def build_roundabout_entry_exit_connector_surface_tin(
    *,
    project_id: str,
    corridor_model,
    applied_section_set,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    surface_id: str,
):
    """Build roundabout entry/exit connector surfaces from connector boundary-loop contracts."""

    from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    service = IntersectionEvaluationService()
    edge_network = service.evaluate_edge_network(intersection_model, intersection_id=intersection_id)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network, intersection_id=intersection_id)
    boundary_loops = service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, intersection_id=intersection_id)
    connector_loops = [
        row
        for row in list(getattr(boundary_loops, "loop_rows", []) or [])
        if str(getattr(row, "loop_role", "") or "") == "roundabout_entry_exit_connector_boundary"
        and str(getattr(row, "status", "") or "") == "ready"
        and bool(getattr(row, "closed", False))
    ]
    if not connector_loops:
        raise ValueError("roundabout_entry_exit_connector_boundary_loops_missing")

    z_value = _roundabout_circulatory_reference_z(applied_section_set, prerequisite)
    vertices: list[TINVertex] = []
    triangles: list[TINTriangle] = []
    boundary_refs: list[str] = []
    approach_refs: list[str] = []
    skipped_loop_count = 0
    for loop_index, loop in enumerate(connector_loops, start=1):
        points = _roundabout_open_loop_points(tuple(getattr(loop, "loop_points_xyz", ()) or ()))
        if len(points) < 4:
            skipped_loop_count += 1
            continue
        points = points[:4]
        area = abs(_xy_polygon_area([(float(point[0]), float(point[1])) for point in points]))
        if area <= 1.0e-6:
            skipped_loop_count += 1
            continue
        loop_ref = str(getattr(loop, "loop_id", "") or f"{surface_id}:connector:{loop_index:02d}")
        boundary_refs.append(loop_ref)
        approach_refs.extend(_roundabout_approach_leg_refs_from_boundary_loop(loop))
        vertex_ids: list[str] = []
        for point_index, point in enumerate(points, start=1):
            vertex_id = f"rec{loop_index:02d}_{point_index:02d}"
            vertex_ids.append(vertex_id)
            vertices.append(
                TINVertex(
                    vertex_id=vertex_id,
                    x=float(point[0]),
                    y=float(point[1]),
                    z=z_value,
                    source_point_ref=f"{loop_ref}:point:{point_index:02d}",
                    notes="roundabout entry/exit connector boundary vertex",
                )
            )
        triangles.append(
            TINTriangle(
                triangle_id=f"rect{len(triangles) + 1:03d}",
                v1=vertex_ids[0],
                v2=vertex_ids[1],
                v3=vertex_ids[2],
                triangle_kind="roundabout_entry_exit_connector_surface",
                quality_ref=loop_ref,
                notes=f"roundabout entry/exit connector loop {loop_index}",
            )
        )
        triangles.append(
            TINTriangle(
                triangle_id=f"rect{len(triangles) + 1:03d}",
                v1=vertex_ids[0],
                v2=vertex_ids[2],
                v3=vertex_ids[3],
                triangle_kind="roundabout_entry_exit_connector_surface",
                quality_ref=loop_ref,
                notes=f"roundabout entry/exit connector loop {loop_index}",
            )
        )

    shape_quality = _intersection_patch_shape_quality(vertices, triangles) if vertices and triangles else {
        "bbox_x": 0.0,
        "bbox_y": 0.0,
        "bbox_aspect_ratio": 0.0,
        "triangle_min_quality": 0.0,
        "skinny_triangle_count": 0,
    }
    approach_refs = _unique_text_values(approach_refs)
    approach_roles = _roundabout_approach_roles_from_refs(approach_refs)
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        surface_id=surface_id,
        surface_kind="roundabout_entry_exit_connector_surface",
        label=f"Roundabout Entry/Exit Connector Surface - {intersection_id or getattr(corridor_model, 'corridor_id', '')}",
        source_refs=[
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            intersection_id,
            str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
            *boundary_refs,
            *approach_refs,
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=boundary_refs,
        quality_rows=[
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_loop_count", "roundabout_entry_exit_connector_loop_count", len(boundary_refs), "count"),
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_skipped_loop_count", "roundabout_entry_exit_connector_skipped_loop_count", skipped_loop_count, "count"),
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_triangle_count", "roundabout_entry_exit_connector_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_geometry_source", "roundabout_entry_exit_connector_geometry_source", "roundabout_entry_exit_connector_boundary_loops"),
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_approach_leg_count", "roundabout_entry_exit_connector_approach_leg_count", len(approach_roles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_approach_leg_roles", "roundabout_entry_exit_connector_approach_leg_roles", ",".join(approach_roles)),
            TINQualityRow(f"{surface_id}:roundabout_entry_exit_connector_approach_leg_source", "roundabout_entry_exit_connector_approach_leg_source", "roundabout_approach_leg_contract"),
            TINQualityRow(f"{surface_id}:patch_boundary_point_count", "patch_boundary_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_source", "patch_boundary_source", "roundabout_entry_exit_connector_boundary"),
            TINQualityRow(f"{surface_id}:patch_triangulation_mode", "patch_triangulation_mode", "roundabout_entry_exit_connector_rectangular_loops"),
            TINQualityRow(f"{surface_id}:patch_surface_boundary_strategy", "patch_surface_boundary_strategy", "roundabout_authoritative_connector_boundary_loops"),
            TINQualityRow(f"{surface_id}:patch_triangle_count", "patch_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_x", "patch_boundary_bbox_x", float(shape_quality["bbox_x"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_y", "patch_boundary_bbox_y", float(shape_quality["bbox_y"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_aspect_ratio", "patch_boundary_bbox_aspect_ratio", float(shape_quality["bbox_aspect_ratio"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_min_quality", "patch_triangle_min_quality", float(shape_quality["triangle_min_quality"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_skinny_count", "patch_triangle_skinny_count", int(shape_quality["skinny_triangle_count"]), "count"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{surface_id}:provenance:roundabout-entry-exit-boundary-loops",
                source_kind="roundabout_entry_exit_connector_boundary_loop_contract",
                source_ref=str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
                notes=(
                    f"intersection={intersection_id}; connector_loops={len(boundary_refs)}; "
                    f"approach_legs={len(approach_roles)}; skipped={skipped_loop_count}"
                ),
            )
        ],
    )


def _roundabout_approach_leg_refs_from_boundary_loop(loop) -> list[str]:
    """Return approach-leg source refs attached to a roundabout boundary loop."""

    refs: list[str] = []
    for ref in tuple(getattr(loop, "source_refs", ()) or ()):
        text = str(ref or "").strip()
        if text.startswith("intersection-roundabout-approach-leg:"):
            refs.append(text)
    return _unique_text_values(refs)


def _roundabout_approach_roles_from_refs(refs: list[str]) -> list[str]:
    """Return stable approach role tokens from approach-leg source refs."""

    roles: list[str] = []
    for ref in refs:
        token = str(ref or "").strip().split(":")[-1]
        if token:
            roles.append(token)
    return _unique_text_values(roles)


def _roundabout_subgrade_depth(intersection_model) -> tuple[float, str]:
    """Return source-policy subgrade depth when available, otherwise a traceable default."""

    for row in list(getattr(intersection_model, "edge_policy_rows", []) or []):
        rule = str(getattr(row, "offset_rule", "") or "").strip().lower()
        if rule == "roundabout_subgrade_depth":
            try:
                value = float(getattr(row, "offset_value", 0.0) or 0.0)
            except Exception:
                value = 0.0
            if value > 0.0:
                return value, "roundabout_subgrade_depth_policy"
    return 0.30, "default_policy_missing"


def build_roundabout_subgrade_surface_tin(
    *,
    project_id: str,
    corridor_model,
    applied_section_set,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    surface_id: str,
):
    """Build a dedicated roundabout subgrade surface below the roundabout ownership footprint."""

    from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    service = IntersectionEvaluationService()
    edge_network = service.evaluate_edge_network(intersection_model, intersection_id=intersection_id)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network, intersection_id=intersection_id)
    boundary_loops = service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, intersection_id=intersection_id)
    loop_rows = list(getattr(boundary_loops, "loop_rows", []) or [])
    outer_loop = next(
        (
            row
            for row in loop_rows
            if str(getattr(row, "loop_role", "") or "") == "roundabout_outer_ownership_boundary"
            and str(getattr(row, "status", "") or "") == "ready"
            and bool(getattr(row, "closed", False))
        ),
        None,
    )
    if outer_loop is None:
        raise ValueError("roundabout_subgrade_ownership_boundary_missing")
    outer_points = _roundabout_open_loop_points(tuple(getattr(outer_loop, "loop_points_xyz", ()) or ()))
    if len(outer_points) < 3:
        raise ValueError("roundabout_subgrade_ownership_boundary_too_few_points")

    clip_loops = [
        row
        for row in loop_rows
        if str(getattr(row, "loop_role", "") or "") == "roundabout_subgrade_clip_boundary"
        and str(getattr(row, "status", "") or "") == "ready"
        and bool(getattr(row, "closed", False))
    ]
    depth, depth_source = _roundabout_subgrade_depth(intersection_model)
    z_value = _roundabout_circulatory_reference_z(applied_section_set, prerequisite) - float(depth)
    center = _roundabout_boundary_center_from_loops(boundary_loops)

    vertices: list[TINVertex] = [
        TINVertex(
            vertex_id="rsub_center",
            x=float(center[0]),
            y=float(center[1]),
            z=z_value,
            source_point_ref=f"{getattr(outer_loop, 'loop_id', '')}:center",
            notes="roundabout subgrade center vertex",
        )
    ]
    for index, point in enumerate(outer_points, start=1):
        vertices.append(
            TINVertex(
                vertex_id=f"rsub_o{index:02d}",
                x=float(point[0]),
                y=float(point[1]),
                z=z_value,
                source_point_ref=f"{getattr(outer_loop, 'loop_id', '')}:point:{index:02d}",
                notes="roundabout subgrade outer ownership boundary",
            )
        )

    triangles: list[TINTriangle] = []
    segment_count = len(outer_points)
    for index in range(segment_count):
        next_index = (index + 1) % segment_count
        triangles.append(
            TINTriangle(
                triangle_id=f"rsub_t{index + 1:03d}",
                v1="rsub_center",
                v2=f"rsub_o{index + 1:02d}",
                v3=f"rsub_o{next_index + 1:02d}",
                triangle_kind="roundabout_subgrade_surface",
                quality_ref=str(getattr(outer_loop, "loop_id", "") or "roundabout_outer_ownership_boundary"),
                notes="roundabout subgrade ownership fan",
            )
        )

    shape_quality = _intersection_patch_shape_quality(vertices, triangles)
    outer_area = float(getattr(outer_loop, "area_xy", 0.0) or 0.0)
    clip_refs = [
        str(getattr(loop, "loop_id", "") or "")
        for loop in clip_loops
        if str(getattr(loop, "loop_id", "") or "")
    ]
    clip_approach_refs = _unique_text_values(
        [
            ref
            for loop in clip_loops
            for ref in _roundabout_approach_leg_refs_from_boundary_loop(loop)
        ]
    )
    clip_approach_roles = _roundabout_approach_roles_from_refs(clip_approach_refs)
    boundary_refs = [
        str(getattr(outer_loop, "loop_id", "") or f"{surface_id}:ownership-outer"),
        *clip_refs,
    ]
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        surface_id=surface_id,
        surface_kind="roundabout_subgrade_surface",
        label=f"Roundabout Subgrade Surface - {intersection_id or getattr(corridor_model, 'corridor_id', '')}",
        source_refs=[
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            intersection_id,
            str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
            str(getattr(outer_loop, "loop_id", "") or ""),
            *clip_refs,
            *clip_approach_refs,
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=boundary_refs,
        quality_rows=[
            TINQualityRow(f"{surface_id}:roundabout_subgrade_boundary_segment_count", "roundabout_subgrade_boundary_segment_count", segment_count, "count"),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_clip_loop_count", "roundabout_subgrade_clip_loop_count", len(clip_refs), "count"),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_approach_leg_count", "roundabout_subgrade_approach_leg_count", len(clip_approach_roles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_approach_leg_roles", "roundabout_subgrade_approach_leg_roles", ",".join(clip_approach_roles)),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_approach_leg_source", "roundabout_subgrade_approach_leg_source", "roundabout_approach_leg_contract" if clip_approach_roles else ""),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_triangle_count", "roundabout_subgrade_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_depth", "roundabout_subgrade_depth", float(depth), "m"),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_depth_source", "roundabout_subgrade_depth_source", depth_source),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_geometry_source", "roundabout_subgrade_geometry_source", "roundabout_outer_ownership_boundary_fan"),
            TINQualityRow(f"{surface_id}:roundabout_subgrade_outer_area", "roundabout_subgrade_outer_area", outer_area, "m2"),
            TINQualityRow(f"{surface_id}:patch_boundary_point_count", "patch_boundary_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_source", "patch_boundary_source", "roundabout_outer_ownership_boundary"),
            TINQualityRow(f"{surface_id}:patch_triangulation_mode", "patch_triangulation_mode", "roundabout_subgrade_ownership_fan"),
            TINQualityRow(f"{surface_id}:patch_surface_boundary_strategy", "patch_surface_boundary_strategy", "roundabout_authoritative_subgrade_boundary_loops"),
            TINQualityRow(f"{surface_id}:patch_triangle_count", "patch_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_x", "patch_boundary_bbox_x", float(shape_quality["bbox_x"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_y", "patch_boundary_bbox_y", float(shape_quality["bbox_y"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_aspect_ratio", "patch_boundary_bbox_aspect_ratio", float(shape_quality["bbox_aspect_ratio"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_min_quality", "patch_triangle_min_quality", float(shape_quality["triangle_min_quality"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_skinny_count", "patch_triangle_skinny_count", int(shape_quality["skinny_triangle_count"]), "count"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{surface_id}:provenance:roundabout-subgrade-boundary-loops",
                source_kind="roundabout_subgrade_boundary_loop_contract",
                source_ref=str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
                notes=(
                    f"intersection={intersection_id}; segments={segment_count}; "
                    f"clip_loops={len(clip_refs)}; approach_legs={len(clip_approach_roles)}; "
                    f"depth_source={depth_source}"
                ),
            )
        ],
    )


def build_roundabout_slope_face_surface_tin(
    *,
    project_id: str,
    corridor_model,
    applied_section_set,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    surface_id: str,
):
    """Build roundabout outer slope strips from exposed outer ownership boundary segments."""

    from ...models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
    service = IntersectionEvaluationService()
    edge_network = service.evaluate_edge_network(intersection_model, intersection_id=intersection_id)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network, intersection_id=intersection_id)
    boundary_loops = service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, intersection_id=intersection_id)
    candidate_loops = list(getattr(boundary_loops, "loop_rows", []) or [])
    outer_loop = next(
        (
            row for row in candidate_loops
            if str(getattr(row, "loop_role", "") or "") == "roundabout_outer_ownership_boundary"
            and str(getattr(row, "status", "") or "") == "ready"
            and bool(getattr(row, "closed", False))
        ),
        None,
    )
    if outer_loop is None:
        outer_loop = next(
            (
                row for row in candidate_loops
                if str(getattr(row, "loop_role", "") or "") == "roundabout_circulatory_outer_boundary"
                and str(getattr(row, "status", "") or "") == "ready"
                and bool(getattr(row, "closed", False))
            ),
            None,
        )
    source_loop_role = str(getattr(outer_loop, "loop_role", "") or "roundabout_circulatory_outer_boundary")
    center = _roundabout_boundary_center_from_loops(boundary_loops)
    outer_points = _roundabout_open_loop_points(tuple(getattr(outer_loop, "loop_points_xyz", ()) or ())) if outer_loop is not None else []
    connector_spans = _roundabout_connector_angle_spans(boundary_loops, center)
    handoff_loops = [
        row
        for row in candidate_loops
        if str(getattr(row, "loop_role", "") or "") == "roundabout_slope_handoff_boundary"
        and str(getattr(row, "status", "") or "") == "ready"
        and bool(getattr(row, "closed", False))
    ]
    handoff_refs = [
        str(getattr(loop, "loop_id", "") or "")
        for loop in handoff_loops
        if str(getattr(loop, "loop_id", "") or "")
    ]
    handoff_approach_refs = _unique_text_values(
        [
            ref
            for loop in handoff_loops
            for ref in _roundabout_approach_leg_refs_from_boundary_loop(loop)
        ]
    )
    handoff_approach_roles = _roundabout_approach_roles_from_refs(handoff_approach_refs)
    width, width_source = _roundabout_slope_face_width(intersection_model)
    z_value = _roundabout_circulatory_reference_z(applied_section_set, prerequisite)
    vertices: list[TINVertex] = []
    triangles: list[TINTriangle] = []
    boundary_refs: list[str] = []
    skipped_connector_count = 0
    skipped_degenerate_count = 0
    if len(outer_points) >= 3 and width > 0.0:
        for segment_index, (first, second) in enumerate(zip(outer_points, [*outer_points[1:], outer_points[0]]), start=1):
            first_xyz = _xyz_tuple(first)
            second_xyz = _xyz_tuple(second)
            midpoint = (
                (float(first_xyz[0]) + float(second_xyz[0])) * 0.5,
                (float(first_xyz[1]) + float(second_xyz[1])) * 0.5,
                (float(first_xyz[2]) + float(second_xyz[2])) * 0.5,
            )
            midpoint_angle = math.atan2(float(midpoint[1]) - float(center[1]), float(midpoint[0]) - float(center[0]))
            if _roundabout_angle_in_any_span(midpoint_angle, connector_spans):
                skipped_connector_count += 1
                continue
            outer_first = _roundabout_radial_offset_point(first_xyz, center, width, z_value=z_value)
            outer_second = _roundabout_radial_offset_point(second_xyz, center, width, z_value=z_value)
            if not outer_first or not outer_second:
                skipped_degenerate_count += 1
                continue
            loop_points = [
                (float(first_xyz[0]), float(first_xyz[1]), z_value),
                (float(second_xyz[0]), float(second_xyz[1]), z_value),
                outer_second,
                outer_first,
            ]
            area = abs(_xy_polygon_area([(point[0], point[1]) for point in loop_points]))
            if area <= 1.0e-6:
                skipped_degenerate_count += 1
                continue
            segment_ref = (
                f"roundabout-slope-face:{_safe_id_fragment(intersection_id or 'main')}:"
                f"{_safe_id_fragment(source_loop_role)}:{segment_index:02d}"
            )
            boundary_refs.append(segment_ref)
            vertex_ids: list[str] = []
            for point_index, point in enumerate(loop_points, start=1):
                vertex_id = f"rsf{segment_index:02d}_{point_index:02d}"
                vertex_ids.append(vertex_id)
                vertices.append(
                    TINVertex(
                        vertex_id=vertex_id,
                        x=float(point[0]),
                        y=float(point[1]),
                        z=float(point[2]),
                        source_point_ref=f"{segment_ref}:point:{point_index:02d}",
                        notes="roundabout slope face strip vertex",
                    )
                )
            triangles.append(
                TINTriangle(
                    triangle_id=f"rsft{len(triangles) + 1:03d}",
                    v1=vertex_ids[0],
                    v2=vertex_ids[1],
                    v3=vertex_ids[2],
                    triangle_kind="roundabout_slope_face_surface",
                    quality_ref=segment_ref,
                    notes=f"roundabout exposed {source_loop_role} strip {segment_index}",
                )
            )
            triangles.append(
                TINTriangle(
                    triangle_id=f"rsft{len(triangles) + 1:03d}",
                    v1=vertex_ids[0],
                    v2=vertex_ids[2],
                    v3=vertex_ids[3],
                    triangle_kind="roundabout_slope_face_surface",
                    quality_ref=segment_ref,
                    notes=f"roundabout exposed {source_loop_role} strip {segment_index}",
                )
            )

    shape_quality = _intersection_patch_shape_quality(vertices, triangles) if vertices and triangles else {
        "bbox_x": 0.0,
        "bbox_y": 0.0,
        "bbox_aspect_ratio": 0.0,
        "triangle_min_quality": 0.0,
        "skinny_triangle_count": 0,
    }
    return TINSurface(
        schema_version=1,
        project_id=project_id,
        surface_id=surface_id,
        surface_kind="roundabout_slope_face_surface",
        label=f"Roundabout Slope Face Surface - {intersection_id or getattr(corridor_model, 'corridor_id', '')}",
        source_refs=[
            str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            intersection_id,
            str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
            str(getattr(outer_loop, "loop_id", "") or ""),
            *boundary_refs,
            *handoff_refs,
            *handoff_approach_refs,
        ],
        vertex_rows=vertices,
        triangle_rows=triangles,
        boundary_refs=boundary_refs,
        quality_rows=[
            TINQualityRow(f"{surface_id}:roundabout_slope_face_boundary_segment_count", "roundabout_slope_face_boundary_segment_count", len(boundary_refs), "count"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_handoff_loop_count", "roundabout_slope_face_handoff_loop_count", len(handoff_refs), "count"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_handoff_approach_leg_count", "roundabout_slope_face_handoff_approach_leg_count", len(handoff_approach_roles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_handoff_approach_leg_roles", "roundabout_slope_face_handoff_approach_leg_roles", ",".join(handoff_approach_roles)),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_handoff_approach_leg_source", "roundabout_slope_face_handoff_approach_leg_source", "roundabout_approach_leg_contract" if handoff_approach_roles else ""),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_skipped_connector_segment_count", "roundabout_slope_face_skipped_connector_segment_count", skipped_connector_count, "count"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_skipped_degenerate_segment_count", "roundabout_slope_face_skipped_degenerate_segment_count", skipped_degenerate_count, "count"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_triangle_count", "roundabout_slope_face_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_width", "roundabout_slope_face_width", float(width), "m"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_width_source", "roundabout_slope_face_width_source", width_source),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_geometry_source", "roundabout_slope_face_geometry_source", f"{source_loop_role}_exposed_segments"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_suppression_source", "roundabout_slope_face_suppression_source", "roundabout_connector_and_handoff_boundary_angle_spans"),
            TINQualityRow(f"{surface_id}:roundabout_slope_face_connector_span_count", "roundabout_slope_face_connector_span_count", len(connector_spans), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_point_count", "patch_boundary_point_count", len(vertices), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_source", "patch_boundary_source", source_loop_role),
            TINQualityRow(f"{surface_id}:patch_triangulation_mode", "patch_triangulation_mode", "roundabout_outer_slope_face_strips"),
            TINQualityRow(f"{surface_id}:patch_surface_boundary_strategy", "patch_surface_boundary_strategy", "roundabout_authoritative_outer_boundary_segments"),
            TINQualityRow(f"{surface_id}:patch_triangle_count", "patch_triangle_count", len(triangles), "count"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_x", "patch_boundary_bbox_x", float(shape_quality["bbox_x"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_y", "patch_boundary_bbox_y", float(shape_quality["bbox_y"]), "m"),
            TINQualityRow(f"{surface_id}:patch_boundary_bbox_aspect_ratio", "patch_boundary_bbox_aspect_ratio", float(shape_quality["bbox_aspect_ratio"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_min_quality", "patch_triangle_min_quality", float(shape_quality["triangle_min_quality"]), "ratio"),
            TINQualityRow(f"{surface_id}:patch_triangle_skinny_count", "patch_triangle_skinny_count", int(shape_quality["skinny_triangle_count"]), "count"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                provenance_id=f"{surface_id}:provenance:roundabout-slope-face-boundary-loops",
                source_kind=f"{source_loop_role}_loop_contract",
                source_ref=str(getattr(boundary_loops, "boundary_loop_result_id", "") or ""),
                notes=(
                    f"intersection={intersection_id}; source_loop_role={source_loop_role}; exposed_segments={len(boundary_refs)}; "
                    f"handoff_loops={len(handoff_refs)}; approach_legs={len(handoff_approach_roles)}; "
                    f"connector_suppressed={skipped_connector_count}; degenerate_skipped={skipped_degenerate_count}"
                ),
            )
        ],
    )


def _roundabout_slope_face_width(intersection_model) -> tuple[float, str]:
    for policy in list(getattr(intersection_model, "edge_policy_rows", []) or []):
        if str(getattr(policy, "offset_rule", "") or "") == "roundabout_slope_face_width":
            value = float(getattr(policy, "offset_value", 0.0) or 0.0)
            if value > 0.0:
                return max(value, 0.5), "roundabout_slope_face_width_policy"
    for policy in list(getattr(intersection_model, "edge_policy_rows", []) or []):
        if str(getattr(policy, "offset_rule", "") or "") == "roundabout_outer_apron_width":
            value = float(getattr(policy, "offset_value", 0.0) or 0.0)
            if value > 0.0:
                return max(value, 0.5), "roundabout_outer_apron_width_fallback"
    return 4.0, "default_policy_missing"


def _roundabout_connector_angle_spans(boundary_loops, center: tuple[float, float, float]) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    suppression_roles = {
        "roundabout_entry_exit_connector_boundary",
        "roundabout_approach_clip_boundary",
        "roundabout_subgrade_clip_boundary",
        "roundabout_slope_handoff_boundary",
    }
    for row in list(getattr(boundary_loops, "loop_rows", []) or []):
        if str(getattr(row, "loop_role", "") or "") not in suppression_roles:
            continue
        points = _roundabout_open_loop_points(tuple(getattr(row, "loop_points_xyz", ()) or ()))
        angles = [
            math.atan2(float(point[1]) - float(center[1]), float(point[0]) - float(center[0]))
            for point in points
            if _xy_distance((float(point[0]), float(point[1])), (float(center[0]), float(center[1]))) > 1.0e-9
        ]
        if not angles:
            continue
        mean_x = sum(math.cos(angle) for angle in angles)
        mean_y = sum(math.sin(angle) for angle in angles)
        center_angle = math.atan2(mean_y, mean_x)
        half_width = max(_roundabout_angular_distance(angle, center_angle) for angle in angles)
        spans.append((center_angle, min(max(half_width, 0.045) + 0.20, math.pi * 0.49)))
    return spans


def _roundabout_angle_in_any_span(angle: float, spans: list[tuple[float, float]]) -> bool:
    return any(_roundabout_angular_distance(angle, center_angle) <= half_width for center_angle, half_width in spans)


def _roundabout_angular_distance(first: float, second: float) -> float:
    delta = (float(first) - float(second) + math.pi) % (2.0 * math.pi) - math.pi
    return abs(delta)


def _roundabout_radial_offset_point(
    point: tuple[float, float, float],
    center: tuple[float, float, float],
    offset: float,
    *,
    z_value: float,
) -> tuple[float, float, float]:
    dx = float(point[0]) - float(center[0])
    dy = float(point[1]) - float(center[1])
    length = math.hypot(dx, dy)
    if length <= 1.0e-9:
        return ()
    ux = dx / length
    uy = dy / length
    return (
        float(point[0]) + ux * float(offset),
        float(point[1]) + uy * float(offset),
        float(z_value),
    )


def _roundabout_circulatory_reference_z(applied_section_set, prerequisite: IntersectionPatchPrerequisiteResult) -> float:
    sections = _intersection_patch_center_sections(
        _intersection_patch_sections(applied_section_set, prerequisite),
        intersection_model=None,
        prerequisite=prerequisite,
    )
    z_values: list[float] = []
    for section in list(sections or []):
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") == "fg_surface":
                z_values.append(float(getattr(point, "z", 0.0) or 0.0))
    return (sum(z_values) / len(z_values)) if z_values else 0.0


def _roundabout_open_loop_points(points: tuple[object, ...]) -> list[tuple[float, float, float]]:
    output = [_xyz_tuple(point) for point in tuple(points or ())]
    if len(output) > 1:
        first = output[0]
        last = output[-1]
        if (
            abs(float(first[0]) - float(last[0])) <= 1.0e-9
            and abs(float(first[1]) - float(last[1])) <= 1.0e-9
            and abs(float(first[2]) - float(last[2])) <= 1.0e-9
        ):
            output.pop()
    return output


def _intersection_patch_shape_quality(vertices: list[object], triangles: list[object]) -> dict[str, object]:
    result = IntersectionPatchShapeQualityService().evaluate(
        IntersectionPatchShapeQualityRequest(
            vertices=tuple(vertices or ()),
            triangles=tuple(triangles or ()),
        )
    )
    return {
        "triangulation_mode": result.triangulation_mode,
        "bbox_x": result.bbox_x,
        "bbox_y": result.bbox_y,
        "bbox_aspect_ratio": result.bbox_aspect_ratio,
        "triangle_min_quality": result.triangle_min_quality,
        "skinny_triangle_count": result.skinny_triangle_count,
    }


def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return xy_distance(a, b)


def _intersection_patch_center_sections(
    sections: list[object],
    *,
    intersection_model=None,
    prerequisite: IntersectionPatchPrerequisiteResult,
) -> list[object]:
    """Keep only the center-nearest Applied Section per participating Alignment."""

    if not sections:
        return []
    target_stations = _intersection_patch_target_stations_by_alignment(intersection_model, prerequisite)
    grouped: dict[str, list[object]] = {}
    for section in sections:
        alignment_id = str(getattr(section, "alignment_id", "") or "")
        grouped.setdefault(alignment_id, []).append(section)
    output: list[object] = []
    for alignment_id, rows in grouped.items():
        if len(rows) <= 1:
            output.extend(rows)
            continue
        target_station = target_stations.get(alignment_id)
        if target_station is None:
            stations = [float(getattr(row, "station", 0.0) or 0.0) for row in rows]
            target_station = sum(stations) / len(stations)
        nearest = min(rows, key=lambda row: abs(float(getattr(row, "station", 0.0) or 0.0) - float(target_station)))
        output.append(nearest)
    return _station_ordered_applied_sections(
        AppliedSectionSet(
            schema_version=1,
            project_id="",
            applied_section_set_id="intersection-patch:center-sections",
            corridor_id="",
            sections=output,
        )
    )


def _intersection_patch_target_stations_by_alignment(intersection_model, prerequisite: IntersectionPatchPrerequisiteResult) -> dict[str, float]:
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    output: dict[str, float] = {}
    if intersection_model is None:
        return output
    source_row = None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if not intersection_id or str(getattr(row, "intersection_id", "") or "") == intersection_id:
            source_row = row
            break
    if source_row is not None:
        primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip()
        if primary_ref:
            output[primary_ref] = float(getattr(source_row, "primary_station", 0.0) or 0.0)
        for alignment_ref, station in dict(getattr(source_row, "secondary_station_refs", {}) or {}).items():
            alignment_id = str(alignment_ref or "").strip()
            if alignment_id:
                output[alignment_id] = float(station or 0.0)
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if intersection_id and str(getattr(area, "intersection_id", "") or "") != intersection_id:
            continue
        alignment_id = str(getattr(area, "alignment_ref", "") or "").strip()
        if not alignment_id or alignment_id in output:
            continue
        ranges = list(getattr(area, "station_ranges", []) or [])
        centers: list[float] = []
        for station_start, station_end in ranges:
            try:
                centers.append((float(station_start) + float(station_end)) / 2.0)
            except Exception:
                continue
        if centers:
            output[alignment_id] = sum(centers) / len(centers)
    return output


# __SERVICE_BODY_END__


__all__ = [
    "build_roundabout_apron_surface_tin",
    "build_roundabout_circulatory_surface_tin",
    "build_roundabout_entry_exit_connector_surface_tin",
    "build_roundabout_slope_face_surface_tin",
    "build_roundabout_subgrade_surface_tin",
]
