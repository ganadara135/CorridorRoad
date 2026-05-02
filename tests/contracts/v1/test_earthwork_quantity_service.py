from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.corridor_model import CorridorModel
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINSurface,
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.services.builders import (
    EarthworkAnalysisBuildRequest,
    EarthworkAnalysisService,
    EarthworkBalanceBuildRequest,
    EarthworkBalanceService,
    EarthworkQuantityBuildRequest,
    EarthworkQuantityService,
)


def _corridor() -> CorridorModel:
    return CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
    )


def _flat_ground_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="eg-1",
        surface_kind="existing_ground_tin",
        vertex_rows=[
            TINVertex("v1", -10.0, -5.0, 0.0),
            TINVertex("v2", 10.0, -5.0, 0.0),
            TINVertex("v3", 10.0, 15.0, 0.0),
            TINVertex("v4", -10.0, 15.0, 0.0),
        ],
        triangle_rows=[
            TINTriangle("t1", "v1", "v2", "v3"),
            TINTriangle("t2", "v1", "v3", "v4"),
        ],
    )


def _section(section_id: str, *, station: float, design_z: float) -> AppliedSection:
    return AppliedSection(
        schema_version=1,
        project_id="proj-1",
        applied_section_id=section_id,
        corridor_id="cor-1",
        alignment_id="align-1",
        assembly_id="assembly-1",
        station=station,
        region_id="region-1",
        point_rows=[
            AppliedSectionPoint(f"{section_id}:r", -5.0, station, design_z, "fg_surface", -5.0),
            AppliedSectionPoint(f"{section_id}:l", 5.0, station, design_z, "fg_surface", 5.0),
        ],
    )


def _section_set(*sections: AppliedSection) -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        station_rows=[
            AppliedSectionStationRow(
                station_row_id=f"sta-{index}",
                station=section.station,
                applied_section_id=section.applied_section_id,
            )
            for index, section in enumerate(sections, start=1)
        ],
        sections=list(sections),
    )


def test_earthwork_quantity_service_converts_analysis_areas_to_volumes() -> None:
    corridor = _corridor()
    section_set = _section_set(
        _section("sec-0", station=0.0, design_z=2.0),
        _section("sec-10", station=10.0, design_z=4.0),
    )
    analysis = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=section_set,
            existing_ground_surface=_flat_ground_surface(),
            analysis_id="analysis-1",
        )
    )

    quantity_model = EarthworkQuantityService().build(
        EarthworkQuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=section_set,
            earthwork_analysis_result=analysis,
            quantity_model_id="earthwork-quantity-1",
        )
    )

    area_rows = [row for row in quantity_model.fragment_rows if row.measurement_kind == "section_earthwork_area"]
    volume_rows = [row for row in quantity_model.fragment_rows if row.measurement_kind == "average_end_area_volume"]
    aggregates = {row.aggregate_kind: row for row in quantity_model.aggregate_rows}

    assert [row.value for row in area_rows] == [20.0, 40.0]
    assert [row.quantity_kind for row in volume_rows] == ["fill"]
    assert volume_rows[0].station_start == 0.0
    assert volume_rows[0].station_end == 10.0
    assert volume_rows[0].value == 300.0
    assert aggregates["fill"].value == 300.0
    assert "cor-1" in quantity_model.source_refs
    assert "sections-1" in quantity_model.source_refs
    assert "analysis-1" in quantity_model.source_refs


def test_earthwork_quantity_output_feeds_balance_service() -> None:
    corridor = _corridor()
    section_set = _section_set(
        _section("sec-0", station=0.0, design_z=3.0),
        _section("sec-10", station=10.0, design_z=1.0),
    )
    analysis = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=section_set,
            existing_ground_surface=_flat_ground_surface(),
            analysis_id="analysis-1",
        )
    )
    quantity_model = EarthworkQuantityService().build(
        EarthworkQuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=section_set,
            earthwork_analysis_result=analysis,
            quantity_model_id="earthwork-quantity-1",
        )
    )
    earthwork_model = EarthworkBalanceService().build(
        EarthworkBalanceBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=section_set,
            quantity_model=quantity_model,
            earthwork_balance_id="earthwork-1",
        )
    )

    assert len(earthwork_model.balance_rows) == 1
    assert earthwork_model.balance_rows[0].cut_value == 0.0
    assert earthwork_model.balance_rows[0].fill_value == 200.0


def test_earthwork_quantity_service_reports_missing_area_fragments() -> None:
    corridor = _corridor()
    section_set = _section_set(_section("sec-0", station=0.0, design_z=2.0))
    analysis = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=section_set,
            existing_ground_surface=None,
            analysis_id="analysis-1",
        )
    )

    quantity_model = EarthworkQuantityService().build(
        EarthworkQuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=section_set,
            earthwork_analysis_result=analysis,
            quantity_model_id="earthwork-quantity-1",
        )
    )

    assert quantity_model.fragment_rows == []
    assert "missing_existing_ground_tin" in {row.kind for row in quantity_model.diagnostic_rows}
    assert "earthwork_volume_missing_input" in {row.kind for row in quantity_model.diagnostic_rows}


def test_earthwork_quantity_service_preserves_area_rows_when_volume_station_pair_is_missing() -> None:
    corridor = _corridor()
    section_set = _section_set(_section("sec-0", station=0.0, design_z=2.0))
    analysis = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=section_set,
            existing_ground_surface=_flat_ground_surface(),
            analysis_id="analysis-1",
        )
    )

    quantity_model = EarthworkQuantityService().build(
        EarthworkQuantityBuildRequest(
            project_id="proj-1",
            corridor=corridor,
            applied_section_set=section_set,
            earthwork_analysis_result=analysis,
            quantity_model_id="earthwork-quantity-1",
        )
    )

    area_rows = [row for row in quantity_model.fragment_rows if row.measurement_kind == "section_earthwork_area"]
    volume_rows = [row for row in quantity_model.fragment_rows if row.measurement_kind == "average_end_area_volume"]

    assert [row.quantity_kind for row in area_rows] == ["fill_area"]
    assert volume_rows == []
    assert "earthwork_volume_missing_input" in {row.kind for row in quantity_model.diagnostic_rows}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 earthwork quantity service contract tests completed.")
