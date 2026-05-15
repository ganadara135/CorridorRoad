"""Shared frame lookup service for v1 3D Centerline results."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...models.result.centerline3d import Centerline3DResult


@dataclass(frozen=True)
class Centerline3DFrame:
    """Resolved station frame on the shared 3D centerline baseline."""

    station: float
    x: float
    y: float
    z: float
    tangent_direction_deg: float = 0.0
    grade: float = 0.0
    status: str = "ok"
    source_mode: str = "centerline3d_result"
    diagnostic_rows: tuple[str, ...] = field(default_factory=tuple)


class Centerline3DFrameService:
    """Resolve station frames from a shared Centerline3DResult."""

    def resolve_station(self, result: Centerline3DResult | None, station: float) -> Centerline3DFrame:
        """Return an interpolated station frame or a blocked diagnostic frame."""

        active_station = float(station)
        if result is None:
            return _blocked_frame(active_station, "missing_centerline3d_result", "Centerline3DResult is required.")
        rows = sorted(
            [
                row
                for row in list(getattr(result, "point_rows", []) or [])
                if str(getattr(row, "status", "") or "ok") != "error"
            ],
            key=lambda row: float(getattr(row, "station", 0.0) or 0.0),
        )
        if str(getattr(result, "status", "") or "") != "ready" or len(rows) < 2:
            return _blocked_frame(active_station, "centerline3d_not_ready", "Centerline3DResult needs at least two ready point rows.")

        lower = rows[0]
        upper = rows[-1]
        for index in range(len(rows) - 1):
            current = rows[index]
            next_row = rows[index + 1]
            if float(current.station) <= active_station <= float(next_row.station):
                lower = current
                upper = next_row
                break

        span = float(upper.station) - float(lower.station)
        ratio = 0.0 if abs(span) <= 1.0e-12 else max(0.0, min(1.0, (active_station - float(lower.station)) / span))
        x = _lerp(float(lower.x), float(upper.x), ratio)
        y = _lerp(float(lower.y), float(upper.y), ratio)
        z = _lerp(float(lower.z), float(upper.z), ratio)
        grade = _lerp(float(getattr(lower, "grade", 0.0) or 0.0), float(getattr(upper, "grade", 0.0) or 0.0), ratio)
        tangent = math.degrees(math.atan2(float(upper.y) - float(lower.y), float(upper.x) - float(lower.x)))
        diagnostics = []
        if active_station < float(rows[0].station) or active_station > float(rows[-1].station):
            diagnostics.append(
                f"warning|station_outside_centerline3d_range|{active_station:.3f}|Station is outside Centerline3DResult range."
            )
        return Centerline3DFrame(
            station=active_station,
            x=x,
            y=y,
            z=z,
            tangent_direction_deg=tangent,
            grade=grade,
            status="ok" if not diagnostics else "warning",
            diagnostic_rows=tuple(diagnostics),
        )

    def resolve_station_offset(
        self,
        result: Centerline3DResult | None,
        station: float,
        offset: float = 0.0,
    ) -> Centerline3DFrame:
        """Return a station frame shifted by lateral offset in the horizontal normal direction."""

        frame = self.resolve_station(result, station)
        if str(getattr(frame, "status", "") or "") == "blocked":
            return frame
        heading = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        normal_x = -math.sin(heading)
        normal_y = math.cos(heading)
        return Centerline3DFrame(
            station=float(station),
            x=float(frame.x) + float(offset) * normal_x,
            y=float(frame.y) + float(offset) * normal_y,
            z=float(frame.z),
            tangent_direction_deg=float(frame.tangent_direction_deg),
            grade=float(frame.grade),
            status=str(frame.status),
            source_mode=str(frame.source_mode),
            diagnostic_rows=tuple(frame.diagnostic_rows),
        )


def _blocked_frame(station: float, code: str, message: str) -> Centerline3DFrame:
    return Centerline3DFrame(
        station=float(station),
        x=0.0,
        y=0.0,
        z=0.0,
        status="blocked",
        diagnostic_rows=(f"error|{code}|{float(station):.3f}|{message}",),
    )


def _lerp(start: float, end: float, ratio: float) -> float:
    return float(start) + (float(end) - float(start)) * float(ratio)
