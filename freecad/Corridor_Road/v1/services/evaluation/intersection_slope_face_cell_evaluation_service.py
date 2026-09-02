"""Evaluate Intersection slope-face cells from shared-breakline result contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_slope_face_cell import (
    IntersectionSlopeFaceCellResult,
    IntersectionSlopeFaceCellRow,
)
from ...models.result.shared_breakline import SharedBreaklineResult, SharedBreaklineRow


@dataclass(frozen=True)
class IntersectionSlopeFaceCellEvaluationRequest:
    """Typed input for source-traceable slope-face cell evaluation."""

    shared_breakline_result: SharedBreaklineResult | None
    intersection_id: str = ""


class IntersectionSlopeFaceCellEvaluationService:
    """Build slope-face cell candidates without FreeCAD document state."""

    def evaluate(
        self,
        request: IntersectionSlopeFaceCellEvaluationRequest,
    ) -> IntersectionSlopeFaceCellResult:
        return _evaluate_intersection_slope_face_cells(
            request.shared_breakline_result,
            intersection_id=request.intersection_id,
        )


def _evaluate_intersection_slope_face_cells(
    shared_breakline_result: SharedBreaklineResult | None,
    *,
    intersection_id: str = "",
) -> IntersectionSlopeFaceCellResult:
    """Build cell candidates for dedicated intersection Slope Face Surface ownership."""

    if shared_breakline_result is None:
        return IntersectionSlopeFaceCellResult(
            schema_version=1,
            project_id="",
            intersection_id=str(intersection_id or ""),
            status="missing",
            diagnostic_rows=["shared_breakline_result_missing"],
        )
    project_id = str(getattr(shared_breakline_result, "project_id", "") or "")
    target_intersection_id = str(intersection_id or getattr(shared_breakline_result, "domain_ref", "") or "")
    result_id = f"intersection-slope-face-cells:{target_intersection_id or 'main'}"
    point_map = {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(shared_breakline_result, "point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }
    rows_by_role: dict[str, list[SharedBreaklineRow]] = {}
    for row in list(getattr(shared_breakline_result, "breakline_rows", []) or []):
        role = str(getattr(row, "breakline_role", "") or "")
        if role:
            rows_by_role.setdefault(role, []).append(row)

    patch_rows = rows_by_role.get("patch_to_intersection_slope_face", [])
    outer_rows = rows_by_role.get("intersection_slope_face_to_corridor_slope_face", [])
    design_rows = rows_by_role.get("intersection_slope_face_to_design_surface", [])
    curb_rows = rows_by_role.get("curb_return_to_intersection_slope_face", [])
    curb_bridge_rows = rows_by_role.get("curb_return_bridge_to_intersection_slope_face", [])
    main_side_tie_rows = rows_by_role.get("main_side_slope_face_tie", [])
    diagnostic_rows: list[str] = []
    cell_rows: list[IntersectionSlopeFaceCellRow] = []

    if not patch_rows:
        diagnostic_rows.append("intersection_slope_face_upper_gap_cell_missing")

    used_outer_refs: set[str] = set()
    used_design_refs: set[str] = set()
    upper_cell_index = 0
    for patch_index, patch_row in enumerate(patch_rows, start=1):
        alignment_ref = str(getattr(patch_row, "alignment_ref", "") or "")
        side = str(getattr(patch_row, "side", "") or "")
        outer_row = _matching_intersection_slope_face_cell_breakline(
            outer_rows,
            alignment_ref=alignment_ref,
            side=side,
            used_refs=used_outer_refs,
        )
        design_row = _matching_intersection_slope_face_cell_breakline(
            design_rows,
            alignment_ref=alignment_ref,
            side=side,
            used_refs=used_design_refs,
        )
        if outer_row is not None:
            used_outer_refs.add(str(getattr(outer_row, "breakline_id", "") or ""))
        if design_row is not None:
            used_design_refs.add(str(getattr(design_row, "breakline_id", "") or ""))
        boundary_refs = _unique_text_values(
            [
                str(getattr(patch_row, "breakline_id", "") or ""),
                str(getattr(outer_row, "breakline_id", "") or "") if outer_row is not None else "",
                str(getattr(design_row, "breakline_id", "") or "") if design_row is not None else "",
            ]
        )
        subcell_loops = _intersection_slope_face_upper_subcell_loops(
            patch_row=patch_row,
            outer_row=outer_row,
            design_row=design_row,
            point_map=point_map,
        )
        if not subcell_loops:
            subcell_loops = [_intersection_slope_face_cell_loop_points([patch_row, design_row, outer_row], point_map)]
        diagnostics: list[str] = []
        if outer_row is None:
            diagnostics.append("intersection_slope_face_cell_edge_missing:outer")
        if design_row is None:
            diagnostics.append("intersection_slope_face_cell_edge_missing:design")
        source_refs: list[str] = []
        for source_row in (patch_row, outer_row, design_row):
            if source_row is None:
                continue
            source_refs.extend(str(value or "") for value in tuple(getattr(source_row, "source_contract_refs", ()) or ()))
        for sub_index, loop_points in enumerate(subcell_loops, start=1):
            upper_cell_index += 1
            cell_diagnostics = list(diagnostics)
            closed_xy = len(loop_points) >= 4 and _intersection_slope_face_points_close_xy(loop_points[0], loop_points[-1])
            if not closed_xy:
                cell_diagnostics.append("intersection_slope_face_cell_open")
            status = "ready" if not cell_diagnostics else "warning"
            role = _intersection_slope_face_upper_cell_role(sub_index, len(subcell_loops), patch_index, len(patch_rows))
            cell_rows.append(
                IntersectionSlopeFaceCellRow(
                    cell_id=f"{result_id}:upper:{upper_cell_index}",
                    intersection_id=target_intersection_id,
                    cell_role=role,
                    alignment_ref=alignment_ref,
                    side=side,
                    inner_breakline_ref=str(getattr(patch_row, "breakline_id", "") or ""),
                    outer_breakline_ref=str(getattr(outer_row, "breakline_id", "") or "") if outer_row is not None else "",
                    left_breakline_ref=str(getattr(design_row, "breakline_id", "") or "") if design_row is not None else "",
                    boundary_breakline_refs=tuple(boundary_refs),
                    loop_points_xyz=tuple(loop_points),
                    source_intersection_refs=tuple(_unique_text_values(source_refs)),
                    source_shared_breakline_refs=tuple(boundary_refs),
                    closed_xy=closed_xy,
                    point_count=len(loop_points),
                    surface_generation_status="ready" if status == "ready" else "not_ready",
                    status=status,
                    diagnostics=tuple(cell_diagnostics),
                    notes=(
                        "Upper transition cell candidate from shared breakline rows."
                        if len(subcell_loops) <= 1
                        else f"Upper transition subcell {sub_index}/{len(subcell_loops)} from shared breakline subdivision."
                    ),
                )
            )

    if not curb_rows:
        diagnostic_rows.append("curb_return_to_intersection_slope_face_missing")
    if not main_side_tie_rows:
        diagnostic_rows.append("intersection_slope_face_main_side_tie_missing")

    used_curb_refs: set[str] = set()
    for index, tie_row in enumerate(main_side_tie_rows, start=1):
        alignment_ref = str(getattr(tie_row, "alignment_ref", "") or "")
        side = str(getattr(tie_row, "side", "") or "")
        curb_row = _matching_intersection_slope_face_cell_breakline(
            curb_rows,
            alignment_ref="",
            side=side,
            used_refs=used_curb_refs,
        )
        if curb_row is not None:
            used_curb_refs.add(str(getattr(curb_row, "breakline_id", "") or ""))
        boundary_refs = _unique_text_values(
            [
                str(getattr(tie_row, "breakline_id", "") or ""),
                str(getattr(curb_row, "breakline_id", "") or "") if curb_row is not None else "",
            ]
        )
        loop_points = _intersection_slope_face_cell_loop_points([tie_row, curb_row], point_map)
        diagnostics: list[str] = []
        if curb_row is None:
            diagnostics.append("intersection_slope_face_cell_edge_missing:curb_return")
        closed_xy = len(loop_points) >= 4 and _intersection_slope_face_points_close_xy(loop_points[0], loop_points[-1])
        if not closed_xy:
            diagnostics.append("intersection_slope_face_cell_open")
        status = "ready" if not diagnostics else "warning"
        source_refs: list[str] = []
        for source_row in (tie_row, curb_row):
            if source_row is None:
                continue
            source_refs.extend(str(value or "") for value in tuple(getattr(source_row, "source_contract_refs", ()) or ()))
        role = "main_to_side_left_tie_cell" if side == "left" or index == 1 else "main_to_side_right_tie_cell"
        cell_rows.append(
            IntersectionSlopeFaceCellRow(
                cell_id=f"{result_id}:main-side:{index}",
                intersection_id=target_intersection_id,
                cell_role=role,
                alignment_ref=alignment_ref,
                side=side,
                inner_breakline_ref=str(getattr(tie_row, "breakline_id", "") or ""),
                arc_breakline_ref=str(getattr(curb_row, "breakline_id", "") or "") if curb_row is not None else "",
                boundary_breakline_refs=tuple(boundary_refs),
                loop_points_xyz=tuple(loop_points),
                source_intersection_refs=tuple(_unique_text_values(source_refs)),
                source_shared_breakline_refs=tuple(boundary_refs),
                closed_xy=closed_xy,
                point_count=len(loop_points),
                surface_generation_status="ready" if status == "ready" else "not_ready",
                status=status,
                diagnostics=tuple(diagnostics),
                notes="Main/side road slope-face tie cell candidate from shared breakline rows.",
            )
        )

    used_bridge_refs: set[str] = set()
    for index, bridge_row in enumerate(curb_bridge_rows, start=1):
        bridge_ref = str(getattr(bridge_row, "breakline_id", "") or "")
        if bridge_ref in used_bridge_refs:
            continue
        used_bridge_refs.add(bridge_ref)
        curb_row = _nearest_intersection_slope_face_cell_breakline(
            curb_rows,
            bridge_row,
            point_map=point_map,
        )
        boundary_refs = _unique_text_values(
            [
                str(getattr(curb_row, "breakline_id", "") or "") if curb_row is not None else "",
                bridge_ref,
            ]
        )
        loop_points = _intersection_slope_face_cell_loop_points([curb_row, bridge_row], point_map)
        diagnostics: list[str] = []
        if curb_row is None:
            diagnostics.append("intersection_slope_face_cell_edge_missing:curb_return")
        if _intersection_slope_face_bridge_row_is_diagnostic_only(bridge_row):
            diagnostics.append("intersection_slope_face_diagnostic_bridge_visible_rejected")
        closed_xy = len(loop_points) >= 4 and _intersection_slope_face_points_close_xy(loop_points[0], loop_points[-1])
        if not closed_xy:
            diagnostics.append("intersection_slope_face_cell_open")
        status = "ready" if not diagnostics else "candidate"
        source_refs: list[str] = []
        for source_row in (curb_row, bridge_row):
            if source_row is None:
                continue
            source_refs.extend(str(value or "") for value in tuple(getattr(source_row, "source_contract_refs", ()) or ()))
        cell_rows.append(
            IntersectionSlopeFaceCellRow(
                cell_id=f"{result_id}:curb-return-bridge:{index}",
                intersection_id=target_intersection_id,
                cell_role="curb_return_bridge_cell",
                alignment_ref=str(getattr(curb_row, "alignment_ref", "") or "") if curb_row is not None else "",
                side=str(getattr(curb_row, "side", "") or "") if curb_row is not None else "",
                inner_breakline_ref=str(getattr(curb_row, "breakline_id", "") or "") if curb_row is not None else "",
                arc_breakline_ref=bridge_ref,
                boundary_breakline_refs=tuple(boundary_refs),
                loop_points_xyz=tuple(loop_points),
                source_intersection_refs=tuple(_unique_text_values(source_refs)),
                source_shared_breakline_refs=tuple(boundary_refs),
                closed_xy=closed_xy,
                point_count=len(loop_points),
                surface_generation_status="ready" if status == "ready" else "not_ready",
                status=status,
                diagnostics=tuple(diagnostics),
                notes="Curb-return bridge cell candidate from diagnostic shared breakline closure.",
            )
        )

    ready_count = sum(1 for row in cell_rows if str(getattr(row, "status", "") or "") == "ready")
    warning_count = sum(1 for row in cell_rows if str(getattr(row, "status", "") or "") in {"candidate", "warning"})
    error_count = sum(1 for row in cell_rows if str(getattr(row, "status", "") or "") == "error")
    open_count = sum(1 for row in cell_rows if not bool(getattr(row, "closed_xy", False)))
    missing_edge_count = sum(
        1
        for row in cell_rows
        for diagnostic in tuple(getattr(row, "diagnostics", ()) or ())
        if str(diagnostic).startswith("intersection_slope_face_cell_edge_missing")
    )
    status = "ready" if cell_rows and warning_count == 0 and error_count == 0 else "warning" if cell_rows else "missing"
    return IntersectionSlopeFaceCellResult(
        schema_version=1,
        project_id=project_id,
        cell_result_id=result_id,
        intersection_id=target_intersection_id,
        status=status,
        cell_count=len(cell_rows),
        ready_count=ready_count,
        warning_count=warning_count,
        error_count=error_count,
        open_cell_count=open_count,
        missing_edge_count=missing_edge_count,
        diagnostic_rows=diagnostic_rows,
        cell_rows=cell_rows,
    )


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


def _resample_polyline_xyz(points: list[tuple[float, float, float]], sample_count: int) -> list[tuple[float, float, float]]:
    if sample_count <= 0 or not points:
        return []
    if len(points) == 1:
        return [points[0] for _index in range(sample_count)]
    if sample_count == 1:
        return [points[0]]
    cumulative = [0.0]
    for first, second in zip(points[:-1], points[1:]):
        cumulative.append(cumulative[-1] + _xyz_distance(first, second))
    total = cumulative[-1]
    if total <= 1.0e-9:
        return [points[0] for _index in range(sample_count)]
    samples: list[tuple[float, float, float]] = []
    for sample_index in range(sample_count):
        distance = total * (float(sample_index) / float(sample_count - 1))
        segment_index = 0
        while segment_index < len(cumulative) - 2 and cumulative[segment_index + 1] < distance:
            segment_index += 1
        start = points[segment_index]
        end = points[segment_index + 1]
        segment_length = max(cumulative[segment_index + 1] - cumulative[segment_index], 1.0e-9)
        ratio = (distance - cumulative[segment_index]) / segment_length
        samples.append(
            (
                float(start[0]) + (float(end[0]) - float(start[0])) * ratio,
                float(start[1]) + (float(end[1]) - float(start[1])) * ratio,
                float(start[2]) + (float(end[2]) - float(start[2])) * ratio,
            )
        )
    return samples


def _xyz_distance(first, second) -> float:
    return math.sqrt(
        (float(first[0]) - float(second[0])) ** 2
        + (float(first[1]) - float(second[1])) ** 2
        + (float(first[2]) - float(second[2])) ** 2
    )


def _matching_intersection_slope_face_cell_breakline(
    rows: list[SharedBreaklineRow],
    *,
    alignment_ref: str,
    side: str,
    used_refs: set[str],
):
    for row in list(rows or []):
        row_id = str(getattr(row, "breakline_id", "") or "")
        if row_id in used_refs:
            continue
        if alignment_ref and str(getattr(row, "alignment_ref", "") or "") != alignment_ref:
            continue
        if side and str(getattr(row, "side", "") or "") != side:
            continue
        return row
    for row in list(rows or []):
        row_id = str(getattr(row, "breakline_id", "") or "")
        if row_id not in used_refs:
            return row
    return None


def _intersection_slope_face_bridge_row_is_diagnostic_only(row) -> bool:
    if row is None:
        return True
    status = str(getattr(row, "source_status", "") or "").strip().lower()
    text = " ".join(
        [
            status,
            str(getattr(row, "breakline_role", "") or ""),
            str(getattr(row, "notes", "") or ""),
            *[str(value or "") for value in tuple(getattr(row, "source_contract_refs", ()) or ())],
            *[str(value or "") for value in tuple(getattr(row, "diagnostic_rows", ()) or ())],
        ]
    ).lower()
    return (
        status in {"diagnostic", "warning", "candidate"}
        or "diagnostic" in text
        or "bridge_required" in text
        or "warning:" in text
    )


def _nearest_intersection_slope_face_cell_breakline(
    rows: list[SharedBreaklineRow],
    target_row,
    *,
    point_map: dict[str, object],
):
    target_points = _intersection_slope_face_cell_row_points(target_row, point_map)
    if not target_points:
        return None
    best_row = None
    best_score: tuple[int, float] | None = None
    for row in list(rows or []):
        points = _intersection_slope_face_cell_row_points(row, point_map)
        if not points:
            continue
        distance = min(_xy_distance(first, second) for first in target_points for second in points)
        shared_endpoint = any(
            _intersection_slope_face_points_close_xy(first, second)
            for first in target_points
            for second in points
        )
        score = (0 if shared_endpoint else 1, distance)
        if best_score is None or score < best_score:
            best_score = score
            best_row = row
    return best_row


def _intersection_slope_face_upper_cell_role(
    sub_index: int,
    sub_count: int,
    patch_index: int,
    patch_count: int,
) -> str:
    if sub_count >= 3:
        if sub_index == 1:
            return "upper_left_transition_cell"
        if sub_index == sub_count:
            return "upper_right_transition_cell"
        return "upper_mid_transition_cell"
    if patch_count >= 3:
        if patch_index == 1:
            return "upper_left_transition_cell"
        if patch_index == patch_count:
            return "upper_right_transition_cell"
        return "upper_mid_transition_cell"
    if sub_count == 2:
        return "upper_left_transition_cell" if sub_index == 1 else "upper_right_transition_cell"
    return "upper_left_transition_cell"


def _intersection_slope_face_upper_subcell_loops(
    *,
    patch_row,
    outer_row,
    design_row,
    point_map: dict[str, object],
) -> list[list[tuple[float, float, float]]]:
    if patch_row is None or outer_row is None or design_row is None:
        return []
    inner_points = _intersection_slope_face_cell_row_points(patch_row, point_map)
    outer_points = _intersection_slope_face_cell_row_points(outer_row, point_map)
    design_points = _intersection_slope_face_cell_row_points(design_row, point_map)
    if len(inner_points) < 2 or len(outer_points) < 2 or len(design_points) < 2:
        return []
    subcell_count = 3 if max(len(inner_points), len(outer_points), len(design_points)) >= 4 else 1
    if subcell_count <= 1:
        return []
    inner_samples = _resample_polyline_xyz(inner_points, subcell_count + 1)
    outer_samples = _resample_polyline_xyz(outer_points, subcell_count + 1)
    design_samples = _resample_polyline_xyz(design_points, subcell_count + 1)
    if len(inner_samples) != subcell_count + 1 or len(outer_samples) != subcell_count + 1:
        return []
    loops: list[list[tuple[float, float, float]]] = []
    for index in range(subcell_count):
        left_inner = inner_samples[index]
        right_inner = inner_samples[index + 1]
        right_outer = outer_samples[index + 1]
        left_outer = outer_samples[index]
        left_design = design_samples[index] if len(design_samples) == subcell_count + 1 else left_inner
        right_design = design_samples[index + 1] if len(design_samples) == subcell_count + 1 else right_inner
        loop = [
            left_inner,
            right_inner,
            right_design,
            right_outer,
            left_outer,
            left_design,
            left_inner,
        ]
        loops.append(_intersection_slope_face_simplified_closed_loop(loop))
    return [loop for loop in loops if len(loop) >= 4]


def _intersection_slope_face_cell_row_points(row, point_map: dict[str, object]) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    if row is None:
        return points
    for ref in tuple(getattr(row, "point_refs", ()) or ()):
        point = point_map.get(str(ref or ""))
        if point is None:
            continue
        xyz = _row_xyz_tuple(point)
        if not points or not _intersection_slope_face_points_close_xyz(points[-1], xyz):
            points.append(xyz)
    return points


def _intersection_slope_face_simplified_closed_loop(
    points: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    output: list[tuple[float, float, float]] = []
    for point in list(points or []):
        if not output or not _intersection_slope_face_points_close_xy(output[-1], point):
            output.append(point)
    if output and not _intersection_slope_face_points_close_xy(output[0], output[-1]):
        output.append(output[0])
    return output


def _intersection_slope_face_cell_loop_points(
    rows: list[SharedBreaklineRow | None],
    point_map: dict[str, object],
) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for row in list(rows or []):
        if row is None:
            continue
        for ref in tuple(getattr(row, "point_refs", ()) or ()):
            point = point_map.get(str(ref or ""))
            if point is None:
                continue
            xyz = _row_xyz_tuple(point)
            if not points or not _intersection_slope_face_points_close_xyz(points[-1], xyz):
                points.append(xyz)
    if points and not _intersection_slope_face_points_close_xy(points[0], points[-1]):
        points.append(points[0])
    return points


def _intersection_slope_face_points_close_xy(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    return math.hypot(float(first[0]) - float(second[0]), float(first[1]) - float(second[1])) <= tolerance


def _intersection_slope_face_points_close_xyz(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    return (
        math.sqrt(
            (float(first[0]) - float(second[0])) ** 2
            + (float(first[1]) - float(second[1])) ** 2
            + (float(first[2]) - float(second[2])) ** 2
        )
        <= tolerance
    )


def _row_xyz_tuple(row) -> tuple[float, float, float]:
    return (
        float(getattr(row, "x", 0.0) or 0.0),
        float(getattr(row, "y", 0.0) or 0.0),
        float(getattr(row, "z", 0.0) or 0.0),
    )


def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


__all__ = [
    "IntersectionSlopeFaceCellEvaluationRequest",
    "IntersectionSlopeFaceCellEvaluationService",
]
