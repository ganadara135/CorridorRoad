"""Replayable TIN edit operations for CorridorRoad v1."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re

from ...models.result.tin_surface import (
    TINProvenanceRow,
    TINQualityRow,
    TINSurface,
    TINTriangle,
    TINVertex,
)
from ...models.source.tin_edit_model import TINEditOperation


@dataclass(frozen=True)
class TINEditReport:
    """Summary for one applied TIN edit operation."""

    operation_id: str
    operation_kind: str
    status: str
    removed_triangle_count: int = 0
    changed_vertex_count: int = 0
    notes: str = ""


@dataclass(frozen=True)
class TINEditResult:
    """Result surface and diagnostics after replaying TIN edits."""

    surface: TINSurface
    operation_reports: list[TINEditReport]
    removed_triangle_count: int = 0
    changed_vertex_count: int = 0
    status: str = "ok"


class TINEditService:
    """Apply deterministic edit operations to a TINSurface without mutating the base surface."""

    def apply_operations(
        self,
        surface: TINSurface,
        operations: Iterable[TINEditOperation | dict[str, object]],
        *,
        edited_surface_id: str | None = None,
        edited_label: str | None = None,
    ) -> TINEditResult:
        """Return a regenerated TINSurface after applying enabled operations in order."""

        if surface is None:
            raise ValueError("TIN surface is required.")
        vertices = {row.vertex_id: row for row in list(surface.vertex_rows or [])}
        triangles = list(surface.triangle_rows or [])
        reports: list[TINEditReport] = []

        for index, raw_operation in enumerate(list(operations or []), start=1):
            operation = _coerce_operation(raw_operation, index=index, target_surface_id=surface.surface_id)
            if not operation.enabled:
                reports.append(
                    TINEditReport(
                        operation.operation_id,
                        operation.operation_kind,
                        "skipped",
                        notes="Operation is disabled.",
                    )
                )
                continue

            kind = str(operation.operation_kind or "").strip().lower()
            before_triangles = len(triangles)
            before_vertices = dict(vertices)
            if kind == "boundary_clip_rect":
                triangles = self._apply_boundary_clip_rect(triangles, vertices, operation)
            elif kind == "void_clip_rect":
                triangles = self._apply_void_clip_rect(triangles, vertices, operation)
            elif kind == "delete_triangles":
                triangles = self._apply_delete_triangles(triangles, operation)
            elif kind == "override_vertex_elevation":
                vertices = self._apply_vertex_elevation_override(vertices, operation)
            else:
                reports.append(
                    TINEditReport(
                        operation.operation_id,
                        operation.operation_kind,
                        "ignored",
                        notes=f"Unsupported TIN edit operation: {operation.operation_kind}",
                    )
                )
                continue

            removed = max(0, before_triangles - len(triangles))
            changed = _changed_vertex_count(before_vertices, vertices)
            status = "ok" if removed or changed or kind == "boundary_clip_rect" else "ok"
            reports.append(
                TINEditReport(
                    operation.operation_id,
                    operation.operation_kind,
                    status,
                    removed_triangle_count=removed,
                    changed_vertex_count=changed,
                    notes=str(operation.notes or ""),
                )
            )

        triangles, vertices = _prune_orphan_vertices(triangles, vertices)
        edited_surface = self._build_edited_surface(
            surface,
            vertices,
            triangles,
            reports,
            edited_surface_id=edited_surface_id,
            edited_label=edited_label,
        )
        removed_total = max(0, len(list(surface.triangle_rows or [])) - len(triangles))
        changed_total = _changed_vertex_count({row.vertex_id: row for row in list(surface.vertex_rows or [])}, vertices)
        return TINEditResult(
            surface=edited_surface,
            operation_reports=reports,
            removed_triangle_count=removed_total,
            changed_vertex_count=changed_total,
            status=_overall_status(reports),
        )

    def _apply_boundary_clip_rect(
        self,
        triangles: list[TINTriangle],
        vertices: dict[str, TINVertex],
        operation: TINEditOperation,
    ) -> list[TINTriangle]:
        rect = _rect_from_parameters(operation.parameters)
        return [triangle for triangle in triangles if _triangle_centroid_inside_rect(triangle, vertices, rect)]

    def _apply_void_clip_rect(
        self,
        triangles: list[TINTriangle],
        vertices: dict[str, TINVertex],
        operation: TINEditOperation,
    ) -> list[TINTriangle]:
        rect = _rect_from_parameters(operation.parameters)
        return [triangle for triangle in triangles if not _triangle_centroid_inside_rect(triangle, vertices, rect)]

    def _apply_delete_triangles(
        self,
        triangles: list[TINTriangle],
        operation: TINEditOperation,
    ) -> list[TINTriangle]:
        ids = _triangle_ids_from_parameters(operation.parameters)
        return [triangle for triangle in triangles if str(triangle.triangle_id) not in ids]

    def _apply_vertex_elevation_override(
        self,
        vertices: dict[str, TINVertex],
        operation: TINEditOperation,
    ) -> dict[str, TINVertex]:
        updates = _vertex_updates_from_parameters(operation.parameters)
        output = dict(vertices)
        for vertex_id, new_z in updates.items():
            vertex = output.get(vertex_id)
            if vertex is None:
                continue
            output[vertex_id] = TINVertex(
                vertex.vertex_id,
                float(vertex.x),
                float(vertex.y),
                float(new_z),
                source_point_ref=vertex.source_point_ref,
                notes=_join_notes(vertex.notes, f"z overridden by {operation.operation_id}"),
            )
        return output

    def _build_edited_surface(
        self,
        base: TINSurface,
        vertices: dict[str, TINVertex],
        triangles: list[TINTriangle],
        reports: list[TINEditReport],
        *,
        edited_surface_id: str | None,
        edited_label: str | None,
    ) -> TINSurface:
        surface_id = str(edited_surface_id or f"{base.surface_id or 'tin'}:edited")
        label = str(edited_label or f"{base.label or base.surface_id or 'TIN'} (edited)")
        operation_ids = [report.operation_id for report in reports if report.status not in {"skipped", "ignored"}]
        provenance = list(base.provenance_rows or [])
        for report in reports:
            provenance.append(
                TINProvenanceRow(
                    provenance_id=f"provenance:{report.operation_id}",
                    source_kind="tin_edit_operation",
                    source_ref=report.operation_id,
                    notes=(
                        f"{report.operation_kind}: removed_triangles={report.removed_triangle_count}; "
                        f"changed_vertices={report.changed_vertex_count}; status={report.status}"
                    ),
                )
            )
        quality = list(base.quality_rows or [])
        quality.extend(
            [
                TINQualityRow("quality:edited-vertex-count", "edited_vertex_count", len(vertices), "count"),
                TINQualityRow("quality:edited-triangle-count", "edited_triangle_count", len(triangles), "count"),
                TINQualityRow(
                    "quality:removed-triangle-count",
                    "removed_triangle_count",
                    max(0, len(list(base.triangle_rows or [])) - len(triangles)),
                    "count",
                ),
                TINQualityRow(
                    "quality:changed-vertex-count",
                    "changed_vertex_count",
                    _changed_vertex_count({row.vertex_id: row for row in list(base.vertex_rows or [])}, vertices),
                    "count",
                ),
            ]
        )
        return TINSurface(
            schema_version=base.schema_version,
            project_id=base.project_id,
            label=label,
            unit_context=base.unit_context,
            coordinate_context=base.coordinate_context,
            source_refs=_unique_strings(list(base.source_refs or []) + [base.surface_id] + operation_ids),
            diagnostic_rows=list(base.diagnostic_rows or []),
            surface_id=surface_id,
            surface_kind=base.surface_kind,
            vertex_rows=[vertices[key] for key in sorted(vertices)],
            triangle_rows=list(triangles),
            boundary_refs=_unique_strings(list(base.boundary_refs or []) + _operation_ids(reports, "boundary_clip_rect")),
            void_refs=_unique_strings(list(base.void_refs or []) + _operation_ids(reports, "void_clip_rect")),
            quality_rows=quality,
            provenance_rows=provenance,
        )


def _coerce_operation(
    raw_operation: TINEditOperation | dict[str, object],
    *,
    index: int,
    target_surface_id: str,
) -> TINEditOperation:
    if isinstance(raw_operation, TINEditOperation):
        return raw_operation
    data = dict(raw_operation or {})
    operation_id = str(data.get("operation_id", "") or f"tin-edit:{index}")
    operation_kind = str(data.get("operation_kind", "") or data.get("kind", "") or "")
    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        parameters = {}
    return TINEditOperation(
        operation_id=operation_id,
        operation_kind=operation_kind,
        target_surface_id=str(data.get("target_surface_id", "") or target_surface_id),
        enabled=bool(data.get("enabled", True)),
        parameters=dict(parameters),
        source_ref=str(data.get("source_ref", "") or ""),
        created_at=str(data.get("created_at", "") or ""),
        notes=str(data.get("notes", "") or ""),
    )


def _rect_from_parameters(parameters: dict[str, object]) -> tuple[float, float, float, float]:
    min_x = _required_float_alias(parameters, "min_x", "x_min", "xmin")
    max_x = _required_float_alias(parameters, "max_x", "x_max", "xmax")
    min_y = _required_float_alias(parameters, "min_y", "y_min", "ymin")
    max_y = _required_float_alias(parameters, "max_y", "y_max", "ymax")
    if max_x < min_x:
        min_x, max_x = max_x, min_x
    if max_y < min_y:
        min_y, max_y = max_y, min_y
    return min_x, max_x, min_y, max_y


def _required_float_alias(parameters: dict[str, object], *keys: str) -> float:
    for key in keys:
        if key in parameters:
            return float(parameters[key])
    raise ValueError(f"Missing rectangle parameter: {keys[0]}")


def _triangle_centroid_inside_rect(
    triangle: TINTriangle,
    vertices: dict[str, TINVertex],
    rect: tuple[float, float, float, float],
) -> bool:
    pts = [vertices.get(triangle.v1), vertices.get(triangle.v2), vertices.get(triangle.v3)]
    if any(vertex is None for vertex in pts):
        return False
    cx = sum(float(vertex.x) for vertex in pts if vertex is not None) / 3.0
    cy = sum(float(vertex.y) for vertex in pts if vertex is not None) / 3.0
    min_x, max_x, min_y, max_y = rect
    return min_x <= cx <= max_x and min_y <= cy <= max_y


def _triangle_ids_from_parameters(parameters: dict[str, object]) -> set[str]:
    raw = parameters.get("triangle_ids", parameters.get("ids", parameters.get("triangle_id", [])))
    if isinstance(raw, str):
        ids: set[str] = set()
        for token in raw.replace(";", ",").split(","):
            ids.update(_expand_triangle_id_token(token))
        return ids
    if isinstance(raw, Iterable):
        ids: set[str] = set()
        for token in raw:
            ids.update(_expand_triangle_id_token(str(token)))
        return ids
    return set()


def _expand_triangle_id_token(raw_token: str) -> set[str]:
    token = str(raw_token or "").strip()
    if not token:
        return set()
    for separator in ("..", "-"):
        if separator not in token:
            continue
        left, right = token.split(separator, 1)
        range_ids = _expand_numeric_suffix_range(left.strip(), right.strip())
        if range_ids:
            return range_ids
    return {token}


def _expand_numeric_suffix_range(left: str, right: str) -> set[str]:
    left_parts = _split_numeric_suffix(left)
    right_parts = _split_numeric_suffix(right)
    if left_parts is None or right_parts is None:
        return set()
    left_prefix, start_text = left_parts
    right_prefix, end_text = right_parts
    if left_prefix and right_prefix and left_prefix != right_prefix:
        return set()
    prefix = left_prefix or right_prefix
    start = int(start_text)
    end = int(end_text)
    step = 1 if end >= start else -1
    width = max(len(start_text), len(end_text)) if start_text.startswith("0") or end_text.startswith("0") else 0
    output = set()
    for value in range(start, end + step, step):
        suffix = f"{value:0{width}d}" if width else str(value)
        output.add(f"{prefix}{suffix}")
    return output


def _split_numeric_suffix(value: str) -> tuple[str, str] | None:
    match = re.match(r"^(.*?)(\d+)$", str(value or "").strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def _vertex_updates_from_parameters(parameters: dict[str, object]) -> dict[str, float]:
    raw_rows = parameters.get("vertices", parameters.get("vertex_rows", None))
    updates: dict[str, float] = {}
    if isinstance(raw_rows, Iterable) and not isinstance(raw_rows, (str, bytes, dict)):
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            vertex_id = str(row.get("vertex_id", "") or row.get("id", "") or "").strip()
            if not vertex_id:
                continue
            value = row.get("new_z", row.get("z", None))
            if value is None:
                continue
            updates[vertex_id] = float(value)
        return updates
    vertex_id = str(parameters.get("vertex_id", "") or parameters.get("id", "") or "").strip()
    value = parameters.get("new_z", parameters.get("z", None))
    if vertex_id and value is not None:
        updates[vertex_id] = float(value)
    return updates


def _prune_orphan_vertices(
    triangles: list[TINTriangle],
    vertices: dict[str, TINVertex],
) -> tuple[list[TINTriangle], dict[str, TINVertex]]:
    used = set()
    valid_triangles = []
    for triangle in triangles:
        ids = [triangle.v1, triangle.v2, triangle.v3]
        if all(vertex_id in vertices for vertex_id in ids):
            valid_triangles.append(triangle)
            used.update(ids)
    return valid_triangles, {vertex_id: vertices[vertex_id] for vertex_id in sorted(used)}


def _changed_vertex_count(before: dict[str, TINVertex], after: dict[str, TINVertex]) -> int:
    count = 0
    for vertex_id, vertex in after.items():
        previous = before.get(vertex_id)
        if previous is not None and abs(float(previous.z) - float(vertex.z)) > 1.0e-9:
            count += 1
    return count


def _operation_ids(reports: list[TINEditReport], kind: str) -> list[str]:
    return [report.operation_id for report in reports if report.operation_kind == kind and report.status == "ok"]


def _unique_strings(values: list[object]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _overall_status(reports: list[TINEditReport]) -> str:
    if any(report.status == "ignored" for report in reports):
        return "partial"
    return "ok"


def _join_notes(*values: object) -> str:
    return "; ".join(str(value).strip() for value in values if str(value or "").strip())
