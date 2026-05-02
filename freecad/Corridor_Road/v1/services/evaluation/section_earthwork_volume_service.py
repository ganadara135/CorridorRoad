"""Section-area to earthwork-volume conversion for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.quantity_model import QuantityFragment


_AREA_TO_VOLUME_KIND = {
    "cut_area": "cut",
    "fill_area": "fill",
}


@dataclass(frozen=True)
class SectionEarthworkVolumeResult:
    """Average-end-area volume fragments derived from section area fragments."""

    rows: list[QuantityFragment]
    status: str = "empty"
    notes: str = ""


class SectionEarthworkVolumeService:
    """Build earthwork volume fragments from station-level section area fragments."""

    def build(
        self,
        fragment_rows: list[QuantityFragment],
        *,
        station_values: list[float],
        fragment_id_prefix: str,
    ) -> SectionEarthworkVolumeResult:
        """Create cut/fill volume rows with the average-end-area method."""

        stations = self._station_values(station_values)
        if len(stations) < 2:
            return SectionEarthworkVolumeResult(
                rows=[],
                status="missing_input",
                notes="At least two station values are required for section volume calculation.",
            )

        area_by_kind_and_station = self._area_by_kind_and_station(fragment_rows)
        if not area_by_kind_and_station:
            return SectionEarthworkVolumeResult(
                rows=[],
                status="missing_input",
                notes="Station-level cut_area or fill_area fragments are required.",
            )

        rows: list[QuantityFragment] = []
        missing_window_count = 0
        for station_start, station_end in zip(stations, stations[1:]):
            length = station_end - station_start
            if length <= 0.0:
                continue
            for area_kind, volume_kind in _AREA_TO_VOLUME_KIND.items():
                start_area = self._area_at(area_by_kind_and_station, area_kind, station_start)
                end_area = self._area_at(area_by_kind_and_station, area_kind, station_end)
                if start_area is None or end_area is None:
                    missing_window_count += 1
                    continue
                value = (start_area + end_area) * 0.5 * length
                if value <= 0.0:
                    continue
                rows.append(
                    QuantityFragment(
                        fragment_id=f"{fragment_id_prefix}:{volume_kind}:{station_start:g}-{station_end:g}",
                        quantity_kind=volume_kind,
                        measurement_kind="average_end_area_volume",
                        value=value,
                        unit="m3",
                        station_start=station_start,
                        station_end=station_end,
                        component_ref="section_earthwork_area",
                    )
                )

        if rows:
            return SectionEarthworkVolumeResult(
                rows=rows,
                status="ok",
                notes=self._notes(rows, missing_window_count=missing_window_count),
            )
        return SectionEarthworkVolumeResult(
            rows=[],
            status="empty",
            notes="No positive section earthwork volume fragments were generated.",
        )

    @staticmethod
    def _station_values(station_values: list[float]) -> list[float]:
        values = []
        seen: set[float] = set()
        for value in station_values:
            rounded = round(float(value), 9)
            if rounded in seen:
                continue
            seen.add(rounded)
            values.append(float(value))
        return sorted(values)

    @staticmethod
    def _area_by_kind_and_station(
        fragment_rows: list[QuantityFragment],
    ) -> dict[str, dict[float, float]]:
        result: dict[str, dict[float, float]] = {}
        for row in list(fragment_rows or []):
            area_kind = str(getattr(row, "quantity_kind", "") or "")
            if area_kind not in _AREA_TO_VOLUME_KIND:
                continue
            if str(getattr(row, "unit", "") or "") != "m2":
                continue
            station = getattr(row, "station_start", None)
            if station is None:
                continue
            rounded_station = round(float(station), 9)
            result.setdefault(area_kind, {})
            result[area_kind][rounded_station] = result[area_kind].get(rounded_station, 0.0) + float(row.value)
        return result

    @staticmethod
    def _area_at(
        area_by_kind_and_station: dict[str, dict[float, float]],
        area_kind: str,
        station: float,
    ) -> float | None:
        return area_by_kind_and_station.get(area_kind, {}).get(round(float(station), 9))

    @staticmethod
    def _notes(rows: list[QuantityFragment], *, missing_window_count: int) -> str:
        cut_count = sum(1 for row in rows if row.quantity_kind == "cut")
        fill_count = sum(1 for row in rows if row.quantity_kind == "fill")
        notes = f"Generated {len(rows)} earthwork volume fragments: cut={cut_count}, fill={fill_count}."
        if missing_window_count:
            notes += f" Skipped {missing_window_count} area endpoints without complete station pairs."
        return notes
