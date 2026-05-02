import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import V1_TREE_ASSEMBLIES, CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_assembly_editor import (
    CmdV1AssemblyEditor,
    V1AssemblyEditorTaskPanel,
    _assembly_preview_points,
    _bench_shape_diagram,
    _ditch_component_note,
    _ditch_effective_field_keys,
    _ditch_material_note,
    _ditch_shape_diagram,
    _ditch_shape_defaults,
    _ditch_visible_field_keys,
    _bench_component_note,
    _merge_bench_parameters,
    _merge_ditch_parameters,
    NEW_ASSEMBLY_SOURCE_KEY,
    _side_slope_bench_preview_segments,
    _validate_assembly_model,
    assembly_source_display_name,
    assembly_source_rows,
    assembly_preset_model_from_document,
    assembly_preset_names,
    apply_v1_assembly_model,
    show_assembly_preview_object,
    starter_assembly_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    ASSEMBLY_DAYLIGHT_MODES,
    AssemblyModel,
    SectionTemplate,
    TemplateComponent,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_assembly import find_v1_assembly_model, to_assembly_model

_QAPP = None


def _new_project_doc():
    doc = App.newDocument("V1AssemblyEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def test_starter_assembly_model_builds_basic_road_components() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        model = starter_assembly_model_from_document(doc, project=project, alignment=alignment)

        components = model.template_rows[0].component_rows
        assert model.assembly_id == "assembly:basic-road"
        assert model.active_template_id == "template:basic-road"
        assert model.alignment_id == alignment.AlignmentId
        assert [component.kind for component in components[:4]] == ["lane", "lane", "shoulder", "shoulder"]
        assert components[0].side == "left"
        assert components[0].width == 3.5
    finally:
        App.closeDocument(doc.Name)


def test_assembly_presets_offer_multiple_practical_templates() -> None:
    doc, project = _new_project_doc()
    try:
        names = assembly_preset_names()

        assert "Basic Road" in names
        assert "Urban Curb & Gutter" in names
        assert "Bridge Interface" in names
        urban = assembly_preset_model_from_document("Urban Curb & Gutter", doc, project=project)
        components = urban.template_rows[0].component_rows
        assert urban.assembly_id == "assembly:urban-curb-gutter"
        assert urban.active_template_id == "template:urban-curb-gutter"
        assert "gutter" in [component.kind for component in components]
        assert "sidewalk" in [component.kind for component in components]
        drainage = assembly_preset_model_from_document("Drainage Ditch Road", doc, project=project)
        ditch_components = [component for component in drainage.template_rows[0].component_rows if component.kind == "ditch"]
        assert ditch_components
        assert {component.parameters.get("shape") for component in ditch_components} == {"trapezoid"}
        assert ditch_components[0].parameters["bottom_width"] == 0.6
        benched = assembly_preset_model_from_document("Benched Slope Road", doc, project=project)
        side_slopes = [component for component in benched.template_rows[0].component_rows if component.kind == "side_slope"]
        assert len(side_slopes) == 2
        assert side_slopes[0].parameters["bench_mode"] == "rows"
        assert side_slopes[0].parameters["bench_rows"][0]["width"] == 1.5
        benched_ditch = assembly_preset_model_from_document("Benched Ditch Road", doc, project=project)
        benched_ditch_components = benched_ditch.template_rows[0].component_rows
        benched_ditch_ditches = [component for component in benched_ditch_components if component.kind == "ditch"]
        benched_ditch_slopes = [component for component in benched_ditch_components if component.kind == "side_slope"]
        assert "Benched Ditch Road" in names
        assert benched_ditch.assembly_id == "assembly:benched-ditch-road"
        assert benched_ditch.active_template_id == "template:benched-ditch-road"
        assert len(benched_ditch_ditches) == 2
        assert len(benched_ditch_slopes) == 2
        assert {component.parameters.get("shape") for component in benched_ditch_ditches} == {"trapezoid"}
        assert all(component.parameters["bench_mode"] == "rows" for component in benched_ditch_slopes)
        assert all(component.parameters["repeat_first_bench_to_daylight"] is True for component in benched_ditch_slopes)
        assert [component.kind for component in benched_ditch_components[-4:]] == ["ditch", "ditch", "side_slope", "side_slope"]
    finally:
        App.closeDocument(doc.Name)


def test_assembly_validation_reports_ditch_shape_parameter_warnings() -> None:
    model = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:ditch-validation",
        template_rows=[
            SectionTemplate(
                template_id="template:ditch-validation",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(
                        "ditch-left",
                        "ditch",
                        side="left",
                        width=1.2,
                        parameters={"shape": "trapezoid", "bottom_width": 0.5},
                    ),
                    TemplateComponent(
                        "ditch-concrete",
                        "ditch",
                        side="right",
                        width=1.2,
                        material="concrete",
                        parameters={"shape": "u", "bottom_width": 0.7, "depth": 0.5},
                    )
                ],
            )
        ],
    )

    messages = _validate_assembly_model(model)

    assert "WARN: ditch component ditch-left missing required parameter depth." in messages
    assert "WARN: ditch component ditch-concrete uses structural material and requires wall_thickness." in messages


