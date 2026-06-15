import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import V1_TREE_APPLIED_SECTIONS, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
import freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections as applied_sections_command
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    CmdV1AppliedSections,
    V1AppliedSectionsTaskPanel,
    applied_section_review_row_color,
    applied_section_review_rows,
    apply_v1_applied_section_set,
    build_document_applied_section_set,
    show_all_applied_sections_preview_object,
    show_applied_section_preview_object,
)
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionControlArea,
    IntersectionCurbReturnPolicyRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.commands.cmd_region_editor import starter_region_model_from_document
from freecad.Corridor_Road.v1.models.source.drainage_model import DrainageElementRow, DrainageModel
from freecad.Corridor_Road.v1.models.source.superelevation_model import CrossfallControlRow, RunoffTransitionRow, SuperelevationModel
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_subassembly_assembly import create_or_update_v1_assembly_subassembly_model_object
from freecad.Corridor_Road.v1.objects.obj_applied_section import (
    build_v1_applied_section_set_review_shape,
    find_v1_applied_section_set,
)
from freecad.Corridor_Road.v1.objects.obj_drainage import create_or_update_v1_drainage_model_object
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_region import create_or_update_v1_region_model_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_superelevation import create_or_update_v1_superelevation_source_object

_QAPP = None


def _new_project_doc():
    doc = App.newDocument("V1AppliedSectionsCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def test_build_document_applied_section_set_uses_v1_sources() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        result = build_document_applied_section_set(doc, project=project)

        assert len(result.station_rows) == 5
        assert result.sections[0].assembly_id == "assembly:basic-road"
        assert result.sections[0].template_id == "template:basic-road"
        assert result.sections[0].region_id == "region:normal-01"
    finally:
        App.closeDocument(doc.Name)


def test_build_document_applied_section_set_uses_superelevation_source() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        create_or_update_v1_superelevation_source_object(
            document=doc,
            project=project,
            superelevation_model=SuperelevationModel(
                schema_version=1,
                project_id="proj-1",
                superelevation_id="superelevation:main",
                alignment_id=str(alignment.AlignmentId),
                control_rows=[
                    CrossfallControlRow("control:normal", 0.0, "both", -2.0),
                    CrossfallControlRow("control:right-full", 60.0, "right", 4.0),
                ],
                transition_rows=[RunoffTransitionRow("transition:runoff", 0.0, 60.0, "runoff")],
            ),
        )

        result = build_document_applied_section_set(doc, project=project)
        section = next(section for section in result.sections if round(section.station, 3) == 60.0)
        right_rows = [row for row in section.subassembly_rows if row.kind in {"lane", "shoulder"} and row.side == "right"]
        review_rows = applied_section_review_rows(result)
        review_row = next(row for row in review_rows if round(float(row["station"]), 3) == 60.0)

        assert section.active_superelevation_id == "superelevation:main"
        assert section.active_superelevation_transition_id == "transition:runoff"
        assert round(section.superelevation_right_crossfall, 6) == 4.0
        assert right_rows
        assert {round(row.slope, 6) for row in right_rows} == {0.04}
        assert review_row["superelevation_summary"] == "L -2.000% | R 4.000% | runoff"
        assert "superelevation:main" in result.source_refs
    finally:
        App.closeDocument(doc.Name)


def test_assembly_preset_apply_syncs_region_refs_for_benched_build() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        apply_v1_assembly_subassembly_model(
            document=doc,
            project=project,
            assembly_model=assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
        )
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        apply_v1_assembly_subassembly_model(
            document=doc,
            project=project,
            assembly_model=assembly_subassembly_preset_model_from_document("Benched Slope Road", doc, project=project, alignment=alignment),
        )

        result = build_document_applied_section_set(doc, project=project)

        assert result.sections
        assert result.sections[0].assembly_id == "assembly:benched-slope-road"
        assert result.sections[0].template_id == "template:benched-slope-road"
        assert any(row.kind == "bench" for row in result.sections[0].subassembly_rows)
        assert any(point.point_role == "bench_surface" for point in result.sections[0].point_rows)
        polylines = applied_sections_command._applied_section_preview_polylines(
            result.sections[0],
            result.sections[0].frame,
        )
        assert any("side_slope_points" in role for role, _points in polylines)
        assert not any(role in {"left_slope_face", "right_slope_face"} for role, _points in polylines)
    finally:
        App.closeDocument(doc.Name)


def test_applied_section_review_rows_summarize_station_context() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        result = build_document_applied_section_set(doc, project=project)

        rows = applied_section_review_rows(result)

        assert len(rows) == len(result.station_rows)
        assert rows[0]["region_id"] == "region:normal-01"
        assert rows[0]["assembly_id"] == "assembly:basic-road"
        assert rows[0]["template_id"] == "template:basic-road"
        assert rows[0]["surface_left_width"] > 0.0
        assert rows[0]["surface_right_width"] > 0.0
        assert rows[0]["subassembly_count"] == 6
        assert rows[0]["subassembly_summary"] == "lane:2, shoulder:2, side_slope:2"
        assert rows[0]["slope_face_summary"]
        assert rows[0]["diagnostic_summary"] == ""
        assert rows[0]["status"] == "ok"
    finally:
        App.closeDocument(doc.Name)


def test_applied_section_review_rows_expose_ditch_context() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=120.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Drainage Ditch Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        first = region_model.region_rows[0]
        region_model.region_rows[0] = type(first)(
            region_id=first.region_id,
            region_index=first.region_index,
            station_start=first.station_start,
            station_end=first.station_end,
            assembly_ref="assembly:drainage-ditch-road",
            template_ref="template:drainage-ditch-road",
            priority=first.priority,
        )
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        result = build_document_applied_section_set(doc, project=project)
        rows = applied_section_review_rows(result)

        assert "ditch:2" in rows[0]["subassembly_summary"]
        assert "subassemblies:2" in rows[0]["ditch_summary"]
        assert "points:" in rows[0]["ditch_summary"]
        assert rows[0]["slope_face_summary"]
        polylines = applied_sections_command._applied_section_preview_polylines(
            result.sections[0],
            result.sections[0].frame,
        )
        assert any(role == "left_ditch_points" for role, _points in polylines)
        assert any(role == "right_ditch_points" for role, _points in polylines)
    finally:
        App.closeDocument(doc.Name)


def test_build_document_applied_sections_resolves_drainage_from_drainage_model_region_refs() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=120.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Drainage Ditch Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        first = region_model.region_rows[0]
        region_model.region_rows[0] = type(first)(
            region_id=first.region_id,
            region_index=first.region_index,
            station_start=first.station_start,
            station_end=first.station_end,
            assembly_ref="assembly:drainage-ditch-road",
            template_ref="template:drainage-ditch-road",
            priority=first.priority,
        )
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        "drainage:plain-left",
                        "ditch",
                        side="left",
                        region_ref=first.region_id,
                        station_start=0.0,
                        station_end=240.0,
                    ),
                    DrainageElementRow(
                        "drainage:plain-right",
                        "ditch",
                        side="right",
                        region_ref=first.region_id,
                        station_start=0.0,
                        station_end=240.0,
                    ),
                ],
            ),
        )

        result = build_document_applied_section_set(doc, project=project)

        ditch_subassemblies = [row for row in result.sections[0].subassembly_rows if row.kind == "ditch"]
        ditch_points = [row for row in result.sections[0].point_rows if row.point_role == "ditch_surface"]
        flowline_points = [row for row in result.sections[0].point_rows if row.point_role == "ditch_flowline"]
        assert [row.drainage_refs for row in ditch_subassemblies] == [["drainage:plain-left"], ["drainage:plain-right"]]
        assert {row.drainage_ref for row in ditch_points} == {"drainage:plain-left", "drainage:plain-right"}
        assert {row.drainage_ref for row in flowline_points} == {"drainage:plain-left", "drainage:plain-right"}
        assert {row.side for row in flowline_points} == {"left", "right"}
        assert "drainage:main" in result.source_refs
    finally:
        App.closeDocument(doc.Name)


