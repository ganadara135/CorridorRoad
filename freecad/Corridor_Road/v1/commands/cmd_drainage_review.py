"""Drainage Review command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project

from ..models.output.drainage_output import DrainageOutput
from ..objects.obj_drainage import find_v1_drainage_model, to_drainage_model
from ..objects.obj_drainage_result import find_v1_drainage_result_object, to_drainage_result
from ..objects.project_document_adapter import route_object_to_project_tree
from ..objects.result_freshness import document_result_freshness
from ..services.evaluation.result_freshness_service import CURRENT, DRAINAGE
from ..services.mapping.drainage_output_mapper import DrainageOutputMapper
from ..ui.viewers.drainage_review_view import V1DrainageReviewTaskPanel, configure_drainage_review_task_panel_runtime

HIGHLIGHT_OBJECT_NAME = "ReviewDrainageCheckHighlight"
# The flowline lies on the ditch surface, so a marker drawn on it shares its faces and shows
# through them in pieces. The stretch is drawn this far above the flowline, the station marker on a
# stem rising to this height (meters, the model's units).
_STRETCH_LIFT_M = 0.05
_MARKER_LIFT_M = 1.5
_MARKER_RADIUS_M = 0.35
_HIGHLIGHT_COLORS = {"error": (0.85, 0.15, 0.15), "warning": (0.95, 0.55, 0.05), "info": (0.2, 0.45, 0.85)}


class CmdV1DrainageReview:
    """Open the read-only Drainage Review panel."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("drainage_review.svg"),
            "MenuText": "Drainage Review",
            "ToolTip": "Review the Drainage flowlines, points, links and their checks",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_drainage_review_command()


def run_v1_drainage_review_command(document=None):
    """Open the v1 Drainage Review task panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    panel = V1DrainageReviewTaskPanel(document=doc)
    if _gui_available() and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def build_drainage_output(document) -> DrainageOutput | None:
    """The Drainage output of the stored source and result, or None when either is missing."""

    model = to_drainage_model(find_v1_drainage_model(document))
    result = to_drainage_result(find_v1_drainage_result_object(document))
    if model is None or result is None:
        return None
    return DrainageOutputMapper().map(model, result)


def drainage_review_state(document) -> tuple[DrainageOutput | None, str]:
    """The output to review and one line on whether its result is current."""

    output = build_drainage_output(document)
    if output is None:
        return None, ""
    row = next(row for row in document_result_freshness(document) if row.stage == DRAINAGE)
    if row.status == CURRENT:
        return output, "The Drainage result is current."
    return output, f"The Drainage result is stale ({', '.join(row.changed_inputs)}); run Rebuild Downstream."


def focus_drainage_check(document, check_ref: str):
    """Highlight one check on its flowline in the 3D view: the stretch it flags, or its station."""

    result = to_drainage_result(find_v1_drainage_result_object(document))
    check = next((row for row in (result.check_rows if result else []) if row.check_id == check_ref), None)
    if check is None:
        raise ValueError(f"No Drainage check {check_ref}; refresh the review.")
    flowlines = [row for row in result.flowline_rows if not check.ditch_run_ref or row.ditch_run_ref == check.ditch_run_ref]
    stations = []
    for flowline in flowlines:
        rows = flowline.station_rows
        if rows and rows[0].station - 1.0e-6 <= check.station_start <= rows[-1].station + 1.0e-6:
            stations = rows
            break
    if not stations:
        raise RuntimeError(f"{check_ref}: no flowline reaches STA {check.station_start:.3f}.")
    import Part

    inside = [row for row in stations if check.station_start - 1.0e-6 <= row.station <= check.station_end + 1.0e-6]
    anchor = min(stations, key=lambda row: abs(row.station - check.station_start))
    foot = App.Vector(anchor.x, anchor.y, anchor.z)
    head = App.Vector(anchor.x, anchor.y, anchor.z + _MARKER_LIFT_M)
    shapes = [Part.makeLine(foot, head), Part.makeSphere(_MARKER_RADIUS_M, head)]
    if len(inside) >= 2:
        shapes.append(Part.makePolygon([App.Vector(row.x, row.y, row.z + _STRETCH_LIFT_M) for row in inside]))
    obj = document.getObject(HIGHLIGHT_OBJECT_NAME) or document.addObject("Part::Feature", HIGHLIGHT_OBJECT_NAME)
    obj.Shape = Part.makeCompound(shapes)
    obj.Label = f"Drainage check: {check.kind} STA {check.station_start:.3f}"
    for name, value in (("CRRecordKind", "v1_review_issue"), ("IssueKind", "drainage_station")):
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "Review", name)
        setattr(obj, name, value)
    project = find_project(document)
    if project is not None:
        route_object_to_project_tree(project, obj)
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        color = _HIGHLIGHT_COLORS.get(check.severity, (0.2, 0.2, 0.2))
        view.ShapeColor = color
        view.LineColor = color
        view.LineWidth = 4.0
        if hasattr(view, "Deviation"):
            # a fine tessellation keeps the small marker sphere round
            view.Deviation = 0.05
        view.Visibility = True
    if _gui_available():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        Gui.SendMsgToActiveView("ViewSelection")
    return obj


def open_drainage_editor(document):
    """Close Drainage Review and open the Drainage panel."""

    from .cmd_drainage_editor import run_v1_drainage_editor_command

    if _gui_available():
        Gui.Control.closeDialog()
    return run_v1_drainage_editor_command(document)


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))


configure_drainage_review_task_panel_runtime(
    {
        "App": App,
        "Gui": Gui,
        "drainage_review_state": drainage_review_state,
        "focus_drainage_check": focus_drainage_check,
        "open_drainage_editor": open_drainage_editor,
    }
)


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1DrainageReview", CmdV1DrainageReview())
