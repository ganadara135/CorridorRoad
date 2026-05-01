import FreeCAD as App
import Mesh
import os
import tempfile

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_profile_editor import (
    CmdV1ProfileEditor,
    V1ProfileEditorTaskPanel,
    apply_profile_control_rows,
    apply_profile_vertical_curve_rows,
    auto_interpolate_profile_elevation_rows,
    build_profile_sheet_preview,
    build_profile_preview_shape,
    build_profile_editor_handoff_context,
    create_blank_v1_profile,
    export_profile_control_rows_to_csv,
    generate_profile_vertical_curve_rows_from_controls,
    import_profile_control_rows_from_csv,
    profile_model_from_editor_rows,
    profile_eg_reference_lines,
    profile_eg_sample_rows,
    profile_control_rows,
    profile_preset_names,
    profile_preset_rows,
    profile_rows_from_stationing,
    profile_station_check_rows,
    profile_station_check_lines,
    profile_vertical_curve_rows,
    run_v1_profile_editor_command,
    show_profile_preview_object,
    _make_profile_polyline,
    _resolve_profile_preview_tin_surface,
)
from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import apply_alignment_ip_rows
from freecad.Corridor_Road.v1.commands.selection_context import selected_alignment_profile_target
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import (
    create_sample_v1_profile,
    find_v1_profile,
    to_profile_model,
)
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing

_QAPP = None


class _Selection:
    def __init__(self, objects):
        self._objects = list(objects or [])

    def getSelection(self):
        return list(self._objects)


class _Gui:
    def __init__(self, objects):
        self.Selection = _Selection(objects)


def _new_project_doc():
    doc = App.newDocument("CRV1ProfileEditorContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _add_existing_ground_mesh(doc):
    obj = doc.addObject("Mesh::Feature", "ExistingGroundTIN")
    mesh = Mesh.Mesh()
    p00 = App.Vector(-50.0, -50.0, 100.0)
    p10 = App.Vector(250.0, -50.0, 106.0)
    p11 = App.Vector(250.0, 120.0, 114.0)
    p01 = App.Vector(-50.0, 120.0, 108.0)
    mesh.addFacet(p00, p10, p11)
    mesh.addFacet(p00, p11, p01)
    obj.Mesh = mesh
    obj.Label = "Existing Ground TIN"
    return obj


def _small_tin_surface_for_profile_resolution():
    from freecad.Corridor_Road.v1.models.result.tin_surface import TINSurface, TINTriangle, TINVertex

    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:profile-resolution",
        label="Profile Resolution TIN",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 10.0),
            TINVertex("v1", 10.0, 0.0, 12.0),
            TINVertex("v2", 10.0, 10.0, 16.0),
            TINVertex("v3", 0.0, 10.0, 14.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
            TINTriangle("t1", "v0", "v2", "v3"),
        ],
    )


