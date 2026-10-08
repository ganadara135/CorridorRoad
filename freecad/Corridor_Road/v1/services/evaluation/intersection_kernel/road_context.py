"""The read-only view of the evaluated roads that the intersection kernel works on.

The kernel asks; it never decides a road's position, direction or pavement width. Those belong to
the Alignment and the Applied Sections (decision D1 of `V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md`).
Stations, offsets and coordinates are metres in Project local coordinates. `left` is the left of
the direction of increasing station.
"""

from __future__ import annotations

import bisect
import math

from dataclasses import dataclass, field
from typing import Protocol


# Stations closer than this are the same station. The alignment geometry is sampled in metres
# with double precision; a micrometre is far below any design tolerance and above the noise.
STATION_TOLERANCE_M = 1.0e-6


@dataclass(frozen=True)
class Crossing:
    """A plan-view crossing of two roads."""

    x: float
    y: float
    station_a: float
    station_b: float


class RoadContext(Protocol):
    def road_refs(self) -> tuple[str, ...]: ...

    def station_range(self, road_ref: str) -> tuple[float, float]: ...

    def point_xy(self, road_ref: str, station: float) -> tuple[float, float]: ...

    def tangent_xy(self, road_ref: str, station: float) -> tuple[float, float]: ...

    def crossings(self, road_a: str, road_b: str) -> tuple[Crossing, ...]: ...

    def pavement_half_width(self, road_ref: str, station: float, side: str) -> float | None: ...

    def finished_grade_z(self, road_ref: str, station: float) -> float | None: ...

    def vertex_stations(self, road_ref: str, start: float, end: float) -> tuple[float, ...]: ...

    def fingerprint_rows(self, road_ref: str) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class PolylineRoad:
    """One road as plain data: its centreline, pavement half widths and finished grade by station.

    `stations` increase strictly and pair with `xy`. `half_width_rows` are `(station, left, right)`
    and `grade_rows` are `(station, z)`, both in increasing station; between rows the value is
    linear, beyond the first or last row it is held.
    """

    road_ref: str
    stations: tuple[float, ...]
    xy: tuple[tuple[float, float], ...]
    half_width_rows: tuple[tuple[float, float, float], ...] = ()
    grade_rows: tuple[tuple[float, float], ...] = ()
    width_source: str = ""


@dataclass
class PolylineRoadContext:
    """`RoadContext` over `PolylineRoad` data. Free of FreeCAD; tests build it analytically."""

    roads: dict[str, PolylineRoad] = field(default_factory=dict)

    def road_refs(self) -> tuple[str, ...]:
        return tuple(self.roads)

    def road(self, road_ref: str) -> PolylineRoad:
        road = self.roads.get(str(road_ref or ""))
        if road is None:
            raise KeyError(f"road not in context: {road_ref}")
        return road

    def has_road(self, road_ref: str) -> bool:
        road = self.roads.get(str(road_ref or ""))
        return road is not None and len(road.stations) >= 2

    def station_range(self, road_ref: str) -> tuple[float, float]:
        road = self.road(road_ref)
        return road.stations[0], road.stations[-1]

    def point_xy(self, road_ref: str, station: float) -> tuple[float, float]:
        road = self.road(road_ref)
        index, ratio = _segment_at(road.stations, station)
        (x0, y0), (x1, y1) = road.xy[index], road.xy[index + 1]
        return x0 + (x1 - x0) * ratio, y0 + (y1 - y0) * ratio

    def tangent_xy(self, road_ref: str, station: float) -> tuple[float, float]:
        road = self.road(road_ref)
        stations = road.stations
        index, _ratio = _segment_at(stations, station)
        direction = _unit(road.xy[index], road.xy[index + 1])
        # at an interior vertex the tangent is the mean of the two segments, so that an offset
        # sampled at the vertex bisects the corner instead of jumping to one side of it
        at_start = abs(float(station) - stations[index]) <= STATION_TOLERANCE_M and index > 0
        at_end = abs(float(station) - stations[index + 1]) <= STATION_TOLERANCE_M and index + 2 < len(stations)
        if at_start:
            direction = _mean_unit(_unit(road.xy[index - 1], road.xy[index]), direction)
        elif at_end:
            direction = _mean_unit(direction, _unit(road.xy[index + 1], road.xy[index + 2]))
        return direction

    def crossings(self, road_a: str, road_b: str) -> tuple[Crossing, ...]:
        a, b = self.road(road_a), self.road(road_b)
        found: list[Crossing] = []
        for i in range(len(a.stations) - 1):
            for j in range(len(b.stations) - 1):
                hit = segment_intersection(a.xy[i], a.xy[i + 1], b.xy[j], b.xy[j + 1])
                if hit is None:
                    continue
                t, u = hit
                x = a.xy[i][0] + (a.xy[i + 1][0] - a.xy[i][0]) * t
                y = a.xy[i][1] + (a.xy[i + 1][1] - a.xy[i][1]) * t
                station_a = a.stations[i] + (a.stations[i + 1] - a.stations[i]) * t
                station_b = b.stations[j] + (b.stations[j + 1] - b.stations[j]) * u
                # a crossing at a shared vertex is found from both segments next to it
                if any(math.hypot(x - row.x, y - row.y) <= STATION_TOLERANCE_M for row in found):
                    continue
                found.append(Crossing(x, y, station_a, station_b))
        return tuple(found)

    def pavement_half_width(self, road_ref: str, station: float, side: str) -> float | None:
        rows = self.road(road_ref).half_width_rows
        if not rows:
            return None
        column = 1 if str(side) == "left" else 2
        value = _interpolate_rows([(row[0], row[column]) for row in rows], station)
        return value if value > 0.0 else None

    def finished_grade_z(self, road_ref: str, station: float) -> float | None:
        rows = self.road(road_ref).grade_rows
        if not rows:
            return None
        return _interpolate_rows(list(rows), station)

    def vertex_stations(self, road_ref: str, start: float, end: float) -> tuple[float, ...]:
        road = self.road(road_ref)
        low, high = min(start, end), max(start, end)
        values = [s for s in road.stations if low + STATION_TOLERANCE_M < s < high - STATION_TOLERANCE_M]
        values += [row[0] for row in road.half_width_rows if low + STATION_TOLERANCE_M < row[0] < high - STATION_TOLERANCE_M]
        return tuple(sorted(set(values)))

    def fingerprint_rows(self, road_ref: str) -> tuple[str, ...]:
        road = self.road(road_ref)
        rows = [f"road|{road.road_ref}|{road.width_source}"]
        rows += [f"c|{s:.6f}|{x:.6f}|{y:.6f}" for s, (x, y) in zip(road.stations, road.xy)]
        rows += [f"w|{s:.6f}|{left:.6f}|{right:.6f}" for s, left, right in road.half_width_rows]
        rows += [f"z|{s:.6f}|{z:.6f}" for s, z in road.grade_rows]
        return tuple(rows)


