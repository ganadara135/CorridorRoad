import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import build_demo_plan_profile_preview
from freecad.Corridor_Road.v1.commands.cmd_review_stations import (
    show_station_highlight as command_show_station_highlight,
)
from freecad.Corridor_Road.v1.ui.presentation import (
    StationHighlightPresentationService,
    show_station_highlight,
)
from freecad.Corridor_Road.v1.ui.viewers import profile_review_view
from freecad.Corridor_Road.v1.ui.viewers.profile_review_view import PlanProfileViewerTaskPanel


class _StatusLabel:
    def __init__(self) -> None:
        self.text = ""
        self.style = ""

    def setText(self, value: str) -> None:
        self.text = str(value)

    def setStyleSheet(self, value: str) -> None:
        self.style = str(value)


def test_station_command_keeps_presentation_service_compatibility_export() -> None:
    assert command_show_station_highlight is show_station_highlight
    assert StationHighlightPresentationService().build_shape(
        {"x": 10.0, "y": 20.0, "tangent": 45.0},
        radius=4.0,
    ) is not None


def test_profile_viewer_highlights_same_context_without_command_import() -> None:
    doc = App.newDocument("ProfileViewerPresentationServiceContract")
    original_gui = profile_review_view.Gui
    profile_review_view.Gui = None
    try:
        panel = PlanProfileViewerTaskPanel.__new__(PlanProfileViewerTaskPanel)
        panel.preview = build_demo_plan_profile_preview("Demo Corridor")
        panel._status_label = _StatusLabel()

        row = panel._station_highlight_row(40.0)
        panel._highlight_station_value(40.0)
        marker = next(
            obj
            for obj in list(doc.Objects)
            if str(getattr(obj, "V1ObjectType", "") or "") == "V1StationHighlight"
        )

        assert row is not None
        assert row["label"] == "STA 40.000"
        assert abs(float(marker.Station) - 40.0) <= 1.0e-9
        assert "Highlighted STA 40.000" in panel._status_label.text
    finally:
        profile_review_view.Gui = original_gui
        App.closeDocument(doc.Name)