def test_apply_profile_control_rows_sorts_and_updates_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        rows = apply_profile_control_rows(
            profile,
            [
                {"station": 150.0, "elevation": 16.0, "kind": "grade_break"},
                {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                {"station": 75.0, "elevation": 14.5, "kind": "pvi"},
            ],
        )
        model = to_profile_model(profile)

        assert [row["station"] for row in rows] == [0.0, 75.0, 150.0]
        assert list(profile.ControlStations) == [0.0, 75.0, 150.0]
        assert list(profile.ControlElevations) == [12.0, 14.5, 16.0]
        assert model is not None
        assert [row.station for row in model.control_rows] == [0.0, 75.0, 150.0]
    finally:
        App.closeDocument(doc.Name)


def test_apply_profile_control_rows_rejects_duplicate_stations() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        try:
            apply_profile_control_rows(
                profile,
                [
                    {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                    {"station": 0.0, "elevation": 13.0, "kind": "pvi"},
                ],
            )
            assert False, "duplicate station should raise"
        except ValueError as exc:
            assert "Duplicate station" in str(exc)
    finally:
        App.closeDocument(doc.Name)


def test_auto_interpolate_profile_elevation_rows_fills_blank_elevations() -> None:
    rows = auto_interpolate_profile_elevation_rows(
        [
            {"station": 0.0, "elevation": 130.0, "kind": "grade_break"},
            {"station": 20.0, "elevation": None, "kind": "pvi"},
            {"station": 40.0, "elevation": "", "kind": "pvi"},
            {"station": 60.0, "elevation": 100.0, "kind": "grade_break"},
        ]
    )

    assert [row["station"] for row in rows] == [0.0, 20.0, 40.0, 60.0]
    assert [round(float(row["elevation"]), 3) for row in rows] == [130.0, 120.0, 110.0, 100.0]


def test_auto_interpolate_profile_elevation_rows_requires_bounded_controls() -> None:
    try:
        auto_interpolate_profile_elevation_rows(
            [
                {"station": 0.0, "elevation": 130.0, "kind": "grade_break"},
                {"station": 20.0, "elevation": None, "kind": "pvi"},
                {"station": 30.0, "elevation": 125.0, "kind": "pvi"},
                {"station": 40.0, "elevation": "", "kind": "grade_break"},
            ]
        )
        assert False, "unbounded auto interpolation should raise"
    except ValueError as exc:
        assert "first and last station" in str(exc)
        assert "First station: 0.000" in str(exc)
        assert "Last station: 40.000" in str(exc)


def test_profile_editor_uses_auto_interpolate_without_random_elevation_button() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)
        panel = V1ProfileEditorTaskPanel(profile=profile, document=doc, preferred_alignment=alignment)

        buttons = {button.text() for button in panel.form.findChildren(QtWidgets.QPushButton)}

        assert "Random Elevation" not in buttons
        assert "Auto Interpolate Elevations" in buttons
    finally:
        App.closeDocument(doc.Name)


def test_apply_profile_vertical_curve_rows_sorts_and_updates_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        rows = apply_profile_vertical_curve_rows(
            profile,
            [
                {
                    "kind": "parabolic_vertical_curve",
                    "station_start": 120.0,
                    "station_end": 150.0,
                    "length": 30.0,
                    "parameter": -0.02,
                },
                {
                    "kind": "parabolic_vertical_curve",
                    "station_start": 40.0,
                    "station_end": 70.0,
                    "length": 30.0,
                    "parameter": 0.03,
                },
            ],
        )

        assert [row["station_start"] for row in rows] == [40.0, 120.0]
        assert list(profile.VerticalCurveStationStarts) == [40.0, 120.0]
        assert list(profile.VerticalCurveStationEnds) == [70.0, 150.0]
        assert list(profile.VerticalCurveParameters) == [0.03, -0.02]
        assert len(profile_vertical_curve_rows(profile)) == 2
    finally:
        App.closeDocument(doc.Name)


def test_profile_vertical_curve_kind_labels_are_normalized_to_parabolic() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        rows = apply_profile_vertical_curve_rows(
            profile,
            [
                {
                    "kind": "Parabolic",
                    "station_start": 40.0,
                    "station_end": 70.0,
                    "length": 30.0,
                    "parameter": 0.0,
                }
            ],
        )

        assert rows[0]["kind"] == "parabolic_vertical_curve"
        assert list(profile.VerticalCurveKinds) == ["parabolic_vertical_curve"]
    finally:
        App.closeDocument(doc.Name)


def test_apply_profile_vertical_curve_rows_rejects_negative_length_window() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        try:
            apply_profile_vertical_curve_rows(
                profile,
                [
                    {
                        "station_start": 80.0,
                        "station_end": 70.0,
                        "length": 10.0,
                        "parameter": 0.0,
                    }
                ],
            )
            assert False, "end station before start station should raise"
        except ValueError as exc:
            assert "end station" in str(exc)
    finally:
        App.closeDocument(doc.Name)


def test_generate_profile_vertical_curve_rows_from_pvi_controls() -> None:
    rows = generate_profile_vertical_curve_rows_from_controls(
        [
            {"station": 0.0, "elevation": 10.0, "kind": "grade_break"},
            {"station": 50.0, "elevation": 15.0, "kind": "pvi"},
            {"station": 100.0, "elevation": 11.0, "kind": "pvi"},
            {"station": 140.0, "elevation": 13.0, "kind": "grade_break"},
        ],
        default_length=30.0,
    )

    assert len(rows) == 2
    assert rows[0]["station_start"] == 35.0
    assert rows[0]["station_end"] == 65.0
    assert rows[0]["length"] == 30.0
    assert rows[1]["station_start"] == 85.0
    assert rows[1]["station_end"] == 115.0
    assert rows[1]["length"] == 30.0
    assert rows[0]["parameter"] < 0.0
    assert rows[1]["parameter"] > 0.0


def test_generate_profile_vertical_curve_rows_clamps_short_tangents() -> None:
    rows = generate_profile_vertical_curve_rows_from_controls(
        [
            {"station": 0.0, "elevation": 10.0, "kind": "grade_break"},
            {"station": 20.0, "elevation": 13.0, "kind": "pvi"},
            {"station": 50.0, "elevation": 11.0, "kind": "grade_break"},
        ],
        default_length=50.0,
    )

    assert len(rows) == 1
    assert rows[0]["station_start"] == 11.0
    assert rows[0]["station_end"] == 29.0
    assert rows[0]["length"] == 18.0


def test_apply_profile_vertical_curve_rows_rejects_overlaps() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        try:
            apply_profile_vertical_curve_rows(
                profile,
                [
                    {"station_start": 40.0, "station_end": 80.0, "length": 40.0},
                    {"station_start": 70.0, "station_end": 100.0, "length": 30.0},
                ],
            )
            assert False, "overlapping vertical curves should raise"
        except ValueError as exc:
            assert "overlaps" in str(exc)
    finally:
        App.closeDocument(doc.Name)


def test_profile_editor_handoff_context_targets_selected_station() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        context = build_profile_editor_handoff_context(
            profile,
            selected_row={"station": 75.0, "elevation": 14.5, "kind": "pvi"},
        )

        assert context["source"] == "v1_profile_editor"
        assert context["preferred_profile_name"] == profile.Name
        assert context["preferred_station"] == 75.0
        assert context["viewer_context"]["source_panel"] == "v1 Profile Editor"
        assert context["viewer_context"]["focus_station_label"] == "STA 75.000"
        assert "FG 14.500" in context["viewer_context"]["selected_row_label"]
    finally:
        App.closeDocument(doc.Name)


def test_profile_editor_tab_helpers_report_curves_eg_and_station_check() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        curve_rows = profile_vertical_curve_rows(profile)
        check_lines = profile_station_check_lines(profile, alignment)
        eg_lines = profile_eg_reference_lines(doc, profile, alignment)

        assert curve_rows
        assert curve_rows[0]["kind"] == "parabolic_vertical_curve"
        assert any("Station check: ok" in line for line in check_lines)
        assert any("EG reference source" in line for line in eg_lines)
    finally:
        App.closeDocument(doc.Name)


def test_profile_station_check_rows_report_stationing_membership() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)

        rows = profile_station_check_rows(
            [
                {"station": 0.0, "kind": "grade_break"},
                {"station": 60.0, "kind": "pvi"},
                {"station": 180.0008, "kind": "grade_break"},
                {"station": 999.0, "kind": "pvi"},
            ],
            alignment,
            stationing,
        )

        assert rows[0]["status"] == "OK"
        assert rows[1]["in_stationing"] == "yes"
        assert rows[2]["in_alignment"] == "yes"
        assert rows[2]["in_stationing"] == "yes"
        assert rows[2]["status"] == "OK"
        assert rows[3]["status"] == "ERROR"
        assert "outside alignment range" in rows[3]["notes"]
    finally:
        App.closeDocument(doc.Name)


