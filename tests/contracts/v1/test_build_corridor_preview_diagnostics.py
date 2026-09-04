"""Contract tests for Build Parametric preview failure diagnostics.

A preview failure must not abort a Build Parametric run, but it must also not
present itself as a successful empty preview. These tests pin the marker that
makes such a fallback visible and traceable on the document object.
"""

from freecad.Corridor_Road.v1.commands.cmd_build_corridor import _mark_preview_shape_failure


class _FakePreviewObject:
    """Minimal stand-in for a FreeCAD document object with dynamic properties."""

    def __init__(self) -> None:
        self.added_properties: list[tuple[str, str]] = []

    def addProperty(self, property_type: str, name: str, group: str, documentation: str) -> None:
        self.added_properties.append((property_type, name))
        setattr(self, name, "")


def test_preview_shape_failure_marks_status_and_diagnostic() -> None:
    obj = _FakePreviewObject()
    error = ValueError("compound build failed")

    result = _mark_preview_shape_failure(
        obj,
        preview_kind="create_drainage_flow_review_highlight",
        error=error,
    )

    assert result is obj
    assert obj.PreviewShapeStatus == "shape_build_failed"
    assert "create_drainage_flow_review_highlight" in obj.PreviewShapeDiagnostic
    assert "ValueError" in obj.PreviewShapeDiagnostic
    assert "compound build failed" in obj.PreviewShapeDiagnostic


def test_preview_shape_failure_declares_both_properties_as_strings() -> None:
    obj = _FakePreviewObject()

    _mark_preview_shape_failure(obj, preview_kind="kind", error=RuntimeError("boom"))

    assert ("App::PropertyString", "PreviewShapeStatus") in obj.added_properties
    assert ("App::PropertyString", "PreviewShapeDiagnostic") in obj.added_properties


def test_preview_shape_failure_diagnostic_stays_bounded() -> None:
    obj = _FakePreviewObject()

    _mark_preview_shape_failure(obj, preview_kind="kind", error=RuntimeError("x" * 5000))

    # The message is truncated so a runaway kernel error cannot fill a document
    # property with an unbounded string.
    assert len(obj.PreviewShapeDiagnostic) < 400


def test_preview_shape_failure_tolerates_an_object_without_properties() -> None:
    # Property writes are best-effort in the preview adapter. A restored or
    # partially constructed object must not turn a preview failure into a
    # second, louder failure.
    class _Inert:
        def addProperty(self, *args, **kwargs):
            raise RuntimeError("property store unavailable")

    obj = _Inert()

    assert _mark_preview_shape_failure(obj, preview_kind="kind", error=ValueError("x")) is obj
