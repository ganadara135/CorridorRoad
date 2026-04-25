from freecad.Corridor_Road.v1.commands.cmd_view_sections import (
    build_demo_section_preview,
    format_section_preview,
    show_v1_section_preview,
)
from freecad.Corridor_Road.v1.models.result import TINSurface
from freecad.Corridor_Road.v1.models.result.tin_surface import TINTriangle, TINVertex
from freecad.Corridor_Road.v1.models.output.section_output import (
    SectionGeometryRow,
    SectionOutput,
)
from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.ui.viewers.cross_section_viewer import (
    build_section_geometry_table_rows,
    build_handoff_status,
    build_handoff_target_rows,
    section_geometry_rows,
)


class _StateObject:
    def __init__(self, *, label: str = "", status: str = "", needs_recompute: bool = False) -> None:
        self.Label = label
        self.Status = status
        self.NeedsRecompute = needs_recompute


def _square_tin_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:section-viewer-square",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 0.0),
            TINVertex("v1", 10.0, 0.0, 10.0),
            TINVertex("v2", 10.0, 10.0, 20.0),
            TINVertex("v3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
            TINTriangle("t1", "v0", "v2", "v3"),
        ],
    )


def _east_alignment_model() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:section-east",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:section-east:tangent:1",
                kind="tangent",
                station_start=0.0,
                station_end=10.0,
                length=10.0,
                geometry_payload={
                    "x_values": [0.0, 10.0],
                    "y_values": [0.0, 0.0],
                },
            )
        ],
    )


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
    assert "Frame: x=1000.000, y=2000.000, z=12.000" in summary
    assert "Frame Profile: grade=0.020000, alignment=ok, profile=ok" in summary
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


def test_show_v1_section_preview_preserves_earthwork_handoff_rows() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "viewer_context": {
                "source_panel": "Earthwork Review",
                "earthwork_window_summary": "0.000 -> 20.000",
                "earthwork_cut_fill_summary": "100.000 / 40.000 m3; ratio=2.125",
                "haul_zone_summary": "surplus_haul_zone; value=45.000 m3",
            },
            "earthwork_hint_rows": [
                {
                    "kind": "earthwork_window",
                    "label": "Earthwork Window",
                    "value": "0.000 -> 20.000",
                    "notes": "Focused window from Earthwork Review.",
                }
            ],
        },
        app_module=None,
        gui_module=None,
    )

    assert preview["viewer_context"]["source_panel"] == "Earthwork Review"
    assert preview["viewer_context"]["earthwork_window_summary"] == "0.000 -> 20.000"
    assert preview["earthwork_hint_rows"][0]["value"] == "0.000 -> 20.000"


def test_show_v1_section_preview_adds_tin_terrain_sample_rows() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "tin_surface": _square_tin_surface(),
            "terrain_offsets": [0.0, 5.0],
            "station_offset_to_xy": lambda station, offset: (5.0, offset),
        },
        app_module=None,
        gui_module=None,
    )

    rows = preview["terrain_rows"]
    tin_rows = [row for row in rows if row["kind"] == "tin_section_sample"]

    assert any(row["kind"] == "tin_section_summary" for row in rows)
    assert len(tin_rows) == 2
    assert tin_rows[0]["value"] == "z=5.000"
    assert tin_rows[1]["value"] == "z=10.000"
    assert "face=" in tin_rows[0]["notes"]


def test_show_v1_section_preview_adds_tin_geometry_polyline_row() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "tin_surface": _square_tin_surface(),
            "terrain_offsets": [0.0, 5.0],
            "station_offset_to_xy": lambda station, offset: (5.0, offset),
        },
        app_module=None,
        gui_module=None,
    )

    geometry_rows = section_geometry_rows(preview)
    table_rows = build_section_geometry_table_rows(preview)

    assert len(geometry_rows) == 1
    assert geometry_rows[0].kind == "existing_ground_tin"
    assert geometry_rows[0].x_values == [0.0, 5.0]
    assert geometry_rows[0].y_values == [5.0, 10.0]
    assert geometry_rows[0].style_role == "existing_ground"
    assert table_rows[0][0] == "existing_ground_tin"
    assert table_rows[0][1] == "2"


def test_show_v1_section_preview_uses_alignment_adapter_for_tin_sampling() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "alignment_model": _east_alignment_model(),
            "tin_surface": _square_tin_surface(),
            "station_row": {"station": 5.0, "label": "STA 5.000"},
            "terrain_offsets": [0.0, 5.0],
        },
        app_module=None,
        gui_module=None,
    )

    geometry_rows = section_geometry_rows(preview)
    tin_rows = [row for row in preview["terrain_rows"] if row["kind"] == "tin_section_sample"]

    assert len(geometry_rows) == 1
    assert geometry_rows[0].x_values == [0.0, 5.0]
    assert geometry_rows[0].y_values == [5.0, 10.0]
    assert len(tin_rows) == 2
    assert tin_rows[0]["value"] == "z=5.000"


def test_show_v1_section_preview_breaks_tin_geometry_at_no_hit_rows() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "tin_surface": _square_tin_surface(),
            "terrain_offsets": [0.0, 2.5, 15.0, 5.0, 7.5],
            "station_offset_to_xy": lambda station, offset: (5.0, offset),
        },
        app_module=None,
        gui_module=None,
    )

    geometry_rows = section_geometry_rows(preview)

    assert len(geometry_rows) == 2
    assert geometry_rows[0].x_values == [0.0, 2.5]
    assert geometry_rows[1].x_values == [5.0, 7.5]


def test_show_v1_section_preview_adds_section_cut_fill_area_quantities() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "section_output": SectionOutput(
                schema_version=1,
                project_id="test-project",
                section_output_id="section:area-test",
                alignment_id="alignment:section-east",
                station=5.0,
                geometry_rows=[
                    SectionGeometryRow(
                        row_id="section:area-test:design",
                        kind="design_section",
                        x_values=[0.0, 5.0],
                        y_values=[8.0, 8.0],
                        z_values=[8.0, 8.0],
                        style_role="finished_grade",
                    )
                ],
            ),
            "tin_surface": _square_tin_surface(),
            "terrain_offsets": [0.0, 5.0],
            "station_offset_to_xy": lambda station, offset: (5.0, offset),
        },
        app_module=None,
        gui_module=None,
    )

    quantity_rows = list(preview["section_output"].quantity_rows)
    area_rows = [
        row
        for row in quantity_rows
        if row.component_ref == "section_earthwork_area"
    ]

    assert preview["section_earthwork_area_result"].status == "ok"
    assert [row.quantity_kind for row in area_rows] == ["cut_area", "fill_area"]
    assert [round(row.value, 6) for row in area_rows] == [2.0, 4.5]


def test_show_v1_section_preview_reports_missing_tin_station_adapter() -> None:
    preview = show_v1_section_preview(
        document=None,
        extra_context={
            "tin_surface": _square_tin_surface(),
            "terrain_offsets": [0.0],
        },
        app_module=None,
        gui_module=None,
    )

    rows = preview["terrain_rows"]
    adapter_rows = [row for row in rows if row["kind"] == "tin_section_adapter"]

    assert adapter_rows
    assert adapter_rows[0]["value"] == "missing"


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
