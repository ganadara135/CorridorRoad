"""Drainage editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project

from ..models.source.drainage_model import DrainageModel
from ..objects.obj_drainage import create_or_update_v1_drainage_model_object, find_v1_drainage_model, to_drainage_model
from ..objects.obj_drainage_result import find_v1_drainage_result_object, to_drainage_result
from ..objects.obj_region import list_v1_region_models, to_region_model
from ..objects.obj_stationing import list_v1_stationings, station_value_rows
from ..objects.obj_subassembly_assembly import list_v1_assembly_subassembly_models, to_assembly_subassembly_model
from ..objects.result_freshness import document_result_freshness
from ..services.editing import prepare_drainage_edit
from ..services.editing.drainage_editing_service import (
    RoadStationSpan,
    ditch_choices,
    ditch_run_diagnostics,
    point_diagnostics,
    policy_diagnostics,
    prefill_ditch_runs,
)
from ..services.evaluation.result_freshness_service import APPLIED_SECTIONS, CURRENT, DRAINAGE, MISSING, STALE
from .cmd_drainage_result import apply_v1_drainage_result, drainage_result_summary
from ..ui.editors.drainage_editor import V1DrainageEditorTaskPanel, configure_drainage_editor_task_panel_runtime


class CmdV1DrainageEditor:
    def GetResources(self):
        return {
            "Pixmap": icon_path("drainage.svg"),
            "MenuText": "Drainage",
            "ToolTip": "Edit which Assembly ditches drain the road, and the drainage policy",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_drainage_editor_command()


def run_v1_drainage_editor_command(document=None):
    """Open the v1 Drainage editor panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    panel = V1DrainageEditorTaskPanel(document=doc)
    if _gui_available() and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def drainage_editor_inputs(document) -> dict[str, object]:
    """What the Drainage editor shows: the stored model, the ditches it can name, and a prefill.

    Reads the document only. When the stored model has no Ditch Runs, `prefilled` is True and the
    model carries the runs prefilled from the Regions and the Assembly; nothing is written.
    """

    assembly_models = _assembly_models(document)
    stored = to_drainage_model(find_v1_drainage_model(document))
    model = stored or DrainageModel(schema_version=1, project_id=_project_id(find_project(document)))
    prefill = prefill_ditch_runs(_roads(document), assembly_models)
    prefilled = not model.ditch_run_rows and bool(prefill)
    if prefilled:
        model = DrainageModel(
            schema_version=model.schema_version,
            project_id=model.project_id,
            label=model.label,
            drainage_model_id=model.drainage_model_id,
            policy=model.policy,
            ditch_run_rows=prefill,
            point_rows=list(model.point_rows),
            link_rows=list(model.link_rows),
        )
    return {
        "model": model,
        "choices": ditch_choices(assembly_models),
        "alignment_ids": [road.alignment_id for road in _roads(document)],
        "prefill": prefill,
        "prefilled": prefilled,
    }


def apply_v1_drainage_model(*, document=None, drainage_model: DrainageModel):
    """Persist a DrainageModel into the document after its checks pass."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    messages = (
        policy_diagnostics(drainage_model.policy)
        + ditch_run_diagnostics(drainage_model.ditch_run_rows, ditch_choices(_assembly_models(doc)))
        + point_diagnostics(drainage_model.point_rows, drainage_model.ditch_run_rows)
    )
    if messages:
        raise ValueError("Drainage was not applied:\n" + "\n".join(messages))
    prepared = prepare_drainage_edit(drainage_model)
    return create_or_update_v1_drainage_model_object(doc, drainage_model=prepared.model, project=find_project(doc))


def refresh_drainage_result(document) -> str:
    """After a Drainage write: evaluate it when the Applied Sections are current, else say what to run.

    A Ditch Run change retags the ditch points, so it makes the Applied Sections stale and the
    evaluation waits for Rebuild Downstream; a Policy change evaluates at once.
    """

    applied = next(row for row in document_result_freshness(document) if row.stage == APPLIED_SECTIONS)
    if applied.status == MISSING:
        return "Build Applied Sections, then run Rebuild Downstream to evaluate the Drainage."
    if applied.status == STALE:
        return (
            f"Applied Sections are stale ({', '.join(applied.changed_inputs)}). "
            "Run Rebuild Downstream to retag the ditch points and evaluate the Drainage."
        )
    return drainage_result_summary(to_drainage_result(apply_v1_drainage_result(document)))


def drainage_suggestions(document) -> tuple[list, str]:
    """The points the stored Drainage result suggests, and a note when there are none to offer.

    Suggestions of a stale result may sit at stations that no longer hold, so none are offered then.
    """

    result = to_drainage_result(find_v1_drainage_result_object(document))
    if result is None:
        return [], "No Drainage result yet: Apply, or run Rebuild Downstream, to get suggestions."
    row = next(row for row in document_result_freshness(document) if row.stage == DRAINAGE)
    if row.status != CURRENT:
        return [], "The Drainage result is stale; run Rebuild Downstream for current suggestions."
    if not result.suggestion_rows:
        return [], "No suggestions: every low point is collected and the inlet spacing holds."
    return list(result.suggestion_rows), f"{len(result.suggestion_rows)} suggestion(s)."


def drainage_status_text(document) -> str:
    """The stored Drainage result's summary and whether it is current."""

    result = to_drainage_result(find_v1_drainage_result_object(document))
    if result is None:
        return ""
    row = next(row for row in document_result_freshness(document) if row.stage == DRAINAGE)
    state = "current" if row.status == CURRENT else f"stale ({', '.join(row.changed_inputs)}); run Rebuild Downstream"
    return f"Stored Drainage result: {state}.\n" + drainage_result_summary(result)


def _assembly_models(document) -> list:
    models = [to_assembly_subassembly_model(obj) for obj in list_v1_assembly_subassembly_models(document)]
    return [model for model in models if model is not None]


def _roads(document) -> list[RoadStationSpan]:
    """One span per road: its Regions, or the span of its Stations when it has no Regions."""

    regions = {}
    for obj in list_v1_region_models(document):
        model = to_region_model(obj)
        if model is not None and list(model.region_rows or []):
            regions.setdefault(str(model.alignment_id or ""), model)
    roads: list[RoadStationSpan] = []
    for stationing in list_v1_stationings(document):
        alignment_id = str(getattr(stationing, "AlignmentId", "") or "")
        stations = [station for station, _label in station_value_rows(stationing)]
        if any(road.alignment_id == alignment_id for road in roads) or not stations:
            continue
        roads.append(RoadStationSpan(alignment_id, regions.get(alignment_id), min(stations), max(stations)))
    for alignment_id, model in regions.items():
        if not any(road.alignment_id == alignment_id for road in roads):
            roads.append(RoadStationSpan(alignment_id, model))
    return roads


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))


configure_drainage_editor_task_panel_runtime(
    {
        "App": App,
        "Gui": Gui,
        "apply_v1_drainage_model": apply_v1_drainage_model,
        "drainage_editor_inputs": drainage_editor_inputs,
        "drainage_status_text": drainage_status_text,
        "drainage_suggestions": drainage_suggestions,
        "refresh_drainage_result": refresh_drainage_result,
    }
)


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditDrainage", CmdV1DrainageEditor())
