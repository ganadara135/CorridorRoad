import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
    build_demo_plan_profile_preview,
    format_plan_profile_preview,
    resolve_station_interval,
    show_v1_plan_profile_preview,
)
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.ui.common import clear_ui_context, get_ui_context
from freecad.Corridor_Road.v1.ui.viewers import profile_review_view
from freecad.Corridor_Road.v1.ui.viewers.profile_review_view import PlanProfileViewerTaskPanel
from freecad.Corridor_Road.v1.models.result import TINSurface
from freecad.Corridor_Road.v1.models.result.tin_surface import TINTriangle, TINVertex


def _demo_tin_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:profile-review-eg",
        vertex_rows=[
            TINVertex("v0", 1000.0, 2000.0, 100.0),
            TINVertex("v1", 1080.0, 2000.0, 108.0),
            TINVertex("v2", 1080.0, 2040.0, 112.0),
            TINVertex("v3", 1000.0, 2040.0, 104.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
            TINTriangle("t1", "v0", "v2", "v3"),
        ],
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


class _DeletingStatusLabel:
    def __init__(self, control: _FakeControl) -> None:
        self.control = control
        self.text = ""

    def setText(self, text: str) -> None:
        if self.control.closed:
            raise RuntimeError("Internal C++ object already deleted")
        self.text = str(text)

    def setStyleSheet(self, _style: str) -> None:
        if self.control.closed:
            raise RuntimeError("Internal C++ object already deleted")


def test_build_demo_plan_profile_preview_returns_outputs() -> None:
    preview = build_demo_plan_profile_preview("Demo Corridor")

    assert preview["alignment_model"].label == "Demo Corridor"
    assert preview["plan_output"].plan_output_id == "alignment:v1-demo"
    assert preview["profile_output"].profile_output_id == "profile:v1-demo"
    assert len(preview["plan_output"].geometry_rows) == 2
    assert len(preview["profile_output"].pvi_rows) == 3
    assert len(preview["plan_output"].station_rows) == 5
    assert len(preview["key_station_rows"]) == 4
    assert preview["key_station_rows"][0]["is_current"] is True
    assert preview["key_station_rows"][0]["alignment_eval_status"] == "ok"
    assert preview["key_station_rows"][0]["x"] == 1000.0
    assert preview["key_station_rows"][0]["y"] == 2000.0
    assert preview["key_station_rows"][0]["profile_eval_status"] == "ok"
    assert preview["key_station_rows"][0]["profile_elevation"] == 12.0
    assert "profile_grade" in preview["key_station_rows"][0]
    assert preview["key_station_rows"][0]["navigation_reason"] == "Current review focus station"
    assert preview["preview_source_kind"] == "demo"
    assert any(
        row["kind"] == "alignment_profile_link" and row["status"] == "ok"
        for row in preview["bridge_diagnostic_rows"]
    )


def test_format_plan_profile_preview_includes_key_counts() -> None:
    preview = build_demo_plan_profile_preview("Demo Corridor")

    text = format_plan_profile_preview(preview)

    assert "CorridorRoad v1 Plan/Profile Viewer" in text
    assert "Alignment elements: 2" in text
    assert "Profile controls: 3" in text
    assert "Evaluated alignment stations: 4" in text
    assert "Evaluated profile stations: 4" in text
    assert "Preview source: demo" in text
    assert "Bridge diagnostics:" in text


def test_show_v1_plan_profile_preview_returns_preview_without_gui() -> None:
    preview = show_v1_plan_profile_preview(document=None, app_module=None, gui_module=None)

    assert preview["plan_output"] is not None
    assert preview["profile_output"] is not None
    assert len(preview["key_station_rows"]) == 4
    assert preview["preview_source_kind"] == "demo"
    assert preview["bridge_diagnostic_rows"]


def test_show_v1_plan_profile_preview_accepts_station_interval() -> None:
    preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={"station_interval": 10.0},
        app_module=None,
        gui_module=None,
    )

    assert preview["station_interval"] == 10.0
    assert preview["viewer_context"]["station_interval"] == 10.0
    assert preview["plan_output"].station_rows[1].station == 10.0
    assert preview["key_station_rows"][1]["station"] == 10.0
    assert "Station interval: 10.000 m" in format_plan_profile_preview(preview)


def test_resolve_station_interval_accepts_viewer_context() -> None:
    interval = resolve_station_interval(
        {
            "viewer_context": {
                "station_interval": "12.5",
            }
        }
    )

    assert interval == 12.5


