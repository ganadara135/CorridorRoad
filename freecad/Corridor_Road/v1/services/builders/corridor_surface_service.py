"""Corridor surface builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.surface_transition_model import SurfaceTransitionModel, SurfaceTransitionRange
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.surface_model import (
    SurfaceBuildRelation,
    SurfaceModel,
    SurfaceRow,
    SurfaceSpanRow,
)


@dataclass(frozen=True)
class CorridorSurfaceBuildRequest:
    """Input bundle used to build minimal corridor-derived surfaces."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    surface_model_id: str
    surface_transition_model: SurfaceTransitionModel | None = None


class CorridorSurfaceService:
    """Build minimal corridor-derived surface families from corridor results."""

    def build(self, request: CorridorSurfaceBuildRequest) -> SurfaceModel:
        """Build a minimal grouped surface result family for a corridor."""

        if request.applied_section_set.station_rows:
            status = "ready"
        else:
            status = "empty"

        design_surface_id = f"{request.corridor.corridor_id}:design"
        subgrade_surface_id = f"{request.corridor.corridor_id}:subgrade"
        daylight_surface_id = f"{request.corridor.corridor_id}:daylight"
        drainage_surface_id = f"{request.corridor.corridor_id}:drainage"

        surface_rows = [
            SurfaceRow(
                surface_id=design_surface_id,
                surface_kind="design_surface",
                tin_ref=f"{design_surface_id}:tin",
                status=status,
            ),
            SurfaceRow(
                surface_id=subgrade_surface_id,
                surface_kind="subgrade_surface",
                tin_ref=f"{subgrade_surface_id}:tin",
                status=status,
                parent_surface_ref=design_surface_id,
            ),
            SurfaceRow(
                surface_id=daylight_surface_id,
                surface_kind="daylight_surface",
                tin_ref=f"{daylight_surface_id}:tin",
                status=status,
                parent_surface_ref=design_surface_id,
            ),
        ]
        if _has_point_role(request.applied_section_set, "ditch_surface"):
            surface_rows.append(
                SurfaceRow(
                    surface_id=drainage_surface_id,
                    surface_kind="drainage_surface",
                    tin_ref=f"{drainage_surface_id}:tin",
                    status=status,
                    parent_surface_ref=design_surface_id,
                )
            )

        build_relation_rows = [
            SurfaceBuildRelation(
                build_relation_id=f"{request.surface_model_id}:design-build",
                surface_ref=design_surface_id,
                relation_kind="corridor_build",
                input_refs=[
                    request.corridor.corridor_id,
                    request.applied_section_set.applied_section_set_id,
                ],
                operation_summary="Built from applied section set skeleton.",
            ),
            SurfaceBuildRelation(
                build_relation_id=f"{request.surface_model_id}:subgrade-build",
                surface_ref=subgrade_surface_id,
                relation_kind="corridor_build",
                input_refs=[design_surface_id],
                operation_summary="Derived as child surface of design surface skeleton.",
            ),
            SurfaceBuildRelation(
                build_relation_id=f"{request.surface_model_id}:daylight-build",
                surface_ref=daylight_surface_id,
                relation_kind="corridor_build",
                input_refs=[design_surface_id],
                operation_summary="Derived as child surface of design surface skeleton.",
            ),
        ]
        if _has_point_role(request.applied_section_set, "ditch_surface"):
            build_relation_rows.append(
                SurfaceBuildRelation(
                    build_relation_id=f"{request.surface_model_id}:drainage-build",
                    surface_ref=drainage_surface_id,
                    relation_kind="corridor_build",
                    input_refs=[
                        request.corridor.corridor_id,
                        request.applied_section_set.applied_section_set_id,
                    ],
                    operation_summary="Built from AppliedSection ditch_surface point rows.",
                )
            )
        span_rows = _build_surface_span_rows(
            request.applied_section_set,
            surface_rows=surface_rows,
            surface_transition_model=request.surface_transition_model,
        )

        source_refs = [
            request.corridor.corridor_id,
            request.applied_section_set.applied_section_set_id,
        ]
        transition_model_id = str(getattr(request.surface_transition_model, "transition_model_id", "") or "")
        if transition_model_id:
            source_refs.append(transition_model_id)

        return SurfaceModel(
            schema_version=1,
            project_id=request.project_id,
            surface_model_id=request.surface_model_id,
            corridor_id=request.corridor.corridor_id,
            label=f"Surfaces for {request.corridor.corridor_id}",
            source_refs=source_refs,
            surface_rows=surface_rows,
            build_relation_rows=build_relation_rows,
            comparison_rows=[],
            span_rows=span_rows,
        )


def _has_point_role(applied_section_set: AppliedSectionSet, point_role: str) -> bool:
    for section in list(getattr(applied_section_set, "sections", []) or []):
        for point in list(getattr(section, "point_rows", []) or []):
            if str(getattr(point, "point_role", "") or "") == point_role:
                return True
    return False


