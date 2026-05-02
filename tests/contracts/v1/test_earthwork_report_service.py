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
    EarthworkReportBuildRequest,
    EarthworkReportService,
)


def _corridor() -> CorridorModel:
    return CorridorModel(
        schema_version=1,
        project_id="proj-1",
        corridor_id="cor-1",
        alignment_id="align-1",
        profile_id="prof-1",
        label="Main Corridor",
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


def test_earthwork_report_service_builds_full_output_stack() -> None:
    result = EarthworkReportService().build(
        EarthworkReportBuildRequest(
            project_id="proj-1",
            corridor=_corridor(),
            applied_section_set=_section_set(
                _section("sec-0", station=0.0, design_z=2.0),
                _section("sec-10", station=10.0, design_z=4.0),
            ),
            existing_ground_surface=_flat_ground_surface(),
            report_id="earthwork-report-1",
        )
    )

    assert result.status == "ok"
    assert result.diagnostic_rows == []
    assert [row.quantity_kind for row in result.analysis_result.area_fragment_rows] == [
        "fill_area",
        "fill_area",
    ]
    assert [row.quantity_kind for row in result.quantity_model.fragment_rows] == [
        "fill_area",
        "fill_area",
        "fill",
    ]
    assert result.earthwork_model.balance_rows[0].fill_value == 300.0
    assert result.earthwork_model.balance_rows[0].cut_value == 0.0
    assert result.mass_haul_model.curve_rows[0].cumulative_mass_values == [0.0, -300.0]
    assert result.quantity_output.summary_rows[0].kind == "fragment_count"
    assert result.earthwork_output.summary_rows[1].kind == "total_fill"
    assert result.earthwork_output.summary_rows[1].value == 300.0
    assert result.mass_haul_output.summary_rows[2].kind == "final_cumulative_mass"
    assert result.mass_haul_output.summary_rows[2].value == -300.0


def test_earthwork_report_service_propagates_missing_input_diagnostics_to_outputs() -> None:
    result = EarthworkReportService().build(
        EarthworkReportBuildRequest(
            project_id="proj-1",
            corridor=_corridor(),
            applied_section_set=_section_set(_section("sec-0", station=0.0, design_z=2.0)),
            existing_ground_surface=None,
            report_id="earthwork-report-1",
        )
    )

    diagnostic_kinds = {row.kind for row in result.diagnostic_rows}

    assert result.status == "partial"
    assert "missing_existing_ground_tin" in diagnostic_kinds
    assert "earthwork_volume_missing_input" in diagnostic_kinds
    assert result.earthwork_model.balance_rows
    assert result.earthwork_model.balance_rows[0].cut_value == 0.0
    assert result.earthwork_model.balance_rows[0].fill_value == 0.0
    assert "missing_existing_ground_tin" in {row.kind for row in result.earthwork_output.diagnostic_rows}
    assert "missing_existing_ground_tin" in {row.kind for row in result.mass_haul_output.diagnostic_rows}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 earthwork report service contract tests completed.")
