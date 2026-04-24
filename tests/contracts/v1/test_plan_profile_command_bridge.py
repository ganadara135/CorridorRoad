from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
    build_demo_plan_profile_preview,
    format_plan_profile_preview,
    show_v1_plan_profile_preview,
)


def test_build_demo_plan_profile_preview_returns_outputs() -> None:
    preview = build_demo_plan_profile_preview("Demo Corridor")

    assert preview["alignment_model"].label == "Demo Corridor"
    assert preview["plan_output"].plan_output_id == "alignment:v1-demo"
    assert preview["profile_output"].profile_output_id == "profile:v1-demo"
    assert len(preview["plan_output"].geometry_rows) == 2
    assert len(preview["profile_output"].pvi_rows) == 3
    assert len(preview["key_station_rows"]) == 3
    assert preview["key_station_rows"][0]["is_current"] is True


def test_format_plan_profile_preview_includes_key_counts() -> None:
    preview = build_demo_plan_profile_preview("Demo Corridor")

    text = format_plan_profile_preview(preview)

    assert "CorridorRoad v1 Plan/Profile Viewer" in text
    assert "Alignment elements: 2" in text
    assert "Profile controls: 3" in text


def test_show_v1_plan_profile_preview_returns_preview_without_gui() -> None:
    preview = show_v1_plan_profile_preview(document=None, app_module=None, gui_module=None)

    assert preview["plan_output"] is not None
    assert preview["profile_output"] is not None
    assert len(preview["key_station_rows"]) == 3


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
