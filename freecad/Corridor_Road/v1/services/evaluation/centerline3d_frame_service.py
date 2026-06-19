"""Shared frame lookup service for v1 3D Centerline results."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...models.result.centerline3d import Centerline3DResult
from .centerline3d_source_geometry_service import (
    ARC_FIT_ABSOLUTE_TOLERANCE,
    ARC_FIT_RELATIVE_TOLERANCE,
    Centerline3DSourceGeometryService,
)


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

    def __init__(self, source_geometry_service: Centerline3DSourceGeometryService | None = None) -> None:
        self.source_geometry_service = source_geometry_service or Centerline3DSourceGeometryService()

    def resolve_station(
        self,
        result: Centerline3DResult | None,
        station: float,
        *,
        alignment=None,
        profile=None,
        arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
        arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    ) -> Centerline3DFrame:
        """Return an interpolated station frame or a blocked diagnostic frame."""

        active_station = float(station)
        source_diagnostics: list[str] = []
        if alignment is not None and profile is not None:
            source_frame = self.source_geometry_service.evaluate_station(
                alignment,
                profile,
                active_station,
                arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
                arc_fit_relative_tolerance=arc_fit_relative_tolerance,
            )
            source_diagnostics.extend(list(getattr(source_frame, "diagnostic_rows", []) or []))
            if str(getattr(source_frame, "status", "") or "") in {"ok", "warning"}:
                return Centerline3DFrame(
                    station=active_station,
                    x=float(getattr(source_frame, "x", 0.0) or 0.0),
                    y=float(getattr(source_frame, "y", 0.0) or 0.0),
                    z=float(getattr(source_frame, "z", 0.0) or 0.0),
                    tangent_direction_deg=float(getattr(source_frame, "tangent_direction_deg", 0.0) or 0.0),
                    grade=float(getattr(source_frame, "grade", 0.0) or 0.0),
                    status=str(getattr(source_frame, "status", "") or "ok"),
                    source_mode=str(getattr(source_frame, "source_mode", "") or "centerline3d_source_geometry"),
                    diagnostic_rows=tuple(source_diagnostics),
                )
        if result is None:
            return _blocked_frame(
                active_station,
                "missing_centerline3d_result",
                "Centerline3DResult is required.",
                source_diagnostics=source_diagnostics,
            )
        rows = sorted(
            [
                row
                for row in list(getattr(result, "point_rows", []) or [])
                if str(getattr(row, "status", "") or "ok") != "error"
            ],
            key=lambda row: float(getattr(row, "station", 0.0) or 0.0),
        )
        if str(getattr(result, "status", "") or "") != "ready" or len(rows) < 2:
            return _blocked_frame(
                active_station,
                "centerline3d_not_ready",
                "Centerline3DResult needs at least two ready point rows.",
                source_diagnostics=source_diagnostics,
            )

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
        span_abs = abs(float(upper.station) - float(lower.station))
        if span_abs <= 5.0 + 1.0e-6:
            diagnostics.append(
                f"info|centerline3d_frame_source_evaluated|{active_station:.3f}|Frame resolved from dense Centerline3DResult segment."
            )
        else:
            diagnostics.append(
                f"warning|centerline3d_frame_sparse_chord_fallback|{active_station:.3f}|"
                f"Frame used sparse point-row chord interpolation over {span_abs:.3f} station units."
            )
        if active_station < float(rows[0].station) or active_station > float(rows[-1].station):
            diagnostics.append(
                f"warning|station_outside_centerline3d_range|{active_station:.3f}|Station is outside Centerline3DResult range."
            )
        diagnostics = [*source_diagnostics, *diagnostics]
        return Centerline3DFrame(
            station=active_station,
            x=x,
            y=y,
            z=z,
            tangent_direction_deg=tangent,
            grade=grade,
            status="warning" if any(str(row).startswith("warning|") for row in diagnostics) else "ok",
            diagnostic_rows=tuple(diagnostics),
        )

    def resolve_station_offset(
        self,
        result: Centerline3DResult | None,
        station: float,
        offset: float = 0.0,
        *,
        alignment=None,
        profile=None,
        arc_fit_absolute_tolerance: float = ARC_FIT_ABSOLUTE_TOLERANCE,
        arc_fit_relative_tolerance: float = ARC_FIT_RELATIVE_TOLERANCE,
    ) -> Centerline3DFrame:
        """Return a station frame shifted by lateral offset in the horizontal normal direction."""

        frame = self.resolve_station(
            result,
            station,
            alignment=alignment,
            profile=profile,
            arc_fit_absolute_tolerance=arc_fit_absolute_tolerance,
            arc_fit_relative_tolerance=arc_fit_relative_tolerance,
        )
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


def _blocked_frame(station: float, code: str, message: str, *, source_diagnostics: list[str] | None = None) -> Centerline3DFrame:
    return Centerline3DFrame(
        station=float(station),
        x=0.0,
        y=0.0,
        z=0.0,
        status="blocked",
        diagnostic_rows=tuple([*(source_diagnostics or []), f"error|{code}|{float(station):.3f}|{message}"]),
    )


def _lerp(start: float, end: float, ratio: float) -> float:
    return float(start) + (float(end) - float(start)) * float(ratio)
