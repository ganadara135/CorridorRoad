"""Contract tests for Alignment editor curve preview wiring."""

from __future__ import annotations

from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import alignment_model_from_editor_rows
from freecad.Corridor_Road.v1.services.evaluation import (
    AlignmentCurvePreviewRequest,
    AlignmentCurvePreviewService,
)


def test_alignment_editor_rows_feed_curve_preview_service() -> None:
    model = alignment_model_from_editor_rows(
        [
            {
                "element_id": "alignment:test:compiled:1",
                "kind": "tangent",
                "station_start": 0.0,
                "station_end": 50.0,
                "length": 50.0,
                "x_values": "0.0,50.0",
                "y_values": "0.0,0.0",
            },
            {
                "element_id": "alignment:test:compiled:2",
                "kind": "sampled_curve",
                "station_start": 50.0,
                "station_end": 100.0,
                "length": 60.0,
                "x_values": "50.0,75.0,100.0",
                "y_values": "0.0,20.0,20.0",
            },
        ],
        alignment_id="alignment:test-preview",
        label="Test Preview",
    )

    result = AlignmentCurvePreviewService().evaluate(
        AlignmentCurvePreviewRequest(alignment=model, sample_interval=10.0)
    )

    assert model.alignment_id == "alignment:test-preview"
    assert len(model.geometry_sequence) == 2
    assert result.status == "ready"
    assert any(row.kind == "PC" for row in result.annotation_rows)
    assert any(row.kind == "PI" for row in result.annotation_rows)
    assert any(row.kind == "PT" for row in result.annotation_rows)
    assert any(row.kind == "Radius" and row.value for row in result.annotation_rows)
    assert any(row.kind == "Delta Angle" and row.value for row in result.annotation_rows)
    assert any(row.kind == "alignment_curve_pc_pi_pt_estimated" for row in result.diagnostic_rows)


if __name__ == "__main__":
    test_alignment_editor_rows_feed_curve_preview_service()
    print("PASS Alignment editor curve preview wiring validation")