def test_assembly_validation_reports_side_slope_bench_warnings() -> None:
    model = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:bench-validation",
        template_rows=[
            SectionTemplate(
                template_id="template:bench-validation",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(
                        "side-slope-left",
                        "side_slope",
                        side="left",
                        width=0.0,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [{"drop": 2.0, "width": 1.2, "slope": -0.02, "post_slope": -0.5}],
                            "repeat_first_bench_to_daylight": True,
                        },
                    )
                ],
            )
        ],
    )

    messages = _validate_assembly_model(model)

    assert "WARN: side_slope component side-slope-left has bench_rows but zero side-slope width." in messages
    assert (
        "WARN: side_slope component side-slope-left repeats bench rows to daylight without daylight mode and max width."
        in messages
    )


def test_assembly_object_roundtrips_side_slope_bench_parameters() -> None:
    doc, project = _new_project_doc()
    try:
        model = assembly_preset_model_from_document("Benched Slope Road", doc, project=project)

        obj = apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        roundtrip = to_assembly_model(obj)
        side_slopes = [component for component in roundtrip.template_rows[0].component_rows if component.kind == "side_slope"]

        assert side_slopes[0].parameters["bench_mode"] == "rows"
        assert side_slopes[0].parameters["bench_rows"][0]["drop"] == 3.0
        assert side_slopes[0].parameters["repeat_first_bench_to_daylight"] is True
    finally:
        App.closeDocument(doc.Name)


def test_assembly_source_rows_list_multiple_assembly_objects() -> None:
    doc, project = _new_project_doc()
    try:
        basic = assembly_preset_model_from_document("Basic Road", doc, project=project)
        benched = assembly_preset_model_from_document("Benched Ditch Road", doc, project=project)

        apply_v1_assembly_model(
            document=doc,
            project=project,
            assembly_model=basic,
            object_name="V1AssemblyModel_basic",
        )
        apply_v1_assembly_model(
            document=doc,
            project=project,
            assembly_model=benched,
            object_name="V1AssemblyModel_benched_ditch",
        )

        rows = assembly_source_rows(doc)
        labels = [str(row["label"]) for row in rows]
        displays = [str(row["display"]) for row in rows]

        assert {row["assembly_id"] for row in rows} >= {"assembly:basic-road", "assembly:benched-ditch-road"}
        assert "assembly:basic-road" in displays
        assert "assembly:benched-ditch-road" in displays
        assert any("assembly:basic-road" in label and "template:basic-road" in label for label in labels)
        assert any("assembly:benched-ditch-road" in label and "template:benched-ditch-road" in label for label in labels)
    finally:
        App.closeDocument(doc.Name)


def test_assembly_editor_can_load_selected_assembly_source() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        basic = assembly_preset_model_from_document("Basic Road", doc, project=project)
        benched = assembly_preset_model_from_document("Benched Ditch Road", doc, project=project)
        first = apply_v1_assembly_model(
            document=doc,
            project=project,
            assembly_model=basic,
            object_name="V1AssemblyModel_basic",
        )
        second = apply_v1_assembly_model(
            document=doc,
            project=project,
            assembly_model=benched,
            object_name="V1AssemblyModel_benched_ditch",
        )

        panel = V1AssemblyEditorTaskPanel(document=doc)
        for index in range(panel._source_combo.count()):
            if str(panel._source_combo.itemData(index) or "") == second.Name:
                panel._source_combo.setCurrentIndex(index)
                break
        panel._load_selected_assembly_source()

        assert panel.assembly_obj == second
        assert panel._assembly_id.text() == "assembly:benched-ditch-road"
        assert panel._template_id.text() == "template:benched-ditch-road"
        assert panel._table.rowCount() == len(benched.template_rows[0].component_rows)
        assert first.Name != second.Name
    finally:
        App.closeDocument(doc.Name)


