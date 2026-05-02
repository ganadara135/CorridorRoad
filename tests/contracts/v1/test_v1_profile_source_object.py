import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    V1_TREE_ALIGNMENTS,
    V1_TREE_PROFILES,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.commands.cmd_create_profile import create_v1_sample_profile
from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
    build_document_plan_profile_preview,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import (
    create_sample_v1_alignment,
    find_v1_alignment,
)
from freecad.Corridor_Road.v1.objects.obj_profile import (
    build_v1_profile_shape,
    create_sample_v1_profile,
    find_v1_profile,
    to_profile_model,
)


def _new_project_doc():
    doc = App.newDocument("CRV1ProfileSourceContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


def test_create_sample_v1_profile_builds_profile_model_contract() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)
        model = to_profile_model(profile)

        assert profile.V1ObjectType == "V1Profile"
        assert model is not None
        assert model.profile_id == profile.ProfileId
        assert model.alignment_id == alignment.AlignmentId
        assert len(model.control_rows) == 3
        assert len(model.vertical_curve_rows) == 1
    finally:
        App.closeDocument(doc.Name)


def test_v1_profile_builds_3d_display_shape_from_alignment_and_profile() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        doc.recompute()
        shape = getattr(profile, "Shape", None)

        assert shape is not None
        assert not shape.isNull()
        assert str(getattr(profile, "DisplayStatus", "") or "") == "ok"
        assert int(getattr(profile, "DisplayPointCount", 0) or 0) >= 2
        assert build_v1_profile_shape(profile) is not None
    finally:
        App.closeDocument(doc.Name)


def test_create_v1_sample_profile_routes_profile_and_creates_alignment_if_missing() -> None:
    doc, project = _new_project_doc()
    try:
        profile = create_v1_sample_profile(document=doc, project=project)
        alignment = find_v1_alignment(doc)
        tree = ensure_project_tree(project, include_references=False)

        assert alignment is not None
        assert find_v1_profile(doc) == profile
        assert alignment.Name in _group_names(tree[V1_TREE_ALIGNMENTS])
        assert profile.Name in _group_names(tree[V1_TREE_PROFILES])
        assert profile.AlignmentId == alignment.AlignmentId
    finally:
        App.closeDocument(doc.Name)


def test_plan_profile_preview_prefers_v1_alignment_and_profile_sources() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        preview = build_document_plan_profile_preview(doc)

        assert preview is not None
        assert preview["preview_source_kind"] == "document"
        assert preview["alignment_model"].alignment_id == alignment.AlignmentId
        assert preview["profile_model"].profile_id == profile.ProfileId
        assert preview["profile_model"].alignment_id == alignment.AlignmentId
        assert preview["legacy_objects"]["alignment"] == alignment
        assert preview["legacy_objects"]["profile"] == profile
        assert preview["profile_output"].profile_output_id == profile.ProfileId
        assert any(
            row["kind"] == "alignment_profile_link" and row["status"] == "ok"
            for row in preview["bridge_diagnostic_rows"]
        )
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile source object contract tests completed.")
