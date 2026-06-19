"""Contract tests for 3D Centerline consistency with curve previews."""

from __future__ import annotations

from freecad.Corridor_Road.v1.models.result.centerline3d import Centerline3DPointRow, Centerline3DResult
from freecad.Corridor_Road.v1.models.source import AlignmentModel
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint, ProfileModel, VerticalCurveRow
from freecad.Corridor_Road.v1.services.evaluation import (
    AlignmentCurvePreviewRequest,
    AlignmentCurvePreviewService,
    Centerline3DConsistencyRequest,
    Centerline3DConsistencyService,
    Centerline3DEvaluationRequest,
    Centerline3DEvaluationService,
    ProfileCurvePreviewRequest,
    ProfileCurvePreviewService,
)


def _alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:test:tangent",
                kind="tangent",
                station_start=0.0,
                station_end=50.0,
                length=50.0,
                geometry_payload={"x_values": [0.0, 50.0], "y_values": [0.0, 0.0]},
            ),
            AlignmentElement(
                element_id="alignment:test:curve",
                kind="sampled_curve",
                station_start=50.0,
                station_end=100.0,
                length=60.0,
                geometry_payload={"x_values": [50.0, 75.0, 100.0], "y_values": [0.0, 20.0, 20.0]},
            ),
        ],
    )


def _profile() -> ProfileModel:
    return ProfileModel(
        schema_version=1,
        project_id="test-project",
        profile_id="profile:test",
        alignment_id="alignment:test",
        control_rows=[
            ProfileControlPoint("pvi:1", 0.0, 10.0, "grade_break"),
            ProfileControlPoint("pvi:2", 50.0, 30.0, "pvi"),
            ProfileControlPoint("pvi:3", 100.0, 10.0, "grade_break"),
        ],
        vertical_curve_rows=[
            VerticalCurveRow(
                vertical_curve_id="vc:1",
                kind="parabolic_vertical_curve",
                station_start=25.0,
                station_end=75.0,
                curve_length=50.0,
            )
        ],
    )


def _preview_and_centerline():
    alignment = _alignment()
    profile = _profile()
    alignment_preview = AlignmentCurvePreviewService().evaluate(
        AlignmentCurvePreviewRequest(alignment=alignment, sample_interval=5.0)
    )
    profile_preview = ProfileCurvePreviewService().evaluate(
        ProfileCurvePreviewRequest(profile=profile, sample_interval=5.0)
    )
    centerline = Centerline3DEvaluationService().evaluate(
        Centerline3DEvaluationRequest(
            alignment_model=alignment,
            profile_model=profile,
            station_values=(0.0, 50.0, 100.0),
            stationing_id="stationing:test",
        )
    )
    return alignment_preview, profile_preview, centerline


def test_centerline3d_consistency_matches_alignment_and_profile_previews() -> None:
    alignment_preview, profile_preview, centerline = _preview_and_centerline()

    result = Centerline3DConsistencyService().evaluate(
        Centerline3DConsistencyRequest(
            centerline3d_result=centerline,
            alignment_preview=alignment_preview,
            profile_preview=profile_preview,
            station_tolerance=1.0e-6,
            horizontal_tolerance=1.0e-6,
            vertical_tolerance=1.0e-6,
        )
    )

    assert centerline.status == "ready"
    assert result.status == "ready"
    assert result.compared_alignment_samples > 0
    assert result.compared_profile_samples > 0
    assert result.mismatch_count == 0
    assert any(row.kind == "centerline3d_preview_consistency_ok" for row in result.diagnostic_rows)


def test_centerline3d_consistency_reports_curve_sample_mismatch() -> None:
    alignment_preview, profile_preview, centerline = _preview_and_centerline()
    rows = list(centerline.point_rows)
    middle = rows[len(rows) // 2]
    rows[len(rows) // 2] = Centerline3DPointRow(
        station=middle.station,
        x=middle.x + 1.0,
        y=middle.y,
        z=middle.z,
        grade=middle.grade,
        source_alignment_ref=middle.source_alignment_ref,
        source_profile_ref=middle.source_profile_ref,
        source_station_ref=middle.source_station_ref,
        status=middle.status,
        diagnostic_refs=middle.diagnostic_refs,
    )
    shifted = Centerline3DResult(
        schema_version=centerline.schema_version,
        project_id=centerline.project_id,
        centerline3d_result_id=centerline.centerline3d_result_id,
        alignment_id=centerline.alignment_id,
        profile_id=centerline.profile_id,
        stationing_id=centerline.stationing_id,
        point_rows=tuple(rows),
        diagnostic_rows=centerline.diagnostic_rows,
        status=centerline.status,
        source_refs=centerline.source_refs,
    )

    result = Centerline3DConsistencyService().evaluate(
        Centerline3DConsistencyRequest(
            centerline3d_result=shifted,
            alignment_preview=alignment_preview,
            profile_preview=profile_preview,
            station_tolerance=1.0e-6,
            horizontal_tolerance=1.0e-6,
            vertical_tolerance=1.0e-6,
        )
    )

    assert result.status == "warning"
    assert result.mismatch_count > 0
    assert any(row.kind == "centerline3d_curve_sample_mismatch" for row in result.diagnostic_rows)


if __name__ == "__main__":
    test_centerline3d_consistency_matches_alignment_and_profile_previews()
    test_centerline3d_consistency_reports_curve_sample_mismatch()
    print("PASS Centerline3D preview consistency validation")