def test_build_document_applied_section_set_uses_region_specific_assembly_objects() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=120.0)
        road_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        bridge_model = assembly_subassembly_preset_model_from_document("Bridge Interface", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(
            doc,
            project=project,
            assembly_model=road_model,
            object_name="V1AssemblySubassemblyModelRoad",
            label="Road Assembly",
        )
        create_or_update_v1_assembly_subassembly_model_object(
            doc,
            project=project,
            assembly_model=bridge_model,
            object_name="V1AssemblySubassemblyModelBridge",
            label="Bridge Assembly",
        )
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        region_model.region_rows[0] = type(region_model.region_rows[0])(
            region_id="region:bridge-all",
            region_index=1,
            station_start=0.0,
            station_end=100000.0,
            assembly_ref="assembly:bridge-interface",
            template_ref="template:bridge-interface",
            priority=80,
        )
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        result = build_document_applied_section_set(doc, project=project)

        assert result.sections
        assert {section.assembly_id for section in result.sections} == {"assembly:bridge-interface"}
        assert {section.template_id for section in result.sections} == {"template:bridge-interface"}
        assert result.sections[0].subassembly_rows[0].source_template_id == "template:bridge-interface"
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_applied_section_set_creates_result_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        obj = apply_v1_applied_section_set(document=doc, project=project)

        assert obj == find_v1_applied_section_set(doc)
        assert obj.V1ObjectType == "V1AppliedSectionSet"
        assert obj.StationCount == 5
        assert list(obj.TemplateIds) == [
            "template:basic-road",
            "template:basic-road",
            "template:basic-road",
            "template:basic-road",
            "template:basic-road",
        ]
        assert hasattr(obj, "Shape")
        assert obj.ReviewShapeStatus == "not_built"
        assert int(obj.ReviewShapeStationCount) == 0
        assert obj.Shape.isNull()
        build_v1_applied_section_set_review_shape(obj)
        assert obj.ReviewShapeStatus == "built"
        assert int(obj.ReviewShapeStationCount) == 5
        assert obj.Shape.BoundBox.XLength > 0.0 or obj.Shape.BoundBox.YLength > 0.0
        if getattr(obj, "ViewObject", None) is not None:
            assert obj.ViewObject.Visibility is False
            assert tuple(round(float(value), 2) for value in obj.ViewObject.LineColor) == (0.58, 0.70, 0.88)
            assert float(obj.ViewObject.LineWidth) <= 1.0
            obj.ViewObject.Visibility = True
            assert obj.ReviewShapeStatus == "built"
            apply_v1_applied_section_set(document=doc, project=project)
            assert obj.ViewObject.Visibility is False
            assert obj.ReviewShapeStatus == "not_built"
    finally:
        App.closeDocument(doc.Name)


def test_applied_sections_panel_shows_progress_bar_and_completes_apply() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    original_show_message = applied_sections_command._show_message
    applied_sections_command._show_message = lambda *_args, **_kwargs: None
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        panel = V1AppliedSectionsTaskPanel(document=doc)
        progress_bars = panel.form.findChildren(QtWidgets.QProgressBar)
        button_labels = [button.text() for button in panel.form.findChildren(QtWidgets.QPushButton)]

        assert len(progress_bars) == 1
        assert not any(check.text() == "Fast Evaluation" for check in panel.form.findChildren(QtWidgets.QCheckBox))
        assert "Build Sections" in button_labels
        assert "Show All" in button_labels
        assert "Validate" not in button_labels
        assert "Apply" not in button_labels
        assert progress_bars[0].format() == "Ready"
        assert panel._apply(close_after=False) is True
        assert panel._progress.value() == 100
        assert panel._progress.format() == "Applied Sections complete"
        assert "Fast Evaluation" not in panel._summary.toPlainText()
        assert panel._review_table.item(0, 6).text() == "basic-road"
        assert panel._review_table.item(0, 7).text() == "basic-road"
    finally:
        applied_sections_command._show_message = original_show_message
        App.closeDocument(doc.Name)


def test_applied_sections_validate_allows_drainage_element_without_region() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    original_show_message = applied_sections_command._show_message
    applied_sections_command._show_message = lambda *_args, **_kwargs: None
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        create_or_update_v1_drainage_model_object(
            doc,
            project=project,
            drainage_model=DrainageModel(
                schema_version=1,
                project_id="proj-1",
                drainage_model_id="drainage:main",
                element_rows=[
                    DrainageElementRow(
                        drainage_element_id="drainage:side-ditch-right",
                        element_kind="ditch",
                        station_start=0.0,
                        station_end=90.0,
                    )
                ],
            ),
        )

        panel = V1AppliedSectionsTaskPanel(document=doc)

        assert panel._validate(show_message=False) is True
        assert "drainage_element_missing_region_ref" not in panel._summary.toPlainText()
        assert panel._apply(close_after=False) is True
        assert find_v1_applied_section_set(doc) is not None
    finally:
        applied_sections_command._show_message = original_show_message
        App.closeDocument(doc.Name)


def test_applied_sections_validate_requires_centerline3d_ready_sources() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    original_show_message = applied_sections_command._show_message
    applied_sections_command._show_message = lambda *_args, **_kwargs: None
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)

        panel = V1AppliedSectionsTaskPanel(document=doc)

        assert panel._validate(show_message=False) is False
        assert "missing_required_sources: Profile" in panel._summary.toPlainText()
    finally:
        applied_sections_command._show_message = original_show_message
        App.closeDocument(doc.Name)


