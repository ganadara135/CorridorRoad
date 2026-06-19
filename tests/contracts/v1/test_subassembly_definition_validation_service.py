from freecad.Corridor_Road.v1.models.source import (
    SubassemblyDefinition,
    SubassemblyLibrary,
    SubassemblyLinkRow,
    SubassemblyParameterRow,
    SubassemblyPointRow,
    SubassemblyShapeRow,
    SubassemblyTargetRow,
)
from freecad.Corridor_Road.v1.models.source.subassembly_definition_presets import (
    subassembly_definition_library_from_preset,
)
from freecad.Corridor_Road.v1.services.evaluation import SubassemblyDefinitionValidationService


def test_subassembly_definition_validation_accepts_starter_primitives() -> None:
    library = subassembly_definition_library_from_preset("Starter Road Primitives", project_id="proj-1")

    result = SubassemblyDefinitionValidationService().validate_library(library)

    assert result.status == "ok"
    assert result.diagnostic_rows == []


def test_subassembly_definition_validation_reports_duplicate_and_missing_refs() -> None:
    library = SubassemblyLibrary(
        schema_version=1,
        project_id="proj-1",
        library_id="subassembly-library:test",
        definition_rows=[
            SubassemblyDefinition(
                definition_id="subassembly-definition:bad",
                parameter_rows=(
                    SubassemblyParameterRow("width", value=3.5),
                    SubassemblyParameterRow("width", value=4.0),
                ),
                point_rows=(SubassemblyPointRow("p0", x_expr="0", z_expr="0"),),
                link_rows=(SubassemblyLinkRow("l0", "p0", "missing", surface_role="design"),),
                shape_rows=(SubassemblyShapeRow("shape:bad", point_refs=("p0", "missing"), closed=True),),
            ),
            SubassemblyDefinition(definition_id="subassembly-definition:bad"),
        ],
    )

    result = SubassemblyDefinitionValidationService().validate_library(library)
    kinds = {row.kind for row in result.diagnostic_rows}

    assert result.status == "error"
    assert "duplicate_definition_id" in kinds
    assert "duplicate_parameter_id" in kinds
    assert "link_end_point_not_found" in kinds
    assert "shape_point_not_found" in kinds
    assert "closed_shape_needs_three_points" in kinds


def test_subassembly_definition_validation_reports_expression_errors() -> None:
    library = SubassemblyLibrary(
        schema_version=1,
        project_id="proj-1",
        library_id="subassembly-library:test",
        definition_rows=[
            SubassemblyDefinition(
                definition_id="subassembly-definition:bad-expression",
                parameter_rows=(SubassemblyParameterRow("width", value=3.5),),
                point_rows=(SubassemblyPointRow("p0", x_expr="missing_width", z_expr="0"),),
            )
        ],
    )

    result = SubassemblyDefinitionValidationService().validate_library(library)

    assert result.status == "error"
    assert any(row.kind == "unknown_parameter" for row in result.diagnostic_rows)


def test_subassembly_definition_validation_warns_required_target_without_fallback() -> None:
    library = SubassemblyLibrary(
        schema_version=1,
        project_id="proj-1",
        library_id="subassembly-library:test",
        definition_rows=[
            SubassemblyDefinition(
                definition_id="subassembly-definition:target-warning",
                point_rows=(SubassemblyPointRow("p0", x_expr="0", z_expr="0"),),
                target_rows=(SubassemblyTargetRow("target:terrain", "terrain_daylight", required=True),),
            )
        ],
    )

    result = SubassemblyDefinitionValidationService().validate_library(library)

    assert result.status == "warning"
    assert any(row.kind == "required_target_without_fallback" for row in result.diagnostic_rows)
