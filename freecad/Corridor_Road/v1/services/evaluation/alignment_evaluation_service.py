"""Alignment evaluation service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin

from ...models.source.alignment_model import AlignmentElement, AlignmentModel


@dataclass(frozen=True)
class AlignmentStationResult:
    """Minimal station evaluation result for horizontal alignment."""

    station: float
    active_element_id: str = ""
    active_element_kind: str = ""
    x: float = 0.0
    y: float = 0.0
    tangent_direction_deg: float = 0.0
    offset_on_element: float = 0.0
    status: str = "not_found"
    notes: str = ""


class AlignmentEvaluationService:
    """Evaluate station-based alignment context from an alignment source model."""

    def evaluate_station(
        self,
        alignment: AlignmentModel,
        station: float,
    ) -> AlignmentStationResult:
        """Resolve the active alignment element at a station."""

        element = self._find_active_element(alignment.geometry_sequence, station)
        if element is None:
            return AlignmentStationResult(
                station=station,
                status="out_of_range",
                notes="Station is outside the alignment geometry sequence.",
            )

        sample = self._sample_element(element, station)
        if sample is None:
            return AlignmentStationResult(
                station=station,
                active_element_id=element.element_id,
                active_element_kind=element.kind,
                offset_on_element=float(station) - float(element.station_start),
                status="unsupported",
                notes="Alignment element does not contain usable XY geometry.",
            )

        x, y, tangent_direction_deg, offset_on_element = sample

        return AlignmentStationResult(
            station=station,
            active_element_id=element.element_id,
            active_element_kind=element.kind,
            x=x,
            y=y,
            tangent_direction_deg=tangent_direction_deg,
            offset_on_element=offset_on_element,
            status="ok",
            notes="Station resolved from alignment element geometry.",
        )

    def station_offset_to_xy(
        self,
        alignment: AlignmentModel,
        station: float,
        offset: float,
    ) -> tuple[float, float]:
        """Convert station/offset into XY using the evaluated alignment frame."""

        result = self.evaluate_station(alignment, station)
        if result.status != "ok":
            raise ValueError(result.notes or "Station could not be evaluated on the alignment.")
        heading_rad = radians(float(result.tangent_direction_deg))
        normal_x = -sin(heading_rad)
        normal_y = cos(heading_rad)
        return (
            result.x + float(offset) * normal_x,
            result.y + float(offset) * normal_y,
        )

    def station_offset_adapter(self, alignment: AlignmentModel):
        """Build a station/offset adapter closure for downstream services."""

        def _adapter(station: float, offset: float) -> tuple[float, float]:
            return self.station_offset_to_xy(alignment, station, offset)

        return _adapter

    @staticmethod
    def _find_active_element(
        elements: list[AlignmentElement],
        station: float,
    ) -> AlignmentElement | None:
        for element in elements:
            if element.station_start <= station <= element.station_end:
                return element
        return None

    def _sample_element(
        self,
        element: AlignmentElement,
        station: float,
    ) -> tuple[float, float, float, float] | None:
        x_values = self._numeric_values(element.geometry_payload.get("x_values", []))
        y_values = self._numeric_values(element.geometry_payload.get("y_values", []))
        point_count = min(len(x_values), len(y_values))
        if point_count < 2:
            return None

        points = list(zip(x_values[:point_count], y_values[:point_count]))
        target_offset = max(0.0, float(station) - float(element.station_start))
        element_length = self._element_length(element, points)
        if element_length <= 1e-12:
            return None

        geometry_length = self._geometry_length(points)
        if geometry_length <= 1e-12:
            return None
        clamped_station_offset = min(max(target_offset, 0.0), element_length)
        clamped_offset = (clamped_station_offset / element_length) * geometry_length
        traversed = 0.0
        for index in range(len(points) - 1):
            x0, y0 = points[index]
            x1, y1 = points[index + 1]
            segment_length = self._distance(x0, y0, x1, y1)
            if segment_length <= 1e-12:
                continue
            if traversed + segment_length >= clamped_offset or index == len(points) - 2:
                local_offset = min(max(clamped_offset - traversed, 0.0), segment_length)
                ratio = local_offset / segment_length
                x = x0 + (x1 - x0) * ratio
                y = y0 + (y1 - y0) * ratio
                tangent = degrees(atan2(y1 - y0, x1 - x0))
                return x, y, tangent, clamped_station_offset
            traversed += segment_length
        return None

    @staticmethod
    def _numeric_values(values) -> list[float]:
        result: list[float] = []
        for value in list(values or []):
            try:
                result.append(float(value))
            except Exception:
                continue
        return result

    def _element_length(
        self,
        element: AlignmentElement,
        points: list[tuple[float, float]],
    ) -> float:
        explicit_length = float(element.length or 0.0)
        if explicit_length > 1e-12:
            return explicit_length
        station_length = float(element.station_end) - float(element.station_start)
        if station_length > 1e-12:
            return station_length
        return sum(
            self._distance(x0, y0, x1, y1)
            for (x0, y0), (x1, y1) in zip(points, points[1:])
        )

    def _geometry_length(self, points: list[tuple[float, float]]) -> float:
        return sum(
            self._distance(x0, y0, x1, y1)
            for (x0, y0), (x1, y1) in zip(points, points[1:])
        )

    @staticmethod
    def _distance(x0: float, y0: float, x1: float, y1: float) -> float:
        return ((float(x1) - float(x0)) ** 2 + (float(y1) - float(y0)) ** 2) ** 0.5
