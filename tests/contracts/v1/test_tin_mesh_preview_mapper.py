import FreeCAD as App
import Mesh

from freecad.Corridor_Road.v1.models.result.tin_surface import (
    TINSurface,
    TINTriangle,
    TINVertex,
)
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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN mesh preview mapper contract tests completed.")
