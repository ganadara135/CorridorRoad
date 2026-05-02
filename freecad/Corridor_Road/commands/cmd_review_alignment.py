# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.ui.task_alignment_editor import (
    _find_alignments,
    build_alignment_review_text,
    show_alignment_review_dialog,
)


def _resolve_alignment(document, gui_module=Gui):
    try:
        selection = list(gui_module.Selection.getSelection() or [])
    except Exception:
        selection = []
    for obj in selection:
        try:
            if str(getattr(obj, "Name", "") or "").startswith("HorizontalAlignment"):
                return obj
        except Exception:
            pass

    project = find_project(document) if document is not None else None
    alignment = getattr(project, "Alignment", None) if project is not None else None
    if alignment is not None:
        return alignment

    alignments = _find_alignments(document)
    if alignments:
        return alignments[0]
    return None


def run_alignment_review_command(
    *,
    app_module=App,
    gui_module=Gui,
    resolve_alignment=None,
    show_review=None,
):
    document = getattr(app_module, "ActiveDocument", None)
    if resolve_alignment is None:
        resolve_alignment = lambda doc: _resolve_alignment(doc, gui_module)
    if show_review is None:
        show_review = show_alignment_review_dialog

    alignment = resolve_alignment(document)
    show_review(
        parent=None,
        document=document,
        alignment=alignment,
        selected_row_label="",
        focus_station_label="",
        summary_lines=[],
    )
    return alignment


class CmdReviewAlignment:
    def GetResources(self):
        return {
            "Pixmap": icon_path("alignment.svg"),
            "MenuText": "Review Alignment",
            "ToolTip": "Review horizontal alignment geometry before generating stations",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        run_alignment_review_command()


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_ReviewAlignment", CmdReviewAlignment())
