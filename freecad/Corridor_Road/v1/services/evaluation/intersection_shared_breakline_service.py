"""Evaluate and assemble typed Intersection shared-breakline contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ...models.result.intersection_shared_breakline_contribution import (
    IntersectionSharedBreaklineContributionResult,
)
from ...models.result.shared_breakline import (
    SharedBreaklinePointRow,
    SharedBreaklineResult,
    SharedBreaklineRow,
)


EXPECTED_CONSUMERS = {
    "patch_to_design_surface": (
        "intersection_surface",
        "design_surface",
        "intersection_slope_face_surface",
    ),
    "curb_return_to_intersection_slope_face": (
        "intersection_surface",
        "intersection_slope_face_surface",
    ),
    "roundabout_island_to_circulatory": (
        "intersection_surface",
        "roundabout_central_island",
        "roundabout_circulatory_surface",
    ),
    "roundabout_circulatory_to_apron": (
        "intersection_surface",
        "roundabout_circulatory_surface",
        "roundabout_apron_surface",
    ),
    "roundabout_apron_to_slope_face": (
        "roundabout_apron_surface",
        "roundabout_slope_face_surface",
    ),
    "roundabout_entry_exit_connector_boundary": (
        "roundabout_entry_exit_connector",
        "design_surface",
        "roundabout_circulatory_surface",
    ),
}


@dataclass(frozen=True)
class IntersectionSharedBreaklineContributionRequest:
    result_id: str
    intersection_id: str
    boundary_loop_result: object | None
    patch_boundary_result: object | None
    boundary_segment_result: object | None
    intersection_model: object | None = None
    boundary_loop_ready: bool = False
    existing_breakline_ids: tuple[str, ...] = ()
    contributor_names: tuple[str, ...] = ("boundary_loops", "patch_to_design")
    tie_slope_result: object | None = None
    tie_slope_window_rows: tuple[object, ...] = ()
    drainage_hint_result: object | None = None
    existing_breakline_rows: tuple[object, ...] = ()
    existing_point_rows: tuple[object, ...] = ()
    applied_section_set: object | None = None
    intersection_kind: str = ""
    upper_panel_candidate_rows: tuple[object, ...] = ()
    upper_panel_supported: bool = True
    slope_face_boundary_result: object | None = None
    visible_slope_boundary_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntersectionSharedBreaklineAssemblyRequest:
    project_id: str
    result_id: str
    intersection_id: str
    breakline_rows: tuple[object, ...]
    point_rows: tuple[object, ...]
    diagnostic_rows: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntersectionSharedBreaklineEvaluationRequest:
    project_id: str
    result_id: str
    intersection_id: str
    intersection_kind: str
    applied_section_set: object
    intersection_model: object | None
    patch_boundary_result: object | None
    boundary_segment_result: object | None
    boundary_loop_result: object | None
    slope_face_boundary_result: object | None
    tie_slope_result: object | None
    tie_slope_window_rows: tuple[object, ...] = ()
    drainage_hint_result: object | None = None
    visible_slope_boundary_ids: tuple[str, ...] = ()
    diagnostic_rows: tuple[str, ...] = ()
    upper_panel_supported: bool = False
    upper_panel_candidate_evaluator: object | None = None


class IntersectionSharedBreaklineService:
    """Own core contributors and final typed result assembly."""

    def evaluate(
        self, request: IntersectionSharedBreaklineEvaluationRequest
    ) -> SharedBreaklineResult:
        breaklines = []
        points = []
        diagnostics = list(request.diagnostic_rows)

        def contribute(name, **overrides):
            values = dict(
                result_id=request.result_id,
                intersection_id=request.intersection_id,
                boundary_loop_result=request.boundary_loop_result,
                patch_boundary_result=request.patch_boundary_result,
                boundary_segment_result=request.boundary_segment_result,
                intersection_model=request.intersection_model,
                contributor_names=(name,),
                tie_slope_result=request.tie_slope_result,
                tie_slope_window_rows=request.tie_slope_window_rows,
                drainage_hint_result=request.drainage_hint_result,
                existing_breakline_ids=tuple(
                    str(getattr(row, "breakline_id", "") or "")
                    for row in breaklines
                ),
                existing_breakline_rows=tuple(breaklines),
                existing_point_rows=tuple(points),
                applied_section_set=request.applied_section_set,
                intersection_kind=request.intersection_kind,
                slope_face_boundary_result=request.slope_face_boundary_result,
                visible_slope_boundary_ids=request.visible_slope_boundary_ids,
            )
            values.update(overrides)
            result = self.evaluate_core(
                IntersectionSharedBreaklineContributionRequest(**values)
            )
            breaklines.extend(result.breakline_rows)
            points.extend(result.point_rows)
            diagnostics.extend(result.diagnostic_rows)

        for name in (
            "boundary_loops",
            "roundabout_clip",
            "curb_return_bridge",
            "tie_slope",
            "patch_to_design",
            "slope_face_contacts",
            "main_side_slope_face",
            "control_area",
            "drainage_handoff",
        ):
            contribute(name)
        candidates = ()
        if request.upper_panel_supported and callable(
            request.upper_panel_candidate_evaluator
        ):
            seed = SharedBreaklineResult(
                schema_version=1,
                project_id=request.project_id,
                breakline_result_id=request.result_id,
                domain_kind="intersection",
                domain_ref=request.intersection_id,
                status="candidate",
                breakline_count=len(breaklines),
                breakline_rows=list(breaklines),
                point_rows=list(points),
            )
            candidates = tuple(
                request.upper_panel_candidate_evaluator(
                    seed,
                    intersection_id=request.intersection_id,
                    intersection_kind=request.intersection_kind,
                )
                or ()
            )
        contribute(
            "upper_panel",
            upper_panel_candidate_rows=candidates,
            upper_panel_supported=request.upper_panel_supported,
        )
        breaklines = self.enrich_profile_refs(
            breaklines,
            intersection_model=request.intersection_model,
            intersection_id=request.intersection_id,
        )
        return self.assemble(
            IntersectionSharedBreaklineAssemblyRequest(
                project_id=request.project_id,
                result_id=request.result_id,
                intersection_id=request.intersection_id,
                breakline_rows=tuple(breaklines),
                point_rows=tuple(points),
                diagnostic_rows=tuple(diagnostics),
            )
        )

    def evaluate_core(
        self,
        request: IntersectionSharedBreaklineContributionRequest,
    ) -> IntersectionSharedBreaklineContributionResult:
        breaklines = []
        points = []
        diagnostics = []
        completed = []
        if "boundary_loops" in request.contributor_names:
            self._append_boundary_loops(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("boundary_loops")
        if "patch_to_design" in request.contributor_names:
            self._append_patch_to_design(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("patch_to_design")
        if "roundabout_clip" in request.contributor_names:
            self._append_roundabout_clip(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("roundabout_clip")
        if "curb_return_bridge" in request.contributor_names:
            self._append_curb_return_bridge(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("curb_return_bridge")
        if "tie_slope" in request.contributor_names:
            self._append_tie_slope(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("tie_slope")
        if "main_side_slope_face" in request.contributor_names:
            self._append_main_side_slope_face(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("main_side_slope_face")
        if "drainage_handoff" in request.contributor_names:
            self._append_drainage_handoff(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("drainage_handoff")
        if "control_area" in request.contributor_names:
            self._append_control_area(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("control_area")
        if "upper_panel" in request.contributor_names:
            self._append_upper_panel(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("upper_panel")
        if "slope_face_contacts" in request.contributor_names:
            _append_slope_face_contacts(
                request,
                breakline_rows=breaklines,
                point_rows=points,
                diagnostics=diagnostics,
            )
            completed.append("slope_face_contacts")
        return IntersectionSharedBreaklineContributionResult(
            status="ready" if breaklines else "missing",
            intersection_id=request.intersection_id,
            breakline_rows=tuple(breaklines),
            point_rows=tuple(points),
            diagnostic_rows=tuple(diagnostics),
            completed_contributors=tuple(completed),
        )

    def assemble(
        self,
        request: IntersectionSharedBreaklineAssemblyRequest,
    ) -> SharedBreaklineResult:
        breaklines = list(request.breakline_rows)
        ready_count = sum(
            str(getattr(row, "source_status", "") or "")
            in {"ready", "accepted"}
            for row in breaklines
        )
        warning_count = sum(
            str(getattr(row, "source_status", "") or "")
            in {"warning", "candidate", "defaulted"}
            for row in breaklines
        )
        error_count = sum(
            str(getattr(row, "source_status", "") or "") == "error"
            for row in breaklines
        )
        status = (
            "ready"
            if breaklines and error_count == 0
            else ("missing" if not breaklines else "warning")
        )
        return SharedBreaklineResult(
            schema_version=1,
            project_id=request.project_id,
            breakline_result_id=request.result_id,
            domain_kind="intersection",
            domain_ref=request.intersection_id,
            status=status,
            breakline_count=len(breaklines),
            ready_count=ready_count,
            warning_count=warning_count,
            error_count=error_count,
            diagnostic_rows=list(request.diagnostic_rows),
            breakline_rows=breaklines,
            point_rows=list(request.point_rows),
        )

    def enrich_profile_refs(self, rows, *, intersection_model, intersection_id):
        refs = _intersection_profile_refs(intersection_model, intersection_id)
        if not refs:
            return list(rows)
        return [
            replace(
                row,
                source_contract_refs=tuple(
                    _unique((*tuple(row.source_contract_refs or ()), *refs))
                ),
            )
            for row in rows
        ]

    def append_local_clip_caps(self, **kwargs) -> None:
        _append_local_clip_caps(**kwargs)

    def _append_boundary_loops(
        self,
        request,
        *,
        breakline_rows,
        point_rows,
        diagnostics,
    ) -> None:
        result = request.boundary_loop_result
        if result is None:
            diagnostics.append("intersection_boundary_loop_result_missing")
            return
        loop_rows = [
            row
            for row in list(getattr(result, "loop_rows", []) or [])
            if str(getattr(row, "loop_role", "") or "")
            in {
                "outer_intersection_boundary",
                "roundabout_central_island_boundary",
                "roundabout_circulatory_outer_boundary",
                "roundabout_outer_ownership_boundary",
                "roundabout_entry_exit_connector_boundary",
            }
            and str(getattr(row, "status", "") or "") == "ready"
            and bool(getattr(row, "closed", False))
        ]
        if not loop_rows:
            diagnostics.append("intersection_boundary_loop_closed_outer_missing")
            return
        accepted_refs = {
            str(ref or "")
            for loop in loop_rows
            for ref in tuple(getattr(loop, "segment_refs", ()) or ())
            if str(ref or "")
        }
        existing_ids = set(request.existing_breakline_ids)
        emitted = set()
        for index, segment in enumerate(
            list(getattr(result, "segment_rows", []) or []),
            start=1,
        ):
            segment_id = str(getattr(segment, "segment_id", "") or "")
            if accepted_refs and segment_id not in accepted_refs:
                continue
            start = tuple(getattr(segment, "from_xyz", ()) or ())
            end = tuple(getattr(segment, "to_xyz", ()) or ())
            if len(start) < 3 or len(end) < 3:
                diagnostics.append(
                    "intersection_boundary_loop_segment_points_missing:"
                    f"{segment_id or index}"
                )
                continue
            start_xyz, end_xyz = _xyz(start), _xyz(end)
            if _distance(start_xyz, end_xyz) <= 1.0e-9:
                diagnostics.append(
                    "intersection_boundary_loop_segment_degenerate:"
                    f"{segment_id or index}"
                )
                continue
            role = _shared_role_for_segment(segment)
            edge_key = (role, tuple(sorted((_node_key(start_xyz), _node_key(end_xyz)))))
            if edge_key in emitted:
                continue
            emitted.add(edge_key)
            base_ref = str(getattr(segment, "shared_breakline_ref", "") or "")
            breakline_id = base_ref or (
                f"{request.result_id}:boundary-loop:"
                f"{role.replace('_', '-')}:{index}"
            )
            if breakline_id in existing_ids:
                breakline_id = f"{breakline_id}:loop"
            existing_ids.add(breakline_id)
            refs = _append_two_points(
                breakline_id,
                start_xyz,
                end_xyz,
                segment,
                point_rows,
            )
            consumers = _expected_consumers(segment, role)
            source_refs = _unique(
                (
                    str(getattr(result, "boundary_loop_result_id", "") or ""),
                    str(getattr(segment, "loop_ref", "") or ""),
                    segment_id,
                    *tuple(getattr(segment, "source_refs", ()) or ()),
                )
            )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="intersection",
                    domain_ref=str(
                        getattr(segment, "intersection_id", "")
                        or request.intersection_id
                    ),
                    breakline_role=role,
                    source_contract_refs=tuple(source_refs),
                    consumer_refs=consumers,
                    from_output_role=(
                        consumers[0] if consumers else "intersection_boundary_loop"
                    ),
                    to_output_role=(
                        consumers[1]
                        if len(consumers) > 1
                        else "intersection_boundary_loop"
                    ),
                    point_refs=tuple(refs),
                    material_role="intersection_boundary",
                    source_status=str(
                        getattr(segment, "source_status", "") or "accepted"
                    ),
                    diagnostic_rows=tuple(
                        str(value or "")
                        for value in tuple(getattr(segment, "diagnostics", ()) or ())
                        if str(value or "")
                    ),
                    handoff_target="intersection_shared_boundary_graph",
                    notes=(
                        "Authoritative intersection boundary-loop segment shared "
                        "by adjacent surface consumers."
                    ),
                )
            )
        if not breakline_rows:
            diagnostics.append("intersection_boundary_loop_shared_breaklines_empty")

    def _append_patch_to_design(
        self,
        request,
        *,
        breakline_rows,
        point_rows,
        diagnostics,
    ) -> None:
        patch = request.patch_boundary_result
        boundary = request.boundary_segment_result
        if patch is None or boundary is None:
            return
        tie_rows = [
            row
            for row in list(getattr(boundary, "segment_rows", []) or [])
            if str(getattr(row, "segment_kind", "") or "") == "tie_in"
        ]
        source_row = _intersection_row_by_id(
            request.intersection_model,
            request.intersection_id,
        )
        primary_ref = str(
            getattr(source_row, "primary_alignment_ref", "") or ""
        )
        appended = 0
        for index, row in enumerate(tie_rows, start=1):
            start = _xyz(getattr(row, "start_xyz", (0.0, 0.0, 0.0)))
            end = _xyz(getattr(row, "end_xyz", (0.0, 0.0, 0.0)))
            if _distance(start, end) <= 1.0e-9:
                diagnostics.append(
                    "patch_to_design_contact_points_missing:"
                    f"{getattr(row, 'boundary_segment_id', '') or index}"
                )
                continue
            alignment_ref = str(getattr(row, "alignment_ref", "") or "")
            contact_role = (
                "pavement_tie_in"
                if primary_ref and alignment_ref == primary_ref
                else "stem_tie_in"
            )
            role = f"patch_to_design_{contact_role}"
            breakline_id = (
                f"{request.result_id}:{role.replace('_', '-')}:{index}"
            )
            refs = []
            for point_index, point in enumerate((start, end)):
                point_id = f"{breakline_id}:p{point_index + 1}"
                refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=breakline_id,
                        sequence=point_index,
                        x=point[0],
                        y=point[1],
                        z=point[2],
                        source_point_ref=str(
                            getattr(row, "boundary_segment_id", "") or ""
                        ),
                        notes=(
                            f"shared patch-to-design {contact_role} contact from "
                            "IntersectionBoundarySegmentResult"
                        ),
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="intersection",
                    domain_ref=request.intersection_id,
                    breakline_role=role,
                    source_contract_refs=(
                        str(getattr(patch, "patch_boundary_result_id", "") or ""),
                        str(
                            getattr(boundary, "boundary_segment_result_id", "")
                            or ""
                        ),
                        str(getattr(row, "boundary_segment_id", "") or ""),
                    ),
                    consumer_refs=("intersection_surface", "design_surface"),
                    from_output_role="intersection_surface",
                    to_output_role="design_surface",
                    point_refs=tuple(refs),
                    alignment_ref=alignment_ref,
                    side=str(getattr(row, "side", "") or ""),
                    material_role="pavement",
                    source_status=str(
                        getattr(row, "status", "")
                        or getattr(patch, "status", "")
                        or "candidate"
                    ),
                    diagnostic_rows=tuple(
                        str(value)
                        for value in list(getattr(patch, "diagnostic_rows", []) or [])
                    ),
                    handoff_target="intersection_patch_to_design",
                    notes=(
                        "Per-contact shared boundary between Intersection Surface "
                        f"and Design Surface; contact_role={contact_role}; "
                        f"source_segment_role={getattr(row, 'segment_role', '')}"
                    ),
                )
            )
            appended += 1
        if appended or patch is None:
            return
        if request.boundary_loop_ready:
            diagnostics.append(
                "patch_to_design_broad_fallback_suppressed:boundary_loop_ready"
            )
            return
        patch_points = [
            row
            for row in list(getattr(patch, "point_rows", []) or [])
            if str(getattr(row, "ring_role", "") or "outer") == "outer"
        ]
        if len(patch_points) < 2:
            diagnostics.append("patch_to_design_breakline_points_missing")
            return
        breakline_id = f"{request.result_id}:patch-to-design"
        refs = []
        for index, point in enumerate(patch_points):
            point_id = f"{breakline_id}:p{index + 1}"
            refs.append(point_id)
            point_rows.append(
                SharedBreaklinePointRow(
                    point_id=point_id,
                    breakline_ref=breakline_id,
                    sequence=index,
                    x=float(getattr(point, "x", 0.0) or 0.0),
                    y=float(getattr(point, "y", 0.0) or 0.0),
                    z=float(getattr(point, "z", 0.0) or 0.0),
                    source_point_ref=str(
                        getattr(point, "boundary_point_id", "") or ""
                    ),
                    notes=(
                        "shared fallback patch-to-design breakline from "
                        "intersection patch boundary"
                    ),
                )
            )
        breakline_rows.append(
            SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="intersection",
                domain_ref=request.intersection_id,
                breakline_role="patch_to_design",
                source_contract_refs=(
                    str(getattr(patch, "patch_boundary_result_id", "") or ""),
                ),
                consumer_refs=("intersection_surface", "design_surface"),
                from_output_role="intersection_surface",
                to_output_role="design_surface",
                point_refs=tuple(refs),
                source_status=str(getattr(patch, "status", "") or "candidate"),
                diagnostic_rows=tuple(
                    str(value)
                    for value in list(getattr(patch, "diagnostic_rows", []) or [])
                ),
                notes=(
                    "Fallback broad shared boundary between Intersection Surface "
                    "and Design Surface."
                ),
            )
        )

    def _append_roundabout_clip(
        self,
        request,
        *,
        breakline_rows,
        point_rows,
        diagnostics,
    ) -> None:
        result = request.boundary_loop_result
        if result is None:
            return
        role_specs = {
            "roundabout_approach_clip_boundary": (
                "roundabout_approach_clip_to_design_surface",
                ("design_surface",),
                "roundabout_approach_clip_boundary",
                "design_surface",
            ),
            "roundabout_subgrade_clip_boundary": (
                "roundabout_subgrade_to_approach_subgrade",
                ("subgrade_surface", "roundabout_subgrade_surface"),
                "roundabout_subgrade_clip_boundary",
                "subgrade_surface",
            ),
            "roundabout_slope_handoff_boundary": (
                "roundabout_slope_to_corridor_slope_face",
                ("slope_face_surface",),
                "roundabout_slope_handoff_boundary",
                "slope_face_surface",
            ),
        }
        accepted = {role: set() for role in role_specs}
        for loop in list(getattr(result, "loop_rows", []) or []):
            role = str(getattr(loop, "loop_role", "") or "")
            if role not in role_specs:
                continue
            if str(getattr(loop, "status", "") or "") != "ready" or not bool(
                getattr(loop, "closed", False)
            ):
                diagnostics.append(
                    f"{role}_shared_breakline_loop_not_ready:"
                    f"{getattr(loop, 'loop_id', '') or ''}"
                )
                continue
            accepted[role].update(
                str(ref or "")
                for ref in tuple(getattr(loop, "segment_refs", ()) or ())
                if str(ref or "")
            )
        if not any(accepted.values()):
            diagnostics.append("roundabout_clip_boundary_shared_breaklines_missing")
            return
        existing = set(request.existing_breakline_ids)
        emitted = set()
        counts = {role: 0 for role in role_specs}
        for index, segment in enumerate(
            list(getattr(result, "segment_rows", []) or []), start=1
        ):
            segment_id = str(getattr(segment, "segment_id", "") or "")
            segment_role = str(getattr(segment, "segment_role", "") or "")
            if segment_id not in accepted.get(segment_role, set()):
                continue
            start = tuple(getattr(segment, "from_xyz", ()) or ())
            end = tuple(getattr(segment, "to_xyz", ()) or ())
            if len(start) < 3 or len(end) < 3:
                diagnostics.append(
                    f"{segment_role}_shared_breakline_points_missing:"
                    f"{segment_id or index}"
                )
                continue
            start_xyz, end_xyz = _xyz(start), _xyz(end)
            if _distance(start_xyz, end_xyz) <= 1.0e-9:
                diagnostics.append(
                    f"{segment_role}_shared_breakline_degenerate:"
                    f"{segment_id or index}"
                )
                continue
            role, consumers, from_owner, to_owner = role_specs[segment_role]
            edge_key = (role, tuple(sorted((_node_key(start_xyz), _node_key(end_xyz)))))
            if edge_key in emitted:
                continue
            emitted.add(edge_key)
            base_ref = str(getattr(segment, "shared_breakline_ref", "") or "")
            safe_role = _safe_id(segment_role)
            breakline_id = (
                f"{base_ref}:roundabout-clip"
                if base_ref
                else f"{request.result_id}:roundabout-clip:{safe_role}:{index}"
            )
            if breakline_id in existing:
                breakline_id = f"{breakline_id}:{len(existing) + 1}"
            existing.add(breakline_id)
            refs = _append_two_points(
                breakline_id, start_xyz, end_xyz, segment, point_rows
            )
            source_refs = _unique(
                (
                    str(getattr(result, "boundary_loop_result_id", "") or ""),
                    str(getattr(segment, "loop_ref", "") or ""),
                    segment_id,
                    *tuple(getattr(segment, "source_refs", ()) or ()),
                )
            )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="intersection",
                    domain_ref=str(
                        getattr(segment, "intersection_id", "")
                        or request.intersection_id
                    ),
                    breakline_role=role,
                    source_contract_refs=tuple(source_refs),
                    consumer_refs=consumers,
                    from_output_role=from_owner,
                    to_output_role=to_owner,
                    point_refs=tuple(refs),
                    material_role="roundabout_clip_boundary",
                    source_status=str(
                        getattr(segment, "source_status", "") or "accepted"
                    ),
                    diagnostic_rows=tuple(
                        str(value or "")
                        for value in tuple(getattr(segment, "diagnostics", ()) or ())
                        if str(value or "")
                    ),
                    handoff_target="roundabout_ordinary_surface_clip",
                    notes=(
                        "Roundabout clip boundary shared breakline for ordinary "
                        "corridor surface handoff."
                    ),
                )
            )
            counts[segment_role] += 1
        total = sum(counts.values())
        if total <= 0:
            diagnostics.append("roundabout_clip_boundary_shared_breaklines_empty")
            return
        diagnostics.append(f"roundabout_clip_boundary_shared_breaklines:{total}")
        diagnostics.extend(
            f"{role}_shared_breaklines:{count}" for role, count in counts.items()
        )

    def _append_curb_return_bridge(
        self,
        request,
        *,
        breakline_rows,
        point_rows,
        diagnostics,
    ) -> None:
        result = request.boundary_loop_result
        if result is None:
            return
        segments = _curb_return_bridge_segments(result)
        if not segments:
            return
        existing = set(request.existing_breakline_ids)
        appended = 0
        for index, (group_id, start, end, source_diagnostic) in enumerate(
            segments, start=1
        ):
            if _distance(start, end) <= 1.0e-9:
                continue
            breakline_id = (
                f"{request.result_id}:curb-return-bridge-to-"
                f"intersection-slope-face:{index}"
            )
            if breakline_id in existing:
                breakline_id = f"{breakline_id}:bridge"
            existing.add(breakline_id)
            refs = []
            for point_index, point in enumerate((start, end), start=1):
                point_id = f"{breakline_id}:p{point_index}"
                refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=breakline_id,
                        sequence=point_index - 1,
                        x=point[0],
                        y=point[1],
                        z=point[2],
                        source_point_ref=group_id,
                        notes=(
                            "diagnostic curb-return bridge point for intersection "
                            "slope-face graph."
                        ),
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="intersection",
                    domain_ref=request.intersection_id,
                    breakline_role=(
                        "curb_return_bridge_to_intersection_slope_face"
                    ),
                    source_contract_refs=tuple(
                        _unique(
                            (
                                str(
                                    getattr(
                                        result, "boundary_loop_result_id", ""
                                    )
                                    or ""
                                ),
                                group_id,
                                source_diagnostic,
                            )
                        )
                    ),
                    consumer_refs=(
                        "intersection_slope_face_surface",
                        "intersection_slope_face_cell_result",
                    ),
                    from_output_role="curb_return_bridge",
                    to_output_role="intersection_slope_face_surface",
                    point_refs=tuple(refs),
                    material_role="side_slope",
                    source_status="diagnostic",
                    handoff_target="intersection_shared_boundary_graph",
                    notes=(
                        "Diagnostic shared bridge candidate for curb-return/"
                        "intersection slope-face closure; not an outer boundary "
                        "loop segment."
                    ),
                )
            )
            appended += 1
        if appended:
            diagnostics.append(
                f"intersection_curb_return_bridge_shared_breaklines:{appended}"
            )

    def _append_tie_slope(
        self,
        request,
        *,
        breakline_rows,
        point_rows,
        diagnostics,
    ) -> None:
        result = request.tie_slope_result
        if result is None:
            diagnostics.append("intersection_tie_slope_shared_breaklines_missing_result")
            return
        if request.tie_slope_window_rows:
            _append_tie_slope_window(
                intersection_id=request.intersection_id,
                tie_slope_result=result,
                window_rows=list(request.tie_slope_window_rows),
                breakline_rows=breakline_rows,
                point_rows=point_rows,
                diagnostics=diagnostics,
                existing_breakline_ids=request.existing_breakline_ids,
            )
            return
        edge_specs = (
            (
                "inner",
                "intersection_tie_slope_transition_inner",
                "inner_intersection_edge_xyz",
                "inner_breakline_ref",
                (
                    "intersection_tie_slope_surface",
                    "intersection_slope_face_surface",
                    "intersection_surface",
                ),
                "intersection_surface",
                "intersection_tie_slope_surface",
            ),
            (
                "outer",
                "intersection_tie_slope_transition_outer",
                "outer_applied_section_edge_xyz",
                "outer_breakline_ref",
                ("intersection_tie_slope_surface", "slope_face_surface"),
                "slope_face_surface",
                "intersection_tie_slope_surface",
            ),
            (
                "start_cap",
                "intersection_tie_slope_start_cap",
                "start_cap_edge_xyz",
                "start_cap_breakline_ref",
                ("intersection_tie_slope_surface",),
                "intersection_tie_slope_surface",
                "intersection_tie_slope_surface",
            ),
            (
                "end_cap",
                "intersection_tie_slope_end_cap",
                "end_cap_edge_xyz",
                "end_cap_breakline_ref",
                ("intersection_tie_slope_surface",),
                "intersection_tie_slope_surface",
                "intersection_tie_slope_surface",
            ),
        )
        existing = set(request.existing_breakline_ids)
        appended = 0
        for row_index, row in enumerate(
            list(getattr(result, "tie_slope_rows", []) or []), start=1
        ):
            tie_id = str(
                getattr(row, "tie_slope_id", "") or f"tie-slope:{row_index}"
            )
            if str(getattr(row, "status", "") or "") != "ready":
                diagnostics.append(
                    f"intersection_tie_slope_shared_breakline_row_not_ready:{tie_id}"
                )
                continue
            source_refs = tuple(
                _unique(
                    (
                        str(getattr(result, "tie_slope_result_id", "") or ""),
                        tie_id,
                        str(
                            getattr(row, "source_intersection_boundary_ref", "")
                            or ""
                        ),
                        str(
                            getattr(row, "source_slope_face_boundary_ref", "")
                            or ""
                        ),
                        *tuple(getattr(row, "source_applied_section_refs", ()) or ()),
                        *tuple(getattr(row, "last_applied_section_refs", ()) or ()),
                    )
                )
            )
            fallback_refs = _tie_slope_breakline_refs(
                request.intersection_id, tie_id
            )
            for edge_key, role, edge_attr, ref_attr, consumers, from_role, to_role in edge_specs:
                points = [
                    _xyz(point)
                    for point in tuple(getattr(row, edge_attr, ()) or ())
                ]
                breakline_id = str(getattr(row, ref_attr, "") or "").strip()
                if len(points) < 2:
                    diagnostics.append(f"{role}_points_missing:{tie_id}")
                    continue
                breakline_id = breakline_id or fallback_refs[edge_key]
                if breakline_id in existing:
                    breakline_id = f"{breakline_id}:tie"
                existing.add(breakline_id)
                refs = []
                for point_index, point in enumerate(points, start=1):
                    point_id = f"{breakline_id}:p{point_index}"
                    refs.append(point_id)
                    point_rows.append(
                        SharedBreaklinePointRow(
                            point_id=point_id,
                            breakline_ref=breakline_id,
                            sequence=point_index - 1,
                            x=point[0],
                            y=point[1],
                            z=point[2],
                            source_point_ref=tie_id,
                            notes=f"Intersection Tie Slope {role} point.",
                        )
                    )
                breakline_rows.append(
                    SharedBreaklineRow(
                        breakline_id=breakline_id,
                        domain_kind="intersection",
                        domain_ref=request.intersection_id,
                        breakline_role=role,
                        source_contract_refs=source_refs,
                        consumer_refs=consumers,
                        from_output_role=from_role,
                        to_output_role=to_role,
                        point_refs=tuple(refs),
                        alignment_ref=str(
                            getattr(row, "alignment_ref", "") or ""
                        ),
                        side=str(getattr(row, "side", "") or ""),
                        material_role="side_slope",
                        source_status="ready",
                        diagnostic_rows=tuple(
                            str(value or "")
                            for value in tuple(getattr(row, "diagnostics", ()) or ())
                            if str(value or "")
                        ),
                        handoff_target="intersection_tie_slope",
                        notes=(
                            "Shared breakline edge for source-owned Intersection "
                            f"Tie Slope; road_role={getattr(row, 'road_role', '')}; "
                            f"edge={role}; legacy_aliases=intersection_tie_slope_"
                            "inner,intersection_tie_slope_outer"
                        ),
                    )
                )
                appended += 1
        diagnostics.append(
            f"intersection_tie_slope_shared_breaklines:{appended}"
            if appended
            else "intersection_tie_slope_shared_breaklines_empty"
        )

    def _append_main_side_slope_face(
        self, request, *, breakline_rows, point_rows, diagnostics
    ) -> None:
        boundary = request.boundary_segment_result
        if boundary is None:
            return
        source_row = _intersection_row_by_id(
            request.intersection_model, request.intersection_id
        )
        primary_ref = str(
            getattr(source_row, "primary_alignment_ref", "") or ""
        ).strip()
        if not primary_ref:
            refs = _unique(
                str(getattr(row, "alignment_ref", "") or "").strip()
                for row in list(getattr(boundary, "segment_rows", []) or [])
                if str(getattr(row, "segment_kind", "") or "") == "tie_in"
            )
            if len(refs) > 1:
                primary_ref = refs[0]
                diagnostics.append(
                    f"main_side_slope_face_tie_primary_alignment_inferred:{primary_ref}"
                )
        rows = [
            row
            for row in list(getattr(boundary, "segment_rows", []) or [])
            if str(getattr(row, "segment_kind", "") or "") == "tie_in"
            and str(getattr(row, "alignment_ref", "") or "").strip()
            and (
                not primary_ref
                or str(getattr(row, "alignment_ref", "") or "").strip()
                != primary_ref
            )
        ]
        for index, row in enumerate(rows, start=1):
            points = [
                _xyz(value)
                for value in (
                    getattr(row, "start_xyz", ()),
                    getattr(row, "end_xyz", ()),
                )
                if len(tuple(value or ())) >= 3
            ]
            if len(points) < 2:
                diagnostics.append(
                    "main_side_slope_face_tie_points_missing:"
                    f"{getattr(row, 'boundary_segment_id', '') or index}"
                )
                continue
            breakline_id = f"{request.result_id}:main-side-slope-face-tie:{index}"
            refs = []
            for point_index, point in enumerate(points):
                point_id = f"{breakline_id}:p{point_index + 1}"
                refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id,
                        breakline_id,
                        point_index,
                        point[0],
                        point[1],
                        point[2],
                        source_point_ref=str(
                            getattr(row, "boundary_segment_id", "") or ""
                        ),
                        notes=(
                            "main/side slope-face tie breakline from "
                            "IntersectionBoundarySegmentResult tie-in segment"
                        ),
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id,
                    "intersection",
                    request.intersection_id,
                    "main_side_slope_face_tie",
                    source_contract_refs=(
                        str(
                            getattr(boundary, "boundary_segment_result_id", "")
                            or ""
                        ),
                        str(getattr(row, "boundary_segment_id", "") or ""),
                    ),
                    consumer_refs=(
                        "intersection_slope_face_surface",
                        "intersection_slope_face_cell_result",
                    ),
                    from_output_role="main_road_intersection_slope_face_cell",
                    to_output_role="side_road_intersection_slope_face_cell",
                    point_refs=tuple(refs),
                    alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                    side=str(getattr(row, "side", "") or ""),
                    material_role="side_slope",
                    source_status=str(getattr(row, "status", "") or "candidate"),
                    handoff_target="intersection_slope_face_surface",
                    notes=(
                        "Internal shared seam between main-road and side-road "
                        "intersection slope-face cells."
                    ),
                )
            )

    def _append_drainage_handoff(
        self, request, *, breakline_rows, point_rows, diagnostics
    ) -> None:
        result = request.drainage_hint_result
        if result is None:
            return
        source_breaklines = [*request.existing_breakline_rows, *breakline_rows]
        source_points = [*request.existing_point_rows, *point_rows]
        for index, hint in enumerate(
            list(getattr(result, "hint_rows", []) or []), start=1
        ):
            role = _drainage_handoff_role(hint)
            source = _drainage_source_breakline(role, source_breaklines)
            hint_id = str(getattr(hint, "hint_id", "") or index)
            if source is None:
                diagnostics.append(f"{role}_source_breakline_missing:{hint_id}")
                continue
            points = _points_for_breakline(
                source_points, str(getattr(source, "breakline_id", "") or "")
            )
            if len(points) < 2:
                diagnostics.append(f"{role}_source_points_missing:{hint_id}")
                continue
            breakline_id = f"{request.result_id}:{_safe_id(role)}:{index}"
            refs = []
            for point_index, source_point in enumerate(points):
                point_id = f"{breakline_id}:p{point_index + 1}"
                refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id,
                        breakline_id,
                        point_index,
                        float(getattr(source_point, "x", 0.0) or 0.0),
                        float(getattr(source_point, "y", 0.0) or 0.0),
                        float(getattr(source_point, "z", 0.0) or 0.0),
                        station=float(
                            getattr(source_point, "station", 0.0) or 0.0
                        ),
                        offset=float(getattr(source_point, "offset", 0.0) or 0.0),
                        source_point_ref=str(
                            getattr(source_point, "point_id", "") or ""
                        ),
                        notes=(
                            "intersection drainage handoff copied from "
                            f"{getattr(source, 'breakline_role', '')}"
                        ),
                    )
                )
            status = str(
                getattr(hint, "status", "")
                or getattr(hint, "source_status", "")
                or "candidate"
            )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id,
                    "intersection",
                    request.intersection_id,
                    role,
                    source_contract_refs=(
                        str(
                            getattr(result, "drainage_hint_result_id", "") or ""
                        ),
                        str(getattr(hint, "hint_id", "") or ""),
                        str(getattr(source, "breakline_id", "") or ""),
                    ),
                    consumer_refs=("intersection_surface", "drainage_surface"),
                    from_output_role="intersection_surface",
                    to_output_role="drainage_surface",
                    point_refs=tuple(refs),
                    alignment_ref=str(getattr(source, "alignment_ref", "") or ""),
                    side=str(getattr(source, "side", "") or ""),
                    material_role="drainage_surface",
                    source_status=status,
                    diagnostic_rows=tuple(
                        str(value)
                        for value in (
                            list(getattr(hint, "diagnostic_rows", ()) or ())
                            + list(
                                getattr(hint, "source_diagnostic_rows", ()) or ()
                            )
                        )
                        if str(value)
                    ),
                    handoff_target=str(
                        getattr(hint, "handoff_target", "")
                        or "intersection_drainage"
                    ),
                    notes=(
                        f"Intersection drainage handoff; hint={getattr(hint, 'hint_kind', '')}; "
                        f"mode={getattr(hint, 'drainage_mode', '')}; "
                        f"source={getattr(source, 'breakline_role', '')}"
                    ),
                )
            )

    def _append_control_area(
        self, request, *, breakline_rows, point_rows, diagnostics
    ) -> None:
        model = request.intersection_model
        applied = request.applied_section_set
        control_ids = {
            str(getattr(row, "control_area_id", "") or "").strip()
            for row in list(getattr(model, "control_area_rows", []) or [])
            if str(getattr(row, "control_area_id", "") or "").strip()
        }
        grouped = {}
        for section in _ordered_sections(applied):
            active_id = str(
                getattr(section, "active_intersection_id", "") or ""
            ).strip()
            if request.intersection_id and active_id != request.intersection_id:
                continue
            if not request.intersection_id and not active_id:
                continue
            control_ref = str(
                getattr(section, "active_intersection_control_area_id", "") or ""
            ).strip()
            if control_ids and control_ref not in control_ids:
                continue
            if not control_ref:
                diagnostics.append(
                    "control_area_boundary_ref_missing:"
                    f"{getattr(section, 'applied_section_id', '')}"
                )
                continue
            key = (
                str(getattr(section, "alignment_id", "") or "").strip(),
                control_ref,
                str(getattr(section, "region_id", "") or "").strip(),
            )
            grouped.setdefault(key, []).append(section)
        if not grouped:
            diagnostics.append("control_area_boundary_shared_breakline_rows_missing")
            return
        for group_index, (key, sections) in enumerate(
            sorted(grouped.items(), key=lambda item: item[0]), start=1
        ):
            alignment_ref, control_ref, region_ref = key
            ordered = sorted(
                sections,
                key=lambda section: float(
                    getattr(section, "station", 0.0) or 0.0
                ),
            )
            for boundary_kind, section in (
                ("control_area_entry", ordered[0]),
                ("control_area_exit", ordered[-1]),
            ):
                for surface_role, points in sorted(
                    _section_surface_role_points(section).items()
                ):
                    if len(points) < 2:
                        continue
                    consumer = _consumer_for_surface_role(surface_role)
                    station = float(getattr(section, "station", 0.0) or 0.0)
                    breakline_id = (
                        f"{request.result_id}:{_safe_id(boundary_kind)}:"
                        f"{group_index}:{_safe_id(control_ref)}:"
                        f"{_safe_id(surface_role)}"
                    )
                    refs = []
                    for point_index, point in enumerate(points):
                        point_id = f"{breakline_id}:p{point_index + 1}"
                        refs.append(point_id)
                        point_rows.append(
                            SharedBreaklinePointRow(
                                point_id,
                                breakline_id,
                                point_index,
                                float(getattr(point, "x", 0.0) or 0.0),
                                float(getattr(point, "y", 0.0) or 0.0),
                                float(getattr(point, "z", 0.0) or 0.0),
                                station=station,
                                offset=float(
                                    getattr(point, "lateral_offset", 0.0) or 0.0
                                ),
                                source_point_ref=(
                                    f"{getattr(section, 'applied_section_id', '')}:"
                                    f"{getattr(point, 'point_id', '')}"
                                ),
                                notes=(
                                    "intersection control-area handoff breakline "
                                    "from Applied Section surface-role endpoints"
                                ),
                            )
                        )
                    breakline_rows.append(
                        SharedBreaklineRow(
                            breakline_id,
                            "intersection_control_area",
                            control_ref,
                            boundary_kind,
                            source_contract_refs=(
                                str(
                                    getattr(section, "applied_section_id", "")
                                    or ""
                                ),
                                control_ref,
                                region_ref,
                            ),
                            consumer_refs=("intersection_surface", consumer),
                            from_output_role="intersection_surface",
                            to_output_role=consumer,
                            point_refs=tuple(refs),
                            station_start=station,
                            station_end=station,
                            alignment_ref=alignment_ref,
                            side="cross_section",
                            material_role=surface_role,
                            source_status="ready",
                            handoff_target="intersection_control_area",
                            notes=(
                                "Region to Intersection control-area handoff; "
                                "role=region_to_intersection_control; "
                                f"boundary={boundary_kind}; region={region_ref}; "
                                f"control_area={control_ref}; surface={surface_role}"
                            ),
                        )
                    )

    def _append_upper_panel(
        self, request, *, breakline_rows, point_rows, diagnostics
    ) -> None:
        if not request.upper_panel_supported:
            diagnostics.append(
                "intersection_upper_slope_face_panel_handoff_suppressed:"
                f"{request.intersection_kind or 'unknown'}"
            )
            return
        candidates = list(request.upper_panel_candidate_rows)
        if not candidates:
            diagnostics.append("intersection_upper_slope_face_panel_handoff_empty")
            return
        appended = 0
        for candidate_index, candidate in enumerate(candidates, start=1):
            loop = [
                _xyz(point)
                for point in list(candidate.get("loop_points_xyz", ()) or ())
                if len(tuple(point or ())) >= 3
            ]
            if len(loop) >= 2 and _distance(loop[0], loop[-1]) <= 1.0e-6:
                loop = loop[:-1]
            candidate_id = str(
                candidate.get("candidate_id", "") or candidate_index
            )
            if len(loop) < 4:
                diagnostics.append(
                    "intersection_upper_slope_face_panel_handoff_loop_missing:"
                    f"{candidate_id}"
                )
                continue
            specs = (
                (
                    "intersection_upper_slope_face_panel_inner",
                    (loop[0], loop[1]),
                    "intersection_surface",
                ),
                (
                    "intersection_upper_slope_face_panel_right_cap",
                    (loop[1], loop[2]),
                    "intersection_slope_face_surface",
                ),
                (
                    "intersection_upper_slope_face_panel_outer",
                    (loop[3], loop[2]),
                    "slope_face_surface",
                ),
                (
                    "intersection_upper_slope_face_panel_left_cap",
                    (loop[0], loop[3]),
                    "intersection_slope_face_surface",
                ),
            )
            source_refs = tuple(
                _unique(
                    (
                        candidate_id,
                        str(candidate.get("inner_edge_ref", "") or ""),
                        str(candidate.get("outer_edge_ref", "") or ""),
                        str(candidate.get("left_cap_ref", "") or ""),
                        str(candidate.get("right_cap_ref", "") or ""),
                        *tuple(
                            candidate.get("source_shared_breakline_refs", ()) or ()
                        ),
                    )
                )
            )
            source_status = (
                "accepted"
                if str(candidate.get("status", "") or "") == "accepted"
                else "warning"
            )
            candidate_diagnostics = tuple(
                str(value or "")
                for value in tuple(candidate.get("diagnostics", ()) or ())
                if str(value or "")
            )
            for role, points, adjacent_role in specs:
                if _distance(points[0], points[-1]) <= 1.0e-9:
                    diagnostics.append(f"{role}_points_missing:{candidate_id}")
                    continue
                breakline_id = (
                    f"{request.result_id}:{role.replace('_', '-')}:"
                    f"{candidate_index}"
                )
                refs = []
                for point_index, point in enumerate(points):
                    point_id = f"{breakline_id}:p{point_index + 1}"
                    refs.append(point_id)
                    point_rows.append(
                        SharedBreaklinePointRow(
                            point_id,
                            breakline_id,
                            point_index,
                            point[0],
                            point[1],
                            point[2],
                            source_point_ref=candidate_id,
                            notes=(
                                "upper rectangular intersection slope-face "
                                f"panel handoff point for {role}"
                            ),
                        )
                    )
                breakline_rows.append(
                    SharedBreaklineRow(
                        breakline_id,
                        "intersection",
                        request.intersection_id,
                        role,
                        source_contract_refs=source_refs,
                        consumer_refs=(
                            "intersection_slope_face_surface",
                            "intersection_upper_slope_face_panel_handoff",
                        ),
                        from_output_role=adjacent_role,
                        to_output_role="intersection_slope_face_surface",
                        point_refs=tuple(refs),
                        alignment_ref=str(
                            candidate.get("alignment_ref", "") or ""
                        ),
                        side=str(candidate.get("side", "") or ""),
                        material_role="side_slope",
                        source_status=source_status,
                        diagnostic_rows=candidate_diagnostics,
                        handoff_target="intersection_slope_face_surface",
                        notes=(
                            "Auditable handoff edge for upper rectangular "
                            "Intersection Slope Face Surface panel; "
                            f"candidate={candidate_id}; adjacent={adjacent_role}."
                        ),
                    )
                )
                appended += 1
        diagnostics.append(
            f"intersection_upper_slope_face_panel_handoff_breaklines:{appended}"
            if appended
            else "intersection_upper_slope_face_panel_handoff_breaklines_empty"
        )


def _append_slope_face_contacts(
    request,
    *,
    breakline_rows,
    point_rows,
    diagnostics,
):
    result_id = request.result_id
    intersection_id = request.intersection_id
    applied_section_set = request.applied_section_set
    slope_boundary_result = request.slope_face_boundary_result
    boundary_result = request.boundary_segment_result
    intersection_slope_face_visible_boundary_ids = set(
        request.visible_slope_boundary_ids
    )
    if slope_boundary_result is None or boundary_result is None:
        return

    def add_intersection_slope_face_cell_breakline(
        *,
        base_id,
        role,
        points,
        source_refs,
        alignment_ref="",
        side="",
        material_role="side_slope",
        source_status="candidate",
        diagnostics_rows=(),
        notes="",
        consumer_refs=("intersection_slope_face_cell_result",),
    ):
        clean_points = [
            _xyz(point)
            for point in list(points or [])
            if len(tuple(point or ())) >= 3
        ]
        if len(clean_points) < 2:
            diagnostics.append(f"{role}_points_missing:{base_id}")
            return ""
        breakline_id = (
            f"{result_id}:{role.replace('_', '-')}:{base_id}"
        )
        refs = []
        for point_index, point in enumerate(clean_points):
            point_id = f"{breakline_id}:p{point_index + 1}"
            refs.append(point_id)
            point_rows.append(
                SharedBreaklinePointRow(
                    point_id,
                    breakline_id,
                    point_index,
                    point[0],
                    point[1],
                    point[2],
                    source_point_ref=";".join(source_refs),
                    notes=(
                        "intersection slope-face cell breakline point "
                        f"for {role}"
                    ),
                )
            )
        breakline_rows.append(
            SharedBreaklineRow(
                breakline_id,
                "intersection",
                intersection_id,
                role,
                source_contract_refs=tuple(
                    value for value in source_refs if value
                ),
                consumer_refs=consumer_refs,
                from_output_role="intersection_slope_face_cell",
                to_output_role="intersection_slope_face_surface",
                point_refs=tuple(refs),
                alignment_ref=alignment_ref,
                side=side,
                material_role=material_role,
                source_status=source_status,
                diagnostic_rows=diagnostics_rows,
                handoff_target="intersection_slope_face_surface",
                notes=notes or (
                    "Shared breakline candidate for cell-based "
                    "Intersection Slope Face Surface."
                ),
            )
        )
        return breakline_id

    for index, row in enumerate(list(getattr(slope_boundary_result, "boundary_rows", []) or []), start=1):
        inner_points = list(getattr(row, "inner_points_xyz", ()) or ())
        if len(inner_points) < 2:
            diagnostics.append(f"patch_to_slope_face_points_missing:{str(getattr(row, 'boundary_id', '') or index)}")
            continue
        breakline_id = f"{result_id}:patch-to-slope-face:{index}"
        refs = []
        for point_index, point in enumerate(inner_points):
            x, y, z = _xyz(point)
            point_id = f"{breakline_id}:p{point_index + 1}"
            refs.append(point_id)
            point_rows.append(
                SharedBreaklinePointRow(
                    point_id=point_id,
                    breakline_ref=breakline_id,
                    sequence=point_index,
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=str(getattr(row, "boundary_id", "") or ""),
                    notes="shared patch-to-slope-face breakline from Applied Section side-slope edge",
                )
            )
        intersection_slope_consumers = (
            ("intersection_surface", "slope_face_surface", "intersection_slope_face_surface")
            if str(getattr(row, "boundary_id", "") or "") in intersection_slope_face_visible_boundary_ids
            else ("intersection_surface", "slope_face_surface")
        )
        breakline_rows.append(
            SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="intersection",
                domain_ref=intersection_id,
                breakline_role="patch_to_slope_face",
                source_contract_refs=(
                    str(getattr(slope_boundary_result, "boundary_result_id", "") or ""),
                    str(getattr(row, "boundary_id", "") or ""),
                ),
                consumer_refs=intersection_slope_consumers,
                from_output_role="intersection_surface",
                to_output_role="slope_face_surface",
                point_refs=tuple(refs),
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="side_slope",
                source_status=str(getattr(row, "status", "") or "candidate"),
                diagnostic_rows=tuple(str(value) for value in list(getattr(row, "diagnostics", ()) or ())),
                notes="Shared boundary between Intersection Surface and Slope Face Surface.",
            )
        )
        row_id = str(getattr(row, "boundary_id", "") or index)
        is_cell_candidate = (
            not intersection_slope_face_visible_boundary_ids
            or row_id in intersection_slope_face_visible_boundary_ids
        )
        if is_cell_candidate:
            common_source_refs = tuple(
                _unique(
                    [
                        str(getattr(slope_boundary_result, "boundary_result_id", "") or ""),
                        row_id,
                        *_slope_face_context_refs(
                            applied_section_set,
                            intersection_id=intersection_id,
                            alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                        ),
                    ]
                )
            )
            add_intersection_slope_face_cell_breakline(
                base_id=str(index),
                role="patch_to_intersection_slope_face",
                points=inner_points,
                source_refs=common_source_refs,
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="side_slope",
                source_status=str(getattr(row, "status", "") or "candidate"),
                diagnostics_rows=tuple(str(value) for value in list(getattr(row, "diagnostics", ()) or ())),
                notes="Cell boundary between Intersection Surface and dedicated Intersection Slope Face Surface.",
                consumer_refs=("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            )
            outer_points = list(getattr(row, "outer_points_xyz", ()) or ())
            add_intersection_slope_face_cell_breakline(
                base_id=str(index),
                role="intersection_slope_face_to_corridor_slope_face",
                points=outer_points,
                source_refs=common_source_refs,
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="side_slope",
                source_status=str(getattr(row, "status", "") or "candidate"),
                diagnostics_rows=tuple(str(value) for value in list(getattr(row, "diagnostics", ()) or ())),
                notes="Cell boundary between dedicated Intersection Slope Face Surface and ordinary Slope Face Surface.",
                consumer_refs=("slope_face_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            )
            _append_local_clip_caps(
                add_breakline=add_intersection_slope_face_cell_breakline,
                row=row,
                row_index=index,
                inner_points=inner_points,
                outer_points=outer_points,
                slope_boundary_result=slope_boundary_result,
                source_refs=common_source_refs,
            )
        shoulder_breakline_id = f"{result_id}:patch-to-shoulder:{index}"
        shoulder_refs = []
        for point_index, point in enumerate(inner_points):
            x, y, z = _xyz(point)
            point_id = f"{shoulder_breakline_id}:p{point_index + 1}"
            shoulder_refs.append(point_id)
            point_rows.append(
                SharedBreaklinePointRow(
                    point_id=point_id,
                    breakline_ref=shoulder_breakline_id,
                    sequence=point_index,
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=str(getattr(row, "boundary_id", "") or ""),
                    notes="shared patch-to-shoulder breakline from Applied Section shoulder edge",
                )
            )
        shoulder_slope_consumers = (
            ("design_surface", "slope_face_surface", "intersection_slope_face_surface")
            if str(getattr(row, "boundary_id", "") or "") in intersection_slope_face_visible_boundary_ids
            else ("design_surface", "slope_face_surface")
        )
        breakline_rows.append(
            SharedBreaklineRow(
                breakline_id=shoulder_breakline_id,
                domain_kind="intersection",
                domain_ref=intersection_id,
                breakline_role="patch_to_shoulder",
                source_contract_refs=(
                    str(getattr(slope_boundary_result, "boundary_result_id", "") or ""),
                    str(getattr(row, "boundary_id", "") or ""),
                ),
                consumer_refs=("intersection_surface", "design_surface"),
                from_output_role="intersection_surface",
                to_output_role="design_surface",
                point_refs=tuple(shoulder_refs),
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="shoulder",
                source_status=str(getattr(row, "status", "") or "candidate"),
                diagnostic_rows=tuple(str(value) for value in list(getattr(row, "diagnostics", ()) or ())),
                notes="Shared shoulder-role boundary between Intersection Surface and Design Surface.",
            )
        )
        shoulder_slope_breakline_id = f"{result_id}:shoulder-to-slope-face:{index}"
        shoulder_slope_refs = []
        for point_index, point in enumerate(inner_points):
            x, y, z = _xyz(point)
            point_id = f"{shoulder_slope_breakline_id}:p{point_index + 1}"
            shoulder_slope_refs.append(point_id)
            point_rows.append(
                SharedBreaklinePointRow(
                    point_id=point_id,
                    breakline_ref=shoulder_slope_breakline_id,
                    sequence=point_index,
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=str(getattr(row, "boundary_id", "") or ""),
                    notes="shared shoulder-to-slope-face breakline from Applied Section shoulder edge",
                )
            )
        breakline_rows.append(
            SharedBreaklineRow(
                breakline_id=shoulder_slope_breakline_id,
                domain_kind="intersection",
                domain_ref=intersection_id,
                breakline_role="shoulder_to_slope_face",
                source_contract_refs=(
                    str(getattr(slope_boundary_result, "boundary_result_id", "") or ""),
                    str(getattr(row, "boundary_id", "") or ""),
                ),
                consumer_refs=shoulder_slope_consumers,
                from_output_role="design_surface",
                to_output_role="slope_face_surface",
                point_refs=tuple(shoulder_slope_refs),
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="shoulder",
                source_status=str(getattr(row, "status", "") or "candidate"),
                diagnostic_rows=tuple(str(value) for value in list(getattr(row, "diagnostics", ()) or ())),
                notes="Shared shoulder-to-slope-face boundary between Design Surface and Slope Face Surface.",
            )
        )
        row_id = str(getattr(row, "boundary_id", "") or index)
        is_cell_candidate = (
            not intersection_slope_face_visible_boundary_ids
            or row_id in intersection_slope_face_visible_boundary_ids
        )
        if is_cell_candidate:
            add_intersection_slope_face_cell_breakline(
                base_id=str(index),
                role="intersection_slope_face_to_design_surface",
                points=inner_points,
                source_refs=tuple(
                    _unique(
                        [
                            str(getattr(slope_boundary_result, "boundary_result_id", "") or ""),
                            str(getattr(row, "boundary_id", "") or index),
                            *_slope_face_context_refs(
                                applied_section_set,
                                intersection_id=intersection_id,
                                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                            ),
                        ]
                    )
                ),
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="shoulder",
                source_status=str(getattr(row, "status", "") or "candidate"),
                diagnostics_rows=tuple(str(value) for value in list(getattr(row, "diagnostics", ()) or ())),
                notes="Cell boundary between dedicated Intersection Slope Face Surface and Design Surface.",
                consumer_refs=("design_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            )
    curb_return_rows = [
        row for row in list(getattr(boundary_result, "segment_rows", []) or [])
        if str(getattr(row, "segment_role", "") or "") == "curb_return"
    ]
    for index, row in enumerate(curb_return_rows, start=1):
        points = list(getattr(row, "chord_points_xyz", ()) or ())
        if len(points) < 2:
            points = [getattr(row, "start_xyz", ()), getattr(row, "end_xyz", ())]
        points = [point for point in points if len(tuple(point or ())) >= 3]
        if len(points) < 2:
            diagnostics.append(f"curb_return_outer_points_missing:{str(getattr(row, 'boundary_segment_id', '') or index)}")
            continue
        breakline_id = f"{result_id}:curb-return-outer:{index}"
        refs = []
        for point_index, point in enumerate(points):
            x, y, z = _xyz(point)
            point_id = f"{breakline_id}:p{point_index + 1}"
            refs.append(point_id)
            point_rows.append(
                SharedBreaklinePointRow(
                    point_id=point_id,
                    breakline_ref=breakline_id,
                    sequence=point_index,
                    x=x,
                    y=y,
                    z=z,
                    source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                    notes="shared curb-return outer breakline from IntersectionBoundarySegmentResult curb_return arc",
                )
            )
        breakline_rows.append(
            SharedBreaklineRow(
                breakline_id=breakline_id,
                domain_kind="intersection",
                domain_ref=intersection_id,
                breakline_role="curb_return_outer",
                source_contract_refs=(
                    str(getattr(boundary_result, "boundary_segment_result_id", "") or ""),
                    str(getattr(row, "boundary_segment_id", "") or ""),
                ),
                consumer_refs=("intersection_surface",),
                from_output_role="intersection_edge_network",
                to_output_role="intersection_surface",
                point_refs=tuple(refs),
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="curb_return",
                source_status=str(getattr(row, "status", "") or "candidate"),
                notes="First-class curb-return outer breakline consumed by the Intersection Surface.",
            )
        )
        center = _xyz(getattr(row, "center_xyz", (0.0, 0.0, 0.0)))
        inner_points = [_lerp(center, _xyz(point), 0.58) for point in points]
        if len(inner_points) >= 2:
            inner_breakline_id = f"{result_id}:curb-return-inner:{index}"
            inner_refs = []
            for point_index, point in enumerate(inner_points):
                x, y, z = _xyz(point)
                point_id = f"{inner_breakline_id}:p{point_index + 1}"
                inner_refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=inner_breakline_id,
                        sequence=point_index,
                        x=x,
                        y=y,
                        z=z,
                        source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                        notes="shared curb-return inner breakline from deterministic curb-return blend offset",
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=inner_breakline_id,
                    domain_kind="intersection",
                    domain_ref=intersection_id,
                    breakline_role="curb_return_inner",
                    source_contract_refs=(
                        str(getattr(boundary_result, "boundary_segment_result_id", "") or ""),
                        str(getattr(row, "boundary_segment_id", "") or ""),
                    ),
                    consumer_refs=("intersection_surface",),
                    from_output_role="intersection_edge_network",
                    to_output_role="intersection_surface",
                    point_refs=tuple(inner_refs),
                    alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                    side=str(getattr(row, "side", "") or ""),
                    material_role="curb_return",
                    source_status=str(getattr(row, "status", "") or "candidate"),
                    notes="First-class curb-return inner breakline consumed by the Intersection Surface.",
                )
            )
        contact_segments = []
        if len(points) >= 2:
            contact_segments.append(("start", points[:2]))
            contact_segments.append(("end", points[-2:]))
        for contact_role, contact_points in contact_segments:
            contact_breakline_id = f"{result_id}:curb-return-to-pavement:{index}:{contact_role}"
            contact_refs = []
            for point_index, point in enumerate(contact_points):
                x, y, z = _xyz(point)
                point_id = f"{contact_breakline_id}:p{point_index + 1}"
                contact_refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=contact_breakline_id,
                        sequence=point_index,
                        x=x,
                        y=y,
                        z=z,
                        source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                        notes=f"shared curb-return to pavement contact segment at {contact_role} arc endpoint",
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=contact_breakline_id,
                    domain_kind="intersection",
                    domain_ref=intersection_id,
                    breakline_role="curb_return_to_pavement",
                    source_contract_refs=(
                        str(getattr(boundary_result, "boundary_segment_result_id", "") or ""),
                        str(getattr(row, "boundary_segment_id", "") or ""),
                    ),
                    consumer_refs=("intersection_surface", "design_surface"),
                    from_output_role="intersection_edge_network",
                    to_output_role="intersection_surface",
                    point_refs=tuple(contact_refs),
                    alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                    side=str(getattr(row, "side", "") or ""),
                    material_role="pavement",
                    source_status=str(getattr(row, "status", "") or "candidate"),
                    notes=f"First-slice curb-return to pavement contact at {contact_role} arc endpoint.",
                )
            )
            shoulder_contact_breakline_id = f"{result_id}:curb-return-to-shoulder:{index}:{contact_role}"
            shoulder_contact_refs = []
            for point_index, point in enumerate(contact_points):
                x, y, z = _xyz(point)
                point_id = f"{shoulder_contact_breakline_id}:p{point_index + 1}"
                shoulder_contact_refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=shoulder_contact_breakline_id,
                        sequence=point_index,
                        x=x,
                        y=y,
                        z=z,
                        source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                        notes=f"shared curb-return to shoulder contact segment at {contact_role} arc endpoint",
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=shoulder_contact_breakline_id,
                    domain_kind="intersection",
                    domain_ref=intersection_id,
                    breakline_role="curb_return_to_shoulder",
                    source_contract_refs=(
                        str(getattr(boundary_result, "boundary_segment_result_id", "") or ""),
                        str(getattr(row, "boundary_segment_id", "") or ""),
                    ),
                    consumer_refs=("intersection_surface", "design_surface"),
                    from_output_role="intersection_edge_network",
                    to_output_role="design_surface",
                    point_refs=tuple(shoulder_contact_refs),
                    alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                    side=str(getattr(row, "side", "") or ""),
                    material_role="shoulder",
                    source_status=str(getattr(row, "status", "") or "candidate"),
                    notes=f"First-slice curb-return to shoulder contact at {contact_role} arc endpoint.",
                )
            )
            slope_contact_breakline_id = f"{result_id}:curb-return-to-slope-face:{index}:{contact_role}"
            slope_contact_refs = []
            for point_index, point in enumerate(contact_points):
                x, y, z = _xyz(point)
                point_id = f"{slope_contact_breakline_id}:p{point_index + 1}"
                slope_contact_refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=slope_contact_breakline_id,
                        sequence=point_index,
                        x=x,
                        y=y,
                        z=z,
                        source_point_ref=str(getattr(row, "boundary_segment_id", "") or ""),
                        notes=f"shared curb-return to slope-face contact segment at {contact_role} arc endpoint",
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=slope_contact_breakline_id,
                    domain_kind="intersection",
                    domain_ref=intersection_id,
                    breakline_role="curb_return_to_slope_face",
                    source_contract_refs=(
                        str(getattr(boundary_result, "boundary_segment_result_id", "") or ""),
                        str(getattr(row, "boundary_segment_id", "") or ""),
                    ),
                    consumer_refs=("intersection_surface", "slope_face_surface", "intersection_slope_face_surface"),
                    from_output_role="intersection_edge_network",
                    to_output_role="slope_face_surface",
                    point_refs=tuple(slope_contact_refs),
                    alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                    side=str(getattr(row, "side", "") or ""),
                    material_role="side_slope",
                    source_status=str(getattr(row, "status", "") or "candidate"),
                    notes=f"First-slice curb-return to slope-face contact at {contact_role} arc endpoint.",
                )
            )
            add_intersection_slope_face_cell_breakline(
                base_id=f"{index}:{contact_role}",
                role="curb_return_to_intersection_slope_face",
                points=contact_points,
                source_refs=(
                    str(getattr(boundary_result, "boundary_segment_result_id", "") or ""),
                    str(getattr(row, "boundary_segment_id", "") or ""),
                ),
                alignment_ref=str(getattr(row, "alignment_ref", "") or ""),
                side=str(getattr(row, "side", "") or ""),
                material_role="side_slope",
                source_status=str(getattr(row, "status", "") or "candidate"),
                notes=f"Cell boundary between curb-return perimeter and Intersection Slope Face Surface at {contact_role}.",
                consumer_refs=("intersection_surface", "intersection_slope_face_surface", "intersection_slope_face_cell_result"),
            )


def _append_tie_slope_window(
    *,
    intersection_id: str,
    tie_slope_result: object,
    window_rows: list[dict[str, object]],
    breakline_rows: list[SharedBreaklineRow],
    point_rows: list[SharedBreaklinePointRow],
    diagnostics: list[str],
    existing_breakline_ids: tuple[str, ...] = (),
) -> None:
    default_edge_specs = (
        (
            "outer",
            "intersection_tie_slope_window_outer",
            "outer_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface", "slope_face_surface"),
            "slope_face_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "inner",
            "intersection_tie_slope_window_inner",
            "inner_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface", "intersection_slope_face_surface"),
            "intersection_slope_face_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "start_cap",
            "intersection_tie_slope_window_start_cap",
            "start_cap_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface"),
            "intersection_tie_slope_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "end_cap",
            "intersection_tie_slope_window_end_cap",
            "end_cap_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface"),
            "intersection_tie_slope_surface",
            "intersection_tie_slope_surface",
        ),
    )

    curb_return_approach_edge_specs = (
        (
            "outer",
            "intersection_tie_slope_approach_outer",
            "outer_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface", "slope_face_surface"),
            "slope_face_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "inner",
            "intersection_tie_slope_to_curb_return_approach",
            "inner_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface", "intersection_slope_face_surface"),
            "intersection_slope_face_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "start_cap",
            "intersection_tie_slope_approach_start_cap",
            "start_cap_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface"),
            "intersection_tie_slope_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "end_cap",
            "intersection_tie_slope_approach_end_cap",
            "end_cap_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface"),
            "intersection_tie_slope_surface",
            "intersection_tie_slope_surface",
        ),
    )
    supplemental_edge_specs = (
        (
            "outer",
            "intersection_tie_slope_supplemental_outer",
            "outer_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface", "slope_face_surface"),
            "slope_face_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "inner",
            "intersection_tie_slope_supplemental_inner",
            "inner_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface", "intersection_slope_face_surface"),
            "intersection_slope_face_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "start_cap",
            "intersection_tie_slope_supplemental_start_cap",
            "start_cap_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface"),
            "intersection_tie_slope_surface",
            "intersection_tie_slope_surface",
        ),
        (
            "end_cap",
            "intersection_tie_slope_supplemental_end_cap",
            "end_cap_edge_xyz",
            ("intersection_tie_slope", "intersection_tie_slope_surface"),
            "intersection_tie_slope_surface",
            "intersection_tie_slope_surface",
        ),
    )
    endpoint_edge_specs = tuple(
        (
            edge_key,
            "intersection_tie_slope_supplemental_endpoint" if edge_key == "inner" else role,
            edge_attr,
            consumers,
            from_role,
            to_role,
        )
        for edge_key, role, edge_attr, consumers, from_role, to_role in supplemental_edge_specs
    )
    existing_ids = set(existing_breakline_ids) | {
        str(getattr(row, "breakline_id", "") or "")
        for row in breakline_rows
    }
    appended_count = 0
    accepted_count = 0
    suppressed_count = 0
    for row_index, row in enumerate(list(window_rows or []), start=1):
        row_id = (
            f"intersection-tie-slope-window:"
            f"{_safe_id(str(row.get('intersection_id', '') or intersection_id))}:"
            f"{_safe_id(str(row.get('alignment_ref', '') or 'alignment'))}:"
            f"{_safe_id(str(row.get('gap_role', '') or 'gap'))}:"
            f"{_safe_id(str(row.get('side', '') or 'side'))}:"
            f"{_safe_id(str(row.get('cell_role', '') or 'cell'))}:"
            f"{row_index}"
        )
        if not _tie_slope_window_surface_row_enabled(row):
            suppressed_count += 1
            ownership_class = str(row.get("ownership_class", "") or "unowned_gap")
            diagnostics.append(
                f"intersection_tie_slope_window_shared_breakline_suppressed_by_ownership:{ownership_class}:{row_id}"
            )
            continue
        row_blocking_diagnostics = [
            str(value or "")
            for value in tuple(row.get("diagnostics", ()) or ())
            if _tie_slope_window_diagnostic_blocks_surface(value)
        ]
        if str(row.get("status", "") or "") != "accepted" or row_blocking_diagnostics:
            diagnostics.append(f"intersection_tie_slope_window_shared_breakline_row_not_accepted:{row_index}")
            continue
        accepted_count += 1
        source_refs = tuple(
            _unique(
                [
                    str(getattr(tie_slope_result, "tie_slope_result_id", "") or ""),
                    row_id,
                    str(row.get("outer_applied_section_ref", "") or ""),
                    str(row.get("inner_applied_section_ref", "") or ""),
                    str(row.get("source_mode", "") or ""),
                ]
            )
        )
        extent_role = str(row.get("supplemental_extent_role", "") or "").strip().lower()
        if extent_role == "supplemental_endpoint_pair":
            edge_specs = endpoint_edge_specs
        elif extent_role == "intersection_supplemental_pair":
            edge_specs = supplemental_edge_specs
        elif str(row.get("cell_role", "") or "") == "curb_return_approach_pair":
            edge_specs = curb_return_approach_edge_specs
        else:
            edge_specs = default_edge_specs
        for edge_key, role, edge_attr, consumers, from_role, to_role in edge_specs:
            points = [_xyz(point) for point in tuple(row.get(edge_attr, ()) or ())]
            if len(points) < 2:
                diagnostics.append(f"{role}_points_missing:{row_id}")
                continue
            breakline_id = f"{row_id}:{role.replace('_', '-')}"
            if breakline_id in existing_ids:
                breakline_id = f"{breakline_id}:window"
            existing_ids.add(breakline_id)
            point_refs: list[str] = []
            for point_index, point in enumerate(points, start=1):
                point_id = f"{breakline_id}:p{point_index}"
                point_refs.append(point_id)
                point_rows.append(
                    SharedBreaklinePointRow(
                        point_id=point_id,
                        breakline_ref=breakline_id,
                        sequence=point_index - 1,
                        x=float(point[0]),
                        y=float(point[1]),
                        z=float(point[2]),
                        source_point_ref=row_id,
                        notes=f"Intersection Tie Slope Applied Section window {role} point.",
                    )
                )
            breakline_rows.append(
                SharedBreaklineRow(
                    breakline_id=breakline_id,
                    domain_kind="intersection",
                    domain_ref=str(row.get("intersection_id", "") or intersection_id),
                    breakline_role=role,
                    source_contract_refs=source_refs,
                    consumer_refs=tuple(consumers),
                    from_output_role=from_role,
                    to_output_role=to_role,
                    point_refs=tuple(point_refs),
                    station_start=float(row.get("outer_station", 0.0) or 0.0),
                    station_end=float(row.get("inner_station", 0.0) or 0.0),
                    alignment_ref=str(row.get("alignment_ref", "") or ""),
                    side=str(row.get("side", "") or ""),
                    material_role="side_slope",
                    source_status="accepted",
                    diagnostic_rows=(),
                    handoff_target="intersection_tie_slope",
                    notes=(
                        "Shared breakline edge for accepted Applied Section window Intersection Tie Slope; "
                        f"cell_role={row.get('cell_role', '')}; edge={edge_key}; "
                        f"supplemental_extent_role={row.get('supplemental_extent_role', '')}; "
                        "source=applied_section_context_transition_window"
                    ),
                )
            )
            appended_count += 1
    if appended_count <= 0:
        diagnostics.append("intersection_tie_slope_window_shared_breaklines_empty")
    else:
        diagnostics.append(
            f"intersection_tie_slope_window_shared_breaklines:{appended_count}; accepted_rows={accepted_count}; suppressed_rows={suppressed_count}"
        )


def _append_two_points(breakline_id, start, end, segment, point_rows):
    refs = []
    for index, point in enumerate((start, end), start=1):
        point_id = f"{breakline_id}:p{index}"
        refs.append(point_id)
        point_rows.append(
            SharedBreaklinePointRow(
                point_id=point_id,
                breakline_ref=breakline_id,
                sequence=index - 1,
                x=point[0],
                y=point[1],
                z=point[2],
                source_point_ref=str(
                    getattr(
                        segment,
                        "from_point_ref" if index == 1 else "to_point_ref",
                        "",
                    )
                ),
                notes=(
                    "authoritative intersection boundary-loop shared breakline point"
                ),
            )
        )
    return refs


def _shared_role_for_segment(segment) -> str:
    role = str(
        getattr(segment, "segment_role", "") or "intersection_outer_boundary"
    )
    mapped = {
        "roundabout_central_island_boundary": "roundabout_island_to_circulatory",
        "roundabout_circulatory_outer_boundary": "roundabout_circulatory_to_apron",
        "roundabout_outer_ownership_boundary": "roundabout_apron_to_slope_face",
        "roundabout_entry_exit_connector_boundary": (
            "roundabout_entry_exit_connector_boundary"
        ),
        "curb_return_envelope_arc": "curb_return_to_intersection_slope_face",
        "curb_return_envelope_connector": "patch_to_design_surface",
    }
    return mapped.get(role, role or "intersection_outer_boundary")


def _expected_consumers(segment, role):
    mapped = EXPECTED_CONSUMERS.get(role, ())
    if mapped:
        return tuple(mapped)
    values = _unique(tuple(getattr(segment, "expected_consumers", ()) or ()))
    return tuple(values) or ("intersection_surface",)


def _intersection_row_by_id(model, intersection_id):
    return next(
        (
            row
            for row in list(getattr(model, "intersection_rows", []) or [])
            if str(getattr(row, "intersection_id", "") or "").strip()
            == str(intersection_id or "").strip()
        ),
        None,
    ) if model is not None else None


def _unique(values):
    output = []
    for value in values:
        text = str(value or "")
        if text and text not in output:
            output.append(text)
    return output


def _xyz(value):
    values = tuple(value or ())
    return tuple(float(values[index]) if len(values) > index else 0.0 for index in range(3))


def _distance(first, second):
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def _node_key(point):
    return tuple(round(float(value), 6) for value in point)


def _safe_id(value):
    return "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in str(value or "")
    ).strip("-") or "unknown"


def _curb_return_bridge_segments(boundary_loop_result):
    rows = []
    seen = set()
    for diagnostic in list(
        getattr(boundary_loop_result, "diagnostic_rows", []) or []
    ):
        text = str(diagnostic or "")
        if (
            "intersection_boundary_curb_arc_bridge_required:" not in text
            or "sample=" not in text
        ):
            continue
        group_id = (
            text.split("intersection_boundary_curb_arc_bridge_required:", 1)[1]
            .split(":missing_segments=", 1)[0]
            .strip()
        )
        for sample in text.split("sample=", 1)[1].split(","):
            parsed = _parse_bridge_sample(sample)
            if parsed is None:
                continue
            key = tuple(sorted((_node_key(parsed[0]), _node_key(parsed[1]))))
            if key in seen:
                continue
            seen.add(key)
            rows.append((group_id, parsed[0], parsed[1], text.strip()))
    return rows


def _parse_bridge_sample(sample):
    if "->" not in str(sample or ""):
        return None
    first, second = str(sample).split("->", 1)
    first_xyz, second_xyz = _parse_bridge_point(first), _parse_bridge_point(second)
    return (first_xyz, second_xyz) if first_xyz and second_xyz else None


def _parse_bridge_point(value):
    parts = str(value or "").split(":")
    if len(parts) < 2:
        return None
    try:
        return (float(parts[0]), float(parts[1]), 0.0)
    except Exception:
        return None


def _tie_slope_breakline_refs(intersection_id, tie_slope_id):
    result_id = f"shared-breakline:intersection:{intersection_id or 'main'}"
    safe_id = _safe_id(tie_slope_id or "tie-slope")
    return {
        "inner": f"{result_id}:intersection-tie-slope-transition-inner:{safe_id}",
        "outer": f"{result_id}:intersection-tie-slope-transition-outer:{safe_id}",
        "start_cap": f"{result_id}:intersection-tie-slope-start-cap:{safe_id}",
        "end_cap": f"{result_id}:intersection-tie-slope-end-cap:{safe_id}",
    }


def _drainage_handoff_role(hint):
    kind = str(getattr(hint, "hint_kind", "") or "").lower()
    recommended = str(
        getattr(hint, "recommended_element_kind", "") or ""
    ).lower()
    mode = str(getattr(hint, "drainage_mode", "") or "").lower()
    if "low_point" in kind or "low_point" in recommended:
        return "low_point_flow_split"
    if "inlet" in kind or "inlet" in recommended or "gutter" in mode:
        return "intersection_gutter_handoff"
    return "intersection_ditch_handoff"


def _drainage_source_breakline(role, rows):
    candidates = {
        "intersection_gutter_handoff": (
            "curb_return_to_pavement",
            "curb_return_to_shoulder",
            "patch_to_shoulder",
            "patch_to_design",
        ),
        "low_point_flow_split": (
            "patch_to_design",
            "patch_to_shoulder",
            "curb_return_to_pavement",
        ),
    }.get(
        role,
        (
            "shoulder_to_slope_face",
            "patch_to_slope_face",
            "curb_return_to_slope_face",
        ),
    )
    return next(
        (
            row
            for candidate in candidates
            for row in rows
            if str(getattr(row, "breakline_role", "") or "") == candidate
        ),
        None,
    )


def _points_for_breakline(points, breakline_id):
    return sorted(
        [
            point
            for point in points
            if str(getattr(point, "breakline_ref", "") or "") == breakline_id
        ],
        key=lambda point: int(getattr(point, "sequence", 0) or 0),
    )


def _ordered_sections(applied_section_set):
    return sorted(
        list(getattr(applied_section_set, "sections", []) or []),
        key=lambda section: (
            str(getattr(section, "alignment_id", "") or ""),
            str(getattr(section, "region_id", "") or ""),
            float(getattr(section, "station", 0.0) or 0.0),
            str(getattr(section, "applied_section_id", "") or ""),
        ),
    )


def _slope_face_context_refs(
    applied_section_set, *, intersection_id, alignment_ref
):
    refs = []
    target_id = str(intersection_id or "").strip()
    target_alignment = str(alignment_ref or "").strip()
    for section in _ordered_sections(applied_section_set):
        section_alignment = str(
            getattr(section, "alignment_id", "") or ""
        ).strip()
        if target_alignment and section_alignment and section_alignment != target_alignment:
            continue
        active_id = str(
            getattr(section, "active_intersection_id", "") or ""
        ).strip()
        if target_id and active_id != target_id:
            continue
        context_id = active_id or target_id
        if context_id:
            refs.append(f"intersection:{context_id}")
        for kind, value in (
            (
                "control-area",
                getattr(section, "active_intersection_control_area_id", ""),
            ),
            ("leg", getattr(section, "active_intersection_leg_id", "")),
            ("leg", getattr(section, "active_intersection_leg_role", "")),
        ):
            text = str(value or "").strip()
            if not text:
                continue
            refs.append(text)
            if ":" not in text:
                refs.append(f"{kind}:{text}")
                if context_id:
                    refs.append(f"intersection:{context_id}:{kind}:{text}")
        refs.extend(
            str(value or "").strip()
            for value in list(
                getattr(section, "active_intersection_control_region_refs", [])
                or []
            )
        )
        region = str(getattr(section, "region_id", "") or "").strip()
        if region:
            refs.append(region if region.startswith("region:") else f"region:{region}")
        if section_alignment:
            refs.append(section_alignment)
    return tuple(_unique(refs))


def _append_local_clip_caps(
    *,
    add_breakline,
    row,
    row_index,
    inner_points,
    outer_points,
    slope_boundary_result,
    source_refs=(),
):
    inner = [_xyz(point) for point in inner_points or ()]
    outer = [_xyz(point) for point in outer_points or ()]
    if len(inner) < 2 or len(outer) < 2:
        return
    refs = tuple(
        _unique(
            (
                str(getattr(slope_boundary_result, "boundary_result_id", "") or ""),
                str(getattr(row, "boundary_id", "") or row_index),
                *source_refs,
            )
        )
    )
    common = {
        "source_refs": refs,
        "alignment_ref": str(getattr(row, "alignment_ref", "") or ""),
        "side": str(getattr(row, "side", "") or ""),
        "material_role": "slope_face_surface",
        "source_status": str(getattr(row, "status", "") or "candidate"),
        "diagnostics_rows": tuple(
            str(value) for value in list(getattr(row, "diagnostics", ()) or ())
        ),
        "consumer_refs": (
            "intersection_surface",
            "slope_face_surface",
            "intersection_slope_face_surface",
            "intersection_slope_face_cell_result",
        ),
    }
    add_breakline(
        base_id=f"{row_index}:local-clip-start",
        role="control_area_entry",
        points=(inner[0], outer[0]),
        notes=(
            "local_clip cap between intersection slope-face inner and outer "
            "boundaries at the source boundary start."
        ),
        **common,
    )
    add_breakline(
        base_id=f"{row_index}:local-clip-end",
        role="control_area_exit",
        points=(inner[-1], outer[-1]),
        notes=(
            "local_clip cap between intersection slope-face inner and outer "
            "boundaries at the source boundary end."
        ),
        **common,
    )


def _lerp(first, second, factor):
    return tuple(
        float(first[index])
        + (float(second[index]) - float(first[index])) * float(factor)
        for index in range(3)
    )


def _section_surface_role_points(section):
    lookup = {
        str(getattr(point, "point_id", "") or ""): point
        for point in list(getattr(section, "subassembly_point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "")
    }
    grouped = {}
    for link in list(getattr(section, "subassembly_link_rows", []) or []):
        role = _normal_surface_role(getattr(link, "surface_role", ""))
        if role not in {"design_surface", "slope_face_surface", "drainage_surface"}:
            continue
        role_points = grouped.setdefault(role, {})
        for ref in (
            getattr(link, "start_point_ref", ""),
            getattr(link, "end_point_ref", ""),
        ):
            point = lookup.get(str(ref or ""))
            if point is None:
                continue
            key = tuple(
                round(float(getattr(point, axis, 0.0) or 0.0), 6)
                for axis in ("x", "y", "z")
            )
            role_points[key] = point
    return {
        role: sorted(
            points.values(),
            key=lambda point: (
                float(getattr(point, "lateral_offset", 0.0) or 0.0),
                str(getattr(point, "point_id", "") or ""),
            ),
        )
        for role, points in grouped.items()
    }


def _normal_surface_role(value):
    text = str(value or "").strip().lower()
    if text in {"design", "fg", "fg_surface", "finished_grade", "finished-grade"}:
        return "design_surface"
    if text in {
        "slope_face",
        "side_slope",
        "side-slope",
        "daylight",
        "daylight_surface",
    }:
        return "slope_face_surface"
    if text in {"drainage", "ditch", "gutter"}:
        return "drainage_surface"
    return text


def _consumer_for_surface_role(role):
    return str(role or "")


def _intersection_profile_refs(model, intersection_id):
    if model is None:
        return []
    target = str(intersection_id or "").strip()
    refs = []
    for row in list(getattr(model, "intersection_rows", []) or []):
        if target and str(getattr(row, "intersection_id", "") or "").strip() != target:
            continue
        for leg in list(getattr(row, "leg_rows", []) or []):
            refs.extend(
                (
                    str(getattr(leg, "profile_ref", "") or "").strip(),
                    str(getattr(leg, "grading_policy_ref", "") or "").strip(),
                )
            )
    for row in list(getattr(model, "grading_policy_rows", []) or []):
        if target and str(getattr(row, "intersection_id", "") or "").strip() != target:
            continue
        refs.extend(
            str(getattr(row, attr, "") or "").strip()
            for attr in ("policy_id", "controlling_profile_ref")
        )
    return _unique(refs)


def _tie_slope_window_diagnostic_blocks_surface(value) -> bool:
    text = str(value or "").strip()
    if not text or text.startswith("info:"):
        return False
    return text not in {
        "intersection_tie_slope_supplemental_endpoint_missing",
        "info:intersection_tie_slope_supplemental_endpoint_pending",
    }


def _tie_slope_window_surface_row_enabled(row) -> bool:
    if str(row.get("ownership_class", "") or "").strip().lower() != (
        "tie_slope_candidate"
    ):
        return False
    return not (
        str(row.get("intersection_kind", "") or "").strip().lower()
        == "cross_intersection"
        and str(row.get("cell_role", "") or "").strip().lower()
        == "intersection_adjacent_pair"
    )
