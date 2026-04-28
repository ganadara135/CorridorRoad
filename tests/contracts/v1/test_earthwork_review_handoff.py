from freecad.Corridor_Road.v1.commands.cmd_earthwork_balance import build_demo_earthwork_report
from freecad.Corridor_Road.v1.ui.common import clear_ui_context, get_ui_context
from freecad.Corridor_Road.v1.ui.viewers import earthwork_review_view
from freecad.Corridor_Road.v1.ui.viewers.earthwork_review_view import (
    EarthworkViewerTaskPanel,
    build_plan_profile_handoff_context,
    build_section_handoff_context,
)


class _FakeControl:
    def __init__(self) -> None:
        self.closed = False

    def closeDialog(self) -> None:
        self.closed = True


class _FakeGui:
    def __init__(self) -> None:
        self.Control = _FakeControl()
        self.ran = []

    def runCommand(self, command_name: str, arg: int) -> None:
        self.ran.append((command_name, arg))


class _FakeStatusLabel:
    def __init__(self) -> None:
        self.text = ""
        self.style = ""

    def setText(self, text: str) -> None:
        self.text = text

    def setStyleSheet(self, style: str) -> None:
        self.style = style


def test_build_section_handoff_context_targets_selected_earthwork_window() -> None:
    report = build_demo_earthwork_report(preferred_station=0.0)

    context = build_section_handoff_context(
        report,
        station_row={"station": 20.0, "label": "STA 20.000"},
    )

    assert context["source"] == "v1_earthwork_to_section"
    assert context["preferred_station"] == 20.0
    assert context["station_row"]["label"] == "STA 20.000"
    assert context["viewer_context"]["source_panel"] == "Earthwork Review"
    assert context["viewer_context"]["earthwork_window_summary"] == "0.000 -> 20.000"
    assert context["viewer_context"]["earthwork_cut_fill_summary"].startswith("100.000 / 40.000 m3")
    assert context["earthwork_hint_rows"][0]["label"] == "Earthwork Window"
    assert context["earthwork_hint_rows"][1]["label"] == "Cut / Fill"


def test_build_plan_profile_handoff_context_targets_selected_earthwork_window() -> None:
    report = build_demo_earthwork_report(preferred_station=0.0)

    context = build_plan_profile_handoff_context(
        report,
        station_row={"station": 20.0, "label": "STA 20.000"},
    )

    assert context["source"] == "v1_earthwork_to_plan_profile"
    assert context["preferred_station"] == 20.0
    assert context["station_row"]["label"] == "STA 20.000"
    assert context["viewer_context"]["source_panel"] == "Earthwork Review"
    assert context["viewer_context"]["focus_station"] == 20.0
    assert context["viewer_context"]["focus_station_label"] == "STA 20.000"
    assert context["viewer_context"]["earthwork_window_summary"] == "0.000 -> 20.000"
    assert context["viewer_context"]["earthwork_cut_fill_summary"].startswith("100.000 / 40.000 m3")


def test_earthwork_viewer_opens_cross_section_with_context() -> None:
    clear_ui_context()
    fake_gui = _FakeGui()
    original_gui = earthwork_review_view.Gui
    earthwork_review_view.Gui = fake_gui
    panel = EarthworkViewerTaskPanel.__new__(EarthworkViewerTaskPanel)
    panel.report = build_demo_earthwork_report(preferred_station=0.0)
    panel._status_label = _FakeStatusLabel()

    try:
        panel._open_cross_section_row({"station": 20.0, "label": "STA 20.000"})
    finally:
        earthwork_review_view.Gui = original_gui

    context = get_ui_context()
    assert fake_gui.Control.closed is True
    assert fake_gui.ran == [("CorridorRoad_V1ViewSections", 0)]
    assert context["source"] == "v1_earthwork_to_section"
    assert context["preferred_station"] == 20.0
    assert context["earthwork_hint_rows"]
    assert "Cross Section Viewer" in panel._status_label.text


def test_earthwork_viewer_opens_plan_profile_with_context() -> None:
    clear_ui_context()
    fake_gui = _FakeGui()
    original_gui = earthwork_review_view.Gui
    earthwork_review_view.Gui = fake_gui
    panel = EarthworkViewerTaskPanel.__new__(EarthworkViewerTaskPanel)
    panel.report = build_demo_earthwork_report(preferred_station=0.0)
    panel._status_label = _FakeStatusLabel()

    try:
        panel._open_plan_profile_row({"station": 20.0, "label": "STA 20.000"})
    finally:
        earthwork_review_view.Gui = original_gui

    context = get_ui_context()
    assert fake_gui.Control.closed is True
    assert fake_gui.ran == [("CorridorRoad_V1ReviewPlanProfile", 0)]
    assert context["source"] == "v1_earthwork_to_plan_profile"
    assert context["preferred_station"] == 20.0
    assert context["viewer_context"]["earthwork_window_summary"] == "0.000 -> 20.000"
    assert "Plan/Profile Connection Review" in panel._status_label.text


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 earthwork review handoff contract tests completed.")
