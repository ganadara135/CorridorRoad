from pathlib import Path

import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_review_tin import (
    build_csv_tin_review,
    build_demo_tin_review,
    format_tin_review,
    _focus_tin_preview_object,
    show_v1_tin_review,
)
from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS,
    V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
    V1_TREE_EXISTING_GROUND_TIN_RESULT,
    V1_TREE_EXISTING_GROUND_TIN_SOURCE,
    V1_TREE_EXISTING_REFERENCES,
    V1_TREE_SURVEY_POINTS,
    CorridorRoadProject,
    ensure_project_tree,
)


SAMPLE_PATH = Path("tests/samples/pointcloud_utm_realistic_hilly.csv")


class _FakeSelection:
    def __init__(self):
        self.selected = []
        self.cleared = False

    def clearSelection(self):
        self.cleared = True
        self.selected = []

    def addSelection(self, obj):
        self.selected.append(obj)


class _FakeView:
    def __init__(self):
        self.isometric = False
        self.fit_selection = False

    def viewIsometric(self):
        self.isometric = True

    def fitSelection(self):
        self.fit_selection = True


class _FakeActiveDocument:
    def __init__(self):
        self.ActiveView = _FakeView()


class _FakeGui:
    def __init__(self):
        self.Selection = _FakeSelection()
        self.ActiveDocument = _FakeActiveDocument()


def test_build_demo_tin_review_returns_surface_and_probe_result() -> None:
    preview = build_demo_tin_review("Demo TIN")

    surface = preview["tin_surface"]
    result = preview["sample_result"]

    assert surface.label == "Demo TIN"
    assert len(surface.vertex_rows) == 4
    assert len(surface.triangle_rows) == 2
    assert result.found is True
    assert result.status == "ok"


def test_format_tin_review_includes_core_summary() -> None:
    text = format_tin_review(build_demo_tin_review())

    assert "CorridorRoad v1 TIN Review" in text
    assert "Vertices: 4" in text
    assert "Triangles: 2" in text
    assert "Extents X: 0.000 -> 10.000" in text
    assert "Extents Y: 0.000 -> 10.000" in text
    assert "Probe extent: inside_extent" in text
    assert "Probe result: hit" in text


def test_show_v1_tin_review_returns_preview_without_gui() -> None:
    preview = show_v1_tin_review(document=None, app_module=None, gui_module=None)

    assert preview["tin_surface"] is not None
    assert preview["sample_result"].found is True
    assert "summary_text" in preview


def test_show_v1_tin_review_accepts_probe_context() -> None:
    preview = show_v1_tin_review(
        document=None,
        extra_context={"probe_x": 50.0, "probe_y": 50.0},
        app_module=None,
        gui_module=None,
    )

    assert preview["probe"]["x"] == 50.0
    assert preview["sample_result"].found is False
    assert preview["sample_result"].status == "no_hit"
    assert preview["probe_extent_status"] == "outside_extent"
    assert "outside the TIN extents" in preview["probe_guidance"]
    assert "Probe guidance:" in preview["summary_text"]


def test_build_csv_tin_review_uses_realistic_sample() -> None:
    preview = build_csv_tin_review(
        str(SAMPLE_PATH),
        surface_id="tin:sample-hilly",
        probe_x=352000.0,
        probe_y=4169000.0,
    )

    surface = preview["tin_surface"]
    result = preview["sample_result"]

    assert len(surface.vertex_rows) == 14641
    assert len(surface.triangle_rows) == 28800
    assert preview["tin_source"].endswith("pointcloud_utm_realistic_hilly.csv")
    assert preview["tin_extent"]["x_min"] == 352000.0
    assert preview["tin_extent"]["x_max"] == 352600.0
    assert preview["tin_extent"]["y_min"] == 4169000.0
    assert preview["tin_extent"]["y_max"] == 4169600.0
    assert preview["tin_extent"]["x_spacing"] == 5.0
    assert preview["tin_extent"]["y_spacing"] == 5.0
    assert preview["probe_extent_status"] == "inside_extent"
    assert result.found is True
    assert abs(float(result.z or 0.0) - 116.0) < 1e-9


