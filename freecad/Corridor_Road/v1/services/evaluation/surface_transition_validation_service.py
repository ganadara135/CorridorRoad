"""Validation service for v1 surface transition source intent."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.source.surface_transition_model import (
    SurfaceTransitionDiagnosticRow,
    SurfaceTransitionModel,
)


@dataclass(frozen=True)
class SurfaceTransitionValidationResult:
    """Validation result for a SurfaceTransitionModel."""

    status: str
    diagnostic_rows: list[SurfaceTransitionDiagnosticRow] = field(default_factory=list)


class SurfaceTransitionValidationService:
    """Validate Region-boundary transition ranges without mutating source rows."""

    def validate(
        self,
        transition_model: SurfaceTransitionModel,
        *,
        known_region_refs: list[str] | None = None,
        boundary_stations: list[float] | None = None,
    ) -> SurfaceTransitionValidationResult:
        diagnostics: list[SurfaceTransitionDiagnosticRow] = []
        rows = list(getattr(transition_model, "transition_ranges", []) or [])
        known_regions = _known_ref_set(known_region_refs)
        boundary_values = _float_values(boundary_stations)
        seen_ids: set[str] = set()
        ranges: list[tuple[float, float, str]] = []

        for index, row in enumerate(rows, start=1):
            transition_id = str(getattr(row, "transition_id", "") or "").strip()
            source_ref = transition_id or f"surface-transition-row:{index}"
            if not transition_id:
                diagnostics.append(_diagnostic("error", "missing_transition_id", source_ref, "Transition id is required."))
            elif transition_id in seen_ids:
                diagnostics.append(
                    _diagnostic("error", "duplicate_transition_id", source_ref, f"Duplicate transition id: {transition_id}.")
                )
            seen_ids.add(transition_id)

            try:
                station_start = float(getattr(row, "station_start", 0.0) or 0.0)
                station_end = float(getattr(row, "station_end", 0.0) or 0.0)
            except Exception:
                diagnostics.append(_diagnostic("error", "invalid_station", source_ref, "Station start/end must be numeric."))
                continue
            if station_start >= station_end:
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "invalid_station_range",
                        source_ref,
                        f"Transition station_start must be lower than station_end: {station_start:g} >= {station_end:g}.",
                    )
                )
            ranges.append((station_start, station_end, source_ref))

            try:
                if float(getattr(row, "sample_interval", 0.0) or 0.0) <= 0.0:
                    diagnostics.append(
                        _diagnostic("error", "invalid_sample_interval", source_ref, "Transition sample_interval must be greater than zero.")
                    )
            except Exception:
                diagnostics.append(_diagnostic("error", "invalid_sample_interval", source_ref, "Transition sample_interval must be numeric."))

            from_region = str(getattr(row, "from_region_ref", "") or "").strip()
            to_region = str(getattr(row, "to_region_ref", "") or "").strip()
            if not from_region or not to_region:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_region_handoff",
                        source_ref,
                        "Transition should reference both from_region_ref and to_region_ref.",
                    )
                )
            if known_regions is not None:
                for region_ref, field_name in ((from_region, "from_region_ref"), (to_region, "to_region_ref")):
                    if region_ref and region_ref not in known_regions:
                        diagnostics.append(
                            _diagnostic(
                                "warning",
                                "missing_region_ref",
                                source_ref,
                                f"Transition {field_name} references missing Region {region_ref}.",
                            )
                        )

            if boundary_values and from_region != to_region:
                covered = [value for value in boundary_values if station_start <= value <= station_end]
                if not covered:
                    diagnostics.append(
                        _diagnostic(
                            "warning",
                            "transition_surface_no_boundary_context",
                            source_ref,
                            "Transition range does not cover a known Region boundary station.",
                        )
                    )
                elif len(covered) > 1:
                    diagnostics.append(
                        _diagnostic(
                            "warning",
                            "transition_surface_multiple_boundaries",
                            source_ref,
                            "Transition range covers multiple Region boundary stations; split the range for clearer review.",
                        )
                    )

        diagnostics.extend(_overlap_diagnostics(ranges))
        status = "error" if any(row.severity == "error" for row in diagnostics) else "warning" if diagnostics else "ok"
        return SurfaceTransitionValidationResult(status=status, diagnostic_rows=diagnostics)


def _overlap_diagnostics(ranges: list[tuple[float, float, str]]) -> list[SurfaceTransitionDiagnosticRow]:
    diagnostics: list[SurfaceTransitionDiagnosticRow] = []
    sorted_ranges = sorted(ranges, key=lambda row: (row[0], row[1], row[2]))
    for left_index, left in enumerate(sorted_ranges):
        for right in sorted_ranges[left_index + 1 :]:
            if float(right[0]) >= float(left[1]):
                break
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "overlapping_transition_ranges",
                    left[2],
                    f"Transition range {left[2]} overlaps {right[2]}.",
                )
            )
    return diagnostics


def _known_ref_set(values: list[str] | None) -> set[str] | None:
    if values is None:
        return None
    return {str(value).strip() for value in list(values or []) if str(value).strip()}


def _float_values(values: list[float] | None) -> list[float]:
    output: list[float] = []
    for value in list(values or []):
        try:
            output.append(float(value))
        except Exception:
            continue
    return sorted(output)


def _diagnostic(severity: str, kind: str, source_ref: str, message: str, notes: str = "") -> SurfaceTransitionDiagnosticRow:
    return SurfaceTransitionDiagnosticRow(
        diagnostic_id=f"surface-transition:{kind}:{source_ref or 'model'}",
        severity=str(severity or "info"),
        kind=str(kind or "info"),
        source_ref=str(source_ref or ""),
        message=str(message or ""),
        notes=str(notes or ""),
    )