def test_profile_eg_sample_rows_use_selected_tin_mesh() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        surface = _add_existing_ground_mesh(doc)
        doc.recompute()

        rows, status = profile_eg_sample_rows(
            doc,
            alignment,
            [
                {"station": 0.0},
                {"station": 90.0},
                {"station": 180.0},
            ],
            interval=30.0,
            surface_obj=surface,
        )

        assert status in {"ok", "partial"}
        assert len(rows) >= 2
        assert any(row["elevation"] is not None for row in rows)
    finally:
        App.closeDocument(doc.Name)


def test_profile_eg_sample_rows_do_not_truncate_large_tin_preview_mesh() -> None:
    from freecad.Corridor_Road.v1.services.builders.tin_build_service import TINBuildService
    from freecad.Corridor_Road.v1.services.mapping.tin_mesh_preview_mapper import TINMeshPreviewMapper

    doc, project = _new_project_doc()
    try:
        surface = TINBuildService().build_from_csv(
            r"tests\samples\pointcloud_tin_mountain_valley_plain.csv",
            project_id="test-project",
            surface_id="tin:mountain-valley-plain",
        )
        result = TINMeshPreviewMapper().create_preview_object(doc, surface)
        tin_obj = doc.getObject(result.object_name)
        alignment = create_sample_v1_alignment(doc, project=project)
        apply_alignment_ip_rows(
            alignment,
            [
                {"x": 353305.0, "y": 4168370.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 353325.0, "y": 4168370.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 353345.0, "y": 4168370.226, "radius": 0.0, "transition_length": 0.0},
            ],
        )
        doc.recompute()

        rows, status = profile_eg_sample_rows(
            doc,
            alignment,
            [
                {"station": 0.0},
                {"station": 20.0},
                {"station": 40.0},
            ],
            interval=20.0,
            surface_obj=tin_obj,
        )

        assert status == "ok"
        assert rows
        assert all(row["status"] == "ok" for row in rows)
        assert all(row["elevation"] is not None for row in rows)
    finally:
        App.closeDocument(doc.Name)


