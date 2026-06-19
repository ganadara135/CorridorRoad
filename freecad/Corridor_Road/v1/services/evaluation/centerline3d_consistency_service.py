"""Consistency checks between curve previews and the 3D Centerline result."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.result.alignment_curve_preview import AlignmentCurvePreviewResult
from ...models.result.centerline3d import Centerline3DResult
from ...models.result.profile_curve_preview import ProfileCurvePreviewResult


@dataclass(frozen=True)
class Centerline3DConsistencyRequest:
    """Inputs for comparing preview samples against the shared 3D Centerline."""

    centerline3d_result: Centerline3DResult | None = None
    alignment_preview: AlignmentCurvePreviewResult | None = None
    profile_preview: ProfileCurvePreviewResult | None = None
    station_tolerance: float = 1.0e-6
    horizontal_tolerance: float = 1.0e-6
    vertical_tolerance: float = 1.0e-6


@dataclass(frozen=True)
class Centerline3DConsistencyResult:
    """Read-only consistency result for preview and 3D Centerline agreement."""

    status: str = "empty"
    compared_alignment_samples: int = 0
    compared_profile_samples: int = 0
    mismatch_count: int = 0
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


class Centerline3DConsistencyService:
    """Compare Alignment/Profile preview rows with Centerline3D point rows."""

    def evaluate(self, request: Centerline3DConsistencyRequest) -> Centerline3DConsistencyResult:
        diagnostics: list[DiagnosticMessage] = []
        centerline = request.centerline3d_result
        if centerline is None or str(getattr(centerline, "status", "") or "") != "ready":
            return Centerline3DConsistencyResult(
                status="blocked",
                diagnostic_rows=[
                    DiagnosticMessage(
                        "error",
                        "centerline3d_consistency_missing_result",
                        "Ready Centerline3DResult is required for preview consistency checks.",
                    )
                ],
            )

        centerline_rows = list(getattr(centerline, "point_rows", []) or [])
        alignment_rows = [
            row
            for row in list(getattr(request.alignment_preview, "point_rows", []) or [])
            if str(getattr(row, "role", "") or "") == "evaluated_path"
        ]
        profile_rows = [
            row
            for row in list(getattr(request.profile_preview, "point_rows", []) or [])
            if str(getattr(row, "role", "") or "") == "evaluated_curve"
        ]

        alignment_compared, alignment_mismatches = _compare_alignment_rows(
            centerline_rows,
            alignment_rows,
            station_tolerance=max(float(request.station_tolerance), 0.0),
            horizontal_tolerance=max(float(request.horizontal_tolerance), 0.0),
        )
        profile_compared, profile_mismatches = _compare_profile_rows(
            centerline_rows,
            profile_rows,
            station_tolerance=max(float(request.station_tolerance), 0.0),
            vertical_tolerance=max(float(request.vertical_tolerance), 0.0),
        )
        diagnostics.extend(alignment_mismatches)
        diagnostics.extend(profile_mismatches)

        if not alignment_rows:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "centerline3d_alignment_preview_missing",
                    "Alignment preview evaluated path rows are missing.",
                )
            )
        if not profile_rows:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "centerline3d_profile_preview_missing",
                    "Profile preview evaluated curve rows are missing.",
                )
            )
        if alignment_compared == 0 and alignment_rows:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "centerline3d_alignment_preview_no_common_stations",
                    "Alignment preview and 3D Centerline have no common station samples.",
                )
            )
        if profile_compared == 0 and profile_rows:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "centerline3d_profile_preview_no_common_stations",
                    "Profile preview and 3D Centerline have no common station samples.",
                )
            )

        mismatch_count = len(
            [row for row in diagnostics if str(getattr(row, "kind", "") or "") == "centerline3d_curve_sample_mismatch"]
        )
        if mismatch_count:
            status = "warning"
        elif any(str(getattr(row, "severity", "") or "") == "error" for row in diagnostics):
            status = "blocked"
        else:
            status = "ready"
            diagnostics.append(
                DiagnosticMessage(
                    "info",
                    "centerline3d_preview_consistency_ok",
                    "3D Centerline samples match available Alignment/Profile preview samples at common stations.",
                )
            )
        return Centerline3DConsistencyResult(
            status=status,
            compared_alignment_samples=alignment_compared,
            compared_profile_samples=profile_compared,
            mismatch_count=mismatch_count,
            diagnostic_rows=diagnostics,
        )


def _compare_alignment_rows(
    centerline_rows,
    alignment_rows,
    *,
    station_tolerance: float,
    horizontal_tolerance: float,
) -> tuple[int, list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    compared = 0
    for preview in alignment_rows:
        centerline = _find_station_row(centerline_rows, float(getattr(preview, "station", 0.0) or 0.0), station_tolerance)
        if centerline is None:
            continue
        compared += 1
        dx = abs(float(getattr(centerline, "x", 0.0) or 0.0) - float(getattr(preview, "x", 0.0) or 0.0))
        dy = abs(float(getattr(centerline, "y", 0.0) or 0.0) - float(getattr(preview, "y", 0.0) or 0.0))
        if max(dx, dy) > horizontal_tolerance:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "centerline3d_curve_sample_mismatch",
                    f"Alignment preview XY and 3D Centerline XY differ at station {float(preview.station):.3f}.",
                    notes=f"dx={dx:.9f}; dy={dy:.9f}",
                )
            )
    return compared, diagnostics


def _compare_profile_rows(
    centerline_rows,
    profile_rows,
    *,
    station_tolerance: float,
    vertical_tolerance: float,
) -> tuple[int, list[DiagnosticMessage]]:
    diagnostics: list[DiagnosticMessage] = []
    compared = 0
    for preview in profile_rows:
        centerline = _find_station_row(centerline_rows, float(getattr(preview, "station", 0.0) or 0.0), station_tolerance)
        if centerline is None:
            continue
        compared += 1
        dz = abs(float(getattr(centerline, "z", 0.0) or 0.0) - float(getattr(preview, "elevation", 0.0) or 0.0))
        if dz > vertical_tolerance:
            diagnostics.append(
                DiagnosticMessage(
                    "warning",
                    "centerline3d_curve_sample_mismatch",
                    f"Profile preview elevation and 3D Centerline Z differ at station {float(preview.station):.3f}.",
                    notes=f"dz={dz:.9f}",
                )
            )
    return compared, diagnostics


def _find_station_row(rows, station: float, tolerance: float):
    for row in list(rows or []):
        if abs(float(getattr(row, "station", 0.0) or 0.0) - float(station)) <= float(tolerance):
            return row
    return None
