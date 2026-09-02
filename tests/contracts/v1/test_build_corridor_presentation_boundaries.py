from __future__ import annotations

from types import SimpleNamespace

import pytest

from freecad.Corridor_Road.v1.ui.presentation.build_corridor_preview_adapter import (
    BuildCorridorPreviewAdapter,
)
from freecad.Corridor_Road.v1.ui.viewers.build_corridor_view import (
    BuildCorridorViewModel,
)


class _PreviewObject:
    def __init__(self, name: str = "Preview") -> None:
        self.Name = name
        self.ViewObject = SimpleNamespace()
        self.added = []

    def addProperty(self, property_type, name, group, description):
        self.added.append((property_type, name, group, description))


class _Document:
    def __init__(self) -> None:
        self.objects = {}
        self.removed = []

    def getObject(self, name):
        return self.objects.get(name)

    def addObject(self, _kind, name):
        obj = _PreviewObject(name)
        self.objects[name] = obj
        return obj

    def removeObject(self, name):
        self.removed.append(name)
        self.objects.pop(name, None)


class _Part:
    @staticmethod
    def makeLine(start, end):
        return ("line", start, end)

    @staticmethod
    def makeSphere(radius, center):
        return ("sphere", radius, center)

    @staticmethod
    def makeCompound(shapes):
        return ("compound", tuple(shapes))


class _App:
    @staticmethod
    def Vector(x, y, z):
        return (x, y, z)


def test_build_corridor_view_model_owns_progress_and_rows() -> None:
    view_model = BuildCorridorViewModel(document_identity="doc:test")

    view_model.set_progress(125, "Building")
    view_model.replace_rows("results", [{"status": "ready"}])

    assert view_model.progress_value == 100
    assert view_model.progress_text == "Building"
    assert view_model.result_rows == [{"status": "ready"}]
    with pytest.raises(ValueError):
        view_model.replace_rows("unknown", [])


def test_preview_adapter_owns_typed_freecad_properties() -> None:
    obj = _PreviewObject()

    BuildCorridorPreviewAdapter.set_string(obj, "Status", "ready")
    BuildCorridorPreviewAdapter.set_integer(obj, "Count", 3)
    BuildCorridorPreviewAdapter.set_string_list(obj, "Rows", ["a", "b"])
    BuildCorridorPreviewAdapter.set_float(obj, "Area", 4.5)

    assert obj.Status == "ready"
    assert obj.Count == 3
    assert obj.Rows == ["a", "b"]
    assert obj.Area == 4.5
    assert {row[0] for row in obj.added} == {
        "App::PropertyString",
        "App::PropertyInteger",
        "App::PropertyStringList",
        "App::PropertyFloat",
    }


def test_preview_adapter_creates_result_coordinate_marker_only() -> None:
    document = _Document()

    marker = BuildCorridorPreviewAdapter().create_marker_compound(
        document=document,
        object_name="Marker",
        label="Review Marker",
        points=[(0.0, 0.0, 1.0), (2.0, 0.0, 1.0)],
        radius=0.25,
        color=(1.0, 0.0, 0.0),
        surface=SimpleNamespace(surface_id="surface:test"),
        corridor_model=SimpleNamespace(corridor_id="corridor:test"),
        connect_points=True,
        app_module=_App,
        part_module=_Part,
    )

    assert marker is document.objects["Marker"]
    assert marker.MarkerCount == 2
    assert marker.SurfaceId == "surface:test"
    assert marker.CorridorId == "corridor:test"
    assert marker.Shape[0] == "compound"
    assert marker.ViewObject.Visibility is True


def test_preview_adapter_removes_stale_empty_marker() -> None:
    document = _Document()
    document.objects["Marker"] = _PreviewObject("Marker")

    marker = BuildCorridorPreviewAdapter().create_marker_compound(
        document=document,
        object_name="Marker",
        label="Review Marker",
        points=[],
        radius=0.25,
        color=(1.0, 0.0, 0.0),
        surface=None,
        corridor_model=None,
        app_module=_App,
        part_module=_Part,
    )

    assert marker is None
    assert document.removed == ["Marker"]


def test_build_corridor_task_panel_implementation_is_ui_owned() -> None:
    from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
        V1BuildCorridorTaskPanel as CommandPanel,
    )
    from freecad.Corridor_Road.v1.ui.viewers.build_corridor_view import (
        V1BuildCorridorTaskPanel as ViewerPanel,
    )

    assert CommandPanel is ViewerPanel
    assert ViewerPanel.__module__.endswith("ui.viewers.build_corridor_view")
