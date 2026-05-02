"""Region validation and resolution services for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models.source.region_model import (
    REGION_PRIMARY_KINDS,
    RegionDiagnosticRow,
    RegionModel,
    RegionRow,
    normalize_region_primary_kind,
)
from ...models.result.region_context import RegionContextSummary


STRUCTURE_REQUIRED_PRIMARY_KINDS = {"bridge", "culvert", "structure_influence"}


@dataclass(frozen=True)
class RegionValidationResult:
    """Validation result for a RegionModel."""

    status: str
    diagnostic_rows: list[RegionDiagnosticRow] = field(default_factory=list)


@dataclass(frozen=True)
class RegionResolutionResult:
    """Resolved region context for a station."""

    station: float
    active_region_id: str = ""
    active_primary_kind: str = ""
    active_applied_layers: list[str] = field(default_factory=list)
    active_policy_set_id: str = ""
    active_template_ref: str = ""
    active_assembly_ref: str = ""
    active_superelevation_ref: str = ""
    active_transition_ref: str = ""
    resolved_structure_ref: str = ""
    resolved_structure_refs: list[str] = field(default_factory=list)
    resolved_drainage_refs: list[str] = field(default_factory=list)
    resolved_ramp_ref: str = ""
    resolved_intersection_ref: str = ""
    overlap_region_ids: list[str] = field(default_factory=list)
    diagnostic_rows: list[RegionDiagnosticRow] = field(default_factory=list)
    notes: str = ""


class RegionValidationService:
    """Validate v1 region source rows without mutating them."""

    def validate(
        self,
        region_model: RegionModel,
        *,
        known_assembly_refs: list[str] | None = None,
        known_structure_refs: list[str] | None = None,
    ) -> RegionValidationResult:
        diagnostics: list[RegionDiagnosticRow] = []
        rows = list(getattr(region_model, "region_rows", []) or [])
        known_assembly_ref_set = _known_ref_set(known_assembly_refs)
        known_structure_ref_set = _known_ref_set(known_structure_refs)
        seen_ids: set[str] = set()
        for index, row in enumerate(rows, start=1):
            region_id = str(getattr(row, "region_id", "") or "").strip()
            source_ref = region_id or f"region-row:{index}"
            if not region_id:
                diagnostics.append(_diagnostic("error", "missing_region_id", source_ref, "Region id is required."))
            elif region_id in seen_ids:
                diagnostics.append(_diagnostic("error", "duplicate_region_id", source_ref, f"Duplicate region id: {region_id}."))
            seen_ids.add(region_id)

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
                        f"Region station_start must be lower than station_end: {station_start:g} >= {station_end:g}.",
                    )
                )

            primary_kind = normalize_region_primary_kind(str(getattr(row, "primary_kind", "") or getattr(row, "region_kind", "")))
            if primary_kind not in REGION_PRIMARY_KINDS:
                diagnostics.append(
                    _diagnostic("warning", "unsupported_primary_kind", source_ref, f"Unsupported primary kind: {primary_kind}.")
                )
            if not str(getattr(row, "assembly_ref", "") or "").strip() and not str(getattr(row, "template_ref", "") or "").strip():
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_assembly_or_template",
                        source_ref,
                        "Region has no assembly_ref or template_ref yet.",
                    )
                )
            assembly_ref = str(getattr(row, "assembly_ref", "") or "").strip()
            if known_assembly_ref_set is not None and assembly_ref and assembly_ref not in known_assembly_ref_set:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_assembly_ref",
                        source_ref,
                        f"Region references missing assembly_ref {assembly_ref}.",
                    )
                )
            try:
                int(getattr(row, "priority", 0) or 0)
            except Exception:
                diagnostics.append(_diagnostic("error", "invalid_priority", source_ref, "Region priority must be numeric."))
            structure_refs = list(getattr(row, "structure_refs", []) or [])
            if len(structure_refs) > 1:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "multiple_structure_refs",
                        source_ref,
                        "Region should reference at most one active Structure; split the range into separate Region rows.",
                    )
                )
            structure_ref = str(getattr(row, "structure_ref", "") or "").strip()
            if _primary_kind_requires_structure(primary_kind) and not structure_ref:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_required_structure_ref",
                        source_ref,
                        f"Region primary_kind {primary_kind} requires a structure_ref.",
                    )
                )
            if known_structure_ref_set is not None and structure_ref and structure_ref not in known_structure_ref_set:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_structure_ref",
                        source_ref,
                        f"Region references missing structure_ref {structure_ref}.",
                    )
                )

        diagnostics.extend(_overlap_diagnostics(rows))
        status = "error" if any(row.severity == "error" for row in diagnostics) else "warning" if diagnostics else "ok"
        return RegionValidationResult(status=status, diagnostic_rows=diagnostics)


class RegionResolutionService:
    """Resolve active region policy rows from a region source model."""

    def __init__(self, *, validation_service: RegionValidationService | None = None) -> None:
        self.validation_service = validation_service or RegionValidationService()

    def validate(
        self,
        region_model: RegionModel,
        *,
        known_assembly_refs: list[str] | None = None,
        known_structure_refs: list[str] | None = None,
    ) -> RegionValidationResult:
        """Validate a RegionModel using the shared validation service."""

        return self.validation_service.validate(
            region_model,
            known_assembly_refs=known_assembly_refs,
            known_structure_refs=known_structure_refs,
        )

    def resolve_station(
        self,
        region_model: RegionModel,
        station: float,
    ) -> RegionResolutionResult:
        """Resolve the active region covering the station."""

        station_value = float(station)
        matches = self._matching_regions(region_model.region_rows, station_value)
        if not matches:
            return RegionResolutionResult(
                station=station_value,
                diagnostic_rows=[
                    _diagnostic("warning", "no_active_region", "", f"No active region covers station {station_value:g}.")
                ],
            )

        matches = sorted(matches, key=_region_sort_key)
        active = matches[0]
        overlap_ids = [row.region_id for row in matches[1:] if row.region_id]
        diagnostics: list[RegionDiagnosticRow] = []
        if len(matches) > 1:
            diagnostics.append(
                _diagnostic(
                    "info",
                    "overlapping_regions",
                    active.region_id,
                    f"Station {station_value:g} overlaps regions: {', '.join(row.region_id for row in matches if row.region_id)}.",
                )
            )
        if len(matches) > 1 and _priority(matches[0]) == _priority(matches[1]):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "equal_priority_overlap",
                    active.region_id,
                    "Overlapping regions share the same priority; region_index was used as the tie breaker.",
                )
            )

        return RegionResolutionResult(
            station=station_value,
            active_region_id=active.region_id,
            active_primary_kind=active.primary_kind,
            active_applied_layers=list(active.applied_layers or []),
            active_policy_set_id=active.policy_set_ref,
            active_template_ref=active.template_ref,
            active_assembly_ref=active.assembly_ref,
            active_superelevation_ref=active.superelevation_ref,
            resolved_structure_ref=str(getattr(active, "structure_ref", "") or ""),
            resolved_structure_refs=list(active.structure_refs or []),
            resolved_drainage_refs=list(active.drainage_refs or []),
            resolved_ramp_ref=active.ramp_ref,
            resolved_intersection_ref=active.intersection_ref,
            overlap_region_ids=overlap_ids,
            diagnostic_rows=diagnostics,
            notes=active.notes,
        )

    def resolve_range(self, region_model: RegionModel, station_start: float, station_end: float) -> list[RegionRow]:
        """Return region rows intersecting a station range."""

        start = float(station_start)
        end = float(station_end)
        if start > end:
            start, end = end, start
        rows = [
            row
            for row in list(getattr(region_model, "region_rows", []) or [])
            if float(row.station_end) >= start and float(row.station_start) <= end
        ]
        return sorted(rows, key=lambda row: (float(row.station_start), int(row.region_index), str(row.region_id)))

    def boundary_stations(self, region_model: RegionModel) -> list[float]:
        """Return sorted unique region boundary stations."""

        values: list[float] = []
        for row in list(getattr(region_model, "region_rows", []) or []):
            values.extend([float(row.station_start), float(row.station_end)])
        output: list[float] = []
        seen: set[float] = set()
        for value in sorted(values):
            key = round(value, 9)
            if key in seen:
                continue
            seen.add(key)
            output.append(value)
        return output

    def resolve_handoff(
        self,
        region_model: RegionModel,
        station: float,
    ) -> RegionContextSummary:
        """Return the normalized Region context consumed by downstream services."""

        result = self.resolve_station(region_model, station)
        active_row = self._find_row(region_model.region_rows, result.active_region_id)
        override_refs = list(getattr(active_row, "override_refs", []) or []) if active_row is not None else []
        return RegionContextSummary(
            station=result.station,
            region_id=result.active_region_id,
            primary_kind=result.active_primary_kind,
            applied_layers=list(result.active_applied_layers or []),
            assembly_ref=result.active_assembly_ref,
            template_ref=result.active_template_ref,
            policy_set_ref=result.active_policy_set_id,
            superelevation_ref=result.active_superelevation_ref,
            structure_ref=result.resolved_structure_ref,
            structure_refs=list(result.resolved_structure_refs or []),
            drainage_refs=list(result.resolved_drainage_refs or []),
            ramp_ref=result.resolved_ramp_ref,
            intersection_ref=result.resolved_intersection_ref,
            override_refs=override_refs,
            overlap_region_ids=list(result.overlap_region_ids or []),
            diagnostic_kinds=[row.kind for row in list(result.diagnostic_rows or []) if row.kind],
            notes=result.notes,
        )

    def resolve_handoff_rows(
        self,
        region_model: RegionModel,
        stations: list[float],
    ) -> list[RegionContextSummary]:
        """Resolve handoff summaries for multiple stations in station order."""

        return [self.resolve_handoff(region_model, float(station)) for station in list(stations or [])]

    @staticmethod
    def _matching_regions(region_rows: list[RegionRow], station: float) -> list[RegionRow]:
        return [
            row
            for row in list(region_rows or [])
            if float(row.station_start) <= station <= float(row.station_end)
        ]

    @staticmethod
    def _find_row(region_rows: list[RegionRow], region_id: str) -> RegionRow | None:
        for row in list(region_rows or []):
            if str(getattr(row, "region_id", "") or "") == str(region_id or ""):
                return row
        return None


def _region_sort_key(row: RegionRow) -> tuple[int, int, float, str]:
    """Sort active candidates by priority, row order, narrowest range, then id."""

    return (-_priority(row), int(getattr(row, "region_index", 0) or 0), _range_length(row), str(row.region_id))


def _priority(row: RegionRow) -> int:
    try:
        return int(getattr(row, "priority", 0) or 0)
    except Exception:
        return 0


def _range_length(row: RegionRow) -> float:
    try:
        return abs(float(row.station_end) - float(row.station_start))
    except Exception:
        return 0.0


def _overlap_diagnostics(rows: list[RegionRow]) -> list[RegionDiagnosticRow]:
    diagnostics: list[RegionDiagnosticRow] = []
    sorted_rows = sorted(list(rows or []), key=lambda row: (float(row.station_start), float(row.station_end), row.region_id))
    for left_index, left in enumerate(sorted_rows):
        for right in sorted_rows[left_index + 1 :]:
            if float(right.station_start) > float(left.station_end):
                break
            if _priority(left) == _priority(right):
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "equal_priority_overlap",
                        left.region_id,
                        f"Region {left.region_id} overlaps {right.region_id} with equal priority {_priority(left)}.",
                    )
                )
    return diagnostics


def _known_ref_set(values: list[str] | None) -> set[str] | None:
    if values is None:
        return None
    return {str(value).strip() for value in list(values or []) if str(value).strip()}


def _primary_kind_requires_structure(primary_kind: str) -> bool:
    return str(primary_kind or "").strip() in STRUCTURE_REQUIRED_PRIMARY_KINDS


def _diagnostic(severity: str, kind: str, source_ref: str, message: str, notes: str = "") -> RegionDiagnosticRow:
    return RegionDiagnosticRow(
        diagnostic_id=f"region:{kind}:{source_ref or 'model'}",
        severity=str(severity or "info"),
        kind=str(kind or "info"),
        source_ref=str(source_ref or ""),
        message=str(message or ""),
        notes=str(notes or ""),
    )
