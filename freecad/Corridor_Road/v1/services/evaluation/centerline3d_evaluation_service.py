"""3D Centerline evaluation service for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from ...models.source.alignment_model import AlignmentModel
from ...models.source.profile_model import ProfileModel
from .alignment_evaluation_service import AlignmentEvaluationService
from .profile_evaluation_service import ProfileEvaluationService


@dataclass(frozen=True)
class Centerline3DEvaluationRequest:
    """Inputs needed to evaluate a shared 3D centerline baseline."""

    project_id: str = "corridorroad-v1"
    alignment_model: AlignmentModel | None = None
    profile_model: ProfileModel | None = None
    station_values: tuple[float, ...] = ()
    stationing_id: str = ""
    source_refs: tuple[str, ...] = ()


class Centerline3DEvaluationService:
    """Evaluate Alignment XY and Profile Z over the accepted station grid."""

    def __init__(self) -> None:
        self._alignment_service = AlignmentEvaluationService()
        self._profile_service = ProfileEvaluationService()

    def evaluate(self, request: Centerline3DEvaluationRequest) -> Centerline3DResult:
        diagnostics: list[str] = []
        alignment = request.alignment_model
        profile = request.profile_model
        stations = tuple(float(value) for value in list(request.station_values or ()))
        if alignment is None:
            diagnostics.append("error|missing_alignment|centerline3d_result|AlignmentModel is required.")
        if profile is None:
            diagnostics.append("error|missing_profile|centerline3d_result|ProfileModel is required.")
        if not stations:
            diagnostics.append("error|missing_stationing|centerline3d_result|Stationing values are required.")
        if diagnostics:
            return Centerline3DResult(
                project_id=str(request.project_id or "corridorroad-v1"),
                alignment_id=str(getattr(alignment, "alignment_id", "") or ""),
                profile_id=str(getattr(profile, "profile_id", "") or ""),
                stationing_id=str(request.stationing_id or ""),
                diagnostic_rows=tuple(diagnostics),
                status="blocked",
                source_refs=tuple(request.source_refs or ()),
            )

        point_rows: list[Centerline3DPointRow] = []
        assert alignment is not None
        assert profile is not None
        for station in stations:
            alignment_result = self._alignment_service.evaluate_station(alignment, station)
            profile_result = self._profile_service.evaluate_station(profile, station)
            row_diagnostics: list[str] = []
            alignment_status = str(getattr(alignment_result, "status", "") or "")
            profile_status = str(getattr(profile_result, "status", "") or "")
            if alignment_status != "ok":
                row_diagnostics.append(f"warning|alignment_station|{station:.3f}|Alignment evaluation status is {alignment_status}.")
            if profile_status != "ok":
                row_diagnostics.append(f"warning|profile_station|{station:.3f}|Profile evaluation status is {profile_status}.")
            diagnostics.extend(row_diagnostics)
            if alignment_status == "ok" and profile_status == "ok":
                point_rows.append(
                    Centerline3DPointRow(
                        station=station,
                        x=float(getattr(alignment_result, "x", 0.0) or 0.0),
                        y=float(getattr(alignment_result, "y", 0.0) or 0.0),
                        z=float(getattr(profile_result, "elevation", 0.0) or 0.0),
                        grade=float(getattr(profile_result, "grade", 0.0) or 0.0),
                        source_alignment_ref=str(getattr(alignment, "alignment_id", "") or ""),
                        source_profile_ref=str(getattr(profile, "profile_id", "") or ""),
                        source_station_ref=str(request.stationing_id or ""),
                        status="ok",
                    )
                )
        status = "ready" if len(point_rows) >= 2 else "blocked"
        if len(point_rows) < 2:
            diagnostics.append("error|not_enough_points|centerline3d_result|At least two evaluated 3D centerline points are required.")
        return Centerline3DResult(
            project_id=str(request.project_id or "corridorroad-v1"),
            alignment_id=str(getattr(alignment, "alignment_id", "") or ""),
            profile_id=str(getattr(profile, "profile_id", "") or ""),
            stationing_id=str(request.stationing_id or ""),
            point_rows=tuple(point_rows),
            diagnostic_rows=tuple(diagnostics),
            status=status,
            source_refs=tuple(value for value in list(request.source_refs or ()) if str(value or "")),
        )