def test_assembly_editor_marks_dirty_and_creates_new_when_assembly_id_differs() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    original_show_message = __import__(
        "freecad.Corridor_Road.v1.commands.cmd_assembly_editor",
        fromlist=["_show_message"],
    )
    old_show_message = original_show_message._show_message
    original_show_message._show_message = lambda *_args, **_kwargs: None
    try:
        model = assembly_preset_model_from_document("Basic Road", doc, project=project)
        obj = apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        panel = V1AssemblyEditorTaskPanel(document=doc)

        panel._assembly_id.setText("assembly:another-road")
        applied = panel._apply(close_after=False)

        assert applied is True
        assert panel.assembly_obj != obj
        assert panel.assembly_obj.AssemblyId == "assembly:another-road"
        assert "Saved" in panel._dirty_summary.text()
        assert any(row["assembly_id"] == "assembly:another-road" for row in assembly_source_rows(doc))
    finally:
        original_show_message._show_message = old_show_message
        App.closeDocument(doc.Name)


def test_assembly_editor_apply_creates_distinct_assembly_source_for_new_id() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    original_show_message = __import__(
        "freecad.Corridor_Road.v1.commands.cmd_assembly_editor",
        fromlist=["_show_message"],
    )
    old_show_message = original_show_message._show_message
    original_show_message._show_message = lambda *_args, **_kwargs: None
    try:
        model = assembly_preset_model_from_document("Basic Road", doc, project=project)
        first = apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        panel = V1AssemblyEditorTaskPanel(document=doc)
        panel._assembly_id.setText("assembly:alternate-road")
        panel._template_id.setText("template:alternate-road")

        panel._apply(close_after=False)

        rows = assembly_source_rows(doc)
        assert first.Name == "V1AssemblyModel"
        assert any(row["assembly_id"] == "assembly:alternate-road" for row in rows)
        assert len(rows) >= 2
    finally:
        original_show_message._show_message = old_show_message
        App.closeDocument(doc.Name)


def test_assembly_source_combo_offers_new_assembly_create_mode() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    try:
        model = assembly_preset_model_from_document("Basic Road", doc, project=project)
        apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        panel = V1AssemblyEditorTaskPanel(document=doc)

        assert panel._source_combo.itemText(0) == "New Assembly Create"
        assert panel._source_combo.itemData(0) == NEW_ASSEMBLY_SOURCE_KEY
    finally:
        App.closeDocument(doc.Name)


def test_assembly_editor_new_assembly_mode_uses_apply_to_create_source() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc()
    original_show_message = __import__(
        "freecad.Corridor_Road.v1.commands.cmd_assembly_editor",
        fromlist=["_show_message"],
    )
    old_show_message = original_show_message._show_message
    original_show_message._show_message = lambda *_args, **_kwargs: None
    try:
        model = assembly_preset_model_from_document("Basic Road", doc, project=project)
        apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        panel = V1AssemblyEditorTaskPanel(document=doc)
        panel._source_combo.setCurrentIndex(0)
        panel._load_selected_assembly_source()

        assert panel._new_assembly_mode is True
        assert panel.assembly_obj is None
        assert panel._assembly_id.text().startswith("assembly:new-assembly")
        assert "New Assembly mode" in panel._editing_summary.text()

        panel._apply(close_after=False)

        assert panel._new_assembly_mode is False
        assert panel.assembly_obj is not None
        assert str(panel.assembly_obj.AssemblyId).startswith("assembly:new-assembly")
        assert any(row["assembly_id"] == panel.assembly_obj.AssemblyId for row in assembly_source_rows(doc))
    finally:
        original_show_message._show_message = old_show_message
        App.closeDocument(doc.Name)


