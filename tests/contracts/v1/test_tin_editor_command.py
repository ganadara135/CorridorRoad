import FreeCAD as App
import Mesh

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS,
    V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
    V1_TREE_EXISTING_GROUND_TIN_RESULT,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.commands import cmd_edit_tin
from freecad.Corridor_Road.v1.commands.cmd_edit_tin import (
    CmdV1TINEditor,
    V1TINEditorTaskPanel,
    _TINFacePickObserver,
    _rect_from_xy_points,
    _remove_rect_previews,
    apply_tin_editor_operations,
    build_tin_source_from_csv,
    nearest_tin_vertex,
    run_v1_tin_editor_command,
    triangle_ids_from_object_info,
    triangle_ids_from_selected_faces,
    triangle_ids_from_view_event,
    triangle_ids_from_view_xy,
)
from freecad.Corridor_Road.v1.models.result.tin_surface import TINSurface, TINTriangle, TINVertex
from freecad.Corridor_Road.v1.models.source import TINEditOperation
from freecad.Corridor_Road.v1.services.mapping import TINMeshPreviewMapper


SAMPLE_PATH = r"tests\samples\pointcloud_utm_realistic_hilly.csv"


class _Selection:
    def __init__(self, objects):
        self._objects = list(objects or [])

    def getSelection(self):
        return list(self._objects)


class _Gui:
    def __init__(self, objects):
        self.Selection = _Selection(objects)


class _SelectionEx:
    def __init__(self, obj, names):
        self.Object = obj
        self.SubElementNames = list(names or [])


class _FaceSelection:
    def __init__(self, selections):
        self._selections = list(selections or [])

    def getSelectionEx(self, *args):
        return list(self._selections)


class _FaceGui:
    def __init__(self, selections):
        self.Selection = _FaceSelection(selections)


class _FakeView:
    def __init__(self, info, point=None):
        self.info = dict(info or {})
        self.point = point
        self.callback = None

    def getObjectInfo(self, *args):
        return dict(self.info)

    def getPoint(self, *args):
        return self.point

    def addEventCallback(self, event_name, callback):
        self.callback = (event_name, callback)
        return "callback-id"

    def removeEventCallback(self, event_name, callback_id):
        self.callback = None


class _FakeActiveDocument:
    def __init__(self, view):
        self.ActiveView = view


class _ViewGui:
    def __init__(self, info, point=None):
        self.ActiveDocument = _FakeActiveDocument(_FakeView(info, point=point))


class _Point:
    def __init__(self, x, y, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)


class _PickPanel:
    def __init__(self):
        self.events = []

    def _handle_triangle_pick_event(self, *args):
        self.events.append(args)


def _small_surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:editor-base",
        label="TIN Base",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 0.0),
            TINVertex("v1", 10.0, 0.0, 10.0),
            TINVertex("v2", 10.0, 10.0, 20.0),
            TINVertex("v3", 0.0, 10.0, 10.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
            TINTriangle("t1", "v0", "v2", "v3"),
        ],
    )


