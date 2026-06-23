"""Superelevation evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from ...common.diagnostics import DiagnosticMessage
from ...models.source.superelevation_model import (
    CrossfallControlRow,
    RunoffTransitionRow,
    SuperelevationModel,
)


VALID_SIDES = {"left", "right", "both", "center"}
DEFAULT_HIGH_CROSSFALL_WARNING_PERCENT = 12.0
STATION_RANGE_TOLERANCE = 1.0e-3


@dataclass(frozen=True)
class SuperelevationValidationResult:
    """Validation result for a SuperelevationModel."""

    status: str
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


@dataclass(frozen=True)
class SuperelevationStationResult:
    """Resolved superelevation state at one station."""

    station: float
    left_crossfall: float = 0.0
    right_crossfall: float = 0.0
    active_control_ids: list[str] = field(default_factory=list)
    active_transition_id: str = ""
    left_source: str = ""
    right_source: str = ""
    status: str = "ok"
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


class SuperelevationValidationService:
    """Validate v1 superelevation source rows without mutating them."""

    def validate(
        self,
        superelevation_model: SuperelevationModel,
        *,
        station_range: tuple[float, float] | None = None,
    ) -> SuperelevationValidationResult:
        diagnostics: list[DiagnosticMessage] = []
        controls = list(getattr(superelevation_model, "control_rows", []) or [])
        transitions = list(getattr(superelevation_model, "transition_rows", []) or [])
        constraints = list(getattr(superelevation_model, "constraint_rows", []) or [])

        if not str(getattr(superelevation_model, "alignment_id", "") or "").strip():
            diagnostics.append(_diagnostic("error", "missing_alignment_id", "SuperelevationModel must reference an Alignment."))

        range_start, range_end = _normalized_station_range(station_range)
        min_transition_length = _constraint_float(constraints, "min_transition_length", 0.0)
        max_crossfall = _constraint_float(constraints, "max_superelevation_rate", DEFAULT_HIGH_CROSSFALL_WARNING_PERCENT)

        seen_control_ids: set[str] = set()
        seen_station_side: set[tuple[float, str]] = set()
        for index, row in enumerate(controls, start=1):
            control_id = str(getattr(row, "control_row_id", "") or "").strip()
            source_ref = control_id or f"control-row:{index}"
            if not control_id:
                diagnostics.append(_diagnostic("error", "missing_control_row_id", "Control row id is required.", notes=source_ref))
            elif control_id in seen_control_ids:
                diagnostics.append(_diagnostic("error", "duplicate_control_row_id", f"Duplicate control row id: {control_id}.", notes=source_ref))
            seen_control_ids.add(control_id)

            side = _side(row)
            if side not in VALID_SIDES:
                diagnostics.append(_diagnostic("error", "invalid_control_side", f"Control row side is not supported: {side}.", notes=source_ref))
            station = _finite_float(getattr(row, "station", None))
            if station is None:
                diagnostics.append(_diagnostic("error", "invalid_control_station", "Control row station must be numeric.", notes=source_ref))
            elif range_start is not None and not _in_range(station, range_start, range_end):
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "control_station_outside_station_range",
                        f"Control station {station:g} is outside available station range {range_start:g}-{range_end:g}.",
                        notes=source_ref,
                    )
                )
            crossfall = _finite_float(getattr(row, "crossfall_value", None))
            if crossfall is None:
                diagnostics.append(_diagnostic("error", "invalid_crossfall_value", "Control row crossfall must be numeric.", notes=source_ref))
            elif abs(crossfall) > max_crossfall:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "high_crossfall_value",
                        f"Control row crossfall {crossfall:g}% exceeds warning limit {max_crossfall:g}%.",
                        notes=source_ref,
                    )
                )
            if station is not None:
                duplicate_key = (round(station, 9), side)
                if duplicate_key in seen_station_side:
                    diagnostics.append(
                        _diagnostic(
                            "warning",
                            "duplicate_station_side_control",
                            f"Multiple control rows share station {station:g} and side {side}.",
                            notes=source_ref,
                        )
                    )
                seen_station_side.add(duplicate_key)

        seen_transition_ids: set[str] = set()
        for index, row in enumerate(transitions, start=1):
            transition_id = str(getattr(row, "transition_id", "") or "").strip()
            source_ref = transition_id or f"transition-row:{index}"
            if not transition_id:
                diagnostics.append(_diagnostic("error", "missing_transition_id", "Transition row id is required.", notes=source_ref))
            elif transition_id in seen_transition_ids:
                diagnostics.append(_diagnostic("error", "duplicate_transition_id", f"Duplicate transition id: {transition_id}.", notes=source_ref))
            seen_transition_ids.add(transition_id)

            start = _finite_float(getattr(row, "station_start", None))
            end = _finite_float(getattr(row, "station_end", None))
            if start is None or end is None:
                diagnostics.append(_diagnostic("error", "invalid_transition_station", "Transition start/end must be numeric.", notes=source_ref))
                continue
            if end < start:
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "invalid_transition_station_range",
                        f"Transition end must be greater than or equal to start: {start:g}-{end:g}.",
                        notes=source_ref,
                    )
                )
            if range_start is not None and (not _in_range(start, range_start, range_end) or not _in_range(end, range_start, range_end)):
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "transition_outside_station_range",
                        f"Transition {start:g}-{end:g} is outside available station range {range_start:g}-{range_end:g}.",
                        notes=source_ref,
                    )
                )
            if min_transition_length > 0.0 and end >= start and (end - start) + STATION_RANGE_TOLERANCE < min_transition_length:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "transition_shorter_than_minimum",
                        f"Transition length {end - start:g} is shorter than minimum {min_transition_length:g}.",
                        notes=source_ref,
                    )
                )
            policy = str(getattr(row, "transition_policy", "") or "linear").strip().lower()
            if policy and policy != "linear":
                diagnostics.append(_diagnostic("warning", "unsupported_transition_policy", f"Transition policy will be treated as linear: {policy}.", notes=source_ref))

        if controls and range_start is not None:
            control_stations = [_finite_float(getattr(row, "station", None)) for row in controls]
            valid_stations = [value for value in control_stations if value is not None]
            if valid_stations:
                if min(valid_stations) > range_start or max(valid_stations) < range_end:
                    diagnostics.append(
                        _diagnostic(
                            "warning",
                            "incomplete_station_coverage",
                            "Superelevation controls do not cover the full available station range.",
                            notes=f"controls={min(valid_stations):g}-{max(valid_stations):g}; range={range_start:g}-{range_end:g}",
                        )
                    )

        status = "error" if any(row.severity == "error" for row in diagnostics) else "warning" if any(row.severity == "warning" for row in diagnostics) else "ok"
        return SuperelevationValidationResult(status=status, diagnostic_rows=diagnostics)


class SuperelevationService:
    """Resolve station-based crossfall behavior from a SuperelevationModel."""

    def __init__(self, *, validation_service: SuperelevationValidationService | None = None) -> None:
        self.validation_service = validation_service or SuperelevationValidationService()

    def validate(
        self,
        superelevation_model: SuperelevationModel,
        *,
        station_range: tuple[float, float] | None = None,
    ) -> SuperelevationValidationResult:
        """Validate a SuperelevationModel using the shared validation service."""

        return self.validation_service.validate(superelevation_model, station_range=station_range)

    def evaluate_station(
        self,
        superelevation_model: SuperelevationModel | None,
        station: float,
        *,
        default_left_crossfall: float = 0.0,
        default_right_crossfall: float = 0.0,
    ) -> SuperelevationStationResult:
        """Evaluate effective left/right crossfall at one station."""

        station_value = float(station)
        if superelevation_model is None:
            return SuperelevationStationResult(
                station=station_value,
                left_crossfall=float(default_left_crossfall),
                right_crossfall=float(default_right_crossfall),
                status="fallback",
                diagnostic_rows=[
                    _diagnostic(
                        "warning",
                        "missing_superelevation_model",
                        "No SuperelevationModel is available; Assembly default slopes were used.",
                    )
                ],
            )
        controls = _sorted_controls(getattr(superelevation_model, "control_rows", []) or [])
        if not controls:
            return SuperelevationStationResult(
                station=station_value,
                left_crossfall=float(default_left_crossfall),
                right_crossfall=float(default_right_crossfall),
                status="fallback",
                diagnostic_rows=[
                    _diagnostic(
                        "warning",
                        "empty_superelevation_controls",
                        "SuperelevationModel has no control rows; Assembly default slopes were used.",
                    )
                ],
            )

        active_transition = _active_transition(getattr(superelevation_model, "transition_rows", []) or [], station_value)
        left_value, left_source = self._evaluate_side(
            controls,
            station_value,
            side="left",
            default_value=float(default_left_crossfall),
            active_transition=active_transition,
        )
        right_value, right_source = self._evaluate_side(
            controls,
            station_value,
            side="right",
            default_value=float(default_right_crossfall),
            active_transition=active_transition,
        )
        active_ids = _unique_nonempty([left_source, right_source])
        diagnostics: list[DiagnosticMessage] = []
        status = "ok"
        if not left_source or not right_source:
            status = "fallback"
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "superelevation_side_fallback",
                    "At least one side used Assembly default crossfall because no active Superelevation control was found.",
                    notes=f"left_source={left_source or '-'}; right_source={right_source or '-'}",
                )
            )

        return SuperelevationStationResult(
            station=station_value,
            left_crossfall=float(left_value),
            right_crossfall=float(right_value),
            active_control_ids=active_ids,
            active_transition_id="" if active_transition is None else str(getattr(active_transition, "transition_id", "") or ""),
            left_source=left_source,
            right_source=right_source,
            status=status,
            diagnostic_rows=diagnostics,
        )

    def sample_stations(
        self,
        superelevation_model: SuperelevationModel | None,
        stations: list[float],
        *,
        default_left_crossfall: float = 0.0,
        default_right_crossfall: float = 0.0,
    ) -> list[SuperelevationStationResult]:
        """Evaluate multiple stations in station order."""

        return [
            self.evaluate_station(
                superelevation_model,
                float(station),
                default_left_crossfall=default_left_crossfall,
                default_right_crossfall=default_right_crossfall,
            )
            for station in sorted(float(value) for value in list(stations or []))
        ]

    def _evaluate_side(
        self,
        controls: list[CrossfallControlRow],
        station: float,
        *,
        side: str,
        default_value: float,
        active_transition: RunoffTransitionRow | None,
    ) -> tuple[float, str]:
        if active_transition is not None:
            blended = _transition_value(
                controls,
                station,
                side=side,
                default_value=default_value,
                transition=active_transition,
            )
            if blended is not None:
                return blended
        control = _active_control(controls, station, side=side)
        if control is None:
            return float(default_value), ""
        return float(getattr(control, "crossfall_value", 0.0) or 0.0), str(getattr(control, "control_row_id", "") or "")


def _transition_value(
    controls: list[CrossfallControlRow],
    station: float,
    *,
    side: str,
    default_value: float,
    transition: RunoffTransitionRow,
) -> tuple[float, str] | None:
    start = float(getattr(transition, "station_start", 0.0) or 0.0)
    end = float(getattr(transition, "station_end", 0.0) or 0.0)
    if end < start or not _in_range(float(station), start, end):
        return None
    before = _control_at_or_before(controls, start, side=side)
    after = _control_between(controls, start, end, side=side)
    if before is None or after is None:
        return None
    start_value = float(getattr(before, "crossfall_value", 0.0) or 0.0)
    end_value = float(getattr(after, "crossfall_value", 0.0) or 0.0)
    ratio = 1.0 if abs(end - start) <= 1.0e-12 else min(max((float(station) - start) / (end - start), 0.0), 1.0)
    value = start_value + (end_value - start_value) * ratio
    source_ids = _unique_nonempty(
        [
            "" if before is None else str(getattr(before, "control_row_id", "") or ""),
            "" if after is None else str(getattr(after, "control_row_id", "") or ""),
        ]
    )
    return float(value), ",".join(source_ids)


def _active_control(controls: list[CrossfallControlRow], station: float, *, side: str) -> CrossfallControlRow | None:
    candidates = [row for row in controls if _control_applies_to_side(row, side) and float(getattr(row, "station", 0.0) or 0.0) <= float(station)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: (float(getattr(row, "station", 0.0) or 0.0), _side_priority(row, side)))[-1]


def _control_at_or_before(controls: list[CrossfallControlRow], station: float, *, side: str) -> CrossfallControlRow | None:
    return _active_control(controls, station, side=side)


def _control_at_or_after(controls: list[CrossfallControlRow], station: float, *, side: str) -> CrossfallControlRow | None:
    candidates = [row for row in controls if _control_applies_to_side(row, side) and float(getattr(row, "station", 0.0) or 0.0) >= float(station)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: (float(getattr(row, "station", 0.0) or 0.0), -_side_priority(row, side)))[0]


def _control_between(controls: list[CrossfallControlRow], start: float, end: float, *, side: str) -> CrossfallControlRow | None:
    candidates = [
        row
        for row in controls
        if _control_applies_to_side(row, side)
        and float(start) <= float(getattr(row, "station", 0.0) or 0.0) <= float(end)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: (float(getattr(row, "station", 0.0) or 0.0), -_side_priority(row, side)))[-1]


def _active_transition(transitions: list[RunoffTransitionRow], station: float) -> RunoffTransitionRow | None:
    matches = [
        row
        for row in list(transitions or [])
        if float(getattr(row, "station_start", 0.0) or 0.0) <= float(station) <= float(getattr(row, "station_end", 0.0) or 0.0)
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda row: (float(getattr(row, "station_start", 0.0) or 0.0), float(getattr(row, "station_end", 0.0) or 0.0)))[0]


def _sorted_controls(controls: list[CrossfallControlRow]) -> list[CrossfallControlRow]:
    return sorted(list(controls or []), key=lambda row: (float(getattr(row, "station", 0.0) or 0.0), str(getattr(row, "control_row_id", "") or "")))


def _control_applies_to_side(row: CrossfallControlRow, side: str) -> bool:
    row_side = _side(row)
    return row_side == side or row_side == "both" or row_side == "center"


def _side(row: object) -> str:
    return str(getattr(row, "side", "") or "").strip().lower()


def _side_priority(row: object, side: str) -> int:
    row_side = _side(row)
    if row_side == side:
        return 2
    if row_side == "both":
        return 1
    return 0


def _constraint_float(constraints: list[object], kind: str, default: float) -> float:
    for row in list(constraints or []):
        if str(getattr(row, "kind", "") or "") != kind:
            continue
        value = _finite_float(getattr(row, "value", None))
        if value is not None:
            return value
    return float(default)


def _normalized_station_range(station_range: tuple[float, float] | None) -> tuple[float | None, float | None]:
    if station_range is None:
        return None, None
    start = float(station_range[0])
    end = float(station_range[1])
    if start > end:
        start, end = end, start
    return start, end


def _in_range(value: float, start: float | None, end: float | None) -> bool:
    if start is None or end is None:
        return True
    return float(start) - STATION_RANGE_TOLERANCE <= float(value) <= float(end) + STATION_RANGE_TOLERANCE


def _finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return number if math.isfinite(number) else None


def _unique_nonempty(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in [str(item or "").strip() for item in list(values or [])]:
        if not value:
            continue
        for part in [chunk.strip() for chunk in value.split(",")]:
            if part and part not in seen:
                seen.add(part)
                output.append(part)
    return output


def _diagnostic(severity: str, kind: str, message: str, notes: str = "") -> DiagnosticMessage:
    return DiagnosticMessage(
        severity=str(severity or "info"),
        kind=str(kind or "superelevation_diagnostic"),
        message=str(message or ""),
        notes=str(notes or ""),
    )