def test_assembly_source_combo_displays_short_assembly_name() -> None:
    doc, project = _new_project_doc()
    try:
        model = assembly_preset_model_from_document("Benched Ditch Road", doc, project=project)
        obj = apply_v1_assembly_model(document=doc, project=project, assembly_model=model)

        assert assembly_source_display_name(obj) == "assembly:benched-ditch-road"
    finally:
        App.closeDocument(doc.Name)


def test_ditch_parameter_editor_merge_preserves_unknown_parameters() -> None:
    merged = _merge_ditch_parameters(
        {"shape": "v", "depth": "0.2", "hydraulic_note": "keep"},
        {"shape": "trapezoid", "bottom_width": "0.6", "depth": "0.45", "top_width": ""},
    )

    assert merged["shape"] == "trapezoid"
    assert merged["bottom_width"] == "0.6"
    assert merged["depth"] == "0.45"
    assert "top_width" not in merged
    assert merged["hydraulic_note"] == "keep"


def test_bench_parameter_editor_merge_preserves_unknown_parameters() -> None:
    merged = _merge_bench_parameters(
        {"drainage_note": "keep", "bench_mode": "none"},
        {
            "bench_mode": "rows",
            "bench_rows": [{"drop": "3.0", "width": "1.5", "slope": "-0.02", "post_slope": "-0.5"}],
            "repeat_first_bench_to_daylight": True,
            "daylight_mode": "terrain",
            "daylight_max_width": "80.000",
        },
    )

    assert merged["drainage_note"] == "keep"
    assert merged["bench_mode"] == "rows"
    assert merged["bench_rows"][0]["width"] == 1.5
    assert merged["repeat_first_bench_to_daylight"] is True
    assert merged["daylight_mode"] == "terrain"


def test_bench_daylight_modes_are_explicit_editor_choices() -> None:
    assert ASSEMBLY_DAYLIGHT_MODES == ("off", "terrain", "fixed_width")


def test_assembly_editor_defaults_daylight_mode_to_terrain() -> None:
    _ensure_qapp()
    doc, _project = _new_project_doc()
    try:
        panel = V1AssemblyEditorTaskPanel(document=doc)

        assert panel._bench_daylight_mode.currentText() == "terrain"
        panel._clear_bench_parameter_fields()
        assert panel._bench_daylight_mode.currentText() == "terrain"
    finally:
        App.closeDocument(doc.Name)


def test_assembly_validation_warns_on_unknown_daylight_mode() -> None:
    model = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly",
        active_template_id="template",
        template_rows=[
            SectionTemplate(
                template_id="template",
                template_kind="roadway",
                label="Template",
                component_rows=[
                    TemplateComponent(
                        "side-slope-left",
                        "side_slope",
                        side="left",
                        width=3.0,
                        parameters={
                            "bench_mode": "rows",
                            "bench_rows": [{"drop": 2.0, "width": 1.2, "slope": -0.02, "post_slope": -0.5}],
                            "repeat_first_bench_to_daylight": True,
                            "daylight_mode": "target_surface",
                            "daylight_max_width": 80.0,
                        },
                    )
                ],
            )
        ],
    )

    messages = _validate_assembly_model(model)

    assert "WARN: side_slope component side-slope-left has unknown daylight_mode target_surface." in messages


