"""Superelevation auto-calculation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.source.superelevation_model import (
    CrossfallControlRow,
    RunoffTransitionRow,
    SuperelevationConstraint,
    SuperelevationModel,
)


@dataclass(frozen=True)
class SuperelevationCurveCandidate:
    """One alignment curve that can receive generated crossfall controls."""

    curve_id: str
    station_start: float
    station_end: float
    radius: float
    direction: str = "right"
    transition_length: float = 0.0


@dataclass(frozen=True)
class SuperelevationAutoCalculationRequest:
    """Input contract for generated Superelevation source rows."""

    project_id: str
    alignment_id: str
    profile_id: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    design_speed_kph: float = 60.0
    max_superelevation_percent: float = 8.0
    side_friction: float = 0.15
    normal_crossfall_percent: float = -2.0
    min_transition_length: float = 20.0
    curve_candidates: list[SuperelevationCurveCandidate] = field(default_factory=list)


@dataclass(frozen=True)
class SuperelevationAutoCalculationResult:
    """Generated model plus explainable calculation diagnostics."""

    superelevation_model: SuperelevationModel
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


class SuperelevationAutoCalculationService:
    """Generate Superelevation control rows from Alignment curve context."""

    def calculate(self, request: SuperelevationAutoCalculationRequest) -> SuperelevationAutoCalculationResult:
        station_start, station_end = _sorted_range(request.station_start, request.station_end)
        normal = float(request.normal_crossfall_percent)
        max_e = max(float(request.max_superelevation_percent), 0.0)
        design_speed = max(float(request.design_speed_kph), 0.0)
        side_friction = max(float(request.side_friction), 0.0)
        min_transition = max(float(request.min_transition_length), 0.0)
        diagnostics: list[DiagnosticMessage] = []
        controls: list[CrossfallControlRow] = []
        transitions: list[RunoffTransitionRow] = []

        candidates = [
            row
            for row in list(request.curve_candidates or [])
            if float(getattr(row, "radius", 0.0) or 0.0) > 0.0
            and float(getattr(row, "station_end", 0.0) or 0.0) >= float(getattr(row, "station_start", 0.0) or 0.0)
        ]
        if station_end >= station_start:
            controls.extend(
                [
                    _control("control:auto-normal-start-left", station_start, "left", normal, "normal_crown"),
                    _control("control:auto-normal-start-right", station_start, "right", normal, "normal_crown"),
                    _control("control:auto-normal-end-left", station_end, "left", normal, "normal_crown"),
                    _control("control:auto-normal-end-right", station_end, "right", normal, "normal_crown"),
                ]
            )
        if not candidates:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "no_alignment_curve_candidates",
                    "No usable Alignment curve candidates were found; normal crossfall rows were generated only.",
                )
            )

        for index, candidate in enumerate(candidates, start=1):
            curve_start, curve_end = _sorted_range(candidate.station_start, candidate.station_end)
            curve_start = _clamp(curve_start, station_start, station_end)
            curve_end = _clamp(curve_end, station_start, station_end)
            curve_length = max(curve_end - curve_start, 0.0)
            if curve_length <= 0.0:
                diagnostics.append(
                    DiagnosticMessage(
                        "warning",
                        "zero_length_curve_candidate",
                        "Curve candidate has no usable station length after clamping.",
                        notes=str(candidate.curve_id),
                    )
                )
                continue
            target_e = _target_superelevation_percent(
                design_speed_kph=design_speed,
                radius=float(candidate.radius),
                side_friction=side_friction,
                max_superelevation_percent=max_e,
            )
            requested_transition = float(candidate.transition_length or 0.0) if candidate.transition_length else min_transition
            transition_length = max(requested_transition, min_transition)
            max_transition = max(curve_length * 0.45, 0.0)
            if max_transition > 0.0 and transition_length > max_transition:
                diagnostics.append(
                    DiagnosticMessage(
                        "warning",
                        "transition_length_clamped_to_curve",
                        "Generated transition length was clamped to fit inside the curve candidate.",
                        notes=f"{candidate.curve_id}: requested={transition_length:g}; clamped={max_transition:g}",
                    )
                )
                transition_length = max_transition
            full_start = min(curve_start + transition_length, curve_end)
            full_end = max(curve_end - transition_length, full_start)
            left_full, right_full = _full_super_crossfalls(candidate.direction, normal, target_e)
            prefix = f"auto-curve-{index:02d}"
            controls.extend(
                [
                    _control(f"control:{prefix}-normal-in-left", curve_start, "left", normal, "normal_crown"),
                    _control(f"control:{prefix}-normal-in-right", curve_start, "right", normal, "normal_crown"),
                    _control(f"control:{prefix}-full-left", full_start, "left", left_full, "full_super"),
                    _control(f"control:{prefix}-full-right", full_start, "right", right_full, "full_super"),
                    _control(f"control:{prefix}-hold-left", full_end, "left", left_full, "full_super"),
                    _control(f"control:{prefix}-hold-right", full_end, "right", right_full, "full_super"),
                    _control(f"control:{prefix}-normal-out-left", curve_end, "left", normal, "rotation_end"),
                    _control(f"control:{prefix}-normal-out-right", curve_end, "right", normal, "rotation_end"),
                ]
            )
            if full_start > curve_start:
                transitions.append(_transition(f"transition:{prefix}-runoff-in", curve_start, full_start, "runoff"))
            if curve_end > full_end:
                transitions.append(_transition(f"transition:{prefix}-runoff-out", full_end, curve_end, "runoff"))

        model = SuperelevationModel(
            schema_version=1,
            project_id=str(request.project_id or "corridorroad-v1"),
            label="Superelevation",
            superelevation_id="superelevation:main",
            alignment_id=str(request.alignment_id or ""),
            profile_id=str(request.profile_id or ""),
            superelevation_kind="roadway_superelevation",
            control_rows=_dedupe_controls(controls),
            transition_rows=transitions,
            constraint_rows=[
                SuperelevationConstraint("constraint:auto-design-speed", "design_speed", design_speed, "km/h", "soft"),
                SuperelevationConstraint("constraint:auto-max-super", "max_superelevation_rate", max_e, "percent", "soft"),
                SuperelevationConstraint("constraint:auto-side-friction", "side_friction", side_friction, "", "soft"),
                SuperelevationConstraint("constraint:auto-min-transition", "min_transition_length", min_transition, "m", "soft"),
            ],
        )
        return SuperelevationAutoCalculationResult(superelevation_model=model, diagnostic_rows=diagnostics)


def _target_superelevation_percent(
    *,
    design_speed_kph: float,
    radius: float,
    side_friction: float,
    max_superelevation_percent: float,
) -> float:
    if radius <= 0.0:
        return 0.0
    required_rate = (float(design_speed_kph) ** 2.0) / (127.0 * float(radius)) - float(side_friction)
    return _clamp(required_rate * 100.0, 0.0, float(max_superelevation_percent))


def _full_super_crossfalls(direction: str, normal_crossfall: float, target_e: float) -> tuple[float, float]:
    target = max(float(target_e), abs(float(normal_crossfall)))
    side = str(direction or "right").strip().lower()
    if side == "left":
        return -target, target
    return target, -target


def _control(control_id: str, station: float, side: str, crossfall: float, kind: str) -> CrossfallControlRow:
    return CrossfallControlRow(
        control_row_id=control_id,
        station=float(station),
        side=side,
        crossfall_value=float(crossfall),
        crossfall_unit="percent",
        kind=kind,
    )


def _transition(transition_id: str, start: float, end: float, kind: str) -> RunoffTransitionRow:
    return RunoffTransitionRow(
        transition_id=transition_id,
        station_start=float(start),
        station_end=float(end),
        kind=kind,
        transition_policy="linear",
    )


def _dedupe_controls(rows: list[CrossfallControlRow]) -> list[CrossfallControlRow]:
    output: list[CrossfallControlRow] = []
    used_ids: set[str] = set()
    for row in sorted(rows, key=lambda item: (float(item.station), str(item.side), str(item.control_row_id))):
        control_id = str(row.control_row_id or "")
        if control_id in used_ids:
            control_id = f"{control_id}-{len(used_ids) + 1}"
            row = CrossfallControlRow(control_id, row.station, row.side, row.crossfall_value, row.crossfall_unit, row.kind)
        used_ids.add(control_id)
        output.append(row)
    return output


def _sorted_range(start: float, end: float) -> tuple[float, float]:
    first = float(start)
    second = float(end)
    if second < first:
        return second, first
    return first, second


def _clamp(value: float, lower: float, upper: float) -> float:
    if upper < lower:
        lower, upper = upper, lower
    return min(max(float(value), float(lower)), float(upper))