def _build_surface_span_rows(
    applied_section_set: AppliedSectionSet,
    *,
    surface_rows: list[SurfaceRow],
    surface_transition_model: SurfaceTransitionModel | None = None,
) -> list[SurfaceSpanRow]:
    sections = _station_ordered_sections(applied_section_set)
    if len(sections) < 2:
        return []
    output: list[SurfaceSpanRow] = []
    for surface_row in list(surface_rows or []):
        surface_ref = str(getattr(surface_row, "surface_id", "") or "")
        surface_kind = str(getattr(surface_row, "surface_kind", "") or "")
        for index in range(len(sections) - 1):
            left = sections[index]
            right = sections[index + 1]
            station_start = _section_station(left)
            station_end = _section_station(right)
            left_region = _section_region_id(left)
            right_region = _section_region_id(right)
            span_kind = "region_boundary" if left_region != right_region else "same_region"
            diagnostics = _surface_span_diagnostic_refs(left, right)
            transition = _matching_surface_transition(
                surface_transition_model,
                station_start=min(station_start, station_end),
                station_end=max(station_start, station_end),
                from_region_ref=left_region,
                to_region_ref=right_region,
                surface_kind=surface_kind,
            )
            transition_ref = str(getattr(transition, "transition_id", "") or "") if transition is not None else ""
            if transition_ref and "surface_transition_applied" not in diagnostics:
                diagnostics.append("surface_transition_applied")
            continuity_status = _surface_span_continuity_status(
                span_kind=span_kind,
                diagnostics=diagnostics,
                transition=transition,
            )
            notes = _surface_span_notes(left, right, diagnostics=diagnostics, transition=transition)
            output.append(
                SurfaceSpanRow(
                    span_id=f"{surface_ref}:span:{index + 1}",
                    surface_ref=surface_ref,
                    station_start=min(station_start, station_end),
                    station_end=max(station_start, station_end),
                    from_region_ref=left_region,
                    to_region_ref=right_region,
                    span_kind=span_kind,
                    transition_ref=transition_ref,
                    continuity_status=continuity_status,
                    diagnostic_refs=diagnostics,
                    notes=f"{surface_kind}: {notes}",
                )
            )
    return output


def _station_ordered_sections(applied_section_set: AppliedSectionSet) -> list[object]:
    section_by_id = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    output: list[object] = []
    for row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda item: float(getattr(item, "station", 0.0) or 0.0),
    ):
        section = section_by_id.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None:
            output.append(section)
    if output:
        return output
    return sorted(list(getattr(applied_section_set, "sections", []) or []), key=_section_station)


def _section_station(section) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0)
    except Exception:
        try:
            return float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            return 0.0


def _section_region_id(section) -> str:
    return str(getattr(section, "region_id", "") or "(unassigned)")


def _surface_span_diagnostic_refs(left, right) -> list[str]:
    diagnostics: list[str] = []
    if _section_region_id(left) != _section_region_id(right):
        diagnostics.append("region_context_change")
    if _section_text(left, "assembly_id") != _section_text(right, "assembly_id"):
        diagnostics.append("assembly_context_change")
    if _section_text(left, "template_id") != _section_text(right, "template_id"):
        diagnostics.append("template_context_change")
    if _structure_refs(left) != _structure_refs(right):
        diagnostics.append("structure_context_change")
    if _surface_point_role_counts(left) != _surface_point_role_counts(right):
        diagnostics.append("surface_point_role_mismatch")
    return diagnostics


def _surface_span_notes(left, right, *, diagnostics: list[str], transition: SurfaceTransitionRange | None = None) -> str:
    if not diagnostics:
        return "same Region span."
    text = (
        f"{_section_region_id(left)} -> {_section_region_id(right)}; "
        f"diagnostics={', '.join(diagnostics)}"
    )
    if transition is not None:
        text += f"; transition={getattr(transition, 'transition_id', '')}"
    return text


def _matching_surface_transition(
    surface_transition_model: SurfaceTransitionModel | None,
    *,
    station_start: float,
    station_end: float,
    from_region_ref: str,
    to_region_ref: str,
    surface_kind: str,
) -> SurfaceTransitionRange | None:
    if surface_transition_model is None:
        return None
    candidates: list[SurfaceTransitionRange] = []
    boundary_station = float(station_start)
    for row in list(getattr(surface_transition_model, "transition_ranges", []) or []):
        if not bool(getattr(row, "enabled", True)):
            continue
        if str(getattr(row, "approval_status", "") or "") == "disabled":
            continue
        if surface_kind not in list(getattr(row, "target_surface_kinds", []) or []):
            continue
        row_from = str(getattr(row, "from_region_ref", "") or "")
        row_to = str(getattr(row, "to_region_ref", "") or "")
        if (row_from, row_to) != (from_region_ref, to_region_ref) and (row_from, row_to) != (to_region_ref, from_region_ref):
            continue
        try:
            row_start = float(getattr(row, "station_start", 0.0) or 0.0)
            row_end = float(getattr(row, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        if row_start > row_end:
            row_start, row_end = row_end, row_start
        if not _ranges_overlap(station_start, station_end, row_start, row_end):
            continue
        if row_start <= boundary_station <= row_end:
            candidates.insert(0, row)
        else:
            candidates.append(row)
    return candidates[0] if candidates else None


def _surface_span_continuity_status(
    *,
    span_kind: str,
    diagnostics: list[str],
    transition: SurfaceTransitionRange | None,
) -> str:
    if transition is not None:
        status = str(getattr(transition, "approval_status", "") or "")
        if status in {"active", "approved"}:
            return "transition_applied"
        return "transition_draft"
    return "needs_review" if diagnostics or span_kind == "region_boundary" else "ok"


def _ranges_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> bool:
    return max(float(left_start), float(right_start)) <= min(float(left_end), float(right_end))


def _section_text(section, attr: str) -> str:
    return str(getattr(section, attr, "") or "").strip()


def _structure_refs(section) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(value or "").strip()
            for value in list(getattr(section, "active_structure_ids", []) or [])
            if str(value or "").strip()
        )
    )


def _surface_point_role_counts(section) -> dict[str, int]:
    roles = {"fg_surface", "subgrade_surface", "ditch_surface", "side_slope_surface", "bench_surface", "daylight_marker"}
    counts = {role: 0 for role in roles}
    for point in list(getattr(section, "point_rows", []) or []):
        role = str(getattr(point, "point_role", "") or "")
        if role in counts:
            counts[role] += 1
    return {role: count for role, count in counts.items() if count}