def _new_project_doc():
    doc = App.newDocument("TINEditorCommandTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def test_apply_tin_editor_operations_creates_edited_preview_and_routes_to_tree() -> None:
    doc, _project, tree = _new_project_doc()
    try:
        result = apply_tin_editor_operations(
            document=doc,
            base_surface=_small_surface(),
            operations=[
                TINEditOperation(
                    "op:delete",
                    "delete_triangles",
                    parameters={"triangle_ids": ["t1"]},
                )
            ],
            mesh_module=Mesh,
            app_module=App,
        )

        preview = result["mesh_preview"]
        obj = doc.getObject(preview.object_name)
        preview_folder = tree[V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW]
        result_folder = tree[V1_TREE_EXISTING_GROUND_TIN_RESULT]
        diagnostics_folder = tree[V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS]
        preview_names = _group_names(preview_folder)
        result_names = _group_names(result_folder)
        diagnostics_names = _group_names(diagnostics_folder)
        edited_result = doc.getObject(result["tree_records"]["edited_result"])
        edit_diagnostics = doc.getObject(result["tree_records"]["edit_diagnostics"])
        assert preview.status == "created"
        assert result["edit_result"].removed_triangle_count == 1
        assert obj is not None
        assert obj.SurfaceRole == "edited"
        assert obj.SurfaceId == "tin:editor-base:edited"
        assert int(getattr(obj.Mesh, "CountFacets", 0) or 0) == 1
        assert preview.object_name in preview_names
        assert edited_result is not None
        assert edited_result.SurfaceRole == "edited"
        assert edited_result.SurfaceId == "tin:editor-base:edited"
        assert edited_result.SourceSurfaceId == "tin:editor-base"
        assert edited_result.TriangleCount == 1
        assert edited_result.RemovedTriangleCount == 1
        assert edit_diagnostics is not None
        assert edit_diagnostics.SurfaceRole == "edited"
        assert "op:delete" in edit_diagnostics.OperationSummary
        assert edited_result.Name in result_names
        assert edit_diagnostics.Name in diagnostics_names
    finally:
        App.closeDocument(doc.Name)


def test_build_tin_source_from_csv_creates_base_preview_for_editor_source_tab() -> None:
    doc, _project, tree = _new_project_doc()
    try:
        result = build_tin_source_from_csv(
            document=doc,
            csv_path=SAMPLE_PATH,
            app_module=App,
        )

        surface = result["tin_surface"]
        preview = result["mesh_preview"]
        source_obj = result["source_obj"]
        preview_names = _group_names(tree[V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW])
        assert surface.surface_id == "tin:pointcloud_utm_realistic_hilly"
        assert len(surface.vertex_rows) == 14641
        assert len(surface.triangle_rows) == 28800
        assert preview.status == "created"
        assert source_obj is not None
        assert source_obj.SurfaceRole == "base"
        assert source_obj.SourceCoords == "Local"
        assert source_obj.ModelCoords == "Local"
        assert preview.object_name in preview_names
    finally:
        App.closeDocument(doc.Name)


def test_tin_editor_uses_apply_as_single_write_button() -> None:
    doc, _project, _tree = _new_project_doc()
    try:
        panel = V1TINEditorTaskPanel(document=doc, base_surface=_small_surface(), gui_module=None)
        buttons = [button.text() for button in panel.form.findChildren(QtWidgets.QPushButton)]

        assert buttons.count("Apply") == 1
        assert "Build TIN" not in buttons
    finally:
        App.closeDocument(doc.Name)


def test_tin_editor_apply_applies_current_editor_state_without_rebuilding_source() -> None:
    doc, _project, _tree = _new_project_doc()
    original_show_message = cmd_edit_tin._show_message
    cmd_edit_tin._show_message = lambda *args, **kwargs: None
    try:
        panel = V1TINEditorTaskPanel(document=doc, base_surface=_small_surface(), gui_module=None)
        panel._triangle_delete_text.setText("t1")

        assert panel._build_tin(close_after=False) is True

        assert panel._last_result is not None
        assert panel._last_result["edit_result"].removed_triangle_count == 1
        assert [triangle.triangle_id for triangle in panel._last_result["edited_surface"].triangle_rows] == ["t0"]
    finally:
        cmd_edit_tin._show_message = original_show_message
        App.closeDocument(doc.Name)


def test_apply_tin_editor_operations_updates_existing_edited_preview() -> None:
    doc, _project, _tree = _new_project_doc()
    try:
        base = _small_surface()
        operation = TINEditOperation("op:delete", "delete_triangles", parameters={"triangle_ids": ["t1"]})

        first = apply_tin_editor_operations(
            document=doc,
            base_surface=base,
            operations=[operation],
            mesh_module=Mesh,
            app_module=App,
        )
        second = apply_tin_editor_operations(
            document=doc,
            base_surface=base,
            operations=[operation],
            mesh_module=Mesh,
            app_module=App,
        )

        assert first["mesh_preview"].status == "created"
        assert second["mesh_preview"].status == "updated"
        assert first["mesh_preview"].object_name == second["mesh_preview"].object_name
    finally:
        App.closeDocument(doc.Name)


def test_apply_tin_editor_operations_boundary_clip_shows_selected_rectangle_only() -> None:
    doc, _project, _tree = _new_project_doc()
    try:
        result = apply_tin_editor_operations(
            document=doc,
            base_surface=_small_surface(),
            operations=[
                TINEditOperation(
                    "op:boundary",
                    "boundary_clip_rect",
                    parameters={"min_x": 0.0, "max_x": 8.0, "min_y": 0.0, "max_y": 5.0},
                )
            ],
            mesh_module=Mesh,
            app_module=App,
        )

        assert [triangle.triangle_id for triangle in result["edited_surface"].triangle_rows] == ["t0"]
        assert result["edit_result"].removed_triangle_count == 1
        assert result["mesh_preview"].facet_count == 1
    finally:
        App.closeDocument(doc.Name)


def test_apply_tin_editor_operations_accepts_multiple_vertex_overrides() -> None:
    doc, _project, _tree = _new_project_doc()
    try:
        result = apply_tin_editor_operations(
            document=doc,
            base_surface=_small_surface(),
            operations=[
                TINEditOperation(
                    "op:z-multi",
                    "override_vertex_elevation",
                    parameters={
                        "vertices": [
                            {"vertex_id": "v1", "new_z": 25.0},
                            {"vertex_id": "v3", "new_z": 30.0},
                        ]
                    },
                )
            ],
            mesh_module=Mesh,
            app_module=App,
        )

        vertices = result["edited_surface"].vertex_map()
        diagnostics = doc.getObject(result["tree_records"]["edit_diagnostics"])
        assert result["edit_result"].changed_vertex_count == 2
        assert vertices["v1"].z == 25.0
        assert vertices["v3"].z == 30.0
        assert diagnostics is not None
        assert diagnostics.ChangedVertexCount == 2
    finally:
        App.closeDocument(doc.Name)


def test_run_v1_tin_editor_command_resolves_selected_tin_preview_surface() -> None:
    doc = App.newDocument("TINEditorResolveSelectedPreviewTest")
    try:
        preview = TINMeshPreviewMapper().create_or_update_preview_object(
            doc,
            _small_surface(),
            object_name="TINPreview_Editor_Base",
            mesh_module=Mesh,
            app_module=App,
        )
        obj = doc.getObject(preview.object_name)

        surface = run_v1_tin_editor_command(document=doc, gui_module=_Gui([obj]))

        assert surface is not None
        assert surface.surface_id == "tin:editor-base"
        assert len(surface.triangle_rows) == 2
    finally:
        App.closeDocument(doc.Name)


def test_triangle_ids_from_selected_faces_maps_freecad_face_names_to_tin_ids() -> None:
    source = object()
    other = object()
    gui = _FaceGui(
        [
            _SelectionEx(source, ["Face1", "Face3"]),
            _SelectionEx(other, ["Face2"]),
            _SelectionEx(source, ["Facet4", "Edge1", "Face3"]),
        ]
    )

    assert triangle_ids_from_selected_faces(gui, source_obj=source) == ["t0", "t2", "t3"]


def test_triangle_ids_from_selected_faces_accepts_mesh_name_variants() -> None:
    source = object()
    gui = _FaceGui(
        [
            _SelectionEx(source, ["Mesh.Facet_1", "Facet0", "TINPreview.Face003"]),
        ]
    )

    assert triangle_ids_from_selected_faces(gui, source_obj=source) == ["t0", "t2"]


def test_triangle_ids_from_selected_faces_falls_back_when_source_wrapper_differs() -> None:
    source = object()
    selected = object()
    gui = _FaceGui([_SelectionEx(selected, ["Face2"])])

    assert triangle_ids_from_selected_faces(gui, source_obj=source) == ["t1"]


def test_triangle_ids_from_object_info_reads_component_face() -> None:
    assert triangle_ids_from_object_info({"Component": "Face5"}) == ["t4"]
    assert triangle_ids_from_object_info({"Component": "Facet_2"}) == ["t1"]


def test_triangle_ids_from_view_event_reads_clicked_component() -> None:
    gui = _ViewGui({"Component": "Face6"})
    event = {"State": "DOWN", "Button": "BUTTON1", "Position": (20, 30)}

    assert triangle_ids_from_view_event(gui, event) == ["t5"]


def test_triangle_ids_from_view_event_falls_back_to_tin_xy_sampling() -> None:
    gui = _ViewGui({}, point=_Point(7.5, 7.5))
    event = {"State": "DOWN", "Button": "BUTTON1", "Position": (20, 30)}

    assert triangle_ids_from_view_event(gui, event, surface=_small_surface()) == ["t0"]
    assert triangle_ids_from_view_xy(gui, event, surface=_small_surface()) == ["t0"]


def test_nearest_tin_vertex_resolves_vertex_id_from_xy_pick() -> None:
    picked = nearest_tin_vertex(_small_surface(), 9.8, 0.2)

    assert picked["vertex_id"] == "v1"
    assert picked["z"] == 10.0
    assert picked["distance"] < 0.3


def test_rect_from_xy_points_normalizes_two_boundary_corners() -> None:
    assert _rect_from_xy_points((10.0, 5.0), (2.0, 20.0)) == {
        "min_x": 2.0,
        "max_x": 10.0,
        "min_y": 5.0,
        "max_y": 20.0,
    }


def test_remove_rect_previews_removes_duplicate_boundary_preview_objects() -> None:
    doc = App.newDocument("TINEditorRemoveBoundaryPreviewTest")
    try:
        boundary = doc.addObject("App::FeaturePython", "CRV1_TIN_Boundary_Rectangle_Preview")
        boundary.Label = "TIN Boundary Rectangle Preview"
        boundary.addProperty("App::PropertyString", "CRRecordKind", "CorridorRoad", "")
        boundary.addProperty("App::PropertyString", "PreviewRole", "CorridorRoad", "")
        boundary.CRRecordKind = "tin_edit_rectangle_preview"
        boundary.PreviewRole = "boundary"
        duplicate = doc.addObject("App::FeaturePython", "CRV1_TIN_Boundary_Rectangle_Preview")
        duplicate.Label = "TIN Boundary Rectangle Preview"
        void = doc.addObject("App::FeaturePython", "CRV1_TIN_Void_Rectangle_Preview")
        void.addProperty("App::PropertyString", "CRRecordKind", "CorridorRoad", "")
        void.addProperty("App::PropertyString", "PreviewRole", "CorridorRoad", "")
        void.CRRecordKind = "tin_edit_rectangle_preview"
        void.PreviewRole = "void"

        _remove_rect_previews(doc, role="boundary")

        names = {str(getattr(obj, "Name", "") or "") for obj in list(doc.Objects)}
        assert not any(name.startswith("CRV1_TIN_Boundary_Rectangle_Preview") for name in names)
        assert any(name.startswith("CRV1_TIN_Void_Rectangle_Preview") for name in names)
    finally:
        App.closeDocument(doc.Name)


def test_tin_face_pick_observer_forwards_selection_events_to_panel() -> None:
    panel = _PickPanel()
    observer = _TINFacePickObserver(panel)

    observer.addSelection("Doc", "TINPreview", "Face4", None)
    observer.setSelection("Doc", "TINPreview", "Facet2", None)

    assert panel.events == [
        ("Doc", "TINPreview", "Face4", None),
        ("Doc", "TINPreview", "Facet2", None),
    ]


def test_tin_editor_command_resources_are_registered_as_tin_editor() -> None:
    resources = CmdV1TINEditor().GetResources()

    assert resources["MenuText"] == "TIN"
    assert "TIN" in resources["ToolTip"]


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN editor command contract tests completed.")
