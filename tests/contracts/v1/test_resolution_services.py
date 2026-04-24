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
