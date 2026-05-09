"""Drainage resolution service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.source.drainage_model import (
    DrainageCollectionRegion,
    DrainageElementRow,
    DrainageModel,
)
from ...models.source.region_model import RegionModel


@dataclass(frozen=True)
class DrainageValidationResult:
    """Validation result for a DrainageModel."""

    status: str
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


@dataclass(frozen=True)
class DrainageResolutionResult:
    """Minimal resolved drainage context for a station."""

    station: float
    active_element_id: str = ""
    active_element_kind: str = ""
    active_policy_set_ref: str = ""
    active_collection_region_id: str = ""
    collection_risk_level: str = ""


class DrainageValidationService:
    """Validate v1 drainage source rows without mutating them."""

    def validate(self, drainage_model: DrainageModel, *, region_model: RegionModel | None = None) -> DrainageValidationResult:
        diagnostics: list[DiagnosticMessage] = []
        element_rows = list(getattr(drainage_model, "element_rows", []) or [])
        policy_rows = list(getattr(drainage_model, "policy_rows", []) or [])
        collection_rows = list(getattr(drainage_model, "collection_region_rows", []) or [])
        policy_ids = _policy_id_set(policy_rows)
        region_ranges = None if region_model is None else _region_station_ranges(region_model)

        diagnostics.extend(_duplicate_id_diagnostics(policy_rows, "policy_set_id", "duplicate_policy_set_id", "Drainage policy id is duplicated."))
        diagnostics.extend(
            _duplicate_id_diagnostics(
                element_rows,
                "drainage_element_id",
                "duplicate_drainage_element_id",
                "Drainage element id is duplicated.",
            )
        )
        diagnostics.extend(
            _duplicate_id_diagnostics(
                collection_rows,
                "collection_region_id",
                "duplicate_collection_region_id",
                "Drainage collection region id is duplicated.",
            )
        )

        for index, row in enumerate(element_rows, start=1):
            element_id = str(getattr(row, "drainage_element_id", "") or "").strip()
            source_ref = element_id or f"drainage-element:{index}"
            if not element_id:
                diagnostics.append(_diagnostic("error", "missing_drainage_element_id", source_ref, "Drainage element id is required."))
            element_kind = str(getattr(row, "element_kind", "") or "").strip()
            if not element_kind:
                diagnostics.append(_diagnostic("warning", "missing_drainage_element_kind", source_ref, "Drainage element kind is not set."))
            side = str(getattr(row, "side", "") or "").strip().lower()
            if side and side not in {"left", "right", "both", "center"}:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "unsupported_drainage_side",
                        source_ref,
                        f"Drainage element side should be left, right, both, or center: {side}.",
                    )
                )
            station_diagnostic = _station_range_diagnostic(
                row,
                source_ref=source_ref,
                kind="invalid_drainage_element_station_range",
                label="Drainage element",
            )
            if station_diagnostic is not None:
                diagnostics.append(station_diagnostic)
            region_diagnostic = _element_region_station_diagnostic(row, source_ref=source_ref, region_ranges=region_ranges)
            if region_diagnostic is not None:
                diagnostics.append(region_diagnostic)
            policy_ref = str(getattr(row, "policy_set_ref", "") or "").strip()
            if not policy_ref:
                diagnostics.append(_diagnostic("warning", "missing_policy_ref", source_ref, "Drainage element has no policy_set_ref."))
            elif policy_ref not in policy_ids:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "missing_policy_set_ref",
                        source_ref,
                        f"Drainage element references missing policy_set_ref {policy_ref}.",
                    )
                )

        for index, row in enumerate(policy_rows, start=1):
            policy_id = str(getattr(row, "policy_set_id", "") or "").strip()
            source_ref = policy_id or f"drainage-policy:{index}"
            if not policy_id:
                diagnostics.append(_diagnostic("error", "missing_policy_set_id", source_ref, "Drainage policy id is required."))
            if not str(getattr(row, "flow_intent", "") or "").strip():
                diagnostics.append(_diagnostic("warning", "missing_flow_intent", source_ref, "Drainage policy flow_intent is not set."))

        for index, row in enumerate(collection_rows, start=1):
            region_id = str(getattr(row, "collection_region_id", "") or "").strip()
            source_ref = region_id or f"drainage-collection:{index}"
            if not region_id:
                diagnostics.append(_diagnostic("error", "missing_collection_region_id", source_ref, "Drainage collection region id is required."))
            station_diagnostic = _station_range_diagnostic(
                row,
                source_ref=source_ref,
                kind="invalid_collection_region_station_range",
                label="Drainage collection region",
            )
            if station_diagnostic is not None:
                diagnostics.append(station_diagnostic)

        status = "error" if any(row.severity == "error" for row in diagnostics) else "warning" if diagnostics else "ok"
        return DrainageValidationResult(status=status, diagnostic_rows=diagnostics)


class DrainageResolutionService:
    """Resolve drainage element and collection-region context for a station."""

    def __init__(self, *, validation_service: DrainageValidationService | None = None) -> None:
        self.validation_service = validation_service or DrainageValidationService()

    def validate(self, drainage_model: DrainageModel, *, region_model: RegionModel | None = None) -> DrainageValidationResult:
        """Validate a DrainageModel using the shared validation service."""

        return self.validation_service.validate(drainage_model, region_model=region_model)

    def resolve_station(
        self,
        drainage_model: DrainageModel,
        station: float,
    ) -> DrainageResolutionResult:
        """Resolve the active drainage context covering the station."""

        element = self._find_active_element(drainage_model.element_rows, station)
        region = self._find_active_region(drainage_model.collection_region_rows, station)

        return DrainageResolutionResult(
            station=station,
            active_element_id="" if element is None else element.drainage_element_id,
            active_element_kind="" if element is None else element.element_kind,
            active_policy_set_ref="" if element is None else element.policy_set_ref,
            active_collection_region_id="" if region is None else region.collection_region_id,
            collection_risk_level="" if region is None else region.risk_level,
        )

    @staticmethod
    def _find_active_element(
        element_rows: list[DrainageElementRow],
        station: float,
    ) -> DrainageElementRow | None:
        for row in element_rows:
            if row.station_start <= station <= row.station_end:
                return row
        return None

    @staticmethod
    def _find_active_region(
        region_rows: list[DrainageCollectionRegion],
        station: float,
    ) -> DrainageCollectionRegion | None:
        for row in region_rows:
            if row.station_start <= station <= row.station_end:
                return row
        return None


def _policy_id_set(policy_rows: list[DrainagePolicySet]) -> set[str]:
    return {str(getattr(row, "policy_set_id", "") or "").strip() for row in list(policy_rows or []) if str(getattr(row, "policy_set_id", "") or "").strip()}


def _duplicate_id_diagnostics(rows: list[object], id_attr: str, kind: str, message: str) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    seen: set[str] = set()
    for index, row in enumerate(list(rows or []), start=1):
        row_id = str(getattr(row, id_attr, "") or "").strip()
        if not row_id:
            continue
        if row_id in seen:
            diagnostics.append(_diagnostic("error", kind, row_id, message, notes=f"row_index={index}"))
        seen.add(row_id)
    return diagnostics


def _station_range_diagnostic(row: object, *, source_ref: str, kind: str, label: str) -> DiagnosticMessage | None:
    try:
        station_start = float(getattr(row, "station_start", 0.0) or 0.0)
        station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    except Exception:
        return _diagnostic("error", kind, source_ref, f"{label} station_start/station_end must be numeric.")
    if station_start >= station_end:
        return _diagnostic(
            "error",
            kind,
            source_ref,
            f"{label} station_start must be lower than station_end: {station_start:g} >= {station_end:g}.",
        )
    return None


def _region_station_ranges(region_model: RegionModel | None) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    if region_model is None:
        return ranges
    for row in list(getattr(region_model, "region_rows", []) or []):
        region_id = str(getattr(row, "region_id", "") or "").strip()
        if not region_id:
            continue
        try:
            station_start = float(getattr(row, "station_start", 0.0) or 0.0)
            station_end = float(getattr(row, "station_end", 0.0) or 0.0)
        except Exception:
            continue
        ranges[region_id] = (min(station_start, station_end), max(station_start, station_end))
    return ranges


def _element_region_station_diagnostic(
    row: object,
    *,
    source_ref: str,
    region_ranges: dict[str, tuple[float, float]] | None,
) -> DiagnosticMessage | None:
    region_ref = str(getattr(row, "region_ref", "") or "").strip()
    if not region_ref or region_ranges is None:
        return None
    region_range = region_ranges.get(region_ref)
    if region_range is None:
        return _diagnostic(
            "warning",
            "missing_drainage_element_region_ref",
            source_ref,
            f"Drainage element references missing Region {region_ref}.",
            notes=f"region_ref={region_ref}",
        )
    try:
        station_start = float(getattr(row, "station_start", 0.0) or 0.0)
        station_end = float(getattr(row, "station_end", 0.0) or 0.0)
    except Exception:
        return None
    lower, upper = region_range
    tolerance = 1.0e-6
    if station_start < lower - tolerance or station_end > upper + tolerance:
        return _diagnostic(
            "error",
            "drainage_element_outside_region_station_range",
            source_ref,
            (
                "Drainage element Start STA and End STA must stay inside the referenced Region boundary: "
                f"{station_start:g}-{station_end:g} outside {region_ref} {lower:g}-{upper:g}."
            ),
            notes=f"region_ref={region_ref};region_start={lower:g};region_end={upper:g};element_start={station_start:g};element_end={station_end:g}",
        )
    return None


def _diagnostic(severity: str, kind: str, source_ref: str, message: str, notes: str = "") -> DiagnosticMessage:
    note_values = [f"source_ref={str(source_ref or '')}"]
    if str(notes or ""):
        note_values.append(str(notes or ""))
    return DiagnosticMessage(
        severity=str(severity or "info"),
        kind=str(kind or "info"),
        message=str(message or ""),
        notes=";".join(note_values),
    )
