from pathlib import Path

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
    V1_TREE_EXISTING_GROUND_TIN_RESULT,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.exchange.landxml_import import scan_landxml_file
from freecad.Corridor_Road.v1.exchange.landxml_surface_mapper import (
    create_or_update_surface_from_landxml_candidate,
    surface_model_from_landxml_tin,
    tin_surface_from_landxml_candidate,
)
from freecad.Corridor_Road.v1.objects.obj_surface import to_surface_model


SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def _new_project_doc():
    doc = App.newDocument("CRV1LandXMLSurfaceMapper")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "Parametric Road Project"
    return doc, project


def test_landxml_surface_candidate_maps_to_tin_surface_and_surface_model() -> None:
    result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")

    tin = tin_surface_from_landxml_candidate(result.surfaces[0], project_id="test-project")
    model = surface_model_from_landxml_tin(tin, project_id="test-project")

    assert tin.project_id == "test-project"
    assert tin.surface_id == "tin:Existing-Ground"
    assert tin.surface_kind == "existing_ground_tin"
    assert len(tin.vertex_rows) == 3
    assert len(tin.triangle_rows) == 1
    assert tin.triangle_rows[0].v1 == "1"
    assert model.surface_model_id == "surface-model:tin:Existing-Ground"
    assert model.surface_rows[0].tin_ref == "tin:Existing-Ground"
    assert model.build_relation_rows[0].relation_kind == "landxml_import"


def test_create_or_update_surface_from_landxml_candidate_routes_result_and_preview() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")

        imported = create_or_update_surface_from_landxml_candidate(doc, result.surfaces[0], project=project)

        obj = imported.surface_model_object
        assert obj.CRRecordKind == "tin_surface_result"
        assert obj.SurfaceModelId == "surface-model:tin:Existing-Ground"
        assert obj.SurfaceCount == 1
        assert obj.Name in _group_names(tree[V1_TREE_EXISTING_GROUND_TIN_RESULT])
        model = to_surface_model(obj)
        assert model is not None
        assert model.surface_rows[0].surface_kind == "existing_ground_tin"
        assert model.surface_rows[0].status == "ready"
        assert imported.preview_result.status in {"created", "updated"}
        preview = doc.getObject(imported.preview_result.object_name)
        assert preview is not None
        assert preview.Name in _group_names(tree[V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW])
        assert preview.SurfaceId == "tin:Existing-Ground"
        assert int(getattr(preview.Mesh, "CountFacets", 0) or 0) == 1

        updated = create_or_update_surface_from_landxml_candidate(doc, result.surfaces[0], project=project)
        assert updated.surface_model_object is obj
        assert updated.preview_result.status == "updated"
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] LandXML surface mapper tests completed.")
