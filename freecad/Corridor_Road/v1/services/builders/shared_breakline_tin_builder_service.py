"""Typed shared-breakline TIN metadata and constraint-edge builders."""

from __future__ import annotations

from dataclasses import replace

from ...models.result.tin_surface import TINQualityRow
from .intersection_patch_constraint_build_service import (
    IntersectionPatchConstraintBuildService,
)
from ..mapping.preview_audit_row_mapper import shared_breakline_segment_rows


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


def _shared_breakline_refs_for_consumer(shared_result, consumer_ref: str) -> list[str]:
    target = str(consumer_ref or "").strip()
    if shared_result is None or not target:
        return []
    return [
        str(getattr(row, "breakline_id", "") or "")
        for row in list(getattr(shared_result, "breakline_rows", []) or [])
        if target in {str(value or "").strip() for value in tuple(getattr(row, "consumer_refs", ()) or ())}
        and str(getattr(row, "breakline_id", "") or "")
    ]


def _tin_surface_with_shared_breakline_metadata(surface, shared_result, *, consumer_ref: str):
    if surface is None or shared_result is None:
        return surface
    surface_id = str(getattr(surface, "surface_id", "") or "surface")
    refs = _shared_breakline_refs_for_consumer(shared_result, consumer_ref)
    boundary_refs = list(getattr(surface, "boundary_refs", []) or [])
    for ref in refs:
        if ref not in boundary_refs:
            boundary_refs.append(ref)
    filtered_quality = [
        quality
        for quality in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(quality, "kind", "") or "") not in {
            "shared_breakline_result_id",
            "shared_breakline_status",
            "shared_breakline_count",
            "shared_breakline_consumed_count",
            "shared_breakline_refs",
            "shared_breakline_constraint_segment_rows",
        }
    ]
    filtered_quality.extend(
        [
            TINQualityRow(f"{surface_id}:shared_breakline_result_id", "shared_breakline_result_id", str(getattr(shared_result, "breakline_result_id", "") or "")),
            TINQualityRow(f"{surface_id}:shared_breakline_status", "shared_breakline_status", str(getattr(shared_result, "status", "") or "")),
            TINQualityRow(f"{surface_id}:shared_breakline_count", "shared_breakline_count", len(refs), "count"),
            TINQualityRow(f"{surface_id}:shared_breakline_consumed_count", "shared_breakline_consumed_count", len(refs), "count"),
            TINQualityRow(f"{surface_id}:shared_breakline_refs", "shared_breakline_refs", ",".join(refs)),
            TINQualityRow(
                f"{surface_id}:shared_breakline_constraint_segment_rows",
                "shared_breakline_constraint_segment_rows",
                ";;".join(shared_breakline_segment_rows(shared_result, refs)),
                "rows",
                "Surface consumes these SharedBreaklineResult segments as normalized constraint edges.",
            ),
        ]
    )
    return replace(surface, boundary_refs=boundary_refs, quality_rows=filtered_quality)


