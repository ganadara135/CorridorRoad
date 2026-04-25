import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_ALIGNMENTS,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.commands.cmd_create_alignment import create_v1_sample_alignment
from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
    build_document_plan_profile_preview,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import (
    build_v1_alignment_shape,
    create_sample_v1_alignment,
    find_v1_alignment,
    to_alignment_model,
)


def _new_project_doc():
    doc = App.newDocument("CRV1AlignmentSourceContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def test_create_sample_v1_alignment_builds_alignment_model_contract() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        model = to_alignment_model(alignment)

        assert alignment.V1ObjectType == "V1Alignment"
        assert model is not None
        assert model.alignment_id == alignment.AlignmentId
        assert model.label == "Main Alignment"
        assert len(model.geometry_sequence) == 3
        assert model.geometry_sequence[0].station_start == 0.0
        assert model.geometry_sequence[-1].station_end == 180.0
    finally:
        App.closeDocument(doc.Name)


def test_create_sample_v1_alignment_builds_display_shape() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        doc.recompute()

        shape = getattr(alignment, "Shape", None)

        assert shape is not None
        assert not shape.isNull()
        assert int(alignment.CompiledPointCount) == 7
        assert int(alignment.CompiledEdgeCount) == 4
        assert int(alignment.CompiledCurveElementCount) == 1
        assert int(alignment.CompiledTransitionElementCount) == 0
        assert build_v1_alignment_shape(alignment) is not None
    finally:
        App.closeDocument(doc.Name)


def test_create_v1_sample_alignment_routes_object_to_v1_tree() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_v1_sample_alignment(document=doc, project=project)
        tree = ensure_project_tree(project, include_references=False)

        assert find_v1_alignment(doc) == alignment
        assert alignment.Name in _group_names(tree[V1_TREE_ALIGNMENTS])
        assert "02_Alignments" not in {
            str(getattr(obj, "Label", "") or "")
            for obj in list(getattr(project, "Group", []) or [])
        }
    finally:
        App.closeDocument(doc.Name)


def test_plan_profile_preview_prefers_v1_alignment_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        preview = build_document_plan_profile_preview(doc)

        assert preview is not None
        assert preview["preview_source_kind"] == "document"
        assert preview["alignment_model"].alignment_id == alignment.AlignmentId
        assert preview["legacy_objects"]["alignment"] == alignment
        assert preview["plan_output"].plan_output_id == alignment.AlignmentId
        assert preview["profile_model"] is None
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 alignment source object contract tests completed.")
