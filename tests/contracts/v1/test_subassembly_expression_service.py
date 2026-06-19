from freecad.Corridor_Road.v1.models.source import (
    SubassemblyDefinition,
    SubassemblyParameterRow,
    SubassemblyPointRow,
)
from freecad.Corridor_Road.v1.services.evaluation import SubassemblyExpressionService


def test_subassembly_expression_service_evaluates_parameter_arithmetic() -> None:
    definition = SubassemblyDefinition(
        definition_id="subassembly-definition:lane-basic",
        parameter_rows=(
            SubassemblyParameterRow("width", value=3.5, unit="m", required=True),
            SubassemblyParameterRow("slope", value=-2.0, unit="%", required=True),
        ),
        point_rows=(
            SubassemblyPointRow("origin", x_expr="0", z_expr="0", code="CROWN"),
            SubassemblyPointRow("edge", x_expr="width", z_expr="width*slope/100", code="ETW"),
        ),
    )

    result = SubassemblyExpressionService().evaluate_definition(definition)

    assert result.status == "ok"
    assert result.parameter_values["width"] == 3.5
    assert len(result.point_rows) == 2
    assert result.point_rows[1].point_id == "edge"
    assert result.point_rows[1].x == 3.5
    assert result.point_rows[1].z == -0.07


def test_subassembly_expression_service_supports_numeric_overrides() -> None:
    definition = SubassemblyDefinition(
        definition_id="subassembly-definition:shoulder-basic",
        parameter_rows=(SubassemblyParameterRow("width", value=1.0),),
        point_rows=(SubassemblyPointRow("outer", x_expr="width*2", z_expr="-width"),),
    )

    result = SubassemblyExpressionService().evaluate_definition(definition, parameter_overrides={"width": 2.5})

    assert result.status == "ok"
    assert result.point_rows[0].x == 5.0
    assert result.point_rows[0].z == -2.5


def test_subassembly_expression_service_rejects_unsafe_syntax() -> None:
    definition = SubassemblyDefinition(
        definition_id="subassembly-definition:unsafe",
        parameter_rows=(SubassemblyParameterRow("width", value=3.5),),
        point_rows=(SubassemblyPointRow("bad", x_expr="__import__('os').system('dir')", z_expr="0"),),
    )

    result = SubassemblyExpressionService().evaluate_definition(definition)

    assert result.status == "error"
    assert any(row.kind == "invalid_expression" for row in result.diagnostic_rows)
    assert result.point_rows == []


def test_subassembly_expression_service_reports_unknown_parameters() -> None:
    definition = SubassemblyDefinition(
        definition_id="subassembly-definition:bad-ref",
        point_rows=(SubassemblyPointRow("edge", x_expr="missing_width", z_expr="0"),),
    )

    result = SubassemblyExpressionService().evaluate_definition(definition)

    assert result.status == "error"
    assert any(row.kind == "unknown_parameter" for row in result.diagnostic_rows)
