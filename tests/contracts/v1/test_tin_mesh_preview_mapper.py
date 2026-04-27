import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
    CorridorRoadProject,
    ensure_project_tree,
    route_to_v1_tree,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINSurface,
    TINTriangle,
    TINVertex,
)
from freecad.Corridor_Road.v1.models.source import TINEditOperation
from freecad.Corridor_Road.v1.services.editing import TINEditService
from freecad.Corridor_Road.v1.services.mapping import TINMeshPreviewMapper


def _small_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:mesh-preview",
        label="Mesh Preview Test",
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


def test_build_facet_rows_uses_tin_triangles() -> None:
    facets = TINMeshPreviewMapper().build_facet_rows(_small_surface())

    assert len(facets) == 2
    assert facets[0][0] == (0.0, 0.0, 10.0)
    assert facets[0][1] == (10.0, 0.0, 12.0)
    assert facets[0][2] == (10.0, 10.0, 16.0)


def test_build_mesh_has_matching_facet_count() -> None:
    mesh = TINMeshPreviewMapper().build_mesh(
        _small_surface(),
        mesh_module=Mesh,
        app_module=App,
    )

    assert int(getattr(mesh, "CountFacets", 0) or 0) == 2


def test_create_preview_object_adds_mesh_feature_to_document() -> None:
    doc = App.newDocument("TINMeshPreviewMapperTest")
    try:
        result = TINMeshPreviewMapper().create_preview_object(
            doc,
            _small_surface(),
            mesh_module=Mesh,
            app_module=App,
        )

        assert result.status == "created"
        assert result.facet_count == 2
        obj = doc.getObject(result.object_name)
        assert obj is not None
        assert int(getattr(obj.Mesh, "CountFacets", 0) or 0) == 2
    finally:
        App.closeDocument(doc.Name)


def test_create_preview_object_skips_without_document() -> None:
    result = TINMeshPreviewMapper().create_preview_object(None, _small_surface())

    assert result.status == "skipped"
    assert result.facet_count == 0


def test_create_or_update_preview_object_reuses_edited_tin_mesh() -> None:
    doc = App.newDocument("TINMeshPreviewMapperUpdateTest")
    try:
        edited = TINEditService().apply_operations(
            _small_surface(),
            [
                TINEditOperation(
                    "op:delete",
                    "delete_triangles",
                    parameters={"triangle_ids": ["t1"]},
                )
            ],
        ).surface
        mapper = TINMeshPreviewMapper()

        created = mapper.create_or_update_preview_object(
            doc,
            edited,
            object_name="TINPreview_Edited_Test",
            label_prefix="TIN Edited Preview",
            surface_role="edited",
            mesh_module=Mesh,
            app_module=App,
        )
        updated = mapper.create_or_update_preview_object(
            doc,
            edited,
            object_name="TINPreview_Edited_Test",
            label_prefix="TIN Edited Preview",
            surface_role="edited",
            mesh_module=Mesh,
            app_module=App,
        )

        obj = doc.getObject(created.object_name)
        assert created.status == "created"
        assert updated.status == "updated"
        assert created.object_name == updated.object_name
        assert obj is not None
        assert obj.SurfaceRole == "edited"
        assert obj.SurfaceId == "tin:mesh-preview:edited"
        assert obj.CRRecordKind == "tin_mesh_preview"
        assert obj.TriangleCount == 1
        assert int(getattr(obj.Mesh, "CountFacets", 0) or 0) == 1
    finally:
        App.closeDocument(doc.Name)


def test_edited_tin_preview_routes_to_existing_ground_mesh_preview_tree() -> None:
    doc = App.newDocument("TINMeshPreviewMapperTreeRouteTest")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)
        edited = TINEditService().apply_operations(
            _small_surface(),
            [
                TINEditOperation(
                    "op:delete",
                    "delete_triangles",
                    parameters={"triangle_ids": ["t1"]},
                )
            ],
        ).surface

        result = TINMeshPreviewMapper().create_or_update_preview_object(
            doc,
            edited,
            object_name="TINPreview_Edited_Route_Test",
            surface_role="edited",
            mesh_module=Mesh,
            app_module=App,
        )
        obj = doc.getObject(result.object_name)
        folder = route_to_v1_tree(project, obj)

        assert folder == tree[V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW]
        assert result.object_name in {
            str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])
        }
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN mesh preview mapper contract tests completed.")
