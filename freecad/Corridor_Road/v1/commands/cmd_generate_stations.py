"""v1 station generation command."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ...objects.project_links import link_project
from ..objects.obj_alignment import find_v1_alignment, to_alignment_model
from ..objects.obj_stationing import create_v1_stationing, find_v1_stationing
from .cmd_create_alignment import create_v1_sample_alignment
from .cmd_review_plan_profile import resolve_station_interval
from .selection_context import selected_alignment_profile_target


def generate_v1_stations(
    *,
    document=None,
    project=None,
    alignment=None,
    interval: float = 20.0,
):
    """Generate v1 station rows for a v1 alignment and route them into the project tree."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document.")

    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"

    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    alignment_obj = alignment or find_v1_alignment(doc)
    if alignment_obj is None:
        alignment_obj = create_v1_sample_alignment(document=doc, project=prj)
    previous_stationing = find_v1_stationing(doc)
    stale_note = _previous_stationing_stale_note(previous_stationing, alignment_obj)

    stationing = create_v1_stationing(
        doc,
        project=prj,
        alignment=alignment_obj,
        interval=interval,
    )
    if stale_note:
        try:
            stationing.Notes = f"{stationing.Notes} | {stale_note}"
        except Exception:
            pass
    link_project(
        prj,
        links={"Stationing": stationing},
        links_if_empty={"Alignment": alignment_obj},
        adopt_extra=[alignment_obj, stationing],
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return stationing


def run_v1_generate_stations_command():
    """Generate v1 stations from current GUI context."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    preferred_alignment, _preferred_profile = selected_alignment_profile_target(Gui, document)
    interval = 20.0
    existing = find_v1_stationing(document)
    if existing is not None:
        try:
            interval = float(getattr(existing, "Interval", 20.0) or 20.0)
        except Exception:
            interval = 20.0
    interval = resolve_station_interval({"station_interval": interval})
    stationing = generate_v1_stations(
        document=document,
        alignment=preferred_alignment,
        interval=interval,
    )
    if Gui is not None:
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(stationing)
        except Exception:
            pass
    return stationing


class CmdV1GenerateStations:
    """Open the unified v1 stationing generation/review panel."""

    def GetResources(self):
        from freecad.Corridor_Road.misc.resources import icon_path

        return {
            "Pixmap": icon_path("stations.svg"),
            "MenuText": "Stations (v1)",
            "ToolTip": "Generate, review, and configure v1 station rows from the v1 alignment",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        from .cmd_review_stations import run_v1_stationing_review_command

        stationing = run_v1_stationing_review_command()
        if App is not None and stationing is not None:
            try:
                App.Console.PrintMessage(_station_generation_console_text(stationing))
            except Exception:
                pass


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1GenerateStations", CmdV1GenerateStations())


def _previous_stationing_stale_note(previous_stationing, alignment_obj) -> str:
    if previous_stationing is None or alignment_obj is None:
        return ""
    alignment_model = to_alignment_model(alignment_obj)
    if alignment_model is None:
        return ""
    try:
        from ..objects.obj_stationing import _alignment_geometry_signature

        new_signature = _alignment_geometry_signature(alignment_model)
    except Exception:
        return ""
    old_signature = str(getattr(previous_stationing, "SourceGeometrySignature", "") or "")
    if old_signature and old_signature != new_signature:
        return "previous_stationing_was_stale=true"
    return ""


def _station_generation_console_text(stationing) -> str:
    count = len(list(getattr(stationing, "StationValues", []) or []))
    alignment_id = str(getattr(stationing, "AlignmentId", "") or "")
    kind_summary = str(getattr(stationing, "ActiveElementKindSummary", "") or "none")
    transition_count = int(getattr(stationing, "TransitionStationCount", 0) or 0)
    curve_count = int(getattr(stationing, "CurveStationCount", 0) or 0)
    return (
        f"Generated {count} v1 stations. "
        f"Alignment={alignment_id}; "
        f"kinds={kind_summary}; "
        f"curve={curve_count}; transition={transition_count}.\n"
    )
