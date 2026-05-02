from freecad.Corridor_Road.v1.models.output.section_output import (
    SectionGeometryRow,
    SectionOutput,
)
from freecad.Corridor_Road.v1.services.evaluation import SectionEarthworkAreaService


def _section_output(
    *,
    design_z: list[float],
    ground_z: list[float],
    x_values: list[float] | None = None,
) -> SectionOutput:
    offsets = x_values or [0.0, 10.0]
    return SectionOutput(
        schema_version=1,
        project_id="test-project",
        section_output_id="section:test",
        alignment_id="alignment:test",
        station=10.0,
        geometry_rows=[
            SectionGeometryRow(
                row_id="section:test:design",
                kind="design_section",
                x_values=offsets,
                y_values=design_z,
                z_values=design_z,
                style_role="finished_grade",
            ),
            SectionGeometryRow(
                row_id="section:test:ground",
                kind="existing_ground_tin",
                x_values=offsets,
                y_values=ground_z,
                z_values=ground_z,
                style_role="existing_ground",
            ),
        ],
    )


def test_section_earthwork_area_service_computes_fill_area() -> None:
    result = SectionEarthworkAreaService().build(
        _section_output(
            design_z=[2.0, 2.0],
            ground_z=[0.0, 0.0],
        )
    )

    assert result.status == "ok"
    assert result.cut_area == 0.0
    assert result.fill_area == 20.0
    assert result.rows[0].quantity_kind == "fill_area"


def test_section_earthwork_area_service_splits_cut_and_fill_at_crossing() -> None:
    result = SectionEarthworkAreaService().build(
        _section_output(
            design_z=[3.0, -2.0],
            ground_z=[0.0, 0.0],
            x_values=[0.0, 5.0],
        )
    )

    assert result.status == "ok"
    assert round(result.fill_area, 6) == 4.5
    assert round(result.cut_area, 6) == 2.0
    assert [row.quantity_kind for row in result.rows] == ["cut_area", "fill_area"]


def test_section_earthwork_area_rows_convert_to_section_quantity_rows() -> None:
    service = SectionEarthworkAreaService()
    result = service.build(
        _section_output(
            design_z=[0.0, 0.0],
            ground_z=[1.0, 1.0],
        )
    )
    rows = service.to_section_quantity_rows(result, row_id_prefix="section:test")

    assert len(rows) == 1
    assert rows[0].quantity_kind == "cut_area"
    assert rows[0].value == 10.0
    assert rows[0].unit == "m2"
    assert rows[0].component_ref == "section_earthwork_area"


def test_section_earthwork_area_service_requires_design_and_ground_lines() -> None:
    result = SectionEarthworkAreaService().build(
        SectionOutput(
            schema_version=1,
            project_id="test-project",
            section_output_id="section:test",
            alignment_id="alignment:test",
            station=10.0,
        )
    )

    assert result.status == "missing_input"
    assert result.rows == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 section earthwork area service contract tests completed.")