def test_show_v1_plan_profile_preview_adds_tin_existing_ground_line() -> None:
    preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={
            "tin_surface": _demo_tin_surface(),
        },
        app_module=None,
        gui_module=None,
    )

    eg_rows = [
        row
        for row in preview["profile_output"].line_rows
        if row.kind == "existing_ground_line"
    ]

    assert eg_rows
    assert eg_rows[0].style_role == "existing_ground"
    assert eg_rows[0].source_ref == "tin:profile-review-eg"
    assert len(eg_rows[0].station_values) >= 2
    assert preview["profile_tin_sample_result"].hit_count >= 2


def test_show_v1_plan_profile_preview_adds_profile_earthwork_hints() -> None:
    preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={
            "tin_surface": _demo_tin_surface(),
        },
        app_module=None,
        gui_module=None,
    )

    hint_rows = [
        row
        for row in preview["profile_output"].earthwork_rows
        if row.kind.startswith("profile_")
    ]

    assert hint_rows
    assert preview["profile_earthwork_hint_result"].status == "ok"
    assert all(row.unit == "m" for row in hint_rows)
    assert any(row.kind == "profile_cut_depth" for row in hint_rows)


def test_show_v1_plan_profile_preview_adds_profile_earthwork_area_hints() -> None:
    preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={
            "tin_surface": _demo_tin_surface(),
            "earthwork_area_width": 12.0,
        },
        app_module=None,
        gui_module=None,
    )

    area_rows = [
        row
        for row in preview["profile_output"].earthwork_rows
        if row.kind in {"profile_cut_area", "profile_fill_area", "profile_balanced_area"}
    ]

    assert area_rows
    assert preview["profile_earthwork_area_hint_result"].status == "ok"
    assert all(row.unit == "m2" for row in area_rows)
    assert any(row.kind == "profile_cut_area" for row in area_rows)


def test_show_v1_plan_profile_preview_accepts_area_width_from_viewer_context() -> None:
    preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={
            "tin_surface": _demo_tin_surface(),
            "viewer_context": {
                "source_panel": "Plan/Profile Viewer",
                "earthwork_area_width": 14.0,
            },
        },
        app_module=None,
        gui_module=None,
    )

    area_rows = [
        row
        for row in preview["profile_output"].earthwork_rows
        if row.kind in {"profile_cut_area", "profile_fill_area", "profile_balanced_area"}
    ]

    assert area_rows
    assert preview["profile_earthwork_area_hint_result"].status == "ok"
    assert all(row.unit == "m2" for row in area_rows)
    summary = format_plan_profile_preview(preview)
    assert "Earthwork area width: 14.000 m" in summary
    assert "Earthwork area status: ok" in summary


def test_plan_profile_viewer_hides_earthwork_section_without_earthwork_context() -> None:
    panel = PlanProfileViewerTaskPanel.__new__(PlanProfileViewerTaskPanel)
    panel.preview = build_demo_plan_profile_preview("Demo Corridor")

    assert panel._should_show_earthwork_section() is False
    assert panel._bridge_diagnostic_rows(issues_only=True)
    assert panel._review_readiness_rows() == []


def test_plan_profile_viewer_reports_missing_review_readiness_inputs() -> None:
    panel = PlanProfileViewerTaskPanel.__new__(PlanProfileViewerTaskPanel)
    panel.preview = {
        "preview_source_kind": "empty",
        "alignment_model": None,
        "profile_model": None,
        "plan_output": None,
        "profile_output": None,
        "key_station_rows": [],
    }

    rows = panel._review_readiness_rows()

    assert ["Alignment", "missing", "Open Alignment Editor and create or import the v1 alignment source."] in rows
    assert ["Stations", "missing", "Open Stations and apply station sampling for the active alignment."] in rows
    assert ["Profile", "missing", "Open Profile and create or import the v1 profile source."] in rows


def test_plan_profile_viewer_uses_tabs_for_review_detail_sections() -> None:
    panel = PlanProfileViewerTaskPanel(build_demo_plan_profile_preview("Demo Corridor"))

    tabs = panel.form.findChildren(QtWidgets.QTabWidget)
    labels = [tabs[0].tabText(index) for index in range(tabs[0].count())]

    assert labels == ["Evaluation", "Geometry", "Profile Controls"]


def test_plan_profile_navigation_station_labels_explain_selection_reason() -> None:
    panel = PlanProfileViewerTaskPanel(build_demo_plan_profile_preview("Demo Corridor"))

    label = panel._key_station_combo.itemText(0)
    buttons = {button.text() for button in panel.form.findChildren(QtWidgets.QPushButton)}
    labels = [label.text() for label in panel.form.findChildren(QtWidgets.QLabel)]

    assert "Current review focus station" in label
    assert {"Focus Previous", "Focus Selected", "Focus Next"}.issubset(buttons)
    assert any("Focus buttons reopen this review" in text for text in labels)
    assert any("Double-click an Alignment Frame or Profile Evaluation row" in text for text in labels)
    assert any("Double-click a Profile Control row" in text for text in labels)
    assert any("Double-click a Plan Geometry or Profile Lines row" in text for text in labels)


