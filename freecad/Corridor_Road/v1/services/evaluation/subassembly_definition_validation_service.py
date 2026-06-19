"""Validation service for v1 Subassembly definition libraries."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.source.subassembly_definition_model import SubassemblyDefinition, SubassemblyLibrary
from .subassembly_bench_row_parser import parse_bench_rows
from .subassembly_expression_service import SubassemblyExpressionService


RECOGNIZED_SURFACE_ROLES = {
    "",
    "design",
    "subgrade",
    "subgrade_surface",
    "slope_face",
    "slope_face_surface",
    "drainage",
    "drainage_surface",
    "structure_interface",
    "material_boundary",
}


@dataclass
class SubassemblyDefinitionValidationResult:
    """Validation result for a Subassembly definition library."""

    status: str
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)


class SubassemblyDefinitionValidationService:
    """Validate reusable Subassembly source definitions before persistence/evaluation."""

    def __init__(self, *, expression_service: SubassemblyExpressionService | None = None) -> None:
        self.expression_service = expression_service or SubassemblyExpressionService()

    def validate_library(self, library: SubassemblyLibrary | None) -> SubassemblyDefinitionValidationResult:
        """Validate a full reusable Subassembly library."""

        diagnostics: list[DiagnosticMessage] = []
        if library is None:
            diagnostics.append(_diagnostic("error", "missing_library", "SubassemblyLibrary is required."))
            return SubassemblyDefinitionValidationResult(status="error", diagnostic_rows=diagnostics)

        definitions = list(getattr(library, "definition_rows", []) or [])
        if not definitions:
            diagnostics.append(_diagnostic("warning", "empty_library", "SubassemblyLibrary has no definitions."))
        _add_duplicate_diagnostics(
            diagnostics,
            "definition",
            [str(getattr(row, "definition_id", "") or "") for row in definitions],
            "duplicate_definition_id",
        )
        for definition in definitions:
            self._validate_definition(definition, diagnostics)

        status = "error" if any(row.severity == "error" for row in diagnostics) else "ok"
        if status == "ok" and any(row.severity == "warning" for row in diagnostics):
            status = "warning"
        return SubassemblyDefinitionValidationResult(status=status, diagnostic_rows=diagnostics)

    def _validate_definition(self, definition: SubassemblyDefinition, diagnostics: list[DiagnosticMessage]) -> None:
        definition_id = str(getattr(definition, "definition_id", "") or "").strip()
        if not definition_id:
            diagnostics.append(_diagnostic("error", "missing_definition_id", "Definition ID is required."))
        point_ids = [str(getattr(row, "point_id", "") or "") for row in list(getattr(definition, "point_rows", []) or [])]
        parameter_ids = [
            str(getattr(row, "parameter_id", "") or "") for row in list(getattr(definition, "parameter_rows", []) or [])
        ]
        link_ids = [str(getattr(row, "link_id", "") or "") for row in list(getattr(definition, "link_rows", []) or [])]
        shape_ids = [str(getattr(row, "shape_id", "") or "") for row in list(getattr(definition, "shape_rows", []) or [])]
        target_ids = [str(getattr(row, "target_id", "") or "") for row in list(getattr(definition, "target_rows", []) or [])]

        _add_duplicate_diagnostics(diagnostics, definition_id, parameter_ids, "duplicate_parameter_id")
        _add_duplicate_diagnostics(diagnostics, definition_id, point_ids, "duplicate_point_id")
        _add_duplicate_diagnostics(diagnostics, definition_id, link_ids, "duplicate_link_id")
        _add_duplicate_diagnostics(diagnostics, definition_id, shape_ids, "duplicate_shape_id")
        _add_duplicate_diagnostics(diagnostics, definition_id, target_ids, "duplicate_target_id")

        point_id_set = {value for value in point_ids if value}
        for parameter in list(getattr(definition, "parameter_rows", []) or []):
            if not str(getattr(parameter, "parameter_id", "") or "").strip():
                diagnostics.append(_diagnostic("error", "missing_parameter_id", "Parameter ID is required.", definition_id))
            if bool(getattr(parameter, "required", False)) and not str(getattr(parameter, "value", "") or "").strip():
                diagnostics.append(
                    _diagnostic(
                        "error",
                        "missing_required_parameter_value",
                        f"Required parameter has no value: {getattr(parameter, 'parameter_id', '')}.",
                        definition_id,
                    )
                )
        _validate_side_slope_bench_rows(definition, diagnostics)

        if not point_id_set:
            diagnostics.append(_diagnostic("warning", "definition_has_no_points", "Definition has no point rows.", definition_id))

        expression_result = self.expression_service.evaluate_definition(definition)
        diagnostics.extend(expression_result.diagnostic_rows)

        for link in list(getattr(definition, "link_rows", []) or []):
            if not str(getattr(link, "link_id", "") or "").strip():
                diagnostics.append(_diagnostic("error", "missing_link_id", "Link ID is required.", definition_id))
            _require_point_ref(
                diagnostics,
                definition_id,
                point_id_set,
                str(getattr(link, "start_point_ref", "") or ""),
                "link_start_point_not_found",
            )
            _require_point_ref(
                diagnostics,
                definition_id,
                point_id_set,
                str(getattr(link, "end_point_ref", "") or ""),
                "link_end_point_not_found",
            )
            surface_role = str(getattr(link, "surface_role", "") or "")
            if surface_role not in RECOGNIZED_SURFACE_ROLES:
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "unknown_surface_role",
                        f"Surface role is not recognized yet: {surface_role}.",
                        definition_id,
                    )
                )

        for shape in list(getattr(definition, "shape_rows", []) or []):
            if not str(getattr(shape, "shape_id", "") or "").strip():
                diagnostics.append(_diagnostic("error", "missing_shape_id", "Shape ID is required.", definition_id))
            point_refs = list(getattr(shape, "point_refs", []) or [])
            for point_ref in point_refs:
                _require_point_ref(diagnostics, definition_id, point_id_set, str(point_ref or ""), "shape_point_not_found")
            if bool(getattr(shape, "closed", False)) and len(point_refs) < 3:
                diagnostics.append(
                    _diagnostic("error", "closed_shape_needs_three_points", "Closed shape needs at least three points.", definition_id)
                )
            if str(getattr(shape, "solid_role", "") or "").strip() and not bool(getattr(shape, "closed", False)):
                diagnostics.append(
                    _diagnostic("error", "solid_shape_must_be_closed", "Shape with solid role must be closed.", definition_id)
                )

        for target in list(getattr(definition, "target_rows", []) or []):
            if not str(getattr(target, "target_id", "") or "").strip():
                diagnostics.append(_diagnostic("error", "missing_target_id", "Target ID is required.", definition_id))
            if bool(getattr(target, "required", False)) and not str(getattr(target, "fallback_policy", "") or "").strip():
                diagnostics.append(
                    _diagnostic(
                        "warning",
                        "required_target_without_fallback",
                        f"Required target has no fallback policy: {getattr(target, 'target_id', '')}.",
                        definition_id,
                    )
                )


def _require_point_ref(
    diagnostics: list[DiagnosticMessage],
    definition_id: str,
    point_ids: set[str],
    point_ref: str,
    kind: str,
) -> None:
    if not point_ref:
        diagnostics.append(_diagnostic("error", kind, "Point reference is required.", definition_id))
    elif point_ref not in point_ids:
        diagnostics.append(_diagnostic("error", kind, f"Point reference was not found: {point_ref}.", definition_id))


def _add_duplicate_diagnostics(
    diagnostics: list[DiagnosticMessage],
    scope: str,
    values: list[str],
    kind: str,
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if text in seen:
            duplicates.add(text)
        seen.add(text)
    for duplicate in sorted(duplicates):
        diagnostics.append(_diagnostic("error", kind, f"Duplicate id: {duplicate}.", scope))


def _validate_side_slope_bench_rows(definition: SubassemblyDefinition, diagnostics: list[DiagnosticMessage]) -> None:
    if str(getattr(definition, "kind", "") or "").strip().lower() != "side_slope":
        return
    definition_id = str(getattr(definition, "definition_id", "") or "").strip()
    parameters = {
        str(getattr(row, "parameter_id", "") or "").strip(): getattr(row, "value", "")
        for row in list(getattr(definition, "parameter_rows", []) or [])
        if str(getattr(row, "parameter_id", "") or "").strip()
    }
    bench_mode = str(parameters.get("bench_mode", "") or "").strip().lower().replace("-", "_")
    if bench_mode and bench_mode not in {"none", "single", "rows"}:
        diagnostics.append(
            _diagnostic(
                "warning",
                "unknown_bench_mode",
                f"side_slope definition has unknown bench_mode: {bench_mode}.",
                definition_id,
            )
        )
    raw_rows = parameters.get("bench_rows", "")
    parse_result = parse_bench_rows(raw_rows, source_id=f"{definition_id}:bench_rows")
    diagnostics.extend(parse_result.diagnostic_rows)
    if bench_mode in {"single", "rows"} and str(raw_rows or "").strip() and not parse_result.rows:
        diagnostics.append(
            _diagnostic(
                "error",
                "bench_rows_required_but_empty",
                "bench_mode requires at least one valid bench_rows entry.",
                definition_id,
            )
        )


def _diagnostic(severity: str, kind: str, message: str, notes: str = "") -> DiagnosticMessage:
    return DiagnosticMessage(severity=severity, kind=kind, message=message, notes=notes)