def test_profile_model_from_editor_rows_builds_transient_preview_model() -> None:
    model = profile_model_from_editor_rows(
        [
            {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
            {"station": 50.0, "elevation": 15.0, "kind": "pvi"},
            {"station": 100.0, "elevation": 13.0, "kind": "grade_break"},
        ],
        [
            {
                "kind": "Parabolic",
                "station_start": 40.0,
                "station_end": 60.0,
                "length": 20.0,
                "parameter": -0.02,
            }
        ],
    )

    assert model.profile_id == "profile:show-preview"
    assert [row.station for row in model.control_rows] == [0.0, 50.0, 100.0]
    assert model.vertical_curve_rows[0].kind == "parabolic_vertical_curve"


def test_profile_preview_shape_uses_current_rows_and_alignment() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        doc.recompute()
        model = profile_model_from_editor_rows(
            [
                {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                {"station": 90.0, "elevation": 15.0, "kind": "pvi"},
                {"station": 180.0, "elevation": 13.5, "kind": "grade_break"},
            ],
        )

        shape, point_count = build_profile_preview_shape(model, alignment, sample_interval=30.0)

        assert point_count >= 2
        assert not shape.isNull()
    finally:
        App.closeDocument(doc.Name)


def test_profile_show_preview_builds_framed_sheet_objects_away_from_model() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        doc.recompute()
        model = profile_model_from_editor_rows(
            [
                {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                {"station": 90.0, "elevation": 15.0, "kind": "pvi"},
                {"station": 180.0, "elevation": 13.5, "kind": "grade_break"},
            ],
        )

        preview = build_profile_sheet_preview(model, alignment, document=doc, sample_interval=30.0)
        obj = show_profile_preview_object(doc, model, alignment, sample_interval=30.0)

        assert obj.Name == "FinishedGradeFG_ShowPreview"
        assert doc.getObject("FinishedGradeFG_ShowPreview_Frame") is not None
        assert doc.getObject("FinishedGradeFG_ShowPreview_Grid") is not None
        assert doc.getObject("FinishedGradeFG_ShowPreview_Title") is not None
        assert len(doc.getObject("FinishedGradeFG_ShowPreview_Frame").Shape.Faces) > 0
        assert len(obj.Shape.Faces) > 0
        assert int(obj.DisplayPointCount) >= 2
        assert round(preview["origin"][0] + 0.5 * preview["plot_width"], 6) == 90.0
        assert preview["origin"][2] > 0.0
        assert preview["plot_height"] > 0.0
    finally:
        App.closeDocument(doc.Name)


def test_profile_show_wire_uses_spline_for_unstroked_profile_line() -> None:
    points = [
        App.Vector(0.0, 0.0, 0.0),
        App.Vector(20.0, 0.0, 5.0),
        App.Vector(40.0, 0.0, 2.0),
        App.Vector(60.0, 0.0, 8.0),
    ]

    shape = _make_profile_polyline(points, stroke_width=0.0)

    assert shape is not None
    assert len(shape.Edges) == 1
    assert "BSpline" in type(shape.Edges[0].Curve).__name__


def test_profile_show_preview_uses_document_mesh_for_existing_ground() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        _add_existing_ground_mesh(doc)
        doc.recompute()
        model = profile_model_from_editor_rows(
            [
                {"station": 0.0, "elevation": 101.0, "kind": "grade_break"},
                {"station": 90.0, "elevation": 104.0, "kind": "pvi"},
                {"station": 180.0, "elevation": 103.0, "kind": "grade_break"},
            ],
        )

        preview = build_profile_sheet_preview(model, alignment, document=doc, sample_interval=30.0)
        obj = show_profile_preview_object(doc, model, alignment, sample_interval=30.0)
        eg_obj = doc.getObject("FinishedGradeFG_ShowPreview_EG")

        assert preview["eg_point_count"] >= 2
        assert int(obj.ExistingGroundPointCount) >= 2
        assert eg_obj is not None
        assert not eg_obj.Shape.isNull()
        assert len(eg_obj.Shape.Faces) > 0
    finally:
        App.closeDocument(doc.Name)


def test_profile_tin_resolution_prefers_edited_preview_when_available() -> None:
    from freecad.Corridor_Road.v1.models.source import TINEditOperation
    from freecad.Corridor_Road.v1.services.editing import TINEditService
    from freecad.Corridor_Road.v1.services.mapping import TINMeshPreviewMapper

    doc, _project = _new_project_doc()
    try:
        base_surface = _small_tin_surface_for_profile_resolution()
        edited_surface = TINEditService().apply_operations(
            base_surface,
            [
                TINEditOperation(
                    "op:delete",
                    "delete_triangles",
                    parameters={"triangle_ids": ["t1"]},
                )
            ],
        ).surface
        mapper = TINMeshPreviewMapper()
        mapper.create_or_update_preview_object(doc, base_surface, object_name="TINPreview_Profile_Base")
        mapper.create_or_update_preview_object(
            doc,
            edited_surface,
            object_name="TINPreview_Profile_Edited",
            surface_role="edited",
        )

        resolved = _resolve_profile_preview_tin_surface(doc)

        assert resolved is not None
        assert resolved.surface_id == edited_surface.surface_id
    finally:
        App.closeDocument(doc.Name)


def test_selection_context_resolves_v1_profile_selection() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        preferred_alignment, preferred_profile = selected_alignment_profile_target(
            _Gui([profile]),
            doc,
        )

        assert preferred_alignment is None
        assert preferred_profile == profile
        assert len(profile_control_rows(profile)) == 3
    finally:
        App.closeDocument(doc.Name)


def test_profile_command_does_not_create_sample_profile_on_open() -> None:
    doc, _project = _new_project_doc()
    try:
        result = run_v1_profile_editor_command()

        assert result is None
        assert find_v1_profile(doc) is None
    finally:
        App.closeDocument(doc.Name)


def test_profile_starter_rows_use_generated_stationing_instead_of_sample_rows() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)

        rows = profile_rows_from_stationing(stationing)

        assert [row["station"] for row in rows] == list(stationing.StationValues)
        assert [row["elevation"] for row in rows] == [None for _row in rows]
        assert rows[0]["kind"] == "grade_break"
        assert rows[-1]["kind"] == "grade_break"
        assert rows[1]["kind"] == "pvi"
    finally:
        App.closeDocument(doc.Name)


def test_auto_from_pvi_requires_elevations_after_stationing_prefill() -> None:
    rows = [
        {"station": 0.0, "elevation": None, "kind": "grade_break"},
        {"station": 60.0, "elevation": None, "kind": "pvi"},
        {"station": 120.0, "elevation": None, "kind": "grade_break"},
    ]

    try:
        generate_profile_vertical_curve_rows_from_controls(rows, default_length=30.0)
        assert False, "missing elevations should raise before auto curve generation"
    except ValueError as exc:
        assert "elevation" in str(exc)


def test_profile_command_menu_text_is_simplified() -> None:
    resources = CmdV1ProfileEditor().GetResources()

    assert resources["MenuText"] == "Profile"
    assert "profile" in resources["ToolTip"].lower()


def test_profile_preset_data_returns_copy_of_control_rows() -> None:
    names = profile_preset_names()

    assert "Starter Road" in names
    rows = profile_preset_rows("Starter Road")
    rows[0]["station"] = 999.0

    assert profile_preset_rows("Starter Road")[0]["station"] == 0.0


def test_profile_csv_import_accepts_v0_style_fg_headers() -> None:
    fd, path = tempfile.mkstemp(prefix="cr_v1_profile_", suffix=".csv")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write("STA,FG,Kind\n")
            handle.write("80,14.5,pvi\n")
            handle.write("0,12.0,grade_break\n")

        rows = import_profile_control_rows_from_csv(path)

        assert [row["station"] for row in rows] == [0.0, 80.0]
        assert [row["elevation"] for row in rows] == [12.0, 14.5]
        assert rows[0]["kind"] == "grade_break"
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def test_profile_csv_export_round_trips_control_rows() -> None:
    fd, path = tempfile.mkstemp(prefix="cr_v1_profile_export_", suffix=".csv")
    os.close(fd)
    try:
        count = export_profile_control_rows_to_csv(
            path,
            [
                {"station": 50.0, "elevation": 14.0, "kind": "pvi"},
                {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
            ],
        )
        rows = import_profile_control_rows_from_csv(path)

        assert count == 2
        assert [row["station"] for row in rows] == [0.0, 50.0]
        assert [row["elevation"] for row in rows] == [12.0, 14.0]
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def test_profile_csv_import_reads_repository_samples() -> None:
    rolling_path = os.path.join("tests", "samples", "profile_v1_pvi_rolling.csv")
    terrain_path = os.path.join("tests", "samples", "profile_v1_pvi_mountain_valley_plain.csv")

    rolling_rows = import_profile_control_rows_from_csv(rolling_path)
    terrain_rows = import_profile_control_rows_from_csv(terrain_path)

    assert len(rolling_rows) == 10
    assert rolling_rows[0]["station"] == 0.0
    assert rolling_rows[-1]["kind"] == "grade_break"
    assert len(terrain_rows) == 9
    assert terrain_rows[0]["elevation"] == 142.0
    assert terrain_rows[-1]["station"] == 460.0


def test_blank_profile_can_be_created_and_applied_from_rows() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_blank_v1_profile(document=doc, project=project, alignment=alignment)
        rows = apply_profile_control_rows(
            profile,
            [
                {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                {"station": 120.0, "elevation": 13.5, "kind": "grade_break"},
            ],
        )

        assert find_v1_profile(doc) == profile
        assert profile.AlignmentId == alignment.AlignmentId
        assert len(rows) == 2
        assert list(profile.ControlStations) == [0.0, 120.0]
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile editor contract tests completed.")
