"""Rebuild Downstream: rebuild the stale result stages in workflow order.

It rebuilds results only (Stations, 3D Centerline, Applied Sections, Build Parametric), never writes a source and
never runs a review. A stage runs when it is stale or when a stage it consumes was rebuilt in the
same run; current and missing stages are skipped. Each stage reuses the options recorded with its
result, so no dialog is shown. A failing stage stops the run; the stages after it stay stale.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ...misc.resources import icon_path
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_applied_section import find_v1_applied_section_set
from ..objects.obj_corridor import find_v1_corridor_model
from ..objects.result_freshness import document_result_freshness, find_centerline3d_object, stationing_freshness_rows
from ..objects.stage_inputs import read_stage_options
from ..services.evaluation.result_freshness_service import (
    APPLIED_SECTIONS,
    BUILD_PARAMETRIC,
    CENTERLINE3D,
    MISSING,
    RESULT_STAGES,
    STAGE_LABELS,
    STALE,
    STATIONING,
    UPSTREAM_STAGE,
    stale_stages,
)


REBUILD_DOWNSTREAM_COMMAND_ID = "CorridorRoad_RebuildDownstream"
REBUILT = "rebuilt"
SKIPPED = "skipped"
FAILED = "failed"

# Options a recorded result may carry, per stage; anything else in an older record is ignored.
_CENTERLINE3D_OPTIONS = (
    "show_station_markers",
    "display_mode",
    "arc_fit_absolute_tolerance",
    "arc_fit_relative_tolerance",
    "source_geometry_sample_spacing",
)
_APPLIED_SECTIONS_OPTIONS = (
    "supplemental_sections_enabled",
    "supplemental_sections_max_spacing",
    "supplemental_sections_tangent_delta_deg",
    "supplemental_sections_chord_deviation",
    "supplemental_sections_vertical_chord_deviation",
    "supplemental_sections_grade_delta",
)
_BUILD_PARAMETRIC_OPTIONS = (
    "build_surfaces",
    "show_daylight_contact_markers",
    "supplemental_sampling_enabled",
    "supplemental_sampling_max_spacing",
    "supplemental_sampling_tangent_delta_deg",
    "supplemental_sampling_chord_deviation",
)


@dataclass(frozen=True)
class RebuildStageOutcome:
    stage: str
    outcome: str
    object_names: tuple[str, ...] = ()
    message: str = ""

    @property
    def text(self) -> str:
        label = STAGE_LABELS.get(self.stage, self.stage)
        names = f" [{', '.join(self.object_names)}]" if self.object_names else ""
        return f"{label}: {self.outcome}{names}" + (f" - {self.message}" if self.message else "")


@dataclass(frozen=True)
class RebuildDownstreamReport:
    outcomes: tuple[RebuildStageOutcome, ...]

    @property
    def failed(self) -> bool:
        return any(row.outcome == FAILED for row in self.outcomes)

    @property
    def rebuilt_stages(self) -> tuple[str, ...]:
        return tuple(row.stage for row in self.outcomes if row.outcome == REBUILT)

    @property
    def text(self) -> str:
        return "\n".join(row.text for row in self.outcomes)


def rebuild_downstream(document, *, through: str = BUILD_PARAMETRIC) -> RebuildDownstreamReport:
    """Rebuild the stale stages up to and including `through`."""

    if document is None:
        raise RuntimeError("No active document.")
    freshness = {row.stage: row for row in document_result_freshness(document)}
    outcomes: list[RebuildStageOutcome] = []
    rebuilt: set[str] = set()
    for stage in RESULT_STAGES[: RESULT_STAGES.index(through) + 1]:
        row = freshness[stage]
        upstream_rebuilt = UPSTREAM_STAGE.get(stage) in rebuilt
        if row.status == MISSING:
            outcomes.append(RebuildStageOutcome(stage, SKIPPED, message="not built yet"))
            continue
        if row.status != STALE and not upstream_rebuilt:
            outcomes.append(RebuildStageOutcome(stage, SKIPPED, row.object_names, "current"))
            continue
        try:
            names = _REBUILDERS[stage](document)
        except Exception as exc:
            # The stage stops the run; its diagnostic names the stage and objects it was rebuilding.
            outcomes.append(RebuildStageOutcome(stage, FAILED, row.object_names, str(exc)))
            break
        rebuilt.add(stage)
        outcomes.append(RebuildStageOutcome(stage, REBUILT, names))
    return RebuildDownstreamReport(tuple(outcomes))


def _rebuild_stationing(document) -> tuple[str, ...]:
    from .cmd_generate_stations import generate_v1_stations

    names = []
    for row in stationing_freshness_rows(document):
        if row.status != STALE:
            continue
        stationing = document.getObject(row.object_names[0])
        alignment_id = str(getattr(stationing, "AlignmentId", "") or "")
        alignment = find_v1_alignment(document, alignment_id=alignment_id)
        if alignment is None:
            raise RuntimeError(f"{stationing.Label}: its Alignment {alignment_id} no longer exists.")
        interval = float(read_stage_options(stationing).get("interval", getattr(stationing, "Interval", 20.0)) or 20.0)
        generate_v1_stations(document=document, alignment=alignment, interval=interval)
        names.append(str(stationing.Name))
    return tuple(names)


def _rebuild_centerline3d(document) -> tuple[str, ...]:
    from .cmd_centerline3d import show_v1_centerline3d_preview_object

    options = _known_options(read_stage_options(find_centerline3d_object(document)), _CENTERLINE3D_OPTIONS)
    obj = show_v1_centerline3d_preview_object(document, **options)
    return (str(obj.Name),)


def _rebuild_applied_sections(document) -> tuple[str, ...]:
    from .cmd_generate_applied_sections import apply_v1_applied_section_set, build_document_applied_section_set

    options = _known_options(read_stage_options(find_v1_applied_section_set(document)), _APPLIED_SECTIONS_OPTIONS)
    applied = build_document_applied_section_set(document, **options)
    obj = apply_v1_applied_section_set(document=document, applied_section_set=applied, build_options=options)
    return (str(obj.Name),)


def _rebuild_build_parametric(document) -> tuple[str, ...]:
    from .cmd_build_corridor import apply_v1_corridor_model, build_document_corridor_model

    options = _known_options(read_stage_options(find_v1_corridor_model(document)), _BUILD_PARAMETRIC_OPTIONS)
    obj = apply_v1_corridor_model(document=document, corridor_model=build_document_corridor_model(document), **options)
    return (str(obj.Name),)


_REBUILDERS = {
    STATIONING: _rebuild_stationing,
    CENTERLINE3D: _rebuild_centerline3d,
    APPLIED_SECTIONS: _rebuild_applied_sections,
    BUILD_PARAMETRIC: _rebuild_build_parametric,
}


def _known_options(options: dict[str, object], names: tuple[str, ...]) -> dict[str, object]:
    return {key: value for key, value in options.items() if key in names}


# FreeCAD asks IsActive many times a second; a freshness check reads every source, so its answer
# is reused for this long per document.
_IS_ACTIVE_TTL_SECONDS = 2.0
_is_active_cache: dict[str, tuple[float, bool]] = {}


def document_has_stale_results(document) -> bool:
    if document is None:
        return False
    key = str(getattr(document, "Name", "") or "")
    now = time.monotonic()
    cached = _is_active_cache.get(key)
    if cached is not None and now - cached[0] < _IS_ACTIVE_TTL_SECONDS:
        return cached[1]
    try:
        value = bool(stale_stages(document_result_freshness(document)))
    except Exception as exc:
        # A freshness check that cannot read the document leaves the command available; running
        # it reports the error.
        if App is not None:
            App.Console.PrintWarning(f"Rebuild Downstream: freshness check failed: {exc}\n")
        value = True
    _is_active_cache[key] = (now, value)
    return value


def run_v1_rebuild_downstream_command(document=None, *, through: str = BUILD_PARAMETRIC) -> RebuildDownstreamReport:
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    report = rebuild_downstream(doc, through=through)
    _is_active_cache.pop(str(getattr(doc, "Name", "") or ""), None)
    if App is not None:
        App.Console.PrintMessage("Rebuild Downstream\n" + report.text + "\n")
    return report


class CmdV1RebuildDownstream:
    """Rebuild every stale result stage with its recorded options."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("rebuild_downstream.svg"),
            "MenuText": "Rebuild Downstream",
            "ToolTip": "Rebuild the stale Stations, 3D Centerline, Applied Sections and Build Parametric results with their last options",
        }

    def IsActive(self):
        return document_has_stale_results(getattr(App, "ActiveDocument", None) if App is not None else None)

    def Activated(self):
        report = run_v1_rebuild_downstream_command()
        try:
            from ...qt_compat import QtWidgets

            show = QtWidgets.QMessageBox.warning if report.failed else QtWidgets.QMessageBox.information
            show(None, "Rebuild Downstream", report.text)
        except ImportError:
            pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(REBUILD_DOWNSTREAM_COMMAND_ID, CmdV1RebuildDownstream())


__all__ = [
    "CmdV1RebuildDownstream",
    "REBUILD_DOWNSTREAM_COMMAND_ID",
    "RebuildDownstreamReport",
    "RebuildStageOutcome",
    "document_has_stale_results",
    "rebuild_downstream",
    "run_v1_rebuild_downstream_command",
]
