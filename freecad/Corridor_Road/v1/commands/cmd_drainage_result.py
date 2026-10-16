"""Build and store the Drainage result of a document.

Reads the Drainage source and the stored Applied Sections, evaluates the Ditch Run flowlines
against the Policy, and writes the result with the inputs it consumed, so result freshness reports
it stale when either changes. Called by the Drainage panel's Apply and by Rebuild Downstream.
"""

from __future__ import annotations

from freecad.Corridor_Road.objects.obj_project import find_project

from ..models.result.drainage_result import DrainageResult
from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_drainage_result import create_or_update_v1_drainage_result_object
from ..objects.project_document_adapter import route_object_to_project_tree
from ..objects.result_freshness import drainage_inputs
from ..objects.stage_inputs import record_stage_inputs
from ..services.evaluation.drainage_evaluation_service import DrainageEvaluationService


def build_document_drainage_result(document) -> DrainageResult:
    drainage_model = to_drainage_model(find_v1_drainage_model(document))
    if drainage_model is None:
        raise RuntimeError("The document has no Drainage source. Add Ditch Runs in the Drainage panel first.")
    applied = to_applied_section_set(find_v1_applied_section_set(document))
    if applied is None:
        raise RuntimeError("Applied Sections are not built yet. Build them before evaluating Drainage.")
    return DrainageEvaluationService().evaluate(drainage_model, applied)


def apply_v1_drainage_result(document):
    """Evaluate the Drainage of the document and store the result; returns its object."""

    result = build_document_drainage_result(document)
    obj = create_or_update_v1_drainage_result_object(document, result)
    record_stage_inputs(obj, drainage_inputs(document))
    project = find_project(document)
    if project is not None:
        route_object_to_project_tree(project, obj)
    return obj


def drainage_result_summary(result: DrainageResult) -> str:
    """A few lines for a panel: status, counts and the warnings and errors."""

    counts = {severity: sum(1 for row in result.check_rows if row.severity == severity) for severity in ("error", "warning", "info")}
    lows = sum(len(row.low_point_stations) for row in result.flowline_rows)
    lines = [
        f"Drainage checks: {result.status}; {len(result.flowline_rows)} flowline(s), {lows} low point(s), "
        f"{counts['error']} error(s), {counts['warning']} warning(s)."
    ]
    lines.extend(row.message for row in result.check_rows if row.severity in {"error", "warning"})
    return "\n".join(lines)


__all__ = ["apply_v1_drainage_result", "build_document_drainage_result", "drainage_result_summary"]
