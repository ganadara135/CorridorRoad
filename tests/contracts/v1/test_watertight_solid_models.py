from freecad.Corridor_Road.v1.models.source.solid_target_model import (
    SolidTargetDiagnosticRow,
    SolidTargetModel,
    SolidTargetRow,
)


def test_solid_target_row_normalizes_family_scope_status_and_refs() -> None:
    row = SolidTargetRow(
        target_id="target:1",
        target_family="Region Body",
        scope_kind="Region",
        readiness_status="Available",
        source_refs=["section:set", "section:set", "corridor:main"],
        diagnostic_refs="diag:1,diag:1;diag:2",
    )

    assert row.target_family == "region_body"
    assert row.scope_kind == "region"
    assert row.readiness_status == "available"
    assert row.source_refs == ["section:set", "corridor:main"]
    assert row.diagnostic_refs == ["diag:1", "diag:2"]


def test_solid_target_row_accepts_intersection_zone_families() -> None:
    row = SolidTargetRow(
        target_id="solid-target:intersection-slope:intersection-t-01:zone-1",
        target_family="Intersection Slope Body",
        scope_kind="Intersection",
        readiness_status="Planned",
    )

    assert row.target_family == "intersection_slope_body"
    assert row.scope_kind == "intersection"
    assert row.readiness_status == "planned"


def test_solid_target_model_preserves_rows_and_diagnostics() -> None:
    row = SolidTargetRow(
        target_id="solid-target:road-body-envelope",
        target_family="road_body_envelope",
        scope_kind="whole_corridor",
        station_start=0.0,
        station_end=100.0,
    )
    diagnostic = SolidTargetDiagnosticRow(
        diagnostic_id="diag:solid:1",
        severity="warning",
        kind="planned_geometry",
        source_ref=row.target_id,
        message="Topology builder is not implemented yet.",
    )

    model = SolidTargetModel(
        schema_version=1,
        project_id="proj-1",
        solid_target_model_id="solid-targets:main",
        corridor_ref="corridor:main",
        target_rows=[row],
        target_diagnostic_rows=[diagnostic],
    )

    assert model.target_rows[0].target_id == "solid-target:road-body-envelope"
    assert model.target_diagnostic_rows[0].source_ref == row.target_id
