"""Station range sampling for CorridorRoad v1 alignments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ...models.source.alignment_model import AlignmentModel
from .alignment_evaluation_service import AlignmentEvaluationService


@dataclass(frozen=True)
class AlignmentStationSampleRow:
    """One evaluated station frame row."""

    station: float
    station_label: str
    x: float = 0.0
    y: float = 0.0
    tangent_direction_deg: float = 0.0
    active_element_id: str = ""
    active_element_kind: str = ""
    status: str = "not_found"
    source_reason: str = "regular_interval"
    notes: str = ""


@dataclass(frozen=True)
class AlignmentStationSampleResult:
    """Ordered station frame samples for one alignment."""

    alignment_id: str
    station_start: float
    station_end: float
    interval: float
    rows: list[AlignmentStationSampleRow] = field(default_factory=list)
    status: str = "empty"
    notes: str = ""

    @property
    def ok_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "ok")


class AlignmentStationSamplingService:
    """Sample an alignment over a station range using shared evaluation logic."""

    def __init__(self, *, evaluation_service: AlignmentEvaluationService | None = None) -> None:
        self.evaluation_service = evaluation_service or AlignmentEvaluationService()

    def sample_range(
        self,
        *,
        alignment: AlignmentModel,
        station_start: float,
        station_end: float,
        interval: float,
        include_end: bool = True,
        extra_stations: Iterable[float] | None = None,
    ) -> AlignmentStationSampleResult:
        """Evaluate an ordered station range."""

        start = float(station_start)
        end = float(station_end)
        step = float(interval)
        if step <= 0.0:
            return AlignmentStationSampleResult(
                alignment_id=alignment.alignment_id,
                station_start=start,
                station_end=end,
                interval=step,
                status="error",
                notes="Station sampling interval must be greater than zero.",
            )

        stations = self._station_values(
            start,
            end,
            step,
            include_end=include_end,
            extra_stations=extra_stations,
        )
        rows = [
            self._sample_station(alignment, station, source_reason=reason)
            for station, reason in stations
        ]
        return AlignmentStationSampleResult(
            alignment_id=alignment.alignment_id,
            station_start=start,
            station_end=end,
            interval=step,
            rows=rows,
            status=self._overall_status(rows),
            notes=self._overall_notes(rows),
        )

    def sample_alignment(
        self,
        *,
        alignment: AlignmentModel,
        interval: float,
        include_end: bool = True,
        extra_stations: Iterable[float] | None = None,
    ) -> AlignmentStationSampleResult:
        """Sample the full station extent of one alignment."""

        extent = self._alignment_station_extent(alignment)
        if extent is None:
            return AlignmentStationSampleResult(
                alignment_id=alignment.alignment_id,
                station_start=0.0,
                station_end=0.0,
                interval=float(interval),
                status="empty",
                notes="Alignment has no geometry sequence station extent.",
            )
        return self.sample_range(
            alignment=alignment,
            station_start=extent[0],
            station_end=extent[1],
            interval=interval,
            include_end=include_end,
            extra_stations=extra_stations,
        )

    def _sample_station(
        self,
        alignment: AlignmentModel,
        station: float,
        *,
        source_reason: str,
    ) -> AlignmentStationSampleRow:
        result = self.evaluation_service.evaluate_station(alignment, station)
        return AlignmentStationSampleRow(
            station=float(station),
            station_label=self._format_station(station),
            x=result.x,
            y=result.y,
            tangent_direction_deg=result.tangent_direction_deg,
            active_element_id=result.active_element_id,
            active_element_kind=result.active_element_kind,
            status=result.status,
            source_reason=source_reason,
            notes=result.notes,
        )

    @staticmethod
    def _station_values(
        station_start: float,
        station_end: float,
        interval: float,
        *,
        include_end: bool,
        extra_stations: Iterable[float] | None,
    ) -> list[tuple[float, str]]:
        start = min(float(station_start), float(station_end))
        end = max(float(station_start), float(station_end))
        values: dict[float, str] = {round(start, 9): "range_start"}
        cursor = start + float(interval)
        while cursor < end - 1e-9:
            values[round(cursor, 9)] = "regular_interval"
            cursor += float(interval)
        if include_end:
            values[round(end, 9)] = "range_end"
        for value in list(extra_stations or []):
            try:
                station = float(value)
            except Exception:
                continue
            if start - 1e-9 <= station <= end + 1e-9:
                values[round(station, 9)] = "extra_station"
        return [(station, values[station]) for station in sorted(values)]

    @staticmethod
    def _alignment_station_extent(alignment: AlignmentModel) -> tuple[float, float] | None:
        elements = list(alignment.geometry_sequence or [])
        if not elements:
            return None
        starts = [float(element.station_start) for element in elements]
        ends = [float(element.station_end) for element in elements]
        return min(starts + ends), max(starts + ends)

    @staticmethod
    def _overall_status(rows: list[AlignmentStationSampleRow]) -> str:
        if not rows:
            return "empty"
        if all(row.status == "ok" for row in rows):
            return "ok"
        if any(row.status == "ok" for row in rows):
            return "partial"
        return "error"

    @staticmethod
    def _overall_notes(rows: list[AlignmentStationSampleRow]) -> str:
        if not rows:
            return "No station rows were sampled."
        ok_count = sum(1 for row in rows if row.status == "ok")
        if ok_count == len(rows):
            return "All alignment station rows evaluated successfully."
        return f"{ok_count} of {len(rows)} alignment station rows evaluated successfully."

    @staticmethod
    def _format_station(station: float) -> str:
        return f"STA {float(station):.3f}"
