"""Evaluate traceable Intersection tie-in edge candidates."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ...models.result.intersection_tie_in_edge import (
    IntersectionTieInEdgeResult,
    IntersectionTieInEdgeRow,
)


@dataclass(frozen=True)
class IntersectionTieInEdgeEvaluationRequest:
    applied_section_set: object
    prerequisite: object
    intersection_model: object | None = None


class IntersectionTieInEdgeEvaluationService:
    """Build tie-in candidates from accepted Applied Section results."""

    def evaluate(
        self,
        request: IntersectionTieInEdgeEvaluationRequest,
    ) -> IntersectionTieInEdgeResult:
        prerequisite = request.prerequisite
        intersection_id = str(
            getattr(prerequisite, "intersection_id", "") or ""
        ).strip()
        sections = _intersection_patch_sections(
            request.applied_section_set,
            prerequisite,
        )
        target_stations = _target_stations_by_alignment(
            request.intersection_model,
            prerequisite,
        )
        grouped: dict[str, list[object]] = {}
        for section in sections:
            alignment_id = str(getattr(section, "alignment_id", "") or "").strip()
            if alignment_id:
                grouped.setdefault(alignment_id, []).append(section)

        edge_rows: list[IntersectionTieInEdgeRow] = []
        diagnostics: list[str] = []
        expected_alignments = [
            str(value or "")
            for value in list(getattr(prerequisite, "alignment_refs", ()) or ())
            if str(value or "").strip()
        ]
        for alignment_id in expected_alignments:
            alignment_sections = sorted(
                grouped.get(alignment_id, []),
                key=_section_station,
            )
            if not alignment_sections:
                diagnostics.append(
                    "intersection_tie_in_edge_missing: no Applied Sections for "
                    f"{alignment_id}."
                )
                continue
            target_station = target_stations.get(alignment_id)
            if target_station is None:
                stations = [
                    float(getattr(row, "station", 0.0) or 0.0)
                    for row in alignment_sections
                ]
                target_station = sum(stations) / len(stations)
            start_section, end_section = _tie_in_section_pair(
                alignment_sections,
                float(target_station),
            )
            for side in ("left", "right"):
                start_point = _tie_in_point(start_section, side)
                end_point = _tie_in_point(end_section, side)
                if start_point is None or end_point is None:
                    diagnostics.append(
                        f"intersection_tie_in_edge_missing: {alignment_id} "
                        f"{side} fg_surface edge is missing."
                    )
                    continue
                start_station = float(
                    getattr(start_section, "station", 0.0) or 0.0
                )
                end_station = float(
                    getattr(end_section, "station", start_station) or start_station
                )
                same_section = str(
                    getattr(start_section, "applied_section_id", "") or ""
                ) == str(
                    getattr(end_section, "applied_section_id", "") or ""
                )
                start_xyz = _point_xyz(start_point)
                end_xyz = _point_xyz(end_point)
                if same_section:
                    synthetic_edge = _single_section_edge(start_section, start_xyz)
                    if synthetic_edge is not None:
                        (
                            start_xyz,
                            end_xyz,
                            start_station,
                            end_station,
                        ) = synthetic_edge
                edge_id = (
                    f"tie-in:{intersection_id}:{_safe_id_fragment(alignment_id)}:"
                    f"{side}"
                )
                if same_section:
                    diagnostics.append(
                        "warning:intersection_tie_in_edge_single_section_candidate: "
                        f"{edge_id} uses one Applied Section; add adjacent section "
                        "rows for a stronger tie-in edge."
                    )
                edge_rows.append(
                    IntersectionTieInEdgeRow(
                        tie_in_edge_id=edge_id,
                        intersection_id=intersection_id,
                        alignment_ref=alignment_id,
                        region_ref=str(
                            getattr(start_section, "region_id", "")
                            or getattr(end_section, "region_id", "")
                            or ""
                        ),
                        side=side,
                        edge_role="pavement_edge",
                        station_start=min(start_station, end_station),
                        station_end=max(start_station, end_station),
                        section_start_ref=str(
                            getattr(start_section, "applied_section_id", "") or ""
                        ),
                        section_end_ref=str(
                            getattr(end_section, "applied_section_id", "") or ""
                        ),
                        start_xyz=start_xyz,
                        end_xyz=end_xyz,
                        status=(
                            "single_section_candidate" if same_section else "candidate"
                        ),
                        notes=f"target_station={float(target_station):.3f}",
                    )
                )

        expected_edge_count = len(expected_alignments) * 2
        if expected_edge_count and len(edge_rows) < expected_edge_count:
            diagnostics.append(
                "intersection_tie_in_edge_incomplete: expected "
                f"{expected_edge_count} left/right edge candidate(s), found "
                f"{len(edge_rows)}."
            )
        status = (
            "ready"
            if edge_rows and not _diagnostics_include_error(diagnostics)
            else ("warning" if edge_rows else "missing")
        )
        return IntersectionTieInEdgeResult(
            schema_version=1,
            project_id=str(
                getattr(request.applied_section_set, "project_id", "") or ""
            ),
            label=f"Intersection Tie-in Edges - {intersection_id}",
            tie_in_edge_result_id=(
                f"intersection-tie-in-edges:{intersection_id or 'unknown'}"
            ),
            intersection_id=intersection_id,
            status=status,
            edge_count=len(edge_rows),
            diagnostic_rows=diagnostics,
            edge_rows=edge_rows,
        )

    def evaluate_context(
        self,
        applied_section_set,
        *,
        prerequisite,
        intersection_model=None,
    ) -> IntersectionTieInEdgeResult:
        """Adapt the boundary-context evaluator signature to the typed request."""

        return self.evaluate(
            IntersectionTieInEdgeEvaluationRequest(
                applied_section_set=applied_section_set,
                prerequisite=prerequisite,
                intersection_model=intersection_model,
            )
        )


def _intersection_patch_sections(applied_section_set, prerequisite) -> list[object]:
    control_refs = {
        str(value or "")
        for value in list(getattr(prerequisite, "control_region_refs", ()) or ())
        if str(value or "")
    }
    intersection_id = str(getattr(prerequisite, "intersection_id", "") or "")
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


def _station_ordered_sections(applied_section_set) -> list[object]:
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


def _section_station(section) -> float:
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


def _target_stations_by_alignment(intersection_model, prerequisite) -> dict[str, float]:
    intersection_id = str(
        getattr(prerequisite, "intersection_id", "") or ""
    ).strip()
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


def _tie_in_section_pair(
    sections: list[object],
    target_station: float,
) -> tuple[object, object]:
    ordered = sorted(
        sections,
        key=lambda row: float(getattr(row, "station", 0.0) or 0.0),
    )
    if not ordered:
        raise ValueError("sections are required")
    tolerance = 1.0e-6
    before = [
        row
        for row in ordered
        if float(getattr(row, "station", 0.0) or 0.0)
        < target_station - tolerance
    ]
    after = [
        row
        for row in ordered
        if float(getattr(row, "station", 0.0) or 0.0)
        > target_station + tolerance
    ]
    exact = [
        row
        for row in ordered
        if abs(float(getattr(row, "station", 0.0) or 0.0) - target_station)
        <= tolerance
    ]
    if before and after:
        start, end = before[-1], after[0]
    elif before and exact:
        start, end = before[-1], exact[-1]
    elif exact and after:
        start, end = exact[0], after[0]
    else:
        start = before[-1] if before else ordered[0]
        end = after[0] if after else ordered[-1]
    if start is end and len(ordered) > 1:
        nearest = sorted(
            [row for row in ordered if row is not start],
            key=lambda row: abs(
                float(getattr(row, "station", 0.0) or 0.0) - target_station
            ),
        )[0]
        if float(getattr(nearest, "station", 0.0) or 0.0) < float(
            getattr(start, "station", 0.0) or 0.0
        ):
            start = nearest
        else:
            end = nearest
    return start, end


def _tie_in_point(section, side: str):
    points = [
        point
        for point in list(getattr(section, "point_rows", []) or [])
        if str(getattr(point, "point_role", "") or "") == "fg_surface"
    ]
    if not points:
        return None
    normalized_side = str(side or "").strip().lower()
    side_matches = [
        point
        for point in points
        if str(getattr(point, "side", "") or "").strip().lower()
        == normalized_side
        or str(getattr(point, "point_id", "") or "")
        .strip()
        .lower()
        .endswith(f":{normalized_side}")
    ]
    if side_matches:
        return side_matches[0]
    if side == "left":
        return max(points, key=_point_lateral_offset)
    return min(points, key=_point_lateral_offset)


def _point_lateral_offset(point) -> float:
    return float(
        getattr(point, "lateral_offset", getattr(point, "offset", 0.0)) or 0.0
    )


def _point_xyz(point) -> tuple[float, float, float]:
    return (
        float(getattr(point, "x", 0.0) or 0.0),
        float(getattr(point, "y", 0.0) or 0.0),
        float(getattr(point, "z", 0.0) or 0.0),
    )


def _single_section_edge(
    section,
    point_xyz: tuple[float, float, float],
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    float,
    float,
] | None:
    frame = getattr(section, "frame", None)
    if frame is None:
        return None
    angle = math.radians(
        float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0)
    )
    direction = (math.cos(angle), math.sin(angle), 0.0)
    if math.sqrt(sum(float(value) ** 2 for value in direction)) <= 1.0e-9:
        return None
    width = abs(float(getattr(section, "surface_left_width", 0.0) or 0.0))
    width += abs(float(getattr(section, "surface_right_width", 0.0) or 0.0))
    half = max(width * 1.5, 8.0) * 0.5
    station = float(getattr(section, "station", 0.0) or 0.0)
    start_xyz = (
        float(point_xyz[0]) - direction[0] * half,
        float(point_xyz[1]) - direction[1] * half,
        float(point_xyz[2]),
    )
    end_xyz = (
        float(point_xyz[0]) + direction[0] * half,
        float(point_xyz[1]) + direction[1] * half,
        float(point_xyz[2]),
    )
    return start_xyz, end_xyz, station - half, station + half


def _diagnostics_include_error(diagnostics) -> bool:
    for value in list(diagnostics or []):
        text = str(value or "").strip().lower()
        if text and not text.startswith("warning:"):
            return True
    return False


def _safe_id_fragment(value: str) -> str:
    text = str(value or "").strip()
    for token in (":", "/", "\\", " ", "|"):
        text = text.replace(token, "-")
    return text.strip("-") or "unknown"