def test_show_v1_tin_review_accepts_csv_context() -> None:
    preview = show_v1_tin_review(
        document=None,
        extra_context={
            "csv_path": str(SAMPLE_PATH),
            "surface_id": "tin:sample-hilly",
            "probe_x": 352000.0,
            "probe_y": 4169000.0,
        },
        app_module=None,
        gui_module=None,
    )

    assert len(preview["tin_surface"].triangle_rows) == 28800
    assert preview["sample_result"].found is True
    assert "Source: tests" in preview["summary_text"]
    assert "Extents X: 352000.000 -> 352600.000" in preview["summary_text"]
    assert "Spacing X/Y: 5.000 / 5.000" in preview["summary_text"]


def test_show_v1_tin_review_creates_mesh_preview_when_document_is_available() -> None:
    doc = App.newDocument("TINReviewMeshPreviewTest")
    try:
        preview = show_v1_tin_review(
            document=doc,
            extra_context={"create_mesh_preview": True},
            app_module=None,
            gui_module=None,
        )

        mesh_preview = preview["mesh_preview"]
        assert mesh_preview.status == "created"
        assert mesh_preview.facet_count == len(preview["tin_surface"].triangle_rows)
        assert doc.getObject(mesh_preview.object_name) is not None
        assert "Mesh preview: created" in preview["summary_text"]
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_tin_review_routes_mesh_preview_to_v1_tree_when_project_exists() -> None:
    doc = App.newDocument("TINReviewMeshPreviewTreeRouteTest")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)

        preview = show_v1_tin_review(
            document=doc,
            extra_context={"create_mesh_preview": True},
            app_module=None,
            gui_module=None,
        )

        mesh_preview = preview["mesh_preview"]
        folder = tree[V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW]
        names = {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}
        existing_reference_names = _group_names(tree[V1_TREE_EXISTING_REFERENCES])
        assert mesh_preview.object_name in names
        assert mesh_preview.object_name not in existing_reference_names
    finally:
        App.closeDocument(doc.Name)


def test_focus_tin_preview_selects_and_centers_mesh_preview() -> None:
    doc = App.newDocument("TINReviewFocusPreviewTest")
    try:
        preview = show_v1_tin_review(
            document=doc,
            extra_context={"create_mesh_preview": True},
            app_module=None,
            gui_module=None,
        )
        gui = _FakeGui()

        focused = _focus_tin_preview_object(doc, preview, gui_module=gui)

        assert focused is True
        assert gui.Selection.cleared is True
        assert len(gui.Selection.selected) == 1
        assert gui.ActiveDocument.ActiveView.isometric is True
        assert gui.ActiveDocument.ActiveView.fit_selection is True
    finally:
        App.closeDocument(doc.Name)


def test_show_v1_tin_review_routes_source_result_and_diagnostics_records_to_v1_tree() -> None:
    doc = App.newDocument("TINReviewTreeRecordRouteTest")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)

        preview = show_v1_tin_review(
            document=doc,
            extra_context={
                "csv_path": str(SAMPLE_PATH),
                "surface_id": "tin:sample-hilly",
                "create_mesh_preview": False,
            },
            app_module=None,
            gui_module=None,
        )

        records = preview["tree_records"]
        source_obj = doc.getObject(records["source"])
        surface_source_obj = doc.getObject(records["surface_source"])
        result_obj = doc.getObject(records["result"])
        diagnostics_obj = doc.getObject(records["diagnostics"])

        assert source_obj is not None
        assert surface_source_obj is not None
        assert result_obj is not None
        assert diagnostics_obj is not None
        assert source_obj.SourcePath.endswith("pointcloud_utm_realistic_hilly.csv")
        assert surface_source_obj.SourceRecordName == records["source"]
        assert result_obj.SurfaceId == "tin:sample-hilly"
        assert result_obj.VertexCount == 14641
        assert result_obj.TriangleCount == 28800
        assert diagnostics_obj.ProbeExtentStatus == "inside_extent"
        assert abs(float(diagnostics_obj.XMin) - 352000.0) < 1e-9

        assert records["source"] in _group_names(tree[V1_TREE_SURVEY_POINTS])
        assert records["surface_source"] in _group_names(tree[V1_TREE_EXISTING_GROUND_TIN_SOURCE])
        assert records["result"] in _group_names(tree[V1_TREE_EXISTING_GROUND_TIN_RESULT])
        assert records["diagnostics"] in _group_names(tree[V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS])
        existing_reference_names = _group_names(tree[V1_TREE_EXISTING_REFERENCES])
        assert records["surface_source"] not in existing_reference_names
        assert records["result"] not in existing_reference_names
        assert records["diagnostics"] not in existing_reference_names
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 TIN review contract tests completed.")
