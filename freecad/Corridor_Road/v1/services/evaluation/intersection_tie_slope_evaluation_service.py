"""Evaluate source-owned Intersection tie-slope result contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_tie_slope import (
    IntersectionTieSlopeResult,
    IntersectionTieSlopeRow,
)
from ...models.result.intersection_boundary_segment import (
    IntersectionBoundarySegmentResult,
)
from ...models.result.intersection_slope_face_boundary import (
    IntersectionSlopeFaceBoundaryResult,
)
from ...models.result.intersection_tie_in_edge import IntersectionTieInEdgeResult
from ...services.geometry import (
    xy_distance,
    xy_polygon_self_intersects,
    xy_polygon_signed_area,
    xyz_point,
)
from .intersection_boundary_segment_evaluation_service import (
    IntersectionBoundarySegmentEvaluationRequest,
    IntersectionBoundarySegmentEvaluationService,
)
from .intersection_evaluation_service import (
    IntersectionEvaluationService,
    IntersectionPatchPrerequisiteResult,
)
from .intersection_slope_face_boundary_evaluation_service import (
    IntersectionSlopeFaceBoundaryEvaluationRequest,
    IntersectionSlopeFaceBoundaryEvaluationService,
)
from .intersection_tie_in_edge_evaluation_service import (
    IntersectionTieInEdgeEvaluationRequest,
    IntersectionTieInEdgeEvaluationService,
)


@dataclass(frozen=True)
class IntersectionTieSlopeEvaluationRequest:
    """Typed input for tie-slope evaluation."""

    applied_section_set: object | None
    prerequisite: IntersectionPatchPrerequisiteResult
    intersection_model: object | None = None
    boundary_segment_result: object | None = None
    slope_face_boundary_result: object | None = None


class IntersectionTieSlopeEvaluationService:
    """Build tie-slope contracts without document or preview geometry."""

    def evaluate(
        self,
        request: IntersectionTieSlopeEvaluationRequest,
    ) -> IntersectionTieSlopeResult:
        return _evaluate_intersection_tie_slope(
            request.applied_section_set,
            prerequisite=request.prerequisite,
            intersection_model=request.intersection_model,
            boundary_segment_result=request.boundary_segment_result,
            slope_face_boundary_result=request.slope_face_boundary_result,
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


def _intersection_row_by_id(intersection_model, intersection_id: str):
    target = str(intersection_id or "").strip()
    if intersection_model is None or not target:
        return None
    for row in list(getattr(intersection_model, "intersection_rows", []) or []):
        if str(getattr(row, "intersection_id", "") or "").strip() == target:
            return row
    return None


def corridor_intersection_tie_in_edge_result(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> IntersectionTieInEdgeResult:
    """Compatibility wrapper for typed tie-in edge evaluation."""

    return IntersectionTieInEdgeEvaluationService().evaluate(
        IntersectionTieInEdgeEvaluationRequest(
            applied_section_set=applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
    )


def corridor_intersection_boundary_segment_result(
    tie_in_result: IntersectionTieInEdgeResult,
    *,
    intersection_model=None,
) -> IntersectionBoundarySegmentResult:
    """Compatibility wrapper for typed boundary-segment evaluation."""

    return IntersectionBoundarySegmentEvaluationService().evaluate(
        IntersectionBoundarySegmentEvaluationRequest(
            tie_in_result=tie_in_result,
            intersection_model=intersection_model,
        )
    )


def corridor_intersection_slope_face_boundary_result(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> IntersectionSlopeFaceBoundaryResult:
    """Compatibility wrapper for typed slope-face boundary evaluation."""

    return IntersectionSlopeFaceBoundaryEvaluationService().evaluate(
        IntersectionSlopeFaceBoundaryEvaluationRequest(
            applied_section_set=applied_section_set,
            prerequisite=prerequisite,
            intersection_model=intersection_model,
        )
    )


def _evaluate_intersection_tie_slope(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    boundary_segment_result=None,
    slope_face_boundary_result=None,
) -> IntersectionTieSlopeResult:
    """Build source-owned tie-slope contracts from Applied Sections to intersection boundaries."""

    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    diagnostics: list[str] = []
    project_id = str(getattr(applied_section_set, "project_id", "") or "") if applied_section_set is not None else ""
    if applied_section_set is None:
        diagnostics.append("intersection_tie_slope_missing: Applied Sections are required.")
        return IntersectionTieSlopeResult(
            schema_version=1,
            project_id=project_id,
            label=f"Intersection Tie Slope - {intersection_id or 'unknown'}",
            tie_slope_result_id=f"intersection-tie-slope:{intersection_id or 'unknown'}",
            intersection_id=intersection_id,
            status="missing",
            diagnostic_rows=diagnostics,
        )
    if str(getattr(prerequisite, "intersection_kind", "") or "").strip().lower() == "roundabout":
        return IntersectionTieSlopeResult(
            schema_version=1,
            project_id=project_id,
            label=f"Intersection Tie Slope - {intersection_id or 'unknown'}",
            tie_slope_result_id=f"intersection-tie-slope:{intersection_id or 'unknown'}",
            intersection_id=intersection_id,
            status="missing",
            diagnostic_rows=(
                "info:roundabout_generic_intersection_tie_slope_disabled",
                "roundabout_tie_slope_requires_dedicated_roundabout_contract",
            ),
        )

    diagnostics.append(
        "intersection_tie_slope_gap_cell_candidate:"
        " terminal Applied Section side-slope edges are exposed; "
        "intersection outer-edge matching, cap clipping, and unsafe-loop review drive surface readiness."
    )
    diagnostics.append(
        "intersection_tie_slope_sta_separation_required:"
        " legacy single-station Tie Slope output is diagnostic-only until Region/control-area STA "
        "and Applied Section intersection STA are paired explicitly."
    )
    tie_boundary_result = _intersection_tie_slope_boundary_segment_result(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
        boundary_segment_result=boundary_segment_result,
    )
    tie_slope_boundary_result = slope_face_boundary_result or corridor_intersection_slope_face_boundary_result(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    tie_boundary_loop_result = _intersection_tie_slope_boundary_loop_result(
        intersection_model,
        applied_section_set,
    )
    rows: list[IntersectionTieSlopeRow] = []
    for spec in _intersection_tie_slope_gap_specs(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    ):
        alignment_ref = str(spec.get("alignment_ref", "") or "")
        road_role = str(spec.get("road_role", "") or "")
        gap_role = str(spec.get("gap_role", "") or "")
        side = str(spec.get("side", "") or "")
        terminal_section = spec.get("terminal_section")
        station_span = dict(spec.get("station_span", {}) or {})
        row_diagnostics: list[str] = []
        for diagnostic in list(station_span.get("diagnostics", []) or []):
            row_diagnostics.append(str(diagnostic or ""))
        road_edge = _intersection_tie_slope_terminal_road_edge(terminal_section, side=side)
        if not road_edge:
            row_diagnostics.append("intersection_tie_slope_road_outer_edge_missing")
        intersection_edge, intersection_ref, intersection_status, intersection_diagnostics = (
            _intersection_tie_slope_intersection_outer_edge_for_gap(
                tie_boundary_result,
                tie_slope_boundary_result,
                tie_boundary_loop_result,
                road_edge,
                alignment_ref=alignment_ref,
                road_role=road_role,
                gap_role=gap_role,
                side=side,
            )
        )
        row_diagnostics.extend(intersection_diagnostics)
        if not intersection_edge:
            row_diagnostics.append("intersection_tie_slope_intersection_outer_edge_missing")
        (
            oriented_road_edge,
            oriented_intersection_edge,
            start_cap_edge,
            end_cap_edge,
            cap_diagnostics,
        ) = _intersection_tie_slope_clipped_cap_edges(
            road_edge,
            intersection_edge,
            control_area_ref=str(spec.get("control_area_ref", "") or ""),
            transition_span_length=float(station_span.get("transition_span_length", 0.0) or 0.0),
        )
        row_diagnostics.extend(cap_diagnostics)
        if not start_cap_edge or not end_cap_edge:
            row_diagnostics.append("intersection_tie_slope_cap_edge_missing")
        if oriented_road_edge:
            road_edge = oriented_road_edge
        if oriented_intersection_edge:
            intersection_edge = oriented_intersection_edge
        (
            loop_points,
            inner_edge,
            outer_edge,
            loop_start_cap_edge,
            loop_end_cap_edge,
            loop_area_xy,
            loop_diagnostics,
        ) = _intersection_tie_slope_closed_loop_edges(
            tuple(intersection_edge),
            tuple(road_edge),
        )
        row_diagnostics.extend(loop_diagnostics)
        unsafe_loop_diagnostics = (
            _intersection_tie_slope_unsafe_loop_diagnostics(
                tuple(loop_points),
                inner_edge=tuple(inner_edge),
                outer_edge=tuple(outer_edge),
                start_cap_edge=tuple(loop_start_cap_edge),
                end_cap_edge=tuple(loop_end_cap_edge),
                loop_area_xy=float(loop_area_xy or 0.0),
            )
            if loop_points and loop_area_xy > 1.0e-6 and not loop_diagnostics
            else ()
        )
        row_diagnostics.extend(unsafe_loop_diagnostics)
        transition_cell_diagnostics = (
            _intersection_tie_slope_transition_cell_window_diagnostics(
                tuple(loop_points),
                inner_edge=tuple(inner_edge),
                outer_edge=tuple(outer_edge),
                start_cap_edge=tuple(loop_start_cap_edge),
                end_cap_edge=tuple(loop_end_cap_edge),
                transition_span_length=float(station_span.get("transition_span_length", 0.0) or 0.0),
                intersection_ref=intersection_ref,
            )
            if loop_points and loop_area_xy > 1.0e-6 and not loop_diagnostics and not unsafe_loop_diagnostics
            else ()
        )
        row_diagnostics.extend(transition_cell_diagnostics)
        if (
            loop_points
            and loop_area_xy > 1.0e-6
            and not loop_diagnostics
            and not unsafe_loop_diagnostics
            and not any("rejected" in item for item in transition_cell_diagnostics)
        ):
            row_diagnostics.append("intersection_tie_slope_unsafe_loop_review_passed")
            row_diagnostics.append("intersection_tie_slope_sta_separation_required")
            row_diagnostics.append("intersection_tie_slope_legacy_single_station_generation_disabled")
            surface_generation_status = "sta_transition_required"
            row_status = "warning"
        elif unsafe_loop_diagnostics or transition_cell_diagnostics:
            surface_generation_status = "unsafe_loop_rejected"
            row_status = "warning"
        else:
            surface_generation_status = "contract_only"
            row_status = "warning"
        closed_xy = bool(loop_points) and _intersection_slope_face_points_close_xy(loop_points[0], loop_points[-1])
        cap_rejected = any("intersection_tie_slope_cap_full_control_area_strip_rejected" in item for item in cap_diagnostics)
        if loop_start_cap_edge and not start_cap_edge and not cap_rejected:
            start_cap_edge = loop_start_cap_edge
        if loop_end_cap_edge and not end_cap_edge and not cap_rejected:
            end_cap_edge = loop_end_cap_edge
        section_ref = str(getattr(terminal_section, "applied_section_id", "") or "") if terminal_section is not None else ""
        if not section_ref:
            row_diagnostics.append("intersection_tie_slope_terminal_side_slope_section_missing")
        control_area_ref = str(spec.get("control_area_ref", "") or "")
        tie_slope_id = (
            f"intersection-tie-slope:{intersection_id or 'unknown'}:"
            f"{_safe_id_fragment(road_role or 'road')}:{_safe_id_fragment(gap_role or 'gap')}:{_safe_id_fragment(side or 'side')}"
        )
        breakline_refs = _intersection_tie_slope_breakline_refs(intersection_id, tie_slope_id)
        shared_breakline_refs = tuple(
            _unique_text_values(
                [
                    breakline_refs["inner"],
                    breakline_refs["outer"],
                    breakline_refs["start_cap"],
                    breakline_refs["end_cap"],
                ]
            )
        )
        rows.append(
            IntersectionTieSlopeRow(
                tie_slope_id=tie_slope_id,
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                road_role=road_role,
                side=side,
                gap_role=gap_role,
                leg_ref=str(spec.get("leg_ref", "") or ""),
                control_area_ref=control_area_ref,
                region_start_sta=float(station_span.get("region_start_sta", 0.0) or 0.0),
                region_end_sta=float(station_span.get("region_end_sta", 0.0) or 0.0),
                intersection_start_sta=float(station_span.get("intersection_start_sta", 0.0) or 0.0),
                intersection_end_sta=float(station_span.get("intersection_end_sta", 0.0) or 0.0),
                transition_outer_sta=float(station_span.get("transition_outer_sta", 0.0) or 0.0),
                transition_inner_sta=float(station_span.get("transition_inner_sta", 0.0) or 0.0),
                transition_window_start_sta=float(station_span.get("transition_window_start_sta", 0.0) or 0.0),
                transition_window_end_sta=float(station_span.get("transition_window_end_sta", 0.0) or 0.0),
                transition_span_length=float(station_span.get("transition_span_length", 0.0) or 0.0),
                transition_span_role=str(station_span.get("transition_span_role", "") or ""),
                transition_window_kind=str(station_span.get("transition_window_kind", "") or ""),
                road_outer_edge_xyz=tuple(road_edge),
                intersection_outer_edge_xyz=tuple(intersection_edge),
                inner_intersection_edge_xyz=tuple(inner_edge or intersection_edge),
                outer_applied_section_edge_xyz=tuple(outer_edge or road_edge),
                start_cap_edge_xyz=tuple(start_cap_edge),
                end_cap_edge_xyz=tuple(end_cap_edge),
                loop_points_xyz=tuple(loop_points),
                loop_area_xy=float(loop_area_xy or 0.0),
                source_applied_section_refs=tuple([section_ref] if section_ref else ()),
                last_applied_section_refs=tuple([section_ref] if section_ref else ()),
                source_intersection_boundary_ref=intersection_ref,
                source_control_area_cap_refs=tuple([control_area_ref] if control_area_ref else ()),
                matched_intersection_contact_refs=tuple([intersection_ref] if intersection_ref else ()),
                intersection_contact_status=intersection_status,
                shared_breakline_refs=shared_breakline_refs,
                inner_breakline_ref=breakline_refs["inner"],
                outer_breakline_ref=breakline_refs["outer"],
                start_cap_breakline_ref=breakline_refs["start_cap"],
                end_cap_breakline_ref=breakline_refs["end_cap"],
                closed_xy=closed_xy,
                point_count=len(loop_points) if loop_points else len(road_edge) + len(intersection_edge) + len(start_cap_edge) + len(end_cap_edge),
                surface_generation_status=surface_generation_status,
                status=row_status,
                diagnostics=tuple(_unique_text_values(row_diagnostics)),
                recommended_action=(
                    "Build separated Region/control-area to Applied Section intersection STA transition before generating Tie Slope surface"
                    if "intersection_tie_slope_sta_separation_required" in row_diagnostics
                    else "Match this gap-cell to an intersection outer boundary before generating surface"
                ),
                notes=(
                    f"gap_role={gap_role}; road_role={road_role}; side={side}; "
                    f"alignment={alignment_ref}; leg_ref={spec.get('leg_ref', '')}; "
                    f"control_area_ref={control_area_ref}; terminal_section={section_ref or '-'}; "
                    f"region_sta={float(station_span.get('region_start_sta', 0.0) or 0.0):.3f}->"
                    f"{float(station_span.get('region_end_sta', 0.0) or 0.0):.3f}; "
                    f"intersection_sta={float(station_span.get('intersection_start_sta', 0.0) or 0.0):.3f}->"
                    f"{float(station_span.get('intersection_end_sta', 0.0) or 0.0):.3f}; "
                    f"transition_sta={float(station_span.get('transition_inner_sta', 0.0) or 0.0):.3f}->"
                    f"{float(station_span.get('transition_outer_sta', 0.0) or 0.0):.3f}; "
                    f"transition_window_sta={float(station_span.get('transition_window_start_sta', 0.0) or 0.0):.3f}->"
                    f"{float(station_span.get('transition_window_end_sta', 0.0) or 0.0):.3f}; "
                    f"transition_span={float(station_span.get('transition_span_length', 0.0) or 0.0):.3f}; "
                    f"transition_span_role={station_span.get('transition_span_role', '') or '-'}; "
                    f"transition_window_kind={station_span.get('transition_window_kind', '') or '-'}; "
                    f"transition_outer_edge_selector_sta={float(station_span.get('transition_outer_sta', 0.0) or 0.0):.3f}; "
                    f"transition_inner_edge_selector_sta={float(station_span.get('transition_inner_sta', 0.0) or 0.0):.3f}; "
                    f"road_outer_edge={'accepted' if road_edge else 'missing'}; "
                    f"intersection_outer_edge={intersection_status}; "
                    f"intersection_outer_edge_ref={intersection_ref or '-'}; "
                    f"cap_source=accepted_transition_endpoint_pair; "
                    f"caps={'accepted' if start_cap_edge and end_cap_edge else 'missing'}; "
                    f"loop={'closed' if closed_xy else 'open'}; "
                    f"loop_area={float(loop_area_xy or 0.0):.3f}; "
                    f"transition_cell_window={'accepted' if any('intersection_tie_slope_transition_cell_window_accepted' in item for item in transition_cell_diagnostics) else 'not_ready'}; "
                    f"generation={surface_generation_status}"
                ),
            )
        )
    return IntersectionTieSlopeResult(
        schema_version=1,
        project_id=project_id,
        label=f"Intersection Tie Slope - {intersection_id or 'unknown'}",
        tie_slope_result_id=f"intersection-tie-slope:{intersection_id or 'unknown'}",
        intersection_id=intersection_id,
        status="ready" if rows and all(str(getattr(row, "status", "") or "") == "ready" for row in rows) else ("warning" if rows else "missing"),
        tie_slope_count=len(rows),
        ready_count=sum(1 for row in rows if str(getattr(row, "status", "") or "") == "ready"),
        warning_count=sum(1 for row in rows if str(getattr(row, "status", "") or "") == "warning"),
        error_count=0,
        diagnostic_rows=diagnostics,
        tie_slope_rows=rows,
    )


def _intersection_tie_slope_breakline_refs(intersection_id: str, tie_slope_id: str) -> dict[str, str]:
    result_id = f"shared-breakline:intersection:{intersection_id or 'main'}"
    safe_tie_id = _safe_id_fragment(tie_slope_id or "tie-slope")
    return {
        "inner": f"{result_id}:intersection-tie-slope-transition-inner:{safe_tie_id}",
        "outer": f"{result_id}:intersection-tie-slope-transition-outer:{safe_tie_id}",
        "start_cap": f"{result_id}:intersection-tie-slope-start-cap:{safe_tie_id}",
        "end_cap": f"{result_id}:intersection-tie-slope-end-cap:{safe_tie_id}",
    }


def _intersection_tie_slope_boundary_segment_result(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
    boundary_segment_result=None,
):
    if boundary_segment_result is not None:
        return boundary_segment_result
    tie_in_result = corridor_intersection_tie_in_edge_result(
        applied_section_set,
        prerequisite=prerequisite,
        intersection_model=intersection_model,
    )
    return corridor_intersection_boundary_segment_result(
        tie_in_result,
        intersection_model=intersection_model,
    )


def _intersection_tie_slope_boundary_loop_result(intersection_model, applied_section_set):
    if intersection_model is None:
        return None
    service = IntersectionEvaluationService()
    topology = service.evaluate_topology(intersection_model)
    edge_network = service.evaluate_edge_network(intersection_model, topology)
    surface_zones = service.evaluate_surface_zones(intersection_model, edge_network)
    slope_loops = service.evaluate_slope_face_loops(intersection_model, surface_zones, edge_network, applied_section_set)
    return service.evaluate_boundary_loops(intersection_model, surface_zones, edge_network, slope_loops, applied_section_set)


def _intersection_tie_slope_intersection_outer_edge_for_gap(
    boundary_segment_result,
    slope_face_boundary_result,
    boundary_loop_result,
    road_edge: tuple[tuple[float, float, float], ...],
    *,
    alignment_ref: str,
    road_role: str,
    gap_role: str,
    side: str,
) -> tuple[tuple[tuple[float, float, float], ...], str, str, tuple[str, ...]]:
    if not road_edge:
        return (), "", "missing", ("intersection_tie_slope_local_window_road_edge_missing",)
    candidates: list[tuple[float, tuple[tuple[float, float, float], ...], str, tuple[str, ...]]] = []
    rejected: list[str] = []
    for segment_ref, edge in _intersection_tie_slope_intersection_edge_candidates(
        boundary_segment_result,
        slope_face_boundary_result,
        boundary_loop_result,
        alignment_ref=alignment_ref,
        side=side,
    ):
        if _xy_distance(edge[0], edge[1]) <= 1.0e-6:
            rejected.append(f"intersection_tie_slope_intersection_outer_edge_degenerate:{segment_ref or 'unknown'}")
            continue
        diagnostics = _intersection_tie_slope_local_gap_window_diagnostics(
            road_edge,
            edge,
            road_role=road_role,
            gap_role=gap_role,
            side=side,
            segment_ref=segment_ref,
        )
        score = _intersection_tie_slope_gap_candidate_score(road_edge, edge)
        blocking = [item for item in diagnostics if "rejected" in item or "too_large" in item or "too_far" in item]
        if blocking:
            rejected.extend(blocking)
            continue
        candidates.append((score, edge, segment_ref, diagnostics))
    if not candidates:
        return (), "", "missing", tuple(_unique_text_values(rejected or ["intersection_tie_slope_intersection_outer_edge_missing"]))
    _score, edge, segment_ref, diagnostics = min(candidates, key=lambda item: item[0])
    return edge, segment_ref, "accepted", tuple(_unique_text_values([*diagnostics, "intersection_tie_slope_local_window_accepted"]))


def _intersection_tie_slope_clipped_cap_edges(
    road_edge: tuple[tuple[float, float, float], ...],
    intersection_edge: tuple[tuple[float, float, float], ...],
    *,
    control_area_ref: str,
    transition_span_length: float = 0.0,
) -> tuple[
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    tuple[str, ...],
]:
    if len(tuple(road_edge or ())) < 2 or len(tuple(intersection_edge or ())) < 2:
        return tuple(road_edge or ()), tuple(intersection_edge or ()), (), (), (
            "intersection_tie_slope_cap_edge_source_missing",
        )
    road_start, road_end = _intersection_tie_slope_endpoint_pair(tuple(road_edge))
    int_start, int_end = _intersection_tie_slope_endpoint_pair(tuple(intersection_edge))
    forward_cost = _xy_distance(road_start, int_start) + _xy_distance(road_end, int_end)
    reverse_cost = _xy_distance(road_start, int_end) + _xy_distance(road_end, int_start)
    if reverse_cost < forward_cost:
        int_start, int_end = int_end, int_start
        oriented_intersection = (int_start, int_end)
    else:
        oriented_intersection = (int_start, int_end)
    oriented_road = (road_start, road_end)
    start_cap = (road_start, int_start)
    end_cap = (road_end, int_end)
    diagnostics: list[str] = []
    road_len = _xy_distance(oriented_road[0], oriented_road[1])
    intersection_len = _xy_distance(oriented_intersection[0], oriented_intersection[1])
    start_cap_len = _xy_distance(start_cap[0], start_cap[1])
    end_cap_len = _xy_distance(end_cap[0], end_cap[1])
    edge_scale = max(road_len, intersection_len, 1.0)
    span_scale = max(float(transition_span_length or 0.0), 1.0)
    cap_limit = max(30.0, edge_scale * 8.0, span_scale * 4.0)
    start_cap_valid = True
    end_cap_valid = True
    if start_cap_len <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_start_cap_degenerate")
        start_cap_valid = False
    if end_cap_len <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_end_cap_degenerate")
        end_cap_valid = False
    if start_cap_len > cap_limit:
        diagnostics.append(
            "intersection_tie_slope_cap_full_control_area_strip_rejected:"
            f"start_cap={start_cap_len:.3f}; limit={cap_limit:.3f}; control_area_ref={control_area_ref or '-'}"
        )
        start_cap_valid = False
    if end_cap_len > cap_limit:
        diagnostics.append(
            "intersection_tie_slope_cap_full_control_area_strip_rejected:"
            f"end_cap={end_cap_len:.3f}; limit={cap_limit:.3f}; control_area_ref={control_area_ref or '-'}"
        )
        end_cap_valid = False
    if not diagnostics:
        diagnostics.append(
            "intersection_tie_slope_cap_edges_clipped:"
            f"control_area_ref={control_area_ref or '-'}; source=accepted_transition_endpoint_pair"
        )
    return (
        oriented_road,
        oriented_intersection,
        start_cap if start_cap_valid else (),
        end_cap if end_cap_valid else (),
        tuple(_unique_text_values(diagnostics)),
    )


def _intersection_tie_slope_intersection_edge_candidates(
    boundary_segment_result,
    slope_face_boundary_result,
    boundary_loop_result,
    *,
    alignment_ref: str,
    side: str,
) -> list[tuple[str, tuple[tuple[float, float, float], tuple[float, float, float]]]]:
    candidates: list[tuple[str, tuple[tuple[float, float, float], tuple[float, float, float]]]] = []
    for segment in list(getattr(boundary_segment_result, "segment_rows", []) or []):
        if str(getattr(segment, "segment_kind", "") or "").strip() != "tie_in":
            continue
        if str(getattr(segment, "alignment_ref", "") or "").strip() != str(alignment_ref or "").strip():
            continue
        if str(getattr(segment, "side", "") or "").strip() != str(side or "").strip():
            continue
        candidates.append((str(getattr(segment, "boundary_segment_id", "") or "").strip(), _intersection_tie_slope_segment_edge(segment)))
    for boundary_row in list(getattr(slope_face_boundary_result, "boundary_rows", []) or []):
        if str(getattr(boundary_row, "alignment_ref", "") or "").strip() != str(alignment_ref or "").strip():
            continue
        if str(getattr(boundary_row, "side", "") or "").strip() != str(side or "").strip():
            continue
        points = tuple(_xyz_tuple(point) for point in tuple(getattr(boundary_row, "inner_points_xyz", ()) or ()))
        if len(points) >= 2:
            candidates.append((str(getattr(boundary_row, "source_intersection_surface_ref", "") or getattr(boundary_row, "boundary_id", "") or ""), (points[0], points[-1])))
    boundary_loop_segments = list(getattr(boundary_loop_result, "segment_rows", []) or []) if boundary_loop_result is not None else []
    for segment in boundary_loop_segments:
        edge = (
            _xyz_tuple(getattr(segment, "from_xyz", (0.0, 0.0, 0.0))),
            _xyz_tuple(getattr(segment, "to_xyz", (0.0, 0.0, 0.0))),
        )
        if _xy_distance(edge[0], edge[1]) <= 1.0e-6:
            continue
        role_text = " ".join(
            [
                str(getattr(segment, "segment_role", "") or ""),
                str(getattr(segment, "notes", "") or ""),
                " ".join(str(ref or "") for ref in tuple(getattr(segment, "source_refs", ()) or ())),
                " ".join(str(ref or "") for ref in tuple(getattr(segment, "expected_consumers", ()) or ())),
            ]
        ).lower()
        if any(token in role_text for token in ("hole", "interior", "pavement_center", "central_junction")):
            continue
        candidates.append((str(getattr(segment, "segment_id", "") or "").strip(), edge))
    return candidates


def _intersection_tie_slope_segment_edge(segment) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    chord_points = tuple(_xyz_tuple(point) for point in tuple(getattr(segment, "chord_points_xyz", ()) or ()))
    if len(chord_points) >= 2:
        for start_index in range(0, len(chord_points) - 1):
            start = chord_points[start_index]
            for end in reversed(chord_points[start_index + 1:]):
                if _xy_distance(start, end) > 1.0e-6:
                    return (start, end)
    return (
        _xyz_tuple(getattr(segment, "start_xyz", (0.0, 0.0, 0.0))),
        _xyz_tuple(getattr(segment, "end_xyz", (0.0, 0.0, 0.0))),
    )


def _intersection_tie_slope_local_gap_window_diagnostics(
    road_edge: tuple[tuple[float, float, float], ...],
    intersection_edge: tuple[tuple[float, float, float], ...],
    *,
    road_role: str,
    gap_role: str,
    side: str,
    segment_ref: str,
) -> tuple[str, ...]:
    road_pair = _intersection_tie_slope_endpoint_pair(tuple(road_edge))
    intersection_pair = _intersection_tie_slope_endpoint_pair(tuple(intersection_edge))
    road_len = _xy_distance(road_pair[0], road_pair[1])
    intersection_len = _xy_distance(intersection_pair[0], intersection_pair[1])
    if road_len <= 1.0e-6 or intersection_len <= 1.0e-6:
        return (f"intersection_tie_slope_local_window_rejected_degenerate:{segment_ref or 'unknown'}",)
    road_mid = _intersection_tie_slope_edge_midpoint(road_pair)
    intersection_mid = _intersection_tie_slope_edge_midpoint(intersection_pair)
    mid_distance = _xy_distance(road_mid, intersection_mid)
    forward_cap = _xy_distance(road_pair[0], intersection_pair[0]) + _xy_distance(road_pair[1], intersection_pair[1])
    reverse_cap = _xy_distance(road_pair[0], intersection_pair[1]) + _xy_distance(road_pair[1], intersection_pair[0])
    cap_distance = min(forward_cap, reverse_cap) / 2.0
    bbox_diag = _intersection_tie_slope_bbox_diagonal([*road_pair, *intersection_pair])
    scale = max(road_len, intersection_len, 1.0)
    diagnostics: list[str] = [
        (
            "intersection_tie_slope_local_window_candidate:"
            f"{segment_ref or 'unknown'}; road_role={road_role}; gap_role={gap_role}; side={side}; "
            f"mid_distance={mid_distance:.3f}; cap_distance={cap_distance:.3f}; bbox_diag={bbox_diag:.3f}"
        )
    ]
    if mid_distance > max(18.0, scale * 5.0):
        diagnostics.append(
            f"intersection_tie_slope_local_window_rejected_too_far:{segment_ref or 'unknown'}:distance={mid_distance:.3f}"
        )
    if cap_distance > max(18.0, scale * 5.0):
        diagnostics.append(
            f"intersection_tie_slope_local_window_rejected_cap_too_far:{segment_ref or 'unknown'}:distance={cap_distance:.3f}"
        )
    if bbox_diag > max(30.0, scale * 8.0):
        diagnostics.append(
            f"intersection_tie_slope_local_window_rejected_too_large:{segment_ref or 'unknown'}:bbox={bbox_diag:.3f}"
        )
    return tuple(diagnostics)


def _intersection_tie_slope_gap_candidate_score(
    road_edge: tuple[tuple[float, float, float], ...],
    intersection_edge: tuple[tuple[float, float, float], ...],
) -> float:
    road_pair = _intersection_tie_slope_endpoint_pair(tuple(road_edge))
    intersection_pair = _intersection_tie_slope_endpoint_pair(tuple(intersection_edge))
    road_mid = _intersection_tie_slope_edge_midpoint(road_pair)
    intersection_mid = _intersection_tie_slope_edge_midpoint(intersection_pair)
    forward_cap = _xy_distance(road_pair[0], intersection_pair[0]) + _xy_distance(road_pair[1], intersection_pair[1])
    reverse_cap = _xy_distance(road_pair[0], intersection_pair[1]) + _xy_distance(road_pair[1], intersection_pair[0])
    return _xy_distance(road_mid, intersection_mid) + min(forward_cap, reverse_cap) * 0.5


def _intersection_tie_slope_edge_midpoint(edge: tuple[tuple[float, float, float], tuple[float, float, float]]) -> tuple[float, float, float]:
    return (
        (float(edge[0][0]) + float(edge[1][0])) / 2.0,
        (float(edge[0][1]) + float(edge[1][1])) / 2.0,
        (float(edge[0][2]) + float(edge[1][2])) / 2.0,
    )


def _intersection_tie_slope_bbox_diagonal(points: list[tuple[float, float, float]]) -> float:
    if not points:
        return 0.0
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5


def _intersection_tie_slope_unsafe_loop_diagnostics(
    loop_points: tuple[tuple[float, float, float], ...],
    *,
    inner_edge: tuple[tuple[float, float, float], ...],
    outer_edge: tuple[tuple[float, float, float], ...],
    start_cap_edge: tuple[tuple[float, float, float], ...],
    end_cap_edge: tuple[tuple[float, float, float], ...],
    loop_area_xy: float,
) -> tuple[str, ...]:
    diagnostics: list[str] = []
    points = [tuple(point) for point in tuple(loop_points or ())]
    if len(points) < 5:
        return ("intersection_tie_slope_open_loop",)
    if not _intersection_slope_face_points_close_xy(points[0], points[-1]):
        diagnostics.append("intersection_tie_slope_open_loop")
    polygon = list(points[:-1])
    if len(polygon) < 4:
        diagnostics.append("intersection_tie_slope_loop_too_few_unique_points")
    if len(polygon) >= 4 and _xy_xyz_polygon_self_crossing(polygon):
        diagnostics.append("intersection_tie_slope_loop_self_crossing")

    area = abs(float(loop_area_xy or 0.0))
    if area <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_loop_zero_area")

    inner_len = _xy_distance(inner_edge[0], inner_edge[1]) if len(tuple(inner_edge or ())) >= 2 else 0.0
    outer_len = _xy_distance(outer_edge[0], outer_edge[1]) if len(tuple(outer_edge or ())) >= 2 else 0.0
    start_cap_len = _xy_distance(start_cap_edge[0], start_cap_edge[1]) if len(tuple(start_cap_edge or ())) >= 2 else 0.0
    end_cap_len = _xy_distance(end_cap_edge[0], end_cap_edge[1]) if len(tuple(end_cap_edge or ())) >= 2 else 0.0
    edge_scale = max(inner_len, outer_len, 1.0)
    cap_scale = max(start_cap_len, end_cap_len, 1.0)
    bbox_diag = _intersection_tie_slope_bbox_diagonal(polygon)
    xs = [float(point[0]) for point in polygon]
    ys = [float(point[1]) for point in polygon]
    bbox_area = max(0.0, max(xs) - min(xs)) * max(0.0, max(ys) - min(ys)) if xs and ys else 0.0
    fill_ratio = area / bbox_area if bbox_area > 1.0e-9 else 0.0

    if bbox_diag > max(30.0, edge_scale * 8.0, cap_scale * 8.0):
        diagnostics.append(f"intersection_tie_slope_long_fan_rejected:bbox={bbox_diag:.3f}")
    if cap_scale > max(18.0, edge_scale * 6.0):
        diagnostics.append(f"intersection_tie_slope_long_fan_rejected:cap={cap_scale:.3f}")
    if bbox_area > 1.0e-9 and fill_ratio < 0.05 and bbox_diag > edge_scale * 4.0:
        diagnostics.append(f"intersection_tie_slope_long_fan_rejected:fill_ratio={fill_ratio:.3f}")

    return tuple(_unique_text_values(diagnostics))


def _intersection_tie_slope_transition_cell_window_diagnostics(
    loop_points: tuple[tuple[float, float, float], ...],
    *,
    inner_edge: tuple[tuple[float, float, float], ...],
    outer_edge: tuple[tuple[float, float, float], ...],
    start_cap_edge: tuple[tuple[float, float, float], ...],
    end_cap_edge: tuple[tuple[float, float, float], ...],
    transition_span_length: float,
    intersection_ref: str,
) -> tuple[str, ...]:
    """Validate a closed Tie Slope cell against its local transition window."""

    points = [tuple(point) for point in tuple(loop_points or ())]
    polygon = points[:-1] if len(points) >= 2 and _intersection_slope_face_points_close_xy(points[0], points[-1]) else points
    if len(polygon) < 4:
        return ("intersection_tie_slope_transition_cell_window_rejected:too_few_points",)

    inner_len = _xy_distance(inner_edge[0], inner_edge[1]) if len(tuple(inner_edge or ())) >= 2 else 0.0
    outer_len = _xy_distance(outer_edge[0], outer_edge[1]) if len(tuple(outer_edge or ())) >= 2 else 0.0
    start_cap_len = _xy_distance(start_cap_edge[0], start_cap_edge[1]) if len(tuple(start_cap_edge or ())) >= 2 else 0.0
    end_cap_len = _xy_distance(end_cap_edge[0], end_cap_edge[1]) if len(tuple(end_cap_edge or ())) >= 2 else 0.0
    bbox_diag = _intersection_tie_slope_bbox_diagonal(list(polygon))
    edge_scale = max(inner_len, outer_len, 1.0)
    cap_scale = max(start_cap_len, end_cap_len, 1.0)
    span_scale = max(float(transition_span_length or 0.0), 1.0)
    limit = max(30.0, edge_scale * 8.0, cap_scale * 8.0, span_scale * 4.0)
    ref_text = str(intersection_ref or "").strip().lower()
    diagnostics: list[str] = [
        (
            "intersection_tie_slope_transition_cell_window_candidate:"
            f"bbox={bbox_diag:.3f}; edge_scale={edge_scale:.3f}; cap_scale={cap_scale:.3f}; "
            f"transition_span={float(transition_span_length or 0.0):.3f}; source={intersection_ref or '-'}"
        )
    ]
    if bbox_diag > limit:
        diagnostics.append(
            "intersection_tie_slope_transition_cell_window_rejected:broad_panel:"
            f"bbox={bbox_diag:.3f}; limit={limit:.3f}"
        )
    if any(token in ref_text for token in ("central_junction", "pavement_center", "patch_interior", "interior")):
        diagnostics.append(
            "intersection_tie_slope_transition_cell_window_rejected:patch_interior_source:"
            f"{intersection_ref or 'unknown'}"
        )
    if not any("rejected" in item for item in diagnostics):
        diagnostics.append("intersection_tie_slope_transition_cell_window_accepted")
    return tuple(_unique_text_values(diagnostics))


def _intersection_tie_slope_closed_loop_edges(
    inner_points: tuple[tuple[float, float, float], ...],
    outer_points: tuple[tuple[float, float, float], ...],
) -> tuple[
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    tuple[tuple[float, float, float], ...],
    float,
    tuple[str, ...],
]:
    diagnostics: list[str] = []
    if len(inner_points) < 2:
        diagnostics.append("intersection_tie_slope_loop_inner_edge_missing")
        return (), (), (), (), (), 0.0, tuple(diagnostics)
    if len(outer_points) < 2:
        diagnostics.append("intersection_tie_slope_loop_outer_edge_missing")
        return (), (), (), (), (), 0.0, tuple(diagnostics)

    inner_start, inner_end = _intersection_tie_slope_endpoint_pair(inner_points)
    outer_start, outer_end = _intersection_tie_slope_endpoint_pair(outer_points)
    forward_cost = _xy_distance(inner_start, outer_start) + _xy_distance(inner_end, outer_end)
    reversed_cost = _xy_distance(inner_start, outer_end) + _xy_distance(inner_end, outer_start)
    if reversed_cost < forward_cost:
        outer_start, outer_end = outer_end, outer_start

    inner_edge = (inner_start, inner_end)
    outer_edge = (outer_start, outer_end)
    start_cap_edge = (inner_start, outer_start)
    end_cap_edge = (inner_end, outer_end)
    if _xy_distance(inner_start, inner_end) <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_loop_inner_edge_degenerate")
    if _xy_distance(outer_start, outer_end) <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_loop_outer_edge_degenerate")
    if _xy_distance(start_cap_edge[0], start_cap_edge[1]) <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_loop_start_cap_degenerate")
    if _xy_distance(end_cap_edge[0], end_cap_edge[1]) <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_loop_end_cap_degenerate")

    loop = [inner_start, inner_end, outer_end, outer_start, inner_start]
    simplified = tuple(_intersection_slope_face_simplified_closed_loop(loop))
    closed_xy = bool(simplified) and _intersection_slope_face_points_close_xy(simplified[0], simplified[-1])
    if not closed_xy:
        diagnostics.append("intersection_tie_slope_loop_not_closed")
    unique_xy = {
        (round(float(point[0]), 6), round(float(point[1]), 6))
        for point in simplified[:-1]
    }
    if len(unique_xy) < 4:
        diagnostics.append("intersection_tie_slope_loop_too_few_unique_points")
    area = abs(_xy_polygon_area([(float(point[0]), float(point[1])) for point in simplified[:-1]])) if len(simplified) >= 4 else 0.0
    if area <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_loop_zero_area")
    return (
        simplified,
        inner_edge,
        outer_edge,
        start_cap_edge,
        end_cap_edge,
        area,
        tuple(_unique_text_values(diagnostics)),
    )


def _intersection_tie_slope_gap_specs(
    applied_section_set,
    *,
    prerequisite: IntersectionPatchPrerequisiteResult,
    intersection_model=None,
) -> list[dict[str, object]]:
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "").strip()
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip() if source_row is not None else ""
    alignment_refs = [
        str(value or "").strip()
        for value in list(getattr(prerequisite, "alignment_refs", []) or [])
        if str(value or "").strip()
    ]
    if not primary_ref and alignment_refs:
        primary_ref = alignment_refs[0]
    secondary_refs = [
        str(value or "").strip()
        for value in list(getattr(source_row, "secondary_alignment_refs", []) or [])
        if str(value or "").strip()
    ] if source_row is not None else []
    if not secondary_refs:
        secondary_refs = [ref for ref in alignment_refs if ref and ref != primary_ref]

    specs: list[dict[str, object]] = []
    target_specs: list[tuple[str, str, str]] = []
    if primary_ref:
        target_specs.append((primary_ref, "primary", "entry"))
        target_specs.append((primary_ref, "primary", "exit"))
    intersection_kind = str(getattr(source_row, "intersection_kind", "") or getattr(prerequisite, "intersection_kind", "") or "")
    for secondary_ref in secondary_refs:
        target_specs.append((secondary_ref, "secondary", "entry"))
        if intersection_kind == "cross_intersection":
            target_specs.append((secondary_ref, "secondary", "exit"))

    for alignment_ref, road_role, gap_role in target_specs:
        for side in ("left", "right"):
            station_span = _intersection_tie_slope_transition_station_span(
                applied_section_set,
                intersection_model,
                intersection_id=intersection_id,
                alignment_ref=alignment_ref,
                road_role=road_role,
                gap_role=gap_role,
            )
            terminal_section = _intersection_tie_slope_terminal_section_for_gap(
                applied_section_set,
                alignment_ref=alignment_ref,
                intersection_id=intersection_id,
                target_station=float(station_span.get("transition_outer_sta", 0.0) or 0.0),
                gap_role=gap_role,
                side=side,
            )
            specs.append(
                {
                    "alignment_ref": alignment_ref,
                    "road_role": road_role,
                    "gap_role": gap_role,
                    "side": side,
                    "terminal_section": terminal_section,
                    "leg_ref": _intersection_tie_slope_leg_ref(
                        source_row,
                        alignment_ref,
                        road_role=road_role,
                    ),
                    "control_area_ref": _intersection_tie_slope_control_area_ref(
                        intersection_model,
                        intersection_id,
                        alignment_ref,
                        source_row=source_row,
                    ),
                    "station_span": station_span,
                }
            )
    return specs


def _intersection_tie_slope_transition_station_span(
    applied_section_set,
    intersection_model,
    *,
    intersection_id: str,
    alignment_ref: str,
    road_role: str,
    gap_role: str,
) -> dict[str, object]:
    """Return the separated Region/control-area and Applied Section intersection STA pair."""

    alignment_id = str(alignment_ref or "").strip()
    role = str(road_role or "").strip().lower()
    gap = str(gap_role or "").strip().lower()
    diagnostics: list[str] = []
    region_range = _intersection_tie_slope_region_station_range(
        intersection_model,
        intersection_id=intersection_id,
        alignment_ref=alignment_id,
    )
    if region_range is None:
        region_range = _intersection_tie_slope_leg_station_range(
            intersection_model,
            intersection_id=intersection_id,
            alignment_ref=alignment_id,
        )
    if region_range is None:
        diagnostics.append("intersection_tie_slope_region_boundary_missing")
        region_range = _intersection_tie_slope_alignment_section_station_range(
            applied_section_set,
            alignment_ref=alignment_id,
        )
    intersection_range = _intersection_tie_slope_applied_intersection_station_range(
        applied_section_set,
        intersection_id=intersection_id,
        alignment_ref=alignment_id,
    )
    if intersection_range is None:
        diagnostics.append("intersection_tie_slope_intersection_station_boundary_missing")
        target = _intersection_tie_slope_target_station(intersection_model, intersection_id, alignment_id)
        if target is not None:
            intersection_range = (float(target), float(target))
    region_start, region_end = _ordered_station_range(region_range)
    intersection_start, intersection_end = _ordered_station_range(intersection_range)
    transition_span_role = f"{role or 'road'}:{gap or 'gap'}"
    if region_range is None or intersection_range is None:
        transition_outer_sta = 0.0
        transition_inner_sta = 0.0
        transition_window_start_sta = 0.0
        transition_window_end_sta = 0.0
        transition_window_kind = "missing"
    elif gap == "exit":
        transition_outer_sta = float(region_end)
        transition_inner_sta = float(intersection_end)
        transition_window_start_sta = float(intersection_end)
        transition_window_end_sta = float(region_end)
        transition_window_kind = "primary_intersection_end_to_region_end" if role == "primary" else "secondary_intersection_end_to_region_end"
    else:
        transition_outer_sta = float(region_start)
        transition_inner_sta = float(intersection_start)
        transition_window_start_sta = float(region_start)
        transition_window_end_sta = float(intersection_start)
        transition_window_kind = "primary_region_start_to_intersection_start" if role == "primary" else "secondary_region_start_to_intersection_start"
    transition_span_length = abs(float(transition_outer_sta) - float(transition_inner_sta))
    if transition_span_length <= 1.0e-6:
        diagnostics.append("intersection_tie_slope_transition_span_too_short")
    else:
        diagnostics.append("intersection_tie_slope_transition_span_diagnostic_ready")
        diagnostics.append("intersection_tie_slope_transition_outer_edge_selector_ready")
        diagnostics.append("intersection_tie_slope_transition_inner_edge_selector_window_ready")
        if transition_window_kind == "primary_region_start_to_intersection_start":
            diagnostics.append("intersection_tie_slope_primary_entry_window_ready")
        elif transition_window_kind == "primary_intersection_end_to_region_end":
            diagnostics.append("intersection_tie_slope_primary_exit_window_ready")
        elif transition_window_kind == "secondary_region_start_to_intersection_start":
            diagnostics.append("intersection_tie_slope_secondary_entry_window_ready")
        elif transition_window_kind == "secondary_intersection_end_to_region_end":
            diagnostics.append("intersection_tie_slope_secondary_exit_window_ready")
    return {
        "region_start_sta": float(region_start),
        "region_end_sta": float(region_end),
        "intersection_start_sta": float(intersection_start),
        "intersection_end_sta": float(intersection_end),
        "transition_outer_sta": float(transition_outer_sta),
        "transition_inner_sta": float(transition_inner_sta),
        "transition_window_start_sta": float(transition_window_start_sta),
        "transition_window_end_sta": float(transition_window_end_sta),
        "transition_span_length": float(transition_span_length),
        "transition_span_role": transition_span_role,
        "transition_window_kind": transition_window_kind,
        "diagnostics": tuple(_unique_text_values(diagnostics)),
    }


def _ordered_station_range(station_range) -> tuple[float, float]:
    if station_range is None:
        return (0.0, 0.0)
    try:
        start, end = tuple(station_range)[:2]
    except Exception:
        return (0.0, 0.0)
    start_value = float(start or 0.0)
    end_value = float(end or 0.0)
    return (min(start_value, end_value), max(start_value, end_value))


def _intersection_tie_slope_region_station_range(
    intersection_model,
    *,
    intersection_id: str,
    alignment_ref: str,
) -> tuple[float, float] | None:
    ranges: list[tuple[float, float]] = []
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if str(getattr(area, "intersection_id", "") or "").strip() != str(intersection_id or "").strip():
            continue
        if str(alignment_ref or "").strip() and str(getattr(area, "alignment_ref", "") or "").strip() != str(alignment_ref or "").strip():
            continue
        for station_range in list(getattr(area, "station_ranges", []) or []):
            start, end = _ordered_station_range(station_range)
            if abs(end - start) > 1.0e-9:
                ranges.append((start, end))
    if not ranges:
        return None
    return (min(start for start, _end in ranges), max(end for _start, end in ranges))


def _intersection_tie_slope_leg_station_range(
    intersection_model,
    *,
    intersection_id: str,
    alignment_ref: str,
) -> tuple[float, float] | None:
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    for leg in list(getattr(source_row, "leg_rows", []) or []):
        if str(alignment_ref or "").strip() and str(getattr(leg, "alignment_ref", "") or "").strip() != str(alignment_ref or "").strip():
            continue
        start = float(getattr(leg, "approach_station_start", 0.0) or 0.0)
        end = float(getattr(leg, "approach_station_end", 0.0) or 0.0)
        if abs(end - start) > 1.0e-9:
            return _ordered_station_range((start, end))
    return None


def _intersection_tie_slope_alignment_section_station_range(
    applied_section_set,
    *,
    alignment_ref: str,
) -> tuple[float, float] | None:
    stations = [
        _section_station(section)
        for section in _station_ordered_applied_sections(applied_section_set)
        if str(getattr(section, "alignment_id", "") or "").strip() == str(alignment_ref or "").strip()
    ]
    if not stations:
        return None
    return (min(stations), max(stations))


def _intersection_tie_slope_applied_intersection_station_range(
    applied_section_set,
    *,
    intersection_id: str,
    alignment_ref: str,
) -> tuple[float, float] | None:
    stations = [
        _section_station(section)
        for section in _station_ordered_applied_sections(applied_section_set)
        if str(getattr(section, "alignment_id", "") or "").strip() == str(alignment_ref or "").strip()
        and str(getattr(section, "active_intersection_id", "") or "").strip() == str(intersection_id or "").strip()
    ]
    if not stations:
        return None
    return (min(stations), max(stations))


def _intersection_tie_slope_terminal_section_for_gap(
    applied_section_set,
    *,
    alignment_ref: str,
    intersection_id: str,
    target_station: float | None,
    gap_role: str,
    side: str,
):
    alignment_id = str(alignment_ref or "").strip()
    if applied_section_set is None or not alignment_id:
        return None
    sections = [
        section
        for section in _station_ordered_applied_sections(applied_section_set)
        if str(getattr(section, "alignment_id", "") or "").strip() == alignment_id
        and _intersection_tie_slope_terminal_road_edge(section, side=side)
    ]
    if not sections:
        return None
    if target_station is None:
        outside_sections = [
            section
            for section in sections
            if str(getattr(section, "active_intersection_id", "") or "").strip() != str(intersection_id or "").strip()
        ]
        return outside_sections[0] if outside_sections else sections[0]

    before_or_at = [
        section for section in sections
        if float(getattr(section, "station", 0.0) or 0.0) <= float(target_station) + 1.0e-9
    ]
    after_or_at = [
        section for section in sections
        if float(getattr(section, "station", 0.0) or 0.0) >= float(target_station) - 1.0e-9
    ]
    if str(gap_role or "").strip().lower() == "exit":
        preferred = after_or_at
        return min(preferred or sections, key=lambda section: abs(_section_station(section) - float(target_station)))
    preferred = before_or_at
    return min(preferred or sections, key=lambda section: abs(_section_station(section) - float(target_station)))


def _intersection_tie_slope_terminal_road_edge(section, *, side: str) -> tuple[tuple[float, float, float], ...]:
    if section is None:
        return ()
    points = _slope_face_applied_section_breakline_points(section, side_label=str(side or "").strip().lower())
    edge = tuple(_xyz_tuple(point) for point in points)
    if len(edge) < 2:
        return ()
    first, last = _intersection_tie_slope_endpoint_pair(edge)
    if _xy_distance(first, last) <= 1.0e-6:
        section_edge = _applied_section_slope_face_edge_points(
            section,
            side_label=str(side or "").strip().lower(),
            fallback_band_width=6.0,
            fallback_band_slope=0.33,
        )
        if section_edge is not None:
            inner, outer = section_edge
            fallback_edge = (_xyz_tuple(inner), _xyz_tuple(outer))
            if _xy_distance(fallback_edge[0], fallback_edge[1]) > 1.0e-6:
                return fallback_edge
        return ()
    return edge


def _intersection_tie_slope_target_station(intersection_model, intersection_id: str, alignment_ref: str) -> float | None:
    source_row = _intersection_row_by_id(intersection_model, intersection_id) if intersection_model is not None else None
    alignment_id = str(alignment_ref or "").strip()
    if source_row is None or not alignment_id:
        return None
    primary_ref = str(getattr(source_row, "primary_alignment_ref", "") or "").strip()
    if alignment_id == primary_ref:
        return float(getattr(source_row, "primary_station", 0.0) or 0.0)
    secondary_stations = dict(getattr(source_row, "secondary_station_refs", {}) or {})
    if alignment_id in secondary_stations:
        return float(secondary_stations.get(alignment_id) or 0.0)
    return None


def _intersection_tie_slope_leg_ref(source_row, alignment_ref: str, *, road_role: str) -> str:
    if source_row is None:
        return ""
    alignment_id = str(alignment_ref or "").strip()
    target_role = str(road_role or "").strip().lower()
    fallback = ""
    for leg in list(getattr(source_row, "leg_rows", []) or []):
        if str(getattr(leg, "alignment_ref", "") or "").strip() != alignment_id:
            continue
        leg_id = str(getattr(leg, "leg_id", "") or "").strip()
        leg_role = str(getattr(leg, "leg_role", "") or "").strip().lower()
        fallback = fallback or leg_id
        if target_role == "primary" and leg_role.startswith("primary"):
            return leg_id
        if target_role == "secondary" and not leg_role.startswith("primary"):
            return leg_id
    return fallback


def _intersection_tie_slope_control_area_ref(intersection_model, intersection_id: str, alignment_ref: str, *, source_row=None) -> str:
    alignment_id = str(alignment_ref or "").strip()
    areas = list(getattr(intersection_model, "control_area_rows", []) or []) if intersection_model is not None else []
    for area in areas:
        if str(getattr(area, "intersection_id", "") or "").strip() != str(intersection_id or "").strip():
            continue
        if alignment_id and str(getattr(area, "alignment_ref", "") or "").strip() != alignment_id:
            continue
        area_id = str(getattr(area, "control_area_id", "") or "").strip()
        if area_id:
            return area_id
    legs = list(getattr(source_row, "leg_rows", []) or []) if source_row is not None else []
    for leg in legs:
        if alignment_id and str(getattr(leg, "alignment_ref", "") or "").strip() == alignment_id:
            return str(getattr(leg, "region_ref", "") or "").strip()
    return ""


def _intersection_tie_slope_endpoint_pair(
    points: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    return (_xyz_tuple(points[0]), _xyz_tuple(points[-1]))


def _xy_xyz_polygon_self_crossing(points: list[tuple[float, float, float]]) -> bool:
    return xy_polygon_self_intersects(points)


def _xyz_tuple(point) -> tuple[float, float, float]:
    return xyz_point(point)


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"


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


def _intersection_slope_face_points_close_xy(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    tolerance: float = 1.0e-6,
) -> bool:
    return math.hypot(float(first[0]) - float(second[0]), float(first[1]) - float(second[1])) <= tolerance


def _applied_section_slope_face_edge_points(
    section,
    *,
    side_label: str,
    fallback_band_width: float,
    fallback_band_slope: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    inner_offset, inner_z = _applied_section_terminal_edge(section, side_label=side_label, fallback_half_width=6.0)
    inner = _applied_section_xyz_at_offset(frame, inner_offset, inner_z)
    explicit_outer = _applied_section_explicit_slope_outer_point(section, side_label=side_label, inner_offset=inner_offset)
    if explicit_outer is not None:
        return inner, explicit_outer
    width_attr = "daylight_left_width" if side_label == "left" else "daylight_right_width"
    slope_attr = "daylight_left_slope" if side_label == "left" else "daylight_right_slope"
    width = max(float(getattr(section, width_attr, 0.0) or 0.0), 0.0)
    if width <= 1.0e-9:
        return None
    slope = abs(float(getattr(section, slope_attr, 0.0) or 0.0))
    if slope <= 1.0e-9:
        slope = abs(float(fallback_band_slope or 0.0))
    normal_x, normal_y = _applied_section_outward_normal(frame, side_label=side_label)
    return inner, (
        float(inner[0]) + normal_x * width,
        float(inner[1]) + normal_y * width,
        float(inner[2]) - abs(float(slope)) * width,
    )


def _applied_section_terminal_edge(section, *, side_label: str, fallback_half_width: float) -> tuple[float, float]:
    frame = getattr(section, "frame", None)
    frame_z = float(getattr(frame, "z", 0.0) or 0.0)
    left_width = float(getattr(section, "surface_left_width", 0.0) or 0.0)
    right_width = float(getattr(section, "surface_right_width", 0.0) or 0.0)
    if left_width <= 0.0 and right_width <= 0.0:
        left_width = right_width = float(fallback_half_width)
    elif left_width <= 0.0:
        left_width = right_width
    elif right_width <= 0.0:
        right_width = left_width
    edge = (max(left_width, 0.1), frame_z) if side_label == "left" else (-max(right_width, 0.1), frame_z)
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"fg_surface", "ditch_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        z = float(getattr(point, "z", frame_z) or frame_z)
        if side_label == "left":
            if offset > edge[0] or (abs(offset - edge[0]) <= 1.0e-9 and z > edge[1]):
                edge = (offset, z)
        elif offset < edge[0] or (abs(offset - edge[0]) <= 1.0e-9 and z > edge[1]):
            edge = (offset, z)
    return edge


def _applied_section_explicit_slope_outer_point(section, *, side_label: str, inner_offset: float) -> tuple[float, float, float] | None:
    direction = 1.0 if side_label == "left" else -1.0
    candidates: list[object] = []
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role not in {"daylight_marker", "side_slope_surface", "bench_surface"}:
            continue
        offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
        if (offset - float(inner_offset)) * direction < -1.0e-9:
            continue
        candidates.append(point)
    if not candidates:
        return None
    chosen = max(
        candidates,
        key=lambda point: abs(float(getattr(point, "lateral_offset", 0.0) or 0.0) - float(inner_offset)),
    )
    return (
        float(getattr(chosen, "x", 0.0) or 0.0),
        float(getattr(chosen, "y", 0.0) or 0.0),
        float(getattr(chosen, "z", 0.0) or 0.0),
    )


def _applied_section_xyz_at_offset(frame, offset: float, z: float) -> tuple[float, float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    return (
        float(getattr(frame, "x", 0.0) or 0.0) + normal_x * float(offset),
        float(getattr(frame, "y", 0.0) or 0.0) + normal_y * float(offset),
        float(z),
    )


def _applied_section_outward_normal(frame, *, side_label: str) -> tuple[float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    if side_label == "right":
        return -normal_x, -normal_y
    return normal_x, normal_y


def _xy_polygon_area(points: list[tuple[float, float]]) -> float:
    return xy_polygon_signed_area(points)


def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return xy_distance(a, b)


def _slope_face_applied_section_breakline_points(section, *, side_label: str) -> list[tuple[float, float, float]]:
    roles = {"side_slope_surface", "bench_surface", "daylight_marker"}
    rows = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") in roles and _point_matches_side(point, side_label=side_label)
    ]
    return _breakline_points_from_rows(rows, side_label=side_label, role_attr="point_role")


def _point_matches_side(point, *, side_label: str) -> bool:
    side = str(getattr(point, "side", "") or "").strip().lower()
    if side in {"left", "right"}:
        return side == side_label
    offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
    return offset >= -1.0e-9 if side_label == "left" else offset <= 1.0e-9


def _breakline_points_from_rows(rows: list[object], *, side_label: str, role_attr: str) -> list[tuple[float, float, float]]:
    direction = 1.0 if side_label == "left" else -1.0
    ordered = sorted(
        list(rows or []),
        key=lambda point: (
            float(getattr(point, "lateral_offset", 0.0) or 0.0) * direction,
            _slope_face_role_order(str(getattr(point, role_attr, "") or "")),
        ),
    )
    return [
        (
            float(getattr(point, "x", 0.0) or 0.0),
            float(getattr(point, "y", 0.0) or 0.0),
            float(getattr(point, "z", 0.0) or 0.0),
        )
        for point in ordered
    ]


def _slope_face_role_order(role: str) -> int:
    text = str(role or "").strip().lower()
    if "hinge" in text or text == "side_slope_surface":
        return 0
    if "bench" in text:
        return 1
    if "daylight" in text:
        return 2
    return 3


# __SERVICE_BODY_END__


__all__ = [
    "IntersectionTieSlopeEvaluationRequest",
    "IntersectionTieSlopeEvaluationService",
]
