from freecad.Corridor_Road.ui import task_cross_section_viewer as cross_section_viewer_module
from freecad.Corridor_Road.v1.commands import cmd_view_sections


class _FakeControl:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def closeDialog(self) -> None:
        self._events.append("close")


class _FakeGui:
    def __init__(self, events: list[str]) -> None:
        self.Control = _FakeControl(events)


def test_cross_section_open_v1_preview_builds_context_before_close() -> None:
    events: list[str] = []
    panel = cross_section_viewer_module.CrossSectionViewerTaskPanel.__new__(
        cross_section_viewer_module.CrossSectionViewerTaskPanel
    )
    panel.doc = "DemoDoc"
    panel._current_section_set = lambda: "SectionSet001"
    panel._current_station_row = lambda: {"station": 25.0}
    panel._build_v1_preview_context = lambda: _record_event(
        events,
        "build",
        {"viewer_context": {"source_panel": "Cross Section Viewer"}},
    )

    original_gui = cross_section_viewer_module.Gui
    original_show = cmd_view_sections.show_v1_section_preview
    cross_section_viewer_module.Gui = _FakeGui(events)
    cmd_view_sections.show_v1_section_preview = lambda **kwargs: _record_show(
        events,
        kwargs,
        expected_document="DemoDoc",
        expected_key="preferred_section_set",
        expected_value="SectionSet001",
    )
    try:
        panel._open_v1_preview()
    finally:
        cross_section_viewer_module.Gui = original_gui
        cmd_view_sections.show_v1_section_preview = original_show

    assert events == ["build", "close", "show"]


def _record_event(events: list[str], name: str, payload: dict[str, object]) -> dict[str, object]:
    events.append(name)
    return payload


def _record_show(
    events: list[str],
    kwargs: dict[str, object],
    *,
    expected_document: object,
    expected_key: str,
    expected_value: object,
) -> dict[str, object]:
    assert kwargs["document"] == expected_document
    assert kwargs[expected_key] == expected_value
    assert kwargs["extra_context"]["viewer_context"]
    events.append("show")
    return {}
