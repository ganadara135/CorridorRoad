"""TIN-backed existing-ground profile sampling for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ...models.result.tin_surface import TINSurface
from ...models.source.alignment_model import AlignmentModel
from .alignment_station_sampling_service import AlignmentStationSamplingService
from .tin_sampling_service import TinSamplingService


@dataclass(frozen=True)
class ProfileTinSampleRow:
    """One existing-ground profile sample row."""

    station: float
    x: float
    y: float
    elevation: float | None = None
    status: str = "no_hit"
    face_id: str = ""
    confidence: float = 0.0
    notes: str = ""

    @property
    def found(self) -> bool:
        return self.status == "ok" and self.elevation is not None


@dataclass(frozen=True)
class ProfileTinSampleResult:
    """Existing-ground profile sampled from a TIN along an alignment."""

    alignment_id: str
    surface_ref: str
    rows: list[ProfileTinSampleRow] = field(default_factory=list)
    status: str = "empty"
    notes: str = ""

    @property
    def hit_count(self) -> int:
        return sum(1 for row in self.rows if row.found)


class ProfileTinSamplingService:
    """Sample existing ground profile elevations from TIN and alignment stations."""

    def __init__(
        self,
        *,
        station_sampling_service: AlignmentStationSamplingService | None = None,
        tin_sampling_service: TinSamplingService | None = None,
    ) -> None:
        self.station_sampling_service = station_sampling_service or AlignmentStationSamplingService()
        self.tin_sampling_service = tin_sampling_service or TinSamplingService()

    def sample_alignment(
        self,
        *,
        alignment: AlignmentModel,
        surface: TINSurface,
        interval: float,
        extra_stations: Iterable[float] | None = None,
    ) -> ProfileTinSampleResult:
        """Sample EG elevations along the full alignment station extent."""

        station_result = self.station_sampling_service.sample_alignment(
            alignment=alignment,
            interval=interval,
            extra_stations=extra_stations,
        )
        rows = []
        for station_row in station_result.rows:
            if station_row.status != "ok":
                rows.append(
                    ProfileTinSampleRow(
                        station=station_row.station,
                        x=station_row.x,
                        y=station_row.y,
                        status=station_row.status,
                        notes=station_row.notes,
                    )
                )
                continue
            sample = self.tin_sampling_service.sample_xy(
                surface=surface,
                x=station_row.x,
                y=station_row.y,
            )
            rows.append(
                ProfileTinSampleRow(
                    station=station_row.station,
                    x=sample.x,
                    y=sample.y,
                    elevation=sample.z,
                    status=sample.status,
                    face_id=sample.face_id,
                    confidence=sample.confidence,
                    notes=sample.notes,
                )
            )

        return ProfileTinSampleResult(
            alignment_id=alignment.alignment_id,
            surface_ref=surface.surface_id,
            rows=rows,
            status=self._overall_status(rows),
            notes=self._overall_notes(rows),
        )

    @staticmethod
    def _overall_status(rows: list[ProfileTinSampleRow]) -> str:
        if not rows:
            return "empty"
        if all(row.found for row in rows):
            return "ok"
        if any(row.found for row in rows):
            return "partial"
        return "no_hit"

    @staticmethod
    def _overall_notes(rows: list[ProfileTinSampleRow]) -> str:
        if not rows:
            return "No EG profile rows were sampled."
        hit_count = sum(1 for row in rows if row.found)
        if hit_count == len(rows):
            return "All EG profile rows were sampled from the TIN."
        return f"{hit_count} of {len(rows)} EG profile rows were sampled from the TIN."