def test_bench_component_note_summarizes_rows_and_daylight_context() -> None:
    note = _bench_component_note(
        side="left",
        parameters={
            "bench_rows": [{"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}],
            "repeat_first_bench_to_daylight": True,
            "daylight_mode": "terrain",
        },
    )

    assert "Left side slope bench rows=1" in note
    assert "first_width=1.500" in note
    assert "repeat_to_daylight=on" in note
    assert "daylight=terrain" in note


def test_bench_shape_diagram_reflects_bench_rows_and_daylight_context() -> None:
    diagram = _bench_shape_diagram(
        [{"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5}],
        width=12.0,
        slope=-0.5,
        repeat=True,
        daylight_mode="terrain",
        max_width="80.000",
    )

    assert "terminal edge -> daylight" in diagram
    assert "____" in diagram
    assert "bench: width=1.500" in diagram
    assert "repeat=on" in diagram
    assert "daylight=terrain, max=80.000" in diagram


def test_ditch_shape_helpers_limit_visible_fields_and_defaults() -> None:
    assert _ditch_visible_field_keys("u") == ("bottom_width", "depth", "wall_thickness", "lining_thickness")
    assert "lining_thickness" in _ditch_effective_field_keys("v", "riprap_lined")
    assert _ditch_visible_field_keys("custom_polyline") == ("section_points",)
    assert _ditch_shape_defaults("v")["invert_offset"] == "0.800"
    assert "bottom" in _ditch_shape_diagram("trapezoid")
    assert "section_points" in _ditch_shape_diagram("custom_polyline")
    assert "structural" in _ditch_material_note("concrete", "u")


def test_ditch_component_note_reflects_shape_material_and_parameters() -> None:
    note = _ditch_component_note(
        side="right",
        material="concrete",
        parameters={"shape": "u", "bottom_width": "0.700", "depth": "0.500", "wall_thickness": "0.150"},
    )

    assert "Right U-shaped ditch" in note
    assert "bottom_width=0.700" in note
    assert "depth=0.500" in note
    assert "material=concrete" in note
    assert "policy=structural" in note


def test_apply_v1_assembly_model_creates_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        model = starter_assembly_model_from_document(doc, project=project)

        obj = apply_v1_assembly_model(document=doc, project=project, assembly_model=model)
        roundtrip = to_assembly_model(obj)

        assert obj == find_v1_assembly_model(doc)
        assert obj.V1ObjectType == "V1AssemblyModel"
        assert obj.CRRecordKind == "v1_assembly_model"
        assert roundtrip.assembly_id == "assembly:basic-road"
        assert len(roundtrip.template_rows[0].component_rows) == 6
    finally:
        App.closeDocument(doc.Name)


def test_show_assembly_preview_object_creates_front_view_cross_section() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        model = starter_assembly_model_from_document(doc, project=project)

        obj = show_assembly_preview_object(doc, model)

        assert obj is not None
        assert obj.CRRecordKind == "v1_assembly_show_preview"
        assert obj.V1ObjectType == "V1AssemblyShowPreview"
        assert obj.AssemblyId == "assembly:basic-road"
        assert int(obj.ComponentCount) == 6
        assert obj.Shape.BoundBox.XLength > 0.0
        assert obj.Shape.BoundBox.ZLength > 0.0
        assert obj.Name in _group_names(tree[V1_TREE_ASSEMBLIES])
    finally:
        App.closeDocument(doc.Name)


def test_assembly_preview_points_follow_shape_aware_ditch_parameters() -> None:
    template = SectionTemplate(
        template_id="template:ditch-preview",
        template_kind="roadway",
        component_rows=[
            TemplateComponent("lane-left", "lane", side="left", width=3.5),
            TemplateComponent(
                "ditch-left",
                "ditch",
                side="left",
                width=1.2,
                parameters={"shape": "u", "bottom_width": 1.2, "depth": 0.8},
            ),
        ],
    )

    points = _assembly_preview_points(template)

    assert any(
        round(float(left.x), 6) == round(float(right.x), 6)
        and abs(float(left.z) - float(right.z)) > 0.5
        for left, right in zip(points, points[1:])
    )


def test_assembly_preview_points_show_side_slope_bench_segments() -> None:
    component = TemplateComponent(
        "side-slope-right",
        "side_slope",
        side="right",
        width=10.0,
        slope=-0.5,
        parameters={
            "bench_rows": [{"drop": 3.0, "width": 2.0, "slope": -0.02, "post_slope": -0.5}],
        },
    )
    template = SectionTemplate(
        template_id="template:bench-preview",
        template_kind="roadway",
        component_rows=[
            TemplateComponent("lane-right", "lane", side="right", width=3.5),
            component,
        ],
    )

    segments = _side_slope_bench_preview_segments(component)
    points = _assembly_preview_points(template)

    assert [segment["kind"] for segment in segments] == ["side_slope", "bench", "side_slope"]
    assert any(
        abs(abs(float(right.x) - float(left.x)) - 2.0) < 1.0e-6
        and abs((float(right.z) - float(left.z)) / (float(right.x) - float(left.x)) + 0.02) < 1.0e-6
        for left, right in zip(points, points[1:])
        if abs(float(right.x) - float(left.x)) > 1.0e-9
    )


def test_assembly_editor_command_resources_are_v1_assembly() -> None:
    resources = CmdV1AssemblyEditor().GetResources()

    assert resources["MenuText"] == "Assembly"
    assert "v1" in resources["ToolTip"]


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 assembly editor command contract tests completed.")
