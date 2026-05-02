from freecad.Corridor_Road.v1.models.result.tin_surface import TINSurface, TINTriangle, TINVertex
from freecad.Corridor_Road.v1.models.source import TINEditOperation
from freecad.Corridor_Road.v1.services.editing import TINEditService
from freecad.Corridor_Road.v1.services.evaluation import TinSamplingService


def _grid_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:grid",
        label="Grid TIN",
        vertex_rows=[
            TINVertex("v00", 0.0, 0.0, 0.0),
            TINVertex("v10", 10.0, 0.0, 10.0),
            TINVertex("v20", 20.0, 0.0, 20.0),
            TINVertex("v01", 0.0, 10.0, 10.0),
            TINVertex("v11", 10.0, 10.0, 20.0),
            TINVertex("v21", 20.0, 10.0, 30.0),
            TINVertex("v02", 0.0, 20.0, 20.0),
            TINVertex("v12", 10.0, 20.0, 30.0),
            TINVertex("v22", 20.0, 20.0, 40.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v00", "v10", "v11"),
            TINTriangle("t1", "v00", "v11", "v01"),
            TINTriangle("t2", "v10", "v20", "v21"),
            TINTriangle("t3", "v10", "v21", "v11"),
            TINTriangle("t4", "v01", "v11", "v12"),
            TINTriangle("t5", "v01", "v12", "v02"),
            TINTriangle("t6", "v11", "v21", "v22"),
            TINTriangle("t7", "v11", "v22", "v12"),
        ],
    )


def test_boundary_clip_rect_creates_edited_surface_without_mutating_base() -> None:
    base = _grid_surface()
    result = TINEditService().apply_operations(
        base,
        [
            TINEditOperation(
                "op:boundary",
                "boundary_clip_rect",
                parameters={"min_x": 0.0, "max_x": 12.0, "min_y": 0.0, "max_y": 12.0},
            )
        ],
    )

    assert result.status == "ok"
    assert result.surface.surface_id == "tin:grid:edited"
    assert len(base.triangle_rows) == 8
    assert len(result.surface.triangle_rows) == 2
    assert result.removed_triangle_count == 6
    assert "op:boundary" in result.surface.boundary_refs
    assert "tin:grid" in result.surface.source_refs


def test_void_clip_rect_removes_triangles_inside_exclusion_area() -> None:
    result = TINEditService().apply_operations(
        _grid_surface(),
        [
            TINEditOperation(
                "op:void",
                "void_clip_rect",
                parameters={"min_x": 0.0, "max_x": 12.0, "min_y": 0.0, "max_y": 12.0},
            )
        ],
    )

    assert len(result.surface.triangle_rows) == 6
    assert result.removed_triangle_count == 2
    assert "op:void" in result.surface.void_refs


def test_delete_triangles_removes_named_faces_and_prunes_orphan_vertices() -> None:
    result = TINEditService().apply_operations(
        _grid_surface(),
        [
            TINEditOperation(
                "op:delete",
                "delete_triangles",
                parameters={"triangle_ids": ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]},
            )
        ],
    )

    assert [triangle.triangle_id for triangle in result.surface.triangle_rows] == ["t7"]
    assert sorted(vertex.vertex_id for vertex in result.surface.vertex_rows) == ["v11", "v12", "v22"]


def test_delete_triangles_accepts_range_tokens() -> None:
    result = TINEditService().apply_operations(
        _grid_surface(),
        [
            TINEditOperation(
                "op:delete-range",
                "delete_triangles",
                parameters={"triangle_ids": "t1-t3;t5"},
            )
        ],
    )

    assert [triangle.triangle_id for triangle in result.surface.triangle_rows] == ["t0", "t4", "t6", "t7"]
    assert result.removed_triangle_count == 4


def test_override_vertex_elevation_changes_sampling_on_edited_surface_only() -> None:
    base = _grid_surface()
    result = TINEditService().apply_operations(
        base,
        [
            TINEditOperation(
                "op:z",
                "override_vertex_elevation",
                parameters={"vertex_id": "v11", "new_z": 120.0},
            )
        ],
    )

    base_sample = TinSamplingService().sample_xy(surface=base, x=7.5, y=7.5)
    edited_sample = TinSamplingService().sample_xy(surface=result.surface, x=7.5, y=7.5)

    assert result.changed_vertex_count == 1
    assert base.vertex_map()["v11"].z == 20.0
    assert result.surface.vertex_map()["v11"].z == 120.0
    assert base_sample.found is True
    assert edited_sample.found is True
    assert float(edited_sample.z or 0.0) > float(base_sample.z or 0.0)


def test_override_vertex_elevation_accepts_multiple_rows() -> None:
    result = TINEditService().apply_operations(
        _grid_surface(),
        [
            TINEditOperation(
                "op:z-multi",
                "override_vertex_elevation",
                parameters={
                    "vertices": [
                        {"vertex_id": "v00", "new_z": 11.0},
                        {"vertex_id": "v22", "new_z": 99.0},
                    ]
                },
            )
        ],
    )

    vertices = result.surface.vertex_map()
    assert result.changed_vertex_count == 2
    assert vertices["v00"].z == 11.0
    assert vertices["v22"].z == 99.0


def test_apply_operations_accepts_dict_operations() -> None:
    result = TINEditService().apply_operations(
        _grid_surface(),
        [
            {
                "operation_id": "op:dict-delete",
                "kind": "delete_triangles",
                "parameters": {"triangle_ids": "t0,t1"},
            }
        ],
    )

    assert len(result.surface.triangle_rows) == 6
    assert result.operation_reports[0].operation_id == "op:dict-delete"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN edit service contract tests completed.")
