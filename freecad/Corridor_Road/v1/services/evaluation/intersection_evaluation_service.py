"""Intersection evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.source.intersection_model import (
    IntersectionControlArea,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)


@dataclass(frozen=True)
class IntersectionEvaluationResult:
    """Minimal resolved intersection context for a station."""

    station: float
    alignment_ref: str = ""
    active_intersection_id: str = ""
    active_control_area_id: str = ""
    active_leg_id: str = ""
    leg_role: str = ""
    control_region_refs: tuple[str, ...] = ()
    curb_return_policy_ref: str = ""
    turn_lane_policy_ref: str = ""
    grading_policy_ref: str = ""
    drainage_policy_ref: str = ""
    diagnostic_rows: tuple[str, ...] = ()


class IntersectionEvaluationService:
    """Resolve intersection control-area context from an intersection source model."""

    def resolve_station(
        self,
        intersection_model: IntersectionModel,
        station: float | None = None,
        *,
        alignment_ref: str = "",
    ) -> IntersectionEvaluationResult:
        """Resolve active intersection context by station and optional Alignment ref."""

        if station is None:
            raise ValueError("station is required.")

        control_area = self._find_active_control_area(
            intersection_model.control_area_rows,
            station,
            alignment_ref=alignment_ref,
        )
        if control_area is None:
            return IntersectionEvaluationResult(
                station=station,
                alignment_ref=alignment_ref,
                diagnostic_rows=(
                    "intersection_context_not_found_for_alignment_station"
                    if alignment_ref
                    else "intersection_context_not_found_for_station",
                ),
            )

        intersection_row = self._find_intersection_row(intersection_model, control_area.intersection_id)
        leg = self._find_active_leg(intersection_row, alignment_ref, station)

        return IntersectionEvaluationResult(
            station=station,
            alignment_ref=alignment_ref,
            active_intersection_id=control_area.intersection_id,
            active_control_area_id=control_area.control_area_id,
            active_leg_id=leg.leg_id if leg is not None else "",
            leg_role=leg.leg_role if leg is not None else "",
            control_region_refs=tuple(control_area.control_region_refs),
            curb_return_policy_ref=control_area.curb_return_policy_ref,
            turn_lane_policy_ref=control_area.turn_lane_policy_ref,
            grading_policy_ref=control_area.grading_policy_ref,
            drainage_policy_ref=control_area.drainage_policy_ref,
            diagnostic_rows=() if leg is not None or not alignment_ref else ("intersection_leg_not_found_for_alignment_station",),
        )

    @staticmethod
    def _find_active_control_area(
        control_areas: list[IntersectionControlArea],
        station: float,
        *,
        alignment_ref: str = "",
    ) -> IntersectionControlArea | None:
        for row in control_areas:
            if alignment_ref and row.alignment_ref and row.alignment_ref != alignment_ref:
                continue
            for station_start, station_end in row.station_ranges:
                if station_start <= station <= station_end:
                    return row
            for station_start, station_end in row.influence_ranges:
                if station_start <= station <= station_end:
                    return row
        return None

    @staticmethod
    def _find_intersection_row(
        intersection_model: IntersectionModel,
        intersection_id: str,
    ) -> IntersectionRow | None:
        for row in intersection_model.intersection_rows:
            if row.intersection_id == intersection_id:
                return row
        return None

    @staticmethod
    def _find_active_leg(
        intersection_row: IntersectionRow | None,
        alignment_ref: str,
        station: float,
    ) -> IntersectionLegRow | None:
        if intersection_row is None:
            return None
        candidates: list[IntersectionLegRow] = []
        for leg in intersection_row.leg_rows:
            if alignment_ref and leg.alignment_ref and leg.alignment_ref != alignment_ref:
                continue
            if leg.approach_station_start or leg.approach_station_end:
                start = min(leg.approach_station_start, leg.approach_station_end)
                end = max(leg.approach_station_start, leg.approach_station_end)
                if not (start <= station <= end):
                    continue
            candidates.append(leg)
        if not candidates:
            return None
        return sorted(candidates, key=lambda row: (row.priority, row.leg_id))[0]