def _tin_surface_with_shared_breakline_constraint_edges(surface, shared_result, *, consumer_ref: str):
    if surface is None or shared_result is None or not consumer_ref:
        return surface
    surface_id = str(getattr(surface, "surface_id", "") or "surface")
    source_triangle_count = len(list(getattr(surface, "triangle_rows", []) or []))
    vertices, triangles, stats = _tin_rows_with_shared_breakline_constraint_edges(
        vertices=list(getattr(surface, "vertex_rows", []) or []),
        triangles=list(getattr(surface, "triangle_rows", []) or []),
        shared_result=shared_result,
        surface_id=surface_id,
        consumer_ref=consumer_ref,
    )
    filtered_quality = [
        quality
        for quality in list(getattr(surface, "quality_rows", []) or [])
        if str(getattr(quality, "kind", "") or "") not in {
            "shared_breakline_constraint_mode",
            "shared_breakline_constraint_segment_count",
            "shared_breakline_constraint_edge_count",
            "shared_breakline_constraint_vertex_count",
            "shared_breakline_boundary_loop_constraint_segment_count",
            "shared_breakline_boundary_loop_constraint_edge_count",
            "shared_breakline_boundary_loop_constraint_refs",
            "shared_breakline_boundary_loop_constraint_role_summary",
            "shared_breakline_constraint_snap_count",
            "shared_breakline_constraint_snap_max_distance",
            "shared_breakline_constraint_snap_diagnostics",
        }
    ]
    filtered_quality.extend(
        [
            TINQualityRow(f"{surface_id}:shared_breakline_constraint_mode", "shared_breakline_constraint_mode", str(stats["mode"])),
            TINQualityRow(f"{surface_id}:shared_breakline_constraint_segment_count", "shared_breakline_constraint_segment_count", int(stats["segment_count"]), "count"),
            TINQualityRow(
                f"{surface_id}:shared_breakline_constraint_edge_count",
                "shared_breakline_constraint_edge_count",
                max(0, len(triangles) - source_triangle_count),
                "count",
            ),
            TINQualityRow(f"{surface_id}:shared_breakline_constraint_vertex_count", "shared_breakline_constraint_vertex_count", int(stats["vertex_count"]), "count"),
            TINQualityRow(
                f"{surface_id}:shared_breakline_boundary_loop_constraint_segment_count",
                "shared_breakline_boundary_loop_constraint_segment_count",
                int(stats.get("boundary_loop_segment_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:shared_breakline_boundary_loop_constraint_edge_count",
                "shared_breakline_boundary_loop_constraint_edge_count",
                int(stats.get("boundary_loop_edge_count", 0) or 0),
                "count",
            ),
            TINQualityRow(
                f"{surface_id}:shared_breakline_boundary_loop_constraint_refs",
                "shared_breakline_boundary_loop_constraint_refs",
                ",".join(_unique_text_values(list(stats.get("boundary_loop_refs", []) or []))),
            ),
            TINQualityRow(
                f"{surface_id}:shared_breakline_boundary_loop_constraint_role_summary",
                "shared_breakline_boundary_loop_constraint_role_summary",
                _shared_breakline_boundary_loop_role_summary(stats),
            ),
            TINQualityRow(f"{surface_id}:shared_breakline_constraint_snap_count", "shared_breakline_constraint_snap_count", int(stats.get("snap_count", 0) or 0), "count"),
            TINQualityRow(f"{surface_id}:shared_breakline_constraint_snap_max_distance", "shared_breakline_constraint_snap_max_distance", float(stats.get("snap_max_distance", 0.0) or 0.0), "m"),
            TINQualityRow(
                f"{surface_id}:shared_breakline_constraint_snap_diagnostics",
                "shared_breakline_constraint_snap_diagnostics",
                "; ".join(list(stats.get("snap_diagnostics", []) or [])),
            ),
        ]
    )
    return replace(surface, vertex_rows=vertices, triangle_rows=triangles, quality_rows=filtered_quality)


def _intersection_surface_tin_with_shared_breakline_constraint_edges(
    *,
    vertices: list[object],
    triangles: list[object],
    shared_result,
    surface_id: str,
) -> tuple[list[object], list[object], dict[str, object]]:
    """Return intersection TIN rows with shared breakline segments preserved as TIN edges."""

    return _tin_rows_with_shared_breakline_constraint_edges(
        vertices=vertices,
        triangles=triangles,
        shared_result=shared_result,
        surface_id=surface_id,
        consumer_ref="intersection_surface",
    )


def _tin_rows_with_shared_breakline_constraint_edges(
    *,
    vertices: list[object],
    triangles: list[object],
    shared_result,
    surface_id: str,
    consumer_ref: str,
) -> tuple[list[object], list[object], dict[str, object]]:
    """Return TIN rows with shared breakline segments preserved as TIN edges."""

    return IntersectionPatchConstraintBuildService().constraint_rows(
        vertices=vertices,
        triangles=triangles,
        shared_result=shared_result,
        surface_id=surface_id,
        consumer_ref=consumer_ref,
    )


def _shared_breakline_boundary_loop_role_summary(stats: dict[str, object]) -> str:
    role_counts = dict((stats or {}).get("boundary_loop_role_counts", {}) or {})
    return ", ".join(
        f"{role}={count}"
        for role, count in sorted(role_counts.items())
        if str(role or "") and int(count or 0) > 0
    )


def tin_surface_with_shared_breakline_metadata(surface, shared_result, *, consumer_ref: str):
    return _tin_surface_with_shared_breakline_metadata(surface, shared_result, consumer_ref=consumer_ref)


def tin_surface_with_shared_breakline_constraint_edges(surface, shared_result, *, consumer_ref: str):
    return _tin_surface_with_shared_breakline_constraint_edges(surface, shared_result, consumer_ref=consumer_ref)


def intersection_surface_tin_with_shared_breakline_constraint_edges(*args, **kwargs):
    return _intersection_surface_tin_with_shared_breakline_constraint_edges(*args, **kwargs)


def tin_rows_with_shared_breakline_constraint_edges(*args, **kwargs):
    return _tin_rows_with_shared_breakline_constraint_edges(*args, **kwargs)