def test_intersection_supplemental_stations_are_added_to_applied_sections() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="proj-1",
        intersection_model_id="intersections:main",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                primary_station=100.0,
                secondary_station_refs={"alignment:side": 40.0},
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="intersection:t-01:main-area",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:main",
                station_ranges=[(90.0, 110.0)],
            ),
            IntersectionControlArea(
                control_area_id="intersection:t-01:side-area",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:side",
                station_ranges=[(30.0, 50.0)],
            ),
        ],
        curb_return_policy_rows=[
            IntersectionCurbReturnPolicyRow(
                policy_id="curb-return:intersection:t-01:default",
                intersection_id="intersection:t-01",
                radius=12.0,
            )
        ],
    )

    main_stations = applied_sections_command._with_intersection_supplemental_stations(
        [0.0, 120.0],
        model,
        "alignment:main",
    )
    main_kinds = applied_sections_command._intersection_supplemental_station_kind_map([0.0, 120.0], main_stations)
    side_stations = applied_sections_command._with_intersection_supplemental_stations(
        [0.0, 80.0],
        model,
        "alignment:side",
    )
    side_kinds = applied_sections_command._intersection_supplemental_station_kind_map([0.0, 80.0], side_stations)

    assert 88.0 in main_stations
    assert 94.0 in main_stations
    assert 100.0 in main_stations
    assert 106.0 in main_stations
    assert 112.0 in main_stations
    assert 90.0 in main_stations
    assert 110.0 in main_stations
    assert 28.0 in side_stations
    assert 34.0 in side_stations
    assert 40.0 in side_stations
    assert 46.0 in side_stations
    assert 52.0 in side_stations
    assert 30.0 in side_stations
    assert 50.0 in side_stations
    assert main_kinds[0.0] == "regular_sample"
    assert main_kinds[100.0] == "intersection_supplemental"
    assert side_kinds[40.0] == "intersection_supplemental"


