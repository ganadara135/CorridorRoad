"""Drainage Review panel for CorridorRoad v1.

The review is rebuilt in the Drainage rework (DR-5, docsV1/V1_DRAINAGE_REWORK_PLAN.md) on the
evaluated Drainage result. Until then the panel says so and reviews nothing.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.ui.common.panel_width import fit_task_panel_width

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None


DRAINAGE_REVIEW_PENDING_NOTE = (
    "Drainage Review is being rebuilt with the new Drainage source. "
    "Ditch Runs are edited in the Drainage panel; the flowline review and its checks come with the "
    "Drainage evaluation."
)


class V1DrainageReviewTaskPanel:
    """Read-only Drainage Review panel; reviews nothing until the Drainage evaluation exists."""

    def __init__(self, *, document=None):
        self.document = document
        self.form = fit_task_panel_width(self._build_ui())

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self.reject()

    def reject(self):
        if Gui is not None and bool(getattr(App, "GuiUp", False)) and hasattr(Gui, "Control"):
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("ParametricRoad v1 - Drainage Review")
        layout = QtWidgets.QVBoxLayout(widget)
        note = QtWidgets.QLabel(DRAINAGE_REVIEW_PENDING_NOTE)
        note.setWordWrap(True)
        layout.addWidget(note)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button)
        return widget
