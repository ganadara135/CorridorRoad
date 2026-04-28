from freecad.Corridor_Road.v1.models.source.override_model import (
    OverrideModel,
    OverrideRow,
    OverrideScope,
    OverrideTarget,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.services.evaluation.override_resolution_service import (
    OverrideResolutionService,
)
from freecad.Corridor_Road.v1.services.evaluation.region_resolution_service import (
    RegionResolutionService,
    RegionValidationService,
)


def test_region_resolution_picks_covering_region() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-1",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-a",
                region_kind="mainline_region",
                station_start=0.0,
                station_end=50.0,
                template_ref="tmpl-a",
                priority=0,
            ),
            RegionRow(
                region_id="region-b",
                region_kind="mainline_region",
                station_start=25.0,
                station_end=75.0,
                template_ref="tmpl-b",
                priority=1,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(region_model, 30.0)

    assert result.active_region_id == "region-b"
    assert result.active_template_ref == "tmpl-b"


def test_region_resolution_preserves_primary_layers_and_domain_refs() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-overlap",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-normal",
                region_index=1,
                primary_kind="normal_road",
                station_start=0.0,
                station_end=200.0,
                assembly_ref="assembly:road",
                template_ref="tmpl-road",
                priority=10,
            ),
            RegionRow(
                region_id="region-bridge",
                region_index=2,
                primary_kind="bridge",
                applied_layers=["ditch", "drainage"],
                station_start=120.0,
                station_end=180.0,
                assembly_ref="assembly:bridge-deck",
                template_ref="tmpl-bridge",
                structure_refs=["structure:bridge-01"],
                drainage_refs=["drainage:deck-drain-left", "drainage:side-ditch-right"],
                priority=80,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(region_model, 150.0)

    assert result.active_region_id == "region-bridge"
    assert result.active_primary_kind == "bridge"
    assert result.active_applied_layers == ["ditch", "drainage"]
    assert result.active_assembly_ref == "assembly:bridge-deck"
    assert result.resolved_structure_refs == ["structure:bridge-01"]
    assert result.resolved_drainage_refs == ["drainage:deck-drain-left", "drainage:side-ditch-right"]
    assert result.overlap_region_ids == ["region-normal"]


def test_region_handoff_rows_are_station_ordered_context_contracts() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-handoff",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-road",
                region_index=1,
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                assembly_ref="assembly:road",
                priority=10,
            ),
            RegionRow(
                region_id="region-ramp",
                region_index=2,
                primary_kind="ramp",
                station_start=100.0,
                station_end=180.0,
                assembly_ref="assembly:ramp",
                ramp_ref="ramp:entry-01",
                priority=70,
            ),
        ],
    )

    rows = RegionResolutionService().resolve_handoff_rows(region_model, [50.0, 120.0])

    assert [row.region_id for row in rows] == ["region-road", "region-ramp"]
    assert rows[1].primary_kind == "ramp"
    assert rows[1].ramp_ref == "ramp:entry-01"


def test_region_resolution_equal_priority_overlap_warns_and_uses_region_index() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-equal",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-b",
                region_index=2,
                primary_kind="bridge",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-b",
                priority=20,
            ),
            RegionRow(
                region_id="region-a",
                region_index=1,
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-a",
                priority=20,
            ),
        ],
    )

    result = RegionResolutionService().resolve_station(region_model, 50.0)

    assert result.active_region_id == "region-a"
    assert any(row.kind == "equal_priority_overlap" for row in result.diagnostic_rows)


def test_region_validation_reports_invalid_range_and_equal_priority_overlap() -> None:
    region_model = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-invalid",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-invalid",
                primary_kind="normal_road",
                station_start=10.0,
                station_end=0.0,
                priority=5,
            ),
            RegionRow(
                region_id="region-a",
                primary_kind="normal_road",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-a",
                priority=10,
            ),
            RegionRow(
                region_id="region-b",
                primary_kind="bridge",
                station_start=50.0,
                station_end=120.0,
                template_ref="tmpl-b",
                priority=10,
            ),
        ],
    )

    result = RegionValidationService().validate(region_model)

    assert result.status == "error"
    assert any(row.kind == "invalid_station_range" for row in result.diagnostic_rows)
    assert any(row.kind == "equal_priority_overlap" for row in result.diagnostic_rows)


def test_override_resolution_filters_by_station_and_region() -> None:
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-1",
        alignment_id="align-1",
        override_rows=[
            OverrideRow(
                override_id="ovr-a",
                override_kind="parameter_override",
                target=OverrideTarget(
                    target_id="target-a",
                    target_kind="section_parameter",
                    target_ref="lane-width",
                ),
                scope=OverrideScope(
                    scope_id="scope-a",
                    scope_kind="station_range",
                    station_start=0.0,
                    station_end=20.0,
                    region_ref="region-a",
                ),
                parameter="width",
                value=3.5,
            ),
            OverrideRow(
                override_id="ovr-b",
                override_kind="parameter_override",
                target=OverrideTarget(
                    target_id="target-b",
                    target_kind="section_parameter",
                    target_ref="lane-width",
                ),
                scope=OverrideScope(
                    scope_id="scope-b",
                    scope_kind="station_range",
                    station_start=21.0,
                    station_end=40.0,
                    region_ref="region-b",
                ),
                parameter="width",
                value=4.0,
            ),
        ],
    )

    result = OverrideResolutionService().resolve_station(
        override_model,
        10.0,
        region_id="region-a",
    )

    assert result.active_override_ids == ["ovr-a"]
