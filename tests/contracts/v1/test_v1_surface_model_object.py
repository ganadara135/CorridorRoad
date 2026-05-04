import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_DESIGN_TIN,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.result.surface_model import SurfaceBuildRelation, SurfaceModel, SurfaceRow, SurfaceSpanRow
from freecad.Corridor_Road.v1.objects.obj_surface import (
    create_or_update_v1_surface_model_object,
    find_v1_surface_model,
    to_surface_model,
)


def _new_project_doc():
    doc = App.newDocument("V1SurfaceModelObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_surface() -> SurfaceModel:
    return SurfaceModel(
        schema_version=1,
        project_id="proj-1",
        surface_model_id="surface:main",
        corridor_id="corridor:main",
        surface_rows=[
            SurfaceRow("corridor:main:design", "design_surface", "corridor:main:design:tin"),
            SurfaceRow("corridor:main:subgrade", "subgrade_surface", "corridor:main:subgrade:tin", parent_surface_ref="corridor:main:design"),
        ],
        build_relation_rows=[
            SurfaceBuildRelation(
                "surface:main:design-build",
                "corridor:main:design",
                "corridor_build",
                input_refs=["corridor:main", "sections:main"],
                operation_summary="Built from applied sections.",
            )
        ],
        span_rows=[
            SurfaceSpanRow(
                "span:design:1",
                "corridor:main:design",
                0.0,
                10.0,
                from_region_ref="region-a",
                to_region_ref="region-b",
                span_kind="region_boundary",
                continuity_status="needs_review",
                diagnostic_refs=["region_context_change"],
                notes="design span crosses Region boundary.",
            )
        ],
        source_refs=["corridor:main", "sections:main"],
    )


def test_create_or_update_v1_surface_model_routes_to_design_tin_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_surface_model_object(document=doc, project=project, surface_model=_sample_surface())

        assert obj.V1ObjectType == "V1SurfaceModel"
        assert obj.CRRecordKind == "v1_surface_model"
        assert obj.SurfaceModelId == "surface:main"
        assert obj.SurfaceCount == 2
        assert obj.Name in _group_names(tree[V1_TREE_DESIGN_TIN])
    finally:
        App.closeDocument(doc.Name)


def test_v1_surface_model_roundtrips_summary_rows() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_surface_model_object(document=doc, project=project, surface_model=_sample_surface())

        model = to_surface_model(obj)

        assert model is not None
        assert model.surface_model_id == "surface:main"
        assert model.corridor_id == "corridor:main"
        assert [row.surface_kind for row in model.surface_rows] == ["design_surface", "subgrade_surface"]
        assert model.build_relation_rows[0].input_refs == ["corridor:main", "sections:main"]
        assert model.span_rows[0].span_kind == "region_boundary"
        assert model.span_rows[0].from_region_ref == "region-a"
        assert model.span_rows[0].to_region_ref == "region-b"
        assert model.span_rows[0].diagnostic_refs == ["region_context_change"]
        assert find_v1_surface_model(doc) == obj
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 surface model object contract tests completed.")
