"""Prepare accepted result inputs for non-roundabout Intersection patches."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.intersection_patch_input import (
    IntersectionPatchInputPreparationResult,
    IntersectionPatchSuperelevationContext,
)
from ...models.result.tin_surface import TINVertex


@dataclass(frozen=True)
class IntersectionPatchInputPreparationRequest:
    applied_section_set: object
    prerequisite: object
    intersection_model: object | None = None


class IntersectionPatchInputPreparationService:
    """Select center sections and build traceable, unique FG vertices."""

    def prepare(
        self,
        request: IntersectionPatchInputPreparationRequest,
    ) -> IntersectionPatchInputPreparationResult:
        prerequisite = request.prerequisite
        intersection_id = str(
            getattr(prerequisite, "intersection_id", "") or ""
        )
        control_refs = tuple(
            sorted(
                {
                    str(value or "")
                    for value in list(
                        getattr(prerequisite, "control_region_refs", ()) or ()
                    )
                    if str(value or "")
                }
            )
        )
        sections = _patch_sections(
            request.applied_section_set,
            intersection_id=intersection_id,
            control_refs=set(control_refs),
        )
        sections = _center_sections(
            sections,
            intersection_model=request.intersection_model,
            intersection_id=intersection_id,
        )
        context = _superelevation_context(sections)
        vertices: list[TINVertex] = []
        seen_xy: set[tuple[float, float]] = set()
        duplicate_count = 0
        for section in sections:
            alignment_id = str(getattr(section, "alignment_id", "") or "")
            station = float(getattr(section, "station", 0.0) or 0.0)
            for point_index, point in enumerate(
                list(getattr(section, "point_rows", []) or []),
                start=1,
            ):
                if str(getattr(point, "point_role", "") or "") != "fg_surface":
                    continue
                x = float(getattr(point, "x", 0.0) or 0.0)
                y = float(getattr(point, "y", 0.0) or 0.0)
                z = float(getattr(point, "z", 0.0) or 0.0)
                key = (round(x, 6), round(y, 6))
                if key in seen_xy:
                    duplicate_count += 1
                    continue
                seen_xy.add(key)
                vertices.append(
                    TINVertex(
                        vertex_id=f"v{len(vertices) + 1}",
                        x=x,
                        y=y,
                        z=z,
                        source_point_ref=(
                            f"{getattr(section, 'applied_section_id', '')}:"
                            f"fg:{point_index}"
                        ),
                        notes=(
                            f"alignment={alignment_id}; station={station:.3f}; "
                            f"region={getattr(section, 'region_id', '')}"
                        ),
                    )
                )
        if len(vertices) < 3:
            message = (
                "intersection_patch_boundary_too_few_points: at least three "
                "unique fg_surface points are required."
            )
            return IntersectionPatchInputPreparationResult(
                status="error",
                intersection_id=intersection_id,
                control_region_refs=control_refs,
                section_rows=tuple(sections),
                vertex_rows=tuple(vertices),
                duplicate_xy_count=duplicate_count,
                superelevation_context=context,
                diagnostic_rows=("intersection_patch_boundary_too_few_points",),
                error_message=message,
            )
        return IntersectionPatchInputPreparationResult(
            status="ready",
            intersection_id=intersection_id,
            control_region_refs=control_refs,
            section_rows=tuple(sections),
            vertex_rows=tuple(vertices),
            duplicate_xy_count=duplicate_count,
            superelevation_context=context,
        )


def _patch_sections(
    applied_section_set: object,
    *,
    intersection_id: str,
    control_refs: set[str],
) -> list[object]:
    return [
        section
        for section in _station_ordered_sections(applied_section_set)
        if (
            intersection_id
            and str(getattr(section, "active_intersection_id", "") or "")
            == intersection_id
        )
        or str(getattr(section, "region_id", "") or "") in control_refs
    ]


def _center_sections(
    sections: list[object],
    *,
    intersection_model: object | None,
    intersection_id: str,
) -> list[object]:
    if not sections:
        return []
    targets = _target_stations(intersection_model, intersection_id)
    grouped: dict[str, list[object]] = {}
    for section in sections:
        grouped.setdefault(
            str(getattr(section, "alignment_id", "") or ""),
            [],
        ).append(section)
    output: list[object] = []
    for alignment_id, rows in grouped.items():
        if len(rows) <= 1:
            output.extend(rows)
            continue
        target = targets.get(alignment_id)
        if target is None:
            stations = [float(getattr(row, "station", 0.0) or 0.0) for row in rows]
            target = sum(stations) / len(stations)
        output.append(
            min(
                rows,
                key=lambda row: abs(
                    float(getattr(row, "station", 0.0) or 0.0) - float(target)
                ),
            )
        )
    return sorted(output, key=_section_station)


def _target_stations(
    intersection_model: object | None,
    intersection_id: str,
) -> dict[str, float]:
    output: dict[str, float] = {}
    if intersection_model is None:
        return output
    source_row = next(
        (
            row
            for row in list(getattr(intersection_model, "intersection_rows", []) or [])
            if not intersection_id
            or str(getattr(row, "intersection_id", "") or "") == intersection_id
        ),
        None,
    )
    if source_row is not None:
        primary_ref = str(
            getattr(source_row, "primary_alignment_ref", "") or ""
        ).strip()
        if primary_ref:
            output[primary_ref] = float(
                getattr(source_row, "primary_station", 0.0) or 0.0
            )
        for alignment_ref, station in dict(
            getattr(source_row, "secondary_station_refs", {}) or {}
        ).items():
            alignment_id = str(alignment_ref or "").strip()
            if alignment_id:
                output[alignment_id] = float(station or 0.0)
    for area in list(getattr(intersection_model, "control_area_rows", []) or []):
        if intersection_id and str(
            getattr(area, "intersection_id", "") or ""
        ) != intersection_id:
            continue
        alignment_id = str(getattr(area, "alignment_ref", "") or "").strip()
        if not alignment_id or alignment_id in output:
            continue
        centers = []
        for station_start, station_end in list(
            getattr(area, "station_ranges", []) or []
        ):
            try:
                centers.append((float(station_start) + float(station_end)) / 2.0)
            except Exception:
                continue
        if centers:
            output[alignment_id] = sum(centers) / len(centers)
    return output


def _station_ordered_sections(applied_section_set: object) -> list[object]:
    sections = {
        str(getattr(section, "applied_section_id", "") or ""): section
        for section in list(getattr(applied_section_set, "sections", []) or [])
    }
    output = []
    for row in sorted(
        list(getattr(applied_section_set, "station_rows", []) or []),
        key=lambda item: float(getattr(item, "station", 0.0) or 0.0),
    ):
        section = sections.get(str(getattr(row, "applied_section_id", "") or ""))
        if section is not None:
            output.append(section)
    return output or sorted(sections.values(), key=_section_station)


def _section_station(section: object) -> float:
    frame = getattr(section, "frame", None)
    try:
        return float(
            getattr(frame, "station", getattr(section, "station", 0.0)) or 0.0
        )
    except Exception:
        try:
            return float(getattr(section, "station", 0.0) or 0.0)
        except Exception:
            return 0.0


def _superelevation_context(
    sections: list[object],
) -> IntersectionPatchSuperelevationContext:
    source_refs = {
        str(getattr(section, "active_superelevation_id", "") or "").strip()
        for section in sections
        if str(getattr(section, "active_superelevation_id", "") or "").strip()
    }
    transition_refs = {
        str(
            getattr(section, "active_superelevation_transition_id", "") or ""
        ).strip()
        for section in sections
        if str(
            getattr(section, "active_superelevation_transition_id", "") or ""
        ).strip()
    }
    left = [
        float(getattr(section, "superelevation_left_crossfall", 0.0) or 0.0)
        for section in sections
    ]
    right = [
        float(getattr(section, "superelevation_right_crossfall", 0.0) or 0.0)
        for section in sections
    ]
    left_min, left_max = (min(left), max(left)) if left else (0.0, 0.0)
    right_min, right_max = (min(right), max(right)) if right else (0.0, 0.0)
    summary = (
        f"sources={len(source_refs)}; transitions={len(transition_refs)}; "
        f"L {left_min:.3f}%..{left_max:.3f}%; "
        f"R {right_min:.3f}%..{right_max:.3f}%"
        if source_refs
        else "sources=0; uses Applied Section default crossfall context"
    )
    return IntersectionPatchSuperelevationContext(
        source_count=len(source_refs),
        transition_count=len(transition_refs),
        left_min=left_min,
        left_max=left_max,
        right_min=right_min,
        right_max=right_max,
        summary=summary,
    )
