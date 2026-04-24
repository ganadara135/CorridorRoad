from freecad.Corridor_Road.v1.commands.cmd_view_sections import (
    build_demo_section_preview,
    format_section_preview,
    show_v1_section_preview,
)
from freecad.Corridor_Road.v1.ui.viewers.cross_section_viewer import (
    build_handoff_status,
    build_handoff_target_rows,
)


class _StateObject:
    def __init__(self, *, label: str = "", status: str = "", needs_recompute: bool = False) -> None:
        self.Label = label
        self.Status = status
        self.NeedsRecompute = needs_recompute


def test_build_demo_section_preview_returns_section_output() -> None:
    preview = build_demo_section_preview(document_label="Demo Doc")

    assert preview["applied_section"].label == "Demo Doc"
    assert preview["section_output"].section_output_id == "section:0"
    assert preview["section_output"].station == 0.0
    assert preview["result_state"]["state"] == "current"
    assert preview["source_inspector"]["component_count"] == 0
    assert preview["terrain_rows"][0]["label"] == "Terrain Source"
    assert preview["structure_rows"][0]["label"] == "Structure Summary"
    assert preview["earthwork_hint_rows"][0]["label"] == "Earthwork Window"
    assert preview["review_marker_rows"][0]["label"] == "Bookmark Slot"
    assert preview["diagnostic_rows"][0]["severity"] == "info"
    assert len(preview["key_station_rows"]) == 3
    assert preview["key_station_rows"][0]["is_current"] is True
    assert preview["source_inspector"]["ownership_status"] == "partial"
    assert "section_set" in preview["source_inspector"]["unresolved_fields"]


def test_format_section_preview_contains_key_summary_lines() -> None:
    summary = format_section_preview(build_demo_section_preview())

    assert "CorridorRoad v1 Cross Section Viewer" in summary
    assert "Result State: current" in summary
    assert "Station: 0.0" in summary
    assert "Station Label: STA 0.000" in summary
    assert "Quantities: 2" in summary
    assert "Earthwork" not in summary


def test_show_v1_section_preview_keeps_key_station_rows() -> None:
    preview = show_v1_section_preview(document=None, app_module=None, gui_module=None)

    assert len(preview["key_station_rows"]) == 3
    assert any(bool(row.get("is_current", False)) for row in preview["key_station_rows"])


def test_show_v1_section_preview_returns_preview_without_gui() -> None:
    preview = show_v1_section_preview(document=None, app_module=None, gui_module=None)

    assert preview["section_output"].section_output_id == "section:0"


def test_show_v1_section_preview_merges_extra_context() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "viewer_context": {
                "tag_summary": "Selected / Current",
                "focused_component": {
                    "key": "id:lane_left",
                    "id": "lane_left",
                    "label": "lane / left / typical [lane_left]",
                },
            }
        },
        app_module=None,
        gui_module=None,
    )

    assert preview["viewer_context"]["tag_summary"] == "Selected / Current"
    assert preview["viewer_context"]["focused_component"]["key"] == "id:lane_left"
    assert preview["source_inspector"]["component_id"] == "lane_left"
    assert "lane / left / typical [lane_left]" in preview["review_marker_rows"][0]["notes"]
    assert preview["diagnostic_rows"]


def test_show_v1_section_preview_resolves_source_inspector_owner_fields() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "legacy_objects": {
                "section_set": _StateObject(label="SectionSet A"),
                "typical_section": _StateObject(label="Typical Section A"),
                "region_plan": _StateObject(label="Region Plan A"),
                "structure_set": _StateObject(label="Structure Set A"),
            }
        },
        app_module=None,
        gui_module=None,
    )

    inspector = preview["source_inspector"]
    assert inspector["section_set_label"] == "SectionSet A"
    assert inspector["template_label"] == "Typical Section A"
    assert inspector["region_label"] == "Region Plan A"
    assert inspector["structure_label"] == "Structure Set A"
    assert inspector["owner_structure"] == "Structure Set A"
    assert inspector["ownership_status"] == "resolved"
    assert inspector["unresolved_fields"] == []


def test_show_v1_section_preview_marks_unresolved_ownership_fields() -> None:
    preview = show_v1_section_preview(document=None, app_module=None, gui_module=None)

    inspector = preview["source_inspector"]
    assert inspector["ownership_status"] in ("partial", "unresolved")
    assert "section_set" in inspector["unresolved_fields"]