def test_show_applied_section_preview_object_creates_selected_section_line() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=90.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        result = build_document_applied_section_set(doc, project=project)

        obj = show_applied_section_preview_object(doc, result, 0)
        marker = doc.getObject("V1AppliedSectionStationMarker")

        assert obj is not None
        assert marker is None
        assert obj.CRRecordKind == "v1_applied_section_show_preview"
        assert obj.V1ObjectType == "V1AppliedSectionShowPreview"
        assert obj.RegionId == "region:normal-01"
        assert obj.AssemblyId == "assembly:basic-road"
        assert obj.TemplateId == "template:basic-road"
        assert obj.PreviewMode == "section_points"
        assert int(obj.PreviewPointCount) >= 4
        assert obj.Shape.BoundBox.XLength > 0.0 or obj.Shape.BoundBox.YLength > 0.0
        assert len(obj.Shape.Edges) >= 4
        assert len(obj.Shape.Solids) == 0
        assert obj.Name in _group_names(tree[V1_TREE_APPLIED_SECTIONS])
    finally:
        App.closeDocument(doc.Name)


def test_show_all_applied_sections_preview_object_creates_combined_section_lines() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=45.0)
        assembly_model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        create_or_update_v1_assembly_subassembly_model_object(doc, project=project, assembly_model=assembly_model)
        region_model = starter_region_model_from_document(doc, project=project, alignment=alignment)
        create_or_update_v1_region_model_object(doc, project=project, region_model=region_model)
        result = build_document_applied_section_set(doc, project=project)

        obj = show_all_applied_sections_preview_object(doc, result)

        assert obj is not None
        assert obj.CRRecordKind == "v1_applied_sections_show_all_preview"
        assert obj.V1ObjectType == "V1AppliedSectionsShowAllPreview"
        assert obj.PreviewMode == "all_section_points"
        assert int(obj.PreviewSectionCount) == len(result.sections)
        assert int(obj.PreviewPointCount) >= len(result.sections) * 4
        assert obj.StationStart <= obj.StationEnd
        assert len(obj.Shape.Edges) >= len(result.sections) * 4
        assert obj.Name in _group_names(tree[V1_TREE_APPLIED_SECTIONS])
    finally:
        App.closeDocument(doc.Name)


def test_applied_sections_command_resources_are_v1() -> None:
    resources = CmdV1AppliedSections().GetResources()

    assert resources["MenuText"] == "Applied Sections"
    assert "v1" in resources["ToolTip"]


def test_applied_section_review_row_colors_are_dark_theme_readable() -> None:
    assert applied_section_review_row_color("ok") == (220, 245, 224)
    assert applied_section_review_row_color("warn") == (255, 241, 205)
    assert applied_section_review_row_color("missing") == (255, 220, 220)
    assert applied_section_review_row_color("unknown") is None


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 applied sections command contract tests completed.")
