from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.services.evaluation.region_resolution_service import (
    RegionResolutionService,
    RegionValidationService,
)


def test_region_row_supports_primary_kind_layers_and_domain_refs() -> None:
    row = RegionRow(
        region_id="region:bridge-01",
        region_index=3,
        primary_kind="bridge",
        applied_layers="ditch, drainage, ditch",
        station_start=120.0,
        station_end=180.0,
        assembly_ref="assembly:bridge-deck",
        structure_refs="structure:bridge-01",
        drainage_refs=["drainage:deck-drain-left", "drainage:side-ditch-right"],
        priority=80,
    )

    assert row.primary_kind == "bridge"
    assert row.applied_layers == ["ditch", "drainage"]
    assert row.structure_ref == "structure:bridge-01"
    assert row.structure_refs == ["structure:bridge-01"]
    assert row.drainage_refs == ["drainage:deck-drain-left", "drainage:side-ditch-right"]


def test_region_row_singular_structure_ref_populates_compatibility_refs() -> None:
    row = RegionRow(
        region_id="region:wall-01",
        station_start=0.0,
        station_end=50.0,
        assembly_ref="assembly:road",
        structure_ref="structure:wall-01",
    )

    assert row.structure_ref == "structure:wall-01"
    assert row.structure_refs == ["structure:wall-01"]


def test_region_resolution_selects_highest_priority_overlap() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:normal",
                region_index=1,
                primary_kind="normal_road",
                station_start=0.0,
                station_end=200.0,
                template_ref="template:road",
                priority=10,
            ),
            RegionRow(
                region_id="region:bridge",
                region_index=2,
                primary_kind="bridge",
                applied_layers=["ditch", "drainage"],
                station_start=120.0,
                station_end=180.0,
                assembly_ref="assembly:bridge-deck",
                template_ref="template:bridge",
                structure_refs=["structure:bridge-01"],
                drainage_refs=["drainage:deck-drain-left"],
                priority=80,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(model, 150.0)

    assert result.active_region_id == "region:bridge"
    assert result.active_primary_kind == "bridge"
    assert result.active_applied_layers == ["ditch", "drainage"]
    assert result.active_assembly_ref == "assembly:bridge-deck"
    assert result.resolved_structure_ref == "structure:bridge-01"
    assert result.resolved_structure_refs == ["structure:bridge-01"]
    assert result.resolved_drainage_refs == ["drainage:deck-drain-left"]
    assert result.overlap_region_ids == ["region:normal"]


def test_region_handoff_summary_preserves_downstream_refs_and_review_rows() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:main",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:normal",
                region_index=1,
                primary_kind="normal_road",
                station_start=0.0,
                station_end=200.0,
                assembly_ref="assembly:road",
                priority=10,
            ),
            RegionRow(
                region_id="region:bridge",
                region_index=2,
                primary_kind="bridge",
                applied_layers=["ditch", "drainage"],
                station_start=120.0,
                station_end=180.0,
                assembly_ref="assembly:bridge-deck",
                template_ref="template:bridge",
                structure_refs=["structure:bridge-01"],
                drainage_refs=["drainage:deck-drain-left"],
                override_refs=["override:bridge-shoulder"],
                priority=80,
            ),
        ],
    )

    summary = RegionResolutionService().resolve_handoff(model, 150.0)
    review_items = {item.row_id: item for item in summary.to_review_items()}

    assert summary.region_id == "region:bridge"
    assert summary.primary_kind == "bridge"
    assert summary.applied_layers == ["ditch", "drainage"]
    assert summary.assembly_ref == "assembly:bridge-deck"
    assert summary.template_ref == "template:bridge"
    assert summary.structure_ref == "structure:bridge-01"
    assert summary.structure_refs == ["structure:bridge-01"]
    assert summary.drainage_refs == ["drainage:deck-drain-left"]
    assert summary.override_refs == ["override:bridge-shoulder"]
    assert summary.overlap_region_ids == ["region:normal"]
    assert "bridge" in summary.summary_text
    assert review_items["region:primary_kind"].value == "bridge"
    assert review_items["region:structures"].value == "structure:bridge-01"


def test_region_validation_warns_when_region_has_multiple_structure_refs() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:multiple-structures",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:bridge",
                primary_kind="bridge",
                station_start=0.0,
                station_end=50.0,
                assembly_ref="assembly:bridge",
                structure_refs=["structure:bridge-01", "structure:wall-01"],
            )
        ],
    )

    result = RegionValidationService().validate(model)

    assert result.status == "warning"
    assert [row.kind for row in result.diagnostic_rows] == ["multiple_structure_refs"]


def test_region_validation_warns_when_assembly_ref_is_unknown() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:assembly-refs",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:missing-assembly",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=50.0,
                assembly_ref="assembly:missing",
            )
        ],
    )

    result = RegionValidationService().validate(model, known_assembly_refs=["assembly:road"])

    assert result.status == "warning"
    assert [row.kind for row in result.diagnostic_rows] == ["missing_assembly_ref"]
    assert "assembly:missing" in result.diagnostic_rows[0].message


def test_region_validation_warns_when_structure_ref_is_unknown() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:structure-refs",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:missing-structure",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=50.0,
                assembly_ref="assembly:road",
                structure_ref="structure:missing",
            )
        ],
    )

    result = RegionResolutionService().validate(
        model,
        known_assembly_refs=["assembly:road"],
        known_structure_refs=["structure:bridge-01"],
    )

    assert result.status == "warning"
    assert [row.kind for row in result.diagnostic_rows] == ["missing_structure_ref"]
    assert "structure:missing" in result.diagnostic_rows[0].message


def test_region_validation_warns_when_structure_required_kind_has_no_structure_ref() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:required-structure",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:bridge-without-structure",
                primary_kind="bridge",
                station_start=0.0,
                station_end=50.0,
                assembly_ref="assembly:bridge",
            )
        ],
    )

    result = RegionValidationService().validate(model)

    assert result.status == "warning"
    assert [row.kind for row in result.diagnostic_rows] == ["missing_required_structure_ref"]
    assert "bridge" in result.diagnostic_rows[0].message


def test_region_validation_allows_normal_road_without_structure_ref() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:optional-structure",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:normal-road",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=50.0,
                assembly_ref="assembly:road",
            )
        ],
    )

    result = RegionValidationService().validate(model)

    assert result.status == "ok"
    assert result.diagnostic_rows == []


def test_region_validation_reports_bad_range_and_equal_priority_overlap() -> None:
    model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="regions:bad",
        alignment_id="alignment:main",
        region_rows=[
            RegionRow(
                region_id="region:bad-range",
                primary_kind="normal_road",
                station_start=20.0,
                station_end=10.0,
            ),
            RegionRow(
                region_id="region:a",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                template_ref="template:a",
                priority=10,
            ),
            RegionRow(
                region_id="region:b",
                primary_kind="bridge",
                station_start=50.0,
                station_end=120.0,
                template_ref="template:b",
                priority=10,
            ),
        ],
    )

    result = RegionValidationService().validate(model)

    assert result.status == "error"
    assert any(row.kind == "invalid_station_range" for row in result.diagnostic_rows)
    assert any(row.kind == "equal_priority_overlap" for row in result.diagnostic_rows)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 region resolution service contract tests completed.")
