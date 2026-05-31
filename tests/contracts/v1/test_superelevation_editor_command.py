import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_SUPERELEVATION,
    ensure_project_tree,
)
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_superelevation_editor import (
    CmdV1SuperelevationEditor,
    V1SuperelevationEditorTaskPanel,
    apply_v1_superelevation_model,
    show_v1_superelevation_review_object,
    starter_superelevation_model_from_document,
    superelevation_preset_model_from_document,
    superelevation_preset_names,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.obj_superelevation import find_v1_superelevation_source, to_superelevation_model

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _new_project_doc(name: str = "V1SuperelevationEditorCommandTest"):
    doc = App.newDocument(name)
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def test_superelevation_editor_resources_are_real_editor_entry() -> None:
    resources = CmdV1SuperelevationEditor().GetResources()

    assert resources["MenuText"] == "Superelevation"
    assert "crossfall" in resources["ToolTip"]


def test_starter_superelevation_model_is_empty_source_intent() -> None:
    model = starter_superelevation_model_from_document()

    assert model.superelevation_id == "superelevation:main"
    assert model.superelevation_kind == "roadway_superelevation"
    assert model.control_rows == []
    assert model.transition_rows == []


def test_superelevation_presets_are_removed_in_favor_of_auto_calculate() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)

        assert superelevation_preset_names() == []
        try:
            superelevation_preset_model_from_document("Simple Right Curve", doc, project=project, alignment=alignment)
        except ValueError as exc:
            assert "removed" in str(exc)
        else:
            raise AssertionError("Superelevation preset loading should be removed.")
    finally:
        App.closeDocument(doc.Name)


def test_superelevation_editor_auto_calculate_fills_rows_without_applying() -> None:
    _ensure_qapp()
    doc, _project, _tree = _new_project_doc("V1SuperelevationEditorPresetEmptyTest")
    try:
        alignment = create_sample_v1_alignment(doc)
        create_v1_stationing(doc, alignment=alignment, interval=50.0)
        panel = V1SuperelevationEditorTaskPanel(document=doc)

        result = panel._auto_calculate()

        assert result is not None
        assert panel._control_table.rowCount() > 0
        assert panel._transition_table.rowCount() > 0
        assert find_v1_superelevation_source(doc) is None
        assert "Auto Calculate complete" in panel._status.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_superelevation_editor_apply_persists_source_object_and_routes_tree() -> None:
    _ensure_qapp()
    doc, project, tree = _new_project_doc("V1SuperelevationEditorApplyTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)
        panel = V1SuperelevationEditorTaskPanel(document=doc)
        panel._auto_calculate()

        assert panel._apply(close_after=False) is True

        obj = find_v1_superelevation_source(doc)
        model = to_superelevation_model(obj)
        assert obj is not None
        assert model is not None
        assert len(model.control_rows) > 1
        assert obj.Name in _group_names(tree[V1_TREE_SUPERELEVATION])
    finally:
        App.closeDocument(doc.Name)


def test_apply_v1_superelevation_model_routes_source_object() -> None:
    _ensure_qapp()
    doc, project, tree = _new_project_doc("V1SuperelevationApplyFunctionTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_v1_stationing(doc, project=project, alignment=alignment, interval=50.0)
        panel = V1SuperelevationEditorTaskPanel(document=doc)
        result = panel._auto_calculate()
        assert result is not None
        model = result.superelevation_model

        obj = apply_v1_superelevation_model(document=doc, project=project, superelevation_model=model)

        assert obj.LastValidationStatus in {"ok", "warning"}
        assert obj.Name in _group_names(tree[V1_TREE_SUPERELEVATION])
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_superelevation_review_object_creates_crossfall_bars() -> None:
    _ensure_qapp()
    doc, project, tree = _new_project_doc("V1SuperelevationReviewObjectTest")
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        create_sample_v1_profile(doc, project=project, alignment=alignment)
        stationing = create_v1_stationing(doc, project=project, alignment=alignment, interval=60.0)
        panel = V1SuperelevationEditorTaskPanel(document=doc)
        result = panel._auto_calculate()
        assert result is not None
        model = result.superelevation_model

        obj = show_v1_superelevation_review_object(
            document=doc,
            superelevation_model=model,
            stations=list(stationing.StationValues),
        )

        assert obj.CRRecordKind == "v1_superelevation_review"
        assert obj.V1ObjectType == "V1SuperelevationReview"
        assert obj.SuperelevationId == "superelevation:main"
        assert int(obj.SampleCount) == len(list(stationing.StationValues))
        assert list(obj.StationLabels)[0] == f"{float(list(stationing.StationValues)[0]):.3f}"
        assert obj.Name in _group_names(tree[V1_TREE_SUPERELEVATION])
        assert not obj.Shape.isNull()
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 superelevation editor command tests completed.")
