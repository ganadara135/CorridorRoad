"""Deterministic expression evaluation for v1 Subassembly definitions."""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.source.subassembly_definition_model import SubassemblyDefinition


@dataclass(frozen=True)
class EvaluatedSubassemblyPoint:
    """Evaluated point coordinate from one Subassembly definition point row."""

    point_id: str
    x: float
    z: float
    code: str = ""
    role: str = ""
    connectable: bool = False


@dataclass
class SubassemblyExpressionEvaluationResult:
    """Result from evaluating a Subassembly definition expression set."""

    status: str
    parameter_values: dict[str, float | str] = field(default_factory=dict)
    point_rows: list[EvaluatedSubassemblyPoint] = field(default_factory=list)
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


class SubassemblyExpressionService:
    """Evaluate Subassembly parameter and point expressions without side effects."""

    def evaluate_definition(
        self,
        definition: SubassemblyDefinition,
        *,
        parameter_overrides: dict[str, object] | None = None,
    ) -> SubassemblyExpressionEvaluationResult:
        """Evaluate one reusable Subassembly definition into numeric point rows."""

        diagnostics: list[DiagnosticMessage] = []
        parameters = self._parameter_values(definition, parameter_overrides or {}, diagnostics)
        points: list[EvaluatedSubassemblyPoint] = []
        for point in list(getattr(definition, "point_rows", []) or []):
            point_id = str(getattr(point, "point_id", "") or "").strip()
            x_value = self.evaluate_expression(
                str(getattr(point, "x_expr", "") or "0.0"),
                parameters,
                expression_id=f"{point_id}:x",
                diagnostics=diagnostics,
            )
            z_value = self.evaluate_expression(
                str(getattr(point, "z_expr", "") or "0.0"),
                parameters,
                expression_id=f"{point_id}:z",
                diagnostics=diagnostics,
            )
            if x_value is None or z_value is None:
                continue
            points.append(
                EvaluatedSubassemblyPoint(
                    point_id=point_id,
                    x=float(x_value),
                    z=float(z_value),
                    code=str(getattr(point, "code", "") or ""),
                    role=str(getattr(point, "role", "") or ""),
                    connectable=bool(getattr(point, "connectable", False)),
                )
            )
        status = "ok" if not any(row.severity == "error" for row in diagnostics) else "error"
        return SubassemblyExpressionEvaluationResult(
            status=status,
            parameter_values=parameters,
            point_rows=points,
            diagnostic_rows=diagnostics,
        )

    def evaluate_expression(
        self,
        expression: str,
        variables: dict[str, object],
        *,
        expression_id: str = "",
        diagnostics: list[DiagnosticMessage] | None = None,
    ) -> float | None:
        """Evaluate a small arithmetic expression with named numeric variables."""

        text = str(expression or "").strip()
        rows = diagnostics if diagnostics is not None else []
        if not text:
            return 0.0
        try:
            tree = ast.parse(text, mode="eval")
            value = _SafeEvaluator(_numeric_variables(variables)).visit(tree)
            return float(value)
        except ZeroDivisionError:
            rows.append(_diagnostic("error", "division_by_zero", "Expression divides by zero.", expression_id, text))
        except KeyError as exc:
            rows.append(
                _diagnostic(
                    "error",
                    "unknown_parameter",
                    f"Expression references unknown parameter: {exc.args[0]}.",
                    expression_id,
                    text,
                )
            )
        except ValueError as exc:
            rows.append(_diagnostic("error", "invalid_expression", str(exc), expression_id, text))
        except SyntaxError as exc:
            rows.append(_diagnostic("error", "invalid_expression_syntax", str(exc), expression_id, text))
        return None

    def _parameter_values(
        self,
        definition: SubassemblyDefinition,
        overrides: dict[str, object],
        diagnostics: list[DiagnosticMessage],
    ) -> dict[str, float | str]:
        values: dict[str, float | str] = {}
        for parameter in list(getattr(definition, "parameter_rows", []) or []):
            parameter_id = str(getattr(parameter, "parameter_id", "") or "").strip()
            if not parameter_id:
                continue
            raw_value = overrides.get(parameter_id, getattr(parameter, "value", ""))
            if _is_numeric(raw_value):
                values[parameter_id] = float(raw_value)
            else:
                values[parameter_id] = str(raw_value or "")
                if bool(getattr(parameter, "required", False)):
                    diagnostics.append(
                        _diagnostic(
                            "warning",
                            "non_numeric_required_parameter",
                            f"Required parameter is not numeric: {parameter_id}.",
                            parameter_id,
                            str(raw_value or ""),
                        )
                    )
        return values


class _SafeEvaluator(ast.NodeVisitor):
    _binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _unary_ops = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def __init__(self, variables: dict[str, float]) -> None:
        self.variables = dict(variables)

    def visit_Expression(self, node: ast.Expression) -> float:  # noqa: N802 - ast visitor API
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:  # noqa: N802 - ast visitor API
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numeric constants are allowed.")

    def visit_Name(self, node: ast.Name) -> float:  # noqa: N802 - ast visitor API
        name = str(node.id or "")
        if name not in self.variables:
            raise KeyError(name)
        return float(self.variables[name])

    def visit_BinOp(self, node: ast.BinOp) -> float:  # noqa: N802 - ast visitor API
        op_type = type(node.op)
        if op_type not in self._binary_ops:
            raise ValueError(f"Operator is not allowed: {op_type.__name__}.")
        return float(self._binary_ops[op_type](self.visit(node.left), self.visit(node.right)))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:  # noqa: N802 - ast visitor API
        op_type = type(node.op)
        if op_type not in self._unary_ops:
            raise ValueError(f"Operator is not allowed: {op_type.__name__}.")
        return float(self._unary_ops[op_type](self.visit(node.operand)))

    def generic_visit(self, node):  # noqa: D401 - ast visitor API
        """Reject all non-arithmetic syntax."""

        raise ValueError(f"Expression syntax is not allowed: {type(node).__name__}.")


def _numeric_variables(values: dict[str, object]) -> dict[str, float]:
    output: dict[str, float] = {}
    for key, value in dict(values or {}).items():
        if _is_numeric(value):
            output[str(key)] = float(value)
    return output


def _is_numeric(value: object) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


def _diagnostic(severity: str, kind: str, message: str, expression_id: str, expression: str) -> DiagnosticMessage:
    notes = f"expression_id={expression_id}; expression={expression}" if expression_id else f"expression={expression}"
    return DiagnosticMessage(severity=severity, kind=kind, message=message, notes=notes)
