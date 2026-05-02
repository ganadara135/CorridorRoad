from freecad.Corridor_Road.v1.models.result.applied_section import (
    AppliedSection,
    AppliedSectionPoint,
)
from freecad.Corridor_Road.v1.models.result.applied_section_set import (
    AppliedSectionSet,
    AppliedSectionStationRow,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINSurface,
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.services.builders import (
    EarthworkAnalysisBuildRequest,
    EarthworkAnalysisService,
)


def _flat_ground_surface(z: float = 0.0) -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="proj-1",
        surface_id="eg-1",
        surface_kind="existing_ground_tin",
        vertex_rows=[
            TINVertex("v1", -10.0, -5.0, z),
            TINVertex("v2", 10.0, -5.0, z),
            TINVertex("v3", 10.0, 15.0, z),
            TINVertex("v4", -10.0, 15.0, z),
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
            AppliedSectionPoint(
                f"{section_id}:right",
                -5.0,
                station,
                design_z,
                "fg_surface",
                -5.0,
            ),
            AppliedSectionPoint(
                f"{section_id}:left",
                5.0,
                station,
                design_z,
                "fg_surface",
                5.0,
            ),
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


def test_earthwork_analysis_service_builds_station_area_fragments() -> None:
    result = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=_section_set(
                _section("sec-0", station=0.0, design_z=2.0),
                _section("sec-10", station=10.0, design_z=4.0),
            ),
            existing_ground_surface=_flat_ground_surface(),
            analysis_id="earthwork-analysis-1",
        )
    )

    assert result.status == "ok"
    assert result.diagnostic_rows == []
    assert [row.quantity_kind for row in result.area_fragment_rows] == [
        "fill_area",
        "fill_area",
    ]
    assert [row.value for row in result.area_fragment_rows] == [20.0, 40.0]
    assert [row.station_start for row in result.area_fragment_rows] == [0.0, 10.0]
    assert all(row.measurement_kind == "section_earthwork_area" for row in result.area_fragment_rows)
    assert all(row.component_ref == "section_earthwork_area" for row in result.area_fragment_rows)
    assert all(row.assembly_ref == "assembly-1" for row in result.area_fragment_rows)
    assert all(row.region_ref == "region-1" for row in result.area_fragment_rows)


def test_earthwork_analysis_service_reports_missing_existing_ground() -> None:
    result = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=_section_set(_section("sec-0", station=0.0, design_z=2.0)),
            existing_ground_surface=None,
            analysis_id="earthwork-analysis-1",
        )
    )

    assert result.status == "missing_input"
    assert result.area_fragment_rows == []
    assert [row.kind for row in result.diagnostic_rows] == ["missing_existing_ground_tin"]


def test_earthwork_analysis_service_reports_missing_design_polyline() -> None:
    result = EarthworkAnalysisService().build(
        EarthworkAnalysisBuildRequest(
            project_id="proj-1",
            applied_section_set=_section_set(
                AppliedSection(
                    schema_version=1,
                    project_id="proj-1",
                    applied_section_id="sec-empty",
                    corridor_id="cor-1",
                    alignment_id="align-1",
                    station=0.0,
                )
            ),
            existing_ground_surface=_flat_ground_surface(),
            analysis_id="earthwork-analysis-1",
        )
    )

    assert result.status == "empty"
    assert result.area_fragment_rows == []
    assert [row.kind for row in result.diagnostic_rows] == ["missing_design_section_polyline"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 earthwork analysis service contract tests completed.")
