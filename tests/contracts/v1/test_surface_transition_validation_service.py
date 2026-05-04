from freecad.Corridor_Road.v1.models.source.surface_transition_model import (
    SurfaceTransitionModel,
    SurfaceTransitionRange,
)
from freecad.Corridor_Road.v1.services.evaluation.surface_transition_validation_service import (
    SurfaceTransitionValidationService,
)


def test_surface_transition_validation_accepts_boundary_centered_range() -> None:
    model = SurfaceTransitionModel(
        schema_version=1,
        project_id="proj-1",
        transition_model_id="surface-transitions:main",
        corridor_ref="corridor:main",
        transition_ranges=[
            SurfaceTransitionRange(
                "transition:100",
                95.0,
                105.0,
                from_region_ref="region:a",
                to_region_ref="region:b",
                approval_status="active",
            )
        ],
    )

    result = SurfaceTransitionValidationService().validate(
        model,
        known_region_refs=["region:a", "region:b"],
        boundary_stations=[100.0],
    )

    assert result.status == "ok"
    assert result.diagnostic_rows == []


def test_surface_transition_validation_reports_invalid_range_and_duplicate_id() -> None:
    model = SurfaceTransitionModel(
        schema_version=1,
        project_id="proj-1",
        transition_ranges=[
            SurfaceTransitionRange("transition:bad", 100.0, 95.0, from_region_ref="region:a", to_region_ref="region:b"),
            SurfaceTransitionRange("transition:bad", 98.0, 102.0, from_region_ref="region:a", to_region_ref="region:b"),
        ],
    )

    result = SurfaceTransitionValidationService().validate(model, boundary_stations=[100.0])

    kinds = [row.kind for row in result.diagnostic_rows]
    assert result.status == "error"
    assert "invalid_station_range" in kinds
    assert "duplicate_transition_id" in kinds


def test_surface_transition_validation_warns_when_range_misses_known_boundary() -> None:
    model = SurfaceTransitionModel(
        schema_version=1,
        project_id="proj-1",
        transition_ranges=[
            SurfaceTransitionRange(
                "transition:miss",
                80.0,
                90.0,
                from_region_ref="region:a",
                to_region_ref="region:b",
            )
        ],
    )

    result = SurfaceTransitionValidationService().validate(model, boundary_stations=[100.0])

    assert result.status == "warning"
    assert [row.kind for row in result.diagnostic_rows] == ["transition_surface_no_boundary_context"]


def test_surface_transition_validation_warns_for_missing_region_reference() -> None:
    model = SurfaceTransitionModel(
        schema_version=1,
        project_id="proj-1",
        transition_ranges=[
            SurfaceTransitionRange(
                "transition:missing-region",
                95.0,
                105.0,
                from_region_ref="region:a",
                to_region_ref="region:missing",
            )
        ],
    )

    result = SurfaceTransitionValidationService().validate(
        model,
        known_region_refs=["region:a"],
        boundary_stations=[100.0],
    )

    assert result.status == "warning"
    assert [row.kind for row in result.diagnostic_rows] == ["missing_region_ref"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] surface transition validation service tests completed.")