def test_format_section_preview_includes_focus_component_line() -> None:
    summary = format_section_preview(
        show_v1_section_preview(
            document=None,
            extra_context={
                "viewer_context": {
                    "focused_component": {
                        "key": "id:lane_left",
                        "id": "lane_left",
                        "label": "lane / left / typical [lane_left]",
                    }
                }
            },
            app_module=None,
            gui_module=None,
        )
    )

    assert "Focus Component: lane / left / typical [lane_left]" in summary


def test_show_v1_section_preview_carries_result_state_reason() -> None:
    preview = show_v1_section_preview(document=None, app_module=None, gui_module=None)

    assert "reason" in preview["result_state"]
    assert preview["result_state"]["reason"]


def test_show_v1_section_preview_accepts_explicit_result_state_override() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "result_state": {
                "state": "stale",
                "reason": "Manual preview override for stale review.",
            }
        },
        app_module=None,
        gui_module=None,
    )

    assert preview["result_state"]["state"] == "stale"
    assert "stale review" in preview["result_state"]["reason"]


def test_format_section_preview_uses_overridden_result_state() -> None:
    summary = format_section_preview(
        show_v1_section_preview(
            document=None,
            extra_context={
                "result_state": {
                    "state": "stale",
                    "reason": "Manual preview override for stale review.",
                }
            },
            app_module=None,
            gui_module=None,
        )
    )

    assert "Result State: stale" in summary
    assert "State Reason: Manual preview override for stale review." in summary


def test_show_v1_section_preview_resolves_rebuild_needed_from_legacy_object() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "result_state": {},
            "legacy_objects": {
                "section_set": _StateObject(label="SectionSet Demo", needs_recompute=True),
            },
        },
        app_module=None,
        gui_module=None,
    )

    assert preview["result_state"]["state"] == "rebuild_needed"
    assert "SectionSet Demo" in preview["result_state"]["reason"]


def test_show_v1_section_preview_resolves_blocked_from_legacy_status() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "result_state": {},
            "legacy_objects": {
                "section_set": _StateObject(label="SectionSet Demo", status="ERROR: Missing section wires"),
            },
        },
        app_module=None,
        gui_module=None,
    )

    assert preview["result_state"]["state"] == "blocked"
    assert "ERROR" in preview["result_state"]["reason"]


def test_show_v1_section_preview_includes_earthwork_hint_rows() -> None:
    preview = show_v1_section_preview(document=None, app_module=None, gui_module=None)

    rows = preview["earthwork_hint_rows"]
    assert len(rows) >= 3
    assert rows[0]["label"] == "Earthwork Window"
    assert rows[1]["label"] == "Cut / Fill"
    assert rows[2]["label"] == "Earthwork State"


def test_show_v1_section_preview_includes_review_marker_rows() -> None:
    preview = show_v1_section_preview(document=None, app_module=None, gui_module=None)

    rows = preview["review_marker_rows"]
    assert len(rows) >= 2
    assert rows[0]["kind"] == "review_bookmark_placeholder"
    assert rows[0]["label"] == "Bookmark Slot"
    assert rows[1]["kind"] == "review_issue_placeholder"


def test_build_handoff_target_rows_marks_ready_targets() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "source": "existing_v0_cross_section_viewer",
            "legacy_objects": {
                "section_set": _StateObject(label="SectionSet A"),
                "typical_section": _StateObject(label="Typical Section A"),
                "region_plan": _StateObject(label="Region Plan A"),
                "structure_set": _StateObject(label="Structure Set A"),
            },
        },
        app_module=None,
        gui_module=None,
    )

    rows = build_handoff_target_rows(preview)

    assert rows[0][0] == "Typical Section"
    assert rows[0][1] == "ready"
    assert "Typical Section A" in rows[0][2]
    assert "STA 0.000" in rows[0][3]
    assert rows[2][0] == "Structures"
    assert rows[2][1] == "ready"
    assert "Structure Set A" in rows[2][2]


def test_build_handoff_status_reports_missing_targets() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "source": "existing_v0_cross_section_viewer",
        },
        app_module=None,
        gui_module=None,
    )

    status = build_handoff_status(preview)

    assert "Handoff Context: STA 0.000" in status["text"]
    assert "Source=existing_v0_cross_section_viewer" in status["text"]
    assert "Missing=" in status["text"]
    assert status["style"] == "color: #b36b00;"
