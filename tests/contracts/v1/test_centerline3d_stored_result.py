"""GR-4: the stored 3D Centerline owns the station frames.

The 3D Centerline command stores its `Centerline3DResult`. Applied Sections read that stored result
and never evaluate their own: a missing, stale or failed 3D Centerline stops the build and says
which, and a station without a frame stops it too instead of taking a frame from elsewhere.
"""

import tempfile
from pathlib import Path

import FreeCAD as App
import pytest

import freecad.Corridor_Road.v1.commands.cmd_centerline3d as centerline_command
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    V1AppliedSectionsTaskPanel,
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_project_setup import create_corridorroad_project
from freecad.Corridor_Road.v1.commands.cmd_rebuild_downstream import rebuild_downstream
from freecad.Corridor_Road.v1.commands.cmd_region_editor import apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.models.source import AlignmentModel, AssemblySubassemblyModel, ProfileModel, RegionModel
from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement
from freecad.Corridor_Road.v1.models.source.assembly_model import SubassemblySectionTemplate, TemplateSubassembly
from freecad.Corridor_Road.v1.models.source.profile_model import ProfileControlPoint
from freecad.Corridor_Road.v1.models.source.region_model import RegionRow
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_centerline3d import find_v1_centerline3d_object, to_centerline3d_result
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile, find_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.services.builders.applied_section_service import (
    AppliedSectionBuildRequest,
    AppliedSectionService,
)

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _source_doc(name: str, *, centerline: bool = True):
    doc = App.newDocument(name)
    project = create_corridorroad_project(doc)
    alignment = create_sample_v1_alignment(doc, project=project)
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    create_v1_stationing(doc, project=project, alignment=alignment, interval=30.0)
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    apply_v1_region_model(
        document=doc,
        project=project,
        region_model=region_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    if centerline:
        show_v1_centerline3d_preview_object(doc, project=project)
    return doc, project


def _raise_profile(doc) -> None:
    profile = find_v1_profile(doc)
    elevations = list(profile.ControlElevations)
    elevations[1] += 1.5
    profile.ControlElevations = elevations


def test_the_3d_centerline_stores_its_result() -> None:
    doc, _project = _source_doc("CRV1StoredCenterline")
    try:
        stored = to_centerline3d_result(find_v1_centerline3d_object(doc))

        assert stored is not None
        assert stored.status == "ready"
        assert stored == centerline_command.build_document_centerline3d_result(doc)

        with tempfile.TemporaryDirectory(prefix="cr_v1_centerline_") as temp_dir:
            path = Path(temp_dir) / "stored_centerline.FCStd"
            doc.saveAs(str(path))
            App.closeDocument(doc.Name)
            doc = None
            reopened = App.openDocument(str(path))
            try:
                assert to_centerline3d_result(find_v1_centerline3d_object(reopened)) == stored
            finally:
                App.closeDocument(reopened.Name)
    finally:
        if doc is not None:
            App.closeDocument(doc.Name)


def test_applied_sections_read_the_stored_result_and_evaluate_none_of_their_own() -> None:
    doc, project = _source_doc("CRV1StoredCenterlineUsed")
    original = centerline_command.build_document_centerline3d_result

    def _refuse(*_args, **_kwargs):
        raise AssertionError("Applied Sections evaluated a 3D Centerline of their own")

    centerline_command.build_document_centerline3d_result = _refuse
    try:
        applied = build_document_applied_section_set(doc, project=project)

        assert applied.sections
        assert all(section.frame.source_mode == "centerline3d_source_geometry" for section in applied.sections)
    finally:
        centerline_command.build_document_centerline3d_result = original
        App.closeDocument(doc.Name)


def test_a_missing_3d_centerline_stops_applied_sections() -> None:
    _ensure_qapp()
    doc, project = _source_doc("CRV1StoredCenterlineMissing", centerline=False)
    try:
        with pytest.raises(RuntimeError, match="3D Centerline, which has not been generated"):
            build_document_applied_section_set(doc, project=project)

        panel = V1AppliedSectionsTaskPanel(document=doc)
        assert panel._validate(show_message=False) is False
        assert "centerline3d_not_usable" in panel._summary.toPlainText()
    finally:
        App.closeDocument(doc.Name)


def test_a_stale_3d_centerline_stops_applied_sections_and_names_the_change() -> None:
    doc, project = _source_doc("CRV1StoredCenterlineStale")
    try:
        _raise_profile(doc)

        with pytest.raises(RuntimeError, match=r"3D Centerline is stale \(profile@"):
            build_document_applied_section_set(doc, project=project)
    finally:
        App.closeDocument(doc.Name)


def test_rebuild_downstream_generates_a_missing_3d_centerline_for_existing_applied_sections() -> None:
    doc, project = _source_doc("CRV1StoredCenterlineRegenerate")
    try:
        applied = build_document_applied_section_set(doc, project=project)
        apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
        doc.removeObject(find_v1_centerline3d_object(doc).Name)

        report = rebuild_downstream(doc)

        assert report.rebuilt_stages == ("centerline3d", "applied_sections")
        assert to_centerline3d_result(find_v1_centerline3d_object(doc)) is not None
    finally:
        App.closeDocument(doc.Name)


def test_a_station_without_a_frame_stops_the_build_instead_of_switching_frame_source() -> None:
    # An Alignment without coordinates and no 3D Centerline: no frame can be resolved.
    request = AppliedSectionBuildRequest(
        project_id="proj-1",
        corridor_id="cor-1",
        alignment=AlignmentModel(
            schema_version=1,
            project_id="proj-1",
            alignment_id="align-1",
            geometry_sequence=[AlignmentElement("el-1", "tangent", 0.0, 100.0)],
        ),
        profile=ProfileModel(
            schema_version=1,
            project_id="proj-1",
            profile_id="prof-1",
            alignment_id="align-1",
            control_rows=[ProfileControlPoint("pvi-1", 0.0, 10.0), ProfileControlPoint("pvi-2", 100.0, 10.0)],
        ),
        assembly=AssemblySubassemblyModel(
            schema_version=1,
            project_id="proj-1",
            assembly_id="asm-1",
            template_rows=[
                SubassemblySectionTemplate(
                    template_id="tmpl-1",
                    template_kind="roadway",
                    subassembly_rows=[TemplateSubassembly(subassembly_id="lane-1", kind="lane", side="right", width=3.5)],
                )
            ],
        ),
        region_model=RegionModel(
            schema_version=1,
            project_id="proj-1",
            region_model_id="reg-1",
            alignment_id="align-1",
            region_rows=[RegionRow(region_id="region-1", station_start=0.0, station_end=100.0, template_ref="tmpl-1")],
        ),
        station=10.0,
        applied_section_id="sec-1",
    )

    with pytest.raises(RuntimeError, match=r"align-1 STA 10\.000: the 3D Centerline gives no frame here"):
        AppliedSectionService().build(request)
