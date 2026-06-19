"""Contract tests for the v1 Alignment curve preview service."""

from __future__ import annotations

from freecad.Corridor_Road.v1.models.source import AlignmentModel
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement
from freecad.Corridor_Road.v1.services.evaluation import (
    AlignmentCurvePreviewRequest,
    AlignmentCurvePreviewService,
)


def _sample_alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:test",
        geometry_sequence=[
            AlignmentElement(
                element_id="element:tangent",
                kind="tangent",
                station_start=0.0,
                station_end=50.0,
                length=50.0,
                geometry_payload={"x_values": [0.0, 50.0], "y_values": [0.0, 0.0]},
            ),
            AlignmentElement(
                element_id="element:curve",
                kind="sampled_curve",
                station_start=50.0,
                station_end=100.0,
                length=60.0,
                geometry_payload={"x_values": [50.0, 75.0, 100.0], "y_values": [0.0, 20.0, 20.0]},
            ),
        ],
    )


def test_alignment_curve_preview_returns_evaluated_and_source_points() -> None:
    result = AlignmentCurvePreviewService().evaluate(
        AlignmentCurvePreviewRequest(alignment=_sample_alignment(), sample_interval=10.0)
    )

    assert result.status == "ready"
    assert result.alignment_id == "alignment:test"
    assert any(row.role == "evaluated_path" for row in result.point_rows)
    assert any(row.role == "source_points" for row in result.point_rows)
    assert any(row.element_ref == "element:curve" for row in result.point_rows)
    assert any(row.kind == "alignment_curve_preview_ok" for row in result.diagnostic_rows)


def test_alignment_curve_preview_reports_curve_direction_and_boundaries() -> None:
    result = AlignmentCurvePreviewService().evaluate(
        AlignmentCurvePreviewRequest(alignment=_sample_alignment(), sample_interval=25.0)
    )

    curve_rows = [row for row in result.element_rows if row.element_id == "element:curve"]
    assert len(curve_rows) == 1
    assert curve_rows[0].point_count == 3
    assert curve_rows[0].curve_direction in {"left", "right"}
    assert curve_rows[0].radius > 0.0
    assert curve_rows[0].central_angle_deg > 0.0
    assert any(row.kind == "Element Start" and row.element_ref == "element:curve" for row in result.annotation_rows)
    assert any(row.kind == "Element End" and row.element_ref == "element:curve" for row in result.annotation_rows)
    assert any(row.kind == "PC" and row.element_ref == "element:curve" for row in result.annotation_rows)
    assert any(row.kind == "PI" and row.element_ref == "element:curve" for row in result.annotation_rows)
    assert any(row.kind == "PT" and row.element_ref == "element:curve" for row in result.annotation_rows)
    assert any(row.kind == "Curve Center" and row.element_ref == "element:curve" for row in result.annotation_rows)
    assert any(row.kind == "Radius" and row.value for row in result.annotation_rows)
    assert any(row.kind == "Delta Angle" and row.value for row in result.annotation_rows)
    assert any(row.kind == "Curve Direction" and row.value for row in result.annotation_rows)
    assert any(row.kind == "Tangent In" and row.value for row in result.annotation_rows)
    assert any(row.kind == "Tangent Out" and row.value for row in result.annotation_rows)
    assert any(row.kind == "alignment_curve_pc_pi_pt_estimated" for row in result.diagnostic_rows)
    assert any(row.kind == "alignment_curve_radius_delta_labeled" for row in result.diagnostic_rows)
    assert any(row.kind == "alignment_curve_tangent_helpers_labeled" for row in result.diagnostic_rows)


def test_alignment_curve_preview_reports_missing_geometry() -> None:
    alignment = AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:bad-curve",
        geometry_sequence=[
            AlignmentElement(
                element_id="element:bad-curve",
                kind="sampled_curve",
                station_start=0.0,
                station_end=20.0,
                geometry_payload={"x_values": [0.0], "y_values": [0.0]},
            )
        ],
    )

    result = AlignmentCurvePreviewService().evaluate(
        AlignmentCurvePreviewRequest(alignment=alignment, sample_interval=5.0)
    )

    assert result.status == "ready"
    assert any(row.kind == "alignment_curve_missing_geometry" for row in result.diagnostic_rows)
    assert any(row.kind == "alignment_curve_pc_pi_pt_estimated" for row in result.diagnostic_rows)
    assert any(row.status == "warning" for row in result.element_rows)


if __name__ == "__main__":
    test_alignment_curve_preview_returns_evaluated_and_source_points()
    test_alignment_curve_preview_reports_curve_direction_and_boundaries()
    test_alignment_curve_preview_reports_missing_geometry()
    print("PASS Alignment curve preview service contract validation")
