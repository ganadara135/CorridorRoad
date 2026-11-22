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

HIGHLIGHT_OBJECT_NAME = "ReviewDrainageCheckHighlight"
PIPE_OBJECT_NAME = "ReviewDrainagePipes"
INTERSECTION_LOW_OBJECT_NAME = "ReviewDrainageIntersectionLowPoint"
_PIPE_COLOR = (0.25, 0.45, 0.75)
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
    """Open the Drainage panel on its Review tab: the review and the editing share one panel."""

    from .cmd_drainage_editor import V1DrainageEditorTaskPanel

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    if _gui_available() and hasattr(Gui, "Control"):
        Gui.Control.closeDialog()
    panel = V1DrainageEditorTaskPanel(document=doc)
    panel._tabs.setCurrentWidget(panel._review_tab)
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


def drainage_intersection_low_state(document):
    """The intersection kernel's result for its low points, and one line on what it shows.

    The kernel evaluates the stored Intersection on the current Applied Sections and nothing is
    stored; a document without an Intersection gives (None, "").
    """

    # Imported here: the Build Parametric command opens this review.
    from .cmd_build_corridor import _document_has_intersection, _document_intersection_kernel_result

    if not _document_has_intersection(document):
        return None, ""
    result = _document_intersection_kernel_result(document)
    if result is None:
        return None, "No intersection result: check the Intersection spec and build Applied Sections."
    if result.status == "blocked":
        codes = ", ".join(sorted({row.code for row in result.diagnostics if row.effect == "blocked"}))
        return None, f"{result.intersection_id} is blocked ({codes}), so it has no low points. Inspect the Intersection panel."
    if not result.drainage_candidates:
        return result, f"{result.intersection_id} ({result.status}) reports no low point."
    partial = " The intersection result is partial." if result.status == "partial" else ""
    return result, f"Where water standing on the intersection surface collects. Not checked against the Drainage points.{partial}"


def focus_drainage_intersection_low(document, label: str, places):
    """Mark the places of one intersection low point in the 3D view (meters, a review preview)."""

    if not places:
        raise ValueError("The intersection low point has no place; refresh the review.")
    import Part

    shapes = []
    for x, y, z in places:
        head = App.Vector(x, y, z + _MARKER_LIFT_M)
        shapes += [Part.makeLine(App.Vector(x, y, z), head), Part.makeSphere(_MARKER_RADIUS_M, head)]
    obj = document.getObject(INTERSECTION_LOW_OBJECT_NAME) or document.addObject("Part::Feature", INTERSECTION_LOW_OBJECT_NAME)
    obj.Shape = Part.makeCompound(shapes)
    obj.Label = f"Intersection low point: {label}"
    for name, value in (("CRRecordKind", "v1_review_issue"), ("IssueKind", "drainage_intersection_low")):
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "Review", name)
        setattr(obj, name, value)
    project = find_project(document)
    if project is not None:
        route_object_to_project_tree(project, obj)
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        color = _HIGHLIGHT_COLORS["info"]
        view.ShapeColor = color
        view.LineColor = color
        view.LineWidth = 4.0
        if hasattr(view, "Deviation"):
            view.Deviation = 0.05
        view.Visibility = True
    if _gui_available():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        Gui.SendMsgToActiveView("ViewSelection")
    return obj


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


def focus_drainage_pipe(document, link_ref: str = ""):
    """Draw one pipe, or every pipe when `link_ref` is empty, as a tube between its end inverts.

    The tube is a review preview of the stored result (meters, the model's units); it is not a
    source and is replaced the next time it is drawn.
    """

    result = to_drainage_result(find_v1_drainage_result_object(document))
    pipes = [row for row in (result.pipe_rows if result else []) if not link_ref or row.link_ref == link_ref]
    if not pipes:
        raise ValueError(f"No Drainage pipe {link_ref}; refresh the review." if link_ref else "The Drainage result has no pipes.")
    import Part

    shapes = []
    for pipe in pipes:
        start = App.Vector(pipe.from_x, pipe.from_y, pipe.from_z)
        axis = App.Vector(pipe.to_x, pipe.to_y, pipe.to_z) - start
        if axis.Length <= 0.0:
            raise RuntimeError(f"{pipe.link_ref}: the pipe has no length, so it cannot be drawn.")
        shapes.append(Part.makeCylinder(pipe.diameter_m / 2.0, axis.Length, start, axis))
    obj = document.getObject(PIPE_OBJECT_NAME) or document.addObject("Part::Feature", PIPE_OBJECT_NAME)
    obj.Shape = Part.makeCompound(shapes)
    obj.Label = f"Drainage pipe: {link_ref}" if link_ref else f"Drainage pipes ({len(pipes)})"
    for name, value in (("CRRecordKind", "v1_review_issue"), ("IssueKind", "drainage_pipe")):
        if not hasattr(obj, name):
            obj.addProperty("App::PropertyString", name, "Review", name)
        setattr(obj, name, value)
    project = find_project(document)
    if project is not None:
        route_object_to_project_tree(project, obj)
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.ShapeColor = _PIPE_COLOR
        view.Visibility = True
    if _gui_available():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        Gui.SendMsgToActiveView("ViewSelection")
    return obj