def test_plan_profile_focus_next_reopens_without_touching_deleted_status_label() -> None:
    clear_ui_context()
    fake_gui = _FakeGui()
    original_gui = profile_review_view.Gui
    profile_review_view.Gui = fake_gui
    panel = PlanProfileViewerTaskPanel(build_demo_plan_profile_preview("Demo Corridor"))
    try:
        panel._open_adjacent_station(1)
    finally:
        profile_review_view.Gui = original_gui

    context = get_ui_context()
    assert fake_gui.Control.closed is True
    assert fake_gui.ran == [("CorridorRoad_V1ReviewPlanProfile", 0)]
    assert context["source"] == "v1_plan_profile_navigation"
    assert context["preferred_station"] == 20.0


def test_plan_profile_open_alignment_editor_does_not_touch_deleted_status_label() -> None:
    clear_ui_context()
    fake_gui = _FakeGui()
    original_gui = profile_review_view.Gui
    profile_review_view.Gui = fake_gui
    panel = PlanProfileViewerTaskPanel.__new__(PlanProfileViewerTaskPanel)
    panel.preview = build_demo_plan_profile_preview("Demo Corridor")
    panel._status_label = _DeletingStatusLabel(fake_gui.Control)
    try:
        panel._open_legacy_command("CorridorRoad_V1EditAlignment")
    finally:
        profile_review_view.Gui = original_gui

    context = get_ui_context()
    assert fake_gui.Control.closed is True
    assert fake_gui.ran == [("CorridorRoad_V1EditAlignment", 0)]
    assert context["source"] == "v1_plan_profile_viewer"


def test_plan_profile_viewer_highlights_station_from_evaluation_row() -> None:
    doc = App.newDocument("PlanProfileStationHighlightTest")
    panel = PlanProfileViewerTaskPanel(build_demo_plan_profile_preview("Demo Corridor"))
    try:
        row = panel._station_highlight_row(40.0)
        panel._status_label.setText("")

        panel._highlight_station_value(40.0)
        markers = [
            obj
            for obj in list(doc.Objects)
            if str(getattr(obj, "V1ObjectType", "") or "") == "V1StationHighlight"
        ]

        assert row is not None
        assert row["label"] == "STA 40.000"
        assert markers
        assert abs(float(markers[0].Station) - 40.0) < 1.0e-9
    finally:
        App.closeDocument(doc.Name)


def test_plan_profile_geometry_range_start_station_parser() -> None:
    panel = PlanProfileViewerTaskPanel(build_demo_plan_profile_preview("Demo Corridor"))

    plan_station = panel._range_start_station_from_table_row(panel._plan_geometry_table, 0, 1)
    profile_station = panel._range_start_station_from_table_row(panel._profile_lines_table, 0, 2)

    assert plan_station == 0.0
    assert profile_station == 0.0


def test_plan_profile_viewer_shows_earthwork_section_for_handoff_context() -> None:
    panel = PlanProfileViewerTaskPanel.__new__(PlanProfileViewerTaskPanel)
    panel.preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={
            "viewer_context": {
                "source_panel": "Earthwork Review",
                "earthwork_area_width": 14.0,
            },
        },
        app_module=None,
        gui_module=None,
    )

    assert panel._should_show_earthwork_section() is True


def test_show_v1_plan_profile_preview_merges_extra_context() -> None:
    preview = show_v1_plan_profile_preview(
        document=None,
        extra_context={
            "viewer_context": {
                "source_panel": "Edit Profiles",
                "focus_station": 40.0,
                "focus_station_label": "STA 40.000 m",
                "selected_row_label": "Row 2 | STA 40.000 | FG 13.500",
            }
        },
        app_module=None,
        gui_module=None,
    )

    assert preview["viewer_context"]["source_panel"] == "Edit Profiles"
    assert preview["viewer_context"]["focus_station"] == 40.0


def test_format_plan_profile_preview_includes_context_lines() -> None:
    text = format_plan_profile_preview(
        show_v1_plan_profile_preview(
            document=None,
            extra_context={
                "viewer_context": {
                    "source_panel": "Edit Profiles",
                    "focus_station_label": "STA 40.000 m",
                    "selected_row_label": "Row 2 | STA 40.000 | FG 13.500",
                }
            },
            app_module=None,
            gui_module=None,
        )
    )

    assert "Context Source: Edit Profiles" in text
    assert "Focus Station: STA 40.000 m" in text
    assert "Selected Row: Row 2 | STA 40.000 | FG 13.500" in text
