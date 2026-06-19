import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    CmdV1AssemblySubassemblyEditor,
    V1AssemblySubassemblyEditorTaskPanel,
    _detail_parameter_rows,
    _merge_detail_parameters,
    _subassembly_preview_text,
    _validate_subassembly_model,
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_subassembly_assembly import (
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)


_QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _new_project_doc():
    doc = App.newDocument("V1SubassemblyEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_tree(project, include_references=False)
    return doc, project


def test_subassembly_preset_model_builds_basic_road_rows() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        model = assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment)
        subassemblies = model.template_rows[0].subassembly_rows

        assert model.assembly_id == "assembly:basic-road"
        assert model.active_template_id == "template:basic-road"
        assert model.alignment_id == alignment.AlignmentId
        assert [row.kind for row in subassemblies[:4]] == ["lane", "lane", "shoulder", "shoulder"]
        assert subassemblies[0].side == "left"
        assert subassemblies[0].width == 3.5
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_presets_offer_ditch_and_benched_slope_parameters() -> None:
    doc, project = _new_project_doc()
    try:
        drainage = assembly_subassembly_preset_model_from_document("Drainage Ditch Road", doc, project=project)
        ditch_rows = [row for row in drainage.template_rows[0].subassembly_rows if row.kind == "ditch"]
        assert ditch_rows
        assert {row.parameters.get("shape") for row in ditch_rows} == {"trapezoid"}
        assert ditch_rows[0].parameters["bottom_width"] == 0.6

        benched = assembly_subassembly_preset_model_from_document("Benched Ditch Road", doc, project=project)
        side_slopes = [row for row in benched.template_rows[0].subassembly_rows if row.kind == "side_slope"]
        assert len(side_slopes) == 2
        assert all(row.parameters["bench_mode"] == "rows" for row in side_slopes)
        assert all(row.parameters["repeat_first_bench_to_daylight"] is True for row in side_slopes)
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_validation_reports_bench_warnings() -> None:
    model = AssemblySubassemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:bench-validation",
        template_rows=[
            SubassemblySectionTemplate(
                template_id="template:bench-validation",
                template_kind="roadway",
                subassembly_rows=[
                    TemplateSubassembly(
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

    messages = _validate_subassembly_model(model)

    assert "WARNING: side_slope subassembly side-slope-left has bench_rows but zero side-slope width." in messages
    assert (
        "WARNING: side_slope subassembly side-slope-left repeats bench rows to daylight without daylight mode and max width."
        in messages
    )


def test_subassembly_object_roundtrips_source_rows() -> None:
    doc, project = _new_project_doc()
    try:
        model = assembly_subassembly_preset_model_from_document("Benched Slope Road", doc, project=project)

        obj = apply_v1_assembly_subassembly_model(document=doc, project=project, assembly_model=model)
        roundtrip = to_assembly_subassembly_model(obj)
        side_slopes = [row for row in roundtrip.template_rows[0].subassembly_rows if row.kind == "side_slope"]

        assert obj == find_v1_assembly_subassembly_model(doc)
        assert obj.V1ObjectType == "V1AssemblySubassemblyModel"
        assert obj.SubassemblyCount == len(model.template_rows[0].subassembly_rows)
        assert side_slopes[0].parameters["bench_mode"] == "rows"
        assert side_slopes[0].parameters["bench_rows"][0]["drop"] == 3.0
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_detail_rows_and_merge_handle_ditch_shape() -> None:
    rows = _detail_parameter_rows(
        "ditch",
        {
            "shape": "trapezoid",
            "bottom_width": 0.6,
            "depth": 0.5,
            "side_slope": 1.5,
            "lining": "grass",
        },
    )

    assert ("shape", "trapezoid") in rows
    assert ("bottom_width", 0.6) in rows
    assert ("depth", 0.5) in rows

    merged = _merge_detail_parameters("ditch", {"shape": "v", "depth": 0.3, "custom": "keep"}, {"shape": "u", "depth": "0.7"})
    assert merged["shape"] == "u"
    assert merged["depth"] == "0.7"
    assert merged["custom"] == "keep"


def test_subassembly_preview_text_uses_subassembly_ownership() -> None:
    text = _subassembly_preview_text(
        subassembly_id="ditch:left",
        kind="ditch",
        side="left",
        width=1.4,
        slope=-0.02,
        thickness=0.1,
        material="concrete",
        parameters={"shape": "trapezoid", "bottom_width": 0.6, "depth": 0.5},
    )

    assert "subassembly_ref: ditch:left" in text
    assert "surface_role=drainage_surface" in text
    assert "shape=trapezoid" in text
    assert "material=concrete" in text


def test_subassembly_detail_changes_only_on_table_row_click() -> None:
    doc, _project = _new_project_doc()
    try:
        panel = V1AssemblySubassemblyEditorTaskPanel(document=doc)
        calls = []
        original_refresh = panel._refresh_selected_detail

        def tracked_refresh():
            calls.append(panel._selected_row())
            original_refresh()

        panel._refresh_selected_detail = tracked_refresh
        panel.table.selectRow(2)
        panel.table.itemSelectionChanged.emit()

        assert calls == []

        panel.table.cellClicked.emit(2, 0)

        assert calls == [2]
    finally:
        App.closeDocument(doc.Name)


def test_subassembly_editor_command_resources() -> None:
    resources = CmdV1AssemblySubassemblyEditor().GetResources()

    assert resources["MenuText"] == "Assembly / Subassembly"
    assert "Subassembly" in resources["ToolTip"]
