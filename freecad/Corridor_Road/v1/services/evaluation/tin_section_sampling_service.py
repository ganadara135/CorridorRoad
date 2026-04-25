"""TIN-backed section terrain sampling for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from ...models.result.tin_surface import TINSurface
from .tin_sampling_service import TinSamplingService


StationOffsetToXY = Callable[[float, float], tuple[float, float]]


@dataclass(frozen=True)
class TinSectionSampleRow:
    """One sampled terrain row across a section."""

    station: float
    offset: float
    x: float
    y: float
    z: float | None = None
    found: bool = False
    status: str = "no_hit"
    face_id: str = ""
    confidence: float = 0.0
    notes: str = ""


@dataclass(frozen=True)
class TinSectionSampleResult:
    """TIN terrain profile sampled at one station."""

    surface_ref: str
    station: float
    rows: list[TinSectionSampleRow] = field(default_factory=list)
    status: str = "empty"
    query_kind: str = "section_offsets"
    notes: str = ""

    @property
    def hit_count(self) -> int:
        """Number of rows that resolved to a TIN face."""

        return sum(1 for row in self.rows if row.found)

    @property
    def miss_count(self) -> int:
        """Number of rows that did not resolve to a TIN face."""

        return sum(1 for row in self.rows if not row.found)


class TinSectionSamplingService:
    """Sample a TIN along section offsets using an explicit XY adapter."""

    def __init__(self, *, sampling_service: TinSamplingService | None = None) -> None:
        self.sampling_service = sampling_service or TinSamplingService()

    def sample_offsets(
        self,
        *,
        surface: TINSurface | None,
        station: float,
        offsets: Iterable[float],
        station_offset_to_xy: StationOffsetToXY | None = None,
        surface_ref: str = "",
    ) -> TinSectionSampleResult:
        """Sample terrain elevations for a station across the supplied offsets."""

        resolved_ref = surface_ref or (surface.surface_id if surface is not None else "")
        offset_values = [float(offset) for offset in list(offsets or [])]
        if not offset_values:
            return TinSectionSampleResult(
                surface_ref=resolved_ref,
                station=float(station),
                status="empty",
                notes="At least one section offset is required.",
            )

        if station_offset_to_xy is None:
            rows = [
                self._error_row(
                    station=float(station),
                    offset=offset,
                    notes="Section sampling requires an explicit station_offset_to_xy adapter.",
                )
                for offset in offset_values
            ]
            return TinSectionSampleResult(
                surface_ref=resolved_ref,
                station=float(station),
                rows=rows,
                status="error",
                notes="Station/offset to XY adapter is missing.",
            )

        rows = [
            self._sample_one(
                surface=surface,
                surface_ref=resolved_ref,
                station=float(station),
                offset=offset,
                station_offset_to_xy=station_offset_to_xy,
            )
            for offset in offset_values
        ]
        return TinSectionSampleResult(
            surface_ref=resolved_ref,
            station=float(station),
            rows=rows,
            status=self._overall_status(rows),
            notes=self._overall_notes(rows),
        )

    def _sample_one(
        self,
        *,
        surface: TINSurface | None,
        surface_ref: str,
        station: float,
        offset: float,
        station_offset_to_xy: StationOffsetToXY,
    ) -> TinSectionSampleRow:
        try:
            x, y = station_offset_to_xy(station, offset)
        except Exception as exc:
            return self._error_row(
                station=station,
                offset=offset,
                notes=f"Station/offset adapter failed: {exc}",
            )

        sample = self.sampling_service.sample_xy(
            surface=surface,
            surface_ref=surface_ref,
            x=float(x),
            y=float(y),
        )
        return TinSectionSampleRow(
            station=station,
            offset=offset,
            x=sample.x,
            y=sample.y,
            z=sample.z,
            found=sample.found,
            status=sample.status,
            face_id=sample.face_id,
            confidence=sample.confidence,
            notes=sample.notes,
        )

    @staticmethod
    def _error_row(
        *,
        station: float,
        offset: float,
        notes: str,
    ) -> TinSectionSampleRow:
        return TinSectionSampleRow(
            station=station,
            offset=offset,
            x=station,
            y=offset,
            status="error",
            notes=notes,
        )

    @staticmethod
    def _overall_status(rows: list[TinSectionSampleRow]) -> str:
        if not rows:
            return "empty"
        statuses = {row.status for row in rows}
        if statuses == {"ok"}:
            return "ok"
        if any(row.status == "ok" for row in rows):
            return "partial"
        if statuses == {"no_hit"}:
            return "no_hit"
        return "error"

    @staticmethod
    def _overall_notes(rows: list[TinSectionSampleRow]) -> str:
        hit_count = sum(1 for row in rows if row.found)
        if hit_count == len(rows):
            return "All section offsets were sampled from the TIN."
        if hit_count:
            return f"{hit_count} of {len(rows)} section offsets were sampled from the TIN."
        return "No section offsets were sampled from the TIN."