def left_normal(direction: tuple[float, float]) -> tuple[float, float]:
    return -direction[1], direction[0]


def segment_intersection(p0, p1, q0, q1) -> tuple[float, float] | None:
    """Return the parameters (t on p, u on q) where two closed segments cross, or None."""

    rx, ry = p1[0] - p0[0], p1[1] - p0[1]
    sx, sy = q1[0] - q0[0], q1[1] - q0[1]
    den = rx * sy - ry * sx
    if abs(den) <= 1.0e-12:
        return None
    dx, dy = q0[0] - p0[0], q0[1] - p0[1]
    t = (dx * sy - dy * sx) / den
    u = (dx * ry - dy * rx) / den
    # the 1e-9 slack keeps a crossing exactly at a segment end from falling between two segments
    if -1.0e-9 <= t <= 1.0 + 1.0e-9 and -1.0e-9 <= u <= 1.0 + 1.0e-9:
        return min(max(t, 0.0), 1.0), min(max(u, 0.0), 1.0)
    return None


def _segment_at(stations: tuple[float, ...], station: float) -> tuple[int, float]:
    if len(stations) < 2:
        raise ValueError("a road needs at least two centreline points")
    value = min(max(float(station), stations[0]), stations[-1])
    index = bisect.bisect_right(stations, value) - 1
    index = min(max(index, 0), len(stations) - 2)
    span = stations[index + 1] - stations[index]
    ratio = 0.0 if span <= 0.0 else (value - stations[index]) / span
    return index, ratio


def _unit(a, b) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= 1.0e-12:
        return 1.0, 0.0
    return dx / length, dy / length


def _mean_unit(a, b) -> tuple[float, float]:
    x, y = a[0] + b[0], a[1] + b[1]
    length = math.hypot(x, y)
    if length <= 1.0e-12:
        return b
    return x / length, y / length


def _interpolate_rows(rows: list[tuple[float, float]], station: float) -> float:
    stations = [row[0] for row in rows]
    value = float(station)
    if value <= stations[0]:
        return float(rows[0][1])
    if value >= stations[-1]:
        return float(rows[-1][1])
    index = bisect.bisect_right(stations, value) - 1
    (s0, v0), (s1, v1) = rows[index], rows[index + 1]
    if s1 - s0 <= 0.0:
        return float(v1)
    return float(v0) + (float(v1) - float(v0)) * (value - s0) / (s1 - s0)
