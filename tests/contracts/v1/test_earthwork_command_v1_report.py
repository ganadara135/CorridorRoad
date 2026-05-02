from freecad.Corridor_Road.v1.commands.cmd_earthwork_balance import (
    build_document_earthwork_report,
)
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
        station=station,
        point_rows=[
            AppliedSectionPoint(f"{section_id}:r", -5.0, station, design_z, "fg_surface", -5.0),
            AppliedSectionPoint(f"{section_id}:l", 5.0, station, design_z, "fg_surface", 5.0),
        ],
    )


def _section_set() -> AppliedSectionSet:
    sections = [
        _section("sec-0", station=0.0, design_z=2.0),
        _section("sec-10", station=10.0, design_z=4.0),
    ]
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
        sections=sections,
    )


def test_build_document_earthwork_report_uses_v1_native_pipeline() -> None:
    report = build_document_earthwork_report(
        None,
        preferred_section_set=_section_set(),
        preferred_station=10.0,
        existing_ground_surface=_flat_ground_surface(),
        corridor_model=_corridor(),
    )

    assert report is not None
    assert report["earthwork_analysis_result"].status == "ok"
    assert report["quantity_model"].quantity_model_id == "cor-1:earthwork:quantity"
    assert report["earthwork_model"].earthwork_balance_id == "cor-1:earthwork:balance"
    assert report["quantity_model"].quantity_model_id != "quantity:v1-demo"
    assert report["earthwork_output"].earthwork_output_id != "earthwork:v1-demo"
    assert report["legacy_objects"] == {}
    assert report["earthwork_output"].summary_rows[1].kind == "total_fill"
    assert report["earthwork_output"].summary_rows[1].value == 300.0
    assert report["mass_haul_output"].summary_rows[2].kind == "final_cumulative_mass"
    assert report["mass_haul_output"].summary_rows[2].value == -300.0
    assert report["station_row"]["station"] == 10.0
    assert len(report["station_rows"]) == 2
    assert report["key_station_rows"] == report["station_rows"]


def test_build_document_earthwork_report_keeps_missing_eg_diagnostics_visible() -> None:
    report = build_document_earthwork_report(
        None,
        preferred_section_set=_section_set(),
        existing_ground_surface=None,
        corridor_model=_corridor(),
    )

    assert report is not None
    assert "missing_existing_ground_tin" in {row.kind for row in report["diagnostic_rows"]}
    assert "missing_existing_ground_tin" in {row.kind for row in report["earthwork_output"].diagnostic_rows}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 earthwork command report contract tests completed.")