# The Drainage shown in the 3D view: one object per kind, so each kind has its colour. The bodies
# are review markers at the points' places on the flowlines (meters, the model's units); their
# sizes say "a point is here", they are not the dimensions of a real inlet or headwall. A pipe is
# its real diameter and length.
STRUCTURE_OBJECT_NAMES = {
    "inlet": "DrainageInlets",
    "outfall": "DrainageOutfalls",
    "culvert": "DrainageCulverts",
    "pipe": "DrainagePipes",
    "open_link": "DrainageOpenLinks",
}
_STRUCTURE_LABELS = {
    "inlet": "Drainage inlets",
    "outfall": "Drainage outfalls",
    "culvert": "Drainage culverts",
    "pipe": "Drainage pipes",
    "open_link": "Drainage open-flow links",
}
_STRUCTURE_COLORS = {
    "inlet": (0.12, 0.55, 0.24),
    "outfall": (0.08, 0.24, 0.67),
    "culvert": (0.51, 0.24, 0.63),
    "pipe": (0.59, 0.39, 0.20),
    "open_link": (0.30, 0.60, 0.30),
}
_INLET_SIZE_M = (1.0, 1.0, 0.8)  # plan x plan x height; the top stands 0.2 m above the flowline
_INLET_TOP_ABOVE_M = 0.2
_OUTFALL_RADIUS_M = 0.6
_OUTFALL_HEIGHT_M = 0.5
_CULVERT_SIZE_M = (1.4, 1.4, 1.2)


def show_drainage_structures(document, *, only_existing: bool = False) -> dict[str, int]:
    """Draw the stored Drainage in the 3D view and return how many of each kind were drawn.

    Inlets, outfalls and culverts are markers at their places on the flowlines, a piped link is a
    tube between its ends, and an open-flow link a line. They are a presentation of the stored
    result, replaced each time; nothing reads them back. With `only_existing`, objects already in
    the document are brought up to date and none is created, so a rebuild keeps a shown Drainage
    true without drawing one nobody asked for.
    """

    if document is None:
        return {}
    if only_existing and not any(document.getObject(name) is not None for name in STRUCTURE_OBJECT_NAMES.values()):
        return {}
    import Part

    output = build_drainage_output(document)
    shapes: dict[str, list] = {kind: [] for kind in STRUCTURE_OBJECT_NAMES}
    places = {}
    for point in output.point_rows if output is not None else []:
        if point.x is None or point.y is None or point.z is None:
            continue
        places[point.point_ref] = App.Vector(point.x, point.y, point.z)
        if point.kind == "inlet":
            dx, dy, dz = _INLET_SIZE_M
            shapes["inlet"].append(Part.makeBox(dx, dy, dz, App.Vector(point.x - dx / 2.0, point.y - dy / 2.0, point.z + _INLET_TOP_ABOVE_M - dz)))
        elif point.kind == "outfall":
            shapes["outfall"].append(
                Part.makeCylinder(_OUTFALL_RADIUS_M, _OUTFALL_HEIGHT_M, App.Vector(point.x, point.y, point.z - _OUTFALL_HEIGHT_M / 2.0))
            )
        elif point.kind == "culvert":
            dx, dy, dz = _CULVERT_SIZE_M
            shapes["culvert"].append(Part.makeBox(dx, dy, dz, App.Vector(point.x - dx / 2.0, point.y - dy / 2.0, point.z - dz / 2.0)))
    piped = set()
    for pipe in output.pipe_rows if output is not None else []:
        start = App.Vector(*pipe.from_xyz)
        axis = App.Vector(*pipe.to_xyz) - start
        if axis.Length <= 0.0:
            continue
        piped.add(pipe.link_ref)
        shapes["pipe"].append(Part.makeCylinder(pipe.diameter_m / 2.0, axis.Length, start, axis))
    lift = App.Vector(0.0, 0.0, _STRETCH_LIFT_M)
    for link in output.link_rows if output is not None else []:
        start, end = places.get(link.from_ref), places.get(link.to_ref)
        if link.link_ref in piped or start is None or end is None or (end - start).Length <= 0.0:
            continue
        shapes["open_link"].append(Part.makeLine(start + lift, end + lift))

    project = find_project(document)
    for kind, name in STRUCTURE_OBJECT_NAMES.items():
        obj = document.getObject(name)
        if not shapes[kind]:
            if obj is not None:
                document.removeObject(name)
            continue
        if obj is None:
            obj = document.addObject("Part::Feature", name)
        obj.Shape = Part.makeCompound(shapes[kind])
        obj.Label = f"{_STRUCTURE_LABELS[kind]} ({len(shapes[kind])})"
        for prop, value in (("CRRecordKind", "v1_drainage_preview"), ("PreviewKind", kind)):
            if not hasattr(obj, prop):
                obj.addProperty("App::PropertyString", prop, "Review", prop)
            setattr(obj, prop, value)
        if project is not None:
            route_object_to_project_tree(project, obj)
        view = getattr(obj, "ViewObject", None)
        if view is not None:
            view.ShapeColor = _STRUCTURE_COLORS[kind]
            view.LineColor = _STRUCTURE_COLORS[kind]
            if kind == "open_link":
                view.LineWidth = 3.0
            view.Visibility = True
    return {kind: len(rows) for kind, rows in shapes.items()}


def _gui_available() -> bool:
    return bool(Gui is not None and getattr(App, "GuiUp", False))


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1DrainageReview", CmdV1DrainageReview())
