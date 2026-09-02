"""Validate source/result ownership on supported normalized output contracts."""

from __future__ import annotations

from ...common.diagnostics import DiagnosticMessage
from ...models.result.output_traceability import OutputTraceabilityResult


SUPPORTED_OUTPUT_OWNER_REQUIREMENTS = {
    "PlanOutput": "source",
    "ProfileOutput": "source",
    "CrossSectionDrawingPayload": "result",
    "SectionOutput": "result",
    "SurfaceOutput": "result",
    "QuantityOutput": "result",
    "EarthworkBalanceOutput": "result",
    "MassHaulOutput": "result",
    "DrainageOutput": "source_and_result",
    "ExchangeOutput": "source_and_result",
    "StructureSolidOutput": "source_and_result",
    "IntersectionSurfaceZoneOutput": "result",
}


class OutputTraceabilityService:
    """Audit output ownership without editing the output or its source models."""

    def validate_supported_output(self, output_model) -> OutputTraceabilityResult:
        output_type = type(output_model).__name__
        requirement = SUPPORTED_OUTPUT_OWNER_REQUIREMENTS.get(output_type, "source_or_result")
        return self.validate(output_model, owner_requirement=requirement)

    def validate(self, output_model, *, owner_requirement: str = "source_or_result") -> OutputTraceabilityResult:
        if output_model is None:
            raise ValueError("output_model is required.")
        requirement = str(owner_requirement or "source_or_result").strip().lower()
        if requirement not in {"source", "result", "source_and_result", "source_or_result"}:
            raise ValueError(f"Unsupported owner requirement: {owner_requirement}")

        output_type = type(output_model).__name__
        output_ref = _output_ref(output_model)
        project_id = str(getattr(output_model, "project_id", "") or "").strip()
        source_refs = _unique_refs(getattr(output_model, "source_refs", ()) or ())
        result_refs = _unique_refs(getattr(output_model, "result_refs", ()) or ())
        diagnostics: list[DiagnosticMessage] = []

        if not project_id:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="output_project_owner_missing",
                    message=f"{output_type} is missing project ownership.",
                    notes="Return to the output mapper and preserve project_id from the consumed contract.",
                )
            )
        if not output_ref:
            diagnostics.append(
                DiagnosticMessage(
                    severity="error",
                    kind="output_identity_missing",
                    message=f"{output_type} has no stable output identity.",
                    notes="Create the output from its normalized mapper; do not infer identity from preview geometry.",
                )
            )
        if requirement in {"source", "source_and_result"} and not source_refs:
            diagnostics.append(_owner_missing(output_type, "source"))
        if requirement in {"result", "source_and_result"} and not result_refs:
            diagnostics.append(_owner_missing(output_type, "result"))
        if requirement == "source_or_result" and not source_refs and not result_refs:
            diagnostics.append(_owner_missing(output_type, "source or result"))

        return OutputTraceabilityResult(
            output_type=output_type,
            output_ref=output_ref,
            owner_requirement=requirement,
            source_refs=source_refs,
            result_refs=result_refs,
            status="error" if diagnostics else "ready",
            diagnostic_rows=tuple(diagnostics),
        )


def _owner_missing(output_type: str, owner_kind: str) -> DiagnosticMessage:
    return DiagnosticMessage(
        severity="error",
        kind=f"output_{owner_kind.replace(' ', '_')}_owner_missing",
        message=f"{output_type} is missing its required {owner_kind} owner reference.",
        notes="Return to the owning source/evaluation stage; do not repair the output from preview geometry.",
    )


def _output_ref(output_model) -> str:
    preferred_names = (
        "exchange_output_id",
        "structure_solid_output_id",
        "quantity_output_id",
        "surface_output_id",
        "section_output_id",
        "drawing_id",
        "profile_output_id",
        "plan_output_id",
        "earthwork_balance_output_id",
        "mass_haul_output_id",
        "drainage_output_id",
        "intersection_surface_zone_output_id",
    )
    for name in preferred_names:
        value = str(getattr(output_model, name, "") or "").strip()
        if value:
            return value
    for name, value in vars(output_model).items():
        if name != "project_id" and name.endswith("_id") and str(value or "").strip():
            return str(value).strip()
    return ""


def _unique_refs(values) -> tuple[str, ...]:
    refs: list[str] = []
    for value in values or ():
        text = str(value or "").strip()
        if text and text not in refs:
            refs.append(text)
    return tuple(refs)


__all__ = ["OutputTraceabilityService", "SUPPORTED_OUTPUT_OWNER_REQUIREMENTS"]
