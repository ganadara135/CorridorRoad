from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
    build_demo_plan_profile_preview,
    format_plan_profile_preview,
    resolve_station_interval,
    show_v1_plan_profile_preview,
)
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
